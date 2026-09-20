TEAM_APP_MODULES = {
    "blue": "team_apps.blue.app",
    "green": "team_apps.green.app",
    "red": "team_apps.red.app",
    "yellow": "team_apps.yellow.app",
    "purple": "team_apps.purple.app",
    "pink": "team_apps.pink.app",
}


def app_module_for_team(team_id):
    return TEAM_APP_MODULES.get(team_id, "game_app")
