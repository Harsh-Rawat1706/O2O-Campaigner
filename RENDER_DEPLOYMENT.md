# Deploy O2O Campaigner to Render

This walkthrough deploys the FastAPI backend and moves the existing local
PostgreSQL test database to Render.

## Important: keep the database separate from the Docker image

Do not bake PostgreSQL or its data directory into the API Docker image. Render
replaces API containers during deployments and restarts; container files are
not a database backup or durable storage location. Use a separate Render
PostgreSQL database for persistent application data. The Docker image contains
the API code and migrations only; the database remains separate and can be
reused across API deployments.

The commands below copy your local test database directly from your machine to
the Render database. The dump file stays local; do not commit it or send it to
anyone. Restore only into a new, empty Render database.

## 1. Push the project to a Git repository

Render needs access to the repository containing this project. Push the
Dockerfile and application code to a branch in your Git provider. Do not commit
`.env`, database dumps, passwords, API tokens, or other credentials.

The repository includes:

- `Dockerfile` to build and start the API.
- `.dockerignore` to keep `.env`, virtual environments, and local data out of
  the Docker build context.
- A startup command that applies `alembic upgrade head` before starting
  Uvicorn.

The API listens on Render's `PORT` environment variable. Do not hard-code a
public port in the Render service.

## 2. Back up the local test database

The existing Compose setup publishes PostgreSQL on local port `5433` and
currently expects the database/user names `o2o_campaigner` and `o2o_user`.
From PowerShell at the repository root, create a PostgreSQL custom-format dump:

```powershell
cmd.exe /c "docker compose exec -T postgres pg_dump -U o2o_user -d o2o_campaigner --format=custom > o2o-test-data.dump"
```

`cmd.exe` is used so the binary dump is written without PowerShell text
encoding. If you changed the database/user names in your local Compose
configuration, use those actual names instead.

Check that the dump exists and is not empty:

```powershell
Get-Item .\o2o-test-data.dump | Select-Object Name, Length
```

The `*.dump` ignore rule keeps this file out of Git. Keep it in a safe local
place until the Render database has been verified. Do not delete your local
database; this process copies it.

Confirm that PostgreSQL can read the archive before connecting to Render:

```powershell
docker run --rm -v "${PWD}:/backup" postgres:17 pg_restore --list /backup/o2o-test-data.dump
```

This checks the dump file locally; it does not contact or change a database.
It should print the archive's table of contents. An error such as "not a
valid archive" means the backup needs to be recreated before continuing.

The local database checked for this guide reports Alembic revision
`20261026_invoices` (head). Check yours before backing up if the database has
changed since:

```powershell
.\tingu\Scripts\alembic.exe current
```

## 3. Create a Render PostgreSQL database and restore the dump

In the Render dashboard:

1. Create a PostgreSQL database. Choose a region and a PostgreSQL version
   compatible with the local PostgreSQL 17 database, if version selection is
   offered.
2. Wait for the database to become available.
3. Copy its **External Database URL** from the database settings. You need the
   external URL for the restore command from your computer. Use the **Internal
   Database URL** later for the API service when both services are on Render.
4. Make sure the database is new and empty. Do not run the API against it yet:
   API startup runs migrations, which would create schema objects before the
   full database restore.
5. If the database's external connection is restricted by IP rules, allow your
   current public IP for the restore and remove that access when finished.

Run the connection test and restore from the repository directory. Copy the
**complete External Database URL** from Render's database connection page.
Do not use the internal URL from your local computer, guess the database name,
type the username/password separately, or append a second `?` query string.
If the URL already has query parameters, leave them intact. Paste the URL into
the secure prompt below; PowerShell will not echo the value as you type.

```powershell
$secureUrl = Read-Host "Paste the Render External Database URL" -AsSecureString
$urlPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureUrl)
try {
  $env:RENDER_DATABASE_URL = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($urlPointer)
  docker run --rm -e RENDER_DATABASE_URL postgres:17 sh -c 'psql "$RENDER_DATABASE_URL" -v ON_ERROR_STOP=1 -c "SELECT current_database(), current_user;"'
  if ($LASTEXITCODE -ne 0) { throw "Connection test failed. Do not run the restore until credentials are corrected." }

  docker run --rm -v "${PWD}:/backup" -e RENDER_DATABASE_URL postgres:17 sh -c 'pg_restore --no-owner --no-acl --dbname="$RENDER_DATABASE_URL" /backup/o2o-test-data.dump'
  if ($LASTEXITCODE -ne 0) { throw "Restore failed. Keep the local dump and inspect the error before retrying." }
}
finally {
  Remove-Item Env:RENDER_DATABASE_URL -ErrorAction SilentlyContinue
  [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($urlPointer)
}
```

Use this only for a fresh, empty target. The restore includes the schema and
test data. If it fails, keep the local dump and inspect the error before
repeating; do not use `--clean` against a database with data you want to keep.
If the connection test reports `password authentication failed`, reopen the
Render database's connection details and copy the current complete **External
Database URL** again. Check that the username and password came from the same
database and that the URL has not been truncated or edited. If you manually
constructed the URL, reserved password characters such as `@`, `:`, `/`, `?`,
`#`, or `%` must be URL-encoded; copying the URL generated by Render avoids
that common mistake. If you cannot confirm the current password, reset it in
Render and use the newly generated URL. If a real database URL was pasted into
a shared chat or committed file, rotate the database password.

Authentication failure happens before the archive can be restored; it does
not mean the dump is invalid. If authentication succeeds but the server says
the database does not exist, confirm the database name in the copied external
URL rather than changing the local dump. If the restore reports that objects
already exist, stop and use a fresh empty Render database; do not blindly add
`--clean`.
If the local database was created outside the Alembic migration chain, verify
its Alembic version before deploying; the startup migration may not be able to
upgrade a manually created schema.

## 4. Create the Render API web service

After the database restore has succeeded:

1. In Render, create a **Web Service** from the same Git repository and branch.
2. Select the **Docker** runtime and the repository root as the Docker build
   context. Use the included `Dockerfile`.
3. Choose the region closest to the database and connect the service to the
   same region where possible.
4. Set the health-check path to `/`. The root endpoint returns a small JSON
   service status response.
5. Configure these service environment variables:

| Variable | Value |
|---|---|
| `DATABASE_URL` | The Render PostgreSQL **Internal Database URL** |
| `JWT_SECRET_KEY` | A strong, random secret generated for this deployment |
| `CORS_ORIGINS` | `*` temporarily for any browser origin, or a comma-separated list of trusted frontend origins |

Do not use the Render External Database URL in the API service when both
services are on Render. Keep both URLs private. If `DATABASE_URL` starts with
`postgres://` or `postgresql://`, the app normalizes it to use the installed
`psycopg` driver.

`CORS_ORIGINS=*` allows browser-based frontends on any origin to call the API.
For better production control, set it to the exact origins, separated by
commas, for example:

```text
https://your-frontend.example,https://your-frontend.onrender.com
```

Do not include a trailing slash in an origin. CORS only controls browser
cross-origin access; it is not authentication. Protected endpoints still
require role-appropriate bearer tokens. The API uses bearer tokens rather than
cookie authentication, so CORS credentials are disabled.

## 5. Deploy and verify

Start the Render deployment. The container runs:

```text
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

If the migration fails, the API process will not start. Read the Render service
logs; verify that `DATABASE_URL` points to the restored database and that the
database is reachable. Do not manually rerun a failing destructive restore.

When the deployment is live, verify:

- `https://<your-service>.onrender.com/` returns the API status JSON.
- `https://<your-service>.onrender.com/docs` loads Swagger.
- `https://<your-service>.onrender.com/openapi.json` returns the live API
  schema.
- Sign in and test representative endpoints. The imported users and records
  should be present.
- From the other desktop, use the public Render service URL as the frontend's
  API base URL, for example
  `https://<your-service>.onrender.com/api/v1`.

If the second desktop runs the frontend locally, `CORS_ORIGINS=*` permits its
browser origin. If you use a restricted origin list, add that frontend's
precise origin (including scheme and port) to `CORS_ORIGINS`, then redeploy.

## 6. Keep the data safe

- Choose a Render PostgreSQL plan whose storage, expiry, and backup behavior
  meet your needs. Review the current plan details in Render before relying on
  it for important data.
- Keep periodic database backups outside the API image. Test restoring a
  backup into a separate database before treating it as your recovery plan.
- Store the original local dump safely until you have verified the migrated
  data and made a separate backup.
- Never add the Render connection URLs, `JWT_SECRET_KEY`, local `.env`, or
  database dumps to Git or frontend code.
- The API's `/docs` and `/openapi.json` are public by default. Do not treat
  hiding Swagger as a substitute for authorization on protected operations.

## Troubleshooting

| Symptom | Check |
|---|---|
| Container exits before becoming healthy | Read startup logs; confirm the migration succeeded and `DATABASE_URL` is set. |
| `failed to resolve host 'dpg-…'` during `alembic upgrade head` | The API cannot resolve the database hostname. If `DATABASE_URL` uses the Render Internal Database URL, verify the API and database are in the same Render region and use the exact Internal Database URL copied from that database's Connect page. If they are in different regions, move them to the same region or use the External Database URL as a temporary workaround. Redeploy after changing the service environment variable. |
| `No module named psycopg2` | Ensure the Render database URL is set and the app is using the current URL normalization and `psycopg` dependency. |
| `password authentication failed` during restore | Use the current full External Database URL copied from Render. Verify the username/password pair, do not append duplicate URL query strings, and test with `psql` before `pg_restore`. |
| `pg_restore` says the file is not a valid archive | Run the local archive-list check in Step 2. If it fails, recreate the backup from the local PostgreSQL service. |
| API returns `401` or `403` | Log in again; verify the token belongs to an active account with the route's required role. |
| Browser reports a CORS error | Check the frontend's exact origin in `CORS_ORIGINS`, then redeploy the API. |
| Existing test records are missing | Confirm the dump was restored to the same Render database URL configured on the API service. |
| Restore reports existing tables or objects | Stop and use a fresh empty Render database; do not blindly run a clean restore against valuable data. |

For local setup and feature documentation, see [README.md](./README.md) and the
[Backend Frontend Guide](./BACKEND_FRONTEND_GUIDE.md).
