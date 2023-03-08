import sys
import os
import json
import glob
import spotipy


def preprocess_streams(
    input_path: str, output_path: str, client_id: str, client_secret: str
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
        with open(file=file_path, mode="r", encoding="UTF-8") as file:
            try:
                data: list = json.load(fp=file)
            except ValueError:
                print(f"{file_path} is not a valid JSON file")
                continue

            for stream in data:
                track_uri: str = stream["spotify_track_uri"]
                album_uri: str = ""
                artist_uri: str = ""
