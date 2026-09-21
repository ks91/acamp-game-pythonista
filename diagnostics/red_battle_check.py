"""Pythonista-only offline battle check. Run this file, then tap test buttons.

Uses Red's real battle implementation, but never fetches a scenario or posts
claims. Test inventory/HP exist only in this view and disappear when it closes.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import ui
from team_apps.red.app import MONSTERS, RedPrototype


class RedBattleCheck(RedPrototype):
    persist_progress = False

    def refresh_server_scenario(self):
        pass  # Offline check: do not start the scenario worker.

    def _claim_active_server_place(self):
        pass  # Test victories must never be sent to the server.

    def show_battle_selection(self, sender=None):
        self.current_screen = "battle_selection"
        self.clear_content()
        self.name = "Red 戦闘確認（オフライン）"
        self.set_status("戦闘の実機確認用です。\n通信・得点登録はしません。\n結果画面の「地図にもどる」でここへ戻ります。")
        cases = (
            ("素手：ゆっくり押す／連打→勝利", "fist"),
            ("武器：木の棒を2回使い切る", "weapon"),
            ("敗北：HP1から攻撃", "defeat"),
        )
        for index, (title, case) in enumerate(cases):
            button = ui.Button(title=title, frame=(16, 20 + index * 70, 343, 54))
            button.test_case = case
            button.action = self.start_check
            self.content.add_subview(button)
        self.style_buttons()
        self.content.content_size = (375, 250)

    def start_check(self, sender):
        case = sender.test_case
        self.inventory = ["木の棒"] if case == "weapon" else []
        self.weapon_uses = {"木の棒": 2} if case == "weapon" else {}
        self.player_max_hp = 1000
        self.player_hp = 1 if case == "defeat" else 1000
        self.active_monster = MONSTERS[5 if case == "weapon" else 0].copy()
        self.active_place_id = None
        self.start_battle()


if __name__ == "__main__":
    RedBattleCheck().present("fullscreen")
