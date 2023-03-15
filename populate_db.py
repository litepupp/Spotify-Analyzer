import sys
import os
import json
import glob
import datetime
import re

import spotipy
from spotipy.exceptions import SpotifyException
import tqdm
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError

from src.server import create_app
from src.server.extensions import db
from src.models.models import Streams, Tracks, Albums, Artists, Genres, OldTrackUris


def sort_stream_uris(json_file_path: str) -> None:
    with open(file=json_file_path, mode="r", encoding="UTF-8") as json_file:
        try:
            json_data: list = json.load(fp=json_file)
        except ValueError:
            print(f"{json_file_path} is not a valid JSON file")
            return

    # Remove stream records with no URIs
    json_data = list(filter(lambda x: x["spotify_track_uri"] is not None, json_data))
    # Sort stream records by URI
    json_data = sorted(json_data, key=lambda x: x["spotify_track_uri"])

    with open(file=json_file_path, mode="w", encoding="UTF-8") as json_file:
        json.dump(json_data, json_file)


def aggregate_json_files(input_path: str, output_file: str) -> None:
    all_streams = []

    if not os.path.exists(path=input_path):
        sys.exit(f"input_path {input_path} does not exist")

    if os.path.exists(path=output_file):
        return

    print("Aggregating JSON files")
    for file_path in tqdm.tqdm(glob.glob(pathname=input_path + "*.json")):
        with open(file=file_path, mode="r", encoding="UTF-8") as json_file:
            try:
                json_data: list = json.load(fp=json_file)
            except ValueError:
                print(f"{file_path} is not a valid JSON file")
                continue

            for stream_object in json_data:
                all_streams.append(stream_object)

    with open(file=output_file, mode="w", encoding="UTF-8") as all_streams_file:
        print(f"Saving JSON file to {output_file}")
        json.dump(obj=all_streams, fp=all_streams_file)


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


def create_artist(artist_uri: str, sp: spotipy.Spotify) -> Artists | None:
    try:
        artist_data = sp.artist(artist_uri)
    except SpotifyException:
        return None

    artist = Artists(
        uri=artist_data["uri"],
        followers=artist_data["followers"]["total"],
        name=artist_data["name"],
        popularity=artist_data["popularity"],
        image_url=artist_data["images"][0]["url"] if artist_data["images"] else None,
        created_date=datetime.datetime.now(datetime.timezone.utc),
        modified_date=datetime.datetime.now(datetime.timezone.utc),
    )

    for artist_data_genre in artist_data["genres"]:
        artist_genre = (
            db.session.query(Genres).filter(Genres.name == artist_data_genre).first()
        )

        if artist_genre is None:
            artist_genre = Genres(name=artist_data_genre)

        artist_genre.artists.append(artist)
        db.session.add(artist_genre)

    db.session.add(artist)
    db.session.commit()

    return artist


def create_album(album_uri: str, sp: spotipy.Spotify) -> Albums | None:
    try:
        album_data = sp.album(album_uri, market="JP")
    except SpotifyException:
        return None

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
        image_url=album_data["images"][0]["url"] if album_data["images"] else None,
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
            album_artist = create_artist(album_data_artist["uri"], sp)
            if album_artist is None:
                return None

        album_artist.albums.append(album)
        db.session.add(album_artist)

    db.session.add(album)
    db.session.commit()

    return album


def create_track(stream_record_uri: str, sp: spotipy.Spotify) -> Tracks | None:
    try:
        track_data = sp.track(stream_record_uri, market="JP")
    except SpotifyException:
        return None

    track = db.session.query(Tracks).filter(Tracks.uri == track_data["uri"]).first()

    if track is not None:
        old_track_uri = OldTrackUris(old_uri=stream_record_uri, track_id=track.id)

        db.session.add(old_track_uri)
        db.session.commit()

        return track

    album = (
        db.session.query(Albums)
        .filter(Albums.uri == track_data["album"]["uri"])
        .first()
    )

    if album is None:
        album = create_album(track_data["album"]["uri"], sp)
        if album is None:
            return None

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
            track_artist = create_artist(track_data_artist["uri"], sp)
            if track_artist is None:
                return None

        track_artist.tracks.append(track)
        db.session.add(track_artist)

    db.session.add(track)
    db.session.commit()

    return track


def create_stream(stream_record: dict, track: Tracks) -> None:
    if track.duration_ms > 0:
        if (stream_record["ms_played"] / track.duration_ms) <= 1.0:
            ratio_played = stream_record["ms_played"] / track.duration_ms
        else:
            ratio_played = 1.0
    else:
        ratio_played = 0.0

    stream = Streams(
        track_id=track.id,
        album_id=track.album_id,
        stream_date=datetime.datetime.strptime(
            stream_record["ts"], "%Y-%m-%dT%H:%M:%SZ"
        ),
        ms_played=stream_record["ms_played"],
        ratio_played=ratio_played,
        reason_start=stream_record["reason_start"],
        reason_end=stream_record["reason_end"],
        shuffle=stream_record["shuffle"],
        created_date=datetime.datetime.now(datetime.timezone.utc),
        modified_date=datetime.datetime.now(datetime.timezone.utc),
    )

    for track_artist in track.artists:
        track_artist.streams.append(stream)
        try:
            db.session.add(track_artist)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()

    for album_artist in track.album.artists:
        album_artist.streams.append(stream)
        try:
            db.session.add(album_artist)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()

    try:
        db.session.add(stream)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()


def process_stream_record(stream_record: dict, sp: spotipy.Spotify) -> bool:
    track = (
        db.session.query(Tracks)
        .filter(Tracks.uri == stream_record["spotify_track_uri"])
        .first()
    )

    if track is None:
        old_track_uri = (
            db.session.query(OldTrackUris)
            .filter(OldTrackUris.old_uri == stream_record["spotify_track_uri"])
            .first()
        )

        if old_track_uri is None:
            track = create_track(stream_record["spotify_track_uri"], sp)
            if track is None:
                return False
        else:
            track = old_track_uri.track

    create_stream(stream_record, track)
    return True


def process_all_streams(
    json_file_path: str, client_id: str, client_secret: str
) -> None:
    """
    auth_manager = spotipy.oauth2.SpotifyClientCredentials(
        client_id=client_id, client_secret=client_secret
    )
    """
    auth_manager = spotipy.oauth2.SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri="http://example.com/",
    )
    sp = spotipy.Spotify(auth_manager=auth_manager, language="ja")

    with open(file=json_file_path, mode="r", encoding="UTF-8") as json_file:
        try:
            json_data: list = json.load(fp=json_file)
        except ValueError:
            print(f"{json_file_path} is not a valid JSON file")
            return

        print("Processing Stream data")
        for stream_record in tqdm.tqdm(json_data):
            if stream_record["spotify_track_uri"] is None:
                continue

            if not process_stream_record(stream_record, sp):
                print("Error")


if __name__ == "__main__":
    INPUT_PATH = "./data/input/"
    OUTPUT_FILE = "./data/output/all_streams.json"
    AUTH_PATH = "./auth.txt"
    CLIENT_ID = ""
    CLIENT_SECRET = ""

    with open(file=AUTH_PATH, mode="r", encoding="ascii") as file:
        CLIENT_ID, CLIENT_SECRET = file.readlines()

    CLIENT_ID = CLIENT_ID.rstrip()
    CLIENT_SECRET = CLIENT_SECRET.rstrip()

    aggregate_json_files(INPUT_PATH, OUTPUT_FILE)
    sort_stream_uris(OUTPUT_FILE)

    app = create_app()
    with app.app_context():
        process_all_streams(OUTPUT_FILE, CLIENT_ID, CLIENT_SECRET)
