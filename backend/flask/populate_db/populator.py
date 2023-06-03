"""
...
"""

import glob
import json
import os
import sys

import spotipy
import tqdm
from flask_sqlalchemy import SQLAlchemy

from src.server import create_app
from src.server.extensions import db
from src.models.models import Streams, Tracks, Albums, Artists, Genres, TrackUris


class Populator:
    """
    ...
    """

    def __init__(self, auth_file_path: str, streams_file_path: str) -> None:
        """
        ...
        """

        self.loaded_unique_track_uris: set[str] = set()
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

        print("Getting unique track URIs and Stream objects")
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

                self.loaded_unique_track_uris.update(
                    stream_object["spotify_track_uri"]
                    for stream_object in json_data
                    if stream_object["spotify_track_uri"] is not None
                )

    def process_loaded_unique_track_uris(self) -> None:
        """
        ...
        """

        # Spotify limit for bulk track requests
        batch_size = 50

        # Get all track_uris in TrackUris table that match URIs in loaded_unique_track_uris set
        current_unique_track_uris: set[str] = {
            uri
            for (uri,) in db.session.query(TrackUris.uri)
            .filter(TrackUris.uri.in_(self.loaded_unique_track_uris))
            .all()
        }

        # Remove the matching URIs from the loaded_unique_track_uris set
        unseen_track_uris = list(
            self.loaded_unique_track_uris - current_unique_track_uris
        )

        print("\nProcessing loaded_unique track URIs")
        for pos in tqdm.tqdm(range(0, len(unseen_track_uris), batch_size)):
            self.process_unseen_track_uris_batch(
                unseen_track_uris[pos : pos + batch_size]
            )

    def process_unseen_track_uris_batch(self, unseen_track_uris: list[str]) -> None:
        """
        ...
        """

        pass
