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

## Classic Blue UI work
The `feature/classic-blue-ui` branch starts the locked desktop redesign: readable Segoe UI typography, wider navigation, centered sign-in dialogs, responsive raised capsule tabs, spacious dashboard cards, a two-column service overview, and page scrolling. The Windows build now bundles branding assets.

Run `python ui_smoke.py` to open every module and exercise tab selection at 1280×760 and 1536×960 using a temporary test database. This needs a graphical desktop (or Xvfb on Linux). The Windows build runs the same checks before packaging.

The exact approved SERVIX logo now replaces the multi-variant asset. The app, installer, shortcuts and uninstaller use a multi-resolution gear icon. The setup wizard uses the Windows 11 style, follows the system's light/dark preference, and includes custom welcome/completion branding. `python branding_assets.py` prepares icon and installer artwork before packaging. Windows CI verifies the embedded icon resources, installs the product, checks startup, uninstalls it, and captures the actual installer in both themes.

Still pending: final visual polish against the approved UI samples, Windows user acceptance testing with representative data and display scaling, and a versioned installer release. The current installer is a 1.0.1 preview.
