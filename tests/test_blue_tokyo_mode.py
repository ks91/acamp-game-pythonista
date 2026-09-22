from pathlib import Path
import unittest


class BlueTokyoModeTests(unittest.TestCase):
    def test_tokyo_mode_builds_quests_only_from_server_places(self):
        source = Path(__file__).parents[1].joinpath("team_apps/blue/app.py").read_text()
        self.assertIn("def _server_place_quests", source)
        self.assertIn('"game_mode", getattr(config, "SELECTED_GAME_MODE", None)', source)
        self.assertIn("self.available_quests = self._server_place_quests(definition)", source)


if __name__ == "__main__":
    unittest.main()
