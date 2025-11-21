# debris.py — asteroid-like debris polys
from __future__ import annotations
import math, random
from typing import List, Tuple

class Debris:
    def __init__(self, x: float):
        self.x = x
        self.r = random.randint(2, 5)
        self.yoff = random.randint(-26, -6)
        self.theta = random.uniform(0, math.tau)
        self.wiggle_w = random.uniform(0.3, 1.0)
        self.wiggle_a = random.uniform(0.6, 1.6)

        n = random.randint(5, 7)
        self.shape_pts: List[Tuple[float, float]] = []
        for i in range(n):
            ang = (i / n) * math.tau + random.uniform(-0.12, 0.12)
            rad = self.r * random.uniform(0.7, 1.15)
            self.shape_pts.append((rad * math.cos(ang), rad * math.sin(ang)))
