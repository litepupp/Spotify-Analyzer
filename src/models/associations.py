from src.server.extensions import db

# Association table for many to many relationship between genres and artists
genre_artist = db.Table(
    "genres_artists",
    db.Column("genre_id", db.Integer, db.ForeignKey("genres.id"), primary_key=True),
    db.Column("artist_id", db.Integer, db.ForeignKey("artists.id"), primary_key=True),
)


