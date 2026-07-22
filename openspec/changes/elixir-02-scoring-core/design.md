# Design — elixir-02-scoring-core

## Context

The Django scoring lives in `tablo/models.py` (`calculateA/B/C`,
`get_b_score`, `get_scores`) and `tablo/views.py` (`counts`, `cmp`, `sort`),
entangled with the ORM (`WrapperErrorCode`, `CombinationStatus`,
`ElementStatus` sortedm2m chains) and per-instance memoization. The stabilized
rules are pinned in `stabilize-django/specs/scoring-correctness/spec.md` and
locked by three test files whose numbers this port must reproduce exactly.
This layer extracts the rules into `Ushu.Scoring`, a pure functional core with
no persistence knowledge, sitting between `elixir-01-foundation` (project
skeleton) and `elixir-03-ecto-schema`/`elixir-04-contexts` (which will load
rows and map them into this module's structs).

## Goals / Non-Goals

**Goals**

- 1:1 behavioral parity with the stabilized Django rules, proven by ported
  golden tests with exact integer assertions.
- A database-free, process-free module: every function referentially
  transparent, testable without any application boot.
- Explicit typed inputs (structs with typespecs) replacing Django's
  positional sortedm2m zip and tri-state `done` integers.
- Teach-by-example: doctests on every public function double as the owner's
  Elixir learning material.

**Non-Goals**

- Loading or persisting scores (elixir-03/04), completeness *enforcement*
  and ownership checks (elixir-04), PubSub events (elixir-05), any UI
  (elixir-06).
- Draw-order ranking of unfinished participations — needs participation
  state, stays in `elixir-04-contexts` (it will call `compare/2` for the
  finished-equal case).
- Re-litigating the rules themselves; they are pinned.

## Decisions

**D1. All values are integer centi-points end to end.**
Score-like quantities (A max 700/500, B inputs/aggregate, error values,
element scores 0.50 → 50, C pools 140/60/cap 200, final) are integers, and
floats appear only at the display boundary (`final_c / 100`). Django kept
floats internally and needed an explicit "round, don't truncate" fix
(`round(calculateB(...) * 100)`) because 9.58 was stored as 957.999….
Integers make that entire artifact class impossible; the only rounding left
is the trimmed-mean division in `aggregate_b/1` (`round/1`, banker-free
nearest integer). *Alternative considered:* `Decimal` library — correct but
heavier API, and needless when every legal input is an exact multiple of
0.01; floats with epsilon comparisons — rejected as the exact bug class the
Django change had to patch.

**D2. Inputs are structs (`Deduction`, `BScore`, `Mark`), not raw maps or
Ecto schemas.**
Structs give compile-checked keys (`@enforce_keys`), typespecs, and pattern
matching in function heads, and keep the core decoupled from persistence —
`elixir-04-contexts` maps Ecto rows to these structs at the boundary
(hexagonal "port" shape). `Mark` carries `verdict :: :pending | :performed |
:failed` replacing Django's `done ∈ {2, 1, 0}` magic integers, plus
`score_c` and `landing` denormalized from the element so the core never has
to look anything up. *Alternative:* passing Ecto structs directly — rejected;
it would drag Repo/preload concerns into the core and make doctests
impossible without a database.

**D3. A-majority keeps Django's consuming list-removal algorithm verbatim.**
`aggregate_a/2` ports `_errors_agreed_by_majority` exactly: walk judge 1's
errors, consume matches out of judges 2/3, then match the leftovers of judge
2 against judge 3. Matching keys on `code_id` only. *Alternative:* a
frequency-map (count per code, agreed when ≥ 2 judges) — simpler, but it is
NOT equivalent when a judge reports the same code multiple times (consumption
pairs one-to-one), and parity with the pinned behavior outranks elegance.
The consumption pass is implemented with `List.delete/2`-style recursion —
immutably, unlike Python's in-place `remove`.

**D4. `aggregate_c/1` zips per-judge mark lists by position, exactly like
Django's `zip(*statuses_per_judge)`.**
Marks arrive one list per judge, each ordered by `position` (the explicit
column that replaces the load-bearing sortedm2m order —
`elixir-03-ecto-schema` guarantees it). Decision per element: ≥ 2 real
`:performed` → agreed performed; else ≥ 2 real `:failed` → agreed failed +
pool deduction; else excluded. `:pending` is an abstention by construction —
it matches neither guard. Pools floor at 0 independently
(`max(0, pool)`), sum capped at 200. *Alternative:* grouping marks by
`element_id` — rejected: combinations may repeat an element, and position is
the identity Django used.

**D5. B aggregation operates on already-effective per-judge values;
`BScore.effective/1` is a separate function.**
Mirrors Django's split (`get_b_score` per score, `calculateB` over the list):
effective = `max(0, base − Σ deductions)`, `nil` only when nothing was
entered. This keeps `aggregate_b/1` a trivially doctestable
`[integer | nil] -> integer` function and gives `elixir-04-contexts` the
same per-judge value it must display on the review screen. Repeated-value
detection uses `Enum.frequencies/1` over integers — exact equality is safe
(D1), unlike Django's float-keyed `Counter` which merely happened to work
because inputs were parsed uniformly.

**D6. Tie-break is two functions: `tiebreak_counts/1` and `compare/2`.**
`tiebreak_counts/1` folds the AGREED marks (the `aggregate_c/1` output) into
`{e4, e3, e2}` with thresholds `score_c > 30 / > 20 / > 10` and the
performed-movement-only filter — the "abstention never counts" rule holds
automatically because undecided elements never reach the agreed list, and
explicitly because the filter demands `verdict: :performed`. `compare/2`
takes `{final_c, counts}` pairs and returns `:lt | :eq | :gt` (idiomatic
Elixir comparator, usable with `Enum.sort/2`). The unfinished-participation
branch of Django's `cmp` (finalscore × BIG − order) is state-dependent and
belongs to `elixir-04-contexts`. *Alternative:* one `sort/1` over rich
participation structs — rejected as scope creep into domain state.

**D7. `assemble/1` takes one flat input struct and returns
`%Ushu.Scoring.Result{}`; no memoization.**
Input: per-panel judge inputs, `age_bucket`, `bonus`, `saved` flags, and the
participation-state hint for no-show. Output carries agreed A errors, the
per-judge and aggregate B values, agreed C marks, per-panel centi scores,
`final_c`, `complete?`. Django memoized `get_scores` per instance because the
O(n log n) sort re-queried; a pure function over in-memory structs is
microseconds, so `elixir-04-contexts` simply assembles once per participation
before sorting. `Result.no_show/0` provides the canonical zero result,
replacing the `FINISHED && finalscore == 0` sentinel.

**D8. Age dependence is a total function over the pinned enum.**
`a_max(:adult) -> 500; a_max(bucket) -> 700` for the other five atoms, with a
guard restricting the input to the enum so a typo'd atom crashes loudly in
tests rather than silently scoring juniors as adults (Django compared
`age == AGE_18_plus`, silently treating any unknown int as junior).

**D9. Tests are a straight port plus doctests; file layout mirrors the
public API.**
`test/ushu/scoring/aggregate_a_test.exs`, `aggregate_b_test.exs`,
`aggregate_c_test.exs`, `assembly_test.exs`, `tiebreak_test.exs` — each
golden case cites its Django origin in a comment. Integer assertions use
`==`; the two Django `assertAlmostEqual` cases (1.5, 1.7) become exact
integer equality (150, 170) thanks to D1. Doctests run via one
`doctest Ushu.Scoring` (and per-struct) line in the test files.

## Risks / Trade-offs

- [Consumption-majority subtlety: duplicate error codes from one judge pair
  one-to-one, and a naive rewrite changes results] → keep the algorithm
  literal (D3) and add a test where one judge reports the same code twice.
- [Centi-point conversion mistakes at the boundary (e.g. passing 9.5 instead
  of 950)] → typespecs say `integer`, struct constructors validate with
  `is_integer` guards, and `elixir-04-contexts` owns a single conversion
  helper; golden tests would fail loudly on a 100× error.
- [Position-zip misalignment if judge mark lists differ in length] →
  `aggregate_c/1` requires equal-length lists (crash on mismatch rather than
  silently dropping tail elements, which `Enum.zip/1` would do);
  `elixir-04-contexts` guarantees every C judge gets the identical
  mark-row skeleton at registration (elixir-03 only defines the schema).
- [Behavioral drift from Django in edge cases the golden suite misses] → the
  suite ports *all three* Django test files, not just the golden file; any
  future divergence found during `elixir-07-cutover` dry runs gets a new
  locked test here first.
- [`round/1` vs Python `round()` half-even difference] → only reachable in
  the trimmed mean on a .5 centi boundary (needs n ≥ 4 distinct scores whose
  trimmed sum is odd); documented in the module doc and covered by a test
  fixing the Elixir behavior (half away from zero) as the spec.

## Open Questions

- Should `Result` also carry the raw per-judge inputs for the review UI?
  Default: yes — `elixir-06-liveview-ui` needs them and they are already in
  hand; revisit in elixir-04 if the struct gets unwieldy.
- Exact module split (`Ushu.Scoring` facade vs `Ushu.Scoring.A/B/C`
  submodules). Default: single facade module with private helpers, structs in
  `lib/ushu/scoring/`; split only if the file passes ~300 lines.
