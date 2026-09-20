"""Pure quest-selection and capture-flow helpers for the Pythonista client."""


def build_quest_cards(definition):
    """Return selectable quest cards without mutating the server definition."""
    cards = []
    for quest in definition.get("quests", []):
        cards.append(
            {
                "id": quest["id"],
                "name": quest["name"],
                "type": quest.get("type"),
                "capture_instruction": quest.get("capture_instruction", ""),
                "difficulty": quest.get("difficulty", "normal"),
                "reward_coins": quest.get("reward_coins", 0),
                "hint": quest.get("hint", ""),
            }
        )
    return cards


def capture_instruction(quest):
    if quest.get("type") == "elevator":
        return "扉全体と操作盤が、同じ写真に写るように撮影してください。"
    return quest.get("capture_instruction", "対象を画面に収めて撮影してください。")


def is_quest_complete(found_group_ids, required_count):
    """A group is counted once even when it was captured repeatedly."""
    return len(set(found_group_ids)) >= required_count
