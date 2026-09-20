"""A small, independent Day 2 game-design playground."""
import ui


class DraftGame(ui.View):
    def __init__(self, team_name, color, prompt):
        super().__init__(frame=(0, 0, 375, 667))
        self.name = team_name + "班 試作"
        self.background_color = "white"
        title = ui.Label(frame=(16, 24, 343, 34))
        title.text = team_name + "班の今日の試作"
        title.font = ("<system-bold>", 24)
        title.text_color = color
        title.alignment = ui.ALIGN_CENTER
        self.add_subview(title)
        self.message = ui.Label(frame=(24, 82, 327, 120))
        self.message.number_of_lines = 0
        self.message.font = ("<system>", 18)
        self.message.text = prompt
        self.add_subview(self.message)
        self.steps = []
        for index, label in enumerate(("最初の行動を決めた", "一回遊んでみた", "面白かったことを決めた")):
            button = ui.Button(title=label, frame=(24, 230 + index * 70, 327, 50))
            button.tint_color = color
            button.action = lambda sender, i=index: self.complete(i)
            self.add_subview(button)
            self.steps.append(button)

    def complete(self, index):
        self.steps[index].enabled = False
        self.steps[index].title = "✓ " + self.steps[index].title
        done = sum(not button.enabled for button in self.steps)
        self.message.text = "{} / 3 できた。\n次は班で『一番面白かった瞬間』を一言で決めよう。".format(done)


def run(team_name, color, prompt):
    DraftGame(team_name, color, prompt).present("fullscreen")
