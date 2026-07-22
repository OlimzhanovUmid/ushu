# elixir-05-realtime

## Why

Every realtime behaviour in the Django app is a workaround — HTML snapshots written to the templates directory, SSE with hand-rolled retry, judge screens polling on timers — because Django has no native process model. Phoenix has one; this change defines the realtime backbone (event bus, monitor state process, judge presence) that layers 04 and 06 plug into.

## What Changes

- Canonical PubSub **topic + event catalog**: topic `"competition"` with events `{:performance_started, participation_id}`, `{:score_saved, score_id}`, `{:score_reopened, score_id}`, `{:performance_finalized, participation_id}`; topic `"monitor"` with event `{:monitor_updated, %MonitorState{}}`. A single `Ushu.Competition.Events` module owns topic names and provides `subscribe_*`/`broadcast_*` helpers so no stringly-typed topics leak into contexts or LiveViews.
- **`Ushu.Competition.MonitorBoard`** GenServer holding the projector snapshot `%MonitorState{mode: :idle | :performing | :scores | :standings, data: ...}` with API `publish_performing/1`, `publish_scores/1`, `publish_standings/1`, `clear/0`, `current/0`. Every mutation broadcasts `{:monitor_updated, state}` on `"monitor"`.
- **Supervision**: MonitorBoard runs as a `:permanent` child of the app supervisor (`:one_for_one`). Its state is ephemeral display state only — on crash it restarts as `:idle` and broadcasts the reset so all projectors converge; the database remains the single source of truth.
- **`UshuWeb.Presence`** (Phoenix.Presence) tracking connected judges on topic `"presence:judges"` with meta `%{username, role, category, online_at}` — the secretary sees who is online (new capability vs Django).
- **Reconnection semantics**: LiveView clients auto-rejoin with backoff; on every connected mount a view re-subscribes and re-derives full state from the DB / `MonitorBoard.current/0`. PubSub events are invalidation hints, never the sole state carrier. No polling anywhere.

## Capabilities

### New Capabilities

- `realtime-event-bus`: canonical PubSub topics and event structs, producer/consumer contract (broadcast after commit, thin id-carrying events, re-query on receive), LiveView reconnection semantics.
- `monitor-board`: the `MonitorBoard` GenServer — snapshot struct, publish/clear/current API, atomic updates, supervision and crash/restart behaviour.
- `judge-presence`: Phoenix.Presence for judge connectivity — topic, tracked meta, secretary visibility, disconnect and multi-tab semantics.

### Modified Capabilities

None — new Elixir codebase.

## Impact

- New files under `elixir/lib/ushu/competition/` (`events.ex`, `monitor_board.ex`, `monitor_state.ex`) and `elixir/lib/ushu_web/presence.ex`; one new child in `Ushu.Application`'s supervision tree.
- Layer 5 of 7. Depends on `elixir-01-foundation` (Phoenix app, PubSub started by the endpoint supervisor) and conceptually on `elixir-04-contexts` (the producers). Defines the event contract that `elixir-04-contexts` produces and `elixir-06-liveview-ui` consumes — the topic/event names in all three changes are identical by construction.
- Replaces the Django mechanisms pinned in `stabilize-django/specs/monitor-realtime/spec.md`: SSE snapshot stream → PubSub + LiveView; in-memory snapshot dict → MonitorBoard GenServer; judge polling → push.
