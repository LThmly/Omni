"""Phone state. The pygame window and the old page both speak this."""

from __future__ import annotations

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULES = ("checklist", "scoreboard", "progress", "key_value")
DEMOS = ("shopping", "scoreboard", "hydration", "notes")


def clamp(number, lo, hi):
    return max(lo, min(hi, number))


def num(value, fallback=0):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    if number.is_integer():
        return int(number)
    return number


def blurb(app):
    data = app.get("state") or {}
    module = app.get("module")
    if module == "checklist":
        left = sum(1 for item in data.get("items") or [] if not item.get("checked"))
        return "1 left" if left == 1 else "%s left" % left
    if module == "scoreboard":
        return "  ·  ".join(
            "%s %s" % (side.get("name"), side.get("score")) for side in data.get("sides") or []
        )
    if module == "progress":
        return "%s / %s %s" % (data.get("value"), data.get("goal"), data.get("unit"))
    row = (data.get("rows") or [None])[0]
    if not row:
        return "Empty"
    return "%s: %s" % (row.get("label"), row.get("value"))


def agent_label(agent, say):
    if agent == "listening":
        return "Listening"
    if agent == "thinking":
        return "Thinking"
    if say:
        return say
    return "Ready when you are"


def layout_of(modules, module_name):
    layout = ((modules.get(module_name) or {}).get("layout")) or {}
    return {
        "margin": layout.get("margin") or 18,
        "header_h": layout.get("header_h") or 48,
        "row_h": layout.get("row_h") or 56,
        "bar_h": layout.get("bar_h") or 16,
    }


def apply_action(app, action):
    name = action.get("action")
    args = action.get("args") or {}
    data = app.get("state")
    module = app.get("module")
    if not isinstance(data, dict):
        return
    if module == "checklist":
        items = data.setdefault("items", [])
        if name == "scroll":
            data["cursor"] = clamp(
                num(data.get("cursor")) + num(args.get("dir")), 0, max(0, len(items) - 1)
            )
        elif name == "toggle":
            index = num(data.get("cursor"))
            if 0 <= index < len(items):
                items[index]["checked"] = not items[index].get("checked")
        elif name == "append" and args.get("label"):
            items.append({"label": str(args["label"]), "checked": False})
        elif name == "remove" and items:
            index = clamp(num(data.get("cursor")), 0, len(items) - 1)
            items.pop(index)
            data["cursor"] = clamp(index, 0, max(0, len(items) - 1))
    elif module == "scoreboard":
        sides = data.get("sides") or []
        if name == "scroll":
            data["cursor"] = clamp(
                num(data.get("cursor")) + num(args.get("dir")), 0, max(0, len(sides) - 1)
            )
        elif name in ("inc", "dec") and sides:
            index = num(data.get("cursor"))
            if 0 <= index < len(sides):
                step = 1 if name == "inc" else -1
                sides[index]["score"] = max(0, num(sides[index].get("score")) + step)
    elif module == "progress" and name == "add":
        amount = num(data.get("step")) if args.get("amount") is None else num(args.get("amount"))
        data["value"] = min(num(data.get("goal")), num(data.get("value")) + amount)
    elif module == "key_value" and name == "scroll":
        rows = data.get("rows") or []
        data["cursor"] = clamp(
            num(data.get("cursor")) + num(args.get("dir")), 0, max(0, len(rows) - 1)
        )


class Device:
    def __init__(self):
        self.screen = "home"
        self.app_id = None
        self.registry = []
        self.agent = "idle"
        self.say = ""
        self.proposal = None
        self.modules = {}
        self.respond_until = None

    def load_modules(self, root=ROOT):
        folder = Path(root) / "contract" / "modules"
        for name in MODULES:
            self.modules[name] = json.loads((folder / (name + ".json")).read_text())

    def load_demos(self, root=ROOT):
        folder = Path(root) / "contract" / "fixtures" / "apps"
        self.registry = [json.loads((folder / (name + ".json")).read_text()) for name in DEMOS]
        self.screen = "home"
        self.app_id = None
        self.proposal = None
        self.agent = "idle"
        self.say = ""
        self.respond_until = None

    def empty(self):
        self.registry = []
        self.screen = "home"
        self.app_id = None
        self.proposal = None
        self.agent = "idle"
        self.say = ""
        self.respond_until = None

    def find(self, app_id):
        for app in self.registry:
            if app.get("id") == app_id:
                return app
        return None

    def current(self):
        if self.screen != "app":
            return None
        return self.find(self.app_id)

    def snapshot(self):
        return {
            "registry": self.registry,
            "screen": self.screen,
            "appId": self.app_id,
        }

    def save(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.snapshot(), indent=2))
        tmp.replace(path)

    def restore(self, path):
        path = Path(path)
        if not path.exists():
            return False
        try:
            saved = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            return False
        registry = saved.get("registry")
        if not isinstance(registry, list):
            return False
        self.registry = registry
        self.screen = saved.get("screen") or "home"
        self.app_id = saved.get("appId")
        if self.screen == "app" and self.find(self.app_id) is None:
            self.screen = "home"
            self.app_id = None
        return True

    def tick(self, now):
        if self.agent == "responding" and self.respond_until is not None and now >= self.respond_until:
            self.agent = "idle"
            self.respond_until = None
            return True
        return False

    def arm_idle(self, now):
        self.respond_until = now + 4.2

    def apply_turn(self, turn, now):
        self.say = turn.get("say") or ""
        self.agent = "responding"
        if turn.get("op") == "propose" and turn.get("app"):
            self.proposal = turn
            self.respond_until = None
        elif turn.get("op") == "mutate":
            app = self.find(turn.get("app_id"))
            if app is not None:
                for action in turn.get("actions") or []:
                    apply_action(app, action)
                self.screen = "app"
                self.app_id = app.get("id")
            self.proposal = None
            self.arm_idle(now)
        else:
            self.proposal = None
            self.arm_idle(now)

    def confirm(self):
        turn = self.proposal
        if not turn or not turn.get("app"):
            return
        app = copy.deepcopy(turn["app"])
        for index, existing in enumerate(self.registry):
            if existing.get("id") == app.get("id"):
                self.registry[index] = app
                break
        else:
            self.registry.append(app)
        self.screen = "app"
        self.app_id = app.get("id")
        self.proposal = None
        self.agent = "idle"
        self.say = ""
        self.respond_until = None

    def cancel(self):
        self.proposal = None
        self.agent = "idle"
        self.say = ""
        self.respond_until = None

    def open_app(self, app_id):
        if self.find(app_id) is None:
            return
        self.screen = "app"
        self.app_id = app_id
        self.proposal = None

    def go_home(self):
        self.screen = "home"
        self.app_id = None
        self.proposal = None

    def local(self, act, index=None, amount=None, app_id=None):
        """Apply a finger tap that does not call the network. Return 'turn' if the caller must."""
        if self.agent == "thinking":
            return None
        if act == "line":
            return "turn"
        if act == "open":
            self.open_app(app_id)
            return None
        if act == "back":
            self.go_home()
            return None
        if act == "confirm":
            self.confirm()
            return None
        if act == "cancel":
            self.cancel()
            return None
        app = self.current()
        if app is None or not isinstance(app.get("state"), dict):
            return None
        if act in ("toggle", "inc", "dec", "focus") and index is not None:
            app["state"]["cursor"] = int(index)
        if act == "toggle":
            apply_action(app, {"action": "toggle", "args": {}})
        elif act in ("inc", "dec"):
            apply_action(app, {"action": act, "args": {}})
        elif act == "add":
            apply_action(app, {"action": "add", "args": {"amount": amount}})
        return None
