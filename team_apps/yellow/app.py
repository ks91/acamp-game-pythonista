"""イエロー班：東京ご当地エジプト探検のDay 2アプリ。"""

import datetime
import hashlib
import json
import os
import sys
import threading
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import location
import ui


REPOSITORY_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPOSITORY_ROOT not in sys.path:
    sys.path.insert(0, REPOSITORY_ROOT)

try:
    import config
except ImportError:
    config = None

from toolkit.api_client import ApiClient
from toolkit.check_in import CheckInService
from toolkit.event_queue import EventQueue
from toolkit.location_payload import make_location_sample


TEAM_COLOR = "#F9A825"
COMPLETION_BONUS = 2

SPOT_STORIES = {
    "sphinx": {
        "names": {"ファン カフェ", "ファンカフェ", "513研修室", "渋谷ハチ公前"},
        "ids": {"fan-cafe", "sphinx"},
        "display_name": "スフィンクス",
        "item_name": "スフィンクス",
        "photo_label": "2枚目",
        "image_filename": "sphinx.jpeg",
        "rare_image_filename": "shubaru-sphinx.jpeg",
        "rare_display_name": "シュバルスフィンクス",
        "rare_item_name": "シュバルスフィンクス",
        "description": "センター棟テスト版では513研修室、東京版では渋谷ハチ公前を守るスフィンクス。",
    },
    "pyramid": {
        "names": {"YCAP", "正面玄関", "ガラスのピラミッド"},
        "ids": {"ycap", "pyramid"},
        "display_name": "ピラミッド",
        "item_name": "ピラミッド",
        "photo_label": "1枚目",
        "image_filename": "pyramid.jpeg",
        "rare_image_filename": "shubaru-pyramid.jpeg",
        "rare_display_name": "シュバルピラミッド",
        "rare_item_name": "シュバルピラミッド",
        "description": "センター棟テスト版では正面玄関、東京版ではガラスのピラミッドを探す。",
    },
}

SPOT_ORDER = ("pyramid", "sphinx")
CHARACTER_CATALOG = (
    ("pyramid", "シュバルピラミッド"),
    ("sphinx", "シュバルスフィンクス"),
    ("pyramid", "ピラミッド"),
    ("sphinx", "スフィンクス"),
)


def _story_for(place):
    for key in SPOT_ORDER:
        story = SPOT_STORIES[key]
        if place.get("id") in story.get("ids", set()) or place.get("name") in story["names"]:
            return key, story
    return None, None


class YellowEgyptGame(ui.View):
    def __init__(self):
        screen_width, screen_height = ui.get_screen_size()
        if screen_width < screen_height:
            screen_width, screen_height = screen_height, screen_width
        super().__init__(frame=(0, 0, screen_width, screen_height))
        self.flex = "WH"
        self.name = "とうエジGO!"
        self.background_color = "#FFF8E1"
        self.api = None
        self.repository_directory = os.path.dirname(os.path.abspath(__file__))
        self.queue = EventQueue(os.path.join(self.repository_directory, "pending-events.json"))
        self.definition = None
        self.state = None
        self.place_buttons = []
        self.reset_button = None
        self.reset_confirmation_pending = False
        self.reset_timer = None
        self.status_label = self._label(
            "位置情報を読み込んでいます…", (16, 14, screen_width - 32, 84), ("<system-bold>", 17), TEAM_COLOR
        )
        self.add_subview(self.status_label)
        self.content = ui.ScrollView(frame=(0, 105, screen_width, screen_height - 105), flex="WH")
        self.add_subview(self.content)
        if config is None:
            self.status_label.text = "設定ファイル config.py が見つかりません。"
            self._render_message(
                "Working Copyでリポジトリ全体をPullしたあと、\n"
                "config.example.pyをconfig.pyとして複製し、\n"
                "スタッフから渡された設定値を入れてください。"
            )
            return
        self.api = ApiClient(base_url=config.API_BASE_URL, token=config.GAME_TOKEN)
        self.status_label.text = "ゲームを最初の状態に戻しています…"
        threading.Thread(target=self._restart_test_session, daemon=True).start()

    def _label(self, text, frame, font=("<system>", 15), color="#4E342E", align=ui.ALIGN_LEFT):
        label = ui.Label(frame=frame)
        label.text = text
        label.font = font
        label.text_color = color
        label.alignment = align
        label.number_of_lines = 0
        return label

    def _button(self, title, frame, action, enabled=True):
        button = ui.Button(frame=frame)
        button.title = title
        button.font = ("<system-bold>", 16)
        button.tint_color = "white"
        button.background_color = TEAM_COLOR
        button.corner_radius = 10
        button.action = action
        button.enabled = enabled
        button.alpha = 1.0 if enabled else 0.45
        return button

    def _clear_content(self):
        for view in list(self.content.subviews):
            self.content.remove_subview(view)
        self.place_buttons = []

    def _target_places(self):
        places = []
        for place in (self.definition or {}).get("places", []):
            key, story = _story_for(place)
            if key and story:
                places.append((key, story, place))
        return sorted(places, key=lambda item: SPOT_ORDER.index(item[0]))

    def _canonical_place_id(self, key, place):
        """表示地点名にかかわらず、APIのキャラクター地点IDへ変換する。"""
        if key == "pyramid":
            return "pyramid"
        if key == "sphinx":
            return "sphinx"
        return place.get("id", key)

    def _place_aliases(self, key, place):
        return {place.get("id"), self._canonical_place_id(key, place)}

    def _claimed_ids(self):
        claimed = set((self.state or {}).get("claimed_places", []))
        for key, _story, place in self._target_places():
            if claimed.intersection(self._place_aliases(key, place)):
                claimed.add(place["id"])
        return claimed

    def _is_rare(self, key, place_id):
        team_id = getattr(config, "TEAM_ID", "yellow") if config is not None else "yellow"
        session_id = getattr(config, "GAME_SESSION_ID", "prototype-yellow-1") if config is not None else "prototype-yellow-1"
        seed = "{}:{}:{}".format(team_id, session_id, key or place_id)
        value = int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8], 16) % 100
        return value < 40

    def _effective_story(self, key, story, place):
        effective = dict(story)
        if self._is_rare(key, place.get("id", key)):
            effective["display_name"] = effective.get(
                "rare_display_name", "シュバル" + effective["display_name"]
            )
            effective["item_name"] = effective.get(
                "rare_item_name", "シュバル" + effective["item_name"]
            )
            if effective.get("rare_image_filename"):
                effective["image_filename"] = effective["rare_image_filename"]
        return effective

    def _story_for_claim(self, story_key, place_id):
        for key, story, place in self._target_places():
            if key == story_key and place_id in self._place_aliases(key, place):
                return self._effective_story(key, story, place)
        return SPOT_STORIES[story_key]

    def refresh(self):
        try:
            self.definition = self.api.get_game_definition()
            self.state = self.api.get_team_state()
        except OSError as error:
            self.status_label.text = "サーバーへ接続できません。\n{}".format(error)
            self._render_message("通信を確認してから、もう一度「現在地を送る」を試してください。")
            return
        self._render()

    def _render(self, message=""):
        self._clear_content()
        claimed_ids = self._claimed_ids()
        target_places = self._target_places()
        target_count = len(SPOT_ORDER)
        claimed_count = sum(place[2]["id"] in claimed_ids for place in target_places)
        server_score = (self.state or {}).get("score", 0)
        bonus_text = "\nコンプリート！ ボーナス{}点の対象".format(COMPLETION_BONUS) if claimed_count == target_count else ""
        self.status_label.text = (
            "とうエジGO!\n"
            "発見: {}/{}　班の得点: {}点{}"
        ).format(claimed_count, target_count, server_score, bonus_text)

        y = 12
        update_button = self._button("位置情報を更新（GPS）", (16, y, self.width - 32, 48), self.update_location)
        self.content.add_subview(update_button)
        y += 64
        reset_button = self._button(
            "最初からやり直す",
            (16, y, self.width - 32, 48),
            self.request_test_session_restart,
        )
        self.reset_button = reset_button
        reset_button.background_color = "#8D6E63"
        self.content.add_subview(reset_button)
        y += 64
        items_button = self._button(
            "獲得済みアイテムを見る",
            (16, y, self.width - 32, 48),
            self.show_collected_items,
        )
        items_button.background_color = "#6D4C41"
        self.content.add_subview(items_button)
        y += 64
        if message:
            notice = self._label(message, (20, y, 335, 60), ("<system-bold>", 16), TEAM_COLOR)
            self.content.add_subview(notice)
            y += 72

        places_by_key = {key: (story, place) for key, story, place in target_places}
        character_title = self._label(
            "現在地からキャラクターを獲得（各スポット半径60m以内）",
            (16, y, self.width - 32, 50),
            ("<system-bold>", 18),
            TEAM_COLOR,
        )
        self.content.add_subview(character_title)
        y += 60

        # スタッフ決定の2地点だけを獲得ボタンとして表示する。
        # 実際の半径判定は、現在地を受け取るサーバー側で行う。
        for key in SPOT_ORDER:
            entry = places_by_key.get(key)
            if entry is None:
                continue
            base_story, place = entry
            claimed = place["id"] in claimed_ids
            story = self._effective_story(key, base_story, place) if claimed else base_story
            location_name = place.get("name", "指定スポット")
            points = place.get("points", 0)
            text = (
                "✓ {}を獲得済み\n{}"
                if claimed
                else "{}を獲得\n{}"
            ).format(story["display_name"], location_name)
            button = self._button(
                text,
                (16, y, self.width - 32, 62),
                self.claim_place,
                enabled=not claimed,
            )
            button.place_id = place["id"]
            button.story_key = key
            self.content.add_subview(button)
            self.place_buttons.append(button)
            y += 70
            if claimed:
                description = self._label(
                    "{}（{}点）\n{}".format(story["display_name"], points, story["description"]),
                    (24, y, self.width - 48, 62),
                    ("<system>", 14),
                )
                self.content.add_subview(description)
                y += 76

        if target_count and claimed_count == target_count:
            complete = self._label(
                "{}種類コンプリート！\nボーナス{}点の対象".format(target_count, COMPLETION_BONUS),
                (20, y + 8, 335, 56),
                ("<system-bold>", 18),
                TEAM_COLOR,
                ui.ALIGN_CENTER,
            )
            self.content.add_subview(complete)
            y += 72
        self.content.content_size = (self.width, y + 24)

    def _render_message(self, message):
        self._clear_content()
        label = self._label(message, (20, 16, 335, 120), ("<system>", 16))
        self.content.add_subview(label)
        retry = self._button("もう一度読み込む", (16, 150, 343, 48), lambda sender: self.refresh())
        self.content.add_subview(retry)
        self.content.content_size = (self.width, 220)

    def _asset_image(self, story):
        filename = story.get("image_filename")
        if not filename:
            return None
        return ui.Image.named(os.path.join(self.repository_directory, "assets", filename))

    def show_collected_items(self, sender):
        self._clear_content()
        claimed_ids = self._claimed_ids()
        target_places = {place["id"]: (key, story, place) for key, story, place in self._target_places()}
        left_width = int(self.width * 0.45)
        right_x = left_width + 24
        right_width = self.width - right_x - 24
        catalog = [
            ("pyramid", "シュバルピラミッド", "shubaru-pyramid.jpeg"),
            ("sphinx", "シュバルスフィンクス", "shubaru-sphinx.jpeg"),
            ("pyramid", "ピラミッド", "pyramid.jpeg"),
            ("sphinx", "スフィンクス", "sphinx.jpeg"),
        ]
        self.status_label.text = "ご当地エジプト図鑑"
        back_button = self._button("ゲーム画面にもどる", (16, 12, self.width - 32, 44), lambda button: self._render())
        self.content.add_subview(back_button)

        preview = ui.ImageView(frame=(16, 72, left_width, 300))
        preview.content_mode = ui.CONTENT_SCALE_ASPECT_FIT
        self.content.add_subview(preview)
        detail = self._label("図鑑からキャラクターを選んでください。", (16, 385, left_width, 160), ("<system>", 16))
        self.content.add_subview(detail)

        def select_item(button):
            entry = button.entry
            if not entry["discovered"]:
                preview.image = ui.Image.named(os.path.join(self.repository_directory, "assets", entry["filename"]))
                preview.alpha = 0.22
                preview.background_color = "#222222"
                detail.text = "{}\n\nこのキャラクターの場所に近づいて、\nこの名前を押すと獲得できます。".format(entry["name"])
                return
            preview.alpha = 1.0
            preview.background_color = "#FFF8E1"
            story = entry["story"]
            preview.image = self._asset_image(story)
            detail.text = "{}\n\n基本情報\nレア度：{}\n発見場所：{}\n\n{}".format(
                story["display_name"], "★2" if story["display_name"].startswith("シュバル") else "★1",
                entry["place"].get("name", "不明"), story["description"]
            )

        entries = []
        for place_id, expected_name, filename in catalog:
            source = target_places.get(place_id)
            discovered = False
            story = None
            place = source[2] if source else {"id": place_id, "name": ""}
            if source and place_id in claimed_ids:
                effective = self._effective_story(source[0], source[1], source[2])
                if effective["display_name"] == expected_name:
                    discovered = True
                    story = effective
            entries.append({"name": expected_name, "filename": filename, "discovered": discovered, "story": story, "place": place, "story_key": source[0] if source else None})

        discovered_entries = [entry for entry in entries if entry["discovered"]]
        unknown_entries = [entry for entry in entries if not entry["discovered"]]
        claimed_order = (self.state or {}).get("claimed_places", [])
        discovered_entries.sort(
            key=lambda entry: claimed_order.index(entry["place"]["id"])
            if entry["place"]["id"] in claimed_order else len(claimed_order)
        )
        entries = discovered_entries + unknown_entries

        y = 72
        for entry in entries:
            title = entry["name"]
            button = self._button(title, (right_x, y, right_width, 56), self.activate_encyclopedia_entry)
            button.entry = entry
            self.content.add_subview(button)
            y += 58
        self.content.content_size = (self.width, max(500, y + 24))
        select_item(type("InitialSelection", (), {"entry": entries[0]})())

    def activate_encyclopedia_entry(self, sender):
        entry = sender.entry
        if entry["discovered"]:
            self.show_collected_items(sender)
            return
        if not entry.get("story_key"):
            self._render_message("このキャラクターの場所がまだ設定されていません。")
            return
        claim_sender = type(
            "EncyclopediaClaim",
            (),
            {"place_id": entry["place"]["id"], "story_key": entry["story_key"]},
        )()
        self.claim_place(claim_sender)

    def request_test_session_restart(self, sender):
        if not self.reset_confirmation_pending:
            self.reset_confirmation_pending = True
            sender.title = "もう一度押すと最初から"
            if self.reset_timer is not None:
                self.reset_timer.cancel()
            self.reset_timer = threading.Timer(8.0, self._clear_reset_confirmation)
            self.reset_timer.daemon = True
            self.reset_timer.start()
            return
        self.reset_confirmation_pending = False
        if self.reset_timer is not None:
            self.reset_timer.cancel()
            self.reset_timer = None
        sender.enabled = False
        sender.title = "初期化中…"
        threading.Thread(target=self._restart_test_session, daemon=True).start()

    def _clear_reset_confirmation(self):
        def clear():
            self.reset_confirmation_pending = False
            self.reset_timer = None
            if self.reset_button is not None:
                self.reset_button.title = "最初からやり直す"
        ui.delay(clear, 0)

    def _restart_test_session(self):
        try:
            request = Request(
                config.API_BASE_URL.rstrip("/") + "/test-session/restart",
                data=json.dumps({"confirm": True}).encode("utf-8"),
                headers={
                    "Accept": "application/json",
                    "Authorization": "Bearer " + config.GAME_TOKEN,
                    "Content-Type": "application/json; charset=utf-8",
                },
                method="POST",
            )
            with urlopen(request, timeout=15) as response:
                result = json.loads(response.read().decode("utf-8"))
            ui.delay(lambda: self._handle_restart_result(result), 0)
        except HTTPError as error:
            try:
                body = error.read().decode("utf-8").strip()
            except Exception:
                body = ""
            detail = body or getattr(error, "reason", "") or "詳細なし"
            error_text = "HTTP {}: {}".format(error.code, detail)
            ui.delay(lambda message=error_text: self._handle_restart_error(message), 0)
        except URLError as error:
            reason = getattr(error, "reason", "") or "詳細なし"
            error_text = "通信エラー: {}".format(reason)
            ui.delay(lambda message=error_text: self._handle_restart_error(message), 0)
        except (OSError, ValueError) as error:
            error_text = "{}: {}".format(type(error).__name__, str(error) or "詳細なし")
            ui.delay(lambda message=error_text: self._handle_restart_error(message), 0)

    def _handle_restart_result(self, result):
        if self.reset_button is not None:
            self.reset_button.enabled = True
            self.reset_button.title = "最初からやり直す"
        if result.get("success", result.get("restarted", True)) is False:
            self._render("テストを最初からに戻せませんでした。\n{}".format(result))
            return
        self.refresh()
        self._render("テストを最初からに戻しました。")

    def _handle_restart_error(self, error_message):
        if self.reset_button is None:
            self.refresh()
            self._render("最初からやり直せませんでした。\n{}".format(error_message))
            return
        self.reset_button.enabled = True
        self.reset_button.title = "最初からやり直す"
        self._render_message("テストを最初からに戻せませんでした。\n{}".format(error_message))

    def update_location(self, sender):
        self.status_label.text = "位置情報を取得しています…"
        location.start_updates()
        try:
            position = location.get_location()
        finally:
            location.stop_updates()
        if position is None:
            self.status_label.text = "位置情報を取得できません。"
            self._render_message("安全な場所で、位置情報の許可と電波を確認して再試行してください。")
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
            self._render_message("通信できないため位置情報を端末に保存しました。\n次回、現在地を送ると再送します。")
            return
        self.refresh()

    def claim_place(self, sender):
        try:
            configured_place_id = sender.place_id
            place_id = configured_place_id
            for key, _story, place in self._target_places():
                if key == sender.story_key and place.get("id") == configured_place_id:
                    place_id = self._canonical_place_id(key, place)
                    break
            result = self.api.claim_place(
                action_id=str(uuid.uuid4()),
                game_session_id=config.GAME_SESSION_ID,
                place_id=place_id,
                device_id=config.DEVICE_ID,
            )
        except HTTPError as error:
            self._render_message("獲得できません。\n" + error.read().decode("utf-8"))
            return
        if result.get("claimed"):
            story = self._story_for_claim(sender.story_key, sender.place_id)
            self.refresh()
            self._render(
                "{}を発見！\n図鑑に登録されました。\nこのスポットの得点：{}点\n現在の班の得点：{}点".format(
                    story["display_name"], result["score_delta"], result["team_score"]
                )
            )
        else:
            self.refresh()
            self._render("この場所はすでに図鑑へ登録されています。")


def run():
    YellowEgyptGame().present("fullscreen")


if __name__ == "__main__":
    run()
