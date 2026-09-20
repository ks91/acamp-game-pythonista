import unittest

from team_apps.registry import gallery_entries_for_team


class GameGalleryTests(unittest.TestCase):
    def test_gallery_lists_all_games_and_marks_home_and_partner(self):
        entries = gallery_entries_for_team("green")

        self.assertEqual(["blue", "green", "pink", "purple", "red", "yellow"], [entry["team_id"] for entry in entries])
        self.assertEqual("自分たちのゲーム", next(entry["label"] for entry in entries if entry["team_id"] == "green"))
        self.assertEqual("今日まず遊ぶペア班のゲーム", next(entry["label"] for entry in entries if entry["team_id"] == "blue"))

    def test_gallery_marks_all_other_games_as_optional(self):
        entries = gallery_entries_for_team("red")

        self.assertEqual("今日まず遊ぶペア班のゲーム", next(entry["label"] for entry in entries if entry["team_id"] == "yellow"))
        self.assertEqual("ほかの班のゲーム", next(entry["label"] for entry in entries if entry["team_id"] == "blue"))


if __name__ == "__main__":
    unittest.main()
