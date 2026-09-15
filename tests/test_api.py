"""HTTP contracts tested against an isolated local server and temporary database."""
import json
from http.server import HTTPServer
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from aquasentinel.server import make_handler
from aquasentinel.store import Store
from aquasentinel.engine import now


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.ready = threading.Event()
        def run():
            store = Store(str(Path(self.temp.name) / "api.sqlite3"))
            handler = make_handler(store)
            handler.log_message = lambda *args: None
            self.server = HTTPServer(("127.0.0.1", 0), handler)
            self.ready.set()
            self.server.serve_forever(poll_interval=.01)
            self.server.server_close()
            store.close()
        self.thread = threading.Thread(target=run)
        self.thread.start()
        self.assertTrue(self.ready.wait(5))
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.thread.join(5)
        self.temp.cleanup()

    def call(self, path, data=None, headers=None):
        defaults = {"Content-Type": "application/json"} if data is not None else {}
        request = Request(self.base + path, data=json.dumps(data).encode() if data is not None else None,
                          headers=defaults | (headers or {}))
        try:
            response = urlopen(request, timeout=5)
        except HTTPError as exc:
            response = exc
        with response:
            return response.status, json.loads(response.read())

    def test_ingest_review_and_duplicate_over_http(self):
        payload = dict(source_id="demo", external_id="one", stream_id="test", observed_at=now(),
                       lat=33, lon=-117, signal="odor", synthetic=True)
        self.assertEqual(self.call("/api/observations", payload)[0], 201)
        status, result = self.call("/api/observations", payload)
        self.assertEqual(status, 200)
        self.assertTrue(result["duplicate"])
        status, decision = self.call("/api/snapshot?stream=test")
        self.assertEqual(status, 200)
        status, reviewed = self.call("/api/reviews", dict(stream_id="test", decision_hash=decision["decision_hash"],
                                                        action="follow_up_required", note="Test review"))
        self.assertEqual(status, 201)
        self.assertTrue(reviewed["review_current"])

    def test_invalid_json_shape_and_timestamp_are_client_errors(self):
        self.assertEqual(self.call("/api/observations", [1, 2])[0], 400)
        self.assertEqual(self.call("/api/snapshot?as_of=invalid")[0], 400)

    def test_cross_origin_write_is_rejected(self):
        self.assertEqual(self.call("/api/observations", {}, {"Origin": "https://other.example"})[0], 403)

    def test_unknown_paths_are_not_served(self):
        self.assertEqual(self.call("/../../aquasentinel/store.py")[0], 404)


if __name__ == "__main__":
    unittest.main()
