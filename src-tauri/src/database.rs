use chrono::Local;
use rusqlite::{params, Connection};

pub fn initialise(conn: &mut Connection) -> Result<(), String> {
    conn.pragma_update(None, "foreign_keys", "ON").map_err(db_err)?;
    conn.execute_batch(
        r#"
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL,
            role TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS clients(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            contact TEXT NOT NULL DEFAULT '',
            mobile TEXT NOT NULL DEFAULT '',
            email TEXT NOT NULL DEFAULT '',
            city TEXT NOT NULL DEFAULT '',
            state TEXT NOT NULL DEFAULT '',
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_clients_mobile ON clients(mobile);
        CREATE INDEX IF NOT EXISTS idx_clients_email ON clients(email);

        CREATE TABLE IF NOT EXISTS equipment(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            servix_equipment_id TEXT NOT NULL UNIQUE,
            client_id INTEGER,
            make TEXT NOT NULL DEFAULT '',
            model TEXT NOT NULL DEFAULT '',
            serial_number TEXT NOT NULL DEFAULT '',
            equipment_type TEXT NOT NULL DEFAULT '',
            location TEXT NOT NULL DEFAULT '',
            coverage TEXT NOT NULL DEFAULT 'Out of Coverage',
            warranty_until TEXT NOT NULL DEFAULT '',
            amc_until TEXT NOT NULL DEFAULT '',
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(client_id) REFERENCES clients(id)
        );
        CREATE INDEX IF NOT EXISTS idx_equipment_serial ON equipment(serial_number);

        CREATE TABLE IF NOT EXISTS engineers(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            contact TEXT NOT NULL DEFAULT '',
            active INTEGER NOT NULL DEFAULT 1,
            skills TEXT NOT NULL DEFAULT '',
            coverage_area TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS service_calls(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_id TEXT NOT NULL UNIQUE,
            opened_date TEXT NOT NULL,
            client_id INTEGER,
            equipment_id INTEGER,
            client_name TEXT NOT NULL,
            equipment_name TEXT NOT NULL,
            make TEXT NOT NULL DEFAULT '',
            model TEXT NOT NULL DEFAULT '',
            serial_number TEXT NOT NULL DEFAULT '',
            reason TEXT NOT NULL,
            complaint TEXT NOT NULL,
            engineer TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL,
            priority TEXT NOT NULL DEFAULT 'Normal',
            service_location TEXT NOT NULL DEFAULT '',
            due_date TEXT NOT NULL DEFAULT '',
            coverage TEXT NOT NULL DEFAULT 'Out of Coverage',
            foc INTEGER NOT NULL DEFAULT 0,
            quote_status TEXT NOT NULL DEFAULT 'No Quote',
            payment_status TEXT NOT NULL DEFAULT 'Pending',
            created_by INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(client_id) REFERENCES clients(id),
            FOREIGN KEY(equipment_id) REFERENCES equipment(id),
            FOREIGN KEY(created_by) REFERENCES users(id)
        );
        CREATE INDEX IF NOT EXISTS idx_service_status ON service_calls(status);
        CREATE INDEX IF NOT EXISTS idx_service_opened ON service_calls(opened_date);

        CREATE TABLE IF NOT EXISTS service_events(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_call_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            old_value TEXT NOT NULL DEFAULT '',
            new_value TEXT NOT NULL DEFAULT '',
            note TEXT NOT NULL DEFAULT '',
            actor_id INTEGER,
            created_at TEXT NOT NULL,
            FOREIGN KEY(service_call_id) REFERENCES service_calls(id),
            FOREIGN KEY(actor_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS part_usage(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_call_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            make TEXT NOT NULL DEFAULT '',
            model TEXT NOT NULL DEFAULT '',
            part_number TEXT NOT NULL DEFAULT '',
            quantity INTEGER NOT NULL DEFAULT 1,
            remarks TEXT NOT NULL DEFAULT '',
            used_at TEXT NOT NULL,
            FOREIGN KEY(service_call_id) REFERENCES service_calls(id)
        );

        CREATE TABLE IF NOT EXISTS attachments(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_type TEXT NOT NULL,
            parent_id INTEGER NOT NULL,
            document_type TEXT NOT NULL,
            stored_path TEXT NOT NULL,
            original_name TEXT NOT NULL,
            mime_type TEXT NOT NULL,
            size_bytes INTEGER NOT NULL DEFAULT 0,
            caption TEXT NOT NULL DEFAULT '',
            created_by INTEGER,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS form_intake(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            external_id TEXT NOT NULL UNIQUE,
            received_at TEXT NOT NULL,
            client_name TEXT NOT NULL DEFAULT '',
            contact TEXT NOT NULL DEFAULT '',
            mobile TEXT NOT NULL DEFAULT '',
            email TEXT NOT NULL DEFAULT '',
            equipment TEXT NOT NULL DEFAULT '',
            make TEXT NOT NULL DEFAULT '',
            model TEXT NOT NULL DEFAULT '',
            serial_number TEXT NOT NULL DEFAULT '',
            complaint TEXT NOT NULL DEFAULT '',
            raw_json TEXT NOT NULL DEFAULT '{}',
            match_summary TEXT NOT NULL DEFAULT '',
            match_tone TEXT NOT NULL DEFAULT 'neutral',
            status TEXT NOT NULL DEFAULT 'New',
            linked_service_id TEXT,
            processed_by INTEGER,
            processed_at TEXT
        );

        CREATE TABLE IF NOT EXISTS sync_log(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            success INTEGER NOT NULL DEFAULT 0,
            fetched_count INTEGER NOT NULL DEFAULT 0,
            new_count INTEGER NOT NULL DEFAULT 0,
            error_message TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS settings(
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS audit_log(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity TEXT NOT NULL,
            action TEXT NOT NULL,
            record_id TEXT NOT NULL DEFAULT '',
            actor_id INTEGER,
            summary TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        );
        "#,
    )
    .map_err(db_err)?;

    let now = Local::now().format("%Y-%m-%d %H:%M:%S").to_string();
    for (key, value) in [
        ("service_prefix", "SRV-"),
        ("service_next_number", "10001"),
        ("service_digits", "5"),
        ("client_prefix", "CLI-"),
        ("client_next_number", "1001"),
        ("client_digits", "5"),
        ("equipment_prefix", "EQ-"),
        ("equipment_next_number", "10001"),
        ("equipment_digits", "5"),
        ("google_form_configured", "false"),
        ("google_sheet_id", "1dXiMB7ls1vAzFL3PHYTOMQDnI-JUtVltVGVuGhu4IJo"),
        ("google_sheet_name", "Form Responses 1"),
        ("google_service_account_json", ""),
        ("google_map_timestamp", "Timestamp"),
        ("google_map_client", "Organisation / Client Name"),
        ("google_map_contact", "Contact Person Name"),
        ("google_map_mobile", "Mobile Number"),
        ("google_map_email", "Email"),
        ("google_map_equipment", "Equipment / Device"),
        ("google_map_make", "Make"),
        ("google_map_model", "Model"),
        ("google_map_serial", "Serial Number"),
        ("google_map_reason", "Reason for Sending"),
        ("google_map_complaint", "Problem / Complaint"),
    ] {
        conn.execute(
            "INSERT OR IGNORE INTO settings(key,value,updated_at) VALUES(?1,?2,?3)",
            params![key, value, now],
        )
        .map_err(db_err)?;
    }

    #[cfg(debug_assertions)]
    seed_preview(conn)?;
    Ok(())
}

fn seed_preview(conn: &Connection) -> Result<(), String> {
    let count: i64 = conn
        .query_row("SELECT COUNT(*) FROM clients", [], |r| r.get(0))
        .map_err(db_err)?;
    if count > 0 {
        return Ok(());
    }
    let now = Local::now().format("%Y-%m-%d %H:%M:%S").to_string();
    conn.execute(
        "INSERT INTO clients(code,name,contact,mobile,email,city,state,created_at,updated_at) VALUES('CLI-01000','City Hospital','Mr. Sharma','9876543210','service@cityhospital.in','New Delhi','Delhi',?1,?1)",
        params![now],
    )
    .map_err(db_err)?;
    let client_id = conn.last_insert_rowid();
    conn.execute(
        "INSERT INTO equipment(servix_equipment_id,client_id,make,model,serial_number,equipment_type,location,coverage,created_at,updated_at) VALUES('EQ-10000',?1,'MAICO','MA42','123456','Audiometer','Audiology Dept.','Out of Coverage',?2,?2)",
        params![client_id, now],
    )
    .map_err(db_err)?;
    let equipment_id = conn.last_insert_rowid();
    conn.execute(
        "INSERT INTO service_calls(service_id,opened_date,client_id,equipment_id,client_name,equipment_name,make,model,serial_number,reason,complaint,engineer,status,priority,service_location,due_date,coverage,foc,quote_status,payment_status,created_at,updated_at) VALUES('SRV-10000','2026-10-05',?1,?2,'City Hospital','Audiometer','MAICO','MA42','123456','Repair','No sound from right ear channel.','Rohit','In Progress','Normal','Onsite','2026-10-10','Out of Coverage',0,'Quote Sent','Pending',?3,?3)",
        params![client_id, equipment_id, now],
    )
    .map_err(db_err)?;
    Ok(())
}

pub fn db_err(e: rusqlite::Error) -> String {
    format!("Database error: {e}")
}
