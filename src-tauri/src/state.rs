use std::{path::PathBuf, sync::Mutex};
use rusqlite::Connection;
use crate::{database, models::SessionUser, service_detail};
pub struct AppState { pub db:Mutex<Connection>, pub session:Mutex<Option<SessionUser>>, pub database_path:PathBuf }
impl AppState {
 pub fn new(database_path:PathBuf)->Result<Self,String>{
  if let Some(parent)=database_path.parent(){std::fs::create_dir_all(parent).map_err(|e|format!("Could not create data directory: {e}"))?;}
  let mut conn=Connection::open(&database_path).map_err(|e|format!("Could not open database: {e}"))?;
  let existing:bool=conn.query_row("SELECT EXISTS(SELECT 1 FROM sqlite_master WHERE type='table' AND name='users')",[],|r|r.get(0)).map_err(|e|e.to_string())?;
  let version:i64=conn.query_row("PRAGMA user_version",[],|r|r.get(0)).map_err(|e|e.to_string())?;
  if version>3{return Err("This database requires a newer SERVIX version. Install the newer version to open it safely.".into())}
  if existing&&version<3{crate::files::safety_backup(&conn,&database_path,"pre-upgrade")?;}
  database::initialise(&mut conn)?;
  service_detail::ensure_schema(&conn)?;
  crate::operations::ensure_schema(&conn)?;
  conn.pragma_update(None,"user_version",3).map_err(|e|e.to_string())?;
  let warning=crate::files::automatic_backup(&conn,&database_path).err().unwrap_or_default();
  conn.execute("INSERT INTO settings(key,value,updated_at) VALUES('auto_backup_warning',?1,datetime('now','localtime')) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",[warning]).map_err(|e|e.to_string())?;
  Ok(Self{db:Mutex::new(conn),session:Mutex::new(None),database_path})
 }
}
#[cfg(test)]mod tests{use super::*;#[test]fn upgrade_creates_safety_and_daily_backup(){let folder=std::env::temp_dir().join(format!("servix-upgrade-{}",rand::random::<u64>()));std::fs::create_dir_all(&folder).unwrap();let path=folder.join("servix.sqlite3");{let mut db=Connection::open(&path).unwrap();database::initialise(&mut db).unwrap();service_detail::ensure_schema(&db).unwrap();db.execute("INSERT INTO users(username,display_name,role,password_hash,created_at) VALUES('admin','Admin','Administrator','hash','today')",[]).unwrap();}let state=AppState::new(path.clone()).unwrap();assert_eq!(state.db.lock().unwrap().query_row("PRAGMA user_version",[],|r|r.get::<_,i64>(0)).unwrap(),3);assert_eq!(std::fs::read_dir(folder.join("backups/pre-upgrade")).unwrap().count(),1);assert_eq!(std::fs::read_dir(folder.join("backups/automatic")).unwrap().count(),1);drop(state);let state=AppState::new(path.clone()).unwrap();assert_eq!(std::fs::read_dir(folder.join("backups/pre-upgrade")).unwrap().count(),1);assert_eq!(std::fs::read_dir(folder.join("backups/automatic")).unwrap().count(),1);drop(state);std::fs::remove_dir_all(folder).unwrap();}}
