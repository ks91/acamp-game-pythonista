"""Set PLACE_ID, then run this in Pythonista 3 to claim a test place."""

import uuid
from urllib.error import HTTPError

import config
from toolkit.api_client import ApiClient

# The server must be configured with a matching ACAMP_GAME_PLACE_SCORE_* value.
PLACE_ID = "time-site"


def main():
    api = ApiClient(base_url=config.API_BASE_URL, token=config.GAME_TOKEN)
    try:
        result = api.claim_place(
            action_id=str(uuid.uuid4()),
            game_session_id=config.GAME_SESSION_ID,
            place_id=PLACE_ID,
        )
    except HTTPError as error:
        print("スポットを獲得できませんでした: HTTP {}".format(error.code))
        print(error.read().decode("utf-8"))
        return
    if result["claimed"]:
        print(
            "スポット獲得: {} (+{}点)、合計 {}点".format(
                result["place_id"], result["score_delta"], result["team_score"]
            )
        )
    else:
        print(
            "このスポットは既に獲得済み。合計 {}点".format(
                result["team_score"]
            )
        )


if __name__ == "__main__":
    main()
