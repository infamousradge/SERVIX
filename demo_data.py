"""Seed an isolated, fictional workspace for reviewing SERVIX workflows."""
from datetime import date, timedelta

from database import connect, hash_password, now


DEMO_PASSWORD = 'Demo@1234'


def seed_demo_data():
    """Create the sample records once; safe to call on every demo launch."""
    salt, digest = hash_password(DEMO_PASSWORD)
    today = date.today()
    ts = now()
    with connect() as con:
        seeded = con.execute("SELECT value FROM settings WHERE key='demo_seeded'").fetchone()
        if seeded and seeded['value'] == '2':
            return
        if seeded and seeded['value'] == '1':
            _expand_demo_data(con, today, ts)
            con.execute("UPDATE settings SET value='2' WHERE key='demo_seeded'")
            return

        con.execute("""UPDATE users SET display_name='Demo Admin', role='Administrator', active=1,
                     password_salt=?, password_hash=?, must_change_password=0, modified=?
                     WHERE username='admin'""", (salt, digest, ts))

        client1 = con.execute("""INSERT INTO clients
            (code,name,contact,mobile,email,address,city,notes,created,modified)
            VALUES(?,?,?,?,?,?,?,?,?,?)""", (
                'CLI-DEMO-001', 'Bluewave Audiology Centre [DEMO]', 'Maya Rao',
                '90000 10001', 'bluewave.demo@servix.local', '12 Lakeview Road',
                'Chennai', 'DEMO record. Use this mobile or email to test duplicate detection.', ts, ts
            )).lastrowid
        client2 = con.execute("""INSERT INTO clients
            (code,name,contact,mobile,email,address,city,notes,created,modified)
            VALUES(?,?,?,?,?,?,?,?,?,?)""", (
                'CLI-DEMO-002', 'Northside ENT & Hearing [DEMO]', 'Kiran Dev',
                '90000 10002', 'northside.demo@servix.local', '44 Green Park Avenue',
                'Chennai', 'Fictional sample client for workspace previews.', ts, ts
            )).lastrowid
        engineer = con.execute("""INSERT INTO engineers
            (code,name,mobile,email,specialization,active,notes,created,modified)
            VALUES(?,?,?,?,?,1,?,?,?)""", (
                'ENG-DEMO-001', 'Arun Kumar [DEMO]', '90000 20001',
                'arun.demo@servix.local', 'Audiology equipment service',
                'Sample engineer account.', ts, ts
            )).lastrowid
        equipment1 = con.execute("""INSERT INTO equipment
            (code,client_id,make,model,serial,stock_id,equipment_type,sold_by,sold_date,
             warranty_till,amc_till,location,notes,created,modified)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                'SEQ-DEMO-001', client1, 'MAICO', 'MA 42', 'DEMO-SN-001',
                'DEMO-ASSET-001', 'Diagnostic Audiometer', 'Us', today.isoformat(),
                (today + timedelta(days=365)).isoformat(), (today + timedelta(days=730)).isoformat(),
                'Audiology Room 1', 'DEMO equipment. Use serial DEMO-SN-001 to test serial duplicate protection.', ts, ts
            )).lastrowid
        equipment2 = con.execute("""INSERT INTO equipment
            (code,client_id,make,model,serial,stock_id,equipment_type,sold_by,sold_date,
             warranty_till,amc_till,location,notes,created,modified)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                'SEQ-DEMO-002', client2, 'PATH MEDICAL', 'Sentiero Desktop', 'DEMO-SN-002',
                'DEMO-ASSET-002', 'OAE / ABR System', 'Us', today.isoformat(),
                (today + timedelta(days=250)).isoformat(), '', 'Clinical Room 2',
                'Fictional sample instrument for list and history views.', ts, ts
            )).lastrowid

        previous_date = (today - timedelta(days=10)).isoformat()
        prior_service = con.execute("""INSERT INTO services
            (code,client_id,equipment_id,opened,request_source,reason,complaint,warranty,amc,
             engineer,priority,status,received_date,received_condition,diagnosis,work_done,
             final_result,foc_chargeable,service_charge,parts_charge,quote_status,payment_status,
             amount_received,completion_date,closure_date,notes,modified)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                'SRV-DEMO-0001', client1, equipment1, previous_date, 'Phone',
                'Breakdown / Complaint', 'Intermittent feedback and sound cuts out after 20 minutes.',
                'Yes', 'No', 'Arun Kumar [DEMO]', 'Normal', 'Closed', previous_date,
                'Unit received with power cable; casing clean.',
                'Loose output connector found during inspection.',
                'Connector reseated and output checked on both channels.', 'Successful',
                'Chargeable', 1200, 0, 'Approved', 'Paid', 1200,
                (today - timedelta(days=8)).isoformat(), (today - timedelta(days=8)).isoformat(),
                'DEMO NOTE: Customer confirmed feedback stopped after connector repair. Follow up after next calibration.', ts
            )).lastrowid
        active_service = con.execute("""INSERT INTO services
            (code,client_id,equipment_id,opened,request_source,reason,complaint,warranty,amc,
             engineer,priority,status,diagnosis,work_done,final_result,foc_chargeable,
             payment_status,notes,modified)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                'SRV-DEMO-0002', client2, equipment2, (today - timedelta(days=1)).isoformat(),
                'Email', 'Calibration', 'Annual calibration and performance verification requested.',
                'Yes', 'No', 'Arun Kumar [DEMO]', 'High', 'Under Diagnosis',
                'Initial response check in progress.', '', 'Pending', 'Chargeable',
                'Not Applicable', 'DEMO NOTE: Keep the calibration certificate with the final service report.', ts
            )).lastrowid

        for offset, note in (
            (10, 'DEMO: Service request received; unit booked in with accessories.'),
            (9, 'DEMO: Initial inspection found intermittent output feedback.'),
            (8, 'DEMO: Connector reseated, both channels verified, customer updated and job closed.'),
        ):
            con.execute('INSERT INTO history(service_id,event_date,note,user) VALUES(?,?,?,?)', (
                prior_service, (today - timedelta(days=offset)).isoformat() + ' 10:00', note, 'demo.admin'
            ))
        con.execute("""INSERT INTO service_updates
            (service_id,update_date,engineer,update_type,diagnosis,work_done,result,next_action,user)
            VALUES(?,?,?,?,?,?,?,?,?)""", (
                prior_service, (today - timedelta(days=9)).isoformat() + ' 11:20',
                'Arun Kumar [DEMO]', 'Technical', 'Feedback reproduced on left channel.',
                'Inspected output connector and cable seating.', 'Pending',
                'Reseat connector and repeat channel test.', 'demo.admin'
            ))
        con.execute("""INSERT INTO service_updates
            (service_id,update_date,engineer,update_type,diagnosis,work_done,result,next_action,user)
            VALUES(?,?,?,?,?,?,?,?,?)""", (
                prior_service, (today - timedelta(days=8)).isoformat() + ' 15:40',
                'Arun Kumar [DEMO]', 'Engineer Update', 'Connector was loose.',
                'Reseated connector; verified both channels for 30 minutes.', 'Successful',
                'Customer to monitor through next calibration cycle.', 'demo.admin'
            ))
        con.execute('''INSERT INTO history(service_id,event_date,note,user) VALUES(?,?,?,?)''', (
            active_service, ts, 'DEMO: Calibration request opened; certificate review is pending.', 'demo.admin'
        ))
        _expand_demo_data(con, today, ts)
        con.execute("""INSERT INTO settings(key,value) VALUES('demo_seeded','2')
                     ON CONFLICT(key) DO UPDATE SET value='2'""")
        con.execute("""INSERT INTO settings(key,value) VALUES('auto_backup_enabled','0')
                     ON CONFLICT(key) DO UPDATE SET value='0'""")
        con.execute("""INSERT INTO settings(key,value) VALUES('company_name','SERVIX Demo Workspace')
                     ON CONFLICT(key) DO UPDATE SET value='SERVIX Demo Workspace'""")


def _expand_demo_data(con, today, ts):
    """Add a varied, versioned sample set for dashboard and report previews."""
    clients = list(con.execute("SELECT id,code FROM clients WHERE code LIKE 'CLI-DEMO-%' ORDER BY code"))
    equipment = list(con.execute("SELECT id,client_id,code FROM equipment WHERE code LIKE 'SEQ-DEMO-%' ORDER BY code"))
    engineers = list(con.execute("SELECT name FROM engineers WHERE code LIKE 'ENG-DEMO-%' ORDER BY code"))
    for i, (name, contact) in enumerate((
        ('Harbor Hearing Clinic [DEMO]', 'Leena Shah'),
        ('Cedar Audiology Group [DEMO]', 'Dev Patel'),
        ('Riverside ENT Centre [DEMO]', 'Nina Das'),
        ('Meadow Hearing Studio [DEMO]', 'Omar Khan'),
    ), start=3):
        code = f'CLI-DEMO-{i:03d}'
        con.execute("""INSERT OR IGNORE INTO clients(code,name,contact,mobile,email,address,city,notes,created,modified)
            VALUES(?,?,?,?,?,?,?,?,?,?)""", (code, name, contact, f'90000 10{i:03d}',
            f'demo{i}@servix.local', f'{i} Sample Lane', 'Chennai', 'Fictional SERVIX demo client.', ts, ts))
    clients = list(con.execute("SELECT id,code FROM clients WHERE code LIKE 'CLI-DEMO-%' ORDER BY code"))
    makes = [('MAICO','MA 25'),('Interacoustics','AD226'),('PATH MEDICAL','Sentiero'),('Inventis','Clarinet'),('GSI','P  Audioscreener'),('MAICO','Ero Scan')]
    for i, (make, model) in enumerate(makes, start=3):
        code = f'SEQ-DEMO-{i:03d}'
        client_id = clients[(i-1) % len(clients)]['id']
        con.execute("""INSERT OR IGNORE INTO equipment(code,client_id,make,model,serial,stock_id,equipment_type,
            sold_by,sold_date,warranty_till,amc_till,location,notes,created,modified)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (code, client_id, make, model, f'DEMO-SN-{i:03d}',
            f'DEMO-ASSET-{i:03d}', 'Audiology Diagnostic System', 'Us', today.isoformat(),
            (today + timedelta(days=(i-4)*20)).isoformat(),
            (today + timedelta(days=(i-2)*35)).isoformat(), f'Room {i}',
            'Fictional equipment for preview and workflow testing.', ts, ts))
    con.execute("""INSERT OR IGNORE INTO engineers(code,name,mobile,email,specialization,active,notes,created,modified)
        VALUES(?,?,?,?,?,1,?,?,?)""", ('ENG-DEMO-002','Priya Menon [DEMO]','90000 20002',
        'priya.demo@servix.local','Calibration and diagnostics','Sample engineer account.',ts,ts))
    con.execute("""INSERT OR IGNORE INTO engineers(code,name,mobile,email,specialization,active,notes,created,modified)
        VALUES(?,?,?,?,?,1,?,?,?)""", ('ENG-DEMO-003','Rohan Iyer [DEMO]','90000 20003',
        'rohan.demo@servix.local','Field service and repairs','Sample engineer account.',ts,ts))
    equipment = list(con.execute("SELECT id,client_id,code FROM equipment WHERE code LIKE 'SEQ-DEMO-%' ORDER BY code"))
    engineers = [r['name'] for r in con.execute("SELECT name FROM engineers WHERE code LIKE 'ENG-DEMO-%' ORDER BY code")]
    statuses = ['New','Assigned','Received','Under Diagnosis','Awaiting Parts','Awaiting Customer',
                'Repair in Progress','Testing','Ready for Dispatch','Closed','Dispatched','Cancelled']
    reasons = ['Breakdown / Complaint','Calibration','Preventive Maintenance','Installation / Commissioning']
    for i in range(1, 25):
        code = f'SRV-DEMO-{i+2:04d}'
        if con.execute('SELECT 1 FROM services WHERE code=?',(code,)).fetchone():
            continue
        eq = equipment[(i-1) % len(equipment)]
        status = statuses[(i-1) % len(statuses)]
        reason = reasons[(i-1) % len(reasons)]
        opened = (today - timedelta(days=(i * 3) % 75)).isoformat()
        paid = 'Paid' if status == 'Closed' and i % 2 else ('Pending' if i % 3 == 0 else 'Not Applicable')
        note = f'DEMO NOTE: Sample {reason.lower()} workflow. Review engineer updates, customer follow-up and service history.'
        service_id = con.execute("""INSERT INTO services(code,client_id,equipment_id,opened,request_source,reason,complaint,
            warranty,amc,engineer,priority,status,diagnosis,work_done,final_result,foc_chargeable,service_charge,
            quote_status,payment_status,amount_received,notes,modified)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            code, eq['client_id'], eq['id'], opened, ('Phone','Email','WhatsApp','Walk-in')[i%4], reason,
            f'{reason} reported for demo equipment {eq["code"]}.', 'Yes' if i%4==0 else 'No', 'Yes' if i%5==0 else 'No',
            engineers[i%len(engineers)], ('Normal','High','Urgent')[i%3], status,
            'Initial inspection recorded for demo review.', 'Bench checks and visual inspection logged.' if i%2 else '',
            'Successful' if status=='Closed' else 'Pending', 'FOC' if i%4==0 else 'Chargeable',
            850 + i*75, 'Approved' if i%3==0 else 'Pending Decision', paid,
            850 + i*75 if paid=='Paid' else 0, note, opened + ' 12:00')).lastrowid
        con.execute('INSERT INTO history(service_id,event_date,note,user) VALUES(?,?,?,?)',
            (service_id, opened+' 09:15', f'DEMO: {reason} request received and logged.', 'demo.admin'))
        con.execute('INSERT INTO history(service_id,event_date,note,user) VALUES(?,?,?,?)',
            (service_id, opened+' 12:00', f'DEMO: Status updated to {status}; next action documented.', 'demo.admin'))
