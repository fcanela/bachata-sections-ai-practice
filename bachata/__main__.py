"""Starts the program: `uv run python -m bachata`.

Two settings, both from the environment:

    PORT           the port to listen on, 8080 when not set
    BACHATA_DATA   the folder of the library, `data` beside the code when not set
"""

import os
from pathlib import Path

import uvicorn

from bachata.model import checked_model_path
from bachata.server import create_app

# Listens on the loopback interface only, so other machines cannot reach it.
HOST = "127.0.0.1"


def main():
    port = int(os.environ.get("PORT", "8080"))
    data = os.environ.get("BACHATA_DATA", Path(__file__).parent.parent / "data")
    checked_model_path()
    app = create_app(data)
    print(f"Bachata sections: http://{HOST}:{port}", flush=True)
    uvicorn.run(app, host=HOST, port=port, server_header=False, proxy_headers=False, log_level="warning")


if __name__ == "__main__":
    main()
