import ast
from pathlib import Path
import unittest


class GameAppSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = Path(__file__).parents[1].joinpath("team_apps", "blue", "app.py").read_text()
        cls.tree = ast.parse(source)

    def test_home_screen_is_quest_selection_only(self):
        methods = {
            node.name: node
            for node in ast.walk(self.tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        home = methods["render_quest_selection"]
        attributes = {
            node.attr
            for node in ast.walk(home)
            if isinstance(node, ast.Attribute)
        }
        self.assertNotIn("update_location", attributes)
        self.assertNotIn("claim_place", attributes)

    def test_capture_screen_offers_photo_selection_and_camera(self):
        methods = {
            node.name: node
            for node in ast.walk(self.tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        capture = methods["render_capture_screen"]
        string_values = {
            node.value
            for node in ast.walk(capture)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }
        attributes = {
            node.attr
            for node in ast.walk(capture)
            if isinstance(node, ast.Attribute)
        }
        self.assertIn("写真を選択", string_values)
        self.assertIn("写真を撮影", string_values)
        self.assertIn("select_photo", attributes)
        self.assertIn("take_photo", attributes)

    def test_capture_status_does_not_claim_unimplemented_upload_is_ready(self):
        string_values = {
            node.value
            for node in ast.walk(self.tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }
        self.assertFalse(
            any("送信する準備ができました" in value for value in string_values)
        )


if __name__ == "__main__":
    unittest.main()