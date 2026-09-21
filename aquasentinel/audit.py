"""Local hash chain. A database owner can rewrite the entire chain."""
import argparse
import json
import sqlite3
from .engine import digest

TABLES = ['observations','reviews','environmental_datasets','weather_captures','alert_outbox']


def install(db):
    db.create_function('aqua_hash', 1, lambda value: digest(json.loads(value)))
    db.execute('CREATE TABLE IF NOT EXISTS audit_events (id INTEGER PRIMARY KEY, kind TEXT NOT NULL, record_id TEXT NOT NULL, payload TEXT NOT NULL, prev_hash TEXT NOT NULL, event_hash TEXT NOT NULL)')
    for table in TABLES:
        columns=[r[1] for r in db.execute('PRAGMA table_info('+table+')')]
        payload='json_object('+','.join("'"+c+"',NEW."+c for c in columns)+')'
        prev="COALESCE((SELECT event_hash FROM audit_events ORDER BY id DESC LIMIT 1),'GENESIS')"
        db.execute(f'''CREATE TRIGGER IF NOT EXISTS audit_{table} AFTER INSERT ON {table}
            BEGIN INSERT INTO audit_events(kind,record_id,payload,prev_hash,event_hash)
            VALUES('{table}',NEW.id,{payload},{prev},aqua_hash(json_array({prev},'{table}',CAST(NEW.id AS TEXT),{payload}))); END''')
    db.commit()


def verify(db):
    db.row_factory=sqlite3.Row
    previous='GENESIS';covered=set();count=0
    for row in db.execute('SELECT * FROM audit_events ORDER BY id'):
        if row['kind'] not in TABLES:raise ValueError('Unknown event kind')
        expected=digest([previous,row['kind'],row['record_id'],json.loads(row['payload'])])
        if row['prev_hash']!=previous or row['event_hash']!=expected:raise ValueError('Broken audit chain at '+str(row['id']))
        actual=db.execute('SELECT * FROM '+row['kind']+' WHERE id=?',(row['record_id'],)).fetchone()
        if actual is None or dict(actual)!=json.loads(row['payload']):raise ValueError('Logged row changed or removed')
        previous=row['event_hash'];covered.add((row['kind'],row['record_id']));count+=1
    unlogged=sum(1 for table in TABLES for r in db.execute('SELECT id FROM '+table) if (table,str(r[0])) not in covered)
    return {'verified_events':count,'chain_tip':previous,'unlogged_legacy_rows':unlogged,
        'limit':'Local consistency only. A database owner can rewrite data and recompute the chain; no external anchor.'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('database');a=p.parse_args()
    with sqlite3.connect(a.database) as db:print(json.dumps(verify(db),indent=2))
