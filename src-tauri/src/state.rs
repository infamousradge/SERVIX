use std::{path::PathBuf, sync::Mutex};
use rusqlite::Connection;
use crate::{database, models::SessionUser, service_detail};
pub struct AppState { pub db:Mutex<Connection>, pub session:Mutex<Option<SessionUser>>, pub database_path:PathBuf }
impl AppState {
 pub fn new(database_path:PathBuf)->Result<Self,String>{
  if let Some(parent)=database_path.parent(){std::fs::create_dir_all(parent).map_err(|e|format!("Could not create data directory: {e}"))?;}
  let mut conn=Connection::open(&database_path).map_err(|e|format!("Could not open database: {e}"))?;
  database::initialise(&mut conn)?;
  service_detail::ensure_schema(&conn)?;
  Ok(Self{db:Mutex::new(conn),session:Mutex::new(None),database_path})
 }
}
