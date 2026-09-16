import os
import tempfile
import unittest

from toolkit.check_in import CheckInService
from toolkit.event_queue import EventQueue


class FailingClient:
    def post_location_sample(self, sample):
        raise OSError("offline")


class RecordingClient:
    def __init__(self):
        self.samples = []

    def post_location_sample(self, sample):
        self.samples.append(sample)
        return {"accepted": True, "event_id": len(self.samples)}


class CheckInServiceTests(unittest.TestCase):
    def test_offline_sample_is_delivered_before_the_next_sample_after_reconnection(self):
        with tempfile.TemporaryDirectory() as directory:
            queue = EventQueue(os.path.join(directory, "pending-events.json"))
            sample_one = {"team_id": "green", "sample_id": "one"}
            sample_two = {"team_id": "green", "sample_id": "two"}

            offline = CheckInService(FailingClient(), queue)
            self.assertEqual({"queued": True}, offline.submit(sample_one))

            online_client = RecordingClient()
            online = CheckInService(online_client, queue)
            self.assertEqual(
                {"accepted": True, "event_id": 2}, online.submit(sample_two)
            )

            self.assertEqual([sample_one, sample_two], online_client.samples)
            self.assertEqual([], queue.pending())


if __name__ == "__main__":
    unittest.main()
