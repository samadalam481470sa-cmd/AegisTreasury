"""AegisTreasury demonstration API.

This service intentionally has NO authentication or authorization. It is a local
teaching demo and must never be exposed to the public internet. See SECURITY.md.
"""
import os
import sqlite3
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import core

DB_PATH = os.getenv('AEGIS_DB_PATH', 'aegis.db')
STATIC = Path(__file__).parent / 'static'

CONTENT_SECURITY_POLICY = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
    "connect-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self'; "
    "form-action 'self'"
)

# Simple per-client write budget. In-process only: a multi-worker deployment gets
# one budget per worker, so put a real limiter at the edge before exposing anything.
try:
    WRITE_LIMIT = max(1, int(os.getenv('AEGIS_WRITE_LIMIT', '120')))
except ValueError:
    WRITE_LIMIT = 120
WRITE_WINDOW_SECONDS = 60
_MAX_TRACKED_CLIENTS = 4096
_write_log: dict[str, list[float]] = {}
_write_lock = threading.Lock()


def connect():
    c = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    c.execute('PRAGMA busy_timeout=5000')
    return c


@asynccontextmanager
async def lifespan(app):
    db = connect()
    try:
        core.initialize(db)
    finally:
        db.close()
    yield


app = FastAPI(title='AegisTreasury', version='1.0.0',
              description='Synthetic demo treasury API; no authentication, local use only',
              lifespan=lifespan)
app.mount('/static', StaticFiles(directory=STATIC), name='static')


@app.middleware('http')
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers['Content-Security-Policy'] = CONTENT_SECURITY_POLICY
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    response.headers['Cross-Origin-Opener-Policy'] = 'same-origin'
    response.headers['Cross-Origin-Resource-Policy'] = 'same-origin'
    response.headers['Cache-Control'] = ('no-store' if request.url.path.startswith('/api/')
                                       else 'no-cache')
    return response


def allow_write(client_key: str) -> bool:
    """Sliding-window limiter so one client cannot flood the ledger with writes."""
    current = time.monotonic()
    cutoff = current - WRITE_WINDOW_SECONDS
    with _write_lock:
        hits = [stamp for stamp in _write_log.get(client_key, []) if stamp >= cutoff]
        if len(hits) >= WRITE_LIMIT:
            _write_log[client_key] = hits
            return False
        hits.append(current)
        _write_log[client_key] = hits
        if len(_write_log) > _MAX_TRACKED_CLIENTS:
            for key in [k for k, v in _write_log.items() if not v or v[-1] < cutoff]:
                _write_log.pop(key, None)
        return True


def write_guard(request: Request):
    client = request.client.host if request.client else 'unknown'
    if not allow_write(client):
        raise HTTPException(status_code=429, detail='Too many write requests; retry shortly')


class JournalLine(BaseModel):
    account_id: int
    amount_cents: int


class JournalIn(BaseModel):
    reference: str = Field(min_length=2, max_length=100)
    description: str = Field(min_length=2, max_length=250)
    lines: list[JournalLine] = Field(min_length=2, max_length=100)


class PaymentIn(BaseModel):
    reference: str = Field(min_length=2, max_length=100)
    counterparty: str = Field(min_length=2, max_length=100)
    amount_cents: int = Field(gt=0)
    source_account_id: int
    destination_account_id: int


class StatusIn(BaseModel):
    status: str = Field(max_length=20)


def result(fn):
    """Run a domain call on a dedicated connection and always close it."""
    db = connect()
    try:
        value = fn(db)
        if db.in_transaction:
            db.commit()
        return value
    except core.DomainError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except sqlite3.IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail='Conflicting data') from exc
    except sqlite3.Error as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail='Database unavailable') from exc
    finally:
        db.close()


@app.get('/')
def home():
    return FileResponse(STATIC / 'index.html')


@app.get('/api/health')
def health():
    return {'status': 'ok', 'mode': 'synthetic-demo'}


@app.get('/api/accounts')
def accounts():
    return result(core.accounts)


@app.get('/api/overview')
def overview():
    return result(core.analytics)


@app.get('/api/payments')
def payments():
    return result(core.payments)


@app.get('/api/journals')
def journals():
    return result(lambda db: [dict(x) for x in db.execute('SELECT * FROM journals ORDER BY id DESC')])


@app.get('/api/audit')
def audit():
    return result(lambda db: {'valid': core.verify_audit(db),
                              'events': [dict(x) for x in
                                         db.execute('SELECT * FROM audit ORDER BY id DESC LIMIT 100')]})


@app.post('/api/journals', status_code=201, dependencies=[Depends(write_guard)])
def post_journal(body: JournalIn):
    return {'id': result(lambda db: core.post_journal(
        db, body.reference, body.description, [x.model_dump() for x in body.lines]))}


@app.post('/api/payments', status_code=201, dependencies=[Depends(write_guard)])
def submit_payment(body: PaymentIn):
    return {'id': result(lambda db: core.submit_payment(db, **body.model_dump()))}


@app.post('/api/payments/{payment_id}/transition', dependencies=[Depends(write_guard)])
def transition(payment_id: int, body: StatusIn):
    return {'status': result(lambda db: core.transition_payment(db, payment_id, body.status))}


@app.get('/api/forecast')
def forecast(days: int = 30, daily_inflow_cents: int = 1850000,
             daily_outflow_cents: int = 2200000, shock_percent: int = 0):
    return result(lambda db: core.forecast(db, days, daily_inflow_cents,
                                           daily_outflow_cents, shock_percent))
