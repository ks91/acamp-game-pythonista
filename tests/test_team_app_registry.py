import unittest

from team_apps.registry import app_module_for_team


class TeamAppRegistryTests(unittest.TestCase):
    def test_every_team_uses_its_own_app_module(self):
        for team in ("green", "blue", "red", "yellow", "purple", "pink"):
            self.assertEqual("team_apps.{}.app".format(team), app_module_for_team(team))

    def test_unknown_team_uses_shared_game_app(self):
        self.assertEqual("game_app", app_module_for_team("orange"))


if __name__ == "__main__":
    unittest.main()
