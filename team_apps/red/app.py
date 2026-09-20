"""レッド班 Day 2 試作：6体のモンスターを選んで戦う。"""

import random

import ui


MONSTERS = [
    {"name": "森のぷに", "stars": 1, "kind": "攻撃系", "drop": "木の棒", "drop_power": 50},
    {"name": "草むらモン", "stars": 1, "kind": "回復系", "drop": "成長フード（+10）", "drop_power": 10},
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

    def show_battle_selection(self):
        self.current_screen = "battle_selection"
        self.clear_content()
        self.set_status(
            "戦闘画面の第一試作\n"
            "戦いたいモンスターを選ぼう。星が高いほど強い。\n"
            "所持: {}/{}個".format(len(self.inventory), self.capacity)
        )
        inventory_button = ui.Button(title="アイテムを見る", frame=(16, 8, 343, 42))
        inventory_button.tint_color = "#6A1B9A"
        inventory_button.action = self.show_inventory
        self.content.add_subview(inventory_button)
        y = 62
        for index, monster in enumerate(self.monsters):
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
            fight_button.monster_index = index
            fight_button.action = self.start_selected_battle
            self.content.add_subview(fight_button)
            y += 112
        self.content.content_size = (375, y + 12)

    def start_selected_battle(self, sender):
        self.active_monster = self.monsters[sender.monster_index]
        self.start_battle(sender)

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
            for item in self.inventory:
                label = ui.Label(frame=(20, y, 335, 44))
                label.number_of_lines = 0
                label.text = "・{}\n  {}".format(item, effect_text.get(item, "効果は戦闘で確認"))
                self.content.add_subview(label)
                y += 58
        back = ui.Button(title="戦う相手を選ぶ", frame=(16, y + 12, 343, 48))
        back.tint_color = "#C62828"
        back.action = lambda button: self.show_battle_selection()
        self.content.add_subview(back)
        self.content.content_size = (375, y + 80)

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

    def revive_if_possible(self):
        if not self.inventory:
            self.player_hp = self.player_max_hp
            return ""
        lost_item = random.choice(self.inventory)
        self.inventory.remove(lost_item)
        self.player_hp = self.player_max_hp
        return lost_item

    def resolve_player_attack(self, power, message):
        damage = random.randint((power * 8) // 10, power)
        self.enemy_hp = max(0, self.enemy_hp - damage)
        message = "{}（{}ダメージ）".format(message, damage)
        if self.enemy_hp == 0:
            self.finish_battle(True, message + "\nモンスターを倒した！")
            return
        enemy_base_damage = 10 * self.active_monster["stars"]
        enemy_damage = random.randint((enemy_base_damage * 8) // 10, enemy_base_damage)
        self.player_hp = max(0, self.player_hp - enemy_damage)
        enemy_message = "モンスターの反撃！（{}ダメージ）".format(enemy_damage)
        if self.player_hp == 0:
            lost_item = self.revive_if_possible()
            if lost_item:
                revival_message = "{}を失って全回復・復活！".format(lost_item)
            else:
                revival_message = "アイテムなしで全回復・復活！"
            self.show_battle(message + "\n" + enemy_message + "\nHP0！" + revival_message)
            return
        self.show_battle(message + "\n" + enemy_message)

    def try_escape(self, sender):
        if self.active_monster["stars"] == 1:
            success = random.random() < 0.8
        elif self.active_monster["stars"] == 2:
            success = random.random() < 0.5
        else:
            success = random.random() < 0.2
        if success:
            self.show_battle_selection()
        else:
            enemy_base_damage = 10 * self.active_monster["stars"]
            enemy_damage = random.randint((enemy_base_damage * 8) // 10, enemy_base_damage)
            self.player_hp = max(0, self.player_hp - enemy_damage)
            enemy_message = "逃走失敗！モンスターの攻撃！（{}ダメージ）".format(enemy_damage)
            if self.player_hp == 0:
                lost_item = self.revive_if_possible()
                if lost_item:
                    revival_message = "{}を失って全回復・復活！".format(lost_item)
                else:
                    revival_message = "アイテムなしで全回復・復活！"
                self.show_battle(enemy_message + "\n" + revival_message)
            else:
                self.show_battle(enemy_message)

    def finish_battle(self, won, message):
        if won:
            self.player_hp = self.player_max_hp
            message += "\n勝利！HP全回復！"
            drop = self.active_monster["drop"]
            if drop.startswith("成長フード（+"):
                food_value = int(drop.split("+")[1].rstrip("）"))
                self.player_max_hp += food_value
                self.capacity += 1
                drop_message = "\n{}を自動摂取！最大HP+{}、所持容量+1。".format(drop, food_value)
            elif len(self.inventory) < self.capacity:
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
        again.action = lambda sender: self.show_battle_selection()
        self.content.add_subview(again)
        self.content.content_size = (375, 240)


def run():
    RedPrototype().present("fullscreen")


if __name__ == "__main__":
    run()
