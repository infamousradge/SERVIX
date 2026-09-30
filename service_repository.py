from database import connect, now

def add_history(service_id: int, note: str, user: str = "Office"):
    with connect() as con:
        con.execute(
            "INSERT INTO history(service_id,event_date,note,user) VALUES(?,?,?,?)",
            (service_id, now(), note.strip(), user),
        )

def add_part(service_id: int, part_no: str, description: str, qty: float, chargeable: str, amount: float, remarks: str = ""):
    with connect() as con:
        con.execute(
            """INSERT INTO parts(service_id,part_no,description,qty,chargeable,amount,remarks)
               VALUES(?,?,?,?,?,?,?)""",
            (service_id, part_no.strip(), description.strip(), qty, chargeable, amount, remarks.strip()),
        )
        con.execute("UPDATE services SET modified=? WHERE id=?", (now(), service_id))

def upsert_calibration(service_id: int, received_date: str, calibration_date: str, result: str, certificate_no: str, certificate_date: str, next_due: str, performed_by: str, standards_reference: str, remarks: str):
    with connect() as con:
        con.execute(
            """INSERT INTO calibration(service_id,received_date,calibration_date,result,certificate_no,certificate_date,next_due,performed_by,standards_reference,remarks)
               VALUES(?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(service_id) DO UPDATE SET
                 received_date=excluded.received_date,
                 calibration_date=excluded.calibration_date,
                 result=excluded.result,
                 certificate_no=excluded.certificate_no,
                 certificate_date=excluded.certificate_date,
                 next_due=excluded.next_due,
                 performed_by=excluded.performed_by,
                 standards_reference=excluded.standards_reference,
                 remarks=excluded.remarks""",
            (service_id, received_date, calibration_date, result, certificate_no.strip(), certificate_date, next_due, performed_by.strip(), standards_reference.strip(), remarks.strip()),
        )
        con.execute("UPDATE services SET modified=? WHERE id=?", (now(), service_id))

def add_attachment(service_id: int, meta: dict):
    with connect() as con:
        con.execute(
            """INSERT INTO attachments(service_id,original_name,stored_path,kind,original_size,stored_size,created)
               VALUES(?,?,?,?,?,?,?)""",
            (service_id, meta["original_name"], meta["stored_path"], meta["kind"],
             meta["original_size"], meta["stored_size"], now()),
        )
        con.execute("UPDATE services SET modified=? WHERE id=?", (now(), service_id))
