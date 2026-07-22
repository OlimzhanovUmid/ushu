# judge-consoles

The three judge scoring screens as LiveViews. All three share a waiting state:
they subscribe to the `"competition"` PubSub topic (catalog in
`elixir-05-realtime`) and switch between "waiting for participant" and the
active scorecard on `{:performance_started, id}` / `{:performance_finalized, id}`
/ `{:score_reopened, score_id}` events. All submissions go through the context
functions of `elixir-04-contexts` (ownership, completeness and validation are
enforced server-side there; the UI adds the client-side layer on top).

## ADDED Requirements

### Requirement: Judge consoles react to activation without reload or polling

Each judge console SHALL subscribe to the `"competition"` topic on connected
mount and switch its UI on broadcast events: show the scorecard for the judge's
own unsaved score when a performance starts, and return to the waiting screen
when the performance is finalized or when their card is submitted. The client
SHALL NOT poll on a timer. If the judge's card for the active participation is
already saved (`submitted: true`), the console SHALL show a read-only "submitted"
state, and SHALL reopen for editing when a `{:score_reopened, score_id}` event
for their score arrives.

#### Scenario: Secretary activates a participant

- **WHEN** a participation transitions to `:performing` while a judge console sits on the waiting screen
- **THEN** the console swaps to the scorecard within the PubSub broadcast (no reload, no timer), showing participant name and tablo

#### Scenario: Reopen returns the card

- **WHEN** the main judge reopens this judge's saved score
- **THEN** the console leaves the "submitted" state and shows the editable card again with the previously entered marks

#### Scenario: Finalization while a card is open

- **WHEN** the main judge finalizes (or marks no-show) while a judge's card is still open
- **THEN** the console returns to the waiting screen with an explanatory flash; a late submit attempt is rejected by the context and surfaces the same message, never a crash

### Requirement: A console records error codes via circles and physical keys

`JudgeALive` SHALL render the error codes of kind `:a` and `:shared` (kinds
from `elixir-03-ecto-schema`; the numeric code stays visible for display) as
large circular touch targets. Tapping a circle appends that error to the
judge's card; the same error MAY be recorded multiple times (each tap is one
deduction row); an entry list with per-entry remove is shown. Submission SHALL
be triggered by the on-screen submit button OR by the physical Space or Enter
key, detected through a JS hook reading `event.code` (`Space`, `Enter`,
`NumpadEnter`) so it works on any keyboard layout. A confirmation step SHALL
guard key-triggered submission against accidental presses.

#### Scenario: Repeated error

- **WHEN** the A judge taps the same error-code circle twice
- **THEN** two deduction entries for that code appear on the card and both are submitted

#### Scenario: Submit by physical key on Cyrillic layout

- **WHEN** the judge's OS keyboard layout is Russian and they press the space bar
- **THEN** the submit flow triggers (hook matched `event.code == "Space"`), a confirmation is shown, and confirming saves the card

#### Scenario: Only own card is affected

- **WHEN** an A submission is processed
- **THEN** only the submitting judge's score rows change (ownership enforced by `elixir-04-contexts`; the LiveView never sends other judges' row ids)

### Requirement: B console validates numeric input before submit

`JudgeBLive` SHALL provide a large on-screen numpad plus keyboard entry for
the base score, and circles for B-applicable error codes (kinds `:b`-relevant
per the catalog — shared deduction codes) that subtract on the server. The
input SHALL be validated with a changeset rendered via `to_form`: numeric,
two decimals, within the configured range (0.00 to the B maximum); invalid
input SHALL disable submit and show the error inline. A base score of exactly
0.00 is a valid submitted vote (never treated as "not submitted").

#### Scenario: Malformed input

- **WHEN** the judge enters `9,5,` or a value above the maximum
- **THEN** the form shows a validation error, the submit button is disabled, and no server save occurs

#### Scenario: Zero is a vote

- **WHEN** the judge submits exactly `0.00`
- **THEN** the score saves as a submitted value and participates in B aggregation (per the pinned scoring rules)

#### Scenario: Deduction below zero

- **WHEN** recorded B deductions exceed the base score
- **THEN** the effective score floors at 0.00 (server rule from `elixir-02-scoring-core`), and the console displays the effective value

### Requirement: C console marks every element with layout-independent keys

`JudgeCLive` SHALL render the judge's element list (from the participation's
combination snapshot) with a visible cursor over the current element. Verdicts
SHALL be settable both by on-screen buttons and by physical keys through a JS
hook on `event.code`: `KeyV` = `:performed`, `KeyX` = `:failed`, `KeyC` =
clear back to `:pending`; arrow keys move the cursor; marking advances the
cursor to the next `:pending` element. Because `event.code` identifies the
physical key, the hotkeys MUST work identically under Cyrillic or any other
layout. Marks map to `score_marks.verdict` (`:pending`/`:performed`/`:failed`)
rows from `elixir-03-ecto-schema`.

#### Scenario: Cyrillic layout hotkeys

- **WHEN** the OS layout is Russian and the judge presses the physical key labelled `М` (position of Latin V)
- **THEN** the current element is marked `:performed` (hook matched `event.code == "KeyV"`)

#### Scenario: Clearing a mark

- **WHEN** the judge presses the physical `KeyC` on an element previously marked `:failed`
- **THEN** the element returns to `:pending` and the submit button becomes disabled again

### Requirement: C submit is blocked until all elements are marked

The C console SHALL keep the submit control disabled while any element is
`:pending`, showing which elements remain unmarked. The server-side
completeness gate lives in `elixir-04-contexts`; if a stale client submits
anyway, the error SHALL be rendered on the card (listing unmarked elements)
and the card stays open. An unmarked element is an abstention in aggregation,
never a pass (pinned rule from `stabilize-django/specs/scoring-correctness`).

#### Scenario: One element pending

- **WHEN** all elements but one are marked
- **THEN** the submit button is disabled and the pending element is highlighted

#### Scenario: Stale client submit

- **WHEN** a submit event reaches the server with a `:pending` mark still present
- **THEN** the context rejects it, the LiveView shows which elements are unmarked, and `submitted` stays false

### Requirement: Judge consoles are usable on weak touch clients

Judge screens SHALL use large touch targets (minimum ~48px), high-contrast
big typography readable at arm's length, and ship no heavy client frameworks —
only the LiveView runtime and the small key-handling hooks. The scorecard
SHALL always display the current participant's name and tablo so a judge
cannot score the wrong athlete unknowingly.

#### Scenario: Old venue laptop

- **WHEN** a judge console runs on a low-power client over the venue LAN
- **THEN** interactions remain responsive (server-rendered diffs, no client-side framework boot) and all controls are finger-sized
