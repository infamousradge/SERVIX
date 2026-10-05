function EquipmentView({data}:{data:DashboardData}){
 const [search,setSearch]=React.useState('');
 const [coverage,setCoverage]=React.useState('All');
 const [selected,setSelected]=React.useState(null as EquipmentRecord|null);
 const rows=data.equipment.filter(x=>(coverage==='All'||x.coverage===coverage)&&`${x.servixEquipmentId} ${x.client} ${x.make} ${x.model} ${x.serialNumber} ${x.type} ${x.location}`.toLowerCase().includes(search.toLowerCase()));
 const relatedServices=selected?data.services.filter(s=>s.equipmentId===selected.id||(s.serialNumber&&selected.serialNumber&&s.serialNumber===selected.serialNumber)):[];
 return <div className="module-content module-list-view">
  <PageHeader title="Equipment" subtitle="Client-linked equipment registry with repeat-service history and coverage context"/>
  <Toolbar>
   <SearchBox value={search} onChange={setSearch} placeholder="Search SERVIX ID, serial, client, make or model..."/>
   <select className="filter-select" value={coverage} onChange={e=>setCoverage(e.target.value)}><option value="All">All Coverage</option><option>Warranty</option><option>AMC</option><option>Out of Coverage</option></select>
  </Toolbar>
  <div className="results-summary"><span><strong>{rows.length}</strong> matching equipment</span><span>Open an equipment record to review repeat-service history.</span></div>
  <section className="table-card fill-table"><div className="data-table equipment-table"><div className="tr th"><span>Equipment ID</span><span>Client</span><span>Make / Model</span><span>Serial Number</span><span>Type / Location</span><span>Coverage</span><span>History</span></div>{rows.map(x=><button className="tr record-row" key={x.id} onClick={()=>setSelected(x)}><span><strong className="linkish">{x.servixEquipmentId}</strong></span><span><strong>{x.client}</strong></span><span><strong>{x.make||'—'}</strong><small>{x.model||'No model'}</small></span><span>{x.serialNumber||'—'}</span><span>{x.type||'—'}<small>{x.location||'No location'}</small></span><span><StatusBadge value={x.coverage}/></span><span><strong>{x.serviceCount} services</strong><small>{x.lastService?`Last: ${x.lastService}`:'No previous service'}</small></span></button>)}</div>{!rows.length&&<EmptyState title="No matching equipment" detail="Adjust the search or coverage filter. Equipment is normally registered during service intake."/>}</section>
  {selected&&<Modal title={`${selected.make} ${selected.model}`.trim()||selected.servixEquipmentId} subtitle={`${selected.servixEquipmentId} • Equipment profile`} onClose={()=>setSelected(null)} wide>
   <div className="record-profile">
    <section className="profile-hero"><div><span className="eyebrow">EQUIPMENT</span><h3>{selected.make} {selected.model}</h3><p>{selected.client} • Serial: {selected.serialNumber||'—'} • {selected.type||'Equipment'}</p></div><StatusBadge value={selected.coverage}/></section>
    <div className="profile-metrics"><div><span>Service Calls</span><strong>{relatedServices.length}</strong></div><div><span>Open / Active</span><strong>{relatedServices.filter(s=>s.status!=='Closed').length}</strong></div><div><span>Last Service</span><strong className="metric-text">{selected.lastService||'—'}</strong></div><div><span>Location</span><strong className="metric-text">{selected.location||'—'}</strong></div></div>
    <div className="profile-grid two">
     <section className="profile-panel"><div className="panel-heading"><div><h4>Equipment Details</h4><p>Current registry information</p></div></div><div className="detail-pairs"><div><span>Client</span><strong>{selected.client}</strong></div><div><span>Make</span><strong>{selected.make||'—'}</strong></div><div><span>Model</span><strong>{selected.model||'—'}</strong></div><div><span>Serial Number</span><strong>{selected.serialNumber||'—'}</strong></div><div><span>Type</span><strong>{selected.type||'—'}</strong></div><div><span>Coverage</span><strong>{selected.coverage}</strong></div></div></section>
     <section className="profile-panel"><div className="panel-heading"><div><h4>Service History</h4><p>Repeat visits for this equipment</p></div><span className="soft-chip">{relatedServices.length}</span></div><div className="profile-list">{relatedServices.slice(0,10).map(s=><div className="profile-list-row" key={s.id}><span><strong>{s.serviceId} • {s.reason}</strong><small>{s.openedDate} • {s.complaint}</small></span><span><StatusBadge value={s.status}/><small>{s.engineer||'Unassigned'}</small></span></div>)}{!relatedServices.length&&<p className="quiet-empty">No service history yet.</p>}</div></section>
    </div>
   </div>
  </Modal>}
 </div>;
}
