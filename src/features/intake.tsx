function intakeSnapshot(item:IntakeItem){
 try{return JSON.parse(item.originalSnapshot||'{}') as Record<string,any>}catch{return {'Original submission':item.originalSnapshot||'Snapshot unavailable'}}
}
function intakeReason(item:IntakeItem){
 const s=intakeSnapshot(item);
 const raw=String(s['Reason for Sending']||s['Service Reason']||s.reason||'').toLowerCase();
 if(raw.includes('calib'))return 'Calibration';
 if(raw.includes('prevent'))return 'Preventive Service';
 if(raw.includes('install')||raw.includes('commission'))return 'Installation / Commissioning';
 if(raw.includes('inspect'))return 'Inspection';
 if(raw.includes('repair')||raw.includes('break'))return 'Repair';
 return 'Repair';
}
function IntakeView({data,onRefresh,onSync,user,initialId}:{data:DashboardData,onRefresh:()=>void,onSync:()=>void,user:SessionUser,initialId?:number}){
 const [tab,setTab]=React.useState('Pending'); const [search,setSearch]=React.useState('');
 const [selected,setSelected]=React.useState(null as IntakeItem|null); const [draft,setDraft]=React.useState(null as IntakeReviewDraft|null);
 const [convertItem,setConvertItem]=React.useState(null as IntakeItem|null); const [busy,setBusy]=React.useState(false); const [error,setError]=React.useState('');
 const tabs=['Pending','New','Reviewed','Converted','Duplicate'];
 const rows=data.intake.filter(x=>(tab==='Pending'?(x.status==='New'||x.status==='Reviewed'):x.status===tab)&&((x.client+' '+x.contact+' '+x.mobile+' '+x.email+' '+x.make+' '+x.model+' '+x.equipment+' '+x.serialNumber+' '+x.complaint).toLowerCase().includes(search.toLowerCase())));
 const openItem=(x:IntakeItem)=>{setSelected(x);setDraft({id:x.id,client:x.client,contact:x.contact,mobile:x.mobile,email:x.email,equipment:x.equipment,make:x.make,model:x.model,serialNumber:x.serialNumber,complaint:x.complaint});setError('')};
 React.useEffect(()=>{if(initialId){const item=data.intake.find(x=>x.id===initialId);if(item)openItem(item)}},[initialId]);
 const set=(k:keyof IntakeReviewDraft,v:any)=>setDraft(d=>d?({...d,[k]:v}):d);
 const saveReview=async()=>{if(!draft||!selected)return;setBusy(true);setError('');try{await ServixApi.saveIntakeReview(draft);await onRefresh();setSelected({...selected,...draft,status:selected.status==='Converted'?'Converted':'Reviewed'}); }catch(e:any){setError(e?.message||String(e))}finally{setBusy(false)}};
 const markDuplicate=async()=>{if(!selected)return;setBusy(true);setError('');try{await ServixApi.updateIntakeStatus(selected.id,'Duplicate');await onRefresh();setSelected({...selected,status:'Duplicate'})}catch(e:any){setError(e?.message||String(e))}finally{setBusy(false)}};
 const beginConvert=()=>{if(!selected||!draft)return;const item={...selected,...draft,status:'Reviewed'} as IntakeItem;setSelected(null);setConvertItem(item)};
 const closeReview=()=>{if(!busy){setSelected(null);setDraft(null);setError('')}};
 const snapshot=selected?intakeSnapshot(selected):{};
 const editable=!!selected&&user.role!=='Read Only'&&(selected.status==='New'||user.role==='Administrator');
 const conversionDraft=convertItem?{client:convertItem.client,contact:convertItem.contact,mobile:convertItem.mobile,email:convertItem.email,equipment:convertItem.equipment,make:convertItem.make,model:convertItem.model,serialNumber:convertItem.serialNumber,complaint:convertItem.complaint,reason:intakeReason(convertItem),sourceIntakeId:convertItem.id}:null;
 return <div className="module-content"><PageHeader title="Incoming Requests" subtitle="Google Form intake queue — review the original submission before creating an official Service ID" actions={<button className="secondary-button" onClick={onSync}><Icon name="refresh"/> Sync Now</button>}/>
  <Toolbar><SearchBox value={search} onChange={setSearch} placeholder="Search client, equipment, serial or complaint..."/><div className="tab-strip">{tabs.map(t=><button className={'intake-tab status-'+t.toLowerCase()+(tab===t?' active':'')} onClick={()=>setTab(t)} key={t}>{t} <span>{t==='Pending'?data.intake.filter(x=>x.status==='New'||x.status==='Reviewed').length:data.intake.filter(x=>x.status===t).length}</span></button>)}</div></Toolbar>
  <div className="results-summary"><span><strong>{rows.length}</strong> matching requests</span><span>Last sync: {data.sync.lastSuccessfulSync||'Not synced'}</span></div>
  <section className="intake-card-list">{rows.map(x=><article className={'intake-request-card status-'+x.status.toLowerCase()} key={x.id}>
   <div className="intake-card-top"><span className="intake-received"><Icon name="intake" size={18}/> {x.receivedAt}</span><StatusBadge value={x.status}/></div>
   <div className="intake-client-line"><h3>{x.client}</h3><span className={'match-text '+x.matchTone}>{x.matchSummary}</span></div>
   <div className="intake-contact-line"><span><small>Contact person</small><strong>{x.contact||'—'}</strong></span><span><small>Mobile</small><strong>{x.mobile||'—'}</strong></span><span className="intake-email"><small>Email</small><strong>{x.email||'—'}</strong></span></div>
   <div className="intake-device-line"><Icon name="equipment" size={20}/><span><small>Make / Model / Serial number</small><strong>{[x.make,x.model,x.serialNumber?'S/N '+x.serialNumber:''].filter(Boolean).join(' • ')||x.equipment}</strong></span><span className="soft-chip">{x.equipment}</span></div>
   <div className="intake-complaint"><small>Complaint / Requirement</small><p>{x.complaint}</p></div>
   <div className="intake-card-footer"><span>{x.linkedServiceId?'Linked: '+x.linkedServiceId:'Incoming #'+x.id}</span><button className="secondary-button" onClick={()=>openItem(x)}><Icon name="chevron" size={17}/>{x.status==='New'?'Review Request':'View / Review'}</button></div>
  </article>)}{!rows.length&&<EmptyState title="No matching requests" detail="Try another filter or sync for new Google Form submissions."/>}</section>
  {selected&&draft&&<Modal title={selected.status==='New'?'Review Incoming Request':'Incoming Request'} subtitle={'Received '+selected.receivedAt+' • Original submission remains preserved'} onClose={closeReview} wide className="intake-review-modal" footer={<>{editable&&selected.status!=='Converted'&&<button className="secondary-button" disabled={busy} onClick={markDuplicate}>Mark Duplicate</button>}<button className="secondary-button" disabled={busy} onClick={closeReview}>Close</button>{editable&&<button className="secondary-button" disabled={busy} onClick={saveReview}>{busy?'Saving…':selected.status==='New'?'Save & Mark Reviewed':'Save Administrator Correction'}</button>}{selected.status==='Reviewed'&&user.role!=='Read Only'&&<button className="primary-button" disabled={busy} onClick={beginConvert}>Create Service Call</button>}</>}>
   {error&&<div className="form-error">{error}</div>}
   <div className="intake-review-summary"><div><span>Match Result</span><strong className={'match-text '+selected.matchTone}>{selected.matchSummary||'No match result'}</strong></div><div><span>Status</span><StatusBadge value={selected.status}/></div><div><span>Linked Service ID</span><strong>{selected.linkedServiceId||'Not created yet'}</strong></div></div>
   <div className="intake-review-grid">
    <section className="detail-card"><div className="detail-card-head"><div><h3>Reviewed SERVIX Fields</h3><p>{selected.status==='Converted'?'Administrator corrections retain this intake link. Update the official Service Call separately if needed.':editable?'Review the contact, equipment and complaint before saving.':'Only an administrator can correct an already reviewed request.'}</p></div></div><div className="form-grid intake-fields">
     <Field label="Client Name" required wide><input disabled={!editable} value={draft.client} onChange={e=>set('client',e.target.value)}/></Field>
     <Field label="Contact Person"><input disabled={!editable} value={draft.contact} onChange={e=>set('contact',e.target.value)}/></Field>
     <Field label="Mobile"><input disabled={!editable} value={draft.mobile} onChange={e=>set('mobile',e.target.value)}/></Field>
     <Field label="Email" wide><input disabled={!editable} value={draft.email} onChange={e=>set('email',e.target.value)}/></Field>
     <Field label="Equipment" required wide><input disabled={!editable} value={draft.equipment} onChange={e=>set('equipment',e.target.value)}/></Field>
     <Field label="Make"><input disabled={!editable} value={draft.make} onChange={e=>set('make',e.target.value)}/></Field>
     <Field label="Model"><input disabled={!editable} value={draft.model} onChange={e=>set('model',e.target.value)}/></Field>
     <Field label="Serial Number"><input disabled={!editable} value={draft.serialNumber} onChange={e=>set('serialNumber',e.target.value)}/></Field>
     <Field label="Complaint / Requirement" required wide><textarea disabled={!editable} value={draft.complaint} onChange={e=>set('complaint',e.target.value)}/></Field>
    </div></section>
    <section className="detail-card original-intake-card"><div className="detail-card-head"><div><h3>Original Submission Snapshot</h3><p>Read-only intake evidence retained exactly as imported.</p></div><span className="soft-chip">Immutable</span></div><div className="original-intake-list">{Object.entries(snapshot).map(([key,value])=><div key={key}><span>{key}</span><strong>{String(value??'')}</strong></div>)}{Object.keys(snapshot).length===0&&<div><span>Snapshot</span><strong>No original snapshot available for this older record.</strong></div>}</div></section>
   </div>
   {selected.status==='New'&&<div className="intake-next-step"><Icon name="service" size={18}/><div><strong>Review first, convert second</strong><p>Saving this screen marks the request Reviewed. It does not consume a Service ID.</p></div></div>}
   {selected.status==='Reviewed'&&<div className="intake-next-step ready"><Icon name="shield" size={18}/><div><strong>Ready for Service Call conversion</strong><p>Create Service Call opens the normal SERVIX Service Call form with these reviewed fields prefilled. Duplicate checks still run before the Service ID is created.</p></div></div>}
  </Modal>}
  {convertItem&&conversionDraft&&<ServiceCallForm initialDraft={conversionDraft} onClose={()=>setConvertItem(null)} onCreated={async()=>{await onRefresh();setConvertItem(null)}}/>}
 </div>;
}
