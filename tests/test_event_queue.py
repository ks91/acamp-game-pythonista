import os
import tempfile
import unittest

from toolkit.event_queue import EventQueue


class EventQueueTests(unittest.TestCase):
    def test_enqueue_persists_event_for_later_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "pending-events.json")
            queue = EventQueue(path)

            queue.enqueue({"type": "location_sample", "sample_id": "sample-1"})

            restored_queue = EventQueue(path)
            self.assertEqual(
                [{"type": "location_sample", "sample_id": "sample-1"}],
                restored_queue.pending(),
            )

    def test_remove_delivered_event_leaves_later_events_queued(self):
        with tempfile.TemporaryDirectory() as directory:
            queue = EventQueue(os.path.join(directory, "pending-events.json"))
            queue.enqueue({"type": "location_sample", "sample_id": "sample-1"})
            queue.enqueue({"type": "action", "action_id": "action-1"})

            queue.remove_first()

            self.assertEqual(
                [{"type": "action", "action_id": "action-1"}],
                queue.pending(),
            )


if __name__ == "__main__":
    unittest.main()
