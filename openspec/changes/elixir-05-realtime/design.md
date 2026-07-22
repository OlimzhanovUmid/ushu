# elixir-05-realtime — design

## Context

The venue runs one laptop server and ~10 browser clients (judge stations, secretary console, projector) on an offline LAN. Django faked realtime with SSE + HTML snapshots written to disk and timer polling on judge screens (pinned in `stabilize-django/specs/monitor-realtime/spec.md`). Phoenix gives us real primitives: PubSub (in-memory message fan-out), GenServer (a supervised stateful process), Presence (CRDT-tracked connections), LiveView (stateful websocket views with auto-reconnect). This change is the contract layer: it fixes topics, event shapes, the monitor process and presence semantics that `elixir-04-contexts` (producer side) and `elixir-06-liveview-ui` (consumer side) both compile against.

## Goals / Non-Goals

**Goals**

- One module (`Ushu.Competition.Events`) owning every topic string and event tuple.
- A supervised `MonitorBoard` GenServer holding the projector snapshot, with a crash story that costs at most one secretary re-push.
- Judge presence visible to the secretary, with correct disconnect/multi-tab semantics.
- Reconnection semantics that make missed events irrelevant (full re-derive on mount).

**Non-Goals**

- The LiveViews themselves (layer 06), the context operations that produce events (layer 04).
- Distribution/clustering — single node by architecture; PubSub runs local-only.
- Event persistence or replay — the `score_events` audit table (layer 03/04) is for humans/protests, not for driving the UI.
- Multi-carpet, multiple simultaneous monitors with different content.

## Decisions

**D1. Thin events carrying ids; consumers re-query.**
Events are `{:score_saved, score_id}`-style tuples, not full rows. Consumers hit SQLite on receipt (sub-millisecond on this dataset). *Alternatives:* (a) fat events carrying changesets/structs — rejected: stale-payload bugs on reorder, payload duplicated per subscriber, and consumers need different projections anyway; (b) `Phoenix.PubSub` with `%SomeEvent{}` structs per event — nice typing, but plain tagged tuples are idiomatic, pattern-match cleanly in `handle_info/2`, and the vocabulary is 5 events. The single exception is `{:monitor_updated, %MonitorState{}}`: the monitor snapshot IS the data (already fully built for display), so shipping it avoids a pointless `current/0` round-trip on every update.

**D2. Topic strings and broadcasts centralized in `Ushu.Competition.Events`.**
Contexts call `Events.broadcast_score_saved(id)`; views call `Events.subscribe_competition()`. *Alternative:* inline `Phoenix.PubSub.broadcast(Ushu.PubSub, "competition", ...)` at each call site — rejected: typo-prone stringly topics, and the 04/05/06 coordination contract would live in nobody's file.

**D3. One global `"competition"` topic, not per-tablo topics.**
At most one participation performs at a time (partial unique index) and there are ~10 subscribers total; topic granularity buys nothing and complicates subscribe logic. *Alternative:* `"competition:tablo:#{id}"` — the standard scaling pattern, rejected as premature; noted in the explainer as what you'd do with many concurrent arenas.

**D4. `MonitorBoard` is a GenServer, not an Agent/ETS table/DB row.**
It needs (a) serialized writes, (b) a broadcast side-effect coupled to each write, (c) a synchronous `current/0` for mounts — a textbook GenServer. *Alternatives:* Agent — no natural place for the broadcast side-effect and no room to grow (e.g. auto-mode timers); ETS — shared-memory read scaling we don't need for ~3 projector reads a minute, and writes still need an owner process; a `monitor_state` DB row — persists what is deliberately ephemeral and makes every push a disk write. This is also the "when you would choose differently" teaching point: if the display state were expensive to rebuild or had to survive restarts, the DB row wins.

**D5. Ephemeral state + let-it-crash: restart resets to `:idle` and broadcasts the reset.**
On crash, the supervisor restarts MonitorBoard; `init/1` broadcasts the idle snapshot so projectors converge with the board instead of showing content the board no longer knows about. Recovery = secretary re-pushes (one click). *Alternatives:* (a) persist snapshot to ETS with an heir process or to disk and restore in `init/1` — machinery to protect a value worth one click, and restored state can silently be stale relative to the DB; (b) restart silently and let projectors keep stale content — rejected: board (`:idle`) and projector (old scores) disagree, and `current/0` on a later remount would "rewind" the projector confusingly.

**D6. Producers broadcast only after commit.**
Context operations run in `Ecto.Multi`; the broadcast happens after `Repo.transaction/1` returns `{:ok, _}` (helper in `Events` takes the result tuple and broadcasts only on success). *Alternative:* broadcasting inside the multi as a `Multi.run` step — rejected: a later step's failure rolls back the DB but cannot un-send the message; subscribers would re-query and see nothing changed (harmless flicker) or, worse, act on a phantom event.

**D7. Presence keyed by user id; tracking performed in the layer-06 `on_mount` hook.**
`UshuWeb.Presence` + topic `"presence:judges"`, meta `%{username, role, category, online_at}`. Keying by user id makes multi-tab semantics correct for free (one key, N metas). This change ships the Presence module and the contract; the hook that calls `track/4` ships with the LiveViews in 06 (it needs the socket). *Alternative:* keying by socket id — every tab appears as a separate "judge", inflating the secretary's panel count.

**D8. Presence is advisory only.**
No context operation reads Presence. Presence is eventually consistent (join/leave propagation, heartbeat timeouts ~30–60s); gating activation or submission on it would add flaky failures to operations whose real invariants are DB constraints. The secretary UI may warn, never block.

**D9. Reconnection = re-derive everything in `mount/3`.**
Views subscribe and load full state when `connected?(socket)`; events only trigger re-query/patch. LiveView's client auto-rejoins with built-in backoff (satisfying the ≥2s-floor spirit of the Django spec without custom code). Missed events during a disconnect need no replay because mount is history-free. *Alternative:* event-sourced assigns with sequence numbers and gap detection — massive complexity for a dataset that re-queries in microseconds.

## Risks / Trade-offs

- [Idle broadcast on deploy/boot startles nobody but tests may race on it] → `init/1` broadcast is fire-and-forget to a topic with usually zero boot-time subscribers; tests subscribe before starting the board when they want to assert it.
- [Secretary must re-push after a MonitorBoard crash (D5)] → acceptable by design: crash frequency ≈ 0 for a process this small; the projector shows a clean idle screen (never wrong data), and re-push is one click. Mitigation beyond that would be persistence machinery (rejected in D5).
- [Thin events cause an N-subscriber query stampede on each event] → N ≤ 10 subscribers, SQLite in WAL with reads that take microseconds; measured non-issue at venue scale. If it ever grows, fatten specific events, not the pattern.
- [Presence lag: a judge can look online up to a heartbeat timeout after unplugging] → documented as advisory (D8); the secretary's operational check is "did the judge's score arrive", which is a DB fact.
- [Contract drift between 04 (producer), 05 (this), 06 (consumer)] → single `Events` module is the compile-time choke point; specs in all three changes name identical topics/events; a cross-layer integration test (task 6.5) broadcasts each event and asserts the tuple shape.

## Open Questions

- Should `publish_performing` be called automatically by the activation operation in 04, or only manually by the secretary? **Default:** automatic on activation (`performance_started` handler in SecretaryLive pushes `:performing`), with the secretary able to override; final wiring decided in 06 — the board API is agnostic either way.
- Exact shape of `data` for each mode (fields of the performing card, standings row). **Default:** defined by the consumer in 06 as plain maps; the board and this spec treat `data` as opaque.
