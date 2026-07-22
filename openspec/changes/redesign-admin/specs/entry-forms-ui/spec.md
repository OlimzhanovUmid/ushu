# entry-forms-ui

## ADDED Requirements

### Requirement: Registration form is clear and catches errors at entry
`participant_create` SHALL present labeled fields with visible focus states and inline, field-level error messages, so the registrar enters an athlete quickly and mistakes are surfaced at the point of entry, not after submission.

#### Scenario: Registrar submits an invalid field
- **WHEN** a field fails validation
- **THEN** a specific error renders inline next to that field, not as a generic top banner

#### Scenario: Keyboard-driven registration
- **WHEN** the registrar tabs through the form
- **THEN** each focused field shows a clear focus state (the token blue focus ring)

### Requirement: Sign-in matches the finalized foundation
`login.html` SHALL be aligned (polish, not rebuild) to the finalized foundation tokens — the sign-in panel, inputs, and primary button consistent with the shared component set.

#### Scenario: Sign-in after the foundation lands
- **WHEN** the sign-in screen renders
- **THEN** its panel, inputs, and button match the foundation tokens with no drift

### Requirement: Form controls meet target and contrast budgets
Form inputs and the primary submit SHALL meet the same large-target and contrast budgets as the rest of the app (placeholder text ≥4.5:1, visible focus, comfortable target size).

#### Scenario: Placeholder legibility
- **WHEN** a field shows placeholder text
- **THEN** the placeholder meets ≥4.5:1 contrast, not a faint gray
