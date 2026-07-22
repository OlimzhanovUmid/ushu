# judge-presence

## ADDED Requirements

### Requirement: Presence module and tracking contract

The system SHALL define `UshuWeb.Presence` (using `Phoenix.Presence`, backed by the app's PubSub) tracking judge connectivity on topic `"presence:judges"`. When a user with role `:judge` or `:main_judge` completes a connected LiveView mount on a judging screen, the view SHALL call `UshuWeb.Presence.track/4` with key = the user's id (as a string) and meta `%{username: username, role: role, category: category, online_at: DateTime.t()}`. (The `on_mount` hook that performs the tracking ships in `elixir-06-liveview-ui`; this change defines the module, topic and meta shape.)

#### Scenario: Judge comes online

- **WHEN** judge "aliya" (role `:judge`, category `:b`) opens her judging screen and the LiveView mounts connected
- **THEN** `UshuWeb.Presence.list("presence:judges")` includes her user id with meta containing `username: "aliya"`, `role: :judge`, `category: :b`

### Requirement: Secretary sees live judge connectivity

The secretary screen SHALL subscribe to `"presence:judges"`, render the currently connected judges grouped by category (A/B/C, plus main judge), and update on every `"presence_diff"` message without reload. This lets the secretary confirm the full panel (3A/4B/3C) is online before activating a participant.

#### Scenario: Panel check before activation

- **WHEN** the secretary opens her console while 9 of 10 judges are connected
- **THEN** the presence panel shows exactly the 9 connected judges by username and category, and the missing judge is identifiable

#### Scenario: Live join

- **WHEN** the tenth judge connects while the secretary console is open
- **THEN** the console's presence panel shows the judge within seconds, without the secretary refreshing

### Requirement: Disconnects are detected automatically

A judge's presence entry SHALL disappear when their LiveView process dies for any reason — browser closed, laptop asleep, network cable pulled — without any explicit "logout" action, relying on process monitoring (Presence untracks on process exit; the websocket's heartbeat detects dead peers). The secretary SHALL see the judge leave within the socket timeout window.

#### Scenario: Judge station loses network

- **WHEN** a judge's station drops off the LAN mid-competition
- **THEN** after the socket heartbeat timeout the judge disappears from the secretary's presence panel with no manual cleanup

### Requirement: Multiple connections count as one judge online

Presence SHALL be keyed by user id so that a judge with several tabs or devices appears once with multiple metas; the judge counts as online while at least one connection remains, and disconnecting one tab of several SHALL NOT show the judge as offline.

#### Scenario: Two tabs, one closed

- **WHEN** a judge has the judging screen open in two tabs and closes one
- **THEN** the secretary still sees the judge online; only closing the last connection removes them

### Requirement: Presence is advisory, never authoritative

Presence data SHALL NOT gate any domain operation at the context layer: score submission validity, panel snapshots and completeness checks are database facts (see `elixir-04-contexts`). The UI MAY warn the secretary when activating while judges appear offline, but the system MUST NOT block operations on presence, since presence is eventually consistent by design.

#### Scenario: Activation with a judge showing offline

- **WHEN** the secretary activates a participant while one judge's presence entry is momentarily absent (reconnect in progress)
- **THEN** the activation succeeds; the judge's score card exists regardless, and the judge can submit as soon as their screen reconnects
