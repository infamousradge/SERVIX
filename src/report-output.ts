type ReportTable = { headers:string[]; rows:(string|number)[][] };

function buildReportTable(tab:string,services:ServiceCall[],parts:PartUsage[]):ReportTable{
 if(tab==='Parts Usage') return {headers:['Date','Service ID','Client','Part','Part Number','Quantity'],rows:parts.map(p=>[p.date,p.serviceId,p.client,p.itemName,p.partNumber,p.quantity])};
 if(tab==='Clients'||tab==='Equipment'||tab==='Engineers'){
  const groups=new Map<string,{label:string;client:string;calls:number;open:number;closed:number}>();
  services.forEach(s=>{
   const key=tab==='Clients'?String(s.clientId??s.client):tab==='Equipment'?String(s.equipmentId??`${s.clientId??s.client}|${s.equipment}|${s.serialNumber||''}`):s.engineer||'Unassigned';
   const label=tab==='Clients'?s.client:tab==='Equipment'?s.equipment+(s.serialNumber?' • '+s.serialNumber:''):s.engineer||'Unassigned';
   const g=groups.get(key)||{label,client:s.client,calls:0,open:0,closed:0};g.calls++;if(s.status==='Closed')g.closed++;else g.open++;groups.set(key,g);
  });
  return {headers:[tab==='Clients'?'Client':tab==='Equipment'?'Equipment / Serial':'Engineer',...(tab==='Equipment'?['Client']:[]),'Calls','Active','Closed'],rows:Array.from(groups.values()).map(g=>[g.label,...(tab==='Equipment'?[g.client]:[]),g.calls,g.open,g.closed])};
 }
 if(tab==='Commercial')return {headers:['Service ID','Client','Opened','Quote Status','Payment Status','FOC'],rows:services.map(s=>[s.serviceId,s.client,s.openedDate,s.quoteStatus,s.paymentStatus,s.foc?'Yes':'No'])};
 const rows=tab==='Calibration'?services.filter(s=>s.reason.trim().toLowerCase()==='calibration'):services;
 return {headers:['Service ID','Opened','Client','Equipment / Serial','Reason','Status','Coverage'],rows:rows.map(s=>[s.serviceId,s.openedDate,s.client,s.equipment+(s.serialNumber?' • '+s.serialNumber:''),s.reason,s.status,s.coverage])};
}

function reportCsv(table:ReportTable,meta:string[]):string{
 const cell=(v:string|number)=>{let text=String(v??'');if(/^[\s]*[=+@-]/.test(text)&&typeof v!=='number')text="'"+text;return '"'+text.replace(/"/g,'""')+'"'};
 return '\ufeff'+[...meta.map(m=>[m]),table.headers,...table.rows].map(row=>row.map(cell).join(',')).join('\r\n');
}

function exportReportCsv(title:string,table:ReportTable,meta:string[]){
 const url=URL.createObjectURL(new Blob([reportCsv(table,meta)],{type:'text/csv;charset=utf-8'}));
 const link=document.createElement('a');link.href=url;link.download=title.replace(/[^a-z0-9-_]+/gi,'-')+'-'+new Date().toISOString().slice(0,10)+'.csv';document.body.appendChild(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
}

function printReportTable(title:string,table:ReportTable,meta:string[]){
 document.querySelector('.servix-print-sheet')?.remove();
 const sheet=document.createElement('section');sheet.className='servix-print-sheet report-print-sheet';
 const head=document.createElement('header');const h=document.createElement('h1');h.textContent=title;const sub=document.createElement('p');sub.textContent='HAC Acoustic Technologies';head.append(h,sub);sheet.appendChild(head);
 const info=document.createElement('div');info.className='servix-print-meta';meta.forEach(value=>{const span=document.createElement('span');span.textContent=value;info.appendChild(span)});sheet.appendChild(info);
 const grid=document.createElement('table');const header=document.createElement('thead');const hr=document.createElement('tr');table.headers.forEach(value=>{const th=document.createElement('th');th.textContent=value;hr.appendChild(th)});header.appendChild(hr);grid.appendChild(header);
 const body=document.createElement('tbody');table.rows.forEach(row=>{const tr=document.createElement('tr');row.forEach(value=>{const td=document.createElement('td');td.textContent=String(value??'');tr.appendChild(td)});body.appendChild(tr)});grid.appendChild(body);sheet.appendChild(grid);document.body.appendChild(sheet);
 const cleanup=()=>sheet.remove();window.addEventListener('afterprint',cleanup,{once:true});setTimeout(()=>window.print(),80);
}
