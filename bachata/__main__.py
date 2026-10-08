"""Starts the program: `uv run python -m bachata`.

With a command it starts nothing, and answers from the library on disk (bachata/places.py):

    uv run python -m bachata where <song> <place>
    uv run python -m bachata bars <song>

Two settings, both from the environment:

    PORT           the port to listen on, 8080 when not set
    BACHATA_DATA   the folder of the library, `data` beside the code when not set
"""

import os
import sys
from pathlib import Path

import uvicorn

from bachata.model import checked_model_path, checked_parts_path
from bachata.places import command
from bachata.server import create_app

# Listens on the loopback interface only, so other machines cannot reach it.
HOST = "127.0.0.1"


def data_folder():
    return os.environ.get("BACHATA_DATA", Path(__file__).parent.parent / "data")


def main():
    port = int(os.environ.get("PORT", "8080"))
    data = data_folder()
    # Both before anything starts: without the second, only the songs whose fills are asked would fail.
    checked_model_path()
    checked_parts_path()
    app = create_app(data)
    print(f"Bachata sections: http://{HOST}:{port}", flush=True)
    uvicorn.run(app, host=HOST, port=port, server_header=False, proxy_headers=False, log_level="warning")


def run(arguments):
    """The server when there are no arguments, and otherwise the command they name."""
    if arguments:
        return command(arguments, data_folder())
    main()


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
