"""Purple team local prototype: Tokyo Man escape game mock.

This file intentionally uses no GPS, API, or real-world chemicals.
It is a button-driven UI mock for testing the two-place -> attack loop.
"""

import random
import ui


START_SCORE = 10
START_BOSS_HP = 1000
ATTACK_COST = 50
ATTACK_DAMAGE = 50

QUESTIONS = [
    {
        "question": "東京23区のうち、区名に漢字の「川」が入っている区はいくつ？",
        "choices": ["0区", "1区", "2区"],
        "answer": "1区",
    },
    {
        "question": "駅を東から西に並べてください。",
        "choices": [
            "東京駅 → 渋谷駅 → 新宿駅",
            "新宿駅 → 渋谷駅 → 東京駅",
            "渋谷駅 → 東京駅 → 新宿駅",
        ],
        "answer": "東京駅 → 渋谷駅 → 新宿駅",
    },
    {
        "question": "東京タワーの高さは、およそ何メートル？",
        "choices": ["33m", "333m", "3,330m"],
        "answer": "333m",
    },
    {
        "question": "銀座線を浅草駅から渋谷方面へ。浅草 → 田原町 → ？ → 上野。？は？",
        "choices": ["稲荷町", "神田", "日本橋"],
        "answer": "稲荷町",
    },
    {
        "question": "銀座線で浅草駅を出発したとき、次に到着する駅は？",
        "choices": ["田原町", "銀座", "渋谷"],
        "answer": "田原町",
    },
    {
        "question": "駅番号G09とM16が表す同じ駅は？",
        "choices": ["東京", "銀座", "赤坂見附"],
        "answer": "銀座",
    },
    {
        "question": "駅番号の「G」は何線？（G09）",
        "choices": ["銀座線", "丸ノ内線", "日比谷線"],
        "answer": "銀座線",
    },
    {
        "question": "銀座線と半蔵門線の両方が通る駅は？",
        "choices": ["三越前", "上野", "新橋"],
        "answer": "三越前",
    },
    {
        "question": "駅名に含まれる数字の小さい順は？（六本木・三越前・四ツ谷）",
        "choices": [
            "三越前 → 四ツ谷 → 六本木",
            "四ツ谷 → 三越前 → 六本木",
            "六本木 → 四ツ谷 → 三越前",
        ],
        "answer": "三越前 → 四ツ谷 → 六本木",
    },
    {
        "question": "🌅 ＋ 🌿。朝＋草でできる東京メトロの駅名は？",
        "choices": ["浅草", "銀座", "新宿"],
        "answer": "浅草",
    },
    {
        "question": "🪙 ＋ 💺。銀＋座でできる駅名は？",
        "choices": ["銀座", "三越前", "日本橋"],
        "answer": "銀座",
    },
    {
        "question": "新しいものを表す漢字＋泊まる場所でできる駅名は？",
        "choices": ["新宿", "浅草", "上野"],
        "answer": "新宿",
    },
    {
        "question": "「三越」の前にある駅名は？",
        "choices": ["三越前", "三越町", "前三越"],
        "answer": "三越前",
    },
    {
        "question": "人形がある町を表す駅名は？",
        "choices": ["人形町", "人形橋", "人形前"],
        "answer": "人形町",
    },
    {
        "question": "条件をすべて満たす駅は？ ひらがな5文字・2文字目が「ん」・最後の音が「く」・漢字に「日」",
        "choices": ["浅草", "上野", "新宿"],
        "answer": "新宿",
    },
]


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
            arrive = self._button("地点{}に到着 (+20pt)".format(number), (24, y + 36, 327, 42), lambda sender, i=index: self._arrive(i), "#000000")
            solve = self._button("謎{}を解く（ランダム +10pt）".format(number), (24, y + 84, 327, 42), lambda sender, i=index: self._solve(i), "#6A1B9A")
            self.place_buttons.append(arrive)
            self.solve_buttons.append(solve)

        self.attack_button = self._button("殴る（50pt → 50ダメージ）", (24, 412, 327, 48), self._attack, "#C62828")
        self.reset_button = self._button("仮試作をリセット", (24, 472, 327, 42), self._reset, "#546E7A")
        self.log_label = self._label("", (24, 530, 327, 90), ("<system>", 14), "#455A64")

    def _refresh(self, message=""):
        self.status_label.text = "ポイント: {}pt    東京マン体力: {}/{}".format(self.score, self.boss_hp, START_BOSS_HP)
        for index in range(2):
            previous_arrived = index == 0 or self.arrived[index - 1]
            can_arrive = previous_arrived and not self.arrived[index]
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
        if index > 0 and not self.arrived[index - 1]:
            self._refresh("先に地点{}へ到着してください。".format(index))
            return
        if self.arrived[index]:
            return
        self.arrived[index] = True
        self.score += 20
        self._refresh("地点{}に到着！ +20pt".format(index + 1))

    def _solve(self, index):
        if not self.arrived[index] or self.solved[index]:
            return
        import dialogs

        question = random.choice(QUESTIONS)
        try:
            selected = dialogs.list_dialog(question["question"], question["choices"])
        except KeyboardInterrupt:
            selected = None
        if selected is None:
            self._refresh("謎解きをキャンセルしました。もう一度挑戦できます。")
            return
        if selected != question["answer"]:
            self._refresh("不正解。正解は「{}」。もう一度挑戦できます。".format(question["answer"]))
            return
        self.solved[index] = True
        self.score += 10
        self._refresh("正解！ 謎{}を解いた！ +10pt".format(index + 1))

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


def run():
    PurpleMockGame().present("fullscreen")


if __name__ == "__main__":
    run()
