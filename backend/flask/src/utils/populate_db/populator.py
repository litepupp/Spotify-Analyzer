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
from src.models.models import TrackUris, Tracks, Albums, Artists


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

        self.current_trackuri_records: dict[str, int] = dict(
            db.session.query(TrackUris.uri, TrackUris.track_id).all()
        )
        self.current_album_records: dict[str, int] = dict(
            db.session.query(Albums.uri, Albums.id).all()
        )
        self.current_artist_records: dict[str, Artists] = {
            artist.uri: artist for artist in db.session.query(Artists).all()
        }

        self.new_trackuri_records: list[TrackUris] = []
        self.new_album_records: list[Albums] = []

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

        print("Loading Track URIs and Stream objects")
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

        print("Processing loaded Track URIs")
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
            album_id: int | None = self.current_album_records.get(album_uri)

            if track_uri in self.current_trackuri_records:
                if track_uri != unseen_track_uri:
                    self.current_trackuri_records[
                        unseen_track_uri
                    ] = self.current_trackuri_records[track_uri]
                    self.new_trackuri_records.append(
                        TrackUris(
                            uri=unseen_track_uri,
                            track_id=self.current_trackuri_records[unseen_track_uri],
                        )
                    )
                continue

            new_track_record: Tracks = Tracks(
                uri=track_uri,
                album_id=album_id,
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

            self.current_trackuri_records[track_uri] = new_track_record.id
            self.new_trackuri_records.append(
                TrackUris(
                    uri=track_uri,
                    track_id=new_track_record.id,
                )
            )

            if album_id is None:
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

        print("Processing loaded Album URIs")
        for pos in tqdm.tqdm(range(0, len(unseen_album_uris), 20)):
            self.process_unseen_album_uris_batch(unseen_album_uris[pos : pos + 20])

        db.session.bulk_save_objects(self.new_album_records)
        db.session.commit()

    def process_unseen_album_uris_batch(
        self, unseen_album_uris_batch: list[tuple[str, list[Tracks]]]
    ) -> None:
        """
        ...
        """

        # List of 20 Album objects returned by spotify API
        album_objects = self.sp_client.albums(
            [album_uri for album_uri, _ in unseen_album_uris_batch], market="JP"
        )
        if album_objects is None:
            return

        for album_object in album_objects["albums"]:
            new_album_record = Albums(
                uri=album_object["uri"],
                album_type=album_object["album_type"],
                total_tracks=album_object["total_tracks"],
                name=album_object["name"],
                release_date=self.parse_release_date(
                    album_object["release_date"],
                    album_object["release_date_precision"],
                ),
                label=album_object["label"],
                popularity=album_object["popularity"],
                image_url=album_object["images"][0]["url"]
                if album_object["images"]
                else None,
                created_date=datetime.datetime.now(datetime.timezone.utc),
                modified_date=datetime.datetime.now(datetime.timezone.utc),
            )
            self.new_album_records.append(new_album_record)

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

    def populate_db(self) -> None:
        """
        ...
        """

        self.process_loaded_track_uris()
        self.process_loaded_album_uris()
