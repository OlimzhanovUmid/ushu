# judge-submission

Judge scorecard operations in `Ushu.Competition`: A/B/C submissions and per-judge reopen.
Ownership is by construction — every submit function takes the authenticated judge and
resolves that judge's own score row for the currently performing participation; client-sent
ids can never address another judge's data.

## ADDED Requirements

### Requirement: Submissions resolve the judge's own card for the active performance

`submit_a/2`, `submit_b/2` and `submit_c/2` SHALL take the submitting judge (`%User{}`) as
their first argument and operate exclusively on the score row belonging to that judge for
the participation currently in state `:performing`. When no participation is performing, or
the judge has no score row for it (e.g. C judge on a young-age tablo), the functions SHALL
return `{:error, :no_active}` without raising and without mutating anything — the
finalize-while-form-open race MUST degrade to this error, never a crash.

#### Scenario: Submit after finalization

- **WHEN** a judge submits a score after the main judge finalized the performance
- **THEN** the result is `{:error, :no_active}` and no score row changes

#### Scenario: Forged mark id belonging to another judge

- **WHEN** a C judge's submission payload includes a `score_marks` id owned by another
  judge's score
- **THEN** that row is not modified and the submission returns an error identifying the
  rejected ids

### Requirement: A submission validates error codes by kind

`submit_a(judge, error_code_ids)` SHALL replace the judge's recorded A deductions with the
given codes and set `submitted: true`, accepting only error codes whose `kind` is `:a` or
`:shared` (the `kind` enum replaces Django's numeric ranges 1–79/90+). Unknown ids or codes
of kind `:b` SHALL cause `{:error, {:invalid_codes, ids}}` with no partial write (reject,
not warn-and-drop). Duplicate codes SHALL be preserved as separate `score_errors` rows (the
same error can be committed twice).

#### Scenario: B-kind code on an A card

- **WHEN** an A judge submits a list containing a `kind: :b` error code
- **THEN** the submission returns `{:error, {:invalid_codes, [id]}}` and the previous card
  content is unchanged

#### Scenario: Repeated error counts twice

- **WHEN** an A judge submits the same error code id twice
- **THEN** two `score_errors` rows are recorded for the card

### Requirement: B submission stores a base score with kind-checked deductions

`submit_b(judge, %{base: score, error_code_ids: ids})` SHALL store the numeric base score
and replace the judge's B deductions, accepting only codes of kind `:b` or `:shared`, then
set `submitted: true`. A base of exactly `0.0` is a real vote and MUST be stored (never treated
as "not submitted"). An unparseable/absent base with no errors SHALL return
`{:error, :invalid_score}`.

#### Scenario: Zero is a vote

- **WHEN** a B judge submits base `0.0`
- **THEN** the score saves and later aggregation (elixir-02) includes it as a submitted value

#### Scenario: A-kind code on a B card

- **WHEN** a B judge submits an error code of kind `:a`
- **THEN** the submission is rejected with `{:error, {:invalid_codes, [id]}}`

### Requirement: C submission is gated on completeness

`submit_c(judge, verdicts)` SHALL accept a map of the judge's own `score_marks` ids to
`:performed | :failed`, apply the verdicts, and set `submitted: true` only when EVERY mark of
that judge's card is `:performed` or `:failed`. If any mark remains `:pending`, the function
SHALL persist the verdicts given so far but return `{:error, {:unmarked, mark_ids}}` with
`submitted` still `false`, so the UI can highlight the missing elements. `:pending` verdicts in
the payload are invalid input.

#### Scenario: Submit with an unmarked element

- **WHEN** a C judge submits verdicts leaving one mark `:pending`
- **THEN** the card is not saved, the result names the unmarked mark ids, and the card stays open

#### Scenario: Fully marked submit

- **WHEN** every mark on the card is `:performed` or `:failed`
- **THEN** the score row becomes `submitted: true` and the judge returns to the waiting state

### Requirement: Any judge's card can be reopened individually

`Ushu.Competition.reopen_judge/2` SHALL take a score id and the acting user, set that single
score's `submitted` to `false` while PRESERVING the entered marks/deductions/base score (the
judge corrects, not re-enters), and work for a judge of ANY category — A, B or C (per-judge
B reopen is an owner wishlist item Django lacked). It SHALL apply only while the score's
participation is `:performing`; otherwise return `{:error, :not_active}`. Authorization
(main-judge role) is enforced by the caller layer (elixir-06 plugs/on_mount), but the
function SHALL record the actor in the audit event.

#### Scenario: Reopen a B judge only

- **WHEN** the main judge reopens one B judge's saved card during a performance
- **THEN** only that score's `submitted` becomes `false`, its base score and errors remain
  visible for correction, and the other judges' cards stay saved

#### Scenario: Reopen after finalization

- **WHEN** `reopen_judge/2` is called for a score whose participation is `:finished`
- **THEN** it returns `{:error, :not_active}` and nothing changes
