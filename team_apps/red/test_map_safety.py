import unittest
from pathlib import Path


SOURCE = Path(__file__).with_name("app.py").read_text(encoding="utf-8")


class RedMapSafetyTests(unittest.TestCase):
    def test_gallery_launch_does_not_load_splash_artwork(self):
        init = SOURCE[SOURCE.index("def __init__"):SOURCE.index("def refresh_server_scenario")]
        self.assertNotIn("self.show_splash(", init)

    def test_callback_targets_accept_the_sender_argument(self):
        import ast
        tree = ast.parse(SOURCE)
        methods = {node.name: node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
        self.assertGreaterEqual(len(methods["show_battle_selection"].args.args), 2)

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

    def test_monster_button_uses_native_map_without_webview(self):
        start = SOURCE.index("def show_interactive_map")
        end = SOURCE.index("def close_map", start)
        body = SOURCE[start:end]
        self.assertIn("MonsterLocationMap", body)
        self.assertNotIn("ui.WebView", body)
        self.assertIn(".set_data(", body)
        self.assertNotIn(".load_html(", body)
        self.assertIn('"★" * monster.get("stars", 1)', SOURCE)
        self.assertIn('"name": monster["name"]', SOURCE)

    def test_screen_change_resets_scroll_to_show_back_button(self):
        start = SOURCE.index("def clear_content")
        end = SOURCE.index("def set_status", start)
        body = SOURCE[start:end]
        self.assertIn("self.content.content_offset = (0, 0)", body)

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
