# relational-integrity

## ADDED Requirements

### Requirement: Competition rows are unique at the database level

Migrations SHALL create unique indexes enforcing: one `tablos` row per
`(age, sex, element_category_id)`; one `participations` row per
`(participant_id, tablo_id)`; one `scores` row per `(judge_id,
participation_id)`; one `users` row per `username`; one `error_codes` row per
`number`; one `score_marks` row per `(score_id, position)`; one
`combination_elements` row per `(combination_id, position)`; one
`element_category_memberships` row per `(element_id, element_category_id)`.
The corresponding changesets MUST declare `unique_constraint/3` with the
matching index name so a violation surfaces as a changeset error, not a raised
`Ecto.ConstraintError`.

#### Scenario: Duplicate registration blocked by the database

- **WHEN** the same participant is inserted twice into the same tablo (double-click or concurrent requests)
- **THEN** the second insert returns `{:error, changeset}` with an error on the participation uniqueness and only one row exists

#### Scenario: Duplicate score card blocked

- **WHEN** two score rows for the same `(judge, participation)` are inserted concurrently
- **THEN** exactly one row persists and the loser receives a changeset error

### Requirement: At most one participation is performing

Migrations SHALL create a partial unique index on `participations`
(`WHERE state = 'performing'`) so the database itself guarantees at most one
athlete on the carpet at any moment. The participation changeset MUST declare
the matching `unique_constraint` (custom index name) so concurrent activation
attempts fail cleanly; the transactional activation flow itself (Ecto.Multi
state machine) is defined in `elixir-04-contexts`.

#### Scenario: Concurrent activation

- **WHEN** two transactions each try to set a different participation to `:performing` while none is active
- **THEN** exactly one commit succeeds; the other receives a changeset error on the performing-uniqueness constraint

#### Scenario: Non-performing states are unlimited

- **WHEN** many participations hold states `:waiting`, `:finished`, or `:no_show`
- **THEN** the partial index does not restrict them

### Requirement: History relations restrict deletion (Django PROTECT parity)

Migrations SHALL declare FK references with `on_delete: :restrict` wherever
Django used `PROTECT`: `scores.judge_id → users`, `score_marks.element_id →
elements`, `score_marks.combination_id → combinations`,
`score_errors.error_code_id → error_codes`, `participants.club_id → clubs`,
`clubs.country_id → countries`, `combination_elements.element_id → elements`.
Deactivation (`users.active = false`), not deletion, is the supported path for
retiring judges. Changesets on the parent side SHALL declare
`foreign_key_constraint/3` with `match: :prefix` or the exact name so a blocked
delete is reportable.

#### Scenario: Deleting a judge with recorded scores

- **WHEN** a delete is attempted for a user referenced by any `scores` row
- **THEN** the database refuses the delete and score history stays intact

#### Scenario: Deleting an element used in past results

- **WHEN** a delete is attempted for an element referenced by any `score_marks` or `combination_elements` row
- **THEN** the delete is refused

### Requirement: Owned children cascade with their parent

Migrations SHALL declare `on_delete: :delete_all` (at the DB level) for
ownership chains, mirroring Django CASCADE: `tablos.element_category_id →
element_categories`; `participations.participant_id → participants` and
`participations.tablo_id → tablos`; `scores.participation_id →
participations`; `score_marks.score_id → scores`; `score_errors.score_id →
scores`; `combination_elements.combination_id → combinations`;
`element_category_memberships` from both sides. `score_events.actor_id`,
`score_events.participation_id`, and `score_events.score_id` SHALL use
`on_delete: :nilify_all` so audit rows outlive the rows they describe.

#### Scenario: Deleting a participation cleans its scoring tree

- **WHEN** a participation with score cards, marks, and error rows is deleted
- **THEN** its `scores`, `score_marks`, and `score_errors` rows are removed by the database, and its `score_events` rows remain with `participation_id = NULL`

#### Scenario: Deleting an element category removes its tablos

- **WHEN** an `element_categories` row is deleted
- **THEN** all its `tablos` rows (and transitively their participations and score trees) are removed

### Requirement: Enum columns carry CHECK constraints

For every `Ecto.Enum` string column, the migration SHALL add a `CHECK`
constraint restricting the column to the declared value set (e.g.
`participations.state IN ('waiting','performing','finished','no_show')`), so
raw SQL — including the `elixir-07-cutover` importer — cannot write undeclared
values. Changesets SHALL declare the matching `check_constraint/3`.

#### Scenario: Raw SQL cannot write a rogue state

- **WHEN** a raw `INSERT`/`UPDATE` sets `participations.state = 'doing'`
- **THEN** SQLite rejects the statement on the CHECK constraint

#### Scenario: Importer maps before insert

- **WHEN** the cutover importer writes rows converted from Django integers (ages 4,0,5,1,2,3 → y7_8, y9_10, y11, y12_14, y15_17, adult)
- **THEN** only mapped string values pass the CHECK constraints

### Requirement: Foreign keys are enforced on every connection

Because SQLite requires `PRAGMA foreign_keys = ON` per connection, the Repo
configuration (established in `elixir-01-foundation`) MUST keep foreign-key
enforcement enabled, and this change SHALL include a regression test proving
an orphaned insert (e.g. a score with a non-existent `participation_id`) is
rejected at the database.

#### Scenario: Orphan insert rejected

- **WHEN** a `scores` row is inserted with a `participation_id` that matches no participation
- **THEN** the insert fails with a foreign-key violation

### Requirement: Migrations run clean, ordered, and reversible

The migration set SHALL apply on a fresh SQLite database with a single
`mix ecto.migrate` in dependency order (users → catalog → roster → competition
→ scoring/audit), and each migration SHALL be reversible (`change/0` with
DSL-reversible operations, or explicit `up/down`) so `mix ecto.rollback --all`
returns to an empty schema. Test-suite setup (`mix test`) MUST run the full
migration set via the sandbox.

#### Scenario: Fresh setup

- **WHEN** `mix ecto.create && mix ecto.migrate` runs against a new database file
- **THEN** all migrations apply without error and every table, index, and constraint from this spec exists

#### Scenario: Full rollback

- **WHEN** `mix ecto.rollback --all` runs after a full migrate
- **THEN** all domain tables are dropped without error
