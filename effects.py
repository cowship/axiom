# effects.py — 시각 효과 (하이퍼스페이스, 잔상) 모듈
from __future__ import annotations

import math, random, tkinter as tk

class HyperspaceFX:
    """S / S' 전환 이펙트: start() → step(dt) → render()"""

    def __init__(self, canvas: tk.Canvas, canvas2: tk.Canvas = None):
        self.canvas = canvas
        self.canvas2 = canvas2 or canvas   # ★ 위쪽 캔버스도 같이 받기
        self.active = False
        self.t = 0.0
        self.duration = 1.0
        self._streaks = []

    def start(self, duration: float = 1.0):
        self.active = True
        self.t = 0.0
        self.duration = max(1e-3, float(duration))
        self._streaks = []
        for _ in range(180):
            ang = random.uniform(0, 2*math.pi)
            spd = random.uniform(120, 320)
            l0  = random.uniform(4, 24)
            self._streaks.append((ang, spd, l0))

    def step(self, dt: float):
        if not self.active:
            return
        self.t += max(0.0, float(dt))
        if self.t >= self.duration:
            self.active = False

    def render(self):
        if not self.active:
            return

        # ★ 두 캔버스 모두에 동일하게 그리기
        for c in (self.canvas, self.canvas2):
            w = c.winfo_width() or 800
            h = c.winfo_height() or 320
            cx, cy = w // 2, h // 2

            prog = min(1.0, self.t / self.duration)
            ease = (1 - math.cos(math.pi * prog)) * 0.5

            # streaks
            for ang, spd, l0 in self._streaks:
                L  = l0 + spd * ease
                x2 = cx + math.cos(ang) * L
                y2 = cy + math.sin(ang) * L
                c.create_line(cx, cy, x2, y2, width=2, fill="#bcd7ff")

            # flash
            a = int(140 + 100 * ease)
            col = f"#{a:02x}{a:02x}{a:02x}"
            r = int(10 + 120 * ease)
            c.create_oval(cx - r, cy - r, cx + r, cy + r, outline="", fill=col)



class FlameFX:
    """위 S에서 전환 시점에 남기는 '잔상' (간단히 선체 외곽만 흐리게)."""
    def __init__(self):
        self.active = False
        self.ghost = None  # (x_center, length_meter)
        self.power = 0.0

    def arm(self, x_center: float, length_m: float):
        self.active = True
        self.ghost = (x_center, length_m)
        self.power = 0.0

    def step(self, dt: float):
        if not self.active: return
        self.power = min(1.0, self.power + 2.0*dt)

    def stop(self):
        self.active = False
        self.ghost = None
        self.power = 0.0


# ---------- 메인 앱 ----------
