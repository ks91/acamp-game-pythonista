import ast
from pathlib import Path
import unittest


class GameAppSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = Path(__file__).parents[1].joinpath("game_app.py").read_text()
        cls.tree = ast.parse(source)

    def test_home_screen_keeps_location_update_and_place_claim_controls(self):
        methods = {
            node.name: node
            for node in ast.walk(self.tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        home = methods["render_location_selection"]
        attributes = {
            node.attr
            for node in ast.walk(home)
            if isinstance(node, ast.Attribute)
        }
        self.assertIn("update_location", attributes)
        self.assertIn("claim_place", attributes)


if __name__ == "__main__":
    unittest.main()