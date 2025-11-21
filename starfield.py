# starfield.py — simple star background
from __future__ import annotations
import random
from theme import BG_CANVAS

class Starfield:
    def __init__(self, canvas, density: int = 120):
        self.canvas = canvas
        self.stars = []
        self.alive = True
        self._spawn(density)

    def _spawn(self, n):
        w = self.canvas.winfo_width() or 800
        h = self.canvas.winfo_height() or 600
        for _ in range(n):
            x = random.uniform(0, w)
            y = random.uniform(0, h)
            r = random.choice([1,1,1,2])
            sp = random.uniform(0.2, 1.2)
            self.stars.append([x,y,r,sp])

    def step(self):
        if not self.alive: return
        w = self.canvas.winfo_width() or 800
        h = self.canvas.winfo_height() or 600
        for s in self.stars:
            s[0] -= s[3]
            if s[0] < -4:
                s[0] = w + random.uniform(0, 30)
                s[1] = random.uniform(0, h)

    def draw(self):
        c = self.canvas
        for s in self.stars:
            x,y,r,_ = s
            c.create_oval(x-r, y-r, x+r, y+r, fill="#9fb7ff", outline="")
