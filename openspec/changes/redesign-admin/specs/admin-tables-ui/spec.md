# admin-tables-ui

## ADDED Requirements

### Requirement: The tablo grid is scannable
`tablo_list` and `tablo_detail` SHALL present the tablo grid as token-styled tables (not card grids) with clear column headers, legible status, and unmistakable per-row actions, so the organizer reads the grid and its state at a glance.

#### Scenario: Organizer scans the grid before a round
- **WHEN** the organizer opens the tablo list
- **THEN** each tablo's identity, state, and available actions are legible in a single scan

### Requirement: Row actions are clear and safe
Per-row actions (open, draw, delete, monitor-push) SHALL be visually distinct by consequence — destructive actions clearly marked (competition red) and separated from routine ones — so a mis-click on a destructive action is unlikely.

#### Scenario: Deleting a participation
- **WHEN** a destructive row action is present
- **THEN** it is visually distinct from routine actions and reads as consequential

### Requirement: The printable protocol drops screen chrome
`tablo_print` SHALL use a dedicated print stylesheet that removes the shell chrome (topbar/sidebar), maximizes ink-efficiency, and preserves the standings structure for a clean printed protocol.

#### Scenario: Printing a protocol
- **WHEN** the organizer prints a tablo protocol
- **THEN** the output shows only the protocol content, no navigation chrome, laid out ink-efficiently
