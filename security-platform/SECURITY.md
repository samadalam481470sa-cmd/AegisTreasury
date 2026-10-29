# Security policy and threat model

## Scope
This repository is an educational, locally hosted portfolio demonstration. It does **not** connect to real banks, cards, SIEMs, or cloud infrastructure. Infrastructure metrics are seeded snapshots, not continuously scraped telemetry. The fraud rules are illustrative heuristics, not validated detection models.

## Implemented controls
- Argon2id-based password storage. No seed account and no hardcoded admin password.
- HttpOnly, SameSite=Strict, short-lived opaque session cookie (database stores token hash); CSRF header validation on every authenticated write.
- Separate admin, analyst, viewer roles; protected event ingestion, alert changes and audit-chain access.
- Strict same-origin browser access; standard anti-framing, nosniff and CSP headers.
- Validate event schemas, amounts and IP addresses; query DB with bound parameters.
- Login throttling based on identity + directly connected IP (per-database, suitable only for a single instance).
- Actions recorded with a hash chain; modifying a record without recalculating subsequent hashes causes integrity verification to fail.
- CI tests and CodeQL workflow.
- No third-party frontend JS/CDN dependencies or tracking.

## Known limitations / production blockers
**Do not deploy publicly to protect real financial or sensitive data without a substantial security review.**

- SQLite, no formal schema migrations, no high availability, and no external immutable log storage.
- Hash chain is tamper-evident *within this database*, not immutable or cryptographically anchored externally; a privileged DB operator could rewrite the whole chain.
- No enterprise SSO, MFA, passkeys, SCIM, account recovery, password reset, multi-tenancy, KMS, managed secrets, or fine-grained tenant/resource authorization.
- Login throttling is basic; add an external rate limiter, reverse-proxy/WAF protections and distributed controls before exposure.
- Browser session safety depends on serving the app over HTTPS and setting AEGIS_HTTPS_ONLY=true. Do not trust arbitrary X-Forwarded-* headers.
- Financial detection rules use fictional examples. They are not financial advice, compliance certification, a fraud-prevention guarantee or a bank-grade risk model.
- Service dashboard shows static seeded values, not connected Prometheus or cloud metrics.
- Add audit retention policies, independent backups, monitoring, replay-resistant ingestion and external SIEM integration if evolving this into a service.

## Responsible disclosure
For a public repository, open a private GitHub Security Advisory rather than publishing exploit details in an issue.
