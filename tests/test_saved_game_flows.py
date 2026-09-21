"""Exercise save hooks in the real game methods with temporary local files."""
import runpy
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from test_red_battle_safety import Button, View, load_app
from toolkit.game_progress import GameProgress


class SavedGameFlowTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.delays = []
        self.ui = types.SimpleNamespace(
            View=View, ScrollView=View, Label=View, Button=Button,
            ALIGN_CENTER=1, ALIGN_LEFT=0, get_screen_size=lambda: (768, 1024),
            delay=lambda callback, seconds: self.delays.append(callback),
        )

    def app(self, team):
        app = load_app(team, self.ui)
        app.config = types.SimpleNamespace(
            TEAM_ID="pink", DEVICE_ID="pink-ipad", GAME_SESSION_ID="configured-session",
            SELECTED_GAME_MODE="tokyo", SELECTED_GAME_TEAM_ID=team,
            API_BASE_URL="https://example.invalid/v1", GAME_TOKEN="set-at-game-start",
        )
        app.make_progress_store = lambda view, config, game: GameProgress(
            view, config, game, self.directory.name)
        return app

    def red(self):
        return self.app("red")

    def purple(self):
        app = self.app("purple")
        cls = app.PurpleMockGame
        for name in ("_build_ui", "_load_server_places", "_refresh", "_show_feedback",
                     "_show_chest_found", "_show_good_bacteria_arrival"):
            setattr(cls, name, Mock())
        return app

    def pink(self):
        app = self.app("pink")
        app.ApiClient = Mock()
        app.ApiClient.return_value.get_game_definition.return_value = {"places": []}
        app.ApiClient.return_value.get_team_state.return_value = {"game_session_id": "pink-tokyo"}
        app.GameView.start_auto_coin_collection = Mock()
        return app

    def test_red_victory_restores_growth_inventory_and_integer_star_keys(self):
        app = self.red()
        game = app.RedPrototype()
        game.active_monster = app.MONSTERS[0].copy()
        game.start_battle()
        game.enemy_hp = 1
        game.attack_with_fist(None)
        restored = app.RedPrototype()
        self.assertEqual("battle_selection", restored.current_screen)
        self.assertIsNone(restored.active_monster)
        self.assertEqual(110, restored.player_max_hp)
        self.assertEqual(["木の棒"], restored.inventory)
        self.assertEqual(5, restored.weapon_uses["木の棒"])
        self.assertEqual({1: 1, 2: 0, 3: 0}, restored.defeated_by_stars)

    def test_red_consumed_weapon_and_damage_survive_without_resuming_battle(self):
        app = self.red()
        game = app.RedPrototype()
        game.inventory = ["木の棒"]
        game.weapon_uses = {"木の棒": 1}
        game.active_monster = app.MONSTERS[5].copy()
        game.start_battle()
        game.attack_with_item(types.SimpleNamespace(item_name="木の棒"))
        restored = app.RedPrototype()
        self.assertEqual([], restored.inventory)
        self.assertEqual({}, restored.weapon_uses)
        self.assertEqual(game.player_hp, restored.player_hp)
        self.assertIsNone(restored.active_monster)
        self.assertEqual(0, restored.enemy_hp)

    def test_red_boss_reward_is_not_repeated_on_restore(self):
        app = self.red()
        game = app.RedPrototype()
        game.active_monster = app.MINIBOSSES[1].copy()
        game.start_battle()
        game.enemy_hp = 1
        game.attack_with_fist(None)
        restored = app.RedPrototype()
        self.assertEqual({app.MINIBOSSES[1]["name"]}, restored.defeated_bosses)
        self.assertEqual(["三種の神器・鏡"], restored.inventory)

    def test_red_server_session_change_cannot_import_another_sessions_growth(self):
        app = self.red()
        game = app.RedPrototype()
        scenario = {
            "game_session_id": "actual-session", "claimed_place_ids": set(), "boss_place_ids": {},
            "places": [{"id": "tokyo", "name": "Tokyo", "latitude": 35.0, "longitude": 139.0}],
        }
        game._apply_server_scenario(scenario, None)
        game.player_max_hp = 150
        game._save_progress()
        restored = app.RedPrototype()
        restored._apply_server_scenario(scenario, None)
        self.assertEqual(150, restored.player_max_hp)
        restored._apply_server_scenario(dict(scenario, game_session_id="next-session"), None)
        self.assertEqual(100, restored.player_max_hp)

    def test_red_diagnostic_neither_reads_nor_writes_real_progress(self):
        app = self.red()
        app.make_progress_store = Mock(side_effect=AssertionError("diagnostic accessed saves"))
        path = Path(__file__).resolve().parents[1] / "diagnostics" / "red_battle_check.py"
        with patch.dict(sys.modules, {"ui": self.ui, "team_apps.red.app": app}):
            namespace = runpy.run_path(str(path))
        diagnostic = namespace["RedBattleCheck"]()
        diagnostic.start_check(types.SimpleNamespace(test_case="fist"))
        diagnostic.enemy_hp = 1
        diagnostic.attack_with_fist(None)
        diagnostic.will_close()
        app.make_progress_store.assert_not_called()
        self.assertEqual([], list(Path(self.directory.name).iterdir()))

    def test_purple_quiz_reward_and_chest_survive_without_resuming_timer(self):
        app = self.purple()
        game = app.PurpleMockGame()
        game.arrived[0] = True
        game._start_quiz(0, 0)
        game._finish_quiz(app.QUESTIONS[0]["answer"])
        restored = app.PurpleMockGame()
        self.assertEqual(40, restored.score)
        self.assertEqual([True, False], restored.solved)
        self.assertEqual(app.CHEST_REWARDS[0], restored.chest_items[0])
        self.assertFalse(restored.quiz_active)
        self.assertIsNone(restored.quiz_overlay)
        restored._solve(0)
        self.assertEqual(40, restored.score)

    def test_purple_boss_defeat_restores_result_without_transition_timer(self):
        app = self.purple()
        game = app.PurpleMockGame()
        game.score = 100
        game._attack(None)
        restored = app.PurpleMockGame()
        self.assertEqual((50, 50), (restored.score, restored.boss_hp))
        restored._attack(None)
        won = app.PurpleMockGame()
        self.assertEqual((0, 0), (won.score, won.boss_hp))
        self.assertFalse(won.boss_defeat_transition)

    def test_purple_manual_reset_replaces_current_session_and_backup(self):
        app = self.purple()
        game = app.PurpleMockGame()
        game.score = 200
        game.arrived = [True, True]
        game._save_progress()
        game._reset()
        Path(game._progress.path).write_text("broken")
        restored = app.PurpleMockGame()
        self.assertEqual(10, restored.score)
        self.assertEqual([False, False], restored.arrived)

    def test_purple_game_over_is_saved_before_delayed_restart(self):
        app = self.purple()
        game = app.PurpleMockGame()
        game.arrived[0] = True
        game.lives = 1
        game._start_quiz(0, 0)
        game._finish_quiz(None, timed_out=True)
        self.assertEqual(0, game.lives)
        restored = app.PurpleMockGame()
        self.assertEqual(3, restored.lives)
        self.assertEqual([False, False], restored.arrived)

    def test_pink_distance_coins_save_but_restart_does_not_count_offline_travel(self):
        app = self.pink()
        game = app.GameView()
        game._collect_distance_coins({"latitude": 35.0, "longitude": 139.0})
        game._collect_distance_coins({"latitude": 35.001, "longitude": 139.0})
        self.assertGreater(game.coins, 0)
        restored = app.GameView()
        self.assertEqual(game.coins, restored.coins)
        self.assertEqual(game.distance_remainder_m, restored.distance_remainder_m)
        self.assertIsNone(restored.last_position)
        self.assertEqual(0, restored._collect_distance_coins({"latitude": 36.0, "longitude": 139.0}))
        self.assertEqual(game.coins, restored.coins)

    def test_pink_gacha_is_saved_even_when_following_refresh_fails(self):
        app = self.pink()
        game = app.GameView()
        game.coins = 100
        app.ApiClient.return_value.get_game_definition.side_effect = OSError("offline")
        game.play_gacha(None)
        restored = app.GameView()
        self.assertEqual(50, restored.coins)
        self.assertEqual(1, sum(restored.tickets.values()))


if __name__ == "__main__":
    unittest.main()
