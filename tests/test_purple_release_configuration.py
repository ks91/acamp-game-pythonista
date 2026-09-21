import ast
from pathlib import Path
import unittest


class PurpleReleaseConfigurationTests(unittest.TestCase):
    def test_infinite_points_is_disabled_in_the_published_game(self):
        tree = ast.parse((Path(__file__).parents[1] / "team_apps" / "purple" / "app.py").read_text())
        values = {
            node.targets[0].id: ast.literal_eval(node.value)
            for node in tree.body
            if isinstance(node, ast.Assign)
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "TEST_INFINITE_POINTS"
        }
        self.assertFalse(values["TEST_INFINITE_POINTS"])


if __name__ == "__main__":
    unittest.main()
