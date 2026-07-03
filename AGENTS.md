# AGENTS.md

## Project Overview

- Stack: Django app with local apps `core`, `judges`, `clubs`, `elements`, `participants`, and `tablo`.
- Entry point: `python manage.py ...`
- Settings module: `ushu.settings`
- Primary URL wiring: `ushu/urls.py` includes `tablo.urls` at the root.
- Default database: SQLite at `db.sqlite3`
- Static and media:
  - collected/static runtime path: `static/`
  - media uploads: `media/`

## Runbook

- Use Python 3.14 for local work on the current dependency set.
- Create or recreate a local virtual environment before running Django commands.
- Install dependencies from `requirements.txt`.
- Common commands:
  - `python manage.py runserver`
  - `python manage.py makemigrations`
  - `python manage.py migrate`
  - `python manage.py test`
- Historical batch files (`start.bat`, `migrate.bat`) assume an old machine-specific `C:\Python36` layout. Do not treat them as the current source of truth.
- Do not rely on any old checked-in virtualenv remnants; rebuild the environment from the declared Python runtime and `requirements.txt`.

## Project Shape

- `ushu/`: project settings, WSGI, root URLs.
- `tablo/`: main user-facing flow and most route wiring.
- `judges/`: custom user model (`AUTH_USER_MODEL = 'judges.User'`).
- `participants/`: participant domain objects and related flows.
- `elements/`, `clubs/`: supporting reference/domain models.
- `core/`: shared templates, static assets, and template tags.
- `locale/`: translation files, currently Russian-focused.

## Editing Guidance

- Keep `DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'` unless the task explicitly includes a schema migration plan. This project preserves historical 32-bit primary keys.
- Prefer targeted changes in the owning app instead of cross-cutting refactors. `tablo` is the highest-blast-radius area.
- Treat committed SQLite databases and JSON dumps as data artifacts, not source files to casually rewrite.
- This repository contains duplicated static asset trees (`static/`, `static__/`, and app-level static folders). Only touch them when the task clearly requires it.
- There are legacy/copied files such as the extra `tablo` model copies. Ignore them unless the user explicitly asks about them.

## Testing Expectations

- Start with focused app-level tests when changing model, view, or form behavior.
- If changing migrations, auth, URL wiring, or shared templates, run a broader Django test pass.
- This codebase appears to have sparse tests in several apps, so manual verification may still be required after changes.

<!-- CODEGRAPH_START -->
## CodeGraph

This project has a CodeGraph MCP server (`codegraph_*` tools) configured. CodeGraph is a tree-sitter-parsed knowledge graph of every symbol, edge, and file. Reads are sub-millisecond and return structural information grep cannot.

### When to prefer codegraph over native search

Use codegraph for **structural** questions - what calls what, what would break, where is X defined, what is X's signature. Use native grep/read only for **literal text** queries (string contents, comments, log messages) or after you already have a specific file open.

| Question | Tool |
|---|---|
| "Where is X defined?" / "Find symbol named X" | `codegraph_search` |
| "What calls function Y?" | `codegraph_callers` |
| "What does Y call?" | `codegraph_callees` |
| "What would break if I changed Z?" | `codegraph_impact` |
| "Show me Y's signature / source / docstring" | `codegraph_node` |
| "Give me focused context for a task/area" | `codegraph_context` |
| "See several related symbols' source at once" | `codegraph_explore` |
| "What files exist under path/" | `codegraph_files` |
| "Is the index healthy?" | `codegraph_status` |

### Rules of thumb

- **Answer directly - don't delegate exploration.** For "how does X work" / architecture / trace questions, answer with 2-3 codegraph calls: `codegraph_context` first, then ONE `codegraph_explore` for the source of the symbols it surfaces. Codegraph IS the pre-built index, so spawning a separate file-reading sub-task/agent - or running a grep + read loop - repeats work codegraph already did and costs more for the same answer.
- **Trust codegraph results.** They come from a full AST parse. Do NOT re-verify them with grep - that's slower, less accurate, and wastes context.
- **Don't grep first** when looking up a symbol by name. `codegraph_search` is faster and returns kind + location + signature in one call.
- **Don't chain `codegraph_search` + `codegraph_node`** when you just want context - `codegraph_context` is one call.
- **Don't loop `codegraph_node` over many symbols** - one `codegraph_explore` call returns several symbols' source grouped in a single capped call, while each separate node/Read call re-reads the whole context and costs far more.
- **Index lag**: the file watcher debounces about 500ms behind writes; don't re-query immediately after editing a file in the same turn.

### Current Status

- CodeGraph is not initialized in this repo at the moment.
- If structural exploration is needed, ask the user: `I notice this project doesn't have CodeGraph initialized. Want me to run codegraph init -i to build the index?`
<!-- CODEGRAPH_END -->
