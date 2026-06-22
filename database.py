import sqlite3
import pandas as pd
from datetime import date, datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent / "inventarios.db"

# Predefined slots: (slot_key, default_name, zone_group, sort_order, svg_x, svg_y, svg_w, svg_h, svg_vertical)
WAREHOUSE_SLOTS = [
    # Recepción
    ("VERIF-CONTROL",    "Verificación y Control",  "Recepción",      0,  250,  42, 198, 148, 0),
    ("CLASIFICACION",    "Clasificación",            "Recepción",      1,  458,  42, 263, 148, 0),
    ("PALETS-VACIOS",    "Palets Vacíos",            "Recepción",      2,  731,  42, 269, 148, 0),
    ("ANDEN-RECEP-1",    "Andén Recepción 1",        "Recepción",      3,   18, 202, 210, 130, 0),
    ("ANDEN-RECEP-2",    "Andén Recepción 2",        "Recepción",      4,   18, 390, 210, 130, 0),
    # Almacenamiento
    ("RACK-L1",          "RACK-L1",                  "Almacenamiento", 10, 265, 258,  50, 182, 1),
    ("RACK-L2",          "RACK-L2",                  "Almacenamiento", 11, 335, 258,  50, 182, 1),
    ("RACK-L3",          "RACK-L3",                  "Almacenamiento", 12, 405, 258,  50, 182, 1),
    ("RACK-C1",          "RACK-C1",                  "Almacenamiento", 13, 488, 258,  50, 182, 1),
    ("RACK-C2",          "RACK-C2",                  "Almacenamiento", 14, 558, 258,  50, 182, 1),
    ("RACK-C3",          "RACK-C3",                  "Almacenamiento", 15, 628, 258,  50, 182, 1),
    ("RACK-R1",          "RACK-R1",                  "Almacenamiento", 16, 711, 258,  50, 182, 1),
    ("RACK-R2",          "RACK-R2",                  "Almacenamiento", 17, 781, 258,  50, 182, 1),
    ("RACK-R3",          "RACK-R3",                  "Almacenamiento", 18, 851, 258,  50, 182, 1),
    ("RACK-R4",          "RACK-R4",                  "Almacenamiento", 19, 921, 258,  50, 182, 1),
    # Picking
    ("AREA-PEDIDOS",     "Área de Pedidos",          "Picking",        20, 250, 497, 208, 120, 0),
    ("PICKING-CAJAS",    "Picking de Cajas",         "Picking",        21, 468, 497, 272, 120, 0),
    ("AREA-EMPAQUETADO", "Área de Empaquetado",      "Picking",        22, 750, 497, 248, 120, 0),
    # Expedición
    ("MUELLES-SALIDA",   "Muelles de Salida 9-16",  "Expedición",     30, 250, 656, 208,  83, 0),
    ("CONSOLIDACION",    "Área de Consolidación",   "Expedición",     31, 468, 656, 272,  83, 0),
    ("ANDEN-EXPEDI",     "Andén de Expedición",     "Expedición",     32, 750, 656, 248,  83, 0),
    # Administración
    ("ZONA-ADMIN",       "Zona Administrativa",     "Administración", 40, 1015,  24, 176, 148, 0),
    ("BANOS-VESTUARIOS", "Baños y Vestuarios",      "Administración", 41, 1015, 196, 176,  92, 0),
    ("ZONA-DESCANSO",    "Zona de Descanso",        "Administración", 42, 1015, 308, 176,  92, 0),
    ("MANTENIMIENTO",    "Mantenimiento",            "Administración", 43, 1015, 426, 176,  92, 0),
]

# Quick lookup: slot_key → default (x, y, w, h, vertical)
_SVG_DEFAULTS = {s[0]: (s[4], s[5], s[6], s[7], s[8]) for s in WAREHOUSE_SLOTS}


def _conn():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = _conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS locations (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT    NOT NULL UNIQUE,
            zone            TEXT    DEFAULT '',
            slot_key        TEXT    DEFAULT '',
            row_pos         INTEGER DEFAULT 0,
            col_pos         INTEGER DEFAULT 0,
            svg_x           INTEGER DEFAULT 0,
            svg_y           INTEGER DEFAULT 0,
            svg_w           INTEGER DEFAULT 100,
            svg_h           INTEGER DEFAULT 60,
            svg_vertical    INTEGER DEFAULT 0,
            svg_initialized INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS differences (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            article      TEXT    NOT NULL,
            location_id  INTEGER NOT NULL,
            difference   REAL    NOT NULL,
            price        REAL    NOT NULL DEFAULT 0,
            created_date TEXT    DEFAULT (date('now')),
            FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS rhythm (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            location_id    INTEGER NOT NULL UNIQUE,
            frequency_days INTEGER DEFAULT 30,
            start_date     TEXT,
            delivery_date  TEXT,
            FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE CASCADE
        );
    """)

    # Migrations for older databases (ignore if column already exists)
    for col, default in [
        ("slot_key", "''"), ("svg_x", 0), ("svg_y", 0),
        ("svg_w", 100), ("svg_h", 60), ("svg_vertical", 0), ("svg_initialized", 0),
    ]:
        try:
            conn.execute(f"ALTER TABLE locations ADD COLUMN {col} INTEGER DEFAULT {default}")
            conn.commit()
        except sqlite3.OperationalError:
            pass

    # Set correct SVG positions for existing zones not yet initialized
    for slot_key, (x, y, w, h, v) in _SVG_DEFAULTS.items():
        conn.execute(
            "UPDATE locations SET svg_x=?, svg_y=?, svg_w=?, svg_h=?,"
            " svg_vertical=?, svg_initialized=1"
            " WHERE slot_key=? AND svg_initialized=0",
            (x, y, w, h, v, slot_key),
        )
    conn.commit()
    conn.close()


def batch_add_warehouse_zones() -> int:
    conn = _conn()
    count = 0
    for slot_key, name, zone, sort_order, svg_x, svg_y, svg_w, svg_h, svg_v in WAREHOUSE_SLOTS:
        try:
            conn.execute(
                "INSERT INTO locations"
                " (name, zone, slot_key, row_pos, col_pos,"
                "  svg_x, svg_y, svg_w, svg_h, svg_vertical, svg_initialized)"
                " VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?, ?, 1)",
                (name, zone, slot_key, sort_order, svg_x, svg_y, svg_w, svg_h, svg_v),
            )
            loc_id = conn.execute(
                "SELECT id FROM locations WHERE slot_key=?", (slot_key,)
            ).fetchone()[0]
            conn.execute("INSERT OR IGNORE INTO rhythm (location_id) VALUES (?)", (loc_id,))
            count += 1
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    conn.close()
    return count


# ── Locations ──────────────────────────────────────────────────────────

def add_location(name: str, zone: str, row_pos: int, col_pos: int, slot_key: str = ""):
    conn = _conn()
    try:
        conn.execute(
            "INSERT INTO locations (name, zone, slot_key, row_pos, col_pos) VALUES (?,?,?,?,?)",
            (name.upper().strip(), zone.strip(), slot_key, row_pos, col_pos),
        )
        loc_id = conn.execute(
            "SELECT id FROM locations WHERE name=?", (name.upper().strip(),)
        ).fetchone()[0]
        conn.execute("INSERT OR IGNORE INTO rhythm (location_id) VALUES (?)", (loc_id,))
        conn.commit()
        return True, ""
    except sqlite3.IntegrityError:
        return False, f"Ya existe una ubicación con el nombre «{name.upper().strip()}»."
    finally:
        conn.close()


def delete_location(loc_id: int):
    conn = _conn()
    conn.execute("DELETE FROM locations WHERE id=?", (loc_id,))
    conn.commit()
    conn.close()


def update_location(loc_id: int, name: str, zone: str):
    conn = _conn()
    try:
        conn.execute(
            "UPDATE locations SET name=?, zone=? WHERE id=?",
            (name.strip(), zone.strip(), loc_id),
        )
        conn.commit()
        return True, ""
    except sqlite3.IntegrityError:
        return False, f"Ya existe una ubicación con el nombre «{name.strip()}»."
    finally:
        conn.close()


def update_location_svg(loc_id: int, x: int, y: int, w: int, h: int, vertical: int):
    conn = _conn()
    conn.execute(
        "UPDATE locations SET svg_x=?, svg_y=?, svg_w=?, svg_h=?, svg_vertical=? WHERE id=?",
        (x, y, w, h, vertical, loc_id),
    )
    conn.commit()
    conn.close()


def reset_location_svg(slot_key: str):
    if slot_key not in _SVG_DEFAULTS:
        return
    x, y, w, h, v = _SVG_DEFAULTS[slot_key]
    conn = _conn()
    conn.execute(
        "UPDATE locations SET svg_x=?, svg_y=?, svg_w=?, svg_h=?, svg_vertical=? WHERE slot_key=?",
        (x, y, w, h, v, slot_key),
    )
    conn.commit()
    conn.close()


def get_locations() -> pd.DataFrame:
    conn = _conn()
    df = pd.read_sql("SELECT * FROM locations ORDER BY row_pos, col_pos, name", conn)
    conn.close()
    return df


# ── Differences ────────────────────────────────────────────────────────

def add_difference(article: str, location_id: int, difference: float, price: float):
    conn = _conn()
    conn.execute(
        "INSERT INTO differences (article, location_id, difference, price, created_date)"
        " VALUES (?,?,?,?,?)",
        (article.strip(), location_id, difference, price, date.today().isoformat()),
    )
    conn.commit()
    conn.close()


def delete_difference(diff_id: int):
    conn = _conn()
    conn.execute("DELETE FROM differences WHERE id=?", (diff_id,))
    conn.commit()
    conn.close()


def get_differences() -> pd.DataFrame:
    conn = _conn()
    df = pd.read_sql(
        """
        SELECT d.id, d.article, l.name AS location, l.zone,
               d.difference, d.price,
               ROUND(d.difference * d.price, 2) AS impact,
               d.created_date
        FROM   differences d
        JOIN   locations   l ON d.location_id = l.id
        ORDER  BY d.created_date DESC, d.id DESC
        """,
        conn,
    )
    conn.close()
    return df


# ── Rhythm ─────────────────────────────────────────────────────────────

def get_rhythm() -> pd.DataFrame:
    conn = _conn()
    df = pd.read_sql(
        """
        SELECT r.id, l.id AS location_id, l.name AS location, l.zone,
               r.frequency_days, r.start_date, r.delivery_date
        FROM   rhythm r
        JOIN   locations l ON r.location_id = l.id
        ORDER  BY l.row_pos, l.name
        """,
        conn,
    )
    conn.close()
    return df


def update_rhythm(location_id: int, frequency_days: int, start_date, delivery_date):
    conn = _conn()
    conn.execute(
        "UPDATE rhythm SET frequency_days=?, start_date=?, delivery_date=? WHERE location_id=?",
        (
            frequency_days,
            start_date.isoformat() if start_date else None,
            delivery_date.isoformat() if delivery_date else None,
            location_id,
        ),
    )
    conn.commit()
    conn.close()


# ── Status ─────────────────────────────────────────────────────────────

def get_location_status():
    today = date.today()
    conn  = _conn()
    diff_locs = {r[0] for r in conn.execute(
        "SELECT DISTINCT location_id FROM differences").fetchall()}
    start_locs = {r[0] for r in conn.execute(
        "SELECT location_id FROM rhythm WHERE start_date IS NOT NULL AND start_date!=''").fetchall()}
    delivery_locs = {r[0] for r in conn.execute(
        "SELECT location_id FROM rhythm WHERE delivery_date IS NOT NULL AND delivery_date!=''").fetchall()}
    today_count = set()
    for loc_id, del_date, freq in conn.execute(
        "SELECT location_id, delivery_date, frequency_days FROM rhythm"
        " WHERE delivery_date IS NOT NULL AND frequency_days IS NOT NULL"
    ).fetchall():
        try:
            last = datetime.strptime(del_date[:10], "%Y-%m-%d").date()
            if last + timedelta(days=int(freq)) == today:
                today_count.add(loc_id)
        except (ValueError, TypeError):
            pass
    conn.close()
    return diff_locs, delivery_locs, start_locs, today_count
