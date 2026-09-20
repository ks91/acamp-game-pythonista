"""Choose a team game without changing config.py or Git branches."""

import importlib

import ui

import config
from team_apps.registry import gallery_entries_for_team


GAME_COLORS = {
    "blue": "#1565C0",
    "green": "#2E7D32",
    "red": "#C62828",
    "yellow": "#F9A825",
    "purple": "#7B1FA2",
    "pink": "#D81B60",
}

TEAM_NAMES = {
    "blue": "ブルー",
    "green": "グリーン",
    "red": "レッド",
    "yellow": "イエロー",
    "purple": "パープル",
    "pink": "ピンク",
}


class GameGallery(ui.View):
    def __init__(self):
        super().__init__(frame=(0, 0, 375, 667))
        self.name = "アカキャン ゲームギャラリー"
        self.background_color = "white"
        self.team_id = config.TEAM_ID
        title = ui.Label(frame=(18, 16, 339, 58), flex="W")
        title.text = "アカキャン ゲームギャラリー\n{}班のiPad".format(TEAM_NAMES.get(self.team_id, self.team_id))
        title.font = ("<system-bold>", 20)
        title.number_of_lines = 0
        self.add_subview(title)
        instruction = ui.Label(frame=(18, 78, 339, 54), flex="W")
        instruction.text = "遊びたいゲームを選んでください。\n自分たちとペア班のゲームから、まず試そう。"
        instruction.number_of_lines = 0
        instruction.font = ("<system>", 15)
        self.add_subview(instruction)
        self.scroll = ui.ScrollView(frame=(0, 142, 375, 525), flex="WH")
        self.add_subview(self.scroll)
        self.render_entries()

    def layout(self):
        self.scroll.frame = (0, 142, self.width, self.height - 142)

    def render_entries(self):
        y = 12
        for entry in gallery_entries_for_team(self.team_id):
            team_id = entry["team_id"]
            button = ui.Button(frame=(16, y, self.width - 32, 68))
            button.title = "{}班のゲーム\n{}".format(TEAM_NAMES[team_id], entry["label"])
            button.font = ("<system-bold>", 17)
            button.tint_color = "white"
            button.background_color = GAME_COLORS[team_id]
            button.corner_radius = 10
            button.action = self.launch_game
            button.module_name = entry["module"]
            button.game_team_id = team_id
            self.scroll.add_subview(button)
            y += 78
        self.scroll.content_size = (self.width, y + 12)

    def launch_game(self, sender):
        config.SELECTED_GAME_TEAM_ID = sender.game_team_id
        module = importlib.import_module(sender.module_name)
        module.run()


def run():
    GameGallery().present("fullscreen")


if __name__ == "__main__":
    run()
