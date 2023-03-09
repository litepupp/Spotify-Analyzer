from datetime import datetime
from src.server.extensions import db
from src.models.associations import genres_artists, genres_albums, genres_tracks


class Streams(db.Model):
    __tablename__: str = "streams"

    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # Many to one relationship to tracks
    track_id = db.Column(db.Integer, db.ForeignKey("tracks.id"), nullable=False)
    track = db.relationship("Tracks", back_populates="streams")

    stream_date: datetime = db.Column(db.DateTime, nullable=False, unique=True)
    ms_played: int = db.Column(db.Integer, nullable=False)
    reason_start: str = db.Column(db.String, nullable=False)
    reason_end: str = db.Column(db.String, nullable=False)
    shuffle: bool = db.Column(db.Boolean, nullable=False)
    skipped: str = db.Column(db.String, nullable=False)

    created_date: datetime = db.Column(db.DateTime)
    modified_date: datetime = db.Column(db.DateTime)


class Tracks(db.Model):
    __tablename__: str = "tracks"

    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uri: str = db.Column(db.String, nullable=False, unique=True)

    # Many to one relationship to albums
    album_id = db.Column(db.Integer, db.ForeignKey("albums.id"), nullable=False)
    album = db.relationship("Albums", back_populates="tracks")

    # One to many relationship with streams
    streams = db.relationship("Streams", back_populates="track")

    # Many to many relationship with genres using genres_tracks association table
    genres = db.relationship("Genres", secondary=genres_tracks, back_populates="tracks")

    disc_number: int = db.Column(db.Integer, nullable=False)
    duration_ms: int = db.Column(db.Integer, nullable=False)
    explicit: bool = db.Column(db.Boolean, nullable=False)
    name: str = db.Column(db.String, nullable=False)
    popularity: int = db.Column(db.Integer, nullable=False)
    preview_url: str = db.Column(db.String, nullable=False)
    track_number: int = db.Column(db.Integer, nullable=False)

    created_date: datetime = db.Column(db.DateTime)
    modified_date: datetime = db.Column(db.DateTime)


class Albums(db.Model):
    __tablename__: str = "albums"

    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uri: str = db.Column(db.String, nullable=False, unique=True)

    # One to many relationship with tracks
    tracks = db.relationship("Tracks", back_populates="album")

    # Many to many relationship with genres using genres_albums association table
    genres = db.relationship("Genres", secondary=genres_albums, back_populates="albums")

    album_type: str = db.Column(db.String, nullable=False)
    total_tracks: int = db.Column(db.Integer, nullable=False)
    name: str = db.Column(db.String, nullable=False)
    release_date: datetime = db.Column(db.DateTime, nullable=False)
    label: str = db.Column(db.String, nullable=False)
    popularity: int = db.Column(db.Integer, nullable=False)

    created_date: datetime = db.Column(db.DateTime)
    modified_date: datetime = db.Column(db.DateTime)


class Artists(db.Model):
    __tablename__: str = "artists"

    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uri: str = db.Column(db.String, nullable=False, unique=True)

    # Many to many relationship with genres using genres_artists association table
    genres = db.relationship(
        "Genres", secondary=genres_artists, back_populates="artists"
    )

    followers: int = db.Column(db.Integer, nullable=False)
    name: str = db.Column(db.String, nullable=False)
    popularity: int = db.Column(db.Integer, nullable=False)

    created_date: datetime = db.Column(db.DateTime)
    modified_date: datetime = db.Column(db.DateTime)


class Genres(db.Model):
    __tablename__: str = "genres"

    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name: str = db.Column(db.String, nullable=False, unique=True)

    # Many to many relationship with artists using genres_artists association table
    artists = db.relationship(
        "Artists", secondary=genres_artists, back_populates="genres"
    )

    # Many to many relationship with albums using genres_albums association table
    albums = db.relationship("Albums", secondary=genres_albums, back_populates="genres")

    # Many to many relationship with albums using genres_tracks association table
    tracks = db.relationship("Tracks", secondary=genres_tracks, back_populates="genres")

    created_date: datetime = db.Column(db.DateTime)
    modified_date: datetime = db.Column(db.DateTime)
