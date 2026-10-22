# SERVIX 2.0 — Master Blueprint & Authoritative Baseline

## Authoritative baseline
- Repository: infamousradge/SERVIX
- Development branch: servix-rebuild-v2
- Do not modify or merge into main without explicit approval.
- Authoritative Windows baseline: GitHub Actions build #136
- Baseline commit: 16d981c0e19ea460a03054f4b64c4a7e7f762c72
- Build #136 conclusion: success.
- Build #135 commit f078f7039e0e9a8ff7b7ad6cf18e9446c103a5d0 is the direct parent of #136.
- Build #135 failed only because EquipmentRecord was missing the TypeScript field cmcUntil.
- Build #136 changes only src/types.ts to add cmcUntil, therefore it contains all #135 functionality plus the compile fix.
- Build #136 is also 71 commits ahead of the earlier in-chat SERVIX baseline a62565997c92656a167d54e0c0df27c2616d11e5 and 0 commits behind.
- Therefore no manual merge of old/new SERVIX work is required. SERVIX 2.0 development continues from #136/current branch head.

## Product direction
SERVIX is an offline-first Windows desktop Service Management application.
Design principle: old SERVIX simplicity + premium NEO-level presentation.
Office-use desktop application; engineers do not log in.
No email integration.
No stock/inventory module; parts/items used are tracked against Service Calls.

## Locked branding
- Exact SERVIX Windows app icon.
- Exact full SERVIX sidebar logo.
- Exact SERVIX login/internal mark.
- Compact modal-style login.
- Customer-facing reports use configurable company identity only; no SERVIX application logo.

## Core record model
### Client
One Client can have many Equipment records.

### Equipment
Each physical device has one SERVIX Equipment ID.
The same device can return for service many times.
Repeat visits must create new Service IDs linked to the existing Equipment ID instead of duplicating the device.

### Service Call
Each service visit has one Service ID.
Service ID is the primary operational work item.

Required relationship:
Client → many Equipment IDs
Equipment ID → many Service IDs
Client → combined service history
Equipment ID → individual repeat-service history

## Service Call workspace
- Whole Service Call row is clickable.
- Service ID is the main visual anchor.
- Service Controls at the top for:
  - Status
  - Payment
  - Quote
  - Coverage
  - FOC
  - Priority
  - Engineer
  - Due Date
- Do not duplicate Coverage/Commercial fields lower in the Service tab when already available in Service Controls.
- Important changes generate explicit old → new history events.
- Tabs include Service, Received Item, Parts Used, History and related workflow areas.

Quote:
- Quote Sent
- No Quote

Payment:
- Pending
- Paid

Status:
- Open
- In Progress
- Pending
- Closed

## Duplicate and existing-record rules
Before issuing a Service ID:
- Match Clients by normalized mobile/email.
- Match Equipment by serial number.
- If Client already exists, show that Client's registered devices so staff can select a returning device.
- Same serial under another Client must raise a warning.
- Possible duplicate open Service Call must raise a warning.
- Serious conflicts require Administrator password override.
- Never silently overwrite an existing Client or Equipment record.
- Duplicate override must be written to history/audit.

## Incoming Requests / Google Form
Locked workflow:
Google Form → linked Google Sheet → Sync New Requests → review/matching → staff correction → official Service Call.

Rules:
- Form submission does not consume a Service ID.
- Review opens full intake details.
- Original imported submission snapshot remains immutable.
- Staff may correct mapped SERVIX fields.
- Save & Mark Reviewed does not create Service ID.
- Create Service Call opens the normal Service Call workflow with reviewed fields prefilled.
- Normal duplicate checks still run.
- Intake becomes Converted only after Service Call creation succeeds.
- Converted intake stores linked Service ID.

## Client workspace
- Compact popup with efficient space usage.
- Registered Equipment is clearly visible.
- One Client may have many devices.
- All Devices = combined Client history.
- Individual device selection = only that Equipment ID's Service IDs/history.
- History should show Date and Time clearly and remain simple to read.

## Equipment workspace
- Stable Client ID link.
- SERVIX Equipment ID.
- Make/model/serial/type/location/coverage.
- Repeat-service history for the exact Equipment ID.
- Coverage/expiry context.
- Warranty, AMC, CMC and Out of Coverage supported.

## History / audit
History format:
- Date & Time
- User
- Action
- Related Service ID
- Details / Note

Important event types include:
Created, Status, Payment, Quote, Coverage, FOC, Priority, Engineer, Due Date, Notes, Communication, Engineer Update, Parts Used, Duplicate Override, Intake Conversion, Documents, and other meaningful operational changes.

Print/PDF and CSV history support is part of SERVIX 2.0.

## Parts / Items Used
No inventory.
Track:
- Item name
- Make
- Model
- Part number
- Quantity
- Remarks
- Service ID
- Client
- Equipment
- Date used

## Documents / photos
- Images and PDFs only.
- Service ID linkage.
- Condition photos, Service Reports, Certificates, Client Letters, Delivery Challans, Other.
- Efficient local storage.
- Searchable document register.
- Backup includes attachments.
- Document actions create history/audit entries.

## Warranty / AMC / CMC
Coverage types:
- Warranty
- AMC
- CMC
- Out of Coverage

Equipment-level expiry dates, renewal status and historical visit counts are part of the product.
Warranty/AMC/CMC reports should be equipment-based where appropriate.

## Calibration
Calibration is a Service Call reason with dedicated workflow/reporting.
Target fields include:
- Done / Pending / Not Done
- Calibration date
- Next due date
- Due/upcoming/overdue
- Certificate/document
- Equipment/service history
- Reports/export

## Service Report
Customer-facing report:
- Editable company identity/letterhead.
- No SERVIX app logo.
- Professional A4.
- Client address.
- Equipment and coverage.
- Complaint / diagnosis / work / outcome.
- Parts/payment/commercial status where appropriate.
- Issued report PDF may be archived back to Service ID documents/history.
- Compact, colorful, professional layout.

## Reports & Analytics
Locked direction: Analytics Studio.
Each topic must use relevant filters rather than one identical filter set.

Topics include:
- Overview
- Service Calls
- Clients
- Equipment
- Warranty / AMC / CMC
- Calibration
- Parts Used
- Payment
- Quote
- Engineers
- Other operational views

Charts/tables must exist across relevant topics, not only Overview.
Warranty/AMC/CMC reporting should be equipment-level where appropriate.

## Global Search
Universal top-bar search across:
- Service ID
- Client
- Equipment
- Serial
- Make/model
- Mobile/email
- Relevant linked records

## Data management
- Export selected / filtered / date range / full.
- CSV and print/PDF where appropriate.
- Import with preview, mapping, validation and duplicate review.
- Track export history and filter/date range.
- Avoid duplicate imports.
- Preserve production ID sequences during historical imports.
- Backup database + attachments.
- Verified restore with safety checks.

## Users / security
- First local Administrator setup.
- Administrator / Office User / Read Only.
- Change Password.
- Local/offline permission enforcement.
- Further permission-matrix refinement can continue.

## Settings
Includes:
- Service ID prefix/start/digits.
- User management.
- Company report identity.
- Google sync mapping/settings.
- Other operational settings.

## Dashboard
Target:
- Compact premium layout.
- Open / Pending / Closed / Overdue.
- Recent Service Calls only, latest first.
- Incoming Requests.
- Payment / Quote / Coverage / Service Type / FOC.
- Top clients.
- Useful live analytics.
- Avoid oversized cards and unnecessary nested scrollers.

## Selection / printing
Service Calls, Clients and Equipment should support:
- Select all.
- Select few.
- Print selected.
- Export selected.
- Respect current filters.

## QA
Controlled QA data should cover:
- 4–5 months.
- Repeat Clients.
- Multiple Equipment per Client.
- Repeat visits on same Equipment.
- Same mobile/email.
- Same serial.
- Open/Closed/Pending.
- Warranty/AMC/CMC/Out.
- Parts.
- Payment.
- Notes.
- Communications.
- Duplicate open calls.
- Incoming Request matching.
- Persistence after restart.

## Build #135 functionality retained in #136
Build #135 added:
- Warranty/AMC export based on Equipment rather than Service Calls.
- Equipment expiry detail.
- Historical Warranty/AMC/CMC visit detail/counts.

Build #135 failed at frontend TypeScript compile because EquipmentRecord lacked cmcUntil.
Build #136 is the direct child of #135 and only adds cmcUntil to EquipmentRecord.
Therefore all #135 functionality is retained and successfully built in #136.

## Later functionality already present in the #136 lineage
- Real Google Sheet intake sync.
- Equipment-history isolation and complete linked Service lists.
- Scoped report tables and CSV exports.
- Linked documents and verified backup recovery.
- Display scaling, centered dialogs and global search improvements.
- Operational settings/directories and multi-month QA.
- Professional paginated printing.
- Calibration and coverage reports.
- Validated CSV import/full exports/account maintenance/recovery safeguards.
- Dashboard/filter refinements.
- Client/equipment selection exports.
- Coverage renewal history and calibration progress.
- Analytics Studio.
- Customer Service Report and editable company identity.
- Single Windows NSIS workflow.
- Change Password.
- CMC coverage/expiry support.
- Deep module analytics.
- Equipment-level Warranty/AMC/CMC export detail.

## Development rule from here
Build #136 / commit 16d981c0e19ea460a03054f4b64c4a7e7f762c72 is the SERVIX 2.0 consolidated baseline.

All future work must:
1. Continue from current servix-rebuild-v2.
2. Preserve this master blueprint and later approved amendments.
3. Avoid reintroducing older duplicate layouts/workflows.
4. Keep main untouched until explicit approval.
5. Produce one verified Windows NSIS installer per approved build.
