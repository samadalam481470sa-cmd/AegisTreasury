"""AegisLedger Ops: security, synthetic fintech risk and service operations API."""
import json
import os
import ipaddress
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import Cookie, Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator, model_validator

from .audit import append_audit, verify_chain
from .db import connect, init_db
from .risk import evaluate
from .security import (check_csrf, hash_value, issue_session, load_session, now,
                       record_failure, too_many_attempts, verify_password)

ROOT = Path(__file__).resolve().parent.parent
COOKIE_SECURE = os.getenv("AEGIS_HTTPS_ONLY", "false").lower() == "true"


@asynccontextmanager
async def lifespan(_app):
    init_db()
    yield


app = FastAPI(title="AegisLedger Ops", version="1.0.0", lifespan=lifespan,
              docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


@app.middleware("http")
async def secure_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = ("default-src 'self'; script-src 'self'; style-src 'self'; "
                                                   "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; "
                                                   "object-src 'none'; base-uri 'self'; form-action 'self'")
    response.headers["Cache-Control"] = "no-store" if request.url.path.startswith("/api/") else "no-cache"
    if COOKIE_SECURE:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


def get_db():
    db = connect()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def current_user(aegis_session: str | None = Cookie(default=None), db=Depends(get_db)):
    session = load_session(db, aegis_session)
    if not session:
        raise HTTPException(401, "Sign in required")
    return session


def authorized_write(request: Request, user=Depends(current_user)):
    if not check_csrf(user, request.headers.get("X-CSRF-Token")):
        raise HTTPException(403, "CSRF check failed")
    return user


def roles(*allowed):
    def check(user=Depends(authorized_write)):
        if user["role"] not in allowed:
            raise HTTPException(403, "Insufficient permissions")
        return user
    return check


def admin_read(user=Depends(current_user)):
    if user["role"] != "admin":
        raise HTTPException(403, "Admin role required")
    return user


class Login(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class EventIn(BaseModel):
    category: Literal["fintech", "cybersecurity", "infrastructure"]
    kind: Literal["transfer", "payment", "payment_chargeback", "login_success", "login_failed",
                  "access_denied", "api_abuse", "malware_detected", "deployment", "service_error"]
    actor: str = Field(min_length=2, max_length=100)
    source_ip: str = Field(min_length=3, max_length=45)
    resource: str = Field(min_length=2, max_length=100)
    amount: float | None = Field(default=None, ge=0, le=1000000000)
    currency: Literal["USD", "EUR", "GBP"] | None = None
    details: dict[str, Any] = Field(default_factory=dict)

    @field_validator("source_ip")
    @classmethod
    def validate_ip(cls, value):
        ipaddress.ip_address(value)
        return value

    @field_validator("details")
    @classmethod
    def limited_details(cls, value):
        if len(json.dumps(value)) > 2000:
            raise ValueError("Details cannot exceed 2KB")
        return value

    @model_validator(mode="after")
    def validate_category_and_amount(self):
        kinds_by_category = {
            "fintech": {"transfer", "payment", "payment_chargeback"},
            "cybersecurity": {"login_success", "login_failed", "access_denied", "api_abuse", "malware_detected"},
            "infrastructure": {"deployment", "service_error"},
        }
        if self.kind not in kinds_by_category[self.category]:
            raise ValueError("Event type does not match category")
        if self.category == "fintech" and (self.amount is None or self.currency is None):
            raise ValueError("Financial events require an amount and currency")
        if self.category != "fintech" and (self.amount is not None or self.currency is not None):
            raise ValueError("Non-financial events cannot have transaction amounts")
        return self


class AlertUpdate(BaseModel):
    status: Literal["open", "investigating", "resolved"]


def _json(row):
    out = dict(row)
    for field in ("details_json", "signals_json"):
        if field in out:
            out[field.removesuffix("_json")] = json.loads(out.pop(field))
    return out


def ingest(db, event: EventIn, actor: str):
    current = datetime.now(timezone.utc)
    cutoff = (current - timedelta(minutes=10)).isoformat(timespec="milliseconds")
    recent = db.execute("SELECT COUNT(*) AS n FROM events WHERE actor=? AND occurred_at>=?",
                        (event.actor, cutoff)).fetchone()["n"]
    result = evaluate(event.kind, event.amount, recent, event.details)
    timestamp = now()
    cur = db.execute("""INSERT INTO events
        (occurred_at,category,kind,actor,source_ip,resource,amount,currency,risk_score,
         signals_json,details_json,ingested_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (timestamp, event.category, event.kind, event.actor, event.source_ip, event.resource,
         event.amount, event.currency, result.score, json.dumps(result.signals),
         json.dumps(event.details, sort_keys=True), timestamp))
    event_id = cur.lastrowid
    alert_id = None
    if result.score >= 40:
        title = {
            "transfer": "Potentially fraudulent money movement",
            "payment_chargeback": "Payment dispute risk detected",
            "malware_detected": "Malware indicator detected",
            "login_failed": "Repeated authentication failures",
            "access_denied": "Suspicious access attempt",
            "api_abuse": "Potential API abuse detected",
        }.get(event.kind, "Elevated security risk detected")
        cur2 = db.execute("""INSERT INTO alerts(event_id,title,severity,status,created_at,updated_at)
                             VALUES (?,?,?,'open',?,?)""",
                          (event_id, title, result.severity, timestamp, timestamp))
        alert_id = cur2.lastrowid
    append_audit(db, actor=actor, action="event.ingested", entity="event", entity_id=event_id,
                 payload={"kind": event.kind, "risk_score": result.score, "alert_id": alert_id})
    return {"id": event_id, "risk_score": result.score, "severity": result.severity,
            "signals": result.signals, "alert_id": alert_id}


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/healthz")
def health():
    return {"status": "ok"}


@app.post("/api/auth/login")
def login(payload: Login, request: Request, response: Response, db=Depends(get_db)):
    email = payload.email.strip().lower()
    client_ip = request.client.host if request.client else "unknown"
    identity = hash_value(f"{email}|{client_ip}")
    if too_many_attempts(db, identity):
        raise HTTPException(429, "Too many attempts; try again in 15 minutes")
    user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    if not user or not verify_password(user["password_hash"], payload.password):
        record_failure(db, identity)
        db.commit()  # persist failed attempts even though the request returns 401
        raise HTTPException(401, "Invalid credentials")
    db.execute("DELETE FROM login_attempts WHERE identity=?", (identity,))
    token, csrf = issue_session(db, user["id"])
    response.set_cookie("aegis_session", token, max_age=8*60*60, httponly=True,
                        secure=COOKIE_SECURE, samesite="strict", path="/")
    response.set_cookie("aegis_csrf", csrf, max_age=8*60*60, httponly=False,
                        secure=COOKIE_SECURE, samesite="strict", path="/")
    append_audit(db, actor=email, action="auth.login", entity="user", entity_id=user["id"], payload={"role": user["role"]})
    return {"email": email, "role": user["role"]}


@app.get("/api/auth/me")
def me(user=Depends(current_user)):
    return {"email": user["email"], "role": user["role"]}


@app.post("/api/auth/logout")
def logout(response: Response, request: Request, user=Depends(authorized_write), db=Depends(get_db)):
    token = request.cookies.get("aegis_session", "")
    db.execute("DELETE FROM sessions WHERE token_hash=?", (hash_value(token),))
    append_audit(db, actor=user["email"], action="auth.logout", entity="user", entity_id=user["id"], payload={})
    response.delete_cookie("aegis_session", path="/", secure=COOKIE_SECURE, samesite="strict")
    response.delete_cookie("aegis_csrf", path="/", secure=COOKIE_SECURE, samesite="strict")
    return {"ok": True}


@app.get("/api/dashboard")
def dashboard(_user=Depends(current_user), db=Depends(get_db)):
    totals = db.execute("""SELECT COUNT(*) AS event_count,
                          COALESCE(ROUND(AVG(risk_score)),0) AS avg_risk,
                          SUM(CASE WHEN category='fintech' THEN 1 ELSE 0 END) AS transactions
                          FROM events""").fetchone()
    alerts = db.execute("""SELECT status,COUNT(*) AS n FROM alerts GROUP BY status""").fetchall()
    severity = db.execute("""SELECT severity,COUNT(*) AS n FROM alerts GROUP BY severity""").fetchall()
    activity = db.execute("""SELECT substr(occurred_at,1,10) AS day,COUNT(*) AS n FROM events
                             GROUP BY day ORDER BY day DESC LIMIT 7""").fetchall()
    return {**dict(totals), "alerts": {r["status"]: r["n"] for r in alerts},
            "severity": {r["severity"]: r["n"] for r in severity},
            "activity": [dict(x) for x in reversed(activity)],
            "active_services": db.execute("SELECT COUNT(*) FROM services WHERE status='healthy'").fetchone()[0],
            "total_services": db.execute("SELECT COUNT(*) FROM services").fetchone()[0]}


@app.get("/api/events")
def events(category: str | None = None, limit: int = 50, _user=Depends(current_user), db=Depends(get_db)):
    if limit < 1 or limit > 200:
        raise HTTPException(422, "limit must be 1–200")
    if category and category not in {"fintech", "cybersecurity", "infrastructure"}:
        raise HTTPException(422, "Invalid category")
    query = "SELECT * FROM events" + (" WHERE category=?" if category else "") + " ORDER BY id DESC LIMIT ?"
    rows = db.execute(query, (category, limit) if category else (limit,)).fetchall()
    return [_json(row) for row in rows]


@app.post("/api/events", status_code=201)
def create_event(event: EventIn, user=Depends(roles("admin", "analyst")), db=Depends(get_db)):
    return ingest(db, event, user["email"])


@app.get("/api/alerts")
def list_alerts(_user=Depends(current_user), db=Depends(get_db)):
    rows = db.execute("""SELECT a.*,e.actor,e.kind,e.risk_score,e.resource
                         FROM alerts a JOIN events e ON a.event_id=e.id
                         ORDER BY a.id DESC LIMIT 200""").fetchall()
    return [dict(row) for row in rows]


@app.patch("/api/alerts/{alert_id}")
def update_alert(alert_id: int, payload: AlertUpdate, user=Depends(roles("admin", "analyst")), db=Depends(get_db)):
    old = db.execute("SELECT status FROM alerts WHERE id=?", (alert_id,)).fetchone()
    if not old:
        raise HTTPException(404, "Alert not found")
    db.execute("UPDATE alerts SET status=?,updated_at=? WHERE id=?", (payload.status, now(), alert_id))
    append_audit(db, actor=user["email"], action="alert.status_changed", entity="alert", entity_id=alert_id,
                 payload={"from": old["status"], "to": payload.status})
    return {"id": alert_id, "status": payload.status}


@app.get("/api/services")
def services(_user=Depends(current_user), db=Depends(get_db)):
    return [dict(row) for row in db.execute("SELECT * FROM services ORDER BY name").fetchall()]


@app.get("/api/audit")
def audit(_user=Depends(admin_read), db=Depends(get_db)):
    return [dict(row) for row in db.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 100")]


@app.get("/api/audit/verify")
def audit_verify(_user=Depends(admin_read), db=Depends(get_db)):
    return verify_chain(db)
