"""レッド班 Day 2 試作：6体のモンスターを選んで戦う。"""

import json
import math
import random
import webbrowser

import location
import ui


MONSTERS = [
    {"name": "森のぷに", "stars": 1, "kind": "攻撃系", "drop": "木の棒", "drop_power": 50},
    {"name": "草むらモン", "stars": 1, "kind": "回復系", "drop": "成長フード（+10）", "drop_power": 10},
    {"name": "石ころモン", "stars": 1, "kind": "強化系", "drop": "木の棒", "drop_power": 50},
    {"name": "青い影", "stars": 2, "kind": "弱体化系", "drop": "弓", "drop_power": 100},
    {"name": "赤い影", "stars": 2, "kind": "攻撃系", "drop": "剣", "drop_power": 100},
    {"name": "幻の王", "stars": 3, "kind": "レア", "drop": "オレンジジュース", "drop_power": 0},
]

MINIBOSSES = [
    {"name": "ヤタ", "kind": "中ボス", "boss_hp": 2000, "drop": "三種の神器・鏡", "boss": True},
    {"name": "ヤサカニ", "kind": "中ボス", "boss_hp": 2000, "drop": "三種の神器・勾玉", "boss": True},
    {"name": "クサナギ", "kind": "中ボス", "boss_hp": 2000, "drop": "三種の神器・剣", "boss": True},
]

STAR_NAMES = {
    1: "かわいいでちゅね",
    2: "かわいいですね",
    3: "かわいいでございますね",
}

STAR_HP = {1: 100, 2: 300, 3: 500}
MAX_HP_GAIN_BY_STAR = {1: 10, 2: 30, 3: 50}
CAPACITY_GAIN_INTERVAL = {1: 5, 2: 3, 3: 1}
LOCATION_TRIGGER_RADIUS_M = 20
WEAPON_POWER = {"木の棒": 50, "剣": 100, "弓": 100, "爆発系": 1000}
WEAPON_USES_PER_ITEM = {"木の棒": 5, "剣": 10, "弓": 10, "爆発系": 10}


def weapon_uses_for(item_name):
    return WEAPON_USES_PER_ITEM.get(item_name, 10)


DESTINATIONS = [
    {
        "id": "center-building",
        "name": "センター棟",
        "plus_code": None,
        "latitude": 35.67437387858118,
        "longitude": 139.69314002932387,
    },
    {
        "id": "cafeteria-fuji",
        "name": "カフェテリアふじ",
        "plus_code": "MMFV+WF",
        "latitude": 35.67484017956108,
        "longitude": 139.6936804736062,
    },
    {
        "id": "linkeee",
        "name": "運動教室（LinKeee）",
        "plus_code": "MMFV+X9",
        "latitude": 35.67437387858118,
        "longitude": 139.69314002932387,
    },
]


def distance_meters(latitude, longitude, target):
    latitude_scale = 111320.0
    longitude_scale = latitude_scale * math.cos(math.radians(target["latitude"]))
    north = (latitude - target["latitude"]) * latitude_scale
    east = (longitude - target["longitude"]) * longitude_scale
    return math.sqrt(north * north + east * east)


class RedPrototype(ui.View):
    def __init__(self):
        super().__init__(frame=(0, 0, 375, 667))
        self.name = "レッド班・皇居救出作戦 試作"
        self.background_color = "#FFEBEE"
        self.inventory = []
        self.weapon_uses = {}
        self.capacity = 5
        self.defeated_by_stars = {1: 0, 2: 0, 3: 0}
        self.current_screen = "map"
        self.unlocked_destinations = set()
        self.active_monster = None
        self.last_position = None
        self.last_accuracy = None
        self.player_max_hp = 100
        self.player_hp = 100
        self.enemy_hp = 0
        self.monsters = list(MONSTERS)
        random.shuffle(self.monsters)
        self.monster_destinations = {
            monster["name"]: random.choice(DESTINATIONS)["id"]
            for monster in self.monsters
        }
        self.build_header()
        self.show_battle_selection()

    def build_header(self):
        self.title = ui.Label(frame=(12, 12, 351, 34))
        self.title.text = "レッド班・皇居救出作戦"
        self.title.font = ("<System-Bold>", 22)
        self.title.text_color = "#B71C1C"
        self.title.alignment = ui.ALIGN_CENTER
        self.add_subview(self.title)

        self.status = ui.Label(frame=(16, 50, 343, 58))
        self.status.number_of_lines = 0
        self.status.font = ("<System>", 14)
        self.add_subview(self.status)

        self.content = ui.ScrollView(frame=(0, 112, 375, 555), flex="WH")
        self.add_subview(self.content)

    def clear_content(self):
        for view in list(self.content.subviews):
            self.content.remove_subview(view)

    def set_status(self, text):
        self.status.text = text

    def inventory_counts(self):
        counts = {}
        for item in self.inventory:
            counts[item] = counts.get(item, 0) + 1
        return counts

    def show_battle_selection(self):
        self.current_screen = "battle_selection"
        self.clear_content()
        self.set_status(
            "戦闘画面の第一試作\n"
            "戦いたいモンスターを選ぼう。星が高いほど強い。\n"
            "所持: {}/{}個".format(len(self.inventory), self.capacity)
        )
        map_button = ui.Button(title="ゲーム内マップを見る", frame=(16, 8, 343, 42))
        map_button.tint_color = "#2E7D32"
        map_button.action = self.show_map
        self.content.add_subview(map_button)
        inventory_button = ui.Button(title="アイテムを見る", frame=(16, 58, 343, 42))
        inventory_button.tint_color = "#6A1B9A"
        inventory_button.action = self.show_inventory
        self.content.add_subview(inventory_button)
        y = 108
        for monster in self.monsters:
            destination_id = self.monster_destinations[monster["name"]]
            destination = next(item for item in DESTINATIONS if item["id"] == destination_id)
            if self.last_position:
                distance = distance_meters(
                    self.last_position["latitude"], self.last_position["longitude"], destination
                )
                distance_text = "約{}m".format(round(distance))
            else:
                distance_text = "距離未測定"
            location_button = ui.Button(
                title="{}（{}）".format(monster["name"], distance_text),
                frame=(16, y, 343, 42),
            )
            location_button.tint_color = "#1565C0"
            location_button.destination = destination
            location_button.monster = monster
            location_button.action = self.check_monster_location
            self.content.add_subview(location_button)
            y += 50
        y += 4
        if not self.unlocked_destinations:
            locked = ui.Label(frame=(20, y, 335, 70))
            locked.number_of_lines = 0
            locked.text = "目的地から20m以内に入ると\nモンスターを発見できます。"
            locked.alignment = ui.ALIGN_CENTER
            locked.font = ("<System-Bold>", 17)
            self.content.add_subview(locked)
            self.content.content_size = (375, y + 90)
            return
        for monster in self.monsters:
            if self.monster_destinations[monster["name"]] not in self.unlocked_destinations:
                continue
            card = ui.Label(frame=(16, y, 343, 58))
            card.number_of_lines = 0
            card.font = ("<System>", 14)
            card.text = "{}  {}  {}\n系統：{} / 敵HP：{}".format(
                "★" * monster["stars"],
                monster["name"],
                STAR_NAMES[monster["stars"]],
                monster["kind"],
                STAR_HP[monster["stars"]],
            )
            self.content.add_subview(card)
            fight_button = ui.Button(title="このモンスターと戦う", frame=(16, y + 60, 343, 42))
            fight_button.tint_color = "#C62828"
            fight_button.monster = monster
            fight_button.action = self.start_selected_battle
            self.content.add_subview(fight_button)
            y += 112
        if self.player_max_hp >= 2000:
            boss_title = ui.Label(frame=(16, y + 8, 343, 44))
            boss_title.text = "三種の神器を守る中ボスが出現！"
            boss_title.font = ("<System-Bold>", 18)
            boss_title.text_color = "#6A1B9A"
            self.content.add_subview(boss_title)
            y += 60
            for boss_index, boss in enumerate(MINIBOSSES):
                boss_button = ui.Button(
                    title="{}（HP2000）".format(boss["name"]),
                    frame=(16, y, 343, 48),
                )
                boss_button.tint_color = "#6A1B9A"
                boss_button.boss_index = boss_index
                boss_button.action = self.start_miniboss
                self.content.add_subview(boss_button)
                y += 62
        self.content.content_size = (375, y + 12)

    def start_selected_battle(self, sender):
        self.active_monster = self.monsters[sender.monster_index]
        self.start_battle(sender)

    def check_monster_location(self, sender):
        self.check_destination_location(sender)

    def check_destination_location(self, sender):
        destination = sender.destination
        self.set_status("{}の位置情報を取得中…\n屋外で少し待ってください。".format(destination["name"]))
        location.start_updates()
        try:
            position = location.get_location()
        finally:
            location.stop_updates()
        if not position:
            self.set_status("位置情報を取得できませんでした。\n位置情報の許可を確認してください。")
            return
        self.last_position = position
        self.last_accuracy = position.get("horizontal_accuracy", "不明")
        distance = distance_meters(
            position["latitude"], position["longitude"], destination
        )
        accuracy = self.last_accuracy
        plus_code = destination.get("plus_code") or "登録済み座標"
        display_name = sender.monster["name"] if hasattr(sender, "monster") else destination["name"]
        if distance <= LOCATION_TRIGGER_RADIUS_M:
            self.unlocked_destinations.add(destination["id"])
            result = "{}を発見！出現地点の20m以内です。".format(display_name)
            self.show_battle_selection()
        else:
            result = "{}（出現地点）まで約{}m。もう少し近づこう。".format(
                display_name, round(distance)
            )
        self.set_status(
            "位置テスト結果\n{}\nPlus Code：{}\nGPS精度：約{}m".format(
                result, plus_code, accuracy
            )
        )

    def show_inventory(self, sender=None):
        self.current_screen = "inventory"
        self.clear_content()
        self.set_status(
            "アイテム一覧\n所持: {}/{}個\n勝利するとHPは全回復します。".format(
                len(self.inventory), self.capacity
            )
        )
        y = 18
        if not self.inventory:
            empty = ui.Label(frame=(20, y, 335, 50))
            empty.text = "まだアイテムはありません。"
            empty.alignment = ui.ALIGN_CENTER
            self.content.add_subview(empty)
            y += 70
        else:
            effect_text = {
                "木の棒": "攻撃：基準50（40〜50ダメージ）",
                "剣": "攻撃：基準100（80〜100ダメージ）",
                "弓": "攻撃：基準100（80〜100ダメージ）",
                "オレンジジュース": "HP0時の復活に使える切り札",
            }
            counts = self.inventory_counts()
            for item, count in counts.items():
                label = ui.Label(frame=(20, y, 335, 44))
                label.number_of_lines = 0
                effect = effect_text.get(item, "効果は戦闘で確認")
                if item in WEAPON_POWER:
                    effect = "攻撃：基準{}（残り{}回）".format(
                        WEAPON_POWER[item],
                        self.weapon_uses.get(item, weapon_uses_for(item)),
                    )
                count_text = " ×{}".format(count) if count > 1 else ""
                label.text = "・{}{}\n  {}".format(item, count_text, effect)
                self.content.add_subview(label)
                y += 58
        back = ui.Button(title="戦う相手を選ぶ", frame=(16, y + 12, 343, 48))
        back.tint_color = "#C62828"
        back.action = lambda button: self.show_battle_selection()
        self.content.add_subview(back)
        self.content.content_size = (375, y + 80)

    def show_interactive_map(self):
        self.set_status(
            "ゲーム内OpenStreetMap\n"
            "指で移動・ピンチで拡大縮小できます。敵の位置も表示します。"
        )
        self.content.content_size = (375, 790)
        self.open_map_view = ui.WebView(frame=(0, 0, 375, 720))
        self.content.add_subview(self.open_map_view)
        self.open_map_view.load_html(self.leaflet_map_html())
        back = ui.Button(title="マップを閉じる", frame=(16, 735, 343, 48))
        back.tint_color = "#C62828"
        back.action = lambda sender: self.show_battle_selection()
        self.content.add_subview(back)

    def leaflet_map_html(self):
        destinations = [
            {
                "name": destination["name"],
                "latitude": destination["latitude"],
                "longitude": destination["longitude"],
            }
            for destination in DESTINATIONS
        ]
        markers = []
        for index, monster in enumerate(self.monsters):
            destination_id = self.monster_destinations[monster["name"]]
            destination = next(item for item in DESTINATIONS if item["id"] == destination_id)
            offset = (index % 3 - 1) * 0.00012
            markers.append(
                {
                    "name": monster["name"],
                    "rank": "★" * monster["stars"],
                    "kind": monster["kind"],
                    "latitude": destination["latitude"] + offset,
                    "longitude": destination["longitude"] + offset,
                }
            )
        destination_json = json.dumps(destinations, ensure_ascii=False)
        marker_json = json.dumps(markers, ensure_ascii=False)
        return """<!doctype html>
<html><head><meta name='viewport' content='width=device-width,initial-scale=1'>
<link rel='stylesheet' href='https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'>
<style>html,body,#map{height:100%%;margin:0} .monster{font-size:20px}</style></head>
<body><div id='map'></div>
<script src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'></script>
<script>
const destinations = %s;
const monsters = %s;
const map = L.map('map', {zoomControl:true}).setView([35.6745,139.6934], 18);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 21, attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);
destinations.forEach(d => {
  L.marker([d.latitude,d.longitude]).addTo(map).bindPopup('目的地：' + d.name);
});
monsters.forEach(m => {
  const icon = L.divIcon({className:'monster', html:'👾', iconSize:[28,28]});
  L.marker([m.latitude,m.longitude], {icon:icon}).addTo(map)
    .bindPopup('<b>' + m.rank + ' ' + m.name + '</b><br>系統：' + m.kind);
});
</script></body></html>""" % (destination_json, marker_json)

    def google_map_url(self, destination):
        return (
            "https://www.google.com/maps/@?api=1&map_action=map&center={},{}&zoom=18"
            "&basemap=roadmap"
        ).format(destination["latitude"], destination["longitude"])

    def move_google_map(self, sender):
        self.google_map_view.load_url(self.google_map_url(sender.destination))

    def show_map(self, sender=None):
        self.current_screen = "map"
        self.clear_content()
        self.show_interactive_map()
        return
        y = 8
        map_label = ui.Label(frame=(16, y, 343, 42))
        map_label.text = "【オリンピックセンター探索マップ】"
        map_label.font = ("<System-Bold>", 18)
        map_label.text_color = "#2E7D32"
        self.content.add_subview(map_label)
        y += 54
        for destination in DESTINATIONS:
            destination_id = destination["id"]
            unlocked = destination_id in self.unlocked_destinations
            card = ui.Label(frame=(16, y, 343, 74))
            card.number_of_lines = 0
            assigned = [
                monster for monster in self.monsters
                if self.monster_destinations[monster["name"]] == destination_id
            ]
            if unlocked:
                kinds = "、".join(sorted({monster["kind"] for monster in assigned})) or "なし"
                card.text = "📍 {}\n系統：{}\nモンスター{}体".format(
                    destination["name"], kinds, len(assigned)
                )
            else:
                card.text = "🔒 {}\n20m以内に入るとモンスターの系統が分かります".format(
                    destination["name"]
                )
            card.font = ("<System>", 14)
            self.content.add_subview(card)
            y += 78
            map_button = ui.Button(title="Googleマップで開く", frame=(16, y, 343, 42))
            map_button.tint_color = "#1565C0"
            map_button.destination = destination
            map_button.action = self.open_google_maps
            self.content.add_subview(map_button)
            y += 54
            if unlocked:
                footprints = ui.Button(title="足跡をたどる", frame=(16, y, 343, 42))
                footprints.tint_color = "#6A1B9A"
                footprints.destination_id = destination_id
                footprints.action = self.show_destination_footprints
                self.content.add_subview(footprints)
                y += 54
        back = ui.Button(title="戦う相手を選ぶ", frame=(16, y, 343, 46))
        back.tint_color = "#C62828"
        back.action = lambda sender: self.show_battle_selection()
        self.content.add_subview(back)
        self.content.content_size = (375, y + 70)

    def open_google_maps(self, sender):
        destination = sender.destination
        url = "https://www.google.com/maps/search/?api=1&query={},{}".format(
            destination["latitude"], destination["longitude"]
        )
        self.set_status("Googleマップで{}を開いています…".format(destination["name"]))
        webbrowser.open(url, new=2, autoraise=True)

    def show_destination_footprints(self, sender):
        destination_id = sender.destination_id
        destination = next(item for item in DESTINATIONS if item["id"] == destination_id)
        monsters = [
            monster for monster in self.monsters
            if self.monster_destinations[monster["name"]] == destination_id
        ]
        self.clear_content()
        self.set_status("{}の足跡\n少しずつ見つかった！".format(destination["name"]))
        y = 20
        trail = ui.Label(frame=(20, y, 335, 100))
        trail.number_of_lines = 0
        trail.alignment = ui.ALIGN_CENTER
        trail.font = ("<System>", 22)
        trail.text = "・   ・     ・   ・\n\n足跡の先にモンスターがいる…"
        self.content.add_subview(trail)
        y += 120
        for monster in monsters:
            button = ui.Button(
                title="{}  {}（{}系）を発見".format(
                    "★" * monster["stars"], monster["name"], monster["kind"]
                ),
                frame=(16, y, 343, 48),
            )
            button.tint_color = "#C62828"
            button.monster = monster
            button.action = self.start_monster_from_map
            self.content.add_subview(button)
            y += 62
        back = ui.Button(title="マップに戻る", frame=(16, y, 343, 46))
        back.action = lambda sender: self.show_map()
        self.content.add_subview(back)
        self.content.content_size = (375, y + 70)

    def start_monster_from_map(self, sender):
        self.active_monster = sender.monster
        self.start_battle(sender)

    def begin_search(self, sender):
        monster = self.monsters[sender.monster_index]
        self.active_monster = monster
        self.current_screen = "search"
        self.clear_content()
        self.set_status(
            "AR探索中\n足跡が少しずつ見つかった！\n"
            "通行の邪魔にならない場所で、立ち止まって探そう。"
        )
        label = ui.Label(frame=(20, 24, 335, 120))
        label.number_of_lines = 0
        label.font = ("<System>", 20)
        label.alignment = ui.ALIGN_CENTER
        label.text = "・   ・     ・\n\n足跡の先に何かいる…"
        self.content.add_subview(label)
        find_button = ui.Button(title="モンスターをタップして発見！", frame=(16, 175, 343, 54))
        find_button.tint_color = "#C62828"
        find_button.action = self.start_battle
        self.content.add_subview(find_button)
        back_button = ui.Button(title="地図にもどる", frame=(16, 245, 343, 44))
        back_button.action = lambda sender: self.show_map()
        self.content.add_subview(back_button)
        self.content.content_size = (375, 310)

    def start_miniboss(self, sender):
        self.active_monster = MINIBOSSES[sender.boss_index]
        self.start_battle(sender)

    def start_battle(self, sender):
        self.current_screen = "battle"
        monster = self.active_monster
        self.enemy_hp = monster["boss_hp"] if monster.get("boss") else STAR_HP[monster["stars"]]
        self.player_hp = min(self.player_hp, self.player_max_hp)
        self.show_battle("モンスターが現れた！")

    def show_battle(self, message):
        self.clear_content()
        monster = self.active_monster
        enemy_max_hp = monster["boss_hp"] if monster.get("boss") else STAR_HP[monster["stars"]]
        rank_text = "BOSS" if monster.get("boss") else "★" * monster["stars"]
        self.set_status(
            "{}  {}\n敵HP: {}/{}\n自分HP: {}/{}\n{}".format(
                rank_text,
                monster["name"],
                self.enemy_hp,
                enemy_max_hp,
                self.player_hp,
                self.player_max_hp,
                message,
            )
        )
        y = 18
        attack_button = ui.Button(title="素手で攻撃（10）", frame=(16, y, 343, 48))
        attack_button.tint_color = "#B71C1C"
        attack_button.action = self.attack_with_fist
        self.content.add_subview(attack_button)
        y += 62
        for item in dict.fromkeys(self.inventory):
            if item in WEAPON_POWER:
                power = WEAPON_POWER[item]
                uses = self.weapon_uses.get(item, weapon_uses_for(item))
                button = ui.Button(
                    title="{}で攻撃（基準{}／残り{}回）".format(item, power, uses),
                    frame=(16, y, 343, 48),
                )
                button.tint_color = "#C62828"
                button.item_name = item
                button.action = self.attack_with_item
                self.content.add_subview(button)
                y += 62
        escape_button = ui.Button(title="逃げる（試作では星で判定）", frame=(16, y, 343, 48))
        escape_button.action = self.try_escape
        self.content.add_subview(escape_button)
        y += 62
        inventory_label = ui.Label(frame=(20, y, 335, 50))
        inventory_label.number_of_lines = 0
        counts = self.inventory_counts()
        summary = []
        for item, count in counts.items():
            count_text = " ×{}".format(count) if count > 1 else ""
            summary.append(item + count_text)
        inventory_label.text = "持ち物: {} / {}\n{}".format(
            len(self.inventory), self.capacity, ", ".join(summary) or "なし"
        )
        self.content.add_subview(inventory_label)
        self.content.content_size = (375, y + 80)

    def attack_with_fist(self, sender):
        self.resolve_player_attack(10, "素手で攻撃！")

    def attack_with_item(self, sender):
        item_name = sender.item_name
        uses_left = self.weapon_uses.get(item_name, weapon_uses_for(item_name)) - 1
        if uses_left <= 0:
            self.weapon_uses.pop(item_name, None)
            self.inventory.remove(item_name)
        else:
            self.weapon_uses[item_name] = uses_left
        self.resolve_player_attack(WEAPON_POWER[item_name], "{}で攻撃！".format(item_name))

    def revive_if_possible(self):
        if not self.inventory:
            self.player_hp = self.player_max_hp
            return ""
        lost_item = random.choice(self.inventory)
        self.inventory.remove(lost_item)
        if lost_item in WEAPON_POWER:
            self.weapon_uses.pop(lost_item, None)
        self.player_hp = self.player_max_hp
        return lost_item

    def resolve_player_attack(self, power, message):
        damage = random.randint((power * 8) // 10, power)
        self.enemy_hp = max(0, self.enemy_hp - damage)
        message = "{}（{}ダメージ）".format(message, damage)
        if self.enemy_hp == 0:
            self.finish_battle(True, message + "\nモンスターを倒した！")
            return
        enemy_tier = 3 if self.active_monster.get("boss") else self.active_monster["stars"]
        enemy_base_damage = 10 * enemy_tier
        enemy_damage = random.randint((enemy_base_damage * 8) // 10, enemy_base_damage)
        self.player_hp = max(0, self.player_hp - enemy_damage)
        enemy_message = "モンスターの反撃！（{}ダメージ）".format(enemy_damage)
        if self.player_hp == 0:
            lost_item = self.revive_if_possible()
            if lost_item:
                revival_message = "{}を失い、回復して帰還！".format(lost_item)
            else:
                revival_message = "アイテムなしで回復して帰還！"
            self.finish_battle(False, message + "\n" + enemy_message + "\nゲームオーバー\n" + revival_message)
            return
        self.show_battle(message + "\n" + enemy_message)

    def try_escape(self, sender):
        if self.active_monster.get("boss"):
            self.show_battle("ボス戦からは逃げられない！")
            return
        if self.active_monster["stars"] == 1:
            success = random.random() < 0.8
        elif self.active_monster["stars"] == 2:
            success = random.random() < 0.5
        else:
            success = random.random() < 0.2
        if success:
            self.show_battle_selection()
        else:
            enemy_tier = self.active_monster["stars"]
            enemy_base_damage = 10 * enemy_tier
            enemy_damage = random.randint((enemy_base_damage * 8) // 10, enemy_base_damage)
            self.player_hp = max(0, self.player_hp - enemy_damage)
            enemy_message = "逃走失敗！モンスターの攻撃！（{}ダメージ）".format(enemy_damage)
            if self.player_hp == 0:
                lost_item = self.revive_if_possible()
                if lost_item:
                    revival_message = "{}を失い、回復して帰還！".format(lost_item)
                else:
                    revival_message = "アイテムなしで回復して帰還！"
                self.finish_battle(False, enemy_message + "\nゲームオーバー\n" + revival_message)
            else:
                self.show_battle(enemy_message)

    def finish_battle(self, won, message):
        if won:
            hp_gain = 0 if self.active_monster.get("boss") else MAX_HP_GAIN_BY_STAR[self.active_monster["stars"]]
            self.player_max_hp += hp_gain
            self.player_hp = self.player_max_hp
            capacity_message = ""
            if not self.active_monster.get("boss"):
                stars = self.active_monster["stars"]
                self.defeated_by_stars[stars] += 1
                interval = CAPACITY_GAIN_INTERVAL[stars]
                if self.defeated_by_stars[stars] % interval == 0:
                    self.capacity += 1
                    capacity_message = " 所持容量+1！"
            message += "\n勝利！最大HP+{}、HP全回復！{}".format(hp_gain, capacity_message)
            drop = self.active_monster["drop"]
            if self.active_monster["kind"] == "回復系":
                roll = random.random()
                if roll < 0.5:
                    drop = "りんご"
                elif roll < 0.8:
                    drop = "金のリンゴ"
                else:
                    drop = None
            elif drop == "オレンジジュース" and random.random() >= 0.3:
                drop = None
            if drop is None:
                drop_message = "\n今回はアイテムがドロップしなかった。"
            elif drop.startswith("成長フード（+"):
                food_value = int(drop.split("+")[1].rstrip("）"))
                self.player_max_hp += food_value
                self.capacity += 1
                drop_message = "\n{}を自動摂取！最大HP+{}、所持容量+1。".format(drop, food_value)
            elif len(self.inventory) < self.capacity:
                self.inventory.append(drop)
                if drop in WEAPON_POWER:
                    self.weapon_uses[drop] = self.weapon_uses.get(drop, 0) + weapon_uses_for(drop)
                    drop_message = "\n{}を自動取得！使用回数+{}回。".format(drop, weapon_uses_for(drop))
                else:
                    drop_message = "\n{}を自動取得！".format(drop)
            else:
                drop_message = "\n容量いっぱいで、{}は入らなかった。".format(drop)
            message += drop_message
        self.clear_content()
        self.set_status(message)
        result = ui.Label(frame=(20, 28, 335, 100))
        result.number_of_lines = 0
        result.font = ("<System-Bold>", 20)
        result.alignment = ui.ALIGN_CENTER
        result.text = "勝利！" if won else ("ゲームオーバー" if "ゲームオーバー" in message else "敗北…")
        self.content.add_subview(result)
        again = ui.Button(title="地図にもどる", frame=(16, 160, 343, 50))
        again.tint_color = "#C62828"
        again.action = lambda sender: self.show_battle_selection()
        self.content.add_subview(again)
        self.content.content_size = (375, 240)


def run():
    RedPrototype().present("fullscreen")


if __name__ == "__main__":
    run()
