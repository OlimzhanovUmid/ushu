# competition-audit-events

Cross-cutting contract every mutating `Ushu.Competition` function honors: an append-only
audit row inside the mutation's transaction, and a `Phoenix.PubSub` broadcast after — and
only after — successful commit. The event catalog itself (topics, payload structs,
subscription semantics) is owned by `elixir-05-realtime`; this capability pins the producer
side to the same names.

## ADDED Requirements

### Requirement: Every mutation appends an audit event atomically

Every state-changing `Ushu.Competition` function (register, draw, activate, submit_a/b/c,
finalize, mark_no_show, reopen_judge, participation deletion) SHALL insert a `score_events`
row in the SAME `Ecto.Multi`/transaction as the mutation, recording the actor's user id,
the action atom, the affected participation and/or score id, a payload map with the
action-specific detail (e.g. submitted code ids, reopened judge, bonus flag), and the
timestamp. The action atoms SHALL come from the `score_events` `event` enum defined in
elixir-03 — `:performance_started`, `:score_saved`, `:score_reopened`,
`:performance_finalized`, `:performance_no_show` — the same names as the PubSub events.
Audit rows are append-only: no context function updates or deletes them.

#### Scenario: Reopen leaves a protest trail

- **WHEN** the main judge reopens a judge's card and that judge resubmits a different score
- **THEN** `score_events` contains both the reopen event (with the main judge as actor and
  the target score id) and the new submit event, in insertion order

#### Scenario: Failed mutation leaves no audit row

- **WHEN** `activate/2` fails with `{:error, :another_performing}`
- **THEN** no `score_events` row is inserted for the attempt

### Requirement: Mutations broadcast the shared PubSub events after commit

After a successful commit — and never on rollback or error — the context SHALL broadcast on
`Ushu.PubSub` exactly the events defined in the `elixir-05-realtime` catalog, topic
`"competition"`: `activate/2` -> `{:performance_started, participation_id}`;
`submit_a/b/c` -> `{:score_saved, score_id}`; `reopen_judge/2` ->
`{:score_reopened, score_id}`; `finalize/3` and `mark_no_show/2` ->
`{:performance_finalized, participation_id}`. Broadcasting is fire-and-forget: a subscriber
crash MUST NOT affect the caller's result. The `"monitor"` topic and
`{:monitor_updated, %MonitorState{}}` are emitted by the `MonitorBoard` GenServer
(elixir-05), not by this layer.

#### Scenario: Save reaches subscribers exactly on commit

- **WHEN** a B judge's `submit_b/2` commits successfully
- **THEN** every subscriber of topic `"competition"` receives `{:score_saved, score_id}`
  and can re-query the already-committed row

#### Scenario: No event on a rejected submission

- **WHEN** `submit_c/2` returns `{:error, {:unmarked, ids}}`
- **THEN** no `{:score_saved, _}` event is broadcast

### Requirement: The database stays the single source of truth

Broadcast payloads SHALL carry only identifiers (and the event atom), never denormalized
row data: subscribers re-query the database on receipt. This guarantees a LiveView that
misses an event (e.g. across a reconnect) can always recover the full state by querying,
and no consumer ever renders stale broadcast-embedded data.

#### Scenario: Subscriber reconnects after missed events

- **WHEN** a LiveView process restarts and re-subscribes after missing several events
- **THEN** its mount-time query returns the current committed state with no dependence on
  the missed payloads
