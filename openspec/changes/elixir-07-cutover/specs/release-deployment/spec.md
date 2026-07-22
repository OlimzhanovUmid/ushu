# release-deployment

## ADDED Requirements

### Requirement: The app ships as a self-contained mix release built on Windows

The project SHALL define a `mix release` (`releases` entry in `mix.exs`) producing a self-contained bundle with ERTS included, runnable without Elixir/Mix installed on the target. Because ERTS is platform-specific, the release for the event laptop SHALL be built on Windows itself (documented one-time toolchain install: Erlang/OTP + Elixir); cross-compiling from macOS/Linux is explicitly out of scope. The release MUST NOT depend on `Mix` at runtime (no `Mix.env/0` outside `config/*.exs`).

#### Scenario: Laptop without developer tools

- **WHEN** the built release folder is copied to a Windows machine that has no Elixir installation
- **THEN** `bin\ushu.bat start` boots the server successfully (ERTS is bundled)

#### Scenario: Release build

- **WHEN** `MIX_ENV=prod mix release` runs on the Windows build machine
- **THEN** the build completes and the bundle contains `bin/ushu.bat`, the compiled app, and ERTS

### Requirement: All deployment knobs live in runtime.exs under USHU_* env vars

`config/runtime.exs` SHALL read, at boot: `USHU_SECRET_KEY_BASE` (→ `secret_key_base`; boot MUST fail with a clear message when unset in prod), `USHU_DB_PATH` (SQLite file location, default `./ushu.sqlite3` relative to the release root), `USHU_PORT` (default `8081` — the port clients already bookmark from the Django deployment), `USHU_EVENT_TITLE` / `USHU_EVENT_SUBTITLE` (idle monitor screen lines), and bind the endpoint to `0.0.0.0` for LAN access. These names deliberately mirror the Django `start.bat` variables (per `elixir-01-foundation`).

#### Scenario: Missing secret

- **WHEN** the release starts in prod without `USHU_SECRET_KEY_BASE` set
- **THEN** boot aborts immediately with a message naming the variable, not a stacktrace deep in Phoenix

#### Scenario: Same URL as before

- **WHEN** the release starts with defaults on the event laptop
- **THEN** judge stations reach the app at `http://<laptop-ip>:8081/` exactly as they reached Django

### Requirement: Migrations and maintenance run through release eval helpers

A `Ushu.Release` module SHALL expose `migrate/0` (runs all pending Ecto migrations by loading the app and calling `Ecto.Migrator`, without Mix) and `backup/0` (writes a consistent, WAL-safe snapshot via `VACUUM INTO` to a timestamped file under a `backups/` directory next to the database). Both SHALL be invocable as `bin\ushu.bat eval "Ushu.Release.migrate()"` / `...backup()`.

#### Scenario: Fresh laptop first boot

- **WHEN** the launcher runs migrate-then-start on a machine with no database file
- **THEN** the SQLite database is created with the full schema and WAL mode enabled before the endpoint accepts connections

#### Scenario: Online backup

- **WHEN** `Ushu.Release.backup()` runs while the server is live during an event
- **THEN** a single self-contained `backups/ushu-<timestamp>.sqlite3` file is produced that opens consistently, with no need to stop the server or copy `-wal`/`-shm` files

### Requirement: A Windows launcher script mirrors the Django start.bat workflow

The release SHALL ship a `start-ushu.bat` at the bundle root with an editable configuration block (the `USHU_*` variables with per-event comments, defaults matching today's `start.bat`), which then runs migrations (`eval "Ushu.Release.migrate()"`) and starts the server in the foreground. A companion `backup-ushu.bat` SHALL invoke `Ushu.Release.backup()`. Double-clicking MUST be sufficient — no terminal knowledge required.

#### Scenario: Event-day start

- **WHEN** the operator edits the title lines in `start-ushu.bat` and double-clicks it
- **THEN** migrations apply and the server starts on port 8081 with the new event title on the idle monitor

#### Scenario: One-click backup

- **WHEN** the operator double-clicks `backup-ushu.bat` after the last event of the day
- **THEN** a timestamped backup file appears under `backups\` and the window reports the file name before closing

### Requirement: The backup procedure is documented WAL-aware

Deployment documentation SHALL state that the live database spans three files in WAL mode (`.sqlite3`, `-wal`, `-shm`) and that a raw file copy is only valid when either the server is stopped or all three files are copied together; the supported online path is `backup-ushu.bat` (`VACUUM INTO`). The docs SHALL prescribe a backup before the import, before each event day, and after the final results.

#### Scenario: Naive copy attempted

- **WHEN** the operator reads the backup section before copying `ushu.sqlite3` alone while the server runs
- **THEN** the documentation has warned that this snapshot may miss committed data in the WAL and directs them to `backup-ushu.bat` instead
