"""Transparent deterministic fraud/security rules for explainable portfolio demos."""
from dataclasses import dataclass


@dataclass(frozen=True)
class RiskResult:
    score: int
    severity: str
    signals: list[str]


def evaluate(kind: str, amount: float | None = None, recent_events: int = 0, details: dict | None = None) -> RiskResult:
    details = details or {}
    score, signals = 0, []
    suspicious_kinds = {"login_failed", "access_denied", "api_abuse", "malware_detected"}
    if kind in suspicious_kinds:
        score += 35
        signals.append("suspicious_security_activity")
    if kind == "malware_detected":
        score += 55
        signals.append("malware_indicator")
    if kind == "payment_chargeback":
        score += 65
        signals.append("chargeback_detected")
    if kind == "transfer" and amount is not None and amount >= 10000:
        score += 65
        signals.append("large_financial_transfer")
    elif kind == "transfer" and amount is not None and amount >= 5000:
        score += 30
        signals.append("elevated_transfer_amount")
    if kind == "transfer" and details.get("new_payee") is True:
        score += 30
        signals.append("new_beneficiary")
    if details.get("unrecognized_device") is True:
        score += 30
        signals.append("unrecognized_device")
    if recent_events >= 5:
        score += 40
        signals.append("velocity_anomaly")
    elif recent_events >= 3:
        score += 20
        signals.append("elevated_activity_velocity")
    score = min(score, 100)
    severity = "critical" if score >= 90 else "high" if score >= 70 else "medium" if score >= 40 else "low"
    return RiskResult(score, severity, signals)
