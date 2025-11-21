# viewpane.py — canvas primitives & badges
from __future__ import annotations
import tkinter as tk
from typing import List, Tuple, Optional
from utils import LinearMap
from theme import FG_ACCENT, FG_TEXT, FG_SUB, ACCENT_HI

class ViewPane:
    def __init__(self, canvas: tk.Canvas, title: str):
        self.canvas = canvas; self.title = title
        self._x_range: Tuple[float,float] | None = None  # ★ 추가

    def set_xrange(self, x_min: float, x_max: float):
        """이번 프레임(한번의 render)에 사용할 x 가시범위. 사용 후 자동 해제하지 않음(다음 프레임에서 덮어씀)."""
        # x_min==x_max 방지용 살짝 여유
        if abs(x_max - x_min) < 1e-9:
            eps = 1.0
            x_min -= eps; x_max += eps
        self._x_range = (x_min, x_max)

    def clear_xrange(self):
        self._x_range = None

    def _mapper(self) -> LinearMap:
        w = self.canvas.winfo_width() or 400
        if self._x_range is not None:
            x_min, x_max = self._x_range
        else:
            x_min, x_max = -400.0, 400.0
        return LinearMap(x_min, x_max, 20, w - 20)


    def clear(self):
        self.canvas.delete("all")

    def draw_axes(self):
        c = self.canvas
        w = c.winfo_width() or 400
        h = c.winfo_height() or 300
        cx, cy = w // 2, h // 2
        c.create_line(0, cy, w, cy, fill="#1f2a40")
        c.create_line(cx, 0, cx, h, fill="#1f2a40")
        for x in range(cx % 50, w, 50):
            c.create_line(x, cy - 4, x, cy + 4, fill="#1f2a40")
        for y in range(cy % 50, h, 50):
            c.create_line(cx - 4, y, cx + 4, y, fill="#1f2a40")
        c.create_text(12, 14, text=self.title, fill=FG_ACCENT, font=("Segoe UI", 11, "bold"), anchor="w")

    def _mapper(self) -> LinearMap:
        w = self.canvas.winfo_width() or 400
        return LinearMap(-400.0, 400.0, 20, w - 20)

    def draw_rod(self, xl: float, xr: float, y: float, *, color=ACCENT_HI, h_px=8, nose=True, width=2):
        m = self._mapper()
        x1 = m.to_px(xl); x2 = m.to_px(xr); y1 = y - h_px; y2 = y + h_px
        self.canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=width)
        if nose:
            self.canvas.create_polygon(x2, y1, x2 + 12, y, x2, y2, outline=color, fill="", width=width)

    def draw_planet(self, x: float, y: float, r_px=18, fill="#1e40af", label: Optional[str] = None):
        m = self._mapper(); px = m.to_px(x)
        self.canvas.create_oval(px - r_px, y - r_px, px + r_px, y + r_px, fill=fill, outline="")
        if label:
            self.canvas.create_text(px, y + r_px + 14, text=label, fill=FG_TEXT, font=("Segoe UI", 10))
    def draw_planet_realistic(self, x: float, y: float, r_px=26, label: Optional[str]=None, hue="#1e40af"):
        m = self._mapper()
        px = m.to_px(x)
        c = self.canvas
        for i in range(6, 0, -1):
            rr = r_px + i*3
            c.create_oval(px-rr, y-rr, px+rr, y+rr, outline="", fill=hue)
        for i in range(r_px, 5, -2):
            col = "#1e3a8a" if i%4 else "#0ea5e9"
            c.create_oval(px-i, y-i, px+i, y+i, outline="", fill=col)
        if label:
            c.create_text(px, y + r_px + 16, text=label, fill=FG_TEXT, font=("Segoe UI", 10))


    def draw_debris_poly(self, x: float, y_px: float, pts: List[Tuple[float,float]],
                         theta: float, fill="#9fb2c9", outline="#e2e8f0", width=1):
        import math
        m = self._mapper(); px = m.to_px(x); cs, sn = math.cos(theta), math.sin(theta)
        pts_abs = []
        for dx, dy in pts:
            rx = dx * cs - dy * sn; ry = dx * sn + dy * cs
            pts_abs.extend([px + rx, y_px + ry])
        self.canvas.create_polygon(pts_abs, fill=fill, outline=outline, width=width)

    def badge(self, xy: Tuple[int,int], lines: List[Tuple[str,str,str]]):
        x0, y0 = xy; c = self.canvas
        pad = 8; line_h = 16; w = 0
        for lb, val, _ in lines:
            t = f"{lb} {val}"
            w = max(w, 8 * max(len(t), 10))
        h = pad*2 + line_h*len(lines)
        c.create_rectangle(x0, y0, x0+w, y0+h, fill="#0e1a33", outline="#213252")
        y = y0 + pad + 2
        for lb, val, col in lines:
            c.create_text(x0+10, y, text=lb, fill=FG_SUB, font=("Segoe UI", 9), anchor="w")
            c.create_text(x0+w-10, y, text=val, fill=col, font=("Consolas", 10, "bold"), anchor="e")
            y += line_h
    def note(self, text: str, x_px: int, y_px: int,
             fill: str = "#cbd5e1", font: Tuple[str, int, str] = ("Consolas", 11, "bold")):
        """
        캔버스 임의 위치에 짧은 텍스트 메모를 남김.
        :param text: 표시할 문자열
        :param x_px: 캔버스 x좌표
        :param y_px: 캔버스 y좌표
        :param fill: 텍스트 색
        :param font: (폰트명, 크기, 스타일)
        """
        self.canvas.create_text(x_px, y_px, text=text, fill=fill, font=font, anchor="w")
