import sqlite3
import pandas as pd
from datetime import date, datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent / "inventarios.db"


def _conn():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = _conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS locations (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name     TEXT    NOT NULL UNIQUE,
            zone     TEXT    DEFAULT '',
            row_pos  INTEGER DEFAULT 0,
            col_pos  INTEGER DEFAULT 0
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
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            location_id   INTEGER NOT NULL UNIQUE,
            frequency_days INTEGER DEFAULT 30,
            start_date    TEXT,
            delivery_date TEXT,
            FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE CASCADE
        );
    """)
    conn.commit()
    conn.close()


# ── Locations ──────────────────────────────────────────────────────────

def add_location(name: str, zone: str, row_pos: int, col_pos: int):
    conn = _conn()
    try:
        conn.execute(
            "INSERT INTO locations (name, zone, row_pos, col_pos) VALUES (?, ?, ?, ?)",
            (name.upper().strip(), zone.strip(), row_pos, col_pos),
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
            (name.upper().strip(), zone.strip(), loc_id),
        )
        conn.commit()
        return True, ""
    except sqlite3.IntegrityError:
        return False, f"Ya existe una ubicación con el nombre «{name.upper().strip()}»."
    finally:
        conn.close()


def get_locations() -> pd.DataFrame:
    conn = _conn()
    df = pd.read_sql(
        "SELECT * FROM locations ORDER BY row_pos, col_pos, name", conn
    )
    conn.close()
    return df


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
        SELECT d.id,
               d.article,
               l.name  AS location,
               l.zone,
               d.difference,
               d.price,
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
        SELECT r.id,
               l.id   AS location_id,
               l.name AS location,
               l.zone,
               r.frequency_days,
               r.start_date,
               r.delivery_date
        FROM   rhythm    r
        JOIN   locations l ON r.location_id = l.id
        ORDER  BY l.row_pos, l.col_pos, l.name
        """,
        conn,
    )
    conn.close()
    return df


def update_rhythm(
    location_id: int,
    frequency_days: int,
    start_date,
    delivery_date,
):
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


# ── Status for layout coloring ─────────────────────────────────────────

def get_location_status():
    """Returns four sets of location_ids per visual state."""
    today = date.today()
    conn  = _conn()

    diff_locs = {
        r[0]
        for r in conn.execute(
            "SELECT DISTINCT location_id FROM differences"
        ).fetchall()
    }
    start_locs = {
        r[0]
        for r in conn.execute(
            "SELECT location_id FROM rhythm"
            " WHERE start_date IS NOT NULL AND start_date != ''"
        ).fetchall()
    }
    delivery_locs = {
        r[0]
        for r in conn.execute(
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
