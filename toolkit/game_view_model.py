def build_game_view_model(definition, state, team_id):
    theme = definition.get("ui", {})
    claimed_places = set(state.get("claimed_places", []))
    places = []
    for place in definition.get("places", []):
        places.append(
            {
                "id": place["id"],
                "name": place["name"],
                "points": place["points"],
                "claimed": place["id"] in claimed_places,
                "narrative": place.get("description") or place.get("hint") or "",
            }
        )
    status_text = "{} / {}班\n{}\n得点: {}点　位置送信: {}回\n獲得済み: {}".format(
        definition.get("name", "ゲーム"),
        team_id,
        definition.get("intro", ""),
        state.get("score", 0),
        state.get("location_event_count", 0),
        ", ".join(claimed_places) or "なし",
    )
    return {
        "theme": {
            "accent_color": theme.get("accent_color", "#1565C0"),
            "background_color": theme.get("background_color", "white"),
        },
        "status_text": status_text,
        "places": places,
    }
