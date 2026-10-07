const isDesktop = !!window.__TAURI__?.core?.invoke;
let mockState: DashboardData = JSON.parse(JSON.stringify(browserMock));
let mockUser: SessionUser|null = { id:1, username:'admin', displayName:'Administrator', role:'Administrator' };

async function invokeNative<T>(command:string,args:Record<string,unknown>={}):Promise<T>{
  const fn=window.__TAURI__?.core?.invoke;
  if(!fn) throw new Error('Tauri bridge unavailable');
  return fn(command,args) as Promise<T>;
}

function mockDetail(id:number):ServiceDetail{
  const s=mockState.services.find(x=>x.id===id);
  if(!s) throw new Error('Service call not found.');
  const parts=mockState.partUsage.filter(p=>p.serviceId===s.serviceId).map(p=>({id:p.id,itemName:p.itemName,make:p.make,model:p.model,partNumber:p.partNumber,quantity:p.quantity,remarks:p.remarks,usedAt:p.date}));
  return {id:s.id,serviceId:s.serviceId,openedDate:s.openedDate,client:s.client,equipment:s.equipment,make:s.make||'',model:s.model||'',serialNumber:s.serialNumber||'',reason:s.reason,complaint:s.complaint,engineer:s.engineer,status:s.status,priority:s.priority,serviceLocation:s.serviceLocation,dueDate:s.dueDate,coverage:s.coverage,foc:s.foc,quoteStatus:s.quoteStatus,paymentStatus:s.paymentStatus,diagnosis:'',workPerformed:'',testingVerification:'',finalResult:'',recommendations:'',receivedCondition:'',receivedAccessories:'',receivedRemarks:'',completionDate:'',attachmentCount:0,parts,events:[{id:1,eventType:'Created',oldValue:'',newValue:s.serviceId,note:'Service call created',actor:'Administrator',createdAt:s.lastUpdated}],updatedAt:s.lastUpdated};
}

const ServixApi = {
  async systemStatus():Promise<SystemStatus>{
    if(isDesktop) return invokeNative<SystemStatus>('system_status');
    return {initialized:true,appVersion:'0.1.0-preview',databasePath:'Browser preview'};
  },
  async createFirstAdmin(username:string,password:string,displayName:string):Promise<SessionUser>{
    if(isDesktop) return invokeNative<SessionUser>('create_first_admin',{username,password,displayName});
    mockUser={id:1,username,displayName,role:'Administrator'}; return mockUser;
  },
  async authenticate(username:string,password:string):Promise<SessionUser>{
    if(isDesktop) return invokeNative<SessionUser>('authenticate',{username,password});
    if(!username||!password) throw new Error('Enter username and password.');
    mockUser={id:1,username,displayName:'Administrator',role:'Administrator'}; return mockUser;
  },
  async logout(){ if(isDesktop) await invokeNative('logout'); mockUser=null; },
  async bootstrap():Promise<DashboardData>{ if(isDesktop) return invokeNative<DashboardData>('bootstrap'); return JSON.parse(JSON.stringify(mockState)); },
  async reviewServiceDuplicates(draft:any):Promise<DuplicateReview>{
    if(isDesktop) return invokeNative<DuplicateReview>('review_service_duplicates',{draft});
    const mobile=String(draft.mobile||'').replace(/\D/g,''); const email=String(draft.email||'').trim().toLowerCase(); const serial=String(draft.serialNumber||'').trim().toLowerCase();
    const clients=mockState.clients.filter(c=>(mobile&&String(c.mobile||'').replace(/\D/g,'')===mobile)||(email&&String(c.email||'').trim().toLowerCase()===email));
    const equipment=mockState.equipment.filter(e=>serial&&String(e.serialNumber||'').trim().toLowerCase()===serial);
    const open=mockState.services.filter(s=>s.status!=='Closed'&&((serial&&String(s.serialNumber||'').trim().toLowerCase()===serial)||(!serial&&s.client.toLowerCase()===String(draft.client||'').toLowerCase()&&s.equipment.toLowerCase()===String(draft.equipment||'').toLowerCase())));
    const warnings:string[]=[]; let requiresOverride=false;
    if(clients.length>1){warnings.push('The entered mobile/email matches more than one client record.');requiresOverride=true}
    if(equipment.length>1){warnings.push('The serial number appears on more than one equipment record.');requiresOverride=true}
    if(equipment.some(e=>!clients.some(c=>c.name===e.client))){warnings.push('This serial number is linked to another client/equipment record.');requiresOverride=true}
    if(open.length){warnings.push('An open / in-progress / pending Service Call already matches this equipment.');requiresOverride=true}
    return {level:requiresOverride?'warning':(clients.length||equipment.length?'match':'clear'),summary:requiresOverride?'Potential duplicate or record conflict found. Review before creating this Service Call.':(clients.length||equipment.length?'Existing client/equipment records were found. Confirm the records to link.':'No existing client/equipment duplicate was found.'),clientCandidates:clients.map(c=>({id:c.id,code:c.code,name:c.name,contact:c.contact,mobile:c.mobile,email:c.email,serviceCount:c.serviceCount,equipmentCount:c.equipmentCount})),equipmentCandidates:equipment.map(e=>({id:e.id,servixEquipmentId:e.servixEquipmentId,clientId:mockState.clients.find(c=>c.name===e.client)?.id||0,clientName:e.client,make:e.make,model:e.model,serialNumber:e.serialNumber,equipmentType:e.type,serviceCount:e.serviceCount})),openServices:open.map(s=>({id:s.id,serviceId:s.serviceId,client:s.client,equipment:s.equipment,status:s.status,openedDate:s.openedDate,complaint:s.complaint})),warnings,requiresOverride};
  },
  async createServiceCall(draft:any):Promise<ServiceCall>{
    if(isDesktop) return invokeNative<ServiceCall>('create_service_call',{draft});
    const id=Math.max(0,...mockState.services.map(x=>x.id))+1;
    const next=24882+mockState.services.length;
    const item:ServiceCall={id,serviceId:`SRV-${next}`,openedDate:draft.openedDate,client:draft.client,equipment:draft.equipment,make:draft.make,model:draft.model,serialNumber:draft.serialNumber,reason:draft.reason,complaint:draft.complaint,engineer:draft.engineer,status:draft.status,priority:draft.priority,serviceLocation:draft.serviceLocation,dueDate:draft.dueDate,coverage:draft.coverage,foc:draft.foc,quoteStatus:draft.quoteStatus,paymentStatus:draft.paymentStatus,lastUpdated:new Date().toLocaleString()};
    mockState.services.unshift(item); return item;
  },
  async getClientHistory(clientId:number):Promise<EntityHistoryEvent[]>{
    if(isDesktop) return invokeNative<EntityHistoryEvent[]>('get_client_history',{clientId});
    const services=mockState.services.filter(s=>s.clientId===clientId);
    const out:EntityHistoryEvent[]=[];
    for(const s of services){const d=mockDetail(s.id);for(const e of d.events)out.push({id:e.id,serviceCallId:s.id,serviceId:s.serviceId,client:s.client,equipment:s.equipment,serialNumber:s.serialNumber||'',reason:s.reason,serviceStatus:s.status,eventType:e.eventType,oldValue:e.oldValue,newValue:e.newValue,note:e.note,actor:e.actor,createdAt:e.createdAt})}
    return out.sort((a,b)=>String(b.createdAt).localeCompare(String(a.createdAt)));
  },
  async getEquipmentHistory(equipmentId:number):Promise<EntityHistoryEvent[]>{
    if(isDesktop) return invokeNative<EntityHistoryEvent[]>('get_equipment_history',{equipmentId});
    const services=mockState.services.filter(s=>s.equipmentId===equipmentId);
    const out:EntityHistoryEvent[]=[];
    for(const s of services){const d=mockDetail(s.id);for(const e of d.events)out.push({id:e.id,serviceCallId:s.id,serviceId:s.serviceId,client:s.client,equipment:s.equipment,serialNumber:s.serialNumber||'',reason:s.reason,serviceStatus:s.status,eventType:e.eventType,oldValue:e.oldValue,newValue:e.newValue,note:e.note,actor:e.actor,createdAt:e.createdAt})}
    return out.sort((a,b)=>String(b.createdAt).localeCompare(String(a.createdAt)));
  },
  async getServiceDetail(id:number):Promise<ServiceDetail>{
    if(isDesktop) return invokeNative<ServiceDetail>('get_service_detail',{id});
    return mockDetail(id);
  },
  async updateServiceDetail(draft:ServiceDetailDraft):Promise<ServiceDetail>{
    if(isDesktop) return invokeNative<ServiceDetail>('update_service_detail',{draft});
    const s=mockState.services.find(x=>x.id===draft.id); if(!s) throw new Error('Service call not found.');
    Object.assign(s,{reason:draft.reason,complaint:draft.complaint,engineer:draft.engineer,status:draft.status,priority:draft.priority,serviceLocation:draft.serviceLocation,dueDate:draft.dueDate,coverage:draft.coverage,foc:draft.foc,quoteStatus:draft.quoteStatus,paymentStatus:draft.paymentStatus,lastUpdated:new Date().toLocaleString()});
    return {...mockDetail(draft.id),...draft,updatedAt:new Date().toLocaleString()};
  },
  async addServicePart(draft:{serviceCallId:number;itemName:string;make:string;model:string;partNumber:string;quantity:number;remarks:string}):Promise<ServiceDetail>{
    if(isDesktop) return invokeNative<ServiceDetail>('add_service_part',{draft});
    const service=mockState.services.find(x=>x.id===draft.serviceCallId); if(!service) throw new Error('Service call not found.');
    mockState.partUsage.unshift({id:Date.now(),date:new Date().toISOString().slice(0,10),serviceId:service.serviceId,client:service.client,equipment:service.equipment,itemName:draft.itemName,make:draft.make,model:draft.model,partNumber:draft.partNumber,quantity:draft.quantity,remarks:draft.remarks});
    return mockDetail(draft.serviceCallId);
  },
  async addServiceNote(serviceCallId:number,note:string):Promise<ServiceDetail>{
    if(isDesktop) return invokeNative<ServiceDetail>('add_service_note',{serviceCallId,note});
    const d=mockDetail(serviceCallId);d.events.unshift({id:Date.now(),eventType:'Note',oldValue:'',newValue:'',note,actor:'Administrator',createdAt:new Date().toLocaleString()});return d;
  },
  async createUser(draft:{username:string;displayName:string;password:string;role:string}):Promise<UserRecord>{
    if(isDesktop) return invokeNative<UserRecord>('create_user',{draft});
    const id=Math.max(0,...mockState.users.map(x=>x.id))+1; const item:any={id,username:draft.username,displayName:draft.displayName,role:draft.role,active:true}; mockState.users.push(item); return item;
  },
  async saveIntakeReview(draft:IntakeReviewDraft):Promise<void>{
    if(isDesktop) return invokeNative('save_intake_review',{draft});
    const item=mockState.intake.find(x=>x.id===draft.id);
    if(item){if(mockUser?.role==='Read Only'||(item.status!=='New'&&mockUser?.role!=='Administrator'))throw new Error('Administrator permission is required for a correction.');Object.assign(item,draft,{status:item.status==='Converted'?'Converted':'Reviewed'});}
  },
  async updateIntakeStatus(id:number,status:IntakeStatus):Promise<void>{
    if(isDesktop) return invokeNative('update_intake_status',{id,status});
    const item=mockState.intake.find(x=>x.id===id); if(item) item.status=status;
  },
  async getGoogleSyncConfig():Promise<GoogleSyncConfig>{
    if(isDesktop) return invokeNative<GoogleSyncConfig>('get_google_sync_config');
    return {sheetId:'1dXiMB7ls1vAzFL3PHYTOMQDnI-JUtVltVGVuGhu4IJo',sheetName:'Form Responses 1',serviceAccountConfigured:false,serviceAccountEmail:'',timestampHeader:'Timestamp',clientHeader:'Organisation / Client Name',contactHeader:'Contact Person Name',mobileHeader:'Mobile Number',emailHeader:'Email',equipmentHeader:'Equipment / Device',makeHeader:'Make',modelHeader:'Model',serialHeader:'Serial Number',reasonHeader:'Reason for Sending',complaintHeader:'Problem / Complaint'};
  },
  async saveGoogleSyncConfig(draft:GoogleSyncConfigDraft):Promise<GoogleSyncConfig>{
    if(isDesktop) return invokeNative<GoogleSyncConfig>('save_google_sync_config',{draft});
    return {...draft,serviceAccountConfigured:!!draft.serviceAccountJson,serviceAccountEmail:draft.serviceAccountJson?'preview@service-account.local':''};
  },
  async syncGoogleForm():Promise<SyncStatus>{
    if(isDesktop) return invokeNative<SyncStatus>('sync_google_form');
    mockState.sync={...mockState.sync,lastAttemptedSync:new Date().toLocaleString(),lastSuccessfulSync:new Date().toLocaleString(),newCount:0,status:'up-to-date',message:'Sync completed in preview mode.'}; return mockState.sync;
  },
  async loadQaMockData():Promise<string>{
    if(isDesktop) return invokeNative<string>('load_qa_mock_data');
    return 'Browser preview already contains representative mock data.';
  }
};
