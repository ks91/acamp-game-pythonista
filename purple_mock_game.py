"""Purple team local prototype: Tokyo Man escape game mock.

This file intentionally uses no GPS, API, or real-world chemicals.
It is a button-driven UI mock for testing the two-place -> attack loop.
"""

import ui


START_SCORE = 10
START_BOSS_HP = 1000
ATTACK_COST = 50
ATTACK_DAMAGE = 50


class PurpleMockGame(ui.View):
    def __init__(self):
        super().__init__(frame=(0, 0, 375, 667))
        self.name = "パープル班 東京マン仮試作"
        self.background_color = "#FFF8E1"
        self.score = START_SCORE
        self.boss_hp = START_BOSS_HP
        self.arrived = [False, False]
        self.solved = [False, False]
        self._build_ui()
        self._refresh()

    def _label(self, text, frame, font, color="#263238", align=ui.ALIGN_LEFT):
        label = ui.Label(frame=frame)
        label.text = text
        label.font = font
        label.text_color = color
        label.alignment = align
        self.add_subview(label)
        return label

    def _button(self, title, frame, action, color="#1565C0"):
        button = ui.Button(frame=frame)
        button.title = title
        button.font = ("<system-bold>", 16)
        button.tint_color = "white"
        button.background_color = color
        button.corner_radius = 10
        button.action = action
        self.add_subview(button)
        return button

    def _build_ui(self):
        width = self.width
        self._label("パープル班｜東京マン脱出ゲーム", (16, 12, width - 32, 30), ("<system-bold>", 20), align=ui.ALIGN_CENTER)
        self.mock_label = self._label("仮動作：GPS・サーバー通信なし", (16, 46, width - 32, 24), ("<system-bold>", 13), "#D84315", ui.ALIGN_CENTER)
        self.status_label = self._label("", (16, 78, width - 32, 72), ("<system-bold>", 17), align=ui.ALIGN_CENTER)

        self.place_buttons = []
        self.solve_buttons = []
        for index, y in enumerate((168, 280)):
            number = index + 1
            self._label("小腸の地点{}".format(number), (24, y, 150, 30), ("<system-bold>", 17))
            arrive = self._button("地点{}に到着 (+20pt)".format(number), (24, y + 36, 327, 42), lambda sender, i=index: self._arrive(i), "#2E7D32")
            solve = self._button("謎{}を解く (+10pt)".format(number), (24, y + 84, 327, 42), lambda sender, i=index: self._solve(i), "#6A1B9A")
            self.place_buttons.append(arrive)
            self.solve_buttons.append(solve)

        self.attack_button = self._button("殴る（50pt → 50ダメージ）", (24, 412, 327, 48), self._attack, "#C62828")
        self.reset_button = self._button("仮試作をリセット", (24, 472, 327, 42), self._reset, "#546E7A")
        self.log_label = self._label("", (24, 530, 327, 90), ("<system>", 14), "#455A64")

    def _refresh(self, message=""):
        self.status_label.text = "ポイント: {}pt    東京マン体力: {}/{}".format(self.score, self.boss_hp, START_BOSS_HP)
        for index in range(2):
            previous_solved = index == 0 or self.solved[index - 1]
            can_arrive = previous_solved and not self.arrived[index]
            self.place_buttons[index].enabled = can_arrive
            self.place_buttons[index].alpha = 1.0 if can_arrive else 0.45
            can_solve = self.arrived[index] and not self.solved[index]
            self.solve_buttons[index].enabled = can_solve
            self.solve_buttons[index].alpha = 1.0 if can_solve else 0.45
        can_attack = self.score >= ATTACK_COST and self.boss_hp > 0
        self.attack_button.enabled = can_attack
        self.attack_button.alpha = 1.0 if can_attack else 0.45
        self.log_label.text = message or "地点へ進み、謎を解いて攻撃ポイントを集めよう。"

    def _arrive(self, index):
        if index > 0 and not self.solved[index - 1]:
            self._refresh("先に地点{}の謎を解いてください。".format(index))
            return
        if self.arrived[index]:
            return
        self.arrived[index] = True
        self.score += 20
        self._refresh("地点{}に到着！ +20pt".format(index + 1))

    def _solve(self, index):
        if not self.arrived[index] or self.solved[index]:
            return
        self.solved[index] = True
        self.score += 10
        self._refresh("謎{}を解いた！ +10pt".format(index + 1))

    def _attack(self, sender):
        if self.score < ATTACK_COST or self.boss_hp <= 0:
            return
        self.score -= ATTACK_COST
        self.boss_hp = max(0, self.boss_hp - ATTACK_DAMAGE)
        if self.boss_hp == 0:
            message = "東京マンを倒した！脱出成功！"
        else:
            message = "殴った！ 東京マンに50ダメージ。"
        self._refresh(message)

    def _reset(self, sender):
        self.score = START_SCORE
        self.boss_hp = START_BOSS_HP
        self.arrived = [False, False]
        self.solved = [False, False]
        self._refresh("仮試作をリセットしました。")


if __name__ == "__main__":
    PurpleMockGame().present("fullscreen")
