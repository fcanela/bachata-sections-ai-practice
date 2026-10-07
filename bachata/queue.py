"""The queue: the stored songs that have no result of this version of the analysis.

They are analysed one at a time, in the order they arrived. The queue is not kept anywhere
of its own: it is read from the library, so it survives a restart, and a song whose result
was made by an older version is in it again.

A song whose analysis failed keeps why and after how long, and is not in the queue again
until its failure is thrown away, which only the page asks for.
"""

import threading
import time
import traceback

from bachata.model import Checkpoint
from bachata.store import RATE

# Why an analysis failed. Everything that is not one of the first three is the last.
REASONS = ("memory", "model", "sound", "other")

# What torch says when it cannot get memory. It says so with a RuntimeError, or with a
# class of that name, and torch is not imported here to ask: that takes seconds.
NO_MEMORY = ("allocate memory", "out of memory", "not enough memory")


class Unreadable(Exception):
    """The stored sound of a song could not be read as samples."""


def reason_of(error):
    """Which of the four reasons an exception of the analysis is."""
    if isinstance(error, Unreadable):
        return "sound"
    if isinstance(error, Checkpoint):
        return "model"
    if isinstance(error, MemoryError) or any(kind.__name__ == "OutOfMemoryError" for kind in type(error).__mro__):
        return "memory"
    if isinstance(error, RuntimeError) and any(said in str(error).lower() for said in NO_MEMORY):
        return "memory"
    return "other"


def failure_of(result):
    """What is said of a stored failure: the reason, and for how long the analysis ran.

    A failure stored before reasons were kept has neither, and is of no known reason
    and of no known length.
    """
    reason = result.get("reason")
    return {"reason": reason if reason in REASONS else "other", "seconds": result.get("seconds")}


class Queue:
    def __init__(self, store, analyse, version):
        self._store = store
        self._analyse = analyse
        self._version = version
        self._current = None
        self._wake = threading.Event()
        self._stopping = False
        self._thread = None

    def state(self, song):
        """waiting, analysing, ready or failed."""
        result = song["result"]
        if result is not None and result["version"] == self._version:
            return "failed" if "error" in result else "ready"
        return "analysing" if song["id"] == self._current else "waiting"

    def run_one(self):
        """Analyses the first song that waits. Returns whether there was one."""
        waiting = [song for song in self._store.songs() if self.state(song) == "waiting"]
        if not waiting:
            return False
        song_id = waiting[0]["id"]
        self._current = song_id
        started = time.monotonic()
        try:
            try:
                result = self._analyse(self._samples(song_id), RATE)
                result = {"version": self._version, **result, "seconds": round(time.monotonic() - started, 1)}
            except Exception as error:
                # One song that cannot be analysed must not stop the ones after it.
                if self._store.song(song_id) is not None:
                    traceback.print_exc()
                # The sound was not read by the analysis: the name kept is of what went wrong there.
                cause = error.__cause__ if isinstance(error, Unreadable) else error
                result = {
                    "version": self._version,
                    "error": type(cause).__name__,
                    "reason": reason_of(error),
                    "seconds": round(time.monotonic() - started, 1),
                }
            # A song deleted while it was analysed is finished and then discarded: the
            # tracker works on a whole song and cannot be stopped half way.
            self._store.write_result(song_id, result)
        finally:
            self._current = None
        return True

    def _samples(self, song_id):
        try:
            return self._store.samples(song_id)
        except Exception as error:
            raise Unreadable(song_id) from error

    def wake(self):
        """Tells the queue that a song arrived, or that one waits again."""
        self._wake.set()

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stopping = True
        self._wake.set()
        self._thread.join()

    def _run(self):
        while not self._stopping:
            try:
                analysed = self.run_one()
            except Exception:
                # The library could not be read or written, a full disk for one. The
                # queue stays alive and tries again when the next song arrives.
                traceback.print_exc()
                analysed = False
            if not analysed:
                self._wake.wait()
                self._wake.clear()
