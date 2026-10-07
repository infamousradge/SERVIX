type ModuleKey = 'dashboard'|'intake'|'service-calls'|'clients'|'equipment'|'engineers'|'coverage'|'calibration'|'parts'|'documents'|'reports'|'data'|'users-settings';
type ServiceStatus = 'Open'|'In Progress'|'Pending'|'Closed';
type CoverageType = 'Warranty'|'AMC'|'Out of Coverage';
type IntakeStatus = 'New'|'Reviewed'|'Converted'|'Duplicate';

type SessionUser = { id:number; username:string; displayName:string; role:'Administrator'|'Office User'|'Read Only' };
type SystemStatus = { initialized:boolean; appVersion:string; databasePath?:string };
type ServiceCall = {
  id:number; serviceId:string; openedDate:string; client:string; clientId?:number|null; equipment:string; equipmentId?:number|null;
  make?:string; model?:string; serialNumber?:string; reason:string; complaint:string; engineer:string; status:ServiceStatus;
  priority:string; serviceLocation:string; dueDate:string; coverage:CoverageType; foc:boolean; quoteStatus:string; paymentStatus:string;
  lastUpdated:string; partsUsed?:number; receivedCondition?:string;
};
type ServicePart = { id:number; itemName:string; make:string; model:string; partNumber:string; quantity:number; remarks:string; usedAt:string };
type ServiceEvent = { id:number; eventType:string; oldValue:string; newValue:string; note:string; actor:string; createdAt:string };
type EntityHistoryEvent = { id:number; serviceCallId:number; serviceId:string; client:string; equipment:string; serialNumber:string; reason:string; serviceStatus:string; eventType:string; oldValue:string; newValue:string; note:string; actor:string; createdAt:string };
type ServiceDetail = {
  id:number; serviceId:string; openedDate:string; client:string; equipment:string; make:string; model:string; serialNumber:string;
  reason:string; complaint:string; engineer:string; status:ServiceStatus; priority:string; serviceLocation:string; dueDate:string;
  coverage:CoverageType; foc:boolean; quoteStatus:string; paymentStatus:string; diagnosis:string; workPerformed:string;
  testingVerification:string; finalResult:string; recommendations:string; receivedCondition:string; receivedAccessories:string;
  receivedRemarks:string; completionDate:string; attachmentCount:number; parts:ServicePart[]; events:ServiceEvent[]; updatedAt:string;
};
type ServiceDetailDraft = Omit<ServiceDetail,'serviceId'|'openedDate'|'client'|'equipment'|'make'|'model'|'serialNumber'|'attachmentCount'|'parts'|'events'|'updatedAt'>;
type DuplicateClientCandidate = { id:number; code:string; name:string; contact:string; mobile:string; email:string; serviceCount:number; equipmentCount:number };
type DuplicateEquipmentCandidate = { id:number; servixEquipmentId:string; clientId:number; clientName:string; make:string; model:string; serialNumber:string; equipmentType:string; serviceCount:number };
type DuplicateServiceCandidate = { id:number; serviceId:string; client:string; equipment:string; status:string; openedDate:string; complaint:string };
type DuplicateReview = { level:'clear'|'match'|'warning'; summary:string; clientCandidates:DuplicateClientCandidate[]; equipmentCandidates:DuplicateEquipmentCandidate[]; openServices:DuplicateServiceCandidate[]; warnings:string[]; requiresOverride:boolean };

type IntakeItem = {
  id:number; receivedAt:string; client:string; contact:string; mobile:string; email:string; equipment:string; make:string; model:string;
  serialNumber:string; complaint:string; matchSummary:string; matchTone:'good'|'neutral'|'warn'; status:IntakeStatus; linkedServiceId?:string;
  originalSnapshot?:string;
};
type IntakeReviewDraft = { id:number; client:string; contact:string; mobile:string; email:string; equipment:string; make:string; model:string; serialNumber:string; complaint:string };
type ClientRecord = { id:number; code:string; name:string; contact:string; mobile:string; email:string; city:string; state:string; active:boolean; serviceCount:number; equipmentCount:number };
type EquipmentRecord = { id:number; servixEquipmentId:string; clientId?:number|null; client:string; make:string; model:string; serialNumber:string; type:string; location:string; coverage:string; serviceCount:number; lastService:string };
type PartUsage = { id:number; date:string; serviceId:string; client:string; equipment:string; itemName:string; make:string; model:string; partNumber:string; quantity:number; remarks:string };
type SyncStatus = { configured:boolean; lastSuccessfulSync:string|null; lastAttemptedSync:string|null; newCount:number; status:'up-to-date'|'warning'|'overdue'|'offline'|'not-configured'; message:string };
type UserRecord = { id:number; username:string; displayName:string; role:'Administrator'|'Office User'|'Read Only'; active:boolean };
type DashboardData = { services:ServiceCall[]; intake:IntakeItem[]; clients:ClientRecord[]; equipment:EquipmentRecord[]; partUsage:PartUsage[]; users:UserRecord[]; sync:SyncStatus };
