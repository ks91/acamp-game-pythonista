"""Green班: APIに登録された地点数と地点情報を確認する。"""
import config
from toolkit.api_client import ApiClient


def main():
    client = ApiClient(
        base_url=config.API_BASE_URL,
        token=config.GAME_TOKEN,
    )
    definition = client.get_game_definition()
    places = definition.get("places", []) if isinstance(definition, dict) else []
    if not isinstance(places, list):
        raise RuntimeError("APIのplacesが配列ではありません")

    print("ゲーム: {}".format(definition.get("name") or definition.get("id", "不明")))
    print("API地点数: {}".format(len(places)))
    for index, place in enumerate(places, 1):
        print(
            "{}. {} | id={} | {}点 | lat={} lon={}".format(
                index,
                place.get("name", "名称不明"),
                place.get("id", "ID不明"),
                place.get("points", 0),
                place.get("latitude", "不明"),
                place.get("longitude", "不明"),
            )
        )


if __name__ == "__main__":
    main()
