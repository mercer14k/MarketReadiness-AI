"""Transactional snapshot store. PostgreSQL in Compose; SQLite for native demo/tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256

from sqlalchemy import JSON, DateTime, String, create_engine, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from marketreadiness.domain.schemas import Dataset


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String(180), primary_key=True)
    kind: Mapped[str] = mapped_column(String(30), index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class Pointer(Base):
    __tablename__ = "pointers"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(180))


class Idempotency(Base):
    __tablename__ = "idempotency"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    request_hash: Mapped[str] = mapped_column(String(64))
    response: Mapped[dict] = mapped_column(JSON)


class Conflict(Exception):
    pass


class Store:
    def __init__(self, url: str, read_url: str | None = None):
        options = (
            {"connect_args": {"check_same_thread": False}}
            if url.startswith("sqlite")
            else {"pool_pre_ping": True}
        )
        self.engine = create_engine(url, **options)
        self.read_engine = create_engine(read_url, pool_pre_ping=True) if read_url else self.engine
        Base.metadata.create_all(self.engine)

    def healthy(self):
        with self.read_engine.connect() as c:
            c.execute(text("SELECT 1"))
        return True

    def get(self, id: str):
        with Session(self.read_engine) as s:
            row = s.get(Document, id)
            return row.payload if row else None

    def list(self, kind: str, offset=0, limit=50):
        with Session(self.read_engine) as s:
            rows = s.scalars(
                select(Document)
                .where(Document.kind == kind)
                .order_by(Document.created_at.desc(), Document.id)
                .offset(offset)
                .limit(limit)
            )
            return [r.payload for r in rows]

    def active(self) -> Dataset | None:
        with Session(self.read_engine) as s:
            pointer = s.get(Pointer, "active_dataset")
            if not pointer:
                return None
            return Dataset.model_validate(s.get(Document, pointer.document_id).payload)

    def write(
        self,
        key: str,
        fingerprint: str,
        docs: list[tuple[str, str, dict]],
        response: dict,
        activate: str | None = None,
    ):
        """Documents, active pointer and retry response commit together.

        A PostgreSQL advisory transaction lock serializes imports/scenario writes;
        uniqueness constraints make repeated request keys safe on SQLite as well.
        """
        hashed_key = sha256(key.encode()).hexdigest()
        try:
            with Session(self.engine) as s, s.begin():
                if self.engine.dialect.name == "postgresql":
                    s.execute(text("SELECT pg_advisory_xact_lock(725839)"))
                prior = s.get(Idempotency, hashed_key)
                if prior:
                    if prior.request_hash != fingerprint:
                        raise Conflict("Idempotency key was already used for a different request")
                    return prior.response
                for id, kind, payload in docs:
                    existing = s.get(Document, id)
                    if existing and existing.payload != payload:
                        raise Conflict(
                            "Immutable document ID already exists with different content"
                        )
                    if not existing:
                        s.add(Document(id=id, kind=kind, payload=payload))
                if activate:
                    pointer = s.get(Pointer, "active_dataset")
                    if pointer:
                        pointer.document_id = activate
                    else:
                        s.add(Pointer(id="active_dataset", document_id=activate))
                s.add(Idempotency(id=hashed_key, request_hash=fingerprint, response=response))
            return response
        except IntegrityError as exc:
            with Session(self.read_engine) as s:
                prior = s.get(Idempotency, hashed_key)
                if prior and prior.request_hash == fingerprint:
                    return prior.response
            raise Conflict("Concurrent update conflict; retry with the same key") from exc

    def close(self):
        self.engine.dispose()
        if self.read_engine is not self.engine:
            self.read_engine.dispose()


def fingerprint(payload: dict) -> str:
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
