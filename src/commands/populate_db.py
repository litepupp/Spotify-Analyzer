#!/usr/bin/env python3

import glob
import json
import os
import sys
import datetime

import tqdm
import spotipy
from flask_sqlalchemy import SQLAlchemy

from src.server import create_app
from src.server.extensions import db
from src.models.models import Streams, Tracks, Albums, Artists, Genres, OldTrackUris


def create_spotify_client(auth_file_path: str) -> spotipy.Spotify:
    with open(file=auth_file_path, mode="r", encoding="ascii") as file:
        client_id, client_secret = file.readlines()

    client_id = client_id.rstrip()
    client_secret = client_secret.rstrip()

    auth_manager = spotipy.oauth2.SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri="http://example.com/",
    )
    client = spotipy.Spotify(auth_manager=auth_manager, language="ja")

    return client


def get_unique_track_uris(input_path: str) -> list[str]:
    all_track_uris: list[str] = []

    if not os.path.exists(path=input_path):
        sys.exit(f"input_path {input_path} does not exist")

    print("Getting unique track URIs")
    for file_path in tqdm.tqdm(glob.glob(pathname=input_path + "*.json")):
        with open(file=file_path, mode="r", encoding="UTF-8") as json_file:
            try:
                json_data: list[dict] = json.load(fp=json_file)
            except ValueError:
                print(f"{file_path} is not a valid JSON file")
                continue

            for stream_object in tqdm.tqdm(json_data, leave=False):
                all_track_uris.append(stream_object["spotify_track_uri"])

    unique_track_uris: list[str] = list(set(all_track_uris))

    return unique_track_uris


def db_get_track(track_uri: str) -> Tracks | None:
    track: Tracks | None = (
        db.session.query(Tracks).filter(Tracks.uri == track_uri).first()
    )

    if track is None:
        old_track_uri: OldTrackUris | None = (
            db.session.query(OldTrackUris)
            .filter(OldTrackUris.old_uri == track_uri)
            .first()
        )

        if old_track_uri is None:
            return None
        else:
            return old_track_uri.track

    return track


def db_get_album(album_uri: str) -> Albums | None:
    album: Albums | None = (
        db.session.query(Albums).filter(Albums.uri == album_uri).first()
    )

    return album


def db_get_artist(artist_uri: str) -> Artists | None:
    artist: Artists | None = (
        db.session.query(Artists).filter(Artists.uri == artist_uri).first()
    )

    return artist


def db_create_artist(artist_data: dict) -> None:
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


def get_artist_data(data_cache: dict, sp: spotipy.Spotify) -> None:
    artists_data: list[dict] = sp.artists(list(data_cache["artists"].keys()))

    for artist_data in artists_data:
        artist = db_create_artist(artist_data)

        for track_uri in list(data_cache["artists"][artist_data["uri"]]["tracks"]):
            track = db_get_track(track_uri)
            artist.tracks.append(track)

        for album_uri in list(data_cache["artists"][artist_data["uri"]]["albums"]):
            album = db_get_album(album_uri)
            artist.albums.append(album)


def db_create_track(
    track_data: dict, album: Albums, sp: spotipy.Spotify, data_cache: dict
) -> None:
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

    db.session.add(track)
    db.session.commit()

    for track_data_artist in track_data["artists"]:
        track_artist = db_get_artist(track_data_artist["uri"])

        if track_artist is None:
            if track_data_artist["uri"] not in data_cache["artists"]:
                data_cache["artists"][track_data_artist["uri"]] = {
                    "tracks": set(),
                    "albums": set(),
                }

            data_cache["artists"][track_data_artist["uri"]]["tracks"].add(
                track_data["uri"]
            )

            if len(data_cache["artists"].keys()) == 50:
                get_artist_data(data_cache, sp)
                data_cache["artists"].clear()
        else:
            track_artist.tracks.append(track)
            db.session.add(track_artist)

    db.session.commit()


def get_track_data(
    track_uris: list[str], sp: spotipy.Spotify, data_cache: dict
) -> None:
    """
    ...
    """
    
    # 
    tracks_data: list[dict] = sp.tracks(track_uris, market="JP")

    for i, track_data in enumerate(tracks_data):
        track = db_get_track(track_data["uri"])
        if track is not None:
            old_track_uri = OldTrackUris(old_uri=track_uris[i], track_id=track.id)

            db.session.add(old_track_uri)
            db.session.commit()
            continue

        album = db_get_album(track_data["album"]["uri"])
        if album is not None:
            db_create_track(track_data, album, sp, data_cache)
            continue

        if track_data["album"]["uri"] not in data_cache["album"]:
            data_cache["album"][track_data["album"]["uri"]] = set()

        data_cache["album"][album_uri].add(track_data["uri"])
        if len(data_cache["album"].keys()) == 50:
            process_album_uris(data_cache["album"].keys(), sp, data_cache)
            data_cache["album"].clear()


def process_track_uris(
    track_uris: list[str], sp: spotipy.Spotify, data_cache: dict
) -> None:
    """
    ...
    """

    # List for storing batches of 50 track_uris for the spotify API
    track_uri_batch: list[str] = []

    print("\nProcessing track URIs")
    for track_uri in tqdm.tqdm(track_uris):
        # Attempt to get a track for specific track_uri
        track = db_get_track(track_uri)
        # If this track exists in the tracks table, skip this track_uri
        if track is not None:
            continue

        # Add this track_uri to the batch
        track_uri_batch.append(track_uri)
        if len(track_uri_batch) == 50:
            # Whenever the size of the batch reaches 50 track_uris, process them and clear the list
            get_track_data(track_uri_batch, sp, data_cache)
            track_uri_batch.clear()


def main() -> None:
    """
    ...
    """

    # Path holding all endsong.json files
    INPUT_PATH = "../../data/input/"
    # Path to file that contains client_id / client_secret
    AUTH_FILE_PATH = "./auth.txt"

    # Create new spotipy client using credentials in AUTH_FILE_PATH
    sp: spotipy.Spotify = create_spotify_client(AUTH_FILE_PATH)
    # Get list of all unique track_uris in streams data
    unique_track_uris: list[str] = get_unique_track_uris(INPUT_PATH)

    # Create cache for album and artist uris ...
    data_cache: dict = {"albums": {}, "artists": {}}

    # Create app and use context to access database
    app = create_app()
    with app.app_context():
        # Begin processing all unique track_uris from streams
        process_track_uris(unique_track_uris, sp, data_cache)


if __name__ == "__main__":
    main()
