# O2O Campaigner Frontend Integration Guide

This guide describes the FastAPI routes currently registered in Swagger and
how a browser frontend can call them. The examples use JavaScript `fetch` and
React-style state where useful; adapt them to your frontend framework.

## 1. Start the services

The current Compose file starts PostgreSQL only. From the repository root:

```powershell
docker compose up -d postgres
.\tingu\Scripts\alembic.exe upgrade head
.\tingu\Scripts\python.exe -m uvicorn app.main:app --reload
```

Open Swagger at `http://127.0.0.1:8000/docs`.

The migration adds the optional store Google Maps column and seeds the category
catalog. Run it against the same database used by the API. If the API is opened
from another device, replace `127.0.0.1` with the API host address and configure
CORS for the frontend origin before browser requests. The current FastAPI app
does not yet configure CORS middleware, so a separately hosted browser frontend
needs that configured before cross-origin API calls will work.

## 2. Common frontend request helper

JSON endpoints accept and return JSON. Send the bearer token for protected
operations. Do not put passwords, access tokens, or database credentials in
source control.

```js
const API_BASE = "http://127.0.0.1:8000/api/v1";

function authHeaders(token) {
  if (!token) return {};
  const headerName = ["Authori", "zation"].join("");
  const scheme = ["Bear", "er"].join("");
  return { [headerName]: `${scheme} ${token}` };
}

async function apiRequest(path, { token, method = "GET", body } = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers: {
      ...(body === undefined ? {} : { "Content-Type": "application/json" }),
      ...authHeaders(token),
    },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });

  if (response.status === 204) return null;

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const message = data?.detail ?? `Request failed (${response.status})`;
    throw new Error(
      typeof message === "string" ? message : JSON.stringify(message),
    );
  }
  return data;
}
```

For a one-off request, the same pattern can be written directly:

```js
const response = await fetch(
  `${API_BASE}/customer/offers?latitude=28.7041&longitude=77.1025&radius_km=2`,
  { headers: authHeaders(token) },
);
const offers = await response.json();
```

If the frontend already uses Axios, the equivalent call is:

```js
const { data: offers } = await axios.get(`${API_BASE}/customer/offers`, {
  params: { latitude: 28.7041, longitude: 77.1025, radius_km: 2 },
  headers: authHeaders(token),
});
```

Typical responses:

- `401`: missing, invalid, or expired bearer token; sign in again.
- `403`: authenticated account does not have the required role.
- `404`: requested record or category ID was not found.
- `409`: state conflict, such as an already claimed voucher or inactive offer.
- `422`: invalid request body or query parameter; show the validation message.
- `204`: success with no response body, for soft deletion/cancellation.

### JSON examples for every endpoint

The [`frontend-api-examples/`](./frontend-api-examples/) folder contains one
JSON example bundle for every currently registered endpoint, including the
service-root check. Each filename identifies the resource and HTTP method.
These files document both the request and a representative success response;
they are examples, not a live export from your database.

Each bundle uses this structure:

```json
{
  "method": "POST",
  "path": "/api/v1/auth/register",
  "auth_required": false,
  "request_body": {
    "name": "Asha Customer",
    "email": "asha@example.com",
    "password": "change-this-password",
    "role": "customer"
  },
  "success_response": {
    "status": 201,
    "body": {
      "id": "6f4019d4-41b6-47f0-b8aa-0714c19f1c20",
      "name": "Asha Customer",
      "email": "asha@example.com",
      "role": "customer",
      "is_active": true
    }
  }
}
```

How to use the bundle:

1. Set the HTTP method and path from the JSON file. Replace `{store_id}`,
   `{offer_id}`, `{merchant_id}`, and `{invoice_code}` with real values returned
   by earlier API calls.
2. If `auth_required` is `true`, use `authHeaders(token)` and the role
   specified by the example file (`role`: customer, merchant, admin,
   or any active user).
3. Add the values in `query_parameters` to the URL as a URL-encoded query
   string. `path_parameters` are path substitutions, not query parameters.
4. For a request with a JSON body, copy only the value of `request_body` into
   the HTTP body and set `Content-Type: application/json`. Do not send the
   outer example wrapper as the API payload.
5. `success_response.status` and `.body` show the expected success status and
   representative response shape. A `204` response has `body: null`; do not
   try to parse it as JSON.
6. `<...>` values are placeholders. UUIDs, dates, invoice codes, and IDs in
   examples must be replaced by values from your own API/database. Passwords
   are examples only; never store real credentials in these files.

| Endpoint | JSON example |
|---|---|
| `GET /` | [root_get.json](./frontend-api-examples/root_get.json) |
| `POST /api/v1/auth/register` | [auth_register_post.json](./frontend-api-examples/auth_register_post.json) |
| `POST /api/v1/auth/login` | [auth_login_post.json](./frontend-api-examples/auth_login_post.json) |
| `GET /api/v1/auth/me` | [auth_me_get.json](./frontend-api-examples/auth_me_get.json) |
| `GET /api/v1/merchant/stores/categories` | [merchant_stores_categories_get.json](./frontend-api-examples/merchant_stores_categories_get.json) |
| `GET /api/v1/merchant/stores` | [merchant_stores_get.json](./frontend-api-examples/merchant_stores_get.json) |
| `POST /api/v1/merchant/stores` | [merchant_stores_post.json](./frontend-api-examples/merchant_stores_post.json) |
| `DELETE /api/v1/merchant/stores/{store_id}` | [merchant_stores_store_id_delete.json](./frontend-api-examples/merchant_stores_store_id_delete.json) |
| `GET /api/v1/merchant/offers` | [merchant_offers_get.json](./frontend-api-examples/merchant_offers_get.json) |
| `POST /api/v1/merchant/offers` | [merchant_offers_post.json](./frontend-api-examples/merchant_offers_post.json) |
| `POST /api/v1/merchant/offers/{offer_id}/publish` | [merchant_offers_offer_id_publish_post.json](./frontend-api-examples/merchant_offers_offer_id_publish_post.json) |
| `DELETE /api/v1/merchant/offers/{offer_id}` | [merchant_offers_offer_id_delete.json](./frontend-api-examples/merchant_offers_offer_id_delete.json) |
| `GET /api/v1/customer/offers` | [customer_offers_get.json](./frontend-api-examples/customer_offers_get.json) |
| `POST /api/v1/customer/offers/{offer_id}/claim` | [customer_offers_offer_id_claim_post.json](./frontend-api-examples/customer_offers_offer_id_claim_post.json) |
| `GET /api/v1/customer/vouchers` | [customer_vouchers_get.json](./frontend-api-examples/customer_vouchers_get.json) |
| `GET /api/v1/customer/dashboard` | [customer_dashboard_get.json](./frontend-api-examples/customer_dashboard_get.json) |
| `POST /api/v1/merchant/billing/sales` | [merchant_billing_sales_post.json](./frontend-api-examples/merchant_billing_sales_post.json) |
| `POST /api/v1/merchant/billing/invoices` | [merchant_billing_invoices_post.json](./frontend-api-examples/merchant_billing_invoices_post.json) |
| `GET /api/v1/merchant/billing/invoices` | [merchant_billing_invoices_get.json](./frontend-api-examples/merchant_billing_invoices_get.json) |
| `GET /api/v1/merchant/billing/invoices/{invoice_code}` | [merchant_billing_invoice_code_get.json](./frontend-api-examples/merchant_billing_invoice_code_get.json) |
| `PATCH /api/v1/merchant/billing/invoices/{invoice_code}/payment-status` | [merchant_billing_invoice_payment_status_patch.json](./frontend-api-examples/merchant_billing_invoice_payment_status_patch.json) |
| `GET /api/v1/merchant/billing/dashboard` | [merchant_billing_dashboard_get.json](./frontend-api-examples/merchant_billing_dashboard_get.json) |
| `GET /api/v1/merchant/dashboard` | [merchant_dashboard_get.json](./frontend-api-examples/merchant_dashboard_get.json) |
| `GET /api/v1/admin/merchants` | [admin_merchants_get.json](./frontend-api-examples/admin_merchants_get.json) |
| `DELETE /api/v1/admin/merchants/{merchant_id}` | [admin_merchants_merchant_id_delete.json](./frontend-api-examples/admin_merchants_merchant_id_delete.json) |
| `POST /api/v1/admin/merchants/{merchant_id}/restore` | [admin_merchants_merchant_id_restore_post.json](./frontend-api-examples/admin_merchants_merchant_id_restore_post.json) |
| `DELETE /api/v1/admin/stores/{store_id}` | [admin_stores_store_id_delete.json](./frontend-api-examples/admin_stores_store_id_delete.json) |
| `GET /api/v1/admin/stores/pending` | [admin_stores_pending_get.json](./frontend-api-examples/admin_stores_pending_get.json) |
| `GET /api/v1/admin/stores/deleted` | [admin_stores_deleted_get.json](./frontend-api-examples/admin_stores_deleted_get.json) |
| `POST /api/v1/admin/stores/{store_id}/restore` | [admin_stores_store_id_restore_post.json](./frontend-api-examples/admin_stores_store_id_restore_post.json) |
| `PATCH /api/v1/admin/stores/{store_id}/verification` | [admin_stores_store_id_verification_patch.json](./frontend-api-examples/admin_stores_store_id_verification_patch.json) |
| `GET /api/v1/admin/dashboard` | [admin_dashboard_get.json](./frontend-api-examples/admin_dashboard_get.json) |

The `request_body` field is the exact JSON shape to send for that call.
Examples with `request_body: null` (or no body field) do not need a request
body. Each endpoint section below further explains its business rules, field
units, and how its returned IDs connect to later calls. The live Swagger
schema at `/docs` remains authoritative if the API changes.

### `GET /`

No token. Basic server check; returns:

```json
{
  "message": "O2O Campaigner API is running"
}
```

## 3. Authentication and role-specific screens

The registration endpoint supports `customer` and `merchant`; it does not
support creating an admin account. Admin accounts must be provisioned by an
authorized operator.

### `POST /api/v1/auth/register`

No token. Request:

```json
{
  "name": "Asha Customer",
  "email": "asha@example.com",
  "password": "change-this-password",
  "role": "customer"
}
```

Set role to `"merchant"` for merchant signup. The role defaults to `customer`
if omitted. Success is `201 Created` and returns the user profile:

```json
{
  "id": "6f4019d4-41b6-47f0-b8aa-0714c19f1c20",
  "name": "Asha Customer",
  "email": "asha@example.com",
  "role": "customer",
  "is_active": true
}
```

An email that is already registered returns `409 Conflict`.

### `POST /api/v1/auth/login`

No token. Request:

```json
{
  "email": "asha@example.com",
  "password": "change-this-password"
}
```

Success returns a bearer token:

```json
{
  "access_token": "<token>",
  "token_type": "bearer"
}
```

Keep the token in the frontend's chosen secure session strategy. For
protected routes, use the shared helper to send the token with the
Bearer scheme. Inactive accounts cannot log in.

### `GET /api/v1/auth/me`

Requires any active logged-in user. Returns the current user's profile, in the
same shape as the registration response. Use it after page load to identify
the user and select the customer, merchant, or admin navigation.

## 4. Store categories dropdown

### `GET /api/v1/merchant/stores/categories`

Returns a list of `{id, name}` values. This route currently does not require a
token. The category list is used as display labels in a dropdown; the category
UUID is the value associated with each option.

Example response:

```json
[
  {
    "id": "c8a0c881-4e2f-5229-b1ff-3c6ac5fb1840",
    "name": "Grocery & Essentials / Kirana & General Store"
  },
  {
    "id": "e64b5098-b660-51a5-8308-a5301d1a2def",
    "name": "Food & Dining / Vegetarian / Restaurant"
  }
]
```

The example is abbreviated; the seeded catalog contains 73 categories. Fetch
the endpoint at runtime rather than hard-coding IDs. Existing category names
in a database retain their existing IDs. Use the API's returned IDs as the
source of truth.

### React dropdown example

```jsx
function CategorySelect({ value, onChange }) {
  const [categories, setCategories] = React.useState([]);
  const [error, setError] = React.useState("");

  React.useEffect(() => {
    apiRequest("/merchant/stores/categories")
      .then(setCategories)
      .catch((err) => setError(err.message));
  }, []);

  return (
    <label>
      Store category
      <select value={value ?? ""} onChange={(event) => onChange(event.target.value || null)}>
        <option value="">No category</option>
        {categories.map((category) => (
          <option key={category.id} value={category.id}>
            {category.name}
          </option>
        ))}
      </select>
      {error && <span role="alert">{error}</span>}
    </label>
  );
}
```

For store creation, send the selected ID as `category_id`. The backend also
accepts `category_name`; it resolves an exact name without regard to case. If
an unknown `category_name` is supplied, the store is created with a null
category. If an explicit non-existent `category_id` is supplied, creation
returns `404`. To select no category, omit both fields or send
`"category_id": null`.

## 5. Merchant store management

### `POST /api/v1/merchant/stores`

Merchant token required. Creates a pending store. A Google Maps HTTPS sharing
link is required for new stores. Existing stores can still have a null link.

Request example using the dropdown's ID:

```json
{
  "name": "Asha Kirana",
  "address": "Rohini Sector 22, Delhi",
  "lat": 28.7041,
  "lng": 77.1025,
  "category_id": "c8a0c881-4e2f-5229-b1ff-3c6ac5fb1840",
  "google_maps_link": "https://maps.app.goo.gl/example",
  "hours": {
    "monday": {
      "open": "09:00",
      "close": "21:00"
    }
  },
  "phone": "8882519873"
}
```

For no category, set `category_id` to `null`. Alternatively, send
`"category_name": "Grocery & Essentials / Kirana & General Store"` instead of
`category_id`; do not send both with non-null values. `lat` and `lng` must be
valid geographic coordinates. Success is `201 Created`; response includes the
new store ID and its `verification_status` (initially `"pending"`).

### `GET /api/v1/merchant/stores`

Merchant token required. Lists that merchant's non-deleted stores. Each item
includes ID, category ID, address, coordinates, Google Maps link, and
verification status. Use returned store IDs for creating offers and recording
sales.

### `DELETE /api/v1/merchant/stores/{store_id}`

Merchant token required; a merchant can only delete their own store. This is a
soft delete: the row and related sales/offers/vouchers are retained, the store
is suspended, and it is hidden from the merchant's normal store list. Success
is `204 No Content`.

## 6. Merchant offers

### `POST /api/v1/merchant/offers`

Merchant token required. The selected `store_id` must belong to the merchant
and the store must be verified. New offers start as `draft`.

```json
{
  "store_id": "ea21eb76-502e-414c-b2dd-37ebb8fd1f72",
  "title": "₹10 off on orders over ₹100",
  "description": "Save ₹10 on your next purchase.",
  "type": "fixed",
  "value": 10,
  "min_order_paise": 10000,
  "max_discount_paise": null,
  "starts_at": "2026-10-27T09:00:00+05:30",
  "ends_at": "2026-10-27T14:00:00+05:30",
  "max_claims": 100,
  "per_customer_limit": 1,
  "terms": "Minimum bill ₹100."
}
```

Amounts use paise except `value` on a fixed discount, which uses rupees:
₹100 is `10000` paise and a fixed `value` of `10` is ₹10. For percent offers,
`value` is a percentage from 1 to 70. Discounts above 20% require
`max_discount_paise`. Timestamps must include a timezone, end after start, and
the duration cannot exceed 90 days. Success is `201 Created` and returns an
`OfferResponse`.

### `GET /api/v1/merchant/offers`

Merchant token required. Lists the merchant's offers with status and schedule.
Use the `id` to publish an offer or to match dashboard rows.

### `POST /api/v1/merchant/offers/{offer_id}/publish`

Merchant token required; only the owner can publish. The offer must be draft,
belong to a verified store, and not have ended. Returns the updated offer. The
status becomes `scheduled` if its start time is in the future, otherwise
`active`.

### `DELETE /api/v1/merchant/offers/{offer_id}`

Merchant token required; only the owner can cancel. This cancels the offer
rather than physically deleting it and cancels vouchers that are still in
`claimed` status. Success is `204 No Content`.

## 7. Customer nearby offers, category filter, and map markers

### `GET /api/v1/customer/offers`

Customer token required. Query parameters:

| Parameter | Required | Meaning |
|---|---:|---|
| `latitude` | yes | Customer latitude, from -90 to 90 |
| `longitude` | yes | Customer longitude, from -180 to 180 |
| `radius_km` | no | Search radius; defaults to 2 and accepts 2 through 10 |
| `category_id` | no | Filter to one selected store category UUID |
| `limit` | no | Page size, defaults to 20, maximum 100 |
| `offset` | no | Number of results to skip, defaults to 0 |

No category chosen: omit `category_id`, which searches all categories:

```http
GET /api/v1/customer/offers?latitude=28.7041&longitude=77.1025&radius_km=2
```

Category chosen: include the selected category ID from the dropdown:

```http
GET /api/v1/customer/offers?latitude=28.7041&longitude=77.1025&radius_km=10&category_id=c8a0c881-4e2f-5229-b1ff-3c6ac5fb1840
```

Only active offers at verified stores are returned, nearest first. Response
example:

```json
[
  {
    "id": "f1b2c3d4-1234-4234-8234-123456789abc",
    "title": "₹10 off",
    "description": "Save on your next visit.",
    "type": "fixed",
    "value": 10,
    "min_order_paise": 10000,
    "max_discount_paise": null,
    "starts_at": "2026-10-27T03:30:00Z",
    "ends_at": "2026-10-27T08:30:00Z",
    "store": {
      "id": "ea21eb76-502e-414c-b2dd-37ebb8fd1f72",
      "name": "Asha Kirana",
      "address": "Rohini Sector 22, Delhi",
      "lat": "28.704100",
      "lng": "77.102500",
      "google_maps_link": "https://maps.app.goo.gl/example",
      "distance_km": 1.25
    }
  }
]
```

The frontend can use `store.lat` and `store.lng` for a map marker and
`google_maps_link` for a link-out action. The backend returns coordinates; it
does not render a map. The customer location can be requested with the browser
Geolocation API after explaining why it is needed and handling permission
denial:

```js
navigator.geolocation.getCurrentPosition(
  ({ coords }) => {
    const params = new URLSearchParams({
      latitude: String(coords.latitude),
      longitude: String(coords.longitude),
      radius_km: "2",
    });
    apiRequest(`/customer/offers?${params}`, { token })
      .then(setOffers)
      .catch(showError);
  },
  (error) => showError(error.message),
);
```

If the customer expands the search, repeat the request with `radius_km=10`.
If the customer picks another category, add or update the `category_id` query
parameter and fetch again. A free frontend map option is Leaflet with
OpenStreetMap tiles; follow the tile service usage policy and attribution
requirements.

## 8. Customer vouchers

### `POST /api/v1/customer/offers/{offer_id}/claim`

Customer token required. The offer must be active now and belong to a verified
store. Claiming twice or exceeding the offer claim limit returns `409 Conflict`.
Success is `201 Created`:

```json
{
  "id": "f264f5b2-fb91-4ad0-b5c4-9fd40284c098",
  "code": "voucher-code",
  "offer_id": "f1b2c3d4-1234-4234-8234-123456789abc",
  "store_id": "ea21eb76-502e-414c-b2dd-37ebb8fd1f72",
  "status": "claimed",
  "claimed_at": "2026-10-27T04:00:00Z",
  "expires_at": "2026-10-27T08:30:00Z"
}
```

Show and preserve the `code`; the merchant needs it to redeem the voucher.
The current database has a unique constraint that permits only one voucher
per customer per offer.

### `GET /api/v1/customer/vouchers`

Customer token required. Lists only the current customer's vouchers,
newest first. Supports `limit` (default 20, maximum 100) and `offset`
(default 0). Each item includes voucher code/status/expiry and offer/store
names.

### `GET /api/v1/customer/dashboard`

Customer token required. Returns voucher counts, not money:

```json
{
  "vouchers_claimed": 4,
  "vouchers_used": 1,
  "vouchers_available": 2,
  "vouchers_expired": 1,
  "vouchers_cancelled": 0
}
```

## 9. Merchant sale entry and dashboard

### `POST /api/v1/merchant/billing/sales`

Merchant token required. This records a completed sale inside this app; it is
not an external POS integration, invoice, tax calculator, or payment gateway.
The store must belong to the merchant and be pending or verified.

Without a voucher:

```json
{
  "store_id": "ea21eb76-502e-414c-b2dd-37ebb8fd1f72",
  "gross_amount_paise": 12500
}
```

With a customer's voucher:

```json
{
  "store_id": "ea21eb76-502e-414c-b2dd-37ebb8fd1f72",
  "gross_amount_paise": 12500,
  "voucher_code": "voucher-code"
}
```

`gross_amount_paise` is the total before voucher discount. The response gives
gross, discount, and net (after discount, before tax), all in paise. Billing is
available for stores in `pending` or `verified` status; voucher discounts are
available only for verified stores. A voucher is locked, validated, redeemed,
and recorded with its sale in the same transaction.

### `POST /api/v1/merchant/billing/invoices`

Create an invoice for a store owned by the signed-in merchant. Pending and
verified stores can be billed; suspended/rejected stores cannot. An invoice
code is generated uniquely across all merchants. Tax is not calculated.
Amounts are integers in paise. A voucher is optional, but can only be redeemed
on a verified store.

Request:

```json
{
  "store_id": "ea21eb76-502e-414c-b2dd-37ebb8fd1f72",
  "items": [
    {
      "description": "Maggie noodles",
      "quantity": 2,
      "unit_price_paise": 1500
    },
    {
      "description": "Cold drink",
      "quantity": 1,
      "unit_price_paise": 4000
    }
  ]
}
```

The example subtotal is `7000` paise (₹70). Add `"voucher_code":
"customer-voucher-code"` to apply a valid voucher at a verified store.
Response is `201 Created`, including the generated code, calculated totals,
payment status (`unpaid` initially), issue timestamp, and line items. Invoices
can be printed or saved as PDF by the frontend; the API returns invoice data
and does not generate a PDF file.

Example response:

```json
{
  "id": "61a6382e-08e7-491a-a339-585096be746b",
  "code": "INV-98AE31829F7A4B358C",
  "store_id": "ea21eb76-502e-414c-b2dd-37ebb8fd1f72",
  "subtotal_paise": 7000,
  "discount_paise": 0,
  "total_paise": 7000,
  "payment_status": "unpaid",
  "issued_at": "2026-10-27T03:30:00Z",
  "paid_at": null,
  "voucher_id": null,
  "line_items": [
    {
      "id": "5fe5b5e8-6086-4d38-b17a-14d1eefbe2bf",
      "position": 0,
      "description": "Maggie noodles",
      "quantity": 2,
      "unit_price_paise": 1500,
      "line_total_paise": 3000
    },
    {
      "id": "29009158-5d12-4bc6-9d55-8d5df004af9f",
      "position": 1,
      "description": "Cold drink",
      "quantity": 1,
      "unit_price_paise": 4000,
      "line_total_paise": 4000
    }
  ]
}
```

### `GET /api/v1/merchant/billing/invoices`

List the authenticated merchant's invoices, newest first. Optional parameters:
`payment_status=paid|unpaid`, `limit` (default 20, maximum 100), and `offset`
(default 0). The response is an array of full invoice records with line items.

### `GET /api/v1/merchant/billing/invoices/{invoice_code}`

Get a single invoice belonging to the authenticated merchant. Another
merchant's invoice is not exposed and returns `404`.

### `PATCH /api/v1/merchant/billing/invoices/{invoice_code}/payment-status`

Mark an invoice paid or unpaid; this is a manual status update, not a payment
gateway operation. Request:

```json
{ "payment_status": "paid" }
```

The API records `paid_at` when set to paid and clears it when marked unpaid.

### `GET /api/v1/merchant/billing/dashboard`

Returns only the current merchant's invoice counts and paise totals:

```json
{
  "invoices_count": 2,
  "paid_invoices_count": 1,
  "unpaid_invoices_count": 1,
  "invoiced_total_paise": 10000,
  "paid_total_paise": 7000,
  "unpaid_total_paise": 3000
}
```

### `GET /api/v1/merchant/dashboard`

The merchant dashboard combines billing totals with offer analytics. Billing
is available even when all the merchant's stores are pending. `offer_analytics`
is `null` until the merchant has a verified store; afterward it contains
sales and offer metrics only for verified stores. Example before verification:

```json
{
  "billing": {
    "invoices_count": 1,
    "paid_invoices_count": 0,
    "unpaid_invoices_count": 1,
    "invoiced_total_paise": 7000,
    "paid_total_paise": 0,
    "unpaid_total_paise": 7000
  },
  "offer_analytics": null
}
```

After a store is verified, `offer_analytics` is populated. In the full
dashboard response, it is nested beside `billing`:

```json
{
  "billing": {
    "invoices_count": 1,
    "paid_invoices_count": 0,
    "unpaid_invoices_count": 1,
    "invoiced_total_paise": 7000,
    "paid_total_paise": 0,
    "unpaid_total_paise": 7000
  },
  "offer_analytics": {
    "gross_sales_paise": 25000,
    "discounts_paise": 1500,
    "net_sales_paise": 23500,
    "sales_count": 3,
    "offers": [
      {
        "offer_id": "f1b2c3d4-1234-4234-8234-123456789abc",
        "title": "₹10 off",
        "status": "active",
        "starts_at": "2026-10-27T03:30:00Z",
        "ends_at": "2026-10-27T08:30:00Z",
        "sales_count": 2,
        "gross_sales_paise": 20000,
        "discounts_paise": 1500,
        "net_sales_paise": 18500,
        "vouchers_claimed": 5,
        "vouchers_used": 2
      }
    ]
  }
}
```

Admin endpoints do not expose invoice records or billing totals. Tax, external
POS synchronization, and online payment processing are not included.

## 10. Admin operations and dashboard

All `/api/v1/admin/...` operations below require an admin token. Admin dashboard
analytics intentionally omit sales amounts and billing data.

### `GET /api/v1/admin/stores/pending`

Lists stores whose verification status is `pending`, ordered oldest first so
admins can review the longest-waiting submissions. Supports `limit` (default
50, maximum 100) and `offset` (default 0). Returns the same store fields as the
merchant store API.

### `GET /api/v1/admin/merchants`

Lists merchants. Optional query parameters: `is_active=true|false`,
`limit` (default 50, maximum 100), and `offset` (default 0). Use
`is_active=false` to find deactivated merchants.

### `DELETE /api/v1/admin/merchants/{merchant_id}`

Deactivates the merchant and archives/suspends their stores. This retains
database records; it is not a physical delete. Inactive accounts cannot log in
or register again with the same email until administratively restored. Returns
merchant state and `stores_suspended`.

### `POST /api/v1/admin/merchants/{merchant_id}/restore`

Reactivates a deactivated merchant. Their stores remain archived until an
admin restores them individually. Returns `stores_restored: false`.

### `GET /api/v1/admin/stores/deleted`

Lists retained deleted stores with deletion timestamp, actor, and reason.
Supports `limit` (default 50, maximum 100) and `offset` (default 0).

### `DELETE /api/v1/admin/stores/{store_id}`

Soft-deletes any store, retaining related data. Success is `204 No Content`.

### `POST /api/v1/admin/stores/{store_id}/restore`

Restores a retained store only if its owner is active. It restores the status
recorded before deletion. Returns the store ID and restored status.

### `PATCH /api/v1/admin/stores/{store_id}/verification`

Approves or rejects a pending store:

```json
{
  "decision": "approve"
}
```

Reject with a reason:

```json
{
  "decision": "reject",
  "reason": "Please provide a clearer storefront photo."
}
```

Returns the updated store. Rejection requires a non-empty reason.

### `GET /api/v1/admin/dashboard`

Admin token required. Returns platform merchant totals, offer counts by status,
top offers by voucher usage, top merchants by voucher usage, and voucher
claim/use counts. The response intentionally contains **no bill values, gross
sales, discounts, net sales, invoices, or billing details**. Offer records are
paginated with `offers_limit` (default 50, maximum 100) and `offers_offset`
(default 0).

## 11. Suggested frontend implementation order

1. Build a shared API client and error display.
2. Add registration/login and persist the access token using the app's chosen
   session design. Call `/auth/me` to select the role-specific screen.
3. Build merchant store creation. Fetch categories for the dropdown, capture
   the selected UUID, request Google Maps link and coordinates, then create the
   store.
4. Build the admin store-review page so the merchant's pending store can be
   approved.
5. Build merchant offer create/list/publish/cancel screens.
6. Build customer nearby-offer search with geolocation, the category dropdown,
   radius expansion, and map/list results.
7. Build customer claim, voucher list, and voucher dashboard.
8. Build merchant sale entry and dashboard.
9. Build admin merchant/store retention controls and admin analytics. Do not
   show sales amounts on the admin screen.

## 12. Current backend boundaries to keep in mind

- Category lookup and store creation are separate requests: load dropdown
  options first, then submit the selected ID (or name).
- The category seed contains common offline business categories, not every
  possible shop type. Unknown category names map to null; an invalid explicit
  category UUID returns `404`.
- The new store request requires `google_maps_link`; the column is nullable so
  pre-existing stores can remain null.
- Customer nearby search requires explicit customer latitude/longitude.
- Only active offers at verified stores are shown to customers.
- Merchant dashboard sales depend on sales entered through the app. No external
  billing/POS data is synchronized.
- Tax calculation, online payment collection, and a graphical dashboard UI are
  not implemented. Merchant invoices are available as JSON records, but the
  API does not generate a PDF.
- Admin dashboard reports offer and voucher performance but no billing values.
- Store/merchant "delete" operations are soft deletes for record retention.
- Swagger (`/docs`) and OpenAPI (`/openapi.json`) are the live API references.
