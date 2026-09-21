"""Send the GPS fix used for a place check before asking the server to claim it."""
import datetime
import uuid

from toolkit.location_payload import make_location_sample


def claim_with_location(api, *, team_id, device_id, game_session_id,
                        place_id, position):
    if not position:
        raise ValueError("現在地を取得してから、もう一度試してください。")
    sample = make_location_sample(
        team_id=team_id, device_id=device_id,
        client_time=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        location=position,
    )
    api.post_location_sample(sample)
    return api.claim_place(
        action_id=str(uuid.uuid4()), game_session_id=game_session_id,
        place_id=place_id, device_id=device_id,
    )
