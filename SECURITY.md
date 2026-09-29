# Security policy

Version 0.1 is a local demonstrator; no production support SLA is promised. Read `docs/security.md` before using operational data or exposing a service.

Do not open a public issue containing credentials, customer data or a working exploit against an actual deployment. Once the repository is published, use GitHub's private vulnerability reporting if enabled. The maintainer must enable that channel before inviting public security reports; no email address or response-time commitment is invented here.

A useful report includes affected version, the trust boundary crossed, a minimal synthetic reproduction, expected vs. actual behavior, and impact. Contributors should preserve confidentiality while a fix is prepared.

Never reuse the public demo database passwords. `.env` and local databases are intentionally ignored. The default loopback restriction is part of the demo's security boundary.
