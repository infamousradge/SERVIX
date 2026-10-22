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
async function printServiceDocument(d:ServiceDetail,client?:ClientRecord,calibration?:CalibrationRecord,preparedBy?:string,equipmentRecord?:EquipmentRecord,mode:'internal'|'client'='internal'){
 document.querySelector('.servix-print-sheet')?.remove();
 const sheet=document.createElement('section');sheet.className='servix-print-sheet service-document '+(mode==='client'?'client-service-document':'internal-service-document');
 const el=(tag:string,text:string,className='')=>{const node=document.createElement(tag);node.textContent=text;if(className)node.className=className;return node};
 const field=(label:string,value:any)=>{const cell=document.createElement('div');cell.className='sr-field';cell.append(el('small',label),el('strong',String(value===undefined||value===null||value===''?'Not recorded':value)));return cell};
 const profile=await ServixApi.getCompanyReportProfile();
 const head=document.createElement('header');head.className='sr-letterhead';
 if(profile.logo){const img=document.createElement('img');img.src=profile.logo;img.alt='Company logo';img.className='sr-logo';head.appendChild(img)}
 const identity=document.createElement('div');identity.className='sr-company';
 identity.appendChild(el('h2',profile.name||'Company Name','sr-company-name'));
 if(profile.address)identity.appendChild(el('p',profile.address,'sr-company-address'));
 const contactDetails=document.createElement('div');contactDetails.className='sr-contact-details';
 for(const [label,value] of [['Mobile',profile.phone],['Email',profile.email],['Website',profile.website]] as [string,string][]){if(!value)continue;const line=document.createElement('p');line.append(el('strong',label+': '),document.createTextNode(value));contactDetails.appendChild(line)}
 identity.appendChild(contactDetails);head.appendChild(identity);sheet.appendChild(head);
 const title=document.createElement('div');title.className='sr-title';title.append(el('h1',mode==='client'?'CLIENT SERVICE REPORT':'INTERNAL SERVICE REPORT'),el('p',mode==='client'?'SERVICE SUMMARY':'DETAILED TECHNICAL & OFFICE RECORD'));sheet.appendChild(title);

 const facts=document.createElement('section');facts.className='sr-facts';
 if(mode==='client'){
  facts.append(field('Service Request No.',d.serviceId),field('Service Date',d.completionDate||d.openedDate),field('Status',d.status),field('Equipment ID',equipmentRecord?.servixEquipmentId||'Not recorded'));
 }else{
  facts.append(field('Service Request No.',d.serviceId),field('Equipment ID',equipmentRecord?.servixEquipmentId||'Not recorded'),field('Date Received',d.openedDate),field('Date Completed',d.completionDate||'Not completed'),field('Report Generated',new Date().toLocaleString()),field('Status',d.status));
 }
 sheet.appendChild(facts);

 const details=document.createElement('div');details.className='sr-profiles';
 const group=(title:string,rows:[string,any][])=>{const section=document.createElement('section');section.className='sr-panel';section.appendChild(el('h2',title));for(const [label,value] of rows){const row=document.createElement('div');row.className='sr-line';row.append(el('span',label),el('span',String(value||'Not recorded')));section.appendChild(row)}return section};
 details.append(
  group('Customer Information',mode==='client'?[['Customer Name',d.client],['Contact Person',client?.contact]]:[['Customer Name',d.client],['Contact Person',client?.contact],['Phone / Email',[client?.mobile,client?.email].filter(Boolean).join(' | ')],['Address',[client?.address,client?.city,client?.state].filter(Boolean).join(', ')]]),
  group('Equipment Information',[['Device Name',d.equipment],['Make / Model',[d.make,d.model].filter(Boolean).join(' / ')],['Serial Number',d.serialNumber],['Equipment ID',equipmentRecord?.servixEquipmentId],...(mode==='internal'?([['Location',equipmentRecord?.location],['Service Type',d.reason]] as [string,any][]):[])])
 );
 sheet.appendChild(details);

 const coverage=document.createElement('section');coverage.className='sr-coverage';coverage.appendChild(el('h2',mode==='client'?'Coverage Information':'Service & Commercial Status'));
 const tiles=document.createElement('div');tiles.className='sr-status-tiles';
 const today=new Date().toISOString().slice(0,10);
 const warrantyUntil=equipmentRecord?.warrantyUntil||'';
 const amcUntil=equipmentRecord?.amcUntil||'';
 const cmcUntil=equipmentRecord?.cmcUntil||'';
 const warrantyStatus=warrantyUntil?(warrantyUntil>=today?'Active till '+warrantyUntil:'Expired '+warrantyUntil):(d.coverage==='Warranty'?'Active / Covered':'Not recorded');
 const amcStatus=amcUntil?(amcUntil>=today?'Active till '+amcUntil:'Expired '+amcUntil):(d.coverage==='AMC'?'Active / Covered':'Not recorded');
 const cmcStatus=cmcUntil?(cmcUntil>=today?'Active till '+cmcUntil:'Expired '+cmcUntil):(d.coverage==='CMC'?'Active / Covered':'Not recorded');
 const coverageRows:[string,string][]=mode==='client'
  ?[['Current Coverage',d.coverage||'Not recorded'],['Warranty',warrantyStatus],['AMC',amcStatus],['CMC',cmcStatus]]
  :[['Current Coverage',d.coverage||'Not recorded'],['Warranty',warrantyStatus],['AMC',amcStatus],['CMC',cmcStatus],['FOC',d.foc?'Yes':'No'],['Quote',d.quoteStatus||'Not recorded'],['Payment',d.paymentStatus||'Not recorded']];
 for(const [label,value] of coverageRows)tiles.appendChild(field(label,value));
 coverage.appendChild(tiles);sheet.appendChild(coverage);

 const services=document.createElement('section');services.className='sr-services';services.appendChild(el('h2',mode==='client'?'Service Summary':'Detailed Service Record'));
 const entries:[string,string][]=mode==='client'
  ?[
    ['Issue Reported',d.complaint],
    ['Inspection / Findings',d.diagnosis],
    ['Work Carried Out',d.workPerformed],
    ['Final Outcome',[d.testingVerification,d.finalResult].filter(Boolean).join(' — ')],
    ...(d.recommendations?[['Recommendation',d.recommendations] as [string,string]]:[])
   ]
  :[
    ['1. Issue Reported / Customer Complaint',d.complaint],
    ['2. Technical Observation / Diagnosis',d.diagnosis],
    ['3. Work Performed / Resolution',d.workPerformed],
    ['4. Final Testing & Outcome',[d.testingVerification,d.finalResult].filter(Boolean).join(' — ')],
    ['5. Recommendations / Remarks',[d.recommendations,d.statusReason].filter(Boolean).join(' — ')]
   ];
 for(const [label,value] of entries){const block=document.createElement('div');block.className='sr-narrative';block.append(el('h3',label),el('p',value||'Not recorded'));services.appendChild(block)}
 if(mode==='internal'&&d.parts.length){const parts=document.createElement('div');parts.className='sr-extra';parts.appendChild(el('strong','Parts Used: '));parts.appendChild(document.createTextNode(d.parts.map(p=>p.itemName+' ('+p.quantity+')').join(', ')));services.appendChild(parts)}
 if(calibration){const cal=document.createElement('div');cal.className='sr-extra';cal.textContent='Calibration: '+calibrationStatus(calibration)+(calibration.certificate?' | Ref: '+calibration.certificate:'')+(calibration.nextDue?' | Next Due: '+calibration.nextDue:'');services.appendChild(cal)}
 sheet.appendChild(services);

 const footer=document.createElement('footer');footer.className='sr-prepared';
 if(mode==='internal')footer.append(el('strong','Prepared By'),el('p',preparedBy||'Not recorded'),el('small','Report generated: '+new Date().toLocaleString()));
 else footer.append(el('strong','Service Closure'),el('p','This report summarizes the service outcome for the equipment listed above.'),el('small','Service Request: '+d.serviceId));
 sheet.appendChild(footer);
 document.body.appendChild(sheet);window.addEventListener('afterprint',()=>sheet.remove(),{once:true});setTimeout(()=>window.print(),80);
}
