"""Server-backed Day 3/Day 4 scenario helpers for Red's monster game.

The gallery owns the selected team and game mode.  This module deliberately
contains no local mode switch, score calculation, or GPS substitution.
"""

from toolkit.api_client import ApiClient


BOSS_PLACE_NAMES = {
    "ゼウス": "皇居",
    "ヤタ": "明治神宮",
    "ヤサカニ": "国会議事堂",
    "クサナギ": "湯島天神",
}


def make_api_client(config_module, client_class=ApiClient):
    """Build the shared client using the Day 3/Day 4 gallery selection."""
    if config_module is None:
        return None
    base_url = getattr(config_module, "API_BASE_URL", "")
    token = getattr(config_module, "GAME_TOKEN", "")
    if not base_url or not token or token == "set-at-game-start":
        return None
    return client_class(
        base_url=base_url,
        token=token,
        game_team_id=getattr(config_module, "SELECTED_GAME_TEAM_ID", None),
        game_mode=getattr(config_module, "SELECTED_GAME_MODE", None),
    )


def _server_place(place):
    """Return a safe playable place only when the scenario supplied coordinates."""
    if not isinstance(place, dict):
        return None
    place_id = place.get("id")
    name = place.get("name")
    latitude = place.get("latitude")
    longitude = place.get("longitude")
    if not place_id or not name or latitude is None or longitude is None:
        return None
    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except (TypeError, ValueError):
        return None
    return {
        "id": str(place_id),
        "name": str(name),
        "latitude": latitude,
        "longitude": longitude,
        "plus_code": place.get("plus_code"),
    }


def scenario_from_server(definition, state):
    """Extract server places and server claim state without creating local scores."""
    definition = definition if isinstance(definition, dict) else {}
    state = state if isinstance(state, dict) else {}
    places = [item for item in (_server_place(place) for place in definition.get("places", [])) if item]
    place_ids_by_name = {place["name"]: place["id"] for place in places}
    boss_place_ids = {
        boss: place_ids_by_name[name]
        for boss, name in BOSS_PLACE_NAMES.items()
        if name in place_ids_by_name
    }
    claimed = state.get("claimed_places", [])
    return {
        "places": places,
        "claimed_place_ids": {str(place_id) for place_id in claimed if place_id is not None},
        "game_session_id": state.get("game_session_id"),
        "boss_place_ids": boss_place_ids,
    }
