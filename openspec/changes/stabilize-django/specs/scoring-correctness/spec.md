# scoring-correctness

Scoring rules as decided by the owner (2026-07-12). The A/B/C aggregation constants stay unchanged: A max 7.0 (5.0 for 18+) with 2-of-3 error agreement; C pools 1.4 movement + 0.6 landing, floored at 0, capped at 2.0; bonus +0.05 applied to B; final = A + B + C rounded to 2 decimals.

## ADDED Requirements

### Requirement: Judge C must judge every element before submitting
The judge C submission SHALL be rejected (client- and server-side) while any of that judge's elements remains unmarked (`done == 2`); `Score.saved` MUST NOT become true with unmarked elements.

#### Scenario: Submit with unmarked element
- **WHEN** a C judge posts a scorecard where at least one element is still unmarked
- **THEN** the score is not saved, the judge sees which elements are unmarked, and the card stays open

#### Scenario: Fully marked submit
- **WHEN** every element is marked pass (1) or fail (0)
- **THEN** the score saves and the judge screen returns to the waiting state

### Requirement: Unmarked elements are abstentions, never passes
In C aggregation and in the medal tie-break, an element marked `done == 2` SHALL count as an abstention: the majority is taken over the judges who marked it, and it SHALL never count as "performed successfully". The tie-break counters (`counts`) SHALL count only elements agreed as performed (`done == 1`).

#### Scenario: One judge abstains, two agree
- **WHEN** judges' marks for an element are (2, 1, 1) or (2, 0, 0)
- **THEN** the majority of the two real votes decides (performed / failed respectively)

#### Scenario: No majority possible
- **WHEN** judges' marks for an element are (2, 1, 0) or (2, 2, x)
- **THEN** the element is excluded from deductions (benefit of the doubt) and is NOT counted as performed in the tie-break

### Requirement: B aggregation is panel-size independent
`calculateB` SHALL return: the repeated value when any submitted score occurs at least twice (most common value; on count ties, the higher value); otherwise the trimmed mean `(sum − max − min) / (n − 2)` for n ≥ 3 submitted scores; the single score for n == 1; and 0 only when no scores were submitted. For the standard 4-judge panel with distinct scores the result SHALL equal the current `(sum − max − min) / 2`.

#### Scenario: Standard 4-judge panel unchanged
- **WHEN** four B judges submit four distinct scores
- **THEN** the result equals the average of the two middle scores (identical to pre-change behavior)

#### Scenario: Repeated value wins
- **WHEN** at least two B judges submit the same value
- **THEN** that value is the B score (the owner's "two identical → take it" rule)

#### Scenario: Three-judge panel
- **WHEN** three B judges submit three distinct scores
- **THEN** the result is the middle score, not half of it

### Requirement: A zero B-score is a submitted vote
A B judge's score of exactly 0.00 (including a score reduced to 0 by deductions) SHALL participate in aggregation like any other value, not be dropped as "not submitted". Only judges with no saved numeric score are excluded.

#### Scenario: Judge awards zero
- **WHEN** a B judge's effective score is 0.00 and three others submit non-zero scores
- **THEN** aggregation runs over all four values

### Requirement: B contribution is rounded, not truncated
Converting the B aggregate to centi-points SHALL round to the nearest integer instead of truncating, so binary-float artifacts cannot shave 0.01 off the final score.

#### Scenario: Truncation artifact
- **WHEN** the B aggregate is 9.58 (stored as 957.999… × 10⁻²)
- **THEN** the B contribution is 958 centi-points and the displayed B score is 9.58

### Requirement: Scoring behavior is locked by end-to-end tests
`Participation.get_scores` (final assembly incl. bonus, no-show sentinel, rounding) and the ranking tie-break (`cmp`/`counts`) SHALL be covered by tests expressing THIS spec; pre-change golden tests SHALL be written first to document which outputs the change intentionally alters.

#### Scenario: Final score end-to-end
- **WHEN** a participation has a full 3A/4B/3C panel with known inputs
- **THEN** a test asserts the exact final float, including bonus and rounding

#### Scenario: Tie-break decides medals
- **WHEN** two participations have equal final scores but different counts of successfully performed high-value elements
- **THEN** a test asserts the ranking order per the e4/e3/e2 threshold rules (>0.3, >0.2, >0.1, movement elements only)
