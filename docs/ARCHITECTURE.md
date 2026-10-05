# SERVIX V2 Architecture

## Product rule

**SERVIX simplicity + NEO-level premium presentation.**

The application is split into reusable frontend building blocks and focused feature files rather than one large UI file. Tauri commands own desktop/database operations. SQLite is the source of truth for the installed desktop application.

## Frontend

- `components.tsx` — shared cards, fields, badges, dialogs and analytics primitives
- `features/*` — feature modules
- `api.ts` — Tauri boundary plus browser-preview adapter
- `styles.css` — one coherent design system, not layered patch files

## Rust / SQLite

- `state.rs` — managed database/session state
- `database.rs` — schema initialization/migrations
- `commands.rs` — application command boundary
- `security.rs` — Argon2 password hashing/verification
- `models.rs` — serializable contracts

## Data philosophy

- Service Call is the central operational record.
- Client and Equipment history is preserved.
- Parts are usage/consumption records, not warehouse inventory.
- Form submissions land in an Intake Queue before a Service ID is issued.
- Email remains outside SERVIX.
- Attachments are linked to Service ID / Client / Equipment.
