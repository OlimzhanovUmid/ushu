# elixir-04-contexts — Tasks

## 1. Scaffolding & shared plumbing

- [ ] 1.1 Create context module skeletons `Ushu.Catalog`, `Ushu.Roster`, `Ushu.Competition`,
      `Ushu.Competition.Audit` with `@moduledoc` stating each context's boundary
- [ ] 1.2 Add `Ushu.Accounts.list_panel_judges/0` (active users with role `:judge`, ordered
      by username) with a test covering exclusion of admin/main_judge/deactivated users
- [ ] 1.3 Implement `Ushu.Competition.Audit.event/3..4` building a `score_events` insert
      (actor id, action atom, participation/score ids, payload map) usable inside any Multi
- [ ] 1.4 Implement the private `broadcast/1` helper on `Ushu.PubSub`, topic `"competition"`,
      called only after `{:ok, _} = Repo.transaction(...)` (event names per elixir-05)

## 2. Catalog & Roster

- [ ] 2.1 Implement `Ushu.Catalog.create_element_category/1` creating the category plus its
      12 tablos (6 age buckets x 2 sexes) in one Multi; idempotent under the unique index
- [ ] 2.2 Implement `Ushu.Catalog.list_error_codes/1` returning codes of the given kind plus
      `:shared`, ordered by number
- [ ] 2.3 Implement `Ushu.Roster.create_participant/1` and `Ushu.Roster.delete_participation/2`
      (refuse `:performing`; delete scores + participation in one Multi with audit event)
- [ ] 2.4 Tests: category creation produces exactly 12 tablos and re-run adds none;
      delete_participation refuses the performing row

## 3. Registration

- [ ] 3.1 Implement `Ushu.Competition.register_participant/2`: one participation per
      matching tablo (age+sex), full rollback on any failure
- [ ] 3.2 Panel snapshot inside the same Multi: score rows (`submitted: false`) for every
      eligible active judge; C-skip for `[:y7_8, :y9_10, :y11, :y12_14]` and for
      `format in [:group, :duilian]`; skip group tablos where the club already participates
- [ ] 3.3 C-mark skeleton inside the same Multi: assign the category's combinations and
      create one `:pending` `score_marks` row per combination element per C-judge score,
      with an identical `position` sequence across the three C judges' cards (consumed by
      `submit_c/2`)
- [ ] 3.4 Tests: adult individual registration yields 3A/4B/3C rows; each C card has one
      `:pending` mark per combination element with matching `position` sequences across
      judges; `:y12_14` yields A+B only; duilian yields A+B for adults; second club member
      skipped in group tablo; deactivated judge gets no row; duplicate registration fails
      on the unique index

## 4. Draw

- [ ] 4.1 Implement `draw_tablo/2` (tablo id + actor; shuffle, `draw_order` 0..n-1,
      transaction, refuse `started: true`) with an injectable shuffle function for
      deterministic tests
- [ ] 4.2 Implement `draw_all/2` (opts + actor) with `force:` option returning
      `%{drawn: _, skipped: _}`
- [ ] 4.3 Tests: per-tablo numbering independent across tablos; started tablo skipped
      without force and drawn with force; mid-draw failure rolls back all orders

## 5. Activation state machine

- [ ] 5.1 Implement `activate/2` (participation id + actor) as a Multi
      (`:waiting -> :performing`), mapping the partial
      unique index violation to `{:error, :another_performing}` and non-waiting states to
      `{:error, :not_waiting}`; implement `active_participation/0`
- [ ] 5.2 Tests: happy path; finished participation rejected; two concurrent activations
      yield exactly one `{:ok, _}` (race the constraint in two tasks/transactions)

## 6. Judge submissions

- [ ] 6.1 Implement the shared resolver (active participation x judge -> own score row or
      `{:error, :no_active}`) used by all three submit functions
- [ ] 6.2 Implement `submit_a/2`: replace `score_errors`, kinds `[:a, :shared]` only,
      duplicates preserved, reject-not-drop invalid ids, `submitted: true`, audit + broadcast
- [ ] 6.3 Implement `submit_b/2`: base score (0.0 is a vote), kinds `[:b, :shared]`,
      `{:error, :invalid_score}` on unparseable base, `submitted: true`, audit + broadcast
- [ ] 6.4 Implement `submit_c/2`: verify all verdict ids belong to the judge's own marks
      (`{:not_owner, ids}`), apply verdicts, completeness gate (`{:unmarked, ids}` with
      partial verdicts persisted, `submitted` stays false), audit + broadcast on save
- [ ] 6.5 Tests: no-active race returns `{:error, :no_active}` for all three; forged mark id
      rejected without writes; B zero stored; C partial submit keeps progress and names
      unmarked ids; full C submit saves; wrong-kind codes rejected atomically

## 7. Finalize, no-show, reopen

- [ ] 7.1 Implement `finalize/3` (participation id, attrs, actor): require all panel scores
      submitted (`{:error, :scores_pending}`), load marks/deductions in one preloaded query,
      delegate assembly to `Ushu.Scoring`, persist `final_score_centi` + `:finished` +
      bonus flag in one Multi
- [ ] 7.2 Implement `mark_no_show/2` (participation id + actor): `:performing -> :no_show`,
      all scores `submitted: true`, `final_score_centi` nil
- [ ] 7.3 Implement `reopen_judge/2`: single score `submitted -> false` preserving content, any
      judge category incl. B, only while participation `:performing`, actor recorded
- [ ] 7.4 Tests: finalize blocked by one pending card; finalized number matches a known
      elixir-02 golden case incl. bonus; no_show releases judge screens; B-judge reopen
      flips only that card and keeps its base score; reopen on finished returns
      `{:error, :not_active}`

## 8. Standings

- [ ] 8.1 Implement `standings/1`: finished ranked by `final_score_centi` with `Ushu.Scoring`
      tie-break counters, `:no_show` after finished, others in draw order; assign ranks
- [ ] 8.2 Tests: equal finals ordered by e4 then e3 then e2 counters (movement elements,
      agreed-performed only); no_show ranks below zero-adjacent finished scores; waiting
      rows keep draw order

## 9. Accounts user management

- [ ] 9.1 Implement `Ushu.Accounts.create_user/1`, `deactivate_user/1` and
      `reset_password/2` (used by the elixir-06 admin screens), returning
      `{:ok, User.t()} | {:error, Ecto.Changeset.t()}`
- [ ] 9.2 Tests: created user appears in `list_panel_judges/0` when role `:judge` and
      active; deactivated user disappears from the panel; reset password hashes and
      verifies with the new password

## 10. Audit & events acceptance

- [ ] 10.1 Test: every mutating function inserts exactly one `score_events` row with correct
      actor/action/ids, and a failed mutation inserts none
- [ ] 10.2 Test: subscribe to `"competition"` in tests and assert each mutation broadcasts
      exactly its catalog event post-commit, and rejected submissions broadcast nothing
- [ ] 10.3 Run `mix format --check-formatted`, `mix credo --strict`, `mix test` green; verify
      no `Repo` call exists in `Ushu.Scoring` and no aggregation arithmetic in contexts
