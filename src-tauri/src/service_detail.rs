use chrono::Local;
use rusqlite::{params, Connection, OptionalExtension};
use serde::{Deserialize, Serialize};
use tauri::State;

use crate::state::AppState;

pub fn ensure_schema(conn: &Connection) -> Result<(), String> {
    conn.execute_batch(
        r#"
        CREATE TABLE IF NOT EXISTS service_details(
            service_call_id INTEGER PRIMARY KEY,
            diagnosis TEXT NOT NULL DEFAULT '',
            work_performed TEXT NOT NULL DEFAULT '',
            testing_verification TEXT NOT NULL DEFAULT '',
            final_result TEXT NOT NULL DEFAULT '',
            recommendations TEXT NOT NULL DEFAULT '',
            received_condition TEXT NOT NULL DEFAULT '',
            received_accessories TEXT NOT NULL DEFAULT '',
            received_remarks TEXT NOT NULL DEFAULT '',
            completion_date TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL,
            FOREIGN KEY(service_call_id) REFERENCES service_calls(id) ON DELETE CASCADE
        );
        "#,
    )
    .map_err(|e| format!("Database error: {e}"))?;
    Ok(())
}

fn require_editor(state: &State<'_, AppState>) -> Result<i64, String> {
    let user = state
        .session
        .lock()
        .map_err(|_| "Session lock failed".to_string())?
        .clone()
        .ok_or_else(|| "Please sign in again.".to_string())?;
    if user.role == "Read Only" {
        return Err("Read-only users cannot change service records.".into());
    }
    Ok(user.id)
}

fn require_user(state: &State<'_, AppState>) -> Result<i64, String> {
    state
        .session
        .lock()
        .map_err(|_| "Session lock failed".to_string())?
        .clone()
        .map(|u| u.id)
        .ok_or_else(|| "Please sign in again.".to_string())
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct DetailPart {
    pub id: i64,
    pub item_name: String,
    pub make: String,
    pub model: String,
    pub part_number: String,
    pub quantity: i64,
    pub remarks: String,
    pub used_at: String,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct DetailEvent {
    pub id: i64,
    pub event_type: String,
    pub old_value: String,
    pub new_value: String,
    pub note: String,
    pub actor: String,
    pub created_at: String,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct EntityHistoryEvent {
    pub id: i64,
    pub service_call_id: i64,
    pub service_id: String,
    pub client: String,
    pub equipment: String,
    pub serial_number: String,
    pub reason: String,
    pub service_status: String,
    pub event_type: String,
    pub old_value: String,
    pub new_value: String,
    pub note: String,
    pub actor: String,
    pub created_at: String,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ServiceDetailView {
    pub id: i64,
    pub service_id: String,
    pub opened_date: String,
    pub client: String,
    pub equipment: String,
    pub make: String,
    pub model: String,
    pub serial_number: String,
    pub reason: String,
    pub complaint: String,
    pub engineer: String,
    pub status: String,
    pub priority: String,
    pub service_location: String,
    pub due_date: String,
    pub coverage: String,
    pub foc: bool,
    pub quote_status: String,
    pub payment_status: String,
    pub diagnosis: String,
    pub work_performed: String,
    pub testing_verification: String,
    pub final_result: String,
    pub recommendations: String,
    pub received_condition: String,
    pub received_accessories: String,
    pub received_remarks: String,
    pub completion_date: String,
    pub attachment_count: i64,
    pub parts: Vec<DetailPart>,
    pub events: Vec<DetailEvent>,
    pub updated_at: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct UpdateServiceDetailDraft {
    pub id: i64,
    pub reason: String,
    pub complaint: String,
    pub engineer: String,
    pub status: String,
    pub priority: String,
    pub service_location: String,
    pub due_date: String,
    pub coverage: String,
    pub foc: bool,
    pub quote_status: String,
    pub payment_status: String,
    pub diagnosis: String,
    pub work_performed: String,
    pub testing_verification: String,
    pub final_result: String,
    pub recommendations: String,
    pub received_condition: String,
    pub received_accessories: String,
    pub received_remarks: String,
    pub completion_date: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct AddPartDraft {
    pub service_call_id: i64,
    pub item_name: String,
    pub make: String,
    pub model: String,
    pub part_number: String,
    pub quantity: i64,
    pub remarks: String,
}

fn load_detail(conn: &Connection, id: i64) -> Result<ServiceDetailView, String> {
    ensure_schema(conn)?;
    let mut detail = conn
        .query_row(
            r#"SELECT sc.id,sc.service_id,sc.opened_date,sc.client_name,sc.equipment_name,sc.make,sc.model,sc.serial_number,
            sc.reason,sc.complaint,sc.engineer,sc.status,sc.priority,sc.service_location,sc.due_date,sc.coverage,sc.foc,
            sc.quote_status,sc.payment_status,COALESCE(sd.diagnosis,''),COALESCE(sd.work_performed,''),
            COALESCE(sd.testing_verification,''),COALESCE(sd.final_result,''),COALESCE(sd.recommendations,''),
            COALESCE(sd.received_condition,''),COALESCE(sd.received_accessories,''),COALESCE(sd.received_remarks,''),
            COALESCE(sd.completion_date,''),sc.updated_at
            FROM service_calls sc LEFT JOIN service_details sd ON sd.service_call_id=sc.id WHERE sc.id=?1"#,
            params![id],
            |r| {
                Ok(ServiceDetailView {
                    id: r.get(0)?,
                    service_id: r.get(1)?,
                    opened_date: r.get(2)?,
                    client: r.get(3)?,
                    equipment: r.get(4)?,
                    make: r.get(5)?,
                    model: r.get(6)?,
                    serial_number: r.get(7)?,
                    reason: r.get(8)?,
                    complaint: r.get(9)?,
                    engineer: r.get(10)?,
                    status: r.get(11)?,
                    priority: r.get(12)?,
                    service_location: r.get(13)?,
                    due_date: r.get(14)?,
                    coverage: r.get(15)?,
                    foc: r.get::<_, i64>(16)? != 0,
                    quote_status: r.get(17)?,
                    payment_status: r.get(18)?,
                    diagnosis: r.get(19)?,
                    work_performed: r.get(20)?,
                    testing_verification: r.get(21)?,
                    final_result: r.get(22)?,
                    recommendations: r.get(23)?,
                    received_condition: r.get(24)?,
                    received_accessories: r.get(25)?,
                    received_remarks: r.get(26)?,
                    completion_date: r.get(27)?,
                    attachment_count: 0,
                    parts: vec![],
                    events: vec![],
                    updated_at: r.get(28)?,
                })
            },
        )
        .optional()
        .map_err(|e| format!("Database error: {e}"))?
        .ok_or_else(|| "Service call not found.".to_string())?;

    detail.attachment_count = conn
        .query_row(
            "SELECT COUNT(*) FROM attachments WHERE parent_type='ServiceCall' AND parent_id=?1",
            params![id],
            |r| r.get(0),
        )
        .map_err(|e| format!("Database error: {e}"))?;

    let mut part_stmt = conn
        .prepare("SELECT id,item_name,make,model,part_number,quantity,remarks,used_at FROM part_usage WHERE service_call_id=?1 ORDER BY used_at DESC,id DESC")
        .map_err(|e| format!("Database error: {e}"))?;
    detail.parts = part_stmt
        .query_map(params![id], |r| {
            Ok(DetailPart {
                id: r.get(0)?,
                item_name: r.get(1)?,
                make: r.get(2)?,
                model: r.get(3)?,
                part_number: r.get(4)?,
                quantity: r.get(5)?,
                remarks: r.get(6)?,
                used_at: r.get(7)?,
            })
        })
        .map_err(|e| format!("Database error: {e}"))?
        .collect::<Result<Vec<_>, _>>()
        .map_err(|e| format!("Database error: {e}"))?;

    let mut event_stmt = conn
        .prepare("SELECT se.id,se.event_type,se.old_value,se.new_value,se.note,COALESCE(u.display_name,'System'),se.created_at FROM service_events se LEFT JOIN users u ON u.id=se.actor_id WHERE se.service_call_id=?1 ORDER BY se.id DESC LIMIT 100")
        .map_err(|e| format!("Database error: {e}"))?;
    detail.events = event_stmt
        .query_map(params![id], |r| {
            Ok(DetailEvent {
                id: r.get(0)?,
                event_type: r.get(1)?,
                old_value: r.get(2)?,
                new_value: r.get(3)?,
                note: r.get(4)?,
                actor: r.get(5)?,
                created_at: r.get(6)?,
            })
        })
        .map_err(|e| format!("Database error: {e}"))?
        .collect::<Result<Vec<_>, _>>()
        .map_err(|e| format!("Database error: {e}"))?;

    Ok(detail)
}

fn collect_history(conn: &Connection, owner_column: &str, owner_id: i64) -> Result<Vec<EntityHistoryEvent>, String> {
    let sql = format!(
        "SELECT se.id,sc.id,sc.service_id,sc.client_name,sc.equipment_name,sc.serial_number,sc.reason,sc.status,
         se.event_type,se.old_value,se.new_value,se.note,COALESCE(u.display_name,'System'),se.created_at
         FROM service_events se
         JOIN service_calls sc ON sc.id=se.service_call_id
         LEFT JOIN users u ON u.id=se.actor_id
         WHERE sc.{}=?1
         ORDER BY se.created_at DESC,se.id DESC LIMIT 500",
        owner_column
    );
    let mut stmt = conn.prepare(&sql).map_err(|e| format!("Database error: {e}"))?;
    let rows = stmt.query_map(params![owner_id], |r| {
        Ok(EntityHistoryEvent {
            id:r.get(0)?,
            service_call_id:r.get(1)?,
            service_id:r.get(2)?,
            client:r.get(3)?,
            equipment:r.get(4)?,
            serial_number:r.get(5)?,
            reason:r.get(6)?,
            service_status:r.get(7)?,
            event_type:r.get(8)?,
            old_value:r.get(9)?,
            new_value:r.get(10)?,
            note:r.get(11)?,
            actor:r.get(12)?,
            created_at:r.get(13)?,
        })
    }).map_err(|e| format!("Database error: {e}"))?;
    rows.collect::<Result<Vec<_>,_>>().map_err(|e| format!("Database error: {e}"))
}

#[tauri::command]
pub fn get_client_history(state: State<'_, AppState>, client_id: i64) -> Result<Vec<EntityHistoryEvent>, String> {
    let _ = require_user(&state)?;
    let db = state.db.lock().map_err(|_| "Database lock failed".to_string())?;
    collect_history(&db, "client_id", client_id)
}

#[tauri::command]
pub fn get_equipment_history(state: State<'_, AppState>, equipment_id: i64) -> Result<Vec<EntityHistoryEvent>, String> {
    let _ = require_user(&state)?;
    let db = state.db.lock().map_err(|_| "Database lock failed".to_string())?;
    collect_history(&db, "equipment_id", equipment_id)
}

#[tauri::command]
pub fn get_service_detail(state: State<'_, AppState>, id: i64) -> Result<ServiceDetailView, String> {
    let _ = require_user(&state)?;
    let db = state.db.lock().map_err(|_| "Database lock failed".to_string())?;
    load_detail(&db, id)
}

#[tauri::command]
pub fn update_service_detail(
    state: State<'_, AppState>,
    draft: UpdateServiceDetailDraft,
) -> Result<ServiceDetailView, String> {
    let actor_id = require_editor(&state)?;
    if !["Open", "In Progress", "Pending", "Closed"].contains(&draft.status.as_str()) {
        return Err("Invalid service status.".into());
    }
    if draft.reason.trim().is_empty() || draft.complaint.trim().is_empty() {
        return Err("Reason and complaint are required.".into());
    }

    let mut db = state.db.lock().map_err(|_| "Database lock failed".to_string())?;
    ensure_schema(&db)?;
    let old_status: String = db
        .query_row("SELECT status FROM service_calls WHERE id=?1", params![draft.id], |r| r.get(0))
        .optional()
        .map_err(|e| format!("Database error: {e}"))?
        .ok_or_else(|| "Service call not found.".to_string())?;
    let now = Local::now().format("%Y-%m-%d %H:%M:%S").to_string();
    let tx = db.transaction().map_err(|e| format!("Database error: {e}"))?;
    tx.execute(
        "UPDATE service_calls SET reason=?1,complaint=?2,engineer=?3,status=?4,priority=?5,service_location=?6,due_date=?7,coverage=?8,foc=?9,quote_status=?10,payment_status=?11,updated_at=?12 WHERE id=?13",
        params![draft.reason.trim(),draft.complaint.trim(),draft.engineer.trim(),draft.status,draft.priority,draft.service_location,draft.due_date,draft.coverage,if draft.foc {1}else{0},draft.quote_status,draft.payment_status,now,draft.id],
    )
    .map_err(|e| format!("Database error: {e}"))?;
    tx.execute(
        r#"INSERT INTO service_details(service_call_id,diagnosis,work_performed,testing_verification,final_result,recommendations,received_condition,received_accessories,received_remarks,completion_date,updated_at)
        VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11)
        ON CONFLICT(service_call_id) DO UPDATE SET diagnosis=excluded.diagnosis,work_performed=excluded.work_performed,
        testing_verification=excluded.testing_verification,final_result=excluded.final_result,recommendations=excluded.recommendations,
        received_condition=excluded.received_condition,received_accessories=excluded.received_accessories,
        received_remarks=excluded.received_remarks,completion_date=excluded.completion_date,updated_at=excluded.updated_at"#,
        params![draft.id,draft.diagnosis.trim(),draft.work_performed.trim(),draft.testing_verification.trim(),draft.final_result.trim(),draft.recommendations.trim(),draft.received_condition.trim(),draft.received_accessories.trim(),draft.received_remarks.trim(),draft.completion_date,now],
    )
    .map_err(|e| format!("Database error: {e}"))?;
    if old_status != draft.status {
        tx.execute(
            "INSERT INTO service_events(service_call_id,event_type,old_value,new_value,note,actor_id,created_at) VALUES(?1,'Status',?2,?3,'Status changed',?4,?5)",
            params![draft.id,old_status,draft.status,actor_id,now],
        )
        .map_err(|e| format!("Database error: {e}"))?;
    }
    tx.execute(
        "INSERT INTO service_events(service_call_id,event_type,note,actor_id,created_at) VALUES(?1,'Updated','Service details updated',?2,?3)",
        params![draft.id,actor_id,now],
    )
    .map_err(|e| format!("Database error: {e}"))?;
    tx.execute(
        "INSERT INTO audit_log(entity,action,record_id,actor_id,summary,created_at) VALUES('ServiceCall','Update',?1,?2,'Service detail updated',?3)",
        params![draft.id.to_string(),actor_id,now],
    )
    .map_err(|e| format!("Database error: {e}"))?;
    tx.commit().map_err(|e| format!("Database error: {e}"))?;
    drop(db);

    let db = state.db.lock().map_err(|_| "Database lock failed".to_string())?;
    load_detail(&db, draft.id)
}

#[tauri::command]
pub fn add_service_part(
    state: State<'_, AppState>,
    draft: AddPartDraft,
) -> Result<ServiceDetailView, String> {
    let actor_id = require_editor(&state)?;
    if draft.item_name.trim().is_empty() {
        return Err("Part / item name is required.".into());
    }
    if draft.quantity < 1 {
        return Err("Quantity must be at least 1.".into());
    }
    let db = state.db.lock().map_err(|_| "Database lock failed".to_string())?;
    let now = Local::now().format("%Y-%m-%d %H:%M:%S").to_string();
    db.execute(
        "INSERT INTO part_usage(service_call_id,item_name,make,model,part_number,quantity,remarks,used_at) VALUES(?1,?2,?3,?4,?5,?6,?7,?8)",
        params![draft.service_call_id,draft.item_name.trim(),draft.make.trim(),draft.model.trim(),draft.part_number.trim(),draft.quantity,draft.remarks.trim(),now],
    )
    .map_err(|e| format!("Database error: {e}"))?;
    db.execute(
        "INSERT INTO service_events(service_call_id,event_type,new_value,note,actor_id,created_at) VALUES(?1,'Part Used',?2,?3,?4,?5)",
        params![draft.service_call_id,draft.item_name.trim(),format!("Quantity {}",draft.quantity),actor_id,now],
    )
    .map_err(|e| format!("Database error: {e}"))?;
    load_detail(&db, draft.service_call_id)
}

#[tauri::command]
pub fn add_service_note(
    state: State<'_, AppState>,
    service_call_id: i64,
    note: String,
) -> Result<ServiceDetailView, String> {
    let actor_id = require_editor(&state)?;
    if note.trim().is_empty() {
        return Err("Enter a note first.".into());
    }
    let db = state.db.lock().map_err(|_| "Database lock failed".to_string())?;
    let now = Local::now().format("%Y-%m-%d %H:%M:%S").to_string();
    db.execute(
        "INSERT INTO service_events(service_call_id,event_type,note,actor_id,created_at) VALUES(?1,'Note',?2,?3,?4)",
        params![service_call_id,note.trim(),actor_id,now],
    )
    .map_err(|e| format!("Database error: {e}"))?;
    load_detail(&db, service_call_id)
}
