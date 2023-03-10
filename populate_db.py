import sys
import os
import json
import glob
import datetime

import spotipy
import tqdm
from flask_sqlalchemy import SQLAlchemy

from src.server import create_app
from src.server.extensions import db
from src.models.models import Streams, Tracks

INPUT_PATH = "./data/input/"
OUTPUT_PATH = "./data/output/"
CLIENT_ID = ""
CLIENT_SECRET = ""
AUTH_PATH = "./auth.txt"


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
    auth_manager = spotipy.oauth2.SpotifyClientCredentials(
        client_id=client_id, client_secret=client_secret
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

                track = (
                    db.session.query(Tracks)
                    .filter(Tracks.uri == stream_record["spotify_track_uri"])
                    .first()
                )
                if track is None:
                    track = Tracks(
                        uri=stream_record["spotify_track_uri"],
                        album_id=1,
                        disc_number=1,
                        duration_ms=1000000,
                        explicit=True,
                        name="asdfafd",
                        popularity=100,
                        preview_url="asdf",
                        track_number=123,
                        created_date=datetime.datetime.now(datetime.timezone.utc),
                        modified_date=datetime.datetime.now(datetime.timezone.utc),
                    )

                    db.session.add(track)
                    db.session.commit()

                stream = Streams(
                    track_id=track.id,
                    stream_date=datetime.datetime.strptime(
                        stream_record["ts"], "%Y-%m-%dT%H:%M:%SZ"
                    ),
                    ms_played=stream_record["ms_played"],
                    ratio_played=stream_record["ms_played"] / track.duration_ms,
                    reason_start=stream_record["reason_start"],
                    reason_end=stream_record["reason_end"],
                    shuffle=stream_record["shuffle"],
                    created_date=datetime.datetime.now(datetime.timezone.utc),
                    modified_date=datetime.datetime.now(datetime.timezone.utc),
                )

                db.session.add(stream)
                db.session.commit()


if __name__ == "__main__":
    with open(file=AUTH_PATH, mode="r", encoding="UTF-8") as file:
        CLIENT_ID, CLIENT_SECRET = file.readlines()

    app = create_app()
    with app.app_context():
        preprocess_streams(INPUT_PATH, OUTPUT_PATH, CLIENT_ID, CLIENT_SECRET, db)
