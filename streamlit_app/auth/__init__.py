"""User authentication system — SQLite-backed multi-user auth with email confirmation."""

from streamlit_app.auth.db import init_db
from streamlit_app.auth.models import User
from streamlit_app.auth.service import AuthService

__all__ = ["init_db", "User", "AuthService"]
