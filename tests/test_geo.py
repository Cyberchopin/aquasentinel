import unittest
from aquasentinel.geo import segment_distance,match


class GeoTests(unittest.TestCase):
    def test_interior_segment_and_endpoint(self):
        self.assertLess(segment_distance((.5,0),(0,0),(1,0)),.001)
        self.assertGreater(segment_distance((2,0),(0,0),(1,0)),100000)
        self.assertAlmostEqual(segment_distance((0,.001),(0,0),(0,0)),111.2,delta=.2)

    def test_separate_streams_and_far_abstention(self):
        self.assertEqual(match(-117.82,33.68)['stream_id'],'demo-creek-a')
        self.assertEqual(match(-117.795,33.68)['stream_id'],'demo-creek-b')
        self.assertIsNone(match(0,0)['stream_id'])
