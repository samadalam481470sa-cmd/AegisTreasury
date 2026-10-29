"""Local sample data only, designed to have no personal or financial identifiers."""
from .security import now


def seed(db):
    from .main import EventIn, ingest
    # Idempotent seed. Never run against live financial systems.
    existing = db.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    if existing:
        return {"events_added": 0, "reason": "database already contains events"}
    sample = [
        ("fintech", "payment", "customer_102", "198.51.100.12", "card-gateway", 129.00, {}),
        ("cybersecurity", "login_success", "engineer_18", "203.0.113.12", "admin-portal", None, {}),
        ("fintech", "transfer", "customer_205", "192.0.2.51", "bank-ledger", 18500.00, {"new_payee": True}),
        ("cybersecurity", "access_denied", "unknown_client", "192.0.2.99", "secrets-store", None, {"unrecognized_device": True}),
        ("infrastructure", "deployment", "ci-bot", "198.51.100.6", "risk-engine", None, {}),
        ("fintech", "payment", "customer_301", "192.0.2.10", "card-gateway", 42.00, {}),
        ("cybersecurity", "malware_detected", "workstation_7", "203.0.113.26", "endpoint-agent", None, {}),
        ("fintech", "payment_chargeback", "customer_221", "203.0.113.77", "dispute-service", 780.00, {}),
        ("fintech", "transfer", "customer_205", "192.0.2.51", "bank-ledger", 5900.00, {"new_payee": True}),
        ("cybersecurity", "api_abuse", "bot_client_9", "203.0.113.60", "public-api", None, {"unrecognized_device": True}),
        ("infrastructure", "service_error", "worker_2", "192.0.2.4", "payment-processor", None, {}),
        ("fintech", "transfer", "customer_308", "198.51.100.88", "bank-ledger", 150.00, {}),
    ]
    for category, kind, actor, ip, resource, amount, details in sample:
        ingest(db, EventIn(category=category, kind=kind, actor=actor, source_ip=ip,
                           resource=resource, amount=amount,
                           currency="USD" if amount is not None else None, details=details), "demo-seeder")
    for name, environment, status, latency, error, uptime in [
        ("Payment Gateway", "production", "healthy", 84, 0.12, 99.98),
        ("Fraud Risk Engine", "production", "healthy", 112, 0.20, 99.95),
        ("Identity Service", "production", "healthy", 58, 0.06, 99.99),
        ("Transaction Ledger", "production", "healthy", 96, 0.11, 99.97),
        ("API Edge", "production", "degraded", 312, 2.34, 98.75),
    ]:
        db.execute("""INSERT OR IGNORE INTO services(name,environment,status,latency_ms,error_rate,uptime,last_checked)
                      VALUES(?,?,?,?,?,?,?)""", (name, environment, status, latency, error, uptime, now()))
    return {"events_added": len(sample), "services_added": 5}
