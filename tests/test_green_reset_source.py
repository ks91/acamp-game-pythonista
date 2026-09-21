import ast
from pathlib import Path
import unittest


class GreenResetSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = Path(__file__).parents[1].joinpath("team_apps", "green", "app.py").read_text()
        cls.tree = ast.parse(source)
        cls.methods = {
            node.name: node
            for node in ast.walk(cls.tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

    def test_participant_can_explicitly_confirm_a_test_restart(self):
        self.assertIn("restart_test_session", self.methods)
        method = self.methods["restart_test_session"]
        strings = {
            node.value
            for node in ast.walk(method)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }
        self.assertIn("もう一度押すと最初から", strings)
        calls = {
            node.func.attr
            for node in ast.walk(method)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        self.assertIn("_restart_test_session_worker", {
            node.attr
            for node in ast.walk(method)
            if isinstance(node, ast.Attribute)
        })
        worker = self.methods["_restart_test_session_worker"]
        worker_calls = {
            node.func.attr
            for node in ast.walk(worker)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        self.assertIn("restart_test_session", worker_calls)


if __name__ == "__main__":
    unittest.main()
