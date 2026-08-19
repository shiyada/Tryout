"""
Ada — Salon Management Backend
FastAPI + SQLite. Mirrors the data model used by the Ada React front end:
stylists, services, appointments, inventory, invoices, and a computed
clients view built from appointment + invoice history.

Run:
    pip install -r requirements.txt
    uvicorn main:app --reload

Docs (interactive):
    http://127.0.0.1:8000/docs
"""

import sqlite3
import time
import uuid
from contextlib import contextmanager
from datetime import date, timedelta
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

DB_PATH = "ada_salon.db"
TAX_RATE = 0.05

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

        # Seed only if empty, so re-running the server doesn't duplicate data.
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


# --------------------------------------------------------------------------
# Schemas
# --------------------------------------------------------------------------

class Stylist(BaseModel):
    id: Optional[str] = None
    name: str
    role: Optional[str] = ""
    phone: Optional[str] = ""
    hours: Optional[str] = ""
    color: str = "#B08D57"
    active: bool = True


class StylistPatch(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    phone: Optional[str] = None
    hours: Optional[str] = None
    color: Optional[str] = None
    active: Optional[bool] = None


class Service(BaseModel):
    id: Optional[str] = None
    name: str
    duration: int = Field(gt=0, description="Minutes")
    price: float = Field(ge=0)


class ServicePatch(BaseModel):
    name: Optional[str] = None
    duration: Optional[int] = None
    price: Optional[float] = None


class InventoryItem(BaseModel):
    id: Optional[str] = None
    name: str
    category: str = "Retail"
    stock: int = 0
    reorder: int = 5
    price: float = 0


class InventoryPatch(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    stock: Optional[int] = None
    reorder: Optional[int] = None
    price: Optional[float] = None


class StockAdjust(BaseModel):
    delta: int


class Appointment(BaseModel):
    id: Optional[str] = None
    date: str
    stylist_id: str
    client: str
    phone: Optional[str] = ""
    service: str
    start: int  # minutes after midnight
    duration: int
    status: str = "booked"


class AppointmentPatch(BaseModel):
    date: Optional[str] = None
    stylist_id: Optional[str] = None
    client: Optional[str] = None
    phone: Optional[str] = None
    service: Optional[str] = None
    start: Optional[int] = None
    duration: Optional[int] = None
    status: Optional[str] = None


class InvoiceItemIn(BaseModel):
    name: str
    qty: int = Field(gt=0)
    price: float = Field(ge=0)


class InvoiceIn(BaseModel):
    client: str
    phone: Optional[str] = ""
    staff_id: str
    payment: str
    items: List[InvoiceItemIn]


# --------------------------------------------------------------------------
# App
# --------------------------------------------------------------------------

app = FastAPI(title="Ada Salon API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this to your front-end origin in production
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


def row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row)


def overlaps(a_start, a_dur, b_start, b_dur):
    return a_start < b_start + b_dur and b_start < a_start + a_dur


# ---- stylists --------------------------------------------------------------

@app.get("/stylists")
def list_stylists():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM stylists ORDER BY name").fetchall()
        return [row_to_dict(r) for r in rows]


@app.post("/stylists", status_code=201)
def create_stylist(s: Stylist):
    sid = s.id or str(uuid.uuid4())
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO stylists (id, name, role, phone, hours, color, active) VALUES (?,?,?,?,?,?,?)",
            (sid, s.name, s.role, s.phone, s.hours, s.color, int(s.active)),
        )
    return {**s.dict(), "id": sid}


@app.patch("/stylists/{stylist_id}")
def update_stylist(stylist_id: str, patch: StylistPatch):
    fields = {k: v for k, v in patch.dict(exclude_unset=True).items()}
    if not fields:
        raise HTTPException(400, "No fields to update")
    if "active" in fields:
        fields["active"] = int(fields["active"])
    with get_conn() as conn:
        existing = conn.execute("SELECT * FROM stylists WHERE id=?", (stylist_id,)).fetchone()
        if not existing:
            raise HTTPException(404, "Stylist not found")
        set_clause = ", ".join(f"{k}=?" for k in fields)
        conn.execute(f"UPDATE stylists SET {set_clause} WHERE id=?", (*fields.values(), stylist_id))
        return row_to_dict(conn.execute("SELECT * FROM stylists WHERE id=?", (stylist_id,)).fetchone())


@app.delete("/stylists/{stylist_id}", status_code=204)
def delete_stylist(stylist_id: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM stylists WHERE id=?", (stylist_id,))


# ---- services (this is where you change the haircut charge) ---------------

@app.get("/services")
def list_services():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM services ORDER BY name").fetchall()
        return [row_to_dict(r) for r in rows]


@app.post("/services", status_code=201)
def create_service(s: Service):
    sid = s.id or str(uuid.uuid4())
    with get_conn() as conn:
        try:
            conn.execute(
                "INSERT INTO services (id, name, duration, price) VALUES (?,?,?,?)",
                (sid, s.name, s.duration, s.price),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(409, f"Service '{s.name}' already exists")
    return {**s.dict(), "id": sid}


@app.patch("/services/{service_id}")
def update_service(service_id: str, patch: ServicePatch):
    """e.g. PATCH /services/{id}  body: {"price": 500}  to change the haircut charge."""
    fields = {k: v for k, v in patch.dict(exclude_unset=True).items()}
    if not fields:
        raise HTTPException(400, "No fields to update")
    with get_conn() as conn:
        existing = conn.execute("SELECT * FROM services WHERE id=?", (service_id,)).fetchone()
        if not existing:
            raise HTTPException(404, "Service not found")
        set_clause = ", ".join(f"{k}=?" for k in fields)
        conn.execute(f"UPDATE services SET {set_clause} WHERE id=?", (*fields.values(), service_id))
        return row_to_dict(conn.execute("SELECT * FROM services WHERE id=?", (service_id,)).fetchone())


@app.delete("/services/{service_id}", status_code=204)
def delete_service(service_id: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM services WHERE id=?", (service_id,))


# ---- inventory --------------------------------------------------------------

@app.get("/inventory")
def list_inventory():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM inventory ORDER BY name").fetchall()
        return [row_to_dict(r) for r in rows]


@app.post("/inventory", status_code=201)
def create_inventory_item(item: InventoryItem):
    iid = item.id or str(uuid.uuid4())
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO inventory (id, name, category, stock, reorder, price) VALUES (?,?,?,?,?,?)",
            (iid, item.name, item.category, item.stock, item.reorder, item.price),
        )
    return {**item.dict(), "id": iid}


@app.patch("/inventory/{item_id}")
def update_inventory_item(item_id: str, patch: InventoryPatch):
    fields = {k: v for k, v in patch.dict(exclude_unset=True).items()}
    if not fields:
        raise HTTPException(400, "No fields to update")
    with get_conn() as conn:
        existing = conn.execute("SELECT * FROM inventory WHERE id=?", (item_id,)).fetchone()
        if not existing:
            raise HTTPException(404, "Inventory item not found")
        set_clause = ", ".join(f"{k}=?" for k in fields)
        conn.execute(f"UPDATE inventory SET {set_clause} WHERE id=?", (*fields.values(), item_id))
        return row_to_dict(conn.execute("SELECT * FROM inventory WHERE id=?", (item_id,)).fetchone())


@app.post("/inventory/{item_id}/adjust")
def adjust_stock(item_id: str, adj: StockAdjust):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM inventory WHERE id=?", (item_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Inventory item not found")
        new_stock = max(0, row["stock"] + adj.delta)
        conn.execute("UPDATE inventory SET stock=? WHERE id=?", (new_stock, item_id))
        return row_to_dict(conn.execute("SELECT * FROM inventory WHERE id=?", (item_id,)).fetchone())


@app.delete("/inventory/{item_id}", status_code=204)
def delete_inventory_item(item_id: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM inventory WHERE id=?", (item_id,))


# ---- appointments -----------------------------------------------------------

@app.get("/appointments")
def list_appointments(date_: Optional[str] = None, stylist_id: Optional[str] = None):
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
        return [row_to_dict(r) for r in rows]


@app.post("/appointments", status_code=201)
def create_appointment(a: Appointment):
    with get_conn() as conn:
        stylist = conn.execute("SELECT id FROM stylists WHERE id=?", (a.stylist_id,)).fetchone()
        if not stylist:
            raise HTTPException(404, "Stylist not found")

        clashes = conn.execute(
            "SELECT start, duration FROM appointments WHERE date=? AND stylist_id=?",
            (a.date, a.stylist_id),
        ).fetchall()
        for c in clashes:
            if overlaps(a.start, a.duration, c["start"], c["duration"]):
                raise HTTPException(409, "This slot overlaps another booking for that stylist")

        aid = a.id or str(uuid.uuid4())
        conn.execute(
            "INSERT INTO appointments (id, date, stylist_id, client, phone, service, start, duration, status) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (aid, a.date, a.stylist_id, a.client, a.phone, a.service, a.start, a.duration, a.status),
        )
    return {**a.dict(), "id": aid}


@app.patch("/appointments/{appt_id}")
def update_appointment(appt_id: str, patch: AppointmentPatch):
    fields = {k: v for k, v in patch.dict(exclude_unset=True).items()}
    if not fields:
        raise HTTPException(400, "No fields to update")
    with get_conn() as conn:
        existing = conn.execute("SELECT * FROM appointments WHERE id=?", (appt_id,)).fetchone()
        if not existing:
            raise HTTPException(404, "Appointment not found")

        merged = {**row_to_dict(existing), **fields}
        clashes = conn.execute(
            "SELECT id, start, duration FROM appointments WHERE date=? AND stylist_id=? AND id<>?",
            (merged["date"], merged["stylist_id"], appt_id),
        ).fetchall()
        for c in clashes:
            if overlaps(merged["start"], merged["duration"], c["start"], c["duration"]):
                raise HTTPException(409, "This slot overlaps another booking for that stylist")

        set_clause = ", ".join(f"{k}=?" for k in fields)
        conn.execute(f"UPDATE appointments SET {set_clause} WHERE id=?", (*fields.values(), appt_id))
        return row_to_dict(conn.execute("SELECT * FROM appointments WHERE id=?", (appt_id,)).fetchone())


@app.delete("/appointments/{appt_id}", status_code=204)
def delete_appointment(appt_id: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM appointments WHERE id=?", (appt_id,))


# ---- invoices / billing -----------------------------------------------------

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
        return result


@app.post("/invoices", status_code=201)
def create_invoice(inv: InvoiceIn):
    with get_conn() as conn:
        staff = conn.execute("SELECT id FROM stylists WHERE id=?", (inv.staff_id,)).fetchone()
        if not staff:
            raise HTTPException(404, "Stylist not found")
        if not inv.items:
            raise HTTPException(400, "Invoice must have at least one item")

        subtotal = sum(i.qty * i.price for i in inv.items)
        tax = round(subtotal * TAX_RATE, 2)
        total = subtotal + tax
        invoice_id = str(uuid.uuid4())

        conn.execute(
            "INSERT INTO invoices (id, date, client, phone, staff_id, subtotal, tax, total, payment) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (invoice_id, date.today().isoformat(), inv.client, inv.phone, inv.staff_id, subtotal, tax, total, inv.payment),
        )
        for item in inv.items:
            conn.execute(
                "INSERT INTO invoice_items (invoice_id, name, qty, price) VALUES (?,?,?,?)",
                (invoice_id, item.name, item.qty, item.price),
            )
            # decrement matching inventory stock, if the item is a stocked product
            conn.execute(
                "UPDATE inventory SET stock = MAX(0, stock - ?) WHERE name = ?",
                (item.qty, item.name),
            )

        return {
            "id": invoice_id,
            "date": date.today().isoformat(),
            "client": inv.client,
            "phone": inv.phone,
            "staff_id": inv.staff_id,
            "subtotal": subtotal,
            "tax": tax,
            "total": total,
            "payment": inv.payment,
            "items": [i.dict() for i in inv.items],
        }


# ---- clients (computed) ------------------------------------------------------

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

        return sorted(clients.values(), key=lambda c: c["last_visit"] or "", reverse=True)


# ---- dashboard summary --------------------------------------------------------

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

        return {
            "date": today,
            "todays_bookings": len(todays_appts),
            "todays_revenue": todays_revenue,
            "low_stock_count": len(low_stock),
            "low_stock_items": [row_to_dict(r) for r in low_stock],
            "active_staff": active_staff,
            "upcoming_today": [row_to_dict(r) for r in todays_appts],
        }


@app.get("/")
def root():
    return {"service": "Ada Salon API", "status": "ok", "docs": "/docs"}
