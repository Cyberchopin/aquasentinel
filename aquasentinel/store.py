"""SQLite event log with immutable ingestion and snapshot-bound reviews."""
import json
import sqlite3
from .engine import assess, digest, now, utc, validate


class Conflict(ValueError):
    pass


class Store:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript('''
          CREATE TABLE IF NOT EXISTS observations (
            id TEXT PRIMARY KEY, source_id TEXT NOT NULL, external_id TEXT NOT NULL,
            stream_id TEXT NOT NULL, observed_at TEXT NOT NULL, received_at TEXT NOT NULL,
            payload TEXT NOT NULL, UNIQUE(source_id, external_id));
          CREATE INDEX IF NOT EXISTS stream_time ON observations(stream_id, received_at, observed_at);
          CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY, stream_id TEXT NOT NULL, reviewed_at TEXT NOT NULL,
            decision_hash TEXT NOT NULL, action TEXT NOT NULL, note TEXT NOT NULL,
            snapshot TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS environmental_datasets (
            id TEXT PRIMARY KEY, stream_id TEXT NOT NULL, imported_at TEXT NOT NULL,
            payload TEXT NOT NULL);
          CREATE INDEX IF NOT EXISTS context_stream_time ON environmental_datasets(stream_id, imported_at);
          CREATE TABLE IF NOT EXISTS weather_captures (
            id TEXT PRIMARY KEY, stream_id TEXT NOT NULL, fetched_at TEXT NOT NULL,
            imported_at TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS alert_outbox (
            id INTEGER PRIMARY KEY, stream_id TEXT NOT NULL, created_at TEXT NOT NULL,
            decision_hash TEXT NOT NULL, level TEXT NOT NULL,
            UNIQUE(stream_id, decision_hash, level));
        ''')
        self.db.commit()
        from .audit import install
        install(self.db)

    def close(self):
        self.db.close()

    def ingest(self, payload, received_at=None):
        record = validate(payload, received_at or now())
        existing = self.db.execute("SELECT payload FROM observations WHERE id=?", (record["id"],)).fetchone()
        if existing:
            old = json.loads(existing["payload"])
            old.setdefault('source_type', 'synthetic' if old['synthetic'] else 'real')
            old.setdefault('record_type', 'rainfall_context' if old['signal'] == 'rainfall' else 'citizen_report')
            if {k: v for k, v in old.items() if k != "received_at"} != {k: v for k, v in record.items() if k != "received_at"}:
                raise Conflict("This source/external_id already exists with different content")
            return {"duplicate": True, "observation": old}
        with self.db:
            self.db.execute("INSERT INTO observations VALUES (?,?,?,?,?,?,?)", (
                record["id"], record["source_id"], record["external_id"], record["stream_id"],
                record["observed_at"], record["received_at"], json.dumps(record, sort_keys=True)))
        return {"duplicate": False, "observation": record}

    def snapshot(self, stream_id, as_of=None):
        time = utc(as_of or now())
        rows = self.db.execute("SELECT payload FROM observations WHERE stream_id=? AND received_at<=? ORDER BY received_at,id", (stream_id, time))
        decision = assess([json.loads(r[0]) for r in rows], stream_id, time)
        context = self.environmental_context(stream_id, time)
        if context:
            # Background does not vote in triage, but reviewers must see/review
            # the exact archive version they had available.
            decision["environmental_context"] = context
            decision["decision_hash"] = digest({"triage_hash": decision["decision_hash"], "context": context})
        from .weather import watch
        from .config import station
        forecast = self.forecast_at(stream_id, time)
        cfg = station()
        warning = watch(forecast, time, cfg['watch_rain_mm'], cfg['watch_window_hours'])
        decision['forecast'] = forecast
        decision['watch'] = warning
        if forecast:
            decision['decision_hash'] = digest({'evidence_hash': decision['decision_hash'],
                'forecast_id': forecast['capture_id'],
                'watch': {k: v for k, v in warning.items() if k != 'lead_hours'} if warning else None})
        decision['alerts'] = [dict(r) for r in self.db.execute(
            'SELECT * FROM alert_outbox WHERE stream_id=? AND created_at<=? ORDER BY created_at,id', (stream_id, time))]
        for alert in decision['alerts']:
            alert['status'] = 'active' if alert['decision_hash'] == decision['decision_hash'] else 'retracted'
            alert['dry_run'] = True
        reviews = [dict(r) for r in self.db.execute(
            "SELECT id,reviewed_at,decision_hash,action,note FROM reviews WHERE stream_id=? AND reviewed_at<=? ORDER BY reviewed_at,id",
            (stream_id, time))]
        decision["reviews"] = reviews
        latest = reviews[-1] if reviews else None
        decision["review_current"] = bool(latest and latest["decision_hash"] == decision["decision_hash"])
        decision["display_state"] = latest["action"] if decision["review_current"] else decision["state"]
        return decision

    def review(self, stream_id, expected_hash, action, note, reviewed_at=None):
        if action not in {"dismissed", "follow_up_required"}:
            raise ValueError("Unsupported review action")
        if not isinstance(note, str) or not note.strip() or len(note) > 1500:
            raise ValueError("Review requires a note (1–1500 characters)")
        time = utc(reviewed_at or now())
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            decision = self.snapshot(stream_id, time)
            if decision["decision_hash"] != expected_hash:
                raise Conflict("Evidence changed; refresh and review the current snapshot")
            if not decision["evidence"]:
                raise ValueError("Cannot review an empty snapshot")
            self.db.execute("INSERT INTO reviews(stream_id,reviewed_at,decision_hash,action,note,snapshot) VALUES(?,?,?,?,?,?)",
                            (stream_id, time, expected_hash, action, note.strip(), json.dumps(decision, sort_keys=True)))
        return self.snapshot(stream_id, time)

    def streams(self):
        return [r[0] for r in self.db.execute("SELECT stream_id FROM observations UNION SELECT stream_id FROM environmental_datasets UNION SELECT stream_id FROM weather_captures ORDER BY stream_id")]

    def import_weather(self, capture, imported_at=None):
        from .weather import validate_capture
        c = validate_capture(capture)
        time = utc(imported_at or now())
        if time < c['fetched_at']:
            raise ValueError('Import cannot predate forecast receipt')
        with self.db:
            cursor = self.db.execute('INSERT OR IGNORE INTO weather_captures VALUES(?,?,?,?,?,?)',
                (c['capture_id'], c['stream_id'], c['fetched_at'], time, c['kind'], json.dumps(c, sort_keys=True)))
        return cursor.rowcount == 1

    def forecast_at(self, stream_id, as_of):
        at = utc(as_of)
        row = self.db.execute("SELECT payload,imported_at FROM weather_captures WHERE stream_id=? AND kind='forecast' AND fetched_at<=? AND imported_at<=? ORDER BY fetched_at DESC,id DESC LIMIT 1", (stream_id, at, at)).fetchone()
        return json.loads(row[0]) | {'imported_at': row[1]} if row else None

    def queue_alert(self, stream_id, at=None):
        time = utc(at or now())
        snapshot = self.snapshot(stream_id, time)
        level = 'review' if snapshot['state'] == 'review_recommended' else 'watch' if snapshot['watch'] else None
        if level:
            with self.db:
                self.db.execute('INSERT OR IGNORE INTO alert_outbox(stream_id,created_at,decision_hash,level) VALUES(?,?,?,?)',
                    (stream_id, time, snapshot['decision_hash'], level))
        return self.snapshot(stream_id, time)

    def import_environment(self, folder, imported_at=None):
        from .usgs import load_bundle
        dataset = load_bundle(folder)
        time = utc(imported_at or now())
        if time < dataset["retrieved_at"]:
            raise ValueError("Import time cannot predate dataset retrieval")
        payload = json.dumps(dataset, sort_keys=True, allow_nan=False)
        existing = self.db.execute("SELECT payload FROM environmental_datasets WHERE id=?", (dataset["dataset_id"],)).fetchone()
        if existing:
            if existing[0] != payload:
                raise Conflict("Dataset ID already exists with different content")
            return False
        with self.db:
            self.db.execute("INSERT INTO environmental_datasets VALUES(?,?,?,?)",
                            (dataset["dataset_id"], dataset["stream_id"], time, payload))
        return True

    def environmental_context(self, stream_id, as_of):
        row = self.db.execute("SELECT imported_at,payload FROM environmental_datasets WHERE stream_id=? AND imported_at<=? ORDER BY imported_at DESC,id DESC LIMIT 1",
                              (stream_id, utc(as_of))).fetchone()
        if not row:
            return None
        return json.loads(row["payload"]) | {"imported_at": row["imported_at"]}
