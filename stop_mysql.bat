@echo off
REM Gracefully stops the standalone MySQL 8.4.11 instance started by start_mysql.bat.
"D:\MySQL84\mysql-8.4.11-winx64\bin\mysqladmin.exe" -u root -h 127.0.0.1 -P 3307 shutdown
echo MySQL 8.4.11 stopped.
