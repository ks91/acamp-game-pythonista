"""Purple team local prototype: Tokyo Man escape game mock.

This file uses local GPS but no server connection or real-world chemicals.
It is a button-driven UI mock for testing the two-place -> attack loop.
"""

import math
import random
import ui
import location


START_SCORE = 10
START_BOSS_HP = 1000
ATTACK_COST = 50
ATTACK_DAMAGE = 50
START_LIVES = 3
GPS_RADIUS_M = 40.0
# 地点が決まったら、ここに緯度・経度を入れる。
# 例: {"latitude": 35.000000, "longitude": 139.000000}
FIXED_PLACES = [
    None,  # 地点1
    None,  # 地点2
]
# 以前に確認した現在地。地点1ではなく、確認用の地図ピン。
REFERENCE_LOCATION = {"latitude": 35.674652, "longitude": 139.693472}

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


MAP_HTML = r"""<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>html,body,#map{margin:0;width:100%;height:100%;}</style>
</head>
<body><div id="map"></div>
<script>
var map = L.map('map').setView([35.6812,139.7671], 16);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '© OpenStreetMap contributors', maxZoom: 19
}).addTo(map);
var currentMarker = null;
var placeMarkers = [];
var referenceMarker = null;
function updatePosition(lat, lon) {
  var point = [lat, lon];
  if (!currentMarker) {
    currentMarker = L.circleMarker(point, {radius:8, color:'#1565C0', fillColor:'#42A5F5', fillOpacity:1}).addTo(map);
    map.setView(point, 17);
  } else { currentMarker.setLatLng(point); }
}
function setPlace(index, lat, lon) {
  var point = [lat, lon];
  if (placeMarkers[index]) { placeMarkers[index].setLatLng(point); return; }
  placeMarkers[index] = L.marker(point).addTo(map).bindPopup('地点' + (index + 1));
}
function setReference(lat, lon) {
  var point = [lat, lon];
  if (referenceMarker) { referenceMarker.setLatLng(point); return; }
  referenceMarker = L.marker(point).addTo(map).bindPopup('以前の確認地点（地点1ではありません）');
}
</script>
</body></html>"""


class PurpleMockGame(ui.View):
    def __init__(self):
        screen_width, screen_height = ui.get_screen_size()
        super().__init__(frame=(0, 0, screen_width, screen_height))
        self.name = "東京マン腸脱出ゲーム"
        self.background_color = "#FFF8E1"
        self.score = START_SCORE
        self.boss_hp = START_BOSS_HP
        self.lives = START_LIVES
        self.arrived = [False, False]
        self.solved = [False, False]
        self.used_question_indexes = set()
        self.feedback_label = None
        self.current_location = None
        self.place_locations = [dict(place) if place else None for place in FIXED_PLACES]
        self._build_ui()
        self._read_current_location()
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
        panel_width = width * 0.5
        map_x = panel_width
        map_width = width - panel_width
        self._label("東京マン腸脱出ゲーム", (6, 8, panel_width - 12, 28), ("<system-bold>", 16), align=ui.ALIGN_CENTER)
        self.mock_label = self._label("仮動作：GPSあり\nサーバー通信なし", (6, 38, panel_width - 12, 32), ("<system-bold>", 10), "#D84315", ui.ALIGN_CENTER)
        self.status_label = self._label("", (6, 74, panel_width - 12, 52), ("<system-bold>", 12), align=ui.ALIGN_CENTER)

        self.map_view = ui.WebView(frame=(map_x, 0, map_width, self.height))
        self.map_view.load_url("https://www.google.com/maps/@35.674652,139.693472,17z")
        self.add_subview(self.map_view)

        self.gps_button = self._button("GPS更新", (6, 132, panel_width - 12, 30), self._update_location, "#455A64")
        self.gps_button.font = ("<system-bold>", 11)
        self.set_place_buttons = []
        for index, y in enumerate((166, 200)):
            button = self._button(
                "地点{}をここに".format(index + 1),
                (6, y, panel_width - 12, 30),
                lambda sender, i=index: self._set_place_here(i),
                "#37474F",
            )
            button.font = ("<system-bold>", 10)
            self.set_place_buttons.append(button)

        self.place_buttons = []
        self.solve_buttons = []
        for index, y in enumerate((244, 326)):
            number = index + 1
            self._label("小腸の地点{}".format(number), (6, y, panel_width - 12, 22), ("<system-bold>", 13), align=ui.ALIGN_CENTER)
            arrive = self._button("地点{} GPS到着".format(number), (6, y + 24, panel_width - 12, 30), lambda sender, i=index: self._check_arrival(i), "#000000")
            solve = self._button("謎{}を解く +10pt".format(number), (6, y + 58, panel_width - 12, 30), lambda sender, i=index: self._solve(i), "#6A1B9A")
            arrive.font = ("<system-bold>", 10)
            solve.font = ("<system-bold>", 10)
            self.place_buttons.append(arrive)
            self.solve_buttons.append(solve)

        self.attack_button = self._button("殴る 50pt", (6, 410, panel_width - 12, 34), self._attack, "#C62828")
        self.attack_button.font = ("<system-bold>", 11)
        self.reset_button = self._button("リセット", (6, 450, panel_width - 12, 30), self._reset, "#546E7A")
        self.reset_button.font = ("<system-bold>", 11)
        self.log_label = self._label("", (6, 486, panel_width - 12, 120), ("<system>", 11), "#455A64", ui.ALIGN_CENTER)

    def _hide_feedback(self):
        if self.feedback_label is not None:
            self.feedback_label.remove_from_superview()
            self.feedback_label = None

    def _show_feedback(self, text, color, seconds):
        self._hide_feedback()
        label = ui.Label(frame=(18, 225, self.width - 36, 160))
        label.text = text
        label.font = ("<system-bold>", 30)
        label.text_color = color
        label.background_color = "#FFFFFF"
        label.alignment = ui.ALIGN_CENTER
        label.number_of_lines = 0
        label.corner_radius = 16
        self.add_subview(label)
        self.feedback_label = label
        ui.delay(self._hide_feedback, seconds)

    def _refresh(self, message=""):
        self.status_label.text = "ポイント: {}pt    東京マン体力: {}/{}\n残機: {}".format(self.score, self.boss_hp, START_BOSS_HP, self.lives)
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

    def _load_google_map(self):
        location_point = self.current_location or REFERENCE_LOCATION
        url = "https://www.google.com/maps/@{},{},17z".format(
            location_point["latitude"], location_point["longitude"]
        )
        try:
            self.map_view.load_url(url)
        except Exception:
            pass

    def _draw_current_marker(self):
        if self.current_location is None:
            return
        try:
            self.map_view.eval_js(
                "updatePosition({},{})".format(
                    self.current_location["latitude"],
                    self.current_location["longitude"],
                )
            )
        except Exception:
            pass

    def _draw_reference_marker(self):
        try:
            self.map_view.eval_js(
                "setReference({},{})".format(
                    REFERENCE_LOCATION["latitude"],
                    REFERENCE_LOCATION["longitude"],
                )
            )
        except Exception:
            pass

    def _draw_place_markers(self):
        for index, place in enumerate(self.place_locations):
            if place is not None:
                try:
                    self.map_view.eval_js(
                        "setPlace({},{},{})".format(index, place["latitude"], place["longitude"])
                    )
                except Exception:
                    pass

    def _read_current_location(self):
        self._refresh("GPSを取得しています…")
        location.start_updates()
        try:
            current = location.get_location()
        finally:
            location.stop_updates()
        if not current:
            self._refresh("GPSを取得できません。位置情報の許可を確認してください。")
            return None
        self.current_location = {
            "latitude": float(current["latitude"]),
            "longitude": float(current["longitude"]),
            "accuracy": float(current.get("horizontal_accuracy", 0.0)),
        }
        try:
            self.map_view.eval_js(
                "updatePosition({},{})".format(
                    self.current_location["latitude"],
                    self.current_location["longitude"],
                )
            )
        except Exception:
            pass
        ui.delay(self._load_google_map, 0.2)
        return self.current_location

    def _distance_m(self, first, second):
        earth_radius_m = 6371000.0
        lat1 = math.radians(first["latitude"])
        lat2 = math.radians(second["latitude"])
        dlat = lat2 - lat1
        dlon = math.radians(second["longitude"] - first["longitude"])
        value = (math.sin(dlat / 2) ** 2
                 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2)
        return 2 * earth_radius_m * math.asin(math.sqrt(value))

    def _set_place_here(self, index):
        if self.place_locations[index] is not None:
            self._refresh("地点{}はすでに共通設定されています。変更できません。".format(index + 1))
            return
        current = self._read_current_location()
        if current is None:
            return
        self.place_locations[index] = dict(current)
        try:
            self.map_view.eval_js(
                "setPlace({},{},{})".format(
                    index,
                    current["latitude"],
                    current["longitude"],
                )
            )
        except Exception:
            pass
        self._refresh("地点{}を仮設定しました。確定後はFIXED_PLACESに埋め込みます。".format(index + 1))

    def _update_location(self, sender):
        current = self._read_current_location()
        if current is None:
            return
        next_index = 0 if not self.arrived[0] else 1
        target = self.place_locations[next_index]
        if target is None:
            self._refresh("現在地を更新しました。先に地点{}をここに設定してください。".format(next_index + 1))
            return
        distance = self._distance_m(current, target)
        if distance <= GPS_RADIUS_M:
            self._arrive(next_index, distance)
        else:
            self._refresh("現在地を更新しました。地点{}まで約{:.0f}mです。".format(next_index + 1, distance))

    def _check_arrival(self, index):
        if index > 0 and not self.arrived[index - 1]:
            self._refresh("先に地点{}へ到着してください。".format(index))
            return
        target = self.place_locations[index]
        if target is None:
            self._refresh("先に「地点{}をここに」を押してください。".format(index + 1))
            return
        current = self._read_current_location()
        if current is None:
            return
        distance = self._distance_m(current, target)
        if distance <= GPS_RADIUS_M:
            self._arrive(index, distance)
        else:
            self._refresh("まだ地点{}の範囲外です。約{:.0f}m離れています。".format(index + 1, distance))

    def _arrive(self, index, distance_m):
        if distance_m > GPS_RADIUS_M:
            self._refresh("地点{}は範囲外です。約{:.0f}m離れています。".format(index + 1, distance_m))
            return
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

        available_indexes = [
            index for index in range(len(QUESTIONS))
            if index not in self.used_question_indexes
        ]
        if not available_indexes:
            self.used_question_indexes.clear()
            available_indexes = list(range(len(QUESTIONS)))
        question_index = random.choice(available_indexes)
        self.used_question_indexes.add(question_index)
        question = QUESTIONS[question_index]
        try:
            selected = dialogs.list_dialog(question["question"], question["choices"])
        except KeyboardInterrupt:
            selected = None
        if selected is None:
            self._refresh("謎解きをキャンセルしました。もう一度挑戦できます。")
            return
        if selected != question["answer"]:
            self.lives -= 1
            if self.lives <= 0:
                self._refresh("3回間違えました。最初からやり直します。")
                self._show_feedback("最初から\nやり直し", "#C62828", 3)
                ui.delay(lambda: self._reset(None), 3)
                return
            if self.lives == 1:
                self._refresh("不正解。残機1。あと1回間違えたら最初からです。")
                self._show_feedback("あと1回間違えたら\n最初からだよ", "#C62828", 3)
            else:
                self._refresh("不正解。正解は「{}」。残機{}。".format(question["answer"], self.lives))
                self._show_feedback("不正解", "#C62828", 2)
            return
        self.solved[index] = True
        self.score += 10
        self._refresh("正解！ 謎{}を解いた！ +10pt".format(index + 1))
        self._show_feedback("正解！\n+10pt", "#2E7D32", 2)

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

    def _reset(self, sender=None):
        self._hide_feedback()
        self.score = START_SCORE
        self.boss_hp = START_BOSS_HP
        self.lives = START_LIVES
        self.arrived = [False, False]
        self.solved = [False, False]
        self.used_question_indexes.clear()
        self._refresh("仮試作をリセットしました。")


def run():
    PurpleMockGame().present("fullscreen")


if __name__ == "__main__":
    run()
