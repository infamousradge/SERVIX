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

def upsert_calibration(service_id: int, calibration_date: str, result: str, certificate_no: str, next_due: str, remarks: str):
    with connect() as con:
        con.execute(
            """INSERT INTO calibration(service_id,calibration_date,result,certificate_no,next_due,remarks)
               VALUES(?,?,?,?,?,?)
               ON CONFLICT(service_id) DO UPDATE SET
                 calibration_date=excluded.calibration_date,
                 result=excluded.result,
                 certificate_no=excluded.certificate_no,
                 next_due=excluded.next_due,
                 remarks=excluded.remarks""",
            (service_id, calibration_date, result, certificate_no.strip(), next_due, remarks.strip()),
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
