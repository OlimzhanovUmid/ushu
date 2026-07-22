# elixir-06-liveview-ui

## Why

The rewrite needs its user-facing layer: every screen of the judging system (judge consoles A/B/C, secretary console, main-judge score review, projector monitor, printable protocol) as Phoenix LiveViews, plus username/password authentication with role-based access — replacing Django's template+polling views and `is_staff`/`is_superuser` checks.

## What Changes

- Adapt `mix phx.gen.auth` to username+password login (no email flows — offline venue LAN), with role-aware `on_mount` guards for `:admin`, `:main_judge`, `:judge`.
- Router `live_session` blocks per role with a shared root layout; a single `/judge` route that mounts the console matching the logged-in judge's category (a/b/c).
- `JudgeALive`: error-code circles (kind `:a` + `:shared`), submit via on-screen button AND physical Space/Enter keys (JS hook on `event.code`).
- `JudgeBLive`: numeric score entry with an on-screen numpad, B-error deductions, client+server validation via `to_form`/changeset.
- `JudgeCLive`: element list with a cursor; verdicts via `event.code` `KeyV`/`KeyC`/`KeyX` (layout-independent — fixes the Cyrillic-layout bug) and on-screen buttons; submit disabled until no mark is `:pending`.
- `SecretaryLive`: category x age x sex tablo grid, standings table with computed ranks, activate/draw/monitor-push actions, judge presence panel (Phoenix.Presence from `elixir-05-realtime`).
- `ScoresLive` (main judge): per-judge score breakdown for the active participation, save/finalize, bonus toggle, no-show, per-judge reopen with confirmation (including B judges).
- `MonitorLive` (projector): subscribes to the `"monitor"` topic; renders four modes (`:idle`, `:performing`, `:scores`, `:standings`) with big typography; unauthenticated.
- `PrintLive`: printable competition protocol per tablo, ranks computed over finished participations only, print CSS.
- i18n via gettext: `ru` default locale, `en` secondary; all user-visible strings through `gettext`.
- Russian explainer `docs/elixir-rewrite/06-liveview-ui.md` teaching LiveView lifecycle, assigns/change tracking, HEEx, `to_form`, JS hooks, streams, `live_session` auth — with Vaadin/Jmix parallels.

## Capabilities

### New Capabilities

- `liveview-auth-routing`: username/password authentication (adapted phx.gen.auth), role-based `on_mount` guards, router `live_session` structure and layout.
- `judge-consoles`: the three judge scoring LiveViews (A errors, B numeric score, C element verdicts) with touch targets and layout-independent physical-key hotkeys.
- `secretary-monitor-screens`: secretary console, main-judge score review, projector monitor and printable protocol LiveViews, with gettext i18n.

### Modified Capabilities

None — new Elixir codebase.

## Impact

- New code only, all under `elixir/lib/ushu_web/` (LiveViews, components, hooks in `elixir/assets/js/`), plus router and gettext `.po` files.
- Layer 6 of 7. Depends on: `elixir-01-foundation` (project, gettext setup), `elixir-03-ecto-schema` (users table with `role`/`category`), `elixir-04-contexts` (all business operations the UI calls — activation, submissions, finalize, reopen, standings, draw), `elixir-05-realtime` (PubSub topic/event catalog, `MonitorBoard`, Presence). Consumed by `elixir-07-cutover` (release ships these screens).
- No changes to the Django app.
