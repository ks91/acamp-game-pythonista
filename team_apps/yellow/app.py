"""イエロー班：東京ご当地エジプト探検のDay 2アプリ。"""

import datetime
import hashlib
import os
import sys
import uuid
from urllib.error import HTTPError

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
    "fan-cafe": {
        "names": {"ファン カフェ", "ファンカフェ"},
        "display_name": "ハチ公スフィンクス",
        "item_name": "スフィンクス",
        "photo_label": "2枚目",
        "image_filename": "sphinx.png",
        "rare_image_filename": "shubaru-sphinx.jpeg",
        "description": "東京の忠犬ハチ公と、古代エジプトのスフィンクスが合体した守り神。",
    },
    "ycap": {
        "names": {"YCAP"},
        "display_name": "ピラミッド",
        "item_name": "ピラミッド",
        "photo_label": "1枚目",
        "image_filename": "pyramid.jpeg",
        "description": "YCAPの冒険を、知恵と協力で登るピラミッドに見立てた場所。",
    },
    "sakura-namiki": {
        "names": {"桜並木"},
        "display_name": "ナイル川",
        "description": "桜の道を、東京の仲間と進むナイル川の探検コースに見立てた場所。",
    },
    "center-building": {
        "names": {"センター棟"},
        "display_name": "アヌビス",
        "item_name": "ファラオ",
        "photo_label": "3枚目",
        "image_filename": "pharaoh.jpeg",
        "description": "センター棟を、みんなの活動を見守る犬の神アヌビスの神殿に見立てた場所。",
    },
}

SPOT_ORDER = ("fan-cafe", "ycap", "sakura-namiki", "center-building")


def _story_for(place):
    for key in SPOT_ORDER:
        story = SPOT_STORIES[key]
        if place.get("id") == key or place.get("name") in story["names"]:
            return key, story
    return None, None


class YellowEgyptGame(ui.View):
    def __init__(self):
        super().__init__(frame=(0, 0, 375, 667))
        self.name = "イエロー班 東京ご当地エジプト"
        self.background_color = "#FFF8E1"
        self.api = None
        self.repository_directory = os.path.dirname(os.path.abspath(__file__))
        self.queue = EventQueue(os.path.join(self.repository_directory, "pending-events.json"))
        self.definition = None
        self.state = None
        self.place_buttons = []
        self.status_label = self._label(
            "位置情報を読み込んでいます…", (16, 14, 343, 98), ("<system-bold>", 17), TEAM_COLOR
        )
        self.add_subview(self.status_label)
        self.content = ui.ScrollView(frame=(0, 120, 375, 547), flex="WH")
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
        self.refresh()

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

    def _claimed_ids(self):
        return set((self.state or {}).get("claimed_places", []))

    def _is_rare(self, key, place_id):
        team_id = getattr(config, "TEAM_ID", "yellow") if config is not None else "yellow"
        session_id = getattr(config, "GAME_SESSION_ID", "prototype-yellow-1") if config is not None else "prototype-yellow-1"
        seed = "{}:{}:{}".format(team_id, session_id, key or place_id)
        value = int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8], 16) % 100
        return value < 40

    def _effective_story(self, key, story, place):
        effective = dict(story)
        if self._is_rare(key, place.get("id", key)):
            effective["display_name"] = "シュバル" + effective["display_name"]
            effective["item_name"] = "シュバル" + effective["item_name"]
            if effective.get("rare_image_filename"):
                effective["image_filename"] = effective["rare_image_filename"]
        return effective

    def _story_for_claim(self, story_key, place_id):
        for key, story, place in self._target_places():
            if key == story_key and place["id"] == place_id:
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
            "イエロー班｜東京ご当地エジプト\n"
            "発見: {}/{}　班の得点: {}点{}"
        ).format(claimed_count, target_count, server_score, bonus_text)

        y = 12
        update_button = self._button("位置情報を更新（GPS）", (16, y, 343, 48), self.update_location)
        self.content.add_subview(update_button)
        y += 64
        reset_button = self._button(
            "得点をリセット（スタッフ操作）",
            (16, y, 343, 48),
            self.show_reset_notice,
        )
        reset_button.background_color = "#8D6E63"
        self.content.add_subview(reset_button)
        y += 64
        items_button = self._button(
            "獲得済みアイテムを見る",
            (16, y, 343, 48),
            self.show_collected_items,
        )
        items_button.background_color = "#6D4C41"
        self.content.add_subview(items_button)
        y += 64
        restart_button = self._button(
            "はじめから",
            (16, y, 343, 48),
            self.show_restart_notice,
        )
        restart_button.background_color = "#455A64"
        self.content.add_subview(restart_button)
        y += 64

        if message:
            notice = self._label(message, (20, y, 335, 60), ("<system-bold>", 16), TEAM_COLOR)
            self.content.add_subview(notice)
            y += 72

        places_by_key = {key: (story, place) for key, story, place in target_places}
        for key in SPOT_ORDER:
            story = SPOT_STORIES[key]
            entry = places_by_key.get(key)
            if entry is None:
                button = self._button(
                    "？？？（設定待ち）",
                    (16, y, 343, 52),
                    lambda sender: None,
                    enabled=False,
                )
                self.content.add_subview(button)
                y += 60
                continue
            story, place = entry
            story = self._effective_story(key, story, place)
            claimed = place["id"] in claimed_ids
            title = story["display_name"] if claimed else "？？？"
            points = place.get("points", 0)
            text = "✓ {}（{}点）".format(title, points) if claimed else "？？？（{}点）".format(points)
            button = self._button(text, (16, y, 343, 52), self.claim_place, enabled=not claimed)
            button.place_id = place["id"]
            button.story_key = key
            self.content.add_subview(button)
            self.place_buttons.append(button)
            y += 60
            if claimed:
                description = self._label(
                    "{}\n{}".format(story["display_name"], story["description"]),
                    (24, y, 327, 62),
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
        collected = []
        for key, story, place in self._target_places():
            if place["id"] in claimed_ids:
                collected.append(self._effective_story(key, story, place))
        self.status_label.text = "獲得済みアイテム図鑑"
        back_button = self._button("ゲーム画面にもどる", (16, 12, 343, 44), lambda button: self._render())
        self.content.add_subview(back_button)
        if not collected:
            empty_label = self._label(
                "まだ獲得済みアイテムはありません。\nスポットをチェックインして集めよう！",
                (24, 72, 327, 70),
                ("<system>", 16),
            )
            self.content.add_subview(empty_label)
            self.content.content_size = (self.width, 160)
            return

        preview = ui.ImageView(frame=(16, 72, 210, 220))
        preview.content_mode = ui.CONTENT_SCALE_ASPECT_FIT
        self.content.add_subview(preview)
        detail = self._label("", (16, 300, 210, 130), ("<system>", 14))
        self.content.add_subview(detail)

        def select_item(button):
            story = button.story
            preview.image = self._asset_image(story)
            detail.text = "{}\n{}\n{}".format(
                story["item_name"], story["display_name"], story["description"]
            )

        y = 72
        for story in collected:
            button = self._button(story["item_name"], (238, y, 121, 48), select_item)
            button.story = story
            self.content.add_subview(button)
            y += 58
        select_item(self.content.subviews[-1])
        self.content.content_size = (self.width, max(450, y + 24))

    def show_restart_notice(self, sender):
        self._render(
            "はじめから始めるには、スタッフが新しいゲームセッションを作ります。\n"
            "今の得点や獲得記録はそのまま残ります。"
        )

    def show_reset_notice(self, sender):
        self._render(
            "得点リセットはサーバー側の操作です。\n"
            "スタッフに新しいゲームセッションを作ってもらってください。"
        )

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
            result = self.api.claim_place(
                action_id=str(uuid.uuid4()),
                game_session_id=config.GAME_SESSION_ID,
                place_id=sender.place_id,
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
