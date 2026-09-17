import json
from typing import Any
from urllib.request import Request, urlopen


class ApiClient:
    def __init__(self, *, base_url: str, token: str, timeout_s: float = 15):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout_s = timeout_s

    def post_location_sample(self, sample: dict[str, Any]) -> dict[str, Any]:
        request = Request(
            self.base_url + "/location-samples",
            data=json.dumps(sample).encode("utf-8"),
            headers={
                "Accept": "application/json",
                "Authorization": "Bearer " + self.token,
                "Content-Type": "application/json; charset=utf-8",
            },
            method="POST",
        )
        with urlopen(request, timeout=self.timeout_s) as response:
            return json.loads(response.read().decode("utf-8"))

    def get_team_state(self) -> dict[str, Any]:
        request = Request(
            self.base_url + "/team/state",
            headers={
                "Accept": "application/json",
                "Authorization": "Bearer " + self.token,
            },
            method="GET",
        )
        with urlopen(request, timeout=self.timeout_s) as response:
            return json.loads(response.read().decode("utf-8"))
