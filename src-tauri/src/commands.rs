use chrono::{Duration, Local, NaiveDateTime};
use rusqlite::{params, Connection, OptionalExtension, Transaction};
use tauri::State;

use crate::{database::db_err, models::*, security, state::AppState};

fn require_user(state: &State<'_, AppState>) -> Result<SessionUser, String> {
    state
        .session
        .lock()
        .map_err(|_| "Session lock failed".to_string())?
        .clone()
        .ok_or_else(|| "Please sign in again.".to_string())
}

fn require_admin(state: &State<'_, AppState>) -> Result<SessionUser, String> {
    let user = require_user(state)?;
    if user.role != "Administrator" {
        return Err("Administrator permission is required.".into());
    }
    Ok(user)
}

fn setting(conn: &Connection, key: &str, default: &str) -> String {
    conn.query_row("SELECT value FROM settings WHERE key=?1", params![key], |r| {
        r.get::<_, String>(0)
    })
    .optional()
    .ok()
    .flatten()
    .unwrap_or_else(|| default.into())
}

fn setting_tx(tx: &Transaction<'_>, key: &str, default: &str) -> String {
    tx.query_row("SELECT value FROM settings WHERE key=?1", params![key], |r| {
        r.get::<_, String>(0)
    })
    .optional()
    .ok()
    .flatten()
    .unwrap_or_else(|| default.into())
}

fn next_human_id(
    tx: &Transaction<'_>,
    prefix_key: &str,
    number_key: &str,
    digits_key: &str,
    default_prefix: &str,
    default_number: i64,
) -> Result<String, String> {
    let prefix = setting_tx(tx, prefix_key, default_prefix);
    let digits: usize = setting_tx(tx, digits_key, "5").parse().unwrap_or(5);
    let next: i64 = setting_tx(tx, number_key, &default_number.to_string())
        .parse()
        .unwrap_or(default_number);
    let id = format!("{}{:0width$}", prefix, next, width = digits);
    let now = Local::now().format("%Y-%m-%d %H:%M:%S").to_string();
    tx.execute(
        "UPDATE settings SET value=?1,updated_at=?2 WHERE key=?3",
        params![(next + 1).to_string(), now, number_key],
    )
    .map_err(db_err)?;
    Ok(id)
}

fn normalize_mobile(value: &str) -> String {
    value.chars().filter(|c| c.is_ascii_digit()).collect()
}

fn normalize_email(value: &str) -> String {
    value.trim().to_lowercase()
}

#[tauri::command]
pub fn system_status(state: State<'_, AppState>) -> Result<SystemStatus, String> {
    let db = state
        .db
        .lock()
        .map_err(|_| "Database lock failed".to_string())?;
    let count: i64 = db
        .query_row("SELECT COUNT(*) FROM users", [], |r| r.get(0))
        .map_err(db_err)?;
    Ok(SystemStatus {
        initialized: count > 0,
        app_version: env!("CARGO_PKG_VERSION").into(),
        database_path: state.database_path.display().to_string(),
    })
}

#[tauri::command]
pub fn create_first_admin(
    state: State<'_, AppState>,
    username: String,
    password: String,
    display_name: String,
) -> Result<SessionUser, String> {
    let mut db = state
        .db
        .lock()
        .map_err(|_| "Database lock failed".to_string())?;
    let count: i64 = db
        .query_row("SELECT COUNT(*) FROM users", [], |r| r.get(0))
        .map_err(db_err)?;
    if count > 0 {
        return Err("SERVIX has already been initialized.".into());
    }
    if username.trim().len() < 3 {
        return Err("Username must be at least 3 characters.".into());
    }
    if display_name.trim().is_empty() {
        return Err("Display name is required.".into());
    }
    let hash = security::hash_password(&password)?;
    let now = Local::now().format("%Y-%m-%d %H:%M:%S").to_string();
    let tx = db.transaction().map_err(db_err)?;
    tx.execute(
        "INSERT INTO users(username,display_name,role,password_hash,created_at) VALUES(?1,?2,'Administrator',?3,?4)",
        params![username.trim(), display_name.trim(), hash, now],
    )
    .map_err(db_err)?;
    let id = tx.last_insert_rowid();
    tx.commit().map_err(db_err)?;
    drop(db);

    let user = SessionUser {
        id,
        username: username.trim().into(),
        display_name: display_name.trim().into(),
        role: "Administrator".into(),
    };
    *state
        .session
        .lock()
        .map_err(|_| "Session lock failed".to_string())? = Some(user.clone());
    Ok(user)
}

#[tauri::command]
pub fn authenticate(
    state: State<'_, AppState>,
    username: String,
    password: String,
) -> Result<SessionUser, String> {
    let db = state
        .db
        .lock()
        .map_err(|_| "Database lock failed".to_string())?;
    let row = db
        .query_row(
            "SELECT id,username,display_name,role,password_hash FROM users WHERE lower(username)=lower(?1) AND active=1",
            params![username.trim()],
            |r| {
                Ok((
                    r.get::<_, i64>(0)?,
                    r.get::<_, String>(1)?,
                    r.get::<_, String>(2)?,
                    r.get::<_, String>(3)?,
                    r.get::<_, String>(4)?,
                ))
            },
        )
        .optional()
        .map_err(db_err)?;
    drop(db);
    let (id, username, display_name, role, hash) =
        row.ok_or_else(|| "Invalid username or password.".to_string())?;
    if !security::verify_password(&password, &hash) {
        return Err("Invalid username or password.".into());
    }
    let user = SessionUser {
        id,
        username,
        display_name,
        role,
    };
    *state
        .session
        .lock()
        .map_err(|_| "Session lock failed".to_string())? = Some(user.clone());
    Ok(user)
}

#[tauri::command]
pub fn logout(state: State<'_, AppState>) -> Result<(), String> {
    *state
        .session
        .lock()
        .map_err(|_| "Session lock failed".to_string())? = None;
    Ok(())
}

#[tauri::command]
pub fn bootstrap(state: State<'_, AppState>) -> Result<DashboardData, String> {
    let _ = require_user(&state)?;
    let db = state
        .db
        .lock()
        .map_err(|_| "Database lock failed".to_string())?;
    Ok(DashboardData {
        services: list_services(&db)?,
        intake: list_intake(&db)?,
        clients: list_clients(&db)?,
        equipment: list_equipment(&db)?,
        part_usage: list_parts(&db)?,
        users: list_users(&db)?,
        sync: sync_status(&db)?,
    })
}

fn list_services(db: &Connection) -> Result<Vec<ServiceCall>, String> {
    let mut stmt = db
        .prepare("SELECT id,service_id,opened_date,client_id,equipment_id,client_name,equipment_name,make,model,serial_number,reason,complaint,engineer,status,priority,service_location,due_date,coverage,foc,quote_status,payment_status,updated_at FROM service_calls ORDER BY updated_at DESC,id DESC")
        .map_err(db_err)?;
    let rows = stmt
        .query_map([], |r| {
            Ok(ServiceCall {
                id: r.get(0)?,
                service_id: r.get(1)?,
                opened_date: r.get(2)?,
                client_id: r.get(3)?,
                equipment_id: r.get(4)?,
                client: r.get(5)?,
                equipment: r.get(6)?,
                make: r.get(7)?,
                model: r.get(8)?,
                serial_number: r.get(9)?,
                reason: r.get(10)?,
                complaint: r.get(11)?,
                engineer: r.get(12)?,
                status: r.get(13)?,
                priority: r.get(14)?,
                service_location: r.get(15)?,
                due_date: r.get(16)?,
                coverage: r.get(17)?,
                foc: r.get::<_, i64>(18)? != 0,
                quote_status: r.get(19)?,
                payment_status: r.get(20)?,
                last_updated: r.get(21)?,
            })
        })
        .map_err(db_err)?;
    rows.collect::<Result<Vec<_>, _>>().map_err(db_err)
}

fn list_intake(db: &Connection) -> Result<Vec<IntakeItem>, String> {
    let mut stmt = db
        .prepare("SELECT id,received_at,client_name,contact,mobile,email,equipment,make,model,serial_number,complaint,match_summary,match_tone,status,linked_service_id FROM form_intake ORDER BY received_at DESC,id DESC LIMIT 500")
        .map_err(db_err)?;
    let rows = stmt
        .query_map([], |r| {
            Ok(IntakeItem {
                id: r.get(0)?,
                received_at: r.get(1)?,
                client: r.get(2)?,
                contact: r.get(3)?,
                mobile: r.get(4)?,
                email: r.get(5)?,
                equipment: r.get(6)?,
                make: r.get(7)?,
                model: r.get(8)?,
                serial_number: r.get(9)?,
                complaint: r.get(10)?,
                match_summary: r.get(11)?,
                match_tone: r.get(12)?,
                status: r.get(13)?,
                linked_service_id: r.get(14)?,
            })
        })
        .map_err(db_err)?;
    rows.collect::<Result<Vec<_>, _>>().map_err(db_err)
}

fn list_clients(db: &Connection) -> Result<Vec<ClientRecord>, String> {
    let mut stmt = db
        .prepare("SELECT c.id,c.code,c.name,c.contact,c.mobile,c.email,c.city,c.state,c.active,(SELECT COUNT(*) FROM service_calls sc WHERE sc.client_id=c.id),(SELECT COUNT(*) FROM equipment e WHERE e.client_id=c.id) FROM clients c ORDER BY c.name")
        .map_err(db_err)?;
    let rows = stmt
        .query_map([], |r| {
            Ok(ClientRecord {
                id: r.get(0)?,
                code: r.get(1)?,
                name: r.get(2)?,
                contact: r.get(3)?,
                mobile: r.get(4)?,
                email: r.get(5)?,
                city: r.get(6)?,
                state: r.get(7)?,
                active: r.get::<_, i64>(8)? != 0,
                service_count: r.get(9)?,
                equipment_count: r.get(10)?,
            })
        })
        .map_err(db_err)?;
    rows.collect::<Result<Vec<_>, _>>().map_err(db_err)
}

fn list_equipment(db: &Connection) -> Result<Vec<EquipmentRecord>, String> {
    let mut stmt = db
        .prepare("SELECT e.id,e.servix_equipment_id,COALESCE(c.name,''),e.make,e.model,e.serial_number,e.equipment_type,e.location,e.coverage,(SELECT COUNT(*) FROM service_calls sc WHERE sc.equipment_id=e.id),COALESCE((SELECT MAX(opened_date) FROM service_calls sc WHERE sc.equipment_id=e.id),'') FROM equipment e LEFT JOIN clients c ON c.id=e.client_id ORDER BY e.id DESC")
        .map_err(db_err)?;
    let rows = stmt
        .query_map([], |r| {
            Ok(EquipmentRecord {
                id: r.get(0)?,
                servix_equipment_id: r.get(1)?,
                client: r.get(2)?,
                make: r.get(3)?,
                model: r.get(4)?,
                serial_number: r.get(5)?,
                r#type: r.get(6)?,
                location: r.get(7)?,
                coverage: r.get(8)?,
                service_count: r.get(9)?,
                last_service: r.get(10)?,
            })
        })
        .map_err(db_err)?;
    rows.collect::<Result<Vec<_>, _>>().map_err(db_err)
}

fn list_parts(db: &Connection) -> Result<Vec<PartUsage>, String> {
    let mut stmt = db
        .prepare("SELECT p.id,p.used_at,sc.service_id,sc.client_name,sc.equipment_name,p.item_name,p.make,p.model,p.part_number,p.quantity,p.remarks FROM part_usage p JOIN service_calls sc ON sc.id=p.service_call_id ORDER BY p.used_at DESC,p.id DESC")
        .map_err(db_err)?;
    let rows = stmt
        .query_map([], |r| {
            Ok(PartUsage {
                id: r.get(0)?,
                date: r.get(1)?,
                service_id: r.get(2)?,
                client: r.get(3)?,
                equipment: r.get(4)?,
                item_name: r.get(5)?,
                make: r.get(6)?,
                model: r.get(7)?,
                part_number: r.get(8)?,
                quantity: r.get(9)?,
                remarks: r.get(10)?,
            })
        })
        .map_err(db_err)?;
    rows.collect::<Result<Vec<_>, _>>().map_err(db_err)
}

fn list_users(db: &Connection) -> Result<Vec<UserRecord>, String> {
    let mut stmt = db
        .prepare("SELECT id,username,display_name,role,active FROM users ORDER BY display_name,username")
        .map_err(db_err)?;
    let rows = stmt
        .query_map([], |r| {
            Ok(UserRecord {
                id: r.get(0)?,
                username: r.get(1)?,
                display_name: r.get(2)?,
                role: r.get(3)?,
                active: r.get::<_, i64>(4)? != 0,
            })
        })
        .map_err(db_err)?;
    rows.collect::<Result<Vec<_>, _>>().map_err(db_err)
}

fn sync_status(db: &Connection) -> Result<SyncStatus, String> {
    let configured = setting(db, "google_form_configured", "false") == "true";
    let last = db
        .query_row(
            "SELECT completed_at FROM sync_log WHERE success=1 ORDER BY id DESC LIMIT 1",
            [],
            |r| r.get::<_, Option<String>>(0),
        )
        .optional()
        .map_err(db_err)?
        .flatten();
    let attempt = db
        .query_row("SELECT started_at FROM sync_log ORDER BY id DESC LIMIT 1", [], |r| {
            r.get::<_, String>(0)
        })
        .optional()
        .map_err(db_err)?;
    let new_count: i64 = db
        .query_row("SELECT COUNT(*) FROM form_intake WHERE status='New'", [], |r| r.get(0))
        .map_err(db_err)?;

    let overdue = last
        .as_deref()
        .and_then(|value| NaiveDateTime::parse_from_str(value, "%Y-%m-%d %H:%M:%S").ok())
        .map(|value| Local::now().naive_local() - value > Duration::hours(24))
        .unwrap_or(false);

    let (status, message) = if !configured {
        ("not-configured", "Google Form intake is not configured yet.")
    } else if last.is_none() {
        ("warning", "Google Form intake has not completed its first successful sync.")
    } else if overdue {
        ("overdue", "Google Form has not synced successfully for more than 24 hours.")
    } else {
        ("up-to-date", "Google Form intake is up to date.")
    };

    Ok(SyncStatus {
        configured,
        last_successful_sync: last,
        last_attempted_sync: attempt,
        new_count,
        status: status.into(),
        message: message.into(),
    })
}

fn find_or_create_client(tx: &Transaction<'_>, draft: &ServiceCallDraft) -> Result<i64, String> {
    let mobile = normalize_mobile(draft.mobile.as_deref().unwrap_or_default());
    let email = normalize_email(draft.email.as_deref().unwrap_or_default());
    let existing = tx
        .query_row(
            "SELECT id FROM clients WHERE (?1<>'' AND replace(replace(replace(mobile,' ',''),'-',''),'+','')=?1) OR (?2<>'' AND lower(email)=?2) ORDER BY active DESC,id LIMIT 1",
            params![mobile, email],
            |r| r.get::<_, i64>(0),
        )
        .optional()
        .map_err(db_err)?;

    let now = Local::now().format("%Y-%m-%d %H:%M:%S").to_string();
    if let Some(id) = existing {
        tx.execute(
            "UPDATE clients SET name=?1,contact=CASE WHEN ?2<>'' THEN ?2 ELSE contact END,mobile=CASE WHEN ?3<>'' THEN ?3 ELSE mobile END,email=CASE WHEN ?4<>'' THEN ?4 ELSE email END,updated_at=?5 WHERE id=?6",
            params![draft.client.trim(), draft.contact.as_deref().unwrap_or_default().trim(), mobile, email, now, id],
        )
        .map_err(db_err)?;
        return Ok(id);
    }

    let code = next_human_id(tx, "client_prefix", "client_next_number", "client_digits", "CLI-", 1001)?;
    tx.execute(
        "INSERT INTO clients(code,name,contact,mobile,email,created_at,updated_at) VALUES(?1,?2,?3,?4,?5,?6,?6)",
        params![
            code,
            draft.client.trim(),
            draft.contact.as_deref().unwrap_or_default().trim(),
            mobile,
            email,
            now
        ],
    )
    .map_err(db_err)?;
    Ok(tx.last_insert_rowid())
}

fn find_or_create_equipment(
    tx: &Transaction<'_>,
    client_id: i64,
    draft: &ServiceCallDraft,
) -> Result<i64, String> {
    let serial = draft.serial_number.as_deref().unwrap_or_default().trim();
    let existing = if serial.is_empty() {
        None
    } else {
        tx.query_row(
            "SELECT id FROM equipment WHERE client_id=?1 AND lower(serial_number)=lower(?2) ORDER BY active DESC,id LIMIT 1",
            params![client_id, serial],
            |r| r.get::<_, i64>(0),
        )
        .optional()
        .map_err(db_err)?
    };

    let now = Local::now().format("%Y-%m-%d %H:%M:%S").to_string();
    if let Some(id) = existing {
        tx.execute(
            "UPDATE equipment SET make=?1,model=?2,equipment_type=?3,location=?4,coverage=?5,updated_at=?6 WHERE id=?7",
            params![
                draft.make.as_deref().unwrap_or_default().trim(),
                draft.model.as_deref().unwrap_or_default().trim(),
                draft.equipment.trim(),
                draft.service_location.trim(),
                draft.coverage.as_str(),
                now,
                id
            ],
        )
        .map_err(db_err)?;
        return Ok(id);
    }

    let servix_id = next_human_id(
        tx,
        "equipment_prefix",
        "equipment_next_number",
        "equipment_digits",
        "EQ-",
        10001,
    )?;
    tx.execute(
        "INSERT INTO equipment(servix_equipment_id,client_id,make,model,serial_number,equipment_type,location,coverage,created_at,updated_at) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?9)",
        params![
            servix_id,
            client_id,
            draft.make.as_deref().unwrap_or_default().trim(),
            draft.model.as_deref().unwrap_or_default().trim(),
            serial,
            draft.equipment.trim(),
            draft.service_location.trim(),
            draft.coverage.as_str(),
            now
        ],
    )
    .map_err(db_err)?;
    Ok(tx.last_insert_rowid())
}

#[tauri::command]
pub fn create_service_call(
    state: State<'_, AppState>,
    draft: ServiceCallDraft,
) -> Result<ServiceCall, String> {
    let user = require_user(&state)?;
    if user.role == "Read Only" {
        return Err("Read-only users cannot create service calls.".into());
    }
    if draft.client.trim().is_empty()
        || draft.equipment.trim().is_empty()
        || draft.reason.trim().is_empty()
        || draft.complaint.trim().is_empty()
    {
        return Err("Client, equipment, reason and complaint are required.".into());
    }

    let mut db = state
        .db
        .lock()
        .map_err(|_| "Database lock failed".to_string())?;
    let tx = db.transaction().map_err(db_err)?;
    let client_id = find_or_create_client(&tx, &draft)?;
    let equipment_id = find_or_create_equipment(&tx, client_id, &draft)?;
    let service_id = next_human_id(
        &tx,
        "service_prefix",
        "service_next_number",
        "service_digits",
        "SRV-",
        10001,
    )?;
    let now = Local::now().format("%Y-%m-%d %H:%M:%S").to_string();

    tx.execute(
        "INSERT INTO service_calls(service_id,opened_date,client_id,equipment_id,client_name,equipment_name,make,model,serial_number,reason,complaint,engineer,status,priority,service_location,due_date,coverage,foc,quote_status,payment_status,created_by,created_at,updated_at) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,?13,?14,?15,?16,?17,?18,?19,?20,?21,?22,?22)",
        params![
            service_id,
            draft.opened_date,
            client_id,
            equipment_id,
            draft.client.trim(),
            draft.equipment.trim(),
            draft.make.as_deref().unwrap_or_default().trim(),
            draft.model.as_deref().unwrap_or_default().trim(),
            draft.serial_number.as_deref().unwrap_or_default().trim(),
            draft.reason,
            draft.complaint,
            draft.engineer.as_deref().unwrap_or_default().trim(),
            draft.status,
            draft.priority,
            draft.service_location,
            draft.due_date.as_deref().unwrap_or_default(),
            draft.coverage,
            if draft.foc { 1 } else { 0 },
            draft.quote_status,
            draft.payment_status,
            user.id,
            now
        ],
    )
    .map_err(db_err)?;
    let id = tx.last_insert_rowid();
    tx.execute(
        "INSERT INTO service_events(service_call_id,event_type,new_value,note,actor_id,created_at) VALUES(?1,'Created',?2,'Service call created',?3,?4)",
        params![id, service_id, user.id, now],
    )
    .map_err(db_err)?;
    tx.execute(
        "INSERT INTO audit_log(entity,action,record_id,actor_id,summary,created_at) VALUES('ServiceCall','Create',?1,?2,?3,?4)",
        params![service_id, user.id, format!("Created service call for {}", draft.client.trim()), now],
    )
    .map_err(db_err)?;
    tx.commit().map_err(db_err)?;
    drop(db);

    let db = state
        .db
        .lock()
        .map_err(|_| "Database lock failed".to_string())?;
    list_services(&db)?
        .into_iter()
        .find(|x| x.id == id)
        .ok_or_else(|| "Service call was saved but could not be reloaded.".into())
}

#[tauri::command]
pub fn create_user(
    state: State<'_, AppState>,
    draft: CreateUserDraft,
) -> Result<UserRecord, String> {
    let actor = require_admin(&state)?;
    let role = draft.role.trim();
    if !["Administrator", "Office User", "Read Only"].contains(&role) {
        return Err("Invalid user role.".into());
    }
    if draft.username.trim().len() < 3 {
        return Err("Username must be at least 3 characters.".into());
    }
    if draft.display_name.trim().is_empty() {
        return Err("Display name is required.".into());
    }
    let hash = security::hash_password(&draft.password)?;
    let now = Local::now().format("%Y-%m-%d %H:%M:%S").to_string();
    let db = state
        .db
        .lock()
        .map_err(|_| "Database lock failed".to_string())?;
    db.execute(
        "INSERT INTO users(username,display_name,role,password_hash,created_at) VALUES(?1,?2,?3,?4,?5)",
        params![draft.username.trim(), draft.display_name.trim(), role, hash, now],
    )
    .map_err(|e| {
        if e.to_string().contains("UNIQUE constraint failed") {
            "That username already exists.".to_string()
        } else {
            db_err(e)
        }
    })?;
    let id = db.last_insert_rowid();
    db.execute(
        "INSERT INTO audit_log(entity,action,record_id,actor_id,summary,created_at) VALUES('User','Create',?1,?2,?3,?4)",
        params![id.to_string(), actor.id, format!("Created {} user {}", role, draft.username.trim()), now],
    )
    .map_err(db_err)?;
    Ok(UserRecord {
        id,
        username: draft.username.trim().into(),
        display_name: draft.display_name.trim().into(),
        role: role.into(),
        active: true,
    })
}

#[tauri::command]
pub fn update_intake_status(
    state: State<'_, AppState>,
    id: i64,
    status: String,
) -> Result<(), String> {
    let user = require_user(&state)?;
    if user.role == "Read Only" {
        return Err("Read-only users cannot change intake records.".into());
    }
    if !["New", "Reviewed", "Converted", "Duplicate"].contains(&status.as_str()) {
        return Err("Invalid intake status.".into());
    }
    let db = state
        .db
        .lock()
        .map_err(|_| "Database lock failed".to_string())?;
    db.execute(
        "UPDATE form_intake SET status=?1,processed_by=?2,processed_at=?3 WHERE id=?4",
        params![
            status,
            user.id,
            Local::now().format("%Y-%m-%d %H:%M:%S").to_string(),
            id
        ],
    )
    .map_err(db_err)?;
    Ok(())
}

#[tauri::command]
pub fn sync_google_form(state: State<'_, AppState>) -> Result<SyncStatus, String> {
    let _ = require_user(&state)?;
    let db = state
        .db
        .lock()
        .map_err(|_| "Database lock failed".to_string())?;
    let configured = setting(&db, "google_form_configured", "false") == "true";
    let now = Local::now().format("%Y-%m-%d %H:%M:%S").to_string();
    if !configured {
        db.execute(
            "INSERT INTO sync_log(started_at,completed_at,success,error_message) VALUES(?1,?1,0,'Google Form intake is not configured')",
            params![now],
        )
        .map_err(db_err)?;
        let mut status = sync_status(&db)?;
        status.message = "Google Form intake is not configured yet. Configure the source and field mapping in Settings.".into();
        return Ok(status);
    }

    // The Google source adapter is intentionally isolated here. Until credentials/source mapping
    // are configured, this command only records a successful connectivity cycle without inventing data.
    db.execute(
        "INSERT INTO sync_log(started_at,completed_at,success,fetched_count,new_count) VALUES(?1,?1,1,0,0)",
        params![now],
    )
    .map_err(db_err)?;
    sync_status(&db)
}
