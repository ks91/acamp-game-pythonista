import unittest

from toolkit.quest_flow import build_quest_cards, capture_instruction, is_quest_complete


class QuestFlowTests(unittest.TestCase):
    def test_builds_selectable_quest_cards_with_easy_reward(self):
        cards = build_quest_cards(
            {
                "quests": [
                    {
                        "id": "find-two-elevators",
                        "name": "エレベーターを2個探せ！",
                        "type": "elevator",
                        "difficulty": "easy",
                        "reward_coins": 20,
                    }
                ]
            }
        )
        self.assertEqual(
            {
                "id": "find-two-elevators",
                "name": "エレベーターを2個探せ！",
                "type": "elevator",
                "capture_instruction": "",
                "difficulty": "easy",
                "reward_coins": 20,
                "hint": "",
            },
            cards[0],
        )

    def test_server_quest_keeps_type_for_capture_instructions(self):
        card = build_quest_cards(
            {
                "quests": [
                    {
                        "id": "elevator",
                        "name": "エレベーター",
                        "type": "elevator",
                    }
                ]
            }
        )[0]
        self.assertIn("操作盤", capture_instruction(card))

    def test_server_quest_keeps_custom_capture_instruction(self):
        card = build_quest_cards(
            {
                "quests": [
                    {
                        "id": "custom",
                        "name": "カスタム",
                        "capture_instruction": "目印を中央に写してください。",
                    }
                ]
            }
        )[0]
        self.assertEqual("目印を中央に写してください。", capture_instruction(card))

    def test_server_quest_without_instruction_uses_default(self):
        card = build_quest_cards(
            {"quests": [{"id": "plain", "name": "通常クエスト"}]}
        )[0]
        self.assertIn("対象を画面に収めて", capture_instruction(card))

    def test_elevator_capture_instruction_is_specific(self):
        self.assertIn("扉全体", capture_instruction({"type": "elevator"}))
        self.assertIn("操作盤", capture_instruction({"type": "elevator"}))

    def test_duplicate_elevator_group_does_not_complete_twice(self):
        self.assertFalse(is_quest_complete(["east", "east"], 2))
        self.assertTrue(is_quest_complete(["east", "west"], 2))


if __name__ == "__main__":
    unittest.main()
