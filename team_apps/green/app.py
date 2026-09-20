"""Green team's local territory-capture prototype for Day 2."""
import ui


PLACES = ("センター棟", "国際交流棟", "カフェテリアふじ")


class GreenTerritoryGame(ui.View):
    def __init__(self):
        super().__init__(frame=(0, 0, 375, 667))
        self.name = "グリーン班 陣地取り試作"
        self.background_color = "#E8F5E9"
        self.owner = [None] * len(PLACES)
        self.status = ui.Label(frame=(16, 18, 343, 100))
        self.status.number_of_lines = 0
        self.status.font = ("<system-bold>", 17)
        self.add_subview(self.status)
        self.buttons = []
        for index, place in enumerate(PLACES):
            button = ui.Button(frame=(20, 140 + index * 78, 335, 58))
            button.font = ("<system-bold>", 17)
            button.tint_color = "#2E7D32"
            button.action = lambda sender, i=index: self.capture(i)
            self.add_subview(button)
            self.buttons.append(button)
        self.reset_button = ui.Button(title="はじめから試す", frame=(20, 400, 335, 48))
        self.reset_button.tint_color = "#546E7A"
        self.reset_button.action = self.reset
        self.add_subview(self.reset_button)
        self.refresh("どの地点を最初の陣地にする？")

    def refresh(self, message):
        count = sum(owner == "green" for owner in self.owner)
        self.status.text = "グリーンの陣地: {} / {}\n{}".format(count, len(PLACES), message)
        for index, place in enumerate(PLACES):
            label = "{}\n{}".format(place, "グリーンの旗" if self.owner[index] == "green" else "まだ誰の陣地でもない")
            self.buttons[index].title = label

    def capture(self, index):
        was_owned = self.owner[index] == "green"
        self.owner[index] = None if was_owned else "green"
        self.refresh("{}を{}。このあと守る？ 次を取りに行く？".format(PLACES[index], "手放した" if was_owned else "手に入れた"))

    def reset(self, sender):
        self.owner = [None] * len(PLACES)
        self.refresh("はじめから。どの地点を最初の陣地にする？")


def run():
    GreenTerritoryGame().present("fullscreen")


if __name__ == "__main__":
    run()
