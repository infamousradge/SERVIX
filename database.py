from pathlib import Path
import sqlite3, datetime, os, sys

APP_ROOT=Path(__file__).resolve().parent
if sys.platform == 'win32':
    DATA_ROOT=Path(os.environ.get('LOCALAPPDATA', Path.home()/'AppData'/'Local'))/'SERVIX'
else:
    DATA_ROOT=Path.home()/'.servix'
DATA=DATA_ROOT/'data'; DATA.mkdir(parents=True,exist_ok=True)
DB=DATA/'servix.db'

def connect():
    con=sqlite3.connect(DB); con.row_factory=sqlite3.Row; return con

def init_db():
    with connect() as con:
        con.executescript('''
        CREATE TABLE IF NOT EXISTS clients(id INTEGER PRIMARY KEY, code TEXT UNIQUE, name TEXT NOT NULL, contact TEXT, mobile TEXT, email TEXT, address TEXT, city TEXT, notes TEXT, created TEXT, modified TEXT);
        CREATE TABLE IF NOT EXISTS equipment(id INTEGER PRIMARY KEY, code TEXT UNIQUE, client_id INTEGER NOT NULL, make TEXT NOT NULL, model TEXT NOT NULL, serial TEXT, stock_id TEXT, equipment_type TEXT, sold_by TEXT, sold_date TEXT, warranty_till TEXT, amc_till TEXT, location TEXT, notes TEXT, created TEXT, modified TEXT);
        CREATE TABLE IF NOT EXISTS services(id INTEGER PRIMARY KEY, code TEXT UNIQUE, client_id INTEGER NOT NULL, equipment_id INTEGER NOT NULL, opened TEXT, request_source TEXT, reason TEXT NOT NULL, complaint TEXT NOT NULL, warranty TEXT NOT NULL, amc TEXT NOT NULL, engineer TEXT, priority TEXT, status TEXT, received_date TEXT, received_condition TEXT, diagnosis TEXT, work_done TEXT, final_result TEXT, foc_chargeable TEXT, service_charge REAL DEFAULT 0, parts_charge REAL DEFAULT 0, quote_status TEXT, quote_amount REAL DEFAULT 0, payment_status TEXT, amount_received REAL DEFAULT 0, dispatch_date TEXT, dispatch_mode TEXT, notes TEXT, modified TEXT);
        CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY, service_id INTEGER NOT NULL, event_date TEXT NOT NULL, note TEXT NOT NULL, user TEXT);
        CREATE TABLE IF NOT EXISTS service_updates(id INTEGER PRIMARY KEY, service_id INTEGER NOT NULL, update_date TEXT NOT NULL, engineer TEXT, update_type TEXT, diagnosis TEXT, work_done TEXT, result TEXT, next_action TEXT, user TEXT);
        CREATE INDEX IF NOT EXISTS idx_service_updates_service ON service_updates(service_id);
        CREATE TABLE IF NOT EXISTS calibration(id INTEGER PRIMARY KEY, service_id INTEGER UNIQUE, calibration_date TEXT, result TEXT, certificate_no TEXT, next_due TEXT, remarks TEXT);
        CREATE TABLE IF NOT EXISTS parts(id INTEGER PRIMARY KEY, service_id INTEGER, part_no TEXT, description TEXT, qty REAL, chargeable TEXT, amount REAL DEFAULT 0, remarks TEXT);
        CREATE TABLE IF NOT EXISTS attachments(id INTEGER PRIMARY KEY, service_id INTEGER, original_name TEXT, stored_path TEXT, kind TEXT, original_size INTEGER, stored_size INTEGER, created TEXT);
        CREATE TABLE IF NOT EXISTS exports(id INTEGER PRIMARY KEY, export_date TEXT, from_date TEXT, to_date TEXT, filename TEXT, record_count INTEGER);
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sequences(entity TEXT PRIMARY KEY, next_number INTEGER NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_services_code ON services(code);
        CREATE INDEX IF NOT EXISTS idx_services_status ON services(status);
        CREATE INDEX IF NOT EXISTS idx_equipment_serial ON equipment(serial);
        CREATE INDEX IF NOT EXISTS idx_history_service ON history(service_id);
        CREATE INDEX IF NOT EXISTS idx_parts_service ON parts(service_id);
        CREATE INDEX IF NOT EXISTS idx_attachments_service ON attachments(service_id);
        ''')
        # Safe additive migrations for databases created by earlier SERVIX builds.
        existing={r[1] for r in con.execute("PRAGMA table_info(services)")}
        additions={
            'pending_reason':'TEXT','work_date':'TEXT','root_cause':'TEXT','testing_result':'TEXT',
            'completion_date':'TEXT','closure_date':'TEXT','dispatch_reference':'TEXT'
        }
        for name,kind in additions.items():
            if name not in existing: con.execute(f'ALTER TABLE services ADD COLUMN {name} {kind}')
        defaults={'service_prefix':'SRV','service_start':'1','service_digits':'6','client_prefix':'CLI','client_start':'1','client_digits':'6','equipment_prefix':'SEQ','equipment_start':'1','equipment_digits':'6'}
        for key,value in defaults.items(): con.execute('INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)',(key,value))

def get_setting(key, default=''):
    with connect() as con:
        row=con.execute('SELECT value FROM settings WHERE key=?',(key,)).fetchone()
    return row[0] if row else default

def set_setting(key, value):
    with connect() as con:
        con.execute('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,str(value)))

def next_code(prefix, table):
    mapping={'services':'service','clients':'client','equipment':'equipment'}
    entity=mapping.get(table,table)
    with connect() as con:
        configured_prefix=con.execute('SELECT value FROM settings WHERE key=?',(f'{entity}_prefix',)).fetchone()
        start=con.execute('SELECT value FROM settings WHERE key=?',(f'{entity}_start',)).fetchone()
        digits=con.execute('SELECT value FROM settings WHERE key=?',(f'{entity}_digits',)).fetchone()
        p=(configured_prefix[0] if configured_prefix else prefix).strip() or prefix
        start_no=max(1,int(start[0] if start else 1)); width=max(1,int(digits[0] if digits else 6))
        row=con.execute('SELECT next_number FROM sequences WHERE entity=?',(entity,)).fetchone()
        if row:
            n=max(start_no,int(row[0]))
        else:
            # Existing installations continue above all already-issued numeric suffixes.
            issued=[]
            for x in con.execute(f'SELECT code FROM {table} WHERE code IS NOT NULL'):
                try: issued.append(int(str(x[0]).rsplit('-',1)[-1]))
                except (ValueError,TypeError): pass
            n=max([start_no]+[x+1 for x in issued])
        code=f'{p}-{n:0{width}d}'
        while con.execute(f'SELECT 1 FROM {table} WHERE code=?',(code,)).fetchone():
            n+=1; code=f'{p}-{n:0{width}d}'
        con.execute('INSERT INTO sequences(entity,next_number) VALUES(?,?) ON CONFLICT(entity) DO UPDATE SET next_number=excluded.next_number',(entity,n+1))
    return code

def now(): return datetime.datetime.now().isoformat(timespec='minutes')
def today(): return datetime.date.today().isoformat()
