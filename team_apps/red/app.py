"""レッド班 Day 2 試作：6体のモンスターを選んで戦う。"""

import json
import math
import os
import random
import sys
import threading
import time
import uuid
import webbrowser

import location
import ui

# Pythonista can execute an app module from its own folder.  Always expose the
# repository root so the shared server_game helper is available in that case.
_REPOSITORY_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPOSITORY_ROOT not in sys.path:
    sys.path.insert(0, _REPOSITORY_ROOT)

try:
    from team_apps.red.server_game import make_api_client, map_destinations, scenario_from_server
except ImportError:
    try:
        from server_game import make_api_client, map_destinations, scenario_from_server
    except ImportError:
        def make_api_client(config_module):
            return None

        def scenario_from_server(game_definition, team_state):
            return {"places": [], "claimed_place_ids": set(), "game_session_id": "", "boss_place_ids": {}}

        def map_destinations(destinations):
            return [place for place in destinations if has_map_coordinates(place)]


try:
    import config
except ImportError:
    config = None


def has_map_coordinates(place):
    """Return false for the redacted 0,0 placeholder used by local data."""
    try:
        return not (
            float(place.get("latitude")) == 0.0
            and float(place.get("longitude")) == 0.0
        )
    except (AttributeError, TypeError, ValueError):
        return False


MONSTERS = [
    {"name": "森のぷに", "stars": 1, "kind": "攻撃系", "drop": "木の棒", "drop_power": 50},
    {"name": "草むらモン", "stars": 1, "kind": "回復系", "drop": "成長フード（+10）", "drop_power": 10},
    {"name": "石ころモン", "stars": 1, "kind": "強化系", "drop": "木の棒", "drop_power": 50},
    {"name": "青い影", "stars": 2, "kind": "弱体化系", "drop": "弓", "drop_power": 100},
    {"name": "赤い影", "stars": 2, "kind": "攻撃系", "drop": "剣", "drop_power": 100},
    {"name": "幻の王", "stars": 3, "kind": "回復系", "drop": "オレンジジュース", "drop_power": 0},
]

MINIBOSSES = [
    {"name": "ゼウス", "kind": "ボス", "boss_hp": 5000, "drop": "ゼウスの雷", "boss": True, "destination_id": "imperial-palace"},
    {"name": "ヤタ", "kind": "中ボス", "boss_hp": 2000, "drop": "三種の神器・鏡", "boss": True, "destination_id": "meiji-jingu"},
    {"name": "ヤサカニ", "kind": "中ボス", "boss_hp": 2000, "drop": "三種の神器・勾玉", "boss": True, "destination_id": "national-diet"},
    {"name": "クサナギ", "kind": "中ボス", "boss_hp": 2000, "drop": "三種の神器・剣", "boss": True, "destination_id": "yushima-tenjin"},
]

MINIBOSS_NAMES = {"ヤタ", "ヤサカニ", "クサナギ"}

STAR_NAMES = {
    1: "かわいいでちゅね",
    2: "かわいいですね",
    3: "かわいいでございますね",
}

STAR_HP = {1: 100, 2: 300, 3: 500}
MAX_HP_GAIN_BY_STAR = {1: 10, 2: 30, 3: 50}
CAPACITY_GAIN_INTERVAL = {1: 5, 2: 3, 3: 1}
LOCATION_TRIGGER_RADIUS_M = 40
MONSTER_COUNT = 100
WEAPON_POWER = {"木の棒": 50, "剣": 100, "弓": 100, "爆発系": 1000}
WEAPON_USES_PER_ITEM = {"木の棒": 5, "剣": 10, "弓": 10, "爆発系": 10}


def weapon_uses_for(item_name):
    return WEAPON_USES_PER_ITEM.get(item_name, 10)


DESTINATIONS = [
    {
        "id": "center-building",
        "name": "センター棟",
        "plus_code": None,
        "latitude": 0.0,
        "longitude": 0.0,
    },
    {
        "id": "cafeteria-fuji",
        "name": "カフェテリアふじ",
        "plus_code": None,
        "latitude": 0.0,
        "longitude": 0.0,
    },
    {
        "id": "linkeee",
        "name": "運動教室（LinKeee）",
        "plus_code": None,
        "latitude": 0.0,
        "longitude": 0.0,
    },
    {
        "id": "imperial-palace",
        "name": "皇居",
        "plus_code": None,
        "latitude": 0.0,
        "longitude": 0.0,
    },
    {
        "id": "meiji-jingu",
        "name": "明治神宮",
        "plus_code": None,
        "latitude": 0.0,
        "longitude": 0.0,
    },
    {
        "id": "yushima-tenjin",
        "name": "湯島天神",
        "plus_code": None,
        "latitude": 0.0,
        "longitude": 0.0,
    },
    {
        "id": "national-diet",
        "name": "国会議事堂",
        "plus_code": None,
        "latitude": 0.0,
        "longitude": 0.0,
    },
]
TOKYO_PUBLIC_ZONES = [
    ("千代田区・日比谷公園", 0.0, 0.0),
    ("中央区・浜町公園", 0.0, 0.0),
    ("港区・芝公園", 0.0, 0.0),
    ("新宿区・新宿中央公園", 0.0, 0.0),
    ("文京区・小石川後楽園前", 0.0, 0.0),
    ("台東区・上野公園", 0.0, 0.0),
    ("墨田区・隅田公園", 0.0, 0.0),
    ("江東区・木場公園", 0.0, 0.0),
    ("品川区・戸越公園", 0.0, 0.0),
    ("目黒区・中目黒公園", 0.0, 0.0),
    ("大田区・蒲田駅前", 0.0, 0.0),
    ("世田谷区・世田谷公園", 0.0, 0.0),
    ("渋谷区・代々木公園", 0.0, 0.0),
    ("中野区・中野四季の森公園", 0.0, 0.0),
    ("杉並区・和田堀公園", 0.0, 0.0),
    ("豊島区・南池袋公園", 0.0, 0.0),
    ("北区・飛鳥山公園", 0.0, 0.0),
    ("荒川区・荒川自然公園", 0.0, 0.0),
    ("板橋区・城北中央公園", 0.0, 0.0),
    ("練馬区・練馬総合運動場公園", 0.0, 0.0),
    ("足立区・舎人公園", 0.0, 0.0),
    ("葛飾区・水元公園", 0.0, 0.0),
    ("江戸川区・西葛西駅前", 0.0, 0.0),
]

CHIYODA_STATIONS = [
    ("代々木上原駅", 0.0, 0.0), ("代々木公園駅", 0.0, 0.0),
    ("明治神宮前駅", 0.0, 0.0), ("表参道駅", 0.0, 0.0),
    ("乃木坂駅", 0.0, 0.0), ("赤坂駅", 0.0, 0.0),
    ("国会議事堂前駅", 0.0, 0.0), ("霞ケ関駅", 0.0, 0.0),
    ("日比谷駅", 0.0, 0.0), ("二重橋前駅", 0.0, 0.0),
    ("大手町駅", 0.0, 0.0), ("新御茶ノ水駅", 0.0, 0.0),
    ("湯島駅", 0.0, 0.0), ("根津駅", 0.0, 0.0),
    ("千駄木駅", 0.0, 0.0), ("西日暮里駅", 0.0, 0.0),
    ("町屋駅", 0.0, 0.0), ("北千住駅", 0.0, 0.0),
    ("綾瀬駅", 0.0, 0.0), ("北綾瀬駅", 0.0, 0.0),
]
for zone_name, latitude, longitude in TOKYO_PUBLIC_ZONES:
    DESTINATIONS.append({"id": "zone-" + zone_name, "name": zone_name, "plus_code": None, "latitude": latitude, "longitude": longitude})
for station_name, latitude, longitude in CHIYODA_STATIONS:
    DESTINATIONS.append({"id": "chiyoda-" + station_name, "name": station_name, "plus_code": None, "latitude": latitude, "longitude": longitude})
SPECIAL_SPAWN_COUNTS = {
    "center-building": 3,
    "chiyoda-代々木公園駅": 5,
    "meiji-jingu-torii-route": 5,
    "kokkai-diet-route": 5,
    "imperial-palace": 10,
    "yushima-academic-route": 5,
}
DESTINATIONS.extend([
    {"id": "meiji-jingu-torii-route", "name": "明治神宮前駅〜一の鳥居", "plus_code": None, "latitude": 0.0, "longitude": 0.0},
    {"id": "kokkai-diet-route", "name": "国会議事堂前駅〜国会議事堂", "plus_code": None, "latitude": 0.0, "longitude": 0.0},
    {"id": "yushima-academic-route", "name": "湯島駅〜湯島天神・学問通り", "plus_code": None, "latitude": 0.0, "longitude": 0.0},
])


def item_usage_text(item_name, remaining=None):
    if item_name in WEAPON_POWER:
        if remaining is None:
            remaining = weapon_uses_for(item_name)
        return "使用制限：{}回（残り{}回）".format(weapon_uses_for(item_name), remaining)
    return "使用制限：1回（使い切り）"


def distance_meters(latitude, longitude, target):
    latitude_scale = 111320.0
    longitude_scale = latitude_scale * math.cos(math.radians(target["latitude"]))
    north = (latitude - target["latitude"]) * latitude_scale
    east = (longitude - target["longitude"]) * longitude_scale
    return math.sqrt(north * north + east * east)


class MonsterLocationMap(ui.View):
    """Small native GPS map: avoids Pythonista WebView crashes."""

    def __init__(self, frame):
        super().__init__(frame=frame)
        self.current_position = None
        self.destinations = []
        self.monsters = []
        self.status = "地点データを読み込み中…"

    def set_data(self, current_position, destinations, monsters, status):
        self.current_position = current_position
        self.destinations = [place for place in destinations if has_map_coordinates(place)]
        self.monsters = monsters
        self.status = status
        self.set_needs_display()

    def draw(self):
        ui.set_color("#E3F2FD")
        ui.fill_rect(0, 0, self.width, self.height)
        margin = 30
        points = list(self.destinations)
        if self.current_position and self.current_position.get("latitude") and self.current_position.get("longitude"):
            points.append(self.current_position)
        if not points:
            ui.set_color("#455A64")
            ui.draw_string(self.status, (18, self.height / 2 - 20, self.width - 36, 60), alignment=ui.ALIGN_CENTER, font=("<System>", 17))
            return
        latitudes = [float(point["latitude"]) for point in points]
        longitudes = [float(point["longitude"]) for point in points]
        minimum_lat, maximum_lat = min(latitudes), max(latitudes)
        minimum_lon, maximum_lon = min(longitudes), max(longitudes)
        lat_span = max(maximum_lat - minimum_lat, 0.0005)
        lon_span = max(maximum_lon - minimum_lon, 0.0005)

        def xy(point):
            x = margin + (float(point["longitude"]) - minimum_lon) / lon_span * (self.width - margin * 2)
            y = self.height - margin - (float(point["latitude"]) - minimum_lat) / lat_span * (self.height - margin * 2)
            return x, y

        ui.set_color("#BBDEFB")
        for step in range(1, 5):
            x = margin + (self.width - margin * 2) * step / 5.0
            y = margin + (self.height - margin * 2) * step / 5.0
            ui.fill_rect(x, margin, 1, self.height - margin * 2)
            ui.fill_rect(margin, y, self.width - margin * 2, 1)
        for destination in self.destinations:
            x, y = xy(destination)
            ui.set_color("#7B1FA2")
            ui.Path.oval(x - 8, y - 8, 16, 16).fill()
            ui.set_color("#263238")
            ui.draw_string(destination["name"], (x + 10, y - 12, 130, 28), font=("<System>", 12))
        for monster in self.monsters:
            destination = monster.get("destination")
            if not destination or not has_map_coordinates(destination):
                continue
            x, y = xy(destination)
            ui.set_color("#D32F2F")
            ui.Path.oval(x - 5, y - 5, 10, 10).fill()
            ui.set_color("#B71C1C")
            ui.draw_string(
                "{} {}".format("★" * monster.get("stars", 1), monster.get("name", "モンスター")),
                (x + 8, y + 4, 150, 24),
                font=("<System-Bold>", 12),
            )
        if self.current_position and self.current_position.get("latitude") and self.current_position.get("longitude"):
            x, y = xy(self.current_position)
            ui.set_color("#1565C0")
            ui.Path.oval(x - 10, y - 10, 20, 20).fill()
            ui.set_color("#FFFFFF")
            ui.Path.oval(x - 3, y - 3, 6, 6).fill()
            ui.set_color("#263238")
            ui.draw_string("現在地", (x + 12, y - 12, 90, 28), font=("<System-Bold>", 13))
        ui.set_color("#37474F")
        ui.draw_string("青：現在地　赤：モンスター　紫：地点", (12, self.height - 24, self.width - 24, 20), alignment=ui.ALIGN_CENTER, font=("<System>", 12))


class RedPrototype(ui.View):
    def __init__(self):
        super().__init__(frame=(0, 0, 375, 667))
        self.name = "ゴット・アプライアンス"
        self.background_color = "#FFEBEE"
        self.inventory = []
        self.weapon_uses = {}
        self.capacity = 5
        self.defeated_by_stars = {1: 0, 2: 0, 3: 0}
        self.current_screen = "map"
        self.unlocked_destinations = set()
        self.defeated_bosses = set()
        self.defeated_monsters = {}
        self.active_monster = None
        self.active_place_id = None
        self.api = make_api_client(config)
        self.game_session_id = getattr(config, "GAME_SESSION_ID", "") if config else ""
        self.device_id = getattr(config, "DEVICE_ID", "red-ipad") if config else "red-ipad"
        self.server_scenario_loaded = False
        self.claimed_place_ids = set()
        self.destinations = list(DESTINATIONS)
        self.boss_place_ids = {boss["name"]: boss["destination_id"] for boss in MINIBOSSES}
        self.last_position = None
        self.last_accuracy = None
        self.location_tracking = False
        self.location_tracking_button = None
        self.player_max_hp = 100
        self.player_hp = 100
        self.enemy_hp = 0
        self.monsters = []
        for index in range(MONSTER_COUNT):
            monster = random.choice(MONSTERS).copy()
            monster["name"] = "{} #{:03d}".format(monster["name"], index + 1)
            self.monsters.append(monster)
        random.shuffle(self.monsters)
        station_destinations = [
            destination["id"] for destination in self.destinations
            if destination["id"].startswith("chiyoda-")
        ]
        public_zone_destinations = [
            destination["id"] for destination in self.destinations
            if destination["id"].startswith("zone-")
        ]
        random_destinations = station_destinations + public_zone_destinations
        self.monster_destinations = {}
        self._setup_background()
        assigned_count = 0
        for destination_id, count in SPECIAL_SPAWN_COUNTS.items():
            for _ in range(count):
                if assigned_count >= len(self.monsters):
                    break
                monster = self.monsters[assigned_count]
                self.monster_destinations[monster["name"]] = destination_id
                assigned_count += 1
        for monster in self.monsters[assigned_count:]:
            self.monster_destinations[monster["name"]] = random.choice(random_destinations)
        self.build_header()
        self.show_battle_selection()
        self.splash_view = None
        self.splash_button = None
        self.splash_next_action = None
        # Do not load large splash artwork during gallery launch.  It can exhaust
        # Pythonista's UI process before Red's home screen appears.
        self.set_status("モンスターを選んで遊ぼう。")
        if self.api is not None:
            ui.delay(self.refresh_server_scenario, 0.1)

    def refresh_server_scenario(self):
        """Load places and claim state selected by the shared Day 3/Day 4 gallery."""
        if self.api is None:
            return
        threading.Thread(target=self._fetch_server_scenario, daemon=True).start()

    def _fetch_server_scenario(self):
        try:
            definition = self.api.get_game_definition()
        except Exception as exc:
            scenario = None
            error = exc
        else:
            # A state-read failure must not throw away the playable server map.
            # The definition owns the places; claims can be refreshed later.
            try:
                state = self.api.get_team_state()
            except Exception:
                state = {}
            scenario = scenario_from_server(definition, state)
            error = None
        ui.delay(lambda: self._apply_server_scenario(scenario, error), 0.0)

    def _apply_server_scenario(self, scenario, error):
        if error is not None:
            self.set_status("サーバーのシナリオを取得できませんでした。\n{}".format(error))
            return
        if not scenario["places"]:
            self.set_status("サーバーのシナリオに、座標つき地点がありません。")
            return
        self.destinations = scenario["places"]
        self.claimed_place_ids = scenario["claimed_place_ids"]
        self.unlocked_destinations.update(self.claimed_place_ids)
        self.game_session_id = scenario["game_session_id"] or self.game_session_id
        self.boss_place_ids.update(scenario["boss_place_ids"])
        self.server_scenario_loaded = True
        for monster in self.monsters:
            self.monster_destinations[monster["name"]] = random.choice(self.destinations)["id"]
        self.show_battle_selection()
        self.set_status("サーバーのシナリオと獲得状況を読み込みました。")

    def _claim_active_server_place(self):
        if not (self.server_scenario_loaded and self.active_place_id and self.game_session_id):
            return
        threading.Thread(target=self._post_server_claim, daemon=True).start()

    def _post_server_claim(self):
        try:
            result = self.api.claim_place(
                action_id=str(uuid.uuid4()),
                game_session_id=self.game_session_id,
                place_id=self.active_place_id,
                device_id=self.device_id,
            )
            error = None
        except Exception as exc:
            result = None
            error = exc
        ui.delay(lambda: self._finish_server_claim(result, error), 0.0)

    def _finish_server_claim(self, result, error):
        if error is not None:
            self.set_status("モンスター報酬は獲得しました。地点のサーバー登録は失敗しました。\n{}".format(error))
            return
        if result and result.get("claimed"):
            self.claimed_place_ids.add(self.active_place_id)
            self.unlocked_destinations.add(self.active_place_id)

    def _setup_background(self):
        background_path = os.path.join(os.path.dirname(__file__), "back.png")
        if not os.path.exists(background_path):
            return
        self.background_view = ui.ImageView(frame=self.bounds, flex="WH")
        with open(background_path, "rb") as image_file:
            self.background_view.image = ui.Image.from_data(image_file.read())
        self.add_subview(self.background_view)

    def show_splash(self, next_action=None):
        image_path = os.path.join(os.path.dirname(__file__), "god_apocalypse_splash.png")
        if not os.path.exists(image_path):
            image_path = os.path.join(os.path.dirname(__file__), "back.png")
        if not os.path.exists(image_path):
            if next_action:
                next_action()
            return
        self.splash_next_action = next_action
        self.splash_view = ui.ImageView(frame=self.bounds, flex="WH")
        with open(image_path, "rb") as image_file:
            self.splash_view.image = ui.Image.from_data(image_file.read())
        self.splash_view.content_mode = ui.CONTENT_SCALE_ASPECT_FILL
        self.add_subview(self.splash_view)
        self.splash_button = ui.Button(title="タップして続ける", frame=(32, self.height - 82, self.width - 64, 52), flex="WT")
        self.splash_button.tint_color = "#B71C1C"
        self.splash_button.font = ("<System-Bold>", 18)
        self.splash_button.corner_radius = 12
        self.splash_button.action = self.dismiss_splash
        self.add_subview(self.splash_button)

    def dismiss_splash(self, sender):
        if self.splash_view:
            self.splash_view.hidden = True
        if self.splash_button:
            self.splash_button.hidden = True
        next_action = self.splash_next_action
        self.splash_view = None
        self.splash_button = None
        self.splash_next_action = None
        if next_action:
            next_action()

    def build_header(self):
        self.title = ui.Label(frame=(12, 12, 351, 34))
        self.title.text = "ゴット・アプライアンス"
        self.title.font = ("<System-Bold>", 22)
        self.title.text_color = "#B71C1C"
        self.title.alignment = ui.ALIGN_CENTER
        self.add_subview(self.title)

        self.status = ui.Label(frame=(16, 50, 343, 58))
        self.status.number_of_lines = 0
        self.status.font = ("<System>", 14)
        self.add_subview(self.status)

        self.content = ui.ScrollView(frame=(0, 112, 375, 555), flex="WH")
        self.add_subview(self.content)

    def style_buttons(self):
        for button in self.content.subviews:
            if not isinstance(button, ui.Button):
                continue
            button.font = ("<System-Bold>", 16)
            button.corner_radius = 12
            button.border_width = 2
            button.border_color = "#FFFFFF"
            button.alpha = 0.98
            button_color = button.tint_color or "#C62828"
            button.background_color = button_color
            button.tint_color = "#FFFFFF"

    def clear_content(self):
        for view in list(self.content.subviews):
            self.content.remove_subview(view)
        self.content.content_offset = (0, 0)

    def set_status(self, text):
        self.status.text = text

    def inventory_counts(self):
        counts = {}
        for item in self.inventory:
            counts[item] = counts.get(item, 0) + 1
        return counts

    def monster_is_active(self, monster):
        respawn_at = self.defeated_monsters.get(monster["name"])
        if respawn_at is None:
            return True
        if time.time() >= respawn_at:
            old_name = monster["name"]
            active_names = {
                item["name"] for item in self.monsters if item is not monster
            }
            candidates = [
                template for template in MONSTERS
                if template["name"] not in active_names
            ]
            replacement = random.choice(candidates or MONSTERS).copy()
            slot_id = old_name.rsplit("#", 1)[-1].strip() if "#" in old_name else old_name
            replacement["name"] = "{} #{}".format(replacement["name"], slot_id)
            monster.clear()
            monster.update(replacement)
            self.defeated_monsters.pop(old_name, None)
            self.monster_destinations.pop(old_name, None)
            self.monster_destinations[monster["name"]] = random.choice(
                [destination for destination in self.destinations if destination["id"].startswith("zone-")] or self.destinations
            )["id"]
            return True
        return False

    def monsters_by_distance(self):
        position = self.last_position
        if not position:
            return list(self.monsters)

        def distance_for(monster):
            destination_id = self.monster_destinations.get(monster["name"])
            destination = next(
                (item for item in self.destinations if item["id"] == destination_id),
                None,
            )
            if not destination:
                return float("inf")
            return distance_meters(
                position["latitude"],
                position["longitude"],
                destination,
            )

        return sorted(self.monsters, key=distance_for)

    def show_battle_selection(self, sender=None):
        self.current_screen = "battle_selection"
        self.clear_content()
        self.set_status(
            "戦闘画面の第一試作\n"
            "戦いたいモンスターを選ぼう。星が高いほど強い。\n"
            "所持: {}/{}個".format(len(self.inventory), self.capacity)
        )
        map_button = ui.Button(title="モンスターを見る", frame=(16, 8, 343, 42))
        map_button.tint_color = "#2E7D32"
        map_button.action = self.show_map
        self.content.add_subview(map_button)
        howto_button = ui.Button(title="遊び方", frame=(16, 58, 343, 42))
        howto_button.tint_color = "#EF6C00"
        howto_button.action = self.show_how_to_play
        self.content.add_subview(howto_button)
        profile_button = ui.Button(title="マイページ（主人公）", frame=(16, 108, 343, 42))
        profile_button.tint_color = "#AD1457"
        profile_button.action = self.show_profile
        self.content.add_subview(profile_button)
        y = 158
        display_monsters = self.monsters_by_distance()
        if self.unlocked_destinations:
            boss_title = ui.Label(frame=(16, y + 8, 343, 44))
            boss_title.text = "中ボス・ボス"
            boss_title.font = ("<System-Bold>", 18)
            boss_title.text_color = "#6A1B9A"
            self.content.add_subview(boss_title)
            y += 60
            for boss_index, boss in enumerate(MINIBOSSES):
                if boss["name"] in self.defeated_bosses:
                    continue
                boss_place_id = self.boss_place_ids.get(boss["name"])
                if boss_place_id not in self.unlocked_destinations:
                    continue
                if boss["name"] == "ゼウス" and not MINIBOSS_NAMES.issubset(self.defeated_bosses):
                    continue
                boss_button = ui.Button(
                    title="{}（HP{}）".format(boss["name"], boss["boss_hp"]),
                    frame=(16, y, 343, 48),
                )
                boss_button.tint_color = "#6A1B9A"
                boss_button.boss_index = boss_index
                boss_button.action = self.start_miniboss
                self.content.add_subview(boss_button)
                y += 62
        for monster in display_monsters:
            destination_id = self.monster_destinations[monster["name"]]
            destination = next(item for item in self.destinations if item["id"] == destination_id)
            if self.last_position:
                distance = distance_meters(
                    self.last_position["latitude"], self.last_position["longitude"], destination
                )
                distance_text = "約{}m".format(round(distance))
            else:
                distance_text = "距離未測定"
            location_button = ui.Button(
                title="{}（{}）".format(monster["name"], distance_text),
                frame=(16, y, 343, 42),
            )
            location_button.tint_color = "#1565C0"
            location_button.destination = destination
            location_button.monster = monster
            location_button.action = self.check_monster_location
            self.content.add_subview(location_button)
            y += 50
        y += 4
        if not self.unlocked_destinations:
            locked = ui.Label(frame=(20, y, 335, 70))
            locked.number_of_lines = 0
            locked.text = "目的地から40m以内に入ると\nモンスターを発見できます。"
            locked.alignment = ui.ALIGN_CENTER
            locked.font = ("<System-Bold>", 17)
            self.content.add_subview(locked)
            self.style_buttons()
            self.content.content_size = (375, y + 90)
            return
        for monster in display_monsters:
            if not self.monster_is_active(monster):
                continue
            if self.monster_destinations[monster["name"]] not in self.unlocked_destinations:
                continue
            card = ui.Label(frame=(16, y, 343, 58))
            card.number_of_lines = 0
            card.font = ("<System>", 14)
            card.text = "{}  {}  {}\n系統：{} / 敵HP：{}".format(
                "★" * monster["stars"],
                monster["name"],
                STAR_NAMES[monster["stars"]],
                monster["kind"],
                STAR_HP[monster["stars"]],
            )
            self.content.add_subview(card)
            fight_button = ui.Button(title="このモンスターと戦う", frame=(16, y + 60, 343, 42))
            fight_button.tint_color = "#C62828"
            fight_button.monster = monster
            fight_button.action = self.start_selected_battle
            self.content.add_subview(fight_button)
            y += 112
        self.style_buttons()
        self.content.content_size = (375, y + 12)

    def start_selected_battle(self, sender):
        self.active_monster = sender.monster
        self.active_place_id = self.monster_destinations[self.active_monster["name"]]
        self.start_battle(sender)

    def check_monster_location(self, sender):
        self.check_destination_location(sender)

    def check_destination_location(self, sender):
        destination = sender.destination
        self.set_status("{}の位置情報を取得中…\n屋外で少し待ってください。".format(destination["name"]))
        location.start_updates()
        try:
            position = location.get_location()
        finally:
            location.stop_updates()
        if not position:
            self.set_status("位置情報を取得できませんでした。\n位置情報の許可を確認してください。")
            return
        self.last_position = position
        self.last_accuracy = position.get("horizontal_accuracy", "不明")
        distance = distance_meters(
            position["latitude"], position["longitude"], destination
        )
        accuracy = self.last_accuracy
        plus_code = destination.get("plus_code") or "登録済み座標"
        display_name = sender.monster["name"] if hasattr(sender, "monster") else destination["name"]
        if distance <= LOCATION_TRIGGER_RADIUS_M:
            self.unlocked_destinations.add(destination["id"])
            result = "{}を発見！出現地点の40m以内です。".format(display_name)
            self.show_battle_selection()
        else:
            result = "{}（出現地点）まで約{}m。もう少し近づこう。".format(
                display_name, round(distance)
            )
        self.set_status(
            "位置テスト結果\n{}\nPlus Code：{}\nGPS精度：約{}m".format(
                result, plus_code, accuracy
            )
        )

    def show_how_to_play(self, sender=None):
        self.current_screen = "how_to_play"
        self.clear_content()
        self.set_status("遊び方")
        home = ui.Button(title="ホームにもどる", frame=(16, 10, 343, 40))
        home.tint_color = "#C62828"
        home.action = self.show_battle_selection
        self.content.add_subview(home)
        title = ui.Label(frame=(18, 60, 339, 120))
        title.number_of_lines = 0
        title.font = ("<System-Bold>", 19)
        title.text_color = "#B71C1C"
        title.text = "大変だ！謎のモンスターによって皇居が占拠され、天皇が監禁されてしまった…モンスターを倒し、アイテムを集め、三種の神器を手に入れてボスモンスターを倒そう！"
        self.content.add_subview(title)

        sections = [
            ("遊び方", "マップ上に表示されたモンスターに近づいてモンスターを発見、倒してHPを上げたりいろんなアイテムをゲットしよう！強いボスを倒し、天皇を救出せよ！"),
            ("アイテム", "攻撃系は武器、回復系は回復アイテムなど、さまざまなアイテムを落とす。強いモンスターほど良いアイテムが落ちるよ！"),
            ("使用回数", "アイテムには使用回数があって、それを超えると使えなくなるよ！"),
            ("HPのひみつ", "HPを上げると何か起こるかも…？"),
        ]
        y = 154
        for heading, body in sections:
            heading_label = ui.Label(frame=(20, y, 335, 30))
            heading_label.font = ("<System-Bold>", 18)
            heading_label.text_color = "#6A1B9A"
            heading_label.text = heading
            self.content.add_subview(heading_label)
            body_label = ui.Label(frame=(20, y + 34, 335, 108))
            body_label.number_of_lines = 0
            body_label.font = ("<System>", 16)
            body_label.text = body
            self.content.add_subview(body_label)
            y += 146
        back = ui.Button(title="ホームにもどる", frame=(16, y, 343, 46))
        back.tint_color = "#C62828"
        back.action = self.show_battle_selection
        self.content.add_subview(back)
        self.style_buttons()
        self.content.content_size = (375, y + 80)

    def show_profile(self, sender=None):
        self.current_screen = "profile"
        self.clear_content()
        self.set_status("マイページ\nぼくの主人公")
        image_path = os.path.join(os.path.dirname(__file__), "player_character.png")
        if os.path.exists(image_path):
            character_image = ui.ImageView(frame=(16, 12, 343, 330))
            with open(image_path, "rb") as image_file:
                character_image.image = ui.Image.from_data(image_file.read())
            self.content.add_subview(character_image)
            y = 356
        else:
            missing = ui.Label(frame=(20, 30, 335, 80))
            missing.number_of_lines = 0
            missing.alignment = ui.ALIGN_CENTER
            missing.text = "player_character.png が\nまだ見つかりません。"
            self.content.add_subview(missing)
            y = 128
        info = ui.Label(frame=(20, y, 335, 70))
        info.number_of_lines = 0
        info.alignment = ui.ALIGN_CENTER
        info.font = ("<System-Bold>", 17)
        info.text = "ゼウスに立ち向かう主人公！\n戦闘で勝利して強くなろう。"
        self.content.add_subview(info)
        item_title = ui.Label(frame=(20, y + 78, 335, 28))
        item_title.text = "アイテムリスト"
        item_title.font = ("<System-Bold>", 18)
        item_title.text_color = "#6A1B9A"
        self.content.add_subview(item_title)
        counts = self.inventory_counts()
        item_lines = []
        for item, count in counts.items():
            remaining = self.weapon_uses.get(item, weapon_uses_for(item))
            item_lines.append("{} ×{}\n{}".format(item, count, item_usage_text(item, remaining)))
        item_list = ui.Label(frame=(20, y + 110, 335, 180))
        item_list.number_of_lines = 0
        item_list.text = "\n".join(item_lines) if item_lines else "まだアイテムはないよ"
        self.content.add_subview(item_list)
        back = ui.Button(title="ホームにもどる", frame=(16, y + 294, 343, 46))
        back.action = self.show_battle_selection
        self.content.add_subview(back)
        self.style_buttons()
        self.content.content_size = (375, y + 360)

    def show_inventory(self, sender=None):
        self.current_screen = "inventory"
        self.clear_content()
        self.set_status(
            "アイテム一覧\n所持: {}/{}個\n勝利するとHPは全回復します。".format(
                len(self.inventory), self.capacity
            )
        )
        y = 18
        if not self.inventory:
            empty = ui.Label(frame=(20, y, 335, 50))
            empty.text = "まだアイテムはありません。"
            empty.alignment = ui.ALIGN_CENTER
            self.content.add_subview(empty)
            y += 70
        else:
            effect_text = {
                "木の棒": "攻撃：基準50（40〜50ダメージ）",
                "剣": "攻撃：基準100（80〜100ダメージ）",
                "弓": "攻撃：基準100（80〜100ダメージ）",
                "オレンジジュース": "HP0時の復活に使える切り札",
            }
            counts = self.inventory_counts()
            for item, count in counts.items():
                label = ui.Label(frame=(20, y, 335, 44))
                label.number_of_lines = 0
                effect = effect_text.get(item, "効果は戦闘で確認")
                if item in WEAPON_POWER:
                    effect = "攻撃：基準{}\n{}".format(
                        WEAPON_POWER[item],
                        item_usage_text(item, self.weapon_uses.get(item, weapon_uses_for(item))),
                    )
                else:
                    effect = "{}\n{}".format(effect, item_usage_text(item))
                count_text = " ×{}".format(count) if count > 1 else ""
                label.text = "・{}{}\n  {}".format(item, count_text, effect)
                self.content.add_subview(label)
                y += 58
        back = ui.Button(title="戦う相手を選ぶ", frame=(16, y + 12, 343, 48))
        back.tint_color = "#C62828"
        back.action = lambda button: self.show_battle_selection()
        self.content.add_subview(back)
        self.style_buttons()
        self.content.content_size = (375, y + 80)

    def show_interactive_map(self):
        self.set_status(
            "モンスター\n"
            "指で移動・ピンチで拡大縮小できます。モンスターの位置も表示します。"
        )
        self.style_buttons()
        self.content.content_size = (375, 790)
        # Keep this screen native: embedded web maps can terminate Pythonista.
        self.open_map_view = MonsterLocationMap(frame=(0, 0, 375, 660))
        self.content.add_subview(self.open_map_view)
        self.refresh_native_map_panel()
        self.location_tracking_button = ui.Button(
            title="位置追跡を開始", frame=(8, 675, 170, 40)
        )
        self.location_tracking_button.tint_color = "#D32F2F"
        self.location_tracking_button.action = self.toggle_location_tracking
        self.content.add_subview(self.location_tracking_button)
        self.set_status("モンスター地図を開きました。現在地を取得を押すとGPSを更新します。")
        location_button = ui.Button(
            title="現在地を取得", frame=(190, 675, 170, 40)
        )
        location_button.tint_color = "#EF6C00"
        location_button.action = self.update_current_location
        self.content.add_subview(location_button)
        back = ui.Button(title="モンスターを閉じる", frame=(16, 735, 343, 48))
        back.tint_color = "#C62828"
        back.action = self.close_map
        self.content.add_subview(back)
        self.style_buttons()

    def refresh_native_map_panel(self):
        if not self.open_map_view:
            return
        if self.server_scenario_loaded:
            status = "モンスター出現地点"
        else:
            status = "地点データを読み込み中…"
        monsters = []
        for monster in self.monsters:
            destination_id = self.monster_destinations.get(monster["name"])
            destination = next((place for place in self.destinations if place["id"] == destination_id), None)
            if destination:
                monsters.append({
                    "destination": destination,
                    "name": monster["name"],
                    "stars": monster["stars"],
                })
        self.open_map_view.set_data(
            self.last_position,
            map_destinations(self.destinations),
            monsters,
            status,
        )

    def close_map(self, sender):
        self.stop_location_tracking()
        self.show_battle_selection()

    def start_location_tracking(self, sender=None):
        if self.location_tracking:
            return
        self.location_tracking = True
        location.start_updates()
        if self.location_tracking_button:
            self.location_tracking_button.title = "位置追跡を停止"
        self.location_tick()

    def stop_location_tracking(self, sender=None):
        self.location_tracking = False
        location.stop_updates()
        if self.location_tracking_button:
            self.location_tracking_button.title = "位置追跡を開始"

    def toggle_location_tracking(self, sender):
        if self.location_tracking:
            self.stop_location_tracking()
        else:
            self.start_location_tracking()

    def location_tick(self):
        if not self.location_tracking:
            return
        position = location.get_location()
        interval = 30
        if position:
            self.last_position = position
            self.last_accuracy = position.get("horizontal_accuracy", "不明")
            self.refresh_native_map_panel()
            playable_destinations = map_destinations(self.destinations)
            if not self.server_scenario_loaded or not playable_destinations:
                self.set_status(
                    "現在地を更新しました。\n地点データを読み込み中です。"
                )
                ui.delay(self.location_tick, interval)
                return
            distances = [
                distance_meters(
                    position["latitude"], position["longitude"], destination
                )
                for destination in playable_destinations
            ]
            nearest_index, nearest = min(
                enumerate(distances), key=lambda item: item[1]
            )
            nearest_destination = playable_destinations[nearest_index]
            self.refresh_native_map_panel()
            if nearest <= LOCATION_TRIGGER_RADIUS_M:
                self.unlocked_destinations.add(nearest_destination["id"])
                self.stop_location_tracking()
                self.set_status(
                    "{}の40m以内に入りました。モンスター発見！".format(
                        nearest_destination["name"]
                    )
                )
                return
            if nearest <= 200:
                interval = 10
            self.set_status(
                "現在地を更新しました。最寄りの目的地まで約{}m\n次の更新：{}秒後".format(
                    round(nearest), interval
                )
            )
        ui.delay(self.location_tick, interval)

    def update_current_location(self, sender):
        self.set_status("現在地を1回取得中…\n屋外で少し待ってください。")
        if not self.location_tracking:
            location.start_updates()
        try:
            position = location.get_location()
        finally:
            if not self.location_tracking:
                location.stop_updates()
        if not position:
            self.set_status("現在地を取得できませんでした。\n位置情報の許可を確認してください。")
            return
        self.last_position = position
        self.last_accuracy = position.get("horizontal_accuracy", "不明")
        self.refresh_native_map_panel()
        self.set_status(
            "現在地を更新しました。\nGPS精度：約{}m".format(self.last_accuracy)
        )

    def leaflet_map_html(self):
        destinations = [
            {
                "name": destination["name"],
                "latitude": destination["latitude"],
                "longitude": destination["longitude"],
            }
            for destination in map_destinations(self.destinations)
        ]
        markers = []
        for index, monster in enumerate(self.monsters):
            if not self.monster_is_active(monster):
                continue
            destination_id = self.monster_destinations[monster["name"]]
            destination = next(item for item in self.destinations if item["id"] == destination_id)
            if not has_map_coordinates(destination):
                continue
            offset = (index % 3 - 1) * 0.00012
            markers.append(
                {
                    "name": monster["name"],
                    "rank": "★" * monster["stars"],
                    "kind": monster["kind"],
                    "latitude": destination["latitude"] + offset,
                    "longitude": destination["longitude"] + offset,
                }
            )
        destination_json = json.dumps(destinations, ensure_ascii=False)
        marker_json = json.dumps(markers, ensure_ascii=False)
        current_json = json.dumps(
            {
                "latitude": self.last_position["latitude"],
                "longitude": self.last_position["longitude"],
            }
            if self.last_position
            and self.last_position.get("latitude")
            and self.last_position.get("longitude")
            else None
        )
        return """<!doctype html>
<html><head><meta name='viewport' content='width=device-width,initial-scale=1'>
<link rel='stylesheet' href='https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'>
<style>html,body,#map{height:100%%;margin:0} .monster{font-size:20px}</style></head>
<body><div id='map'></div>
<script src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'></script>
<script>
const destinations = %s.filter(d => d.latitude !== 0 && d.longitude !== 0);
const monsters = %s.filter(m => m.latitude !== 0 && m.longitude !== 0);
const current = %s;
const map = L.map('map', {zoomControl:true});
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 21, attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);
if (current) {
  map.setView([current.latitude,current.longitude], 18);
} else if (destinations.length) {
  map.fitBounds(destinations.map(d => [d.latitude, d.longitude]), {padding:[24,24]});
} else {
  map.remove();
  document.getElementById('map').style.cssText = 'display:flex;align-items:center;justify-content:center;text-align:center;padding:24px;font:17px sans-serif;color:#555;background:#f4f4f4';
  document.getElementById('map').textContent = '位置情報を取得中…\n「現在地を取得」を押して、屋外で少し待ってください。';
}
destinations.forEach(d => {
  L.marker([d.latitude,d.longitude]).addTo(map).bindPopup('目的地：' + d.name);
});
if (current) {
  L.circleMarker([current.latitude,current.longitude], {
    radius: 9, color: '#D32F2F', fillColor: '#F44336', fillOpacity: 0.9
  }).addTo(map).bindPopup('現在地');
  map.setView([current.latitude,current.longitude], 18);
}
monsters.forEach(m => {
  const icon = L.divIcon({className:'monster', html:'👾', iconSize:[28,28]});
  L.marker([m.latitude,m.longitude], {icon:icon}).addTo(map)
    .bindPopup('<b>' + m.rank + ' ' + m.name + '</b><br>系統：' + m.kind);
});
</script></body></html>""" % (destination_json, marker_json, current_json)

    def google_map_url(self, destination):
        return (
            "https://www.google.com/maps/@?api=1&map_action=map&center={},{}&zoom=18"
            "&basemap=roadmap"
        ).format(destination["latitude"], destination["longitude"])

    def move_google_map(self, sender):
        self.google_map_view.load_url(self.google_map_url(sender.destination))

    def show_map(self, sender=None):
        self.current_screen = "map"
        self.clear_content()
        self.show_interactive_map()
        return
        y = 8
        map_label = ui.Label(frame=(16, y, 343, 42))
        map_label.text = "【オリンピックセンター探索マップ】"
        map_label.font = ("<System-Bold>", 18)
        map_label.text_color = "#2E7D32"
        self.content.add_subview(map_label)
        y += 54
        for destination in self.destinations:
            destination_id = destination["id"]
            unlocked = destination_id in self.unlocked_destinations
            card = ui.Label(frame=(16, y, 343, 74))
            card.number_of_lines = 0
            assigned = [
                monster for monster in self.monsters
                if self.monster_destinations[monster["name"]] == destination_id
            ]
            if unlocked:
                kinds = "、".join(sorted({monster["kind"] for monster in assigned})) or "なし"
                card.text = "📍 {}\n系統：{}\nモンスター{}体".format(
                    destination["name"], kinds, len(assigned)
                )
            else:
                card.text = "🔒 {}\n40m以内に入るとモンスターの系統が分かります".format(
                    destination["name"]
                )
            card.font = ("<System>", 14)
            self.content.add_subview(card)
            y += 78
            map_button = ui.Button(title="Googleマップで開く", frame=(16, y, 343, 42))
            map_button.tint_color = "#1565C0"
            map_button.destination = destination
            map_button.action = self.open_google_maps
            self.content.add_subview(map_button)
            y += 54
            if unlocked:
                footprints = ui.Button(title="足跡をたどる", frame=(16, y, 343, 42))
                footprints.tint_color = "#6A1B9A"
                footprints.destination_id = destination_id
                footprints.action = self.show_destination_footprints
                self.content.add_subview(footprints)
                y += 54
        back = ui.Button(title="戦う相手を選ぶ", frame=(16, y, 343, 46))
        back.tint_color = "#C62828"
        back.action = lambda sender: self.show_battle_selection()
        self.content.add_subview(back)
        self.style_buttons()
        self.content.content_size = (375, y + 70)

    def open_google_maps(self, sender):
        destination = sender.destination
        url = "https://www.google.com/maps/search/?api=1&query={},{}".format(
            destination["latitude"], destination["longitude"]
        )
        self.set_status("Googleマップで{}を開いています…".format(destination["name"]))
        webbrowser.open(url, new=2, autoraise=True)

    def show_destination_footprints(self, sender):
        destination_id = sender.destination_id
        destination = next(item for item in self.destinations if item["id"] == destination_id)
        monsters = [
            monster for monster in self.monsters
            if self.monster_is_active(monster)
            and self.monster_destinations[monster["name"]] == destination_id
        ]
        self.clear_content()
        self.set_status("{}の足跡\n少しずつ見つかった！".format(destination["name"]))
        y = 20
        trail = ui.Label(frame=(20, y, 335, 100))
        trail.number_of_lines = 0
        trail.alignment = ui.ALIGN_CENTER
        trail.font = ("<System>", 22)
        trail.text = "・   ・     ・   ・\n\n足跡の先にモンスターがいる…"
        self.content.add_subview(trail)
        y += 120
        for monster in monsters:
            button = ui.Button(
                title="{}  {}（{}系）を発見".format(
                    "★" * monster["stars"], monster["name"], monster["kind"]
                ),
                frame=(16, y, 343, 48),
            )
            button.tint_color = "#C62828"
            button.monster = monster
            button.action = self.start_monster_from_map
            self.content.add_subview(button)
            y += 62
        back = ui.Button(title="マップに戻る", frame=(16, y, 343, 46))
        back.action = lambda sender: self.show_map()
        self.content.add_subview(back)
        self.style_buttons()
        self.content.content_size = (375, y + 70)

    def start_monster_from_map(self, sender):
        self.active_monster = sender.monster
        self.active_place_id = self.monster_destinations[self.active_monster["name"]]
        self.start_battle(sender)

    def begin_search(self, sender):
        monster = self.monsters[sender.monster_index]
        self.active_monster = monster
        self.current_screen = "search"
        self.clear_content()
        self.set_status(
            "AR探索中\n足跡が少しずつ見つかった！\n"
            "通行の邪魔にならない場所で、立ち止まって探そう。"
        )
        label = ui.Label(frame=(20, 24, 335, 120))
        label.number_of_lines = 0
        label.font = ("<System>", 20)
        label.alignment = ui.ALIGN_CENTER
        label.text = "・   ・     ・\n\n足跡の先に何かいる…"
        self.content.add_subview(label)
        find_button = ui.Button(title="モンスターをタップして発見！", frame=(16, 175, 343, 54))
        find_button.tint_color = "#C62828"
        find_button.action = self.start_battle
        self.content.add_subview(find_button)
        back_button = ui.Button(title="地図にもどる", frame=(16, 245, 343, 44))
        back_button.action = lambda sender: self.show_map()
        self.content.add_subview(back_button)
        self.style_buttons()
        self.content.content_size = (375, 310)

    def start_miniboss(self, sender):
        self.active_monster = MINIBOSSES[sender.boss_index]
        self.active_place_id = self.boss_place_ids.get(self.active_monster["name"])
        self.start_battle(sender)

    def start_battle(self, sender):
        self.current_screen = "battle"
        monster = self.active_monster
        self.enemy_hp = monster["boss_hp"] if monster.get("boss") else STAR_HP[monster["stars"]]
        self.player_hp = min(self.player_hp, self.player_max_hp)
        self.show_splash(lambda: self.show_battle("モンスターが現れた！"))

    def show_battle(self, message):
        self.clear_content()
        monster = self.active_monster
        enemy_max_hp = monster["boss_hp"] if monster.get("boss") else STAR_HP[monster["stars"]]
        rank_text = "BOSS" if monster.get("boss") else "★" * monster["stars"]
        self.set_status(
            "{}  {}\n敵HP: {}/{}\n自分HP: {}/{}\n{}".format(
                rank_text,
                monster["name"],
                self.enemy_hp,
                enemy_max_hp,
                self.player_hp,
                self.player_max_hp,
                message,
            )
        )
        y = 18
        player_image_path = os.path.join(os.path.dirname(__file__), "player_character.png")
        if os.path.exists(player_image_path):
            player_image = ui.ImageView(frame=(16, y, 343, 180))
            with open(player_image_path, "rb") as image_file:
                player_image.image = ui.Image.from_data(image_file.read())
            self.content.add_subview(player_image)
            y += 194
        if monster and monster.get("boss") and monster["name"] == "ゼウス":
            zeus_image_path = os.path.join(os.path.dirname(__file__), "zeus_boss.png")
            if os.path.exists(zeus_image_path):
                zeus_image = ui.ImageView(frame=(16, y, 343, 180))
                with open(zeus_image_path, "rb") as image_file:
                    zeus_image.image = ui.Image.from_data(image_file.read())
                self.content.add_subview(zeus_image)
                y += 194
        attack_button = ui.Button(title="素手で攻撃（10）", frame=(16, y, 343, 48))
        attack_button.tint_color = "#B71C1C"
        attack_button.action = self.attack_with_fist
        self.content.add_subview(attack_button)
        y += 62
        for item in dict.fromkeys(self.inventory):
            if item in WEAPON_POWER:
                power = WEAPON_POWER[item]
                uses = self.weapon_uses.get(item, weapon_uses_for(item))
                button = ui.Button(
                    title="{}で攻撃（基準{}／残り{}回）".format(item, power, uses),
                    frame=(16, y, 343, 48),
                )
                button.tint_color = "#C62828"
                button.item_name = item
                button.action = self.attack_with_item
                self.content.add_subview(button)
                y += 62
        if monster.get("boss"):
            artifact_titles = {
                "三種の神器・鏡": "鏡：攻撃を2倍返し",
                "三種の神器・剣": "剣：攻撃力2000",
                "三種の神器・勾玉": "勾玉：攻撃無効化",
            }
            for artifact, title in artifact_titles.items():
                if artifact not in self.inventory:
                    continue
                artifact_button = ui.Button(title=title, frame=(16, y, 343, 48))
                artifact_button.tint_color = "#6A1B9A"
                artifact_button.artifact_name = artifact
                artifact_button.action = self.use_artifact
                self.content.add_subview(artifact_button)
                y += 62
        escape_button = ui.Button(title="逃げる（試作では星で判定）", frame=(16, y, 343, 48))
        escape_button.action = self.try_escape
        self.content.add_subview(escape_button)
        y += 62
        inventory_label = ui.Label(frame=(20, y, 335, 50))
        inventory_label.number_of_lines = 0
        counts = self.inventory_counts()
        summary = []
        for item, count in counts.items():
            count_text = " ×{}".format(count) if count > 1 else ""
            summary.append(item + count_text)
        inventory_label.text = "持ち物: {} / {}\n{}".format(
            len(self.inventory), self.capacity, ", ".join(summary) or "なし"
        )
        self.content.add_subview(inventory_label)
        self.style_buttons()
        self.content.content_size = (375, y + 80)

    def use_artifact(self, sender):
        if not self.active_monster.get("boss"):
            return
        artifact = sender.artifact_name
        if artifact not in self.inventory:
            return
        self.inventory.remove(artifact)
        if artifact == "三種の神器・剣":
            self.resolve_player_attack(2000, "神器・剣で攻撃！攻撃力2000！")
            return
        enemy_tier = 3
        enemy_base_damage = 10 * enemy_tier
        enemy_damage = random.randint((enemy_base_damage * 8) // 10, enemy_base_damage)
        if artifact == "三種の神器・鏡":
            reflected = enemy_damage * 2
            self.enemy_hp -= reflected
            message = "神器・鏡！敵の攻撃{}を{}ダメージ返した！".format(
                enemy_damage, reflected
            )
            if self.enemy_hp <= 0:
                self.finish_battle(True, message + "\n中ボスを倒した！")
            else:
                self.show_battle(message)
        elif artifact == "三種の神器・勾玉":
            self.show_battle("神器・勾玉！敵の攻撃{}を無効化した！".format(enemy_damage))

    def attack_with_fist(self, sender):
        self.resolve_player_attack(10, "素手で攻撃！")

    def attack_with_item(self, sender):
        item_name = sender.item_name
        uses_left = self.weapon_uses.get(item_name, weapon_uses_for(item_name)) - 1
        if uses_left <= 0:
            self.weapon_uses.pop(item_name, None)
            self.inventory.remove(item_name)
        else:
            self.weapon_uses[item_name] = uses_left
        self.resolve_player_attack(WEAPON_POWER[item_name], "{}で攻撃！".format(item_name))

    def revive_if_possible(self):
        if not self.inventory:
            self.player_hp = self.player_max_hp
            return ""
        lost_item = random.choice(self.inventory)
        self.inventory.remove(lost_item)
        if lost_item in WEAPON_POWER:
            self.weapon_uses.pop(lost_item, None)
        self.player_hp = self.player_max_hp
        return lost_item

    def resolve_player_attack(self, power, message):
        damage = random.randint((power * 8) // 10, power)
        self.enemy_hp = max(0, self.enemy_hp - damage)
        message = "{}（{}ダメージ）".format(message, damage)
        if self.enemy_hp == 0:
            self.finish_battle(True, message + "\nモンスターを倒した！")
            return
        enemy_tier = 3 if self.active_monster.get("boss") else self.active_monster["stars"]
        enemy_base_damage = 10 * enemy_tier
        enemy_damage = random.randint((enemy_base_damage * 8) // 10, enemy_base_damage)
        self.player_hp = max(0, self.player_hp - enemy_damage)
        enemy_message = "モンスターの反撃！（{}ダメージ）".format(enemy_damage)
        if self.player_hp == 0:
            lost_item = self.revive_if_possible()
            if lost_item:
                revival_message = "{}を失い、回復して帰還！".format(lost_item)
            else:
                revival_message = "アイテムなしで回復して帰還！"
            self.finish_battle(False, message + "\n" + enemy_message + "\nゲームオーバー\n" + revival_message)
            return
        self.show_battle(message + "\n" + enemy_message)

    def try_escape(self, sender):
        if self.active_monster.get("boss"):
            self.show_battle("ボス戦からは逃げられない！")
            return
        if self.active_monster["stars"] == 1:
            success = random.random() < 0.8
        elif self.active_monster["stars"] == 2:
            success = random.random() < 0.5
        else:
            success = random.random() < 0.2
        if success:
            self.show_battle_selection()
        else:
            enemy_tier = self.active_monster["stars"]
            enemy_base_damage = 10 * enemy_tier
            enemy_damage = random.randint((enemy_base_damage * 8) // 10, enemy_base_damage)
            self.player_hp = max(0, self.player_hp - enemy_damage)
            enemy_message = "逃走失敗！モンスターの攻撃！（{}ダメージ）".format(enemy_damage)
            if self.player_hp == 0:
                lost_item = self.revive_if_possible()
                if lost_item:
                    revival_message = "{}を失い、回復して帰還！".format(lost_item)
                else:
                    revival_message = "アイテムなしで回復して帰還！"
                self.finish_battle(False, enemy_message + "\nゲームオーバー\n" + revival_message)
            else:
                self.show_battle(enemy_message)

    def finish_battle(self, won, message):
        if won:
            self._claim_active_server_place()
            if self.active_monster.get("boss"):
                self.defeated_bosses.add(self.active_monster["name"])
            else:
                self.defeated_monsters[self.active_monster["name"]] = time.time() + 180
            hp_gain = 0 if self.active_monster.get("boss") else MAX_HP_GAIN_BY_STAR[self.active_monster["stars"]]
            self.player_max_hp += hp_gain
            self.player_hp = self.player_max_hp
            capacity_message = ""
            if not self.active_monster.get("boss"):
                stars = self.active_monster["stars"]
                self.defeated_by_stars[stars] += 1
                interval = CAPACITY_GAIN_INTERVAL[stars]
                if self.defeated_by_stars[stars] % interval == 0:
                    self.capacity += 1
                    capacity_message = " 所持容量+1！"
            message += "\n勝利！最大HP+{}、HP全回復！{}".format(hp_gain, capacity_message)
            drop = self.active_monster["drop"]
            if self.active_monster["kind"] == "回復系":
                roll = random.random()
                if roll < 0.5:
                    drop = "りんご"
                elif roll < 0.8:
                    drop = "金のリンゴ"
                else:
                    drop = None
            elif drop == "オレンジジュース" and random.random() >= 0.3:
                drop = None
            if self.active_monster.get("boss"):
                self.inventory.append(drop)
                if drop in WEAPON_POWER:
                    self.weapon_uses[drop] = self.weapon_uses.get(drop, 0) + weapon_uses_for(drop)
                drop_message = "\n{}を100%確定で獲得！".format(drop)
            elif drop is None:
                drop_message = "\n今回はアイテムがドロップしなかった。"
            elif drop.startswith("成長フード（+"):
                food_value = int(drop.split("+")[1].rstrip("）"))
                self.player_max_hp += food_value
                self.capacity += 1
                drop_message = "\n{}を自動摂取！最大HP+{}、所持容量+1。".format(drop, food_value)
            elif len(self.inventory) < self.capacity:
                self.inventory.append(drop)
                if drop in WEAPON_POWER:
                    self.weapon_uses[drop] = self.weapon_uses.get(drop, 0) + weapon_uses_for(drop)
                    drop_message = "\n{}を自動取得！使用回数+{}回。".format(drop, weapon_uses_for(drop))
                else:
                    drop_message = "\n{}を自動取得！".format(drop)
            else:
                drop_message = "\n容量いっぱいで、{}は入らなかった。".format(drop)
            message += drop_message
        self.clear_content()
        self.set_status(message)
        result = ui.Label(frame=(20, 28, 335, 100))
        result.number_of_lines = 0
        result.font = ("<System-Bold>", 20)
        result.alignment = ui.ALIGN_CENTER
        result.text = "勝利！" if won else ("ゲームオーバー" if "ゲームオーバー" in message else "敗北…")
        self.content.add_subview(result)
        again = ui.Button(title="地図にもどる", frame=(16, 160, 343, 50))
        again.tint_color = "#C62828"
        again.action = lambda sender: self.show_battle_selection()
        self.content.add_subview(again)
        self.style_buttons()
        self.content.content_size = (375, 240)
        self.show_splash()


def run():
    RedPrototype().present("fullscreen")


if __name__ == "__main__":
    run()
