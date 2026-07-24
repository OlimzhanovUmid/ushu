@ECHO OFF
REM Deploy / update script for the ushu scoreboard on the Windows event laptop.
REM Safe to run repeatedly: creates the venv on first run, then only updates.
REM Steps: venv -> pip install -> migrate -> collectstatic -> translations.
REM After it finishes, launch the server with start.bat.

cd /d "%~dp0"

REM --- 1. Find Python 3.14 (py launcher preferred, PATH python as fallback) --
set "PY_CMD="
py -3.14 --version >NUL 2>&1 && set "PY_CMD=py -3.14"
if not defined PY_CMD py -3 --version >NUL 2>&1 && set "PY_CMD=py -3"
if not defined PY_CMD python --version >NUL 2>&1 && set "PY_CMD=python"
if not defined PY_CMD (
    echo [ERROR] Python not found. Install Python 3.14 from python.org
    echo         and check "Add python.exe to PATH" in the installer.
    goto :fail
)
echo Using: %PY_CMD%

REM --- 2. Create the virtualenv on first run -------------------------------
if not exist ".venv\Scripts\python.exe" (
    echo Creating virtualenv .venv ...
    %PY_CMD% -m venv .venv || goto :fail
)
call .venv\Scripts\activate.bat || goto :fail

REM --- 3. Install / update dependencies ------------------------------------
python -m pip install --upgrade pip
python -m pip install -r requirements.txt || goto :fail

REM --- 4. Database migrations ----------------------------------------------
python manage.py migrate --noinput || goto :fail

REM --- 5. Static files (served by WhiteNoise) ------------------------------
python manage.py collectstatic --noinput || goto :fail

REM --- 6. Translations ------------------------------------------------------
REM The compiled catalog locale\ru\LC_MESSAGES\django.mo is committed to git,
REM so nothing is required here. If GNU gettext happens to be installed
REM (msgfmt on PATH), recompile to pick up local .po edits.
where msgfmt >NUL 2>&1
if %ERRORLEVEL%==0 (
    echo Recompiling translations ...
    python manage.py compilemessages -l ru || goto :fail
) else (
    if exist "locale\ru\LC_MESSAGES\django.mo" (
        echo Using committed translation catalog ^(gettext not installed^).
    ) else (
        echo [WARNING] locale\ru\LC_MESSAGES\django.mo is missing and gettext
        echo           is not installed - the UI will fall back to English.
    )
)

echo.
echo Deploy finished. Start the server with start.bat
pause
exit /b 0

:fail
echo.
echo [ERROR] Deploy failed - see the message above.
pause
exit /b 1
