# elixir-04-contexts

## Why

The Ecto schemas (elixir-03) give us data with constraints but no behavior; every business
rule of the live competition — registration panel snapshots, the draw, the single-performing
state machine, judge submissions, finalization, standings — must live in well-named context
functions with explicit success/error contracts so the LiveView layer (elixir-06) can call
them without re-implementing any rule.

## What Changes

- Add context modules `Ushu.Accounts` (judge-panel queries), `Ushu.Catalog` (element
  categories with automatic tablo creation, error-code queries by kind), `Ushu.Roster`
  (participants, participation deletion) and `Ushu.Competition` (all live-competition
  operations).
- `Ushu.Competition.register_participant/2`: creates participations in every matching tablo
  and snapshots the judge panel (3A/4B/3C score rows for active judges), skipping C judges
  for young age buckets and for `:group`/`:duilian` formats, and deduplicating group
  participations per club.
- `draw_tablo/2` and `draw_all/2`: transactional per-tablo shuffling with 0..n-1 numbering,
  refusing already-started tablos unless forced.
- `activate/2`: `:waiting -> :performing` transition inside an `Ecto.Multi`, backed by the
  partial unique index (single-performing invariant from elixir-03).
- `submit_a/2`, `submit_b/2`, `submit_c/2`: judge submissions with ownership by construction,
  error-code `kind` validation, C completeness gate, and graceful `{:error, :no_active}`
  when no participation is performing.
- `finalize/3`, `mark_no_show/2`, `reopen_judge/2` (ANY judge including B — owner wishlist),
  `standings/1` with the tie-break delegated to the pure `Ushu.Scoring` core (elixir-02).
- Every mutation appends a `score_events` audit row in the same transaction and broadcasts
  the `Phoenix.PubSub` events named in the elixir-05 realtime catalog after commit.

## Capabilities

### New Capabilities

- `competition-lifecycle`: registration with panel snapshot, draw, activation state machine,
  finalization, no-show, and standings with tie-break.
- `judge-submission`: A/B/C scorecard submission (ownership, validation, completeness) and
  per-judge reopen.
- `competition-audit-events`: append-only audit trail and post-commit PubSub broadcasts for
  every competition mutation.

### Modified Capabilities

None — new Elixir codebase.

## Impact

- Affected code: new files under `elixir/lib/ushu/` (`accounts.ex` additions, `catalog.ex`,
  `roster.ex`, `competition.ex`, `competition/audit.ex`) and their tests under
  `elixir/test/ushu/`.
- Layer 4 of 7. Depends on: `elixir-01-foundation` (project), `elixir-02-scoring-core`
  (pure aggregation and tie-break), `elixir-03-ecto-schema` (schemas, changesets,
  constraints incl. the partial unique performing index). Consumed by: `elixir-06-liveview-ui`
  (calls these functions), `elixir-05-realtime` (defines the PubSub event catalog these
  functions emit — topic and event names must match).
- No UI, no GenServers, no channels in this layer.
