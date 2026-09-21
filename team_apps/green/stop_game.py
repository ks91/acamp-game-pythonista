"""Green班のミニゲーム集。10秒・国旗4択・なぞなぞミッション。"""
import random
import time
import ui

TARGET_SECONDS = 10.0
DIFFICULTIES = (("ゆっくり", 1.0), ("ふつう", 0.7), ("はやい", 0.4))
TOTAL_ROUNDS = 3
FLAGS = (
    ("🇯🇵", "日本"), ("🇺🇸", "アメリカ"), ("🇫🇷", "フランス"), ("🇮🇹", "イタリア"),
    ("🇬🇧", "イギリス"), ("🇩🇪", "ドイツ"), ("🇰🇷", "韓国"), ("🇧🇷", "ブラジル"),
    ("🇨🇦", "カナダ"), ("🇦🇺", "オーストラリア"), ("🇪🇸", "スペイン"), ("🇮🇳", "インド"),
    ("🇮🇩", "インドネシア"), ("🇲🇨", "モナコ"), ("🇹🇩", "チャド"), ("🇷🇴", "ルーマニア"),
)
SIMILAR_FLAG_GROUPS = (("インドネシア", "モナコ"), ("チャド", "ルーマニア"))
RIDDLES = (
    ("パンはパンでも、食べられないパンは？", "フライパン", ("あんパン", "フライパン", "食パン", "メロンパン")),
    ("いつも走っているのに、ぜんぜん疲れないものは？", "時計", ("時計", "電車", "犬", "自転車")),
    ("切っても切っても、切れないものは？", "水", ("紙", "水", "木", "ケーキ")),
    ("冷蔵庫の中にいる動物は？", "ゾウ", ("ネコ", "ゾウ", "イヌ", "キリン")),
    ("雨の日に大きくなって、晴れの日に小さくなるものは？", "水たまり", ("雲", "水たまり", "傘", "虹")),
)


class MissionMiniGame(ui.View):
    """One embeddable territory mission; GPS and claiming stay in app.py."""

    def __init__(self, kind, on_success, on_cancel, frame=(0, 0, 390, 844)):
        super().__init__(frame=frame)
        if kind not in ("stop", "flag", "riddle"):
            raise ValueError("unknown Green mission kind: {}".format(kind))
        self.flex = "WH"
        self.background_color = (0, 0, 0, 0.66)
        self.kind = kind
        self.on_success = on_success
        self.on_cancel = on_cancel
        self.running = False
        self.started_at = None
        self.card = ui.View()
        self.card.background_color = "#17212B"
        self.add_subview(self.card)
        self.title_label = self._label("", (20, 18, 310, 52), ("<system-bold>", 23))
        self.message_label = self._label(
            "", (20, 75, 310, 90), ("<system-bold>", 18), color="#D9EAF7"
        )
        self.buttons = []
        self.cancel_button = self._button("やめる", (75, 345, 200, 40), self._cancel, "#486581")
        self._build_mission()

    def layout(self):
        card_width = min(430, self.width - 40)
        card_height = 410
        self.card.frame = (
            (self.width - card_width) / 2,
            max(35, (self.height - card_height) / 2),
            card_width,
            card_height,
        )
        content_width = card_width - 40
        self.title_label.frame = (20, 18, content_width, 52)
        self.message_label.frame = (20, 75, content_width, 90)
        self.cancel_button.frame = ((card_width - 200) / 2, 345, 200, 40)

    def _label(self, text, frame, font, color="white"):
        label = ui.Label(
            frame=frame, text=text, font=font, text_color=color,
            alignment=ui.ALIGN_CENTER, number_of_lines=0,
        )
        self.card.add_subview(label)
        return label

    def _button(self, title, frame, action, color="#2EBD85"):
        button = ui.Button(frame=frame, title=title, font=("<system-bold>", 17), action=action)
        button.background_color = color
        button.tint_color = "white"
        button.corner_radius = 10
        self.card.add_subview(button)
        return button

    def _clear_answer_buttons(self):
        for button in self.buttons:
            self.card.remove_subview(button)
        self.buttons = []

    def _build_mission(self):
        self._clear_answer_buttons()
        if self.kind == "stop":
            self.title_label.text = "10秒ぴったりミッション"
            self.message_label.text = "START後、10秒だと思ったらSTOP！\n成功範囲は9.0〜11.0秒"
            self.start_button = self._button("START", (35, 190, 130, 64), self._start_timer)
            self.stop_button = self._button("STOP", (185, 190, 130, 64), self._stop_timer, "#EF8354")
            self.stop_button.enabled = False
            self.buttons = [self.start_button, self.stop_button]
        elif self.kind == "flag":
            flag, answer = random.choice(FLAGS)
            names = [name for _, name in FLAGS]
            self.current_answer = answer
            self.current_choices = self._make_choices(answer, names, SIMILAR_FLAG_GROUPS)
            self.title_label.text = "国旗当てミッション　{}".format(flag)
            self.message_label.text = "この国旗はどこの国？"
            self._add_choice_buttons(self.current_choices)
        else:
            question, answer, choices = random.choice(RIDDLES)
            self.current_answer = answer
            self.current_choices = list(choices)
            self.title_label.text = "なぞなぞミッション"
            self.message_label.text = question
            self._add_choice_buttons(self.current_choices)

    @staticmethod
    def _make_choices(answer, values, similar_groups=()):
        choices = {answer}
        while len(choices) < 4:
            candidate = random.choice(values)
            blocked = any(answer in group and candidate in group for group in similar_groups)
            if not blocked:
                choices.add(candidate)
        result = list(choices)
        random.shuffle(result)
        return result

    def _add_choice_buttons(self, choices):
        for index, choice in enumerate(choices):
            button = self._button(
                choice, (35, 170 + index * 43, 280, 36),
                lambda sender, i=index: self._answer(i), "#486581",
            )
            self.buttons.append(button)

    def _answer(self, index):
        for button in self.buttons:
            button.enabled = False
        if self.current_choices[index] == self.current_answer:
            self.message_label.text = "正解！ ミッションクリア！"
            self.message_label.text_color = "#7CFF6B"
            ui.delay(self._succeed, 0.5)
            return
        self.message_label.text = "残念！ 正解は {}\nもう一度挑戦しよう".format(self.current_answer)
        self.message_label.text_color = "#FF9B85"
        retry = self._button("もう一度", (75, 305, 200, 36), self._retry, "#D97745")
        self.buttons.append(retry)

    def _start_timer(self, sender):
        if self.running:
            return
        self.running = True
        self.started_at = time.monotonic()
        self.start_button.enabled = False
        self.stop_button.enabled = True
        self.message_label.text_color = "#D9EAF7"
        self._tick()

    def _tick(self):
        if not self.running or self.started_at is None:
            return
        self.message_label.text = "{:.2f}秒".format(time.monotonic() - self.started_at)
        ui.delay(self._tick, 0.05)

    def _stop_timer(self, sender):
        if not self.running or self.started_at is None:
            return
        elapsed = time.monotonic() - self.started_at
        self.running = False
        self.stop_button.enabled = False
        if abs(elapsed - TARGET_SECONDS) <= 1.0:
            self.message_label.text = "{:.2f}秒　成功！".format(elapsed)
            self.message_label.text_color = "#7CFF6B"
            ui.delay(self._succeed, 0.5)
            return
        self.message_label.text = "{:.2f}秒　惜しい！\n9.0〜11.0秒を目指そう".format(elapsed)
        self.message_label.text_color = "#FF9B85"
        self.start_button.title = "もう一度"
        self.start_button.enabled = True

    def _retry(self, sender=None):
        self.message_label.text_color = "#D9EAF7"
        self._build_mission()

    def _succeed(self):
        self.running = False
        self.on_success()

    def _cancel(self, sender=None):
        self.running = False
        self.on_cancel()


class TenSecondGame(ui.View):
    def __init__(self):
        super().__init__(frame=(0, 0, 390, 844))
        self.flex = "WH"
        self.background_color = "#102A43"
        self.name = "グリーン班ミニゲーム"
        self.started_at = None
        self.running = False
        self.counting_down = False
        self.difficulty_index = 1
        self.round_number = 1
        self.records = []
        self.home_view = ui.View(frame=self.bounds, flex="WH")
        self.stop_view = ui.View(frame=self.bounds, flex="WH")
        self.flag_view = ui.View(frame=self.bounds, flex="WH")
        self.riddle_view = ui.View(frame=self.bounds, flex="WH")
        for view in (self.home_view, self.stop_view, self.flag_view, self.riddle_view):
            self.add_subview(view)
        self._build_home()
        self._build_stop_game()
        self._build_flag_quiz()
        self._build_riddle_quiz()
        self.show_home()

    @property
    def difficulty_name(self):
        return DIFFICULTIES[self.difficulty_index][0]

    @property
    def countdown_speed(self):
        return DIFFICULTIES[self.difficulty_index][1]

    def _label(self, parent, frame, text, font, color="white", **kwargs):
        label = ui.Label(frame=frame, text=text, font=font, text_color=color, **kwargs)
        parent.add_subview(label)
        return label

    def _button(self, parent, frame, title, action, color):
        button = ui.Button(frame=frame, title=title, font=("<system-bold>", 18), action=action)
        button.background_color = color
        button.tint_color = "white"
        button.corner_radius = 12
        parent.add_subview(button)
        return button

    def _build_home(self):
        self._label(self.home_view, (20, 35, 350, 65), "グリーン班\nミニゲーム集", ("<system-bold>", 28), alignment=ui.ALIGN_CENTER, number_of_lines=2, flex="W")
        self.stop_game_button = self._button(self.home_view, (45, 135, 300, 62), "10秒ストップゲーム", self.open_stop_game, "#2EBD85")
        self.flag_game_button = self._button(self.home_view, (45, 225, 300, 62), "国旗当てゲーム", self.open_flag_quiz, "#7B61FF")
        self.riddle_game_button = self._button(self.home_view, (45, 315, 300, 62), "なぞなぞミッション", self.open_riddle_quiz, "#D97745")
        self._label(self.home_view, (30, 430, 330, 90), "遊びたいゲームを\n選んでね！", ("<system>", 22), color="#D9EAF7", alignment=ui.ALIGN_CENTER, number_of_lines=2, flex="W")

    def _build_stop_game(self):
        self._label(self.stop_view, (20, 40, 350, 45), "10秒ぴったりゲーム", ("<system-bold>", 25), alignment=ui.ALIGN_CENTER, flex="W")
        self.round_label = self._label(self.stop_view, (25, 90, 340, 32), "", ("<system-bold>", 18), color="#7CFF6B", alignment=ui.ALIGN_CENTER, flex="W")
        self.stop_difficulty_label = self._label(self.stop_view, (25, 125, 340, 32), "", ("<system-bold>", 17), color="#FFD166", alignment=ui.ALIGN_CENTER, flex="W")
        self._label(self.stop_view, (25, 165, 340, 45), "カウントダウン後、10秒でSTOP！", ("<system>", 16), color="#D9EAF7", alignment=ui.ALIGN_CENTER, number_of_lines=2, flex="W")
        self.countdown_label = self._label(self.stop_view, (20, 210, 350, 60), "", ("<system-bold>", 42), color="#FF6B6B", alignment=ui.ALIGN_CENTER, flex="W")
        self.time_label = self._label(self.stop_view, (20, 275, 350, 90), "0.00秒", ("<system-bold>", 56), alignment=ui.ALIGN_CENTER, flex="W")
        self.stop_result = self._label(self.stop_view, (25, 375, 340, 80), "ゲームスタートで開始！", ("<system-bold>", 19), color="#FFD166", alignment=ui.ALIGN_CENTER, number_of_lines=3, flex="W")
        self.start_button = self._button(self.stop_view, (35, 485, 145, 64), "START", self.start, "#2EBD85")
        self.stop_button = self._button(self.stop_view, (210, 485, 145, 64), "STOP", self.stop, "#EF8354")
        self.stop_button.enabled = False
        self._button(self.stop_view, (95, 590, 200, 42), "ホームに戻る", self.show_home, "#486581")
        self._button(self.stop_view, (95, 645, 200, 38), "カウント速度を変更", self.change_difficulty, "#486581")

    def _build_flag_quiz(self):
        self._label(self.flag_view, (20, 45, 350, 45), "国旗当てゲーム", ("<system-bold>", 27), alignment=ui.ALIGN_CENTER, flex="W")
        self.flag_score_label = self._label(self.flag_view, (25, 95, 340, 35), "", ("<system-bold>", 18), color="#FFD166", alignment=ui.ALIGN_CENTER, flex="W")
        self.flag_label = self._label(self.flag_view, (20, 155, 350, 125), "", ("<system-bold>", 88), alignment=ui.ALIGN_CENTER, flex="W")
        self.flag_message = self._label(self.flag_view, (25, 290, 340, 55), "この国旗はどこ？", ("<system-bold>", 20), color="#D9EAF7", alignment=ui.ALIGN_CENTER, flex="W")
        self.flag_buttons = []
        for index in range(4):
            self.flag_buttons.append(self._button(self.flag_view, (35, 365 + index * 58, 320, 46), "", lambda sender, i=index: self.answer_flag(i), "#486581"))
        self.flag_next_button = self._button(self.flag_view, (95, 625, 200, 42), "次の問題", self.next_flag_question, "#2EBD85")
        self.flag_next_button.enabled = False
        self._button(self.flag_view, (95, 680, 200, 42), "ホームに戻る", self.show_home, "#486581")

    def _build_riddle_quiz(self):
        self._label(self.riddle_view, (20, 45, 350, 45), "なぞなぞミッション", ("<system-bold>", 26), alignment=ui.ALIGN_CENTER, flex="W")
        self.riddle_score_label = self._label(self.riddle_view, (25, 95, 340, 35), "", ("<system-bold>", 18), color="#FFD166", alignment=ui.ALIGN_CENTER, flex="W")
        self.riddle_question = self._label(self.riddle_view, (25, 160, 340, 105), "", ("<system-bold>", 23), alignment=ui.ALIGN_CENTER, number_of_lines=4, flex="W")
        self.riddle_message = self._label(self.riddle_view, (25, 285, 340, 55), "答えを選んでね！", ("<system-bold>", 19), color="#D9EAF7", alignment=ui.ALIGN_CENTER, number_of_lines=2, flex="W")
        self.riddle_buttons = []
        for index in range(4):
            self.riddle_buttons.append(self._button(self.riddle_view, (35, 355 + index * 58, 320, 46), "", lambda sender, i=index: self.answer_riddle(i), "#486581"))
        self.riddle_next_button = self._button(self.riddle_view, (95, 625, 200, 42), "次の問題", self.next_riddle, "#2EBD85")
        self.riddle_next_button.enabled = False
        self._button(self.riddle_view, (95, 680, 200, 42), "ホームに戻る", self.show_home, "#486581")

    def show_home(self, sender=None):
        self.running = False
        self.counting_down = False
        for view in (self.home_view, self.stop_view, self.flag_view, self.riddle_view):
            view.hidden = True
        self.home_view.hidden = False

    def open_stop_game(self, sender):
        self.reset_stop_game(None)
        self.home_view.hidden = True
        self.stop_view.hidden = False

    def open_flag_quiz(self, sender):
        self.home_view.hidden = True
        self.flag_view.hidden = False
        self.flag_score = 0
        self.flag_question_number = 0
        self.next_flag_question(None)

    def open_riddle_quiz(self, sender):
        self.home_view.hidden = True
        self.riddle_view.hidden = False
        self.riddle_score = 0
        self.riddle_number = 0
        self.next_riddle(None)

    def _update_stop_text(self):
        self.round_label.text = "ラウンド {} / {}".format(self.round_number, TOTAL_ROUNDS)
        self.stop_difficulty_label.text = "カウント速度：{}　目標10秒".format(self.difficulty_name)

    def change_difficulty(self, sender):
        if not self.running and not self.counting_down:
            self.difficulty_index = (self.difficulty_index + 1) % len(DIFFICULTIES)
            self._update_stop_text()

    def start(self, sender):
        if self.running or self.counting_down:
            return
        if self.round_number > TOTAL_ROUNDS:
            self.reset_stop_game(None)
        self.counting_down = True
        self.start_button.enabled = False
        self.stop_button.enabled = False
        self._update_stop_text()
        self.stop_result.text = "準備してね！"
        self._countdown_tick(3)

    def _countdown_tick(self, number):
        if not self.counting_down:
            return
        if number > 0:
            self.countdown_label.text = str(number)
            ui.delay(lambda: self._countdown_tick(number - 1), self.countdown_speed)
            return
        self.countdown_label.text = "GO!"
        self.counting_down = False
        self.running = True
        self.started_at = time.monotonic()
        self.stop_button.enabled = True
        self.stop_result.text = "今だと思ったらSTOP！"
        ui.delay(self._clear_countdown, 0.5)
        self.tick()

    def _clear_countdown(self):
        if self.running:
            self.countdown_label.text = ""

    def tick(self):
        if not self.running or self.started_at is None:
            return
        self.time_label.text = "{:.2f}秒".format(time.monotonic() - self.started_at)
        ui.delay(self.tick, 0.05)

    def stop(self, sender):
        if not self.running or self.started_at is None:
            return
        elapsed = time.monotonic() - self.started_at
        self.running = False
        self.start_button.enabled = True
        self.stop_button.enabled = False
        error = abs(elapsed - TARGET_SECONDS)
        self.records.append(error)
        if len(self.records) < TOTAL_ROUNDS:
            self.round_number += 1
            self.stop_result.text = "{}回目：誤差 {:.2f}秒\n次はラウンド{}！".format(len(self.records), error, self.round_number)
            self.start_button.title = "次のラウンド"
        else:
            self.round_number = TOTAL_ROUNDS + 1
            self.stop_result.text = "3回終了！\n合計誤差 {:.2f}秒\nSTARTでもう一度".format(sum(self.records))
            self.start_button.title = "もう一度"
        self.time_label.text = "{:.2f}秒".format(elapsed)
        self._update_stop_text()

    def reset_stop_game(self, sender):
        self.running = False
        self.counting_down = False
        self.started_at = None
        self.round_number = 1
        self.records = []
        self.time_label.text = "0.00秒"
        self.countdown_label.text = ""
        self.stop_result.text = "ゲームスタートで開始！"
        self.start_button.title = "START"
        self.start_button.enabled = True
        self.stop_button.enabled = False
        self._update_stop_text()

    def _make_choices(self, answer, values, similar_groups=()):
        choices = {answer}
        while len(choices) < 4:
            candidate = random.choice(values)
            blocked = any(answer in group and candidate in group for group in similar_groups)
            if not blocked:
                choices.add(candidate)
        result = list(choices)
        random.shuffle(result)
        return result

    def next_flag_question(self, sender):
        self.flag_question_number += 1
        self.current_flag, self.current_answer = random.choice(FLAGS)
        names = [name for _, name in FLAGS]
        self.flag_choices = self._make_choices(self.current_answer, names, SIMILAR_FLAG_GROUPS)
        self.flag_label.text = self.current_flag
        self.flag_score_label.text = "正解 {}問　問題 {}".format(self.flag_score, self.flag_question_number)
        self.flag_message.text = "この国旗はどこ？"
        self.flag_message.text_color = "#D9EAF7"
        self.flag_next_button.enabled = False
        for index, button in enumerate(self.flag_buttons):
            button.title = self.flag_choices[index]
            button.enabled = True
            button.background_color = "#486581"

    def answer_flag(self, index):
        for button in self.flag_buttons:
            button.enabled = False
        answer = self.flag_choices[index]
        if answer == self.current_answer:
            self.flag_score += 1
            self.flag_message.text = "正解！"
            self.flag_message.text_color = "#7CFF6B"
            self.flag_buttons[index].background_color = "#2EBD85"
        else:
            self.flag_message.text = "残念！正解は {}".format(self.current_answer)
            self.flag_message.text_color = "#FF9B85"
            self.flag_buttons[index].background_color = "#EF8354"
            for button, choice in zip(self.flag_buttons, self.flag_choices):
                if choice == self.current_answer:
                    button.background_color = "#2EBD85"
        self.flag_score_label.text = "正解 {}問　問題 {}".format(self.flag_score, self.flag_question_number)
        self.flag_next_button.enabled = True

    def next_riddle(self, sender):
        self.riddle_number += 1
        if self.riddle_number > len(RIDDLES):
            self.riddle_number = 1
            self.riddle_score = 0
        question, answer, choices = RIDDLES[self.riddle_number - 1]
        self.current_riddle_answer = answer
        self.current_riddle_choices = list(choices)
        self.riddle_question.text = "ミッション {} / {}\n{}".format(self.riddle_number, len(RIDDLES), question)
        self.riddle_score_label.text = "正解 {}問".format(self.riddle_score)
        self.riddle_message.text = "答えを選んでね！"
        self.riddle_message.text_color = "#D9EAF7"
        self.riddle_next_button.enabled = False
        for index, button in enumerate(self.riddle_buttons):
            button.title = self.current_riddle_choices[index]
            button.enabled = True
            button.background_color = "#486581"

    def answer_riddle(self, index):
        for button in self.riddle_buttons:
            button.enabled = False
        answer = self.current_riddle_choices[index]
        if answer == self.current_riddle_answer:
            self.riddle_score += 1
            self.riddle_message.text = "正解！ミッションクリア！"
            self.riddle_message.text_color = "#7CFF6B"
            self.riddle_buttons[index].background_color = "#2EBD85"
        else:
            self.riddle_message.text = "残念！答えは {}".format(self.current_riddle_answer)
            self.riddle_message.text_color = "#FF9B85"
            self.riddle_buttons[index].background_color = "#EF8354"
            for button, choice in zip(self.riddle_buttons, self.current_riddle_choices):
                if choice == self.current_riddle_answer:
                    button.background_color = "#2EBD85"
        self.riddle_score_label.text = "正解 {}問".format(self.riddle_score)
        self.riddle_next_button.enabled = True


def run():
    TenSecondGame().present("fullscreen")


if __name__ == "__main__":
    run()
