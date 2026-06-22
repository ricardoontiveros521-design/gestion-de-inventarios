import sqlite3
import pandas as pd
from datetime import date, datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent / "inventarios.db"

# Predefined warehouse slots (slot_key, default_name, zone_group, sort_order)
WAREHOUSE_SLOTS = [
    # Recepción
    ("VERIF-CONTROL",    "Verificación y Control",  "Recepción",      0),
    ("CLASIFICACION",    "Clasificación",            "Recepción",      1),
    ("PALETS-VACIOS",    "Palets Vacíos",            "Recepción",      2),
    ("ANDEN-RECEP-1",   "Andén Recepción 1",        "Recepción",      3),
    ("ANDEN-RECEP-2",   "Andén Recepción 2",        "Recepción",      4),
    # Almacenamiento principal
    ("RACK-L1",          "RACK-L1",                  "Almacenamiento", 10),
    ("RACK-L2",          "RACK-L2",                  "Almacenamiento", 11),
    ("RACK-L3",          "RACK-L3",                  "Almacenamiento", 12),
    ("RACK-C1",          "RACK-C1",                  "Almacenamiento", 13),
    ("RACK-C2",          "RACK-C2",                  "Almacenamiento", 14),
    ("RACK-C3",          "RACK-C3",                  "Almacenamiento", 15),
    ("RACK-R1",          "RACK-R1",                  "Almacenamiento", 16),
    ("RACK-R2",          "RACK-R2",                  "Almacenamiento", 17),
    ("RACK-R3",          "RACK-R3",                  "Almacenamiento", 18),
    ("RACK-R4",          "RACK-R4",                  "Almacenamiento", 19),
    # Picking / Preparación
    ("AREA-PEDIDOS",     "Área de Pedidos",          "Picking",        20),
    ("PICKING-CAJAS",    "Picking de Cajas",         "Picking",        21),
    ("AREA-EMPAQUETADO", "Área de Empaquetado",      "Picking",        22),
    # Expedición
    ("MUELLES-SALIDA",   "Muelles de Salida 9-16",  "Expedición",     30),
    ("CONSOLIDACION",    "Área de Consolidación",    "Expedición",     31),
    ("ANDEN-EXPEDI",     "Andén de Expedición",      "Expedición",     32),
    # Administración (derecha)
    ("ZONA-ADMIN",       "Zona Administrativa",      "Administración", 40),
    ("BANOS-VESTUARIOS", "Baños y Vestuarios",       "Administración", 41),
    ("ZONA-DESCANSO",    "Zona de Descanso",         "Administración", 42),
    ("MANTENIMIENTO",    "Mantenimiento",             "Administración", 43),
]


def _conn():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = _conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS locations (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            name      TEXT    NOT NULL UNIQUE,
            zone      TEXT    DEFAULT '',
            slot_key  TEXT    DEFAULT '',
            row_pos   INTEGER DEFAULT 0,
            col_pos   INTEGER DEFAULT 0
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
    # Migration: add slot_key if older DB doesn't have it
    try:
        conn.execute("ALTER TABLE locations ADD COLUMN slot_key TEXT DEFAULT ''")
        conn.commit()
    except sqlite3.OperationalError:
        pass
    conn.close()


def batch_add_warehouse_zones() -> int:
    """Insert all predefined warehouse slots. Returns count of newly added zones."""
    conn = _conn()
    count = 0
    for slot_key, name, zone, sort_order in WAREHOUSE_SLOTS:
        try:
            conn.execute(
                "INSERT INTO locations (name, zone, slot_key, row_pos, col_pos)"
                " VALUES (?, ?, ?, ?, 0)",
                (name, zone, slot_key, sort_order),
            )
            loc_id = conn.execute(
                "SELECT id FROM locations WHERE slot_key=?", (slot_key,)
            ).fetchone()[0]
            conn.execute(
                "INSERT OR IGNORE INTO rhythm (location_id) VALUES (?)", (loc_id,)
            )
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
            "INSERT INTO locations (name, zone, slot_key, row_pos, col_pos)"
            " VALUES (?, ?, ?, ?, ?)",
            (name.upper().strip(), zone.strip(), slot_key, row_pos, col_pos),
        )
        loc_id = conn.execute(
            "SELECT id FROM locations WHERE name = ?", (name.upper().strip(),)
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
    conn.execute("DELETE FROM locations WHERE id = ?", (loc_id,))
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


def get_locations() -> pd.DataFrame:
    conn = _conn()
    df = pd.read_sql(
        "SELECT * FROM locations ORDER BY row_pos, col_pos, name", conn
    )
    conn.close()
    return df


def get_slot_map() -> dict:
    """Returns {slot_key: {'id': int, 'name': str, 'zone': str}} for SVG coloring."""
    conn = _conn()
    rows = conn.execute(
        "SELECT id, name, zone, slot_key FROM locations WHERE slot_key != '' AND slot_key IS NOT NULL"
    ).fetchall()
    conn.close()
    return {r[3]: {"id": r[0], "name": r[1], "zone": r[2]} for r in rows}


# ── Differences ────────────────────────────────────────────────────────

def add_difference(article: str, location_id: int, difference: float, price: float):
    conn = _conn()
    conn.execute(
        "INSERT INTO differences (article, location_id, difference, price, created_date)"
        " VALUES (?, ?, ?, ?, ?)",
        (article.strip(), location_id, difference, price, date.today().isoformat()),
    )
    conn.commit()
    conn.close()


def delete_difference(diff_id: int):
    conn = _conn()
    conn.execute("DELETE FROM differences WHERE id = ?", (diff_id,))
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
        FROM   rhythm    r
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
        "UPDATE rhythm SET frequency_days=?, start_date=?, delivery_date=?"
        " WHERE location_id=?",
        (
            frequency_days,
            start_date.isoformat() if start_date else None,
            delivery_date.isoformat() if delivery_date else None,
            location_id,
        ),
    )
    conn.commit()
    conn.close()


# ── Status for SVG coloring ────────────────────────────────────────────

def get_location_status():
    today = date.today()
    conn  = _conn()

    diff_locs = {
        r[0] for r in conn.execute(
            "SELECT DISTINCT location_id FROM differences"
        ).fetchall()
    }
    start_locs = {
        r[0] for r in conn.execute(
            "SELECT location_id FROM rhythm"
            " WHERE start_date IS NOT NULL AND start_date != ''"
        ).fetchall()
    }
    delivery_locs = {
        r[0] for r in conn.execute(
            "SELECT location_id FROM rhythm"
            " WHERE delivery_date IS NOT NULL AND delivery_date != ''"
        ).fetchall()
    }

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
