function CoverageView({data}:{data:DashboardData}){
 const [search,setSearch]=React.useState('');
 const [coverage,setCoverage]=React.useState('All');
 const warranty=data.equipment.filter(x=>x.coverage==='Warranty');
 const amc=data.equipment.filter(x=>x.coverage==='AMC');
 const out=data.equipment.filter(x=>x.coverage==='Out of Coverage');
 const rows=data.equipment.filter(x=>(coverage==='All'||x.coverage===coverage)&&`${x.servixEquipmentId} ${x.client} ${x.make} ${x.model} ${x.serialNumber}`.toLowerCase().includes(search.toLowerCase()));
 return <div className="module-content module-list-view">
  <PageHeader title="Warranty / AMC" subtitle="Current equipment coverage with service-history snapshots"/>
  <div className="kpi-grid compact coverage-kpis"><KpiCard label="Warranty" value={warranty.length} icon="shield" tone="blue"/><KpiCard label="AMC" value={amc.length} icon="shield" tone="green"/><KpiCard label="Out of Coverage" value={out.length} icon="shield" tone="amber"/></div>
  <Toolbar><SearchBox value={search} onChange={setSearch} placeholder="Search client, equipment or serial..."/><select className="filter-select" value={coverage} onChange={e=>setCoverage(e.target.value)}><option value="All">All Coverage</option><option>Warranty</option><option>AMC</option><option>Out of Coverage</option></select></Toolbar>
  <div className="results-summary"><span><strong>{rows.length}</strong> matching equipment</span><span>Coverage shown here reflects the current equipment record.</span></div>
  <section className="table-card fill-table"><div className="data-table coverage-table"><div className="tr th"><span>Equipment ID</span><span>Client</span><span>Make / Model</span><span>Serial Number</span><span>Coverage</span><span>Service History</span><span>Last Service</span></div>{rows.map(x=><div className="tr" key={x.id}><span><strong className="linkish">{x.servixEquipmentId}</strong></span><span><strong>{x.client}</strong></span><span><strong>{x.make||'—'}</strong><small>{x.model||'No model'}</small></span><span>{x.serialNumber||'—'}</span><span><StatusBadge value={x.coverage}/></span><span><strong>{x.serviceCount} calls</strong></span><span>{x.lastService||'—'}</span></div>)}</div>{!rows.length&&<EmptyState title="No matching coverage records" detail="Adjust the search or coverage filter."/>}</section>
 </div>;
}
