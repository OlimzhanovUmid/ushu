@ECHO OFF
REM Production launcher for the ushu scoreboard.
REM One laptop serves ~10 LAN clients. Edit the config block per event,
REM then double-click this file. Requires a local venv at .venv
REM (create once: py -3.14 -m venv .venv && .venv\Scripts\pip install -r requirements.txt)

cd /d "%~dp0"

REM --- configuration (edit per event) --------------------------------------
set USHU_DEBUG=0
set USHU_SECRET_KEY=CHANGE-ME-set-a-random-50+char-secret-once-per-install
set USHU_ALLOWED_HOSTS=*
set USHU_EVENT_TITLE=O'ZBEKISTON USHU FEDERATSIYASI
set USHU_EVENT_SUBTITLE=O'RTA OSIYO CHEMPIONATI
REM -------------------------------------------------------------------------

call .venv\Scripts\activate.bat
python manage.py migrate --noinput
python manage.py collectstatic --noinput
REM threads must cover judge requests + long-lived monitor SSE streams.
waitress-serve --host=0.0.0.0 --port=8081 --threads=16 ushu.wsgi:application
