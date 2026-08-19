# Ada Salon — Backend

A FastAPI + SQLite backend for the Ada salon management app. It mirrors the
data model used by the front end: stylists, services, appointments,
inventory, invoices, and a computed client list.

## Setup

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn main:app --reload
```

The API is now live at `http://127.0.0.1:8000`, with interactive docs at
`http://127.0.0.1:8000/docs`. A SQLite file `ada_salon.db` is created
automatically on first run and seeded with sample data (same as the front
end's demo data).

## Changing the haircut charge

Prices live in the `services` table now, not hardcoded in the front end.

1. Find the Haircut service's id:
   ```bash
   curl http://127.0.0.1:8000/services
   ```
2. Update its price:
   ```bash
   curl -X PATCH http://127.0.0.1:8000/services/<service_id> \
        -H "Content-Type: application/json" \
        -d '{"price": 500}'
   ```

Every new booking and invoice will use the updated price.

## Endpoints

| Resource | Routes |
|---|---|
| Stylists | `GET/POST /stylists`, `PATCH/DELETE /stylists/{id}` |
| Services | `GET/POST /services`, `PATCH/DELETE /services/{id}` |
| Appointments | `GET/POST /appointments`, `PATCH/DELETE /appointments/{id}` (conflict-checked per stylist) |
| Inventory | `GET/POST /inventory`, `PATCH/DELETE /inventory/{id}`, `POST /inventory/{id}/adjust` (`{"delta": -1}`) |
| Invoices | `GET/POST /invoices` (creating one auto-decrements matching inventory stock) |
| Clients | `GET /clients` (computed from appointment + invoice history) |
| Dashboard | `GET /dashboard` (today's bookings, revenue, low stock, active staff) |

## Connecting the React front end

The API allows all origins by default (`CORSMiddleware`), so the Ada React
artifact can call it directly, e.g.:

```js
const res = await fetch("http://127.0.0.1:8000/appointments?date_=2026-08-19");
const appointments = await res.json();
```

For production, tighten `allow_origins` in `main.py` to your actual front-end
domain, and swap SQLite for Postgres if you need multiple concurrent writers.

## Notes

- Times (`start`, `duration`) are stored as **minutes after midnight** to
  match the front end's calendar grid (e.g. 9:30 AM = 570).
- Tax is a flat 5% GST, applied in `create_invoice`. Change `TAX_RATE` in
  `main.py` if your rate differs.
- This is a single-file app for clarity. If it grows, split into
  `models.py`, `db.py`, and `routers/` per resource.
