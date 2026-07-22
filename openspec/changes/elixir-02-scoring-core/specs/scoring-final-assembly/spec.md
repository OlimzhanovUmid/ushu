# scoring-final-assembly

Assembly of the final score from the three panel aggregates in integer
centi-points, the bonus, the no-show zero result, and the e4/e3/e2 medal
tie-break. Golden numbers come verbatim from `tablo/test_scoring_golden.py`.

## ADDED Requirements

### Requirement: Final score is assembled in integer centi-points

`assemble/1` SHALL compute the final score as the integer centi-point sum
`a_score_c + b_contribution_c + c_score_c` and expose it in an
`Ushu.Scoring.Result` struct carrying the per-panel aggregates (agreed A
errors, B aggregate, agreed C marks), the centi total (`final_c`) and the
display value (`final_c / 100`, two decimals). The B contribution SHALL be the
`aggregate_b/1` result ROUNDED to the nearest centi-point — never truncated —
so binary-float artifacts cannot shave 0.01 off the final score.

#### Scenario: Full panel end-to-end (golden)

- **WHEN** the A panel agrees on one 1.00 error (junior max 7.00 → 600), the B
  panel submits [9.5, 9.6, 9.6, 9.7] (repeated 9.6 → 960) and all C judges
  mark both elements performed (→ 200)
- **THEN** the result is A 6.0, B 9.6, C 2.0, `final_c == 1760`, displayed
  final 17.6

#### Scenario: Truncation artifact prevented (golden)

- **WHEN** the B panel submits [9.57, 9.59, 9.4, 9.7] (distinct → trimmed mean
  9.58) with A 600 and C 200
- **THEN** the B contribution is exactly 958 centi-points and the final is
  17.58 — not 17.57

### Requirement: Bonus adds five centi-points to the B contribution

When the participation carries the bonus flag, `assemble/1` SHALL add exactly
5 centi-points (0.05) to the B contribution before summing, and the displayed
B value SHALL include the bonus.

#### Scenario: Bonus end-to-end (golden)

- **WHEN** the same full panel as above (600 + 960 + 200) has `bonus: true`
- **THEN** `final_c == 1765` (600 + 965 + 200) and the displayed final is 17.65

### Requirement: Assembly reports completeness

`assemble/1` SHALL receive each score's `saved` flag and expose
`complete? :: boolean` on the result — true only when EVERY panel score is
saved. This is the pure-core input to the main judge's finalize gate enforced
by `elixir-04-contexts`.

#### Scenario: Unsaved card blocks completeness

- **WHEN** one C judge's score has `saved: false`
- **THEN** the assembled result has `complete?: false`

### Requirement: A no-show participation assembles to the zero result

The core SHALL provide a canonical zero result (`Result.no_show/0` or
`assemble/1` on state `:no_show`) with all aggregates empty, `final_c == 0`
and `complete?: false`. This replaces the Django `FINISHED && finalscore == 0`
sentinel; `elixir-04-contexts` maps participation state `:no_show` to it.

#### Scenario: No-show yields zeros

- **WHEN** a participation is assembled as `:no_show`
- **THEN** every aggregate is empty/zero and `final_c == 0`

### Requirement: Tie-break counters count only agreed performed movement elements

`tiebreak_counts/1` SHALL take the agreed C marks and return `{e4, e3, e2}`
counting only marks with `verdict: :performed` and `landing: false`
(movement), where e4 counts elements with `score_c > 30` (0.30), e3 with
`score_c > 20`, e2 with `score_c > 10`. `:pending` (abstention) and `:failed`
marks MUST NOT count; agreed marks are the `aggregate_c/1` output, so
undecided elements never reach the counters.

#### Scenario: Performed movement counted (golden)

- **WHEN** the agreed marks contain one `:performed` movement element with
  score 0.50
- **THEN** the counters are {1, 1, 1}

#### Scenario: Abstention not counted (golden)

- **WHEN** a mark is `:pending` for a movement element with score 0.50
- **THEN** the counters are {0, 0, 0}

#### Scenario: Failed not counted (golden)

- **WHEN** the agreed marks contain one `:failed` movement element with score
  0.50
- **THEN** the counters are {0, 0, 0}

#### Scenario: Landing elements never counted

- **WHEN** the agreed marks contain one `:performed` landing element with
  score 0.30
- **THEN** the counters are {0, 0, 0}

### Requirement: Equal finals are ranked by e4, then e3, then e2

`compare/2` over `{final_c, {e4, e3, e2}}` pairs SHALL order by `final_c`
first; on equal finals it SHALL compare e4, then e3, then e2, returning
`:gt | :eq | :lt`. Ordering by draw order for unfinished participations stays
in `elixir-04-contexts` (it needs participation state, which the pure core
does not know).

#### Scenario: Equal finals broken by a high-value element (golden)

- **WHEN** two participations have equal `final_c` but one's C judges agreed
  one more performed 0.50 movement element (counters {1,1,1} vs {0,0,0})
- **THEN** `compare/2` ranks that participation higher

#### Scenario: Fully equal compares equal

- **WHEN** both `final_c` and all three counters are equal
- **THEN** `compare/2` returns `:eq`

### Requirement: The golden numbers are locked by ExUnit tests

Every scenario in this change marked "(golden)" SHALL exist as an ExUnit test
asserting the exact number from the Django suite (`test_scoring_golden.py`,
`test_scoring_rules.py`, `tests.py`), and every public function SHALL carry at
least one doctest. The suite MUST pass with `mix test` on the
`elixir-01-foundation` skeleton.

#### Scenario: Ported golden suite is green

- **WHEN** `mix test test/ushu/scoring` runs
- **THEN** all golden-case assertions (A: 700/550/500/600/500-adult; B:
  950/980/955/800/950/930/0; C: 200/150/170/200-excluded; final:
  1760/1765/1758; tie-break orderings) pass with exact integer equality
