function ReportsView({data}:{data:DashboardData}){
 const [tab,setTab]=React.useState('Overview');
 const tabs=['Overview','Service Calls','Clients','Equipment','Parts Usage','Engineers','Calibration','Commercial'];
 const today=new Date().toISOString().slice(0,10);
 const [fromDate,setFromDate]=React.useState(`${new Date().getFullYear()}-01-01`);
 const [toDate,setToDate]=React.useState(today);
 const [client,setClient]=React.useState('All');
 const selectedClient=data.clients.find(c=>String(c.id)===client);
 const inRange=(d:string)=>(!fromDate&&!toDate)||!!d&&((!fromDate||d.slice(0,10)>=fromDate)&&(!toDate||d.slice(0,10)<=toDate));
 const filteredServices=data.services.filter(s=>inRange(s.openedDate)&&(client==='All'||(selectedClient&&(s.clientId!=null?s.clientId===selectedClient.id:s.client===selectedClient.name))));
 const clientServiceIds=new Set(data.services.filter(s=>selectedClient&&(s.clientId!=null?s.clientId===selectedClient.id:s.client===selectedClient.name)).map(s=>s.serviceId));
 const filteredParts=data.partUsage.filter(p=>inRange(p.date)&&(client==='All'||clientServiceIds.has(p.serviceId)));
 const topParts=Object.entries(filteredParts.reduce((a:any,p)=>{a[p.itemName]=(a[p.itemName]||0)+p.quantity;return a},{})).sort((a:any,b:any)=>b[1]-a[1]).map(([label,value]:any)=>({label,value}));
 const reasons=Object.entries(filteredServices.reduce((a:any,s)=>{a[s.reason]=(a[s.reason]||0)+1;return a},{})).map(([label,value]:any)=>({label,value}));
 const coverage=['Warranty','AMC','Out of Coverage'].map((label,i)=>({label,value:filteredServices.filter(s=>s.coverage===label).length,tone:['seg-blue','seg-green','seg-amber'][i]}));
 const uniqueClients=new Set(filteredServices.map(s=>s.clientId??s.client)).size;
 const uniqueEquipment=new Set(filteredServices.map(s=>s.equipmentId||`${s.client}|${s.equipment}|${s.serialNumber||''}`)).size;
 const monthKeys=Array.from({length:12},(_,i)=>{const d=new Date();d.setDate(1);d.setMonth(d.getMonth()-(11-i));return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`});
 const trendValues=monthKeys.map(k=>filteredServices.filter(s=>s.openedDate?.startsWith(k)).length);
 const clearFilters=()=>{setClient('All');setFromDate('');setToDate('')};
 const scopeLabel=`${client==='All'?'All customers':selectedClient?.name||'Unknown customer'}${fromDate||toDate?` • ${fromDate||'Start'} to ${toDate||'Today'}`:''}`;
 const report=buildReportTable(tab,filteredServices,filteredParts);
 const invalidDates=!!(fromDate&&toDate&&fromDate>toDate);
 const reportTitle=tab==='Overview'?'Service Activity Report':tab+' Report';
 const reportMeta=()=>['Customer: '+(client==='All'?'All customers':selectedClient?.name||'Unknown customer'),'Date range: '+(fromDate||'All dates')+' to '+(toDate||'Present'),'Records: '+report.rows.length,'Generated: '+new Date().toLocaleString()];
 return <div className="module-content reports-view">
  <PageHeader title="Reports & Analytics" subtitle="Live operational reporting with customer and date-range selection" actions={<><button className="secondary-button" disabled={invalidDates||!report.rows.length} onClick={()=>printReportTable(reportTitle,report,reportMeta())}><Icon name="print"/> Print / PDF</button><button className="secondary-button" disabled={invalidDates||!report.rows.length} onClick={()=>exportReportCsv(reportTitle,report,reportMeta())}><Icon name="export"/> Export CSV</button></>}/>
  <div className="report-tabs">{tabs.map(t=><button className={tab===t?'active':''} onClick={()=>setTab(t)} key={t}>{t}</button>)}</div>
  <Toolbar><div className="report-filter-band"><label className="report-filter-field"><span>Customer</span><select value={client} onChange={e=>setClient(e.target.value)}><option value="All">All Customers</option>{data.clients.slice().sort((a,b)=>a.name.localeCompare(b.name)).map(c=><option key={c.id} value={String(c.id)}>{c.name}</option>)}</select></label><label className="report-date-field"><span>From Date</span><input type="date" value={fromDate} max={toDate||undefined} onChange={e=>setFromDate(e.target.value)}/></label><label className="report-date-field"><span>To Date</span><input type="date" value={toDate} min={fromDate||undefined} onChange={e=>setToDate(e.target.value)}/></label><button className="text-button" onClick={clearFilters}>Clear Filters</button></div></Toolbar>
  <div className="report-scope"><span>Showing</span><strong>{scopeLabel}</strong><span>• {filteredServices.length} service call{filteredServices.length===1?'':'s'}</span></div>
  {invalidDates&&<div className="form-error">From Date must be on or before To Date.</div>}
  {tab!=='Overview'&&<section className="table-card report-results"><div className="results-summary"><strong>{reportTitle}</strong><span>{report.rows.length} records • print and CSV use these rows</span></div><div className="report-table-scroll"><table><thead><tr>{report.headers.map(h=><th key={h}>{h}</th>)}</tr></thead><tbody>{report.rows.map((row,i)=><tr key={i}>{row.map((value,j)=><td key={j}>{value}</td>)}</tr>)}</tbody></table></div>{!report.rows.length&&<EmptyState title="No matching report records" detail="Adjust the customer or date range."/>}</section>}
  <div className="kpi-grid compact"><KpiCard label="Service Calls" value={filteredServices.length} icon="service" tone="blue"/><KpiCard label="Clients" value={uniqueClients} icon="clients" tone="green"/><KpiCard label="Equipment" value={uniqueEquipment} icon="equipment" tone="amber"/><KpiCard label="Parts Qty Used" value={filteredParts.reduce((a,b)=>a+b.quantity,0)} icon="parts" tone="orange"/></div>
  <div className="dashboard-grid three"><section className="card"><div className="card-head"><div><h3>Service Activity</h3><p>Rolling 12-month trend for the selected scope</p></div></div><Sparkline values={trendValues}/></section><section className="card"><div className="card-head"><div><h3>Coverage Mix</h3><p>Warranty / AMC / Out of Coverage</p></div></div><Donut segments={coverage} totalLabel="Calls"/></section><section className="card"><div className="card-head"><div><h3>Service Reasons</h3><p>Most common work types in this selection</p></div></div><MiniBars items={reasons}/></section></div>
  <div className="dashboard-grid two"><section className="card"><div className="card-head"><div><h3>Parts Consumption</h3><p>Used items within the selected customer/date range</p></div></div><MiniBars items={topParts}/></section><section className="card report-note"><h3>Report controls</h3><p>Print / PDF opens the print dialog; choose Microsoft Print to PDF to save a file. CSV exports the active report with customer, date range, record count and generation time. Calibration lists service calls recorded with the Calibration reason.</p><div className="chip-row"><span>Customer-aware</span><span>Date range</span><span>Live</span><span>Print / PDF</span><span>CSV</span></div></section></div>
 </div>;
}
