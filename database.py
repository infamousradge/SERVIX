from pathlib import Path
import sqlite3, datetime, os, sys, hashlib, hmac, secrets

APP_ROOT=Path(__file__).resolve().parent
if sys.platform == 'win32':
    DATA_ROOT=Path(os.environ.get('LOCALAPPDATA', Path.home()/'AppData'/'Local'))/'SERVIX'
else:
    DATA_ROOT=Path.home()/'.servix'
DATA=DATA_ROOT/'data'; DATA.mkdir(parents=True,exist_ok=True)
DB=DATA/'servix.db'

ROLES=('Administrator','Service Manager','Service Coordinator','Commercial / Accounts','Management / View Only')
ROLE_PERMISSIONS={
    'Administrator': {'*'},
    'Service Manager': {'dashboard','services','clients','equipment','warranty','engineers','parts','documents','reports'},
    'Service Coordinator': {'dashboard','services','clients','equipment','warranty','engineers','parts','documents'},
    'Commercial / Accounts': {'dashboard','services','clients','equipment','commercial','reports'},
    'Management / View Only': {'dashboard','services','clients','equipment','warranty','engineers','parts','commercial','documents','reports'},
}
PBKDF2_ITERATIONS=310000

def hash_password(password, salt=None):
    salt=salt or secrets.token_hex(16)
    digest=hashlib.pbkdf2_hmac('sha256',password.encode('utf-8'),bytes.fromhex(salt),PBKDF2_ITERATIONS).hex()
    return salt,digest

def verify_password(password,salt,digest):
    if not salt or not digest:return False
    _,candidate=hash_password(password,salt)
    return hmac.compare_digest(candidate,digest)

def authenticate(username,password):
    with connect() as con: row=con.execute('SELECT * FROM users WHERE lower(username)=lower(?) AND active=1',(username.strip(),)).fetchone()
    return row if row and verify_password(password,row['password_salt'],row['password_hash']) else None

def can(role,permission):
    allowed=ROLE_PERMISSIONS.get(role,set())
    return '*' in allowed or permission in allowed

def ensure_default_user():
    with connect() as con:
        if not con.execute('SELECT 1 FROM users LIMIT 1').fetchone():
            ts=datetime.datetime.now().isoformat(timespec='seconds')
            con.execute('INSERT INTO users(username,display_name,role,active,created,modified) VALUES(?,?,?,?,?,?)',('admin','Admin','Administrator',1,ts,ts))

def connect():
    con=sqlite3.connect(DB); con.row_factory=sqlite3.Row; return con

def init_db():
    with connect() as con:
        con.executescript('''
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, display_name TEXT NOT NULL, role TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1, password_salt TEXT, password_hash TEXT, must_change_password INTEGER NOT NULL DEFAULT 1, created TEXT, modified TEXT);
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
        CREATE TABLE IF NOT EXISTS commercial_discussions(id INTEGER PRIMARY KEY, service_id INTEGER NOT NULL, discussion_date TEXT NOT NULL, person TEXT, contact TEXT, method TEXT, amount REAL DEFAULT 0, approved TEXT, notes TEXT, user TEXT);
        CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY, service_id INTEGER NOT NULL, payment_date TEXT NOT NULL, amount REAL NOT NULL DEFAULT 0, mode TEXT, reference TEXT, notes TEXT, user TEXT);
        CREATE TABLE IF NOT EXISTS inventory_items(id INTEGER PRIMARY KEY, code TEXT UNIQUE, part_name TEXT NOT NULL, part_number TEXT, category TEXT, unit TEXT DEFAULT 'Nos', reorder_level REAL NOT NULL DEFAULT 0, active INTEGER NOT NULL DEFAULT 1, notes TEXT, created TEXT, modified TEXT);
        CREATE TABLE IF NOT EXISTS inventory_movements(id INTEGER PRIMARY KEY, item_id INTEGER NOT NULL, movement_date TEXT NOT NULL, movement_type TEXT NOT NULL, qty REAL NOT NULL, service_id INTEGER, reference TEXT, notes TEXT, username TEXT);
        CREATE TABLE IF NOT EXISTS engineers(id INTEGER PRIMARY KEY, code TEXT UNIQUE, name TEXT NOT NULL, mobile TEXT, email TEXT, specialization TEXT, active INTEGER NOT NULL DEFAULT 1, notes TEXT, created TEXT, modified TEXT);
        CREATE TABLE IF NOT EXISTS audit_log(id INTEGER PRIMARY KEY, event_date TEXT NOT NULL, username TEXT, entity_type TEXT NOT NULL, entity_id TEXT, action TEXT NOT NULL, details TEXT);
        CREATE TABLE IF NOT EXISTS backup_history(id INTEGER PRIMARY KEY, backup_date TEXT NOT NULL, filename TEXT NOT NULL, status TEXT NOT NULL, notes TEXT);
        CREATE INDEX IF NOT EXISTS idx_commercial_discussions_service ON commercial_discussions(service_id);
        CREATE INDEX IF NOT EXISTS idx_payments_service ON payments(service_id);
        CREATE INDEX IF NOT EXISTS idx_services_code ON services(code);
        CREATE INDEX IF NOT EXISTS idx_services_status ON services(status);
        CREATE INDEX IF NOT EXISTS idx_equipment_serial ON equipment(serial);
        CREATE INDEX IF NOT EXISTS idx_history_service ON history(service_id);
        CREATE INDEX IF NOT EXISTS idx_parts_service ON parts(service_id);
        CREATE INDEX IF NOT EXISTS idx_attachments_service ON attachments(service_id);
        ''')
        user_existing={r[1] for r in con.execute("PRAGMA table_info(users)")}
        for name,kind in {'password_salt':'TEXT','password_hash':'TEXT','must_change_password':'INTEGER NOT NULL DEFAULT 1'}.items():
            if name not in user_existing: con.execute(f'ALTER TABLE users ADD COLUMN {name} {kind}')
        # Safe additive migrations for databases created by earlier SERVIX builds.
        existing={r[1] for r in con.execute("PRAGMA table_info(services)")}
        additions={
            'pending_reason':'TEXT','work_date':'TEXT','root_cause':'TEXT','testing_result':'TEXT',
            'completion_date':'TEXT','closure_date':'TEXT','dispatch_reference':'TEXT',
            'next_action':'TEXT','cancel_reason':'TEXT','service_location':'TEXT','pickup_location':'TEXT','drop_location':'TEXT','location_notes':'TEXT','quote_no':'TEXT','quote_date':'TEXT','po_reference':'TEXT','invoice_no':'TEXT','invoice_date':'TEXT','invoice_amount':'REAL DEFAULT 0','payment_reference':'TEXT'
        }
        for name,kind in additions.items():
            if name not in existing: con.execute(f'ALTER TABLE services ADD COLUMN {name} {kind}')
        defaults={'service_prefix':'SRV','service_start':'1','service_digits':'6','client_prefix':'CLI','client_start':'1','client_digits':'6','equipment_prefix':'SEQ','equipment_start':'1','equipment_digits':'6','company_short_name':'HAC','company_name':'HAC','system_title':'Service Management System','system_subtitle':'Service   |   Calibration   |   Warranty   |   AMC','company_logo_path':'','repeat_complaint_days':'60','auto_backup_enabled':'1','auto_backup_days':'1','auto_backup_keep':'14'}
        for key,value in defaults.items(): con.execute('INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)',(key,value))
    ensure_default_user()

def get_setting(key, default=''):
    with connect() as con:
        row=con.execute('SELECT value FROM settings WHERE key=?',(key,)).fetchone()
    return row[0] if row else default

def set_setting(key, value):
    with connect() as con:
        con.execute('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,str(value)))


def audit(username,entity_type,entity_id,action,details=''):
    with connect() as con: con.execute('INSERT INTO audit_log(event_date,username,entity_type,entity_id,action,details) VALUES(?,?,?,?,?,?)',(now(),username or '',entity_type,str(entity_id or ''),action,details))

def repeat_complaints(equipment_id, complaint='', days=None):
    days=int(days or get_setting('repeat_complaint_days','60') or 60)
    words={w.lower() for w in complaint.split() if len(w)>3}
    with connect() as con:
        rows=con.execute("""SELECT code,opened,complaint,status FROM services WHERE equipment_id=? AND reason='Breakdown / Complaint'
                            AND date(opened)>=date('now',?) ORDER BY id DESC""",(equipment_id,f'-{days} day')).fetchall()
    if not words:return rows
    return [r for r in rows if not words or words.intersection({w.lower() for w in (r['complaint'] or '').split() if len(w)>3})]

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
