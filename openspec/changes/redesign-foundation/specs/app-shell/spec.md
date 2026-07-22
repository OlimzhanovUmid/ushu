# app-shell

## ADDED Requirements

### Requirement: One token-driven shell frame
Every authenticated screen SHALL render inside the shared shell — fixed navy topbar and sidebar — whose offsets derive from the layout tokens (`--topbar-h`, `--sidebar-w`, `--gutter`), not hardcoded pixel margins.

#### Scenario: A new screen is added
- **WHEN** a screen extends the shell template
- **THEN** its content sits at the token-derived offsets with no per-screen margin hacks

### Requirement: Brand block and event title
The topbar SHALL show the red brand block on the left and the configured `EVENT_TITLE` as the running competition title, sourced from settings, not hardcoded template text.

#### Scenario: Rebranding for a new event
- **WHEN** the operator changes `EVENT_TITLE` and restarts
- **THEN** the topbar reflects it with no source edit

### Requirement: Sidebar navigation states
Sidebar links SHALL render at ~82% white weight and, on hover/active, brighten to full white with the gold left-edge marker. This 3px gold left border on a nav item is the single sanctioned exception to the no-side-stripe rule; content cards SHALL NOT use colored side stripes.

#### Scenario: Active section
- **WHEN** a nav item is the current section
- **THEN** it shows the gold left marker and full-white text

### Requirement: Document locale is Russian
The shell `<html>` element SHALL declare `lang="ru"` (the UI language) so assistive tech and hyphenation behave correctly.

#### Scenario: Screen reader announces the page
- **WHEN** a screen reader loads any app screen
- **THEN** it announces Russian, matching the visible content
