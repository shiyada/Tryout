# Ada Salon — Backend (Flask + PostgreSQL)

Same API as the SQLite/Flask version, now backed by PostgreSQL.

## Setup

1. **Create the database** (adjust user/host as needed):
   ```bash
   createdb ada_salon
   ```
   Or from `psql`:
   ```sql
   CREATE DATABASE ada_salon;
   ```

2. **Configure the connection**:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and set `DATABASE_URL`, e.g.:
   ```
   DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/ada_salon
   ```

3. **Install dependencies**:
   ```bash
   python -m venv venv
   source venv/bin/activate      # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

## Run

```bash
python main.py
```

The API is live at `http://127.0.0.1:5000`. Tables are created automatically
on first run, and seeded with sample data (same demo data as before) if the
`stylists` table is empty.

## Changing the haircut charge

Prices live in the `services` table.

```bash
curl http://127.0.0.1:5000/services
curl -X PATCH http://127.0.0.1:5000/services/<service_id> \
     -H "Content-Type: application/json" \
     -d '{"price": 500}'
```

## Endpoints

Identical to the SQLite version:

| Resource | Routes |
|---|---|
| Stylists | `GET/POST /stylists`, `PATCH/DELETE /stylists/<id>` |
| Services | `GET/POST /services`, `PATCH/DELETE /services/<id>` |
| Appointments | `GET/POST /appointments`, `PATCH/DELETE /appointments/<id>` (conflict-checked per stylist) |
| Inventory | `GET/POST /inventory`, `PATCH/DELETE /inventory/<id>`, `POST /inventory/<id>/adjust` (`{"delta": -1}`) |
| Invoices | `GET/POST /invoices` (auto-decrements matching inventory stock) |
| Clients | `GET /clients` (computed from appointment + invoice history) |
| Dashboard | `GET /dashboard` |

`GET /appointments` accepts optional `?date=YYYY-MM-DD` and `?stylist_id=`.

## Connecting a front end

CORS is open to all origins by default. The `ada_salon_live.html` front end
(the API-connected version of the Ada app) points at whatever URL you set
in its API settings panel — point it at this server's address, e.g.
`http://127.0.0.1:5000` on the same machine, or your computer's LAN IP if
opening the page from a phone.

## Notes

- Because Postgres returns `NUMERIC` columns as `Decimal`, `to_dict()`
  converts them to plain floats (or ints for whole-number stock/qty fields)
  so the JSON stays clean.
- Times (`start`, `duration`) are stored as **minutes after midnight**.
- Tax is a flat 5% GST — change `TAX_RATE` in `main.py` if needed.
- For production: use a connection pool (e.g. `psycopg2.pool` or
  `SQLAlchemy`) instead of opening a new connection per request, and run
  behind gunicorn rather than the Flask dev server.
