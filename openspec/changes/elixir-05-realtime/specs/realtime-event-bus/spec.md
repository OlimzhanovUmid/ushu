# realtime-event-bus

## ADDED Requirements

### Requirement: Canonical topic and event catalog

The system SHALL define exactly two domain PubSub topics with a fixed event vocabulary, owned by a single module `Ushu.Competition.Events`:

- topic `"competition"` — events `{:performance_started, participation_id}`, `{:score_saved, score_id}`, `{:score_reopened, score_id}`, `{:performance_finalized, participation_id}`;
- topic `"monitor"` — event `{:monitor_updated, %Ushu.Competition.MonitorState{}}`.

`Ushu.Competition.Events` MUST expose `subscribe_competition/0`, `subscribe_monitor/0` and one `broadcast_*` function per event; no other module SHALL call `Phoenix.PubSub.broadcast/3` with these topic strings directly. Producers are the `Ushu.Competition` context operations (defined in `elixir-04-contexts`) and `MonitorBoard`; consumers are the LiveViews (defined in `elixir-06-liveview-ui`).

#### Scenario: Score submission reaches all subscribed views

- **WHEN** a judge's score submission commits and the context calls `Events.broadcast_score_saved(score_id)`
- **THEN** every process subscribed via `Events.subscribe_competition/0` receives `{:score_saved, score_id}` in its mailbox, with no other topic or tuple shape involved

#### Scenario: Topic strings do not leak

- **WHEN** the codebase is grepped for the literals `"competition"` and `"monitor"` as PubSub topics
- **THEN** they appear only inside `Ushu.Competition.Events`

### Requirement: Events are thin and carry ids, not row data

Competition events SHALL carry only the id of the affected row (the monitor event, which carries the full `%MonitorState{}` snapshot, is the sole exception). Consumers MUST treat an event as an invalidation hint and re-query the database (or `MonitorBoard.current/0`) for current data; they SHALL NOT render event payload fields directly.

#### Scenario: Consumer re-queries on event

- **WHEN** a LiveView receives `{:performance_finalized, id}`
- **THEN** it reloads the affected data from the database before re-rendering, so a stale or reordered event can never display outdated values

### Requirement: Events broadcast only after commit

Producers SHALL broadcast a competition event only after the database transaction that caused it has committed successfully. A rolled-back `Ecto.Multi` MUST NOT emit any event.

#### Scenario: Rolled-back activation emits nothing

- **WHEN** an activation transaction fails on the single-performing partial unique index and rolls back
- **THEN** no `{:performance_started, _}` event is broadcast and no subscriber re-renders

#### Scenario: Consumer never reads uncommitted state

- **WHEN** a subscriber re-queries the database immediately upon receiving an event
- **THEN** the query observes the committed change that the event announced

### Requirement: LiveView reconnection re-derives full state

Every realtime LiveView SHALL subscribe to its topics and derive its complete assigns from the database (and `MonitorBoard.current/0` for the projector) inside `mount/3` when `connected?(socket)` is true. After a network interruption the LiveView client auto-rejoins with backoff (Phoenix default, ≥ 1s growing), the server re-runs `mount/3`, and the view MUST show current state without any manual reload — events missed while disconnected are irrelevant because mount does not depend on event history.

#### Scenario: Projector recovers from a network blip

- **WHEN** the projector's websocket drops for ten seconds while the secretary publishes new standings, then the client reconnects
- **THEN** the remounted MonitorLive fetches `MonitorBoard.current/0` and immediately renders the standings it never received as an event

#### Scenario: Server restart

- **WHEN** the server restarts while judge and monitor screens are connected
- **THEN** each client rejoins automatically with backoff and renders current state on remount, with no user action

### Requirement: No polling

No realtime screen SHALL poll on a timer for data changes: there MUST be no client-side refresh intervals and no server-side `Process.send_after`-driven periodic re-query loops for content that PubSub events already announce.

#### Scenario: Idle system is silent

- **WHEN** no competition state changes for ten minutes with all screens connected
- **THEN** no data queries are issued on behalf of the connected views during that period (websocket heartbeats excepted)
