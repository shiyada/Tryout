import React, { useState, useMemo } from "react";
import {
  LayoutDashboard, CalendarDays, Users, UserRound, Receipt, Package,
  Plus, X, Search, Phone, ChevronLeft, ChevronRight, AlertTriangle,
  TrendingUp, Trash2, Minus, CheckCircle2,
} from "lucide-react";

/* ============================= constants ============================= */

const DAY_START = 9 * 60;
const DAY_END = 19 * 60;
const PX_PER_MIN = 1.5;
const GRID_STEP = 30;
const TAX_RATE = 0.05;

const STYLISTS_SEED = [
  { id: "maya", name: "Maya", role: "Senior Stylist", phone: "98450 11223", hours: "9:00 AM – 6:00 PM", color: "#C17A6F", active: true },
  { id: "theo", name: "Theo", role: "Barber", phone: "97401 55678", hours: "10:00 AM – 7:00 PM", color: "#7A8B6E", active: true },
  { id: "priya", name: "Priya", role: "Colorist", phone: "99012 34567", hours: "9:00 AM – 5:00 PM", color: "#5C7A8A", active: true },
];

const SERVICES = [
  { name: "Haircut", duration: 45, price: 450 },
  { name: "Blowout", duration: 30, price: 350 },
  { name: "Beard trim", duration: 20, price: 200 },
  { name: "Color", duration: 120, price: 1800 },
  { name: "Balayage", duration: 150, price: 3200 },
  { name: "Treatment", duration: 60, price: 900 },
];

const INVENTORY_SEED = [
  { id: "p1", name: "Shampoo 250ml", category: "Retail", stock: 14, reorder: 6, price: 480 },
  { id: "p2", name: "Conditioner 250ml", category: "Retail", stock: 11, reorder: 6, price: 460 },
  { id: "p3", name: "Argan Oil Serum", category: "Retail", stock: 4, reorder: 5, price: 690 },
  { id: "p4", name: "Hair Color Tube", category: "Backbar", stock: 3, reorder: 8, price: 320 },
  { id: "p5", name: "Developer 1L", category: "Backbar", stock: 9, reorder: 4, price: 380 },
  { id: "p6", name: "Disposable Razors", category: "Supplies", stock: 22, reorder: 10, price: 20 },
  { id: "p7", name: "Foil Rolls", category: "Supplies", stock: 2, reorder: 5, price: 250 },
];

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}
function isoDaysAgo(n) {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
}

const APPTS_SEED = [
  { id: "a1", date: todayISO(), stylist: "maya", client: "Renu Kapoor", phone: "98450 11223", service: "Balayage", start: 9 * 60 + 30, duration: 150, status: "booked" },
  { id: "a2", date: todayISO(), stylist: "theo", client: "Arvind Shetty", phone: "97401 55678", service: "Haircut", start: 10 * 60, duration: 45, status: "booked" },
  { id: "a3", date: todayISO(), stylist: "priya", client: "Leela Nair", phone: "99012 34567", service: "Color", start: 11 * 60, duration: 120, status: "booked" },
  { id: "a4", date: todayISO(), stylist: "theo", client: "Vikram Rao", phone: "90123 88990", service: "Beard trim", start: 12 * 60, duration: 20, status: "booked" },
  { id: "a5", date: todayISO(), stylist: "maya", client: "Sana Iqbal", phone: "88990 11234", service: "Blowout", start: 14 * 60, duration: 30, status: "booked" },
];

const INVOICES_SEED = [
  { id: "inv1", date: isoDaysAgo(1), client: "Renu Kapoor", phone: "98450 11223", staff: "maya", items: [{ name: "Haircut", qty: 1, price: 450 }], subtotal: 450, tax: 22.5, total: 472.5, payment: "UPI" },
  { id: "inv2", date: isoDaysAgo(2), client: "Vikram Rao", phone: "90123 88990", staff: "theo", items: [{ name: "Beard trim", qty: 1, price: 200 }, { name: "Argan Oil Serum", qty: 1, price: 690 }], subtotal: 890, tax: 44.5, total: 934.5, payment: "Cash" },
  { id: "inv3", date: todayISO(), client: "Sana Iqbal", phone: "88990 11234", staff: "priya", items: [{ name: "Treatment", qty: 1, price: 900 }], subtotal: 900, tax: 45, total: 945, payment: "Card" },
];

const TABS = [
  { id: "dashboard", label: "Overview", icon: LayoutDashboard },
  { id: "book", label: "Calendar", icon: CalendarDays },
  { id: "clients", label: "Clients", icon: Users },
  { id: "staff", label: "Staff", icon: UserRound },
  { id: "billing", label: "Billing", icon: Receipt },
  { id: "inventory", label: "Inventory", icon: Package },
];

/* ============================= helpers ============================= */

function fmtTime(mins) {
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  const period = h >= 12 ? "PM" : "AM";
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return `${h12}:${String(m).padStart(2, "0")} ${period}`;
}
function fmtDateHeading(iso) {
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" });
}
function fmtDateShort(iso) {
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}
function addDaysISO(iso, delta) {
  const d = new Date(iso + "T00:00:00");
  d.setDate(d.getDate() + delta);
  return d.toISOString().slice(0, 10);
}
function overlaps(aStart, aDur, bStart, bDur) {
  const aEnd = aStart + aDur, bEnd = bStart + bDur;
  return aStart < bEnd && bStart < aEnd;
}
function rupee(n) {
  return "₹" + n.toLocaleString("en-IN", { maximumFractionDigits: 0 });
}

/* ============================= root ============================= */

export default function AdaSalon() {
  const [tab, setTab] = useState("dashboard");
  const [appointments, setAppointments] = useState(APPTS_SEED);
  const [stylists, setStylists] = useState(STYLISTS_SEED);
  const [inventory, setInventory] = useState(INVENTORY_SEED);
  const [invoices, setInvoices] = useState(INVOICES_SEED);
  const [extraClients, setExtraClients] = useState([]); // walk-ins added manually with no history yet

  const clients = useMemo(() => buildClients(appointments, invoices, extraClients), [appointments, invoices, extraClients]);

  return (
    <div style={styles.app}>
      <GlobalStyle />
      <TopBar tab={tab} />
      <div style={styles.content}>
        {tab === "dashboard" && (
          <Dashboard
            appointments={appointments}
            invoices={invoices}
            inventory={inventory}
            stylists={stylists}
            goTo={setTab}
          />
        )}
        {tab === "book" && (
          <BookingCalendar appointments={appointments} setAppointments={setAppointments} stylists={stylists} />
        )}
        {tab === "clients" && (
          <Clients clients={clients} setExtraClients={setExtraClients} />
        )}
        {tab === "staff" && <Staff stylists={stylists} setStylists={setStylists} appointments={appointments} />}
        {tab === "billing" && (
          <Billing invoices={invoices} setInvoices={setInvoices} stylists={stylists} inventory={inventory} setInventory={setInventory} />
        )}
        {tab === "inventory" && <Inventory inventory={inventory} setInventory={setInventory} />}
      </div>
      <BottomNav tab={tab} setTab={setTab} />
    </div>
  );
}

function buildClients(appointments, invoices, extraClients) {
  const map = new Map();
  const touch = (name, phone) => {
    const key = name.trim().toLowerCase();
    if (!map.has(key)) map.set(key, { name, phone: phone || "", visits: 0, spent: 0, lastVisit: null });
    return map.get(key);
  };
  appointments.forEach((a) => {
    const c = touch(a.client, a.phone);
    c.visits += 1;
    if (!c.lastVisit || a.date > c.lastVisit) c.lastVisit = a.date;
  });
  invoices.forEach((inv) => {
    const c = touch(inv.client, inv.phone);
    c.spent += inv.total;
    if (!c.lastVisit || inv.date > c.lastVisit) c.lastVisit = inv.date;
  });
  extraClients.forEach((ec) => touch(ec.name, ec.phone));
  return Array.from(map.values()).sort((a, b) => (b.lastVisit || "").localeCompare(a.lastVisit || ""));
}

/* ============================= shared chrome ============================= */

function GlobalStyle() {
  return (
    <style>{`
      @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');
      * { box-sizing: border-box; }
      ::-webkit-scrollbar { width: 8px; height: 8px; }
      ::-webkit-scrollbar-thumb { background: #D8CCB4; border-radius: 4px; }
      button { font-family: inherit; }
      button:focus-visible, [tabindex]:focus-visible, input:focus-visible, select:focus-visible { outline: 2px solid #B08D57; outline-offset: 2px; }
    `}</style>
  );
}

function TopBar({ tab }) {
  const title = TABS.find((t) => t.id === tab)?.label || "";
  return (
    <header style={styles.header}>
      <div style={styles.brandRow}>
        <div style={styles.pinDot} />
        <div>
          <div style={styles.brand}>Ada</div>
          <div style={styles.brandSub}>{title}</div>
        </div>
      </div>
    </header>
  );
}

function BottomNav({ tab, setTab }) {
  return (
    <nav style={styles.bottomNav}>
      {TABS.map((t) => {
        const Icon = t.icon;
        const active = tab === t.id;
        return (
          <button key={t.id} onClick={() => setTab(t.id)} style={{ ...styles.navItem, color: active ? "#1C2333" : "#8A7F68" }}>
            <Icon size={20} strokeWidth={active ? 2.2 : 1.8} />
            <span style={{ ...styles.navLabel, fontWeight: active ? 600 : 500 }}>{t.label}</span>
            {active && <div style={styles.navDot} />}
          </button>
        );
      })}
    </nav>
  );
}

/* ============================= dashboard ============================= */

function Dashboard({ appointments, invoices, inventory, stylists, goTo }) {
  const today = todayISO();
  const todays = appointments.filter((a) => a.date === today).sort((a, b) => a.start - b.start);
  const todaysRevenue = invoices.filter((i) => i.date === today).reduce((s, i) => s + i.total, 0);
  const lowStock = inventory.filter((p) => p.stock <= p.reorder);
  const activeStaff = stylists.filter((s) => s.active).length;

  return (
    <div style={styles.section}>
      <div style={styles.dateHeading}>{fmtDateHeading(today)}</div>

      <div style={styles.statGrid}>
        <StatCard label="Today's bookings" value={todays.length} icon={CalendarDays} onClick={() => goTo("book")} />
        <StatCard label="Today's revenue" value={rupee(todaysRevenue)} icon={TrendingUp} onClick={() => goTo("billing")} />
        <StatCard label="Low stock items" value={lowStock.length} icon={AlertTriangle} warn={lowStock.length > 0} onClick={() => goTo("inventory")} />
        <StatCard label="Active staff" value={activeStaff} icon={UserRound} onClick={() => goTo("staff")} />
      </div>

      <div style={styles.subheading}>Up next</div>
      {todays.length === 0 && <EmptyNote text="Nothing on the books for today yet." />}
      <div style={styles.listStack}>
        {todays.slice(0, 6).map((a) => {
          const st = stylists.find((s) => s.id === a.stylist);
          return (
            <div key={a.id} style={styles.rowCard}>
              <span style={{ ...styles.dotSmall, background: st?.color || "#B08D57" }} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={styles.rowTitle}>{a.client}</div>
                <div style={styles.rowMeta}>{a.service} · {st?.name}</div>
              </div>
              <div style={styles.rowTime}>{fmtTime(a.start)}</div>
            </div>
          );
        })}
      </div>

      {lowStock.length > 0 && (
        <>
          <div style={styles.subheading}>Reorder soon</div>
          <div style={styles.listStack}>
            {lowStock.map((p) => (
              <div key={p.id} style={styles.rowCard}>
                <AlertTriangle size={16} color="#B0453F" />
                <div style={{ flex: 1 }}>
                  <div style={styles.rowTitle}>{p.name}</div>
                  <div style={styles.rowMeta}>{p.category}</div>
                </div>
                <div style={styles.stockBadgeLow}>{p.stock} left</div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function StatCard({ label, value, icon: Icon, warn, onClick }) {
  return (
    <button style={{ ...styles.statCard, borderColor: warn ? "#E4B9B4" : "#E4DAC8" }} onClick={onClick}>
      <Icon size={17} color={warn ? "#B0453F" : "#B08D57"} />
      <div style={styles.statValue}>{value}</div>
      <div style={styles.statLabel}>{label}</div>
    </button>
  );
}

function EmptyNote({ text }) {
  return <div style={styles.emptyNote}>{text}</div>;
}

/* ============================= booking calendar ============================= */

function BookingCalendar({ appointments, setAppointments, stylists }) {
  const [date, setDate] = useState(todayISO());
  const [activeStylist, setActiveStylist] = useState("all");
  const [panel, setPanel] = useState(null);
  const [error, setError] = useState("");

  const visibleStylists = activeStylist === "all" ? stylists : stylists.filter((s) => s.id === activeStylist);
  const dayAppointments = useMemo(() => appointments.filter((a) => a.date === date), [appointments, date]);
  const totalHeight = (DAY_END - DAY_START) * PX_PER_MIN;
  const hourMarks = [];
  for (let t = DAY_START; t <= DAY_END; t += 60) hourMarks.push(t);

  function openNew(stylistId, startMin) {
    setError("");
    setPanel({ mode: "new", id: null, stylist: stylistId, client: "", phone: "", service: SERVICES[0].name, start: startMin, duration: SERVICES[0].duration, status: "booked" });
  }
  function openEdit(appt) {
    setError("");
    setPanel({ mode: "edit", ...appt });
  }
  function closePanel() {
    setPanel(null);
    setError("");
  }
  function saveAppointment() {
    if (!panel.client.trim()) { setError("Add the client's name before saving."); return; }
    const conflict = appointments.some((a) => a.date === date && a.stylist === panel.stylist && a.id !== panel.id && overlaps(a.start, a.duration, panel.start, panel.duration));
    if (conflict) { setError("This slot overlaps another booking for that stylist."); return; }
    if (panel.mode === "new") {
      const { mode, ...rest } = panel;
      setAppointments((prev) => [...prev, { ...rest, id: "a" + Date.now(), date }]);
    } else {
      const { mode, ...rest } = panel;
      setAppointments((prev) => prev.map((a) => (a.id === panel.id ? { ...rest, date } : a)));
    }
    closePanel();
  }
  function deleteAppointment() {
    setAppointments((prev) => prev.filter((a) => a.id !== panel.id));
    closePanel();
  }
  function slotClick(stylistId, e) {
    if (e.target !== e.currentTarget) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const y = e.clientY - rect.top;
    let minutes = DAY_START + Math.round(y / PX_PER_MIN / GRID_STEP) * GRID_STEP;
    minutes = Math.min(Math.max(minutes, DAY_START), DAY_END - 30);
    openNew(stylistId, minutes);
  }

  return (
    <div style={styles.section}>
      <div style={styles.dateNav}>
        <button style={styles.navBtn} onClick={() => setDate((d) => addDaysISO(d, -1))} aria-label="Previous day"><ChevronLeft size={18} /></button>
        <div style={styles.dateLabel}>
          {fmtDateHeading(date)}
          {date !== todayISO() && <button style={styles.todayBtn} onClick={() => setDate(todayISO())}>Today</button>}
        </div>
        <button style={styles.navBtn} onClick={() => setDate((d) => addDaysISO(d, 1))} aria-label="Next day"><ChevronRight size={18} /></button>
      </div>

      <div style={styles.filterRow}>
        <button style={{ ...styles.chip, ...(activeStylist === "all" ? styles.chipActive : {}) }} onClick={() => setActiveStylist("all")}>All chairs</button>
        {stylists.map((s) => (
          <button key={s.id} style={{ ...styles.chip, ...(activeStylist === s.id ? { ...styles.chipActive, borderColor: s.color, color: "#2B2620" } : {}) }} onClick={() => setActiveStylist(s.id)}>
            <span style={{ ...styles.chipDot, background: s.color }} />{s.name}
          </button>
        ))}
        <div style={styles.count}>{dayAppointments.length} booked</div>
      </div>

      <div style={styles.gridWrap}>
        <div style={{ ...styles.gridInner, minHeight: totalHeight + 20 }}>
          <div style={styles.timeRail}>
            {hourMarks.map((t) => (
              <div key={t} style={{ ...styles.hourMark, top: (t - DAY_START) * PX_PER_MIN }}>
                <span style={styles.hourLabel}>{fmtTime(t)}</span>
              </div>
            ))}
          </div>
          <div style={{ ...styles.columns, gridTemplateColumns: `repeat(${visibleStylists.length}, minmax(160px, 1fr))` }}>
            {visibleStylists.map((s) => (
              <div key={s.id} style={styles.column}>
                <div style={{ ...styles.columnHeader, borderBottomColor: s.color }}>
                  <span style={{ ...styles.chipDot, background: s.color }} />{s.name}
                </div>
                <div style={{ ...styles.columnBody, height: totalHeight }} onClick={(e) => slotClick(s.id, e)}>
                  {hourMarks.map((t) => <div key={t} style={{ ...styles.ruleLine, top: (t - DAY_START) * PX_PER_MIN }} />)}
                  {dayAppointments.filter((a) => a.stylist === s.id).map((a) => (
                    <button key={a.id} onClick={(e) => { e.stopPropagation(); openEdit(a); }}
                      style={{ ...styles.slip, top: (a.start - DAY_START) * PX_PER_MIN + 2, height: Math.max(a.duration * PX_PER_MIN - 4, 26), borderLeftColor: s.color }}>
                      <div style={styles.slipClient}>{a.client}</div>
                      <div style={styles.slipMeta}>{a.service} · {fmtTime(a.start)}</div>
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
      <div style={styles.hint}>Tap an empty line to book. Tap a slip to edit or cancel.</div>

      {panel && (
        <SlidePanel title={panel.mode === "new" ? "New booking" : "Edit booking"} onClose={closePanel}>
          <label style={styles.label}>Client name</label>
          <input style={styles.input} value={panel.client} onChange={(e) => setPanel({ ...panel, client: e.target.value })} placeholder="Full name" />
          <label style={styles.label}>Phone</label>
          <input style={styles.input} value={panel.phone} onChange={(e) => setPanel({ ...panel, phone: e.target.value })} placeholder="Optional" />
          <label style={styles.label}>Stylist</label>
          <div style={styles.segRow}>
            {stylists.map((s) => (
              <button key={s.id} style={{ ...styles.segBtn, ...(panel.stylist === s.id ? { background: s.color, color: "#fff", borderColor: s.color } : {}) }} onClick={() => setPanel({ ...panel, stylist: s.id })}>{s.name}</button>
            ))}
          </div>
          <label style={styles.label}>Service</label>
          <div style={styles.segRow}>
            {SERVICES.map((svc) => (
              <button key={svc.name} style={{ ...styles.segBtnSmall, ...(panel.service === svc.name ? styles.segBtnSmallActive : {}) }} onClick={() => setPanel({ ...panel, service: svc.name, duration: svc.duration })}>{svc.name}</button>
            ))}
          </div>
          <div style={styles.row2}>
            <div style={{ flex: 1 }}>
              <label style={styles.label}>Start time</label>
              <select style={styles.select} value={panel.start} onChange={(e) => setPanel({ ...panel, start: Number(e.target.value) })}>
                {Array.from({ length: (DAY_END - DAY_START) / GRID_STEP }).map((_, i) => { const t = DAY_START + i * GRID_STEP; return <option key={t} value={t}>{fmtTime(t)}</option>; })}
              </select>
            </div>
            <div style={{ flex: 1 }}>
              <label style={styles.label}>Duration</label>
              <select style={styles.select} value={panel.duration} onChange={(e) => setPanel({ ...panel, duration: Number(e.target.value) })}>
                {[15, 20, 30, 45, 60, 90, 120, 150, 180].map((d) => <option key={d} value={d}>{d} min</option>)}
              </select>
            </div>
          </div>
          {error && <div style={styles.errorText}>{error}</div>}
          <div style={styles.panelActions}>
            {panel.mode === "edit" && <button style={styles.deleteBtn} onClick={deleteAppointment}>Cancel booking</button>}
            <button style={styles.saveBtn} onClick={saveAppointment}>{panel.mode === "new" ? "Book slot" : "Save changes"}</button>
          </div>
        </SlidePanel>
      )}
    </div>
  );
}

/* ============================= clients ============================= */

function Clients({ clients, setExtraClients }) {
  const [query, setQuery] = useState("");
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState({ name: "", phone: "" });

  const filtered = clients.filter((c) => c.name.toLowerCase().includes(query.toLowerCase()));

  function addClient() {
    if (!form.name.trim()) return;
    setExtraClients((prev) => [...prev, form]);
    setForm({ name: "", phone: "" });
    setAdding(false);
  }

  return (
    <div style={styles.section}>
      <div style={styles.searchRow}>
        <div style={styles.searchBox}>
          <Search size={15} color="#8A7F68" />
          <input style={styles.searchInput} placeholder="Search clients" value={query} onChange={(e) => setQuery(e.target.value)} />
        </div>
        <button style={styles.addBtn} onClick={() => setAdding(true)}><Plus size={18} /></button>
      </div>

      {filtered.length === 0 && <EmptyNote text="No clients match that search." />}

      <div style={styles.listStack}>
        {filtered.map((c) => (
          <div key={c.name} style={styles.clientCard}>
            <div style={styles.avatarCircle}>{c.name.charAt(0).toUpperCase()}</div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={styles.rowTitle}>{c.name}</div>
              <div style={styles.rowMeta}>
                {c.phone && <><Phone size={11} style={{ verticalAlign: "-1px" }} /> {c.phone} · </>}
                {c.visits} visit{c.visits === 1 ? "" : "s"}
              </div>
            </div>
            <div style={styles.clientSpent}>
              <div style={styles.clientSpentValue}>{rupee(c.spent)}</div>
              <div style={styles.clientLast}>{c.lastVisit ? fmtDateShort(c.lastVisit) : "—"}</div>
            </div>
          </div>
        ))}
      </div>

      {adding && (
        <SlidePanel title="Add client" onClose={() => setAdding(false)}>
          <label style={styles.label}>Name</label>
          <input style={styles.input} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Full name" />
          <label style={styles.label}>Phone</label>
          <input style={styles.input} value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="Optional" />
          <div style={styles.panelActions}>
            <button style={styles.saveBtn} onClick={addClient}>Save client</button>
          </div>
        </SlidePanel>
      )}
    </div>
  );
}

/* ============================= staff ============================= */

function Staff({ stylists, setStylists, appointments }) {
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState({ name: "", role: "", phone: "", hours: "", color: "#B08D57" });
  const today = todayISO();
  const palette = ["#C17A6F", "#7A8B6E", "#5C7A8A", "#B08D57", "#9C6ADE"];

  function addStaff() {
    if (!form.name.trim()) return;
    setStylists((prev) => [...prev, { ...form, id: "s" + Date.now(), active: true }]);
    setForm({ name: "", role: "", phone: "", hours: "", color: palette[stylists.length % palette.length] });
    setAdding(false);
  }
  function toggleActive(id) {
    setStylists((prev) => prev.map((s) => (s.id === id ? { ...s, active: !s.active } : s)));
  }

  return (
    <div style={styles.section}>
      <div style={styles.searchRow}>
        <div style={styles.subheading}>{stylists.length} team members</div>
        <button style={styles.addBtn} onClick={() => setAdding(true)}><Plus size={18} /></button>
      </div>

      <div style={styles.listStack}>
        {stylists.map((s) => {
          const bookedToday = appointments.filter((a) => a.stylist === s.id && a.date === today).length;
          return (
            <div key={s.id} style={styles.staffCard}>
              <div style={{ ...styles.avatarCircle, background: s.color }}>{s.name.charAt(0)}</div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={styles.rowTitle}>{s.name} <span style={{ ...styles.roleTag, color: s.color }}>{s.role}</span></div>
                <div style={styles.rowMeta}>{s.hours} · {bookedToday} booked today</div>
              </div>
              <button style={{ ...styles.statusPill, ...(s.active ? styles.statusActive : styles.statusInactive) }} onClick={() => toggleActive(s.id)}>
                {s.active ? "Active" : "Off"}
              </button>
            </div>
          );
        })}
      </div>

      {adding && (
        <SlidePanel title="Add staff member" onClose={() => setAdding(false)}>
          <label style={styles.label}>Name</label>
          <input style={styles.input} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Full name" />
          <label style={styles.label}>Role</label>
          <input style={styles.input} value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} placeholder="e.g. Stylist" />
          <label style={styles.label}>Phone</label>
          <input style={styles.input} value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="Optional" />
          <label style={styles.label}>Working hours</label>
          <input style={styles.input} value={form.hours} onChange={(e) => setForm({ ...form, hours: e.target.value })} placeholder="e.g. 9:00 AM – 6:00 PM" />
          <label style={styles.label}>Chair color</label>
          <div style={styles.segRow}>
            {palette.map((c) => (
              <button key={c} onClick={() => setForm({ ...form, color: c })} style={{ width: 32, height: 32, borderRadius: "50%", background: c, border: form.color === c ? "3px solid #1C2333" : "1px solid #E4DAC8", cursor: "pointer" }} />
            ))}
          </div>
          <div style={styles.panelActions}>
            <button style={styles.saveBtn} onClick={addStaff}>Add to team</button>
          </div>
        </SlidePanel>
      )}
    </div>
  );
}

/* ============================= billing / POS ============================= */

function Billing({ invoices, setInvoices, stylists, inventory, setInventory }) {
  const [checkout, setCheckout] = useState(false);
  const [client, setClient] = useState("");
  const [phone, setPhone] = useState("");
  const [staffId, setStaffId] = useState(stylists[0]?.id || "");
  const [payment, setPayment] = useState("Cash");
  const [items, setItems] = useState([]);

  const subtotal = items.reduce((s, it) => s + it.price * it.qty, 0);
  const tax = Math.round(subtotal * TAX_RATE * 100) / 100;
  const total = subtotal + tax;

  function addItem(name, price) {
    setItems((prev) => {
      const existing = prev.find((it) => it.name === name);
      if (existing) return prev.map((it) => (it.name === name ? { ...it, qty: it.qty + 1 } : it));
      return [...prev, { name, price, qty: 1 }];
    });
  }
  function changeQty(name, delta) {
    setItems((prev) => prev.map((it) => (it.name === name ? { ...it, qty: Math.max(1, it.qty + delta) } : it)).filter((it) => it.qty > 0));
  }
  function removeItem(name) {
    setItems((prev) => prev.filter((it) => it.name !== name));
  }
  function resetCheckout() {
    setClient(""); setPhone(""); setItems([]); setPayment("Cash"); setCheckout(false);
  }
  function completeSale() {
    if (!client.trim() || items.length === 0) return;
    const invoice = { id: "inv" + Date.now(), date: todayISO(), client, phone, staff: staffId, items, subtotal, tax, total, payment };
    setInvoices((prev) => [invoice, ...prev]);
    setInventory((prev) => prev.map((p) => {
      const sold = items.find((it) => it.name === p.name);
      return sold ? { ...p, stock: Math.max(0, p.stock - sold.qty) } : p;
    }));
    resetCheckout();
  }

  return (
    <div style={styles.section}>
      <div style={styles.searchRow}>
        <div style={styles.subheading}>{invoices.length} invoices</div>
        <button style={styles.addBtn} onClick={() => setCheckout(true)}><Plus size={18} /></button>
      </div>

      {invoices.length === 0 && <EmptyNote text="No sales recorded yet." />}
      <div style={styles.listStack}>
        {invoices.map((inv) => {
          const s = stylists.find((st) => st.id === inv.staff);
          return (
            <div key={inv.id} style={styles.rowCard}>
              <Receipt size={16} color="#B08D57" />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={styles.rowTitle}>{inv.client}</div>
                <div style={styles.rowMeta}>{fmtDateShort(inv.date)} · {s?.name || "—"} · {inv.payment} · {inv.items.length} item{inv.items.length === 1 ? "" : "s"}</div>
              </div>
              <div style={styles.clientSpentValue}>{rupee(inv.total)}</div>
            </div>
          );
        })}
      </div>

      {checkout && (
        <SlidePanel title="New sale" onClose={resetCheckout}>
          <label style={styles.label}>Client name</label>
          <input style={styles.input} value={client} onChange={(e) => setClient(e.target.value)} placeholder="Full name" />
          <label style={styles.label}>Phone</label>
          <input style={styles.input} value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="Optional" />
          <label style={styles.label}>Stylist</label>
          <div style={styles.segRow}>
            {stylists.map((s) => (
              <button key={s.id} style={{ ...styles.segBtn, ...(staffId === s.id ? { background: s.color, color: "#fff", borderColor: s.color } : {}) }} onClick={() => setStaffId(s.id)}>{s.name}</button>
            ))}
          </div>

          <label style={styles.label}>Services</label>
          <div style={styles.segRow}>
            {SERVICES.map((svc) => (
              <button key={svc.name} style={styles.segBtnSmall} onClick={() => addItem(svc.name, svc.price)}>{svc.name} · {rupee(svc.price)}</button>
            ))}
          </div>

          <label style={styles.label}>Retail products</label>
          <div style={styles.segRow}>
            {inventory.filter((p) => p.stock > 0).map((p) => (
              <button key={p.id} style={styles.segBtnSmall} onClick={() => addItem(p.name, p.price)}>{p.name} · {rupee(p.price)}</button>
            ))}
          </div>

          {items.length > 0 && (
            <>
              <label style={styles.label}>Cart</label>
              <div style={styles.cartStack}>
                {items.map((it) => (
                  <div key={it.name} style={styles.cartRow}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={styles.rowTitle}>{it.name}</div>
                      <div style={styles.rowMeta}>{rupee(it.price)} each</div>
                    </div>
                    <button style={styles.qtyBtn} onClick={() => changeQty(it.name, -1)}><Minus size={13} /></button>
                    <div style={styles.qtyValue}>{it.qty}</div>
                    <button style={styles.qtyBtn} onClick={() => changeQty(it.name, 1)}><Plus size={13} /></button>
                    <button style={styles.trashBtn} onClick={() => removeItem(it.name)}><Trash2 size={14} /></button>
                  </div>
                ))}
              </div>

              <label style={styles.label}>Payment method</label>
              <div style={styles.segRow}>
                {["Cash", "Card", "UPI"].map((p) => (
                  <button key={p} style={{ ...styles.segBtnSmall, ...(payment === p ? styles.segBtnSmallActive : {}) }} onClick={() => setPayment(p)}>{p}</button>
                ))}
              </div>

              <div style={styles.totalsBox}>
                <div style={styles.totalRow}><span>Subtotal</span><span>{rupee(subtotal)}</span></div>
                <div style={styles.totalRow}><span>GST (5%)</span><span>{rupee(tax)}</span></div>
                <div style={{ ...styles.totalRow, ...styles.totalRowFinal }}><span>Total</span><span>{rupee(total)}</span></div>
              </div>
            </>
          )}

          <div style={styles.panelActions}>
            <button style={styles.saveBtn} onClick={completeSale} disabled={!client.trim() || items.length === 0}>
              <CheckCircle2 size={16} style={{ verticalAlign: "-3px", marginRight: 6 }} />
              Complete sale
            </button>
          </div>
        </SlidePanel>
      )}
    </div>
  );
}

/* ============================= inventory ============================= */

function Inventory({ inventory, setInventory }) {
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState({ name: "", category: "Retail", stock: 0, reorder: 5, price: 0 });

  function adjust(id, delta) {
    setInventory((prev) => prev.map((p) => (p.id === id ? { ...p, stock: Math.max(0, p.stock + delta) } : p)));
  }
  function addProduct() {
    if (!form.name.trim()) return;
    setInventory((prev) => [...prev, { ...form, id: "p" + Date.now(), stock: Number(form.stock), reorder: Number(form.reorder), price: Number(form.price) }]);
    setForm({ name: "", category: "Retail", stock: 0, reorder: 5, price: 0 });
    setAdding(false);
  }

  const sorted = [...inventory].sort((a, b) => (a.stock <= a.reorder ? -1 : 1) - (b.stock <= b.reorder ? -1 : 1));

  return (
    <div style={styles.section}>
      <div style={styles.searchRow}>
        <div style={styles.subheading}>{inventory.length} products</div>
        <button style={styles.addBtn} onClick={() => setAdding(true)}><Plus size={18} /></button>
      </div>

      <div style={styles.listStack}>
        {sorted.map((p) => {
          const low = p.stock <= p.reorder;
          return (
            <div key={p.id} style={styles.rowCard}>
              <span style={{ ...styles.dotSmall, background: low ? "#B0453F" : "#6B8F71" }} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={styles.rowTitle}>{p.name}</div>
                <div style={styles.rowMeta}>{p.category} · {rupee(p.price)}</div>
              </div>
              <button style={styles.qtyBtn} onClick={() => adjust(p.id, -1)}><Minus size={13} /></button>
              <div style={{ ...styles.qtyValue, ...(low ? { color: "#B0453F" } : {}) }}>{p.stock}</div>
              <button style={styles.qtyBtn} onClick={() => adjust(p.id, 1)}><Plus size={13} /></button>
            </div>
          );
        })}
      </div>

      {adding && (
        <SlidePanel title="Add product" onClose={() => setAdding(false)}>
          <label style={styles.label}>Name</label>
          <input style={styles.input} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Product name" />
          <label style={styles.label}>Category</label>
          <div style={styles.segRow}>
            {["Retail", "Backbar", "Supplies"].map((c) => (
              <button key={c} style={{ ...styles.segBtnSmall, ...(form.category === c ? styles.segBtnSmallActive : {}) }} onClick={() => setForm({ ...form, category: c })}>{c}</button>
            ))}
          </div>
          <div style={styles.row2}>
            <div style={{ flex: 1 }}>
              <label style={styles.label}>Starting stock</label>
              <input style={styles.input} type="number" value={form.stock} onChange={(e) => setForm({ ...form, stock: e.target.value })} />
            </div>
            <div style={{ flex: 1 }}>
              <label style={styles.label}>Reorder at</label>
              <input style={styles.input} type="number" value={form.reorder} onChange={(e) => setForm({ ...form, reorder: e.target.value })} />
            </div>
          </div>
          <label style={styles.label}>Price</label>
          <input style={styles.input} type="number" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} />
          <div style={styles.panelActions}>
            <button style={styles.saveBtn} onClick={addProduct}>Add product</button>
          </div>
        </SlidePanel>
      )}
    </div>
  );
}

/* ============================= slide panel ============================= */

function SlidePanel({ title, onClose, children }) {
  return (
    <div style={styles.overlay} onClick={onClose}>
      <div style={styles.panel} onClick={(e) => e.stopPropagation()}>
        <div style={styles.panelHeader}>
          <div style={styles.panelTitle}>{title}</div>
          <button style={styles.closeBtn} onClick={onClose} aria-label="Close"><X size={20} /></button>
        </div>
        {children}
      </div>
    </div>
  );
}

/* ============================= styles ============================= */

const styles = {
  app: { fontFamily: "'Inter', sans-serif", background: "#F7F1E6", color: "#2B2620", minHeight: "100vh", display: "flex", flexDirection: "column" },
  header: { padding: "18px 16px 12px", borderBottom: "1px solid #E4DAC8", background: "#F7F1E6", position: "sticky", top: 0, zIndex: 5 },
  brandRow: { display: "flex", alignItems: "center", gap: 10 },
  pinDot: { width: 10, height: 10, borderRadius: "50%", background: "#B08D57", boxShadow: "0 0 0 3px rgba(176,141,87,0.18)" },
  brand: { fontFamily: "'Fraunces', serif", fontSize: 24, fontWeight: 700, lineHeight: 1, color: "#1C2333" },
  brandSub: { fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, letterSpacing: "0.08em", textTransform: "uppercase", color: "#8A7F68", marginTop: 3 },
  content: { flex: 1, overflowY: "auto", paddingBottom: 88 },
  section: { padding: "16px" },
  dateHeading: { fontFamily: "'Fraunces', serif", fontSize: 20, fontWeight: 600, color: "#1C2333", marginBottom: 14 },
  subheading: { fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.06em", color: "#8A7F68", margin: "18px 0 8px" },

  statGrid: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 },
  statCard: { background: "#FCFAF4", border: "1px solid #E4DAC8", borderRadius: 12, padding: "14px", textAlign: "left", cursor: "pointer" },
  statValue: { fontFamily: "'Fraunces', serif", fontSize: 22, fontWeight: 700, color: "#1C2333", marginTop: 8 },
  statLabel: { fontSize: 11.5, color: "#8A7F68", marginTop: 2 },

  listStack: { display: "flex", flexDirection: "column", gap: 8 },
  rowCard: { display: "flex", alignItems: "center", gap: 10, background: "#FCFAF4", border: "1px solid #E4DAC8", borderRadius: 10, padding: "10px 12px" },
  dotSmall: { width: 8, height: 8, borderRadius: "50%", flexShrink: 0 },
  rowTitle: { fontSize: 14, fontWeight: 600, color: "#1C2333" },
  rowMeta: { fontFamily: "'IBM Plex Mono', monospace", fontSize: 10.5, color: "#8A7F68", marginTop: 2 },
  rowTime: { fontFamily: "'IBM Plex Mono', monospace", fontSize: 12, color: "#6B6152", flexShrink: 0 },
  stockBadgeLow: { fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: "#B0453F", background: "#FBEAE8", padding: "3px 8px", borderRadius: 12, flexShrink: 0 },
  emptyNote: { fontSize: 13, color: "#8A7F68", padding: "20px 4px", textAlign: "center" },

  dateNav: { display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8, marginBottom: 12 },
  navBtn: { width: 32, height: 32, borderRadius: "50%", border: "1px solid #E4DAC8", background: "#fff", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center" },
  dateLabel: { fontFamily: "'Fraunces', serif", fontSize: 16, fontWeight: 600, color: "#1C2333", display: "flex", alignItems: "center", gap: 10, flex: 1, justifyContent: "center" },
  todayBtn: { fontFamily: "'IBM Plex Mono', monospace", fontSize: 10, textTransform: "uppercase", letterSpacing: "0.06em", border: "1px solid #B08D57", color: "#B08D57", background: "transparent", borderRadius: 20, padding: "3px 9px", cursor: "pointer" },
  filterRow: { display: "flex", alignItems: "center", gap: 8, overflowX: "auto", marginBottom: 12, paddingBottom: 2 },
  chip: { fontSize: 12.5, fontWeight: 500, color: "#6B6152", border: "1px solid #E4DAC8", background: "#fff", borderRadius: 20, padding: "6px 12px", display: "flex", alignItems: "center", gap: 6, cursor: "pointer", whiteSpace: "nowrap", flexShrink: 0 },
  chipActive: { background: "#1C2333", color: "#fff", borderColor: "#1C2333" },
  chipDot: { width: 7, height: 7, borderRadius: "50%", display: "inline-block" },
  count: { marginLeft: "auto", fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: "#8A7F68", whiteSpace: "nowrap", flexShrink: 0 },
  gridWrap: { overflow: "auto" },
  gridInner: { display: "flex", position: "relative" },
  timeRail: { width: 56, flexShrink: 0, position: "relative" },
  hourMark: { position: "absolute", left: 0, right: 0, transform: "translateY(-7px)" },
  hourLabel: { fontFamily: "'IBM Plex Mono', monospace", fontSize: 10.5, color: "#8A7F68" },
  columns: { display: "grid", flex: 1, gap: 8, marginLeft: 4 },
  column: { display: "flex", flexDirection: "column" },
  columnHeader: { fontFamily: "'Fraunces', serif", fontWeight: 600, fontSize: 13.5, color: "#1C2333", display: "flex", alignItems: "center", gap: 6, paddingBottom: 8, borderBottom: "2px solid", marginBottom: 4 },
  columnBody: { position: "relative", background: "#FCFAF4", border: "1px solid #E4DAC8", borderRadius: 8, cursor: "pointer" },
  ruleLine: { position: "absolute", left: 0, right: 0, borderTop: "1px solid #E4DAC8" },
  slip: { position: "absolute", left: 5, right: 5, background: "#fff", borderRadius: 6, borderLeft: "3px solid", boxShadow: "0 1px 2px rgba(28,35,51,0.08)", padding: "5px 8px", textAlign: "left", cursor: "pointer", overflow: "hidden" },
  slipClient: { fontSize: 12, fontWeight: 600, color: "#1C2333", lineHeight: 1.2 },
  slipMeta: { fontFamily: "'IBM Plex Mono', monospace", fontSize: 9.5, color: "#8A7F68", marginTop: 2 },
  hint: { textAlign: "center", fontSize: 11.5, color: "#8A7F68", padding: "10px 0 4px" },

  searchRow: { display: "flex", alignItems: "center", gap: 10, marginBottom: 14 },
  searchBox: { flex: 1, display: "flex", alignItems: "center", gap: 8, background: "#FCFAF4", border: "1px solid #E4DAC8", borderRadius: 10, padding: "9px 12px" },
  searchInput: { border: "none", background: "none", outline: "none", fontSize: 14, flex: 1, color: "#2B2620" },
  addBtn: { width: 36, height: 36, borderRadius: 10, background: "#1C2333", color: "#fff", border: "none", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", flexShrink: 0 },

  clientCard: { display: "flex", alignItems: "center", gap: 10, background: "#FCFAF4", border: "1px solid #E4DAC8", borderRadius: 10, padding: "10px 12px" },
  staffCard: { display: "flex", alignItems: "center", gap: 10, background: "#FCFAF4", border: "1px solid #E4DAC8", borderRadius: 10, padding: "10px 12px" },
  avatarCircle: { width: 36, height: 36, borderRadius: "50%", background: "#B08D57", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "'Fraunces', serif", fontWeight: 700, fontSize: 15, flexShrink: 0 },
  clientSpent: { textAlign: "right", flexShrink: 0 },
  clientSpentValue: { fontSize: 13.5, fontWeight: 600, color: "#1C2333" },
  clientLast: { fontFamily: "'IBM Plex Mono', monospace", fontSize: 10, color: "#8A7F68", marginTop: 2 },
  roleTag: { fontSize: 11, fontWeight: 500, marginLeft: 6 },
  statusPill: { fontFamily: "'IBM Plex Mono', monospace", fontSize: 10.5, borderRadius: 14, padding: "5px 10px", border: "none", cursor: "pointer", flexShrink: 0 },
  statusActive: { background: "#E9F0E6", color: "#4E7350" },
  statusInactive: { background: "#EFE8D8", color: "#8A7F68" },

  cartStack: { display: "flex", flexDirection: "column", gap: 6, marginBottom: 4 },
  cartRow: { display: "flex", alignItems: "center", gap: 8, background: "#fff", border: "1px solid #E4DAC8", borderRadius: 8, padding: "8px 10px" },
  qtyBtn: { width: 24, height: 24, borderRadius: 6, border: "1px solid #E4DAC8", background: "#fff", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", flexShrink: 0 },
  qtyValue: { fontFamily: "'IBM Plex Mono', monospace", fontSize: 13, fontWeight: 500, minWidth: 18, textAlign: "center" },
  trashBtn: { border: "none", background: "none", color: "#B0453F", cursor: "pointer", flexShrink: 0, marginLeft: 2 },
  totalsBox: { background: "#fff", border: "1px solid #E4DAC8", borderRadius: 10, padding: "12px 14px", marginTop: 6 },
  totalRow: { display: "flex", justifyContent: "space-between", fontSize: 13, color: "#6B6152", padding: "3px 0" },
  totalRowFinal: { fontSize: 15.5, fontWeight: 700, color: "#1C2333", borderTop: "1px solid #E4DAC8", marginTop: 4, paddingTop: 8 },

  overlay: { position: "fixed", inset: 0, background: "rgba(28,35,51,0.45)", display: "flex", alignItems: "flex-end", justifyContent: "center", zIndex: 30 },
  panel: { background: "#FCFAF4", width: "100%", maxWidth: 440, borderRadius: "16px 16px 0 0", padding: "18px 20px 26px", maxHeight: "86vh", overflowY: "auto", boxShadow: "0 -8px 30px rgba(28,35,51,0.25)" },
  panelHeader: { display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 },
  panelTitle: { fontFamily: "'Fraunces', serif", fontSize: 18, fontWeight: 700, color: "#1C2333" },
  closeBtn: { border: "none", background: "none", color: "#8A7F68", cursor: "pointer", display: "flex" },
  label: { display: "block", fontFamily: "'IBM Plex Mono', monospace", fontSize: 10.5, textTransform: "uppercase", letterSpacing: "0.06em", color: "#8A7F68", margin: "12px 0 6px" },
  input: { width: "100%", padding: "10px 12px", borderRadius: 8, border: "1px solid #E4DAC8", fontSize: 14.5, background: "#fff", color: "#2B2620" },
  select: { width: "100%", padding: "10px 12px", borderRadius: 8, border: "1px solid #E4DAC8", fontSize: 14.5, background: "#fff", color: "#2B2620" },
  segRow: { display: "flex", gap: 6, flexWrap: "wrap" },
  segBtn: { flex: "1 1 auto", padding: "8px 10px", borderRadius: 8, border: "1px solid #E4DAC8", background: "#fff", color: "#2B2620", fontSize: 13.5, fontWeight: 500, cursor: "pointer" },
  segBtnSmall: { padding: "6px 10px", borderRadius: 16, border: "1px solid #E4DAC8", background: "#fff", color: "#6B6152", fontSize: 12, cursor: "pointer" },
  segBtnSmallActive: { background: "#1C2333", color: "#fff", borderColor: "#1C2333" },
  row2: { display: "flex", gap: 12 },
  errorText: { color: "#B0453F", fontSize: 12.5, marginTop: 10 },
  panelActions: { display: "flex", gap: 10, marginTop: 20 },
  saveBtn: { flex: 1, background: "#1C2333", color: "#fff", border: "none", borderRadius: 10, padding: "12px 16px", fontSize: 14.5, fontWeight: 600, cursor: "pointer" },
  deleteBtn: { background: "#fff", color: "#B0453F", border: "1px solid #E4B9B4", borderRadius: 10, padding: "12px 16px", fontSize: 14.5, fontWeight: 600, cursor: "pointer" },

  bottomNav: { position: "fixed", bottom: 0, left: 0, right: 0, background: "#FCFAF4", borderTop: "1px solid #E4DAC8", display: "flex", justifyContent: "space-around", padding: "8px 4px 10px", zIndex: 10 },
  navItem: { display: "flex", flexDirection: "column", alignItems: "center", gap: 3, background: "none", border: "none", cursor: "pointer", padding: "4px 6px", position: "relative", flex: 1 },
  navLabel: { fontSize: 9.5 },
  navDot: { position: "absolute", top: -8, width: 4, height: 4, borderRadius: "50%", background: "#B08D57" },
};
