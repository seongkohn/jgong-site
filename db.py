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

CREATE TABLE IF NOT EXISTS work_video (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id INTEGER NOT NULL,
    title TEXT,
    video_url TEXT NOT NULL,
    sort_order INTEGER DEFAULT 0,
    FOREIGN KEY (work_id) REFERENCES work(id) ON DELETE CASCADE
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
        g.db.execute("PRAGMA foreign_keys = ON")
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

    # Migrate existing video_url data from work table into work_video
    work_cols = [r[1] for r in db.execute("PRAGMA table_info(work)").fetchall()]
    if "video_url" in work_cols:
        rows = db.execute("SELECT id, video_url FROM work WHERE video_url IS NOT NULL AND video_url != ''").fetchall()
        for row in rows:
            existing = db.execute(
                "SELECT id FROM work_video WHERE work_id = ? AND video_url = ?",
                (row["id"], row["video_url"]),
            ).fetchone()
            if not existing:
                db.execute(
                    "INSERT INTO work_video (work_id, video_url, sort_order) VALUES (?, ?, 0)",
                    (row["id"], row["video_url"]),
                )

    # Add title column to work_video if missing
    wv_cols = [r[1] for r in db.execute("PRAGMA table_info(work_video)").fetchall()]
    if "title" not in wv_cols:
        db.execute("ALTER TABLE work_video ADD COLUMN title TEXT")

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
