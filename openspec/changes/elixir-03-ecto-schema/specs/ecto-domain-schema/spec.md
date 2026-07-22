# ecto-domain-schema

## ADDED Requirements

### Requirement: Every domain table has an Ecto schema with timestamps

The system SHALL define an Ecto schema for each domain table — `users`,
`countries`, `clubs`, `participants`, `element_categories`, `elements`,
`element_category_memberships`, `combinations`, `combination_elements`,
`error_codes`, `tablos`, `participations`, `scores`, `score_marks`,
`score_errors`, `score_events` — with integer primary keys (compatible with
the id-preserving importer in `elixir-07-cutover`) and `timestamps()`
(`inserted_at`/`updated_at`), except `score_events` which is append-only and
carries only `inserted_at`. Schemas SHALL live under the context namespaces
fixed by `elixir-04-contexts`: `Ushu.Accounts.User`; `Ushu.Catalog.{ElementCategory,
Element, ElementCategoryMembership, Combination, CombinationElement, ErrorCode}`;
`Ushu.Roster.{Country, Club, Participant}`; `Ushu.Competition.{Tablo,
Participation, Score, ScoreMark, ScoreError, ScoreEvent}`.

#### Scenario: Schema round-trip

- **WHEN** a valid struct of any domain schema is inserted through `Repo.insert/1` and re-read with `Repo.get/2`
- **THEN** all persisted fields round-trip unchanged and `inserted_at` is set

#### Scenario: Audit rows are insert-only

- **WHEN** code attempts to build an update changeset for a `ScoreEvent`
- **THEN** no update path exists (the schema exposes only a create changeset and has no `updated_at` column)

### Requirement: Domain enums are typed with Ecto.Enum

All formerly implicit Django magic values SHALL be modeled as `Ecto.Enum`
fields stored as strings: `users.role` `[:admin, :main_judge, :judge]`,
`users.category` `[:a, :b, :c]`, `participations.state`
`[:waiting, :performing, :finished, :no_show]`, `element_categories.format`
`[:individual, :group, :duilian]`, `error_codes.kind` `[:a, :b, :shared]`,
age buckets `[:y7_8, :y9_10, :y11, :y12_14, :y15_17, :adult]`, sex
`[:male, :female]`, `elements.difficulty` `[:a, :b, :c, :d]`, and
`score_marks.verdict` `[:pending, :performed, :failed]`. Casting a value
outside the declared set MUST make the changeset invalid.

#### Scenario: Invalid enum value rejected at cast

- **WHEN** a participation changeset is cast with `state: "doing"` (the old Django label) or any undeclared value
- **THEN** the changeset is invalid with an error on `:state` and nothing is written

#### Scenario: no_show replaces the finalscore sentinel

- **WHEN** a participation ends without the athlete appearing
- **THEN** it is representable as `state: :no_show` with `final_score_centi: nil`, and no code needs the Django `FINISHED && finalscore == 0` sentinel

### Requirement: User schema replaces Django flag overloading

The `Ushu.Accounts.User` schema SHALL carry `username` (unique, required),
`hashed_password`, `role`, `category`, and `active` (boolean, default `true`).
The changeset MUST require `category` when `role == :judge` and MUST force
`category` to `nil` for any other role, replacing Django's overloaded
`is_superuser`/`is_staff`/`category` combination. No email field or email flow
exists (offline-LAN deployment).

#### Scenario: Judge requires a category

- **WHEN** a user changeset is cast with `role: :judge` and no `category`
- **THEN** the changeset is invalid with an error on `:category`

#### Scenario: Non-judge cannot keep a category

- **WHEN** a user changeset is cast with `role: :main_judge, category: :b`
- **THEN** the persisted user has `category: nil`

### Requirement: Score values are stored as integer centi-points

All persisted score quantities — `participations.final_score_centi`,
`scores.b_score_centi`, `elements.value_centi`, `error_codes.deduction_centi`
— SHALL be integers denominated in centi-points (7.00 → 700), matching the
integer-centi arithmetic of `elixir-02-scoring-core` and eliminating float
drift. `scores.b_score_centi` SHALL be nullable, with `nil` meaning "judge
entered nothing" (a real 0 is a valid vote). `participations.final_score_centi`
SHALL be nullable and `nil` until finalization.

#### Scenario: Centi round-trip without drift

- **WHEN** a B-judge value of 8.55 is stored as `b_score_centi: 855` and read back
- **THEN** the exact integer 855 is returned (no 8.549999 float artifacts)

#### Scenario: Zero is a vote, nil is silence

- **WHEN** one score row has `b_score_centi: 0` and another has `b_score_centi: nil`
- **THEN** the schemas distinguish them: 0 participates in aggregation, nil is excluded

### Requirement: Score marks and score errors are explicit rows

C-judge element verdicts SHALL be persisted as `score_marks` rows with fields
`score_id`, `combination_id`, `element_id`, `position` (0-based, unique per
score), and `verdict` (`:pending` default). This replaces the Django
`CombinationStatus`/`ElementStatus` sortedm2m chains whose positional zip was
load-bearing: the cross-judge alignment key is now the explicit `(score_id,
position)` pair, and `combination_id` preserves the visual grouping for the
judge UI.

A-judge and B-judge recorded deductions SHALL be persisted as `score_errors`
rows (`score_id`, `error_code_id`) with NO uniqueness over the pair, so the
same error code can legitimately be recorded multiple times on one card
(replacing Django's `WrapperErrorCode` indirection). Which panel the error
belongs to is derived from the owning score's judge, not from a column.

#### Scenario: Marks align across judges by position

- **WHEN** three C-judge score cards are created for the same participation from the same combination list
- **THEN** each card contains the same number of `score_marks` rows and rows with equal `position` reference the same `element_id`

#### Scenario: Fresh card is all pending

- **WHEN** score marks are created at registration time
- **THEN** every row has `verdict: :pending`, representing the untouched state (Django's `done == 2`)

#### Scenario: Repeated error on one card

- **WHEN** an A-judge records error code 12 twice on the same score card
- **THEN** two `score_errors` rows exist and both are returned when the card is loaded

### Requirement: Combinations order their elements explicitly

The `combinations` ↔ `elements` relation SHALL be an explicit join schema
`Ushu.Catalog.CombinationElement` on table `combination_elements` with fields
`combination_id`, `element_id`, `position` (0-based), unique on
`(combination_id, position)`. Loading a combination's elements ordered by
`position` MUST reproduce the exact sequence in which they were assigned
(replacing sortedm2m). The unordered `elements` ↔ `element_categories`
relation SHALL likewise be an explicit join schema
`ElementCategoryMembership`, unique on `(element_id, element_category_id)`.

#### Scenario: Element order survives round-trip

- **WHEN** a combination is created with elements [E3, E1, E2] at positions [0, 1, 2] and re-loaded ordered by `position`
- **THEN** the elements come back as [E3, E1, E2]

#### Scenario: Duplicate position rejected

- **WHEN** a second `combination_elements` row is inserted with the same `(combination_id, position)`
- **THEN** the insert fails on the unique index and the changeset reports an error on `:position`

### Requirement: Changesets validate domain rules before the database

Each schema SHALL expose changeset functions that enforce, at minimum:
required fields (participant names/sex/age/club; element name/difficulty/value;
error-code name/number/kind; tablo age/sex/category); `error_codes.number >= 1`
and `deduction_centi >= 0`; `elements.value_centi >= 0`;
`scores.b_score_centi` between 0 and 1000 when present;
`participations.draw_order >= 0`. Validation failures MUST be reported on the
changeset without touching the database.

#### Scenario: Negative deduction rejected

- **WHEN** an error-code changeset is cast with `deduction_centi: -10`
- **THEN** the changeset is invalid with an error on `:deduction_centi` and no INSERT is attempted

#### Scenario: Out-of-range B score rejected

- **WHEN** a score changeset is cast with `b_score_centi: 1200`
- **THEN** the changeset is invalid with an error on `:b_score_centi`

### Requirement: Score events capture the audit trail

`Ushu.Competition.ScoreEvent` SHALL record who did what and when with fields:
`actor_id` (FK users, nullable), `participation_id` (FK, nullable),
`score_id` (FK, nullable), `event` enum `[:performance_started,
:score_saved, :score_reopened, :performance_finalized,
:performance_no_show]`, `payload` (map, JSON-encoded, default `%{}`), and
`inserted_at`. The `payload` SHALL denormalize enough context (e.g. judge
username, participant name, tablo label) that the event stays meaningful even
if the referenced rows are later deleted.

#### Scenario: Reopen is attributable

- **WHEN** the main judge reopens judge B2's card (per-judge reopen, incl. B judges)
- **THEN** a `score_events` row exists with `event: :score_reopened`, `actor_id` = the main judge, `score_id` = the reopened card, and a payload naming the judge

#### Scenario: Event survives participation deletion

- **WHEN** a participation referenced by score events is deleted by the secretary
- **THEN** the event rows remain readable (FKs nilified) and the payload still identifies the participant and tablo
