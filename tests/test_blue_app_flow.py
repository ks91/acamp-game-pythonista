import ast
from pathlib import Path
import unittest


class BlueAppFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = Path(__file__).parents[1].joinpath("team_apps/blue/app.py").read_text()
        cls.source = source
        cls.methods = {
            node.name: node
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.FunctionDef)
        }

    def test_app_starts_at_title_then_location_then_quest(self):
        self.assertIn("render_title_screen", self.methods)
        self.assertIn("start_game", self.methods)
        self.assertIn("select_location", self.methods)
        self.assertIn("blue位置ゲー開発（仮）", self.source)
        self.assertIn("場所を選択してください", self.source)
        self.assertIn("オリンピックセンター探索イベント（仮）", self.source)


if __name__ == "__main__":
    unittest.main()
