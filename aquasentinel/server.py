"""Loopback-only local prototype; intentionally has no public-deployment auth."""
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import time
from urllib.parse import urlparse, parse_qs
from .store import Store, Conflict
from .demo import seed

WEB = Path(__file__).resolve().parent.parent / "web"


def make_handler(store):
    class Handler(BaseHTTPRequestHandler):
        def respond(self, status, value, content_type="application/json"):
            body = json.dumps(value, allow_nan=False).encode() if content_type == "application/json" else value
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            try:
                if parsed.path == "/api/health":
                    return self.respond(200, {"status": "ok", "mode": "local-prototype"})
                if parsed.path == "/api/streams":
                    return self.respond(200, {"streams": store.streams()})
                if parsed.path == "/api/snapshot":
                    started = time.perf_counter()
                    result = store.snapshot(query.get("stream", ["demo-creek-a"])[0], query.get("as_of", [None])[0])
                    result["query_ms"] = round((time.perf_counter() - started) * 1000, 3)
                    return self.respond(200, result)
                files = {"/": ("index.html", "text/html; charset=utf-8"), "/app.js": ("app.js", "text/javascript; charset=utf-8"), "/style.css": ("style.css", "text/css; charset=utf-8")}
                if parsed.path in files:
                    name, mime = files[parsed.path]
                    return self.respond(200, (WEB / name).read_bytes(), mime)
                self.respond(404, {"error": "Not found"})
            except (ValueError, TypeError) as exc:
                self.respond(400, {"error": str(exc)})

        def do_POST(self):
            # Browser requests must originate from this local UI, not another website.
            origin = self.headers.get("Origin")
            expected_origin = f"http://127.0.0.1:{self.server.server_port}"
            if self.headers.get("Host") != f"127.0.0.1:{self.server.server_port}" or (origin and origin != expected_origin):
                return self.respond(403, {"error": "Local same-origin requests only"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 32000:
                    return self.respond(413, {"error": "Body must be 1–32000 bytes"})
                if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                    return self.respond(415, {"error": "JSON required"})
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValueError("Expected a JSON object")
                if self.path == "/api/observations":
                    result = store.ingest(data)
                    return self.respond(200 if result["duplicate"] else 201, result)
                if self.path == "/api/reviews":
                    return self.respond(201, store.review(data["stream_id"], data["decision_hash"], data["action"], data["note"]))
                self.respond(404, {"error": "Not found"})
            except Conflict as exc:
                self.respond(409, {"error": str(exc)})
            except (ValueError, TypeError, KeyError) as exc:
                self.respond(400, {"error": str(exc)})
    return Handler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--db", default="runtime/aquasentinel.sqlite3")
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()
    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    store = Store(args.db)
    if args.demo and not store.streams():
        seed(store)
    server = HTTPServer(("127.0.0.1", args.port), make_handler(store))
    print(f"AquaSentinel local prototype: http://127.0.0.1:{args.port}", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        store.close()


if __name__ == "__main__":
    main()
