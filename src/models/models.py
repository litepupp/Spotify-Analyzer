from src.server.extensions import db
from datetime import datetime


class Streams(db.Model):
    __tablename__: str = "streams"

    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)

    stream_date: datetime = db.Column(db.DateTime, nullable=False, unique=True)
    ms_played: int = db.Column(db.Integer, nullable=False)

    reason_start: str = db.Column(db.String, nullable=False)
    reason_end: str = db.Column(db.String, nullable=False)
    shuffle: bool = db.Column(db.Boolean, nullable=False)
    skipped: str = db.Column(db.String, nullable=False)

    created_date: datetime = db.Column(db.DateTime)
    modified_date: datetime = db.Column(db.DateTime)
