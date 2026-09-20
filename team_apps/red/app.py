"""レッド班 Day 2 試作：6体のモンスターを選んで戦う。"""

import random

import ui


MONSTERS = [
    {"name": "森のぷに", "stars": 1, "kind": "攻撃系", "drop": "木の棒", "drop_power": 50},
    {"name": "草むらモン", "stars": 1, "kind": "回復系", "drop": "成長フード", "drop_power": 10},
    {"name": "石ころモン", "stars": 1, "kind": "強化系", "drop": "木の棒", "drop_power": 50},
    {"name": "青い影", "stars": 2, "kind": "弱体化系", "drop": "弓", "drop_power": 100},
    {"name": "赤い影", "stars": 2, "kind": "攻撃系", "drop": "剣", "drop_power": 100},
    {"name": "幻の王", "stars": 3, "kind": "レア", "drop": "オレンジジュース", "drop_power": 0},
]

STAR_NAMES = {
    1: "かわいいでちゅね",
    2: "かわいいですね",
    3: "かわいいでございますね",
}

STAR_HP = {1: 100, 2: 300, 3: 500}


class RedPrototype(ui.View):
    def __init__(self):
        super().__init__(frame=(0, 0, 375, 667))
        self.name = "レッド班・皇居救出作戦 試作"
        self.background_color = "#FFEBEE"
        self.inventory = []
        self.capacity = 3
        self.current_screen = "map"
        self.active_monster = None
        self.player_max_hp = 100
        self.player_hp = 100
        self.enemy_hp = 0
        self.monsters = list(MONSTERS)
        random.shuffle(self.monsters)
        self.build_header()
        self.show_map()

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

    def show_map(self):
        self.current_screen = "map"
        self.clear_content()
        self.set_status(
            "皇居を占拠したモンスターを探そう。\n"
            "マークで系統、星で強さが分かる。詳しいアイテムは秘密！\n"
            "所持: {}/{}個".format(len(self.inventory), self.capacity)
        )
        y = 8
        for index, monster in enumerate(self.monsters):
            card = ui.Label(frame=(16, y, 343, 58))
            card.number_of_lines = 0
            card.font = ("<System>", 14)
            card.text = "{}  {}  {}\nおおまかな位置：中央広場から約{}歩".format(
                "★" * monster["stars"],
                monster["kind"],
                STAR_NAMES[monster["stars"]],
                10 + index * 2,
            )
            self.content.add_subview(card)
            find_button = ui.Button(title="ARで探す", frame=(16, y + 60, 343, 42))
            find_button.tint_color = "#C62828"
            find_button.monster_index = index
            find_button.action = self.begin_search
            self.content.add_subview(find_button)
            y += 112
        self.content.content_size = (375, y + 12)

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

    def start_battle(self, sender):
        self.current_screen = "battle"
        self.enemy_hp = STAR_HP[self.active_monster["stars"]]
        self.player_hp = min(self.player_hp, self.player_max_hp)
        self.show_battle("モンスターが現れた！")

    def show_battle(self, message):
        self.clear_content()
        monster = self.active_monster
        self.set_status(
            "{}  {}\n敵HP: {}/{}\n自分HP: {}/{}\n{}".format(
                "★" * monster["stars"],
                monster["name"],
                self.enemy_hp,
                STAR_HP[monster["stars"]],
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
        for item in self.inventory:
            if item in ("木の棒", "剣", "弓"):
                power = {"木の棒": 50, "剣": 100, "弓": 100}[item]
                button = ui.Button(title="{}で攻撃（{}）".format(item, power), frame=(16, y, 343, 48))
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
        inventory_label.text = "持ち物: {} / {}\n{}".format(
            len(self.inventory), self.capacity, ", ".join(self.inventory) or "なし"
        )
        self.content.add_subview(inventory_label)
        self.content.content_size = (375, y + 80)

    def attack_with_fist(self, sender):
        self.resolve_player_attack(10, "素手で攻撃！")

    def attack_with_item(self, sender):
        self.inventory.remove(sender.item_name)
        power = {"木の棒": 50, "剣": 100, "弓": 100}[sender.item_name]
        self.resolve_player_attack(power, "{}で攻撃！".format(sender.item_name))

    def resolve_player_attack(self, power, message):
        self.enemy_hp = max(0, self.enemy_hp - power)
        if self.enemy_hp == 0:
            self.finish_battle(True, message + "\nモンスターを倒した！")
            return
        enemy_damage = 10 * self.active_monster["stars"]
        self.player_hp = max(0, self.player_hp - enemy_damage)
        if self.player_hp == 0:
            self.finish_battle(False, message + "\nモンスターの反撃で倒れた…")
            return
        self.show_battle(message + "\nモンスターの反撃！")

    def try_escape(self, sender):
        if self.active_monster["stars"] == 1:
            success = random.random() < 0.8
        elif self.active_monster["stars"] == 2:
            success = random.random() < 0.5
        else:
            success = random.random() < 0.2
        if success:
            self.show_map()
        else:
            self.player_hp = max(0, self.player_hp - 10 * self.active_monster["stars"])
            if self.player_hp == 0:
                self.finish_battle(False, "逃げられず、モンスターの攻撃を受けた…")
            else:
                self.show_battle("逃走失敗！モンスターの攻撃！")

    def finish_battle(self, won, message):
        if won:
            drop = self.active_monster["drop"]
            if len(self.inventory) < self.capacity:
                self.inventory.append(drop)
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
        result.text = "勝利！" if won else "敗北…"
        self.content.add_subview(result)
        again = ui.Button(title="地図にもどる", frame=(16, 160, 343, 50))
        again.tint_color = "#C62828"
        again.action = lambda sender: self.show_map()
        self.content.add_subview(again)
        self.content.content_size = (375, 240)


def run():
    RedPrototype().present("fullscreen")


if __name__ == "__main__":
    run()
