#!/usr/bin/env python3


import os

from src.utils.populate_db.populator import Populator

from src.server import create_app


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


if __name__ == "__main__":
    main()
