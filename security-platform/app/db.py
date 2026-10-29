"""SQLite persistence for the portfolio demonstration. No live financial data."""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_FILE = os.getenv("AEGIS_DB_PATH", "data/aegis.db")


def connect():
    path = Path(os.getenv("AEGIS_DB_PATH", DB_FILE))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(path), timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA busy_timeout = 10000")
    db.execute("PRAGMA journal_mode = WAL")
    return db


@contextmanager
def database():
    db = connect()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    with database() as db:
        db.executescript("""
          CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin','analyst','viewer')),
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
          );
          CREATE TABLE IF NOT EXISTS sessions (
            token_hash TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            csrf_hash TEXT NOT NULL,
            expires_at TEXT NOT NULL
          );
          CREATE TABLE IF NOT EXISTS login_attempts (
            identity TEXT PRIMARY KEY,
            failed_count INTEGER NOT NULL DEFAULT 0,
            first_failed_at TEXT NOT NULL
          );
          CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            occurred_at TEXT NOT NULL,
            category TEXT NOT NULL,
            kind TEXT NOT NULL,
            actor TEXT NOT NULL,
            source_ip TEXT NOT NULL,
            resource TEXT NOT NULL,
            amount REAL,
            currency TEXT,
            risk_score INTEGER NOT NULL,
            signals_json TEXT NOT NULL,
            details_json TEXT NOT NULL,
            ingested_at TEXT NOT NULL
          );
          CREATE INDEX IF NOT EXISTS idx_events_occurred ON events(occurred_at DESC);
          CREATE INDEX IF NOT EXISTS idx_events_actor ON events(actor, occurred_at DESC);
          CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL REFERENCES events(id),
            title TEXT NOT NULL,
            severity TEXT NOT NULL CHECK(severity IN ('critical','high','medium','low')),
            status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','investigating','resolved')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
          );
          CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            actor TEXT NOT NULL,
            action TEXT NOT NULL,
            entity TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            prev_hash TEXT NOT NULL,
            entry_hash TEXT NOT NULL
          );
          CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            environment TEXT NOT NULL,
            status TEXT NOT NULL,
            latency_ms INTEGER NOT NULL,
            error_rate REAL NOT NULL,
            uptime REAL NOT NULL,
            last_checked TEXT NOT NULL
          );
        """)
