import unittest
from pathlib import Path


SOURCE = Path(__file__).with_name("app.py").read_text(encoding="utf-8")


class RedMapSafetyTests(unittest.TestCase):
    def test_map_never_initializes_at_zero_coordinate(self):
        self.assertNotIn("setView([0,0]", SOURCE)
        self.assertNotIn("setView([0.0,0.0]", SOURCE)
        self.assertIn("位置情報を取得中…", SOURCE)

    def test_no_distance_calculation_before_server_scenario(self):
        start = SOURCE.index("def location_tick")
        end = SOURCE.index("def update_current_location", start)
        tick = SOURCE[start:end]
        self.assertIn("if not self.server_scenario_loaded", tick)
        self.assertLess(
            tick.index("if not self.server_scenario_loaded"),
            tick.index("distances = ["),
        )

    def test_root_import_is_available_from_pythonista_entrypoint(self):
        self.assertIn("_REPOSITORY_ROOT", SOURCE)
        self.assertIn("sys.path.insert(0, _REPOSITORY_ROOT)", SOURCE)


if __name__ == "__main__":
    unittest.main()
