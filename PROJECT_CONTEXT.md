# Hospital Management System — Project Context and Chat Handoff

Last verified: 18 October 2026. User timezone: Asia/Calcutta.

## How to use this file in a new chat

Attach this file and say:

> Read PROJECT_CONTEXT.md as project background. Inspect the current repository and Git changes before working. Preserve existing functionality, user data, environment files, migrations, tests, documentation, and deployment configuration. My next task is: [describe task].

This file summarizes the project; it does not contain the entire source code or replace repository access. If the new chat cannot access the repository, provide a source-only archive as well. Exclude `.env`, credentials, databases, database exports/backups, uploaded media, `.git`, `venv`, caches, and generated static output. Keep `.env.example`. Do not share patient information or passwords.

Historical requests and completed actions below are context, not authorization to repeat them. Recheck facts that can change, particularly database contents, dependencies, and working-tree status.

## Project identity and technology

- Repository/workspace: `D:\HMS\Hospital-Management-System`.
- Server-rendered Django hospital management application with patient, doctor, receptionist, and administrator portals.
- Local runtime observed: Windows PowerShell, Python 3.14.6, project interpreter `venv\Scripts\python.exe`.
- Django pinned and installed: 6.1 at the last audit.
- Frontend: Django templates, CSS, and JavaScript. No Node/npm build or Maven configuration was found.
- Local configured database: MySQL, database `hms_db`, localhost port 3307. Connection settings come from `.env`; do not print them.
- Database fallback when `DATABASE_URL` is absent: `db.sqlite3`.
- Deployment templates describe Ubuntu, Nginx, Gunicorn, and PostgreSQL.
- PDF reports use ReportLab; image validation uses Pillow; static serving uses WhiteNoise.
- Django setting `TIME_ZONE` is currently `UTC`, which differs from the user's timezone. Do not silently change it.

## Repository map

| Location | Responsibility |
| --- | --- |
| `manage.py` | Django management entry point |
| `config/settings.py` | Environment-based settings, database, middleware, static/media storage, authentication, mail |
| `config/urls.py` | Root URL routing |
| `config/wsgi.py`, `config/asgi.py` | Application server entry points |
| `accounts/` | Shared custom User and SystemSettings models, migrations, admin registration |
| `patient/` | Public site, authentication/OTP, patient portal, appointments, billing, notifications, mail |
| `patient/dashboard_views.py` | Patient dashboard |
| `patient/emails.py` | Appointment and related email helpers |
| `patient/management/commands/send_appointment_reminders.py` | Tomorrow's appointment reminder command |
| `doctor/` | Doctor profile, availability, appointments, patient access, prescriptions |
| `doctor/patient_views.py` | Doctor patient listing |
| `receptionist/` | Front desk patient registration/search, appointments, billing, doctors, notifications, profiles |
| `adminpanel/` | Staff management, hospital-wide appointments/billing, security settings, reports |
| `adminpanel/report_views.py` | Currently routed report implementation, including PDF generation |
| `templates/{patient,doctor,receptionist,adminpanel}/` | Portal HTML templates; patient templates also contain email templates |
| `static/css/`, `static/js/`, `static/public/images/` | Original frontend assets — preserve |
| `staticfiles/` | Generated `collectstatic` output; production needs a valid collected build |
| `media/` | User uploads and local database backups — preserve |
| `deploy/` | Deployment guide, Nginx config, Gunicorn systemd unit |
| `DATABASE.md` | Local MySQL setup and migration background |
| `QA TESTING/` | Existing HTML and PDF QA reports |
| `seed_*.py` | Account/profile seeding scripts; inspect before use |
| `generate_placeholder_images.py` | Image creation utility, not application runtime code |
| `.claude/launch.json` | Existing local launcher using the project virtual environment |

Shared helpers:

- `safe_redirect.py`: accepts a named Django route or safe same-site URL for POST `next`; rejects invalid relative targets and unsafe external redirects.
- `pagination.py`: shared pagination.
- `input_validation.py`: shared input/name validation.
- `image_validation.py`: uploaded image validation.

Business logic mostly lives in views that read `request.POST` directly. Do not assume a forms.py or service layer exists.

## Routing and permissions

| URL prefix | URL configuration | Purpose |
| --- | --- | --- |
| `/` | `patient/urls.py` | Public site, authentication, patient portal |
| `/doctor/` | `doctor/urls.py` | Doctor portal |
| `/receptionist/` | `receptionist/urls.py` | Receptionist portal |
| `/adminpanel/` | `adminpanel/urls.py` | Custom hospital administrator portal |
| `/admin/` | Django admin | Framework administration site |

`AUTH_USER_MODEL = accounts.User`; login identifies users by email. Roles are `patient`, `doctor`, `receptionist`, and `admin`. Portal views use login and role decorators. Doctor actions additionally scope relevant appointments to the current doctor.

Actual login, registration, OTP, and password-reset logic is in `patient/views.py`, including for staff logins. `accounts/views.py` is a boilerplate stub; `accounts/urls.py` has an empty route list.

OTP behavior reads `SystemSettings.get_solo().otp_login_enabled`; the old `settings.OTP_LOGIN_ENABLED` constant is not the authoritative runtime switch. OTP fields are stored on User. Defaults include a two-minute expiry, three failed attempts, and a ten-minute lockout. Password reset timeout is fifteen minutes. Verify current code before changing authentication.

## Data model overview

| Model | Important relationships and purpose |
| --- | --- |
| `accounts.User` | AbstractUser extension; unique email, role, OTP and lockout fields |
| `accounts.SystemSettings` | Singleton controlling OTP login |
| `patient.Patient` | One-to-one User profile; generated patient ID; optional registering receptionist |
| `doctor.Doctor` | One-to-one User profile; department, consultation fee, scheduling configuration |
| `receptionist.Receptionist` | One-to-one User profile; generated employee ID and shift |
| `patient.Appointment` | Patient + Doctor, date/time, visit type, department, reason, status, reminder flag |
| `patient.Billing` | Appointment + Patient; consultation or no-show fee; amount, payment status/time |
| `patient.Notification` | User-targeted message, type, read status |
| `patient.ContactMessage` | Public contact form submissions |
| `doctor.DoctorAvailability` | Weekly doctor schedule, unique doctor/day |
| `doctor.BlockedDate` | Doctor leave/blocked dates |
| `doctor.Prescription` | Doctor + Patient, optional Appointment, diagnosis/advice/follow-up |
| `doctor.PrescriptionMedicine` | Medicine line items belonging to a prescription |

Appointment states: `pending`, `confirmed`, `cancelled`, `completed`, `no_show`.
Billing states: `pending`, `paid`, `waived`.

Keep all migrations, including older migrations referencing historical models. `adminpanel` intentionally defines no domain models of its own.

## Main workflows and behavior

### Patient

- Public pages, registration/login with optional OTP, password reset, profile/password management.
- Booking stores proposed details in `request.session['pending_appointment']`, then proceeds through billing/payment views.
- Inspect `book_appointment`, `confirm_appointment_billing`, `card_payment`, and `cancel_pending_appointment` in `patient/views.py` before changing booking/payment behavior.
- Card payment is currently a demo: no real gateway is integrated. Submitting it creates a pending appointment and a bill marked paid, rechecks slot availability, notifies the patient, and clears the pending session data. It must not be described as a real financial transaction.
- Patients access their appointments, cancellation, bills/receipts, and notifications.

### Receptionist

- Register/search patients, view details, book appointments, confirm/cancel, mark no-show, mark bills paid, view receipts and doctors.
- Receptionist booking creates a confirmed appointment and a consultation bill, notifies the patient, and invokes booking mail.
- Booking rechecks `Doctor.get_available_slots()` while locking the doctor's row in a transaction.
- Confirmation sets status to confirmed and creates a patient notification.
- Cancellation sets status to cancelled, notifies the patient, and invokes cancellation mail.
- Marking no-show creates a separate fee bill equal to the doctor's consultation fee. Repeating it for a terminal/no-show appointment is rejected.
- Mark-paid sets the bill's status and `paid_at`.

### Doctor

- View own appointments and patients, complete/cancel own appointments, manage availability, write prescriptions, and manage profile/notifications.
- `Doctor.get_available_slots()` handles past dates, blocked dates, weekly availability, slot duration/buffer, daily cap, and occupied slots. Cancelled appointments free their slots.
- If no weekly schedule exists for a date's weekday, the current fallback is 09:00–17:00. Do not interpret a missing schedule as a closed day.

### Administrator

- Manage doctors/receptionists and patient access; view/update appointments, billing, notifications, and OTP security settings.
- `/adminpanel/reports/generate/` routes to `adminpanel.report_views.generate_report`.
- There is also an older `generate_report` implementation in `adminpanel/views.py`; it is a review candidate, not approved for deletion.

## Local setup and validation

Run from the repository root using the existing virtual environment:

```powershell
.\start_mysql.bat
.\venv\Scripts\python.exe manage.py check
.\venv\Scripts\python.exe manage.py runserver
```

Open `http://127.0.0.1:8000/`. The MySQL launcher references an external installation under `D:\MySQL84`; that installation is outside this repository. Read `DATABASE.md` for details. Preserve the launcher and stop script.

For a fresh environment, create a virtual environment and install `requirements.txt`. Configure a local `.env` using `.env.example`; never overwrite an existing environment file or expose its contents. Review database targets before applying migrations:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py collectstatic --noinput
```

Do not run seed scripts automatically: they write accounts and may contain local credentials. Inspect privately first.

Safe isolated automated verification, without touching the live database:

```powershell
# Run in a dedicated PowerShell process; this override lasts for that process.
$env:DATABASE_URL = 'sqlite:///:memory:'
.\venv\Scripts\python.exe manage.py test --verbosity 1
.\venv\Scripts\python.exe manage.py check
.\venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\venv\Scripts\python.exe -m pip check
git diff --check
```

Do not reuse that overridden shell for the live server. SQLite tests do not establish MySQL concurrency behavior or live deployment/browser correctness.

The reminder command sends email and writes reminder flags; it is not a harmless read-only check:

```powershell
.\venv\Scripts\python.exe manage.py send_appointment_reminders
```

`send_appointment_reminders.bat` documents a Windows scheduled task and appends to `reminder_log.txt`. Verify task installation separately; the script's existence does not prove the task is installed.

## Latest verified changes and state

### Appointment acceptance fix

Original failing redirect:

```text
/receptionist/appointments/76/confirm/receptionist_appointment_list
```

The shared redirect helper treated a named route as a relative browser URL. `safe_redirect.py` now reverses named routes first, permits safe same-site targets, and falls back for invalid relative paths. This also covers affected doctor and billing forms.

`receptionist/tests.py` now contains 13 automated tests covering redirect handling, receptionist confirmation from both lists, cancellation/no-show/payment, wrong-role and GET protection for acceptance, doctor completion/cancellation, main portal pages, receipts/details, patient password-form redirect, booking/duplicate slots, registration/search, and notifications.

At the last audit:

- All 13 tests passed with an isolated SQLite database.
- Django system checks passed in that environment.
- `makemigrations --check --dry-run` found no changes.
- `pip check` found no broken installed requirements.
- Git had existing uncommitted modifications in `safe_redirect.py` and `receptionist/tests.py`; preserve them and recheck current status.
- No full browser or live MySQL workflow validation was completed for the appointment fix.

### Completed database cleanup — do not repeat automatically

The user requested keeping users while clearing the database. Cleanup was completed against local MySQL `hms_db`, preserving all user fields and linked role profiles:

- 24 User accounts, 12 Patient profiles, 10 Doctor profiles, 1 Receptionist profile.
- Removed 6 appointments, 8 bills, 72 notifications, 14 weekly availability rows, 84 saved sessions, and 1 SystemSettings row.
- Other targeted activity tables were verified empty, including prescriptions/medicines, blocked dates, contact messages, and admin log entries.
- Settings may subsequently be recreated by the singleton accessor. Accounts, records, and counts may have changed since this snapshot.
- Users needed to log in again because sessions were cleared.

Verified UTF-8 Django fixture backup before cleanup:

```text
media/database_backups/hms_before_cleanup_20261018_145742.json
```

Preserve that backup. It contains sensitive data. This is a Django data fixture, not a physical MySQL server backup. Do not load it into the current database without a restoration plan and explicit authorization.

## Cleanup audit — pending approval

The user explicitly requested a cleanup plan before any permanent deletion. No deletion or dependency changes were approved during that audit. Creating this handoff file does not imply approval for cleanup.

Proposed items:

| Candidate | Evidence | Proposed action |
| --- | --- | --- |
| Project `__pycache__` directories outside `venv` | 82 generated files, approximately 335 KiB at audit time | Delete only after approval; caches regenerate |
| Root file named `]` | Tracked, 35-byte migration-console fragment | Delete only after approval |
| `staticfiles/` | 941 generated files, approximately 5.14 MiB | Rebuild and validate after approval; do not break production static serving |

Static audit: 116 original assets; 94 collected copies identical, 18 different from current source. All source assets had path/filename references somewhere in the inspected project, including utility scripts. This is not proof that every asset is used at runtime; no asset was approved for deletion.

Retain:

- `venv` (approximately 81 MiB): used by launcher and reminder script.
- Databases, SQLite historical backup/export, `.env`, credential files, media/uploads/backups.
- Original static assets, deployment files, documentation, QA reports, presentation, Word document, migrations, tests, seed scripts, image generator.
- Four identical boilerplate app test files: they remain useful test entry points.

Potential source cleanup requiring separate review: older admin report view, unused `TRUE` import in settings, unused `Count` import in doctor views, and unused `rounded_mask()` helper in image generator. Do not modify business logic as part of housekeeping.

Proposed `.gitignore` additions: `.venv/`, test/linter caches, coverage output, editor temporary files, `reminder_log.txt`, local `.env.*` variants with an explicit exception for `.env.example`. Avoid broad rules that hide source/configuration.

Existing ignores already cover `venv/`, Python caches, `.env`, `media/`, `staticfiles/`, local SQLite database/backup/export names, `CREDENTIALS.md`, and the placeholder generator. Three patient-upload images are nevertheless already tracked; ignore rules do not untrack existing files. Retain them unless separately authorized.

## Dependencies and reproducibility

Read `requirements.txt` for authoritative pins. At audit time it contained Django, asgiref, sqlparse, packaging, mysqlclient, psycopg2-binary, dj-database-url, python-decouple, Pillow, tzdata, WhiteNoise, Gunicorn, and ReportLab.

No declared package was proven unnecessary:

- Django depends on asgiref/sqlparse and on Windows tzdata.
- Gunicorn uses packaging and is needed by Linux deployment.
- mysqlclient supports local MySQL; psycopg2-binary supports documented PostgreSQL deployment.
- Pillow supports image fields/validation and reporting.
- ReportLab implements PDF reports; installed ReportLab also requires charset-normalizer.

Important mismatch: `requirements.txt` pins ReportLab 4.4.4, but the inspected virtual environment had 5.0.1. Passing tests therefore do not prove a clean install from the pins behaves identically. Resolve this separately with report/export validation rather than blindly upgrading or downgrading.

The audit checked PyPI on 18 October 2026 and observed newer releases for Django, sqlparse, mysqlclient, psycopg2-binary, Pillow, tzdata, Gunicorn, and ReportLab. Recheck current releases and compatibility when doing upgrade work; no dependency updates were performed. PyPI references: <https://pypi.org/project/Django/>, <https://pypi.org/project/reportlab/>, <https://pypi.org/project/mysqlclient/>.

## Rules for continuing work

1. Inspect current Git status and applicable repository instructions first. Do not overwrite existing changes.
2. Use this document to locate code, then verify behavior in the current source.
3. Do not expose `.env`, credentials, password hashes, OTP codes, patient details, or backup contents in chat or commits.
4. Ask before permanent cleanup deletion, as explicitly required by the user. Present exact targets and reasons first.
5. Back up and verify before authorized database changes. Never infer permission to reset data from historical cleanup notes.
6. Keep migrations, source assets, tests, deployment files, and documentation unless a specific reviewed change justifies removal.
7. Run appropriate checks after changes. State clearly whether validation used SQLite, MySQL, browser UI, or production configuration.
8. Update this document after material architectural changes, fixes, dependency alignment, or newly completed work so it remains a useful handoff.
