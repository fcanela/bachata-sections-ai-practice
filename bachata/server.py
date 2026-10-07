"""The web program: the page, and the addresses the page talks to.

    GET    /api/songs               the list, in the order the songs arrived
    GET    /api/songs/<id>          one song, or 404 when the id is not in the library
    PUT    /api/songs/<id>          an upload: ?name=...&rate=44100&frames=N, and the samples
    GET    /api/songs/<id>/sound    the stored sound
    GET    /api/songs/<id>/result   the beats, with the tempo, the place in the bar and the
                                    count at each, once the song is ready
    PATCH  /api/songs/<id>          a new name: ?name=...
    PUT    /api/songs/<id>/ones     the beat at ?at=<seconds> is count 1
    DELETE /api/songs/<id>/ones     it no longer is
    DELETE /api/songs/<id>/result   try again: the result of an analysis that failed is thrown
                                    away, and the song waits. 409 unless the song has failed
    DELETE /api/songs/<id>          a deletion

An upload is plain samples: 16 bits, little-endian, left and right in turn, at 44.1 kHz,
4 bytes for each of the N moments. The stored sound comes back as the same bytes. The page
decodes the file; the server never reads a media file made elsewhere, and it checks again
every limit the page checked.

Every answer carries the security headers, including the 404s and the errors.
"""

import contextlib
import json
import re
from pathlib import Path

from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import MutableHeaders
from starlette.requests import ClientDisconnect
from starlette.responses import FileResponse, PlainTextResponse, Response
from starlette.routing import Route

from bachata.analysis import ANALYSIS_VERSION
from bachata.queue import Queue, failure_of
from bachata.store import (
    BYTES_PER_FRAME,
    LIBRARY_LIMIT_BYTES,
    MAX_NAME,
    MAX_ONES,
    MAX_SECONDS,
    MIN_SECONDS,
    RATE,
    Known,
    Store,
    TooMany,
    well_formed,
)

WEB = Path(__file__).parent.parent / "web"

SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    # No other site may embed a stored sound or anything else from here.
    "Cross-Origin-Resource-Policy": "same-origin",
}

# The files of the page. They are read once at startup: a request never becomes a file path.
PAGE_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/song.js": ("song.js", "text/javascript; charset=utf-8"),
    "/draw.js": ("draw.js", "text/javascript; charset=utf-8"),
    # The typeface. web/fonts/LICENSE.txt says where it comes from.
    "/fonts/hind-500.woff2": ("fonts/hind-500.woff2", "font/woff2"),
    "/fonts/hind-700.woff2": ("fonts/hind-700.woff2", "font/woff2"),
}

# The names the program answers to. A request for any other host is refused, so a
# foreign domain pointed at 127.0.0.1 cannot make a browser treat the library as its own.
HOSTS = ("127.0.0.1", "localhost")


class Refused(Exception):
    def __init__(self, status, reason):
        self.status = status
        self.reason = reason


def refused(request, exc):
    return PlainTextResponse(exc.reason + "\n", status_code=exc.status)


def not_found(request=None, exc=None):
    return PlainTextResponse("Not found\n", status_code=404)


def answer(content, status=200):
    # The list changes while a song is analysed: a browser must not keep an old answer.
    return Response(json.dumps(content), status, {"Cache-Control": "no-store"}, "application/json")


class Guard:
    """Refuses requests for another host and adds the security headers to every answer.

    It wraps the whole application, so it also covers the answers Starlette makes itself.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in SECURITY_HEADERS.items():
                    headers[name] = value
            await send(message)

        hosts = [value.decode("latin-1") for name, value in scope["headers"] if name == b"host"]
        if len(hosts) != 1 or hosts[0].rsplit(":", 1)[0] not in HOSTS:
            response = PlainTextResponse("Unknown host\n", status_code=400)
            return await response(scope, receive, send_with_headers)
        await self.app(scope, receive, send_with_headers)


def from_own_page(request):
    """Whether a request was made by the application's own page.

    A browser states the origin of the page behind every request that is not a plain read,
    and a page cannot change what it states. A page of another site therefore shows its
    own origin here, and a program that is not a browser shows none.
    """
    own = f"http://{request.headers['host']}"
    return request.headers.get("origin") == own and request.headers.get("sec-fetch-site", "same-origin") == "same-origin"


def checked_name(name):
    """The name of a song as the page sent it, or a refusal."""
    if name is None or name.strip() == "":
        raise Refused(400, "The song has no name")
    if len(name) > MAX_NAME:
        raise Refused(400, f"The name is longer than {MAX_NAME} characters")
    if any(ord(character) < 32 or ord(character) == 127 for character in name):
        raise Refused(400, "The name has control characters")
    return name


# A time in seconds as the page writes it: digits, and up to three more after a point.
SECONDS = re.compile(r"[0-9]{1,4}(\.[0-9]{1,3})?", re.ASCII)


def checked_time(at, song):
    """A time inside a song, in seconds, as the page sent it, or a refusal."""
    if at is None or SECONDS.fullmatch(at) is None:
        raise Refused(400, "The time is not a number of seconds")
    if float(at) > song["frames"] / RATE:
        raise Refused(400, "The time is after the end of the song")
    return float(at)


def checked_frames(request):
    """The number of moments an upload says it holds, or a refusal."""
    query = request.query_params
    if query.get("rate") != str(RATE):
        raise Refused(400, f"The samples must be at {RATE} Hz")
    frames = query.get("frames", "")
    if not (frames.isascii() and frames.isdigit() and len(frames) <= 12):
        raise Refused(400, "The number of frames is missing")
    frames = int(frames)
    if frames < MIN_SECONDS * RATE:
        raise Refused(400, f"The song is shorter than {MIN_SECONDS} seconds")
    if frames > MAX_SECONDS * RATE:
        raise Refused(413, f"The song is longer than {MAX_SECONDS // 60} minutes")
    if request.headers.get("content-length") != str(frames * BYTES_PER_FRAME):
        raise Refused(400, "The body is not 4 bytes for every frame")
    return frames


def create_app(data, analyse=None, version=ANALYSIS_VERSION, limit=LIBRARY_LIMIT_BYTES):
    """The application, with its library in the folder `data`.

    `analyse` and `version` are the analysis and its version. The tests pass their own.
    """
    if analyse is None:
        from bachata.analysis import analyse

    store = Store(data, limit)
    queue = Queue(store, analyse, version)

    def shown(song):
        state = queue.state(song)
        listed = {
            "id": song["id"],
            "name": song["name"],
            "state": state,
            "seconds": round(song["frames"] / RATE, 1),
            # The beats the user said are count 1, as times. The list is asked for every
            # two seconds, so every browser learns of a change.
            "ones": song["ones"],
        }
        if state == "failed":
            # Why, and after how long. The name of the exception stays in the library.
            listed["failure"] = failure_of(song["result"])
        return listed

    def song_id_of(request):
        song_id = request.path_params["id"]
        if not well_formed(song_id):
            raise Refused(400, "Not a song id")
        return song_id

    def song_of(request):
        song = store.song(song_id_of(request))
        if song is None:
            raise Refused(404, "No such song")
        return song

    def page_file(name, content_type):
        body = (WEB / name).read_bytes()

        async def endpoint(request):
            # A browser asks again every time, so the page never runs with an old part.
            return Response(body, media_type=content_type, headers={"Cache-Control": "no-cache"})

        return endpoint

    async def list_songs(request):
        return answer([shown(song) for song in store.songs()])

    async def one_song(request):
        return answer(shown(song_of(request)))

    async def sound(request):
        song = song_of(request)
        # The samples, as they were uploaded. They are data and nothing else: a browser
        # that is sent here saves them, it never shows them.
        return FileResponse(
            store.sound_path(song["id"]),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{song["id"]}.raw"'},
        )

    async def result(request):
        song = song_of(request)
        if queue.state(song) != "ready":
            raise Refused(404, "No result yet")
        return answer({key: song["result"][key] for key in ("beats", "bpm", "bar", "count")})

    async def upload(request):
        if not from_own_page(request):
            raise Refused(403, "Not from the application's own page")
        song_id = song_id_of(request)
        name = checked_name(request.query_params.get("name"))
        expected = checked_frames(request) * BYTES_PER_FRAME
        if store.song(song_id) is not None:
            raise Refused(409, "The song is already in the library")
        if store.full():
            raise Refused(507, "The library is full")

        incoming = store.incoming(song_id)
        try:
            received = 0
            with open(incoming, "wb") as file:
                async for chunk in request.stream():
                    received += len(chunk)
                    if received > expected:
                        break
                    file.write(chunk)
            if received != expected:
                raise Refused(400, "The body is not 4 bytes for every frame")
            await run_in_threadpool(store.add, song_id, name, incoming)
        except ClientDisconnect:
            return Response(status_code=400)
        except Known:
            raise Refused(409, "The song is already in the library") from None
        finally:
            store.discard(incoming)
        queue.wake()
        return answer(shown(store.song(song_id)), 201)

    async def rename(request):
        if not from_own_page(request):
            raise Refused(403, "Not from the application's own page")
        song_id = song_id_of(request)
        name = checked_name(request.query_params.get("name"))
        if not store.rename(song_id, name):
            raise Refused(404, "No such song")
        return Response(status_code=204)

    async def set_one(request):
        if not from_own_page(request):
            raise Refused(403, "Not from the application's own page")
        song = song_of(request)
        at = checked_time(request.query_params.get("at"), song)
        try:
            found = store.set_one(song["id"], at, request.method == "PUT")
        except TooMany:
            raise Refused(400, f"The song has {MAX_ONES} beats set to count 1 already") from None
        if not found:
            raise Refused(404, "No such song")
        return Response(status_code=204)

    async def delete(request):
        if not from_own_page(request):
            raise Refused(403, "Not from the application's own page")
        if not store.delete(song_id_of(request)):
            raise Refused(404, "No such song")
        return Response(status_code=204)

    async def try_again(request):
        if not from_own_page(request):
            raise Refused(403, "Not from the application's own page")
        song = song_of(request)
        # The store looks again before it removes: of two browsers that ask at once, one
        # finds nothing to throw away, and a song that is ready by then keeps its result.
        if queue.state(song) != "failed" or not store.discard_failure(song["id"]):
            if store.song(song["id"]) is None:
                raise Refused(404, "No such song")
            raise Refused(409, "The song has not failed")
        queue.wake()
        return Response(status_code=204)

    @contextlib.asynccontextmanager
    async def lifespan(app):
        queue.start()
        yield
        queue.stop()

    routes = [Route(path, page_file(*file)) for path, file in PAGE_FILES.items()] + [
        Route("/api/songs", list_songs),
        Route("/api/songs/{id}", one_song),
        Route("/api/songs/{id}", upload, methods=["PUT"]),
        Route("/api/songs/{id}", rename, methods=["PATCH"]),
        Route("/api/songs/{id}", delete, methods=["DELETE"]),
        Route("/api/songs/{id}/ones", set_one, methods=["PUT", "DELETE"]),
        Route("/api/songs/{id}/sound", sound),
        Route("/api/songs/{id}/result", result),
        Route("/api/songs/{id}/result", try_again, methods=["DELETE"]),
    ]
    app = Starlette(
        routes=routes, exception_handlers={Refused: refused, 404: not_found, 405: not_found}, lifespan=lifespan
    )
    guarded = Guard(app)
    guarded.store, guarded.queue = store, queue
    return guarded
