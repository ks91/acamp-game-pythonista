import ast
from pathlib import Path
import unittest


APP_PATH = Path(__file__).parents[1] / "team_apps" / "purple" / "app.py"


class PurpleServerModeIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = APP_PATH.read_text()
        cls.tree = ast.parse(cls.source)

    def test_constructs_shared_api_client_with_gallery_selected_team_and_mode(self):
        calls = [
            node
            for node in ast.walk(self.tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "ApiClient"
        ]
        self.assertEqual(1, len(calls))
        keywords = {keyword.arg: ast.unparse(keyword.value) for keyword in calls[0].keywords}
        self.assertEqual("getattr(config, 'SELECTED_GAME_TEAM_ID', None)", keywords["game_team_id"])
        self.assertEqual("getattr(config, 'SELECTED_GAME_MODE', None)", keywords["game_mode"])

    def test_uses_server_definition_places_without_local_mode_or_location_overrides(self):
        assigned_names = {
            target.id
            for node in self.tree.body
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
        }
        self.assertFalse({"GAME_MODE", "FIXED_PLACES", "REFERENCE_LOCATION", "TEST_PLACE1_IS_CURRENT", "TEST_INFINITE_POINTS"} & assigned_names)
        self.assertNotIn("_set_place_here", self.source)
        self.assertIn("get_game_definition", self.source)
        self.assertIn('definition.get("places", [])', self.source)

    def test_keeps_the_published_chest_test_action(self):
        self.assertIn("テスト用：謎を解いた", self.source)


if __name__ == "__main__":
    unittest.main()
