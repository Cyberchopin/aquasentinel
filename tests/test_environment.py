import json
from pathlib import Path
import shutil
import tempfile
import unittest
from aquasentinel.store import Store
from aquasentinel.usgs import FIXTURE, load_bundle


class EnvironmentTests(unittest.TestCase):
    def test_raw_fixture_units_and_identity(self):
        bundle = load_bundle()
        self.assertEqual(len(bundle['records']), 8)
        self.assertEqual(bundle['unit'], 'ft^3/s')
        self.assertEqual(bundle['records'][4]['value'], 164)
        self.assertIsNone(bundle['original_publication_time'])
        self.assertTrue(all(r['record_type'] == 'sensor' and r['source_type'] == 'real' for r in bundle['records']))

    def test_late_archive_does_not_leak_or_vote_as_citizen(self):
        store = Store(':memory:')
        self.addCleanup(store.close)
        t = '2026-09-21T06:00:00Z'
        self.assertTrue(store.import_environment(FIXTURE, t))
        self.assertFalse(store.import_environment(FIXTURE, '2026-09-22T06:00:00Z'))
        before = store.snapshot('USGS-11098000', '2026-09-21T05:59:59Z')
        after = store.snapshot('USGS-11098000', t)
        self.assertNotIn('environmental_context', before)
        self.assertEqual(after['state'], 'monitor')
        self.assertEqual(after['distinct_sources'], 0)
        self.assertEqual(after['evidence'], [])
        self.assertNotEqual(before['decision_hash'], after['decision_hash'])

    def test_modified_raw_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / 'capture'
            shutil.copytree(FIXTURE, folder)
            with (folder / 'daily.json').open('ab') as out:
                out.write(b' ')
            with self.assertRaisesRegex(ValueError, 'Checksum'):
                load_bundle(folder)

    def test_import_cannot_predate_capture(self):
        store = Store(':memory:')
        self.addCleanup(store.close)
        with self.assertRaises(ValueError):
            store.import_environment(FIXTURE, '2024-02-01T00:00:00Z')
