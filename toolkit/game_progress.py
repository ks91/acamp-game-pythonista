"""Local, atomic progress snapshots; never stores GPS, tokens or UI objects."""
import copy
import hashlib
import json
import math
import os
import tempfile
import threading


FIELDS = {
    "red": {
        "inventory": "strings", "weapon_uses": "counts", "capacity": "positive",
        "defeated_by_stars": "stars", "unlocked_destinations": "strings",
        "defeated_bosses": "strings", "player_max_hp": "positive", "player_hp": "count",
    },
    "purple": {
        "score": "count", "boss_hp": "count", "lives": "count",
        "arrived": "flags", "solved": "flags", "used_question_indexes": "indices",
        "chest_arrival_checked": "flags", "chest_riddle_checked": "flags",
        "chest_items": "items2", "item_inventory": "counts",
        "good_bacteria_visible": "bool", "good_bacteria_hp": "count",
    },
    "pink": {
        "coins": "count", "tickets": "counts", "distance_remainder_m": "number",
        "collected_coin_ids": "strings",
    },
}
_LOCK = threading.Lock()


def _valid(value, kind):
    if kind in ("count", "positive"):
        return type(value) is int and value >= (1 if kind == "positive" else 0)
    if kind == "number":
        return type(value) in (int, float) and math.isfinite(value) and value >= 0
    if kind == "bool":
        return type(value) is bool
    if kind in ("counts", "stars"):
        return (type(value) is dict
                and all(type(k) is str and _valid(v, "count") for k, v in value.items())
                and (kind != "stars" or set(value) == {"1", "2", "3"}))
    if type(value) is not list:
        return False
    if kind == "strings":
        return all(type(item) is str for item in value)
    if kind == "indices":
        return all(_valid(item, "count") for item in value)
    if kind == "flags":
        return len(value) == 2 and all(type(item) is bool for item in value)
    if kind == "items2":
        return len(value) == 2 and all(item is None or type(item) is str for item in value)
    return False


class GameProgress:
    def __init__(self, view, config, game_team, directory=None):
        self.game_team = game_team
        self.identity = {
            "player_team": config.TEAM_ID,
            "game_team": game_team,
            "mode": getattr(config, "SELECTED_GAME_MODE", None) or "default",
            "configured_session": config.GAME_SESSION_ID,
        }
        digest = hashlib.sha256(json.dumps(self.identity, sort_keys=True).encode()).hexdigest()
        directory = directory or os.path.expanduser("~/Documents/acamp-game-progress")
        self.path = os.path.join(directory, digest + ".json")
        self.defaults = self._snapshot(view)
        self.set_fields = {name for name in FIELDS[game_team] if isinstance(getattr(view, name), set)}
        self.warning = ""
        self.session_id = config.GAME_SESSION_ID
        document = self._read()
        if document is not None:
            self.session_id = document["last_session"]
        self._restore(view, document)

    def _snapshot(self, view):
        state = {name: sorted(getattr(view, name)) if isinstance(getattr(view, name), set)
                 else getattr(view, name) for name in FIELDS[self.game_team]}
        # Copy mutable values and normalize integer JSON dictionary keys.
        return json.loads(json.dumps(state, ensure_ascii=False, allow_nan=False))

    def _valid_state(self, state):
        if not isinstance(state, dict):
            return False
        if any(name not in state or not _valid(state[name], kind)
               for name, kind in FIELDS[self.game_team].items()):
            return False
        # Fixed item catalogs must remain complete after restoring a snapshot.
        for name in ("tickets", "item_inventory"):
            if name in self.defaults and set(state[name]) != set(self.defaults[name]):
                return False
        if self.game_team == "red" and state["player_hp"] > state["player_max_hp"]:
            return False
        if self.game_team == "purple":
            if state["boss_hp"] > self.defaults["boss_hp"] or state["lives"] > self.defaults["lives"]:
                return False
        return True

    def _read(self):
        failed = False
        for path in (self.path, self.path + ".bak"):
            try:
                with open(path, encoding="utf-8") as source:
                    document = json.load(source)
                if (not isinstance(document, dict) or document.get("version") != 1
                        or document.get("identity") != self.identity
                        or not isinstance(document.get("sessions"), dict)
                        or not isinstance(document.get("last_session"), str)
                        or document["last_session"] not in document["sessions"]
                        or not all(self._valid_state(state) for state in document["sessions"].values())):
                    raise ValueError("invalid progress document")
                if failed:
                    self.warning = "保存データを予備の記録から復元しました。"
                return document
            except FileNotFoundError:
                continue
            except (OSError, ValueError, TypeError, OverflowError, RecursionError):
                failed = True
        if failed:
            self.warning = "保存データを読み込めませんでした。初期状態で開始します。"
        return None

    def _restore(self, view, document):
        state = copy.deepcopy((document or {}).get("sessions", {}).get(self.session_id, self.defaults))
        # A game-over animation must not restore a zero-life, unplayable screen.
        if self.game_team == "purple" and state["lives"] == 0:
            state = copy.deepcopy(self.defaults)
        for name, value in state.items():
            if name not in FIELDS[self.game_team]:
                continue
            if name in self.set_fields:
                value = set(value)
            elif name == "defeated_by_stars":
                value = {int(k): v for k, v in value.items()}
            setattr(view, name, value)

    @staticmethod
    def _atomic_write(path, document):
        directory = os.path.dirname(path)
        os.makedirs(directory, exist_ok=True)
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=directory,
                                             prefix=".progress-", delete=False) as destination:
                temporary_path = destination.name
                json.dump(document, destination, ensure_ascii=False, allow_nan=False)
                destination.flush()
                os.fsync(destination.fileno())
            os.replace(temporary_path, path)
        finally:
            if temporary_path and os.path.exists(temporary_path):
                os.unlink(temporary_path)

    def save(self, view, reset=False):
        try:
            state = self._snapshot(view)
            if self.game_team == "purple" and state["lives"] == 0:
                state = copy.deepcopy(self.defaults)
                reset = True
            if not self._valid_state(state):
                raise ValueError("invalid progress state")
            with _LOCK:
                previous = self._read()
                document = copy.deepcopy(previous) if previous else {
                    "version": 1, "identity": self.identity, "sessions": {},
                }
                document["sessions"][self.session_id] = state
                document["last_session"] = self.session_id
                # Reset also replaces the backup so recovery cannot undo a reset.
                self._atomic_write(self.path + ".bak", document if reset or previous is None else previous)
                self._atomic_write(self.path, document)
            self.warning = ""
            return True
        except (OSError, ValueError, TypeError, OverflowError, RecursionError) as error:
            self.warning = "進行を保存できません。ゲームを閉じる前にスタッフへ伝えてください。({})".format(type(error).__name__)
            return False

    def bind_session(self, view, session_id):
        if not isinstance(session_id, str) or not session_id or session_id == self.session_id:
            return False
        self.session_id = session_id
        self._restore(view, self._read())
        self.save(view)
        return True


def make_progress_store(view, config, game_team):
    if not config or not getattr(config, "TEAM_ID", "") or not getattr(config, "GAME_SESSION_ID", ""):
        return None
    return GameProgress(view, config, game_team)


def progress_warning(view):
    progress = getattr(view, "_progress", None)
    return "\n" + progress.warning if progress and progress.warning else ""
