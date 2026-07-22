# score-breakdown-ui

## ADDED Requirements

### Requirement: The stage breakdown reads on a dark surface at distance
`scores.html` SHALL render as the immersive dark "stage" screen — white-on-navy at greater-than-AA contrast — with the per-judge marks and the aggregate legible from a distance.

#### Scenario: Breakdown shown on the stage screen
- **WHEN** a participant's score breakdown is displayed
- **THEN** all marks read clearly on the dark background at hall distance

### Requirement: The main mark is gold
The aggregate/main mark on the breakdown SHALL use the gold token as the single emphasized value, consistent with Gold-Means-Now.

#### Scenario: Final aggregate shown
- **WHEN** the breakdown shows the final aggregate
- **THEN** the main mark is the gold-emphasized value and no other value competes for that emphasis

### Requirement: Per-judge marks keep their semantic status colors
The individual element/judge statuses SHALL keep their semantic colors (ok / performed / failed) legibly on the dark surface, not collapse into one indistinct color.

#### Scenario: Mixed statuses on the breakdown
- **WHEN** a card has ok, performed, and failed elements
- **THEN** each status is distinguishable on the dark stage screen
