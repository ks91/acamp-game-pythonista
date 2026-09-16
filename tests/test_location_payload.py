import unittest

from toolkit.location_payload import make_location_sample


class LocationPayloadTests(unittest.TestCase):
    def test_make_location_sample_keeps_gps_coordinates_and_adds_team_metadata(self):
        result = make_location_sample(
            team_id="green",
            device_id="green-ipad",
            client_time="2026-09-20T10:00:00+09:00",
            sample_id="green-0001",
            location={"latitude": 35.3387, "longitude": 139.4888, "horizontal_accuracy": 18.5},
        )

        self.assertEqual(
            {
                "team_id": "green",
                "device_id": "green-ipad",
                "client_time": "2026-09-20T10:00:00+09:00",
                "sample_id": "green-0001",
                "latitude": 35.3387,
                "longitude": 139.4888,
                "accuracy_m": 18.5,
            },
            result,
        )


if __name__ == "__main__":
    unittest.main()
