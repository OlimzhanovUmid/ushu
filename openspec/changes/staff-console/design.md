# Design: staff-console

## Context

Django 6 admin currently registers most models with bare `register()` (default CRUD). Staff reach it via the sidebar "Admin" link (from harden-errors-and-admin-access). Relevant domain facts grounding the design:

- `Score(judge, participation, aclass M2M, bclass float, berrors M2M, cclass sorted-M2M, saved bool)` — a score is a rich structure (A error codes, B value, C element trees), not a single number. Editing those fields raw is error-prone.
- `open_judge(idx)` re-opens one judge's score slot, but only for `get_current_participation()` (the active DOING participation). Correcting a **finished** participation is not reachable through the live flow.
- `delete_participation(pk)` hard-deletes a participation and its scores in a transaction (staff-gated, POST).
- Judges are `PROTECT`-ed from deletion once they have scores; retirement means `is_active=False`.
- Foundation tokens + the navy shell exist; PRODUCT.md anti-references include "generic Bootstrap admin" and "enterprise gray".

## Goals / Non-Goals

**Goals:**
- The 3–5 hot correction tasks are task-first, fast to find the right object, and mistake-proof.
- Correcting a finished participation is possible without raw admin.
- The long-tail setup/reference CRUD is on-brand and navigable, not generic gray.
- Everything stays inside the Federation Standard shell.

**Non-Goals:**
- No raw field-level score editing in the console (stays in styled admin).
- No scoring-logic change.
- No new setup features (bulk import, championship entity).
- No Elixir work.

## Decisions

### D1. Re-open, don't hand-edit scores
The console's correction primitive is **re-opening a judge's slot (or a whole participation) so the judge re-enters through the existing judging UI**, not editing `aclass`/`bclass`/`cclass` by hand. Rationale: re-entry goes through the validated scoring path (completeness gate, aggregation), so a correction can't produce an impossible score; raw field edits can. Generalize `open_judge` to accept any participation, not just the active one. The rare surgical field edit stays in the styled admin.

### D2. Task-first console, model-first admin
Two surfaces, deliberately. The **console** is organized by verbs ("Найти участника", "Переоткрыть судью", "Снять участие", "Вывести судью из ротации") for the hot, dangerous jobs. The **styled admin** stays model-organized for the long tail (clubs, countries, elements, combinations, error codes, user setup). Rationale: verbs suit urgent correction; model-CRUD suits unhurried setup. Forcing either into the other's shape is the current pain.

### D3. Custom AdminSite over template/CSS override
Style the admin with a custom `AdminSite` subclass plus `admin/base_site.html` and an admin stylesheet built on the foundation tokens (navy header, cool surfaces, token buttons), rather than fighting per-model. Add Russian `verbose_name`/`verbose_name_plural` and useful `list_display`/`search_fields`/`list_filter` on the heavy models (Score by judge+participant, Participation by participant+tablo+state). Rationale: one styling seam, and the list config is what makes a 1635-row table usable.

### D4. Irreversible actions confirm, in red, worded in domain terms
Withdraw-participation and retire-judge (and re-open, which discards a saved result) present an explicit confirmation naming the concrete object ("Снять Latysheva из Nandao 18+?"), styled competition-red, separated from routine actions. Rationale: PRODUCT.md mistake-proof principle; these are irreversible during a live event.

## Surface sketch

```
  Sidebar "Admin" (is_staff)
        │
        ▼
  ┌─────────────────────────────────────────────┐
  │  STAFF CONSOLE  (task-first, navy shell)      │
  │  • Найти участника  →  участия + судьи + баллы │
  │        └─ переоткрыть судью / всё участие      │
  │        └─ снять участие            (red+confirm)│
  │  • Вывести судью из ротации        (confirm)   │
  │  • ⋯                                           │
  │  ────────────────────────────────────────────  │
  │  Настройка → [Открыть админ]  (styled Django)  │
  └───────────────────────────────┬───────────────┘
                                  ▼
                    ┌──────────────────────────────┐
                    │ BRANDED DJANGO ADMIN (styled) │
                    │ клубы/страны/элементы/коды/    │
                    │ судьи-setup/участники          │
                    └──────────────────────────────┘
```

## Risks

- Generalizing re-open to finished participations could reopen the wrong one under time pressure. Mitigation: the confirm names the concrete participant+tablo+judge; search returns disambiguated rows.
- Custom AdminSite can drift from Django admin upgrades. Mitigation: subclass + template extend, minimal overrides, no forked admin internals.
- Scope creep into a full bespoke admin. Mitigation: hard line — only the hot verbs are bespoke; everything else stays in the styled admin.
