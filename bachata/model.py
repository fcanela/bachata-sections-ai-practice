"""Where the two checkpoints are and what they must be.

- Beat This, for the beats.
- Hybrid Demucs as torchaudio publishes it, for the parts of a song (bachata/fills.py).

Both are fetched once by scripts/fetch_model.py. The application only reads the local
files and never asks the network for them.
"""

import hashlib
from pathlib import Path

MODEL_URL = "https://cloud.cp.jku.at/public.php/dav/files/7ik4RrBKTS273gp/final0.ckpt"
MODEL_SHA256 = "8c328b45f59d8dd3dff219253ff6a8d6482be57d0133a29140e2febbf8eb8331"
MODEL_PATH = Path(__file__).parent.parent / "models" / "beat_this-final0.ckpt"

PARTS_URL = "https://download.pytorch.org/torchaudio/models/hdemucs_high_trained.pt"
PARTS_SHA256 = "a004b2790d73ffeaa535db458a1a79b539dfdbafbccc31f275d07e632ebd7816"
PARTS_PATH = Path(__file__).parent.parent / "models" / "hdemucs_high_trained.pt"


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        while chunk := file.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def _checked(path, sha256):
    if not path.exists():
        raise RuntimeError(f"{path} is missing: run `uv run python scripts/fetch_model.py`")
    found = sha256_of(path)
    if found != sha256:
        raise RuntimeError(f"{path} has sha256 {found}, expected {sha256}")
    return path


def checked_model_path():
    """The path of the Beat This checkpoint, after checking it is the recorded file."""
    return _checked(MODEL_PATH, MODEL_SHA256)


def checked_parts_path():
    """The path of the Hybrid Demucs checkpoint, after checking it is the recorded file."""
    return _checked(PARTS_PATH, PARTS_SHA256)
