from src.server.extensions import db

# Association table for many to many relationship between genres and artists
genres_artists = db.Table(
    "genres_artists",
    db.Column(
        "genre_id",
        db.Integer,
        db.ForeignKey("genres.id"),
        primary_key=True,
        nullable=False,
    ),
    db.Column(
        "artist_id",
        db.Integer,
        db.ForeignKey("artists.id"),
        primary_key=True,
        nullable=False,
    ),
)

# Association table for many to many relationship between genres and albums
genres_albums = db.Table(
    "genres_albums",
    db.Column(
        "genre_id",
        db.Integer,
        db.ForeignKey("genres.id"),
        primary_key=True,
        nullable=False,
    ),
    db.Column(
        "album_id",
        db.Integer,
        db.ForeignKey("albums.id"),
        primary_key=True,
        nullable=False,
    ),
)

# Association table for many to many relationship between genres and tracks
genres_tracks = db.Table(
    "genres_tracks",
    db.Column(
        "genre_id",
        db.Integer,
        db.ForeignKey("genres.id"),
        primary_key=True,
        nullable=False,
    ),
    db.Column(
        "track_id",
        db.Integer,
        db.ForeignKey("tracks.id"),
        primary_key=True,
        nullable=False,
    ),
)

# Association table for many to many relationship between artists and tracks
artists_tracks = db.Table(
    "artists_tracks",
    db.Column(
        "artist_id",
        db.Integer,
        db.ForeignKey("artists.id"),
        primary_key=True,
        nullable=False,
    ),
    db.Column(
        "track_id",
        db.Integer,
        db.ForeignKey("tracks.id"),
        primary_key=True,
        nullable=False,
    ),
)

# Association table for many to many relationship between artists and albums
artists_albums = db.Table(
    "artists_albums",
    db.Column(
        "artist_id",
        db.Integer,
        db.ForeignKey("artists.id"),
        primary_key=True,
        nullable=False,
    ),
    db.Column(
        "album_id",
        db.Integer,
        db.ForeignKey("albums.id"),
        primary_key=True,
        nullable=False,
    ),
)

# Association table for many to many relationship between artists and streams
artists_streams = db.Table(
    "artists_streams",
    db.Column(
        "artist_id",
        db.Integer,
        db.ForeignKey("artists.id"),
        primary_key=True,
        nullable=False,
    ),
    db.Column(
        "stream_id",
        db.Integer,
        db.ForeignKey("streams.id"),
        primary_key=True,
        nullable=False,
    ),
)
