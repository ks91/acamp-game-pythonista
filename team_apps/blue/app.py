"""Pythonista 3 one-screen interface for a team's location game."""

import datetime
import json
import os
import uuid
from urllib.error import HTTPError

import location
import ui

import config
from toolkit.api_client import ApiClient
from toolkit.check_in import CheckInService
from toolkit.event_queue import EventQueue
from toolkit.game_view_model import build_game_view_model
from toolkit.location_payload import make_location_sample
from team_apps.blue.elevator_locations import classify_location
from toolkit.quest_flow import build_quest_cards, capture_instruction


class GameView(ui.View):
    def __init__(self):
        super().__init__(frame=(0, 0, 375, 667))
        self.name = "アカキャン位置ゲー"
        self.background_color = "white"
        self.api = ApiClient(
            base_url=config.API_BASE_URL,
            token=config.GAME_TOKEN,
            game_team_id=getattr(config, "SELECTED_GAME_TEAM_ID", None),
        )
        self.repository_directory = os.path.dirname(os.path.abspath(__file__))
        self.queue = EventQueue(os.path.join(self.repository_directory, "pending-events.json"))
        self.elevator_locations_path = os.path.join(self.repository_directory, "confirmed-elevators.json")
        self.confirmed_elevators = self._load_confirmed_elevators()
        self.status_label = ui.Label(frame=(16, 12, 340, 110), flex="W")
        self.status_label.number_of_lines = 0
        self.add_subview(self.status_label)
        self.scroll = ui.ScrollView(frame=(0, 130, 0, 0), flex="WH")
        self.add_subview(self.scroll)
        self.definition = None
        self.state = None
        self.selected_quest = None
        self.refresh()

    def layout(self):
        self.status_label.frame = (16, 12, self.width - 32, 110)
        self.scroll.frame = (0, 130, self.width, self.height - 130)

    def show_message(self, message):
        self.status_label.text = message

    def _load_confirmed_elevators(self):
        try:
            with open(self.elevator_locations_path, "r") as source:
                locations = json.load(source)
            return locations if isinstance(locations, list) else []
        except (OSError, ValueError):
            return []

    def _save_confirmed_elevators(self):
        with open(self.elevator_locations_path, "w") as destination:
            json.dump(self.confirmed_elevators, destination)

    def refresh(self):
        try:
            definition = self.api.get_game_definition()
            state = self.api.get_team_state()
        except OSError as error:
            self.show_message("サーバーへ接続できません。\n{}".format(error))
            return
        self.definition = definition
        self.state = state
        model = build_game_view_model(definition, state, config.TEAM_ID)
        self.model = model
        theme = model["theme"]
        accent_color = theme["accent_color"]
        self.background_color = theme["background_color"]
        self.status_label.text_color = accent_color
        self.places = {place["id"]: place for place in definition.get("places", [])}
        self.available_quests = build_quest_cards(definition) or [
            {
                "id": "find-two-elevators",
                "name": "エレベーターを2個探せ！",
                "difficulty": "easy",
                "reward_coins": 20,
                "hint": "",
                "type": "elevator",
            }
        ]
        self.render_title_screen(accent_color)

    def _clear_content(self):
        for view in list(self.scroll.subviews):
            self.scroll.remove_subview(view)

    def _add_button(self, title, y, action, accent_color):
        button = ui.Button(title=title, frame=(16, y, self.width - 32, 48))
        button.action = action
        button.tint_color = accent_color
        self.scroll.add_subview(button)
        return button

    def render_title_screen(self, accent_color):
        self._clear_content()
        self.show_message("blue位置ゲー開発（仮）")
        self._add_button("開始", 12, self.start_game, accent_color)
        self.scroll.content_size = (self.width, 80)

    def start_game(self, sender):
        self.render_location_selection(self.status_label.text_color)

    def render_location_selection(self, accent_color):
        self._clear_content()
        self.show_message("場所を選択してください")
        self._add_button(
            self.definition.get("name", "オリンピックセンター"),
            12,
            self.select_location,
            accent_color,
        )
        self.scroll.content_size = (self.width, 80)

    def select_location(self, sender):
        self.render_quest_selection(self.status_label.text_color)

    def render_quest_selection(self, accent_color):
        self._clear_content()
        self.show_message(
            "オリンピックセンター探索イベント（仮）\n"
            "オリンピックセンターの中を歩いて、\n"
            "身近なものをカメラで探してみよう！\n\n"
            "クエストを選択してください"
        )
        y = 12
        for quest in self.available_quests:
            button = self._add_button(
                "{}  {} / {}コイン".format(
                    quest["name"], quest["difficulty"], quest["reward_coins"]
                ),
                y,
                self.select_quest,
                accent_color,
            )
            button.quest = quest
            y += 60
        self.scroll.content_size = (self.width, y + 16)

    def select_quest(self, sender):
        self.selected_quest = sender.quest
        self.render_capture_screen(self.status_label.text_color)

    def render_capture_screen(self, accent_color):
        self._clear_content()
        quest = self.selected_quest
        self.show_message("{}\n{}".format(quest["name"], capture_instruction(quest)))
        select_button = self._add_button("写真を選択", 12, self.select_photo, accent_color)
        select_button.tint_color = accent_color
        camera_button = self._add_button("写真を撮影", 72, self.take_photo, accent_color)
        camera_button.tint_color = accent_color
        back_button = self._add_button("クエスト一覧にもどる", 132, self.back_to_quests, accent_color)
        back_button.tint_color = accent_color
        self.scroll.content_size = (self.width, 200)

    def select_photo(self, sender):
        try:
            import photos
            image = photos.pick_image(show_albums=True)
        except (ImportError, OSError) as error:
            self.show_message("写真を選択できません。\n{}".format(error))
            return
        if image is None:
            self.show_message("写真の選択をキャンセルしました。\n" + capture_instruction(self.selected_quest))
            return
        self._photo_received(image, "選択した写真")

    def take_photo(self, sender):
        try:
            import photos
            image = photos.capture_image()
        except (ImportError, OSError) as error:
            self.show_message("カメラを起動できません。\n{}".format(error))
            return
        if image is None:
            self.show_message("写真の撮影をキャンセルしました。\n" + capture_instruction(self.selected_quest))
            return
        self._photo_received(image, "撮影した写真")

    def _photo_received(self, image, source_label):
        self._clear_content()
        self.show_message(
            "{}を受け取りました。\n".format(source_label)
            + "人がエレベーターだと確認したら、GPSで同じ位置か調べます。\n"
            + "写真はサーバーへ送信しません。"
        )
        preview = ui.ImageView(frame=(16, 12, self.width - 32, 180))
        preview.image = image
        preview.content_mode = ui.CONTENT_SCALE_ASPECT_FIT
        preview.flex = "W"
        self.scroll.add_subview(preview)
        self._add_button(
            "人が確認した → GPSで位置を比べる",
            204,
            self.confirm_elevator_position,
            self.status_label.text_color,
        )
        self._add_button("クエスト一覧にもどる", 264, self.back_to_quests, self.status_label.text_color)
        self.scroll.content_size = (self.width, 332)

    def confirm_elevator_position(self, sender):
        self.show_message("GPS位置を取得しています…")
        location.start_updates()
        try:
            position = location.get_location()
        finally:
            location.stop_updates()
        if position is None:
            self.show_message("位置情報を取得できません。屋外で位置情報の許可と電波を確認してください。")
            return
        candidate = {
            "latitude": position["latitude"],
            "longitude": position["longitude"],
        }
        result = classify_location(self.confirmed_elevators, candidate, threshold_m=10)
        if result["kind"] == "same_position_group":
            self.show_message(
                "同じ位置グループのエレベーターです。\n"
                "階違いの可能性があります。新しい発見には数えません。"
            )
            return
        self.confirmed_elevators.append(candidate)
        self._save_confirmed_elevators()
        self.show_message(
            "別の位置グループのエレベーターを発見！\n"
            "現在 {} か所。GPS記録はこのiPad内に保存しました。".format(
                len(self.confirmed_elevators)
            )
        )

    def back_to_quests(self, sender):
        self.render_quest_selection(self.status_label.text_color)


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
        result = CheckInService(self.api, self.queue).submit(sample)
        if result.get("queued"):
            self.show_message("通信できないため位置情報を端末に保存しました。次回更新時に再送します。")
            return
        self.refresh()

    def claim_place(self, sender):
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
            self.show_message("{} を獲得！ +{}点".format(result["place_id"], result["score_delta"]))
        else:
            self.show_message("この場所は既に獲得済みです。")
        self.refresh()


def run():
    GameView().present("fullscreen")


if __name__ == "__main__":
    run()
