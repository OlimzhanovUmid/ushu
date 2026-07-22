# elixir-05-realtime — tasks

## 1. Event bus

- [ ] 1.1 Create `Ushu.Competition.Events` with `@competition_topic "competition"` and `@monitor_topic "monitor"` as the only definitions of these strings
- [ ] 1.2 Implement `subscribe_competition/0` and `subscribe_monitor/0` wrapping `Phoenix.PubSub.subscribe(Ushu.PubSub, topic)`
- [ ] 1.3 Implement `broadcast_performance_started/1`, `broadcast_score_saved/1`, `broadcast_score_reopened/1`, `broadcast_performance_finalized/1` emitting the exact tuples `{:performance_started, id}`, `{:score_saved, id}`, `{:score_reopened, id}`, `{:performance_finalized, id}`
- [ ] 1.4 Implement `broadcast_monitor_updated/1` emitting `{:monitor_updated, %MonitorState{}}` on the monitor topic
- [ ] 1.5 Add an after-commit helper `Events.broadcast_after(result, fun)` that broadcasts only when the transaction result is `{:ok, _}` and passes the result through unchanged
- [ ] 1.6 Add typespecs and module docs listing the full producer/consumer catalog (who emits, who listens — referencing elixir-04-contexts and elixir-06-liveview-ui)

## 2. Monitor state and GenServer

- [ ] 2.1 Create `Ushu.Competition.MonitorState` defstruct `[mode: :idle, data: nil, updated_at: nil]` with `@type mode :: :idle | :performing | :scores | :standings` and a `t()` typespec
- [ ] 2.2 Create `Ushu.Competition.MonitorBoard` GenServer registered as `name: __MODULE__`, `init/1` returning the idle state
- [ ] 2.3 Implement client API `publish_performing/1`, `publish_scores/1`, `publish_standings/1` as casts and `clear/0` as a cast, each building the new `%MonitorState{}` with `updated_at: DateTime.utc_now()`
- [ ] 2.4 Implement `current/0` as a synchronous `GenServer.call` returning the state struct
- [ ] 2.5 Broadcast `{:monitor_updated, state}` via `Events.broadcast_monitor_updated/1` from every `handle_cast` that changes state, and from `init/1` (idle reset on restart)
- [ ] 2.6 Verify the module contains no `Repo`/`Ecto` references (data is built by callers)

## 3. Supervision

- [ ] 3.1 Add `Ushu.Competition.MonitorBoard` to `Ushu.Application` children after `{Phoenix.PubSub, name: Ushu.PubSub}` and before the Endpoint, default `:permanent` restart under the existing `:one_for_one` strategy
- [ ] 3.2 Test: kill the board with `Process.exit(pid, :kill)`; assert the supervisor restarts it, `current/0` returns the idle state, and a subscriber receives the idle `{:monitor_updated, _}` broadcast
- [ ] 3.3 Test: a subscriber process survives a board crash and stays subscribed (receives the next publish after restart)

## 4. Presence

- [ ] 4.1 Create `UshuWeb.Presence` with `use Phoenix.Presence, otp_app: :ushu, pubsub_server: Ushu.PubSub`
- [ ] 4.2 Add `UshuWeb.Presence` to the application children (after PubSub, before the Endpoint)
- [ ] 4.3 Define the tracking contract in module docs: topic `"presence:judges"`, key `to_string(user.id)`, meta `%{username, role, category, online_at}` (the tracking `on_mount` hook itself ships in elixir-06-liveview-ui)
- [ ] 4.4 Add convenience functions `track_judge(pid, user)` and `list_judges/0` returning `[%{id, username, role, category, online_at}]` sorted by category then username
- [ ] 4.5 Test: track two pids under one user id, assert `list_judges/0` shows the judge once; kill one pid, judge remains; kill the second, judge disappears (assert via `"presence_diff"` message)

## 5. Reconnection semantics

- [ ] 5.1 Document (moduledoc on `Events`) the consumer rule: subscribe + full state derive in connected `mount/3`; events are invalidation hints; no timer polling
- [ ] 5.2 Test: subscribe a test process, call `MonitorBoard.publish_scores/1`, assert the received snapshot equals `MonitorBoard.current/0` (mount-time fetch and event payload agree)
- [ ] 5.3 Test: after a simulated missed event (publish while not subscribed), a fresh `current/0` returns the latest snapshot — proving remount needs no replay

## 6. Contract and integration tests

- [ ] 6.1 Test each `broadcast_*` function delivers exactly its documented tuple to a subscribed test process (shape-pinning tests for the 04/06 contract)
- [ ] 6.2 Test `broadcast_after/2` broadcasts on `{:ok, _}` and stays silent on `{:error, _, _, _}` (Multi failure shape) and `{:error, _}`
- [ ] 6.3 Test no torn reads: publish two snapshots rapidly; assert a subscriber only ever receives complete `%MonitorState{}` structs whose mode matches their data
- [ ] 6.4 Test `clear/0` broadcasts an idle snapshot with `data: nil`
- [ ] 6.5 Cross-layer smoke test kept green through 04/06: a single test module asserting the topic names and every event tuple shape, referenced by the sibling changes' tasks
- [ ] 6.6 Run `mix test` and `mix format --check-formatted`; all green

## 7. Documentation

- [ ] 7.1 Write the Russian explainer `docs/elixir-rewrite/05-realtime.md` (processes/mailboxes, GenServer walkthrough on MonitorBoard, supervision & let-it-crash, PubSub mechanics, Presence CRDT basics, DB-as-source-of-truth rationale)
- [ ] 7.2 Cross-check explainer code samples compile against the actual modules (paste into `iex -S mix` or a doctest)
