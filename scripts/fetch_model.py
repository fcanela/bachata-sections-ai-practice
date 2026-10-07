"""Downloads the two checkpoints from their authors' releases, once: Beat This and Hybrid Demucs.

    uv run python scripts/fetch_model.py

This is the only step that uses the network. Each file is checked against the sha256
recorded in bachata/model.py and is not committed.
"""

import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from bachata.model import MODEL_PATH, MODEL_SHA256, MODEL_URL, PARTS_PATH, PARTS_SHA256, PARTS_URL, sha256_of

for path, sha256, url in ((MODEL_PATH, MODEL_SHA256, MODEL_URL), (PARTS_PATH, PARTS_SHA256, PARTS_URL)):
    if path.exists() and sha256_of(path) == sha256:
        print(f"{path}: already there, sha256 matches")
        continue
    path.parent.mkdir(exist_ok=True)
    partial = path.with_suffix(".partial")
    print(f"downloading {url}")
    urllib.request.urlretrieve(url, partial)
    found = sha256_of(partial)
    if found != sha256:
        partial.unlink()
        sys.exit(f"sha256 is {found}, expected {sha256}: nothing kept")
    partial.rename(path)
    print(f"{path}: {path.stat().st_size} bytes, sha256 matches")
