const isDesktop = !!window.__TAURI__?.core?.invoke;
let mockState: DashboardData = JSON.parse(JSON.stringify(browserMock));
let mockUser: SessionUser|null = { id:1, username:'admin', displayName:'Administrator', role:'Administrator' };

async function invokeNative<T>(command:string,args:Record<string,unknown>={}):Promise<T>{
  const fn=window.__TAURI__?.core?.invoke;
  if(!fn) throw new Error('Tauri bridge unavailable');
  return fn(command,args) as Promise<T>;
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
  async createServiceCall(draft:any):Promise<ServiceCall>{
    if(isDesktop) return invokeNative<ServiceCall>('create_service_call',{draft});
    const id=Math.max(0,...mockState.services.map(x=>x.id))+1;
    const next=24882+mockState.services.length;
    const item:ServiceCall={id,serviceId:`SRV-${next}`,openedDate:draft.openedDate,client:draft.client,equipment:draft.equipment,make:draft.make,model:draft.model,serialNumber:draft.serialNumber,reason:draft.reason,complaint:draft.complaint,engineer:draft.engineer,status:draft.status,priority:draft.priority,serviceLocation:draft.serviceLocation,dueDate:draft.dueDate,coverage:draft.coverage,foc:draft.foc,quoteStatus:draft.quoteStatus,paymentStatus:draft.paymentStatus,lastUpdated:new Date().toLocaleString()};
    mockState.services.unshift(item); return item;
  },
  async createUser(draft:{username:string;displayName:string;password:string;role:string}):Promise<UserRecord>{
    if(isDesktop) return invokeNative<UserRecord>('create_user',{draft});
    const id=Math.max(0,...mockState.users.map(x=>x.id))+1; const item:any={id,username:draft.username,displayName:draft.displayName,role:draft.role,active:true}; mockState.users.push(item); return item;
  },
  async updateIntakeStatus(id:number,status:IntakeStatus):Promise<void>{
    if(isDesktop) return invokeNative('update_intake_status',{id,status});
    const item=mockState.intake.find(x=>x.id===id); if(item) item.status=status;
  },
  async syncGoogleForm():Promise<SyncStatus>{
    if(isDesktop) return invokeNative<SyncStatus>('sync_google_form');
    mockState.sync={...mockState.sync,lastAttemptedSync:new Date().toLocaleString(),lastSuccessfulSync:new Date().toLocaleString(),newCount:0,status:'up-to-date',message:'Sync completed in preview mode.'}; return mockState.sync;
  }
};
