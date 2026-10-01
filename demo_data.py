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
        if seeded and seeded['value'] == '1':
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
        con.execute("""INSERT INTO settings(key,value) VALUES('demo_seeded','1')
                     ON CONFLICT(key) DO UPDATE SET value='1'""")
        con.execute("""INSERT INTO settings(key,value) VALUES('auto_backup_enabled','0')
                     ON CONFLICT(key) DO UPDATE SET value='0'""")
        con.execute("""INSERT INTO settings(key,value) VALUES('company_name','SERVIX Demo Workspace')
                     ON CONFLICT(key) DO UPDATE SET value='SERVIX Demo Workspace'""")

