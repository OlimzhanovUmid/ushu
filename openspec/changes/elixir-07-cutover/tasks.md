# elixir-07-cutover — Tasks

## 1. Import core

- [ ] 1.1 Create `Ushu.Import` module skeleton: open source DB via `Exqlite.Sqlite3.open(path, mode: :readonly)`, validate expected Django tables exist, wrap the whole run in `Ushu.Repo.transaction/2` with rollback on any error
- [ ] 1.2 Implement the empty-target guard: refuse (with recreate instructions) when any domain table has rows
- [ ] 1.3 Implement pure mapping functions (no catch-all clauses): `map_age/1`, `map_sex/1`, `map_state/2` (incl. no-show sentinel), `map_role/3`, `map_format/1`, `map_kind/1`, `map_verdict/1` with doctests covering every branch and a raising case
- [ ] 1.4 Import reference tables preserving ids: countries, clubs, element_categories (+`format`), elements, error_codes (+`kind`), combinations + ordered `combination_elements` from `sort_value`
- [ ] 1.5 Import users from `judges_user`: role/category mapping, `active` flag; generate temp passwords for active users through the `Ushu.Accounts` registration changeset, unusable randoms for inactive; write the `--password-file` CSV
- [ ] 1.6 Import participants (age/sex enums) and tablos (age enum, category FK, `started`), preserving ids
- [ ] 1.7 Import participations with state mapping incl. `:no_show` sentinel, `order`, `finalscore`, `bonus`, `group`, preserving ids
- [ ] 1.8 Import scores (judge/participation FKs, `b_score_centi` from `bclass` × 100 rounded, `submitted` from `saved`), preserving ids
- [ ] 1.9 Flatten `score_aclass`/`score_berrors` through `wrappererrorcode` into `score_errors` rows (duplicates preserved)
- [ ] 1.10 Flatten the `cclass → combinationstatus → statuses → elementstatus` chain into `score_marks` with NOT NULL `combination_id` (from the `combinationstatus` row), global 0-based `position` ordered by (`cclass.sort_value`, `statuses.sort_value`), and verdict mapping
- [ ] 1.11 Bump id sequences: for every imported table present in `sqlite_sequence`, set `seq = MAX(id)`
- [ ] 1.12 Implement media copy: `countries/` images into the `USHU_MEDIA_DIR` location, preserving relative paths; warn-and-continue with a dangling-path list when the source media dir is missing; never copy `showme*.html`/`file.count`

## 2. Verification

- [ ] 2.1 Implement row-count parity checks for every mapped table pair, incl. derived counts for `score_marks`, `score_errors`, `combination_elements`
- [ ] 2.2 Implement spot checksums: Σ `final_score_centi`, Σ `b_score_centi`, per-tablo participation counts, saved-score counts per judge
- [ ] 2.3 Implement the recompute gate: for every participation imported as `:finished`, rebuild scoring input from imported rows, run `Ushu.Scoring` final assembly, diff vs stored `finalscore`; abort on |diff| > 0.01, warn-or-abort within 0.01 per `--allow-score-drift`
- [ ] 2.4 Implement the verification report printer (counts table, checksums, drift list) and non-zero exit on abort
- [ ] 2.5 Implement `--dry-run`: full import + verification, print report, force rollback

## 3. Task surfaces

- [ ] 3.1 Write `mix ushu.import` wrapper (`lib/mix/tasks/ushu.import.ex`): argument/switch parsing (`--media`, `--dry-run`, `--password-file`, `--allow-score-drift`), `Mix.Task` docs via `@shortdoc`/`@moduledoc`
- [ ] 3.2 Expose `Ushu.Release.import/2` calling the same `Ushu.Import` core for release-side (`bin\ushu.bat eval`) use

## 4. Import tests

- [ ] 4.1 Build a synthetic Django-schema SQLite fixture generator covering every mapping edge: all six age ints, no-show sentinel, `group`/`duilian`/individual categories, error codes in all three ranges plus 701/702, duplicate A-error, abstention (`done=2`) marks, multi-combination C card with non-trivial `sort_value` order, inactive user, staff/superuser users
- [ ] 4.2 Test: full import of the fixture → every enum/row assertion, ids preserved, sequences bumped (insert after import gets max+1), CSV written, passwords hashed and old ones rejected
- [ ] 4.3 Test: verification failures — tampered count, tampered `finalscore` (drift > 0.01) → rollback + non-zero; `--dry-run` leaves target empty
- [ ] 4.4 Test: guards — non-empty target refused, missing source refused, missing media dir warns with dangling list
- [ ] 4.5 Integration test against a checkpointed copy of the real production dump (local-only, not CI): import exits 0, all 225 participations map, all finished finals reproduce

## 5. Release packaging

- [ ] 5.1 Add the `releases` entry to `mix.exs`; ensure no runtime `Mix` usage; `MIX_ENV=prod mix release` builds clean
- [ ] 5.2 Finalize `config/runtime.exs`: `USHU_SECRET_KEY_BASE` (fail-fast when missing in prod), `USHU_DB_PATH`, `USHU_PORT` (default 8081), `USHU_EVENT_TITLE`/`USHU_EVENT_SUBTITLE`, bind `0.0.0.0`
- [ ] 5.3 Implement `Ushu.Release.migrate/0` (Ecto.Migrator, no Mix) and `Ushu.Release.backup/0` (`VACUUM INTO backups/ushu-<timestamp>.sqlite3`)
- [ ] 5.4 Write `rel/` launcher assets: `start-ushu.bat` (editable `USHU_*` config block, migrate-then-start) and `backup-ushu.bat`
- [ ] 5.5 Test `Ushu.Release.backup/0`: snapshot taken under live writes opens consistently and contains committed data
- [ ] 5.6 Build the release ON Windows (documented toolchain install), boot it on a machine without Elixir, verify LAN access on 8081 and a login per role

## 6. Runbook and docs

- [ ] 6.1 Write the deployment doc: Windows build steps, launcher usage, `USHU_*` reference, WAL-aware backup procedure (VACUUM INTO + three-file rule), backup cadence
- [ ] 6.2 Write the dry-run tournament checklist (per `cutover-runbook` spec: fresh import from a COPY, per-role logins, registration/draw/activation, full 3A/4B/3C round from real client stations incl. Cyrillic-layout C hotkeys, reopen, finalize/no-show, standings tie-break, monitor modes, print, backup) with observable pass criteria per item
- [ ] 6.3 Write the cutover-day plan (7 ordered steps with the hard verification checkpoint) and the rollback procedure (Django untouched, data-cost statement, print-per-tablo mitigation) and the Django retirement condition
- [ ] 6.4 Write the Russian explainer `docs/elixir-rewrite/07-cutover.md` (mix tasks, releases vs uberjar, runtime.exs, BEAM on Windows, SQLite from Elixir, data-migration discipline)
- [ ] 6.5 Execute the dry-run checklist end-to-end on the event laptop and record the results; fix-and-repeat until all-green
