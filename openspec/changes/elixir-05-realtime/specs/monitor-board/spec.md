# monitor-board

## ADDED Requirements

### Requirement: MonitorBoard holds the projector snapshot

`Ushu.Competition.MonitorBoard` SHALL be a locally registered GenServer whose entire state is one `%Ushu.Competition.MonitorState{mode: mode, data: data, updated_at: DateTime.t()}` struct, where `mode` is one of `:idle`, `:performing`, `:scores`, `:standings` and `data` is a mode-specific plain map built by the caller (`nil` for `:idle`). The public API SHALL be:

- `publish_performing(data)` — set mode `:performing`;
- `publish_scores(data)` — set mode `:scores`;
- `publish_standings(data)` — set mode `:standings`;
- `clear()` — reset to `:idle`;
- `current()` — return the current `%MonitorState{}` (synchronous call).

Callers (SecretaryLive and, for automatic mode switches, the `Ushu.Competition` context — see `elixir-04-contexts`/`elixir-06-liveview-ui`) build the complete display data from the database BEFORE calling publish; the board never queries the database.

#### Scenario: Secretary pushes standings

- **WHEN** the secretary triggers a standings push and the caller invokes `MonitorBoard.publish_standings(data)` with fully built rows
- **THEN** `MonitorBoard.current/0` returns `%MonitorState{mode: :standings, data: data}` from then on

#### Scenario: Board owns no queries

- **WHEN** `MonitorBoard`'s module source is inspected
- **THEN** it contains no `Repo` calls — it stores and serves structs only

### Requirement: Every state change broadcasts the full snapshot

Each successful `publish_*`/`clear` SHALL broadcast `{:monitor_updated, %MonitorState{}}` (the complete new state) on topic `"monitor"` via `Ushu.Competition.Events`. Because the snapshot travels as a single immutable message and `current/0` is a single `GenServer.call`, a consumer MUST always observe either the complete old snapshot or the complete new one — never a mix.

#### Scenario: No torn reads

- **WHEN** `publish_scores/1` replaces a `:standings` snapshot while three projector processes are consuming
- **THEN** each projector renders either the full old standings or the full new scores, never fields of both

#### Scenario: Publish failure publishes nothing

- **WHEN** the caller crashes while building display data (e.g. a missing flag asset raises)
- **THEN** no `publish_*` call is made, no event is broadcast, and the previous snapshot remains intact on the board

### Requirement: MonitorBoard is supervised and restarts to idle

`MonitorBoard` SHALL run as a `:permanent` child in `Ushu.Application`'s `:one_for_one` supervision tree, started after `{Phoenix.PubSub, name: Ushu.PubSub}` and before `UshuWeb.Endpoint` in `Ushu.Supervisor`'s child list. Its state is ephemeral display state: on crash the supervisor restarts it with `mode: :idle`, and `init/1` SHALL broadcast `{:monitor_updated, idle_state}` so every connected projector converges with the restarted board instead of showing stale content. Recovery cost is one re-push by the secretary; no snapshot persistence SHALL be implemented.

#### Scenario: Crash resets the projector to idle

- **WHEN** `MonitorBoard` crashes while displaying scores
- **THEN** the supervisor restarts it, connected projectors receive the broadcast idle snapshot and render the idle screen, and the secretary re-pushes the scores in one click

#### Scenario: Restart does not take down subscribers

- **WHEN** `MonitorBoard` crashes and restarts
- **THEN** projector LiveView processes stay alive and stay subscribed (subscriptions live in PubSub, not in the board), and only the board process is restarted

### Requirement: The database stays the source of truth

The board SHALL hold nothing that cannot be rebuilt from the database plus one secretary action. No scoring, standings or participation fact SHALL exist only in `MonitorBoard`; all authoritative reads (protocols, standings, score review) go to the database, and the board is written to only at explicit publish points.

#### Scenario: Board loss loses no results

- **WHEN** the whole application is killed and restarted mid-competition
- **THEN** all scores, states and standings are intact in SQLite; only the projector's current display selection is lost and is restored by re-publishing

### Requirement: Monitor works with a read-only application directory

Publishing to the monitor SHALL involve no filesystem writes: no rendered HTML files, no counter files (replacing Django's `showme*.html`/`file.count` mechanism).

#### Scenario: Read-only deploy

- **WHEN** the application directory is mounted read-only (database directory excepted)
- **THEN** monitor publishing and rendering work unchanged
