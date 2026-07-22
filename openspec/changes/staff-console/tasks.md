# Tasks: staff-console

_Depends on: redesign-foundation (tokens/shell) and harden-errors-and-admin-access (sidebar Admin link)._

## 1. Console shell & task home (staff-console)

- [x] 1.1 Add a staff-gated console home view + URL, on the Federation Standard shell, listing the correction tasks in Russian domain wording; retarget the sidebar "Admin" link to it
- [x] 1.2 Enforce `is_staff` (StaffRequiredMixin / staff_required) on every console view; verify a category judge is denied

## 2. Find participant & score state (staff-console)

- [x] 2.1 Participant search (name / club / tablo) → results with participations and per-judge score state, disambiguated by tablo
- [x] 2.2 Participation detail: judges + their score state, with the correction actions

## 3. Correction primitives (staff-console)

- [x] 3.1 Generalize the re-open: allow re-opening a judge's slot / a whole participation for ANY participation (incl. finished), not only the active one; re-entry goes through the normal judging UI
- [x] 3.2 Withdraw participation behind a named, competition-red confirmation (reuse delete_participation logic)
- [x] 3.3 Retire judge: `is_active=False` (never delete), with the "preserves history" rationale shown
- [x] 3.4 Every irreversible action confirms first, names the concrete object, destructive control separated + red

## 4. Branded admin (branded-admin)

- [x] 4.1 Custom `AdminSite` + `admin/base_site.html` + admin CSS on foundation tokens (navy header, cool surfaces, token buttons)
- [x] 4.2 Russian `verbose_name`/`verbose_name_plural` across the registered models
- [x] 4.3 `list_display` / `search_fields` / `list_filter` on Score (judge+participant) and Participation (participant+tablo+state) so large tables are navigable
- [x] 4.4 Link the styled admin from the console ("setup / open admin"); keep a path back to the app

## 5. Verify

- [x] 5.1 Manual: correct a finished participant's score via re-open → re-entry re-aggregates correctly
- [x] 5.2 Manual: withdraw + retire flows confirm in domain terms; non-staff blocked from every console URL
- [x] 5.3 Playwright pass: console task home, find-participant, a re-open, the styled admin — screenshots + on-brand check
