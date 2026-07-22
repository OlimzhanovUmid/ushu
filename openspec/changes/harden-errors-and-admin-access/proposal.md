# Proposal: harden-errors-and-admin-access

## Why

A live Playwright walk of the full flow (login → registration → grid → detail → print → monitor → judge A/B/C) surfaced screens that crash with HTTP 500 instead of a clean 404, and no on-brand error page for when they do. `TabloDetailView.get_tablo()` resolves a tablo by `Tablo.objects.get(category=pk, sex=sex, age=age)` from the URL pk plus `?age`/`?sex` query params — so `/tablo/detail/56/` with no params (or any non-existent age/sex/category combo) raises `Tablo.DoesNotExist` and returns a raw Django 500. The same unguarded `objects.get()` pattern repeats across the print, monitor, activation, and score views. On the venue LAN with `DEBUG=0` a missing object shows Django's plain default 500/404 pages (off-brand); with `DEBUG=1` it shows the yellow debug traceback. Separately, `favicon.ico` 404s on every page load (log noise), and there is no in-app way for the main judge/secretary to reach Django's `/admin/`.

Scope is the current Django app only; the `elixir/` rewrite is untouched.

## What Changes

- Make object-lookup views return a proper **404** (not 500) when the requested tablo/participant does not exist: `TabloDetailView.get_tablo` (category+age+sex), `TabloMonitorView`/`TabloPrintView` (`get(pk=...)`), `ParticipantScoreView`/`PntElementView` (`Participant.objects.get(pk=...)`), and the activation lookup (`Tablo.objects.get(pk=...)`). Use `get_object_or_404` / explicit `Http404`, and treat missing/blank `age`/`sex` params as a 404, not an unhandled exception.
- Add **on-brand `404.html` and `500.html`** error templates using the foundation design tokens (navy "Federation Standard" shell), Russian text, with a link back to a safe screen. Wire `handler404`/`handler500` so they render even with `DEBUG=0`.
- Add a **favicon** (link + route) reusing the existing logo asset, so no page 404s for `favicon.ico`.
- Add a staff-only **"Admin" link** to the app-shell sidebar (`base_tablo_wmenu.html`) pointing at Django's `/admin/`, shown only to `is_staff` users, styled with the existing sidebar nav token vocabulary.

Out of scope: redesign of the working screens (done in the redesign changes), any scoring/behavior change, the Elixir rewrite.

## Capabilities

### New Capabilities

- `error-resilience`: object-not-found returns 404, on-brand 404/500 pages render under `DEBUG=0`, favicon served.
- `admin-access`: staff-only in-app entry point to the Django admin.

### Modified Capabilities

_None._

## Impact

- **Code**: `tablo/views.py` (guard the `objects.get()` lookups), `ushu/urls.py` (favicon route, `handler404`/`handler500` if not template-auto), `core/templates/404.html` + `core/templates/500.html` (new), `core/templates/core/base.html` (favicon link — already present, verify), `tablo/templates/tablo/base_tablo_wmenu.html` (staff-only Admin link).
- **Behavior**: bad/missing URLs now 404 cleanly instead of 500; no other behavior changes. Valid pages unaffected.
- **Depends on**: the redesign-foundation tokens/shell (already merged) for the error-page and Admin-link styling.
