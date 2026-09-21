from datetime import datetime, timedelta, timezone
import unittest
from aquasentinel.store import Store
from aquasentinel.weather import validate_capture, watch


def capture(at='2026-09-21T00:00:00Z', rain=2, kind='forecast'):
    base = datetime(2026, 9, 21, tzinfo=timezone.utc)
    return validate_capture(dict(stream_id='test', source_type='synthetic', kind=kind,
        fetched_at=at, issued_at=None, raw={'utc_offset_seconds': 0, 'hourly_units': {'rain':'mm'},
        'hourly': {'time':[(base+timedelta(hours=i)).isoformat() for i in range(1,49)], 'rain':[rain]*48}}))


class WeatherTests(unittest.TestCase):
    def setUp(self):
        self.store=Store(':memory:')
        self.addCleanup(self.store.close)

    def test_versions_and_late_import_are_time_scoped(self):
        wet=capture(); dry=capture('2026-09-21T02:00:00Z',0)
        self.store.import_weather(wet,wet['fetched_at'])
        self.store.import_weather(dry,'2026-09-21T03:00:00Z')
        self.assertIsNone(self.store.snapshot('test','2026-09-20T23:59:00Z')['forecast'])
        self.assertEqual(self.store.snapshot('test','2026-09-21T02:30:00Z')['forecast']['capture_id'],wet['capture_id'])
        self.assertIsNone(self.store.snapshot('test','2026-09-21T03:00:00Z')['watch'])
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM weather_captures').fetchone()[0],2)

    def test_dedup_retract_and_replay(self):
        c=capture();self.store.import_weather(c,c['fetched_at'])
        a=self.store.queue_alert('test',c['fetched_at'])
        b=self.store.queue_alert('test',c['fetched_at'])
        self.assertEqual(len(b['alerts']),1)
        self.assertEqual(a['alerts'][0]['status'],'active')
        dry=capture('2026-09-21T01:00:00Z',0);self.store.import_weather(dry,dry['fetched_at'])
        self.assertEqual(self.store.snapshot('test',dry['fetched_at'])['alerts'][0]['status'],'retracted')
        self.assertEqual(self.store.snapshot('test',c['fetched_at'])['alerts'][0]['status'],'active')

    def test_reanalysis_never_drives_watch(self):
        c=capture(kind='reanalysis');self.store.import_weather(c,c['fetched_at'])
        self.assertIsNone(watch(c,c['fetched_at']))
        self.assertIsNone(self.store.snapshot('test',c['fetched_at'])['watch'])

    def test_missing_or_expired_data_abstains(self):
        c=capture(rain=None)
        self.assertIsNone(watch(c,c['fetched_at']))
        self.assertIsNone(watch(capture(),'2026-09-21T13:00:00Z'))

    def test_mutation_does_not_overwrite(self):
        c=capture();self.assertTrue(self.store.import_weather(c,c['fetched_at']))
        self.assertFalse(self.store.import_weather(c,c['fetched_at']))
        with self.assertRaises(ValueError):self.store.import_weather(c,'2026-09-20T00:00:00Z')
