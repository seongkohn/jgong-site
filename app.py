import os
from datetime import datetime
from flask import Flask
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from config import Config
from db import close_db, init_db

login_manager = LoginManager()
login_manager.login_view = "admin_bp.login"


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    CSRFProtect(app)
    login_manager.init_app(app)

    from models import load_user
    login_manager.user_loader(load_user)

    app.teardown_appcontext(close_db)

    with app.app_context():
        init_db()

    @app.context_processor
    def inject_globals():
        return {
            "now": datetime.utcnow,
            "turnstile_site_key": app.config["TURNSTILE_SITE_KEY"],
        }

    from routes_public import public_bp
    from routes_admin import admin_bp
    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
