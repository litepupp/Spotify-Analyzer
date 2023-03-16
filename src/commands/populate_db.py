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
    """
    ...
    """

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


def db_create_album(album_data: dict, data_cache: dict, sp: spotipy.Spotify) -> Albums:
    """
    ...
    """

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

    db.session.add(album)
    db.session.commit()

    for album_data_artist in album_data["artists"]:
        album_artist = db_get_artist(album_data_artist["uri"])

        if album_artist is None:
            if album_data_artist["uri"] not in data_cache["artists"]:
                data_cache["artists"][album_data_artist["uri"]] = {
                    "tracks": set(),
                    "albums": set(),
                }

            data_cache["artists"][album_data_artist["uri"]]["albums"].add(
                album_data["uri"]
            )

            # If total artists in data_cache reach 50, create artists
            # when finished, clear dict of artists and albums/tracks relating to artist
            if len(data_cache["artists"].keys()) == 50:
                get_artist_data(data_cache, sp)
                data_cache["artists"].clear()
        else:
            album_artist.tracks.append(album)
            db.session.add(album_artist)

    db.session.commit()
    return album


def db_create_track(
    track_data: dict, album: Albums | None, sp: spotipy.Spotify, data_cache: dict
) -> None:
    """
    ...
    """

    # Create new track object to be inserted into database
    track = Tracks(
        uri=track_data["uri"],
        album_id=album.id if album is not None else None,
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

    # Add the track
    db.session.add(track)
    db.session.commit()

    # For each artist_uri that belongs to track
    for track_data_artist in track_data["artists"]:
        track_artist = db_get_artist(track_data_artist["uri"])

        # If artist does not exist for that specific uri in database
        if track_artist is None:
            # In the data_cache, add set for tracks
            # and album uris that belong to current artist
            if track_data_artist["uri"] not in data_cache["artists"]:
                data_cache["artists"][track_data_artist["uri"]] = {
                    "tracks": set(),
                    "albums": set(),
                }

            # Add current track_uri to set of tracks that belong to artist
            data_cache["artists"][track_data_artist["uri"]]["tracks"].add(
                track_data["uri"]
            )

            # If total artists in data_cache reach 50, create artists
            # when finished, clear dict of artists and albums/tracks relating to artist
            if len(data_cache["artists"].keys()) == 50:
                get_artist_data(data_cache, sp)
                data_cache["artists"].clear()
        else:
            track_artist.tracks.append(track)
            db.session.add(track_artist)

    db.session.commit()


def get_artist_data(data_cache: dict, sp: spotipy.Spotify) -> None:
    """
    ...
    """

    artists_data: list[dict] = sp.artists(list(data_cache["artists"].keys()))

    for artist_data in artists_data:
        artist = db_create_artist(artist_data)

        for track_uri in list(data_cache["artists"][artist_data["uri"]]["tracks"]):
            track = db_get_track(track_uri)
            artist.tracks.append(track)
            db.session.add(track)

        for album_uri in list(data_cache["artists"][artist_data["uri"]]["albums"]):
            album = db_get_album(album_uri)
            artist.albums.append(album)
            db.session.add(album)

        db.session.commit()


def get_album_data(album_uris: str, sp: spotipy.Spotify, data_cache: dict) -> None:
    """
    ...
    """

    albums_data = sp.albums(album_uris, market="JP")

    for album_data in albums_data:
        album = db_create_album(album_data, data_cache, sp)

        for track_uri in list(data_cache["album"][album_data["uri"]]):
            track = db_get_track(track_uri)
            album.tracks.append(track)
            db.session.add(track)

        db.session.commit()


def get_track_data(
    track_uris: list[str], sp: spotipy.Spotify, data_cache: dict
) -> None:
    """
    ...
    """

    # List of 50 track objects returned by spotify API
    tracks_data: list[dict] = sp.tracks(track_uris, market="JP")

    for i, track_data in enumerate(tracks_data):
        # Attempt to get track from database by current track_data uri
        track = db_get_track(track_data["uri"])
        if track is not None:
            # If the track does exist after calling the API,
            # add the original track_uri from the stream
            # to the mapping table to the actual track_item in the database and skip track data
            old_track_uri = OldTrackUris(old_uri=track_uris[i], track_id=track.id)

            db.session.add(old_track_uri)
            db.session.commit()
            continue

        # Attempt to get album from database by current track_data album uri
        album = db_get_album(track_data["album"]["uri"])
        # Create a track with track_data, its relationship to its album
        # is set if an album actually exists for its album_uri
        db_create_track(track_data, album, sp, data_cache)
        if album is not None:
            # If album was actually found in db, continue to next track_data
            # since relationship has already been set and the album_uri does not need
            # to be set in the data_cache
            continue

        if track_data["album"]["uri"] not in data_cache["album"]:
            data_cache["album"][track_data["album"]["uri"]] = set()

        data_cache["album"][track_data["album"]["uri"]].add(track_data["uri"])
        if len(data_cache["album"].keys()) == 50:
            get_album_data(data_cache["album"].keys(), sp, data_cache)
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
