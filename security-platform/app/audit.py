"""SHA-256 hash chain (tamper-evident, NOT immutable against DB admins)."""
import hashlib
import json
from .security import now

GENESIS = "0" * 64


def canonical(record):
    return json.dumps(record, separators=(",", ":"), sort_keys=True, ensure_ascii=True)


def digest(prev_hash, payload):
    return hashlib.sha256((prev_hash + "|" + canonical(payload)).encode("utf-8")).hexdigest()


def append_audit(db, *, actor, action, entity, entity_id, payload):
    # Serialize writers so concurrent inserts cannot fork the hash chain.
    db.execute("UPDATE audit_logs SET entry_hash=entry_hash WHERE id=-1")
    previous = db.execute("SELECT entry_hash FROM audit_logs ORDER BY id DESC LIMIT 1").fetchone()
    prev_hash = previous["entry_hash"] if previous else GENESIS
    timestamp = now()
    payload_json = canonical(payload)
    record = dict(created_at=timestamp, actor=actor, action=action, entity=entity,
                  entity_id=str(entity_id), payload_json=payload_json)
    new_hash = digest(prev_hash, record)
    db.execute("INSERT INTO audit_logs(created_at,actor,action,entity,entity_id,payload_json,prev_hash,entry_hash) "
               "VALUES(?,?,?,?,?,?,?,?)", (timestamp, actor, action, entity, str(entity_id), payload_json, prev_hash, new_hash))
    return new_hash


def verify_chain(db):
    previous = GENESIS
    rows = db.execute("SELECT * FROM audit_logs ORDER BY id").fetchall()
    for row in rows:
        payload = {key: row[key] for key in ("created_at", "actor", "action", "entity", "entity_id", "payload_json")}
        if row["prev_hash"] != previous or digest(previous, payload) != row["entry_hash"]:
            return {"valid": False, "entries": len(rows), "failed_at": row["id"]}
        previous = row["entry_hash"]
    return {"valid": True, "entries": len(rows), "head": previous}
