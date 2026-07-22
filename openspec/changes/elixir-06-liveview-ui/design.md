# Design — elixir-06-liveview-ui

## Context

Layer 6 of the ushu Elixir rewrite: every screen as a LiveView. The Django app
serves ~10 weak browser clients over an offline venue LAN from one laptop, with
timer-polling judge screens and an HTML-snapshot SSE monitor. This layer
replaces all of that with server-rendered LiveViews driven by the PubSub
events and `MonitorBoard` snapshot from `elixir-05-realtime`, calling only the
context functions from `elixir-04-contexts`. Auth is session-based
username/password (no email on an offline LAN), roles `[:admin, :main_judge,
:judge]` from `elixir-03-ecto-schema`.

Assumed interfaces (coordination notes in the master brief):

- Topic `"competition"`, events `{:performance_started, id}`,
  `{:score_saved, score_id}`, `{:score_reopened, score_id}`,
  `{:performance_finalized, id}` (defined in `elixir-05-realtime`).
- Topic `"monitor"`, event `{:monitor_updated, %MonitorState{}}`;
  `Ushu.Competition.MonitorBoard.current/0` for the current snapshot,
  `MonitorState.mode ∈ [:idle, :performing, :scores, :standings]`.
- `UshuWeb.Presence` tracking judges on a topic defined in `elixir-05-realtime`.
- Context functions from `elixir-04-contexts`:
  `Competition.register_participant/2`, `Competition.draw_tablo/2`,
  `Competition.draw_all/2` (opts: `force:`, `shuffle:`),
  `Competition.activate/2`, `Competition.active_participation/0`,
  `Competition.submit_a/2`, `Competition.submit_b/2`, `Competition.submit_c/2`
  (judge is the actor), `Competition.finalize/3` (attrs: `%{bonus: boolean}` —
  bonus is an argument of finalize, there is no separate set_bonus),
  `Competition.mark_no_show/2`, `Competition.reopen_judge/2`,
  `Competition.standings/1`; plus `Accounts.create_user/1`,
  `Accounts.deactivate_user/1`, `Accounts.reset_password/2` and the adapted
  phx.gen.auth session functions.

## Goals / Non-Goals

Goals:

- All eight screens (login, judge A/B/C, secretary, scores review, monitor,
  print) as LiveViews under role-scoped `live_session`s.
- Layout-independent physical-key hotkeys (`event.code`) for judges A and C.
- Client-side ergonomics (disabled submits, confirmations, inline validation)
  on top of — never instead of — the server-side rules in `elixir-04-contexts`.
- gettext i18n, `ru` default.

Non-Goals:

- No business logic in LiveViews (belongs to `elixir-04-contexts`).
- No event/topic definitions (belongs to `elixir-05-realtime`).
- No offline/PWA capability, no mobile app, no multi-carpet UI.
- No CSS framework bake-off: whatever `elixir-01-foundation` set up
  (Phoenix 1.8 default: Tailwind + daisyUI) is used as-is.

## Decisions

### D1 — phx.gen.auth as the base, surgically de-mailed

Adapt the generator output already committed by `elixir-03-ecto-schema` (do
NOT rerun `mix phx.gen.auth` — it collides with the existing migration and
schema), removing email-centric parts: registration stays
admin-only (no self-signup), delete confirmation/magic-link/reset-by-email
controllers, templates and tokens; rename `email` to `username` in the schema
usage (the `users` table itself is owned by `elixir-03-ecto-schema`). Keep the
generated session controller, `UserAuth` plug/on_mount machinery, and the
"sudo mode" removal is acceptable since only the admin edits users.
*Alternatives*: hand-rolled auth (rejected: reimplements session fixation
protection, token hashing, remember-me for no gain); keeping email flows
dormant (rejected: dead attack surface and confusing code for a learner
codebase).

### D2 — role guard as a parameterized on_mount in UserAuth

One hook, `on_mount({UshuWeb.UserAuth, {:ensure_role, [:admin, ...]}})`,
attached per `live_session`. It reads `current_scope`/`current_user` from the
session, halts with `redirect(to: ~p"/login")` when absent, halts with a flash
when the role does not match. Plugs guard the non-live controller routes
(session create/delete) symmetrically. *Alternatives*: per-LiveView `mount`
checks (rejected: forgettable, duplicated); separate router pipelines only
(rejected: pipelines do not run on live navigation within a session —
`on_mount` does).

### D3 — live_session per role, monitor public

Sessions: `:judge_area` (`/judge`), `:main_judge_area` (`/scores`, allowed
`[:main_judge, :admin]`), `:admin_area` (`/secretary`, `/users`,
`/print/:tablo_id`, allowed `[:admin]`), `:monitor_public` (`/monitor`, no
auth — the projector machine has no operator; it shows only public data).
Live navigation cannot cross live_sessions, which is exactly the security
property we want. *Alternative*: one big session with per-view checks
(rejected: a compromised judge socket could live-navigate into secretary
views before the check runs; session boundaries make the guard structural).

### D4 — one /judge route, three LiveView modules

`/judge` is handled by a tiny dispatcher: `mount` reads
`current_user.category` and the route table actually defines one live view per
console (`/judge` redirects/patches to itself but assigns the right component).
Concretely: keep three modules `JudgeALive`, `JudgeBLive`, `JudgeCLive` and let
a plug (dead render) or `push_navigate` in a `JudgeEntryLive` route to the
right one. Three modules keep each console's state machine small and readable.
*Alternative*: one `JudgeLive` with `case category` in render (rejected: three
unrelated state shapes and hotkey hooks in one module; harder to teach and
test).

### D5 — hotkeys via small JS hooks keyed on event.code

One hook per console (`AHotkeys`, `CHotkeys`) attached to the card's root
element: `window`-level `keydown` listener filtering on `event.code`
(`Space`/`Enter`/`NumpadEnter` for A submit; `KeyV`/`KeyC`/`KeyX` plus arrows
for C), calling `this.pushEvent("mark", %{verdict: ...})`. `event.code` names
the physical key position, independent of layout — this is the fix for the
Cyrillic-layout bug pinned in the brief. Hooks are removed in `destroyed()`.
*Alternatives*: `phx-window-keydown` (rejected for C: it delivers `event.key`,
which is layout-dependent — exactly the bug; acceptable for pure
Space/Enter but we keep one mechanism for both consoles); global shortcut
libraries (rejected: dependency for 30 lines of JS).

### D6 — forms only where there is a form

`JudgeBLive` uses an embedded-schema changeset + `to_form` (numeric cast,
range validation, live `phx-change` validation). A and C cards are not forms:
they are lists of tap events mutating server state per interaction
(`phx-click`/hook `pushEvent`), with the card state held in assigns and
persisted through context calls. *Alternative*: modeling A/C as big forms
(rejected: fights LiveView — every tap is already a server round-trip; there
is no "unsubmitted form state" worth keeping).

### D7 — streams for long lists, plain assigns for computed tables

Participation lists in `SecretaryLive` use `Phoenix.LiveView.streams` (bounded
server memory, id-addressed row updates on PubSub events). The standings table
and per-judge breakdown use plain assigns: ranks and aggregates are computed
over the whole set on every relevant event, so diffing whole small tables is
simpler and correct-by-construction. *Alternative*: streams everywhere
(rejected: rank columns change globally on one insert — stream row-patching
buys nothing and complicates reset logic).

### D8 — LiveViews re-query on event, payloads carry ids only

Event payloads are `{event, id}` (defined in 05); consoles re-fetch exactly
what they show through context functions. DB (SQLite on the same laptop) is
the source of truth; re-query cost is negligible at this scale (≤ hundreds of
rows) and eliminates stale-payload bugs. *Alternative*: fat event payloads
(rejected in 05's contract; also creates divergent copies of truth).

### D9 — monitor state from MonitorBoard, LiveView replaces SSE

`MonitorLive.mount` (connected) does `MonitorBoard.current()` +
`PubSub.subscribe("monitor")`; `handle_info({:monitor_updated, state})`
replaces the assign wholesale. Reconnect-after-restart is LiveView's built-in
rejoin: mount runs again and reads the fresh snapshot — this satisfies the
pinned monitor-realtime requirements (no polling, no torn reads, no
filesystem HTML) without a custom SSE channel. Idle branding comes from
`EVENT_TITLE`/`EVENT_SUBTITLE` runtime env (from `elixir-01-foundation`).

### D10 — PrintLive as a LiveView with print CSS

The protocol is a LiveView in the `:admin_area` session (it needs live tablo
selection anyway); printing is plain browser print with an `@media print`
stylesheet hiding chrome. *Alternative*: dead controller render or PDF
generation (rejected: a printable HTML page is sufficient for the venue
printer, zero deps; PDF libs are heavy and unneeded).

### D11 — locale in the session, applied twice

A plug resolves the locale (`?locale=` param → session → default `ru`) and
calls `Gettext.put_locale/2`; an `on_mount` hook repeats this for the live
socket process (LiveView runs in a different process than the dead render, so
the plug alone is not enough). *Alternative*: per-user locale column
(rejected for now: an event is run in one language; the session toggle covers
the rare English need — recorded as the default answer to the open question).

## Risks / Trade-offs

- [Judge stations on flaky venue Wi-Fi lose the socket and miss a broadcast]
  → LiveView auto-rejoins and every console re-reads its state in `mount`;
  state is derived from the DB, never accumulated client-side, so a rejoin is
  always a full resync. Presence makes drops visible to the secretary.
- [Key hooks double-fire submits (key repeat, key + button)] → confirmation
  step on A submit; server-side idempotence (submitting an already-saved card
  is rejected by the context); hooks ignore `event.repeat`.
- [Public `/monitor` leaks data] → snapshot contains only what the hall
  screen shows anyway; mitigation is scope discipline in `MonitorState`
  (05), not auth.
- [`live_session` misconfiguration silently exposes a view] → router test
  asserting every non-monitor live route sits in a session with the expected
  `on_mount` guards; guard unit tests per role.
- [Tailwind/daisyUI purge misses classes built dynamically (state badges)] →
  never string-build class names; map enums to full literal class strings.
- [gettext msgids drift / raw msgid on screen] → `mix gettext.extract --check`
  in CI (from `elixir-01-foundation`) plus a smoke test rendering key screens
  under `ru`.

## Migration Plan

None within this change (new code). Cutover from the Django UI happens in
`elixir-07-cutover`; both UIs can run side by side against separate DBs during
the dry-run tournament.

## Open Questions

- Should judge consoles show the running A/B aggregate to the judge before
  finalization? Default: no — judges see only their own card (matches Django
  behavior and avoids anchoring); the main judge sees aggregates in
  `ScoresLive`.
- Monitor `:scores` mode auto-switch on finalization vs explicit secretary
  push only. Default: explicit push only (matches the Django operator flow);
  the `MonitorBoard` API in 05 already supports either.
