from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_db


class Admin(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def get_by_id(user_id):
        row = get_db().execute("SELECT * FROM admin WHERE id = ?", (user_id,)).fetchone()
        if row:
            return Admin(row["id"], row["username"], row["password_hash"])
        return None

    @staticmethod
    def get_by_username(username):
        row = get_db().execute("SELECT * FROM admin WHERE username = ?", (username,)).fetchone()
        if row:
            return Admin(row["id"], row["username"], row["password_hash"])
        return None

    @staticmethod
    def create(username, password):
        db = get_db()
        db.execute(
            "INSERT INTO admin (username, password_hash) VALUES (?, ?)",
            (username, generate_password_hash(password)),
        )
        db.commit()


def load_user(user_id):
    return Admin.get_by_id(int(user_id))
