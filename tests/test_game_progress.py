import copy
import json
import os
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from toolkit.game_progress import GameProgress, make_progress_store


def configuration(**overrides):
    values = dict(TEAM_ID="red", GAME_SESSION_ID="configured-session", SELECTED_GAME_MODE="tokyo")
    values.update(overrides)
    return types.SimpleNamespace(**values)


def pink_view():
    return types.SimpleNamespace(coins=0, tickets={"skip": 0, "hint": 0},
                                 distance_remainder_m=0.0, collected_coin_ids=set())


def purple_view():
    return types.SimpleNamespace(
        score=10, boss_hp=100, lives=3, arrived=[False, False], solved=[False, False],
        used_question_indexes=set(), chest_arrival_checked=[False, False],
        chest_riddle_checked=[False, False], chest_items=[None, None],
        item_inventory={"bomb": 0}, good_bacteria_visible=False, good_bacteria_hp=50,
    )


class GameProgressTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)

    def open(self, view=None, config=None, game="pink"):
        view = view or pink_view()
        store = GameProgress(view, config or configuration(), game, self.directory.name)
        return view, store

    def test_restore_progress_and_mutable_containers_without_gps_or_secrets(self):
        view, store = self.open()
        view.coins = 77
        view.tickets["skip"] = 2
        view.collected_coin_ids.add("coin1")
        view.distance_remainder_m = 12.5
        view.last_position = {"latitude": 35, "longitude": 139}
        view.token = "not-for-disk"
        self.assertTrue(store.save(view))
        restored, _ = self.open()
        self.assertEqual(77, restored.coins)
        self.assertEqual({"skip": 2, "hint": 0}, restored.tickets)
        self.assertEqual({"coin1"}, restored.collected_coin_ids)
        self.assertEqual(12.5, restored.distance_remainder_m)
        saved = Path(store.path).read_text()
        self.assertNotIn("latitude", saved)
        self.assertNotIn("not-for-disk", saved)

    def test_player_mode_game_and_configured_session_are_separate(self):
        view, store = self.open()
        view.coins = 99
        store.save(view)
        for config in (configuration(TEAM_ID="purple"), configuration(SELECTED_GAME_MODE="center_test"),
                       configuration(GAME_SESSION_ID="other")):
            restored, other = self.open(config=config)
            self.assertEqual(0, restored.coins)
            self.assertNotEqual(store.path, other.path)
        _, purple = self.open(purple_view(), game="purple")
        self.assertNotEqual(store.path, purple.path)

    def test_resolved_sessions_are_separate_and_latest_is_available_offline(self):
        view, store = self.open()
        store.bind_session(view, "tokyo-day4")
        view.coins = 25
        store.save(view)
        restored, again = self.open()
        self.assertEqual("tokyo-day4", again.session_id)
        self.assertEqual(25, restored.coins)
        self.assertTrue(again.bind_session(restored, "tokyo-day5"))
        self.assertEqual(0, restored.coins)
        restored.coins = 3
        again.save(restored)
        again.bind_session(restored, "tokyo-day4")
        self.assertEqual(25, restored.coins)
        self.assertFalse(again.bind_session(restored, "tokyo-day4"))

    def test_interleaved_stores_keep_other_sessions(self):
        first, a = self.open()
        second, b = self.open()
        a.bind_session(first, "A")
        b.bind_session(second, "B")
        first.coins = 10
        second.coins = 20
        a.save(first)
        b.save(second)
        b.bind_session(second, "A")
        self.assertEqual(10, second.coins)

    def test_corrupt_primary_recovers_previous_complete_snapshot(self):
        view, store = self.open()
        view.coins = 10
        store.save(view)
        view.coins = 20
        store.save(view)
        Path(store.path).write_text('{"interrupted":')
        restored, recovered = self.open()
        self.assertEqual(10, restored.coins)
        self.assertIn("予備", recovered.warning)

    def test_bad_shapes_and_broken_files_do_not_prevent_launch(self):
        view, store = self.open()
        store.save(view)
        original = json.loads(Path(store.path).read_text())
        bad_states = [None, {"coins": 2}, dict(original["sessions"][store.session_id], coins="bad"),
                      dict(original["sessions"][store.session_id], tickets={}),
                      dict(original["sessions"][store.session_id], coins=True)]
        for bad in bad_states:
            document = copy.deepcopy(original)
            document["sessions"][store.session_id] = bad
            for path in (store.path, store.path + ".bak"):
                Path(path).write_text(json.dumps(document))
            restored, recovered = self.open()
            self.assertEqual(0, restored.coins)
            self.assertTrue(recovered.warning)
        for path in (store.path, store.path + ".bak"):
            Path(path).write_bytes(b'\xff\xff')
        restored, recovered = self.open()
        self.assertEqual(0, restored.coins)
        self.assertTrue(recovered.warning)

    def test_failed_replace_keeps_last_saved_state_and_does_not_raise(self):
        view, store = self.open()
        view.coins = 10
        store.save(view)
        view.coins = 20
        real_replace = os.replace
        def fail_primary(source, destination):
            if destination == store.path:
                raise OSError("disk full")
            return real_replace(source, destination)
        with patch("toolkit.game_progress.os.replace", side_effect=fail_primary):
            self.assertFalse(store.save(view))
        self.assertIn("保存できません", store.warning)
        self.assertEqual(10, self.open()[0].coins)
        self.assertFalse(list(Path(self.directory.name).glob(".progress-*")))

    def test_reset_and_backup_cannot_resurrect_old_progress(self):
        view, store = self.open()
        view.coins = 100
        store.save(view)
        view.coins = 0
        store.save(view, reset=True)
        Path(store.path).write_text("broken")
        self.assertEqual(0, self.open()[0].coins)

    def test_extremely_nested_corrupt_json_does_not_prevent_launch(self):
        view, store = self.open()
        store.save(view)
        for path in (store.path, store.path + ".bak"):
            Path(path).write_text("[" * 2000 + "]" * 2000)
        restored, recovered = self.open()
        self.assertEqual(0, restored.coins)
        self.assertTrue(recovered.warning)

    def test_purple_game_over_restores_initial_playable_state(self):
        view, store = self.open(purple_view(), game="purple")
        view.score = 200
        view.boss_hp = 50
        view.lives = 0
        store.save(view)
        restored, _ = self.open(purple_view(), game="purple")
        self.assertEqual((10, 100, 3), (restored.score, restored.boss_hp, restored.lives))
        self.assertEqual([False, False], restored.arrived)

    def test_no_store_for_missing_configuration(self):
        self.assertIsNone(make_progress_store(pink_view(), None, "pink"))
        self.assertIsNone(make_progress_store(pink_view(), types.SimpleNamespace(), "pink"))


if __name__ == "__main__":
    unittest.main()
