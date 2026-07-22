# Tasks: elixir-03-ecto-schema

## 1. Users & auth schema

- [ ] 1.1 Run `mix phx.gen.auth Accounts User users` inside `elixir/`, commit the generated baseline, then strip email/confirmation/reset artifacts (keep hashing + token schema files parked for layer 06)
- [ ] 1.2 Adapt the users migration: `username` (unique, `COLLATE NOCASE`), `hashed_password`, `role` TEXT + CHECK (`admin|main_judge|judge`), `category` TEXT nullable + CHECK (`a|b|c`), `active` boolean default true, timestamps
- [ ] 1.3 Adapt `Ushu.Accounts.User` schema: `Ecto.Enum` for `role`/`category`; changeset requires `category` iff `role == :judge` and forces it to nil otherwise; username format/length validation + `unique_constraint`
- [ ] 1.4 Tests: role/category coupling, duplicate username (case-insensitive) returns a changeset error

## 2. Catalog schemas (elements, combinations, error codes)

- [ ] 2.1 Migration `create_catalog`: `element_categories` (name unique, `format` TEXT + CHECK `individual|group|duilian`), `elements` (name, `difficulty` TEXT + CHECK `a|b|c|d`, `value_centi` integer, `landing` boolean, `symbol`), `error_codes` (name, `number` unique, `deduction_centi`, `kind` TEXT + CHECK `a|b|shared`), all with timestamps
- [ ] 2.2 Migration (same file): `element_category_memberships` (unique `(element_id, element_category_id)`, both FKs `on_delete: :delete_all`) and `combinations` + `combination_elements` (`position`, unique `(combination_id, position)`, element FK `on_delete: :restrict`, combination FK `:delete_all`)
- [ ] 2.3 Schemas + changesets: `ElementCategory`, `Element` (value_centi >= 0), `ElementCategoryMembership`, `Combination`, `CombinationElement` (position >= 0), `ErrorCode` (number >= 1, deduction_centi >= 0); `has_many ... through` for element↔category and ordered combination→elements preload by `position`
- [ ] 2.4 Tests: combination element order round-trips [E3, E1, E2]; duplicate `(combination_id, position)` is a changeset error; deleting an element used in a combination is refused

## 3. Roster schemas (countries, clubs, participants)

- [ ] 3.1 Migration `create_roster`: `countries` (name_ru/name_en, short codes, `flag_path`), `clubs` (name, country FK `on_delete: :restrict`), `participants` (name_ru/name_en, `sex` TEXT + CHECK `male|female`, `age` TEXT + CHECK of the six bucket values, club FK `on_delete: :restrict`), timestamps
- [ ] 3.2 Schemas + changesets: `Country`, `Club`, `Participant` (required names/sex/age/club; `Ecto.Enum` for sex/age)
- [ ] 3.3 Tests: invalid age bucket rejected at cast; deleting a country with clubs / a club with participants is refused at the DB

## 4. Competition schemas (tablos, participations)

- [ ] 4.1 Migration `create_competition`: `tablos` (`age`/`sex` TEXT + CHECKs, category FK `on_delete: :delete_all`, `started` boolean, unique `(age, sex, element_category_id)`), `participations` (participant/tablo FKs `:delete_all`, `draw_order` integer, `state` TEXT + CHECK `waiting|performing|finished|no_show` default `waiting`, `final_score_centi` nullable integer, `bonus` boolean, `group_entry` boolean, unique `(participant_id, tablo_id)`), timestamps
- [ ] 4.2 Migration (same file): partial unique index on `participations(state) WHERE state = 'performing'` with a stable name (e.g. `one_performing_participation`)
- [ ] 4.3 Schemas + changesets: `Tablo` and `Participation` (`Ecto.Enum` state; draw_order >= 0; `unique_constraint`s for both indexes incl. the partial one; `check_constraint` for state)
- [ ] 4.4 Tests: duplicate `(participant, tablo)` insert returns changeset error; two `:performing` rows impossible (second insert/update errors on the partial index); `state: "doing"` fails at cast AND raw SQL `'doing'` fails the CHECK

## 5. Scoring & audit schemas (scores, marks, errors, events)

- [ ] 5.1 Migration `create_scoring`: `scores` (judge FK `on_delete: :restrict`, participation FK `:delete_all`, `b_score_centi` nullable integer, `submitted` boolean default false, unique `(judge_id, participation_id)`), timestamps
- [ ] 5.2 Migration (same file): `score_marks` (score FK `:delete_all`, combination FK `:restrict`, element FK `:restrict`, `position` integer, `verdict` TEXT + CHECK `pending|performed|failed` default `pending`, unique `(score_id, position)`); `score_errors` (score FK `:delete_all`, error_code FK `:restrict`, NO uniqueness); `score_events` (actor/participation/score FKs all `on_delete: :nilify_all` and nullable, `event` TEXT + CHECK of the five event values, `payload` JSON-map default `{}`, `inserted_at` only)
- [ ] 5.3 Schemas + changesets: `Score` (b_score_centi in 0..1000 when present), `ScoreMark`, `ScoreError`, `ScoreEvent` (create-only changeset, required `event`, payload map)
- [ ] 5.4 Tests: duplicate `(judge, participation)` is a changeset error; duplicate error-code rows on one score are allowed; deleting a judge with scores is refused; deleting a participation cascades scores→marks/errors while its `score_events` survive with nilified FKs
- [ ] 5.5 Tests: `(score_id, position)` uniqueness; marks default to `:pending`; three same-shape cards align by `position` (same element per position across cards)

## 6. Cross-cutting integrity & verification

- [ ] 6.1 Regression test: `PRAGMA foreign_keys` is ON for pooled connections — inserting a score with a bogus `participation_id` fails with a foreign-key error
- [ ] 6.2 Constraint-name audit test helper: for every custom-named unique/check constraint, trigger the violation and assert it surfaces as `{:error, %Ecto.Changeset{}}` (not a raised `Ecto.ConstraintError`)
- [ ] 6.3 Verify `mix ecto.create && mix ecto.migrate` on a fresh DB, then `mix ecto.rollback --all` back to empty; fix any irreversible operation
- [ ] 6.4 Run `mix format --check-formatted`, `mix credo`, and the full `mix test` suite green
- [ ] 6.5 Write the Russian explainer `docs/elixir-rewrite/03-ecto-schema.md` (Repo/Schema/Changeset/Query vs Django ORM and JPA; migrations DSL; changeset vs DB constraints; explicit join schemas) and cross-check its old→new mapping table against the final migrations
