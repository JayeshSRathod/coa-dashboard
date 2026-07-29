import unittest

from dashboard.structure_trails import build_level_trail, build_wall_trails


class StructureTrailTests(unittest.TestCase):
    def test_builds_chronological_level_points_and_markers(self):
        events = [
            {"event_id": "2", "occurred_at": "2026-07-28T09:16:00+05:30", "event_type": "RESISTANCE_BREAK", "payload": {"spot": 24020}},
            {"event_id": "1", "occurred_at": "2026-07-28T09:15:00+05:30", "event_type": "STRUCTURE_SNAPSHOT", "scenario_track": "COA1_PLUS_COA2", "payload": {"spot": 23990, "levels": {"SUPPORT": 23950, "RESISTANCE": 24000, "EOS": 23940, "EOR": 24010}}},
        ]
        points, markers = build_level_trail(events)
        self.assertEqual(points[0]["support"], 23950.0)
        self.assertEqual(points[0]["resistance"], 24000.0)
        self.assertEqual(markers[0]["event_type"], "RESISTANCE_BREAK")

    def test_groups_wall_strike_history_by_side_metric_and_rank(self):
        walls = [
            {"wall_id": "W2", "captured_at": "2026-07-28T09:16:00+05:30", "side": "CE", "metric": "VOLUME", "rank": 1, "strike": 24050, "metric_value": 200, "payload": {"contract": "NIFTY 24050 CE"}},
            {"wall_id": "W1", "captured_at": "2026-07-28T09:15:00+05:30", "side": "CE", "metric": "VOLUME", "rank": 1, "strike": 24000, "metric_value": 100, "payload": {"contract": "NIFTY 24000 CE"}},
        ]
        trails = build_wall_trails(walls)
        self.assertEqual(len(trails), 1)
        self.assertEqual([point["strike"] for point in trails[0]["points"]], [24000.0, 24050.0])
