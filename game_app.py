"""Pythonista 3 one-screen interface for a team's location game."""

import datetime
import os
import uuid
from urllib.error import HTTPError

import location
import ui

import config
from toolkit.api_client import ApiClient
from toolkit.check_in import CheckInService
from toolkit.event_queue import EventQueue
from toolkit.location_payload import make_location_sample


class GameView(ui.View):
    def __init__(self):
        super().__init__(frame=(0, 0, 375, 667))
        self.name = "アカキャン位置ゲー"
        self.background_color = "white"
        self.api = ApiClient(base_url=config.API_BASE_URL, token=config.GAME_TOKEN)
        self.repository_directory = os.path.dirname(os.path.abspath(__file__))
        self.queue = EventQueue(os.path.join(self.repository_directory, "pending-events.json"))
        self.status_label = ui.Label(frame=(16, 12, 340, 110), flex="W")
        self.status_label.number_of_lines = 0
        self.add_subview(self.status_label)
        self.scroll = ui.ScrollView(frame=(0, 130, 0, 0), flex="WH")
        self.add_subview(self.scroll)
        self.refresh()

    def show_message(self, message):
        self.status_label.text = message

    def refresh(self):
        try:
            definition = self.api.get_game_definition()
            state = self.api.get_team_state()
        except OSError as error:
            self.show_message("サーバーへ接続できません。\n{}".format(error))
            return
        claimed = set(state.get("claimed_places", []))
        self.show_message(
            "{} / {}班\n得点: {}点　位置送信: {}回\n獲得済み: {}".format(
                definition.get("name", "ゲーム"),
                config.TEAM_ID,
                state.get("score", 0),
                state.get("location_event_count", 0),
                ", ".join(claimed) or "なし",
            )
        )
        for view in list(self.scroll.subviews):
            self.scroll.remove_subview(view)
        update_button = ui.Button(title="現在地を更新", frame=(16, 0, 220, 44))
        update_button.action = self.update_location
        self.scroll.add_subview(update_button)
        y = 58
        for place in definition.get("places", []):
            title = "✓ " if place["id"] in claimed else ""
            button = ui.Button(
                title="{}{}（{}点）".format(title, place["name"], place["points"]),
                frame=(16, y, 340, 44),
            )
            button.place_id = place["id"]
            button.action = self.claim_place
            self.scroll.add_subview(button)
            y += 52
        self.scroll.content_size = (375, y + 16)

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
            )
        except HTTPError as error:
            self.show_message("獲得できません。\n" + error.read().decode("utf-8"))
            return
        if result["claimed"]:
            self.show_message("{} を獲得！ +{}点".format(result["place_id"], result["score_delta"]))
        else:
            self.show_message("この場所は既に獲得済みです。")
        self.refresh()


if __name__ == "__main__":
    GameView().present("fullscreen")
