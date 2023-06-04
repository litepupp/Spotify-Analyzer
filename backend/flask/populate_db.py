#!/usr/bin/env python3

import glob
import json
import os
import sys
import datetime

import tqdm
import spotipy
from src.utils.populate_db.populator import Populator

from src.server import create_app
from src.server.extensions import db
from src.models.models import Streams, Tracks, Albums, Artists, Genres, TrackUris


def create_spotify_client(auth_file_path: str) -> spotipy.Spotify:
    """
    ...
    """

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


def load_stream_objects(input_path: str) -> tuple[set[str], list[dict]]:
    """
    ...
    """

    if not os.path.exists(input_path):
        sys.exit(f"input_path {input_path} does not exist")

    unique_track_uris: set[str] = set()
    stream_objects: list[dict] = []

    print("Getting unique track URIs and Stream objects")
    for file_path in tqdm.tqdm(glob.glob(input_path + "*.json")):
        with open(file_path, "r", encoding="UTF-8") as json_file:
            try:
                json_data: list[dict] = json.load(json_file)
            except ValueError:
                print(f"{file_path} is not a valid JSON file")
                continue

            stream_objects.extend(json_data)

            unique_track_uris.update(
                stream_object["spotify_track_uri"]
                for stream_object in json_data
                if stream_object["spotify_track_uri"] is not None
            )

    return unique_track_uris, stream_objects


def parse_release_date(
    release_date: str, release_date_precision: str
) -> datetime.datetime:
    """
    ...
    """

    if release_date_precision == "year":
        return (
            datetime.datetime.strptime(release_date, "%Y")
            if int(release_date) > 0
            else datetime.datetime.now()
        )
    if release_date_precision == "month":
        return datetime.datetime.strptime(release_date, "%Y-%m")
    if release_date_precision == "day":
        return datetime.datetime.strptime(release_date, "%Y-%m-%d")

    return datetime.datetime.now()


def db_get_tracks(track_uris: list[str]) -> list[Tracks] | None:
    """
    ...
    """

    track = db.session.query(Tracks).filter(Tracks.uri.in_(track_uris)).all()

    if tracks is None:
        old_track_uri = (
            db.session.query(OldTrackUris.track)
            .filter(OldTrackUris.old_uri == track_uri)
            .first()
        )

        return old_track_uri.track if old_track_uri else None

    return track


def db_get_album(album_uri: str) -> Albums | None:
    """
    ...
    """

    album: Albums | None = (
        db.session.query(Albums).filter(Albums.uri == album_uri).first()
    )

    return album


def db_get_artist(artist_uri: str) -> Artists | None:
    """
    ...
    """

    artist: Artists | None = (
        db.session.query(Artists).filter(Artists.uri == artist_uri).first()
    )

    return artist


def db_create_artist(artist_data: dict) -> Artists:
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


def db_create_album(
    album_data: dict, data_cache: dict, sp_client: spotipy.Spotify
) -> Albums:
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
                get_artist_data(data_cache, sp_client)
                data_cache["artists"].clear()
        else:
            album_artist.albums.append(album)
            db.session.add(album_artist)

    db.session.commit()
    return album


def db_create_track(
    track_data: dict, album: Albums | None, sp_client: spotipy.Spotify, data_cache: dict
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
                get_artist_data(data_cache, sp_client)
                data_cache["artists"].clear()
        else:
            track_artist.tracks.append(track)
            db.session.add(track_artist)

    db.session.commit()


def get_artist_data(data_cache: dict, sp_client: spotipy.Spotify) -> None:
    """
    ...
    """

    artists_data = sp_client.artists(list(data_cache["artists"].keys()))
    if artists_data is None:
        return

    for artist_data in artists_data["artists"]:
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


def get_album_data(
    album_uri_batch: list[str], sp_client: spotipy.Spotify, data_cache: dict
) -> None:
    """
    ...
    """

    albums_data = sp_client.albums(album_uri_batch, market="JP")
    if albums_data is None:
        return

    for album_data in albums_data["albums"]:
        album = db_create_album(album_data, data_cache, sp_client)

        for track_uri in list(data_cache["albums"][album_data["uri"]]):
            track = db_get_track(track_uri)
            album.tracks.append(track)

        db.session.commit()


def get_track_data(
    old_track_uris: list[str], sp_client: spotipy.Spotify, data_cache: dict
) -> None:
    """
    ...
    """

    # List of 50 track objects returned by spotify API
    tracks_data = sp_client.tracks(old_track_uris, market="JP")
    if tracks_data is None:
        return

    unique_tracks_data = list(
        {
            track_data.uri: track_data
            for old_track_uri, track_data in zip(old_track_uris, tracks_data)
        }.values()
    )

    """
    track_uri = track_data["uri"]
    track = db_get_track(track_uri)
    if track is not None:
        db.session.add(OldTrackUris(old_uri=track_uri_batch[i], track_id=track.id))
        db.session.commit()
        continue

    album_uri = track_data["album"]["uri"]
    album = db_get_album(album_uri)
    db_create_track(track_data, album, sp_client, data_cache)
    if album is not None:
        continue

    if album_uri not in data_cache["albums"]:
        data_cache["albums"][album_uri] = set()

    data_cache["albums"][album_uri].add(track_uri)
    if len(data_cache["albums"].keys()) == 20:
        get_album_data(list(data_cache["albums"].keys()), sp_client, data_cache)
        data_cache["albums"].clear()
    """


def process_unique_track_uris(
    unique_track_uris: set[str], sp_client: spotipy.Spotify, data_cache: dict
) -> None:
    """
    ...
    """
    # Spotify limit for bulk track requests
    batch_size = 50

    # Get all track_uris in Tracks table that match URIs in unique_track_uris set
    current_unique_track_uris: set[str] = {
        uri
        for (uri,) in db.session.query(TrackUris.uri)
        .filter(TrackUris.uri.in_(unique_track_uris))
        .all()
    }

    # Remove the matching URIs from the unique_track_uris set
    new_track_uris = list(unique_track_uris - current_unique_track_uris)

    print(f"unique_track_uris: {len(unique_track_uris)}")
    print(f"current_unique_track_uris: {len(current_unique_track_uris)}")
    print(f"new_track_uris: {len(new_track_uris)}")

    print("\nProcessing track URIs")
    for pos in tqdm.tqdm(range(0, len(new_track_uris), batch_size)):
        get_track_data(new_track_uris[pos : pos + batch_size], sp_client, data_cache)

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
            get_track_data(track_uri_batch, sp_client, data_cache)
            track_uri_batch.clear()

    # If there are remaining elements in track_uri_batch, process them
    if track_uri_batch:
        get_track_data(track_uri_batch, sp_client, data_cache)
        track_uri_batch.clear()

    # If data_cache still has album_uris, process them
    if data_cache["albums"]:
        get_album_data(list(data_cache["albums"].keys()), sp_client, data_cache)
        data_cache["albums"].clear()

    # If data_cache still has artist_uris, process them
    if data_cache["artists"]:
        get_artist_data(data_cache, sp_client)
        data_cache["artists"].clear()
    """


def create_streams(stream_objects: list[dict]) -> None:
    """
    ...
    """

    streams: list[Streams] = []

    print("\nCreating Streams")
    for stream_object in tqdm.tqdm(stream_objects):
        if stream_object["spotify_track_uri"] is not None:
            track = db_get_track(stream_object["spotify_track_uri"])
            if track is None:
                continue

            streams.append(
                Streams(
                    track_id=track.id,
                    album_id=track.album_id,
                    stream_date=datetime.datetime.strptime(
                        stream_object["ts"], "%Y-%m-%dT%H:%M:%SZ"
                    ),
                    ms_played=stream_object["ms_played"],
                    ratio_played=min(
                        stream_object["ms_played"] / track.duration_ms, 1.0
                    )
                    if track.duration_ms > 0
                    else 0.0,
                    reason_start=stream_object["reason_start"],
                    reason_end=stream_object["reason_end"],
                    shuffle=stream_object["shuffle"],
                    created_date=datetime.datetime.now(datetime.timezone.utc),
                    modified_date=datetime.datetime.now(datetime.timezone.utc),
                )
            )

    # Batch insertion of streams
    print("Saving...", end="")
    db.session.bulk_save_objects(streams)
    db.session.commit()
    print("DONE!")

    print("\nLinking Streams")
    for stream in tqdm.tqdm(streams):
        for track_artist in stream.track.artists:
            track_artist.streams.append(stream)

        for album_artist in stream.album.artists:
            album_artist.streams.append(stream)

    db.session.commit()


def get_track_features(sp_client: spotipy.Spotify) -> None:
    """
    ...
    """

    tracks = db.session.query(Tracks).all()
    track_uris = [track.uri for track in tracks]

    num_tracks = len(track_uris)
    batch_size = 100

    print("\nGetting Track Features")
    for pos in tqdm.tqdm(range(0, num_tracks, batch_size)):
        track_uris_batch = track_uris[pos : pos + batch_size]

        features_batch = sp_client.audio_features(track_uris_batch)
        if features_batch is None:
            return

        for i, features in enumerate(features_batch):
            if not features:
                continue
            track = tracks[pos + i]
            track.acousticness = features["acousticness"]
            track.danceability = features["danceability"]
            track.energy = features["energy"]
            track.instrumentalness = features["instrumentalness"]
            track.key = features["key"]
            track.liveness = features["liveness"]
            track.loudness = features["loudness"]
            track.mode = features["mode"]
            track.speechiness = features["speechiness"]
            track.tempo = features["tempo"]
            track.time_signature = features["time_signature"]
            track.valence = features["valence"]

        db.session.commit()


def main() -> None:
    """
    ...
    """

    # Path to file that contains client_id / client_secret
    auth_file_path = os.path.abspath("./auth.txt")
    # Path holding all endsong.json files
    streams_file_path = os.path.abspath("./data/input/")

    app = create_app()
    with app.app_context():
        populator = Populator(auth_file_path, streams_file_path)
        populator.populate_db()

    """
    # Create new spotipy client using credentials in auth_file_path
    sp_client = create_spotify_client(auth_file_path)
    # Get list of all unique track_uris in streams data and streams objects themselves
    unique_track_uris, stream_objects = load_stream_objects(json_file_path)

    # Create cache for album and artist uris ...
    data_cache: dict = {"albums": {}, "artists": {}}

    # Create app and use context to access database
    app = create_app()
    with app.app_context():
        # Begin processing all unique track_uris from streams
        process_unique_track_uris(unique_track_uris, sp_client, data_cache)
        # get_track_features(sp_client)
        # create_streams(stream_objects)
    """


if __name__ == "__main__":
    main()
