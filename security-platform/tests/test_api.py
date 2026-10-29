import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import database
from app.security import hash_password

PASSWORD = "CorrectHorseBatteryStaple!2026"


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv('AEGIS_DB_PATH', str(tmp_path / 'test.db'))
    with TestClient(app) as client:
        with database() as db:
            for email, role in [('admin@example.test', 'admin'), ('analyst@example.test', 'analyst'), ('viewer@example.test', 'viewer')]:
                db.execute('INSERT INTO users(email,password_hash,role) VALUES(?,?,?)',
                           (email, hash_password(PASSWORD), role))
        yield client


def login(client, role='admin'):
    res = client.post('/api/auth/login', json={'email': f'{role}@example.test', 'password': PASSWORD})
    assert res.status_code == 200
    return client.cookies['aegis_csrf']


def sample_event():
    return {'category': 'fintech', 'kind': 'transfer', 'actor': 'sample_customer',
            'source_ip': '192.0.2.99', 'resource': 'bank-ledger', 'amount': 23000,
            'currency': 'USD', 'details': {'new_payee': True}}


def test_auth_required_and_login(client):
    assert client.get('/api/dashboard').status_code == 401
    login(client)
    assert client.get('/api/dashboard').status_code == 200
    assert client.get('/api/auth/me').json()['role'] == 'admin'


def test_csrf_required_for_mutation(client):
    token = login(client)
    assert client.post('/api/events', json=sample_event()).status_code == 403
    result = client.post('/api/events', json=sample_event(), headers={'X-CSRF-Token': token})
    assert result.status_code == 201
    assert result.json()['risk_score'] == 95
    assert result.json()['alert_id'] is not None


def test_role_permissions(client):
    token = login(client, 'viewer')
    assert client.post('/api/events', json=sample_event(), headers={'X-CSRF-Token': token}).status_code == 403
    assert client.get('/api/audit').status_code == 403
    assert client.get('/api/events').status_code == 200


def test_alert_workflow_and_audit_validation(client):
    token = login(client)
    created = client.post('/api/events', json=sample_event(), headers={'X-CSRF-Token': token}).json()
    alert_id = created['alert_id']
    updated = client.patch(f'/api/alerts/{alert_id}', json={'status': 'investigating'},
                           headers={'X-CSRF-Token': token})
    assert updated.status_code == 200
    assert updated.json()['status'] == 'investigating'
    assert client.get('/api/audit/verify').json()['valid'] is True
    with database() as db:
        db.execute('UPDATE audit_logs SET action=? WHERE id=?', ('tampered', 1))
    assert client.get('/api/audit/verify').json()['valid'] is False


def test_source_ip_validation(client):
    token = login(client)
    bad = sample_event();bad['source_ip'] = 'not-an-ip'
    assert client.post('/api/events', json=bad, headers={'X-CSRF-Token': token}).status_code == 422


def test_failed_logins_throttled(client):
    for _ in range(5):
        assert client.post('/api/auth/login', json={'email': 'admin@example.test', 'password': 'wrong'}).status_code == 401
    assert client.post('/api/auth/login', json={'email': 'admin@example.test', 'password': PASSWORD}).status_code == 429
