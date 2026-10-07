use crate::{state::AppState,models::SessionUser,security};
use rusqlite::{params,Connection};
use serde::Deserialize;
use tauri::State;
fn err(e:impl std::fmt::Display)->String{format!("Account operation failed: {e}")}
fn actor(state:&AppState)->Result<SessionUser,String>{state.session.lock().map_err(err)?.clone().ok_or("Please sign in again.".into())}
#[derive(Deserialize)]
#[serde(rename_all="camelCase")]
pub struct AccountDraft{pub id:i64,pub display_name:String,pub role:String,pub active:bool,pub password:String}
fn update(db:&mut Connection,u:&SessionUser,d:&AccountDraft)->Result<(),String>{
 if u.role!="Administrator"{return Err("Administrator permission is required.".into())}
 if d.display_name.trim().is_empty()||!["Administrator","Office User","Read Only"].contains(&d.role.as_str()){return Err("Display name and a valid role are required.".into())}
 let tx=db.transaction().map_err(err)?;
 let (old_role,old_active):(String,bool)=tx.query_row("SELECT role,active FROM users WHERE id=?1",[d.id],|r|Ok((r.get(0)?,r.get(1)?))).map_err(err)?;
 if d.id==u.id&&(!d.active||d.role!=u.role){return Err("Use another administrator account to change your own role or deactivate your account.".into())}
 let admins:i64=tx.query_row("SELECT COUNT(*) FROM users WHERE active=1 AND role='Administrator'",[],|r|r.get(0)).map_err(err)?;
 if old_active&&old_role=="Administrator"&&(!d.active||d.role!="Administrator")&&admins<=1{return Err("The last active administrator must be retained.".into())}
 tx.execute("UPDATE users SET display_name=?1,role=?2,active=?3 WHERE id=?4",params![d.display_name.trim(),d.role,d.active,d.id]).map_err(err)?;
 if !d.password.is_empty(){let hash=security::hash_password(&d.password)?;tx.execute("UPDATE users SET password_hash=?1 WHERE id=?2",params![hash,d.id]).map_err(err)?;}
 tx.execute("INSERT INTO audit_log(entity,action,record_id,actor_id,summary,created_at) VALUES('User','Update',?1,?2,?3,datetime('now','localtime'))",params![d.id.to_string(),u.id,format!("Role: {} → {}; active: {} → {}; password reset: {}",old_role,d.role,old_active,d.active,!d.password.is_empty())]).map_err(err)?;
 tx.commit().map_err(err)
}
#[tauri::command]
pub fn update_account(state:State<'_,AppState>,draft:AccountDraft)->Result<(),String>{let u=actor(&state)?;let mut db=state.db.lock().map_err(err)?;update(&mut db,&u,&draft)?;if draft.id==u.id{if let Some(current)=state.session.lock().map_err(err)?.as_mut(){current.display_name=draft.display_name.trim().into()}}Ok(())}
#[tauri::command]
pub fn change_password(state:State<'_,AppState>,current_password:String,new_password:String)->Result<(),String>{let u=actor(&state)?;let mut db=state.db.lock().map_err(err)?;let tx=db.transaction().map_err(err)?;let old:String=tx.query_row("SELECT password_hash FROM users WHERE id=?1 AND active=1",[u.id],|r|r.get(0)).map_err(err)?;if !security::verify_password(&current_password,&old){return Err("Current password is incorrect.".into())}let hash=security::hash_password(&new_password)?;tx.execute("UPDATE users SET password_hash=?1 WHERE id=?2",params![hash,u.id]).map_err(err)?;tx.execute("INSERT INTO audit_log(entity,action,record_id,actor_id,summary,created_at) VALUES('User','Password Changed',?1,?2,'Password changed by account holder',datetime('now','localtime'))",params![u.id.to_string(),u.id]).map_err(err)?;tx.commit().map_err(err)}
#[cfg(test)] mod tests{use super::*;#[test]fn account_safeguards(){let mut db=Connection::open_in_memory().unwrap();crate::database::initialise(&mut db).unwrap();db.execute("INSERT INTO users(id,username,display_name,role,password_hash,created_at) VALUES(1,'admin','Admin','Administrator','hash','today')",[]).unwrap();let u=SessionUser{id:1,username:"admin".into(),display_name:"Admin".into(),role:"Administrator".into()};let mut d=AccountDraft{id:1,display_name:"Admin".into(),role:"Read Only".into(),active:true,password:String::new()};assert!(update(&mut db,&u,&d).is_err());let other=SessionUser{id:2,..u.clone()};assert!(update(&mut db,&other,&d).is_err());d.role="Administrator".into();d.password="weak".into();assert!(update(&mut db,&u,&d).is_err());assert_eq!(db.query_row("SELECT display_name FROM users WHERE id=1",[],|r|r.get::<_,String>(0)).unwrap(),"Admin");d.password="StrongPassword9".into();update(&mut db,&u,&d).unwrap();let hash:String=db.query_row("SELECT password_hash FROM users WHERE id=1",[],|r|r.get(0)).unwrap();assert!(security::verify_password("StrongPassword9",&hash));let audit:String=db.query_row("SELECT summary FROM audit_log ORDER BY id DESC LIMIT 1",[],|r|r.get(0)).unwrap();assert!(!audit.contains("StrongPassword9"));}}
