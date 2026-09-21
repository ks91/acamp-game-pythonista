"""Pythonista 3 one-screen interface for a team's location game."""

import datetime
import math
import os
import random
import uuid
from urllib.error import HTTPError

import location
import motion
import ui

import config
from toolkit.api_client import ApiClient
from toolkit.check_in import CheckInService
from toolkit.event_queue import EventQueue
from toolkit.game_view_model import build_game_view_model
from toolkit.location_payload import make_location_sample


PINK_RIDDLES = [
    ("津島神社", "神社にある、赤くて大きな門はなーんだ？", "鳥居"),
    ("参宮橋公園", "公園で座って休むものはなーんだ？", "ベンチ"),
    ("代々木八幡宮", "神社で、パンパンと手をたたいてお願いすることを何という？", "お参り"),
    ("代々木出世稲荷大明神", "稲荷神社と仲良しの動物はなーんだ？", "キツネ"),
    ("代々木ポニー公園", "小さな馬のような動物はなーんだ？", "ポニー"),
]

SPOT_ADDRESSES = {
    "津島神社": {
        "plus_code": "MMHV+XV 渋谷区、東京都",
        "coordinates": "35.680002644293516, 139.69468821491773",
        "address": "東京都渋谷区代々木付近",
    },
}

COIN_SPACING_M = 30
COIN_RADIUS_M = 5


class GameView(ui.View):
    def __init__(self):
        super().__init__(frame=(0, 0, 375, 667))
        self.name = "アカキャン位置ゲー"
        self.background_color = "white"
        self.api = ApiClient(
            base_url=config.API_BASE_URL,
            token=config.GAME_TOKEN,
            game_team_id=getattr(config, "SELECTED_GAME_TEAM_ID", None),
            game_mode=getattr(config, "SELECTED_GAME_MODE", None),
        )
        self.repository_directory = os.path.dirname(os.path.abspath(__file__))
        self.queue = EventQueue(os.path.join(self.repository_directory, "pending-events.json"))
        self.coins = 0
        self.tickets = {"スキップチケット": 0, "交換チケット": 0, "ヒントチケット": 0}
        self.coin_points = []
        self.collected_coin_ids = set()
        self.last_position = None
        self.distance_remainder_m = 0.0
        self.motion_available = False
        self.auto_coin_collection_active = True
        self.status_label = ui.Label(frame=(16, 12, 340, 110), flex="W")
        self.status_label.number_of_lines = 0
        self.add_subview(self.status_label)
        self.scroll = ui.ScrollView(frame=(0, 130, 0, 0), flex="WH")
        self.add_subview(self.scroll)
        self.refresh()
        self.start_auto_coin_collection()

    def layout(self):
        self.status_label.frame = (16, 12, self.width - 32, 110)
        self.scroll.frame = (0, 130, self.width, self.height - 130)

    def show_message(self, message):
        self.status_label.text = message

    def start_auto_coin_collection(self):
        try:
            location.start_updates()
            motion.start_updates()
            self.motion_available = True
        except Exception:
            self.auto_coin_collection_active = False
            return
        ui.delay(self.auto_collect_coins, 5.0)

    def auto_collect_coins(self):
        if not self.auto_coin_collection_active:
            return
        try:
            position = location.get_location()
            if position is not None:
                collected = self._collect_distance_coins(position)
                if collected:
                    self.show_message("🪙 移動30mごとにコインを{}枚獲得しました！".format(collected))
                    self.refresh()
        except Exception:
            pass
        ui.delay(self.auto_collect_coins, 5.0)

    def will_close(self):
        self.auto_coin_collection_active = False
        try:
            location.stop_updates()
        except Exception:
            pass
        try:
            motion.stop_updates()
        except Exception:
            pass

    @staticmethod
    def _distance_m(latitude_a, longitude_a, latitude_b, longitude_b):
        earth_radius_m = 6371000
        lat_a = math.radians(latitude_a)
        lat_b = math.radians(latitude_b)
        delta_lat = math.radians(latitude_b - latitude_a)
        delta_lon = math.radians(longitude_b - longitude_a)
        value = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat_a) * math.cos(lat_b) * math.sin(delta_lon / 2) ** 2
        )
        return 2 * earth_radius_m * math.asin(math.sqrt(value))

    def _build_coin_points(self, definition):
        places = [
            place for place in definition.get("places", [])
            if place.get("latitude") is not None and place.get("longitude") is not None
        ]
        points = []
        for route_index, (start, end) in enumerate(zip(places, places[1:])):
            distance = self._distance_m(
                start["latitude"], start["longitude"],
                end["latitude"], end["longitude"],
            )
            steps = int(distance // COIN_SPACING_M)
            for step in range(1, steps + 1):
                fraction = (step * COIN_SPACING_M) / distance
                points.append({
                    "id": "route-{}-coin-{}".format(route_index, step),
                    "latitude": start["latitude"] + (end["latitude"] - start["latitude"]) * fraction,
                    "longitude": start["longitude"] + (end["longitude"] - start["longitude"]) * fraction,
                })
        return points

    def _device_is_moving(self):
        if not self.motion_available:
            return True
        try:
            acceleration = motion.get_user_acceleration()
            if not acceleration:
                return True
            magnitude = math.sqrt(
                acceleration.get("x", 0.0) ** 2
                + acceleration.get("y", 0.0) ** 2
                + acceleration.get("z", 0.0) ** 2
            )
            return magnitude >= 0.08
        except Exception:
            return True

    def _collect_distance_coins(self, position):
        latitude = position.get("latitude")
        longitude = position.get("longitude")
        if latitude is None or longitude is None:
            return 0
        if self.last_position is None:
            self.last_position = {"latitude": latitude, "longitude": longitude}
            return 0
        moved_m = self._distance_m(
            self.last_position["latitude"], self.last_position["longitude"],
            latitude, longitude,
        )
        self.last_position = {"latitude": latitude, "longitude": longitude}
        if moved_m < 3.0 and not self._device_is_moving():
            return 0
        self.distance_remainder_m += moved_m
        collected = int(self.distance_remainder_m // COIN_SPACING_M)
        self.distance_remainder_m %= COIN_SPACING_M
        self.coins += collected
        return collected

    def _collect_nearby_coins(self, position):
        latitude = position.get("latitude")
        longitude = position.get("longitude")
        if latitude is None or longitude is None:
            return 0
        collected = 0
        for coin in self.coin_points:
            if coin["id"] in self.collected_coin_ids:
                continue
            distance = self._distance_m(
                latitude, longitude, coin["latitude"], coin["longitude"]
            )
            if distance <= COIN_RADIUS_M:
                self.collected_coin_ids.add(coin["id"])
                collected += 1
        self.coins += collected
        return collected

    def refresh(self):
        try:
            definition = self.api.get_game_definition()
            state = self.api.get_team_state()
        except OSError as error:
            self.show_message("サーバーへ接続できません。\n{}".format(error))
            return
        model = build_game_view_model(definition, state, config.TEAM_ID)
        theme = model["theme"]
        accent_color = theme["accent_color"]
        self.background_color = theme["background_color"]
        self.status_label.text_color = accent_color
        self.places = {place["id"]: place for place in definition.get("places", [])}
        if not self.coin_points:
            self.coin_points = self._build_coin_points(definition)
        self.show_message("こんにちは、{}班です！\n{}".format(config.TEAM_ID, model["status_text"]))
        for view in list(self.scroll.subviews):
            self.scroll.remove_subview(view)
        update_button = ui.Button(title="現在地を更新", frame=(16, 0, 220, 44))
        update_button.action = self.update_location
        update_button.tint_color = accent_color
        self.scroll.add_subview(update_button)
        self.coin_label = ui.Label(frame=(16, 48, 170, 40), flex="W")
        self.coin_label.text = "🪙 コイン: {}枚\n移動距離の残り: {:.1f}m / {}m".format(
            self.coins, self.distance_remainder_m, COIN_SPACING_M
        )
        self.coin_label.number_of_lines = 0
        self.scroll.add_subview(self.coin_label)
        gacha_button = ui.Button(title="🎁 ガチャ（50コイン）", frame=(190, 48, 170, 36))
        gacha_button.action = self.play_gacha
        gacha_button.tint_color = accent_color
        self.scroll.add_subview(gacha_button)
        y = 94
        for place in model["places"]:
            title = "✓ " if place["claimed"] else ""
            button = ui.Button(
                title="{}{}（{}点）".format(title, place["name"], place["points"]),
                frame=(16, y, 340, 44),
            )
            button.place_id = place["id"]
            button.action = self.claim_place
            button.tint_color = accent_color
            self.scroll.add_subview(button)
            narrative = place["narrative"]
            if narrative:
                label = ui.Label(frame=(24, y + 42, 330, 36), flex="W")
                label.text = narrative
                label.font = ("<System>", 13)
                label.number_of_lines = 0
                self.scroll.add_subview(label)
                y += 88
            else:
                y += 52
        y += 12
        riddle_title = ui.Label(frame=(16, y, 340, 32), flex="W")
        riddle_title.text = "🌸 ピンク班のかんたんなぞなぞ"
        riddle_title.font = ("<System-Bold>", 16)
        self.scroll.add_subview(riddle_title)
        y += 38
        for place_name, question, answer in PINK_RIDDLES:
            label = ui.Label(frame=(20, y, 330, 48), flex="W")
            label.text = "{}\n{}".format(place_name, question)
            label.number_of_lines = 0
            label.font = ("<System>", 13)
            self.scroll.add_subview(label)
            answer_button = ui.Button(title="答えを見る", frame=(220, y + 48, 110, 32))
            answer_button.riddle_answer = answer
            answer_button.action = self.reveal_riddle_answer
            answer_button.tint_color = accent_color
            self.scroll.add_subview(answer_button)
            y += 88

        address = SPOT_ADDRESSES.get("津島神社")
        if address:
            address_label = ui.Label(frame=(20, y, 330, 72), flex="W")
            address_label.text = "📍 津島神社\n{}\nPlus Code: {}".format(
                address["address"], address["plus_code"]
            )
            address_label.number_of_lines = 0
            address_label.font = ("<System>", 13)
            self.scroll.add_subview(address_label)
            y += 84
        ticket_label = ui.Label(frame=(20, y, 330, 48), flex="W")
        ticket_label.text = "🎫 チケット: スキップ {} / 交換 {} / ヒント {}".format(
            self.tickets["スキップチケット"],
            self.tickets["交換チケット"],
            self.tickets["ヒントチケット"],
        )
        ticket_label.number_of_lines = 0
        ticket_label.font = ("<System>", 13)
        self.scroll.add_subview(ticket_label)
        y += 60
        self.scroll.content_size = (375, y + 16)

    def play_gacha(self, sender):
        if self.coins < 50:
            self.show_message("コインが足りません。スポットを獲得してコインを集めよう！")
            return
        self.coins -= 50
        prize = random.choice(list(self.tickets))
        self.tickets[prize] += 1
        self.show_message("🎉 {}をゲット！".format(prize))
        self.refresh()

    def reveal_riddle_answer(self, sender):
        sender.title = "答え: {}".format(sender.riddle_answer)
        sender.enabled = False

    def update_location(self, sender):
        self.show_message("位置情報を取得しています…")
        location.start_updates()
        try:
            position = location.get_location()
        finally:
            location.stop_updates()
        if position is None:
            self.show_message("位置情報を取得できません。屋外で位置情報の許可と電波を確認してください。")
            return
        sample = make_location_sample(
            team_id=config.TEAM_ID,
            device_id=config.DEVICE_ID,
            client_time=datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(),
            sample_id=str(uuid.uuid4()),
            location=position,
        )
        collected_coins = self._collect_distance_coins(position)
        result = CheckInService(self.api, self.queue).submit(sample)
        if result.get("queued"):
            self.show_message(
                "通信できないため位置情報を端末に保存しました。\n今回の移動で獲得: {}枚".format(
                    collected_coins
                )
            )
            return
        self.refresh()

    def _riddle_for_place(self, place_id):
        """地点ごとの選択式なぞなぞを返す。正解するまで地点は獲得しない。"""
        place = self.places.get(place_id, {})
        place_name = place.get("name", "")
        for riddle_place, question, answer in PINK_RIDDLES:
            if riddle_place in place_name or place_name in riddle_place:
                return question, answer
        # サーバー側の地点名が変わっても、地点ごとに問題を出せるようにする。
        index = list(self.places).index(place_id) % len(PINK_RIDDLES)
        _, question, answer = PINK_RIDDLES[index]
        return question, answer

    def claim_place(self, sender):
        question, answer = self._riddle_for_place(sender.place_id)
        choices = [answer]
        for _, _, other_answer in PINK_RIDDLES:
            if other_answer not in choices:
                choices.append(other_answer)
            if len(choices) == 3:
                break
        selected = ui.alert(
            "なぞなぞ",
            question,
            *choices,
            hide_cancel_button=False,
        )
        if selected != answer:
            self.show_message("不正解です。もう一度なぞなぞに答えてください。")
            return

        try:
            result = self.api.claim_place(
                action_id=str(uuid.uuid4()),
                game_session_id=config.GAME_SESSION_ID,
                place_id=sender.place_id,
                device_id=config.DEVICE_ID,
            )
        except HTTPError as error:
            self.show_message("獲得できません。\n" + error.read().decode("utf-8"))
            return
        if result["claimed"]:
            self.show_message(
                "正解！ {}班が{}点獲得！".format(
                    config.TEAM_ID, result["score_delta"]
                )
            )
        else:
            self.show_message("この場所は既に獲得済みです。")
        self.refresh()


def run():
    GameView().present("fullscreen")


if __name__ == "__main__":
    run()
