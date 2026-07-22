# monitor-display-ui

## ADDED Requirements

### Requirement: Critical content reads across the hall
The projector screens SHALL size the current performer, the live score, and the standings ranks in display-scale type so they are legible from across a hall (tens of metres) on a beamer, not merely at laptop distance.

#### Scenario: Spectator reads the score from the back row
- **WHEN** a score is shown on the monitor
- **THEN** it is legible from the back of the hall without squinting

### Requirement: Beyond-AA contrast for beamer washout
Text and key marks on the monitor surface SHALL exceed AA contrast (target ≥7:1) against the dark background, giving headroom for beamer washout and variable hall light.

#### Scenario: Bright hall / washed-out beamer
- **WHEN** ambient light or a weak beamer reduces effective contrast
- **THEN** the text still reads because it started well above AA

### Requirement: The current performer is unmistakable
The currently-performing athlete SHALL be marked with the gold "current" token and given clear visual primacy on the screen, so viewers instantly know who is up.

#### Scenario: Performer changes
- **WHEN** the active performer changes
- **THEN** the gold current marker and primacy move to the new athlete

### Requirement: Standings are readable at distance
The standings table (`monitor_tablo`) SHALL present rank / name / club / score with enough size, spacing, and contrast to be scanned at distance; country flags SHALL render with a safe placeholder when an image is missing, never breaking the layout.

#### Scenario: Club with no flag image
- **WHEN** a standings row's country has no flag image
- **THEN** a placeholder renders and the row stays aligned and readable

### Requirement: No broadcast-scoreboard clutter
The monitor screens SHALL NOT use competing animations or busy broadcast-overlay decoration; motion is limited to what aids reading (e.g. a new score appearing) and SHALL provide a reduced-motion alternative.

#### Scenario: Reduced motion on the monitor
- **WHEN** reduced motion is requested
- **THEN** score updates appear without animation and nothing critical depends on a transition firing
