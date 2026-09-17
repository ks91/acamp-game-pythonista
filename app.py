"""Run this file in Pythonista 3 after creating config.py from config.example.py."""

import datetime
import os
import uuid

import location

import config
from toolkit.api_client import ApiClient
from toolkit.check_in import CheckInService
from toolkit.event_queue import EventQueue
from toolkit.location_payload import make_location_sample


def main():
    location.start_updates()
    try:
        position = location.get_location()
    finally:
        location.stop_updates()

    if position is None:
        raise RuntimeError("位置情報を取得できませんでした。位置情報の許可と屋外の電波状況を確認してください。")

    sample = make_location_sample(
        team_id=config.TEAM_ID,
        device_id=config.DEVICE_ID,
        client_time=datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(),
        sample_id=str(uuid.uuid4()),
        location=position,
    )
    repository_directory = os.path.dirname(os.path.abspath(__file__))
    queue = EventQueue(os.path.join(repository_directory, "pending-events.json"))
    api = ApiClient(base_url=config.API_BASE_URL, token=config.GAME_TOKEN)
    result = CheckInService(api, queue).submit(sample)

    if result.get("queued"):
        print("通信できなかったため、位置情報を端末に保存しました。次回の送信時に再試行します。")
    else:
        print("位置情報を送信しました: event_id={}".format(result["event_id"]))
        state = api.get_team_state()
        print(
            "この班の位置送信回数: {}".format(
                state["location_event_count"]
            )
        )


if __name__ == "__main__":
    main()
