"""Pythonista 3 one-screen interface for a team's location game."""

import datetime
import io
import json
import math
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


LOCATION_MATCH_THRESHOLD_M = 30


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
        self.quest_locations_path = os.path.expanduser("~/Documents/blue-quest-locations.json")
        self.legacy_quest_locations_path = os.path.join(self.repository_directory, "registered-quest-locations.json")
        self.registered_quest_locations = self._load_registered_quest_locations()
        self._ensure_test_game_locations()
        self.completed_quests_path = os.path.join(self.repository_directory, "completed-quests.json")
        self.completed_quests = self._load_completed_quests()
        self.quest_progress_path = os.path.join(self.repository_directory, "quest-progress.json")
        self.quest_progress = self._load_quest_progress()
        self.status_label = ui.Label(frame=(16, 12, 340, 110), flex="W")
        self.status_label.number_of_lines = 0
        self.add_subview(self.status_label)
        self.scroll = ui.ScrollView(frame=(0, 130, 0, 0), flex="WH")
        self.add_subview(self.scroll)
        self.definition = None
        self.state = None
        self.selected_quest = None
        self.pending_photo = None
        self.pending_photo_location = None
        self.in_test_game = False
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

    def _save_registered_quest_locations(self):
        with open(self.quest_locations_path, "w") as destination:
            json.dump(self.registered_quest_locations, destination)

    def _load_registered_quest_locations(self):
        paths = [self.quest_locations_path, self.legacy_quest_locations_path]
        for path in paths:
            try:
                with open(path, "r") as source:
                    locations = json.load(source)
                if isinstance(locations, dict):
                    normalized = {
                        quest_id: self._location_list(value)
                        for quest_id, value in locations.items()
                    }
                    if path != self.quest_locations_path:
                        self.registered_quest_locations = normalized
                        self._save_registered_quest_locations()
                    return normalized
            except (OSError, ValueError):
                continue
        return {}

    def _ensure_test_game_locations(self):
        defaults = {
            "513研修室": {"latitude": 35.67407073059871, "longitude": 139.69317184609355},
            "事務所側入口": {"latitude": 35.67465399946227, "longitude": 139.69315284937827},
            "カフェテリアふじ出口": {"latitude": 35.675026446445194, "longitude": 139.6939601327121},
            "正面入口": {"latitude": 35.67492708549511, "longitude": 139.69340021778783},
        }
        changed = False
        for name, location_value in defaults.items():
            if not self._location_list(self.registered_quest_locations.get(name)):
                self.registered_quest_locations[name] = [location_value]
                changed = True
        if changed:
            self._save_registered_quest_locations()


    def _load_completed_quests(self):
        try:
            with open(self.completed_quests_path, "r") as source:
                completed = json.load(source)
            return set(completed) if isinstance(completed, list) else set()
        except (OSError, ValueError):
            return set()

    def _save_completed_quests(self):
        with open(self.completed_quests_path, "w") as destination:
            json.dump(sorted(self.completed_quests), destination)

    def _load_quest_progress(self):
        try:
            with open(self.quest_progress_path, "r") as source:
                progress = json.load(source)
            return progress if isinstance(progress, dict) else {}
        except (OSError, ValueError):
            return {}

    def _save_quest_progress(self):
        with open(self.quest_progress_path, "w") as destination:
            json.dump(self.quest_progress, destination)

    @staticmethod
    def _location_list(value):
        if isinstance(value, list):
            return value
        if isinstance(value, dict) and "latitude" in value and "longitude" in value:
            return [value]
        return []

    @staticmethod
    def _distance_m(first, second):
        earth_radius_m = 6_371_000
        latitude_delta = math.radians(second["latitude"] - first["latitude"])
        longitude_delta = math.radians(second["longitude"] - first["longitude"])
        haversine = (
            math.sin(latitude_delta / 2) ** 2
            + math.cos(math.radians(first["latitude"]))
            * math.cos(math.radians(second["latitude"]))
            * math.sin(longitude_delta / 2) ** 2
        )
        return 2 * earth_radius_m * math.asin(math.sqrt(haversine))

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
            {"id": "elevator", "name": "エレベーターを2箇所探せ！", "difficulty": "easy", "reward_coins": 20, "required_count": 2},
            {"id": "vending-machine", "name": "自動販売機を3箇所探せ！", "difficulty": "easy", "reward_coins": 20, "required_count": 3},
            {"id": "convenience-store", "name": "D棟のコンビニを探せ！", "difficulty": "normal", "reward_coins": 50, "required_count": 1, "public_location_only": True},
            {"id": "cafeteria-fuji", "name": "カフェテリアふじを探せ！", "difficulty": "normal", "reward_coins": 50},
            {"id": "facility-sign", "name": "施設案内を探せ！", "difficulty": "hard", "reward_coins": 100},
        ]
        for quest in self.available_quests:
            registered = self.registered_quest_locations.get(quest["id"])
            server_quest = next(
                (item for item in definition.get("quests", []) if item.get("id") == quest["id"]),
                {},
            )
            public_location = server_quest.get("target_location")
            if public_location is None and "latitude" in server_quest and "longitude" in server_quest:
                public_location = {
                    "latitude": server_quest["latitude"],
                    "longitude": server_quest["longitude"],
                }
            if public_location is not None:
                quest["target_locations"] = self._location_list(public_location)
            elif registered:
                quest["target_locations"] = self._location_list(registered)
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
        self._add_button("座標を登録する", 72, self.start_registration, accent_color)
        self._add_button("テストゲーム", 132, self.start_test_game, accent_color)
        self.scroll.content_size = (self.width, 200)

    def start_test_game(self, sender):
        preferred = [
            ("513研修室", ("513", "研修室")),
            ("事務所側入口", ("事務所", "office")),
            ("カフェテリアふじ出口", ("ふじ", "カフェテリア")),
            ("正面入口", ("正面", "main")),
        ]
        pairs = []
        for label, keywords in preferred:
            for key, value in self.registered_quest_locations.items():
                key_text = str(key).lower()
                if any(keyword.lower() in key_text for keyword in keywords):
                    locations = self._location_list(value)
                    if locations:
                        pairs.append((label, locations[0]))
                        break
        if len(pairs) < 4:
            all_locations = []
            for value in self.registered_quest_locations.values():
                all_locations.extend(self._location_list(value))
            if len(all_locations) >= 4:
                pairs = [(label, location) for (label, _), location in zip(preferred, all_locations[:4])]
        if len(pairs) < 4:
            self._clear_content()
            self.show_message("テストゲームには4地点の保存済み座標が必要です。\n現在：{}地点".format(len(pairs)))
            self._add_button("ホームにもどる", 12, self.back_to_title, self.status_label.text_color)
            self.scroll.content_size = (self.width, 80)
            return
        self.test_game_quests = [
            {
                "id": "test-{}".format(index),
                "name": "テスト：{}を撮影！".format(label),
                "difficulty": "test",
                "reward_coins": 0,
                "required_count": 1,
                "target_locations": [location],
                "capture_instruction": "{}を撮影してください。".format(label),
            }
            for index, (label, location) in enumerate(pairs, start=1)
        ]
        self.in_test_game = True
        self.render_test_quest_selection(self.status_label.text_color)

    def render_test_quest_selection(self, accent_color):
        self._clear_content()
        self.show_message("テストゲーム\n4つの登録地点からクエストを選択してください")
        y = 12
        for quest in self.test_game_quests:
            label = "✓ クリア済み：" if quest["id"] in self.completed_quests else ""
            button = self._add_button(label + quest["name"], y, self.select_quest, accent_color)
            button.quest = quest
            y += 60
        self._add_button("ホームにもどる", y, self.back_to_title, accent_color)
        self.scroll.content_size = (self.width, y + 76)

    def start_registration(self, sender):
        self.render_registration_quests(self.status_label.text_color)

    def render_registration_quests(self, accent_color):
        self._clear_content()
        self.show_message("登録する対象を選んでください")
        y = 12
        for quest in self.available_quests:
            saved_count = len(self._location_list(self.registered_quest_locations.get(quest["id"])))
            button = self._add_button(
                "{} の座標を登録（保存済み：{}か所）".format(quest["name"], saved_count),
                y,
                self.select_registration_quest,
                accent_color,
            )
            button.quest = quest
            y += 60
        self._add_button("タイトルにもどる", y, self.back_to_title, accent_color)
        self.scroll.content_size = (self.width, y + 76)

    def select_registration_quest(self, sender):
        self.selected_quest = sender.quest
        if self.selected_quest.get("public_location_only"):
            self._clear_content()
            self.show_message("このクエストは公開MAP座標を使用します。館内座標の登録は不要です。")
            self._add_button("対象一覧にもどる", 12, self.start_registration, self.status_label.text_color)
            self.scroll.content_size = (self.width, 80)
            return
        self.render_registration_detail(self.status_label.text_color)

    def render_registration_detail(self, accent_color, message=None):
        self._clear_content()
        locations = self._location_list(self.registered_quest_locations.get(self.selected_quest["id"]))
        self.show_message(message or "{}の座標を登録できます。\n保存済み：{}か所".format(self.selected_quest["name"], len(locations)))
        y = 12
        self._add_button("この場所を追加登録", y, self.register_quest_location, accent_color)
        y += 60
        for index, saved in enumerate(locations, start=1):
            title = "{}: 緯度{} 経度{}".format(index, saved["latitude"], saved["longitude"])
            button = self._add_button(title + " を削除", y, self.delete_registered_location, accent_color)
            button.location_index = index - 1
            y += 60
        self._add_button("対象一覧にもどる", y, self.start_registration, accent_color)
        self.scroll.content_size = (self.width, y + 76)

    def register_quest_location(self, sender):
        location.start_updates()
        try:
            position = location.get_location()
        finally:
            location.stop_updates()
        if position is None:
            self.show_message("位置情報を取得できませんでした。")
            return
        registered = {"latitude": position["latitude"], "longitude": position["longitude"]}
        quest_id = self.selected_quest["id"]
        locations = self._location_list(self.registered_quest_locations.get(quest_id))
        already_saved = any(
            classify_location([saved], registered, threshold_m=LOCATION_MATCH_THRESHOLD_M)["kind"] == "same_position_group"
            for saved in locations
        )
        if already_saved:
            message = "この位置はすでに保存されています。\n保存済み：{}か所".format(len(locations))
        else:
            locations.append(registered)
            self.registered_quest_locations[quest_id] = locations
            self._save_registered_quest_locations()
            message = "座標を保存しました。\n保存済み：{}か所".format(len(locations))
        self.selected_quest["target_locations"] = locations
        self.render_registration_detail(self.status_label.text_color, message)

    def delete_registered_location(self, sender):
        quest_id = self.selected_quest["id"]
        locations = self._location_list(self.registered_quest_locations.get(quest_id))
        index = sender.location_index
        if index < 0 or index >= len(locations):
            return
        locations.pop(index)
        self.registered_quest_locations[quest_id] = locations
        self._save_registered_quest_locations()
        self.selected_quest["target_locations"] = locations
        self.render_registration_detail(
            self.status_label.text_color,
            "座標を削除しました。\n保存済み：{}か所".format(len(locations)),
        )

    def back_to_title(self, sender):
        self.in_test_game = False
        self.render_title_screen(self.status_label.text_color)

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
        self._add_button("ホームにもどる", 72, self.back_to_title, accent_color)
        self.scroll.content_size = (self.width, 140)

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
            label = "✓ クリア済み：" if quest["id"] in self.completed_quests else ""
            button = self._add_button(
                "{}{}  {} / {}コイン".format(
                    label, quest["name"], quest["difficulty"], quest["reward_coins"]
                ),
                y,
                self.select_quest,
                accent_color,
            )
            button.quest = quest
            y += 60
        self._add_button("場所選択にもどる", y, self.back_to_location, accent_color)
        self.scroll.content_size = (self.width, y + 76)

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

    def _get_current_location(self):
        location.start_updates()
        try:
            position = location.get_location()
        finally:
            location.stop_updates()
        if position is None:
            return None
        return {"latitude": position["latitude"], "longitude": position["longitude"]}

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
        captured_location = self._get_current_location()
        if captured_location is None:
            self.show_message("写真は選択できましたが、位置情報を取得できませんでした。")
            return
        self._photo_received(image, "選択した写真", captured_location)

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
        captured_location = self._get_current_location()
        if captured_location is None:
            self.show_message("写真は撮影できましたが、位置情報を取得できませんでした。")
            return
        self._photo_received(image, "撮影した写真", captured_location)

    @staticmethod
    def _preview_image(image):
        """Convert Pythonista's PIL result to a ui.Image without photos helpers."""
        if isinstance(image, ui.Image):
            return image
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return ui.Image.from_data(buffer.getvalue())

    def _photo_received(self, image, source_label, captured_location):
        self.pending_photo = image
        self.pending_photo_location = captured_location
        self._clear_content()
        self.show_message(
            "{}を受け取りました。\n".format(source_label)
            + "人がエレベーターだと確認したら、GPSで同じ位置か調べます。\n"
            + "写真はサーバーへ送信しません。"
        )
        preview = ui.ImageView(frame=(16, 12, self.width - 32, 180))
        preview.image = self._preview_image(image)
        preview.content_mode = ui.CONTENT_SCALE_ASPECT_FIT
        preview.flex = "W"
        self.scroll.add_subview(preview)
        self._add_button(
            "人が確認した → GPSで位置を比べる",
            204,
            self.confirm_elevator_position,
            self.status_label.text_color,
        )
        self._add_button(
            "写真を端末に保存",
            264,
            self.save_pending_photo,
            self.status_label.text_color,
        )
        self._add_button("クエスト画面にもどる", 324, self.back_to_capture, self.status_label.text_color)
        self.scroll.content_size = (self.width, 392)

    def save_pending_photo(self, sender):
        if self.pending_photo is None:
            self.show_message("保存する写真がありません。")
            return
        try:
            photo_directory = os.path.expanduser("~/Documents/blue-photos")
            if not os.path.isdir(photo_directory):
                os.makedirs(photo_directory)
            filename = "photo-{}.png".format(datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
            path = os.path.join(photo_directory, filename)
            png_data = self._preview_image(self.pending_photo).to_png()
            with open(path, "wb") as destination:
                destination.write(png_data)
        except (OSError, ValueError, TypeError) as error:
            self.show_message("写真を保存できません。\n{}".format(error))
            return
        self.show_message("写真を保存しました。\n{}".format(path))

    def confirm_elevator_position(self, sender):
        self.show_message("写真を撮った時点のGPS位置で判定しています…")
        position = self.pending_photo_location
        if position is None:
            self.show_message("写真撮影時の位置情報がありません。もう一度撮影してください。")
            return
        candidate = {
            "latitude": position["latitude"],
            "longitude": position["longitude"],
        }
        targets = self._location_list(
            self.selected_quest.get("target_locations")
            or self.selected_quest.get("target_location")
        )
        if not targets:
            self.render_capture_screen(self.status_label.text_color)
            self.show_message("このクエストの座標が未登録です。スタッフが座標を登録してください。")
            return
        nearest_index, nearest_target = min(
            enumerate(targets),
            key=lambda item: self._distance_m(candidate, item[1]),
        )
        nearest_distance = self._distance_m(candidate, nearest_target)
        distance_message = "最寄りの保存位置まで約{}m".format(round(nearest_distance))
        if nearest_distance > LOCATION_MATCH_THRESHOLD_M:
            self.render_capture_screen(self.status_label.text_color)
            self.show_message("{}\n{}mを超えているため失敗です。".format(distance_message, LOCATION_MATCH_THRESHOLD_M))
            return
        quest_id = self.selected_quest["id"]
        found = set(self.quest_progress.get(quest_id, []))
        required_count = self.selected_quest.get("required_count", len(targets))
        if nearest_index in found:
            self.render_capture_screen(self.status_label.text_color)
            self.show_message("{}\nこの位置は登録済みです。別の場所を探してください。".format(distance_message))
            return
        found.add(nearest_index)
        self.quest_progress[quest_id] = sorted(found)
        self._save_quest_progress()
        if len(found) >= required_count:
            self.completed_quests.add(quest_id)
            self._save_completed_quests()
            self.render_completion_screen(self.status_label.text_color)
            return
        self.render_capture_screen(self.status_label.text_color)
        self.show_message(
            "{}\n{} / {}箇所を発見しました。次の場所を探してください。".format(
                distance_message, len(found), required_count
            )
        )

    def render_completion_screen(self, accent_color):
        self._clear_content()
        quest = self.selected_quest
        self.show_message(
            "おめでとう！\n"
            "{}をクリアしました。\n"
            "報酬はコイン{}枚だよ！".format(quest["name"], quest["reward_coins"])
        )
        self._add_button("別のクエストに挑戦する", 12, self.back_to_quests, accent_color)
        self._add_button("ホームに戻る", 72, self.back_to_title, accent_color)
        self.scroll.content_size = (self.width, 140)

    def back_to_quests(self, sender):
        if self.in_test_game:
            self.render_test_quest_selection(self.status_label.text_color)
        else:
            self.render_quest_selection(self.status_label.text_color)

    def back_to_capture(self, sender):
        self.render_capture_screen(self.status_label.text_color)

    def back_to_location(self, sender):
        self.render_location_selection(self.status_label.text_color)


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
