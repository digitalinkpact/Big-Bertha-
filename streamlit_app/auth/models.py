"""Data classes for the auth system."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    id: int
    email: str
    password_hash: str
    is_email_confirmed: bool
    is_approved: bool
    is_admin: bool
    is_deleted: bool
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row) -> "User":
        return cls(
            id=row["id"],
            email=row["email"],
            password_hash=row["password_hash"],
            is_email_confirmed=bool(row["is_email_confirmed"]),
            is_approved=bool(row["is_approved"]),
            is_admin=bool(row["is_admin"]),
            is_deleted=bool(row["is_deleted"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


@dataclass
class PasswordResetEvent:
    id: int
    user_id: int
    event_type: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    created_at: str

    @classmethod
    def from_row(cls, row) -> "PasswordResetEvent":
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            event_type=row["event_type"],
            ip_address=row["ip_address"],
            user_agent=row["user_agent"],
            created_at=row["created_at"],
        )
