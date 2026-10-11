"""Provision trusted employees from a private terminal, without logging passwords."""

import argparse
from getpass import getpass

from auth.security import hash_password
from database import SessionLocal
from models.user import User, UserRole


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--role", choices=[role.value for role in UserRole], default="agent")
    args = parser.parse_args()
    password = getpass("New password (hidden): ")
    if len(password) < 12:
        parser.error("Use a password with at least 12 characters")
    if password != getpass("Repeat password: "):
        parser.error("Passwords did not match")
    with SessionLocal() as db:
        if db.query(User).filter((User.username == args.username) | (User.email == args.email)).first():
            parser.error("Username or email already exists; no existing account was changed")
        db.add(User(username=args.username, email=args.email, role=UserRole(args.role),
                    hashed_password=hash_password(password)))
        db.commit()
    print("Employee account created.")


if __name__ == "__main__":
    main()
