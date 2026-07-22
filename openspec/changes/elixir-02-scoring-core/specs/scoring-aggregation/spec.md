# scoring-aggregation

Pure aggregation of the A (technical errors), B (numeric quality) and C
(difficulty elements) judge panels, ported 1:1 from the stabilized Django
rules (`stabilize-django/specs/scoring-correctness`). All monetary-style
values are integer centi-points (7.00 → 700, 0.05 → 5). Golden numbers below
come verbatim from `tablo/tests.py`, `tablo/test_scoring_rules.py` and
`tablo/test_scoring_golden.py`.

## ADDED Requirements

### Requirement: Scoring inputs are explicit structs

The scoring core SHALL accept only plain structs — `Ushu.Scoring.Deduction`
(`code_id`, `value_c`), `Ushu.Scoring.BScore` (`base_c :: integer | nil`,
`deductions :: [Deduction.t()]`) and `Ushu.Scoring.Mark` (`element_id`,
`position`, `verdict :: :pending | :performed | :failed`, `score_c`,
`landing :: boolean`) — and MUST NOT reference `Ushu.Repo`, Ecto schemas or
any process state. Deduction equality for majority matching SHALL be by
`code_id` (two judges reporting the same error code agree even if structs
differ in other fields).

#### Scenario: Core is database-free

- **WHEN** any `Ushu.Scoring` function is compiled and called
- **THEN** it performs no Repo/Ecto call and returns a value determined solely
  by its arguments (referential transparency)

#### Scenario: Majority matching keys on the error code

- **WHEN** two A judges report deductions carrying the same `code_id`
- **THEN** the pair is treated as agreement on that error regardless of struct
  identity

### Requirement: A aggregation uses a consuming 2-of-3 majority

`aggregate_a/2` SHALL take the three A judges' deduction lists and return
`{agreed :: [Deduction.t()], score_c :: integer}` where an error counts only
when at least two of the three judges reported it; matched entries are
CONSUMED so repeated identical errors pair one-to-one (an error reported twice
by one judge and once by another agrees exactly once, unless matched twice).
Agreement between judges 2 and 3 alone SHALL also count. The agreed values are
summed and subtracted from the age-dependent maximum.

#### Scenario: No agreement returns the full score (golden)

- **WHEN** the three judges report three different error codes, each worth
  1.00 (100 centi), for a junior participant
- **THEN** `agreed == []` and the score is 700 (7.00)

#### Scenario: All three agree deducts once (golden)

- **WHEN** all three judges report the same code worth 1.50
- **THEN** the agreed list contains that error once and the score is 550 (5.50)

#### Scenario: Two of three agree (golden)

- **WHEN** judges 1 and 2 report the same code worth 2.00 and judge 3 reports
  a different code
- **THEN** only the shared error is agreed and the score is 500 (5.00)

#### Scenario: Agreement only between judges two and three (golden)

- **WHEN** judge 1 reports nothing and judges 2 and 3 both report a code worth
  1.00
- **THEN** the error is agreed and the score is 600 (6.00)

### Requirement: A maximum depends on the age bucket

The A maximum SHALL be 500 centi-points (5.00) for the `:adult` age bucket and
700 centi-points (7.00) for every other bucket (`:y7_8`, `:y9_10`, `:y11`,
`:y12_14`, `:y15_17`).

#### Scenario: Adult maximum is five (golden)

- **WHEN** three adult-category judges report three different 1.00 errors (no
  agreement)
- **THEN** the score is 500 (5.00)

### Requirement: A B judge's effective score clamps at zero and nil means no vote

`BScore.effective/1` SHALL return `nil` only when the judge entered nothing at
all (`base_c == nil` and no deductions); otherwise it returns
`max(0, base_c − sum(deduction values))` in centi-points — a legitimate 0.00
is a real vote.

#### Scenario: No input returns nil (golden)

- **WHEN** a B score has `base_c: nil` and no deductions
- **THEN** the effective score is `nil` and is excluded from aggregation

#### Scenario: Zero is a real vote (golden)

- **WHEN** a B score has `base_c: 0` (0.00)
- **THEN** the effective score is 0, not `nil`

#### Scenario: Deduction clamped at zero (golden)

- **WHEN** a B score has `base_c: 50` (0.50) and a deduction worth 200 (2.00)
- **THEN** the effective score is 0

### Requirement: B aggregation is repeated-value-wins, else trimmed mean, panel-size independent

`aggregate_b/1` SHALL take the effective B scores (`integer | nil`), drop only
`nil` entries, and return in centi-points: the repeated value when any value
occurs at least twice (the most frequent value; on frequency ties, the HIGHER
value); otherwise the trimmed mean `(sum − max − min) / (n − 2)` rounded to
the nearest centi-point for n ≥ 3; the average for n == 2; the single value
for n == 1; and 0 when no scores remain.

#### Scenario: Repeated value wins (golden)

- **WHEN** the effective scores are [950, 950, 970, 980] (9.5, 9.5, 9.7, 9.8)
- **THEN** the result is 950 (9.5)

#### Scenario: Frequency tie breaks to the higher value (golden)

- **WHEN** the effective scores are [950, 950, 980, 980]
- **THEN** the result is 980 (9.8)

#### Scenario: Standard four-judge distinct panel matches the historical formula (golden)

- **WHEN** the effective scores are [940, 950, 960, 970]
- **THEN** the result is 955 (9.55), identical to `(sum − max − min) / 2`

#### Scenario: Three distinct scores yield the middle score (golden)

- **WHEN** the effective scores are [700, 900, 800]
- **THEN** the result is 800 (8.0) — the middle score, not half of it

#### Scenario: Two distinct scores average (golden)

- **WHEN** the effective scores are [940, 960]
- **THEN** the result is 950 (9.5)

#### Scenario: Single score passes through (golden)

- **WHEN** the effective scores are [930]
- **THEN** the result is 930 (9.3)

#### Scenario: Nil entries dropped, zeros kept (golden)

- **WHEN** the effective scores are [nil, 0, 0]
- **THEN** the result is 0 (a repeated real vote), and [nil, nil] yields 0
  because no scores were submitted

#### Scenario: All equal returns that value (golden)

- **WHEN** the effective scores are [850, 850, 850]
- **THEN** the result is 850 (8.5)

### Requirement: C aggregation decides each element by a 2-of-N real-vote majority with abstentions

`aggregate_c/1` SHALL take one `Mark` list per C judge (aligned by
`position`), zip the judges' marks per element, and decide each element only
when at least two judges gave the SAME real verdict: two-plus `:performed` →
agreed performed (no deduction); two-plus `:failed` → agreed failed (deduct
the element's `score_c` from its pool). A `:pending` mark is an abstention —
it never counts as performed and elements without a two-real-vote majority are
EXCLUDED (benefit of the doubt: no deduction, not in the agreed list). Returns
`{agreed :: [Mark.t()], score_c}`.

#### Scenario: One abstains, two performed (golden)

- **WHEN** the marks for a movement element (0.50) are (:pending, :performed,
  :performed)
- **THEN** the element is agreed performed and the C score is 200 (2.0)

#### Scenario: One abstains, two failed (golden)

- **WHEN** the marks for a movement element (0.50) are (:pending, :failed,
  :failed)
- **THEN** the element is agreed failed and the C score is 150
  ((1.4 − 0.5) + 0.6 = 1.5)

#### Scenario: No majority possible (golden)

- **WHEN** the marks are (:pending, :performed, :failed)
- **THEN** the element is excluded: `agreed == []`, no deduction, C score 200

#### Scenario: Single real vote excluded (golden)

- **WHEN** the marks are (:pending, :pending, :performed)
- **THEN** the element is excluded: `agreed == []`, C score 200

### Requirement: C pools are 1.40 movement plus 0.60 landing, floored at zero, capped at 2.00

Failed movement elements (`landing: false`) SHALL deduct from a 140
centi-point pool and failed landing elements (`landing: true`) from a 60
centi-point pool; each pool floors at 0 independently and the summed C score
is capped at 200 centi-points. An empty panel yields `{[], 0}`.

#### Scenario: All performed, capped at two (golden)

- **WHEN** all three judges mark a movement element (0.50) `:performed`
- **THEN** the C score is 200 (pools full, cap applied)

#### Scenario: Failed movement deducts from the movement pool (golden)

- **WHEN** all three judges mark a movement element (0.50) `:failed`
- **THEN** the C score is 150 (1.4 − 0.5 + 0.6)

#### Scenario: Failed landing deducts from the landing pool (golden)

- **WHEN** all three judges mark a landing element (0.30) `:failed`
- **THEN** the C score is 170 (1.4 + (0.6 − 0.3))

#### Scenario: Empty input

- **WHEN** `aggregate_c/1` receives an empty list
- **THEN** it returns `{[], 0}`
