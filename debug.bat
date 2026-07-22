@ECHO OFF
REM Development launcher (DEBUG on, auto-reload). Not for the live event.
cd /d "%~dp0"

set USHU_DEBUG=1

call .venv\Scripts\activate.bat
python manage.py runserver 0.0.0.0:8081
