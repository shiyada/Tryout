"""
Ada — Salon Management Backend (Flask + PostgreSQL)

Same API as the SQLite version, backed by Postgres via psycopg2.
Mirrors the data model used by the Ada front end: stylists, services,
appointments, inventory, invoices, and a computed clients view built
from appointment + invoice history.

Setup:
    1. Create a database:           createdb ada_salon
    2. Copy .env.example to .env and fill in DATABASE_URL
    3. pip install -r requirements.txt
    4. python main.py

Server starts at http://127.0.0.1:5000
"""

import os
import uuid
from contextlib import contextmanager
from datetime import date

import psycopg2
import psycopg2.extras
from flask import Flask, request, jsonify
from flask_cors import CORS

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional; env vars can be set another way

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/ada_salon"
)
TAX_RATE = 0.05

app = Flask(__name__)
CORS(app)  # allow all origins; tighten in production

# --------------------------------------------------------------------------
# DB setup
# --------------------------------------------------------------------------

@contextmanager
def get_conn():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS stylists (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                role TEXT,
                phone TEXT,
                hours TEXT,
                color TEXT,
                active BOOLEAN DEFAULT TRUE
            );

            CREATE TABLE IF NOT EXISTS services (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                duration INTEGER NOT NULL,   -- minutes
                price NUMERIC NOT NULL
            );

            CREATE TABLE IF NOT EXISTS inventory (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT,
                stock INTEGER DEFAULT 0,
                reorder INTEGER DEFAULT 5,
                price NUMERIC DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS appointments (
                id TEXT PRIMARY KEY,
                date TEXT NOT NULL,          -- YYYY-MM-DD
                stylist_id TEXT NOT NULL REFERENCES stylists(id),
                client TEXT NOT NULL,
                phone TEXT,
                service TEXT NOT NULL,
                start INTEGER NOT NULL,      -- minutes after midnight
                duration INTEGER NOT NULL,
                status TEXT DEFAULT 'booked'
            );

            CREATE TABLE IF NOT EXISTS invoices (
                id TEXT PRIMARY KEY,
                date TEXT NOT NULL,
                client TEXT NOT NULL,
                phone TEXT,
                staff_id TEXT REFERENCES stylists(id),
                subtotal NUMERIC NOT NULL,
                tax NUMERIC NOT NULL,
                total NUMERIC NOT NULL,
                payment TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS invoice_items (
                id SERIAL PRIMARY KEY,
                invoice_id TEXT NOT NULL REFERENCES invoices(id),
                name TEXT NOT NULL,
                qty INTEGER NOT NULL,
                price NUMERIC NOT NULL
            );
            """
        )
        conn.commit()

        cur.execute("SELECT COUNT(*) AS n FROM stylists")
        if cur.fetchone()["n"] == 0:
            seed(conn)


def seed(conn):
    cur = conn.cursor()

    stylists = [
        ("maya", "Maya", "Senior Stylist", "98450 11223", "9:00 AM – 6:00 PM", "#C17A6F", True),
        ("theo", "Theo", "Barber", "97401 55678", "10:00 AM – 7:00 PM", "#7A8B6E", True),
        ("priya", "Priya", "Colorist", "99012 34567", "9:00 AM – 5:00 PM", "#5C7A8A", True),
    ]
    cur.executemany(
        "INSERT INTO stylists (id, name, role, phone, hours, color, active) VALUES (%s,%s,%s,%s,%s,%s,%s)",
        stylists,
    )

    services = [
        ("Haircut", 45, 450),
        ("Blowout", 30, 350),
        ("Beard trim", 20, 200),
        ("Color", 120, 1800),
        ("Balayage", 150, 3200),
        ("Treatment", 60, 900),
    ]
    cur.executemany(
        "INSERT INTO services (id, name, duration, price) VALUES (%s,%s,%s,%s)",
        [(str(uuid.uuid4()), n, d, p) for n, d, p in services],
    )

    inventory = [
        ("Shampoo 250ml", "Retail", 14, 6, 480),
        ("Conditioner 250ml", "Retail", 11, 6, 460),
        ("Argan Oil Serum", "Retail", 4, 5, 690),
        ("Hair Color Tube", "Backbar", 3, 8, 320),
        ("Developer 1L", "Backbar", 9, 4, 380),
        ("Disposable Razors", "Supplies", 22, 10, 20),
        ("Foil Rolls", "Supplies", 2, 5, 250),
    ]
    cur.executemany(
        "INSERT INTO inventory (id, name, category, stock, reorder, price) VALUES (%s,%s,%s,%s,%s,%s)",
        [(str(uuid.uuid4()), *row) for row in inventory],
    )

    today = date.today().isoformat()
    appts = [
        (today, "maya", "Renu Kapoor", "98450 11223", "Balayage", 9 * 60 + 30, 150),
        (today, "theo", "Arvind Shetty", "97401 55678", "Haircut", 10 * 60, 45),
        (today, "priya", "Leela Nair", "99012 34567", "Color", 11 * 60, 120),
        (today, "theo", "Vikram Rao", "90123 88990", "Beard trim", 12 * 60, 20),
        (today, "maya", "Sana Iqbal", "88990 11234", "Blowout", 14 * 60, 30),
    ]
    cur.executemany(
        "INSERT INTO appointments (id, date, stylist_id, client, phone, service, start, duration, status) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s, 'booked')",
        [(str(uuid.uuid4()), *row) for row in appts],
    )
    conn.commit()


def to_dict(row):
    """RealDictRow -> plain dict, with NUMERIC columns coerced to float/int for clean JSON."""
    if row is None:
        return None
    d = dict(row)
    for k, v in d.items():
        if hasattr(v, "__class__") and v.__class__.__name__ == "Decimal":
            f = float(v)
            d[k] = int(f) if f.is_integer() and k in ("stock", "reorder", "qty") else f
    return d


def overlaps(a_start, a_dur, b_start, b_dur):
    return a_start < b_start + b_dur and b_start < a_start + a_dur


def error(message, status=400):
    return jsonify({"error": message}), status


# --------------------------------------------------------------------------
# Stylists
# --------------------------------------------------------------------------

@app.get("/stylists")
def list_stylists():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM stylists ORDER BY name")
        return jsonify([to_dict(r) for r in cur.fetchall()])


@app.post("/stylists")
def create_stylist():
    body = request.get_json(force=True)
    if not body.get("name"):
        return error("'name' is required")
    sid = body.get("id") or str(uuid.uuid4())
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO stylists (id, name, role, phone, hours, color, active) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING *",
            (sid, body["name"], body.get("role", ""), body.get("phone", ""),
             body.get("hours", ""), body.get("color", "#B08D57"), bool(body.get("active", True))),
        )
        return jsonify(to_dict(cur.fetchone())), 201


@app.patch("/stylists/<stylist_id>")
def update_stylist(stylist_id):
    body = request.get_json(force=True)
    allowed = {"name", "role", "phone", "hours", "color", "active"}
    fields = {k: v for k, v in body.items() if k in allowed}
    if not fields:
        return error("No valid fields to update")
    if "active" in fields:
        fields["active"] = bool(fields["active"])
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM stylists WHERE id=%s", (stylist_id,))
        if not cur.fetchone():
            return error("Stylist not found", 404)
        set_clause = ", ".join(f"{k}=%s" for k in fields)
        cur.execute(
            f"UPDATE stylists SET {set_clause} WHERE id=%s RETURNING *",
            (*fields.values(), stylist_id),
        )
        return jsonify(to_dict(cur.fetchone()))


@app.delete("/stylists/<stylist_id>")
def delete_stylist(stylist_id):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM stylists WHERE id=%s", (stylist_id,))
        return "", 204


# --------------------------------------------------------------------------
# Services (this is where you change the haircut charge)
# --------------------------------------------------------------------------

@app.get("/services")
def list_services():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM services ORDER BY name")
        return jsonify([to_dict(r) for r in cur.fetchall()])


@app.post("/services")
def create_service():
    body = request.get_json(force=True)
    if not body.get("name") or "duration" not in body or "price" not in body:
        return error("'name', 'duration', and 'price' are required")
    sid = body.get("id") or str(uuid.uuid4())
    with get_conn() as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO services (id, name, duration, price) VALUES (%s,%s,%s,%s) RETURNING *",
                (sid, body["name"], body["duration"], body["price"]),
            )
        except psycopg2.errors.UniqueViolation:
            return error(f"Service '{body['name']}' already exists", 409)
        return jsonify(to_dict(cur.fetchone())), 201


@app.patch("/services/<service_id>")
def update_service(service_id):
    """e.g. PATCH /services/<id>  body: {"price": 500}  to change the haircut charge."""
    body = request.get_json(force=True)
    allowed = {"name", "duration", "price"}
    fields = {k: v for k, v in body.items() if k in allowed}
    if not fields:
        return error("No valid fields to update")
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM services WHERE id=%s", (service_id,))
        if not cur.fetchone():
            return error("Service not found", 404)
        set_clause = ", ".join(f"{k}=%s" for k in fields)
        cur.execute(
            f"UPDATE services SET {set_clause} WHERE id=%s RETURNING *",
            (*fields.values(), service_id),
        )
        return jsonify(to_dict(cur.fetchone()))


@app.delete("/services/<service_id>")
def delete_service(service_id):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM services WHERE id=%s", (service_id,))
        return "", 204


# --------------------------------------------------------------------------
# Inventory
# --------------------------------------------------------------------------

@app.get("/inventory")
def list_inventory():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM inventory ORDER BY name")
        return jsonify([to_dict(r) for r in cur.fetchall()])


@app.post("/inventory")
def create_inventory_item():
    body = request.get_json(force=True)
    if not body.get("name"):
        return error("'name' is required")
    iid = body.get("id") or str(uuid.uuid4())
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO inventory (id, name, category, stock, reorder, price) "
            "VALUES (%s,%s,%s,%s,%s,%s) RETURNING *",
            (iid, body["name"], body.get("category", "Retail"), body.get("stock", 0),
             body.get("reorder", 5), body.get("price", 0)),
        )
        return jsonify(to_dict(cur.fetchone())), 201


@app.patch("/inventory/<item_id>")
def update_inventory_item(item_id):
    body = request.get_json(force=True)
    allowed = {"name", "category", "stock", "reorder", "price"}
    fields = {k: v for k, v in body.items() if k in allowed}
    if not fields:
        return error("No valid fields to update")
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM inventory WHERE id=%s", (item_id,))
        if not cur.fetchone():
            return error("Inventory item not found", 404)
        set_clause = ", ".join(f"{k}=%s" for k in fields)
        cur.execute(
            f"UPDATE inventory SET {set_clause} WHERE id=%s RETURNING *",
            (*fields.values(), item_id),
        )
        return jsonify(to_dict(cur.fetchone()))


@app.post("/inventory/<item_id>/adjust")
def adjust_stock(item_id):
    body = request.get_json(force=True)
    delta = body.get("delta")
    if delta is None:
        return error("'delta' is required, e.g. {\"delta\": -1}")
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM inventory WHERE id=%s", (item_id,))
        row = cur.fetchone()
        if not row:
            return error("Inventory item not found", 404)
        new_stock = max(0, row["stock"] + int(delta))
        cur.execute(
            "UPDATE inventory SET stock=%s WHERE id=%s RETURNING *", (new_stock, item_id)
        )
        return jsonify(to_dict(cur.fetchone()))


@app.delete("/inventory/<item_id>")
def delete_inventory_item(item_id):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM inventory WHERE id=%s", (item_id,))
        return "", 204


# --------------------------------------------------------------------------
# Appointments
# --------------------------------------------------------------------------

@app.get("/appointments")
def list_appointments():
    date_ = request.args.get("date")
    stylist_id = request.args.get("stylist_id")
    query = "SELECT * FROM appointments WHERE 1=1"
    params = []
    if date_:
        query += " AND date=%s"
        params.append(date_)
    if stylist_id:
        query += " AND stylist_id=%s"
        params.append(stylist_id)
    query += " ORDER BY date, start"
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(query, params)
        return jsonify([to_dict(r) for r in cur.fetchall()])


@app.post("/appointments")
def create_appointment():
    body = request.get_json(force=True)
    required = {"date", "stylist_id", "client", "service", "start", "duration"}
    missing = required - body.keys()
    if missing:
        return error(f"Missing required fields: {', '.join(sorted(missing))}")

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM stylists WHERE id=%s", (body["stylist_id"],))
        if not cur.fetchone():
            return error("Stylist not found", 404)

        cur.execute(
            "SELECT start, duration FROM appointments WHERE date=%s AND stylist_id=%s",
            (body["date"], body["stylist_id"]),
        )
        for c in cur.fetchall():
            if overlaps(body["start"], body["duration"], c["start"], c["duration"]):
                return error("This slot overlaps another booking for that stylist", 409)

        aid = body.get("id") or str(uuid.uuid4())
        cur.execute(
            "INSERT INTO appointments (id, date, stylist_id, client, phone, service, start, duration, status) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *",
            (aid, body["date"], body["stylist_id"], body["client"], body.get("phone", ""),
             body["service"], body["start"], body["duration"], body.get("status", "booked")),
        )
        return jsonify(to_dict(cur.fetchone())), 201


@app.patch("/appointments/<appt_id>")
def update_appointment(appt_id):
    body = request.get_json(force=True)
    allowed = {"date", "stylist_id", "client", "phone", "service", "start", "duration", "status"}
    fields = {k: v for k, v in body.items() if k in allowed}
    if not fields:
        return error("No valid fields to update")

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM appointments WHERE id=%s", (appt_id,))
        existing = cur.fetchone()
        if not existing:
            return error("Appointment not found", 404)

        merged = {**to_dict(existing), **fields}
        cur.execute(
            "SELECT id, start, duration FROM appointments WHERE date=%s AND stylist_id=%s AND id<>%s",
            (merged["date"], merged["stylist_id"], appt_id),
        )
        for c in cur.fetchall():
            if overlaps(merged["start"], merged["duration"], c["start"], c["duration"]):
                return error("This slot overlaps another booking for that stylist", 409)

        set_clause = ", ".join(f"{k}=%s" for k in fields)
        cur.execute(
            f"UPDATE appointments SET {set_clause} WHERE id=%s RETURNING *",
            (*fields.values(), appt_id),
        )
        return jsonify(to_dict(cur.fetchone()))


@app.delete("/appointments/<appt_id>")
def delete_appointment(appt_id):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM appointments WHERE id=%s", (appt_id,))
        return "", 204


# --------------------------------------------------------------------------
# Invoices / billing
# --------------------------------------------------------------------------

@app.get("/invoices")
def list_invoices():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM invoices ORDER BY date DESC")
        invoices = cur.fetchall()
        result = []
        for inv in invoices:
            cur.execute(
                "SELECT name, qty, price FROM invoice_items WHERE invoice_id=%s", (inv["id"],)
            )
            items = cur.fetchall()
            result.append({**to_dict(inv), "items": [to_dict(i) for i in items]})
        return jsonify(result)


@app.post("/invoices")
def create_invoice():
    body = request.get_json(force=True)
    required = {"client", "staff_id", "payment", "items"}
    missing = required - body.keys()
    if missing:
        return error(f"Missing required fields: {', '.join(sorted(missing))}")
    items = body["items"]
    if not items:
        return error("Invoice must have at least one item")
    for it in items:
        if not {"name", "qty", "price"} <= it.keys():
            return error("Each item needs 'name', 'qty', and 'price'")

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM stylists WHERE id=%s", (body["staff_id"],))
        if not cur.fetchone():
            return error("Stylist not found", 404)

        subtotal = sum(it["qty"] * it["price"] for it in items)
        tax = round(subtotal * TAX_RATE, 2)
        total = subtotal + tax
        invoice_id = str(uuid.uuid4())
        today = date.today().isoformat()

        cur.execute(
            "INSERT INTO invoices (id, date, client, phone, staff_id, subtotal, tax, total, payment) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (invoice_id, today, body["client"], body.get("phone", ""), body["staff_id"],
             subtotal, tax, total, body["payment"]),
        )
        for it in items:
            cur.execute(
                "INSERT INTO invoice_items (invoice_id, name, qty, price) VALUES (%s,%s,%s,%s)",
                (invoice_id, it["name"], it["qty"], it["price"]),
            )
            cur.execute(
                "UPDATE inventory SET stock = GREATEST(0, stock - %s) WHERE name = %s",
                (it["qty"], it["name"]),
            )

        return jsonify({
            "id": invoice_id,
            "date": today,
            "client": body["client"],
            "phone": body.get("phone", ""),
            "staff_id": body["staff_id"],
            "subtotal": float(subtotal),
            "tax": float(tax),
            "total": float(total),
            "payment": body["payment"],
            "items": items,
        }), 201


# --------------------------------------------------------------------------
# Clients (computed)
# --------------------------------------------------------------------------

@app.get("/clients")
def list_clients():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT client, phone, date FROM appointments")
        appts = cur.fetchall()
        cur.execute("SELECT client, phone, date, total FROM invoices")
        invs = cur.fetchall()

        clients = {}

        def touch(name, phone):
            key = name.strip().lower()
            if key not in clients:
                clients[key] = {"name": name, "phone": phone or "", "visits": 0, "spent": 0.0, "last_visit": None}
            return clients[key]

        for a in appts:
            c = touch(a["client"], a["phone"])
            c["visits"] += 1
            if not c["last_visit"] or a["date"] > c["last_visit"]:
                c["last_visit"] = a["date"]

        for i in invs:
            c = touch(i["client"], i["phone"])
            c["spent"] += float(i["total"])
            if not c["last_visit"] or i["date"] > c["last_visit"]:
                c["last_visit"] = i["date"]

        return jsonify(sorted(clients.values(), key=lambda c: c["last_visit"] or "", reverse=True))


# --------------------------------------------------------------------------
# Dashboard summary
# --------------------------------------------------------------------------

@app.get("/dashboard")
def dashboard():
    today = date.today().isoformat()
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM appointments WHERE date=%s ORDER BY start", (today,))
        todays_appts = cur.fetchall()

        cur.execute("SELECT COALESCE(SUM(total),0) AS rev FROM invoices WHERE date=%s", (today,))
        todays_revenue = float(cur.fetchone()["rev"])

        cur.execute("SELECT * FROM inventory WHERE stock <= reorder")
        low_stock = cur.fetchall()

        cur.execute("SELECT COUNT(*) AS n FROM stylists WHERE active=TRUE")
        active_staff = cur.fetchone()["n"]

        return jsonify({
            "date": today,
            "todays_bookings": len(todays_appts),
            "todays_revenue": todays_revenue,
            "low_stock_count": len(low_stock),
            "low_stock_items": [to_dict(r) for r in low_stock],
            "active_staff": active_staff,
            "upcoming_today": [to_dict(r) for r in todays_appts],
        })


@app.get("/")
def root():
    return jsonify({"service": "Ada Salon API (Flask + PostgreSQL)", "status": "ok"})


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
