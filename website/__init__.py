import os
import secrets
from pathlib import Path

from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
login_manager = LoginManager()


def create_app(test_config=None):
    app = Flask(__name__)
    instance_path = Path(app.instance_path or "instance")
    instance_path.mkdir(parents=True, exist_ok=True)
    database_path = Path(os.environ.get("DATABASE_PATH", instance_path / "database.db"))
    database_path.parent.mkdir(parents=True, exist_ok=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{database_path.as_posix()}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.init_app(app)

    from .views import views
    from .auth import auth

    app.register_blueprint(views)
    app.register_blueprint(auth)

    from .models import User

    with app.app_context():
        db.create_all()

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return db.session.get(User, int(user_id))
        except (TypeError, ValueError):
            return None

    return app