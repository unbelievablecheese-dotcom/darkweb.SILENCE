import os
import secrets
from pathlib import Path

from flask import Flask, jsonify, redirect, request, url_for
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
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
        elif database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    else:
        database_url = f"sqlite:///{database_path.as_posix()}"

    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        SQLALCHEMY_DATABASE_URI=database_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.init_app(app)

    @login_manager.unauthorized_handler
    def handle_unauthorized():
        if request.endpoint == "views.harvey_chat":
            return jsonify(
                error="Your session has expired. Sign in again to continue.",
                loginUrl=url_for("auth.login"),
            ), 401
        return redirect(url_for(login_manager.login_view, next=request.full_path))

    from .views import PLAYER_ROSTER, is_coach, views
    from .auth import auth
    from .coach import coach

    app.register_blueprint(views)
    app.register_blueprint(auth)
    app.register_blueprint(coach)
    app.jinja_env.globals['is_coach'] = is_coach

    from .models import CoachRequest, PlayerApplication, PlayerProfile, User

    with app.app_context():
        db.create_all()
        schema_additions = {
            CoachRequest.__tablename__: {'last_email_sent_at': 'INTEGER'},
            PlayerApplication.__tablename__: {'status_code_hash': 'VARCHAR(64)'},
            PlayerProfile.__tablename__: {'rank': 'VARCHAR(120)'},
        }
        inspector = db.inspect(db.engine)
        for table_name, columns in schema_additions.items():
            existing_columns = {column['name'] for column in inspector.get_columns(table_name)}
            for column_name, column_type in columns.items():
                if column_name not in existing_columns:
                    with db.engine.begin() as connection:
                        connection.execute(
                            db.text(f'ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}')
                        )
        for player in PLAYER_ROSTER:
            if db.session.get(PlayerProfile, player['slug']) is None:
                db.session.add(PlayerProfile(slug=player['slug'], name=player['name']))
        db.session.commit()

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return db.session.get(User, int(user_id))
        except (TypeError, ValueError):
            return None

    return app