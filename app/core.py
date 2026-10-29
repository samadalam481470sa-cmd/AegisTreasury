"""Treasury domain logic. Monetary amounts are integer USD cents."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
import sqlite3
from contextlib import contextmanager

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS accounts (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, kind TEXT NOT NULL,
 currency TEXT NOT NULL DEFAULT 'USD', initial_cents INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS journals (
 id INTEGER PRIMARY KEY, reference TEXT NOT NULL UNIQUE, description TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS entries (
 id INTEGER PRIMARY KEY, journal_id INTEGER NOT NULL REFERENCES journals(id),
 account_id INTEGER NOT NULL REFERENCES accounts(id), amount_cents INTEGER NOT NULL CHECK(amount_cents <> 0)
);
CREATE TABLE IF NOT EXISTS payments (
 id INTEGER PRIMARY KEY, reference TEXT NOT NULL UNIQUE, counterparty TEXT NOT NULL,
 amount_cents INTEGER NOT NULL CHECK(amount_cents > 0), status TEXT NOT NULL,
 source_account_id INTEGER NOT NULL REFERENCES accounts(id),
 destination_account_id INTEGER NOT NULL REFERENCES accounts(id),
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 CHECK(status IN ('pending','approved','settled','rejected'))
);
CREATE TABLE IF NOT EXISTS audit (
 id INTEGER PRIMARY KEY, action TEXT NOT NULL, payload TEXT NOT NULL,
 prior_hash TEXT NOT NULL, event_hash TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_entries_account ON entries(account_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
"""

class DomainError(ValueError):
    pass

@contextmanager
def transaction(conn):
    try:
        conn.execute('BEGIN IMMEDIATE')
        yield
        conn.commit()
    except Exception:
        conn.rollback()
        raise

def initialize(conn):
    conn.executescript(SCHEMA)
    if conn.execute('SELECT COUNT(*) FROM accounts').fetchone()[0]:
        return
    with transaction(conn):
        rows = [
            ('Operating Cash','asset', 385000000), ('Reserve Cash','asset', 172000000),
            ('Settlement Clearing','asset', 92500000), ('Customer Liabilities','liability', -215000000),
            ('Treasury Equity','equity', -434500000),
        ]
        conn.executemany('INSERT INTO accounts(name,kind,initial_cents) VALUES(?,?,?)',rows)
        audit(conn,'seed',{'account_count':len(rows)})

def audit(conn,action,payload):
    last = conn.execute('SELECT event_hash FROM audit ORDER BY id DESC LIMIT 1').fetchone()
    prior = last[0] if last else 'GENESIS'
    encoded = json.dumps({'action':action,'payload':payload,'prior_hash':prior},sort_keys=True,separators=(',',':'))
    digest = hashlib.sha256(encoded.encode()).hexdigest()
    conn.execute('INSERT INTO audit(action,payload,prior_hash,event_hash) VALUES(?,?,?,?)',(action,json.dumps(payload,sort_keys=True),prior,digest))

def verify_audit(conn):
    events = conn.execute('SELECT action,payload,prior_hash,event_hash FROM audit ORDER BY id').fetchall()
    prior = 'GENESIS'
    for event in events:
        payload=json.loads(event['payload'])
        encoded=json.dumps({'action':event['action'],'payload':payload,'prior_hash':prior},sort_keys=True,separators=(',',':'))
        if event['prior_hash'] != prior or hashlib.sha256(encoded.encode()).hexdigest() != event['event_hash']:
            return False
        prior=event['event_hash']
    return True

def accounts(conn):
    return [dict(r) for r in conn.execute('''SELECT a.id,a.name,a.kind,a.currency,a.initial_cents,
      a.initial_cents+COALESCE(SUM(e.amount_cents),0) AS balance_cents
      FROM accounts a LEFT JOIN entries e ON a.id=e.account_id GROUP BY a.id ORDER BY a.id''')]

def post_journal(conn,reference,description,lines):
    if len(lines)<2 or any(not isinstance(x.get('amount_cents'),int) or isinstance(x.get('amount_cents'),bool) or x['amount_cents']==0 for x in lines):
        raise DomainError('Journal requires at least two nonzero integer-cent entries')
    if sum(x['amount_cents'] for x in lines)!=0:
        raise DomainError('Journal entries must net to zero')
    ids={x['id'] for x in accounts(conn)}
    if any(x.get('account_id') not in ids for x in lines):
        raise DomainError('Unknown account')
    with transaction(conn):
        try:
            cur=conn.execute('INSERT INTO journals(reference,description) VALUES(?,?)',(reference,description))
        except sqlite3.IntegrityError as exc:
            raise DomainError('Duplicate journal reference') from exc
        conn.executemany('INSERT INTO entries(journal_id,account_id,amount_cents) VALUES(?,?,?)',[(cur.lastrowid,x['account_id'],x['amount_cents']) for x in lines])
        audit(conn,'journal.posted',{'journal_id':cur.lastrowid,'reference':reference,'lines':lines})
    return cur.lastrowid

def submit_payment(conn,reference,counterparty,amount_cents,source_account_id,destination_account_id):
    if not isinstance(amount_cents,int) or isinstance(amount_cents,bool) or amount_cents<=0:
        raise DomainError('Payment amount must be positive integer cents')
    if source_account_id==destination_account_id:
        raise DomainError('Source and destination must differ')
    ids={x['id'] for x in accounts(conn)}
    if source_account_id not in ids or destination_account_id not in ids:
        raise DomainError('Unknown account')
    with transaction(conn):
        try:
            cur=conn.execute('INSERT INTO payments(reference,counterparty,amount_cents,status,source_account_id,destination_account_id) VALUES(?,?,?,?,?,?)',
                (reference,counterparty,amount_cents,'pending',source_account_id,destination_account_id))
        except sqlite3.IntegrityError as exc:
            raise DomainError('Duplicate payment reference') from exc
        audit(conn,'payment.submitted',{'payment_id':cur.lastrowid,'reference':reference,'amount_cents':amount_cents})
    return cur.lastrowid

def transition_payment(conn,payment_id,new_status):
    allowed={'pending':{'approved','rejected'},'approved':{'settled','rejected'}}
    with transaction(conn):
        payment=conn.execute('SELECT * FROM payments WHERE id=?',(payment_id,)).fetchone()
        if not payment:
            raise DomainError('Unknown payment')
        if new_status not in allowed.get(payment['status'],set()):
            raise DomainError('Invalid payment status transition')
        if new_status=='settled':
            amount=payment['amount_cents']
            available=next(x['balance_cents'] for x in accounts(conn) if x['id']==payment['source_account_id'])
            if available<amount:
                raise DomainError('Insufficient available balance')
            cur=conn.execute('INSERT INTO journals(reference,description) VALUES(?,?)',('PAY-'+payment['reference'],'Payment settlement'))
            conn.executemany('INSERT INTO entries(journal_id,account_id,amount_cents) VALUES(?,?,?)',[
                (cur.lastrowid,payment['source_account_id'],-amount),
                (cur.lastrowid,payment['destination_account_id'],amount)])
        conn.execute('UPDATE payments SET status=? WHERE id=?',(new_status,payment_id))
        audit(conn,'payment.'+new_status,{'payment_id':payment_id,'reference':payment['reference']})
    return new_status

def payments(conn):
    return [dict(x) for x in conn.execute('SELECT * FROM payments ORDER BY id DESC')]

def analytics(conn):
    aa=accounts(conn)
    cash=sum(x['balance_cents'] for x in aa if x['kind']=='asset')
    pending=conn.execute("SELECT COALESCE(SUM(amount_cents),0) FROM payments WHERE status IN ('pending','approved')").fetchone()[0]
    settled=conn.execute("SELECT COUNT(*) FROM payments WHERE status='settled'").fetchone()[0]
    return {'accounts':len(aa),'total_assets_cents':cash,'pending_outflows_cents':pending,
        'settled_payments':settled,'liquidity_coverage_ratio':round(cash / pending,2) if pending else None,
        'audit_valid':verify_audit(conn)}

def forecast(conn,days=30,daily_inflow_cents=1850000,daily_outflow_cents=2200000,shock_percent=0):
    if days<1 or days>365 or shock_percent<0 or shock_percent>100:
        raise DomainError('Invalid forecast parameters')
    opening=sum(x['balance_cents'] for x in accounts(conn) if x['kind']=='asset')
    pending=conn.execute("SELECT COALESCE(SUM(amount_cents),0) FROM payments WHERE status IN ('pending','approved')").fetchone()[0]
    daily_inflow=Decimal(daily_inflow_cents)
    daily_outflow=Decimal(daily_outflow_cents)*(Decimal(100+shock_percent)/100)
    result=[]
    for day in range(days+1):
        delta=(daily_inflow-daily_outflow)*day
        balance=opening-pending+int(delta.quantize(Decimal('1'),rounding=ROUND_HALF_UP))
        result.append({'date':(date.today()+timedelta(days=day)).isoformat(),'balance_cents':balance})
    return {'assumptions':{'daily_inflow_cents':daily_inflow_cents,'daily_outflow_cents':daily_outflow_cents,
              'shock_percent':shock_percent,'pending_outflows_cents':pending},'points':result,
              'min_balance_cents':min(x['balance_cents'] for x in result)}
