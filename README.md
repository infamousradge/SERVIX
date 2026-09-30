# SERVIX — Service Management

Standalone, office-operated Windows service management application.

## V1 foundation
- Modern dashboard UI based on the approved SERVIX concept
- Client master and duplicate checking
- SERVIX Equipment ID (`SEQ-xxxxxx`) independent of stock/external ID
- Manual service-call entry only
- Warranty / AMC flags
- Calibration as a service reason
- Office-side engineer updates
- Service history timeline
- Commercial / quotation / payment fields
- Service detail workflow with Overview / Technical / Parts / Calibration / Attachments / Commercial / History tabs
- Parts usage entries from office-side engineer updates
- Calibration completion fields and certificate references
- Image/PDF attachments; images are automatically resized/compressed, while PDFs are kept lossless/readable
- Filtered service list and CSV export
- Local SQLite database

## Run locally
1. Install Python 3.11+ on Windows.
2. `pip install -r requirements.txt`
3. Double-click `run_servix.bat`, or run `python app.py`.

## Repository structure
- `app.py` — desktop UI
- `database.py` — SQLite schema/data access
- `assets/` — approved SERVIX branding
- `data/` — local database (ignored by Git)
- `attachments/` — local attachments (ignored by Git)
- `exports/` — generated exports (ignored by Git)
- `backups/` — backups (ignored by Git)

## Important product rules
- No email integration.
- No QR code workflow.
- Engineers do not enter field updates directly; office staff enter engineer updates.
- Customer receipt after dispatch is not tracked in detail.
- Courier/AWB is optional.
- Attachments should be optimized/compressed while remaining readable.


## Current workflow build
The `feature/service-workflow-v2` development branch adds the first complete office-side service update layer. Open a Service ID from Service Calls and use the tabs to record technical progress, parts, calibration, documents and commercial status. Engineers do not need direct application access.
