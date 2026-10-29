"""AegisTreasury demonstration API. No authentication: NEVER expose on public internet."""
import os
import sqlite3
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from . import core

DB_PATH=os.getenv('AEGIS_DB_PATH','aegis.db')
STATIC=Path(__file__).parent/'static'

def connect():
    c=sqlite3.connect(DB_PATH,timeout=10,check_same_thread=False)
    c.row_factory=sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    c.execute('PRAGMA busy_timeout=5000')
    return c

@asynccontextmanager
async def lifespan(app):
    with connect() as db: core.initialize(db)
    yield

app=FastAPI(title='AegisTreasury',version='1.0.0',description='Synthetic demo treasury API; not production safe',lifespan=lifespan)
app.mount('/static',StaticFiles(directory=STATIC),name='static')

class JournalLine(BaseModel):
    account_id:int
    amount_cents:int
class JournalIn(BaseModel):
    reference:str=Field(min_length=2,max_length=100)
    description:str=Field(min_length=2,max_length=250)
    lines:list[JournalLine]=Field(min_length=2)
class PaymentIn(BaseModel):
    reference:str=Field(min_length=2,max_length=100)
    counterparty:str=Field(min_length=2,max_length=100)
    amount_cents:int=Field(gt=0)
    source_account_id:int
    destination_account_id:int
class StatusIn(BaseModel):
    status:str

def result(fn):
    try:
        with connect() as db: return fn(db)
    except core.DomainError as e:
        raise HTTPException(status_code=400,detail=str(e)) from e

@app.get('/')
def home(): return FileResponse(STATIC/'index.html')
@app.get('/api/health')
def health():return {'status':'ok','mode':'synthetic-demo'}
@app.get('/api/accounts')
def accounts():return result(core.accounts)
@app.get('/api/overview')
def overview():return result(core.analytics)
@app.get('/api/payments')
def payments():return result(core.payments)
@app.get('/api/journals')
def journals():return result(lambda db:[dict(x) for x in db.execute('SELECT * FROM journals ORDER BY id DESC')])
@app.get('/api/audit')
def audit():return result(lambda db:{'valid':core.verify_audit(db),'events':[dict(x) for x in db.execute('SELECT * FROM audit ORDER BY id DESC LIMIT 100')]})
@app.post('/api/journals',status_code=201)
def post_journal(body:JournalIn):return {'id':result(lambda db:core.post_journal(db,body.reference,body.description,[x.model_dump() for x in body.lines]))}
@app.post('/api/payments',status_code=201)
def submit_payment(body:PaymentIn):return {'id':result(lambda db:core.submit_payment(db,**body.model_dump()))}
@app.post('/api/payments/{payment_id}/transition')
def transition(payment_id:int,body:StatusIn):return {'status':result(lambda db:core.transition_payment(db,payment_id,body.status))}
@app.get('/api/forecast')
def forecast(days:int=30,daily_inflow_cents:int=1850000,daily_outflow_cents:int=2200000,shock_percent:int=0):
    return result(lambda db:core.forecast(db,days,daily_inflow_cents,daily_outflow_cents,shock_percent))
