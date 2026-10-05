"""Where the Beat This checkpoint is and what it must be.

The checkpoint is fetched once by scripts/fetch_model.py. The application only reads
the local file and never asks the network for it.
"""

import hashlib
from pathlib import Path

MODEL_URL = "https://cloud.cp.jku.at/public.php/dav/files/7ik4RrBKTS273gp/final0.ckpt"
MODEL_SHA256 = "8c328b45f59d8dd3dff219253ff6a8d6482be57d0133a29140e2febbf8eb8331"
MODEL_PATH = Path(__file__).parent.parent / "models" / "beat_this-final0.ckpt"


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        while chunk := file.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def checked_model_path():
    """The path of the checkpoint, after checking it is the recorded file."""
    if not MODEL_PATH.exists():
        raise RuntimeError(f"{MODEL_PATH} is missing: run `uv run python scripts/fetch_model.py`")
    found = sha256_of(MODEL_PATH)
    if found != MODEL_SHA256:
        raise RuntimeError(f"{MODEL_PATH} has sha256 {found}, expected {MODEL_SHA256}")
    return MODEL_PATH
