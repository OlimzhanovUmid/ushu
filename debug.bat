@ECHO OFF

set PYTHONPATH=C:\Python36
set PATH=%PYTHONPATH%;%PATH%;%PYTHONPATH%\Scripts

cd %PYTHONPATH%\Scripts\ushu
python manage.py runserver 0.0.0.0:80