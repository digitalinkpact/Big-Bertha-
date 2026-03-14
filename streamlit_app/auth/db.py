"""Database initialisation — SQLite with WAL mode for concurrent reads."""

import sqlite3
from pathlib import Path

_DB_DIR = Path.home() / ".nanobot"
_DB_PATH = _DB_DIR / "auth.db"


def _get_db_path() -> Path:
    import os
    custom = os.environ.get("NANOBOT_AUTH_DB")
    if custom:
        return Path(custom)
    return _DB_PATH


def get_connection() -> sqlite3.Connection:
    """Return a connection with WAL mode and foreign keys enabled."""
    db_path = _get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Create all tables if they don't exist."""
    conn = get_connection()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                email           TEXT    NOT NULL UNIQUE COLLATE NOCASE,
                password_hash   TEXT    NOT NULL,
                is_email_confirmed INTEGER NOT NULL DEFAULT 0,
                is_approved     INTEGER NOT NULL DEFAULT 0,
                is_admin        INTEGER NOT NULL DEFAULT 0,
                is_deleted      INTEGER NOT NULL DEFAULT 0,
                created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
                updated_at      TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS email_verification_tokens (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                token       TEXT    NOT NULL UNIQUE,
                expires_at  TEXT    NOT NULL,
                used_at     TEXT
            );

            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                token       TEXT    NOT NULL UNIQUE,
                expires_at  TEXT    NOT NULL,
                used_at     TEXT
            );

            CREATE TABLE IF NOT EXISTS password_reset_events (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                event_type  TEXT    NOT NULL,
                ip_address  TEXT,
                user_agent  TEXT,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_users_email
                ON users(email);
            CREATE INDEX IF NOT EXISTS idx_evt_token
                ON email_verification_tokens(token);
            CREATE INDEX IF NOT EXISTS idx_prt_token
                ON password_reset_tokens(token);
            CREATE INDEX IF NOT EXISTS idx_pre_user
                ON password_reset_events(user_id);
        """)
        conn.commit()
    finally:
        conn.close()
