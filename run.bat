@echo off
REM Cross-platform launcher for Money4Band (Windows).
REM Thin wrapper: all logic lives in run.py so behaviour is identical
REM everywhere. Prefers the py launcher, falls back to python.
cd /d "%~dp0"
where py >nul 2>&1 && (py -3 run.py %* & goto :eof)
python run.py %*
