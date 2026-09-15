from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from aquasentinel.store import Store, Conflict
from aquasentinel.demo import seed
from aquasentinel.engine import assess

BASE = "2026-09-15T08:00:00Z"
END = "2026-09-15T12:00:00Z"


def observation(source="one", external="1", signal="turbidity", stream="creek-a", at=BASE):
    payload = dict(source_id=source, external_id=external, stream_id=stream, observed_at=at,
                   lat=33.68, lon=-117.82, signal=signal, synthetic=True)
    if signal == "rainfall":
        payload.update(value=12, unit="mm", period_hours=6)
    return payload


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.temp.name) / "events.sqlite3")
        self.store = Store(self.path)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def ingest(self, **kwargs):
        return self.store.ingest(observation(**kwargs), BASE)

    def storm(self):
        self.ingest(source="weather", signal="rainfall")
        self.ingest(source="one")
        self.ingest(source="two")

    def test_missing_context_abstains(self):
        self.ingest()
        s = self.store.snapshot("creek-a", END)
        self.assertEqual(s["state"], "needs_corroboration")
        self.assertIn("missing", " ".join(s["reasons"]))

    def test_corroborated_storm_recommends_review(self):
        self.storm()
        self.assertEqual(self.store.snapshot("creek-a", END)["state"], "review_recommended")

    def test_duplicate_preserves_first_receipt_and_state(self):
        first = self.ingest()["observation"]
        again = self.store.ingest(observation(), END)
        self.assertTrue(again["duplicate"])
        self.assertEqual(first, again["observation"])
        self.assertEqual(len(self.store.snapshot("creek-a", END)["evidence"]), 1)

    def test_changed_payload_does_not_overwrite(self):
        self.ingest()
        with self.assertRaises(Conflict):
            self.ingest(signal="odor")
        self.assertEqual(self.store.snapshot("creek-a", END)["evidence"][0]["signal"], "turbidity")

    def test_one_source_cannot_self_corroborate(self):
        self.ingest(source="weather", signal="rainfall")
        for n in range(10):
            self.ingest(external=str(n))
        s = self.store.snapshot("creek-a", END)
        self.assertEqual(s["distinct_sources"], 1)
        self.assertEqual(s["state"], "needs_corroboration")

    def test_same_coordinates_different_stream_stays_separate(self):
        self.ingest(source="weather", signal="rainfall")
        self.ingest()
        self.ingest(source="two", stream="creek-b")
        self.assertEqual(self.store.snapshot("creek-a", END)["distinct_sources"], 1)

    def test_conflicting_normal_report_prevents_escalation(self):
        self.storm()
        self.ingest(source="three", signal="normal")
        s = self.store.snapshot("creek-a", END)
        self.assertEqual(s["state"], "needs_corroboration")
        self.assertEqual(len(s["conflict_ids"]), 1)

    def test_rain_expires_and_invalidates_old_review(self):
        self.storm()
        s = self.store.snapshot("creek-a", END)
        self.store.review("creek-a", s["decision_hash"], "follow_up_required", "Check field observations", END)
        later = self.store.snapshot("creek-a", "2026-09-15T15:00:00Z")
        self.assertEqual(later["state"], "needs_corroboration")
        self.assertFalse(later["review_current"])

    def test_late_report_never_leaks_into_earlier_replay(self):
        self.storm()
        before = self.store.snapshot("creek-a", "2026-09-15T09:00:00Z")
        self.store.ingest(observation(source="late", signal="normal"), "2026-09-15T10:00:00Z")
        replay = self.store.snapshot("creek-a", "2026-09-15T09:00:00Z")
        self.assertEqual(before, replay)
        self.assertEqual(self.store.snapshot("creek-a", END)["state"], "needs_corroboration")

    def test_review_is_time_scoped_and_invalidated_by_new_evidence(self):
        self.storm()
        s = self.store.snapshot("creek-a", "2026-09-15T09:00:00Z")
        reviewed = self.store.review("creek-a", s["decision_hash"], "dismissed", "Fixture review", "2026-09-15T09:00:00Z")
        self.assertTrue(reviewed["review_current"])
        self.assertEqual(self.store.snapshot("creek-a", BASE)["reviews"], [])
        self.store.ingest(observation(source="new"), "2026-09-15T10:00:00Z")
        self.assertFalse(self.store.snapshot("creek-a", END)["review_current"])
        self.assertEqual(len(self.store.snapshot("creek-a", END)["reviews"]), 1)
        with self.assertRaises(Conflict):
            self.store.review("creek-a", s["decision_hash"], "dismissed", "Stale", END)

    def test_restart_replay_is_identical(self):
        self.storm()
        first = self.store.snapshot("creek-a", END)
        self.store.close()
        self.store = Store(self.path)
        self.assertEqual(first, self.store.snapshot("creek-a", END))

    def test_input_order_does_not_change_assessment(self):
        self.storm()
        s = self.store.snapshot("creek-a", END)
        forward = assess(s["evidence"], "creek-a", END)
        backward = assess(list(reversed(s["evidence"])), "creek-a", END)
        self.assertEqual(forward, backward)

    def test_invalid_contracts_rejected(self):
        bad = [{"lat": float("nan")}, {"lon": 181}, {"synthetic": "true"},
               {"observed_at": "2026-09-15T08:00:00"}, {"observed_at": "2027-01-01T00:00:00Z"},
               {"source_id": ""}, {"signal": "toxic"}, {"extra": 1}]
        for patch in bad:
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                self.store.ingest(observation() | patch, BASE)
        self.assertEqual(self.store.streams(), [])

    def test_rain_units_and_finite_values_required(self):
        for patch in ({"unit": "inch"}, {"value": -1}, {"value": float("inf")}, {"value": True}, {"period_hours": 24}):
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                self.store.ingest(observation(signal="rainfall") | patch, BASE)

    def test_new_dry_rainfall_context_supersedes_old_wet_context(self):
        self.storm()
        payload = observation(source="weather", external="new", signal="rainfall", at="2026-09-15T10:00:00Z")
        payload["value"] = 0
        self.store.ingest(payload, "2026-09-15T10:00:00Z")
        s = self.store.snapshot("creek-a", END)
        self.assertEqual(s["state"], "needs_corroboration")
        self.assertIn("0 mm", " ".join(s["reasons"]))

    def test_old_data_expires_and_empty_reviews_rejected(self):
        self.ingest()
        s = self.store.snapshot("creek-a", "2026-09-17T12:00:00Z")
        self.assertEqual(s["evidence"], [])
        with self.assertRaises(ValueError):
            self.store.review("creek-a", s["decision_hash"], "dismissed", "No evidence", "2026-09-17T12:00:00Z")

    def test_demo_has_explainable_priority_transition(self):
        seed(self.store, datetime(2026, 9, 15, 8, tzinfo=timezone.utc))
        times = ["08:10", "08:40", "09:10", "10:45"]
        actual = [self.store.snapshot("demo-creek-a", f"2026-09-15T{t}:00Z")["state"] for t in times]
        self.assertEqual(actual, ["monitor", "needs_corroboration", "review_recommended", "needs_corroboration"])


if __name__ == "__main__":
    unittest.main()
