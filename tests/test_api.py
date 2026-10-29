import os
import pytest
from fastapi.testclient import TestClient
from app import api

@pytest.fixture()
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(api,'DB_PATH',str(tmp_path/'test.db'))
    with TestClient(api.app) as c: yield c

def test_health_and_accounts(client):
    assert client.get('/api/health').json()['status']=='ok'
    a=client.get('/api/accounts').json()
    assert len(a)==5
    assert sum(x['balance_cents'] for x in a)==0

def test_journal_balancing(client):
    bad=client.post('/api/journals',json={'reference':'J1','description':'Test','lines':[{'account_id':1,'amount_cents':100},{'account_id':2,'amount_cents':-99}]})
    assert bad.status_code==400
    good=client.post('/api/journals',json={'reference':'J1','description':'Test','lines':[{'account_id':1,'amount_cents':-100},{'account_id':2,'amount_cents':100}]})
    assert good.status_code==201
    assert client.post('/api/journals',json={'reference':'J1','description':'Test','lines':[{'account_id':1,'amount_cents':-100},{'account_id':2,'amount_cents':100}]}).status_code==400

def test_payment_lifecycle_and_atomic_posting(client):
    payload={'reference':'PAY-001','counterparty':'Vendor','amount_cents':12000,'source_account_id':1,'destination_account_id':2}
    r=client.post('/api/payments',json=payload)
    assert r.status_code==201
    i=r.json()['id']
    assert client.post(f'/api/payments/{i}/transition',json={'status':'settled'}).status_code==400
    assert client.post(f'/api/payments/{i}/transition',json={'status':'approved'}).status_code==200
    before=client.get('/api/accounts').json()
    assert client.post(f'/api/payments/{i}/transition',json={'status':'settled'}).status_code==200
    after=client.get('/api/accounts').json()
    assert after[0]['balance_cents']==before[0]['balance_cents']-12000
    assert after[1]['balance_cents']==before[1]['balance_cents']+12000
    assert client.post(f'/api/payments/{i}/transition',json={'status':'settled'}).status_code==400

def test_insufficient_funds(client):
    r=client.post('/api/payments',json={'reference':'P2','counterparty':'Large payment','amount_cents':9999999999,'source_account_id':1,'destination_account_id':2})
    i=r.json()['id']
    client.post(f'/api/payments/{i}/transition',json={'status':'approved'})
    assert client.post(f'/api/payments/{i}/transition',json={'status':'settled'}).status_code==400
    assert client.get('/api/payments').json()[0]['status']=='approved'

def test_forecast_stress(client):
    base=client.get('/api/forecast?days=10').json()
    shocked=client.get('/api/forecast?days=10&shock_percent=40').json()
    assert len(base['points'])==11
    assert shocked['min_balance_cents']<base['min_balance_cents']

def test_audit_integrity(client):
    assert client.get('/api/audit').json()['valid'] is True
    with api.connect() as db:
        db.execute("UPDATE audit SET action='tampered' WHERE id=1")
        db.commit()
    assert client.get('/api/audit').json()['valid'] is False

def test_validation_and_page(client):
    assert 'text/html' in client.get('/').headers['content-type']
    assert client.post('/api/payments',json={'reference':'xx'}).status_code==422
    assert client.get('/api/forecast?days=500').status_code==400
