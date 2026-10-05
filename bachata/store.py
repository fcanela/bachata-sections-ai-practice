"""The library: the songs the server remembers, in one data folder.

    <data>/songs/<id>/song.json     the name, the length and when the song arrived
    <data>/songs/<id>/sound.raw     the sound: the samples, exactly as they were uploaded
    <data>/songs/<id>/result.json   the results, with the version of the analysis that made them
    <data>/tmp/                     songs on their way in or out

Nothing is written outside the data folder. Names on disk come from the song's id, which
is checked here, and never from text a page sent.

The sound is kept as the plain samples the page sent: 16 bits, left and right in turn, at
44.1 kHz. The server never reads a media file made elsewhere. FLAC would take about half
the room, but Chrome does not decode it back to the same samples (LOG.md, session 3).
"""

import itertools
import json
import os
import re
import shutil
import threading
import time
from pathlib import Path

import numpy as np

# What an upload must be: 16-bit samples, left and right in turn, at 44.1 kHz.
RATE = 44100
CHANNELS = 2
BYTES_PER_FRAME = 4

MIN_SECONDS = 20
MAX_SECONDS = 15 * 60
MAX_NAME = 200
LIBRARY_LIMIT_BYTES = 20 * 1000**3

ID = re.compile(r"[0-9a-f]{32}")


def well_formed(song_id):
    return isinstance(song_id, str) and ID.fullmatch(song_id) is not None


class Known(Exception):
    """The song is already in the library."""


class Store:
    def __init__(self, folder, limit=LIBRARY_LIMIT_BYTES):
        self._limit = limit
        self._songs_folder = Path(folder) / "songs"
        self._tmp = Path(folder) / "tmp"
        self._songs_folder.mkdir(parents=True, exist_ok=True)
        # Whatever is in tmp was interrupted: an upload that never finished, or a deletion.
        shutil.rmtree(self._tmp, ignore_errors=True)
        self._tmp.mkdir()
        self._lock = threading.Lock()
        self._unique = itertools.count()
        # What is on disk, read once. From here on this process is the only writer.
        self._songs = {}
        for song_folder in self._songs_folder.iterdir():
            if well_formed(song_folder.name):
                song = json.loads((song_folder / "song.json").read_text())
                song["result"] = self._read_result(song_folder.name)
                self._songs[song_folder.name] = song

    def _folder(self, song_id):
        if not well_formed(song_id):
            raise ValueError("not a song id")
        return self._songs_folder / song_id

    def _read_result(self, song_id):
        try:
            return json.loads((self._folder(song_id) / "result.json").read_text())
        except FileNotFoundError:
            return None

    def _new_tmp(self, song_id):
        self._folder(song_id)
        return self._tmp / f"{song_id}.{next(self._unique)}"

    def songs(self):
        """Every song, in the order they arrived."""
        with self._lock:
            return sorted(self._songs.values(), key=lambda song: (song["added"], song["id"]))

    def song(self, song_id):
        with self._lock:
            return self._songs.get(song_id)

    def full(self):
        """Whether the library has reached its limit on disk."""
        return sum(file.stat().st_size for file in self._songs_folder.glob("*/*")) >= self._limit

    def incoming(self, song_id):
        """A file inside the data folder where an upload is written before it is added."""
        folder = self._new_tmp(song_id)
        folder.mkdir()
        return folder / "upload"

    def add(self, song_id, name, upload):
        """Adds a song whose samples are in `upload`, a file from incoming().

        The song appears in the library all at once, or not at all.
        """
        folder = upload.parent
        try:
            frames = upload.stat().st_size // BYTES_PER_FRAME
            upload.rename(folder / "sound.raw")
            song = {"id": song_id, "name": name, "frames": frames, "added": time.time_ns()}
            (folder / "song.json").write_text(json.dumps(song))
            with self._lock:
                if song_id in self._songs:
                    raise Known(song_id)
                os.rename(folder, self._folder(song_id))
                self._songs[song_id] = {**song, "result": None}
        finally:
            shutil.rmtree(folder, ignore_errors=True)

    def discard(self, upload):
        """Removes a file from incoming() that will not be added."""
        shutil.rmtree(upload.parent, ignore_errors=True)

    def sound_path(self, song_id):
        return self._folder(song_id) / "sound.raw"

    def samples(self, song_id):
        """The stored sound: one row per moment, one column per channel."""
        return np.fromfile(self.sound_path(song_id), dtype="<i2").reshape(-1, CHANNELS)

    def write_result(self, song_id, result):
        """Keeps the result of an analysis. Does nothing when the song was deleted meanwhile."""
        partial = self._new_tmp(song_id)
        partial.write_text(json.dumps(result))
        with self._lock:
            if song_id in self._songs:
                os.replace(partial, self._folder(song_id) / "result.json")
                self._songs[song_id]["result"] = result
            else:
                partial.unlink()

    def delete(self, song_id):
        """Removes a song. Returns whether it was there."""
        with self._lock:
            if self._songs.pop(song_id, None) is None:
                return False
            gone = self._new_tmp(song_id)
            os.rename(self._folder(song_id), gone)
        shutil.rmtree(gone, ignore_errors=True)
        return True
