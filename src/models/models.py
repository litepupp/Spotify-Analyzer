from src.server.extensions import db
from datetime import datetime


class Streams(db.Model):
    __tablename__: str = "streams"

    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)

    stream_date: datetime = db.Column(db.DateTime)

    created_date: datetime = db.Column(db.DateTime)
    modified_date: datetime = db.Column(db.DateTime)

    def __init__(self, stream_date: datetime) -> None:
        self.stream_date = stream_date
