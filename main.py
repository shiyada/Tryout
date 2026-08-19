"""
Ada — Salon Management Backend (Flask)
Flask + SQLite. Mirrors the data model used by the Ada React front end:
stylists, services, appointments, inventory, invoices, and a computed
clients view built from appointment + invoice history.

Run:
    pip install -r requirements.txt
    python main.py

Server starts at http://127.0.0.1:5000
"""

import sqlite3
import uuid
from contextlib import contextmanager
from datetime import date

from flask import Flask, request, jsonify
from flask_cors import CORS

DB_PATH = "ada_salon.db"
TAX_RATE = 0.05

app = Flask(__name__)
CORS(app)  # allow all origins; tighten in production

# --------------------------------------------------------------------------
# DB setup
# --------------------------------------------------------------------------

@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS stylists (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                role TEXT,
                phone TEXT,
                hours TEXT,
                color TEXT,
                active INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS services (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                duration INTEGER NOT NULL,   -- minutes
                price REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS inventory (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT,
                stock INTEGER DEFAULT 0,
                reorder INTEGER DEFAULT 5,
                price REAL DEFAULT 0
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
                subtotal REAL NOT NULL,
                tax REAL NOT NULL,
                total REAL NOT NULL,
                payment TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS invoice_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id TEXT NOT NULL REFERENCES invoices(id),
                name TEXT NOT NULL,
                qty INTEGER NOT NULL,
                price REAL NOT NULL
            );
            """
        )

        if conn.execute("SELECT COUNT(*) FROM stylists").fetchone()[0] == 0:
            seed(conn)


def seed(conn):
    stylists = [
        ("maya", "Maya", "Senior Stylist", "98450 11223", "9:00 AM – 6:00 PM", "#C17A6F", 1),
        ("theo", "Theo", "Barber", "97401 55678", "10:00 AM – 7:00 PM", "#7A8B6E", 1),
        ("priya", "Priya", "Colorist", "99012 34567", "9:00 AM – 5:00 PM", "#5C7A8A", 1),
    ]
    conn.executemany(
        "INSERT INTO stylists (id, name, role, phone, hours, color, active) VALUES (?,?,?,?,?,?,?)",
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
    conn.executemany(
        "INSERT INTO services (id, name, duration, price) VALUES (?,?,?,?)",
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
    conn.executemany(
        "INSERT INTO inventory (id, name, category, stock, reorder, price) VALUES (?,?,?,?,?,?)",
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
    conn.executemany(
        "INSERT INTO appointments (id, date, stylist_id, client, phone, service, start, duration, status) "
        "VALUES (?,?,?,?,?,?,?,?, 'booked')",
        [(str(uuid.uuid4()), *row) for row in appts],
    )


def row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row)


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
        rows = conn.execute("SELECT * FROM stylists ORDER BY name").fetchall()
        return jsonify([row_to_dict(r) for r in rows])


@app.post("/stylists")
def create_stylist():
    body = request.get_json(force=True)
    if not body.get("name"):
        return error("'name' is required")
    sid = body.get("id") or str(uuid.uuid4())
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO stylists (id, name, role, phone, hours, color, active) VALUES (?,?,?,?,?,?,?)",
            (sid, body["name"], body.get("role", ""), body.get("phone", ""),
             body.get("hours", ""), body.get("color", "#B08D57"), int(body.get("active", True))),
        )
        return jsonify(row_to_dict(conn.execute("SELECT * FROM stylists WHERE id=?", (sid,)).fetchone())), 201


@app.patch("/stylists/<stylist_id>")
def update_stylist(stylist_id):
    body = request.get_json(force=True)
    allowed = {"name", "role", "phone", "hours", "color", "active"}
    fields = {k: v for k, v in body.items() if k in allowed}
    if not fields:
        return error("No valid fields to update")
    if "active" in fields:
        fields["active"] = int(fields["active"])
    with get_conn() as conn:
        existing = conn.execute("SELECT * FROM stylists WHERE id=?", (stylist_id,)).fetchone()
        if not existing:
            return error("Stylist not found", 404)
        set_clause = ", ".join(f"{k}=?" for k in fields)
        conn.execute(f"UPDATE stylists SET {set_clause} WHERE id=?", (*fields.values(), stylist_id))
        return jsonify(row_to_dict(conn.execute("SELECT * FROM stylists WHERE id=?", (stylist_id,)).fetchone()))


@app.delete("/stylists/<stylist_id>")
def delete_stylist(stylist_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM stylists WHERE id=?", (stylist_id,))
        return "", 204


# --------------------------------------------------------------------------
# Services (this is where you change the haircut charge)
# --------------------------------------------------------------------------

@app.get("/services")
def list_services():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM services ORDER BY name").fetchall()
        return jsonify([row_to_dict(r) for r in rows])


@app.post("/services")
def create_service():
    body = request.get_json(force=True)
    if not body.get("name") or "duration" not in body or "price" not in body:
        return error("'name', 'duration', and 'price' are required")
    sid = body.get("id") or str(uuid.uuid4())
    with get_conn() as conn:
        try:
            conn.execute(
                "INSERT INTO services (id, name, duration, price) VALUES (?,?,?,?)",
                (sid, body["name"], body["duration"], body["price"]),
            )
        except sqlite3.IntegrityError:
            return error(f"Service '{body['name']}' already exists", 409)
        return jsonify(row_to_dict(conn.execute("SELECT * FROM services WHERE id=?", (sid,)).fetchone())), 201


@app.patch("/services/<service_id>")
def update_service(service_id):
    """e.g. PATCH /services/<id>  body: {"price": 500}  to change the haircut charge."""
    body = request.get_json(force=True)
    allowed = {"name", "duration", "price"}
    fields = {k: v for k, v in body.items() if k in allowed}
    if not fields:
        return error("No valid fields to update")
    with get_conn() as conn:
        existing = conn.execute("SELECT * FROM services WHERE id=?", (service_id,)).fetchone()
        if not existing:
            return error("Service not found", 404)
        set_clause = ", ".join(f"{k}=?" for k in fields)
        conn.execute(f"UPDATE services SET {set_clause} WHERE id=?", (*fields.values(), service_id))
        return jsonify(row_to_dict(conn.execute("SELECT * FROM services WHERE id=?", (service_id,)).fetchone()))


@app.delete("/services/<service_id>")
def delete_service(service_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM services WHERE id=?", (service_id,))
        return "", 204


# --------------------------------------------------------------------------
# Inventory
# --------------------------------------------------------------------------

@app.get("/inventory")
def list_inventory():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM inventory ORDER BY name").fetchall()
        return jsonify([row_to_dict(r) for r in rows])


@app.post("/inventory")
def create_inventory_item():
    body = request.get_json(force=True)
    if not body.get("name"):
        return error("'name' is required")
    iid = body.get("id") or str(uuid.uuid4())
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO inventory (id, name, category, stock, reorder, price) VALUES (?,?,?,?,?,?)",
            (iid, body["name"], body.get("category", "Retail"), body.get("stock", 0),
             body.get("reorder", 5), body.get("price", 0)),
        )
        return jsonify(row_to_dict(conn.execute("SELECT * FROM inventory WHERE id=?", (iid,)).fetchone())), 201


@app.patch("/inventory/<item_id>")
def update_inventory_item(item_id):
    body = request.get_json(force=True)
    allowed = {"name", "category", "stock", "reorder", "price"}
    fields = {k: v for k, v in body.items() if k in allowed}
    if not fields:
        return error("No valid fields to update")
    with get_conn() as conn:
        existing = conn.execute("SELECT * FROM inventory WHERE id=?", (item_id,)).fetchone()
        if not existing:
            return error("Inventory item not found", 404)
        set_clause = ", ".join(f"{k}=?" for k in fields)
        conn.execute(f"UPDATE inventory SET {set_clause} WHERE id=?", (*fields.values(), item_id))
        return jsonify(row_to_dict(conn.execute("SELECT * FROM inventory WHERE id=?", (item_id,)).fetchone()))


@app.post("/inventory/<item_id>/adjust")
def adjust_stock(item_id):
    body = request.get_json(force=True)
    delta = body.get("delta")
    if delta is None:
        return error("'delta' is required, e.g. {\"delta\": -1}")
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM inventory WHERE id=?", (item_id,)).fetchone()
        if not row:
            return error("Inventory item not found", 404)
        new_stock = max(0, row["stock"] + int(delta))
        conn.execute("UPDATE inventory SET stock=? WHERE id=?", (new_stock, item_id))
        return jsonify(row_to_dict(conn.execute("SELECT * FROM inventory WHERE id=?", (item_id,)).fetchone()))


@app.delete("/inventory/<item_id>")
def delete_inventory_item(item_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM inventory WHERE id=?", (item_id,))
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
        query += " AND date=?"
        params.append(date_)
    if stylist_id:
        query += " AND stylist_id=?"
        params.append(stylist_id)
    query += " ORDER BY date, start"
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
        return jsonify([row_to_dict(r) for r in rows])


@app.post("/appointments")
def create_appointment():
    body = request.get_json(force=True)
    required = {"date", "stylist_id", "client", "service", "start", "duration"}
    missing = required - body.keys()
    if missing:
        return error(f"Missing required fields: {', '.join(sorted(missing))}")

    with get_conn() as conn:
        stylist = conn.execute("SELECT id FROM stylists WHERE id=?", (body["stylist_id"],)).fetchone()
        if not stylist:
            return error("Stylist not found", 404)

        clashes = conn.execute(
            "SELECT start, duration FROM appointments WHERE date=? AND stylist_id=?",
            (body["date"], body["stylist_id"]),
        ).fetchall()
        for c in clashes:
            if overlaps(body["start"], body["duration"], c["start"], c["duration"]):
                return error("This slot overlaps another booking for that stylist", 409)

        aid = body.get("id") or str(uuid.uuid4())
        conn.execute(
            "INSERT INTO appointments (id, date, stylist_id, client, phone, service, start, duration, status) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (aid, body["date"], body["stylist_id"], body["client"], body.get("phone", ""),
             body["service"], body["start"], body["duration"], body.get("status", "booked")),
        )
        return jsonify(row_to_dict(conn.execute("SELECT * FROM appointments WHERE id=?", (aid,)).fetchone())), 201


@app.patch("/appointments/<appt_id>")
def update_appointment(appt_id):
    body = request.get_json(force=True)
    allowed = {"date", "stylist_id", "client", "phone", "service", "start", "duration", "status"}
    fields = {k: v for k, v in body.items() if k in allowed}
    if not fields:
        return error("No valid fields to update")

    with get_conn() as conn:
        existing = conn.execute("SELECT * FROM appointments WHERE id=?", (appt_id,)).fetchone()
        if not existing:
            return error("Appointment not found", 404)

        merged = {**row_to_dict(existing), **fields}
        clashes = conn.execute(
            "SELECT id, start, duration FROM appointments WHERE date=? AND stylist_id=? AND id<>?",
            (merged["date"], merged["stylist_id"], appt_id),
        ).fetchall()
        for c in clashes:
            if overlaps(merged["start"], merged["duration"], c["start"], c["duration"]):
                return error("This slot overlaps another booking for that stylist", 409)

        set_clause = ", ".join(f"{k}=?" for k in fields)
        conn.execute(f"UPDATE appointments SET {set_clause} WHERE id=?", (*fields.values(), appt_id))
        return jsonify(row_to_dict(conn.execute("SELECT * FROM appointments WHERE id=?", (appt_id,)).fetchone()))


@app.delete("/appointments/<appt_id>")
def delete_appointment(appt_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM appointments WHERE id=?", (appt_id,))
        return "", 204


# --------------------------------------------------------------------------
# Invoices / billing
# --------------------------------------------------------------------------

@app.get("/invoices")
def list_invoices():
    with get_conn() as conn:
        invoices = conn.execute("SELECT * FROM invoices ORDER BY date DESC").fetchall()
        result = []
        for inv in invoices:
            items = conn.execute(
                "SELECT name, qty, price FROM invoice_items WHERE invoice_id=?", (inv["id"],)
            ).fetchall()
            result.append({**row_to_dict(inv), "items": [row_to_dict(i) for i in items]})
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
        staff = conn.execute("SELECT id FROM stylists WHERE id=?", (body["staff_id"],)).fetchone()
        if not staff:
            return error("Stylist not found", 404)

        subtotal = sum(it["qty"] * it["price"] for it in items)
        tax = round(subtotal * TAX_RATE, 2)
        total = subtotal + tax
        invoice_id = str(uuid.uuid4())
        today = date.today().isoformat()

        conn.execute(
            "INSERT INTO invoices (id, date, client, phone, staff_id, subtotal, tax, total, payment) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (invoice_id, today, body["client"], body.get("phone", ""), body["staff_id"],
             subtotal, tax, total, body["payment"]),
        )
        for it in items:
            conn.execute(
                "INSERT INTO invoice_items (invoice_id, name, qty, price) VALUES (?,?,?,?)",
                (invoice_id, it["name"], it["qty"], it["price"]),
            )
            conn.execute(
                "UPDATE inventory SET stock = MAX(0, stock - ?) WHERE name = ?",
                (it["qty"], it["name"]),
            )

        return jsonify({
            "id": invoice_id,
            "date": today,
            "client": body["client"],
            "phone": body.get("phone", ""),
            "staff_id": body["staff_id"],
            "subtotal": subtotal,
            "tax": tax,
            "total": total,
            "payment": body["payment"],
            "items": items,
        }), 201


# --------------------------------------------------------------------------
# Clients (computed)
# --------------------------------------------------------------------------

@app.get("/clients")
def list_clients():
    with get_conn() as conn:
        appts = conn.execute("SELECT client, phone, date FROM appointments").fetchall()
        invs = conn.execute("SELECT client, phone, date, total FROM invoices").fetchall()

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
            c["spent"] += i["total"]
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
        todays_appts = conn.execute(
            "SELECT * FROM appointments WHERE date=? ORDER BY start", (today,)
        ).fetchall()
        todays_revenue = conn.execute(
            "SELECT COALESCE(SUM(total),0) AS rev FROM invoices WHERE date=?", (today,)
        ).fetchone()["rev"]
        low_stock = conn.execute("SELECT * FROM inventory WHERE stock <= reorder").fetchall()
        active_staff = conn.execute("SELECT COUNT(*) AS n FROM stylists WHERE active=1").fetchone()["n"]

        return jsonify({
            "date": today,
            "todays_bookings": len(todays_appts),
            "todays_revenue": todays_revenue,
            "low_stock_count": len(low_stock),
            "low_stock_items": [row_to_dict(r) for r in low_stock],
            "active_staff": active_staff,
            "upcoming_today": [row_to_dict(r) for r in todays_appts],
        })


@app.get("/")
def root():
    return jsonify({"service": "Ada Salon API (Flask)", "status": "ok"})


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
