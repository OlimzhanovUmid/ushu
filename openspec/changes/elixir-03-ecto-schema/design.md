# Design: elixir-03-ecto-schema

## Context

Layer 3 of the 7-layer Elixir rewrite. `elixir-01-foundation` provides the
Phoenix 1.8 project under `elixir/` with `ecto_sqlite3` (SQLite + WAL) and the
test skeleton; `elixir-02-scoring-core` defines pure scoring functions that
consume plain structs in integer centi-points. This change lays down every
Ecto schema, changeset, and migration the contexts (`elixir-04-contexts`) and
the importer (`elixir-07-cutover`) will build on.

The Django model being replaced (pinned in
`openspec/changes/stabilize-django/`) encodes critical rules implicitly:
integer choice fields whose labels drifted from constants, a
`FINISHED + finalscore==0` sentinel for no-shows, category matching on the
free-text names `'group'`/`'duilian'`, error-code semantics hidden in numeric
ranges, and a positional zip across sortedm2m chains
(`Score.cclass → CombinationStatus.statuses → ElementStatus`) that silently
breaks if any judge's chain diverges. All of these become explicit columns,
enums, and constraints here.

## Goals / Non-Goals

**Goals**

- One Ecto schema + changeset per domain table; one dependency-ordered,
  reversible migration set.
- Database-enforced invariants: uniqueness (tablo/participation/score/
  username/positions), partial unique `:performing`, FK restrict for history,
  enum CHECK constraints.
- Typed enums for everything that was a magic value in Django.
- Exact structural parity with what the cutover importer (07) needs: integer
  PKs preserved, enum string values fixed here.

**Non-Goals**

- No business operations (registration, draw, activation, submission,
  finalize, reopen, standings) — that is `elixir-04-contexts`. Changesets here
  validate shape, not workflow.
- No PubSub/LiveView/auth pages (05/06). No data import (07).
- No scoring math — `Ushu.Scoring` (02) stays Repo-free; schemas only feed it.

## Decisions

**D1. Schemas live under their future context namespaces.**
`Ushu.Accounts.User`; `Ushu.Catalog.{ElementCategory, Element,
ElementCategoryMembership, Combination, CombinationElement, ErrorCode}`;
`Ushu.Roster.{Country, Club, Participant}`; `Ushu.Competition.{Tablo,
Participation, Score, ScoreMark, ScoreError, ScoreEvent}`.
*Rationale:* `elixir-04-contexts` names these four contexts; placing schemas
there now avoids a rename churn and matches Phoenix convention (schema modules
inside their context directory). *Alternative:* a flat `Ushu.Schema.*`
namespace — rejected, fights the Phoenix context idiom and forces aliasing
gymnastics later.

**D2. All score quantities are integer centi-points.**
`participations.final_score_centi`, `scores.b_score_centi`,
`elements.value_centi`, `error_codes.deduction_centi` — integers, 7.00 ⇒ 700.
*Rationale:* the pinned Django rule already computes the final score "in
integer centi-points rounded to 2dp" precisely because floats drifted; SQLite
has no decimal type (Ecto `:decimal` maps to TEXT in ecto_sqlite3), and layer
02's pure core computes in centi ints. Storing the same unit removes every
conversion boundary except display formatting. *Alternatives:* `:float`
(rejected — reintroduces the drift Django fought), `:decimal` (rejected —
TEXT-backed on SQLite, slower comparisons, still needs conversion for 02).

**D3. `Ecto.Enum` over string columns + DB CHECK constraints.**
Schema fields use `Ecto.Enum, values: [...]`; migrations store TEXT and add
`CHECK (col IN (...))`. *Rationale:* atoms in code, readable values in the DB
file (helpful when inspecting the SQLite DB during a tournament), and the
CHECK is defense-in-depth against raw-SQL writes — most importantly the
07 importer. *Alternatives:* integer-coded enums mirroring Django (rejected —
perpetuates the drifted-label problem this rewrite exists to kill); no CHECK
(rejected — the importer is exactly the raw path that needs the net).

**D4. Explicit join schemas instead of `many_to_many`.**
`combination_elements(combination_id, element_id, position)` replaces
sortedm2m; `element_category_memberships(element_id, element_category_id)`
replaces the plain M2M. *Rationale:* sortedm2m's ordering was load-bearing;
Ecto's `many_to_many` cannot carry a `position` column, while an explicit
schema makes order a first-class, uniquely-indexed fact. For the unordered
element↔category relation the explicit schema keeps one consistent pattern
and gives the importer a named table. `has_many :combination_elements` +
`has_many :elements, through: [...]` still gives ergonomic preloads (ordering
applied via a `preload_order` / explicit query on `position`).
*Alternative:* `many_to_many` with `join_keys` (rejected — no extra columns,
no order).

**D5. `score_marks` flattens the Django chain and adds `combination_id`.**
The brief fixes `score_marks(score_id, element_id, position, verdict)`; we add
`combination_id` (FK restrict). *Rationale:* the cross-judge alignment key is
`(score_id, position)` — flat, unique, and directly zippable in the C
aggregation — but the judge UI still renders marks grouped by combination, and
deriving group boundaries from positions alone would re-create implicit
structure. One nullable-free FK keeps display grouping explicit without
touching the alignment contract. *Alternative:* exactly the brief's four
columns (workable, but the UI would need a parallel lookup of combination
lengths; rejected as hidden coupling).

**D6. on_delete policy: restrict = Django PROTECT, delete_all = CASCADE,
nilify_all for audit.**
Restrict: `scores.judge_id`, `score_marks.element_id`,
`score_marks.combination_id`, `score_errors.error_code_id`,
`participants.club_id`, `clubs.country_id`, `combination_elements.element_id`.
Delete-all: `tablos.element_category_id`, `participations.{participant_id,
tablo_id}`, `scores.participation_id`, `score_marks.score_id`,
`score_errors.score_id`, `combination_elements.combination_id`, both FKs of
`element_category_memberships`. Nilify: all three FKs on `score_events`, whose
`payload` denormalizes actor/participant/tablo names so the audit line stays
meaningful after deletion. *Rationale:* mirrors the pinned `data-integrity`
spec (history is protected; owned trees die with their parent) while keeping
the audit trail deletion-proof. Enforcement lives in the DB (`references(...,
on_delete:)`), not in `Ecto.Schema` association options, because raw deletes
must obey it too. *Alternative:* restrict on `score_events` FKs (rejected —
would make legitimate secretary deletions impossible once audited).

**D7. Single-performing invariant as a partial unique index.**
`CREATE UNIQUE INDEX one_performing_participation ON participations (state)
WHERE state = 'performing'` (Ecto: `unique_index(..., where: "state =
'performing'", name: ...)`). The changeset declares the matching
`unique_constraint`. *Rationale:* SQLite supports partial indexes natively;
this is the same trick the stabilized Django app uses, and it makes the
invariant hold even against buggy application code. The guarded transition
(Ecto.Multi: verify `:waiting`, set `:performing`, insert audit event) is
04's job; the index is the backstop. *Alternative:* advisory locking in a
GenServer (rejected as the *enforcement* mechanism — process state can drift
from DB truth; a GenServer may still serialize UX in 04/05).

**D8. `users` via `mix phx.gen.auth`, adapted to username-only.**
Run the generator, then strip email/confirmation/reset flows; keep `username`
(unique, `citext`-like handled as `COLLATE NOCASE` unique index),
`hashed_password` (pbkdf2_elixir), `role`, `category`, `active`. The changeset
enforces `category` required iff `role == :judge`, forced nil otherwise.
*Rationale:* gen_auth gives battle-tested password hashing and session
plumbing (the session/LiveView halves land in 06); adapting beats hand-rolling
crypto. Hashing uses `pbkdf2_elixir` (pure Elixir) instead of the generator's
default `bcrypt_elixir`, which is a NIF requiring a C compiler toolchain the
Windows competition laptop does not have; `elixir-07-cutover` (per-event
password resets) depends on this library choice. Passwords are not imported from Django (07 resets them per event).
*Alternative:* hand-written auth schema (rejected — needless crypto risk).

**D9. Rename columns that were SQL keywords or transliterations.**
`order` → `draw_order`, `group` → `group_entry`, `prizemlenie` → `landing`
(boolean on elements), Django `Score.saved` → `submitted`, `Country.image` →
`flag_path` (string; media copied in 07). *Rationale:* `order`/`group` are SQL
keywords that force quoting in every raw query (and the importer is raw);
`landing` matches the scoring core's terminology (`MAX_LANDING_SCORE`).
The 07 importer owns the old→new column mapping.

**D10. Five dependency-ordered migrations, each reversible.**
`001_create_users`, `002_create_catalog` (element_categories, elements,
memberships, combinations, combination_elements, error_codes),
`003_create_roster` (countries, clubs, participants), `004_create_competition`
(tablos, participations), `005_create_scoring` (scores, score_marks,
score_errors, score_events). *Rationale:* group-per-bounded-area keeps each
file reviewable and rollback meaningful; strict ordering satisfies FK
creation. *Alternative:* one mega-migration (rejected — unreviewable) or
one-per-table (rejected — 16 files with interleaved FK ordering pain).

**D11. Timestamps everywhere; `score_events` is append-only.**
Every table gets `timestamps()`; `score_events` uses
`timestamps(updated_at: false)` and its schema exposes only a create
changeset. *Rationale:* `inserted_at`/`updated_at` cost nothing and answer
"when did this row last change" during protests; an audit row that can be
updated is not an audit row.

## Risks / Trade-offs

- [SQLite enforces FKs only with `PRAGMA foreign_keys = ON` per connection]
  → Foundation config must keep it on (exqlite exposes the pragma); this
  change adds a regression test inserting an orphan row and asserting a
  constraint error, so a config regression fails CI immediately.
- [Changeset `unique_constraint`/`check_constraint` names must exactly match
  index/constraint names in migrations, or violations raise instead of
  returning `{:error, changeset}`] → every custom-named index gets a test that
  triggers the violation and asserts it lands on the changeset.
- [`delete_all` cascades in SQLite are DB-level; Ecto schema-level
  `on_delete` options would silently not apply on raw deletes] → all cascade/
  restrict behavior is declared in `references(..., on_delete:)` inside
  migrations, never only in schema associations; tests delete via raw
  `Repo.delete` to prove DB-level behavior.
- [Adding `combination_id` to score_marks slightly widens the brief's minimal
  column set] → documented here (D5); alignment key stays `(score_id,
  position)` so 02/04 are unaffected.
- [Integer centi-points push a formatting duty to the UI layer (06)] →
  a single `Ushu.Scoring.Format` helper (or similar, owned by 02/06) converts
  centi → "7.00"; schemas never store formatted strings.
- [phx.gen.auth generates more than layer 03 needs (session tokens, LiveViews)]
  → generated session/UI files are parked for 06; only the schema, migration,
  and changeset adaptations are in scope here, and tasks call that boundary
  out explicitly.

## Migration Plan

Fresh database only — no in-place upgrade of a production DB exists yet
(the Django SQLite DB is imported wholesale by `elixir-07-cutover`, which
preserves integer PKs and maps Django's integer enums / error-code numeric
ranges to the string enum values fixed in this change). Rollback of this
layer is `mix ecto.rollback --all` on a dev/test database.

## Open Questions

- Should `users.username` uniqueness be case-insensitive? **Default: yes**
  (unique index with `COLLATE NOCASE`) — prevents `Judge1`/`judge1` twins at
  an offline event where accounts are created in a hurry.
- Should `tablos.started` survive as a boolean, given 04 may derive it?
  **Default: yes, keep the column** — the draw guard ("refuse re-draw unless
  forced") in the pinned spec reads it directly, and the importer has a value
  for it.
