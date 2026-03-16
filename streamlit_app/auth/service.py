"""Core authentication service — signup, login, verification, reset, admin."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt

from streamlit_app.auth.db import get_connection
from streamlit_app.auth.models import PasswordResetEvent, User

_TOKEN_BYTES = 32  # 256-bit random tokens
_VERIFY_EXPIRY_HOURS = 48
_RESET_EXPIRY_HOURS = 1


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def _generate_token() -> str:
    return secrets.token_urlsafe(_TOKEN_BYTES)


class AuthService:
    """Stateless service — every method opens its own DB connection."""

    # ------------------------------------------------------------------
    # Sign-up
    # ------------------------------------------------------------------
    def create_user(self, email: str, password: str) -> tuple[User, str]:
        """Create user + verification token.  Returns (user, token)."""
        password_hash = _hash_password(password)
        token = _generate_token()
        expires = (datetime.now(timezone.utc) + timedelta(hours=_VERIFY_EXPIRY_HOURS)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        conn = get_connection()
        try:
            cur = conn.execute(
                """INSERT INTO users (email, password_hash)
                   VALUES (?, ?)""",
                (email.strip().lower(), password_hash),
            )
            user_id = cur.lastrowid
            conn.execute(
                """INSERT INTO email_verification_tokens (user_id, token, expires_at)
                   VALUES (?, ?, ?)""",
                (user_id, token, expires),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            return User.from_row(row), token
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Email verification
    # ------------------------------------------------------------------
    def verify_email(self, token: str) -> Optional[User]:
        """Mark email confirmed if token is valid.  Returns user or None."""
        now = _utcnow()
        conn = get_connection()
        try:
            row = conn.execute(
                """SELECT * FROM email_verification_tokens
                   WHERE token = ? AND used_at IS NULL AND expires_at > ?""",
                (token, now),
            ).fetchone()
            if not row:
                return None
            user_id = row["user_id"]
            conn.execute(
                "UPDATE email_verification_tokens SET used_at = ? WHERE id = ?",
                (now, row["id"]),
            )
            conn.execute(
                "UPDATE users SET is_email_confirmed = 1, updated_at = ? WHERE id = ?",
                (now, user_id),
            )
            conn.commit()
            user_row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            return User.from_row(user_row)
        finally:
            conn.close()

    def regenerate_verification_token(self, user_id: int) -> str:
        """Create a fresh verification token for a user."""
        token = _generate_token()
        expires = (datetime.now(timezone.utc) + timedelta(hours=_VERIFY_EXPIRY_HOURS)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        conn = get_connection()
        try:
            # Invalidate old tokens
            conn.execute(
                "UPDATE email_verification_tokens SET used_at = ? WHERE user_id = ? AND used_at IS NULL",
                (_utcnow(), user_id),
            )
            conn.execute(
                "INSERT INTO email_verification_tokens (user_id, token, expires_at) VALUES (?, ?, ?)",
                (user_id, token, expires),
            )
            conn.commit()
            return token
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------
    def authenticate(self, email: str, password: str) -> tuple[Optional[User], str]:
        """Authenticate user.  Returns (user, error_message).
        User is None if authentication fails."""
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM users WHERE email = ? AND is_deleted = 0",
                (email.strip().lower(),),
            ).fetchone()
            if not row:
                return None, "Invalid email or password."
            user = User.from_row(row)
            if not _verify_password(password, user.password_hash):
                return None, "Invalid email or password."
            if not user.is_email_confirmed:
                return None, "Please confirm your email first."
            if not user.is_approved:
                return None, "Your account is pending admin approval."
            return user, ""
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Password reset
    # ------------------------------------------------------------------
    def request_password_reset(
        self, email: str, ip_address: str | None = None, user_agent: str | None = None
    ) -> tuple[Optional[str], Optional[int]]:
        """Generate reset token.  Returns (token, user_id) or (None, None)."""
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM users WHERE email = ? AND is_deleted = 0",
                (email.strip().lower(),),
            ).fetchone()
            if not row:
                return None, None

            user_id = row["id"]
            token = _generate_token()
            now = _utcnow()
            expires = (datetime.now(timezone.utc) + timedelta(hours=_RESET_EXPIRY_HOURS)).strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            # Invalidate old unused reset tokens
            conn.execute(
                "UPDATE password_reset_tokens SET used_at = ? WHERE user_id = ? AND used_at IS NULL",
                (now, user_id),
            )
            conn.execute(
                "INSERT INTO password_reset_tokens (user_id, token, expires_at) VALUES (?, ?, ?)",
                (user_id, token, expires),
            )
            conn.execute(
                """INSERT INTO password_reset_events
                   (user_id, event_type, ip_address, user_agent)
                   VALUES (?, 'reset_requested', ?, ?)""",
                (user_id, ip_address, user_agent),
            )
            conn.commit()
            return token, user_id
        finally:
            conn.close()

    def validate_reset_token(self, token: str) -> Optional[int]:
        """Check token validity.  Returns user_id or None."""
        conn = get_connection()
        try:
            row = conn.execute(
                """SELECT * FROM password_reset_tokens
                   WHERE token = ? AND used_at IS NULL AND expires_at > ?""",
                (token, _utcnow()),
            ).fetchone()
            return row["user_id"] if row else None
        finally:
            conn.close()

    def reset_password(
        self,
        token: str,
        new_password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> bool:
        """Set new password using reset token.  Returns True on success."""
        now = _utcnow()
        conn = get_connection()
        try:
            row = conn.execute(
                """SELECT * FROM password_reset_tokens
                   WHERE token = ? AND used_at IS NULL AND expires_at > ?""",
                (token, now),
            ).fetchone()
            if not row:
                return False

            user_id = row["user_id"]
            password_hash = _hash_password(new_password)

            conn.execute(
                "UPDATE password_reset_tokens SET used_at = ? WHERE id = ?",
                (now, row["id"]),
            )
            conn.execute(
                "UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?",
                (password_hash, now, user_id),
            )
            conn.execute(
                """INSERT INTO password_reset_events
                   (user_id, event_type, ip_address, user_agent)
                   VALUES (?, 'password_changed', ?, ?)""",
                (user_id, ip_address, user_agent),
            )
            conn.commit()
            return True
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Admin: user management
    # ------------------------------------------------------------------
    def list_users(self, include_deleted: bool = False) -> list[User]:
        conn = get_connection()
        try:
            if include_deleted:
                rows = conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM users WHERE is_deleted = 0 ORDER BY created_at DESC"
                ).fetchall()
            return [User.from_row(r) for r in rows]
        finally:
            conn.close()

    def get_user(self, user_id: int) -> Optional[User]:
        conn = get_connection()
        try:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            return User.from_row(row) if row else None
        finally:
            conn.close()

    def approve_user(self, user_id: int) -> bool:
        return self._update_user_flag(user_id, "is_approved", 1)

    def block_user(self, user_id: int) -> bool:
        return self._update_user_flag(user_id, "is_approved", 0)

    def verify_email_admin(self, user_id: int) -> bool:
        """Admin manually confirms a user's email."""
        return self._update_user_flag(user_id, "is_email_confirmed", 1)

    def delete_user(self, user_id: int) -> bool:
        """Soft delete."""
        return self._update_user_flag(user_id, "is_deleted", 1)

    def make_admin(self, user_id: int) -> bool:
        return self._update_user_flag(user_id, "is_admin", 1)

    def revoke_admin(self, user_id: int) -> bool:
        return self._update_user_flag(user_id, "is_admin", 0)

    def _update_user_flag(self, user_id: int, flag: str, value: int) -> bool:
        # Column name is validated, never from user input — safe for f-string SQL
        _ALLOWED_FLAGS = {"is_approved", "is_deleted", "is_admin", "is_email_confirmed"}
        if flag not in _ALLOWED_FLAGS:
            raise ValueError(f"Invalid flag: {flag!r}. Must be one of {_ALLOWED_FLAGS}")
        conn = get_connection()
        try:
            conn.execute(
                f"UPDATE users SET {flag} = ?, updated_at = ? WHERE id = ?",  # noqa: S608
                (value, _utcnow(), user_id),
            )
            conn.commit()
            return conn.total_changes > 0
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Audit: password recovery events
    # ------------------------------------------------------------------
    def get_reset_events(self, user_id: int | None = None) -> list[PasswordResetEvent]:
        conn = get_connection()
        try:
            if user_id:
                rows = conn.execute(
                    "SELECT * FROM password_reset_events WHERE user_id = ? ORDER BY created_at DESC",
                    (user_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM password_reset_events ORDER BY created_at DESC"
                ).fetchall()
            return [PasswordResetEvent.from_row(r) for r in rows]
        finally:
            conn.close()
