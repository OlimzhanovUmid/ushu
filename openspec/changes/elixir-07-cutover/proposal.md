# elixir-07-cutover

## Why

The Elixir rewrite (layers 01–06) is feature-complete only on an empty database; the competition history, reference catalogs, and user accounts live in the Django SQLite file, and the event laptop still boots Django. This final layer moves the data, packages the app for the Windows laptop, and gives the owner a rehearsed, reversible switch-over procedure.

## What Changes

- New `mix ushu.import <django-db> [--media DIR] [--dry-run] [--password-file PATH] [--allow-score-drift]` task that reads the Django SQLite file directly (read-only exqlite connection) and populates the Elixir schema table by table, preserving Django integer primary keys and bumping SQLite sequences afterwards.
- Enum/typed-domain mapping during import: user role from `is_superuser`/`is_staff`/`category`, age ints → age-bucket enums, participation `FINISHED + finalscore == 0` sentinel → `:no_show`, error-code number ranges → `kind`, category name `group`/`duilian` → `format`, sortedm2m `sort_value` chains flattened into `score_marks` positions.
- Passwords are NOT imported (Django pbkdf2 hashes are useless off-platform and per-event resets are policy); the importer generates temporary passwords and writes a username→password CSV for the main judge.
- Media copy: `media/countries/` flag images are copied into the Elixir media directory with stored relative paths preserved; Django runtime artifacts (`showme*.html`, `file.count`) and Django-internal tables (sessions, admin log, auth groups, content types, migrations) are explicitly skipped.
- Built-in verification: per-table row-count parity, spot checksums, and a full recompute of every finished participation's final score through `Ushu.Scoring` diffed against the stored `finalscore` — the import reports and fails on unexplained drift.
- `mix release` packaging with `Ushu.Release.migrate/0` and `Ushu.Release.backup/0` eval helpers, `runtime.exs` driven by `USHU_*` env vars, a Windows `.bat` launcher mirroring today's `start.bat`, and a WAL-aware backup procedure (`VACUUM INTO` plus the three-file copy rule).
- Cutover runbook: dry-run tournament checklist, cutover-day ordered plan with a verification checkpoint, and a rollback path that keeps the Django install untouched and startable.

## Capabilities

### New Capabilities

- `django-data-import`: id-preserving, enum-mapping, self-verifying one-shot import of the Django SQLite database and media files into the Elixir application.
- `release-deployment`: `mix release` packaging for the Windows event laptop — runtime configuration, launcher script, migrations-from-release, and WAL-aware backups.
- `cutover-runbook`: documented dry-run tournament checklist, cutover-day plan, and rollback procedure with Django kept runnable.

### Modified Capabilities

None — new Elixir codebase.

## Impact

- Position: layer 7 of 7 — final layer; depends on ALL previous changes: `elixir-01-foundation` (project, `USHU_*` env config, SQLite+WAL), `elixir-02-scoring-core` (`Ushu.Scoring` used to recompute finals for verification), `elixir-03-ecto-schema` (target tables/changesets the importer writes), `elixir-04-contexts` (`Ushu.Accounts` password hashing path), `elixir-05-realtime` / `elixir-06-liveview-ui` (the app the release actually serves and the dry-run checklist exercises).
- Affected code: `elixir/lib/mix/tasks/ushu.import.ex`, `elixir/lib/ushu/release.ex`, `elixir/config/runtime.exs`, `elixir/rel/` launcher assets, deployment docs; no changes to the Django codebase (it must remain runnable for rollback).
- Data: one-time write of the entire Elixir database; importer refuses to run against a non-empty target.
- Risk concentration: this is the layer where silent data corruption would surface at a live event — hence verification is a hard requirement, not a nice-to-have.
