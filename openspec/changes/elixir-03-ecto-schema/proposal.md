# Proposal: elixir-03-ecto-schema

## Why

The Elixir rewrite needs a persistence layer that encodes the competition domain with typed enums and database-enforced invariants, replacing Django's implicit magic values (integer choice fields, `FINISHED + finalscore==0` sentinel, name-matching on `'group'`/`'duilian'`) and the fragile sortedm2m positional-zip chains with explicit, constraint-backed tables.

## What Changes

- Add Ecto schemas, changesets, and SQLite migrations for every domain table:
  `users`, `countries`, `clubs`, `participants`, `element_categories`,
  `elements`, `element_category_memberships`, `combinations`,
  `combination_elements`, `error_codes`, `tablos`, `participations`, `scores`,
  `score_marks`, `score_errors`, `score_events`.
- Model all typed enums with `Ecto.Enum` (user role/category, participation
  state incl. `:no_show`, element-category `format`, error-code `kind`, age
  buckets, sex, element difficulty, mark verdict), stored as strings with DB
  `CHECK` constraints.
- Replace Django's `WrapperErrorCode`/`CombinationStatus`/`ElementStatus`
  sortedm2m chains with flat `score_marks(score_id, combination_id, element_id,
  position, verdict)` and `score_errors(score_id, error_code_id)` rows.
- Replace sortedm2m on `Combination.elements` with an explicit ordered join
  schema `combination_elements` carrying a `position` column.
- Enforce data integrity in the database: unique indexes on tablo
  (age, sex, category), participation (participant, tablo), score
  (judge, participation), username; a partial unique index guaranteeing at most
  one `:performing` participation; FK `on_delete: :restrict` mirroring Django
  `PROTECT` for history relations (judge→scores, element→score_marks,
  error_code→score_errors, country→clubs, club→participants).
- Add the append-only `score_events` audit table (new vs Django).
- `timestamps()` on every table; changesets translate constraint violations
  into user-visible errors via `unique_constraint`/`foreign_key_constraint`/
  `check_constraint`.

## Capabilities

### New Capabilities

- `ecto-domain-schema`: Ecto schemas, typed enums, and changesets for the full
  ushu competition domain, organized under the context namespaces defined in
  `elixir-04-contexts`.
- `relational-integrity`: SQLite migrations with unique indexes, the partial
  unique "one performing" index, enum CHECK constraints, and FK on_delete
  policies mirroring Django PROTECT/CASCADE semantics.

### Modified Capabilities

None — new Elixir codebase.

## Impact

- Layer 3 of 7 in the Elixir rewrite sequence. Depends on
  `elixir-01-foundation` (Phoenix project under `elixir/`, `ecto_sqlite3`,
  test skeleton). Independent of `elixir-02-scoring-core` (pure functions, no
  Repo), but shares its numeric convention: score values are stored as integer
  centi-points.
- Downstream: `elixir-04-contexts` builds all business operations on these
  schemas/changesets; `elixir-07-cutover` imports the Django SQLite DB into
  these tables preserving integer primary keys.
- New code only under `elixir/lib/ushu/**` (schemas) and
  `elixir/priv/repo/migrations/**` plus schema tests under `elixir/test/**`.
  No Django code is touched.
