# debris.py — asteroid-like debris polys
from __future__ import annotations
import math, random
from typing import List, Tuple

_PALETTES = [
    ("#a5b4fc", "#e0e7ff"),
    ("#93c5fd", "#dbeafe"),
    ("#6ee7b7", "#bbf7d0"),
    ("#fcd34d", "#fef3c7"),
    ("#fca5a5", "#fee2e2"),
    ("#c4b5fd", "#ede9fe"),
]

class Debris:
    def __init__(self, x: float, y_base_px: int, color_pair: Tuple[str,str]):
        self.x = x
        self.y_base_px = y_base_px
        self.fill, self.outline = color_pair
        self.r = random.randint(2, 5)
        self.theta = random.uniform(0, math.tau)
        n = random.randint(5, 7)
        self.shape_pts = []
        for i in range(n):
            ang = (i / n) * math.tau + random.uniform(-0.12, 0.12)
            rad = self.r * random.uniform(0.7, 1.15)
            self.shape_pts.append((rad * math.cos(ang), rad * math.sin(ang)))
        self.wiggle_w = random.uniform(0.3, 1.0)
        self.wiggle_a = random.uniform(0.6, 1.6)
