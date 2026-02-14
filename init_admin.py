"""Run once to create the admin user: python init_admin.py"""
import sys
from getpass import getpass
from app import create_app
from models import Admin

app = create_app()

with app.app_context():
    username = input("Admin username: ").strip()
    if not username:
        print("Username cannot be empty.")
        sys.exit(1)

    if Admin.get_by_username(username):
        print(f"User '{username}' already exists.")
        sys.exit(1)

    password = getpass("Admin password: ")
    if len(password) < 6:
        print("Password must be at least 6 characters.")
        sys.exit(1)

    Admin.create(username, password)
    print(f"Admin user '{username}' created.")
