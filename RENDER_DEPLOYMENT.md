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

Run the restore from the repository directory. The URL is entered at the
PowerShell prompt and passed to a temporary PostgreSQL client container; it is
not written to a project file:

```powershell
$env:RENDER_DATABASE_URL = Read-Host "Paste the Render External Database URL"
docker run --rm -v "$((Get-Location).Path):/backup" -e RENDER_DATABASE_URL postgres:17 sh -c 'pg_restore --no-owner --no-acl --dbname="$RENDER_DATABASE_URL" /backup/o2o-test-data.dump'
Remove-Item Env:RENDER_DATABASE_URL
```

Use this only for a fresh, empty target. The restore includes the schema and
test data. If it fails, keep the local dump and inspect the error before
repeating; do not use `--clean` against a database with data you want to keep.
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
| `No module named psycopg2` | Ensure the Render database URL is set and the app is using the current URL normalization and `psycopg` dependency. |
| API returns `401` or `403` | Log in again; verify the token belongs to an active account with the route's required role. |
| Browser reports a CORS error | Check the frontend's exact origin in `CORS_ORIGINS`, then redeploy the API. |
| Existing test records are missing | Confirm the dump was restored to the same Render database URL configured on the API service. |
| Restore reports existing tables or objects | Stop and use a fresh empty Render database; do not blindly run a clean restore against valuable data. |

For local setup and feature documentation, see [README.md](./README.md) and the
[Backend Frontend Guide](./BACKEND_FRONTEND_GUIDE.md).
