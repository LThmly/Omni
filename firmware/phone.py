#!/usr/bin/env python3
"""Omni phone, drawn with pygame.

Laptop, upright 480×800 window:

    python3 firmware/phone.py

Pi, fullscreen, turned onto the 800×480 glass:

    python3 firmware/phone.py --kiosk

Quit with Ctrl+Shift+Q, or `python3 firmware/phone.py --stop`.
"""

from __future__ import annotations

import argparse
import base64
import copy
try:
    import fcntl
except ImportError:
    fcntl = None
import io
import json
import math
import os
import queue
import shutil
import signal
import struct
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import wave
from pathlib import Path

from logic import ROOT, Device, agent_label, blurb, layout_of, num

try:
    import pygame
except ImportError:
    pygame = None

PW, PH = 480, 800
HEADER_H = 58
DOCK_TOP = 724
BODY_H = DOCK_TOP - HEADER_H
PTT = pygame.Rect(16, 734, 448, 52) if pygame else None

BG = (0, 0, 0)
INK = (255, 255, 255)
MUTED = (167, 173, 186)
CARD = (34, 38, 51)
CARD2 = (42, 48, 64)
ACCENT = (255, 107, 61)
ACCENT_INK = (42, 18, 12)
BLUE = (122, 162, 255)
GREEN = (126, 224, 198)
AMBER = (255, 209, 102)
CURSOR = (42, 36, 31)
PTT_BG = (38, 43, 56)
PTT_LINE = (60, 68, 88)
GHOST = (52, 59, 78)
BAR = (44, 50, 66)
HAIRLINE = (42, 46, 58)
TILE_LINE = (49, 55, 72)
CHECK = (139, 147, 163)

BADGE = {
    "checklist": (ACCENT, ACCENT_INK),
    "scoreboard": (BLUE, (16, 19, 28)),
    "progress": (GREEN, (16, 34, 28)),
    "key_value": (AMBER, (36, 28, 12)),
}

ARROWS = (
    (-126, 58, 18, 11, 4.5),
    (-52, 48, 16, 10, 4.5),
    (15, 58, 18, 11, 4.5),
    (90, 50, 16, 10, 4.5),
    (162, 46, 16, 10, 4.5),
)

DEMO_LINES = (
    ("List", "Add milk to my shopping list."),
    ("Score", "Keep score for ping pong between me and Alex."),
    ("Water", "Log 16 ounces of water."),
)
TALK_LINE = DEMO_LINES[0][1]
STORE = Path.home() / ".omni" / "registry.json"
PID_PATH = Path.home() / ".omni" / "shell.pid"
WORDMARK = ROOT / "sim" / "neuropolitical.ttf"

_marks = {}
_lock = None


def placed(window, turn):
    width, height = window
    if turn in ("right", "left"):
        rotated = (PH, PW)
    else:
        rotated = (PW, PH)
    scale = min(width / rotated[0], height / rotated[1])
    origin_x = (width - rotated[0] * scale) / 2
    origin_y = (height - rotated[1] * scale) / 2
    return scale, origin_x, origin_y


def phone_point(mx, my, window, turn):
    """Map a window pixel back onto the upright 480×800 phone."""
    scale, origin_x, origin_y = placed(window, turn)
    if scale <= 0:
        return None
    rx = (mx - origin_x) / scale
    ry = (my - origin_y) / scale
    if turn == "right":
        # Clockwise 90°. The portrait top lands on the right edge of the glass.
        x = ry
        y = PH - rx
    elif turn == "left":
        x = PW - ry
        y = rx
    else:
        x, y = rx, ry
    if x < -0.5 or y < -0.5 or x > PW + 0.5 or y > PH + 0.5:
        return None
    return min(max(x, 0), PW - 0.01), min(max(y, 0), PH - 0.01)


def screen_point(x, y, window, turn):
    scale, origin_x, origin_y = placed(window, turn)
    if turn == "right":
        rx, ry = PH - y, x
    elif turn == "left":
        rx, ry = y, PW - x
    else:
        rx, ry = x, y
    return origin_x + rx * scale, origin_y + ry * scale


def arrow_points(angle, length, head_l, head_w, shaft_w):
    rad = math.radians(angle)
    ux, uy = math.cos(rad), math.sin(rad)
    px, py = -uy, ux
    start = 18
    base = length - head_l
    offsets = (
        (start, shaft_w),
        (base, shaft_w),
        (base, head_w),
        (length, 0),
        (base, -head_w),
        (base, -shaft_w),
        (start, -shaft_w),
    )
    return [(70 + ux * along + px * side, 70 + uy * along + py * side) for along, side in offsets]


def omni_mark(size):
    cached = _marks.get(size)
    if cached is not None:
        return cached
    big = size * 2
    surf = pygame.Surface((big, big), pygame.SRCALPHA)
    scale = big / 140
    for arrow in ARROWS:
        points = [(x * scale, y * scale) for x, y in arrow_points(*arrow)]
        pygame.draw.polygon(surf, INK, points)
    center = (70 * scale, 70 * scale)
    pygame.draw.circle(surf, INK, center, 22 * scale)
    hole = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    pygame.draw.circle(hole, (255, 255, 255, 255), center, 11 * scale)
    surf.blit(hole, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)
    mark = pygame.transform.smoothscale(surf, (size, size))
    _marks[size] = mark
    return mark


def draw_mic(surf, center, color):
    x, y = center
    pygame.draw.rect(surf, color, (x - 4, y - 11, 8, 13), border_radius=4)
    pygame.draw.lines(
        surf,
        color,
        False,
        [(x - 8, y - 2), (x - 8, y + 3), (x + 8, y + 3), (x + 8, y - 2)],
        2,
    )
    pygame.draw.line(surf, color, (x, y + 3), (x, y + 8), 2)
    pygame.draw.line(surf, color, (x - 6, y + 8), (x + 6, y + 8), 2)


def blit_mark(dest, size, center, ticks, listening):
    mark = omni_mark(size)
    if listening:
        mark = pygame.transform.rotate(mark, -(ticks % 14000) / 14000 * 360)
    dest.blit(mark, mark.get_rect(center=center))


class Hit:
    def __init__(self, rect, act, index=None, text="", amount=None, app_id=""):
        self.rect = rect
        self.act = act
        self.index = index
        self.text = text
        self.amount = amount
        self.app_id = app_id


class Screen:
    def __init__(self):
        self.launcher = False
        self.selection = 0
        self.hits = []
        self.scroll = 0
        self.content_h = 0
        self._fonts = {}
        ui = pygame.font.SysFont("sans", 18)
        self.ui_name = ui.get_name() if hasattr(ui, "get_name") else None

    def font(self, size, bold=False, word=False):
        key = (size, bold, word)
        found = self._fonts.get(key)
        if found is not None:
            return found
        if word and WORDMARK.exists():
            face = pygame.font.Font(str(WORDMARK), size)
        else:
            face = pygame.font.SysFont(self.ui_name, size, bold=bold)
        self._fonts[key] = face
        return face

    def paint(self, surf, device, ticks, draft):
        for _ in range(2):
            self.hits.clear()
            self.content_h = 0
            surf.fill(BG)
            if device.current() is not None or draft or device.agent != "idle":
                self.header(surf, device, ticks, draft)
            body = pygame.Rect(0, HEADER_H, PW, BODY_H)
            surf.set_clip(body)
            app = device.current()
            if app is None:
                self.home(surf, device, ticks, body)
            else:
                self.app_view(surf, device, app, body)
            surf.set_clip(None)
            self.dock(surf, device)
            if device.proposal:
                self.modal(surf, device.proposal)
            limit = max(0, self.content_h - BODY_H)
            clamped = min(max(self.scroll, 0), limit)
            if clamped == self.scroll:
                break
            self.scroll = clamped

    def add(self, rect, act, clip=None, **kwargs):
        rect = pygame.Rect(rect)
        if clip is not None:
            rect = rect.clip(clip)
        if rect.width <= 0 or rect.height <= 0:
            return
        self.hits.append(Hit(rect, act, **kwargs))

    def at(self, pos):
        if pos is None:
            return None
        for hit in reversed(self.hits):
            if hit.rect.collidepoint(pos):
                return hit
        return None

    def text(self, face, value, width, color):
        value = "" if value is None else str(value)
        if face.size(value)[0] <= width:
            return face.render(value, True, color)
        ellipsis = "…"
        while value and face.size(value + ellipsis)[0] > width:
            value = value[:-1]
        return face.render((value + ellipsis) if value else ellipsis, True, color)

    def tail(self, face, value, width):
        if face.size(value)[0] <= width:
            return value
        while value and face.size("…" + value)[0] > width:
            value = value[1:]
        return "…" + value

    def header(self, surf, device, ticks, draft):
        pygame.draw.line(surf, HAIRLINE, (0, HEADER_H - 1), (PW, HEADER_H - 1))
        listening = device.agent == "listening"
        blit_mark(surf, 32, (18 + 16, HEADER_H / 2), ticks, listening)
        word = self.font(22, word=True).render("omni", True, INK)
        surf.blit(word, word.get_rect(midleft=(18 + 32 + 8, HEADER_H / 2)))
        clock = self.font(14).render(time.strftime("%-I:%M %p"), True, MUTED)
        surf.blit(clock, clock.get_rect(midright=(PW - 18, HEADER_H / 2)))
        x = 18 + 32 + 8 + word.get_width() + 12
        right = PW - 18 - clock.get_width() - 10
        dot = BLUE if device.agent == "listening" else AMBER if device.agent == "thinking" else GREEN if device.agent == "responding" else (109, 116, 132)
        if device.agent in ("listening", "thinking"):
            wave = 0.4 + 0.6 * abs(math.sin(ticks / 1100 * math.pi))
            color = tuple(int(channel * wave) for channel in dot)
        else:
            color = dot
        pygame.draw.circle(surf, color, (int(x + 5), HEADER_H // 2), 5)
        x += 18
        if listening:
            for index in range(4):
                phase = ticks / 900 + index * 0.12
                scale = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(phase * math.tau))
                bar_h = max(3, int(14 * scale))
                pygame.draw.rect(
                    surf,
                    BLUE,
                    (x + index * 6, HEADER_H / 2 - bar_h / 2, 3, bar_h),
                    border_radius=2,
                )
            x += 4 * 6 + 6
        if draft and device.agent == "idle":
            label = self.tail(self.font(15), draft, max(0, right - x))
        else:
            label = agent_label(device.agent, device.say)
        face = self.font(15)
        rendered = self.text(face, label, max(0, right - x), INK)
        surf.blit(rendered, rendered.get_rect(midleft=(x, HEADER_H / 2)))

    def step_selection(self, device, direction):
        self.launcher = True
        if device.registry:
            self.selection = (self.selection + direction) % len(device.registry)

    def home(self, surf, device, ticks, body):
        self.content_h = BODY_H
        if not self.launcher:
            blit_mark(surf, 246, (240, 320), ticks, device.agent == "listening")
            word = self.font(64, word=True).render("omni", True, INK)
            surf.blit(word, word.get_rect(midtop=(240, 454)))
            hint = self.font(17).render("Tap to explore", True, MUTED)
            surf.blit(hint, hint.get_rect(center=(240, 632)))
            self.add(body, "launcher", clip=body)
            return
        # The original simulator's corner arc, scaled to the portrait LCD.
        blit_mark(surf, 94, (410, 112), ticks, False)
        word = self.font(36, word=True).render("omni", True, INK)
        surf.blit(word, word.get_rect(midright=(350, 106)))
        self.add((270, 65, 195, 90), "logo", clip=body)
        if not device.registry:
            title = self.font(30, word=True).render("your apps", True, INK)
            surf.blit(title, title.get_rect(midright=(444, 216)))
            hint = self.font(19).render("Ask Omni to make something.", True, MUTED)
            surf.blit(hint, hint.get_rect(center=(240, 380)))
            self.chips(surf, 390, body)
            return
        self.selection %= len(device.registry)
        app = device.registry[self.selection]
        title = self.text(self.font(32, word=True), app.get("title", "").lower(), 410, INK)
        surf.blit(title, title.get_rect(midright=(444, 211)))
        pygame.draw.rect(surf, INK, (374, 249, 70, 4))
        detail = self.text(self.font(16), blurb(app), 300, MUTED)
        surf.blit(detail, detail.get_rect(midright=(444, 278)))
        cx, cy, radius = -8, 686, 328
        points = [(cx + math.cos(math.radians(a)) * radius,
                   cy + math.sin(math.radians(a)) * radius) for a in range(-86, -3)]
        pygame.draw.lines(surf, INK, False, points, 2)
        slots = [(-2, -80, 28), (-1, -62, 37), (0, -42, 58), (1, -22, 37), (2, -6, 28)]
        # Small registries show each app once, always including the focus.
        seen = set()
        nodes = []
        for offset, angle, r in sorted(slots, key=lambda slot: abs(slot[0])):
            index = (self.selection + offset) % len(device.registry)
            if index in seen:
                continue
            seen.add(index)
            nodes.append((offset, angle, r, index))
        for offset, angle, r, index in reversed(nodes):
            x = round(cx + math.cos(math.radians(angle)) * radius)
            y = round(cy + math.sin(math.radians(angle)) * radius)
            active = offset == 0
            pygame.draw.circle(surf, INK if active else BG, (x, y), r)
            pygame.draw.circle(surf, INK, (x, y), r, 2)
            self.app_icon(surf, device.registry[index], (x, y), r, BG if active else INK)
            target = pygame.Rect(x-r, y-r, r*2, r*2)
            self.add(target, "open" if active else "select", clip=body,
                     index=index, app_id=device.registry[index].get("id"))
        hint = self.font(15).render("Swipe to browse · tap to open", True, MUTED)
        surf.blit(hint, hint.get_rect(midright=(451, 707)))

    def app_icon(self, surf, app, center, radius, color):
        x, y = center
        size = radius * 0.48
        width = max(2, round(radius / 14))
        module = app.get("module")
        if app.get("id") == "notes":
            pygame.draw.rect(surf, color, (x-size, y-size*1.2, size*2, size*2.4), width)
            for row in (-1, 0, 1):
                yy = y + row * size * 0.6
                pygame.draw.line(surf, color, (x-size*0.6, yy), (x+size*0.6, yy), width)
        elif module == "checklist":
            for row in (-1, 0, 1):
                yy = y + row * size * 0.7
                pygame.draw.rect(surf, color, (x-size, yy-width, width*2, width*2))
                pygame.draw.line(surf, color, (x-size*0.45, yy), (x+size, yy), width)
        elif module == "scoreboard":
            for side in (-1, 1):
                rect = pygame.Rect(x + side*size*0.6-size*0.4, y-size, size*0.8, size*2)
                pygame.draw.rect(surf, color, rect, width)
            pygame.draw.line(surf, color, (x, y-size), (x, y+size), width)
        elif module == "progress":
            # Water droplet, matching the simulator's hydration glyph.
            pygame.draw.polygon(surf, color, [(x, y-size*1.2), (x-size*0.7, y), (x+size*0.7, y)])
            pygame.draw.circle(surf, color, (x, y+size*0.25), size*0.75)
        else:
            for i, height in enumerate((0.7, 1.2, 1.8)):
                pygame.draw.rect(surf, color, (x-size+i*size*0.7, y+size-height*size, size*0.45, height*size))

    def cy(self, content_y, body):
        return body.top + content_y - self.scroll

    def chips(self, surf, content_y, body):
        gap = 8
        width = (PW - 36 - gap * 2) / 3
        for index, (label, text) in enumerate(DEMO_LINES):
            rect = pygame.Rect(18 + index * (width + gap), self.cy(content_y, body), width, 48)
            pygame.draw.rect(surf, CARD2, rect, border_radius=14)
            face = self.font(15, bold=True)
            rendered = face.render(label, True, INK)
            surf.blit(rendered, rendered.get_rect(center=rect.center))
            self.add(rect, "line", clip=body, text=text)

    def app_view(self, surf, device, app, body):
        layout = layout_of(device.modules, app.get("module"))
        margin = layout["margin"]
        y = margin
        head = pygame.Rect(margin, self.cy(y, body), PW - margin * 2, layout["header_h"])
        back = pygame.Rect(head.x, head.centery - 20, 40, 40)
        pygame.draw.rect(surf, CARD, back, border_radius=12)
        pygame.draw.lines(
            surf,
            INK,
            False,
            [(back.centerx + 4, back.centery - 7), (back.centerx - 4, back.centery), (back.centerx + 4, back.centery + 7)],
            2,
        )
        self.add(back, "back", clip=body)
        module = self.font(13).render(str(app.get("module") or "").upper(), True, MUTED)
        surf.blit(module, module.get_rect(midright=(head.right, head.centery)))
        title_w = max(0, head.width - 40 - 12 - module.get_width() - 12)
        title = self.text(self.font(26, bold=True), app.get("title"), title_w, INK)
        surf.blit(title, title.get_rect(midleft=(back.right + 8, head.centery)))
        y += layout["header_h"] + 12
        module_name = app.get("module")
        if module_name == "checklist":
            y = self.checklist(surf, app, layout, y, body)
        elif module_name == "scoreboard":
            y = self.scoreboard(surf, app, layout, y, body)
        elif module_name == "progress":
            y = self.progress(surf, app, layout, y, body)
        else:
            y = self.key_value(surf, app, layout, y, body)
        self.content_h = y + 8

    def checklist(self, surf, app, layout, y, body):
        items = (app.get("state") or {}).get("items") or []
        cursor = (app.get("state") or {}).get("cursor") or 0
        if not items:
            empty = self.font(18).render("Nothing on the list.", True, MUTED)
            surf.blit(empty, empty.get_rect(midtop=(PW / 2, self.cy(y + 28, body))))
            return y + 80
        for index, item in enumerate(items):
            rect = pygame.Rect(layout["margin"], self.cy(y, body), PW - layout["margin"] * 2, layout["row_h"])
            if index == cursor:
                pygame.draw.rect(surf, CURSOR, rect, border_radius=14)
            box = pygame.Rect(rect.x + 14, rect.centery - 11, 22, 22)
            checked = bool(item.get("checked"))
            if checked:
                pygame.draw.circle(surf, ACCENT, box.center, 11)
                pygame.draw.lines(
                    surf,
                    ACCENT_INK,
                    False,
                    [(box.centerx - 6, box.centery), (box.centerx - 2, box.centery + 4), (box.centerx + 6, box.centery - 5)],
                    2,
                )
            else:
                pygame.draw.circle(surf, CHECK, box.center, 11, width=2)
            label = self.text(
                self.font(18),
                item.get("label"),
                rect.width - 64,
                MUTED if checked else INK,
            )
            dest = label.get_rect(midleft=(box.right + 12, rect.centery))
            surf.blit(label, dest)
            if checked:
                pygame.draw.line(surf, MUTED, (dest.left, dest.centery), (dest.right, dest.centery), 1)
            self.add(rect, "toggle", clip=body, index=index)
            y += layout["row_h"] + 8
        return y

    def scoreboard(self, surf, app, layout, y, body):
        sides = (app.get("state") or {}).get("sides") or []
        cursor = (app.get("state") or {}).get("cursor") or 0
        gap = 12
        width = (PW - layout["margin"] * 2 - gap) / 2
        height = 220
        for index, side in enumerate(sides[:2]):
            rect = pygame.Rect(layout["margin"] + index * (width + gap), self.cy(y, body), width, height)
            pygame.draw.rect(surf, CARD, rect, border_radius=16)
            border = ACCENT if index == cursor else TILE_LINE
            pygame.draw.rect(surf, border, rect, width=2 if index == cursor else 1, border_radius=16)
            name = self.text(self.font(16), side.get("name"), rect.width - 24, MUTED)
            surf.blit(name, name.get_rect(topleft=(rect.x + 16, rect.y + 16)))
            score = self.font(64, bold=True).render(str(side.get("score")), True, INK)
            surf.blit(score, score.get_rect(topleft=(rect.x + 16, rect.y + 44)))
            button_w = (rect.width - 16 * 2 - 8) / 2
            for offset, act, glyph in ((0, "dec", "−"), (1, "inc", "+")):
                button = pygame.Rect(rect.x + 16 + offset * (button_w + 8), rect.bottom - 16 - 48, button_w, 48)
                pygame.draw.rect(surf, CARD2, button, border_radius=12)
                mark = self.font(24, bold=True).render(glyph, True, INK)
                surf.blit(mark, mark.get_rect(center=button.center))
                self.add(button, act, clip=body, index=index)
        return y + height

    def progress(self, surf, app, layout, y, body):
        data = app.get("state") or {}
        goal = num(data.get("goal"), 1) or 1
        value = num(data.get("value"))
        unit = data.get("unit") or ""
        step = num(data.get("step"), 1) or 1
        label = self.font(16).render(str(data.get("label") or ""), True, MUTED)
        surf.blit(label, (layout["margin"], self.cy(y, body)))
        y += label.get_height() + 2
        metric = self.font(64, bold=True).render(str(value), True, INK)
        surf.blit(metric, (layout["margin"], self.cy(y, body)))
        y += metric.get_height() + 2
        goal_line = self.font(16).render("of %s %s" % (data.get("goal"), unit), True, MUTED)
        surf.blit(goal_line, (layout["margin"], self.cy(y, body)))
        y += goal_line.get_height() + 12
        bar = pygame.Rect(layout["margin"], self.cy(y, body), PW - layout["margin"] * 2, layout["bar_h"])
        pygame.draw.rect(surf, BAR, bar, border_radius=99)
        filled = bar.copy()
        filled.width = int(bar.width * max(0, min(1, value / goal)))
        if filled.width:
            pygame.draw.rect(surf, GREEN, filled, border_radius=99)
        y += layout["bar_h"] + 14
        gap = 10
        width = (PW - layout["margin"] * 2 - gap) / 2
        for index, amount in enumerate((step, step * 2)):
            button = pygame.Rect(layout["margin"] + index * (width + gap), self.cy(y, body), width, 52)
            pygame.draw.rect(surf, CARD, button, border_radius=14)
            caption = self.font(18, bold=True).render("+%s %s" % (amount, unit), True, INK)
            surf.blit(caption, caption.get_rect(center=button.center))
            self.add(button, "add", clip=body, amount=amount)
        return y + 52

    def key_value(self, surf, app, layout, y, body):
        rows = (app.get("state") or {}).get("rows") or []
        cursor = (app.get("state") or {}).get("cursor") or 0
        for index, row in enumerate(rows):
            rect = pygame.Rect(layout["margin"], self.cy(y, body), PW - layout["margin"] * 2, layout["row_h"])
            if index == cursor:
                pygame.draw.rect(surf, CURSOR, rect, border_radius=14)
            label = self.text(self.font(18), row.get("label"), rect.width / 2, MUTED)
            value = self.text(self.font(18, bold=True), row.get("value"), rect.width / 2 - 28, INK)
            surf.blit(label, label.get_rect(midleft=(rect.x + 14, rect.centery)))
            surf.blit(value, value.get_rect(midright=(rect.right - 14, rect.centery)))
            self.add(rect, "focus", clip=body, index=index)
            y += layout["row_h"] + 8
        return y

    def dock(self, surf, device):
        hot = device.agent == "listening"
        pygame.draw.rect(surf, INK if hot else BG, PTT, border_radius=26)
        pygame.draw.rect(surf, INK if hot else MUTED, PTT, width=1, border_radius=26)
        color = BG if hot else INK
        label = self.font(16, bold=True).render("Release to send" if hot else "Hold to talk", True, color)
        icon_w = 18
        total = icon_w + 8 + label.get_width()
        left = PTT.centerx - total / 2
        draw_mic(surf, (left + icon_w / 2, PTT.centery + 1), color)
        surf.blit(label, label.get_rect(midleft=(left + icon_w + 8, PTT.centery)))
        self.add(PTT, "talk")

    def modal(self, surf, proposal):
        dim = pygame.Surface((PW, PH), pygame.SRCALPHA)
        dim.fill((8, 9, 12, 184))
        surf.blit(dim, (0, 0))
        self.add(pygame.Rect(0, 0, PW, PH), "blank")
        text = proposal.get("say") or "Create this app?"
        face = self.font(22)
        words = str(text).split()
        lines = []
        current = ""
        limit = 400 - 44
        for word in words:
            trial = word if not current else current + " " + word
            if face.size(trial)[0] <= limit:
                current = trial
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        height = 22 + len(lines) * (face.get_height() + 4) + 18 + 48 + 22
        dialog = pygame.Rect(40, (PH - height) / 2, 400, height)
        pygame.draw.rect(surf, PTT_BG, dialog, border_radius=20)
        pygame.draw.rect(surf, (70, 80, 106), dialog, width=1, border_radius=20)
        y = dialog.y + 22
        for line in lines:
            rendered = face.render(line, True, INK)
            surf.blit(rendered, (dialog.x + 22, y))
            y += face.get_height() + 4
        y += 14
        gap = 10
        width = (dialog.width - 44 - gap) / 2
        yes = pygame.Rect(dialog.x + 22, y, width, 48)
        no = pygame.Rect(yes.right + gap, y, width, 48)
        pygame.draw.rect(surf, ACCENT, yes, border_radius=12)
        pygame.draw.rect(surf, GHOST, no, border_radius=12)
        yes_label = self.font(16, bold=True).render("Yes, create it", True, ACCENT_INK)
        no_label = self.font(16, bold=True).render("Cancel", True, INK)
        surf.blit(yes_label, yes_label.get_rect(center=yes.center))
        surf.blit(no_label, no_label.get_rect(center=no.center))
        self.add(yes, "confirm")
        self.add(no, "cancel")


def post_json(url, payload):
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=8) as response:
        return json.loads(response.read().decode())


def boost_wav(wav_bytes: bytes, gain: float = 2.5) -> bytes:
    try:
        with io.BytesIO(wav_bytes) as in_io, wave.open(in_io, "rb") as wf:
            params = wf.getparams()
            frames = wf.readframes(wf.getnframes())
            sampwidth = wf.getsampwidth()
        if sampwidth == 2:
            count = len(frames) // 2
            samples = struct.unpack(f"<{count}h", frames)
            boosted = [max(-32768, min(32767, int(s * gain))) for s in samples]
            out_frames = struct.pack(f"<{count}h", *boosted)
        elif sampwidth == 4:
            count = len(frames) // 4
            samples = struct.unpack(f"<{count}i", frames)
            max_i = 2147483647
            min_i = -2147483648
            boosted = [max(min_i, min(max_i, int(s * gain))) for s in samples]
            out_frames = struct.pack(f"<{count}i", *boosted)
        else:
            return wav_bytes

        out_io = io.BytesIO()
        with wave.open(out_io, "wb") as out_wf:
            out_wf.setparams(params)
            out_wf.writeframes(out_frames)
        return out_io.getvalue()
    except Exception:
        return wav_bytes


class AudioRecorder:
    """Non-blocking background audio recorder for push-to-talk using arecord."""

    def __init__(self, tmp_path=Path("/tmp/omni_talk.wav")):
        self.proc = None
        self.tmp_path = Path(tmp_path)
        self.start_time = 0.0

    def find_device(self) -> str:
        if not shutil.which("arecord"):
            return "default"
        try:
            res = subprocess.run(["arecord", "-l"], capture_output=True, text=True, timeout=2)
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    if "card" in line and "device" in line:
                        if any(k in line.lower() for k in ("voicehat", "googlevoice", "i2s", "soundcard")):
                            parts = line.split(":")
                            card = int(parts[0].replace("card", "").strip())
                            dev = int(parts[1].split(",")[1].replace("device", "").strip())
                            return f"plughw:{card},{dev}"
        except Exception:
            pass
        return "default"

    def start(self):
        if not shutil.which("arecord"):
            return
        device = self.find_device()
        self.start_time = time.monotonic()
        try:
            self.tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        cmd = [
            "arecord",
            "-D", device,
            "-c", "2",
            "-r", "48000",
            "-f", "S32_LE",
            "-t", "wav",
            str(self.tmp_path),
        ]
        try:
            self.proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            self.proc = None

    def stop(self, gain: float = 2.5) -> str | None:
        if self.proc is None:
            return None
        proc = self.proc
        self.proc = None
        duration = time.monotonic() - self.start_time
        try:
            proc.terminate()
            proc.wait(timeout=1.0)
        except Exception:
            pass

        if duration < 0.25:
            return None

        if not self.tmp_path.exists():
            return None

        try:
            raw_bytes = self.tmp_path.read_bytes()
            if len(raw_bytes) < 200:
                return None
            boosted = boost_wav(raw_bytes, gain=gain)
            return base64.b64encode(boosted).decode("ascii")
        except Exception:
            return None


def hold_lock(pid_path=PID_PATH):
    global _lock
    pid_path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(pid_path, "a+")
    if fcntl is not None:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            handle.seek(0)
            existing = handle.read().strip() or "unknown"
            print("Omni is already running (pid %s)." % existing)
            print("Quit it with: python3 firmware/phone.py --stop")
            sys.exit(0)
    handle.seek(0)
    handle.truncate()
    handle.write(str(os.getpid()))
    handle.flush()
    _lock = handle


def stop_running(pid_path=PID_PATH):
    if not pid_path.exists():
        print("Omni is not running.")
        return
    text = pid_path.read_text().strip()
    if not text.isdigit():
        print("Omni is not running.")
        return
    try:
        os.kill(int(text), signal.SIGTERM)
    except OSError as exc:
        print("Could not stop pid %s: %s" % (text, exc))
        return
    print("Stopped Omni.")


def require_pygame():
    if pygame is not None:
        return
    sys.stderr.write(
        "pygame is missing.\n"
        "On the Pi: sudo apt install python3-pygame\n"
        "On a Mac: python3 -m venv .venv && .venv/bin/pip install pygame-ce\n"
    )
    sys.exit(1)


class App:
    def __init__(self, stub, turn, kiosk, store=STORE):
        self.device = Device()
        self.device.load_modules()
        if not self.device.restore(store):
            self.device.load_demos()
            self.device.save(store)
        # Restore saved apps, but always enter through the new logo screen.
        self.device.go_home()
        self.screen = Screen()
        self.recorder = AudioRecorder()
        self.stub = stub
        self.turn = turn if kiosk else "none"
        self.kiosk = kiosk
        self.store = store
        self.draft = ""
        self.events = queue.Queue()
        self.press = None
        self.stopping = False
        self.phone = pygame.Surface((PW, PH))

    def send(self, text="", wav_base64=None):
        text = (text or "").strip()
        self.draft = ""
        if self.device.agent == "thinking":
            return
        if not text and not wav_base64:
            self.device.agent = "responding"
            self.device.say = "Type a request, or hold the bar to speak."
            self.device.arm_idle(time.monotonic())
            return
        self.device.agent = "thinking"
        self.device.proposal = None
        self.device.say = ""
        self.device.respond_until = None
        payload = {
            "text": text,
            "registry": copy.deepcopy(self.device.registry),
            "focused_app_id": self.device.app_id,
        }
        if wav_base64:
            payload["wav_base64"] = wav_base64
        threading.Thread(target=self.fetch, args=(payload,), daemon=True).start()

    def fetch(self, payload):
        try:
            turn = post_json(self.stub, payload)
        except (OSError, urllib.error.URLError, json.JSONDecodeError, ValueError):
            self.events.put(("error", None))
            return
        self.events.put(("turn", turn))

    def poll(self):
        try:
            kind, payload = self.events.get_nowait()
        except queue.Empty:
            return
        if kind == "turn":
            self.device.apply_turn(payload, time.monotonic())
            self.device.save(self.store)
        else:
            self.device.agent = "responding"
            self.device.say = "The turn stub is not running."
            self.device.arm_idle(time.monotonic())
        self.screen.scroll = 0

    def activate(self, hit):
        if hit is None or hit.act in ("talk", "blank"):
            return
        if hit.act == "line":
            self.send(hit.text)
            return
        if hit.act == "launcher":
            self.screen.launcher = True
            return
        if hit.act == "logo":
            self.screen.launcher = False
            return
        if hit.act == "select":
            self.screen.selection = hit.index
            return
        if hit.act in ("back", "open"):
            self.screen.launcher = True
        before = (self.device.screen, self.device.app_id)
        self.device.local(hit.act, index=hit.index, amount=hit.amount, app_id=hit.app_id)
        self.device.save(self.store)
        if (self.device.screen, self.device.app_id) != before:
            self.screen.scroll = 0

    def on_down(self, pos):
        if self.device.agent == "thinking" or pos is None:
            return
        hit = self.screen.at(pos)
        if hit is not None and hit.act == "talk":
            self.device.agent = "listening"
            self.recorder.start()
            self.press = {"talk": True, "x": pos[0], "y": pos[1], "scroll": self.screen.scroll, "moved": False}
            return
        self.press = {
            "talk": False,
            "x": pos[0],
            "y": pos[1],
            "scroll": self.screen.scroll,
            "moved": False,
            "hit": hit,
        }

    def on_move(self, pos):
        press = self.press
        if press is None or press["talk"] or pos is None or self.device.proposal:
            return
        if abs(pos[1] - press["y"]) < 12:
            return
        press["moved"] = True
        if self.device.current() is not None:
            self.screen.scroll = press["scroll"] - (pos[1] - press["y"])

    def on_up(self, pos):
        press = self.press
        self.press = None
        if press is None:
            return
        if press["talk"]:
            wav_b64 = self.recorder.stop()
            if self.device.agent == "listening":
                fallback_text = self.draft or (TALK_LINE if not wav_b64 else "")
                self.send(text=fallback_text, wav_base64=wav_b64)
            return
        if press["moved"]:
            if self.device.current() is None and not self.device.proposal and pos is not None:
                self.screen.step_selection(self.device, 1 if pos[1] < press["y"] else -1)
            return
        hit = self.screen.at(pos) if pos is not None else press.get("hit")
        self.activate(hit)

    def on_key(self, event):
        mods = event.mod
        ctrl = bool(mods & (pygame.KMOD_CTRL | pygame.KMOD_META))
        if ctrl and event.key == pygame.K_q and (mods & pygame.KMOD_SHIFT):
            return "quit"
        if ctrl and event.key == pygame.K_e:
            self.device.empty()
            self.device.save(self.store)
            self.screen.scroll = 0
            self.draft = ""
            return None
        if ctrl and event.key == pygame.K_d:
            self.device.load_demos()
            self.device.save(self.store)
            self.screen.scroll = 0
            self.draft = ""
            return None
        if event.key == pygame.K_ESCAPE:
            if self.device.proposal:
                self.device.cancel()
                self.device.save(self.store)
            elif self.device.screen == "app":
                self.device.go_home()
                self.screen.launcher = True
                self.device.save(self.store)
                self.screen.scroll = 0
            elif self.screen.launcher:
                self.screen.launcher = False
            elif not self.kiosk:
                return "quit"
            return None
        if ctrl:
            return None
        if not self.device.proposal and self.device.current() is None and not self.draft:
            if event.key in (pygame.K_UP, pygame.K_DOWN):
                self.screen.step_selection(self.device, -1 if event.key == pygame.K_UP else 1)
                return None
            if event.key == pygame.K_RETURN:
                if not self.screen.launcher:
                    self.screen.launcher = True
                elif self.device.registry:
                    index = self.screen.selection % len(self.device.registry)
                    self.activate(Hit((0, 0, 1, 1), "open", app_id=self.device.registry[index]["id"]))
                return None
        if event.key == pygame.K_BACKSPACE:
            self.draft = self.draft[:-1]
        elif event.key == pygame.K_RETURN and not ctrl:
            self.send(self.draft)
        return None

    def on_text(self, text):
        if self.device.agent == "thinking" or not text or text.isspace():
            return
        self.draft += text

    def frame(self, display):
        self.device.tick(time.monotonic())
        self.poll()
        self.screen.paint(self.phone, self.device, pygame.time.get_ticks(), self.draft)
        if self.turn == "none":
            frame = self.phone
        else:
            frame = pygame.transform.rotate(self.phone, -90 if self.turn == "right" else 90)
        window = display.get_size()
        scale, origin_x, origin_y = placed(window, self.turn)
        if abs(scale - 1) < 0.01 and frame.get_size() == window:
            display.blit(frame, (0, 0))
        else:
            sized = (max(1, int(frame.get_width() * scale)), max(1, int(frame.get_height() * scale)))
            scaled = pygame.transform.smoothscale(frame, sized)
            display.fill((0, 0, 0))
            display.blit(scaled, (int(origin_x), int(origin_y)))

    def run(self):
        flags = 0
        size = (PW, PH)
        if self.kiosk:
            flags = pygame.FULLSCREEN
            size = (0, 0)
        display = pygame.display.set_mode(size, flags)
        pygame.display.set_caption("Omni")
        pygame.mouse.set_visible(not self.kiosk)
        icon = omni_mark(64)
        pygame.display.set_icon(icon)
        clock = pygame.time.Clock()
        active_finger = None
        while True:
            if self.stopping:
                return 0
            suppress = False
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return 0 if self.stopping or not self.kiosk else 2
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not getattr(event, "touch", False):
                    self.on_down(phone_point(*event.pos, display.get_size(), self.turn))
                elif event.type == pygame.MOUSEMOTION and self.press is not None and not getattr(event, "touch", False):
                    self.on_move(phone_point(*event.pos, display.get_size(), self.turn))
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and not getattr(event, "touch", False):
                    self.on_up(phone_point(*event.pos, display.get_size(), self.turn))
                elif event.type == pygame.MOUSEWHEEL and not self.device.proposal:
                    if hasattr(self, "scroll_input"):
                        self.scroll_input(-event.y)
                    elif self.device.current() is None:
                        self.screen.step_selection(self.device, -event.y)
                    else:
                        self.screen.scroll -= event.y * 48
                elif event.type == pygame.FINGERDOWN and active_finger is None:
                    active_finger = event.finger_id
                    self.on_down(phone_point(event.x*display.get_width(), event.y*display.get_height(), display.get_size(), self.turn))
                elif event.type == pygame.FINGERMOTION and event.finger_id == active_finger:
                    self.on_move(phone_point(event.x*display.get_width(), event.y*display.get_height(), display.get_size(), self.turn))
                elif event.type == pygame.FINGERUP and event.finger_id == active_finger:
                    active_finger = None
                    self.on_up(phone_point(event.x*display.get_width(), event.y*display.get_height(), display.get_size(), self.turn))
                elif event.type == pygame.WINDOWFOCUSLOST and hasattr(self, "cancel_press"):
                    active_finger = None
                    self.cancel_press()
                elif event.type == pygame.KEYDOWN:
                    mods = event.mod
                    if mods & (pygame.KMOD_CTRL | pygame.KMOD_META):
                        suppress = True
                    if self.on_key(event) == "quit":
                        return 0
                elif event.type == pygame.TEXTINPUT and not suppress:
                    self.on_text(event.text)
            self.frame(display)
            pygame.display.flip()
            clock.tick(60)


def pi_model():
    path = Path("/proc/device-tree/model")
    if not path.exists():
        return ""
    return path.read_bytes().decode("utf-8", "replace").strip("\x00").strip()


def main():
    parser = argparse.ArgumentParser(description="Open the Omni phone.")
    parser.add_argument("--kiosk", action="store_true", help="Fullscreen on the panel.")
    parser.add_argument("--turn", choices=("right", "left"), default="right")
    parser.add_argument("--stub", default="http://127.0.0.1:8787/v1/turn")
    parser.add_argument("--sim", action="store_true", help="Use an isolated simulator profile; same UI/input as the Pi.")
    parser.add_argument("--live", action="store_true", help="Send requests to --stub instead of local demo generation.")
    parser.add_argument("--store", type=Path, help="Override the registry path (preferences live alongside it).")
    parser.add_argument("--stop", action="store_true", help="Quit a running phone.")
    args = parser.parse_args()

    store = args.store or (Path.home()/".omni"/"simulator"/"registry.json" if args.sim else Path.home()/".omni"/"pi-ui"/"registry.json")
    pid_path = store.with_name("shell.pid") if args.sim else PID_PATH
    if args.stop:
        stop_running(pid_path)
        return

    require_pygame()
    hold_lock(pid_path)
    model = pi_model()
    if model:
        print(model)
    if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY") and sys.platform.startswith("linux"):
        print("No desktop session. Log in on the panel, then from SSH:")
        print("  export XDG_RUNTIME_DIR=/run/user/$(id -u)")
        print("  export WAYLAND_DISPLAY=wayland-0")

    pygame.init()
    pygame.font.init()
    from native_ui import NativeApp
    app = NativeApp(args.stub, args.turn, args.kiosk, store=store, live=args.live)
    print("Omni UI: shared pygame simulator/Pi. File: %s" % Path(__file__).resolve())
    print("Omni phone. Registry at %s" % app.store)
    if args.kiosk:
        print("Stays up until Ctrl+Shift+Q, or: python3 firmware/phone.py --stop")
    else:
        print("Tap the logo, rotate the wheel, and tap an app. Hold the waveform to simulate speech.")
        print("Type a request and Enter, or use the on-screen keyboard. Escape goes back; Ctrl+Shift+Q quits.")

    def handle_stop(signum, frame):
        app.stopping = True

    signal.signal(signal.SIGTERM, handle_stop)
    signal.signal(signal.SIGINT, handle_stop)
    code = app.run()
    pygame.quit()
    sys.exit(code)


if __name__ == "__main__":
    main()
