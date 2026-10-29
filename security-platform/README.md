# ◈ AegisLedger Ops

**Unified security intelligence for cybersecurity, fintech risk and engineering operations.**

AegisLedger Ops is a hands-on portfolio project combining a cybersecurity alerting workflow, a rule-based transaction risk engine, operational service visibility, and a tamper-evident audit chain. It is intended to demonstrate backend engineering, application security, practical fraud-detection design and DevSecOps fundamentals.

> **Educational simulation.** All example events, account identities, IP addresses and service metrics are synthetic. There is no live banking, SIEM or cloud provider integration. **Not production-ready or security audited.**

## Capabilities

| Area | Implemented feature | Relevant roles |
|------|---------------------|----------------|
| Cybersecurity | Failed auth, malicious activity and access-denial detections, alert triage | SOC Analyst, Security Engineer |
| Fintech | Rule-based high-value transfer, new beneficiary, dispute and velocity signals | Fraud Analyst, Fintech Engineer |
| Engineering | REST event ingestion, services dashboard, latency/error/uptime snapshots | Backend, Infrastructure, SRE |
| Application security | Argon2id, opaque sessions, CSRF, RBAC, secure response headers, input validation | AppSec, DevSecOps |
| Audit | SHA-256 linked event/action history and verification | Compliance, Security Engineering |
| Delivery | Dockerfile, Compose, GitHub Actions test workflow, CodeQL | Platform, DevSecOps |

## Tech stack

- **Backend:** Python 3.12+, FastAPI, Pydantic, SQLite, Argon2id.
- **Frontend:** Responsive HTML5, CSS3, vanilla JavaScript, dynamically rendered SVG analytics (no CDN dependencies).
- **Deployment and quality:** Docker, Docker Compose, pytest, GitHub Actions, CodeQL.
- **API style:** JSON REST endpoints using same-origin authenticated sessions.

## Run locally (Python)

```bash
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt

# Interactive bootstrap — prompts for your password; none is bundled.
python -m app.manage init-admin --email you@example.com

# Load 12 synthetic events and 5 static example services.
python -m app.manage seed-demo

# Start local server
uvicorn app.main:app --reload
```

Visit **http://127.0.0.1:8000** and log in with the admin account you created.

### Docker alternative

```bash
docker compose up --build -d
docker compose exec aegisledger python -m app.manage init-admin --email you@example.com
docker compose exec aegisledger python -m app.manage seed-demo
```

Access **http://127.0.0.1:8000**. The Compose port is intentionally bound to localhost. An `aegis_data` volume preserves the local demo database.

## Roles and feature access

| Role | Read dashboard / alerts | Inject synthetic events | Triage alerts | View / verify audit |
|------|-------------------------|-------------------------|--------------|---------------------|
| admin | Yes | Yes | Yes | Yes |
| analyst | Yes | Yes | Yes | No |
| viewer | Yes | No | No | No |

To add a least-privilege user, run:

```bash
python -m app.manage create-user --email analyst@example.com --role analyst
python -m app.manage create-user --email viewer@example.com --role viewer
```

## Demo walkthrough

1. Sign in. The overview shows alert volumes, an activity chart and severity breakdown.
2. Explore **Threat intelligence**, review suspicious events and mark an alert as investigating or resolved.
3. Navigate to **Event explorer** and use **Simulate event**. Choose a large transfer, unauthorized access, malware indicator, chargeback or normal payment.
4. The risk engine generates an explainable integer score (0–100) and detection signals; elevated risk becomes an alert.
5. Compare synthetic infrastructure service statuses under **Infrastructure**.
6. As an administrator, use **Audit integrity → Verify audit chain**. The log covers login, event ingestion and alert state changes.

## Selected API routes

| HTTP | Route | Access |
|------|-------|--------|
| POST | `/api/auth/login` | Public, JSON login |
| GET | `/api/auth/me` | Signed in |
| POST | `/api/auth/logout` | Signed in + CSRF |
| GET | `/api/dashboard` | Signed in |
| GET | `/api/events?category=fintech` | Signed in |
| POST | `/api/events` | Admin/analyst + CSRF |
| GET | `/api/alerts` | Signed in |
| PATCH | `/api/alerts/{id}` | Admin/analyst + CSRF |
| GET | `/api/services` | Signed in |
| GET | `/api/audit` | Admin |
| GET | `/api/audit/verify` | Admin |
| GET | `/healthz` | Public health check |

## Run tests

```bash
python -m pytest -q
```

Includes tests for rule outcomes, login required, role permissions, CSRF, validation, alert workflow, audit tamper detection and failed-login throttling.

## Engineering notes

The rules are intentionally **deterministic and explainable**. A high-value transfer, new payee, unusual device and elevated event velocity contribute separate weights; scores are capped at 100. Thresholds: low under 40, medium 40–69, high 70–89, critical 90–100. Medium+ events create alerts. This is not an ML classifier; it can later be extended with model scoring and ground-truth evaluation.

Hash-chained audits detect changes to past event records provided the attacker cannot rewrite every hash. This is not blockchain, external notarization or an append-only managed ledger. Refer to [SECURITY.md](SECURITY.md) for design boundaries and production blockers.

## Roadmap

- [ ] PostgreSQL, Alembic migrations and integration tests against a real database
- [ ] Microsoft Entra ID / OIDC SSO with MFA and enterprise RBAC
- [ ] Prometheus/Grafana metrics and OpenTelemetry tracing
- [ ] Kafka or Redis Streams for streaming ingestion and asynchronous risk decisions
- [ ] Webhooks with signed requests, idempotency tokens and replay protection
- [ ] Event enrichment using permitted threat intelligence providers
- [ ] Independent audit-log anchoring and backup integrity checks
- [ ] Production deployment guides, disaster recovery and load tests

## Suggested GitHub repository

**Repository:** `aegis-ledger-ops`  
**Description:** `Security operations platform combining fintech fraud detection, threat intelligence, RBAC, hash-chained audit logs, and infrastructure monitoring using Python/FastAPI and Docker.`  
**Topics:** `cybersecurity` `fintech` `security-engineering` `fraud-detection` `fastapi` `python` `devsecops` `rbac` `audit-logging` `docker` `rest-api`

MIT licensed. Review and replace copyright metadata if needed.
