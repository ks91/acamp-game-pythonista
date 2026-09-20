import json
from typing import Any, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class ApiClient:
    def __init__(
        self, *, base_url: str, token: str, timeout_s: float = 15, game_team_id: Optional[str] = None
    ):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout_s = timeout_s
        self.game_team_id = game_team_id

    def _url(self, path: str) -> str:
        if self.game_team_id is None:
            return self.base_url + path
        return self.base_url + path + "?" + urlencode({"game_team": self.game_team_id})

    def post_location_sample(self, sample: dict[str, Any]) -> dict[str, Any]:
        request = Request(
            self._url("/location-samples"),
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

    def get_game_definition(self) -> dict[str, Any]:
        request = Request(
            self._url("/game/definition"),
            headers={
                "Accept": "application/json",
                "Authorization": "Bearer " + self.token,
            },
            method="GET",
        )
        with urlopen(request, timeout=self.timeout_s) as response:
            return json.loads(response.read().decode("utf-8"))

    def claim_place(
        self, *, action_id: str, game_session_id: str, place_id: str, device_id: str
    ) -> dict[str, Any]:
        request = Request(
            self._url("/actions"),
            data=json.dumps(
                {
                    "action_id": action_id,
                    "game_session_id": game_session_id,
                    "type": "claim_place",
                    "place_id": place_id,
                    "device_id": device_id,
                }
            ).encode("utf-8"),
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
            self._url("/team/state"),
            headers={
                "Accept": "application/json",
                "Authorization": "Bearer " + self.token,
            },
            method="GET",
        )
        with urlopen(request, timeout=self.timeout_s) as response:
            return json.loads(response.read().decode("utf-8"))
