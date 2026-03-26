"""Streamlit UI pages for authentication: login, signup, verify, reset, admin."""

from __future__ import annotations

import hmac
import os
import re
import time

import streamlit as st

from streamlit_app.auth.db import init_db
from streamlit_app.auth.email_sender import send_password_reset_email, send_verification_email
from streamlit_app.auth.service import AuthService

_MAX_LOGIN_ATTEMPTS = 5
_LOGIN_LOCKOUT_SECONDS = 300

_auth = AuthService()


def _base_url() -> str:
    return os.environ.get("NANOBOT_BASE_URL", "http://localhost:8501")


def _valid_email(email: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))


def _password_strong_enough(password: str) -> tuple[bool, str]:
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    if not re.search(r"[A-Z]", password):
        return False, "Password must include an uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Password must include a lowercase letter."
    if not re.search(r"[0-9]", password):
        return False, "Password must include a digit."
    return True, ""


# ------------------------------------------------------------------
# Login page
# ------------------------------------------------------------------

def _first_run_setup() -> bool:
    """Show a first-run admin creation form when no users exist.
    Returns True once the admin is created and logged in."""
    st.title("⚡ Baccano AI — First-time Setup")
    st.info("No users exist yet. Create your admin account to get started.")

    email = st.text_input("Admin email", key="setup_email")
    password = st.text_input("Password", type="password", key="setup_password")
    confirm = st.text_input("Confirm password", type="password", key="setup_confirm")

    if st.button("Create Admin Account", key="setup_btn"):
        if not email or not password or not confirm:
            st.error("All fields are required.")
            return False
        if not _valid_email(email):
            st.error("Invalid email format.")
            return False
        if password != confirm:
            st.error("Passwords do not match.")
            return False
        ok, msg = _password_strong_enough(password)
        if not ok:
            st.error(msg)
            return False

        try:
            user, _token = _auth.create_user(email, password)
            _auth.verify_email_admin(user.id)
            _auth.approve_user(user.id)
            _auth.make_admin(user.id)
        except Exception as e:
            st.error(f"Failed to create admin: {e}")
            return False

        st.session_state["authenticated"] = True
        st.session_state["current_user"] = {
            "id": user.id,
            "email": user.email,
            "is_admin": True,
        }
        st.success("Admin account created! Logging you in…")
        st.rerun()
        return True

    return False


def show_login_page() -> bool:
    """Render login form.  Returns True if user is authenticated."""
    if st.session_state.get("authenticated") and st.session_state.get("current_user"):
        return True

    # First-run: no users in the database yet → show setup screen
    if not _auth.list_users():
        return _first_run_setup()

    # Handle query params for email verification and password reset
    params = st.query_params
    if "token" in params:
        page = params.get("page", "verify-email")
        if page == "verify-email":
            _handle_verify_email(params["token"])
            return False
        elif page == "reset-password":
            _handle_reset_password(params["token"])
            return False

    # Brute-force lockout
    attempts = st.session_state.get("login_attempts", 0)
    lockout_until = st.session_state.get("lockout_until", 0)
    if time.time() < lockout_until:
        remaining = int(lockout_until - time.time())
        st.title("🔒 Nanobot Voice Chat")
        st.error(f"Too many failed attempts. Try again in {remaining}s.")
        return False

    st.title("🔒 Nanobot Voice Chat")

    tab_login, tab_signup, tab_forgot = st.tabs(["Login", "Sign Up", "Forgot Password"])

    with tab_login:
        _login_form()

    with tab_signup:
        _signup_form()

    with tab_forgot:
        _forgot_password_form()

    return False


def _login_form():
    email = st.text_input("Email", key="login_email")
    password = st.text_input("Password", type="password", key="login_password")

    if st.button("Login", key="login_btn"):
        if not email or not password:
            st.error("Please enter email and password.")
            return

        user, error = _auth.authenticate(email, password)
        if user:
            st.session_state["authenticated"] = True
            st.session_state["current_user"] = {
                "id": user.id,
                "email": user.email,
                "is_admin": user.is_admin,
            }
            st.session_state["login_attempts"] = 0
            st.rerun()
        else:
            attempts = st.session_state.get("login_attempts", 0) + 1
            st.session_state["login_attempts"] = attempts
            if attempts >= _MAX_LOGIN_ATTEMPTS:
                st.session_state["lockout_until"] = time.time() + _LOGIN_LOCKOUT_SECONDS
                st.error(f"Locked out for {_LOGIN_LOCKOUT_SECONDS // 60} minutes.")
            else:
                st.error(f"{error} ({_MAX_LOGIN_ATTEMPTS - attempts} attempts remaining)")


def _signup_form():
    email = st.text_input("Email", key="signup_email")
    password = st.text_input("Password", type="password", key="signup_password")
    confirm = st.text_input("Confirm password", type="password", key="signup_confirm")

    if st.button("Sign Up", key="signup_btn"):
        if not email or not password or not confirm:
            st.error("All fields are required.")
            return
        if not _valid_email(email):
            st.error("Invalid email format.")
            return
        if password != confirm:
            st.error("Passwords do not match.")
            return
        ok, msg = _password_strong_enough(password)
        if not ok:
            st.error(msg)
            return

        try:
            user, token = _auth.create_user(email, password)
        except Exception as e:
            if "UNIQUE" in str(e).upper():
                st.error("An account with this email already exists.")
            else:
                st.error(f"Sign-up failed: {e}")
            return

        # Send verification email
        sent = send_verification_email(user.email, token, _base_url())
        if sent:
            st.success(
                "Account created! Check your email for a verification link. "
                "After verifying, an admin must approve your account."
            )
        else:
            st.success(
                "Account created! Email sending is not configured. "
                "Ask your admin to verify and approve your account."
            )
            st.info(f"Verification token (for admin): `{token}`")


def _forgot_password_form():
    email = st.text_input("Your account email", key="forgot_email")
    if st.button("Send Reset Link", key="forgot_btn"):
        if not email:
            st.error("Enter your email.")
            return
        # Always show success to prevent email enumeration
        token, user_id = _auth.request_password_reset(email)
        if token:
            send_password_reset_email(email, token, _base_url())
        st.success("If an account with that email exists, a reset link has been sent.")


# ------------------------------------------------------------------
# Email verification handler
# ------------------------------------------------------------------

def _handle_verify_email(token: str):
    st.title("📧 Email Verification")
    user = _auth.verify_email(token)
    if user:
        st.success(f"Email confirmed for {user.email}! An admin must approve your account before you can log in.")
    else:
        st.error("Invalid or expired verification link.")
    if st.button("Go to Login"):
        st.query_params.clear()
        st.rerun()


# ------------------------------------------------------------------
# Password reset handler
# ------------------------------------------------------------------

def _handle_reset_password(token: str):
    st.title("🔑 Reset Password")
    user_id = _auth.validate_reset_token(token)
    if not user_id:
        st.error("Invalid or expired reset link.")
        if st.button("Go to Login"):
            st.query_params.clear()
            st.rerun()
        return

    new_pw = st.text_input("New password", type="password", key="reset_new_pw")
    confirm_pw = st.text_input("Confirm new password", type="password", key="reset_confirm_pw")

    if st.button("Reset Password", key="reset_btn"):
        if not new_pw or not confirm_pw:
            st.error("Both fields required.")
            return
        if new_pw != confirm_pw:
            st.error("Passwords do not match.")
            return
        ok, msg = _password_strong_enough(new_pw)
        if not ok:
            st.error(msg)
            return

        success = _auth.reset_password(token, new_pw)
        if success:
            st.success("Password updated! You can now log in.")
            st.query_params.clear()
        else:
            st.error("Reset failed. The link may have expired.")


# ------------------------------------------------------------------
# Admin panel
# ------------------------------------------------------------------

def show_admin_panel():
    """Render admin user management panel in sidebar or main area."""
    current = st.session_state.get("current_user", {})
    if not current.get("is_admin"):
        return

    st.header("🛡️ Admin Panel")

    users = _auth.list_users()
    if not users:
        st.info("No users found.")
        return

    for user in users:
        with st.expander(f"{'✅' if user.is_approved else '⏳'} {user.email} (ID: {user.id})"):
            col1, col2, col3 = st.columns(3)
            st.caption(
                f"Email confirmed: {'Yes' if user.is_email_confirmed else 'No'} | "
                f"Approved: {'Yes' if user.is_approved else 'No'} | "
                f"Admin: {'Yes' if user.is_admin else 'No'} | "
                f"Created: {user.created_at}"
            )

            with col1:
                if not user.is_approved:
                    if st.button("✅ Approve", key=f"approve_{user.id}"):
                        _auth.approve_user(user.id)
                        st.rerun()
                else:
                    if st.button("🚫 Block", key=f"block_{user.id}"):
                        _auth.block_user(user.id)
                        st.rerun()

            with col2:
                if not user.is_email_confirmed:
                    if st.button("📧 Confirm email", key=f"confirm_{user.id}"):
                        _auth.verify_email_admin(user.id)
                        st.rerun()

            with col3:
                if st.button("🗑️ Delete", key=f"del_{user.id}"):
                    _auth.delete_user(user.id)
                    st.rerun()

    # Audit log
    st.subheader("🔍 Password Reset Audit")
    events = _auth.get_reset_events()
    if events:
        for ev in events[:20]:
            st.caption(
                f"[{ev.created_at}] User {ev.user_id}: {ev.event_type} "
                f"| IP: {ev.ip_address or 'N/A'} | UA: {ev.user_agent or 'N/A'}"
            )
    else:
        st.caption("No password reset events.")
