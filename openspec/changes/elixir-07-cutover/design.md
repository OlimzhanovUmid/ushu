# elixir-07-cutover — Design

## Context

Layers 01–06 produce a complete Elixir/Phoenix app with an empty SQLite database. The production data lives in the Django SQLite file (`db.sqlite3`: 12 users, 14 element categories, 168 tablos, 225 participations, 1635 scores, 612 element statuses, sortedm2m join tables carrying load-bearing `sort_value` ordering). The event laptop is a Windows machine operated by non-developers via double-clickable `.bat` files. The rewrite is only "done" when this data is inside the Elixir app, the app is packaged for that laptop, and there is a rehearsed way to switch — and a rehearsed way back.

## Goals / Non-Goals

**Goals**

- One-shot, repeatable, self-verifying import of the Django database and media into the Elixir schema, preserving integer ids.
- A production packaging story: `mix release`, `runtime.exs`, Windows launcher, WAL-aware backups.
- A written, rehearsable cutover procedure with a hard verification gate and a cheap rollback.
- Teach the owner (explainer): mix tasks, releases vs uberjar, runtime config, BEAM on Windows, SQLite from Elixir, data-migration discipline.

**Non-Goals**

- No continuous/two-way sync with Django — this is a one-time migration; Django is read-only input.
- No import of Django-internal tables (sessions, admin log, auth groups/permissions, content types, migration history).
- No password migration (decided in the master brief).
- No multi-carpet, archive, or online-entry data concerns (out of scope everywhere).
- No changes to the Django codebase (rollback depends on it staying untouched).

## Decisions

**D1. Read the source with direct `exqlite`, not a second Ecto repo.**
The importer opens the Django file with `Exqlite.Sqlite3.open(path, mode: :readonly)` and iterates plain SQL result rows. *Alternative considered:* a dynamic `Ushu.ImportRepo` (Ecto) over the Django file — rejected because we would still write schemaless queries against Django's table names (no Ecto schemas exist for them and writing throwaway schemas for 20 legacy tables is pure ceremony), and a second started repo invites accidental writes. Read-only exqlite is fewer moving parts and makes "the source cannot be modified" a connection-level guarantee. Writes go through the normal `Ushu.Repo` (`insert_all` in chunks for bulk tables; changeset-validated inserts for users so hashing/validation runs).

**D2. Preserve Django primary keys; bump sequences after.**
All entity tables keep their Django ids (`insert_all` with explicit `id`). This keeps every FK mapping trivial (no id-translation map to carry through join flattening) and keeps printed protocols/participant numbers comparable across systems during the transition. After insert, for each table present in `sqlite_sequence`, set `seq = MAX(id)`; for plain rowid tables SQLite already continues from max rowid, so the bump is a belt-and-suspenders no-op there. *Alternative:* fresh ids + translation maps — rejected as more code, more failure modes, zero benefit on an empty target.

**D3. Enum mappings are total functions that crash on unknown input.**
Each mapping (`age`, `state`, `role`, `format`, `kind`, `verdict`, `sex`) is a pattern-matched function with NO catch-all clause (except where the rule itself has one, e.g. format defaults to `:individual` by design). An unexpected source value raises, aborting the transaction with the row identified. The mappings:

| Domain | Django | Elixir |
|---|---|---|
| user role | `is_superuser=1` | `:admin` (category nil) |
| | else `is_staff=1` | `:main_judge` (category nil) |
| | else | `:judge`, category `0/1/2 → :a/:b/:c` |
| age | `4 / 0 / 5 / 1 / 2 / 3` | `:y7_8 / :y9_10 / :y11 / :y12_14 / :y15_17 / :adult` |
| sex | `0 / 1` | `:male / :female` |
| participation state | `0 / 1 / 2` | `:waiting / :performing / :finished` |
| no-show sentinel | `state=2 AND finalscore=0` | `:no_show` |
| category format | name `"group"` / `"duilian"` (case-insensitive) / else | `:group / :duilian / :individual` |
| error kind | number `1..79 / 80..89 / >=90` | `:a / :b / :shared` |
| mark verdict | done `2 / 1 / 0` | `:pending / :performed / :failed` |

Note on codes 701/702 ("70A"/"70B"): they fall in `>= 90 → :shared`, which reproduces the Django runtime exactly (A submit accepted `>= 90`, B submit accepted everything not `1..79` — both could record them). If the owner wants them under `:a` semantically, that is a post-import admin edit, not an importer special case.

**D4. Flatten the positional sortedm2m chains into `score_marks` at import time.**
For each C score: `SELECT ... FROM tablo_score_cclass sc JOIN tablo_combinationstatus_statuses ss ON ... JOIN tablo_elementstatus es ON ... WHERE sc.score_id = ? ORDER BY sc.sort_value, ss.sort_value`, emitting `score_marks` rows with a 0-based global `position` and the NOT NULL `combination_id` taken from the `tablo_combinationstatus` row on the chain (per elixir-03 D5). This bakes the exact order the Django `zip(*statuses_per_judge)` depended on into an explicit column — the whole point of the `score_marks` redesign (elixir-03). A/B error wrappers flatten to `score_errors` rows (duplicates preserved as rows). Wrapper entities (`WrapperErrorCode`, `CombinationStatus`, `ElementStatus`) are consumed and get no target table. `score_events` is NOT backfilled: fabricating who/when for historical submits would poison the audit trail's trustworthiness; the trail starts at cutover.

**D5. Passwords: generate temporary ones, hash through `Ushu.Accounts`, emit a CSV.**
Django pbkdf2 hashes are not portable into the phx.gen.auth scheme, and per-event password resets are already policy. The importer generates a random temporary password per active user, runs it through the same registration changeset the app uses (the hash algorithm — `pbkdf2_elixir`, decided in elixir-03 design D8 — is the app's concern; the importer does not know or care), and writes `import_passwords.csv`. Inactive users get an unusable random password and no CSV line. *Alternative considered:* implementing Django's pbkdf2_sha256 verifier in Elixir for a transparent first login — rejected: real work, permanent crypto surface, for a 12-user one-time event where handing out temp passwords is operationally normal.

**D6. Verification is part of the import, inside the transaction, fail-closed.**
Three tiers: (a) row-count parity per mapped table (with derived formulas for flattened tables); (b) spot checksums (Σ `final_score_centi`, Σ `b_score_centi`, per-tablo participation counts, saved counts per judge); (c) semantic recompute — every `:finished` participation's final is recomputed via `Ushu.Scoring` from the imported marks/errors and diffed against the stored Django `finalscore`. Counts/checksums mismatching or |diff| > 0.01 abort (rollback, non-zero exit). Diffs ≤ 0.01 can only be waived explicitly with `--allow-score-drift` (they may occur for legacy rows computed before stabilize-django's rounding fix). `--dry-run` runs everything and rolls back regardless. Rationale: tier (c) is simultaneously the strongest possible test of `elixir-02-scoring-core` against 225 real-world cases — data migration and scoring verification pay for each other. *Alternative:* a separate `mix ushu.verify` task — rejected as a gap operators will skip; verification you can forget is verification that won't happen on cutover day.

**D7. Build the release on Windows; no cross-compilation.**
`mix release` bundles ERTS, which is platform-specific; producing a Windows release requires building on Windows (documented one-time install of Erlang/OTP + Elixir on the laptop or a Windows build machine). *Alternatives:* Burrito/cross-build containers — rejected as exotic tooling for a single known target; Docker — no (Windows laptop, offline venue, ops burden). Note: a NIF-based hashing lib (bcrypt_elixir/argon2) would require a C toolchain on the Windows build machine; elixir-03 design D8 chose `pbkdf2_elixir` (pure Elixir) precisely to avoid that — the importer is agnostic either way (D5).

**D8. Maintenance via `Ushu.Release` eval helpers; backup via `VACUUM INTO`.**
Releases have no Mix, so `mix ecto.migrate` does not exist on the laptop: `Ushu.Release.migrate/0` (Ecto.Migrator) runs from the launcher before start. `Ushu.Release.backup/0` uses `VACUUM INTO 'backups/ushu-<ts>.sqlite3'` — SQLite's supported online-snapshot mechanism, safe under WAL with the server live, producing a single self-contained file. Manual copies remain documented with the three-file WAL rule (matches current DEPLOY.md discipline). *Alternative:* `sqlite3.exe` CLI on the laptop — rejected: another install, and the release can already do it.

**D9. Keep port 8081 and the `USHU_*` variable names.**
Ten client machines have the URL bookmarked/muscle-memorized; the operator knows the `start.bat` config block. `runtime.exs` defaults the port to 8081 and reuses `USHU_SECRET_KEY_BASE`, `USHU_EVENT_TITLE`, `USHU_EVENT_SUBTITLE`, plus `USHU_DB_PATH`/`USHU_PORT`. The dry-run runs Elixir with `USHU_PORT=8082` (the side-by-side port from `elixir-01-foundation`) alongside Django on 8081; at cutover the release takes 8081 (Django stopped, never uninstalled).

**D10. Importer runs as a Mix task in dev, and the same core module is release-callable.**
Logic lives in `Ushu.Import` (plain module, testable); `mix ushu.import` is a thin Mix wrapper for the dev/dry-run workflow; `Ushu.Release.import(path, opts)` exposes it on the laptop (`bin\ushu.bat eval ...`) since the release has no Mix. Cutover-day docs use the release form.

## Risks / Trade-offs

- [Recompute drift on legacy rows: old finals stored under the pre-stabilize truncation bug may differ by 0.01] → the 0.01 warn band + explicit `--allow-score-drift`; anything larger is a hard stop and must be root-caused (that is the feature, not the bug).
- [NIF-compiled password hashing fails to build on Windows] → averted by elixir-03 design D8 (`pbkdf2_elixir`, pure Elixir); importer itself has no crypto dependency (D5); dry-run checklist includes a login per role, which catches any regression before cutover day.
- [Operator copies the live DB while the server runs and gets a torn backup] → `backup-ushu.bat` (VACUUM INTO) is the only advertised online path; WAL three-file rule documented for stopped-server copies.
- [Rollback after real data entered in Elixir loses that data in Django] → stated cost in the runbook; mitigation: print protocol + backup after every finished tablo during the first live event.
- [Importer run against the live Django file, not a copy] → docs mandate checkpoint-and-copy first; the read-only connection guarantees the source is never mutated either way.
- [Target DB not empty → id collisions] → hard refusal on any existing domain rows; recreate-and-migrate is the documented reset.
- [sqlite_sequence table absent when no table uses AUTOINCREMENT] → bump code handles both (update where present; rowid tables need nothing).

## Migration Plan

1. Implement + test importer against a checkpointed copy of the production dump (CI fixture: a small synthetic Django DB with every mapping edge: no-show sentinel, duplicate error, abstention marks, group dedup rows, 701/702 codes).
2. Build the Windows release; install on the laptop next to (not over) the Django tree.
3. Dry-run tournament per the `cutover-runbook` checklist (Elixir on `USHU_PORT=8082`, Django untouched :8081).
4. Cutover day per the ordered plan; hard gate on the import verification report.
5. Rollback at any point = stop release, double-click old `start.bat`.
6. Retire Django only after one full clean tournament on Elixir.

## Open Questions

- Should the printable protocol (elixir-06) show Django-era participation ids anywhere? Default: yes implicitly — ids are preserved (D2), so no action needed.
- Exact temporary-password policy (length/alphabet)? Default: 8 chars, unambiguous alphabet (no 0/O/1/l), generated with `:crypto.strong_rand_bytes/1` — good enough for an offline LAN and typed once.
