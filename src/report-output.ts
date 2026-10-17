type ReportTable = { headers:string[]; rows:(string|number)[][] };

function buildReportTable(tab:string,services:ServiceCall[],parts:PartUsage[],calibrations:CalibrationRecord[]=[]):ReportTable{
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
 if(tab==='Calibration')return {headers:['Service ID','Client','Equipment / Serial','Engineer','Status','Calibration Status','Calibration Date','Certificate / Reference','Result','Next Due'],rows:services.filter(s=>s.reason==='Calibration').map(s=>{const r=calibrations.find(r=>r.serviceCallId===s.id);return [s.serviceId,s.client,s.equipment+(s.serialNumber?' • '+s.serialNumber:''),s.engineer,s.status,calibrationStatus(r),r?.calibrationDate||'',r?.certificate||'',r?.result||'Not recorded',r?.nextDue||'']})};
 if(tab==='Warranty / AMC'){const groups=new Map<string,ServiceCall[]>();services.forEach(s=>{const key=String(s.equipmentId??s.client+'|'+s.equipment+'|'+s.serialNumber);groups.set(key,[...(groups.get(key)||[]),s])});return {headers:['Equipment / Serial','Client','Warranty Calls','AMC Calls','Out of Coverage Calls','FOC Calls'],rows:Array.from(groups.values()).map(items=>[items[0].equipment+' • '+(items[0].serialNumber||'—'),items[0].client,...['Warranty','AMC','Out of Coverage'].map(c=>items.filter(s=>s.coverage===c).length),items.filter(s=>s.foc).length])}}
 if(tab==='Commercial')return {headers:['Service ID','Client','Opened','Quote Status','Payment Status','FOC'],rows:services.map(s=>[s.serviceId,s.client,s.openedDate,s.quoteStatus,s.paymentStatus,s.foc?'Yes':'No'])};
 const rows=tab==='Calibration'?services.filter(s=>s.reason.trim().toLowerCase()==='calibration'):services;
 return {headers:['Service ID','Opened','Client','Equipment / Serial','Reason','Status','Coverage'],rows:rows.map(s=>[s.serviceId,s.openedDate,s.client,s.equipment+(s.serialNumber?' • '+s.serialNumber:''),s.reason,s.status,s.coverage])};
}

function reportCsv(table:ReportTable,meta:string[]):string{
 const cell=(v:string|number)=>{let text=String(v??'');if(/^[\s]*[=+@-]/.test(text)&&typeof v!=='number')text="'"+text;return '"'+text.replace(/"/g,'""')+'"'};
 return '\ufeff'+[...meta.map(m=>[m]),table.headers,...table.rows].map(row=>row.map(cell).join(',')).join('\r\n');
}

async function exportReportCsv(title:string,table:ReportTable,meta:string[]){
 if(isDesktop){try{await invokeNative('record_csv_export',{title,scope:meta,rows:table.rows.length})}catch(e:any){window.alert('Could not record export history: '+(e?.message||String(e)));return}}
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
async function printServiceDocument(d:ServiceDetail,client?:ClientRecord,calibration?:CalibrationRecord,preparedBy?:string,equipmentRecord?:EquipmentRecord){
 document.querySelector('.servix-print-sheet')?.remove();
 const sheet=document.createElement('section');sheet.className='servix-print-sheet service-document';
 const el=(tag:string,value:string,className='')=>{const e=document.createElement(tag);e.textContent=value;if(className)e.className=className;return e};
 const addLine=(parent:HTMLElement,label:string,value:any)=>{const row=document.createElement('p');const key=el('strong',label+': ');row.append(key,document.createTextNode(String(value===undefined||value===null||value===''?'Not recorded':value)));parent.appendChild(row)};
 const block=(title:string,lines:string[])=>{const b=document.createElement('section');b.className='print-info-block';b.appendChild(el('h2',title));lines.filter(Boolean).forEach(s=>b.appendChild(el('p',s)));return b};
 const profile=await ServixApi.getCompanyReportProfile();
 const head=document.createElement('header');
 if(profile.logo){const companyLogo=document.createElement('img');companyLogo.src=profile.logo;companyLogo.alt='Company Logo';companyLogo.style.cssText='max-height:65px;max-width:180px;object-fit:contain;display:block;margin:0 0 6px';head.appendChild(companyLogo)}
 head.append(el('p',profile.name,'company-letterhead'),el('h1','SERVICE REPORT'),el('p','Technical Service & Maintenance'));
 if(profile.address)head.appendChild(el('p',profile.address));
 if(profile.phone||profile.email||profile.website)head.appendChild(el('p',[profile.phone,profile.email,profile.website].filter(Boolean).join('  •  ')));
 sheet.appendChild(head);
 const summary=document.createElement('section');summary.className='print-info-block';
 summary.appendChild(el('h2','Service Report Details'));
 addLine(summary,'Service Request Number / Service ID',d.serviceId);
 if(equipmentRecord?.servixEquipmentId)addLine(summary,'Equipment ID',equipmentRecord.servixEquipmentId);
 addLine(summary,'Date Received / Reported',d.openedDate);
 addLine(summary,'Date Completed',d.completionDate||'Not completed');
 addLine(summary,'Report Generated',new Date().toLocaleString());
 addLine(summary,'Service Status',d.status);
 addLine(summary,'Assigned Engineer',d.engineer||'Unassigned');
 addLine(summary,'Service Type / Reason',d.reason);
 addLine(summary,'Service Location',d.serviceLocation);
 if(d.statusReason)addLine(summary,'Status / Pending Remarks',d.statusReason);
 sheet.appendChild(summary);
 const commercial=document.createElement('section');commercial.className='print-info-block';
 commercial.appendChild(el('h2','Coverage & Payment Status'));
 addLine(commercial,'Warranty / AMC Coverage',d.coverage);
 addLine(commercial,'AMC / CMC Status',d.coverage==='AMC'?'AMC (as recorded)':'Not recorded / Not applicable');
 addLine(commercial,'FOC',d.foc?'Yes':'No');
 addLine(commercial,'Quotation Status',d.quoteStatus);
 addLine(commercial,'Payment Status',d.paymentStatus||'Not recorded');
 sheet.appendChild(commercial);
 const profiles=document.createElement('div');profiles.className='print-profile-grid';
 profiles.append(
  block('Customer Information',[d.client,client?.contact?'Contact: '+client.contact:'',client?.mobile?'Mobile: '+client.mobile:'',client?.email?'Email: '+client.email:'',[client?.city,client?.state].filter(Boolean).join(', ')]),
  block('Device / Equipment Information',[d.equipment,'Make: '+(d.make||'Not recorded'),'Model: '+(d.model||'Not recorded'),'Serial number: '+(d.serialNumber||'Not recorded'),'Service reason: '+d.reason])
 );
 sheet.appendChild(profiles);
 for(const [title,value] of [
  ['01 — Issue Reported / Customer Complaint',d.complaint],
  ['02 — Technical Observation / Diagnosis',d.diagnosis],
  ['03 — Work Performed / Resolution',d.workPerformed],
  ['04 — Final Testing / Verification',d.testingVerification],
  ['05 — Final Outcome / Result',d.finalResult],
  ['06 — Recommendations / Pending Work',d.recommendations]
 ] as [string,string][]){
  const section=block(title,[value||'Not recorded']);section.classList.add('print-narrative');sheet.appendChild(section);
 }
 if(calibration)sheet.appendChild(block('Calibration Details',['Calibration status: '+calibrationStatus(calibration),'Certificate / Reference: '+(calibration.certificate||'Not recorded'),'Calibration date: '+(calibration.calibrationDate||'Not recorded'),'Result: '+(calibration.result||'Not recorded'),'Next due: '+(calibration.nextDue||'Not recorded'),calibration.notes||'']));
 if(d.parts.length){const section=document.createElement('section');section.appendChild(el('h2','Parts / Items Used'));const table=document.createElement('table');const thead=document.createElement('thead');const hr=document.createElement('tr');['Part / Item','Make / Model','Reference','Quantity','Remarks'].forEach(v=>hr.appendChild(el('th',v)));thead.appendChild(hr);table.appendChild(thead);const tbody=document.createElement('tbody');d.parts.forEach(p=>{const row=document.createElement('tr');[p.itemName,[p.make,p.model].filter(Boolean).join(' '),p.partNumber,String(p.quantity),p.remarks].forEach(v=>row.appendChild(el('td',v||'—')));tbody.appendChild(row)});table.appendChild(tbody);section.appendChild(table);sheet.appendChild(section)}
 const footer=document.createElement('footer');footer.className='print-signatures';
 footer.append(el('div','Prepared By: '+(preparedBy||'Not recorded')),el('div','Checked / Approved By: ____________________'),el('div','Customer Acknowledgement (if applicable): ____________________'));
 sheet.appendChild(footer);
 document.body.appendChild(sheet);window.addEventListener('afterprint',()=>sheet.remove(),{once:true});setTimeout(()=>window.print(),80);
}
