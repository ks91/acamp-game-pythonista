import ast
from pathlib import Path
import unittest


class PurpleReleaseConfigurationTests(unittest.TestCase):
    def test_published_game_has_no_infinite_points_override(self):
        tree = ast.parse((Path(__file__).parents[1] / "team_apps" / "purple" / "app.py").read_text())
        assigned_names = {
            target.id
            for node in tree.body
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
        }
        self.assertNotIn("TEST_INFINITE_POINTS", assigned_names)


if __name__ == "__main__":
    unittest.main()
