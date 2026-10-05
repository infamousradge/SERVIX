# SERVIX V2 Rebuild

Fresh SERVIX service-management desktop application.

## Architecture

- Tauri 2 / Rust native shell
- React + TypeScript frontend
- Embedded SQLite via rusqlite
- Offline-first Windows desktop design

The rebuild intentionally keeps the simple SERVIX service workflow while using the premium interaction and visual direction selected from the NEO RC4 reference. It does **not** copy NEO's monolithic frontend structure.

## Current milestone

The first vertical slice includes:

- First-run administrator setup and local login
- Premium reusable application shell
- Live dashboard fed from SQLite in desktop mode
- Google Form Intake queue shell and sync status model
- Service Calls list and simplified New Service Call workflow
- Clients and Equipment views
- Parts / Items Used consumption view
- Documents workflow shell
- Live Reports & Analytics shell
- Users & Settings shell
- Embedded SQLite schema for core service records, audit/history, intake, attachments and sync logging
- One GitHub Actions workflow producing exactly one NSIS Windows EXE artifact

## Build

```powershell
npm install
npm run desktop:build
```

The browser preview uses sample data so the visual system can be reviewed without Tauri. The packaged desktop application uses SQLite.
