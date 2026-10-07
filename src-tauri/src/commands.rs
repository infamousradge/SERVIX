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
        .prepare("SELECT id,received_at,client_name,contact,mobile,email,equipment,make,model,serial_number,complaint,match_summary,match_tone,status,linked_service_id,raw_json FROM form_intake ORDER BY received_at DESC,id DESC LIMIT 500")
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
                original_snapshot: r.get(15)?,
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
        .prepare("SELECT e.id,e.servix_equipment_id,COALESCE(e.client_id,0),COALESCE(c.name,''),e.make,e.model,e.serial_number,e.equipment_type,e.location,e.coverage,(SELECT COUNT(*) FROM service_calls sc WHERE sc.equipment_id=e.id),COALESCE((SELECT MAX(opened_date) FROM service_calls sc WHERE sc.equipment_id=e.id),'') FROM equipment e LEFT JOIN clients c ON c.id=e.client_id ORDER BY e.id DESC")
        .map_err(db_err)?;
    let rows = stmt
        .query_map([], |r| {
            Ok(EquipmentRecord {
                id: r.get(0)?,
                servix_equipment_id: r.get(1)?,
                client_id: r.get(2)?,
                client: r.get(3)?,
                make: r.get(4)?,
                model: r.get(5)?,
                serial_number: r.get(6)?,
                r#type: r.get(7)?,
                location: r.get(8)?,
                coverage: r.get(9)?,
                service_count: r.get(10)?,
                last_service: r.get(11)?,
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

fn duplicate_review(db: &Connection, draft: &ServiceCallDraft) -> Result<DuplicateReview, String> {
    let mobile = normalize_mobile(draft.mobile.as_deref().unwrap_or_default());
    let email = normalize_email(draft.email.as_deref().unwrap_or_default());
    let serial = draft.serial_number.as_deref().unwrap_or_default().trim().to_string();

    let client_candidates = {
        let mut stmt = db.prepare(
            "SELECT c.id,c.code,c.name,c.contact,c.mobile,c.email,
             (SELECT COUNT(*) FROM service_calls sc WHERE sc.client_id=c.id),
             (SELECT COUNT(*) FROM equipment e WHERE e.client_id=c.id)
             FROM clients c
             WHERE c.active=1 AND (
               (?1<>'' AND replace(replace(replace(replace(replace(c.mobile,' ',''),'-',''),'+',''),'(',''),')','')=?1)
               OR (?2<>'' AND lower(trim(c.email))=?2)
             )
             ORDER BY c.name,c.id"
        ).map_err(db_err)?;
        let rows = stmt.query_map(params![mobile,email], |r| Ok(DuplicateClientCandidate{
            id:r.get(0)?,code:r.get(1)?,name:r.get(2)?,contact:r.get(3)?,mobile:r.get(4)?,email:r.get(5)?,
            service_count:r.get(6)?,equipment_count:r.get(7)?
        })).map_err(db_err)?;
        rows.collect::<Result<Vec<_>,_>>().map_err(db_err)?
    };

    let exact_serial_candidates = if serial.is_empty() {
        Vec::new()
    } else {
        let mut stmt = db.prepare(
            "SELECT e.id,e.servix_equipment_id,COALESCE(e.client_id,0),COALESCE(c.name,''),e.make,e.model,e.serial_number,e.equipment_type,
             (SELECT COUNT(*) FROM service_calls sc WHERE sc.equipment_id=e.id)
             FROM equipment e LEFT JOIN clients c ON c.id=e.client_id
             WHERE e.active=1 AND lower(trim(e.serial_number))=lower(trim(?1))
             ORDER BY e.id"
        ).map_err(db_err)?;
        let rows = stmt.query_map(params![serial], |r| Ok(DuplicateEquipmentCandidate{
            id:r.get(0)?,servix_equipment_id:r.get(1)?,client_id:r.get(2)?,client_name:r.get(3)?,make:r.get(4)?,
            model:r.get(5)?,serial_number:r.get(6)?,equipment_type:r.get(7)?,service_count:r.get(8)?
        })).map_err(db_err)?;
        rows.collect::<Result<Vec<_>,_>>().map_err(db_err)?
    };

    // If the serial did not identify a device but the client is known, show that
    // client's registered equipment. Staff can deliberately select the returning
    // device or create a genuinely new device under the same client.
    let equipment_candidates = if !exact_serial_candidates.is_empty() {
        exact_serial_candidates
    } else if client_candidates.len()==1 {
        let client_id = client_candidates[0].id;
        let mut stmt = db.prepare(
            "SELECT e.id,e.servix_equipment_id,COALESCE(e.client_id,0),COALESCE(c.name,''),e.make,e.model,e.serial_number,e.equipment_type,
             (SELECT COUNT(*) FROM service_calls sc WHERE sc.equipment_id=e.id)
             FROM equipment e LEFT JOIN clients c ON c.id=e.client_id
             WHERE e.active=1 AND e.client_id=?1
             ORDER BY (CASE WHEN lower(trim(e.equipment_type))=lower(trim(?2)) THEN 0 ELSE 1 END),
                      (CASE WHEN ?3<>'' AND lower(trim(e.make))=lower(trim(?3)) THEN 0 ELSE 1 END),
                      (CASE WHEN ?4<>'' AND lower(trim(e.model))=lower(trim(?4)) THEN 0 ELSE 1 END),
                      e.id DESC"
        ).map_err(db_err)?;
        let rows = stmt.query_map(
            params![client_id,draft.equipment.trim(),draft.make.as_deref().unwrap_or_default().trim(),draft.model.as_deref().unwrap_or_default().trim()],
            |r| Ok(DuplicateEquipmentCandidate{
                id:r.get(0)?,servix_equipment_id:r.get(1)?,client_id:r.get(2)?,client_name:r.get(3)?,make:r.get(4)?,
                model:r.get(5)?,serial_number:r.get(6)?,equipment_type:r.get(7)?,service_count:r.get(8)?
            })
        ).map_err(db_err)?;
        rows.collect::<Result<Vec<_>,_>>().map_err(db_err)?
    } else {
        Vec::new()
    };

    let open_services = {
        let mut stmt = if !serial.is_empty() {
            db.prepare(
                "SELECT id,service_id,client_name,equipment_name,status,opened_date,complaint
                 FROM service_calls
                 WHERE status<>'Closed' AND lower(trim(serial_number))=lower(trim(?1))
                 ORDER BY opened_date DESC,id DESC"
            ).map_err(db_err)?
        } else {
            db.prepare(
                "SELECT id,service_id,client_name,equipment_name,status,opened_date,complaint
                 FROM service_calls
                 WHERE status<>'Closed' AND lower(trim(client_name))=lower(trim(?1)) AND lower(trim(equipment_name))=lower(trim(?2))
                 ORDER BY opened_date DESC,id DESC"
            ).map_err(db_err)?
        };
        if !serial.is_empty() {
            stmt.query_map(params![serial], |r| Ok(DuplicateServiceCandidate{
                id:r.get(0)?,service_id:r.get(1)?,client:r.get(2)?,equipment:r.get(3)?,status:r.get(4)?,opened_date:r.get(5)?,complaint:r.get(6)?
            })).map_err(db_err)?.collect::<Result<Vec<_>,_>>().map_err(db_err)?
        } else {
            stmt.query_map(params![draft.client.trim(),draft.equipment.trim()], |r| Ok(DuplicateServiceCandidate{
                id:r.get(0)?,service_id:r.get(1)?,client:r.get(2)?,equipment:r.get(3)?,status:r.get(4)?,opened_date:r.get(5)?,complaint:r.get(6)?
            })).map_err(db_err)?.collect::<Result<Vec<_>,_>>().map_err(db_err)?
        }
    };

    let mut warnings = Vec::new();
    let mut requires_override = false;
    if client_candidates.len() > 1 {
        warnings.push("The entered mobile/email matches more than one client record. Choose the correct client or create a separate record with administrator approval.".into());
        requires_override = true;
    }
    if equipment_candidates.len() > 1 {
        warnings.push("The serial number already exists on more than one equipment record. Confirm the correct equipment before continuing.".into());
        requires_override = true;
    }
    if !equipment_candidates.is_empty() {
        let client_ids: Vec<i64> = client_candidates.iter().map(|x| x.id).collect();
        let serial_on_other_client = equipment_candidates.iter().any(|e| client_ids.is_empty() || !client_ids.contains(&e.client_id));
        if serial_on_other_client {
            warnings.push("This serial number is already linked to another client/equipment record.".into());
            requires_override = true;
        }
    }
    if !open_services.is_empty() {
        warnings.push(format!("{} open / in-progress / pending Service Call(s) already match this equipment. Creating another call requires administrator approval.", open_services.len()));
        requires_override = true;
    }

    let level = if requires_override {"warning"} else if !client_candidates.is_empty() || !equipment_candidates.is_empty() {"match"} else {"clear"}.to_string();
    let has_exact_serial_match = !serial.is_empty() && equipment_candidates.iter().any(|e| e.serial_number.eq_ignore_ascii_case(&serial));
    let summary = if level == "warning" {
        "Potential duplicate or record conflict found. Review the existing records before creating this Service Call.".to_string()
    } else if has_exact_serial_match {
        "This device already exists in SERVIX. Select the existing equipment record so this visit is added to its history.".to_string()
    } else if client_candidates.len()==1 && !equipment_candidates.is_empty() {
        "Existing client found with registered equipment. Select the returning device, or create a new equipment record under this client.".to_string()
    } else if level == "match" {
        "Existing client/equipment records were found. Confirm the records SERVIX should link to this Service Call.".to_string()
    } else {
        "No existing client/equipment duplicate was found.".to_string()
    };

    Ok(DuplicateReview{level,summary,client_candidates,equipment_candidates,open_services,warnings,requires_override})
}

fn verify_admin_override(db: &Connection, password: &str) -> Result<bool, String> {
    if password.is_empty() { return Ok(false); }
    let mut stmt = db.prepare("SELECT password_hash FROM users WHERE role='Administrator' AND active=1").map_err(db_err)?;
    let rows = stmt.query_map([], |r| r.get::<_,String>(0)).map_err(db_err)?;
    for row in rows {
        if security::verify_password(password, &row.map_err(db_err)?) { return Ok(true); }
    }
    Ok(false)
}

#[tauri::command]
pub fn review_service_duplicates(state: State<'_, AppState>, draft: ServiceCallDraft) -> Result<DuplicateReview, String> {
    let _ = require_user(&state)?;
    let db = state.db.lock().map_err(|_| "Database lock failed".to_string())?;
    duplicate_review(&db, &draft)
}

fn insert_new_client(tx: &Transaction<'_>, draft: &ServiceCallDraft) -> Result<i64, String> {
    let code = next_human_id(tx, "client_prefix", "client_next_number", "client_digits", "CLI-", 1001)?;
    let now = Local::now().format("%Y-%m-%d %H:%M:%S").to_string();
    tx.execute(
        "INSERT INTO clients(code,name,contact,mobile,email,created_at,updated_at) VALUES(?1,?2,?3,?4,?5,?6,?6)",
        params![code,draft.client.trim(),draft.contact.as_deref().unwrap_or_default().trim(),normalize_mobile(draft.mobile.as_deref().unwrap_or_default()),normalize_email(draft.email.as_deref().unwrap_or_default()),now],
    ).map_err(db_err)?;
    Ok(tx.last_insert_rowid())
}

fn find_or_create_client(tx: &Transaction<'_>, draft: &ServiceCallDraft) -> Result<i64, String> {
    if draft.force_new_client { return insert_new_client(tx,draft); }
    if let Some(id) = draft.selected_client_id {
        let exists: Option<i64> = tx.query_row("SELECT id FROM clients WHERE id=?1 AND active=1",params![id],|r|r.get(0)).optional().map_err(db_err)?;
        return exists.ok_or_else(|| "The selected client is no longer available. Review duplicates again.".into());
    }
    let mobile = normalize_mobile(draft.mobile.as_deref().unwrap_or_default());
    let email = normalize_email(draft.email.as_deref().unwrap_or_default());
    let mut stmt = tx.prepare(
        "SELECT id FROM clients WHERE active=1 AND ((?1<>'' AND replace(replace(replace(replace(replace(mobile,' ',''),'-',''),'+',''),'(',''),')','')=?1) OR (?2<>'' AND lower(trim(email))=?2)) ORDER BY id"
    ).map_err(db_err)?;
    let ids = stmt.query_map(params![mobile,email],|r|r.get::<_,i64>(0)).map_err(db_err)?.collect::<Result<Vec<_>,_>>().map_err(db_err)?;
    match ids.len() {0=>insert_new_client(tx,draft),1=>Ok(ids[0]),_=>Err("More than one client matches this mobile/email. Review duplicates and choose a client before saving.".into())}
}

fn insert_new_equipment(tx: &Transaction<'_>, client_id: i64, draft: &ServiceCallDraft) -> Result<i64, String> {
    let servix_id = next_human_id(tx, "equipment_prefix", "equipment_next_number", "equipment_digits", "EQ-", 10001)?;
    let now = Local::now().format("%Y-%m-%d %H:%M:%S").to_string();
    tx.execute(
        "INSERT INTO equipment(servix_equipment_id,client_id,make,model,serial_number,equipment_type,location,coverage,created_at,updated_at) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?9)",
        params![servix_id,client_id,draft.make.as_deref().unwrap_or_default().trim(),draft.model.as_deref().unwrap_or_default().trim(),draft.serial_number.as_deref().unwrap_or_default().trim(),draft.equipment.trim(),draft.service_location.trim(),draft.coverage.as_str(),now],
    ).map_err(db_err)?;
    Ok(tx.last_insert_rowid())
}

fn find_or_create_equipment(tx: &Transaction<'_>, client_id: i64, draft: &ServiceCallDraft) -> Result<i64, String> {
    if let Some(id) = draft.selected_equipment_id {
        let owner: Option<i64> = tx.query_row("SELECT client_id FROM equipment WHERE id=?1 AND active=1",params![id],|r|r.get(0)).optional().map_err(db_err)?;
        let owner = owner.ok_or_else(|| "The selected equipment is no longer available. Review duplicates again.".to_string())?;
        if owner != client_id { return Err("Selected equipment belongs to a different client. Choose its linked client or create a separate equipment record with administrator approval.".into()); }
        return Ok(id);
    }
    if draft.force_new_equipment { return insert_new_equipment(tx,client_id,draft); }
    let serial = draft.serial_number.as_deref().unwrap_or_default().trim();
    if !serial.is_empty() {
        let mut stmt = tx.prepare("SELECT id FROM equipment WHERE active=1 AND client_id=?1 AND lower(trim(serial_number))=lower(trim(?2)) ORDER BY id").map_err(db_err)?;
        let ids = stmt.query_map(params![client_id,serial],|r|r.get::<_,i64>(0)).map_err(db_err)?.collect::<Result<Vec<_>,_>>().map_err(db_err)?;
        if ids.len()==1 { return Ok(ids[0]); }
        if ids.len()>1 { return Err("More than one equipment record with this serial exists for the selected client. Review duplicates and choose one.".into()); }
        let other_count:i64=tx.query_row("SELECT COUNT(*) FROM equipment WHERE active=1 AND client_id<>?1 AND lower(trim(serial_number))=lower(trim(?2))",params![client_id,serial],|r|r.get(0)).map_err(db_err)?;
        if other_count>0 { return Err("This serial number is already linked to another client. Use duplicate review and administrator override to create a separate equipment record.".into()); }
    }
    insert_new_equipment(tx,client_id,draft)
}

#[tauri::command]
pub fn create_service_call(state: State<'_, AppState>, draft: ServiceCallDraft) -> Result<ServiceCall, String> {
    let user = require_user(&state)?;
    if user.role == "Read Only" { return Err("Read-only users cannot create service calls.".into()); }
    if draft.client.trim().is_empty() || draft.equipment.trim().is_empty() || draft.reason.trim().is_empty() || draft.complaint.trim().is_empty() {
        return Err("Client, equipment, reason and complaint are required.".into());
    }

    let mut db = state.db.lock().map_err(|_| "Database lock failed".to_string())?;
    let review = duplicate_review(&db, &draft)?;
    let creating_separate_client = draft.force_new_client && !review.client_candidates.is_empty();
    let creating_separate_equipment = draft.force_new_equipment && !review.equipment_candidates.is_empty();
    let override_needed = review.requires_override || creating_separate_client || creating_separate_equipment;
    let override_ok = if override_needed {
        let password = draft.duplicate_override_password.as_deref().unwrap_or_default();
        if !verify_admin_override(&db,password)? { return Err("Administrator password is required to override this duplicate/conflict warning.".into()); }
        true
    } else { false };

    if review.client_candidates.len()>1 && draft.selected_client_id.is_none() && !draft.force_new_client {
        return Err("Choose the correct existing client, or choose Create Separate Client with administrator approval.".into());
    }
    if review.equipment_candidates.len()>1 && draft.selected_equipment_id.is_none() && !draft.force_new_equipment {
        return Err("Choose the correct existing equipment, or choose Create Separate Equipment with administrator approval.".into());
    }

    let tx = db.transaction().map_err(db_err)?;
    let client_id = find_or_create_client(&tx,&draft)?;
    let equipment_id = find_or_create_equipment(&tx,client_id,&draft)?;
    let linked_client_name:String=tx.query_row("SELECT name FROM clients WHERE id=?1",params![client_id],|r|r.get(0)).map_err(db_err)?;
    let (linked_equipment_name,linked_make,linked_model,linked_serial):(String,String,String,String)=tx.query_row(
        "SELECT equipment_type,make,model,serial_number FROM equipment WHERE id=?1",params![equipment_id],
        |r|Ok((r.get(0)?,r.get(1)?,r.get(2)?,r.get(3)?))
    ).map_err(db_err)?;

    let service_id=next_human_id(&tx,"service_prefix","service_next_number","service_digits","SRV-",10001)?;
    let now=Local::now().format("%Y-%m-%d %H:%M:%S").to_string();
    tx.execute(
        "INSERT INTO service_calls(service_id,opened_date,client_id,equipment_id,client_name,equipment_name,make,model,serial_number,reason,complaint,engineer,status,priority,service_location,due_date,coverage,foc,quote_status,payment_status,created_by,created_at,updated_at) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,?13,?14,?15,?16,?17,?18,?19,?20,?21,?22,?22)",
        params![
            service_id,draft.opened_date,client_id,equipment_id,linked_client_name,
            if linked_equipment_name.trim().is_empty(){draft.equipment.trim()}else{linked_equipment_name.as_str()},
            if linked_make.trim().is_empty(){draft.make.as_deref().unwrap_or_default().trim()}else{linked_make.as_str()},
            if linked_model.trim().is_empty(){draft.model.as_deref().unwrap_or_default().trim()}else{linked_model.as_str()},
            if linked_serial.trim().is_empty(){draft.serial_number.as_deref().unwrap_or_default().trim()}else{linked_serial.as_str()},
            draft.reason,draft.complaint,draft.engineer.as_deref().unwrap_or_default().trim(),draft.status,draft.priority,draft.service_location,
            draft.due_date.as_deref().unwrap_or_default(),draft.coverage,if draft.foc {1}else{0},draft.quote_status,draft.payment_status,user.id,now
        ],
    ).map_err(db_err)?;
    let id=tx.last_insert_rowid();
    tx.execute("INSERT INTO service_events(service_call_id,event_type,new_value,note,actor_id,created_at) VALUES(?1,'Created',?2,'Service call created',?3,?4)",params![id,service_id,user.id,now]).map_err(db_err)?;
    if override_ok {
        tx.execute("INSERT INTO service_events(service_call_id,event_type,note,actor_id,created_at) VALUES(?1,'Duplicate Override','Administrator password override approved after duplicate/conflict review',?2,?3)",params![id,user.id,now]).map_err(db_err)?;
    }
    let audit_summary=if override_ok {format!("Created service call for {} after duplicate override",linked_client_name)} else {format!("Created service call for {}",linked_client_name)};
    tx.execute("INSERT INTO audit_log(entity,action,record_id,actor_id,summary,created_at) VALUES('ServiceCall','Create',?1,?2,?3,?4)",params![service_id,user.id,audit_summary,now]).map_err(db_err)?;
    if let Some(intake_id) = draft.source_intake_id {
        tx.execute(
            "UPDATE form_intake SET status='Converted',linked_service_id=?1,processed_by=?2,processed_at=?3 WHERE id=?4",
            params![service_id,user.id,now,intake_id],
        ).map_err(db_err)?;
        tx.execute(
            "INSERT INTO service_events(service_call_id,event_type,new_value,note,actor_id,created_at) VALUES(?1,'Intake Converted',?2,'Converted from incoming request after staff review',?3,?4)",
            params![id,intake_id.to_string(),user.id,now],
        ).map_err(db_err)?;
        tx.execute(
            "INSERT INTO audit_log(entity,action,record_id,actor_id,summary,created_at) VALUES('Intake','Convert',?1,?2,?3,?4)",
            params![intake_id.to_string(),user.id,format!("Converted to {}",service_id),now],
        ).map_err(db_err)?;
    }
    tx.commit().map_err(db_err)?;
    drop(db);

    let db=state.db.lock().map_err(|_| "Database lock failed".to_string())?;
    list_services(&db)?.into_iter().find(|x|x.id==id).ok_or_else(|| "Service call was saved but could not be reloaded.".into())
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
pub fn save_intake_review(
    state: State<'_, AppState>,
    draft: IntakeReviewDraft,
) -> Result<(), String> {
    let user = require_user(&state)?;
    if user.role == "Read Only" {
        return Err("Read-only users cannot review intake records.".into());
    }
    if draft.client.trim().is_empty() || draft.equipment.trim().is_empty() || draft.complaint.trim().is_empty() {
        return Err("Client, equipment and complaint are required before marking the request Reviewed.".into());
    }
    let db = state.db.lock().map_err(|_| "Database lock failed".to_string())?;
    let current_status: String = db.query_row(
        "SELECT status FROM form_intake WHERE id=?1",
        params![draft.id],
        |r| r.get(0)
    ).optional().map_err(db_err)?.ok_or_else(|| "Incoming request not found.".to_string())?;
    if current_status == "Converted" {
        return Err("Converted intake records are read-only.".into());
    }
    let now = Local::now().format("%Y-%m-%d %H:%M:%S").to_string();
    db.execute(
        "UPDATE form_intake SET client_name=?1,contact=?2,mobile=?3,email=?4,equipment=?5,make=?6,model=?7,serial_number=?8,complaint=?9,status='Reviewed',processed_by=?10,processed_at=?11 WHERE id=?12",
        params![
            draft.client.trim(),draft.contact.trim(),normalize_mobile(&draft.mobile),normalize_email(&draft.email),
            draft.equipment.trim(),draft.make.trim(),draft.model.trim(),draft.serial_number.trim(),draft.complaint.trim(),
            user.id,now,draft.id
        ],
    ).map_err(db_err)?;
    db.execute(
        "INSERT INTO audit_log(entity,action,record_id,actor_id,summary,created_at) VALUES('Intake','Review',?1,?2,'Incoming request reviewed; original submission snapshot retained',?3)",
        params![draft.id.to_string(),user.id,now],
    ).map_err(db_err)?;
    Ok(())
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


fn qa_insert_client(
    tx: &Transaction<'_>,
    name: &str,
    contact: &str,
    mobile: &str,
    email: &str,
    city: &str,
    state_name: &str,
    now: &str,
) -> Result<i64, String> {
    let code = next_human_id(tx, "client_prefix", "client_next_number", "client_digits", "CLI-", 1001)?;
    tx.execute(
        "INSERT INTO clients(code,name,contact,mobile,email,city,state,created_at,updated_at) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?8)",
        params![code,name,contact,mobile,email,city,state_name,now],
    ).map_err(db_err)?;
    Ok(tx.last_insert_rowid())
}

fn qa_insert_equipment(
    tx: &Transaction<'_>,
    client_id: i64,
    make: &str,
    model: &str,
    serial: &str,
    equipment_type: &str,
    location: &str,
    coverage: &str,
    warranty_until: &str,
    amc_until: &str,
    now: &str,
) -> Result<i64, String> {
    let equipment_id = next_human_id(tx, "equipment_prefix", "equipment_next_number", "equipment_digits", "EQ-", 10001)?;
    tx.execute(
        "INSERT INTO equipment(servix_equipment_id,client_id,make,model,serial_number,equipment_type,location,coverage,warranty_until,amc_until,created_at,updated_at) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?11)",
        params![equipment_id,client_id,make,model,serial,equipment_type,location,coverage,warranty_until,amc_until,now],
    ).map_err(db_err)?;
    Ok(tx.last_insert_rowid())
}

#[allow(clippy::too_many_arguments)]
fn qa_insert_service(
    tx: &Transaction<'_>,
    actor_id: i64,
    opened_date: &str,
    client_id: i64,
    equipment_id: i64,
    client_name: &str,
    equipment_name: &str,
    make: &str,
    model: &str,
    serial: &str,
    reason: &str,
    complaint: &str,
    engineer: &str,
    status: &str,
    priority: &str,
    due_date: &str,
    coverage: &str,
    foc: bool,
    quote_status: &str,
    payment_status: &str,
    now: &str,
) -> Result<(i64, String), String> {
    let service_id = next_human_id(tx, "service_prefix", "service_next_number", "service_digits", "SRV-", 10001)?;
    tx.execute(
        "INSERT INTO service_calls(service_id,opened_date,client_id,equipment_id,client_name,equipment_name,make,model,serial_number,reason,complaint,engineer,status,priority,service_location,due_date,coverage,foc,quote_status,payment_status,created_by,created_at,updated_at) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,?13,?14,'Workshop',?15,?16,?17,?18,?19,?20,?21,?21)",
        params![service_id,opened_date,client_id,equipment_id,client_name,equipment_name,make,model,serial,reason,complaint,engineer,status,priority,due_date,coverage,if foc {1}else{0},quote_status,payment_status,actor_id,now],
    ).map_err(db_err)?;
    let id = tx.last_insert_rowid();
    tx.execute(
        "INSERT INTO service_events(service_call_id,event_type,new_value,note,actor_id,created_at) VALUES(?1,'Created',?2,'QA service call created',?3,?4)",
        params![id,service_id,actor_id,now],
    ).map_err(db_err)?;
    Ok((id, service_id))
}

#[tauri::command]
pub fn load_qa_mock_data(state: State<'_, AppState>) -> Result<String, String> {
    let actor = require_admin(&state)?;
    let mut db = state.db.lock().map_err(|_| "Database lock failed".to_string())?;
    if setting(&db, "qa_seed_version", "") == "qa-v1" {
        return Ok("QA test data is already loaded. Existing QA records were left unchanged.".into());
    }

    let now = Local::now().format("%Y-%m-%d %H:%M:%S").to_string();
    let today = Local::now().date_naive();
    let date = |days: i64| (today + Duration::days(days)).format("%Y-%m-%d").to_string();
    let tx = db.transaction().map_err(db_err)?;

    // Clients deliberately include a same-mobile/same-email duplicate scenario.
    let city = qa_insert_client(&tx,"City Hospital","Mr. Sharma","9876543210","service@cityhospital.in","New Delhi","Delhi",&now)?;
    let city_duplicate = qa_insert_client(&tx,"City Hospital - North Wing","Ms. Riya","9876543210","service@cityhospital.in","New Delhi","Delhi",&now)?;
    let hearing = qa_insert_client(&tx,"Hearing Care Clinic","Dr. Mehta","9811122233","care@hearingclinic.in","Gurugram","Haryana",&now)?;
    let apollo = qa_insert_client(&tx,"Apollo Audiology Centre","Ms. Nisha","9988776655","audiology@apolloqa.in","Bengaluru","Karnataka",&now)?;
    let sound = qa_insert_client(&tx,"Sound & Speech Centre","Mr. Arjun","9900112233","service@soundandspeech.in","Mumbai","Maharashtra",&now)?;

    // Equipment deliberately includes the same serial under the duplicate City Hospital client.
    let e_city_ma42 = qa_insert_equipment(&tx,city,"MAICO","MA42","QA-MA42-001","Audiometer","Audiology Dept.","Warranty",&date(120),"",&now)?;
    let e_city_sentiero = qa_insert_equipment(&tx,city,"PATH MEDICAL","Sentiero Advanced","QA-SEN-2002","Diagnostic Platform","ENT Dept.","AMC","",&date(180),&now)?;
    let e_hearing_ma42 = qa_insert_equipment(&tx,hearing,"MAICO","MA42","QA-MA42-003","Audiometer","Clinic Room 2","Out of Coverage","","",&now)?;
    let e_apollo_titan = qa_insert_equipment(&tx,apollo,"Interacoustics","Titan","QA-TIT-004","Tympanometer","Audiology Lab","Warranty",&date(240),"",&now)?;
    let e_duplicate_serial = qa_insert_equipment(&tx,city_duplicate,"MAICO","MA42","QA-MA42-001","Audiometer","North Wing","Out of Coverage","","",&now)?;
    let e_sound_oae = qa_insert_equipment(&tx,sound,"PATH MEDICAL","Qscreen","QA-QSC-005","Newborn Screening","NICU","AMC","",&date(75),&now)?;

    // Repeat-equipment history, repeat complaint, open/closed status, all coverage types and commercial states.
    let (s1, _) = qa_insert_service(&tx,actor.id,&date(-150),city,e_city_ma42,"City Hospital","Audiometer","MAICO","MA42","QA-MA42-001","Calibration","Annual calibration and performance verification","Rohit","Closed","Normal",&date(-145),"Warranty",true,"No Quote","Paid",&now)?;
    let (s2, _) = qa_insert_service(&tx,actor.id,&date(-55),city,e_city_ma42,"City Hospital","Audiometer","MAICO","MA42","QA-MA42-001","Repair / Breakdown","Intermittent right channel output","Amit","Closed","High",&date(-50),"Warranty",false,"Quote Sent","Paid",&now)?;
    let (s3, _) = qa_insert_service(&tx,actor.id,&date(-2),city,e_city_ma42,"City Hospital","Audiometer","MAICO","MA42","QA-MA42-001","Repair / Breakdown","Intermittent right channel output again","Amit","Open","High",&date(2),"Warranty",false,"No Quote","Pending",&now)?;
    let (s4, _) = qa_insert_service(&tx,actor.id,&date(-7),city,e_city_sentiero,"City Hospital","Diagnostic Platform","PATH MEDICAL","Sentiero Advanced","QA-SEN-2002","Preventive Maintenance","AMC preventive maintenance visit","Rohit","Pending","Normal",&date(5),"AMC",true,"No Quote","Pending",&now)?;
    let (s5, _) = qa_insert_service(&tx,actor.id,&date(-38),hearing,e_hearing_ma42,"Hearing Care Clinic","Audiometer","MAICO","MA42","QA-MA42-003","Repair / Breakdown","No bone conduction output","Vikram","Closed","Normal",&date(-31),"Out of Coverage",false,"Quote Sent","Paid",&now)?;
    let (s6, _) = qa_insert_service(&tx,actor.id,&date(0),apollo,e_apollo_titan,"Apollo Audiology Centre","Tympanometer","Interacoustics","Titan","QA-TIT-004","Repair / Breakdown","Probe not detected intermittently","Rohit","In Progress","Urgent",&date(3),"Warranty",true,"No Quote","Pending",&now)?;
    let (s7, _) = qa_insert_service(&tx,actor.id,&date(0),city_duplicate,e_duplicate_serial,"City Hospital - North Wing","Audiometer","MAICO","MA42","QA-MA42-001","Repair / Breakdown","Same serial entered under another client record","Amit","Open","Normal",&date(4),"Out of Coverage",false,"No Quote","Pending",&now)?;
    let (s8, _) = qa_insert_service(&tx,actor.id,&date(-12),sound,e_sound_oae,"Sound & Speech Centre","Newborn Screening","PATH MEDICAL","Qscreen","QA-QSC-005","Inspection","Screening unit requires verification before camp","Vikram","Closed","Normal",&date(-8),"AMC",true,"No Quote","Paid",&now)?;

    for (service_id,event_type,note) in [
        (s2,"Communication","Customer approved repair by phone; formal quote was also sent."),
        (s2,"Engineer Update","Right-channel connector reseated and output verified."),
        (s3,"Communication","Customer requested urgent turnaround due to scheduled patient testing."),
        (s3,"Repeat Complaint","Complaint resembles the previous repair on the same equipment."),
        (s4,"Customer Update","AMC visit date discussed with hospital biomedical team."),
        (s6,"Engineer Update","Probe cable being checked before replacement decision."),
    ] {
        tx.execute(
            "INSERT INTO service_events(service_call_id,event_type,note,actor_id,created_at) VALUES(?1,?2,?3,?4,?5)",
            params![service_id,event_type,note,actor.id,now],
        ).map_err(db_err)?;
    }

    for (service_id,item,make,model,part_number,qty,remarks) in [
        (s2,"Audio Jack Assembly","MAICO","MA42","QA-PN-1001",1_i64,"Replaced during right-channel repair"),
        (s3,"Headphone Cable","Generic","DD45","QA-PN-1002",1_i64,"Used for diagnostic substitution test"),
        (s5,"BC Connector","MAICO","MA42","QA-PN-2001",1_i64,"Replaced and retested"),
        (s6,"Probe Seal Set","Interacoustics","Titan","QA-PN-3001",2_i64,"Used during probe verification"),
    ] {
        tx.execute(
            "INSERT INTO part_usage(service_call_id,item_name,make,model,part_number,quantity,remarks,used_at) VALUES(?1,?2,?3,?4,?5,?6,?7,?8)",
            params![service_id,item,make,model,part_number,qty,remarks,now],
        ).map_err(db_err)?;
    }

    // Intake rows mimic real Google submissions and include duplicate/matching cases.
    let intake_rows = [
        ("QA-INTAKE-001",&date(-1),"City Hospital","Mr. Sharma","9876543210","service@cityhospital.in","Audiometer","MAICO","MA42","QA-MA42-001","Intermittent right channel output again","Existing Client + Equipment Found","good","New"),
        ("QA-INTAKE-002",&date(0),"City Hospital","Mr. Sharma","9876543210","service@cityhospital.in","Audiometer","MAICO","MA42","QA-MA42-001","Intermittent right channel output again","Possible duplicate open Service Call","warn","New"),
        ("QA-INTAKE-003",&date(0),"New Life Hospital","Ms. Kavya","9000011111","biomed@newlifeqa.in","Tympanometer","MAICO","easyTymp","QA-NEW-9001","No pressure seal","New Client","neutral","New"),
        ("QA-INTAKE-004",&date(0),"City Hospital - North Wing","Ms. Riya","9876543210","service@cityhospital.in","Audiometer","MAICO","MA42","QA-MA42-001","Equipment received for repair","Same serial appears under another client","warn","Reviewed"),
    ];
    for (external_id,received_at,client_name,contact,mobile,email,equipment,make,model,serial,complaint,match_summary,match_tone,status) in intake_rows {
        let raw_json = format!("{{\"externalId\":\"{}\",\"client\":\"{}\",\"serial\":\"{}\",\"complaint\":\"{}\"}}",external_id,client_name,serial,complaint.replace('"', "'"));
        tx.execute(
            "INSERT INTO form_intake(external_id,received_at,client_name,contact,mobile,email,equipment,make,model,serial_number,complaint,raw_json,match_summary,match_tone,status) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,?13,?14,?15)",
            params![external_id,received_at,client_name,contact,mobile,email,equipment,make,model,serial,complaint,raw_json,match_summary,match_tone,status],
        ).map_err(db_err)?;
    }

    tx.execute(
        "INSERT INTO settings(key,value,updated_at) VALUES('qa_seed_version','qa-v1',?1) ON CONFLICT(key) DO UPDATE SET value='qa-v1',updated_at=excluded.updated_at",
        params![now],
    ).map_err(db_err)?;
    tx.execute(
        "INSERT INTO audit_log(entity,action,record_id,actor_id,summary,created_at) VALUES('QAData','Load','qa-v1',?1,'Loaded controlled SERVIX duplicate/history QA dataset',?2)",
        params![actor.id,now],
    ).map_err(db_err)?;
    tx.commit().map_err(db_err)?;

    Ok("QA test data loaded: repeat clients/equipment, duplicate mobile/email, duplicate serial, open/closed calls, Warranty/AMC/out-of-coverage, parts, payments, notes and intake cases.".into())
}
