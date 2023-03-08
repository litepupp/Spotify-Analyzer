from flask import Flask
from src.routes import register_blueprints
from .extensions import db, migrate
from .config import Config


def create_app(config: Config = Config) -> Flask:
    app: Flask = Flask(import_name=__name__)

    if config:
        app.config.from_object(obj=config)

    db.init_app(app=app)
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    migrate.init_app(app=app, db=db)

    register_blueprints(app)

    return app
