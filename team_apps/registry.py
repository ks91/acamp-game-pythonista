TEAM_APP_MODULES = {
    "blue": "team_apps.blue.app",
    "green": "team_apps.green.app",
    "red": "team_apps.red.app",
    "yellow": "team_apps.yellow.app",
    "purple": "team_apps.purple.app",
    "pink": "team_apps.pink.app",
}

PARTNER_TEAMS = {
    "blue": "green",
    "green": "blue",
    "red": "yellow",
    "yellow": "red",
    "purple": "pink",
    "pink": "purple",
}


def app_module_for_team(team_id):
    return TEAM_APP_MODULES.get(team_id, "game_app")


def gallery_entries_for_team(team_id):
    partner = PARTNER_TEAMS.get(team_id)
    entries = []
    for game_team_id in sorted(TEAM_APP_MODULES):
        if game_team_id == team_id:
            label = "自分たちのゲーム"
        elif game_team_id == partner:
            label = "今日まず遊ぶペア班のゲーム"
        else:
            label = "ほかの班のゲーム"
        entries.append(
            {
                "team_id": game_team_id,
                "module": app_module_for_team(game_team_id),
                "label": label,
            }
        )
    return entries
