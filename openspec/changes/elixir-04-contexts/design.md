# elixir-04-contexts — Design

## Context

Layer 4 of the 7-layer Elixir rewrite. elixir-02 delivered the pure scoring core
(`Ushu.Scoring`), elixir-03 the Ecto schemas with database constraints (unique tablo/
participation/score keys, the partial unique index on `participations(state='performing')`,
FK `on_delete: :restrict` on reference data). This layer adds the business operations the
Django app spread across `ParticipationManager`, view classes (`JudgeASubmit`,
`ParticipantActivateView`, `JrebiView`, `open_judge`, …) and a post-save signal — as
context modules with explicit, testable function contracts. elixir-06 LiveViews will be
thin: parse input, call one context function, render the tagged-tuple result.

## Goals / Non-Goals

**Goals**

- One public function per business operation, exact signature, exact error atoms.
- Invariants enforced in the context + database, not in the UI: single-performing,
  panel snapshot rules, C completeness, ownership, error-code kinds.
- Every mutation: audit row in-transaction, PubSub broadcast post-commit.
- Standings/tie-break arithmetic stays in `Ushu.Scoring`; contexts only load and map data.

**Non-Goals**

- No LiveViews, plugs, or authorization checks by role (elixir-06 owns "who may call");
  contexts own "what is a valid call".
- No GenServers/Presence/MonitorBoard (elixir-05).
- No CSV/DB import (elixir-07).
- No CRUD beyond what the competition flow needs (admin CRUD is thin Ecto passthrough,
  listed in tasks but not specified per-field).

## Decisions

**D1 — Four contexts: `Ushu.Accounts`, `Ushu.Catalog`, `Ushu.Roster`, `Ushu.Competition`.**
Bounded by change-reason: Accounts = identity and panel membership; Catalog = reference
data configured before the event (element categories, elements, combinations, error codes);
Roster = who competes (participants, clubs, countries, participation removal);
Competition = everything that happens live. Alternatives: one `Ushu.Core` god-context
(rejected: Django's `tablo/views.py` shows where that ends — 800 lines mixing draw, auth,
SSE and scoring); context-per-schema (rejected: `activate/2` touches participations, scores
and audit — schema-sized contexts force cross-context writes for one operation).

**D2 — Tagged tuples + `with`, never exceptions, for domain outcomes.** Every public
mutation returns `{:ok, value} | {:error, reason}` where `reason` is an atom or
`{atom, detail}` from a documented, exhaustive-per-function set. Bang variants are not
exposed for mutations. Constraint violations that encode domain rules (the partial unique
performing index) are converted via changeset constraints to `{:error, :another_performing}`.
Alternative: raising + `Plug.Exception` style rescue (Spring-like, rejected: race-driven
errors here are NORMAL flow — a judge submitting after finalize happens at every event and
must render as a friendly message, per the Django stabilization spec).

**D3 — Exact public signatures (the elixir-06 contract).**

```elixir
# Ushu.Accounts (additions to phx.gen.auth output from 01/03)
list_panel_judges()   :: [User.t()]           # active, role: :judge, ordered by username
create_user(attrs)    :: {:ok, User.t()} | {:error, Ecto.Changeset.t()}   # admin screens (elixir-06)
deactivate_user(%User{}) :: {:ok, User.t()} | {:error, Ecto.Changeset.t()}
reset_password(%User{}, new_password) :: {:ok, User.t()} | {:error, Ecto.Changeset.t()}
list_online_ids(...)  # deferred to elixir-05 (Presence)

# Ushu.Catalog
create_element_category(attrs) ::
  {:ok, %{category: ElementCategory.t(), tablos: [Tablo.t()]}} | {:error, Ecto.Changeset.t()}
list_error_codes(kind :: :a | :b) :: [ErrorCode.t()]   # includes :shared codes

# Ushu.Roster
create_participant(attrs)  :: {:ok, Participant.t()} | {:error, Ecto.Changeset.t()}
delete_participation(id, actor) :: {:ok, Participation.t()} | {:error, :not_found | :performing}

# Ushu.Competition
register_participant(%Participant{}, %ElementCategory{}) ::
  {:ok, [Participation.t()]} | {:error, Ecto.Changeset.t()}
draw_tablo(tablo_id, actor)  :: {:ok, Tablo.t()} | {:error, :not_found | :already_started}
draw_all(opts \\ [], actor)  :: {:ok, %{drawn: [tablo_id], skipped: [tablo_id]}}   # force: boolean
activate(participation_id, actor) ::
  {:ok, Participation.t()} | {:error, :not_found | :not_waiting | :another_performing}
active_participation() :: Participation.t() | nil
submit_a(%User{}, [error_code_id]) ::
  {:ok, Score.t()} | {:error, :no_active | {:invalid_codes, [id]}}
submit_b(%User{}, %{base: number, error_code_ids: [id]}) ::
  {:ok, Score.t()} | {:error, :no_active | :invalid_score | {:invalid_codes, [id]}}
submit_c(%User{}, %{mark_id => :performed | :failed}) ::
  {:ok, Score.t()} | {:error, :no_active | {:not_owner, [id]} | {:unmarked, [id]}}
finalize(participation_id, %{bonus: boolean}, actor) ::
  {:ok, Participation.t()} | {:error, :not_found | :not_performing | :scores_pending}
mark_no_show(participation_id, actor) ::
  {:ok, Participation.t()} | {:error, :not_found | :not_performing}
reopen_judge(score_id, %User{} = actor) ::
  {:ok, Score.t()} | {:error, :not_found | :not_active}
standings(tablo_id) :: [%{rank: pos_integer | nil, participation: Participation.t(),
                          result: Ushu.Scoring.Result.t() | nil}]
```

Every mutation not initiated by a judge takes an explicit `actor` (`%User{}`) as its last
argument, feeding the audit event's actor id; `submit_a/b/c` omit it because the judge IS
the actor.

Rationale: submit functions take the JUDGE, not a score id — the card is derived
server-side (`active participation` × `judge`), so ownership cannot be forged (fixes the
Django IDOR class by construction, not by filtering). Alternative: LiveView passes
`score_id` (rejected: re-introduces the trust boundary we removed).

**D4 — Panel snapshot at registration (Django-compatible).** Score rows are created
eagerly in `register_participant/2` for every eligible active judge, encoding at
registration time who judges this participation. C-skip: age bucket in
`[:y7_8, :y9_10, :y11, :y12_14]` or `format in [:group, :duilian]` (enum, not name text).
Group dedup: skip a `:group` tablo when a group participation for the same club exists.
Alternative: snapshot the panel at ACTIVATION (fresher — a judge hired mid-day gets cards)
— rejected: changes operational semantics the owner relies on (cards visible in the scores
grid from registration), and mid-event judge changes are handled by deactivating + reopen,
same as Django.

**D5 — Every multi-step mutation is one `Ecto.Multi`, audit inside, broadcast outside.**
Pattern for all mutations:

```elixir
Multi.new()
|> Multi.update(:participation, state_changeset)
|> Multi.insert(:audit, fn %{participation: p} -> Audit.event(actor, :activated, p) end)
|> Repo.transaction()
|> case do
  {:ok, %{participation: p}} -> broadcast({:performance_started, p.id}); {:ok, p}
  {:error, _step, changeset, _} -> translate_error(changeset)
end
```

Audit insert shares the transaction (no mutation without its event, no event for a rolled-
back mutation). Broadcast strictly post-commit so subscribers re-querying always see the
committed row. Alternative: audit via broadcast consumer (rejected: loses atomicity — a
crashed consumer silently drops protest evidence).

**D6 — Error-code validation by `kind`, reject instead of warn-and-drop.** A accepts kinds
`[:a, :shared]`, B accepts `[:b, :shared]`; any other id in the payload fails the whole
submission with `{:error, {:invalid_codes, ids}}`. Django warned and silently kept the rest;
rejected here because a partially-applied deduction list is exactly the "silently swallowed
input" failure the stabilization spec banned, and the LiveView UI (06) can re-render the
form with the codes highlighted at zero cost.

**D7 — `submit_c/2` persists partial verdicts but gates `submitted` on completeness.** Verdicts
map applies to the judge's own `score_marks`; foreign ids fail with `{:not_owner, ids}`
before any write. If pending marks remain, applied verdicts persist (the judge keeps
progress across screen reloads — Django behaved the same) but `submitted` stays false and
`{:error, {:unmarked, ids}}` names the gaps. Alternative: all-or-nothing (rejected: a C
judge marks 20+ elements live; losing them to one missed tap is an operational hazard).

**D8 — `reopen_judge/2` works per-score for ANY category, preserving entered data.** Only
flips `submitted -> false`; marks, deductions and base score remain for correction. This
honors the owner's zametka.txt wishlist (B judges were not individually reopenable in
Django — `open_judge` addressed judges by list index; we address by score id). Restricted
to `:performing` participations; changing a finished result is finalize-again territory and
stays out of scope (audit trail covers protests).

**D9 — `finalize/3` requires all cards saved.** Django exposed the same rule as the
`can_be_saved` flag driving the button; making it a server-side gate
(`{:error, :scores_pending}`) closes the gap where a crafted POST finalized early. Final
score = `Ushu.Scoring` assembly over data loaded via one preload query; centi-point
arithmetic lives ONLY in elixir-02.

**D10 — `mark_no_show/2` replaces the zero-score sentinel.** Explicit `:no_show` state; all
score rows set `submitted: true` to release judge screens; `final_score_centi` stays nil.
Standings sort: finished by (final_score_centi, tie-break) desc, then no_show, then
waiting/performing by `draw_order`. Tie-break counters come from `Ushu.Scoring` (e4/e3/e2 over agreed-performed
movement elements, thresholds 0.3/0.2/0.1).

**D11 — `create_element_category/1` creates tablos explicitly, not via signal.** Django
used a `post_save` signal (racy per the data-integrity spec). Here one Multi inserts the
category and its 12 tablos (6 age buckets × 2 sexes); the unique index from elixir-03 makes
re-runs idempotent. Explicit call sites over lifecycle magic — the Elixir norm.

## Risks / Trade-offs

- [Draw uses randomness — flaky tests] → Draw accepts an injectable shuffle function via an
  internal seam (`draw_all([force: false, shuffle: &Enum.shuffle/1], actor)` default); tests pass a
  deterministic one. Spec-level behavior (0..n-1 unique per tablo) is random-independent.
- [SQLite single-writer: concurrent activates serialize on the write lock, so the partial
  index race is near-untriggerable in production] → Keep the constraint mapping anyway
  (costs nothing, guards future Postgres moves); test it with two racing transactions.
- [PubSub event names drift between 04 (producer) and 05/06 (catalog/consumer)] → Names are
  pinned identically in all three specs: topic `"competition"`, events
  `{:performance_started, id}`, `{:score_saved, score_id}`, `{:score_reopened, score_id}`,
  `{:performance_finalized, id}`. elixir-05 additionally defines a single
  `Ushu.Competition.Events` module both sides compile against; 04 tasks include a TODO
  marker to swap raw tuples for that module when 05 lands (tuple shape is identical).
- [Registration silently skipping group duplicates may confuse the secretary] → Return
  value distinguishes created vs skipped tablos in the `{:ok, participations}` list length;
  06 surfaces a notice when fewer participations than matching tablos were created.
- [Partial C persistence (D7) can leave half-updated cards if the judge abandons the form]
  → Harmless: `submitted` stays false, the card renders with saved progress, reopen semantics
  unchanged.

## Open Questions

- Should `delete_participation/2` be blocked once ANY score row has content (not just when
  `:performing`)? Default chosen: allow while `:waiting`/`:performing` is refused only for
  `:performing`; audit event records the deletion with actor. Revisit if protests demand
  stricter retention.
- Base score precision for B (`float` vs `Decimal`): elixir-02 fixed centi-point integer
  arithmetic internally; contexts pass through what the schema (elixir-03) stores. Default:
  keep the schema's type, convert at the `Ushu.Scoring` boundary.
