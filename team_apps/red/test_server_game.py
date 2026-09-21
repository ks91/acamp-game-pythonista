import unittest

from team_apps.red import server_game


class FakeConfig:
    API_BASE_URL = "https://example.test/v1"
    GAME_TOKEN = "red-token"
    SELECTED_GAME_TEAM_ID = "red"
    SELECTED_GAME_MODE = "tokyo"


class RecordingClient:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class RedServerGameTests(unittest.TestCase):
    def test_client_uses_gallery_selected_team_and_mode(self):
        client = server_game.make_api_client(FakeConfig, client_class=RecordingClient)

        self.assertEqual(
            {
                "base_url": "https://example.test/v1",
                "token": "red-token",
                "game_team_id": "red",
                "game_mode": "tokyo",
            },
            client.kwargs,
        )

    def test_server_places_and_claims_are_authoritative(self):
        definition = {
            "places": [
                {"id": "palace", "name": "皇居", "latitude": 35.685175, "longitude": 139.7528},
                {"id": "invalid", "name": "No coordinates"},
            ]
        }
        state = {"claimed_places": ["palace"], "game_session_id": "session-1"}

        scenario = server_game.scenario_from_server(definition, state)

        self.assertEqual(["palace"], [place["id"] for place in scenario["places"]])
        self.assertEqual({"palace"}, scenario["claimed_place_ids"])
        self.assertEqual("session-1", scenario["game_session_id"])
        self.assertEqual({"ゼウス": "palace"}, scenario["boss_place_ids"])

    def test_redacted_zero_coordinate_place_is_not_playable(self):
        definition = {
            "places": [
                {"id": "redacted", "name": "Hidden", "latitude": 0, "longitude": 0},
            ]
        }

        scenario = server_game.scenario_from_server(definition, {})

        self.assertEqual([], scenario["places"])
        self.assertFalse(server_game.has_map_coordinates(definition["places"][0]))

    def test_missing_credentials_do_not_create_a_client(self):
        class MissingConfig:
            API_BASE_URL = ""
            GAME_TOKEN = ""

        self.assertIsNone(server_game.make_api_client(MissingConfig, client_class=RecordingClient))


if __name__ == "__main__":
    unittest.main()
