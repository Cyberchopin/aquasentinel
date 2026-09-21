import random
import unittest
from datetime import datetime,timedelta,timezone
from aquasentinel.store import Store
from aquasentinel.audit import verify


class AuditTests(unittest.TestCase):
    def test_chain_detects_mutated_record(self):
        s=Store(':memory:');self.addCleanup(s.close)
        s.ingest(dict(source_id='x',external_id='1',stream_id='x',observed_at='2026-09-21T00:00:00Z',lat=0,lon=0,signal='odor',synthetic=True),'2026-09-21T01:00:00Z')
        self.assertEqual(verify(s.db)['verified_events'],1)
        s.db.execute("UPDATE observations SET payload='{}'")
        with self.assertRaisesRegex(ValueError,'changed'):verify(s.db)

    def test_random_late_arrivals_preserve_past_hash(self):
        rng=random.Random(921)
        s=Store(':memory:');self.addCleanup(s.close)
        at=datetime(2026,9,21,tzinfo=timezone.utc)
        before=s.snapshot('x',at.isoformat())['decision_hash']
        for i in range(100):
            s.ingest(dict(source_id=str(i),external_id=str(i),stream_id='x',
                observed_at=(at-timedelta(minutes=rng.randrange(1440))).isoformat(),lat=0,lon=0,
                signal=rng.choice(['normal','odor','turbidity']),synthetic=True),
                (at+timedelta(seconds=rng.randrange(1,10000))).isoformat())
            self.assertEqual(before,s.snapshot('x',at.isoformat())['decision_hash'])
        self.assertEqual(verify(s.db)['verified_events'],100)
