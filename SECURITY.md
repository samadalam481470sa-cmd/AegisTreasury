# Security policy

This repository contains two independent, locally hosted educational projects:

| Project | Path | Purpose |
|---|---|---|
| **AegisTreasury** | `app/` | Synthetic double-entry treasury demo (FastAPI + SQLite) |
| **AegisLedger Ops** | `security-platform/` | Security operations / fraud alerting demo with accounts and RBAC |

Neither is a production service. Neither processes real money, real customers or real
security telemetry. Both are portfolio demonstrations built on synthetic data.

## Reporting a vulnerability

Please **do not open a public issue** for a security problem.

- Use GitHub's **private vulnerability reporting**: *Security* tab → *Report a vulnerability*
  (this opens a private GitHub Security Advisory).
- Include the affected project (`app/` or `security-platform/`), the version or commit,
  reproduction steps, and the impact you believe it has.
- Expect an initial response within about seven days. This is a personal portfolio
  repository maintained on a best-effort basis: there is **no SLA, no bug bounty and no
  payment** for reports.

Please act in good faith: do not access data that is not yours, do not run destructive
tests, and give reasonable time for a fix before any public disclosure.

## Supported versions

Only the latest commit on the default branch is maintained. There are no backported
security releases and no published support window.

## Controls in place

### AegisTreasury (`app/`)

**This application has no authentication and no authorization by design.** It is a
single-user teaching demo. Anyone who can reach it can read and write the ledger.
It is safe only when bound to loopback (`app/__main__.py` and `compose.yaml` do this).

What it does implement:

- Strict Content-Security-Policy (`script-src 'self'`, no inline script), `nosniff`,
  `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, COOP/CORP and a
  `Permissions-Policy`, plus `Cache-Control: no-store` on API responses.
- Pydantic-validated request bodies with bounded lengths, and integer-cent amounts only.
- Balanced-journal and payment-state invariants enforced in the domain layer; every write
  happens inside a single SQLite transaction with rollback on failure.
- Parameterised SQL everywhere (no string-built queries) and a managed connection per
  request that is always closed, so malformed or repeated calls cannot exhaust file
  descriptors.
- Per-client write budget (`AEGIS_WRITE_LIMIT`, default 120 writes/minute) returning
  HTTP 429, to blunt accidental or malicious write floods.
- Generic error responses: internal database errors are never reflected to callers.
- Hash-chained audit events for tamper detection.

### AegisLedger Ops (`security-platform/`)

- Argon2id password hashing; no default account, no hardcoded credentials, minimum
  password length 14.
- Opaque, database-backed sessions: only a SHA-256 token hash is stored; HttpOnly,
  `SameSite=Strict`, fixed 8-hour expiry; `Secure` when `AEGIS_HTTPS_ONLY=true`.
- CSRF: per-session token stored server-side, sent as `X-CSRF-Token`, verified with
  `hmac.compare_digest` on every authenticated write.
- Role-based access control (`admin`, `analyst`, `viewer`) with least privilege on event
  ingestion, alert triage and audit access.
- Login throttling (5 failures / 15 minutes per identity + source IP) returning HTTP 429,
  and constant-cost failures so response timing does not reveal which emails exist.
- Strict CSP, anti-framing, `nosniff`, no-referrer, COOP/CORP, `no-store` on API routes,
  HSTS when serving over HTTPS. Docs/OpenAPI endpoints are disabled.
- Input validation on every field (enums, bounded strings, validated IP addresses, 2 KB
  event-detail cap); bound SQL parameters throughout.
- Container hardening: non-root user, `read_only` root filesystem, `tmpfs` only for
  `/tmp`, `cap_drop: ALL`, `no-new-privileges`, published on `127.0.0.1` only.

### Repository level

- CodeQL analysis (Python + JavaScript) on every push and pull request plus a weekly
  schedule, and dependency vulnerability auditing (`pip-audit`) in CI.
- Dependabot update PRs for pip dependencies and GitHub Actions.
- `.gitignore` excludes `.env` variants, databases and virtualenvs so secrets and local
  data cannot be committed by accident.

## Known limitations

These are deliberate scope boundaries, not oversights. Read them before judging fitness.

**AegisTreasury**

- No authentication, no authorization, no multi-user separation, no HTTPS termination.
- SQLite is single-file and single-node; no migrations, encryption at rest, backups or HA.
- The hash chain is tamper-**evident only**. Anyone with database write access can
  recompute the whole chain. It is not an external, immutable or anchored ledger.
- The forecast is a constant-cash-flow projection, not a predictive model.
- The write limiter is in-process, so it is per-worker and resets on restart.

**AegisLedger Ops**

- SQLite, no migrations, no high availability, no external audit retention.
- No SSO/OIDC, MFA, passkeys, account recovery, self-service password reset or
  multi-tenancy.
- Throttling is database-backed and per-instance; a distributed attacker with many IPs
  can spread attempts. Add an edge rate limiter / WAF before any exposure.
- Session safety depends on real HTTPS; do not trust `X-Forwarded-*` headers.
- Fraud rules are illustrative heuristics, not a validated detection model, and produce
  false positives and false negatives.

**Both**

- Not independently audited, not penetration-tested, and not certified against any
  standard (SOC 2, ISO 27001, PCI DSS, etc.). See [LEGAL.md](LEGAL.md).

## If you fork this to deploy it

At minimum: put it behind HTTPS with a reverse proxy, replace SQLite with a server
database, add real authentication (OIDC + MFA) and per-tenant authorization, move secrets
to a managed secret store, enable structured audit logging with external retention,
add monitoring and backups, pin and scan dependencies, and get an independent security
review. Do not put real customer, card or health data into either project.
