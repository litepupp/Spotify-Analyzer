"""
...
"""

import glob
import json
import os
import sys

import spotipy
import tqdm

from src.server.extensions import db
from src.models.models import TrackUris


class Populator:
    """
    ...
    """

    def __init__(self, auth_file_path: str, streams_file_path: str) -> None:
        """
        ...
        """

        self.loaded_track_uris: set[str] = set()
        self.current_trackuri_records: dict[str, int] = {}
        self.loaded_stream_objects = []

        self.auth_file_path = auth_file_path
        self.streams_file_path = streams_file_path

        self.create_spotify_client()
        self.load_stream_objects()

    def create_spotify_client(self) -> None:
        """
        ...
        """

        with open(file=self.auth_file_path, mode="r", encoding="ascii") as file:
            client_id, client_secret = file.readlines()

        client_id = client_id.rstrip()
        client_secret = client_secret.rstrip()

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
            glob.glob(self.streams_file_path + "*.json")
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

        self.current_trackuri_records = dict(db.session.query(TrackUris).all())

        unseen_track_uris = list(
            self.loaded_track_uris - self.current_trackuri_records.keys()
        )

        print(f"self.current_trackuri_records: {len(self.current_trackuri_records)}")
        print(f"self.loaded_track_uris: {len(self.loaded_track_uris)}")
        print(f"unseen_track_uris: {len(unseen_track_uris)}")

        unseen_track_uris_batch: list[str] = []

        print("Processing loaded Track URIs")
        for unseen_track_uri in tqdm.tqdm(unseen_track_uris):
            if unseen_track_uri in self.current_trackuri_records:
                continue

            unseen_track_uris_batch.append(unseen_track_uri)
            if len(unseen_track_uris_batch) == 50:
                self.process_unseen_track_uris_batch(unseen_track_uris_batch)
                unseen_track_uris_batch.clear()

                break

    def process_unseen_track_uris_batch(
        self, unseen_track_uris_batch: list[str]
    ) -> None:
        """
        ...
        """

        # List of 50 track objects returned by spotify API
        track_objects = self.sp_client.tracks(unseen_track_uris_batch, market="JP")
        if track_objects is None:
            return

        new_trackuri_records = []

        for unseen_track_uri, track_object in zip(
            unseen_track_uris_batch, track_objects["tracks"]
        ):
            if track_object["uri"] in self.current_trackuri_records:
                self.current_trackuri_records[
                    unseen_track_uri
                ] = self.current_trackuri_records[track_object["uri"]]
                new_trackuri_records.append(
                    TrackUris(
                        uri=unseen_track_uri,
                        track_id=self.current_trackuri_records[track_object["uri"]],
                    )
                )
                continue

        db.session.bulk_save_objects(new_trackuri_records)
        db.session.commit()
