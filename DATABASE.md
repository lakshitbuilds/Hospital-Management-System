# Database: MySQL

This project now runs on MySQL instead of SQLite. Connection settings live in `.env`
as a single `DATABASE_URL` (read via `config/settings.py`); omit it and the project
falls back to `db.sqlite3`.

```
DATABASE_URL=mysql://root:@127.0.0.1:3307/hms_db
```

## Why port 3307, and why a standalone install

Django on this project requires **MySQL 8.4+ or MariaDB 10.11+**. Two MySQL-family
servers were already on this machine and neither qualified:

- XAMPP's bundled MariaDB (port 3306) — 10.4.32, too old.
- The installed `MySQL80` Windows service — MySQL 8.0.46, also too old, and stopped
  (its `my.ini` also targets port 3306, conflicting with XAMPP's MariaDB).

Rather than touch either of those (XAMPP's MariaDB serves other local projects;
reconfiguring the `MySQL80` service needs admin rights), a separate **MySQL 8.4.11
Community Server** was downloaded as the official "no-install" ZIP distribution and
extracted to `D:\MySQL84`, with its own data directory at `D:\MySQL84\data`. It runs
as a plain process (not a Windows service) on port **3307**, so it doesn't collide
with anything else on this machine.

## Starting / stopping it

```bash
start_mysql.bat   # starts MySQL 8.4.11 in the background on port 3307
stop_mysql.bat    # gracefully shuts it down
```

Run `start_mysql.bat` before `manage.py runserver` each dev session (it doesn't
auto-start on login since it isn't installed as a service). Root has no password —
local dev only, don't reuse this setup as-is anywhere internet-facing.

## Migration from SQLite

All data from the pre-MySQL `db.sqlite3` was dumped and reloaded:

```bash
python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.permission -e admin.logentry -e sessions.session --indent 2 -o data_dump_sqlite.json
python manage.py migrate
python manage.py loaddata data_dump_sqlite.json
```

`data_dump_sqlite.json` and the original `db.sqlite3` are kept on disk (gitignored)
as a rollback point in case anything needs to be re-migrated.
