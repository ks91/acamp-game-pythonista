import ast
from pathlib import Path
import unittest


class PurpleTokyoManArtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).parents[1]
        cls.source = cls.root.joinpath("team_apps", "purple", "app.py").read_text()
        cls.tree = ast.parse(cls.source)
        cls.methods = {node.name: node for node in ast.walk(cls.tree) if isinstance(node, ast.FunctionDef)}

    def test_health_state_selects_submitted_tokyoman_art(self):
        for name in ("tokyoman_full.jpeg", "tokyoman_half.jpeg", "tokyoman_defeated.jpeg"):
            self.assertTrue(self.root.joinpath("team_apps", "purple", "assets", name).is_file())
        self.assertIn("_update_tokyoman_art", self.methods)
        text = ast.get_source_segment(self.source, self.methods["_update_tokyoman_art"])
        self.assertIn("tokyoman_full.jpeg", text)
        self.assertIn("tokyoman_half.jpeg", text)
        self.assertIn("tokyoman_defeated.jpeg", text)


if __name__ == "__main__":
    unittest.main()
