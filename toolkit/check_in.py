from typing import Any

from toolkit.event_queue import EventQueue


class CheckInService:
    def __init__(self, api_client: Any, queue: EventQueue):
        self.api_client = api_client
        self.queue = queue

    def submit(self, sample: dict[str, Any]) -> dict[str, Any]:
        if not self._flush_pending():
            self.queue.enqueue({"type": "location_sample", "payload": sample})
            return {"queued": True}

        try:
            return self.api_client.post_location_sample(sample)
        except OSError:
            self.queue.enqueue({"type": "location_sample", "payload": sample})
            return {"queued": True}

    def _flush_pending(self) -> bool:
        while self.queue.pending():
            event = self.queue.pending()[0]
            try:
                if event["type"] != "location_sample":
                    return False
                self.api_client.post_location_sample(event["payload"])
            except OSError:
                return False
            self.queue.remove_first()
        return True
