# Kotak School Data API

Private FastAPI service for the school dashboard. It reads PostgreSQL, masks student identifiers, restricts refresh operations to administrators, and records refresh attempts in `pipeline_audit_log`.

## Local development

```bash
python -m venv .venv
.venv/bin/pip install -r web_api/requirements.txt
AUTH_DISABLED=true .venv/bin/uvicorn web_api.main:app --reload
```

`AUTH_DISABLED=true` is rejected when `ENVIRONMENT=production`.
The service also serves the compiled dashboard at `/`, so local use needs only
`http://127.0.0.1:8000`. The private hosted dashboard can connect to the same
API by entering its HTTPS address and an API key in the connection dialog.

## Container deployment

Copy `web_api/.env.example` values into the repository `.env`, use strong and
different administrator/viewer keys, set `ENVIRONMENT=production`, and run:

```bash
docker compose --env-file /dev/null up -d --build api
```

Terminate TLS at the hosting platform or reverse proxy. Add its exact HTTPS
dashboard origin to `WEB_ALLOWED_ORIGINS`; never expose PostgreSQL publicly.
The explicit empty Compose interpolation file is intentional: application
secrets are loaded literally through the service's raw `env_file`, so `$`
characters in credentials are not treated as Compose variables.
If you also start the optional local `postgres` service, set
`POSTGRES_CONTAINER_PASSWORD` in your shell instead of using its development
fallback.

## Vercel deployment

The repository root contains Vercel's `app.py`, production `requirements.txt`,
and CDN-ready assets in `public/`. `.vercelignore` excludes notebooks, source
exports, backups, local secrets, and other student data from every upload.

Required production variables are `DATABASE_URL`, `ENVIRONMENT=production`,
`ADMIN_API_KEY`, `VIEWER_API_KEY`, and `WEB_ALLOWED_ORIGINS`. Add secrets with
Vercel's sensitive environment-variable option and deploy with `vercel --prod`.

## Authentication

Send `X-API-Key` with every `/api/*` request. The viewer key can access reports. The administrator key can additionally access audit records and request refreshes.

## Attendance import

Validate the bundled attendance exports without changing PostgreSQL:

```bash
.venv/bin/python -m web_api.import_attendance
```

Create a verified `pg_dump` backup, create `attendance_report`, and upsert all
available attendance rows:

```bash
.venv/bin/python -m web_api.import_attendance --apply
```

Status IDs follow the source system: `1 = Absent`, `2 = Present`, `3 = Not
joined/TC`, and `4 = Holiday`. Percentages use only Present and Absent records.

## Refresh safety

Refresh execution is denied by default. To enable it, set `ENABLE_PIPELINE_EXECUTION=true` and configure the reviewed command for each pipeline. Before executing a command the API:

1. obtains a process-wide refresh lock;
2. creates and verifies a PostgreSQL backup;
3. records an audit entry;
4. executes without a shell;
5. records success or failure and releases the lock.

For multiple API replicas, replace the process lock with a PostgreSQL advisory lock or a distributed job queue.

