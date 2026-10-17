import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';

const source=readFileSync(new URL('../src/report-output.ts',import.meta.url),'utf8');
const context=vm.createContext({});
vm.runInContext(ts.transpile(readFileSync(new URL('../src/operations.tsx',import.meta.url),'utf8'),{target:ts.ScriptTarget.ES2019,jsx:ts.JsxEmit.React}),context);
vm.runInContext(ts.transpile(source,{target:ts.ScriptTarget.ES2019}),context);
const services=[
 {id:1,serviceId:'SRV-1',clientId:1,client:'Same Name',equipmentId:1,equipment:'MA42',serialNumber:'shared',openedDate:'2026-10-01',reason:'Calibration',status:'Closed',coverage:'Warranty',engineer:'A',quoteStatus:'Quote Sent',paymentStatus:'Paid',foc:false},
 {id:2,serviceId:'SRV-2',clientId:2,client:'Same Name',equipmentId:2,equipment:'MA42',serialNumber:'shared',openedDate:'2026-10-02',reason:'Repair',status:'Pending',coverage:'AMC',engineer:'',quoteStatus:'No Quote Sent',paymentStatus:'Pending',foc:true}
];
const parts=[{date:'2026-10-01',serviceId:'SRV-1',client:'Same Name',itemName:'Probe',partNumber:'P1',quantity:2}];
for(const tab of ['Overview','Service Calls','Clients','Equipment','Parts Usage','Engineers','Calibration','Warranty / AMC','Commercial']){
 const report=context.buildReportTable(tab,services,parts);
 assert.ok(report.rows.every(row=>row.length===report.headers.length),tab);
 assert.equal(context.buildReportTable(tab,[],[]).rows.length,0,tab);
}
assert.equal(context.buildReportTable('Clients',services,[]).rows.length,2);
assert.equal(context.buildReportTable('Equipment',services,[]).rows.length,2);
assert.equal(context.buildReportTable('Calibration',services,[]).rows[0][0],'SRV-1');
assert.equal(context.buildReportTable('Service Calls',[services[1]],[]).rows.length,1);
const calibration=context.buildReportTable('Calibration',services,[],[{serviceCallId:1,calibrationDate:'2026-10-01',certificate:'CERT-1',result:'Pass',nextDue:'2027-10-01'}]);assert.ok(calibration.headers.includes('Certificate / Reference'));assert.ok(calibration.rows[0].includes('CERT-1'));assert.equal(context.buildReportTable('Warranty / AMC',services,[]).rows.length,2);
const csv=context.reportCsv({headers:['Name','Qty'],rows:[['=SUM(A1:A2)',-2],['a,"b"\nnext',3]]},['Customer: Test']);
assert.ok(csv.startsWith('\ufeff"Customer: Test"\r\n'));
assert.ok(csv.includes('"\'=SUM(A1:A2)","-2"'));
assert.ok(csv.includes('"a,""b""\nnext","3"'));

context.filterScope=(data,client,fromDate,toDate)=>{const scope=context.reportScope(data,{...context.newServiceQuery(),client,from:fromDate,to:toDate});return {filteredServices:scope.services,filteredParts:scope.parts}};
const scopeData={clients:[{id:1,name:'Same Name'},{id:2,name:'Same Name'}],services,partUsage:[...parts,{...parts[0],serviceId:'SRV-2'}]};
const scope=context.filterScope(scopeData,'1','2026-10-01','2026-10-02');
assert.equal(scope.filteredServices.length,1);
assert.equal(scope.filteredParts.length,1);
assert.equal(context.filterScope(scopeData,'All','2026-10-02','2026-10-02').filteredServices[0].serviceId,'SRV-2');
assert.equal(context.filterScope(scopeData,'All','2026-10-03','2026-10-04').filteredServices.length,0);
console.log('Report checks passed: all tabs, empty results, stable grouping IDs, calibration, scope, CSV quoting and formula escaping.');

vm.runInContext(ts.transpile(readFileSync(new URL('../src/features/reports.tsx',import.meta.url),'utf8'),{target:ts.ScriptTarget.ES2019,jsx:ts.JsxEmit.React}),context);
assert.ok(context.reportFilterKeys('Parts Usage').includes('make'));assert.ok(!context.reportFilterKeys('Parts Usage').includes('payment'));assert.ok(context.reportFilterKeys('Commercial').includes('payment'));assert.ok(!context.reportFilterKeys('Commercial').includes('make'));const switched=context.reportQueryForTab('Parts Usage',{...context.newServiceQuery(),status:'Pending',payment:'Pending',from:'2026-09-01',client:'1'});assert.equal(switched.status,'All');assert.equal(switched.payment,'All');assert.equal(switched.from,'2026-09-01');assert.equal(switched.client,'1');console.log('Report-specific filter sets and drilldown scope cleanup passed.');

const reportFunction=source.slice(source.indexOf('async function printServiceDocument('));
assert.ok(reportFunction.includes("getCompanyReportProfile()"),'Customer report must use configured company letterhead');
assert.ok(reportFunction.includes("sr-profiles"),'Customer and equipment panels must be present');
assert.ok(reportFunction.includes("sr-status-tiles"),'Coverage and payment status must be present');
assert.ok(reportFunction.indexOf("sheet.appendChild(details)")<reportFunction.indexOf("sheet.appendChild(coverage)"),'Coverage/payment must appear below customer and equipment panels');
assert.ok(reportFunction.indexOf("sheet.appendChild(coverage)")<reportFunction.indexOf("sheet.appendChild(services)"),'Technical service narrative must follow coverage');
assert.ok(reportFunction.includes("Prepared By"),'Digital report must include prepared-by');
assert.ok(!/Customer Acknowledgement|Checked \/ Approved By|Approved By:/.test(reportFunction),'Digital service report must not request acknowledgement or approval');
assert.ok(!/SERVIX|servix-logo|servix-sidebar-logo/.test(reportFunction),'Customer report must not show software branding');
const stylesheet=readFileSync(new URL('../src/refinements.css',import.meta.url),'utf8');
assert.ok(stylesheet.includes('.service-document .sr-facts'),'A4 service report layout must be present');
assert.ok(stylesheet.includes('grid-template-columns:repeat(6'),'Six-field report summary must remain compact');
console.log('Approved single-page report layout, ordering and branding safeguards passed.');
