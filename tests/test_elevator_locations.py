import unittest

from team_apps.blue.elevator_locations import classify_location


class ElevatorLocationTests(unittest.TestCase):
    def test_marks_nearby_elevator_as_same_position_group(self):
        result = classify_location(
            [{"latitude": 35.0, "longitude": 139.0}],
            {"latitude": 35.00003, "longitude": 139.0},
            threshold_m=10,
        )
        self.assertEqual("same_position_group", result["kind"])
        self.assertEqual(0, result["matching_index"])

    def test_marks_distant_elevator_as_new_position_group(self):
        result = classify_location(
            [{"latitude": 35.0, "longitude": 139.0}],
            {"latitude": 35.0002, "longitude": 139.0},
            threshold_m=10,
        )
        self.assertEqual("new_position_group", result["kind"])
        self.assertIsNone(result["matching_index"])


if __name__ == "__main__":
    unittest.main()
