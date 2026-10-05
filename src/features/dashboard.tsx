function DashboardView({data,onNavigate,onSync}:{data:DashboardData,onNavigate:(m:ModuleKey)=>void,onSync:()=>void}){
 const counts={open:data.services.filter(s=>s.status==='Open').length,inProgress:data.services.filter(s=>s.status==='In Progress').length,pending:data.services.filter(s=>s.status==='Pending').length,closed:data.services.filter(s=>s.status==='Closed').length};
 const overdue=data.services.filter(s=>s.status!=='Closed'&&s.dueDate&&new Date(s.dueDate)<new Date()).length;
 const coverage=['Warranty','AMC','Out of Coverage'].map((label,i)=>({label,value:data.services.filter(s=>s.coverage===label).length,tone:['seg-blue','seg-green','seg-amber'][i]}));
 const topClients=Object.entries(data.services.reduce((a:any,s)=>{a[s.client]=(a[s.client]||0)+1;return a},{})).sort((a:any,b:any)=>b[1]-a[1]).slice(0,5).map(([label,value]:any)=>({label,value}));
 const topParts=Object.entries(data.partUsage.reduce((a:any,p)=>{a[p.itemName]=(a[p.itemName]||0)+p.quantity;return a},{})).sort((a:any,b:any)=>b[1]-a[1]).slice(0,5).map(([label,value]:any)=>({label,value}));
 return <div className="module-content dashboard-view">
  <PageHeader title="Dashboard" subtitle="Live overview of service operations and incoming work" actions={<button className="primary-button" onClick={()=>onNavigate('service-calls')}><Icon name="plus"/> Manual Service Call</button>}/>
  <div className="kpi-grid">
   <KpiCard label="Open" value={counts.open} icon="service" tone="blue" onClick={()=>onNavigate('service-calls')}/>
   <KpiCard label="In Progress" value={counts.inProgress} icon="service" tone="orange" onClick={()=>onNavigate('service-calls')}/>
   <KpiCard label="Pending" value={counts.pending} icon="bell" tone="amber" onClick={()=>onNavigate('service-calls')}/>
   <KpiCard label="Closed" value={counts.closed} icon="shield" tone="green" onClick={()=>onNavigate('service-calls')}/>
   <KpiCard label="Overdue" value={overdue} icon="bell" tone="red" onClick={()=>onNavigate('service-calls')}/>
  </div>
  <div className="dashboard-grid two">
   <section className="card chart-card"><div className="card-head"><div><h3>Service Calls Trend</h3><p>Recent activity</p></div><span className="soft-chip">Live</span></div><Sparkline values={[9,12,11,16,14,18,21,19,24,20,25,23]}/><div className="trend-labels"><span>Earlier</span><strong>Current period</strong></div></section>
   <section className="card coverage-summary-card"><div className="card-head"><div><h3>Coverage Mix</h3><p>Warranty, AMC and out-of-coverage calls</p></div></div><Donut segments={coverage} totalLabel="Calls"/></section>
  </div>
  <div className="dashboard-grid three">
   <section className={`card sync-card ${data.sync.status==='overdue'?'attention':''}`}><div className="card-head"><div><h3>Google Form Sync</h3><p>Incoming request source</p></div><StatusBadge value={data.sync.status==='up-to-date'?'Up to date':data.sync.status==='not-configured'?'Not configured':'Warning'}/></div><div className="sync-time"><span>Last successful sync</span><strong>{data.sync.lastSuccessfulSync||'Not yet synced'}</strong></div><div className="sync-stat"><span>{data.sync.newCount} new requests</span><button className="secondary-button" onClick={onSync}><Icon name="refresh"/> Sync Now</button></div></section>
   <section className="card"><div className="card-head"><div><h3>Recent Incoming Requests</h3><p>Needs office review</p></div><button className="text-button" onClick={()=>onNavigate('intake')}>View all</button></div><div className="compact-list">{data.intake.slice(0,4).map(x=><button key={x.id} onClick={()=>onNavigate('intake')}><span><strong>{x.client}</strong><small>{x.equipment}</small></span><StatusBadge value={x.status}/></button>)}</div></section>
   <section className="card"><div className="card-head"><div><h3>Recent Service Calls</h3><p>Newest activity first</p></div><button className="text-button" onClick={()=>onNavigate('service-calls')}>View all</button></div><div className="compact-list">{data.services.slice(0,4).map(x=><button key={x.id} onClick={()=>onNavigate('service-calls')}><span><strong>{x.serviceId}</strong><small>{x.client} • {x.equipment}</small></span><StatusBadge value={x.status}/></button>)}</div></section>
  </div>
  <div className="dashboard-grid three">
   <section className="card"><div className="card-head"><div><h3>Alerts / Reminders</h3><p>Items needing attention</p></div></div><div className="alerts"><div className="alert red"><Icon name="bell"/><span><strong>{overdue} service calls overdue</strong><small>Review due dates and pending work</small></span></div><div className="alert amber"><Icon name="calibration"/><span><strong>Calibration watch</strong><small>Track due and upcoming calibrations</small></span></div><div className="alert blue"><Icon name="shield"/><span><strong>Coverage reminders</strong><small>Warranty / AMC expiry monitoring</small></span></div></div></section>
   <section className="card"><div className="card-head"><div><h3>Top Clients</h3><p>By service activity</p></div></div><MiniBars items={topClients}/></section>
   <section className="card"><div className="card-head"><div><h3>Parts Usage</h3><p>Consumption, not inventory</p></div></div><MiniBars items={topParts}/></section>
  </div>
 </div>;
}
