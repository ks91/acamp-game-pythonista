"""Exercise real battle callbacks with a small, queued Pythonista UI stand-in.

These tests check lifecycle and game state, not UIKit's native implementation.
The crash itself still needs an iPad regression check.
"""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch


class View:
    def __init__(self, **attributes):
        self.subviews = []
        self.tint_color = None
        self.frame = attributes.get("frame", (0, 0, 375, 667))
        self.width, self.height = self.frame[2:]
        self.bounds = (0, 0, self.width, self.height)
        self.__dict__.update(attributes)

    def add_subview(self, view):
        self.subviews.append(view)

    def remove_subview(self, view):
        self.subviews.remove(view)


class Button(View):
    pass


def load_app(team, ui):
    path = Path(__file__).resolve().parents[1] / "team_apps" / team / "app.py"
    spec = importlib.util.spec_from_file_location("test_" + team + "_app", path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {
        "ui": ui, "location": types.SimpleNamespace(stop_updates=Mock()),
        "motion": types.SimpleNamespace(),
        "config": types.SimpleNamespace(),
    }):
        spec.loader.exec_module(module)
    return module


class RedBattleSafetyTests(unittest.TestCase):
    def setUp(self):
        self.delays = []
        ui = types.SimpleNamespace(
            View=View, ScrollView=View, Label=View, Button=Button,
            ALIGN_CENTER=1, delay=lambda callback, seconds: self.delays.append(callback),
        )
        self.app = load_app("red", ui)
        self.game = self.app.RedPrototype()
        self.game.active_monster = self.app.MONSTERS[0].copy()
        self.game.start_battle()
        self.random = patch.object(self.app.random, "randint", side_effect=lambda lo, hi: hi)
        self.random.start()
        self.addCleanup(self.random.stop)

    def button(self, prefix):
        return next(view for view in self.game.content.subviews
                    if isinstance(view, Button) and view.title.startswith(prefix))

    def flush(self):
        callbacks, self.delays[:] = self.delays[:], []
        for callback in callbacks:
            callback()

    def tap(self, button):
        controls = list(self.game.content.subviews)
        button.action(button)
        self.assertEqual(controls, self.game.content.subviews,
                         "Do not replace native views inside a button callback")

    def test_repeated_attacks_keep_native_controls(self):
        game = self.game
        game.enemy_hp = game.player_hp = game.player_max_hp = 100000
        controls = list(game.content.subviews)
        button = self.button("素手")
        for _ in range(1000):
            self.tap(button)
            self.flush()
        self.assertEqual(90000, game.enemy_hp)
        self.assertEqual(90000, game.player_hp)
        self.assertEqual(controls, game.content.subviews)

    def test_burst_is_one_turn_and_next_tap_still_works(self):
        button = self.button("素手")
        for _ in range(30):
            self.tap(button)
        self.assertEqual(100, self.game.enemy_hp)
        self.assertEqual(1, len(self.delays))
        self.flush()
        self.assertEqual(90, self.game.enemy_hp)
        self.tap(button)
        self.flush()
        self.assertEqual(80, self.game.enemy_hp)

    def test_weapon_count_updates_then_consumed_button_becomes_stale(self):
        game = self.game
        game.inventory = ["木の棒"]
        game.weapon_uses = {"木の棒": 2}
        game.enemy_hp = 500
        game.show_battle("test")
        button = self.button("木の棒")
        self.tap(button)
        self.flush()
        self.assertIn("残り1回", button.title)
        self.assertIs(button, self.button("木の棒"))
        self.tap(button)
        self.flush()
        self.assertEqual([], game.inventory)
        self.tap(button)
        self.flush()
        self.assertEqual(400, game.enemy_hp)

    def test_victory_and_old_taps_award_only_once(self):
        game = self.game
        game.enemy_hp = 10
        button = self.button("素手")
        self.tap(button)
        self.flush()
        self.assertEqual("battle_result", game.current_screen)
        self.assertEqual(["木の棒"], game.inventory)
        self.assertEqual(110, game.player_max_hp)
        self.tap(button)
        self.flush()
        game.finish_battle(True, "stale result")
        self.assertEqual(["木の棒"], game.inventory)
        self.assertEqual(110, game.player_max_hp)

    def test_defeat_revives_once(self):
        self.game.player_hp = 1
        button = self.button("素手")
        self.tap(button)
        self.flush()
        self.assertEqual("battle_result", self.game.current_screen)
        self.assertEqual(100, self.game.player_hp)
        self.tap(button)
        self.flush()
        self.assertEqual(100, self.game.player_hp)

    def test_navigation_or_close_invalidates_pending_attack(self):
        for leave in (self.game.show_battle_selection, self.game.will_close):
            self.game.start_battle()
            button = self.button("素手")
            self.tap(button)
            leave()
            self.flush()
            self.assertEqual(100, self.game.enemy_hp)
            self.assertFalse(self.game._battle_action_pending)

    def test_escape_invalidates_old_attack(self):
        attack = self.button("素手")
        with patch.object(self.app.random, "random", return_value=0):
            self.tap(self.button("逃げる"))
            self.flush()
        self.tap(attack)
        self.flush()
        self.assertEqual("battle_selection", self.game.current_screen)
        self.assertEqual(100, self.game.enemy_hp)

    def test_artifact_is_consumed_only_once(self):
        self.game.active_monster = self.app.MINIBOSSES[0].copy()
        self.game.inventory = ["三種の神器・鏡"]
        self.game.start_battle()
        button = self.button("鏡：")
        self.tap(button)
        self.flush()
        self.tap(button)
        self.flush()
        self.assertEqual([], self.game.inventory)
        self.assertEqual(4940, self.game.enemy_hp)


if __name__ == "__main__":
    unittest.main()
