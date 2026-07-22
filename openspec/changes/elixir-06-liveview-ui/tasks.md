# Tasks — elixir-06-liveview-ui

## 1. Auth (phx.gen.auth adapted)

- [ ] 1.1 Adapt/unpark the `mix phx.gen.auth` (LiveView option) output already committed by `elixir-03-ecto-schema` — do NOT rerun the generator (it collides with the existing migration/schema); reconcile with the `users` table (username, role, category, active — no email)
- [ ] 1.2 Strip email flows: remove confirmation/magic-link/password-reset routes, controllers, templates and token types; login form is username+password only
- [ ] 1.3 Make login reject `active: false` users with the generic invalid-credentials error
- [ ] 1.4 Add `{:ensure_role, roles}` on_mount clause (and matching plug for controller routes) to `UshuWeb.UserAuth`; redirect anonymous to login, wrong-role to their home with a flash
- [ ] 1.5 Write auth tests: username login success/failure, inactive rejection, on_mount halt for anonymous and wrong-role on both dead and connected mounts

## 2. Router, layout, i18n plumbing

- [ ] 2.1 Define live_sessions in the router: `:judge_area` (/judge), `:main_judge_area` (/scores), `:admin_area` (/secretary, /users, /print/:tablo_id), `:monitor_public` (/monitor); root redirect per role after login
- [ ] 2.2 Root layout: current user name + role badge, logout button, flash group; projector layout variant without chrome for /monitor
- [ ] 2.3 Locale plug (param → session → `ru` default) plus `on_mount :set_locale` hook so live processes match the dead render; language toggle in the layout
- [ ] 2.4 Router test: every live route except /monitor is inside a live_session carrying the expected role guard
- [ ] 2.5 User management screens for admin (`/users`): create judge (username, password, role, category), deactivate/reactivate, password reset — calling `Ushu.Accounts.create_user/1`, `deactivate_user/1`, `reset_password/2` from `elixir-04-contexts`; tests

## 3. Judge consoles

- [ ] 3.1 `JudgeEntryLive` at /judge: dispatch by `current_user.category` to the A/B/C console; friendly error for nil category
- [ ] 3.2 Shared judge-console behavior (waiting screen, subscribe to `"competition"`, swap on `{:performance_started, id}` / `{:performance_finalized, id}` / `{:score_reopened, score_id}`, read-only submitted state) as a function-component + helper module
- [ ] 3.3 `JudgeALive`: error-code circles (kinds `:a` + `:shared`), tap-to-add with duplicates, entry list with per-entry remove, submit with confirmation; calls `Competition.submit_a/2`
- [ ] 3.4 `AHotkeys` JS hook: `event.code` Space/Enter/NumpadEnter triggers the submit confirmation; ignore `event.repeat`; detach in `destroyed`
- [ ] 3.5 `JudgeBLive`: numpad + keyboard input, embedded-schema changeset via `to_form` (numeric, 2 decimals, range), live `phx-change` validation, B-error circles, submit disabled while invalid; calls `Competition.submit_b/2`
- [ ] 3.6 `JudgeCLive`: element list from the participation snapshot with cursor, verdict buttons, submit disabled while any mark is `:pending`, unmarked-elements highlight; calls `Competition.submit_c/2`
- [ ] 3.7 `CHotkeys` JS hook: `KeyV`/`KeyX`/`KeyC` set performed/failed/pending, arrows move cursor, marking advances to next pending — all via `event.code`
- [ ] 3.8 LiveView tests for the three consoles: activation swap, reopen returns the card, late-submit-after-finalize shows flash (no crash), C submit blocked until fully marked, B rejects malformed input and accepts 0.00

## 4. Secretary and main judge

- [ ] 4.1 `SecretaryLive`: tablo grid (category x age x sex), tablo selection via `handle_params` patch, participation list as a stream with state badges and draw order
- [ ] 4.2 Standings table with tie-break ranks from `Competition.standings/1`; finished-only ranks, no_show unranked at the bottom
- [ ] 4.3 Secretary actions: activate, per-tablo draw, push standings/scores to monitor, delete participation — confirmations on destructive actions, context errors surfaced as flashes
- [ ] 4.4 Subscribe `SecretaryLive` to `"competition"` and refresh streams/tables on each event
- [ ] 4.5 Judge presence panel from `UshuWeb.Presence` (topic per `elixir-05-realtime`): online/offline per judge with category, updates on presence_diff
- [ ] 4.6 `ScoresLive`: per-judge breakdown (A errors, B effective scores, C marks) + aggregated A/B/C and projected final; bonus toggle, finalize (disabled until all cards saved, missing judges listed), no-show, per-judge reopen incl. B judges — every reopen behind a confirm
- [ ] 4.7 Tests: activation race error rendering, finalize gate, reopen broadcast round-trip (judge console leaves submitted state), no-show produces `:no_show` not finished-with-zero, presence panel reflects join/leave

## 5. Monitor and print

- [ ] 5.1 `MonitorLive`: mount reads `MonitorBoard.current()` + subscribes `"monitor"`; `handle_info({:monitor_updated, state})` replaces the assign; four mode renders (idle/performing/scores/standings) with projector-scale typography
- [ ] 5.2 Idle mode branding from `EVENT_TITLE`/`EVENT_SUBTITLE` runtime config; flag images with blank placeholder when missing
- [ ] 5.3 `PrintLive` at /print/:tablo_id: protocol header, rank-ordered rows (finished only), no-show marking, `@media print` stylesheet hiding chrome with clean page breaks
- [ ] 5.4 Tests: monitor mode switching on `{:monitor_updated, ...}`, snapshot re-read on remount (restart simulation), print ranks cover exactly finished participations

## 6. i18n and polish

- [ ] 6.1 Wrap all user-visible strings in `gettext`/`dgettext`; run `mix gettext.extract && mix gettext.merge priv/gettext --locale ru --locale en`
- [ ] 6.2 Fill `ru` translations (complete) and `en` translations; smoke test asserting key screens render Russian by default with no raw msgids
- [ ] 6.3 Touch-target and typography pass on judge consoles and monitor (min ~48px targets, high contrast); map state enums to literal Tailwind class strings (no string-built classes)
- [ ] 6.4 End-to-end LiveView test: activate → three consoles submit → finalize → standings and monitor update — asserting the full happy path over PubSub
- [ ] 6.5 Write the Russian explainer `docs/elixir-rewrite/06-liveview-ui.md` (lifecycle, assigns/change tracking, HEEx, to_form, hooks, streams, live_session auth, Vaadin parallels)
