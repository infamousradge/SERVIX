use crate::{models::SessionUser,state::AppState};
use chrono::Local;
use rusqlite::{params,Connection,OptionalExtension};
use serde::{Deserialize,Serialize};
use sha2::{Digest,Sha256};
use std::{fs,path::{Path,PathBuf},time::Duration};
use tauri::State;

fn err(e:impl std::fmt::Display)->String{format!("SERVIX transfer failed: {e}")}
fn hash(bytes:&[u8])->String{hex::encode(Sha256::digest(bytes))}
fn admin(state:&AppState)->Result<SessionUser,String>{let u=state.session.lock().map_err(err)?.clone().ok_or("Please sign in again.")?;if u.role!="Administrator"{return Err("Administrator permission is required for SERVIX data transfer.".into())}Ok(u)}
fn root(state:&AppState)->Result<PathBuf,String>{Ok(state.database_path.parent().ok_or("Data folder unavailable")?.join("attachments"))}
fn safe_name(s:&str)->bool{!s.is_empty()&&s.len()<=128&&s.chars().all(|c|c.is_ascii_hexdigit())}

#[derive(Serialize,Deserialize,Clone)]
struct FileEntry{name:String,data:String}
#[derive(Serialize,Deserialize)]
#[serde(rename_all="camelCase")]
struct TransferPackage{
 format:String,version:u32,source_installation_id:String,source_name:String,source_app_version:String,
 created_at:String,mode:String,since:String,database:String,database_hash:String,files:Vec<FileEntry>
}
#[derive(Serialize)]
#[serde(rename_all="camelCase")]
pub struct TransferInfo{pub installation_id:String,pub site_name:String,pub last_export:String}
#[derive(Serialize)]
#[serde(rename_all="camelCase")]
pub struct TransferPreview{
 pub path:String,pub checksum:String,pub source_installation_id:String,pub source_name:String,pub created_at:String,pub mode:String,pub since:String,
 pub clients:i64,pub equipment:i64,pub services:i64,pub events:i64,pub files:usize,pub new_records:i64,pub existing_records:i64,pub conflicts:i64
}

fn snapshot(db:&Connection)->Result<Vec<u8>,String>{
 let mut target=Connection::open_in_memory().map_err(err)?;
 rusqlite::backup::Backup::new(db,&mut target).map_err(err)?.run_to_completion(128,Duration::from_millis(10),None).map_err(err)?;
 let temp=std::env::temp_dir().join(format!("servix-transfer-{}.sqlite",rand::random::<u64>()));
 let result=(||{target.execute("VACUUM INTO ?1",[temp.to_string_lossy().as_ref()]).map_err(err)?;fs::read(&temp).map_err(err)})();
 let _=fs::remove_file(temp);result
}
fn package(db:&Connection,folder:&Path,mode:&str,since:&str)->Result<TransferPackage,String>{
 let database=snapshot(db)?;let mut files=Vec::new();
 let mut q=db.prepare("SELECT DISTINCT stored_path FROM attachments").map_err(err)?;
 let names=q.query_map([],|r|r.get::<_,String>(0)).map_err(err)?;
 for n in names{let name=n.map_err(err)?;if !safe_name(&name){return Err("Attachment storage path is invalid.".into())}let bytes=fs::read(folder.join(&name)).map_err(err)?;if hash(&bytes)!=name{return Err("Attachment integrity check failed.".into())}files.push(FileEntry{name,data:hex::encode(bytes)})}
 let setting=|k:&str|db.query_row("SELECT value FROM settings WHERE key=?1",[k],|r|r.get::<_,String>(0)).unwrap_or_default();
 Ok(TransferPackage{format:"SERVIX-DATA-TRANSFER".into(),version:1,source_installation_id:setting("servix_installation_id"),source_name:setting("servix_site_name"),source_app_version:env!("CARGO_PKG_VERSION").into(),created_at:Local::now().to_rfc3339(),mode:mode.into(),since:since.into(),database_hash:hash(&database),database:hex::encode(database),files})
}
fn read_package(path:&str)->Result<(TransferPackage,String),String>{
 let meta=fs::metadata(path).map_err(err)?;if meta.len()>512*1024*1024{return Err("Transfer package exceeds the 512 MB limit.".into())}
 let bytes=fs::read(path).map_err(err)?;let checksum=hash(&bytes);let p:TransferPackage=serde_json::from_slice(&bytes).map_err(err)?;
 if p.format!="SERVIX-DATA-TRANSFER"||p.version!=1{return Err("Unsupported SERVIX transfer package.".into())}
 if p.source_installation_id.trim().is_empty(){return Err("Transfer package has no installation identity.".into())}
 let dbbytes=hex::decode(&p.database).map_err(err)?;if hash(&dbbytes)!=p.database_hash{return Err("Transfer database checksum failed.".into())}
 for f in &p.files{if !safe_name(&f.name){return Err("Transfer contains an invalid attachment reference.".into())}let b=hex::decode(&f.data).map_err(err)?;if hash(&b)!=f.name{return Err("Transfer attachment checksum failed.".into())}}
 Ok((p,checksum))
}
fn source_db(p:&TransferPackage)->Result<(Connection,PathBuf),String>{
 let bytes=hex::decode(&p.database).map_err(err)?;
 let temp=std::env::temp_dir().join(format!("servix-transfer-import-{}.sqlite",rand::random::<u64>()));
 fs::write(&temp,bytes).map_err(err)?;
 let db=Connection::open_with_flags(&temp,rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY).map_err(err)?;
 let check:String=db.query_row("PRAGMA integrity_check",[],|r|r.get(0)).map_err(err)?;if check!="ok"{let _=fs::remove_file(&temp);return Err("Transfer database integrity check failed.".into())}
 Ok((db,temp))
}
fn counts(db:&Connection)->Result<(i64,i64,i64,i64),String>{Ok((
 db.query_row("SELECT COUNT(*) FROM clients",[],|r|r.get(0)).map_err(err)?,
 db.query_row("SELECT COUNT(*) FROM equipment",[],|r|r.get(0)).map_err(err)?,
 db.query_row("SELECT COUNT(*) FROM service_calls",[],|r|r.get(0)).map_err(err)?,
 db.query_row("SELECT COUNT(*) FROM service_events",[],|r|r.get(0)).map_err(err)?
))}
fn assess(target:&Connection,source:&Connection)->Result<(i64,i64,i64),String>{
 let mut newn=0;let mut existing=0;let mut conflicts=0;
 for (table,column) in [("clients","code"),("equipment","servix_equipment_id"),("service_calls","service_id")]{
  let mut q=source.prepare(&format!("SELECT {column} FROM {table}")).map_err(err)?;
  for v in q.query_map([],|r|r.get::<_,String>(0)).map_err(err)?{let v=v.map_err(err)?;let exists:bool=target.query_row(&format!("SELECT EXISTS(SELECT 1 FROM {table} WHERE lower({column})=lower(?1))"),[&v],|r|r.get(0)).map_err(err)?;if exists{existing+=1;if table=="service_calls"{conflicts+=1}}else{newn+=1}}
 }
 Ok((newn,existing,conflicts))
}

#[tauri::command]
pub fn transfer_info(state:State<'_,AppState>)->Result<TransferInfo,String>{admin(&state)?;let db=state.db.lock().map_err(err)?;let get=|k:&str|db.query_row("SELECT value FROM settings WHERE key=?1",[k],|r|r.get::<_,String>(0)).unwrap_or_default();Ok(TransferInfo{installation_id:get("servix_installation_id"),site_name:get("servix_site_name"),last_export:get("servix_last_transfer_export")})}

#[tauri::command]
pub fn save_transfer_site(state:State<'_,AppState>,site_name:String)->Result<TransferInfo,String>{let u=admin(&state)?;let name=site_name.trim();if name.is_empty()||name.len()>80{return Err("Enter an office / site name up to 80 characters.".into())}let db=state.db.lock().map_err(err)?;let now=Local::now().to_rfc3339();db.execute("UPDATE settings SET value=?1,updated_at=?2 WHERE key='servix_site_name'",params![name,now]).map_err(err)?;db.execute("INSERT INTO audit_log(entity,action,actor_id,summary,created_at) VALUES('Transfer','Site',?1,?2,datetime('now','localtime'))",params![u.id,format!("Transfer site name set to {name}")]).map_err(err)?;drop(db);transfer_info(state)}

#[tauri::command]
pub fn choose_transfer_path(state:State<'_,AppState>,folder:bool)->Result<Option<String>,String>{
 admin(&state)?;
 #[cfg(target_os="windows")]
 {let script=if folder{"Add-Type -AssemblyName System.Windows.Forms; $d=New-Object System.Windows.Forms.FolderBrowserDialog; $d.Description='Choose SERVIX transfer folder'; if($d.ShowDialog() -eq 'OK'){[Console]::Write($d.SelectedPath)}"}else{"Add-Type -AssemblyName System.Windows.Forms; $d=New-Object System.Windows.Forms.OpenFileDialog; $d.Filter='SERVIX Data Transfer (*.servixdata)|*.servixdata'; if($d.ShowDialog() -eq 'OK'){[Console]::Write($d.FileName)}"};let o=std::process::Command::new("powershell.exe").args(["-NoProfile","-STA","-Command",script]).output().map_err(err)?;if !o.status.success(){return Err("Could not open the Windows file picker.".into())}let s=String::from_utf8(o.stdout).map_err(err)?.trim().to_string();Ok(if s.is_empty(){None}else{Some(s)})}
 #[cfg(not(target_os="windows"))]{let _=folder;Err("File picker is available on Windows.".into())}
}

#[tauri::command]
pub fn export_servix_transfer(state:State<'_,AppState>,destination:String,mode:String)->Result<String,String>{
 let u=admin(&state)?;if !["full","incremental"].contains(&mode.as_str()){return Err("Invalid transfer mode.".into())}
 let dest=PathBuf::from(destination.trim());if !dest.is_absolute(){return Err("Choose an absolute transfer folder.".into())}
 let db=state.db.lock().map_err(err)?;let site:String=db.query_row("SELECT value FROM settings WHERE key='servix_site_name'",[],|r|r.get(0)).unwrap_or_default();if site.trim().is_empty(){return Err("Set the office / site name before creating a transfer package.".into())}
 let since=if mode=="incremental"{db.query_row("SELECT value FROM settings WHERE key='servix_last_transfer_export'",[],|r|r.get::<_,String>(0)).unwrap_or_default()}else{String::new()};
 let p=package(&db,&root(&state)?,&mode,&since)?;fs::create_dir_all(&dest).map_err(err)?;
 let filename=format!("SERVIX-{}-{}-{}.servixdata",site.chars().map(|c|if c.is_ascii_alphanumeric(){c}else{'-'}).collect::<String>(),if mode=="full"{"FULL"}else{"CHANGES"},Local::now().format("%Y%m%d-%H%M%S"));
 let path=dest.join(filename);let pending=path.with_extension("pending");let bytes=serde_json::to_vec(&p).map_err(err)?;fs::write(&pending,&bytes).map_err(err)?;fs::rename(&pending,&path).map_err(err)?;
 let now=Local::now().to_rfc3339();db.execute("UPDATE settings SET value=?1,updated_at=?1 WHERE key='servix_last_transfer_export'",[&now]).map_err(err)?;
 db.execute("INSERT INTO servix_transfer_log(direction,source_installation_id,source_name,package_hash,mode,created_at) VALUES('Export',?1,?2,?3,?4,?5)",params![p.source_installation_id,p.source_name,hash(&bytes),mode,now]).map_err(err)?;
 db.execute("INSERT INTO audit_log(entity,action,actor_id,summary,created_at) VALUES('Transfer','Export',?1,?2,datetime('now','localtime'))",params![u.id,path.to_string_lossy().to_string()]).map_err(err)?;
 Ok(path.to_string_lossy().to_string())
}

#[tauri::command]
pub fn preview_servix_transfer(state:State<'_,AppState>,path:String)->Result<TransferPreview,String>{
 admin(&state)?;let (p,checksum)=read_package(&path)?;let (src,temp)=source_db(&p)?;let (clients,equipment,services,events)=counts(&src)?;
 let db=state.db.lock().map_err(err)?;let (new_records,existing_records,conflicts)=assess(&db,&src)?;drop(db);drop(src);let _=fs::remove_file(temp);
 Ok(TransferPreview{path,checksum,source_installation_id:p.source_installation_id,source_name:p.source_name,created_at:p.created_at,mode:p.mode,since:p.since,clients,equipment,services,events,files:p.files.len(),new_records,existing_records,conflicts})
}

fn target_id(db:&Connection,table:&str,column:&str,value:&str)->Result<Option<i64>,String>{db.query_row(&format!("SELECT id FROM {table} WHERE {column}=?1 COLLATE NOCASE"),[value],|r|r.get(0)).optional().map_err(err)}

#[tauri::command]
pub fn import_servix_transfer(state:State<'_,AppState>,path:String,checksum:String)->Result<String,String>{
 let u=admin(&state)?;let (p,current)=read_package(&path)?;if current!=checksum{return Err("Transfer package changed after preview. Preview it again.".into())}
 let (src,temp)=source_db(&p)?;let mut db=state.db.lock().map_err(err)?;
 let safety=crate::files::safety_backup(&db,&state.database_path,"pre-transfer-import")?;
 let folder=root(&state)?;fs::create_dir_all(&folder).map_err(err)?;
 for f in &p.files{let bytes=hex::decode(&f.data).map_err(err)?;let dest=folder.join(&f.name);if !dest.exists(){fs::write(dest,bytes).map_err(err)?}}
 let tx=db.transaction().map_err(err)?;let mut newn=0_i64;let mut existing=0_i64;let mut conflicts=0_i64;
 // Clients
 {let mut q=src.prepare("SELECT code,name,contact,mobile,email,address,city,state,active,created_at,updated_at FROM clients ORDER BY id").map_err(err)?;
 for row in q.query_map([],|r|Ok((r.get::<_,String>(0)?,r.get::<_,String>(1)?,r.get::<_,String>(2)?,r.get::<_,String>(3)?,r.get::<_,String>(4)?,r.get::<_,String>(5)?,r.get::<_,String>(6)?,r.get::<_,String>(7)?,r.get::<_,i64>(8)?,r.get::<_,String>(9)?,r.get::<_,String>(10)?))).map_err(err)?{let (code,name,contact,mobile,email,address,city,state,active,created,updated)=row.map_err(err)?;if target_id(&tx,"clients","code",&code)?.is_some(){existing+=1;continue}tx.execute("INSERT INTO clients(code,name,contact,mobile,email,address,city,state,active,created_at,updated_at) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11)",params![code,name,contact,mobile,email,address,city,state,active,created,updated]).map_err(err)?;newn+=1;}}}
 // Equipment
 {let mut q=src.prepare("SELECT e.servix_equipment_id,c.code,e.make,e.model,e.serial_number,e.equipment_type,e.location,e.coverage,e.warranty_until,e.amc_until,e.cmc_until,e.active,e.created_at,e.updated_at FROM equipment e LEFT JOIN clients c ON c.id=e.client_id ORDER BY e.id").map_err(err)?;
 for row in q.query_map([],|r|Ok((r.get::<_,String>(0)?,r.get::<_,Option<String>>(1)?.unwrap_or_default(),r.get::<_,String>(2)?,r.get::<_,String>(3)?,r.get::<_,String>(4)?,r.get::<_,String>(5)?,r.get::<_,String>(6)?,r.get::<_,String>(7)?,r.get::<_,String>(8)?,r.get::<_,String>(9)?,r.get::<_,String>(10)?,r.get::<_,i64>(11)?,r.get::<_,String>(12)?,r.get::<_,String>(13)?))).map_err(err)?{let (eid,ccode,make,model,serial,kind,loc,cov,warr,amc,cmc,active,created,updated)=row.map_err(err)?;if target_id(&tx,"equipment","servix_equipment_id",&eid)?.is_some(){existing+=1;continue}let cid=target_id(&tx,"clients","code",&ccode)?;tx.execute("INSERT INTO equipment(servix_equipment_id,client_id,make,model,serial_number,equipment_type,location,coverage,warranty_until,amc_until,cmc_until,active,created_at,updated_at) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,?13,?14)",params![eid,cid,make,model,serial,kind,loc,cov,warr,amc,cmc,active,created,updated]).map_err(err)?;newn+=1;}}}
 // Engineers
 {let mut q=src.prepare("SELECT name,contact,active,skills,coverage_area FROM engineers ORDER BY id").map_err(err)?;for row in q.query_map([],|r|Ok((r.get::<_,String>(0)?,r.get::<_,String>(1)?,r.get::<_,i64>(2)?,r.get::<_,String>(3)?,r.get::<_,String>(4)?))).map_err(err)?{let (name,contact,active,skills,area)=row.map_err(err)?;let exists:bool=tx.query_row("SELECT EXISTS(SELECT 1 FROM engineers WHERE lower(name)=lower(?1) AND contact=?2)",params![name,contact],|r|r.get(0)).map_err(err)?;if !exists{tx.execute("INSERT INTO engineers(name,contact,active,skills,coverage_area) VALUES(?1,?2,?3,?4,?5)",params![name,contact,active,skills,area]).map_err(err)?;newn+=1}else{existing+=1}}}
 // Service calls and linked detail tables
 {let mut q=src.prepare("SELECT sc.service_id,sc.opened_date,c.code,e.servix_equipment_id,sc.client_name,sc.equipment_name,sc.make,sc.model,sc.serial_number,sc.reason,sc.complaint,sc.engineer,sc.status,sc.priority,sc.service_location,sc.due_date,sc.coverage,sc.foc,sc.quote_status,sc.payment_status,sc.created_at,sc.updated_at FROM service_calls sc LEFT JOIN clients c ON c.id=sc.client_id LEFT JOIN equipment e ON e.id=sc.equipment_id ORDER BY sc.id").map_err(err)?;
 for row in q.query_map([],|r|Ok((r.get::<_,String>(0)?,r.get::<_,String>(1)?,r.get::<_,Option<String>>(2)?.unwrap_or_default(),r.get::<_,Option<String>>(3)?.unwrap_or_default(),r.get::<_,String>(4)?,r.get::<_,String>(5)?,r.get::<_,String>(6)?,r.get::<_,String>(7)?,r.get::<_,String>(8)?,r.get::<_,String>(9)?,r.get::<_,String>(10)?,r.get::<_,String>(11)?,r.get::<_,String>(12)?,r.get::<_,String>(13)?,r.get::<_,String>(14)?,r.get::<_,String>(15)?,r.get::<_,String>(16)?,r.get::<_,i64>(17)?,r.get::<_,String>(18)?,r.get::<_,String>(19)?,r.get::<_,String>(20)?,r.get::<_,String>(21)?))).map_err(err)?{
  let (sid,opened,ccode,eid,cname,ename,make,model,serial,reason,complaint,engineer,status,priority,location,due,cov,foc,quote,payment,created,updated)=row.map_err(err)?;
  if let Some(existing_id)=target_id(&tx,"service_calls","service_id",&sid)?{let _=existing_id;existing+=1;conflicts+=1;continue}
  let cid=target_id(&tx,"clients","code",&ccode)?;let eqid=target_id(&tx,"equipment","servix_equipment_id",&eid)?;
  tx.execute("INSERT INTO service_calls(service_id,opened_date,client_id,equipment_id,client_name,equipment_name,make,model,serial_number,reason,complaint,engineer,status,priority,service_location,due_date,coverage,foc,quote_status,payment_status,created_by,created_at,updated_at) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,?13,?14,?15,?16,?17,?18,?19,?20,?21,?22,?23)",params![sid,opened,cid,eqid,cname,ename,make,model,serial,reason,complaint,engineer,status,priority,location,due,cov,foc,quote,payment,u.id,created,updated]).map_err(err)?;
  let new_service_id=tx.last_insert_rowid();let old_service_id:i64=src.query_row("SELECT id FROM service_calls WHERE service_id=?1",[&sid],|r|r.get(0)).map_err(err)?;
  if let Some((diag,work,test,result,reco,rc,ra,rr,complete,dupd))=src.query_row("SELECT diagnosis,work_performed,testing_verification,final_result,recommendations,received_condition,received_accessories,received_remarks,completion_date,updated_at FROM service_details WHERE service_call_id=?1",[old_service_id],|r|Ok((r.get::<_,String>(0)?,r.get::<_,String>(1)?,r.get::<_,String>(2)?,r.get::<_,String>(3)?,r.get::<_,String>(4)?,r.get::<_,String>(5)?,r.get::<_,String>(6)?,r.get::<_,String>(7)?,r.get::<_,String>(8)?,r.get::<_,String>(9)?))).optional().map_err(err)?{tx.execute("INSERT INTO service_details(service_call_id,diagnosis,work_performed,testing_verification,final_result,recommendations,received_condition,received_accessories,received_remarks,completion_date,updated_at) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11)",params![new_service_id,diag,work,test,result,reco,rc,ra,rr,complete,dupd]).map_err(err)?}
  if let Some((sr,fd))=src.query_row("SELECT status_reason,follow_up_date FROM service_followups WHERE service_call_id=?1",[old_service_id],|r|Ok((r.get::<_,String>(0)?,r.get::<_,String>(1)?))).optional().map_err(err)?{tx.execute("INSERT INTO service_followups(service_call_id,status_reason,follow_up_date) VALUES(?1,?2,?3)",params![new_service_id,sr,fd]).map_err(err)?}
  {let mut qe=src.prepare("SELECT event_type,old_value,new_value,note,created_at FROM service_events WHERE service_call_id=?1 ORDER BY id").map_err(err)?;for ev in qe.query_map([old_service_id],|r|Ok((r.get::<_,String>(0)?,r.get::<_,String>(1)?,r.get::<_,String>(2)?,r.get::<_,String>(3)?,r.get::<_,String>(4)?))).map_err(err)?{let (et,ov,nv,note,at)=ev.map_err(err)?;tx.execute("INSERT INTO service_events(service_call_id,event_type,old_value,new_value,note,actor_id,created_at) VALUES(?1,?2,?3,?4,?5,?6,?7)",params![new_service_id,et,ov,nv,note,u.id,at]).map_err(err)?}}
  {let mut qp=src.prepare("SELECT item_name,make,model,part_number,quantity,remarks,used_at FROM part_usage WHERE service_call_id=?1 ORDER BY id").map_err(err)?;for pr in qp.query_map([old_service_id],|r|Ok((r.get::<_,String>(0)?,r.get::<_,String>(1)?,r.get::<_,String>(2)?,r.get::<_,String>(3)?,r.get::<_,i64>(4)?,r.get::<_,String>(5)?,r.get::<_,String>(6)?))).map_err(err)?{let (item,pmake,pmodel,pn,qty,remarks,used)=pr.map_err(err)?;tx.execute("INSERT INTO part_usage(service_call_id,item_name,make,model,part_number,quantity,remarks,used_at) VALUES(?1,?2,?3,?4,?5,?6,?7,?8)",params![new_service_id,item,pmake,pmodel,pn,qty,remarks,used]).map_err(err)?}}
  if let Some((cd,cert,res,next,notes))=src.query_row("SELECT calibration_date,certificate,result,next_due,notes FROM calibration_records WHERE service_call_id=?1",[old_service_id],|r|Ok((r.get::<_,String>(0)?,r.get::<_,String>(1)?,r.get::<_,String>(2)?,r.get::<_,String>(3)?,r.get::<_,String>(4)?))).optional().map_err(err)?{tx.execute("INSERT INTO calibration_records(service_call_id,calibration_date,certificate,result,next_due,notes) VALUES(?1,?2,?3,?4,?5,?6)",params![new_service_id,cd,cert,res,next,notes]).map_err(err)?}
  if let Some(cp)=src.query_row("SELECT status FROM calibration_progress WHERE service_call_id=?1",[old_service_id],|r|r.get::<_,String>(0)).optional().map_err(err)?{tx.execute("INSERT INTO calibration_progress(service_call_id,status) VALUES(?1,?2)",params![new_service_id,cp]).map_err(err)?}
  {let mut qa=src.prepare("SELECT document_type,stored_path,original_name,mime_type,size_bytes,caption,created_at FROM attachments WHERE parent_type='ServiceCall' AND parent_id=?1 ORDER BY id").map_err(err)?;for ar in qa.query_map([old_service_id],|r|Ok((r.get::<_,String>(0)?,r.get::<_,String>(1)?,r.get::<_,String>(2)?,r.get::<_,String>(3)?,r.get::<_,i64>(4)?,r.get::<_,String>(5)?,r.get::<_,String>(6)?))).map_err(err)?{let (dt,sp,on,mime,size,cap,at)=ar.map_err(err)?;tx.execute("INSERT INTO attachments(parent_type,parent_id,document_type,stored_path,original_name,mime_type,size_bytes,caption,created_by,created_at) VALUES('ServiceCall',?1,?2,?3,?4,?5,?6,?7,?8,?9)",params![new_service_id,dt,sp,on,mime,size,cap,u.id,at]).map_err(err)?}}
  newn+=1;
 }}
 // Incoming requests remain source-distinct by external_id; collisions are skipped.
 {let mut q=src.prepare("SELECT external_id,received_at,client_name,contact,mobile,email,equipment,make,model,serial_number,complaint,raw_json,match_summary,match_tone,status,linked_service_id,processed_at,rejection_reason FROM form_intake ORDER BY id").map_err(err)?;
 for row in q.query_map([],|r|Ok((r.get::<_,String>(0)?,r.get::<_,String>(1)?,r.get::<_,String>(2)?,r.get::<_,String>(3)?,r.get::<_,String>(4)?,r.get::<_,String>(5)?,r.get::<_,String>(6)?,r.get::<_,String>(7)?,r.get::<_,String>(8)?,r.get::<_,String>(9)?,r.get::<_,String>(10)?,r.get::<_,String>(11)?,r.get::<_,String>(12)?,r.get::<_,String>(13)?,r.get::<_,String>(14)?,r.get::<_,Option<String>>(15)?,r.get::<_,Option<String>>(16)?,r.get::<_,String>(17)?))).map_err(err)?{let (ext,received,client,contact,mobile,email,equipment,make,model,serial,complaint,raw,ms,mt,status,linked,processed,rejection)=row.map_err(err)?;let exists:bool=tx.query_row("SELECT EXISTS(SELECT 1 FROM form_intake WHERE external_id=?1)",[&ext],|r|r.get(0)).map_err(err)?;if !exists{tx.execute("INSERT INTO form_intake(external_id,received_at,client_name,contact,mobile,email,equipment,make,model,serial_number,complaint,raw_json,match_summary,match_tone,status,linked_service_id,processed_by,processed_at,rejection_reason) VALUES(?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,?13,?14,?15,?16,?17,?18,?19)",params![ext,received,client,contact,mobile,email,equipment,make,model,serial,complaint,raw,ms,mt,status,linked,u.id,processed,rejection]).map_err(err)?;newn+=1}else{existing+=1}}}
 tx.execute("INSERT INTO servix_transfer_log(direction,source_installation_id,source_name,package_hash,mode,new_records,existing_records,conflicts,created_at) VALUES('Import',?1,?2,?3,?4,?5,?6,?7,datetime('now','localtime'))",params![p.source_installation_id,p.source_name,current,p.mode,newn,existing,conflicts]).map_err(err)?;
 tx.execute("INSERT INTO audit_log(entity,action,actor_id,summary,created_at) VALUES('Transfer','Import',?1,?2,datetime('now','localtime'))",params![u.id,format!("{}: {} new, {} existing, {} conflicts",p.source_name,newn,existing,conflicts)]).map_err(err)?;
 tx.commit().map_err(err)?;drop(db);drop(src);let _=fs::remove_file(temp);
 Ok(format!("Imported from {}. {} new records, {} existing skipped, {} Service ID conflicts skipped. Safety backup: {}",if p.source_name.trim().is_empty(){p.source_installation_id}else{p.source_name},newn,existing,conflicts,safety))
}

#[tauri::command]
pub fn transfer_history(state:State<'_,AppState>)->Result<Vec<serde_json::Value>,String>{admin(&state)?;let db=state.db.lock().map_err(err)?;let mut q=db.prepare("SELECT id,direction,source_installation_id,source_name,mode,new_records,existing_records,conflicts,created_at FROM servix_transfer_log ORDER BY id DESC LIMIT 50").map_err(err)?;let rows=q.query_map([],|r|Ok(serde_json::json!({"id":r.get::<_,i64>(0)?,"direction":r.get::<_,String>(1)?,"installationId":r.get::<_,String>(2)?,"sourceName":r.get::<_,String>(3)?,"mode":r.get::<_,String>(4)?,"newRecords":r.get::<_,i64>(5)?,"existingRecords":r.get::<_,i64>(6)?,"conflicts":r.get::<_,i64>(7)?,"createdAt":r.get::<_,String>(8)?}))).map_err(err)?;rows.collect::<Result<Vec<_>,_>>().map_err(err)}
