mod commands;
mod files;
mod database;
mod models;
mod security;
mod service_detail;
mod state;

use tauri::Manager;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            let data_dir = app
                .path()
                .app_data_dir()
                .map_err(|e| std::io::Error::other(format!("Could not determine SERVIX data directory: {e}")))?;
            let state = state::AppState::new(data_dir.join("servix.sqlite3"))
                .map_err(|e| std::io::Error::other(format!("Could not initialise SERVIX: {e}")))?;
            app.manage(state);
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            files::choose_backup_path,
            files::list_documents,
            files::add_document,
            files::read_document,
            files::create_backup,
            files::preview_restore,
            files::restore_backup,
            commands::system_status,
            commands::create_first_admin,
            commands::authenticate,
            commands::logout,
            commands::bootstrap,
            commands::create_service_call,
            commands::review_service_duplicates,
            commands::create_user,
            commands::save_intake_review,
            commands::update_intake_status,
            commands::get_google_sync_config,
            commands::save_google_sync_config,
            commands::sync_google_form,
            commands::load_qa_mock_data,
            service_detail::get_service_detail,
            service_detail::get_client_history,
            service_detail::get_equipment_history,
            service_detail::update_service_detail,
            service_detail::add_service_part,
            service_detail::add_service_note
        ])
        .run(tauri::generate_context!())
        .expect("SERVIX failed to start");
}
