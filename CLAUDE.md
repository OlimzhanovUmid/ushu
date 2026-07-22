# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Django scoreboard/judging system ("tablo") for wushu competitions: participants are registered, drawn into a random order ("jrebiy"), judged live by A/B/C-category judges, and results are shown on a monitor screen. UI text is Russian-focused (`locale/`, `LANGUAGE_CODE = 'ru-RU'`).

Also see `AGENTS.md` — it carries additional runbook/editing guidance and the CodeGraph MCP usage notes.

## Design Context

See `PRODUCT.md` (strategy) and `DESIGN.md` (visual system) at the repo root for design work. Register: **product**. Platform: **web**. Core principles: fast and mistake-proof on the judge-entry hot path; legible across a hall on the projector/stage screens; one continuous event flow (draw → judging → results); restraint over decoration (authoritative, calm — spend gold for "current", red for the accent moment); light enough for weak LAN clients. Anti-references: consumer SaaS/startup, generic Bootstrap admin, cluttered broadcast scoreboard, enterprise gray. Visual tokens live in `core/static/css/style.css`.

## Commands

Requires Python 3.14 and a local virtualenv built from `requirements.txt` (Django 6). The checked-in `*.bat` files assume an old `C:\Python36` Windows layout — ignore them.

```sh
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python manage.py runserver          # dev server
python manage.py makemigrations
python manage.py migrate
python manage.py test               # all tests
python manage.py test tablo         # one app
python manage.py test tablo.tests.SomeTest.test_case   # one test
```

Tests are sparse across apps; manual verification is often still needed.

Database is SQLite at `db.sqlite3` (a commented-out PostgreSQL config exists in `ushu/settings.py`). `jrebiy.py` is a shell snippet (run via `manage.py shell`) that randomizes `Participation.order` across all tablos and flips `Tablo.started`.

## Architecture

App dependency order (from `INSTALLED_APPS` comments in `ushu/settings.py`):

- `judges`, `clubs`, `elements` — no dependencies. `judges.User` is the custom auth user (`AUTH_USER_MODEL = 'judges.User'`) with a `category` field: judge class A, B, or C.
- `participants` — depends on `elements`, `clubs`. `Participant` = athlete with age/sex/club.
- `tablo` — depends on everything; this is the whole application flow. All URLs are wired here (`ushu/urls.py` includes `tablo.urls` at root), all views live in `tablo/views.py` (~800 lines), and the domain core in `tablo/models.py`.
- `core` — shared templates, static assets, template tags.
- `monitor/` exists at the repo root but is empty and NOT in `INSTALLED_APPS` — ignore it.

Domain model (all in `tablo/models.py`):

- `Tablo` = one competition bracket (age group × sex × `ElementCategory` like Nanquan/Taijiquan). Signals on `ElementCategory` auto-create/delete the full Tablo grid for every age/sex combination.
- `Participation` links a `Participant` to a `Tablo` with draw `order`, `state` machine, and `finalscore`. `ParticipationManager.assign_participation` encodes the business rules: group categories share one participation per club, and `Score` rows are pre-created for each non-staff judge — with C-class judges skipped for young age groups and for group/duilian categories. `is_staff` marks the Main judge (only reopens and saves final results).
- `Score` per judge per participation; C-judge scores hold nested `CombinationStatus`/`ElementStatus` trees (built by `assign_combinations`) tracking which elements were performed correctly.

Runtime flow: judges log in → `JudgeView` (root URL) → per-category submit endpoints (`JudgeASubmit`/`B`/`C`) → activation/deactivation of the current participant is managed via module-level helpers (`gl_activate_participant` etc.) in `tablo/views.py` → spectator screens poll `has_update` and render `MonitorView`/`ShowmeView` (note `render_to_file` writes `showme.html` to disk).

## Constraints and traps

- Keep `DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'` — the historical DB schema uses 32-bit primary keys; do not migrate to BigAutoField.
- Treat committed SQLite files (`db.sqlite3`, `backup.sqlite3`) and JSON dumps (`ushu.json`, `v1_october10.json`, …) as data artifacts — never casually rewrite.
- Duplicated static trees exist (`static/` is STATIC_ROOT/collected, `static__/`, plus app-level static dirs). Edit app-level sources, not collected output, and only when the task requires it.
- Legacy copies litter `tablo/` (`models - копияpy`, `models_py`) — ignore them; `tablo/models.py` is the real one.
- Prefer targeted changes in the owning app; `tablo` is the highest-blast-radius area.
