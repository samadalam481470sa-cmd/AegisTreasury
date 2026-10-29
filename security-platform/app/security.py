"""Opaque database-backed sessions, Argon2id passwords and role checks."""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError

ph = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)
SESSION_HOURS = 8
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


def now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def hash_value(token: str):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def hash_password(password: str):
    if len(password) < 14 or len(password) > 256:
        raise ValueError("Password must be 14–256 characters")
    return ph.hash(password)


def verify_password(encoded: str, password: str):
    try:
        return ph.verify(encoded, password)
    except (VerifyMismatchError, VerificationError, ValueError):
        return False


def issue_session(db, user_id):
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    expiry = (datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS)).isoformat()
    db.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
    db.execute("INSERT INTO sessions(token_hash,user_id,csrf_hash,expires_at) VALUES(?,?,?,?)",
               (hash_value(token), user_id, hash_value(csrf), expiry))
    return token, csrf


def load_session(db, token):
    if not token:
        return None
    row = db.execute("""SELECT u.id, u.email, u.role, s.csrf_hash, s.expires_at
                        FROM sessions s JOIN users u ON u.id=s.user_id
                        WHERE s.token_hash=?""", (hash_value(token),)).fetchone()
    if not row or datetime.fromisoformat(row["expires_at"]) <= datetime.now(timezone.utc):
        return None
    return dict(row)


def check_csrf(session, submitted):
    return bool(submitted and hmac.compare_digest(session["csrf_hash"], hash_value(submitted)))


def too_many_attempts(db, identity):
    row = db.execute("SELECT failed_count,first_failed_at FROM login_attempts WHERE identity=?", (identity,)).fetchone()
    if not row:
        return False
    recent = datetime.fromisoformat(row["first_failed_at"]) > datetime.now(timezone.utc) - timedelta(minutes=LOCKOUT_MINUTES)
    return recent and row["failed_count"] >= MAX_FAILED_ATTEMPTS


def record_failure(db, identity):
    row = db.execute("SELECT first_failed_at FROM login_attempts WHERE identity=?", (identity,)).fetchone()
    old = datetime.fromisoformat(row["first_failed_at"]) if row else None
    if not old or old <= datetime.now(timezone.utc) - timedelta(minutes=LOCKOUT_MINUTES):
        db.execute("INSERT INTO login_attempts(identity,failed_count,first_failed_at) VALUES(?,1,?) "
                   "ON CONFLICT(identity) DO UPDATE SET failed_count=1,first_failed_at=excluded.first_failed_at",
                   (identity, now()))
    else:
        db.execute("UPDATE login_attempts SET failed_count=failed_count+1 WHERE identity=?", (identity,))
