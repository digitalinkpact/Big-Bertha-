"""Database initialisation — SQLite with WAL mode for concurrent reads."""

import sqlite3
from pathlib import Path


def _resolve_db_path() -> Path:
    """Return the first writable path for the auth database.

    Priority:
      1. NANOBOT_AUTH_DB env var (explicit override)
      2. ~/.nanobot/auth.db  (standard location)
      3. <workspace>/.nanobot/auth.db  (Codespaces / Docker: home may be root-owned)
      4. /tmp/baccano_auth.db  (guaranteed writable on any Linux/macOS)
    """
    import os

    candidates = []

    custom = os.environ.get("NANOBOT_AUTH_DB")
    if custom:
        return Path(custom)

    candidates.append(Path.home() / ".nanobot" / "auth.db")
    candidates.append(Path(__file__).resolve().parent.parent.parent / ".nanobot" / "auth.db")
    candidates.append(Path("/tmp") / "baccano_auth.db")

    for path in candidates:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            # Probe writability: try creating/touching the file
            path.touch(exist_ok=True)
            return path
        except (OSError, PermissionError):
            continue

    # Should never reach here, but satisfy the type checker
    return candidates[-1]


def get_connection() -> sqlite3.Connection:
    """Return a connection with WAL mode and foreign keys enabled."""
    db_path = _resolve_db_path()
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
