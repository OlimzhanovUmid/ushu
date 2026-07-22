# judge-entry-ui

## ADDED Requirements

### Requirement: Score controls are large, unambiguous targets
The interactive score-entry controls SHALL be sized as large targets (≥44px in the primary interactive dimension) with a single, obvious primary action per screen, so a judge can enter a score quickly without mis-tapping on a weak client.

#### Scenario: Judge enters a score under time pressure
- **WHEN** an A/B judge enters and submits a score
- **THEN** the primary control and submit action are large and unmistakable, reachable in minimal steps

### Requirement: The current subject is marked in gold
The currently-active participant SHALL be marked with the gold "current" token; on the C screen the currently-active element SHALL likewise be marked, so the judge always knows what they are scoring.

#### Scenario: Participant changes
- **WHEN** the active participant changes
- **THEN** the gold current marker moves to the new subject and no stale subject stays highlighted

### Requirement: Incomplete input cannot be submitted by accident
Where a screen requires complete input before submission (C-judge element cards), the submit affordance SHALL visibly read as blocked until every element is marked, reflecting the server-side completeness gate, so an incomplete card is not submitted and bounced mid-competition.

#### Scenario: C judge tries to submit an incomplete card
- **WHEN** one or more elements are still unmarked
- **THEN** the submit affordance is visibly disabled/blocked with a clear reason, and no rejected round-trip occurs

### Requirement: The waiting state is calm and legible
`judge_empty` SHALL present an obviously-intentional "no active participant" waiting state — legible at a glance, clearly not an error or a broken page.

#### Scenario: No participant active
- **WHEN** no participant is active
- **THEN** the judge sees a calm waiting screen, not a blank or error-looking page
