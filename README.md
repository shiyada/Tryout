# Ada Salon — Backend (Flask)

A Flask + SQLite backend for the Ada salon management app. Mirrors the data
model used by the front end: stylists, services, appointments, inventory,
invoices, and a computed client list.

## Setup

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

The API is live at `http://127.0.0.1:5000`. A SQLite file `ada_salon.db` is
created automatically on first run and seeded with sample data (same demo
data as the front end).

## Changing the haircut charge

Prices live in the `services` table, not hardcoded in the front end.

1. Find the Haircut service's id:
   ```bash
   curl http://127.0.0.1:5000/services
   ```
2. Update its price:
   ```bash
   curl -X PATCH http://127.0.0.1:5000/services/<service_id> \
        -H "Content-Type: application/json" \
        -d '{"price": 500}'
   ```

Every new booking and invoice will use the updated price.

## Endpoints

| Resource | Routes |
|---|---|
| Stylists | `GET/POST /stylists`, `PATCH/DELETE /stylists/<id>` |
| Services | `GET/POST /services`, `PATCH/DELETE /services/<id>` |
| Appointments | `GET/POST /appointments`, `PATCH/DELETE /appointments/<id>` (conflict-checked per stylist) |
| Inventory | `GET/POST /inventory`, `PATCH/DELETE /inventory/<id>`, `POST /inventory/<id>/adjust` (`{"delta": -1}`) |
| Invoices | `GET/POST /invoices` (creating one auto-decrements matching inventory stock) |
| Clients | `GET /clients` (computed from appointment + invoice history) |
| Dashboard | `GET /dashboard` (today's bookings, revenue, low stock, active staff) |

`GET /appointments` accepts optional `?date=YYYY-MM-DD` and `?stylist_id=`
query params.

## Connecting the React front end

CORS is open to all origins by default via `flask-cors`. Example call from
the Ada React artifact:

```js
const res = await fetch("http://127.0.0.1:5000/appointments?date=2026-08-19");
const appointments = await res.json();
```

For production, restrict CORS to your actual front-end domain
(`CORS(app, origins=["https://yourdomain.com"])`), use a production WSGI
server (gunicorn/waitress) instead of the Flask dev server, and consider
Postgres if you need multiple concurrent writers.

## Notes

- Times (`start`, `duration`) are stored as **minutes after midnight**,
  matching the front end's calendar grid (e.g. 9:30 AM = 570).
- Tax is a flat 5% GST, applied in the invoice route. Change `TAX_RATE` in
  `main.py` if your rate differs.
- Single-file app for clarity. If it grows, split into blueprints per
  resource (`stylists.py`, `appointments.py`, etc.).
