import sqlite3
from flask import g, current_app

SCHEMA = """
CREATE TABLE IF NOT EXISTS admin (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS work (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    year INTEGER,
    duration TEXT,
    description TEXT,
    performers TEXT,
    video_url TEXT,
    image_filename TEXT,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS gallery (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_filename TEXT NOT NULL,
    caption TEXT,
    sort_order INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS message (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    body TEXT NOT NULL,
    is_read INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS setting (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS event (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    date TEXT,
    time TEXT,
    location TEXT,
    description TEXT,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def _migrate(db):
    """Add columns that may not exist yet."""
    for table in ("work", "event"):
        cols = [r[1] for r in db.execute(f"PRAGMA table_info({table})").fetchall()]
        if "sort_order" not in cols:
            db.execute(f"ALTER TABLE {table} ADD COLUMN sort_order INTEGER DEFAULT 0")
    db.commit()


def init_db():
    db = get_db()
    db.executescript(SCHEMA)
    _migrate(db)
    # Seed default settings
    defaults = {
        "recipient_email": "jingmiangong@outlook.com",
        "mail_server": "smtp.gmail.com",
        "mail_port": "587",
        "mail_username": "",
        "mail_password": "",
    }
    for key, value in defaults.items():
        existing = db.execute("SELECT key FROM setting WHERE key = ?", (key,)).fetchone()
        if not existing:
            db.execute("INSERT INTO setting (key, value) VALUES (?, ?)", (key, value))
    db.commit()


def get_setting(key, default=""):
    row = get_db().execute("SELECT value FROM setting WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key, value):
    db = get_db()
    db.execute("INSERT OR REPLACE INTO setting (key, value) VALUES (?, ?)", (key, value))
    db.commit()
