import { useEffect, useRef, type ReactNode } from "react";
import { RefreshCw, X } from "lucide-react";
export function Label({
  children,
  tone = "",
}: {
  children: ReactNode;
  tone?: string;
}) {
  return <span className={`label ${tone}`}>{children}</span>;
}
export function ErrorMessage({ message }: { message: string }) {
  return (
    <div className="error" role="alert">
      {message}
    </div>
  );
}
export function Empty({ children }: { children: ReactNode }) {
  return <div className="empty">{children}</div>;
}
export function Loading() {
  return (
    <div className="loading" role="status">
      <RefreshCw className="spin" size={18} /> Loading evidence…
    </div>
  );
}

export function Modal({
  title,
  children,
  close,
}: {
  title: string;
  children: ReactNode;
  close: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const el = dialog.current!;
    el.showModal();
    return () => el.close();
  }, []);
  return (
    <dialog
      ref={dialog}
      className="detail-dialog"
      onCancel={close}
      aria-labelledby="dialog-title"
    >
      <div className="dialog-header">
        <div>
          <span className="eyebrow">EVIDENCE WORKSPACE</span>
          <h2 id="dialog-title">{title}</h2>
        </div>
        <button
          className="icon-button"
          aria-label="Close details"
          onClick={close}
        >
          <X size={20} />
        </button>
      </div>
      <div className="dialog-body">{children}</div>
    </dialog>
  );
}
