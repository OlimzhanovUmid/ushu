# django-data-import

## ADDED Requirements

### Requirement: Import task reads the Django database read-only and writes atomically

`mix ushu.import <path-to-django-db>` SHALL open the Django SQLite file over a dedicated read-only connection (direct `exqlite`, `mode: :readonly` — never the application `Ushu.Repo`) and SHALL write to the target database inside a single transaction so a failed import leaves the target exactly as it was. The task MUST refuse to run when the target database contains any domain rows (users, participants, scores, …) and MUST refuse when the source file does not exist or lacks the expected Django tables. With `--dry-run` the task SHALL perform the full import and verification, print the report, then roll the transaction back.

#### Scenario: Crash mid-import

- **WHEN** the import fails partway through (mapping error, constraint violation, power loss)
- **THEN** the target database contains no partial data — the transaction rolled back and the source file is untouched (it was opened read-only)

#### Scenario: Target not empty

- **WHEN** `mix ushu.import` is run against a target database that already has domain rows
- **THEN** the task aborts with a message telling the operator to recreate the database (`mix ecto.drop && mix ecto.create && mix ecto.migrate`) before importing

#### Scenario: Dry run

- **WHEN** the task runs with `--dry-run`
- **THEN** the full verification report is printed and the target database is left empty

### Requirement: Django primary keys are preserved and sequences bumped

Every imported row SHALL keep its Django integer primary key (participants, users, clubs, countries, element_categories, elements, combinations, error_codes, tablos, participations, scores). After inserting, the task SHALL ensure the next auto-generated id in every imported table is strictly greater than the maximum imported id (updating `sqlite_sequence` where the table uses AUTOINCREMENT). Rows synthesized during flattening (`score_marks`, `score_errors`, `combination_elements`) get fresh ids.

#### Scenario: New row after import

- **WHEN** a new participant is created through the Elixir app right after an import whose maximum participant id was 225
- **THEN** the new row receives id ≥ 226 and no primary-key collision occurs

#### Scenario: Cross-references survive

- **WHEN** any imported score is loaded with its participation, judge, tablo, and participant
- **THEN** every foreign key resolves to the same logical entity it referenced in Django

### Requirement: User accounts are mapped to the typed role model without passwords

Rows from `judges_user` SHALL map to `users` as: `is_superuser = 1` → `role: :admin`; else `is_staff = 1` → `role: :main_judge`; else `role: :judge` with `category` mapped `0 → :a, 1 → :b, 2 → :c`. `category` MUST be nil for `:admin` and `:main_judge`. `is_active` maps to `active`. Django password hashes SHALL NOT be imported: the task generates a random temporary password per active user, hashes it through the `Ushu.Accounts` registration path (from `elixir-04-contexts`; the hash algorithm, `pbkdf2_elixir`, is decided in `elixir-03-ecto-schema` design D8), and writes a `username,temporary_password` CSV to the path given by `--password-file` (default `import_passwords.csv`), printing a reminder that the file must be handed to the main judge and deleted after passwords are changed.

#### Scenario: Role mapping of the current panel

- **WHEN** the production dump (users `admin`, `main`, `A1..A3`, `B1..B4`, `C1..C3`) is imported
- **THEN** `admin` becomes `:admin`, `main` becomes `:main_judge`, and the ten judges become `:judge` with categories `:a`/`:b`/`:c` matching their Django `category` ints, all with `category` nil for the two non-judges

#### Scenario: Old password rejected

- **WHEN** a judge tries to log in to the Elixir app with their old Django password after import
- **THEN** authentication fails; only the temporary password from the CSV works

### Requirement: Magic values become typed enums during mapping

The importer SHALL apply exactly these mappings: participant/tablo age ints `4 → :y7_8, 0 → :y9_10, 5 → :y11, 1 → :y12_14, 2 → :y15_17, 3 → :adult`; participation state `0 → :waiting, 1 → :performing, 2 → :finished`, EXCEPT `state = 2 AND finalscore = 0` which becomes `:no_show`; element_category `format` from the lower-cased name — `"group" → :group`, `"duilian" → :duilian`, anything else `→ :individual`; error_code `kind` from `number` — `1..79 → :a`, `80..89 → :b`, `>= 90 → :shared` (the display `number` itself is imported unchanged). Any source value outside these domains SHALL abort the import with the offending row identified.

#### Scenario: No-show sentinel is lifted

- **WHEN** a Django participation has `state = 2` and `finalscore = 0`
- **THEN** the imported participation has state `:no_show`, and a finished one with `finalscore > 0` has state `:finished`

#### Scenario: Sub-code errors land in shared

- **WHEN** error codes 701 ("70A") and 702 ("70B") are imported
- **THEN** they receive `kind: :shared` (numbers ≥ 90), matching the Django runtime behavior where both A and B judges could record them

#### Scenario: Unknown age int

- **WHEN** a participant row carries an age int outside `{0,1,2,3,4,5}`
- **THEN** the import aborts naming the participant id, instead of guessing a bucket

### Requirement: Positional sortedm2m chains flatten into explicit rows

For every C-judge score, the Django chain `tablo_score_cclass (sort_value) → tablo_combinationstatus → tablo_combinationstatus_statuses (sort_value) → tablo_elementstatus` SHALL flatten into `score_marks(score_id, combination_id, element_id, position, verdict)` — `combination_id` (NOT NULL) taken from the `tablo_combinationstatus` row reached through the `score_cclass` chain — where `position` is the 0-based global index ordered by (`cclass.sort_value`, `statuses.sort_value`) and `verdict` maps `2 → :pending, 1 → :performed, 0 → :failed`. `tablo_score_aclass` and `tablo_score_berrors` SHALL flatten through `tablo_wrappererrorcode` into `score_errors(score_id, error_code_id)` rows, preserving duplicates as multiple rows. Combination element order (`elements_combination_elements.sort_value`) maps to the ordered-join `position` from `elixir-03-ecto-schema`. Wrapper tables (`WrapperErrorCode`, `CombinationStatus`, `ElementStatus`) are consumed, not imported as entities. `score_events` is NOT backfilled — the audit trail starts at cutover.

#### Scenario: Mark order preserved

- **WHEN** a C-judge score with three combinations of sizes 2, 3, 2 is imported
- **THEN** the score has exactly 7 `score_marks` with positions 0..6 whose element ids follow the Django (`cclass.sort_value`, `statuses.sort_value`) order — the same order the positional zip in `calculateC` relied on

#### Scenario: Duplicate deduction survives

- **WHEN** a Django A-judge score references the same error code twice via two wrapper rows
- **THEN** the imported score has two `score_errors` rows for that error code

### Requirement: Media files are copied and runtime artifacts skipped

With `--media DIR` (default: sibling `media/` of the source db) the task SHALL copy `countries/` flag images into the Elixir media directory (the directory configured by `USHU_MEDIA_DIR`, defined in the `elixir-01-foundation` runtime-configuration env contract), preserving the relative paths stored in `countries.image`. The task SHALL skip Django-internal tables (`django_migrations`, `django_session`, `django_admin_log`, `django_content_type`, `auth_*`, `judges_user_groups`, `judges_user_user_permissions`) and SHALL NOT copy Django runtime artifacts (`showme*.html`, `file.count`, static build output).

#### Scenario: Flag renders after import

- **WHEN** a country with `image = "countries/uzb.png"` is imported and the media copy runs
- **THEN** the file exists under the Elixir media directory at `countries/uzb.png` and the monitor screen renders the flag

#### Scenario: Missing media directory

- **WHEN** the source media directory does not exist
- **THEN** the task warns, lists countries whose image paths are now dangling, and continues (missing flags are cosmetic, not blocking)

### Requirement: The import verifies itself and fails loudly on drift

After writing, still inside the task, verification SHALL run and print a report: (1) row-count parity for every mapped table pair, including derived expectations for flattened tables (e.g. `score_marks` count equals reachable `elementstatus` links, `score_errors` count equals `aclass + berrors` link counts); (2) spot checksums — sum of `participations.final_score_centi`, sum of `scores.b_score_centi`, per-tablo participation counts, saved-score count per judge; (3) a recompute of the final score via `Ushu.Scoring` (from `elixir-02-scoring-core`) for EVERY participation imported as `:finished`, diffed against the stored Django `finalscore`. Any count/checksum mismatch SHALL abort (roll back). Any recompute difference greater than 0.01 SHALL abort; differences up to 0.01 are listed as warnings and abort unless `--allow-score-drift` is given. The task exits non-zero on any abort.

#### Scenario: Count mismatch

- **WHEN** the number of imported scores differs from `tablo_score` row count
- **THEN** the import rolls back and exits non-zero, printing both counts

#### Scenario: Recompute disagrees

- **WHEN** a finished participation's `Ushu.Scoring` recompute differs from the stored `finalscore` by more than 0.01
- **THEN** the import rolls back listing the participation id, stored value, and recomputed value — the discrepancy must be explained (source-data audit or scoring-core bug) before cutover

#### Scenario: Clean import of the production dump

- **WHEN** the current production dump (12 users, 168 tablos, 225 participations, 1635 scores) is imported
- **THEN** the report shows all counts matching, all finished finals reproducing, and the task exits 0
