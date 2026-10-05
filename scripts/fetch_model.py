"""Downloads the Beat This checkpoint from its authors' release, once.

    uv run python scripts/fetch_model.py

This is the only step that uses the network. The file is checked against the sha256
recorded in bachata/model.py and is not committed.
"""

import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from bachata.model import MODEL_PATH, MODEL_SHA256, MODEL_URL, sha256_of

if MODEL_PATH.exists() and sha256_of(MODEL_PATH) == MODEL_SHA256:
    print(f"{MODEL_PATH}: already there, sha256 matches")
    sys.exit(0)

MODEL_PATH.parent.mkdir(exist_ok=True)
partial = MODEL_PATH.with_suffix(".partial")
print(f"downloading {MODEL_URL}")
urllib.request.urlretrieve(MODEL_URL, partial)
found = sha256_of(partial)
if found != MODEL_SHA256:
    partial.unlink()
    sys.exit(f"sha256 is {found}, expected {MODEL_SHA256}: nothing kept")
partial.rename(MODEL_PATH)
print(f"{MODEL_PATH}: {MODEL_PATH.stat().st_size} bytes, sha256 matches")
