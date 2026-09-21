"""Loopback-only local prototype; intentionally has no public-deployment auth."""
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
import secrets
from http.cookies import SimpleCookie
from pathlib import Path
import time
from urllib.parse import urlparse, parse_qs
from .store import Store, Conflict
from .demo import seed

WEB = Path(__file__).resolve().parent.parent / "web"


def make_handler(store, read_only=False, public_demo=False, public_origin=None):
    sessions = {}
    def session(token):
        current = time.monotonic()
        for key in list(sessions):
            if current - sessions[key][1] > 3600:
                sessions.pop(key)[0].close()
        if token not in sessions:
            if len(sessions) >= 50:
                raise ValueError('Demo busy; try later')
            token = secrets.token_urlsafe(32)
            sandbox = Store(':memory:')
            store.db.backup(sandbox.db)
            sessions[token] = [sandbox, current, current, 0]
        item = sessions[token]
        item[1] = current
        if current - item[2] > 60:
            item[2], item[3] = current, 0
        item[3] += 1
        if item[3] > 120:
            raise ValueError('Demo rate limit; retry in one minute')
        return token, item[0]

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(10)

        def select_store(self):
            self.active_store = store
            self.session_cookie = None
            if public_demo:
                cookies = SimpleCookie()
                try:
                    cookies.load(self.headers.get('Cookie', ''))
                except Exception:
                    cookies = SimpleCookie()
                token = cookies['aqua_session'].value if 'aqua_session' in cookies else None
                token, self.active_store = session(token)
                self.session_cookie = token

        def respond(self, status, value, content_type="application/json"):
            body = json.dumps(value, allow_nan=False).encode() if content_type == "application/json" else value
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            if getattr(self, 'session_cookie', None):
                secure = '; Secure' if public_origin and public_origin.startswith('https:') else ''
                self.send_header('Set-Cookie', 'aqua_session='+self.session_cookie+'; HttpOnly; SameSite=Strict; Path=/; Max-Age=3600'+secure)
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            try:
                self.select_store()
            except ValueError as exc:
                return self.respond(429, {'error': str(exc)})
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            try:
                if parsed.path == "/api/health":
                    return self.respond(200, {"status": "ok", "mode": "public-demo-sandbox" if public_demo else "read-only-replay" if read_only else "local-prototype"})
                if parsed.path == "/api/geometry":
                    from .geo import features
                    return self.respond(200, features())
                if parsed.path == "/api/reach":
                    from .geo import match
                    return self.respond(200, match(float(query.get('lon',['nan'])[0]),float(query.get('lat',['nan'])[0])))
                if parsed.path == "/api/streams":
                    return self.respond(200, {"streams": self.active_store.streams()})
                if parsed.path in {"/api/brief", "/api/fhir"}:
                    from .exports import brief, fhir_bundle
                    snapshot = self.active_store.snapshot(query.get("stream", ["demo-creek-a"])[0], query.get("as_of", [None])[0])
                    if parsed.path == "/api/brief":
                        return self.respond(200, brief(snapshot).encode(), "text/html; charset=utf-8")
                    return self.respond(200, fhir_bundle(snapshot))
                if parsed.path == "/api/snapshot":
                    started = time.perf_counter()
                    result = self.active_store.snapshot(query.get("stream", ["demo-creek-a"])[0], query.get("as_of", [None])[0])
                    result["query_ms"] = round((time.perf_counter() - started) * 1000, 3)
                    return self.respond(200, result)
                files = {"/": ("index.html", "text/html; charset=utf-8"), "/app.js": ("app.js", "text/javascript; charset=utf-8"), "/style.css": ("style.css", "text/css; charset=utf-8")}
                files.update({"/vendor/leaflet.js": ("vendor/leaflet.js", "text/javascript"), "/vendor/leaflet.css": ("vendor/leaflet.css", "text/css")})
                if parsed.path in files:
                    name, mime = files[parsed.path]
                    return self.respond(200, (WEB / name).read_bytes(), mime)
                self.respond(404, {"error": "Not found"})
            except (ValueError, TypeError) as exc:
                self.respond(400, {"error": str(exc)})

        def do_POST(self):
            if read_only:
                return self.respond(403, {"error": "Shared replay is read-only"})
            try:
                self.select_store()
            except ValueError as exc:
                return self.respond(429, {'error': str(exc)})
            # Browser requests must originate from this local UI, not another website.
            origin = self.headers.get("Origin")
            expected_origin = public_origin or f"http://127.0.0.1:{self.server.server_port}"
            if self.headers.get("Host") != urlparse(expected_origin).netloc or (origin and origin != expected_origin):
                return self.respond(403, {"error": "Local same-origin requests only"})
            try:
                if public_demo and self.active_store.db.execute('SELECT count(*) FROM observations').fetchone()[0] >= 500:
                    return self.respond(429, {'error': 'Session record limit reached'})
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 32000:
                    return self.respond(413, {"error": "Body must be 1–32000 bytes"})
                if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                    return self.respond(415, {"error": "JSON required"})
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValueError("Expected a JSON object")
                if self.path == "/api/observations":
                    result = self.active_store.ingest(data)
                    self.active_store.queue_alert(result["observation"]["stream_id"])
                    return self.respond(200 if result["duplicate"] else 201, result)
                if self.path == "/api/alerts":
                    return self.respond(200, self.active_store.queue_alert(data["stream_id"]))
                if self.path == "/api/reviews":
                    return self.respond(201, self.active_store.review(data["stream_id"], data["decision_hash"], data["action"], data["note"]))
                self.respond(404, {"error": "Not found"})
            except Conflict as exc:
                self.respond(409, {"error": str(exc)})
            except (ValueError, TypeError, KeyError) as exc:
                self.respond(400, {"error": str(exc)})
    return Handler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8765")))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--read-only", action="store_true")
    parser.add_argument("--public-demo", action="store_true")
    parser.add_argument("--public-origin", default=os.environ.get("PUBLIC_ORIGIN"))
    parser.add_argument("--weather-dir", type=Path)
    parser.add_argument("--db", default="runtime/aquasentinel.sqlite3")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--usgs-fixture", nargs="?", const=str(Path(__file__).resolve().parent.parent / "data" / "usgs-arroyo-seco-2024-02"),
                        help="Import a verified USGS offline archive (optional custom directory)")
    args = parser.parse_args()
    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    store = Store(args.db)
    if args.demo and not store.streams():
        seed(store)
    if args.usgs_fixture:
        store.import_environment(args.usgs_fixture)
    if args.weather_dir:
        for path in sorted(args.weather_dir.glob("*.json")):
            store.import_weather(json.loads(path.read_text(encoding="utf-8")))
    if args.public_demo and (args.read_only or not args.public_origin):
        parser.error("--public-demo requires --public-origin and cannot combine with --read-only")
    if args.host != "127.0.0.1" and not (args.read_only or args.public_demo):
        parser.error("External binding currently requires --read-only")
    server = HTTPServer((args.host, args.port), make_handler(store, args.read_only, args.public_demo, args.public_origin))
    print(f"AquaSentinel local prototype: http://127.0.0.1:{args.port}", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        store.close()


if __name__ == "__main__":
    main()
