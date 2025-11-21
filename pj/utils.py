# utils.py — LinearMap & helpers
from __future__ import annotations

class LinearMap:
    def __init__(self, x_min: float, x_max: float, px_min: float, px_max: float):
        self.x_min, self.x_max = x_min, x_max
        self.px_min, self.px_max = px_min, px_max
    def to_px(self, x: float) -> float:
        if self.x_max == self.x_min:
            return (self.px_min + self.px_max) * 0.5
        r = (x - self.x_min) / (self.x_max - self.x_min)
        return self.px_min + r * (self.px_max - self.px_min)

def si_str(n: float) -> str:
    a = abs(n)
    if a >= 1e9: return f"{n/1e9:.1f} G"
    if a >= 1e6: return f"{n/1e6:.1f} M"
    if a >= 1e3: return f"{n/1e3:.1f} k"
    if a >= 1:   return f"{n:.0f}"
    return f"{n:.2g}"
