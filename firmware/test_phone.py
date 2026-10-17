"""Behavior of the pygame phone. No window required."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from logic import Device, apply_action, blurb
from phone import PW, PH, App, Hit, Screen, phone_point, screen_point

import pygame


class LogicTest(unittest.TestCase):
    def setUp(self):
        self.device = Device()
        self.device.load_modules()
        self.device.load_demos()

    def test_toggle_and_floor_and_cap(self):
        shopping = self.device.find("shopping")
        apply_action(shopping, {"action": "toggle", "args": {}})
        self.assertTrue(shopping["state"]["items"][0]["checked"])
        apply_action(shopping, {"action": "toggle", "args": {}})
        self.assertFalse(shopping["state"]["items"][0]["checked"])

        board = self.device.find("pingpong")
        apply_action(board, {"action": "dec", "args": {}})
        self.assertEqual(board["state"]["sides"][0]["score"], 0)
        apply_action(board, {"action": "inc", "args": {}})
        self.assertEqual(board["state"]["sides"][0]["score"], 1)

        water = self.device.find("water")
        apply_action(water, {"action": "add", "args": {"amount": 16}})
        self.assertEqual(water["state"]["value"], 32)
        apply_action(water, {"action": "add", "args": {"amount": 100}})
        self.assertEqual(water["state"]["value"], 64)
        self.assertEqual(blurb(shopping), "2 left")

    def test_propose_then_confirm_and_mutate(self):
        self.device.empty()
        self.device.apply_turn(
            {
                "op": "propose",
                "say": "Make one?",
                "app": {
                    "id": "shopping",
                    "module": "checklist",
                    "title": "Shopping",
                    "state": {"cursor": 0, "items": [{"label": "Milk", "checked": False}]},
                },
            },
            now=0,
        )
        self.assertIsNotNone(self.device.proposal)
        self.device.confirm()
        self.assertEqual(self.device.app_id, "shopping")
        self.assertEqual(len(self.device.registry), 1)
        self.device.apply_turn(
            {
                "op": "mutate",
                "app_id": "shopping",
                "say": "Added coffee and bread.",
                "actions": [
                    {"action": "append", "args": {"label": "Coffee"}},
                    {"action": "append", "args": {"label": "Bread"}},
                ],
            },
            now=0,
        )
        labels = [item["label"] for item in self.device.find("shopping")["state"]["items"]]
        self.assertEqual(labels, ["Milk", "Coffee", "Bread"])

    def test_registry_roundtrip(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "registry.json"
            self.device.open_app("water")
            self.device.save(path)
            restored = Device()
            self.assertTrue(restored.restore(path))
            self.assertEqual(restored.app_id, "water")
            self.assertEqual(restored.screen, "app")


class PointerTest(unittest.TestCase):
    def test_turn_roundtrip(self):
        window = (800, 480)
        for turn in ("right", "left"):
            for point in ((10, 20), (240, 400), (470, 790), (0, 0), (479, 799)):
                mapped = phone_point(*screen_point(*point, window, turn), window, turn)
                self.assertIsNotNone(mapped)
                self.assertAlmostEqual(mapped[0], point[0], delta=0.6)
                self.assertAlmostEqual(mapped[1], point[1], delta=0.6)
        upright = phone_point(30, 40, (PW, PH), "none")
        self.assertEqual(upright, (30, 40))

    def test_black_bar_is_outside(self):
        self.assertIsNone(phone_point(1, 1, (1000, 480), "right"))


class PaintTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.font.init()

    def paint(self, device, name, agent="idle"):
        device.agent = agent
        screen = Screen()
        surf = pygame.Surface((PW, PH))
        screen.paint(surf, device, ticks=1000, draft="")
        folder = Path(tempfile.gettempdir()) / "omni-frames"
        folder.mkdir(exist_ok=True)
        pygame.image.save(surf, str(folder / name))
        return screen, surf

    def test_home_shopping_water_and_proposal(self):
        device = Device()
        device.load_modules()
        device.load_demos()
        screen, home = self.paint(device, "home.png")
        self.assertEqual(home.get_at((10, 10))[:3], (0, 0, 0))
        opens = [hit for hit in screen.hits if hit.act == "open"]
        self.assertEqual(len(opens), 0)
        self.assertTrue(any(hit.act == "launcher" for hit in screen.hits))
        device.local("open", app_id="shopping")
        screen, _surf = self.paint(device, "shopping.png")
        toggles = [hit for hit in screen.hits if hit.act == "toggle"]
        self.assertGreaterEqual(len(toggles), 2)
        device.local("toggle", index=0)
        self.assertTrue(device.find("shopping")["state"]["items"][0]["checked"])

        device.open_app("pingpong")
        screen, _surf = self.paint(device, "score.png")
        self.assertEqual(sorted(hit.act for hit in screen.hits if hit.act in ("inc", "dec")), ["dec", "dec", "inc", "inc"])
        device.local("inc", index=1)
        self.assertEqual(device.find("pingpong")["state"]["sides"][1]["score"], 1)
        self.assertEqual(device.find("pingpong")["state"]["cursor"], 1)

        device.open_app("water")
        screen, _surf = self.paint(device, "water.png")
        adds = [hit for hit in screen.hits if hit.act == "add"]
        self.assertEqual([hit.amount for hit in adds], [8, 16])
        device.local("add", amount=16)
        self.assertEqual(device.find("water")["state"]["value"], 32)

        device.empty()
        device.proposal = {
            "op": "propose",
            "say": "You don't have a shopping list yet. Make one?",
            "app": {"id": "shopping", "module": "checklist", "title": "Shopping", "state": {}},
        }
        screen, _surf = self.paint(device, "proposal.png")
        acts = {hit.act for hit in screen.hits}
        self.assertIn("confirm", acts)
        self.assertIn("cancel", acts)

        device.agent = "listening"
        _screen, listening = self.paint(device, "listening.png", agent="listening")
        turned = pygame.transform.rotate(listening, -90)
        self.assertEqual(turned.get_size(), (800, 480))
        pygame.image.save(turned, str(Path(tempfile.gettempdir()) / "omni-frames" / "kiosk.png"))

        mark = pygame.Surface((64, 64), pygame.SRCALPHA)
        from phone import omni_mark

        mark = omni_mark(64)
        self.assertEqual(mark.get_at((32, 32))[3], 0)


class LauncherTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_navigation_and_swipe(self):
        with tempfile.TemporaryDirectory() as folder:
            app = App("http://unused", "none", False, Path(folder) / "registry.json")
            app.device.go_home()
            def paint():
                app.screen.paint(app.phone, app.device, 1000, "")
            paint()
            app.on_down((240, 320))
            app.on_up((240, 320))
            self.assertTrue(app.screen.launcher)
            paint()
            selected = next(hit for hit in app.screen.hits if hit.act == "open")
            self.assertEqual(selected.app_id, "shopping")
            app.on_down((400, 500))
            app.on_move((400, 400))
            app.on_up((400, 400))
            self.assertEqual(app.screen.selection, 1)
            self.assertIsNone(app.device.current())
            app.on_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0))
            self.assertEqual(app.device.app_id, "pingpong")
            app.on_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0))
            self.assertIsNone(app.device.current())
            self.assertTrue(app.screen.launcher)
            app.on_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0))
            self.assertFalse(app.screen.launcher)

    def test_restart_restores_apps_but_opens_logo(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Path(folder) / "registry.json"
            device = Device()
            device.load_demos()
            device.open_app("shopping")
            device.save(store)
            app = App("http://unused", "none", False, store)
            self.assertEqual(len(app.device.registry), 4)
            self.assertIsNone(app.device.current())
            self.assertFalse(app.screen.launcher)

    def test_registry_sizes_and_wrapping(self):
        device = Device()
        device.load_demos()
        original = device.registry[:]
        for count in range(5):
            device.registry = original[:count]
            screen = Screen()
            screen.step_selection(device, -1)
            surface = pygame.Surface((PW, PH))
            screen.paint(surface, device, 0, "")
            nodes = [hit for hit in screen.hits if hit.act in ("open", "select")]
            self.assertEqual(len(nodes), count)
            self.assertEqual(len({hit.app_id for hit in nodes}), count)
            if count:
                self.assertEqual(screen.selection, count - 1)
                self.assertEqual(sum(hit.act == "open" for hit in nodes), 1)
            else:
                self.assertEqual(sum(hit.act == "line" for hit in screen.hits), 3)
            if count == 4:
                pygame.image.save(surface, "/tmp/omni-arc-ui.png")


if __name__ == "__main__":
    unittest.main()
