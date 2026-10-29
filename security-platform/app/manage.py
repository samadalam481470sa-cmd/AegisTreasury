"""CLI: python -m app.manage init-admin / seed-demo"""
import argparse
import getpass
from .db import database, init_db
from .security import hash_password
from .seed import seed


def main():
    parser = argparse.ArgumentParser(description="AegisLedger Ops administration")
    commands = parser.add_subparsers(dest="command", required=True)
    admin = commands.add_parser("init-admin", help="Interactively create an administrator")
    admin.add_argument("--email", required=True)
    user = commands.add_parser("create-user", help="Create analyst or viewer account")
    user.add_argument("--email", required=True)
    user.add_argument("--role", choices=["analyst", "viewer"], required=True)
    commands.add_parser("seed-demo", help="Seed SYNTHETIC events and services (safe to re-run)")
    args = parser.parse_args()
    init_db()
    if args.command == "seed-demo":
        with database() as db:
            counts = seed(db)
        print(f"Synthetic demo loaded: {counts}")
        return
    role = "admin" if args.command == "init-admin" else args.role
    email = args.email.strip().lower()
    password = getpass.getpass("Choose a strong password (14+ chars): ")
    if password != getpass.getpass("Confirm password: "):
        raise SystemExit("Passwords do not match")
    with database() as db:
        try:
            db.execute("INSERT INTO users(email,password_hash,role) VALUES(?,?,?)", (email, hash_password(password), role))
        except Exception as exc:
            if "UNIQUE constraint failed" in str(exc):
                raise SystemExit("User already exists") from exc
            raise
    print(f"Created {role} user: {email}")


if __name__ == "__main__":
    main()
