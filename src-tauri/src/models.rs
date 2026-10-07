use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct SessionUser {
    pub id: i64,
    pub username: String,
    pub display_name: String,
    pub role: String,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct UserRecord {
    pub id: i64,
    pub username: String,
    pub display_name: String,
    pub role: String,
    pub active: bool,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct SystemStatus {
    pub initialized: bool,
    pub app_version: String,
    pub database_path: String,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ServiceCall {
    pub id: i64,
    pub service_id: String,
    pub opened_date: String,
    pub client: String,
    pub client_id: Option<i64>,
    pub equipment: String,
    pub equipment_id: Option<i64>,
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
    pub last_updated: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ServiceCallDraft {
    pub opened_date: String,
    pub client: String,
    pub contact: Option<String>,
    pub mobile: Option<String>,
    pub email: Option<String>,
    pub equipment: String,
    pub make: Option<String>,
    pub model: Option<String>,
    pub serial_number: Option<String>,
    pub reason: String,
    pub complaint: String,
    pub engineer: Option<String>,
    pub status: String,
    pub priority: String,
    pub service_location: String,
    pub due_date: Option<String>,
    pub coverage: String,
    pub foc: bool,
    pub quote_status: String,
    pub payment_status: String,
    #[serde(default)]
    pub selected_client_id: Option<i64>,
    #[serde(default)]
    pub selected_equipment_id: Option<i64>,
    #[serde(default)]
    pub force_new_client: bool,
    #[serde(default)]
    pub force_new_equipment: bool,
    #[serde(default)]
    pub duplicate_override_password: Option<String>,
    #[serde(default)]
    pub source_intake_id: Option<i64>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct DuplicateClientCandidate {
    pub id: i64,
    pub code: String,
    pub name: String,
    pub contact: String,
    pub mobile: String,
    pub email: String,
    pub service_count: i64,
    pub equipment_count: i64,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct DuplicateEquipmentCandidate {
    pub id: i64,
    pub servix_equipment_id: String,
    pub client_id: i64,
    pub client_name: String,
    pub make: String,
    pub model: String,
    pub serial_number: String,
    pub equipment_type: String,
    pub service_count: i64,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct DuplicateServiceCandidate {
    pub id: i64,
    pub service_id: String,
    pub client: String,
    pub equipment: String,
    pub status: String,
    pub opened_date: String,
    pub complaint: String,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct DuplicateReview {
    pub level: String,
    pub summary: String,
    pub client_candidates: Vec<DuplicateClientCandidate>,
    pub equipment_candidates: Vec<DuplicateEquipmentCandidate>,
    pub open_services: Vec<DuplicateServiceCandidate>,
    pub warnings: Vec<String>,
    pub requires_override: bool,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct CreateUserDraft {
    pub username: String,
    pub display_name: String,
    pub password: String,
    pub role: String,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct IntakeItem {
    pub id: i64,
    pub received_at: String,
    pub client: String,
    pub contact: String,
    pub mobile: String,
    pub email: String,
    pub equipment: String,
    pub make: String,
    pub model: String,
    pub serial_number: String,
    pub complaint: String,
    pub match_summary: String,
    pub match_tone: String,
    pub status: String,
    pub linked_service_id: Option<String>,
    pub original_snapshot: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct IntakeReviewDraft {
    pub id: i64,
    pub client: String,
    pub contact: String,
    pub mobile: String,
    pub email: String,
    pub equipment: String,
    pub make: String,
    pub model: String,
    pub serial_number: String,
    pub complaint: String,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ClientRecord {
    pub id: i64,
    pub code: String,
    pub name: String,
    pub contact: String,
    pub mobile: String,
    pub email: String,
    pub city: String,
    pub state: String,
    pub active: bool,
    pub service_count: i64,
    pub equipment_count: i64,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct EquipmentRecord {
    pub id: i64,
    pub servix_equipment_id: String,
    pub client_id: i64,
    pub client: String,
    pub make: String,
    pub model: String,
    pub serial_number: String,
    pub r#type: String,
    pub location: String,
    pub coverage: String,
    pub service_count: i64,
    pub last_service: String,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct PartUsage {
    pub id: i64,
    pub date: String,
    pub service_id: String,
    pub client: String,
    pub equipment: String,
    pub item_name: String,
    pub make: String,
    pub model: String,
    pub part_number: String,
    pub quantity: i64,
    pub remarks: String,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct SyncStatus {
    pub configured: bool,
    pub last_successful_sync: Option<String>,
    pub last_attempted_sync: Option<String>,
    pub new_count: i64,
    pub status: String,
    pub message: String,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct DashboardData {
    pub services: Vec<ServiceCall>,
    pub intake: Vec<IntakeItem>,
    pub clients: Vec<ClientRecord>,
    pub equipment: Vec<EquipmentRecord>,
    pub part_usage: Vec<PartUsage>,
    pub users: Vec<UserRecord>,
    pub sync: SyncStatus,
}
