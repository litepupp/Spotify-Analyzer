from src.server.extensions import db
from datetime import datetime


class Streams(db.Model):
    __tablename__: str = "streams"

    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)

    stream_date: datetime = db.Column(db.DateTime)

    created_date: datetime = db.Column(db.DateTime)
    modified_date: datetime = db.Column(db.DateTime)
