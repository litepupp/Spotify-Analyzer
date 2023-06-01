import os


class Config(object):
    APP_DIR: str = os.path.abspath(os.path.dirname(__file__))
    PROJECT_ROOT: str = os.path.abspath(os.path.join(APP_DIR, os.pardir))

    SQLALCHEMY_DATABASE_URI: str = "sqlite:///data.db"
