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

    def test_map_open_does_not_automatically_start_continuous_gps(self):
        start = SOURCE.index("def show_interactive_map")
        end = SOURCE.index("def close_map", start)
        body = SOURCE[start:end]
        self.assertNotIn("self.start_location_tracking()", body)
        self.assertIn("現在地を取得を押すとGPSを更新します", body)

    def test_monster_button_uses_native_panel_not_webview(self):
        start = SOURCE.index("def show_interactive_map")
        end = SOURCE.index("def close_map", start)
        body = SOURCE[start:end]
        self.assertNotIn("ui.WebView", body)
        self.assertNotIn("load_html", body)
        self.assertIn("refresh_native_map_panel", body)

    def test_how_to_play_has_a_visible_home_button(self):
        start = SOURCE.index("def show_how_to_play")
        end = SOURCE.index("def show_profile", start)
        body = SOURCE[start:end]
        self.assertIn('title="ホームにもどる", frame=(16, 10, 343, 40)', body)

    def test_root_import_is_available_from_pythonista_entrypoint(self):
        self.assertIn("_REPOSITORY_ROOT", SOURCE)
        self.assertIn("sys.path.insert(0, _REPOSITORY_ROOT)", SOURCE)


if __name__ == "__main__":
    unittest.main()
