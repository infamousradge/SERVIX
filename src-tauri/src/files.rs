use crate::{state::AppState,models::SessionUser};
use chrono::Local;
use rusqlite::{params,Connection};
use serde::{Serialize,Deserialize};
use sha2::{Digest,Sha256};
use std::{fs,path::{Path,PathBuf},time::Duration};
use tauri::State;

const LIMIT:usize=10*1024*1024;
fn err(e:impl std::fmt::Display)->String{format!("File operation failed: {e}")}
fn hash(bytes:&[u8])->String{hex::encode(Sha256::digest(bytes))}
fn user(state:&AppState,admin:bool,edit:bool)->Result<SessionUser,String>{let u=state.session.lock().map_err(err)?.clone().ok_or("Please sign in again.")?;if admin&&u.role!="Administrator"||edit&&u.role=="Read Only"{return Err("You do not have permission for this action.".into())}Ok(u)}
fn root(state:&AppState)->Result<PathBuf,String>{Ok(state.database_path.parent().ok_or("Data folder unavailable")?.join("attachments"))}
fn safe_name(name:&str)->bool{name.len()==64&&name.bytes().all(|b|b.is_ascii_hexdigit())}
fn mime(bytes:&[u8])->Result<&'static str,String>{if bytes.starts_with(b"%PDF-"){Ok("application/pdf")}else if bytes.starts_with(&[137,80,78,71,13,10,26,10]){Ok("image/png")}else if bytes.starts_with(&[255,216,255]){Ok("image/jpeg")}else{Err("Only PDF, PNG and JPEG files are accepted.".into())}}
#[derive(Serialize)]
#[serde(rename_all="camelCase")]
pub struct Document{pub id:i64,pub service_call_id:i64,pub service_id:String,pub client:String,pub equipment:String,pub document_type:String,pub original_name:String,pub mime_type:String,pub size_bytes:i64,pub created_at:String}
#[tauri::command]
pub fn list_documents(state:State<'_,AppState>)->Result<Vec<Document>,String>{user(&state,false,false)?;let db=state.db.lock().map_err(err)?;let mut q=db.prepare("SELECT a.id,a.parent_id,s.service_id,s.client_name,s.equipment_name,a.document_type,a.original_name,a.mime_type,a.size_bytes,a.created_at FROM attachments a JOIN service_calls s ON s.id=a.parent_id WHERE a.parent_type='ServiceCall' ORDER BY a.id DESC").map_err(err)?;let rows=q.query_map([],|r|Ok(Document{id:r.get(0)?,service_call_id:r.get(1)?,service_id:r.get(2)?,client:r.get(3)?,equipment:r.get(4)?,document_type:r.get(5)?,original_name:r.get(6)?,mime_type:r.get(7)?,size_bytes:r.get(8)?,created_at:r.get(9)?})).map_err(err)?;rows.collect::<Result<Vec<_>,_>>().map_err(err)}
#[tauri::command]
pub fn add_document(state:State<'_,AppState>,service_call_id:i64,original_name:String,document_type:String,bytes:Vec<u8>)->Result<(),String>{
 let actor=user(&state,false,true)?;if bytes.is_empty()||bytes.len()>LIMIT{return Err("Each file must be between 1 byte and 10 MB.".into())}let kind=mime(&bytes)?;if original_name.trim().is_empty()||original_name.len()>240{return Err("Invalid filename.".into())}
 if !["Client Letter","Delivery Challan","Condition Photo","Service Report","Certificate","Other"].contains(&document_type.as_str()){return Err("Invalid document category.".into())}
 let mut db=state.db.lock().map_err(err)?;let exists:bool=db.query_row("SELECT EXISTS(SELECT 1 FROM service_calls WHERE id=?1)",[service_call_id],|r|r.get(0)).map_err(err)?;if !exists{return Err("Service Call not found.".into())}
 let folder=root(&state)?;fs::create_dir_all(&folder).map_err(err)?;let name=hash(&bytes);let path=folder.join(&name);if !path.exists(){fs::write(&path,&bytes).map_err(err)?}else if hash(&fs::read(&path).map_err(err)?)!=name{return Err("Stored attachment failed its integrity check.".into())}
 let now=Local::now().format("%Y-%m-%d %H:%M:%S").to_string();let tx=db.transaction().map_err(err)?;
 tx.execute("INSERT INTO attachments(parent_type,parent_id,document_type,stored_path,original_name,mime_type,size_bytes,created_by,created_at) VALUES('ServiceCall',?1,?2,?3,?4,?5,?6,?7,?8)",params![service_call_id,document_type,name,original_name,kind,bytes.len() as i64,actor.id,now]).map_err(err)?;
 tx.execute("INSERT INTO service_events(service_call_id,event_type,note,actor_id,created_at) VALUES(?1,'Document Added',?2,?3,?4)",params![service_call_id,format!("{document_type}: {original_name}"),actor.id,now]).map_err(err)?;tx.commit().map_err(err)?;Ok(())
}
#[tauri::command]
pub fn read_document(state:State<'_,AppState>,id:i64)->Result<Vec<u8>,String>{user(&state,false,false)?;let db=state.db.lock().map_err(err)?;let name:String=db.query_row("SELECT stored_path FROM attachments WHERE id=?1",[id],|r|r.get(0)).map_err(err)?;if !safe_name(&name){return Err("Unsupported attachment path.".into())}let bytes=fs::read(root(&state)?.join(&name)).map_err(err)?;if hash(&bytes)!=name{return Err("Attachment integrity check failed.".into())}Ok(bytes)}

#[derive(Serialize,Deserialize)]
struct FileEntry{name:String,data:String}
#[derive(Serialize,Deserialize)]
struct Package{format:String,version:u32,created_at:String,database:String,database_hash:String,files:Vec<FileEntry>}
#[derive(Serialize)]
#[serde(rename_all="camelCase")]
pub struct RestorePreview{pub path:String,pub checksum:String,pub created_at:String,pub services:i64,pub clients:i64,pub files:usize}
fn snapshot(db:&Connection)->Result<Vec<u8>,String>{let mut target=Connection::open_in_memory().map_err(err)?;rusqlite::backup::Backup::new(db,&mut target).map_err(err)?.run_to_completion(128,Duration::from_millis(10),None).map_err(err)?;
 // VACUUM INTO produces a standalone SQLite file with no WAL dependencies.
 let temp=std::env::temp_dir().join(format!("servix-{}.sqlite",rand::random::<u64>()));let result=(||{target.execute("VACUUM INTO ?1",[temp.to_string_lossy().as_ref()]).map_err(err)?;fs::read(&temp).map_err(err)})();let _=fs::remove_file(temp);result}
fn package(db:&Connection,folder:&Path)->Result<Package,String>{let database=snapshot(db)?;let mut files=Vec::new();let mut stmt=db.prepare("SELECT DISTINCT stored_path FROM attachments").map_err(err)?;let names=stmt.query_map([],|r|r.get::<_,String>(0)).map_err(err)?;for name in names{let name=name.map_err(err)?;if !safe_name(&name){return Err("An attachment has an unsupported storage path.".into())}let bytes=fs::read(folder.join(&name)).map_err(err)?;if hash(&bytes)!=name{return Err("Attachment integrity check failed. Backup was not created.".into())}files.push(FileEntry{name,data:hex::encode(bytes)});}Ok(Package{format:"SERVIX-BACKUP".into(),version:1,created_at:Local::now().to_rfc3339(),database_hash:hash(&database),database:hex::encode(database),files})}
fn save_package(db:&Connection,folder:&Path,destination:&Path)->Result<String,String>{fs::create_dir_all(destination).map_err(err)?;let package=package(db,folder)?;let path=destination.join(format!("SERVIX-{}.servixbackup",Local::now().format("%Y%m%d-%H%M%S-%f")));let pending=path.with_extension("pending");let bytes=serde_json::to_vec(&package).map_err(err)?;fs::write(&pending,bytes).map_err(err)?;fs::rename(&pending,&path).map_err(err)?;Ok(path.to_string_lossy().to_string())}
fn validate(p:&Package)->Result<Connection,String>{if p.format!="SERVIX-BACKUP"||p.version!=1{return Err("Unsupported backup format.".into())}let bytes=hex::decode(&p.database).map_err(err)?;if hash(&bytes)!=p.database_hash{return Err("Backup database checksum failed.".into())}
 let temp=std::env::temp_dir().join(format!("servix-verify-{}.sqlite",rand::random::<u64>()));fs::write(&temp,bytes).map_err(err)?;
 let result=(||{let source=Connection::open_with_flags(&temp,rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY).map_err(err)?;let check:String=source.query_row("PRAGMA integrity_check",[],|r|r.get(0)).map_err(err)?;if check!="ok"{return Err("Backup database integrity check failed.".into())}
 let violations:i64=source.query_row("SELECT COUNT(*) FROM pragma_foreign_key_check",[],|r|r.get(0)).map_err(err)?;if violations!=0{return Err("Backup has broken record links.".into())}
 for table in ["users","clients","equipment","service_calls","service_events","attachments","service_details","settings","audit_log","form_intake","part_usage"]{let found:bool=source.query_row("SELECT EXISTS(SELECT 1 FROM sqlite_master WHERE type='table' AND name=?1)",[table],|r|r.get(0)).map_err(err)?;if !found{return Err(format!("Backup is missing {table}."))}}
 let mut expected=Connection::open_in_memory().map_err(err)?;crate::database::initialise(&mut expected)?;crate::service_detail::ensure_schema(&expected)?;
 let mut tables=expected.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").map_err(err)?;
 let table_names=tables.query_map([],|r|r.get::<_,String>(0)).map_err(err)?.collect::<Result<Vec<_>,_>>().map_err(err)?;
 for table in table_names{let mut columns=expected.prepare("SELECT name FROM pragma_table_info(?1)").map_err(err)?;let names=columns.query_map([&table],|r|r.get::<_,String>(0)).map_err(err)?.collect::<Result<Vec<_>,_>>().map_err(err)?;for column in names{let exists:bool=source.query_row("SELECT EXISTS(SELECT 1 FROM pragma_table_info(?1) WHERE name=?2)",params![table,column],|r|r.get(0)).map_err(err)?;if !exists{return Err(format!("Backup schema is incompatible: {table}.{column} is missing."))}}}
 let mut target=Connection::open_in_memory().map_err(err)?;rusqlite::backup::Backup::new(&source,&mut target).map_err(err)?.run_to_completion(128,Duration::from_millis(10),None).map_err(err)?;
 let mut known=std::collections::HashSet::new();for f in &p.files{if !safe_name(&f.name)||!known.insert(f.name.clone()){return Err("Invalid or duplicate backup attachment.".into())}let bytes=hex::decode(&f.data).map_err(err)?;if bytes.len()>LIMIT||hash(&bytes)!=f.name{return Err("Backup attachment checksum failed.".into())}mime(&bytes)?;}
 let mut q=target.prepare("SELECT stored_path,size_bytes,mime_type FROM attachments").map_err(err)?;let rows=q.query_map([],|r|Ok((r.get::<_,String>(0)?,r.get::<_,i64>(1)?,r.get::<_,String>(2)?))).map_err(err)?;for row in rows{let (name,size,kind)=row.map_err(err)?;let f=p.files.iter().find(|f|f.name==name).ok_or("Backup is missing an attachment.")?;let bytes=hex::decode(&f.data).map_err(err)?;if bytes.len() as i64!=size||mime(&bytes)?!=kind{return Err("Backup attachment metadata mismatch.".into())}}
 drop(q);Ok(target)})();let _=fs::remove_file(temp);result}
fn read_package(path:&str)->Result<(Package,String),String>{let meta=fs::metadata(path).map_err(err)?;if meta.len()>512*1024*1024{return Err("Backup exceeds the 512 MB limit.".into())}let bytes=fs::read(path).map_err(err)?;let checksum=hash(&bytes);Ok((serde_json::from_slice(&bytes).map_err(err)?,checksum))}
#[tauri::command]
pub fn create_backup(state:State<'_,AppState>,destination:String)->Result<String,String>{user(&state,true,false)?;let db=state.db.lock().map_err(err)?;let dest=if destination.trim().is_empty(){state.database_path.parent().ok_or("Data folder unavailable")?.join("backups")}else{let p=PathBuf::from(destination.trim());if !p.is_absolute(){return Err("Enter an absolute backup folder path.".into())}p};save_package(&db,&root(&state)?,&dest)}
#[tauri::command]
pub fn preview_restore(state:State<'_,AppState>,path:String)->Result<RestorePreview,String>{user(&state,true,false)?;let (p,checksum)=read_package(&path)?;let db=validate(&p)?;Ok(RestorePreview{path,checksum,created_at:p.created_at,services:db.query_row("SELECT COUNT(*) FROM service_calls",[],|r|r.get(0)).map_err(err)?,clients:db.query_row("SELECT COUNT(*) FROM clients",[],|r|r.get(0)).map_err(err)?,files:p.files.len()})}
#[tauri::command]
pub fn restore_backup(state:State<'_,AppState>,path:String,checksum:String)->Result<String,String>{user(&state,true,false)?;let (p,current)=read_package(&path)?;if checksum!=current{return Err("Backup changed since preview. Preview it again.".into())}let source=validate(&p)?;let mut db=state.db.lock().map_err(err)?;let folder=root(&state)?;let safety=save_package(&db,&folder,&state.database_path.parent().ok_or("Data folder unavailable")?.join("backups"))?;
 fs::create_dir_all(&folder).map_err(err)?;for f in &p.files{let dest=folder.join(&f.name);let bytes=hex::decode(&f.data).map_err(err)?;if dest.exists(){if hash(&fs::read(&dest).map_err(err)?)!=f.name{return Err("Existing attachment integrity check failed. Live database was not replaced.".into())}}else{fs::write(dest,bytes).map_err(err)?}}
 rusqlite::backup::Backup::new(&source,&mut db).map_err(err)?.run_to_completion(128,Duration::from_millis(10),None).map_err(err)?;db.pragma_update(None,"foreign_keys","ON").map_err(err)?;*state.session.lock().map_err(err)?=None;Ok(format!("Restore completed. Pre-restore backup: {safety}. Sign in with an account from the restored backup."))}

#[cfg(test)]
mod tests{
 use super::*;
 #[test]fn rejects_bad_files_and_paths(){assert!(mime(b"executable").is_err());assert!(!safe_name("../outside"));assert_eq!(mime(b"%PDF-1.7 test").unwrap(),"application/pdf");}
 #[test]fn database_backup_restore_round_trip(){let dir=std::env::temp_dir().join(format!("servix-test-{}",rand::random::<u64>()));fs::create_dir_all(&dir).unwrap();let mut db=Connection::open_in_memory().unwrap();crate::database::initialise(&mut db).unwrap();crate::service_detail::ensure_schema(&db).unwrap();db.execute("INSERT INTO service_calls(service_id,opened_date,client_name,equipment_name,reason,complaint,status,created_at,updated_at) VALUES('TEST-1','2026-10-07','Test Client','Test Device','Repair','Test complaint','Open','2026-10-07','2026-10-07')",[]).unwrap();
 let bytes=b"%PDF-1.7 test attachment";let name=hash(bytes);fs::write(dir.join(&name),bytes).unwrap();db.execute("INSERT INTO attachments(parent_type,parent_id,document_type,stored_path,original_name,mime_type,size_bytes,created_at) VALUES('ServiceCall',1,'Other',?1,'test.pdf','application/pdf',?2,'2026-10-07')",params![name,bytes.len() as i64]).unwrap();
 let p=package(&db,&dir).unwrap();let restored=validate(&p).unwrap();assert_eq!(restored.query_row("SELECT COUNT(*) FROM service_calls",[],|r|r.get::<_,i64>(0)).unwrap(),1);
 let mut destination=Connection::open_in_memory().unwrap();rusqlite::backup::Backup::new(&restored,&mut destination).unwrap().run_to_completion(128,Duration::from_millis(10),None).unwrap();assert_eq!(destination.query_row("SELECT COUNT(*) FROM attachments",[],|r|r.get::<_,i64>(0)).unwrap(),1);
 let backup_path=save_package(&db,&dir,&dir.join("backups")).unwrap();let (saved,_)=read_package(&backup_path).unwrap();assert_eq!(saved.files.len(),1);assert!(validate(&saved).is_ok());
 let mut missing=package(&db,&dir).unwrap();missing.files.clear();assert!(validate(&missing).is_err());
 let mut corrupted=package(&db,&dir).unwrap();corrupted.files[0].data=hex::encode(b"%PDF-1.7 corrupted");assert!(validate(&corrupted).is_err());
 fs::remove_file(dir.join(&name)).unwrap();assert!(package(&db,&dir).is_err());assert_eq!(restored.query_row("PRAGMA integrity_check",[],|r|r.get::<_,String>(0)).unwrap(),"ok");let mut broken=p;broken.database_hash="invalid".into();assert!(validate(&broken).is_err());fs::remove_dir_all(dir).unwrap();}
}

#[tauri::command]
pub fn choose_backup_path(state:State<'_,AppState>,folder:bool)->Result<Option<String>,String>{
 user(&state,true,false)?;
 #[cfg(target_os="windows")]
 {let script=if folder{"Add-Type -AssemblyName System.Windows.Forms; $d=New-Object System.Windows.Forms.FolderBrowserDialog; $d.Description='Choose SERVIX backup folder'; if($d.ShowDialog() -eq 'OK'){[Console]::Write($d.SelectedPath)}"}else{"Add-Type -AssemblyName System.Windows.Forms; $d=New-Object System.Windows.Forms.OpenFileDialog; $d.Filter='SERVIX Backup (*.servixbackup)|*.servixbackup'; if($d.ShowDialog() -eq 'OK'){[Console]::Write($d.FileName)}"};let output=std::process::Command::new("powershell.exe").args(["-NoProfile","-STA","-Command",script]).output().map_err(err)?;if !output.status.success(){return Err("Could not open the Windows file picker. Enter the path manually.".into())}let path=String::from_utf8(output.stdout).map_err(err)?.trim().to_string();Ok(if path.is_empty(){None}else{Some(path)})}
 #[cfg(not(target_os="windows"))]
 {let _=folder;Err("File picker is available on Windows.".into())}
}
