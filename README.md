# AegisTreasury

**Treasury intelligence, payment controls, and liquidity scenario analysis — a full-stack fintech engineering portfolio project.**

AegisTreasury is a **local synthetic-data demonstration**, not a financial product. It features a balanced double-entry general ledger, account balances, controlled payment lifecycle, simulated liquidity projections, stress scenarios, cryptographically hash-linked audit events, and a responsive browser dashboard.

## Features

- **Balanced journals** — every posting must have at least two nonzero lines summing to exactly zero; all amounts use **integer cents**.
- **Payment lifecycle** — `pending → approved → settled` or rejected, with illegal transitions blocked.
- **Atomic settlement** — payment status and accounting entries update in one SQLite transaction; insufficient balances fail safely.
- **Risk and liquidity analytics** — balance overview, outstanding payments, coverage ratio, 1–365 day projections and adjustable outflow stress.
- **Tamper-evident audit history** — deterministic SHA-256 chain verification (demonstration only; an operator with database access can rewrite the chain).
- **REST API** — documented automatically at `/docs`, request validation with Pydantic.
- **Responsive operations UI**, Docker Compose, CI and pytest coverage.

## Run locally

Requires Python 3.11+.

```bash
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows: .venv\\Scripts\\activate
pip install -r requirements-dev.txt
python -m app
```

Open **http://127.0.0.1:8000**. API docs: **http://127.0.0.1:8000/docs**. The database initializes automatically with fictional balances. You can run `python -m pytest -q` to execute tests.

Docker: `docker compose up --build` (binds to localhost only).

## API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/overview` | Treasury KPIs |
| GET | `/api/accounts` | Current balances |
| GET | `/api/journals` | Journal history |
| POST | `/api/journals` | Balanced accounting posting |
| GET | `/api/payments` | Payment queue |
| POST | `/api/payments` | Create payment |
| POST | `/api/payments/{id}/transition` | Approve, settle, or reject |
| GET | `/api/forecast` | Configurable liquidity simulation |
| GET | `/api/audit` | Audit integrity and events |
| GET | `/api/health` | Health check |

### Example payment

```bash
curl -X POST http://127.0.0.1:8000/api/payments \\
  -H 'Content-Type: application/json' \\
  -d '{"reference":"INV-2026-001","counterparty":"Example Vendor","amount_cents":125000,"source_account_id":1,"destination_account_id":3}'
```

Then `POST /api/payments/1/transition` with `{"status":"approved"}` and subsequently `{"status":"settled"}`.

## Architecture

```text
Browser (HTML/CSS/JS)
        |
    FastAPI + Pydantic
        |
 Treasury domain services
 | ledger | payment states | stress simulation | audit |
        |
 SQLite (transactional local persistence)
```

## Security and limitations

**Do not deploy this demo publicly as is.** There is no authentication, authorization, access control, multi-user separation, request throttling, or secure operational key management. Seeded balances and counterparties are fictional. There are no bank integrations, funds transfers, real-time market feeds, or regulatory compliance claims. API inputs are validated, but this is educational software, not production-grade banking infrastructure. The scenario forecast assumes constant daily cash flows and is not a predictive model. For production, add role-based auth, approvals with separation of duties, PostgreSQL, migrations, encryption, backups, idempotency keys, monitoring, and immutable external audit retention.

## Tech stack

Python • FastAPI • Pydantic • SQLite • JavaScript • HTML/CSS • Docker • GitHub Actions • pytest

## Resume description

> Built AegisTreasury, a full-stack treasury operations platform with atomic double-entry ledger posting, payment-state workflows, tamper-evident event logging, liquidity forecasting and scenario stress testing, using Python, FastAPI, SQLite, JavaScript, and automated CI tests.

MIT License.
