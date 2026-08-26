@echo off
REM Starts the standalone MySQL 8.4.11 instance used by this project (see DATABASE.md).
REM Runs detached in the background on port 3307; safe to run again if already up
REM (skips launching a second instance if port 3307 is already listening).
netstat -ano | findstr ":3307" | findstr "LISTENING" >nul
if %errorlevel%==0 (
  echo MySQL 8.4.11 already running on port 3307, skipping.
  exit /b 0
)
start "HMS MySQL 8.4.11" /min "D:\MySQL84\mysql-8.4.11-winx64\bin\mysqld.exe" ^
  --datadir="D:\MySQL84\data" ^
  --basedir="D:\MySQL84\mysql-8.4.11-winx64" ^
  --port=3307 ^
  --log-error="D:\MySQL84\mysql_err.log"
echo Starting MySQL 8.4.11 on port 3307 (log: D:\MySQL84\mysql_err.log)...
