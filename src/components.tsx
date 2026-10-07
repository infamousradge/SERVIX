function StatusBadge({value}:{value:string}){
  const tone=value==='Closed'||value==='Paid'||value==='Up to date'||value==='Converted'?'green':value==='Pending'||value==='Warning'||value==='Reviewed'?'amber':value==='In Progress'||value==='Open'||value==='New'?'blue':value==='Duplicate'||value==='Overdue'?'red':'slate';
  return <span className={`status-badge ${tone}`}>{value}</span>;
}
function KpiCard({label,value,meta,icon,tone='blue',onClick}:{label:string,value:number|string,meta?:string,icon:string,tone?:string,onClick?:()=>void}){
  return <button className={`kpi-card tone-${tone}`} onClick={onClick} type="button"><span className="kpi-icon"><Icon name={icon} size={19}/></span><span className="kpi-copy"><span className="kpi-label">{label}</span><strong>{value}</strong>{meta&&<small>{meta}</small>}</span></button>;
}
function PageHeader({title,subtitle,actions}:{title:string,subtitle?:string,actions?:any}){
  return <div className="page-header"><div><h1>{title}</h1>{subtitle&&<p>{subtitle}</p>}</div><div className="page-actions">{actions}</div></div>;
}
function EmptyState({title,detail}:{title:string,detail:string}){return <div className="empty-state"><div className="empty-icon"><Icon name="service" size={24}/></div><strong>{title}</strong><p>{detail}</p></div>}
function Field({label,required,children,wide}:{label:string,required?:boolean,children?:any,wide?:boolean}){return <label className={`field ${wide?'wide':''}`}><span>{label}{required&&<em>*</em>}</span>{children}</label>}
function Modal({title,subtitle,onClose,children,footer,wide=false}:{title:string,subtitle?:string,onClose:()=>void,children?:any,footer?:any,wide?:boolean}){
 return <div className="modal-backdrop" onMouseDown={e=>{if(e.target===e.currentTarget)onClose()}}><section className={`modal ${wide?'modal-wide':''}`}><header><div><h2>{title}</h2>{subtitle&&<p>{subtitle}</p>}</div><button className="icon-button" onClick={onClose}><Icon name="close"/></button></header><div className="modal-body">{children}</div>{footer&&<footer>{footer}</footer>}</section></div>;
}
function Toolbar({children}:{children?:any}){return <div className="toolbar">{children}</div>}
function SearchBox({value,onChange,placeholder='Search...'}:{value:string,onChange:(v:string)=>void,placeholder?:string}){return <div className="search-box"><Icon name="search" size={17}/><input value={value} onChange={e=>onChange((e.target as HTMLInputElement).value)} placeholder={placeholder}/></div>}
function MiniBars({items}:{items:{label:string,value:number}[]}){
 const max=Math.max(1,...items.map(x=>x.value));
 return <div className="mini-bars">{items.map((item,i)=><div className="mini-bar-row" key={i}><span>{item.label}</span><div className="mini-track"><i style={{width:`${Math.max(5,item.value/max*100)}%`}}/></div><strong>{item.value}</strong></div>)}</div>;
}
function Donut({segments,totalLabel}:{segments:{label:string,value:number,tone:string}[],totalLabel:string}){
 const total=Math.max(1,segments.reduce((a,b)=>a+b.value,0)); let offset=0;
 return <div className="donut-layout"><svg className="donut" viewBox="0 0 42 42"><circle className="donut-base" cx="21" cy="21" r="15.9"/><g transform="rotate(-90 21 21)">{segments.map((s,i)=>{const pct=s.value/total*100; const el=<circle key={i} className={`donut-seg ${s.tone}`} cx="21" cy="21" r="15.9" strokeDasharray={`${pct} ${100-pct}`} strokeDashoffset={-offset}/>; offset+=pct; return el;})}</g><text x="21" y="20" textAnchor="middle" className="donut-number">{total}</text><text x="21" y="25" textAnchor="middle" className="donut-label">{totalLabel}</text></svg><div className="legend">{segments.map((s,i)=><div key={i}><i className={s.tone}/><span>{s.label}</span><strong>{s.value}</strong></div>)}</div></div>;
}
function Sparkline({values}:{values:number[]}){
 const max=Math.max(...values,1), min=Math.min(...values,0); const pts=values.map((v,i)=>`${i/(values.length-1)*100},${32-(v-min)/(max-min||1)*26}`).join(' ');
 return <svg className="sparkline" viewBox="0 0 100 36" preserveAspectRatio="none"><polyline points={pts} fill="none" stroke="currentColor" strokeWidth="2"/><polygon points={`0,36 ${pts} 100,36`} fill="currentColor" opacity=".07"/></svg>;
}


type PrintableHistoryRow = { dateTime:string; user:string; action:string; serviceId:string; details:string; context?:string; status?:string };

function historyRowsToCsv(fileName:string,rows:PrintableHistoryRow[]){
 const csvCell=(v:any)=>'"'+String(v??'').replace(/"/g,'""')+'"';
 const header=['Date & Time','User','Action','Service ID','Details','Context','Status'].map(csvCell).join(',');
 const body=rows.map(r=>[r.dateTime,r.user,r.action,r.serviceId,r.details,r.context||'',r.status||''].map(csvCell).join(',')).join('\r\n');
 const blob=new Blob(['\ufeff'+header+'\r\n'+body],{type:'text/csv;charset=utf-8'});
 const url=URL.createObjectURL(blob); const a=document.createElement('a'); a.href=url; a.download=fileName.replace(/[^a-z0-9-_]+/gi,'-')+'.csv'; document.body.appendChild(a); a.click(); a.remove(); setTimeout(()=>URL.revokeObjectURL(url),1000);
}

function printHistoryDocument(title:string,subtitle:string,rows:PrintableHistoryRow[],meta:string[]=[]){
 const existing=document.querySelector('.servix-print-sheet'); if(existing)existing.remove();
 const sheet=document.createElement('section'); sheet.className='servix-print-sheet';
 const head=document.createElement('header'); const h=document.createElement('h1'); h.textContent=title; const sub=document.createElement('p'); sub.textContent=subtitle; head.append(h,sub);
 const metaBox=document.createElement('div'); metaBox.className='servix-print-meta';
 [...meta,'Generated: '+new Date().toLocaleString()].forEach(v=>{const span=document.createElement('span');span.textContent=v;metaBox.appendChild(span)});
 const table=document.createElement('table');
 const thead=document.createElement('thead'); const hr=document.createElement('tr');
 ['Date & Time','User','Action','Service ID','Details'].forEach(v=>{const th=document.createElement('th');th.textContent=v;hr.appendChild(th)}); thead.appendChild(hr);
 const tbody=document.createElement('tbody');
 rows.forEach(r=>{const tr=document.createElement('tr');[r.dateTime,r.user,r.action,r.serviceId,r.details+(r.context?' • '+r.context:'')].forEach(v=>{const td=document.createElement('td');td.textContent=v||'—';tr.appendChild(td)});tbody.appendChild(tr)});
 table.append(thead,tbody); sheet.append(head,metaBox,table); document.body.appendChild(sheet);
 const cleanup=()=>sheet.remove(); window.addEventListener('afterprint',cleanup,{once:true}); setTimeout(()=>window.print(),80); setTimeout(()=>{if(document.body.contains(sheet))sheet.remove()},120000);
}
