# O2O Campaigner

O2O Campaigner is a FastAPI and PostgreSQL backend for a hyperlocal offers
platform. Customers can find nearby offers and claim vouchers; merchants can
manage stores and offers and record sales or invoices; administrators can
review stores and manage retained merchant/store records.

## Features

- JWT bearer authentication and customer, merchant, and admin roles.
- Merchant store management with a 73-category catalog, coordinates, and
  Google Maps sharing links.
- Scheduled offers and customer nearby search with optional category and
  distance filters.
- Customer voucher claiming and merchant voucher redemption.
- Merchant sales entry and invoices with line items and manually managed paid
  or unpaid status.
- Merchant, customer, and admin dashboards. Admin analytics do not expose
  billing amounts or invoice details.
- Alembic database migrations.

## Requirements

- Windows with PowerShell (commands below use Windows paths).
- Python version compatible with the packages in `requirements.txt`.
- Docker Desktop with Docker Compose.

## Local setup

Run commands from the repository root.

### 1. Configure environment variables

The application reads `.env` from the repository root. It requires
`DATABASE_URL` and `JWT_SECRET_KEY`. PostgreSQL Compose configuration also
uses `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB`.

The repository's `.env` is ignored by Git. Create or update it locally with
your own values; do not commit credentials. For example, the database URL for
the local PostgreSQL container should use host port `5433`:

```dotenv
POSTGRES_USER=your_local_user
POSTGRES_PASSWORD=your_local_password
POSTGRES_DB=o2o_campaigner
DATABASE_URL=postgresql+psycopg://your_local_user:your_local_password@localhost:5433/o2o_campaigner
JWT_SECRET_KEY=replace_with_a_long_random_secret
```

If a password contains URL-reserved characters, percent-encode it in
`DATABASE_URL`. Keep the Compose database credentials and the credentials in
the URL consistent.

### 2. Create a Python environment and install dependencies

If the repository's `tingu` virtual environment is already installed, activate
it and skip the creation step:

```powershell
python -m venv tingu
.\tingu\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell does not allow script activation, call the executables directly,
as shown below.

### 3. Start PostgreSQL

The Compose file starts PostgreSQL only; it does not start the API:

```powershell
docker compose up -d postgres
docker compose ps
```

Wait until the PostgreSQL service is healthy before applying migrations.

### 4. Apply database migrations

```powershell
.\tingu\Scripts\alembic.exe upgrade head
```

This creates/updates the schema and applies the category seed migration.
Alembic and the API must use the same `DATABASE_URL`.

### 5. Start the API

```powershell
.\tingu\Scripts\python.exe -m uvicorn app.main:app --reload
```

Local URLs:

- API root: <http://127.0.0.1:8000/>
- Swagger UI: <http://127.0.0.1:8000/docs>
- OpenAPI JSON: <http://127.0.0.1:8000/openapi.json>

## API overview

Protected endpoints require an access token from `POST /api/v1/auth/login`:

```http
Authorization: Bearer <access_token>
```

| Area | Main endpoints |
|---|---|
| Authentication | `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `GET /api/v1/auth/me` |
| Merchant stores | `GET /api/v1/merchant/stores/categories`, `GET/POST /api/v1/merchant/stores` |
| Merchant offers | `GET/POST /api/v1/merchant/offers`, publish and cancel offer routes |
| Customer offers | `GET /api/v1/customer/offers`, `POST /api/v1/customer/offers/{offer_id}/claim` |
| Customer vouchers | `GET /api/v1/customer/vouchers`, `GET /api/v1/customer/dashboard` |
| Merchant billing | `/api/v1/merchant/billing/sales`, `/api/v1/merchant/billing/invoices` |
| Dashboards | `GET /api/v1/merchant/dashboard`, `/api/v1/customer/dashboard`, `/api/v1/admin/dashboard` |
| Admin operations | Merchant retention, store review, delete, and restore routes under `/api/v1/admin` |

Register only customer and merchant accounts through the API. Admin accounts
must be provisioned by an authorized operator. The customer nearby-offer
endpoint requires coordinates; its `category_id` filter is optional, so
omitting it searches across categories.

For the full route catalog, request and response formats, example frontend
calls, invoice flows, and all endpoint-specific JSON samples, see the
[Backend Frontend Guide](./BACKEND_FRONTEND_GUIDE.md) and
[frontend-api-examples/](./frontend-api-examples/). Category names and IDs are
also listed in [STORE_CATEGORIES.md](./STORE_CATEGORIES.md); use the category
API as the runtime source of truth.

## Frontend integration notes

- Send JSON request bodies with `Content-Type: application/json`.
- Include the bearer token for protected routes and use an account with the
  required role.
- Handle `401` (missing/invalid token), `403` (wrong role), `404` (record not
  found), `409` (state conflict), and `422` (invalid input).
- The FastAPI app does not currently configure CORS. A separately hosted
  browser frontend needs CORS configured for its origin before cross-origin
  requests will work.
- Invoice amounts use integer paise. Tax calculation, online payment
  collection, and PDF generation are not provided by the API.

## Database and record retention

Use Alembic for schema changes and review migrations before applying them to
non-local databases. Store and merchant deactivation/deletion operations are
soft operations that retain records; restore actions are available to admins.

## Security

Never commit `.env`, access tokens, passwords, database credentials, or private
keys. Use strong local secrets and a dedicated secret-management solution for
deployed environments. Do not expose admin credentials or tokens in a
frontend application.
