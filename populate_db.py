import sys
import os
import json
import glob
import datetime

import spotipy
import tqdm
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError

from src.server import create_app
from src.server.extensions import db
from src.models.models import Streams, Tracks, Albums, Artists, Genres

INPUT_PATH = "./data/input/"
OUTPUT_PATH = "./data/output/"
AUTH_PATH = "./auth.txt"


def parse_release_date(
    release_date: str, release_date_precision: str
) -> datetime.datetime:
    if release_date_precision == "year":
        if int(release_date) > 0:
            return datetime.datetime.strptime(release_date, "%Y")
        return datetime.datetime.now()
    elif release_date_precision == "month":
        return datetime.datetime.strptime(release_date, "%Y-%m")
    elif release_date_precision == "day":
        return datetime.datetime.strptime(release_date, "%Y-%m-%d")
    else:
        return datetime.datetime.now()


def preprocess_streams(
    input_path: str,
    output_path: str,
    client_id: str,
    client_secret: str,
    db: SQLAlchemy,
) -> None:
    """
    ...
    """
    auth_manager = spotipy.oauth2.SpotifyOAuth(
        client_id=client_id,
        client_secret=client_id,
        redirect_uri="http://example.com/",
    )
    sp = spotipy.Spotify(auth_manager=auth_manager)

    if not os.path.exists(path=input_path):
        sys.exit(f"input_path {input_path} does not exist")

    if not os.path.exists(path=input_path):
        os.makedirs(name=output_path)

    for file_path in glob.glob(pathname=input_path + "*.json"):
        with open(file=file_path, mode="r", encoding="UTF-8") as json_file:
            try:
                json_data: list = json.load(fp=json_file)
            except ValueError:
                print(f"{file_path} is not a valid JSON file")
                continue

            print(f"Processing {file_path}")
            for stream_record in tqdm.tqdm(json_data):
                if stream_record["spotify_track_uri"] is None:
                    continue

                track_data = sp.track(stream_record["spotify_track_uri"], market="JP")

                track = (
                    db.session.query(Tracks)
                    .filter(Tracks.uri == track_data["uri"])
                    .first()
                )
                if track is None:
                    album = (
                        db.session.query(Albums)
                        .filter(Albums.uri == track_data["album"]["uri"])
                        .first()
                    )
                    if album is None:
                        album_data = sp.album(track_data["album"]["uri"], market="JP")

                        album = Albums(
                            uri=album_data["uri"],
                            album_type=album_data["album_type"],
                            total_tracks=album_data["total_tracks"],
                            name=album_data["name"],
                            release_date=parse_release_date(
                                album_data["release_date"],
                                album_data["release_date_precision"],
                            ),
                            label=album_data["label"],
                            popularity=album_data["popularity"],
                            created_date=datetime.datetime.now(datetime.timezone.utc),
                            modified_date=datetime.datetime.now(datetime.timezone.utc),
                        )

                        for album_data_artist in album_data["artists"]:
                            album_artist = (
                                db.session.query(Artists)
                                .filter(Artists.uri == album_data_artist["uri"])
                                .first()
                            )

                            if album_artist is None:
                                album_artist_data = sp.artist(album_data_artist["uri"])
                                album_artist = Artists(
                                    uri=album_artist_data["uri"],
                                    followers=album_artist_data["followers"]["total"],
                                    name=album_artist_data["name"],
                                    popularity=album_artist_data["popularity"],
                                    created_date=datetime.datetime.now(
                                        datetime.timezone.utc
                                    ),
                                    modified_date=datetime.datetime.now(
                                        datetime.timezone.utc
                                    ),
                                )

                                for album_artist_data_genre in album_artist_data[
                                    "genres"
                                ]:
                                    album_artist_genre = (
                                        db.session.query(Genres)
                                        .filter(Genres.name == album_artist_data_genre)
                                        .first()
                                    )

                                    if album_artist_genre is None:
                                        album_artist_genre = Genres(
                                            name=album_artist_data_genre,
                                            created_date=datetime.datetime.now(
                                                datetime.timezone.utc
                                            ),
                                            modified_date=datetime.datetime.now(
                                                datetime.timezone.utc
                                            ),
                                        )

                                    album_artist_genre.artists.append(album_artist)
                                    db.session.add(album_artist_genre)

                            album_artist.albums.append(album)
                            db.session.add(album_artist)

                        for album_data_genre in album_data["genres"]:
                            album_genre = (
                                db.session.query(Genres)
                                .filter(Genres.name == album_data_genre)
                                .first
                            )

                            if album_genre is None:
                                album_genre = Genres(
                                    name=album_data_genre,
                                    created_date=datetime.datetime.now(
                                        datetime.timezone.utc
                                    ),
                                    modified_date=datetime.datetime.now(
                                        datetime.timezone.utc
                                    ),
                                )

                            album_genre.albums.append(album)
                            db.session.add(album_genre)

                        db.session.add(album)
                        db.session.commit()

                    track = Tracks(
                        uri=track_data["uri"],
                        album_id=album.id,
                        disc_number=track_data["disc_number"],
                        duration_ms=track_data["duration_ms"],
                        explicit=track_data["explicit"],
                        name=track_data["name"],
                        popularity=track_data["popularity"],
                        preview_url=track_data["preview_url"],
                        track_number=track_data["track_number"],
                        created_date=datetime.datetime.now(datetime.timezone.utc),
                        modified_date=datetime.datetime.now(datetime.timezone.utc),
                    )

                    for track_data_artist in track_data["artists"]:
                        track_artist = (
                            db.session.query(Artists)
                            .filter(Artists.uri == track_data_artist["uri"])
                            .first()
                        )

                        if track_artist is None:
                            track_artist_data = sp.artist(track_data_artist["uri"])
                            track_artist = Artists(
                                uri=track_artist_data["uri"],
                                followers=track_artist_data["followers"]["total"],
                                name=track_artist_data["name"],
                                popularity=track_artist_data["popularity"],
                                created_date=datetime.datetime.now(
                                    datetime.timezone.utc
                                ),
                                modified_date=datetime.datetime.now(
                                    datetime.timezone.utc
                                ),
                            )

                            for track_artist_data_genre in track_artist_data["genres"]:
                                track_artist_genre = (
                                    db.session.query(Genres)
                                    .filter(Genres.name == track_artist_data_genre)
                                    .first()
                                )

                                if track_artist_genre is None:
                                    track_artist_genre = Genres(
                                        name=track_artist_data_genre,
                                        created_date=datetime.datetime.now(
                                            datetime.timezone.utc
                                        ),
                                        modified_date=datetime.datetime.now(
                                            datetime.timezone.utc
                                        ),
                                    )

                                track_artist_genre.artists.append(track_artist)
                                db.session.add(track_artist_genre)

                        track_artist.tracks.append(track)
                        db.session.add(track_artist)

                    if "genres" in track_data:
                        for track_data_genre in track_data["genres"]:
                            track_genre = (
                                db.session.query(Genres)
                                .filter(Genres.name == track_data_genre)
                                .first
                            )

                            if track_genre is None:
                                track_genre = Genres(
                                    name=track_data_genre,
                                    created_date=datetime.datetime.now(
                                        datetime.timezone.utc
                                    ),
                                    modified_date=datetime.datetime.now(
                                        datetime.timezone.utc
                                    ),
                                )

                            track_genre.tracks.append(track)
                            db.session.add(track_genre)

                    db.session.add(track)
                    db.session.commit()

                stream = Streams(
                    track_id=track.id,
                    album_id=track.album_id,
                    stream_date=datetime.datetime.strptime(
                        stream_record["ts"], "%Y-%m-%dT%H:%M:%SZ"
                    ),
                    ms_played=stream_record["ms_played"],
                    ratio_played=(stream_record["ms_played"] / track.duration_ms)
                    if ((stream_record["ms_played"] / track.duration_ms) <= 1.0)
                    else 1.0,
                    reason_start=stream_record["reason_start"],
                    reason_end=stream_record["reason_end"],
                    shuffle=stream_record["shuffle"],
                    created_date=datetime.datetime.now(datetime.timezone.utc),
                    modified_date=datetime.datetime.now(datetime.timezone.utc),
                )

                try:
                    db.session.add(stream)
                    db.session.commit()
                except IntegrityError:
                    db.session.rollback()


if __name__ == "__main__":
    CLIENT_ID = ""
    CLIENT_SECRET = ""
    with open(file=AUTH_PATH, mode="r", encoding="ascii") as file:
        CLIENT_ID, CLIENT_SECRET = file.readlines()

    app = create_app()
    with app.app_context():
        preprocess_streams(INPUT_PATH, OUTPUT_PATH, CLIENT_ID, CLIENT_SECRET, db)
