"""
...
"""

import glob
import json
import os
import sys
import datetime

import spotipy
import tqdm

from src.server.extensions import db
from src.models.models import (
    TrackUris,
    Tracks,
    Albums,
    Artists,
    Labels,
    Genres,
    Streams,
)


class Populator:
    """
    ...
    """

    def __init__(self, auth_file_path: str, streams_file_path: str) -> None:
        """
        ...
        """

        self.loaded_stream_objects = []
        self.loaded_track_uris: set[str] = set()
        self.loaded_album_uris: dict[str, list[Tracks]] = {}
        self.loaded_artist_uris: dict[str, tuple[list[Tracks], list[Albums]]] = {}
        self.loaded_label_names: dict[str, list[Albums]] = {}
        self.loaded_genre_names: dict[str, list[Artists]] = {}

        self.current_trackuri_records: dict[str, Tracks] = {
            trackuri.uri: trackuri.track
            for trackuri in db.session.query(TrackUris).all()
        }
        self.current_album_records: dict[str, Albums] = {
            album.uri: album for album in db.session.query(Albums).all()
        }
        self.current_artist_records: dict[str, Artists] = {
            artist.uri: artist for artist in db.session.query(Artists).all()
        }
        self.current_label_records: dict[str, Labels] = {
            label.name: label for label in db.session.query(Labels).all()
        }
        self.current_genre_records: dict[str, Genres] = {
            genre.name: genre for genre in db.session.query(Genres).all()
        }

        self.new_trackuri_records: list[TrackUris] = []

        self.auth_file_path: str = auth_file_path
        self.streams_file_path: str = streams_file_path

        self.create_spotify_client()
        self.load_stream_objects()

    def create_spotify_client(self) -> None:
        """
        ...
        """

        with open(file=self.auth_file_path, mode="r", encoding="ascii") as file:
            client_id, client_secret = file.readlines()

        client_id: str = client_id.rstrip()
        client_secret: str = client_secret.rstrip()

        auth_manager = spotipy.oauth2.SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri="http://example.com/",
        )

        self.sp_client = spotipy.Spotify(auth_manager=auth_manager, language="ja")

    def load_stream_objects(self) -> None:
        """
        ...
        """

        if not os.path.exists(self.streams_file_path):
            sys.exit(f"input_path {self.streams_file_path} does not exist")

        print("\nLoading Track URIs and Stream objects")
        for current_file_path in tqdm.tqdm(
            glob.glob(self.streams_file_path + "/*.json")
        ):
            with open(current_file_path, "r", encoding="UTF-8") as json_file:
                try:
                    json_data: list = json.load(json_file)
                except ValueError:
                    print(f"{current_file_path} is not a valid JSON file")
                    continue

                self.loaded_stream_objects.extend(json_data)

                self.loaded_track_uris.update(
                    stream_object["spotify_track_uri"]
                    for stream_object in json_data
                    if stream_object["spotify_track_uri"] is not None
                )

    def process_loaded_track_uris(self) -> None:
        """
        ...
        """

        unseen_track_uris: list[str] = list(
            self.loaded_track_uris - self.current_trackuri_records.keys()
        )

        print("\nProcessing loaded Track URIs")
        for pos in tqdm.tqdm(range(0, len(unseen_track_uris), 50)):
            self.process_unseen_track_uris_batch(unseen_track_uris[pos : pos + 50])

        db.session.bulk_save_objects(self.new_trackuri_records)
        db.session.commit()

    def process_unseen_track_uris_batch(
        self, unseen_track_uris_batch: list[str]
    ) -> None:
        """
        ...
        """

        # List of 50 Track objects returned by spotify API
        track_objects = self.sp_client.tracks(unseen_track_uris_batch, market="JP")
        if track_objects is None:
            return

        for unseen_track_uri, track_object in zip(
            unseen_track_uris_batch, track_objects["tracks"]
        ):
            track_uri: str = track_object["uri"]
            album_uri: str = track_object["album"]["uri"]
            album: Albums | None = self.current_album_records.get(album_uri)

            if track_uri in self.current_trackuri_records:
                if track_uri != unseen_track_uri:
                    self.current_trackuri_records[
                        unseen_track_uri
                    ] = self.current_trackuri_records[track_uri]
                    self.new_trackuri_records.append(
                        TrackUris(
                            uri=unseen_track_uri,
                            track_id=self.current_trackuri_records[unseen_track_uri].id,
                        )
                    )
                continue

            new_track_record: Tracks = Tracks(
                uri=track_uri,
                album_id=album.id if album else None,
                album_name=album.name if album else None,
                disc_number=track_object["disc_number"],
                duration_ms=track_object["duration_ms"],
                explicit=track_object["explicit"],
                name=track_object["name"],
                popularity=track_object["popularity"],
                preview_url=track_object["preview_url"],
                track_number=track_object["track_number"],
                created_date=datetime.datetime.now(datetime.timezone.utc),
                modified_date=datetime.datetime.now(datetime.timezone.utc),
            )
            db.session.add(new_track_record)
            db.session.commit()

            self.current_trackuri_records[track_uri] = new_track_record
            self.new_trackuri_records.append(
                TrackUris(
                    uri=track_uri,
                    track_id=new_track_record.id,
                )
            )

            if album is None:
                if album_uri not in self.loaded_album_uris:
                    self.loaded_album_uris[album_uri] = []

                self.loaded_album_uris[album_uri].append(new_track_record)

            for track_object_artist in track_object["artists"]:
                track_artist_uri: str = track_object_artist["uri"]
                track_artist: Artists | None = self.current_artist_records.get(
                    track_artist_uri
                )

                if track_artist is None:
                    if track_artist_uri not in self.loaded_artist_uris:
                        self.loaded_artist_uris[track_artist_uri] = ([], [])

                    self.loaded_artist_uris[track_artist_uri][0].append(
                        new_track_record
                    )
                    continue

                track_artist.tracks.append(new_track_record)

    def process_loaded_album_uris(self) -> None:
        """
        ...
        """

        unseen_album_uris: list[tuple[str, list[Tracks]]] = list(
            self.loaded_album_uris.items()
        )

        print("\nProcessing loaded Album URIs")
        for pos in tqdm.tqdm(range(0, len(unseen_album_uris), 20)):
            self.process_unseen_album_uris_batch(unseen_album_uris[pos : pos + 20])

    def process_unseen_album_uris_batch(
        self, unseen_album_uris_batch: list[tuple[str, list[Tracks]]]
    ) -> None:
        """
        ...
        """

        # List of 20 Album objects returned by spotify API
        album_objects = self.sp_client.albums(
            [album_uri for (album_uri, _) in unseen_album_uris_batch], market="JP"
        )
        if album_objects is None:
            return

        for album_object, (_, tracks) in zip(
            album_objects["albums"], unseen_album_uris_batch
        ):
            label_name: str = album_object["label"]
            label: Labels | None = self.current_label_records.get(label_name)

            new_album_record: Albums = Albums(
                uri=album_object["uri"],
                album_type=album_object["album_type"],
                total_tracks=album_object["total_tracks"],
                name=album_object["name"],
                release_date=self.parse_release_date(
                    album_object["release_date"],
                    album_object["release_date_precision"],
                ),
                label_id=label.id if label else None,
                label_name=label_name,
                popularity=album_object["popularity"],
                image_url=album_object["images"][0]["url"]
                if album_object["images"]
                else None,
                created_date=datetime.datetime.now(datetime.timezone.utc),
                modified_date=datetime.datetime.now(datetime.timezone.utc),
            )
            db.session.add(new_album_record)
            db.session.commit()

            for track in tracks:
                track.album_name = new_album_record.name
                new_album_record.tracks.append(track)
            db.session.commit()

            if label is None and label_name is not None:
                if label_name not in self.loaded_label_names:
                    self.loaded_label_names[label_name] = []

                self.loaded_label_names[label_name].append(new_album_record)

            for album_object_artist in album_object["artists"]:
                album_artist_uri: str = album_object_artist["uri"]
                album_artist: Artists | None = self.current_artist_records.get(
                    album_artist_uri
                )

                if album_artist is None:
                    if album_artist_uri not in self.loaded_artist_uris:
                        self.loaded_artist_uris[album_artist_uri] = ([], [])

                    self.loaded_artist_uris[album_artist_uri][1].append(
                        new_album_record
                    )
                    continue

                album_artist.albums.append(new_album_record)
                db.session.commit()

    def process_loaded_artist_uris(self) -> None:
        """
        ...
        """

        unseen_artist_uris: list[tuple[str, tuple[list[Tracks], list[Albums]]]] = list(
            self.loaded_artist_uris.items()
        )

        print("\nProcessing loaded Artist URIs")
        for pos in tqdm.tqdm(range(0, len(unseen_artist_uris), 50)):
            self.process_unseen_artist_uris_batch(unseen_artist_uris[pos : pos + 50])

    def process_unseen_artist_uris_batch(
        self,
        unseen_artist_uris_batch: list[tuple[str, tuple[list[Tracks], list[Albums]]]],
    ) -> None:
        """
        ...
        """

        # List of 50 Artist objects returned by spotify API
        artist_objects = self.sp_client.artists(
            [artist_uri for (artist_uri, _) in unseen_artist_uris_batch]
        )
        if artist_objects is None:
            return

        for artist_object, (_, (tracks, albums)) in zip(
            artist_objects["artists"], unseen_artist_uris_batch
        ):
            new_artist_record: Artists = Artists(
                uri=artist_object["uri"],
                followers=artist_object["followers"]["total"],
                name=artist_object["name"],
                popularity=artist_object["popularity"],
                image_url=artist_object["images"][0]["url"]
                if artist_object["images"]
                else None,
                created_date=datetime.datetime.now(datetime.timezone.utc),
                modified_date=datetime.datetime.now(datetime.timezone.utc),
            )

            db.session.add(new_artist_record)
            db.session.commit()

            new_artist_record.tracks.extend(tracks)
            new_artist_record.albums.extend(albums)
            db.session.commit()

            for genre_name in artist_object["genres"]:
                genre: Genres | None = self.current_genre_records.get(genre_name)

                if genre is None:
                    if genre_name not in self.loaded_genre_names:
                        self.loaded_genre_names[genre_name] = []

                    self.loaded_genre_names[genre_name].append(new_artist_record)
                    continue

                genre.artists.append(new_artist_record)
                db.session.commit()

    def process_loaded_label_names(self) -> None:
        """
        ...
        """

        unseen_label_names: list[tuple[str, list[Albums]]] = list(
            self.loaded_label_names.items()
        )

        print("\nProcessing loaded Label names")
        for label_name, albums in tqdm.tqdm(unseen_label_names):
            new_label_record: Labels = Labels(name=label_name)

            db.session.add(new_label_record)
            db.session.commit()

            new_label_record.albums.extend(albums)
            db.session.commit()

    def process_loaded_genre_names(self) -> None:
        """
        ...
        """

        unseen_genre_names: list[tuple[str, list[Artists]]] = list(
            self.loaded_genre_names.items()
        )

        print("\nProcessing loaded Genre names")
        for genre_name, artists in tqdm.tqdm(unseen_genre_names):
            new_genre_record: Genres = Genres(name=genre_name)

            db.session.add(new_genre_record)
            db.session.commit()

            new_genre_record.artists.extend(artists)
            db.session.commit()

    def parse_release_date(
        self, release_date: str, release_date_precision: str
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

    def get_track_features(self) -> None:
        """
        ...
        """

        tracks: list[Tracks] = list(self.current_trackuri_records.values())
        track_uris: list[str] = [track.uri for track in tracks]

        print("\nGetting Track Features")
        for pos in tqdm.tqdm(range(0, len(tracks), 100)):
            track_uris_batch = track_uris[pos : pos + 100]

            features_batch = self.sp_client.audio_features(track_uris_batch)
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

    def create_streams(self) -> None:
        """
        ...
        """

        new_stream_records: list[Streams] = []

        print("\nCreating Streams")
        for stream_object in tqdm.tqdm(self.loaded_stream_objects):
            if stream_object["spotify_track_uri"] is not None:
                track = self.current_trackuri_records.get(
                    stream_object["spotify_track_uri"]
                )
                if track is None:
                    continue

                new_stream_records.append(
                    Streams(
                        track_id=track.id,
                        track_name=track.name,
                        album_id=track.album_id,
                        album_name=track.album.name,
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
        db.session.add_all(new_stream_records)
        db.session.commit()
        print("DONE!")

        print("\nLinking Streams")
        for stream in tqdm.tqdm(new_stream_records):
            stream.artists.extend(
                {
                    artist.uri: artist
                    for artist in stream.track.artists + stream.album.artists
                }.values()
            )

        db.session.commit()

    def populate_db(self) -> None:
        """
        ...
        """

        self.process_loaded_track_uris()
        self.process_loaded_album_uris()
        self.process_loaded_artist_uris()
        self.process_loaded_label_names()
        self.process_loaded_genre_names()
        self.get_track_features()
        self.create_streams()
