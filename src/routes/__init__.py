from flask import Blueprint, Flask
from flask_restx import Api, Resource

from src.routes.streams import api as streams_api


def register_blueprints(app: Flask) -> None:
    blueprint = Blueprint(name="api_v1", import_name=__name__, url_prefix="/api")
    api = Api(app=blueprint, doc="/docs")
    app.register_blueprint(blueprint=blueprint)

    api.add_namespace(streams_api)
