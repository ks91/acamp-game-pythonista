"""Green team's self-contained real-map territory game for Pythonista."""
import json
import threading
import time

import location
import ui

from toolkit.api_client import ApiClient
from toolkit.location_payload import make_location_sample

try:
    import config
except ImportError:
    config = None

DARK_BG = "#101820"
LIGHT_BG = "#F4F7F9"


class TerritoryMap(ui.View):
    """Leaflet/OpenStreetMap map embedded in a normal Pythonista view."""

    def __init__(self, on_select):
        super().__init__()
        self.on_select = on_select
        self.web = ui.WebView(frame=self.bounds, flex="WH")
        self.web.delegate = self
        self.last_model = {}
        self.add_subview(self.web)
        self.web.load_html(r'''<!doctype html><html><head>
<meta name="viewport" content="width=device-width,initial-scale=1.0,user-scalable=no">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>html,body,#map{height:100%;margin:0;background:#101820}.dark .leaflet-tile{filter:brightness(.55) saturate(.75)}.flag{border-radius:50% 50% 50% 0;width:28px;height:28px;transform:rotate(-45deg);border:3px solid #fff;box-shadow:0 2px 5px #0008}.flag span{display:block;transform:rotate(45deg);font-size:17px;text-align:center;padding-top:3px}</style>
</head><body><div id="map"></div><script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script><script>
const map=L.map('map').setView([35.37695,139.44909],14);L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© OpenStreetMap'}).addTo(map);L.control.zoom({position:'bottomright'}).addTo(map);let layers=L.layerGroup().addTo(map),firstFit=true;
function render(model){layers.clearLayers();let points=model.places||[],owned=points.filter(p=>p.owner&&p.latitude!=null);owned.forEach(p=>L.circle([p.latitude,p.longitude],{radius:180,color:'#43A047',weight:2,fillColor:'#43A047',fillOpacity:.18}).addTo(layers));points.forEach(p=>{if(p.latitude==null||p.longitude==null)return;let color=p.owner?'#43A047':'#9E9E9E';let symbol=p.is_boss?'★':'⚑';let icon=L.divIcon({className:'',html:`<div class="flag" style="background:${color}"><span>${symbol}</span></div>`,iconSize:[28,28],iconAnchor:[14,28]});let marker=L.marker([p.latitude,p.longitude],{icon:icon}).addTo(layers);marker.bindPopup(`<b>${p.name}</b><br>${p.owner?'グリーンの陣地':'未獲得'}<br>${p.points}点`);marker.on('click',()=>window.location='pythonista://select/'+encodeURIComponent(p.id));});if(firstFit&&points.length){let bounds=points.filter(p=>p.latitude!=null).map(p=>[p.latitude,p.longitude]);if(bounds.length)map.fitBounds(bounds,{padding:[25,25]});firstFit=false;}map.invalidateSize();}
function setTheme(mode){document.documentElement.className=mode==='dark'?'dark':'';}
window.render=render;window.setTheme=setTheme;
</script></body></html>''')

    def update_model(self, model):
        self.last_model = model
        try:
            payload = json.dumps(model)
            self.web.evaluate_javascript("setTheme({});render({});".format(json.dumps(model.get("theme_mode", "dark")), payload))
        except Exception:
            # The WebView may still be loading its HTML/Leaflet assets.
            # webview_did_finish_load will retry with the saved model.
            pass

    def webview_did_finish_load(self, webview):
        if self.last_model:
            ui.delay(lambda: self.update_model(self.last_model), 0.1)

    def webview_should_start_load(self, webview, url, navigation_type):
        prefix = "pythonista://select/"
        if url.startswith(prefix):
            self.on_select(url[len(prefix):])
            return False
        return True


class GreenTerritoryGame(ui.View):
    def __init__(self):
        super().__init__(frame=(0, 0, 390, 844))
        self.flex = "WH"
        self.background_color = DARK_BG
        self.name = "グリーン班 戦略陣地戦"
        self.team_id = getattr(config, "TEAM_ID", "green") if config else "green"
        self.device_id = getattr(config, "DEVICE_ID", "green-ipad") if config else "green-ipad"
        self.session_id = getattr(config, "GAME_SESSION_ID", "") if config else ""
        self.api_client = self._make_client()
        self.model = self._offline_model()
        self.selected_id = None
        self._refreshing = False

        self.header = ui.Label(frame=(16, 12, 280, 54), font=("<system-bold>", 17), number_of_lines=2)
        self.add_subview(self.header)
        self.theme_button = ui.Button(title="☀︎", frame=(300, 12, 38, 34), action=self.toggle_theme)
        self.add_subview(self.theme_button)
        self.refresh_button = ui.Button(title="↻", frame=(344, 12, 38, 34), action=self.refresh_now)
        self.add_subview(self.refresh_button)
        self.offline_label = ui.Label(frame=(16, 66, 360, 25), font=("<system-bold>", 13))
        self.add_subview(self.offline_label)
        self.map_view = TerritoryMap(self.select_place)
        self.map_view.frame = (0, 0, self.width, self.height)
        self.map_view.flex = "WH"
        self.add_subview(self.map_view)
        self.map_view.send_to_back()
        self.detail = ui.Label(frame=(16, 500, 358, 92), font=("<system>", 15), number_of_lines=0)
        self.detail.background_color = (0, 0, 0, 0.72)
        self.detail.text_color = "white"
        self.add_subview(self.detail)
        self.action_button = ui.Button(frame=(16, 600, 358, 48), font=("<system-bold>", 16), action=self.run_mission)
        self.action_button.background_color = (0, 0, 0, 0.78)
        self.add_subview(self.action_button)
        self.refresh_view()
        ui.delay(self.refresh_now, 0.2)

    def layout(self):
        width, height = self.bounds.width, self.bounds.height
        self.map_view.frame = (0, 0, width, height)
        self.header.frame = (16, 12, max(220, width - 112), 54)
        self.theme_button.frame = (width - 90, 12, 38, 34)
        self.refresh_button.frame = (width - 46, 12, 38, 34)
        self.offline_label.frame = (16, 66, width - 32, 25)
        self.detail.frame = (16, max(120, height - 170), width - 32, 88)
        self.action_button.frame = (16, max(210, height - 76), width - 32, 48)

    @staticmethod
    def _offline_model():
        return {"score": 0, "remaining_seconds": None, "offline": False, "connection_status": "connecting", "theme_mode": "dark", "places": []}

    def _make_client(self):
        if config is None:
            return None
        base_url = getattr(config, "API_BASE_URL", "")
        token = getattr(config, "GAME_TOKEN", "")
        if not base_url or not token or token == "set-at-game-start":
            return None
        return ApiClient(base_url=base_url, token=token)

    @staticmethod
    def _build_model(definition, state, team_id):
        claimed = set(state.get("claimed_places", []))
        places = []
        for place in definition.get("places", []):
            owner = team_id if place["id"] in claimed else None
            places.append({
                "id": place["id"], "name": place["name"],
                "latitude": place.get("latitude"), "longitude": place.get("longitude"),
                "points": place.get("points", 0), "owner": owner,
                "is_boss": bool(place.get("is_boss", False)),
                "mission": place.get("mission", place.get("description", "")),
                "action_label": "状態確認" if owner else "ミッション開始",
            })
        return {"score": state.get("score", 0), "remaining_seconds": None, "offline": False, "connection_status": "online", "theme_mode": "dark", "places": places}

    def refresh_view(self):
        remaining = self.model.get("remaining_seconds")
        time_text = "--:--" if remaining is None else "{}:{:02d}".format(max(0, int(remaining)) // 60, max(0, int(remaining)) % 60)
        self.header.text = "得点: {}点\n残り時間: {}".format(self.model.get("score", 0), time_text)
        status = self.model.get("connection_status", "offline" if self.model.get("offline") else "online")
        labels = {"connecting": "● 接続確認中", "online": "● オンライン", "offline": "● オフライン", "not_configured": "● API設定待ち"}
        self.offline_label.text = labels.get(status, "● 接続状態不明")
        self.offline_label.text_color = {"online": "#66BB6A", "connecting": "#90CAF9", "not_configured": "#B0BEC5"}.get(status, "#FFB300")
        offline = status != "online"
        dark = self.model.get("theme_mode") == "dark"
        primary_text = "white" if dark else "#263238"
        self.header.text_color = primary_text
        self.detail.text_color = primary_text
        self.theme_button.tint_color = primary_text
        self.refresh_button.tint_color = primary_text
        self.action_button.tint_color = primary_text
        self.detail.background_color = (0, 0, 0, 0.72) if dark else (1, 1, 1, 0.84)
        self.action_button.background_color = (0, 0, 0, 0.78) if dark else (1, 1, 1, 0.88)
        self.theme_button.title = "☀︎" if dark else "☾"
        self.map_view.update_model(self.model)
        place = next((item for item in self.model["places"] if item["id"] == self.selected_id), None)
        if place is None:
            self.detail.text = "地図上の旗をタップすると地点の詳細を表示します。"
            self.action_button.title = "地点を選択してください"
            self.action_button.enabled = False
            return
        kind = "★ボス地点" if place["is_boss"] else "通常地点"
        self.detail.text = "{} [{}]\n得点: {}点\nミッション: {}".format(place["name"], kind, place["points"], place["mission"] or "詳細を確認")
        self.action_button.title = place["action_label"] if not offline else "オフラインのためプレイ不可"
        self.action_button.enabled = not offline

    def refresh_now(self, sender=None):
        if self.api_client is None:
            self.model["offline"] = False
            self.model["connection_status"] = "not_configured"
            self.refresh_view()
            return
        if self._refreshing:
            return
        self._refreshing = True
        self.detail.text = "ゲーム状態を更新しています…"
        threading.Thread(target=self._fetch_remote_state, daemon=True).start()

    def _fetch_remote_state(self):
        definition = None
        state = None
        error = None
        try:
            definition = self.api_client.get_game_definition()
            state = self.api_client.get_team_state()
        except Exception as exc:
            error = exc
        ui.delay(lambda: self._apply_remote_state(definition, state, error), 0.0)

    def _apply_remote_state(self, definition, state, error):
        self._refreshing = False
        if error is None and definition is not None and state is not None:
            self.session_id = getattr(config, "GAME_SESSION_ID", self.session_id) if config else self.session_id
            self.model = self._build_model(definition, state, self.team_id)
        else:
            self.model["offline"] = True
            self.model["connection_status"] = "offline"
        self.refresh_view()

    def select_place(self, place_id):
        self.selected_id = place_id
        self.refresh_view()

    def toggle_theme(self, sender):
        self.model["theme_mode"] = "light" if self.model.get("theme_mode") == "dark" else "dark"
        self.refresh_view()

    def run_mission(self, sender):
        if self.selected_id is None or self.api_client is None or self.model.get("offline"):
            return
        self.action_button.enabled = False
        self.detail.text = "現在地を確認しています…"
        try:
            current = location.get_location()
            if not current:
                raise RuntimeError("現在地を取得できませんでした")
            sample = make_location_sample(team_id=self.team_id, device_id=self.device_id, client_time=time.strftime("%Y-%m-%dT%H:%M:%S%z"), location=current)
            self.api_client.post_location_sample(sample)
            result = self.api_client.claim_place(action_id="green-{}".format(int(time.time() * 1000)), game_session_id=self.session_id, place_id=self.selected_id, device_id=self.device_id)
            if result.get("claimed"):
                self.detail.text = "陣地を獲得しました！\n+{}点　班合計: {}点".format(result.get("score_delta", 0), result.get("team_score", 0))
            else:
                self.detail.text = "この地点はすでに自班の陣地です。"
            self.refresh_now()
        except Exception as error:
            self.detail.text = "ミッションを実行できませんでした。\n{}".format(error)
            self.refresh_view()


def run():
    GreenTerritoryGame().present("fullscreen")


if __name__ == "__main__":
    run()
