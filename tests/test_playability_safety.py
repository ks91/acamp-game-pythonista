"""Regression checks for GPS claims, quest data and delayed game callbacks."""
import types
import unittest
from unittest.mock import Mock, patch

from test_red_battle_safety import Button, View, load_app
from toolkit.claim_flow import claim_with_location


POSITION = {"latitude": 35.68, "longitude": 139.76, "horizontal_accuracy": 15.0}


class ClaimFlowTests(unittest.TestCase):
    def test_location_is_sent_before_claim_for_the_player_team(self):
        api = Mock()
        api.claim_place.return_value = {"claimed": True}
        result = claim_with_location(
            api, team_id="pink", device_id="pink-ipad", game_session_id="purple-tokyo",
            place_id="first", position=POSITION,
        )
        self.assertEqual(["post_location_sample", "claim_place"],
                         [call[0] for call in api.mock_calls])
        sample = api.post_location_sample.call_args.args[0]
        self.assertEqual("pink", sample["team_id"])
        self.assertEqual(15.0, sample["accuracy_m"])
        self.assertEqual("first", api.claim_place.call_args.kwargs["place_id"])
        self.assertTrue(result["claimed"])

    def test_location_failure_does_not_claim_using_an_older_server_fix(self):
        api = Mock()
        api.post_location_sample.side_effect = OSError("offline")
        with self.assertRaises(OSError):
            claim_with_location(api, team_id="pink", device_id="ipad",
                                game_session_id="session", place_id="first", position=POSITION)
        api.claim_place.assert_not_called()

    def test_missing_fix_cannot_be_used_to_claim(self):
        api = Mock()
        with self.assertRaises(ValueError):
            claim_with_location(api, team_id="pink", device_id="ipad",
                                game_session_id="session", place_id="first", position=None)
        self.assertEqual([], api.mock_calls)


class AppSafetyTests(unittest.TestCase):
    def setUp(self):
        self.delays = []
        self.ui = types.SimpleNamespace(
            View=View, ScrollView=View, Label=View, Button=Button,
            ALIGN_CENTER=1, ALIGN_LEFT=0,
            delay=lambda callback, seconds: self.delays.append(callback),
        )

    def app(self, team):
        app = load_app(team, self.ui)
        app.config = types.SimpleNamespace(TEAM_ID="pink", DEVICE_ID="pink-ipad",
                                           GAME_SESSION_ID="session")
        return app

    def flush(self):
        callbacks, self.delays[:] = self.delays[:], []
        for callback in callbacks:
            callback()

    @staticmethod
    def view(cls):
        view = cls.__new__(cls)
        View.__init__(view)
        return view

    def purple(self):
        app = self.app("purple")
        game = self.view(app.PurpleMockGame)
        game._round_generation = game._quiz_generation = 0
        game._arriving = False
        game.current_location = dict(POSITION)
        game.place_locations = [dict(POSITION, id="first", name="first", radius_m=40),
                                dict(POSITION, id="second", name="second", radius_m=40)]
        game.api = Mock()
        game.api.claim_place.return_value = {"claimed": True, "team_score": 20}
        game.arrived = [False, False]
        game.solved = [False, False]
        game.score = 10
        game.lives = 3
        game.used_question_indexes = set()
        game.quiz_overlay = None
        game.quiz_active = False
        game._refresh = Mock()
        game._hide_feedback = Mock()
        game._show_feedback = Mock()
        game._show_good_bacteria_arrival = Mock()
        game._maybe_spawn_chest = Mock(return_value="")
        return app, game

    def test_purple_arrival_posts_gps_and_ignores_duplicate_taps(self):
        app, game = self.purple()
        workers = []
        with patch.object(app.threading, "Thread", side_effect=lambda target, daemon:
                          types.SimpleNamespace(start=lambda: workers.append(target))):
            game._arrive(0, 0)
            game._arrive(0, 0)
        self.assertEqual(1, len(workers))
        self.assertFalse(game.arrived[0])
        workers.pop()()
        self.flush()
        self.assertTrue(game.arrived[0])
        self.assertFalse(game._arriving)
        self.assertEqual(["post_location_sample", "claim_place"],
                         [call[0] for call in game.api.mock_calls])

    def test_purple_arrival_can_retry_after_network_failure(self):
        app, game = self.purple()
        game.api.post_location_sample.side_effect = OSError("offline")
        with patch.object(app.threading, "Thread", side_effect=lambda target, daemon:
                          types.SimpleNamespace(start=target)):
            game._arrive(0, 0)
            self.flush()
            self.assertFalse(game.arrived[0])
            self.assertFalse(game._arriving)
            game.api.claim_place.assert_not_called()
            game.api.post_location_sample.side_effect = None
            game._arrive(0, 0)
            self.flush()
        self.assertTrue(game.arrived[0])

    def test_purple_closed_game_ignores_in_flight_arrival(self):
        app, game = self.purple()
        with patch.object(app.threading, "Thread", side_effect=lambda target, daemon:
                          types.SimpleNamespace(start=target)):
            game._arrive(0, 0)
        game.will_close()
        self.flush()
        self.assertFalse(game.arrived[0])

    def test_purple_old_quiz_timer_cannot_speed_up_next_quiz(self):
        app, game = self.purple()
        game._start_quiz(0, 0)
        game._finish_quiz(app.QUESTIONS[0]["answer"])
        game._start_quiz(1, 1)
        self.assertEqual(2, len(self.delays))
        self.flush()
        self.assertEqual(29, game.quiz_remaining)
        self.assertEqual(1, len(self.delays))

    def test_purple_reset_invalidates_old_quiz_and_pending_game_over(self):
        _, game = self.purple()
        game._start_quiz(0, 0)
        old_generation = game._round_generation
        game._reset()
        game.score = 99
        game._restore_checkpoint(old_generation)
        self.flush()
        self.assertEqual(99, game.score)
        self.assertFalse(game.quiz_active)
        self.assertIsNone(game.quiz_overlay)
        self.assertEqual([], self.delays)

    def test_green_uses_server_radius_instead_of_ten_meter_test_radius(self):
        app = self.app("green")
        for radius in (10, 40, 100):
            model = app.GreenTerritoryGame._build_model(
                {"places": [dict(POSITION, id="place", name="place", radius_m=radius)]},
                {}, "green",
            )
            self.assertEqual(radius, model["places"][0]["capture_radius_meters"])

    def test_red_claim_keeps_original_place_and_position_across_next_battle(self):
        app = self.app("red")
        game = app.RedPrototype()
        game.api = Mock()
        game.api.claim_place.return_value = {"claimed": True}
        game.server_scenario_loaded = True
        game.game_session_id = "session"
        game.active_place_id = "first"
        game.last_position = dict(POSITION)
        workers = []
        with patch.object(app.threading, "Thread", side_effect=lambda target, args, daemon:
                          types.SimpleNamespace(start=lambda: workers.append(lambda: target(*args)))):
            game._claim_active_server_place()
        game.active_place_id = "second"
        game.last_position["latitude"] = 35.0
        workers.pop()()
        self.flush()
        self.assertEqual("first", game.api.claim_place.call_args.kwargs["place_id"])
        self.assertEqual(POSITION["latitude"], game.api.post_location_sample.call_args.args[0]["latitude"])
        self.assertEqual({"first"}, game.claimed_place_ids)

    def test_blue_keeps_all_server_targets_and_required_count(self):
        app = self.app("blue")
        game = self.view(app.GameView)
        game.api = Mock()
        targets = [dict(POSITION), dict(POSITION, longitude=139.77)]
        quest = {"id": "two", "name": "two", "target_locations": targets, "required_count": 1}
        game.api.get_game_definition.return_value = {"quests": [quest]}
        game.api.get_team_state.return_value = {}
        game.status_label = View()
        game.registered_quest_locations = {"two": [dict(POSITION, longitude=0)]}
        game.render_title_screen = Mock()
        game.refresh()
        self.assertEqual(targets, game.available_quests[0]["target_locations"])
        self.assertEqual(1, game.available_quests[0]["required_count"])

    def test_pink_manual_update_keeps_auto_collection_gps_running(self):
        app = self.app("pink")
        game = self.view(app.GameView)
        game.auto_coin_collection_active = True
        game.api = Mock()
        game.queue = Mock()
        game.show_message = Mock()
        game._collect_distance_coins = Mock(return_value=0)
        app.location = Mock()
        app.location.get_location.return_value = dict(POSITION)
        with patch.object(app, "CheckInService") as checkin:
            checkin.return_value.submit.return_value = {"queued": True}
            game.update_location(None)
        app.location.start_updates.assert_called_once()
        app.location.stop_updates.assert_not_called()

    def test_blue_and_pink_can_retry_after_offline_launch(self):
        for team in ("blue", "pink"):
            with self.subTest(team=team):
                app = self.app(team)
                game = self.view(app.GameView)
                game.api = Mock()
                game.api.get_game_definition.side_effect = OSError("offline")
                game.scroll = View()
                game.status_label = View()
                game.refresh()
                self.assertEqual(1, len(game.scroll.subviews))
                retry = game.scroll.subviews[0]
                retry.action(retry)
                self.assertEqual(2, game.api.get_game_definition.call_count)
                self.assertEqual(1, len(game.scroll.subviews))

    def test_partner_games_never_reset_the_players_own_session(self):
        yellow = self.app("yellow")
        game = self.view(yellow.YellowEgyptGame)
        game.api = Mock()
        game.api.game_team_id = "yellow"  # The player is pink, not yellow.
        game._handle_restart_error = Mock()
        game._restart_test_session()
        self.flush()
        game.api.restart_test_session.assert_not_called()
        game._handle_restart_error.assert_called_once()

        green = self.app("green")
        game = self.view(green.GreenTerritoryGame)
        game.team_id = "blue"
        game.api_client = Mock()
        game.api_client.game_team_id = "green"
        game.detail = View()
        game._restart_test_session_complete = Mock()
        with patch.object(green.threading, "Thread") as thread:
            game.restart_test_session(None)
            thread.assert_not_called()
        game._restart_test_session_worker()
        self.flush()
        game.api_client.restart_test_session.assert_not_called()
        game._restart_test_session_complete.assert_called_once()


if __name__ == "__main__":
    unittest.main()
