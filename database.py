from pathlib import Path
import sqlite3, datetime
ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'; DATA.mkdir(exist_ok=True)
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
        CREATE TABLE IF NOT EXISTS calibration(id INTEGER PRIMARY KEY, service_id INTEGER UNIQUE, calibration_date TEXT, result TEXT, certificate_no TEXT, next_due TEXT, remarks TEXT);
        CREATE TABLE IF NOT EXISTS parts(id INTEGER PRIMARY KEY, service_id INTEGER, part_no TEXT, description TEXT, qty REAL, chargeable TEXT, amount REAL DEFAULT 0, remarks TEXT);
        CREATE TABLE IF NOT EXISTS attachments(id INTEGER PRIMARY KEY, service_id INTEGER, original_name TEXT, stored_path TEXT, kind TEXT, original_size INTEGER, stored_size INTEGER, created TEXT);
        CREATE TABLE IF NOT EXISTS exports(id INTEGER PRIMARY KEY, export_date TEXT, from_date TEXT, to_date TEXT, filename TEXT, record_count INTEGER);
        ''')

def next_code(prefix, table):
    with connect() as con:
        n=con.execute(f'SELECT COALESCE(MAX(id),0)+1 FROM {table}').fetchone()[0]
    return f'{prefix}-{n:06d}'

def now(): return datetime.datetime.now().isoformat(timespec='minutes')
def today(): return datetime.date.today().isoformat()
