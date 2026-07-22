# competition-lifecycle

Business operations that move a competition forward: registering a participant into tablos
with a snapshotted judge panel, drawing performance order, activating a performer,
finalizing or marking no-show, and computing standings. All functions live in
`Ushu.Competition` and return tagged tuples; no function raises for a domain-rule violation.

## ADDED Requirements

### Requirement: Registration creates participations with a judge-panel snapshot

`Ushu.Competition.register_participant/2` SHALL, for a given participant and element
category, create one participation per matching tablo (same age bucket and sex) in a single
transaction, and SHALL snapshot the judge panel by creating one score row (`submitted: false`)
per active, non-admin, non-main-judge user. Deactivated judges (`active: false`) MUST NOT
receive score rows. For each C-judge score row, registration SHALL also create the mark
skeleton the C card renders and `submit_c/2` later consumes: the element category's
combinations are assigned to the participation and one `score_marks` row with
`verdict: :pending` is created per combination element per C-judge score, with an identical
`position` sequence across all three C judges' cards. The function SHALL return
`{:ok, [participation]}` or `{:error, reason}` with full rollback.

#### Scenario: Standard registration snapshots 3A/4B/3C panel

- **WHEN** a participant aged `:adult` is registered into an individual category while
  3 active A judges, 4 active B judges, 3 active C judges, one main judge and one admin exist
- **THEN** one participation is created per matching tablo with exactly 10 score rows
  (3 A + 4 B + 3 C), none for the main judge or admin, all with `submitted: false`

#### Scenario: C cards get a pending mark skeleton at registration

- **WHEN** a participant is registered into a category whose combinations total N elements
  while 3 active C judges exist
- **THEN** each of the 3 C-judge score rows has exactly N `score_marks` rows with
  `verdict: :pending`, and the `position` sequence of the marks is identical across the
  three judges' cards

#### Scenario: Deactivated judge gets no card

- **WHEN** a participant is registered while a judge account has `active: false`
- **THEN** no score row is created for that judge and the panel size assumptions hold

### Requirement: C judging is skipped for young ages and non-individual formats

Registration SHALL NOT create score rows for C-category judges when the tablo's age bucket
is one of `[:y7_8, :y9_10, :y11, :y12_14]`, nor when the element category's `format` is
`:group` or `:duilian`. The decision SHALL use the `format` enum, never the category name
text (replaces Django's matching on the free-text name).

#### Scenario: Young age bucket has no C cards

- **WHEN** a participant aged `:y12_14` is registered into an individual category
- **THEN** score rows exist only for A and B judges and the participation's panel is 3A/4B

#### Scenario: Duilian never gets C cards regardless of age

- **WHEN** an `:adult` participant is registered into a category with `format: :duilian`
- **THEN** no C-judge score rows are created

### Requirement: Group registrations are deduplicated per club

For a tablo whose element category has `format: :group`, registration SHALL create at most
one participation per club: when a group participation for the participant's club already
exists in that tablo, registration SHALL skip that tablo silently (no error, no duplicate)
and continue with the remaining tablos.

#### Scenario: Second member of the same club joins a group tablo

- **WHEN** a second participant from the same club is registered into a `:group` category
- **THEN** no new participation is created in the group tablo and the result is still `{:ok, _}`

### Requirement: The draw is transactional and per-tablo

`Ushu.Competition.draw_tablo/2` SHALL shuffle the tablo's participations and assign
`draw_order` values `0..n-1` unique within that tablo, in a single transaction. `draw_all/2`
SHALL draw every tablo the same way in one transaction and SHALL skip tablos already marked
`started` unless called with `force: true`; skipped tablos SHALL be reported in the result
(`{:ok, %{drawn: [...], skipped: [...]}}`). A failure mid-draw MUST roll back all order
changes.

#### Scenario: Draw after competition started

- **WHEN** `draw_all/2` runs while some tablos have `started: true` and no `force` option
- **THEN** those tablos keep their existing order and appear in `skipped`; the rest are drawn

#### Scenario: Forced re-draw

- **WHEN** `draw_all(force: true)` runs
- **THEN** every tablo including started ones receives a fresh 0..n-1 ordering

#### Scenario: Crash mid-draw rolls back

- **WHEN** the draw transaction fails partway through
- **THEN** no participation's `draw_order` changes persist

### Requirement: Activation enforces the single-performing state machine

`Ushu.Competition.activate/2` SHALL transition a participation from `:waiting` to
`:performing` inside an `Ecto.Multi`, returning `{:error, :not_waiting}` when the
participation is in any other state and `{:error, :another_performing}` when another
participation is already `:performing`. The partial unique index on
`participations(state = 'performing')` SHALL act as the concurrency backstop: a constraint
violation is mapped to `{:error, :another_performing}`, never an unhandled exception.

#### Scenario: Concurrent double activation

- **WHEN** two processes call `activate/2` for different waiting participations at the same time
- **THEN** exactly one returns `{:ok, participation}`; the other returns
  `{:error, :another_performing}` and no judge ever sees two active performers

#### Scenario: Re-activating a finished participation

- **WHEN** `activate/2` is called for a participation in state `:finished`
- **THEN** it returns `{:error, :not_waiting}` and the state does not change

### Requirement: Finalization computes the score and closes the performance

`Ushu.Competition.finalize/3` SHALL accept the performing participation, attrs
(`%{bonus: boolean()}`) and the acting user, require every panel score row to have
`submitted: true` (otherwise `{:error, :scores_pending}`), compute the final score by loading
the panel's marks/deductions and delegating to `Ushu.Scoring` (elixir-02), and transition
`:performing -> :finished` with `final_score_centi` persisted, all in one transaction.
Calling it on a non-performing participation SHALL return `{:error, :not_performing}`.

#### Scenario: Finalize with a pending judge card

- **WHEN** the main judge finalizes while one judge's score has `submitted: false`
- **THEN** the result is `{:error, :scores_pending}` and the participation stays `:performing`

#### Scenario: Successful finalization

- **WHEN** all panel scores are saved and `finalize/3` is called with `bonus: true`
- **THEN** the participation becomes `:finished` with `final_score_centi` equal to the
  `Ushu.Scoring` assembly (A + B + 0.05 bonus + C, rounded to 2 decimals)

### Requirement: No-show is an explicit state, not a zero-score sentinel

`Ushu.Competition.mark_no_show/2` SHALL transition a performing participation to state
`:no_show` (replacing Django's `FINISHED + finalscore == 0` sentinel), mark all its score
rows `submitted: true` so no judge screen stays blocked, and leave `final_score_centi`
empty. No-show participations SHALL rank below every finished participation in standings.

#### Scenario: Marking the active performer absent

- **WHEN** `mark_no_show/2` is called for the performing participation
- **THEN** its state becomes `:no_show`, all its scores are released (`submitted: true`), and
  judges' screens return to waiting

### Requirement: Standings order by final score with the scoring-core tie-break

`Ushu.Competition.standings/1` SHALL return a tablo's participations ordered for display:
finished participations ranked by `final_score_centi` descending, ties broken by delegating to the
`Ushu.Scoring` tie-break counters (e4/e3/e2 thresholds over elements agreed as performed,
movement elements only — elixir-02 is authoritative for the counting rules); `:no_show`
after all finished; non-finished participations ordered by `draw_order`. The context SHALL
only load data — no aggregation arithmetic outside `Ushu.Scoring`.

#### Scenario: Equal finals decided by high-value elements

- **WHEN** two finished participations have equal `final_score_centi` but different counts of
  agreed-performed movement elements above the 0.3 threshold
- **THEN** the one with more such elements ranks higher

#### Scenario: Waiting participants listed in draw order

- **WHEN** a tablo has finished and waiting participations
- **THEN** finished ones appear ranked first and waiting ones follow in `draw_order` sequence
