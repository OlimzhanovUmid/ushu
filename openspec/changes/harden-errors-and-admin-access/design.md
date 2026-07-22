# Design: harden-errors-and-admin-access

## Context

Django 6 / Python 3.14, one waitress process on the venue LAN, `DEBUG=0` in production. Views resolve domain objects with bare `Model.objects.get(...)`:

- `TabloDetailView.get_tablo` → `Tablo.objects.get(category=pk, sex=sex, age=age)` (pk from URL, age/sex from query string)
- `TabloMonitorView.get_tablo` / `TabloPrintView.get_tablo` → `Tablo.objects.get(pk=pk)`
- `ParticipantScoreView` / `PntElementView` → `Participant.objects.get(pk=pk)`
- activation → `Tablo.objects.get(pk=tablo_id)`

Any missing row raises `DoesNotExist` → unhandled → HTTP 500. There are no `404.html`/`500.html` templates and no `handler404`/`handler500`, so error output is Django's default. The redesign foundation tokens and shell already exist and are the styling source for the new error pages and the Admin link.

## Goals / Non-Goals

**Goals:**
- A bad or incomplete object URL returns a clean 404, never a 500.
- Under `DEBUG=0`, 404 and 500 render on-brand (navy shell, Russian), with a way back.
- No favicon 404 noise.
- Staff can reach `/admin/` from the app shell; non-staff cannot see the link.

**Non-Goals:**
- No redesign of the working screens.
- No scoring/behavior change.
- No Elixir work.

## Decisions

### D1. `get_object_or_404`, and missing params = 404
Replace the unguarded `objects.get()` in the lookup views with `get_object_or_404` (or catch `DoesNotExist`/`ValueError` and raise `Http404`). For `TabloDetailView.get_tablo`, blank/missing `age` or `sex` query params are treated as a 404 (the object genuinely can't be resolved), not coerced or allowed to blow up. Rationale: these are user-reachable URLs (typed, stale bookmarks, a detail link opened without params); 404 is the correct semantic, 500 is a bug.

### D2. Template-based error handlers
Add `core/templates/404.html` and `core/templates/500.html`. Django auto-uses root-level `404.html`/`500.html` when `DEBUG=0`; `500.html` must be self-contained (no context processors are guaranteed during a 500). Keep them lightweight: navy background, crest/logo, a short Russian message, and a link to the standings/login. Rationale: the 500 template runs in a degraded request, so it cannot depend on `EVENT_TITLE` context or heavy includes.

### D3. Favicon via static link + a redirect route
Add a `<link rel="icon">` to the shells (base already has one — verify it points at a real asset) and a `/favicon.ico` route that redirects to the static logo, so direct `favicon.ico` hits (browsers request it implicitly) stop 404ing. Rationale: cheap, removes recurring log noise.

### D4. Admin link is staff-gated in the template
Add the Admin link to `base_tablo_wmenu.html` inside `{% if request.user.is_staff %}`, using `{% url 'admin:index' %}`, styled with the existing sidebar nav classes. Rationale: authorization is already `is_staff` for secretary actions; the link must not appear for category judges.

## Risks

- `500.html` accidentally depending on context/tags that aren't available during an error → the error page itself errors. Mitigation: keep it static, test by forcing a 500 with `DEBUG=0`.
- Over-broadening 404: a genuine server bug masked as 404. Mitigation: only the object-not-found / bad-param paths become 404; unexpected exceptions still surface as 500 (now branded).
