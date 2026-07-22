# cutover-runbook

## ADDED Requirements

### Requirement: A dry-run tournament checklist rehearses the full flow before cutover

The runbook SHALL contain a dry-run checklist executed on the real event laptop with the Elixir app on a non-production port (`USHU_PORT=8082`, per `elixir-01-foundation`) while Django remains available on 8081. The checklist SHALL cover, in order: fresh import from a checkpointed copy of the production Django database (never the live file); temporary-password login for every role; registering a participant (panel snapshot, group dedup, C-skip for young ages and group/duilian); per-tablo and global draw; activation; full 3A/4B/3C judging round from real judge stations (touch and physical-key hotkeys); main-judge review with per-judge reopen; finalize and no-show; standings with a tie-break case; monitor modes (idle/performing/scores/standings) on the projector; printable protocol; and a `backup-ushu.bat` run. Every item MUST have an observable pass criterion.

#### Scenario: Dry run finds a defect

- **WHEN** any checklist item fails during the rehearsal
- **THEN** cutover is postponed, the defect is fixed, and the dry run restarts from a fresh import — the checklist is all-or-nothing

#### Scenario: Judge stations exercised for real

- **WHEN** the dry run reaches the judging round
- **THEN** it is performed from the actual weak client machines over the venue LAN (including a Cyrillic-layout keyboard on a C station), not from the laptop's own browser

### Requirement: Cutover day follows an ordered plan with a hard verification checkpoint

The runbook SHALL define the cutover-day sequence: (1) stop Django; (2) checkpoint and back up the Django database (`PRAGMA wal_checkpoint(TRUNCATE)` + file copy, per DEPLOY.md); (3) run `mix ushu.import` (or the release-side equivalent) against the fresh copy; (4) HARD CHECKPOINT — proceed only if the import exited 0 with all counts matching and all finals reproducing; (5) distribute temporary passwords from the CSV and have each user set a new password; (6) start the release on port 8081; (7) smoke-test one station per role plus the monitor. Until step 6 succeeds, Django MUST remain startable via the untouched `start.bat`.

#### Scenario: Import verification fails on cutover day

- **WHEN** step 4 reports a count mismatch or score drift
- **THEN** the operator does not proceed: Django is restarted on 8081 and the event runs on Django while the discrepancy is investigated offline

#### Scenario: Clean cutover

- **WHEN** all seven steps pass
- **THEN** clients connect to the same `http://<laptop-ip>:8081/` URL with no reconfiguration on the ten client machines

### Requirement: Rollback keeps Django runnable and states its data cost

The rollback procedure SHALL be: stop the Elixir release, double-click the original `start.bat` — nothing in this change may modify the Django installation, its virtualenv, or its database file (the importer reads a COPY). The runbook MUST state explicitly that any data entered into the Elixir app after cutover is NOT back-ported to Django: rolling back mid-event means re-entering those results by hand from the printed protocols, which is why a backup and a printed protocol are taken after every finished tablo during the first live event.

#### Scenario: Rollback mid-event

- **WHEN** the Elixir app fails during the first live event after three tablos were judged in it
- **THEN** Django is running again within minutes via `start.bat`, and the three tablos' results are re-entered manually from the printed protocols — the runbook told the secretary to print after each tablo precisely for this case

#### Scenario: Django install integrity

- **WHEN** the cutover procedures (import, release install, launchers) have all run
- **THEN** the Django tree, venv, `start.bat`, and live `db.sqlite3` are byte-for-byte untouched apart from the operator's own backup copies

### Requirement: Post-cutover retirement is explicit, not implicit

The runbook SHALL define when Django may be retired: only after one full live tournament has completed on the Elixir stack with zero rollbacks, and after a final Django database backup is archived. Until then, `start.bat` and the Django tree stay on the laptop untouched.

#### Scenario: Premature cleanup attempt

- **WHEN** disk-space cleanup is considered a week after a successful cutover but before a full tournament has run
- **THEN** the runbook forbids deleting the Django install — the retirement condition (one clean tournament) is not yet met
