from datetime import datetime
from src.server.extensions import db
from src.models.associations import (
    genres_artists,
    genres_albums,
    genres_tracks,
    artists_tracks,
    artists_albums,
    artists_streams,
)


class TrackUris(db.Model):
    __tablename__: str = "track_uris"

    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uri = db.Column(db.String, nullable=False, unique=True)

    # Many to one relationship to tracks
    track_id = db.Column(db.Integer, db.ForeignKey("tracks.id"), nullable=False)
    track = db.relationship("Tracks", back_populates="uris")


class Streams(db.Model):
    __tablename__: str = "streams"

    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # Many to one relationship to tracks
    track_id = db.Column(db.Integer, db.ForeignKey("tracks.id"), nullable=False)
    track = db.relationship("Tracks", back_populates="streams")

    # Many to one relationship to albums
    album_id = db.Column(db.Integer, db.ForeignKey("albums.id"), nullable=False)
    album = db.relationship("Albums", back_populates="streams")

    # Many to many relationship with artists using artists_streams association table
    artists = db.relationship(
        "Artists", secondary=artists_streams, back_populates="streams"
    )

    stream_date: datetime = db.Column(db.DateTime, nullable=False)
    ms_played: int = db.Column(db.Integer, nullable=False)
    ratio_played: float = db.Column(db.Numeric(asdecimal=False), nullable=False)
    reason_start: str = db.Column(db.String, nullable=False)
    reason_end: str = db.Column(db.String, nullable=False)
    shuffle: bool = db.Column(db.Boolean, nullable=False)

    created_date: datetime = db.Column(db.DateTime, nullable=False)
    modified_date: datetime = db.Column(db.DateTime, nullable=False)


class Tracks(db.Model):
    __tablename__: str = "tracks"

    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uri = db.Column(db.String, nullable=False, unique=True)

    # One to many relationship with track_uris
    uris = db.relationship("TrackUris", back_populates="track")

    # Many to one relationship to albums
    album_id = db.Column(db.Integer, db.ForeignKey("albums.id"))
    album = db.relationship("Albums", back_populates="tracks")

    # Many to many relationship with artists using artists_tracks association table
    artists = db.relationship(
        "Artists", secondary=artists_tracks, back_populates="tracks"
    )

    # One to many relationship with streams
    streams = db.relationship("Streams", back_populates="track")

    # Many to many relationship with genres using genres_tracks association table
    genres = db.relationship("Genres", secondary=genres_tracks, back_populates="tracks")

    disc_number: int = db.Column(db.Integer, nullable=False)
    duration_ms: int = db.Column(db.Integer, nullable=False)
    explicit: bool = db.Column(db.Boolean, nullable=False)
    name: str = db.Column(db.String, nullable=False)
    popularity: int = db.Column(db.Integer, nullable=False)
    preview_url: str = db.Column(db.String)
    track_number: int = db.Column(db.Integer, nullable=False)

    acousticness: float = db.Column(db.Numeric(asdecimal=False))
    danceability: float = db.Column(db.Numeric(asdecimal=False))
    energy: float = db.Column(db.Numeric(asdecimal=False))
    instrumentalness: float = db.Column(db.Numeric(asdecimal=False))
    key: int = db.Column(db.Integer)
    liveness: float = db.Column(db.Numeric(asdecimal=False))
    loudness: float = db.Column(db.Numeric(asdecimal=False))
    mode: int = db.Column(db.Integer)
    speechiness: float = db.Column(db.Numeric(asdecimal=False))
    tempo: float = db.Column(db.Numeric(asdecimal=False))
    time_signature: float = db.Column(db.Numeric(asdecimal=False))
    valence: float = db.Column(db.Numeric(asdecimal=False))

    created_date: datetime = db.Column(db.DateTime, nullable=False)
    modified_date: datetime = db.Column(db.DateTime, nullable=False)


class Albums(db.Model):
    __tablename__: str = "albums"

    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uri: str = db.Column(db.String, nullable=False, unique=True)

    # One to many relationship with tracks
    tracks = db.relationship("Tracks", back_populates="album")

    # Many to many relationship with artists using artists_albums association table
    artists = db.relationship(
        "Artists", secondary=artists_albums, back_populates="albums"
    )

    # One to many relationship with streams
    streams = db.relationship("Streams", back_populates="album")

    # Many to many relationship with genres using genres_albums association table
    genres = db.relationship("Genres", secondary=genres_albums, back_populates="albums")

    album_type: str = db.Column(db.String, nullable=False)
    total_tracks: int = db.Column(db.Integer, nullable=False)
    name: str = db.Column(db.String, nullable=False)
    release_date: datetime = db.Column(db.DateTime, nullable=False)
    label: str = db.Column(db.String)
    popularity: int = db.Column(db.Integer, nullable=False)
    image_url: str = db.Column(db.String)

    created_date: datetime = db.Column(db.DateTime, nullable=False)
    modified_date: datetime = db.Column(db.DateTime, nullable=False)


class Artists(db.Model):
    __tablename__: str = "artists"

    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uri: str = db.Column(db.String, nullable=False, unique=True)

    # Many to many relationship with tracks using artists_tracks association table
    tracks = db.relationship(
        "Tracks", secondary=artists_tracks, back_populates="artists"
    )

    # Many to many relationship with albums using artists_albums association table
    albums = db.relationship(
        "Albums", secondary=artists_albums, back_populates="artists"
    )

    # Many to many relationship with streams using artists_streams association table
    streams = db.relationship(
        "Streams", secondary=artists_streams, back_populates="artists"
    )

    # Many to many relationship with genres using genres_artists association table
    genres = db.relationship(
        "Genres", secondary=genres_artists, back_populates="artists"
    )

    followers: int = db.Column(db.Integer, nullable=False)
    name: str = db.Column(db.String, nullable=False)
    popularity: int = db.Column(db.Integer, nullable=False)
    image_url: str = db.Column(db.String)

    created_date: datetime = db.Column(db.DateTime, nullable=False)
    modified_date: datetime = db.Column(db.DateTime, nullable=False)


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
