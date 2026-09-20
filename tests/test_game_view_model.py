import unittest

from toolkit.game_view_model import build_game_view_model


class GameViewModelTests(unittest.TestCase):
    def test_builds_team_specific_theme_status_and_place_cards(self):
        model = build_game_view_model(
            definition={
                "name": "ブルー班試作",
                "intro": "発見を集めよう。",
                "ui": {"accent_color": "#1565C0", "background_color": "#E3F2FD"},
                "places": [
                    {"id": "station", "name": "駅", "points": 120, "description": "入口"}
                ],
            },
            state={"score": 120, "location_event_count": 2, "claimed_places": ["station"]},
            team_id="blue",
        )
        self.assertEqual("#1565C0", model["theme"]["accent_color"])
        self.assertIn("ブルー班試作 / blue班", model["status_text"])
        self.assertTrue(model["places"][0]["claimed"])
        self.assertEqual("入口", model["places"][0]["narrative"])


if __name__ == "__main__":
    unittest.main()
