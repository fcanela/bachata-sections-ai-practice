"""The queue: the stored songs that have no result of this version of the analysis.

They are analysed one at a time, in the order they arrived. The queue is not kept anywhere
of its own: it is read from the library, so it survives a restart, and a song whose result
was made by an older version is in it again.
"""

import threading
import time
import traceback

from bachata.store import RATE


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
                result = self._analyse(self._store.samples(song_id), RATE)
                result = {"version": self._version, **result, "seconds": round(time.monotonic() - started, 1)}
            except Exception as error:
                # One song that cannot be analysed must not stop the ones after it.
                if self._store.song(song_id) is not None:
                    traceback.print_exc()
                result = {"version": self._version, "error": type(error).__name__}
            # A song deleted while it was analysed is finished and then discarded: the
            # tracker works on a whole song and cannot be stopped half way.
            self._store.write_result(song_id, result)
        finally:
            self._current = None
        return True

    def wake(self):
        """Tells the queue that a song arrived."""
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
