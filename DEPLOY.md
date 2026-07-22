# Deploying ushu at a competition

One laptop runs the server; ~10 client machines (judge stations + the monitor
projector) connect over one LAN by the laptop's IP. No internet is required.

## One-time setup on the laptop

```
py -3.14 -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

Edit the config block at the top of `start.bat`:

| Variable | Meaning |
|---|---|
| `USHU_SECRET_KEY` | random 50+ char string; set once per install, keep secret |
| `USHU_DEBUG` | `0` in production (never `1` at a live event) |
| `USHU_ALLOWED_HOSTS` | `*` for an isolated LAN, or the laptop's IP |
| `USHU_EVENT_TITLE` / `USHU_EVENT_SUBTITLE` | the two lines shown on the idle monitor screen |

## Running

Double-click `start.bat` (production: waitress, `DEBUG=0`, port 8081).
Clients open `http://<laptop-LAN-IP>:8081/`. Use `debug.bat` only for development.

Judge stations must use a **Latin keyboard layout** — the judge C keys (V / C / X)
are read by character, and a Cyrillic layout will not register them.

## Backups (important — the DB uses WAL mode)

SQLite runs in WAL journal mode, so the live data spans three files:
`db.sqlite3`, `db.sqlite3-wal`, `db.sqlite3-shm`. To take a consistent backup,
either copy **all three** together, or checkpoint first so everything is folded
into the main file:

```
.venv\Scripts\python manage.py shell -c "from django.db import connection; connection.cursor().execute('PRAGMA wal_checkpoint(TRUNCATE)')"
copy db.sqlite3 backups\db-<date>.sqlite3
```

Take a backup before and after each event. The database is no longer tracked in
git — it is competition data, not source.

## Draw of lots (jrebiy)

Run `python manage.py jrebiy` to randomize start order across all boards
(per-board numbering, one transaction). It refuses boards already started
unless you pass `--force`.
