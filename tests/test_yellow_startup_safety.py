import types
import unittest
from unittest.mock import Mock, patch

from test_red_battle_safety import Button, View, load_app


class YellowStartupSafetyTests(unittest.TestCase):
    def setUp(self):
        self.delays = []
        ui = types.SimpleNamespace(
            View=View, ScrollView=View, Label=View, Button=Button,
            ALIGN_CENTER=1, ALIGN_LEFT=0, get_screen_size=lambda: (768, 1024),
            delay=lambda callback, seconds: self.delays.append(callback),
        )
        self.app = load_app("yellow", ui)
        self.app.config = types.SimpleNamespace(
            API_BASE_URL="https://example.invalid/v1", GAME_TOKEN="test-token",
            SELECTED_GAME_TEAM_ID="yellow", SELECTED_GAME_MODE="tokyo",
        )

    def make_game(self, api):
        workers = []
        def thread(target, daemon):
            return types.SimpleNamespace(start=lambda: workers.append(target))
        with patch.object(self.app, "ApiClient", return_value=api) as client, \
                patch.object(self.app.threading, "Thread", side_effect=thread):
            game = self.app.YellowEgyptGame()
        self.assertEqual("yellow", client.call_args.kwargs["game_team_id"])
        self.assertEqual("tokyo", client.call_args.kwargs["game_mode"])
        for worker in workers:
            worker()
        for callback in self.delays:
            callback()
        self.delays.clear()
        return game

    def test_opening_game_reads_existing_progress_without_resetting(self):
        api = Mock()
        api.get_game_definition.return_value = {"places": []}
        api.get_team_state.return_value = {"score": 30, "claimed_places": ["pyramid"]}
        game = self.make_game(api)
        api.restart_test_session.assert_not_called()
        self.assertEqual(30, game.state["score"])
        self.assertIn("pyramid", game.state["claimed_places"])

    def test_connection_failure_keeps_a_retry_control(self):
        api = Mock()
        api.get_game_definition.side_effect = OSError("offline")
        game = self.make_game(api)
        api.restart_test_session.assert_not_called()
        self.assertTrue(any(getattr(view, "title", "").startswith("位置情報を更新")
                            for view in game.content.subviews))
        self.assertTrue(any("offline" in getattr(view, "text", "")
                            for view in game.content.subviews))

    def test_explicit_restart_uses_the_selected_api_client(self):
        game = self.app.YellowEgyptGame.__new__(self.app.YellowEgyptGame)
        game.api = Mock()
        game.api.restart_test_session.return_value = {"restarted": True}
        game._handle_restart_result = Mock()
        game._restart_test_session()
        game.api.restart_test_session.assert_called_once_with()
        self.delays.pop()()
        game._handle_restart_result.assert_called_once_with({"restarted": True})


if __name__ == "__main__":
    unittest.main()
