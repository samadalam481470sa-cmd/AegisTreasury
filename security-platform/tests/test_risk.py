from app.risk import evaluate


def test_large_transfer_and_new_payee_is_critical():
    result = evaluate('transfer', 22000, 0, {'new_payee': True})
    assert result.score == 95
    assert result.severity == 'critical'
    assert 'large_financial_transfer' in result.signals


def test_normal_payment_is_low_risk():
    result = evaluate('payment', 39, 0, {})
    assert result.score == 0
    assert result.signals == []


def test_repeated_security_events_raise_risk():
    result = evaluate('login_failed', None, 5, {'unrecognized_device': True})
    assert result.score == 100
    assert 'velocity_anomaly' in result.signals


def test_score_never_exceeds_100():
    result = evaluate('malware_detected', None, 100, {'unrecognized_device': True})
    assert result.score == 100
