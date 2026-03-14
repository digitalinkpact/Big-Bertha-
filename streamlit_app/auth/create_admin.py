#!/usr/bin/env python3
"""Create the first admin user.  Run once after deployment.

Usage:
    python -m streamlit_app.auth.create_admin admin@example.com YourPassword123
"""

from __future__ import annotations

import sys


def main():
    if len(sys.argv) < 3:
        print("Usage: python -m streamlit_app.auth.create_admin <email> <password>")
        sys.exit(1)

    email = sys.argv[1]
    password = sys.argv[2]

    from streamlit_app.auth.db import init_db
    from streamlit_app.auth.service import AuthService

    init_db()
    auth = AuthService()

    try:
        user, _token = auth.create_user(email, password)
    except Exception as e:
        if "UNIQUE" in str(e).upper():
            print(f"User {email} already exists.")
            sys.exit(1)
        raise

    # Mark as confirmed + approved + admin
    auth.verify_email_admin(user.id)
    auth.approve_user(user.id)
    auth.make_admin(user.id)

    print(f"Admin user created: {email} (ID: {user.id})")
    print("You can now log in with this email and password.")


if __name__ == "__main__":
    main()
