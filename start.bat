@ECHO OFF

set PYTHONPATH=C:\Python36
set PATH=%PYTHONPATH%;%PATH%;%PYTHONPATH%\Scripts

cd %PYTHONPATH%\Scripts\ushu
waitress-serve --port=8081 ushu.wsgi:application
