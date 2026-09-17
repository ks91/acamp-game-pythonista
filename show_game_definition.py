"""Run in Pythonista 3 to list the active scenario's places."""

import config
from toolkit.api_client import ApiClient


def main():
    definition = ApiClient(
        base_url=config.API_BASE_URL, token=config.GAME_TOKEN
    ).get_game_definition()
    print(definition["name"] or definition["id"])
    for place in definition["places"]:
        print("- {}: {}点".format(place["name"], place["points"]))


if __name__ == "__main__":
    main()
