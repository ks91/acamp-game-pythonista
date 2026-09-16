import json
import os
from typing import Any


class EventQueue:
    """A small durable FIFO queue for events created while offline."""

    def __init__(self, path: str):
        self.path = path

    def pending(self) -> list[dict[str, Any]]:
        if not os.path.exists(self.path):
            return []
        with open(self.path, "r", encoding="utf-8") as source:
            return json.load(source)

    def enqueue(self, event: dict[str, Any]) -> None:
        events = self.pending()
        events.append(event)
        self._write(events)

    def remove_first(self) -> None:
        events = self.pending()
        if events:
            self._write(events[1:])

    def _write(self, events: list[dict[str, Any]]) -> None:
        directory = os.path.dirname(self.path) or "."
        os.makedirs(directory, exist_ok=True)
        temporary_path = self.path + ".tmp"
        with open(temporary_path, "w", encoding="utf-8") as destination:
            json.dump(events, destination, ensure_ascii=False, separators=(",", ":"))
        os.replace(temporary_path, self.path)
