@echo off
REM Runs the daily "appointment tomorrow" reminder email job (see
REM patient/management/commands/send_appointment_reminders.py). Registered
REM as a Windows Scheduled Task ("HMS Appointment Reminders") to run once a
REM day; requires the project's MySQL (start_mysql.bat) to be up.
cd /d "D:\HMS\Hospital-Management-System"
"D:\HMS\Hospital-Management-System\venv\Scripts\python.exe" manage.py send_appointment_reminders >> "D:\HMS\Hospital-Management-System\reminder_log.txt" 2>&1
