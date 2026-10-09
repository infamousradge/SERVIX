type DocumentRecord={id:number;serviceCallId:number;serviceId:string;client:string;equipment:string;documentType:string;originalName:string;mimeType:string;sizeBytes:number;createdAt:string};
type RestorePreview={path:string;checksum:string;createdAt:string;services:number;clients:number;files:number};
const FileApi={
 async choose(folder:boolean):Promise<string|null>{return invokeNative('choose_backup_path',{folder})},
 async list():Promise<DocumentRecord[]>{if(!isDesktop)return [];return invokeNative('list_documents')},
 async add(serviceCallId:number,file:File,documentType:string){
  if(!isDesktop)throw new Error('File storage is available in the installed Windows application.');
  if(file.size>10*1024*1024)throw new Error('Maximum upload size is 10 MB.');
  let blob:Blob=file;let name=file.name;
  if(['image/png','image/jpeg'].includes(file.type)){
   const bitmap=await createImageBitmap(file);try{const scale=Math.min(1,1920/Math.max(bitmap.width,bitmap.height));const canvas=document.createElement('canvas');canvas.width=Math.max(1,Math.round(bitmap.width*scale));canvas.height=Math.max(1,Math.round(bitmap.height*scale));const ctx=canvas.getContext('2d');if(!ctx)throw new Error('Image processing unavailable.');ctx.fillStyle='#ffffff';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.drawImage(bitmap,0,0,canvas.width,canvas.height);const compressed=await new Promise<Blob>((resolve,reject)=>canvas.toBlob(b=>b?resolve(b):reject(new Error('Could not compress image.')),'image/jpeg',0.82));if(compressed.size<file.size){blob=compressed;name=file.name.replace(/\.[^.]+$/, '')+'.jpg'}}finally{bitmap.close()}
  }
  await invokeNative('add_document',{serviceCallId,originalName:name,documentType,bytes:Array.from(new Uint8Array(await blob.arrayBuffer()))});
 },
 async read(id:number):Promise<number[]>{return invokeNative('read_document',{id})},
 async backup(destination:string):Promise<string>{if(!isDesktop)throw new Error('Backups are available in the installed Windows application.');return invokeNative('create_backup',{destination})},
 async preview(path:string):Promise<RestorePreview>{if(!isDesktop)throw new Error('Restore is available in the installed Windows application.');return invokeNative('preview_restore',{path})},
 async restore(preview:RestorePreview):Promise<string>{return invokeNative('restore_backup',{path:preview.path,checksum:preview.checksum})}
};
function AttachmentPanel({serviceCallId,onChanged,initialDocumentId}:{serviceCallId:number;onChanged?:()=>void;initialDocumentId?:number}){
 const [rows,setRows]=React.useState([] as DocumentRecord[]);const [category,setCategory]=React.useState('Other');const [busy,setBusy]=React.useState(false);const [error,setError]=React.useState('');const [preview,setPreview]=React.useState(null as {url:string;record:DocumentRecord}|null);
 const refresh=async()=>setRows((await FileApi.list()).filter(x=>x.serviceCallId===serviceCallId));
 React.useEffect(()=>{refresh().catch(e=>setError(String(e)))},[serviceCallId]);
 React.useEffect(()=>()=>{if(preview)URL.revokeObjectURL(preview.url)},[preview]);
 const upload=async(file:File)=>{setBusy(true);setError('');try{await FileApi.add(serviceCallId,file,category);await refresh();if(onChanged)await onChanged()}catch(e:any){setError(e?.message||String(e))}finally{setBusy(false)}};
 const open=async(record:DocumentRecord)=>{setBusy(true);setError('');try{const bytes=await FileApi.read(record.id);setPreview({record,url:URL.createObjectURL(new Blob([new Uint8Array(bytes)],{type:record.mimeType}))})}catch(e:any){setError(e?.message||String(e))}finally{setBusy(false)}};
 React.useEffect(()=>{if(initialDocumentId){FileApi.list().then(items=>{const record=items.find(r=>r.id===initialDocumentId);if(record)return open(record)}).catch(e=>setError(String(e)))}},[initialDocumentId]);
 return <section className="detail-card attachment-panel"><h3>Photos & Documents</h3><p>PDF, PNG or JPEG • maximum 10 MB per upload • photos compressed automatically</p><div className="attachment-toolbar"><select className="filter-select" value={category} onChange={e=>setCategory(e.target.value)}>{['Client Letter','Delivery Challan','Condition Photo','Service Report','Certificate','Other'].map(c=><option key={c}>{c}</option>)}</select><label className="secondary-button">{busy?'Working…':'Add file'}<input type="file" accept="application/pdf,image/png,image/jpeg" disabled={busy} onChange={e=>{const f=e.target.files?.[0];e.target.value='';if(f)upload(f)}}/></label></div>{error&&<div className="form-error">{error}</div>}<div className="profile-list">{rows.map(r=><button type="button" className="profile-list-row document-row" disabled={busy} key={r.id} onClick={()=>open(r)}><span><strong>{r.originalName}</strong><small>{r.documentType+' • '+Math.ceil(r.sizeBytes/1024)+' KB'}</small></span><small>{r.createdAt}</small></button>)}{!rows.length&&<p>No linked files yet.</p>}</div>{preview&&<div className="attachment-preview"><div className="attachment-toolbar"><strong>{preview.record.originalName}</strong><button className="text-button" onClick={()=>setPreview(null)}>Close preview</button></div>{preview.record.mimeType==='application/pdf'?<iframe title={preview.record.originalName} src={preview.url}/>:<img alt={preview.record.originalName} src={preview.url}/>}</div>}</section>;
}
