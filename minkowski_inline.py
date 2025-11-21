# minkowski_inline.py — inline Minkowski renderer
from __future__ import annotations
import sr_sim as sim
from typing import Tuple, List
from utils import si_str
from theme import FG_ACCENT, FG_TEXT
import tkinter as tk

class MinkowskiMapper:
    def __init__(self, canvas: tk.Canvas, x_min, x_max, ct_min, ct_max):
        self.canvas = canvas
        self.dom_x_min, self.dom_x_max = x_min, x_max
        self.dom_ct_min, self.dom_ct_max = ct_min, ct_max
        w = canvas.winfo_width() or 320; h = canvas.winfo_height() or 260
        pad = 10
        self.px_min_x, self.px_max_x = pad, w - pad
        self.px_min_ct, self.px_max_ct = h - pad, pad
        self._sx = (self.px_max_x - self.px_min_x) / max(1e-9, (x_max - x_min))
        self._st = (self.px_min_ct - self.px_max_ct) / max(1e-9, (ct_max - ct_min))
    def to_px(self, x, ct) -> Tuple[int,int]:
        X = self.px_min_x + (x - self.dom_x_min) * self._sx
        Y = self.px_min_ct - (ct - self.dom_ct_min) * self._st
        return int(X), int(Y)

class MinkowskiInline:
    def __init__(self, canvas: tk.Canvas, get_cluster_xs):
        self.canvas = canvas
        self.get_cluster_xs = get_cluster_xs

    def _axes(self, mapper: MinkowskiMapper, beta: float):
        c = self.canvas; w = c.winfo_width() or 320; h = c.winfo_height() or 260
        ox, oy = mapper.to_px(0, 0)
        c.create_rectangle(1,1,w-1,h-1, outline="#213252")
        c.create_line(0, oy, w, oy, fill="#cbd5e1")  # x
        c.create_line(ox, h, ox, 0, fill="#cbd5e1")  # ct
        if abs(beta) > 1e-9:
            p1 = mapper.to_px(mapper.dom_x_min, beta * mapper.dom_x_min)
            p2 = mapper.to_px(mapper.dom_x_max, beta * mapper.dom_x_max)
            c.create_line(*p1, *p2, fill="#ef4444", width=2)  # x'
            p1 = mapper.to_px(beta * mapper.dom_ct_min, mapper.dom_ct_min)
            p2 = mapper.to_px(beta * mapper.dom_ct_max, mapper.dom_ct_max)
            c.create_line(*p1, *p2, fill="#ef4444", width=2)  # ct'
        # light-cone
        p1 = mapper.to_px(mapper.dom_x_min, mapper.dom_x_min); p2 = mapper.to_px(mapper.dom_x_max, mapper.dom_x_max)
        self.canvas.create_line(*p1, *p2, fill="#60a5fa", dash=(2,2))
        p1 = mapper.to_px(mapper.dom_x_min, -mapper.dom_x_min); p2 = mapper.to_px(mapper.dom_x_max, -mapper.dom_x_max)
        self.canvas.create_line(*p1, *p2, fill="#60a5fa", dash=(2,2))

    def render(self, scenario: sim.LengthContractionScenario):
        c = self.canvas; c.delete("all")
        cluster = self.get_cluster_xs()
        if not cluster: return
        xP, xQ = cluster
        tS = scenario.sim.t; ct_now = sim.C * tS
        beta = scenario.train.v / sim.C
        g = sim.gamma(beta) if abs(beta) > 0 else 1.0

        if abs(beta) > 1e-12:
            boost = sim.LorentzBoost1D(beta=beta)
            ship_now = sim.Event(ct=ct_now, x=scenario.train.center_x)
            ct_p_now = boost.to_other(ship_now).ct
            xP_p = (xP / g) - (beta * ct_p_now); xQ_p = (xQ / g) - (beta * ct_p_now)
            Pp_S = boost.to_self(sim.Event(ct=ct_p_now, x=xP_p))
            Qp_S = boost.to_self(sim.Event(ct=ct_p_now, x=xQ_p))
            Lp = xQ_p - xP_p
        else:
            Pp_S = sim.Event(ct=ct_now, x=xP); Qp_S = sim.Event(ct=ct_now, x=xQ); Lp = xQ - xP

        x_min = min(0.0, xP, Pp_S.x, Qp_S.x) - 0.1 * max(1.0, abs(xQ - xP))
        x_max = max(xQ, Pp_S.x, Qp_S.x) + 0.1 * max(1.0, abs(xQ - xP))
        ct_min = 0.0; ct_max = max(ct_now, Pp_S.ct, Qp_S.ct) * 1.1 if ct_now > 0 else 1.0
        mapper = MinkowskiMapper(self.canvas, x_min, x_max, ct_min, ct_max)
        self._axes(mapper, beta)

        p1 = mapper.to_px(x_min, ct_now); p2 = mapper.to_px(x_max, ct_now)
        c.create_line(*p1, *p2, fill="#94a3b8", dash=(3,3))
        PP = mapper.to_px(xP, ct_now); QQ = mapper.to_px(xQ, ct_now)
        c.create_oval(PP[0]-3,PP[1]-3,PP[0]+3,PP[1]+3, fill="#111827", outline="#e5e7eb")
        c.create_oval(QQ[0]-3,QQ[1]-3,QQ[0]+3,QQ[1]+3, fill="#111827", outline="#e5e7eb")
        c.create_line(PP[0], PP[1], QQ[0], QQ[1], fill="#e5e7eb", width=2)

        Pp = mapper.to_px(Pp_S.x, Pp_S.ct); Qp = mapper.to_px(Qp_S.x, Qp_S.ct)
        c.create_line(Pp[0], Pp[1], Qp[0], Qp[1], fill="#fca5a5", width=2)
        c.create_oval(Pp[0]-3,Pp[1]-3,Pp[0]+3,Pp[1]+3, fill="#7f1d1d", outline="#fca5a5")
        c.create_oval(Qp[0]-3,Qp[1]-3,Qp[0]+3,Qp[1]+3, fill="#7f1d1d", outline="#fca5a5")

        L = xQ - xP
        c.create_text((PP[0]+QQ[0])//2, PP[1]-12, text=f"L = {si_str(L)} m", fill="#e5e7eb", font=("Consolas", 8))
        c.create_text((Pp[0]+Qp[0])//2, (Pp[1]+Qp[1])//2+12, text=f"L′ ≈ {si_str(Lp)} m (≈ L/γ)", fill="#fca5a5", font=("Consolas", 8))
