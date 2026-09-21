"""Purple team's Tokyo Man game using the gallery-selected server scenario."""

import math
import os
import random
import threading
import ui
import location

from toolkit.api_client import ApiClient
from toolkit.claim_flow import claim_with_location
from toolkit.game_progress import make_progress_store, progress_warning

APP_DIR = os.path.dirname(
    globals().get("__file__", os.path.join(os.getcwd(), "team_apps", "purple", "app.py"))
)

try:
    import config
except ImportError:
    # The shared repository intentionally does not contain each iPad's config.py.
    config = None


START_SCORE = 10
START_BOSS_HP = 100
GOOD_BACTERIA_HP = 50
ARRIVAL_REWARD_POINTS = 20
GOOD_BACTERIA_REWARD_POINTS = 60
ATTACK_COST = 50
ATTACK_DAMAGE = 50
START_LIVES = 3
GPS_RADIUS_M = 40.0
SERVER_PLACE_COUNT = 2
CHEST_REWARD_POINTS = 10
CHEST_LOCATION_CHANCE = 0.0
CHEST_RIDDLE_CHANCE = 1.0
ITEM_COSTS = {
    "液体窒素＆硫酸": 50,
    "亜硝酸ナトリウム爆弾": 20,
}
ITEM_DAMAGE = {
    "液体窒素＆硫酸": 50,
    "亜硝酸ナトリウム爆弾": 50,
}
ITEM_IMAGES = {
    "液体窒素＆硫酸": "liquid_nitrogen.jpeg",
    "亜硝酸ナトリウム爆弾": "sodium_nitrite_bomb.jpeg",
}
CHEST_REWARDS = [
    "亜硝酸ナトリウム爆弾",  # 地点1
    "液体窒素＆硫酸",        # 地点2
]
CHEST_IMAGE = "treasure_chest.jpeg"


def dms_to_decimal(degrees, minutes, seconds, direction):
    value = degrees + minutes / 60.0 + seconds / 3600.0
    return -value if direction in ("S", "W") else value


def make_api_client():
    """Use the team and mode selected by the shared game gallery."""
    if config is None:
        return None
    base_url = getattr(config, "API_BASE_URL", "")
    token = getattr(config, "GAME_TOKEN", "")
    if not base_url or not token or token == "set-at-game-start":
        return None
    return ApiClient(
        base_url=base_url,
        token=token,
        game_team_id=getattr(config, "SELECTED_GAME_TEAM_ID", None),
        game_mode=getattr(config, "SELECTED_GAME_MODE", None),
    )

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
var map = L.map('map').setView([0.0,0.0], 16);
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


GOOGLE_MAP_HTML = r"""<!doctype html>
<html><head>
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<style>html,body,#map{margin:0;width:100%;height:100%;}</style>
<script>
var map, currentMarker, placeMarkers = [];
function initMap() {
  map = new google.maps.Map(document.getElementById('map'), {
    center: {lat: 0.0, lng: 0.0}, zoom: 17,
    streetViewControl: false, fullscreenControl: false, mapTypeControl: false
  });
}
function fitAll() {
  if (!map) return;
  var bounds = new google.maps.LatLngBounds();
  var hasPoint = false;
  if (currentMarker) { bounds.extend(currentMarker.getPosition()); hasPoint = true; }
  placeMarkers.forEach(function(marker) {
    if (marker) { bounds.extend(marker.getPosition()); hasPoint = true; }
  });
  if (hasPoint) map.fitBounds(bounds, 45);
}
function updatePosition(lat, lon) {
  if (!map) return;
  var point = {lat: lat, lng: lon};
  if (!currentMarker) {
    currentMarker = new google.maps.Marker({position: point, map: map, label: '●', title: '現在地'});
  } else { currentMarker.setPosition(point); }
  fitAll();
}
function setPlace(index, lat, lon) {
  if (!map) return;
  var point = {lat: lat, lng: lon};
  if (!placeMarkers[index]) {
    placeMarkers[index] = new google.maps.Marker({position: point, map: map, label: '旗', title: '地点' + (index + 1)});
  } else { placeMarkers[index].setPosition(point); }
  fitAll();
}
</script>
<script src="https://maps.googleapis.com/maps/api/js?key=__API_KEY__&callback=initMap" async defer></script>
</head><body><div id="map"></div></body></html>"""


class PurpleMockGame(ui.View):
    def __init__(self):
        screen_width, screen_height = ui.get_screen_size()
        super().__init__(frame=(0, 0, screen_width, screen_height))
        self.name = "東京マン腸脱出ゲーム"
        self.background_color = "#FFF8E1"
        self.score = START_SCORE
        self.boss_hp = START_BOSS_HP
        self.boss_defeat_transition = False
        self.lives = START_LIVES
        self.arrived = [False, False]
        self.solved = [False, False]
        self.used_question_indexes = set()
        self.feedback_label = None
        self.current_location = None
        self.place_locations = [None] * SERVER_PLACE_COUNT
        self.api = make_api_client()
        self.definition = None
        self.quiz_overlay = None
        self.quiz_active = False
        self.quiz_index = None
        self.quiz_question = None
        self.quiz_remaining = 0
        self._quiz_generation = 0
        self._round_generation = 0
        self._arriving = False
        self.checkpoint_state = None
        self.chest_arrival_checked = [False, False]
        self.chest_riddle_checked = [False, False]
        self.chest_items = [None, None]
        self.item_inventory = {item: 0 for item in ITEM_COSTS}
        self.item_popup = None
        self.good_bacteria_popup = None
        self.good_bacteria_visible = False
        self.good_bacteria_hp = GOOD_BACTERIA_HP
        self._progress = make_progress_store(self, config, "purple")
        self._build_ui()
        self._load_server_places()
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
        left_width = width * 0.25
        character_width = width * 0.25
        map_x = left_width + character_width
        map_width = width - map_x
        panel_width = left_width
        self._label("東京マン腸脱出ゲーム", (6, 8, panel_width - 12, 28), ("<system-bold>", 16), align=ui.ALIGN_CENTER)
        self.mock_label = self._label("ギャラリー選択の\nサーバー地点を読込中", (6, 38, panel_width - 12, 32), ("<system-bold>", 10), "#D84315", ui.ALIGN_CENTER)
        self.status_label = self._label("", (6, 74, panel_width - 12, 52), ("<system-bold>", 12), align=ui.ALIGN_CENTER)

        self.character_panel = ui.View(frame=(left_width, 0, character_width, self.height))
        self.character_panel.background_color = "#F3F0F4"
        self.add_subview(self.character_panel)
        self.character_health_label = ui.Label(frame=(8, 8, character_width - 16, 38))
        self.character_health_label.text = "東京マン体力\n{}/{}".format(self.boss_hp, START_BOSS_HP)
        self.character_health_label.font = ("<system-bold>", 15)
        self.character_health_label.text_color = "white"
        self.character_health_label.background_color = "#45205C"
        self.character_health_label.alignment = ui.ALIGN_CENTER
        self.character_health_label.number_of_lines = 0
        self.character_panel.add_subview(self.character_health_label)
        self.character_image = ui.ImageView(frame=(8, 54, character_width - 16, self.height - 62))
        self.character_image.content_mode = ui.CONTENT_SCALE_ASPECT_FIT
        self.character_panel.add_subview(self.character_image)
        self._update_tokyoman_art()

        self.map_view = ui.WebView(frame=(map_x, 0, map_width, self.height))
        self.maps_key = getattr(config, "GOOGLE_MAPS_API_KEY", "")
        if self.maps_key and self.maps_key != "set-at-game-start":
            self.map_view.load_html(GOOGLE_MAP_HTML.replace("__API_KEY__", self.maps_key))
        else:
            self.map_view.load_url("https://www.google.com/maps/@0.0,0.0,17z")
        self.add_subview(self.map_view)

        self.gps_button = self._button("GPS更新", (6, 132, panel_width - 12, 30), self._update_location, "#455A64")
        self.gps_button.font = ("<system-bold>", 11)

        self.place_buttons = []
        self.solve_buttons = []
        for index, y in enumerate((244, 326)):
            number = index + 1
            self._label("小腸の地点{}".format(number), (6, y, panel_width - 12, 22), ("<system-bold>", 13), align=ui.ALIGN_CENTER)
            arrive = self._button("地点{} GPS到着".format(number), (6, y + 24, panel_width - 12, 30), lambda sender, i=index: self._check_arrival(i), "#000000")
            solve = self._button("謎{}を解く +20pt".format(number), (6, y + 58, panel_width - 12, 30), lambda sender, i=index: self._solve(i), "#6A1B9A")
            arrive.font = ("<system-bold>", 10)
            solve.font = ("<system-bold>", 10)
            self.place_buttons.append(arrive)
            self.solve_buttons.append(solve)

        self.attack_button = self._button("殴る 50pt", (6, 410, panel_width - 12, 34), self._attack, "#C62828")
        self.attack_button.font = ("<system-bold>", 11)
        self.reset_button = self._button("リセット", (6, 450, panel_width - 12, 30), self._reset, "#546E7A")
        self.reset_button.font = ("<system-bold>", 11)
        self._label("攻撃アイテム", (6, 486, panel_width - 12, 22), ("<system-bold>", 12), align=ui.ALIGN_CENTER)
        self.item_buttons = []
        for item_index, item_name in enumerate(ITEM_COSTS):
            button = self._button(
                item_name,
                (6, 512 + item_index * 36, panel_width - 12, 30),
                self._buy_item,
                "#6A1B9A",
            )
            button.item_name = item_name
            button.font = ("<system-bold>", 9)
            self.item_buttons.append(button)
        self.log_label = self._label("", (6, 596, panel_width - 12, max(60, self.height - 606)), ("<system>", 10), "#455A64", ui.ALIGN_CENTER)

    def _hide_feedback(self):
        if self.feedback_label is not None:
            self.remove_subview(self.feedback_label)
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

    def _update_tokyoman_art(self):
        if self.good_bacteria_visible:
            if self.good_bacteria_hp <= 0:
                self.character_image.image = None
            else:
                filename = "zen_dama.jpeg"
                path = os.path.join(APP_DIR, "assets", filename)
                try:
                    with open(path, "rb") as source:
                        self.character_image.image = ui.Image.from_data(source.read())
                except OSError:
                    self.character_image.image = None
            self.character_health_label.text = "善玉くん体力\n{}/{}".format(self.good_bacteria_hp, GOOD_BACTERIA_HP)
            return
        if self.boss_hp <= 0 and not self.boss_defeat_transition:
            filename = "tokyoman_defeated.jpeg"
        elif self.boss_hp <= START_BOSS_HP / 2 or self.boss_defeat_transition:
            filename = "tokyoman_half.jpeg"
        else:
            filename = "tokyoman_full.jpeg"
        path = os.path.join(APP_DIR, "assets", filename)
        try:
            with open(path, "rb") as source:
                self.character_image.image = ui.Image.from_data(source.read())
        except OSError:
            self.character_image.image = None
        self.character_health_label.text = "東京マン体力\n{}/{}".format(self.boss_hp, START_BOSS_HP)

    def _show_good_bacteria_arrival(self):
        if self.good_bacteria_popup is not None:
            self.remove_subview(self.good_bacteria_popup)
        popup = ui.View(frame=(self.width * 0.25, 70, self.width * 0.5, min(430, self.height - 100)))
        popup.background_color = "#E8F5E9"
        popup.corner_radius = 18
        image = ui.ImageView(frame=(20, 20, popup.width - 40, popup.height - 105))
        image.content_mode = ui.CONTENT_SCALE_ASPECT_FIT
        path = os.path.join(APP_DIR, "assets", "zen_dama.jpeg")
        try:
            with open(path, "rb") as source:
                image.image = ui.Image.from_data(source.read())
        except OSError:
            image.image = None
        popup.add_subview(image)
        caption = ui.Label(frame=(12, popup.height - 78, popup.width - 24, 58))
        caption.text = "善玉くんが現れた！"
        caption.font = ("<system-bold>", 24)
        caption.text_color = "#2E7D32"
        caption.alignment = ui.ALIGN_CENTER
        popup.add_subview(caption)
        self.add_subview(popup)
        self.good_bacteria_popup = popup
        ui.delay(self._hide_good_bacteria_arrival, 3.0)

    def _hide_good_bacteria_arrival(self):
        if self.good_bacteria_popup is not None:
            self.remove_subview(self.good_bacteria_popup)
            self.good_bacteria_popup = None

    def _refresh(self, message=""):
        self._update_tokyoman_art()
        self.status_label.text = "ポイント: {}pt    東京マン体力: {}/{}\n残機: {}".format(self.score, self.boss_hp, START_BOSS_HP, self.lives)
        for index in range(2):
            previous_arrived = index == 0 or self.arrived[index - 1]
            can_arrive = previous_arrived and not self.arrived[index] and not self._arriving
            self.place_buttons[index].enabled = can_arrive
            self.place_buttons[index].alpha = 1.0 if can_arrive else 0.45
            can_solve = self.arrived[index] and not self.solved[index] and not self._arriving
            self.solve_buttons[index].enabled = can_solve
            self.solve_buttons[index].alpha = 1.0 if can_solve else 0.45
        can_attack = (self.good_bacteria_visible and self.good_bacteria_hp > 0) or (not self.good_bacteria_visible and self.score >= ATTACK_COST and self.boss_hp > 0)
        self.attack_button.title = "善玉くんを殴る 50pt" if self.good_bacteria_visible else "殴る 50pt"
        self.attack_button.enabled = can_attack and not self._arriving
        self.attack_button.alpha = 1.0 if self.attack_button.enabled else 0.45
        for button in self.item_buttons:
            item_name = button.item_name
            offered = item_name in self.chest_items
            owned = self.item_inventory[item_name]
            button.hidden = not offered and not owned
            button.title = "{} {}pt".format(item_name, ITEM_COSTS[item_name]) if offered else ""
            if owned:
                button.title = "{} ×{}".format(item_name, owned)
            button.enabled = (offered or owned > 0) and self.boss_hp > 0 and not self._arriving
            button.alpha = 1.0 if button.enabled else 0.35
        self.log_label.text = (message or "地点へ進み、謎を解いて攻撃ポイントを集めよう。") + progress_warning(self)

    def _save_progress(self, reset=False):
        if getattr(self, "_progress", None):
            self._progress.save(self, reset=reset)

    def _maybe_spawn_chest(self, index, chance, source):
        if source == "riddle":
            if self.chest_riddle_checked[index]:
                return ""
            self.chest_riddle_checked[index] = True
            item_name = CHEST_REWARDS[index]
            self.chest_items[index] = item_name
            self.score += CHEST_REWARD_POINTS
            self._save_progress()
            self._show_chest_found(item_name)
            return "宝箱が開いた！ {}を入手。 +{}pt".format(item_name, CHEST_REWARD_POINTS)
        if self.chest_items[index] is not None:
            return ""
        if source == "location":
            if self.chest_arrival_checked[index]:
                return ""
            self.chest_arrival_checked[index] = True
        if random.random() >= chance:
            return ""
        item_name = CHEST_REWARDS[index]
        self.chest_items[index] = item_name
        self._save_progress()
        self._show_chest_found(item_name)
        return "宝箱が出た！ {}".format(item_name)

    def _show_chest_found(self, item_name):
        if self.item_popup is not None:
            self.remove_subview(self.item_popup)
        popup = ui.View(frame=(self.width * 0.25, 70, self.width * 0.5, min(430, self.height - 100)))
        popup.background_color = "#FFF8E1"
        popup.corner_radius = 18
        popup.alpha = 0.0
        image = ui.ImageView(frame=(20, 20, popup.width - 40, popup.height - 105))
        image.content_mode = ui.CONTENT_SCALE_ASPECT_FIT
        path = os.path.join(APP_DIR, "assets", CHEST_IMAGE)
        try:
            with open(path, "rb") as source:
                image.image = ui.Image.from_data(source.read())
        except Exception:
            image.image = None
        popup.add_subview(image)
        if image.image is None:
            fallback = ui.Label(frame=(20, 70, popup.width - 40, 140))
            fallback.text = "宝箱"
            fallback.font = ("<system-bold>", 42)
            fallback.text_color = "#E65100"
            fallback.alignment = ui.ALIGN_CENTER
            popup.add_subview(fallback)
        caption = ui.Label(frame=(12, popup.height - 78, popup.width - 24, 58))
        caption.text = "宝箱を発見！"
        caption.font = ("<system-bold>", 26)
        caption.text_color = "#E65100"
        caption.alignment = ui.ALIGN_CENTER
        popup.add_subview(caption)
        self.add_subview(popup)
        self.item_popup = popup
        ui.animate(lambda: self._open_chest_animation(popup), duration=0.45)
        ui.delay(lambda: self._show_item_get(item_name), 1.4)

    def _open_chest_animation(self, popup):
        if self.item_popup is popup:
            popup.alpha = 1.0

    def _show_item_get(self, item_name):
        if self.item_popup is not None:
            self.remove_subview(self.item_popup)
        popup = ui.View(frame=(self.width * 0.25, 70, self.width * 0.5, min(430, self.height - 100)))
        popup.background_color = "#FFFFFF"
        popup.corner_radius = 18
        image = ui.ImageView(frame=(20, 20, popup.width - 40, popup.height - 105))
        image.content_mode = ui.CONTENT_SCALE_ASPECT_FIT
        path = os.path.join(APP_DIR, "assets", ITEM_IMAGES[item_name])
        try:
            with open(path, "rb") as source:
                image.image = ui.Image.from_data(source.read())
        except OSError:
            image.image = None
        popup.add_subview(image)
        caption = ui.Label(frame=(12, popup.height - 78, popup.width - 24, 58))
        caption.text = "{}をゲット！".format(item_name)
        caption.font = ("<system-bold>", 22)
        caption.text_color = "#6A1B9A"
        caption.alignment = ui.ALIGN_CENTER
        caption.number_of_lines = 0
        popup.add_subview(caption)
        self.add_subview(popup)
        self.item_popup = popup
        ui.delay(self._hide_item_get, 2.0)

    def _hide_item_get(self):
        if self.item_popup is not None:
            self.remove_subview(self.item_popup)
            self.item_popup = None

    def _buy_item(self, sender):
        if self._arriving:
            return
        item_name = sender.item_name
        if not isinstance(item_name, str) or item_name not in self.chest_items:
            return
        cost = ITEM_COSTS[item_name]
        if self.score < cost:
            self._refresh("ptが足りません。{}pt必要です。".format(cost))
            return
        self.score -= cost
        damage = ITEM_DAMAGE[item_name]
        self.boss_hp = max(0, self.boss_hp - damage)
        for index, offered_item in enumerate(self.chest_items):
            if offered_item == item_name:
                self.chest_items[index] = None
                break
        self._save_progress()
        self._refresh("{}を使った！ 東京マンに{}ダメージ。".format(item_name, damage))

    def _load_google_map(self):
        if not self.maps_key or self.maps_key == "set-at-game-start":
            target = next((place for place in self.place_locations if place is not None), self.current_location)
            if target is not None:
                url = "https://www.google.com/maps/search/?api=1&query={},{}".format(
                    target["latitude"], target["longitude"]
                )
                try:
                    self.map_view.load_url(url)
                except Exception:
                    pass
            return
        try:
            if self.current_location is not None:
                self.map_view.eval_js(
                    "updatePosition({},{})".format(
                        self.current_location["latitude"],
                        self.current_location["longitude"],
                    )
                )
            self._draw_place_markers()
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

    def _draw_place_markers(self):
        for index, place in enumerate(self.place_locations):
            if place is not None:
                try:
                    self.map_view.eval_js(
                        "setPlace({},{},{})".format(index, place["latitude"], place["longitude"])
                    )
                except Exception:
                    pass

    def _load_server_places(self):
        """Load scenario places from the server selected by the game gallery."""
        if self.api is None:
            self.mock_label.text = "サーバー設定待ち\nギャラリーから起動してください"
            self._refresh("ゲームサーバーの設定がありません。ギャラリーからゲームを選択してください。")
            return
        try:
            definition = self.api.get_game_definition()
            places = definition.get("places", [])
            if len(places) < SERVER_PLACE_COUNT:
                raise ValueError("このシナリオの地点が不足しています")
            normalized = []
            for place in places[:SERVER_PLACE_COUNT]:
                if not place.get("id") or place.get("latitude") is None or place.get("longitude") is None:
                    raise ValueError("サーバー地点の情報が不完全です")
                normalized.append({
                    "id": place["id"],
                    "name": place.get("name", "地点"),
                    "latitude": float(place["latitude"]),
                    "longitude": float(place["longitude"]),
                    "radius_m": float(place.get("radius_m", place.get("radius_meters", GPS_RADIUS_M))),
                })
        except Exception as error:
            self.mock_label.text = "サーバー地点を\n取得できません"
            self._refresh("サーバーのシナリオを取得できません。{}".format(error))
            return
        self.definition = definition
        if self._progress:
            self._progress.bind_session(self, definition.get("game_session_id"))
        self.place_locations = normalized
        self.mock_label.text = "サーバーシナリオ\n{}".format(definition.get("name", "読込済み"))
        self._draw_place_markers()
        self._load_google_map()

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
            "horizontal_accuracy": float(current.get("horizontal_accuracy", -1.0)),
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

    def _update_location(self, sender):
        current = self._read_current_location()
        if current is None:
            return
        next_index = 0 if not self.arrived[0] else 1
        target = self.place_locations[next_index]
        if target is None:
            self._refresh("サーバーの地点を読み込めていません。ギャラリーから選び直してください。")
            return
        distance = self._distance_m(current, target)
        if distance <= target["radius_m"]:
            self._arrive(next_index, distance)
        else:
            message = "現在地を更新しました。\n登録地点「{}」まであと約{:.0f}mです。".format(target["name"], distance)
            self._refresh(message)
            self._show_feedback("登録地点まで\nあと約{:.0f}m".format(distance), "#1565C0", 3)

    def _check_arrival(self, index):
        if index > 0 and not self.arrived[index - 1]:
            self._refresh("先に地点{}へ到着してください。".format(index))
            return
        target = self.place_locations[index]
        if target is None:
            self._refresh("サーバーの地点を読み込めていません。")
            return
        current = self._read_current_location()
        if current is None:
            return
        distance = self._distance_m(current, target)
        if distance <= target["radius_m"]:
            self._arrive(index, distance)
        else:
            message = "登録地点「{}」まであと約{:.0f}mです。".format(target["name"], distance)
            self._refresh(message)
            self._show_feedback("登録地点まで\nあと約{:.0f}m".format(distance), "#1565C0", 3)

    def _arrive(self, index, distance_m):
        if self._arriving:
            return
        target = self.place_locations[index]
        if target is None or distance_m > target["radius_m"]:
            self._refresh("地点{}はサーバー指定の範囲外です。".format(index + 1))
            return
        if index > 0 and not self.arrived[index - 1]:
            self._refresh("先に地点{}へ到着してください。".format(index))
            return
        if self.arrived[index]:
            return
        session_id = getattr(config, "GAME_SESSION_ID", "") if config else ""
        device_id = getattr(config, "DEVICE_ID", "") if config else ""
        if self.api is None or not session_id or not device_id:
            self._refresh("サーバー設定がないため地点を獲得できません。")
            return
        self._arriving = True
        generation = self._round_generation
        position = dict(self.current_location) if self.current_location else None
        self._refresh("現在地と地点到着をサーバーへ送っています…")
        def send():
            result = error = None
            try:
                result = claim_with_location(
                    self.api, team_id=config.TEAM_ID, device_id=device_id,
                    game_session_id=session_id, place_id=target["id"], position=position,
                )
            except Exception as exc:
                error = exc
            ui.delay(lambda: self._finish_arrival(index, target, generation, result, error), 0)
        threading.Thread(target=send, daemon=True).start()

    def _finish_arrival(self, index, target, generation, result, error):
        if generation != self._round_generation:
            return
        self._arriving = False
        if error is not None:
            self._refresh("地点の獲得をサーバーへ送れませんでした。{}".format(error))
            return
        self.arrived[index] = True
        if "team_score" in result:
            self.score = result["team_score"]
        if index == 1:
            self.good_bacteria_visible = True
            self.good_bacteria_hp = GOOD_BACTERIA_HP
        self._save_progress()
        if index == 1:
            self._show_good_bacteria_arrival()
        chest_message = self._maybe_spawn_chest(index, CHEST_LOCATION_CHANCE, "location")
        message = "{}を{}。登録地点まであと0mです。".format(target["name"], "獲得" if result.get("claimed") else "確認")
        if chest_message:
            message += "\n" + chest_message
        self._refresh(message)

    def _solve(self, index):
        if self._arriving or not self.arrived[index] or self.solved[index] or self.quiz_active:
            return
        available_indexes = [
            question_index for question_index in range(len(QUESTIONS))
            if question_index not in self.used_question_indexes
        ]
        if not available_indexes:
            self.used_question_indexes.clear()
            available_indexes = list(range(len(QUESTIONS)))
        question_index = random.choice(available_indexes)
        self.used_question_indexes.add(question_index)
        self._start_quiz(index, question_index)

    def _start_quiz(self, index, question_index):
        self._quiz_generation += 1
        question = QUESTIONS[question_index]
        self.quiz_index = index
        self.quiz_question = question
        self.quiz_remaining = 30
        self.quiz_active = True
        overlay = ui.View(frame=(10, 20, self.width - 20, self.height - 40))
        overlay.background_color = "#FFFFFF"
        overlay.corner_radius = 18
        self.add_subview(overlay)
        self.quiz_overlay = overlay

        title = ui.Label(frame=(18, 16, overlay.width - 36, 36))
        title.text = "謎{}（30秒）".format(index + 1)
        title.font = ("<system-bold>", 24)
        title.text_color = "#263238"
        title.alignment = ui.ALIGN_CENTER
        overlay.add_subview(title)

        timer = ui.Label(frame=(18, 56, overlay.width - 36, 46))
        timer.font = ("<system-bold>", 34)
        timer.text_color = "#C62828"
        timer.alignment = ui.ALIGN_CENTER
        timer.name = "quiz_timer"
        overlay.add_subview(timer)

        question_label = ui.Label(frame=(18, 112, overlay.width - 36, 110))
        question_label.text = question["question"]
        question_label.font = ("<system-bold>", 18)
        question_label.text_color = "#263238"
        question_label.alignment = ui.ALIGN_CENTER
        question_label.number_of_lines = 0
        overlay.add_subview(question_label)

        for choice_index, choice in enumerate(question["choices"]):
            button = ui.Button(frame=(28, 238 + choice_index * 58, overlay.width - 56, 46))
            button.title = choice
            button.font = ("<system-bold>", 15)
            button.tint_color = "white"
            button.background_color = "#6A1B9A"
            button.corner_radius = 10
            button.choice = choice
            button.action = self._answer_quiz
            overlay.add_subview(button)

        self._update_quiz_timer()
        generation = self._quiz_generation
        ui.delay(lambda: self._quiz_tick(generation), 1.0)

    def _update_quiz_timer(self):
        if self.quiz_overlay is None:
            return
        timer = next(
            (view for view in self.quiz_overlay.subviews if getattr(view, "name", "") == "quiz_timer"),
            None,
        )
        if timer is not None:
            timer.text = "残り {}秒".format(self.quiz_remaining)

    def _quiz_tick(self, generation):
        if generation != self._quiz_generation or not self.quiz_active:
            return
        self.quiz_remaining -= 1
        if self.quiz_remaining <= 0:
            self._finish_quiz(None, timed_out=True)
            return
        self._update_quiz_timer()
        ui.delay(lambda: self._quiz_tick(generation), 1.0)

    def _answer_quiz(self, sender):
        self._finish_quiz(sender.choice, timed_out=False)

    def _finish_quiz(self, selected, timed_out=False):
        if not self.quiz_active or self.quiz_question is None:
            return
        question = self.quiz_question
        index = self.quiz_index
        if index is None:
            return
        self.quiz_active = False
        if self.quiz_overlay is not None:
            self.remove_subview(self.quiz_overlay)
            self.quiz_overlay = None
        self.quiz_question = None
        self.quiz_index = None

        if not timed_out and selected == question["answer"]:
            self.solved[index] = True
            self.score += 20
            self._save_progress()
            chest_message = self._maybe_spawn_chest(index, CHEST_RIDDLE_CHANCE, "riddle")
            message = "正解！ 謎{}を解いた！ +20pt".format(index + 1)
            if chest_message:
                message += "\n" + chest_message
            if chest_message:
                self._refresh(chest_message)
                return
            self._refresh(message)
            self._show_feedback("正解！\n+20pt", "#2E7D32", 3)
            return

        self.lives -= 1
        self._save_progress()
        if self.lives <= 0:
            self._refresh("ライフ0。セーブポイントから再開します。")
            self._show_feedback("ライフ0\n最初からやり直し", "#C62828", 3)
            generation = self._round_generation
            ui.delay(lambda: self._restore_checkpoint(generation), 3.0)
        elif self.lives == 1:
            self._refresh("残機1。あと1回間違えると最初からです。")
            self._show_feedback("あと1回間違えたら\n最初からだよ", "#C62828", 3)
        elif timed_out:
            self._refresh("時間切れ。残機{}。".format(self.lives))
            self._show_feedback("時間切れ\n残機{}".format(self.lives), "#C62828", 3)
        else:
            self._refresh("不正解。残機{}。".format(self.lives))
            self._show_feedback("不正解\n残機{}".format(self.lives), "#C62828", 3)

    def _restore_checkpoint(self, generation):
        if generation != self._round_generation:
            return
        # セーブポイント機能を追加したら、ここで保存済み状態を復元する。
        # 現在はセーブポイント未実装なので、得点・情報を保持せず最初から始める。
        self._reset(None)

    def _attack(self, sender):
        if self._arriving:
            return
        if self.good_bacteria_visible:
            if self.good_bacteria_hp <= 0:
                self.good_bacteria_visible = False
                self._refresh("善玉くんは倒されています。東京マンを攻撃できます。")
                return
            self.good_bacteria_hp = 0
            self.good_bacteria_visible = False
            self.score += GOOD_BACTERIA_REWARD_POINTS
            self._save_progress()
            self._refresh("善玉くんを一発で倒した！ +{}pt".format(GOOD_BACTERIA_REWARD_POINTS))
            return
        if self.score < ATTACK_COST or self.boss_hp <= 0:
            return
        self.score -= ATTACK_COST
        self.boss_hp = max(0, self.boss_hp - ATTACK_DAMAGE)
        self._save_progress()
        if self.boss_hp == 0:
            self.boss_defeat_transition = True
            self._refresh("東京マンにとどめの一撃！")
            ui.delay(self._finish_boss_defeat, 3.0)
            return
        message = "殴った！ 東京マンに{}ダメージ。".format(ATTACK_DAMAGE)
        self._refresh(message)

    def _finish_boss_defeat(self):
        self.boss_defeat_transition = False
        self._refresh("東京マンを倒した！腸破壊完了おめでとう！")
        self._show_feedback("腸破壊完了\nおめでとう！", "#6A1B9A", 4)

    def _reset(self, sender=None):
        self._round_generation += 1
        self._arriving = False
        self._stop_quiz()
        self._hide_feedback()
        self.score = START_SCORE
        self.boss_hp = START_BOSS_HP
        self.boss_defeat_transition = False
        self.lives = START_LIVES
        self.arrived = [False, False]
        self.solved = [False, False]
        self.used_question_indexes.clear()
        self.chest_arrival_checked = [False, False]
        self.chest_riddle_checked = [False, False]
        self.chest_items = [None, None]
        self.item_inventory = {item: 0 for item in ITEM_COSTS}
        self.good_bacteria_visible = False
        self.good_bacteria_hp = GOOD_BACTERIA_HP
        self._save_progress(reset=True)
        self._refresh("仮試作をリセットしました。")

    def _stop_quiz(self):
        self._quiz_generation += 1
        self.quiz_active = False
        self.quiz_question = None
        self.quiz_index = None
        if self.quiz_overlay is not None:
            self.remove_subview(self.quiz_overlay)
            self.quiz_overlay = None

    def will_close(self):
        self._save_progress()
        self._round_generation += 1
        self._stop_quiz()


def run():
    PurpleMockGame().present("fullscreen")


if __name__ == "__main__":
    run()
