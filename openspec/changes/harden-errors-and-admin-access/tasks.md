# Tasks: harden-errors-and-admin-access

## 1. 404 on missing objects (error-resilience)

- [x] 1.1 `TabloDetailView.get_tablo`: return 404 (get_object_or_404 / Http404) when no Tablo matches `category`+`age`+`sex`, including blank/missing `age`/`sex` params
- [x] 1.2 `TabloMonitorView.get_tablo` and `TabloPrintView.get_tablo`: 404 on a non-existent `pk`
- [x] 1.3 `ParticipantScoreView` and `PntElementView`: 404 on a non-existent participant `pk` (lines ~188, ~223)
- [x] 1.4 Activation lookup (`Tablo.objects.get(pk=tablo_id)`, ~line 694): 404 on missing tablo
- [x] 1.5 Manual check: each bad URL returns 404, valid URLs unchanged

## 2. Branded error pages (error-resilience)

- [x] 2.1 Add `core/templates/404.html` — navy shell, Russian message, link back to standings/login; uses foundation tokens
- [x] 2.2 Add `core/templates/500.html` — self-contained (no context-processor / heavy-include dependency), navy, Russian, link back
- [x] 2.3 Confirm `handler404`/`handler500` resolve the templates (Django auto-picks root `404.html`/`500.html`); wire explicitly in `ushu/urls.py` if needed
- [x] 2.4 Verify with `DEBUG=0`: force a 404 and a 500, confirm branded pages render and the 500 page does not itself error

## 3. Favicon (error-resilience)

- [x] 3.1 Ensure a `<link rel="icon">` in `base.html` / monitor / login points at a real logo asset
- [x] 3.2 Add a `/favicon.ico` route (redirect to the static logo) in `ushu/urls.py`
- [x] 3.3 Confirm no `favicon.ico` 404 in the server log during a page load

## 4. Admin link (admin-access)

- [x] 4.1 Add a staff-only "Admin" link to `base_tablo_wmenu.html` sidebar: `{% if request.user.is_staff %}` → `{% url 'admin:index' %}`, sidebar nav token styling
- [x] 4.2 Verify: staff sees it and reaches `/admin/`; a category judge does not see it
