import unittest
from aquasentinel.store import Store
from aquasentinel.exports import brief, fhir_bundle
from aquasentinel.usgs import FIXTURE


class ExportTests(unittest.TestCase):
    def test_sensor_subject_and_date_semantics(self):
        store=Store(':memory:');self.addCleanup(store.close)
        store.import_environment(FIXTURE,'2026-09-21T06:00:00Z')
        s=store.snapshot('USGS-11098000','2026-09-21T06:00:00Z')
        b=fhir_bundle(s)
        self.assertEqual(b['entry'][0]['resource']['resourceType'],'Location')
        observations=[e['resource'] for e in b['entry'] if e['resource']['resourceType']=='Observation']
        self.assertEqual(len(observations),8)
        self.assertEqual(observations[0]['effectiveDateTime'],'2024-02-01')
        self.assertNotIn('issued',observations[0])
        self.assertIn('Public-health officer',brief(s))
        self.assertIn('not water-quality truth',brief(s))

    def test_brief_escapes_untrusted_stream(self):
        store=Store(':memory:');self.addCleanup(store.close)
        self.assertIn('&lt;script&gt;',brief(store.snapshot('<script>')))
