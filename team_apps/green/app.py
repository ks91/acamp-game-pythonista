"""Green team's self-contained real-map territory game for Pythonista."""
import json
import math
import random
import threading
import time
import traceback
from urllib.request import Request, urlopen

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


CENTER_TEST_PLACE_NAMES = frozenset({"カフェテリアふじ出口", "513研修室", "事務所側入口", "正面入口"})
CENTER_TEST_RADIUS_METERS = 10
LOCAL_CENTER_TEST_PLACES = (
    {"id": "center-513-training-room", "name": "513研修室", "latitude": 35.67407073059871, "longitude": 139.69317184609355, "radius_m": 10, "points": 120, "description": "センター棟の必須攻略地点。窓際のためGPS精度に注意。", "required": True},
    {"id": "center-office-entrance", "name": "事務所側入口", "latitude": 35.67465399946227, "longitude": 139.69315284937827, "radius_m": 10, "points": 120, "description": "センター棟の任意攻略地点。", "required": False},
    {"id": "center-cafeteria-fuji-exit", "name": "カフェテリアふじ出口", "latitude": 35.675026446445194, "longitude": 139.6939601327121, "radius_m": 10, "points": 120, "description": "センター棟の必須攻略地点。", "required": True},
    {"id": "center-main-entrance", "name": "正面入口", "latitude": 35.67492708549511, "longitude": 139.69340021778783, "radius_m": 10, "points": 120, "description": "センター棟の任意攻略地点。", "required": False},
)


class TerritoryMap(ui.View):
    """Leaflet/OpenStreetMap map embedded in a normal Pythonista view."""

    def __init__(self, on_select):
        super().__init__()
        self.on_select = on_select
        self.web = None
        self.last_model = {}
        ui.delay(self._create_webview, 0.2)

    def _create_webview(self):
        try:
            self._create_webview_inner()
        except Exception as exc:
            trace = traceback.format_exc()
            print("[green] WebView生成例外: " + trace)
            try:
                ui.alert("Green WebViewエラー", "{}\n\n{}".format(exc, trace), "閉じる")
            except Exception:
                pass

    def _create_webview_inner(self):
        if self.web is not None:
            return
        self.web = ui.WebView(frame=self.bounds, flex="WH")
        self.web.delegate = self
        self.add_subview(self.web)
        self.web.load_html(r'''<!doctype html><html><head>
<meta name="viewport" content="width=device-width,initial-scale=1.0,user-scalable=no">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>html,body,#map{height:100%;margin:0;background:#101820}.dark .leaflet-tile{filter:brightness(.55) saturate(.75)}.flag{border-radius:50% 50% 50% 0;width:28px;height:28px;transform:rotate(-45deg);border:3px solid #fff;box-shadow:0 2px 5px #0008}.flag span{display:block;transform:rotate(45deg);font-size:17px;text-align:center;padding-top:3px}</style>
</head><body><div id="map"></div><script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script><script>
const map=L.map('map').setView([35.37695,139.44909],14);L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© OpenStreetMap'}).addTo(map);L.control.zoom({position:'bottomright'}).addTo(map);let layers=L.layerGroup().addTo(map),firstFit=true;
function ownerColor(owner){return ({green:'#43A047',blue:'#1E88E5',red:'#E53935',yellow:'#FDD835',purple:'#8E24AA',pink:'#D81B60'})[owner]||'#9E9E9E';}
function roleColor(role,owner){return ({own_home:'#00A86B',enemy_target:'#7B1FA2',enemy_base:'#7B1FA2',neutral:'#9E9E9E',own_base:'#43A047'})[role]||ownerColor(owner);}
function roleSymbol(role){return ({own_home:'⌂',enemy_target:'◆',enemy_base:'◆',neutral:'○',own_base:'⚑'})[role]||'⚑';}
function render(model){layers.clearLayers();let points=model.places||[],owned=points.filter(p=>p.owner&&p.latitude!=null);owned.forEach(p=>L.circle([p.latitude,p.longitude],{radius:180,color:roleColor(p.role,p.owner),weight:2,fillColor:roleColor(p.role,p.owner),fillOpacity:.18}).addTo(layers));points.forEach(p=>{if(p.latitude==null||p.longitude==null)return;let color=roleColor(p.role,p.owner);let symbol=roleSymbol(p.role);let icon=L.divIcon({className:'',html:`<div class="flag" style="background:${color}"><span>${symbol}</span></div>`,iconSize:[28,28],iconAnchor:[14,28]});let marker=L.marker([p.latitude,p.longitude],{icon:icon}).addTo(layers);marker.bindPopup(`<b>${p.name}</b><br>${p.role_label||'地点'}<br>${p.owner_label||'所有者不明'}<br>${p.distance_text||'距離不明'}<br>${p.points}点`);marker.on('click',()=>window.location='pythonista://select/'+encodeURIComponent(p.id));});if(firstFit&&points.length){let bounds=points.filter(p=>p.latitude!=null).map(p=>[p.latitude,p.longitude]);if(bounds.length)map.fitBounds(bounds,{padding:[25,25]});firstFit=false;}map.invalidateSize();}
function setTheme(mode){document.documentElement.className=mode==='dark'?'dark':'';}
window.render=render;window.setTheme=setTheme;
</script></body></html>''')

    def update_model(self, model):
        self.last_model = model
        if self.web is None:
            return
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
        self.game_mode = getattr(config, "SELECTED_GAME_MODE", "center_test") if config else "center_test"
        self.name = "グリーン班 {}版".format("東京" if self.game_mode == "tokyo" else "センター棟テスト")
        self.team_id = getattr(config, "TEAM_ID", "green") if config else "green"
        self.device_id = getattr(config, "DEVICE_ID", "green-ipad") if config else "green-ipad"
        self.session_id = getattr(config, "GAME_SESSION_ID", "") if config else ""
        self.api_client = self._make_client()
        self.model = self._offline_model()
        self.selected_id = None
        self._refreshing = False
        self._last_api_error = ""
        self._debug_log = []
        self._mission_assignments = {}

        self.header = ui.Label(frame=(16, 12, 280, 54), font=("<system-bold>", 17), number_of_lines=2)
        self.add_subview(self.header)
        self.theme_button = ui.Button(title="☀︎", frame=(300, 12, 38, 34), action=self.toggle_theme)
        self.add_subview(self.theme_button)
        self.refresh_button = ui.Button(title="↻", frame=(344, 12, 38, 34), action=self.refresh_now)
        self.add_subview(self.refresh_button)
        self.restart_button = ui.Button(title="テストを最初から", frame=(16, 94, 132, 32), action=self.restart_test_session)
        self.restart_button.font = ("<system-bold>", 13)
        self.restart_button.background_color = (0.05, 0.18, 0.12, 0.88)
        self.add_subview(self.restart_button)
        self.legend_label = ui.Label(frame=(180, 66, 300, 30), text="◆相手陣地（攻略可能）　○未占領　⚑自班　⌂自班拠点", font=("<system>", 10), number_of_lines=2)
        self.legend_label.background_color = (0, 0, 0, 0.68)
        self.add_subview(self.legend_label)
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
        self.restart_button.frame = (16, 94, min(150, width - 32), 32)
        self.legend_label.frame = (max(180, width - 320), 66, min(304, width - max(180, width - 320) - 16), 30)
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
        return ApiClient(
            base_url=base_url,
            token=token,
            game_team_id=getattr(config, "SELECTED_GAME_TEAM_ID", None),
            game_mode=getattr(config, "SELECTED_GAME_MODE", None),
        )

    @staticmethod
    def _build_model(definition, state, team_id):
        claimed = set(state.get("claimed_places", []))
        territory_by_id = {item.get("place_id"): item for item in (state.get("territories") or [])}
        use_demo_opponents = False
        opponent_teams = ("blue", "red", "yellow", "purple", "pink")
        places = []
        configured_places = definition.get("places") or []
        center_places = [place for place in configured_places if place.get("name") in CENTER_TEST_PLACE_NAMES]
        scenario_places = center_places if len(center_places) >= 2 else list(LOCAL_CENTER_TEST_PLACES)
        for index, place in enumerate(scenario_places):
            territory = territory_by_id.get(place["id"], {})
            owner = territory.get("owner")
            simulated = False
            simulated_role = None
            if owner is None and place["id"] in claimed:
                owner = team_id
            elif owner is None and use_demo_opponents:
                if index % 4 == 0:
                    simulated_role = "neutral"
                else:
                    owner = opponent_teams[index % len(opponent_teams)]
                simulated = True
            owner_label = "自班（グリーン）" if owner == team_id else ("テスト表示: 未占領" if simulated_role == "neutral" else ("テスト表示: {}班".format(owner) if simulated else ("相手班" if owner else "中立")))
            home_id = state.get("home_place_id") or (getattr(config, "HOME_PLACE_ID", None) if config else None)
            if place.get("role"):
                role = place["role"]
            elif simulated_role is not None:
                role = simulated_role
            elif owner == team_id and place["id"] == home_id:
                role = "own_home"
            elif owner and owner != team_id and place.get("is_boss"):
                role = "enemy_target"
            elif owner and owner != team_id:
                role = "enemy_base"
            elif owner == team_id:
                role = "own_base"
            else:
                role = "neutral"
            role_labels = {"own_home": "自班の拠点", "enemy_target": "相手陣地（攻略可能）", "enemy_base": "相手陣地（攻略可能）", "neutral": "未占領の拠点", "own_base": "自班の拠点"}
            action_label = "状態確認" if owner == team_id else ("攻略する" if owner else "ミッション開始")
            mission_text = place.get("mission", place.get("description", ""))
            if "猫" in mission_text or "ねこ" in mission_text:
                mission_kind = "cat"
            elif "お化け" in mission_text or "ゴースト" in mission_text or "幽霊" in mission_text:
                mission_kind = "ghost"
            else:
                mission_kind = "mash"
            places.append({
                "id": place["id"], "name": place["name"],
                "latitude": place.get("latitude"), "longitude": place.get("longitude"),
                "points": territory.get("points", place.get("points", 0)), "owner": owner,
                "capture_radius_meters": CENTER_TEST_RADIUS_METERS,
                "owner_label": owner_label, "simulated_owner": simulated,
                "role": role, "role_label": role_labels.get(role, "地点"),
                "is_boss": bool(place.get("is_boss", False)),
                "mission": place.get("mission", place.get("description", "")),
                "mission_kind": mission_kind,
                "action_label": action_label,
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
        self.legend_label.text_color = primary_text
        self.legend_label.background_color = (0, 0, 0, 0.68) if dark else (1, 1, 1, 0.88)
        self.detail.background_color = (0, 0, 0, 0.72) if dark else (1, 1, 1, 0.84)
        self.action_button.background_color = (0, 0, 0, 0.78) if dark else (1, 1, 1, 0.88)
        self.theme_button.title = "☀︎" if dark else "☾"
        self._update_place_distances()
        self.map_view.update_model(self.model)
        place = next((item for item in self.model["places"] if item["id"] == self.selected_id), None)
        if place is None:
            if status == "offline" and self._last_api_error:
                self.detail.text = "API接続エラー\n{}".format(self._last_api_error)
            else:
                self.detail.text = "地図上の旗をタップすると地点の詳細を表示します。"
            self.action_button.title = "地点を選択してください"
            self.action_button.enabled = False
            return
        kind = "★ボス地点" if place["is_boss"] else "通常地点"
        mission_text = place["mission"] or "この地点に到着してミッションを達成する"
        distance_text = self._selected_place_distance_text(place)
        self.detail.text = "{} [{}]\n{}　得点: {}点\n現在地から: {}\nミッション: {}\n成功条件: 地点の範囲内で開始".format(place["name"], kind, place["role_label"], place["points"], distance_text, mission_text)
        self.action_button.title = place["action_label"] if not offline else "接続が必要です"
        self.action_button.enabled = True

    def _update_place_distances(self):
        try:
            current = location.get_location()
            if not current:
                raise RuntimeError("GPS unavailable")
            for place in self.model.get("places", []):
                if place.get("latitude") is None or place.get("longitude") is None:
                    place["distance_text"] = "距離不明"
                    continue
                distance = self._distance_meters(current["latitude"], current["longitude"], place["latitude"], place["longitude"])
                radius = float(place.get("capture_radius_meters", 100))
                place["distance_text"] = "約{:.0f}m（範囲{:.0f}m）".format(distance, radius)
        except Exception:
            for place in self.model.get("places", []):
                place["distance_text"] = "GPS取得不可"

    def _selected_place_distance_text(self, place):
        return place.get("distance_text", "GPS取得不可")

    def _debug(self, message):
        """Keep a short, secret-free trace visible after a failed refresh."""
        entry = "{} {}".format(time.strftime("%H:%M:%S"), message)
        self._debug_log.append(entry)
        self._debug_log = self._debug_log[-24:]
        print("[green] " + entry)

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

    def restart_test_session(self, sender):
        if self.api_client is None:
            self.detail.text = "テスト開始し直しには、ゲームサーバーへの接続が必要です。"
            return
        if not getattr(self, "_restart_confirmed", False):
            self._restart_confirmed = True
            self.restart_button.title = "もう一度押すと最初から"
            self.detail.text = "得点・陣地・ホームをテスト開始時の状態へ戻します。もう一度押してください。"
            ui.delay(self._cancel_restart_confirmation, 8.0)
            return
        self._restart_confirmed = False
        self.restart_button.enabled = False
        self.restart_button.title = "初期化中…"
        threading.Thread(target=self._restart_test_session_worker, daemon=True).start()

    def _cancel_restart_confirmation(self):
        if getattr(self, "_restart_confirmed", False):
            self._restart_confirmed = False
            self.restart_button.title = "テストを最初から"

    def _restart_test_session_worker(self):
        error = None
        try:
            if hasattr(self.api_client, "restart_test_session"):
                result = self.api_client.restart_test_session()
            else:
                request = Request(
                    self.api_client.base_url + "/test-session/restart",
                    data=json.dumps({"confirm": True}).encode("utf-8"),
                    headers={"Accept": "application/json", "Authorization": "Bearer " + self.api_client.token, "Content-Type": "application/json; charset=utf-8"},
                    method="POST",
                )
                with urlopen(request, timeout=15) as response:
                    result = json.loads(response.read().decode("utf-8"))
            if isinstance(result, dict) and result.get("error"):
                raise RuntimeError(str(result["error"]))
        except Exception as exc:
            error = exc
        ui.delay(lambda error=error: self._restart_test_session_complete(error), 0.0)

    def _restart_test_session_complete(self, error):
        self.restart_button.enabled = True
        self.restart_button.title = "テストを最初から"
        if error is not None:
            self.detail.text = "テストを最初からにできません。\n{}".format(error)
            return
        self.selected_id = None
        self._mission_assignments = {}
        self.detail.text = "テストを最初からにしました。地点を選んで、もう一度遊ぼう。"
        self.refresh_now()

    def _fetch_remote_state(self):
        definition = None
        state = None
        error = None
        self._debug_log = []
        self._debug("状態更新開始")
        try:
            self._debug("ゲーム定義を取得中")
            definition = self.api_client.get_game_definition()
            self._debug("ゲーム定義を取得完了")
            self._debug("チーム状態を取得中")
            state = self.api_client.get_team_state()
            self._debug("チーム状態を取得完了")
        except Exception as exc:
            error = exc
            trace = traceback.format_exc()
            self._debug("例外: {}".format(type(exc).__name__))
            for line in trace.rstrip().splitlines():
                self._debug(line)
        ui.delay(lambda: self._apply_remote_state(definition, state, error), 0.0)

    def _assign_random_missions(self):
        mission_kinds = ("cat", "mash", "ghost")
        for place in self.model.get("places", []):
            place_id = place["id"]
            if place_id not in self._mission_assignments:
                self._mission_assignments[place_id] = random.choice(mission_kinds)
            place["mission_kind"] = self._mission_assignments[place_id]

    def _apply_remote_state(self, definition, state, error):
        try:
            self._apply_remote_state_inner(definition, state, error)
        except Exception as exc:
            trace = traceback.format_exc()
            self._debug("画面反映中の例外: {}".format(type(exc).__name__))
            for line in trace.rstrip().splitlines():
                self._debug(line)
            self._refreshing = False
            self._last_api_error = "{}\n{}".format(exc, "\n".join(self._debug_log))
            self.model = self._offline_model()
            self.model["offline"] = True
            self.model["connection_status"] = "offline"
            self.detail.text = "状態反映エラー\n{}".format(self._last_api_error)
            self.action_button.title = "ログを確認してください"
            self.action_button.enabled = False

    def _apply_remote_state_inner(self, definition, state, error):
        self._refreshing = False
        if error is None and definition is not None and state is not None:
            self.session_id = (state.get("game_session_id") if isinstance(state, dict) else None) or (getattr(config, "GAME_SESSION_ID", self.session_id) if config else self.session_id)
            self.model = self._build_model(definition, state, self.team_id)
            self._assign_random_missions()
        else:
            trace_text = "\n".join(self._debug_log)
            self._last_api_error = "{}\n{}".format(str(error) if error is not None else "APIからゲーム状態を取得できませんでした", trace_text)
            fallback_state = {"score": self.model.get("score", 0), "territories": [], "claimed_places": []}
            self.model = self._build_model({"places": list(LOCAL_CENTER_TEST_PLACES)}, fallback_state, self.team_id)
            self._assign_random_missions()
            self.model["offline"] = True
            self.model["connection_status"] = "offline"
            self.detail.text = "APIに接続できないため、センター棟4地点をテスト表示しています。"
        self.refresh_view()

    def select_place(self, place_id):
        self.selected_id = place_id
        self.refresh_view()

    def toggle_theme(self, sender):
        self.model["theme_mode"] = "light" if self.model.get("theme_mode") == "dark" else "dark"
        self.refresh_view()

    def _close_mission_overlay(self, sender=None):
        if getattr(self, "mission_overlay", None) is not None:
            self.remove_subview(self.mission_overlay)
            self.mission_overlay = None

    def _show_mission_overlay(self, title, message, primary_title, primary_action):
        self._close_mission_overlay()
        overlay = ui.View(frame=self.bounds, flex="WH")
        overlay.background_color = (0, 0, 0, 0.58)
        card_width = min(430, self.width - 40)
        card_height = 270
        card = ui.View(frame=((self.width - card_width) / 2, max(70, (self.height - card_height) / 2), card_width, card_height))
        card.background_color = "#17212B" if self.model.get("theme_mode") == "dark" else "#FFFFFF"
        title_label = ui.Label(frame=(20, 18, card_width - 40, 34), text=title, font=("<system-bold>", 20), alignment=ui.ALIGN_CENTER)
        title_label.text_color = "white" if self.model.get("theme_mode") == "dark" else "#263238"
        card.add_subview(title_label)
        message_label = ui.Label(frame=(20, 66, card_width - 40, 86), text=message, font=("<system>", 16), number_of_lines=0, alignment=ui.ALIGN_CENTER)
        message_label.text_color = title_label.text_color
        card.add_subview(message_label)
        primary = ui.Button(frame=(20, 166, card_width - 40, 44), title=primary_title, font=("<system-bold>", 16), action=primary_action)
        primary.tint_color = "#42A5F5"
        card.add_subview(primary)
        if primary_title != "閉じる":
            close = ui.Button(frame=(20, 218, card_width - 40, 34), title="閉じる", action=self._close_mission_overlay)
            close.tint_color = title_label.text_color
            card.add_subview(close)
        overlay.add_subview(card)
        self.add_subview(overlay)
        self.mission_overlay = overlay

    def run_mission(self, sender):
        place = next((item for item in self.model["places"] if item["id"] == self.selected_id), None)
        if place is None:
            self.detail.text = "先に地図上の地点を選択してください。"
            return
        if self.model.get("connection_status") != "online":
            status = self.model.get("connection_status", "接続状態不明")
            self._show_mission_overlay("接続が必要です", "現在の状態: {}\nゲーム状態を取得できるまでミッションを開始できません。".format(status), "閉じる", self._close_mission_overlay)
            return
        if place["owner"] == self.team_id:
            self._show_mission_overlay("陣地の状態", "{}\n所有者: {}\n得点: {}点".format(place["name"], place["owner_label"], place["points"]), "閉じる", self._close_mission_overlay)
            return
        self._show_mission_overlay("ミッション開始確認", "{}\n分類: {}\n内容: {}\n成功条件: 先にGPSで地点範囲を確認し、その後ミニゲームをクリア".format(place["name"], place["role_label"], place["mission"] or "地点到着ミッション"), "開始する", self._check_location_before_minigame)

    def _check_location_before_minigame(self, sender=None):
        place = next((item for item in self.model["places"] if item["id"] == self.selected_id), None)
        if place is None:
            return
        self._close_mission_overlay()
        self.action_button.enabled = False
        self.detail.text = "GPSを更新中…範囲内か確認しています。"
        try:
            location.start_updates()
            self._location_check_place = place
            ui.delay(self._finish_location_check_on_main, 3.0)
        except Exception as error:
            self._show_mission_overlay("GPS開始失敗", "{}\nミニゲームは開始しません。".format(error), "再確認", self._check_location_before_minigame)
            self.action_button.enabled = True

    def _finish_location_check_on_main(self):
        place = getattr(self, "_location_check_place", None)
        try:
            current = location.get_location()
            self._evaluate_location_for_minigame(place, current)
        except Exception as error:
            self._show_mission_overlay("GPS確認失敗", "{}\nミニゲームは開始しません。".format(error), "再確認", self._check_location_before_minigame)
            self.action_button.enabled = True
        finally:
            try:
                location.stop_updates()
            except Exception:
                pass
            self._location_check_place = None

    def _evaluate_location_for_minigame(self, place, current):
        try:
            if not current:
                raise RuntimeError("現在地を取得できませんでした")
            latitude = current.get("latitude")
            longitude = current.get("longitude")
            if latitude is None or longitude is None:
                raise RuntimeError("GPSの緯度・経度を取得できませんでした")
            if place.get("latitude") is None or place.get("longitude") is None:
                raise RuntimeError("地点の座標が設定されていません")
            distance = self._distance_meters(latitude, longitude, place["latitude"], place["longitude"])
            radius = float(place.get("capture_radius_meters", 100))
            accuracy = current.get("horizontal_accuracy")
            if accuracy is not None and float(accuracy) > radius:
                raise RuntimeError("GPS精度が低すぎます（精度約{:.0f}m、必要範囲{}m）".format(float(accuracy), int(radius)))
            if distance > radius:
                self._show_mission_overlay("ミッション開始不可", "地点の範囲外です。\n地点まで約{:.0f}m\n必要範囲: {:.0f}m\n範囲内に移動してから再試行してください。".format(distance, radius), "再確認", self._check_location_before_minigame)
                return
            self._mission_location = current
            self.detail.text = "GPS確認OK（約{:.0f}m）\nミニゲームを開始します。".format(distance)
            self._start_minigame()
        except Exception as error:
            self._show_mission_overlay("GPS確認失敗", "{}\nミニゲームは開始しません。".format(error), "再確認", self._check_location_before_minigame)
        finally:
            self.action_button.enabled = True

    @staticmethod
    def _distance_meters(latitude1, longitude1, latitude2, longitude2):
        radius = 6371000.0
        lat1, lat2 = math.radians(float(latitude1)), math.radians(float(latitude2))
        dlat = lat2 - lat1
        dlon = math.radians(float(longitude2) - float(longitude1))
        value = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        return 2 * radius * math.asin(math.sqrt(value))

    def _start_minigame(self, sender=None):
        place = next((item for item in self.model["places"] if item["id"] == self.selected_id), None)
        if place is None:
            return
        self._close_mission_overlay()
        kind = place.get("mission_kind", "mash")
        overlay = ui.View(frame=self.bounds, flex="WH")
        overlay.background_color = (0, 0, 0, 0.62)
        card_width = min(430, self.width - 40)
        card = ui.View(frame=((self.width - card_width) / 2, max(45, (self.height - 400) / 2), card_width, 400))
        card.background_color = "#17212B" if self.model.get("theme_mode") == "dark" else "#FFFFFF"
        title = "猫を探せ" if kind == "cat" else ("お化けを倒せ" if kind == "ghost" else "ボタン連打ミッション")
        instruction = "9マスから猫を1回で見つけよう" if kind == "cat" else ("攻撃ボタンを15回押そう" if kind == "ghost" else "ボタンを10回押そう")
        label = ui.Label(frame=(18, 18, card_width - 36, 70), text=title + "\n" + instruction, font=("<system-bold>", 20), number_of_lines=2, alignment=ui.ALIGN_CENTER)
        label.text_color = "white" if self.model.get("theme_mode") == "dark" else "#263238"
        card.add_subview(label)
        self._mini_state = {"kind": kind, "count": 0, "target": 15 if kind == "ghost" else 10}
        if kind == "cat":
            self._mini_state["cat_index"] = random.randrange(9)
            for index in range(9):
                button = ui.Button(frame=(24 + (index % 3) * (card_width - 48) / 3, 105 + (index // 3) * 62, (card_width - 60) / 3, 50), title="？", font=("<system-bold>", 22))
                button.action = lambda sender, i=index: self._cat_tap(i, sender)
                card.add_subview(button)
        else:
            button = ui.Button(frame=(35, 145, card_width - 70, 100), title="攻撃 0/{}".format(self._mini_state["target"]), font=("<system-bold>", 24))
            button.action = self._mini_tap
            card.add_subview(button)
            self._mini_button = button
        cancel = ui.Button(frame=(24, 350, card_width - 48, 34), title="やめる", action=self._close_mission_overlay)
        cancel.tint_color = label.text_color
        card.add_subview(cancel)
        overlay.add_subview(card)
        self.add_subview(overlay)
        self.mission_overlay = overlay

    def _cat_tap(self, index, sender):
        if index == self._mini_state.get("cat_index"):
            self._mini_success()
        else:
            sender.title = "×"
            self.detail.text = "そのマスにはいません。別のマスを探そう。"

    def _mini_tap(self, sender):
        self._mini_state["count"] += 1
        count = self._mini_state["count"]
        sender.title = "攻撃 {} / {}".format(count, self._mini_state["target"])
        if count >= self._mini_state["target"]:
            self._mini_success()

    def _mini_success(self):
        self._close_mission_overlay()
        self.detail.text = "ミニゲーム成功！\n現在地を確認しています。"
        self._execute_mission()

    def _execute_mission(self, sender=None):
        self._close_mission_overlay()
        self.action_button.enabled = False
        self.detail.text = "ミッション実行中…\n陣地を確認しています。"
        try:
            current = getattr(self, "_mission_location", None)
            if not current:
                raise RuntimeError("GPS確認がありません。先に範囲確認を行ってください")
            sample = make_location_sample(team_id=self.team_id, device_id=self.device_id, client_time=time.strftime("%Y-%m-%dT%H:%M:%S%z"), location=current)
            self.api_client.post_location_sample(sample)
            result = self.api_client.claim_place(action_id="green-{}".format(int(time.time() * 1000)), game_session_id=self.session_id, place_id=self.selected_id, device_id=self.device_id)
            self._mission_result(result)
        except Exception as error:
            self._mission_error(error)

    def _mission_result(self, result):
        if result.get("claimed"):
            self.detail.text = "陣地を獲得しました！"
            self.refresh_now()
            self._show_mission_overlay("ミッション成功", "+{}点\n班合計: {}点\n旗を立てました。".format(result.get("score_delta", 0), result.get("team_score", 0)), "地図へ戻る", self._close_mission_overlay)
        else:
            self._show_mission_overlay("ミッション完了", "この地点はすでに自班の陣地です。", "地図へ戻る", self._close_mission_overlay)
        self.action_button.enabled = True
        self.refresh_view()

    def _mission_error(self, error):
        self._show_mission_overlay("ミニゲーム成功後の陣地獲得失敗", "{}\nミニゲームは成功しています。\n得点と陣地は変化しません。".format(error), "GPSから再試行", self._check_location_before_minigame)
        self.action_button.enabled = True
        self.refresh_view()


def run():
    try:
        GreenTerritoryGame().present("fullscreen")
    except Exception as exc:
        trace = traceback.format_exc()
        print("[green] 起動例外: " + trace)
        try:
            ui.alert("Green起動エラー", "{}\n\n{}".format(exc, trace), "閉じる")
        except Exception:
            pass


if __name__ == "__main__":
    run()
