# minkowski_twins.py — Twins 전용 민코프스키 렌더러
from __future__ import annotations
import math
import tkinter as tk
import sr_sim as sim
from minkowski_inline import MinkowskiMapper  # 기존 인라인 렌더의 매퍼 재사용

# 색상(메인과 톤 맞춤)
FG_TEXT   = "#e2e8f0"
FG_SUB    = "#a3aed0"
AXIS_COL  = "#cbd5e1"
CONE_COL  = "#60a5fa"
EARTH_COL = "#3b82f6"  # 파랑
SHIP_COL  = "#ef4444"  # 빨강
LINE_S    = "#94a3b8"
ICIF_COL  = "#fca5a5"

class MinkowskiTwinsInline:
    """쌍둥이 역설용 민코프스키:
    - 현재 지구 사건 E: (x=0, ct=C*t)
    - 현재 우주선 사건 S: (x=x_ship, ct=C*t), 라벨에 τ(고유시간) 표기
    - 수평선(ct=const) 가이드 + ICIF(순간적 공준 관성계) 축을 S를 지나도록 표시
    """
    def __init__(self, canvas: tk.Canvas):
        self.canvas = canvas

    def _axes(self, mapper: MinkowskiMapper, beta: float, through=None):
        c = self.canvas
        w = c.winfo_width() or 320
        h = c.winfo_height() or 260
        ox, oy = mapper.to_px(0, 0)

        # 테두리
        c.create_rectangle(1, 1, w-1, h-1, outline="#213252")
        # x, ct
        c.create_line(0, oy, w, oy, fill=AXIS_COL)
        c.create_line(ox, h, ox, 0, fill=AXIS_COL)

        # 광원뿔
        p1 = mapper.to_px(mapper.dom_x_min, mapper.dom_x_min)
        p2 = mapper.to_px(mapper.dom_x_max, mapper.dom_x_max)
        c.create_line(*p1, *p2, fill=CONE_COL, dash=(2, 2))
        p1 = mapper.to_px(mapper.dom_x_min, -mapper.dom_x_min)
        p2 = mapper.to_px(mapper.dom_x_max, -mapper.dom_x_max)
        c.create_line(*p1, *p2, fill=CONE_COL, dash=(2, 2))

        # ICIF 축 (현재 beta를 가진 S′의 x′, ct′ 축; S 사건을 지나도록)
        # x′축: ct = beta * (x - x_S) + ct_S
        # ct′축: x  = beta * (ct - ct_S) + x_S
        if through and abs(beta) > 1e-9:
            xS, ctS = through
            # x′
            X1, X2 = mapper.dom_x_min, mapper.dom_x_max
            ct1 = beta * (X1 - xS) + ctS
            ct2 = beta * (X2 - xS) + ctS
            p1 = mapper.to_px(X1, ct1); p2 = mapper.to_px(X2, ct2)
            c.create_line(*p1, *p2, fill=ICIF_COL, width=2)
            # ct′
            CT1, CT2 = mapper.dom_ct_min, mapper.dom_ct_max
            x1 = beta * (CT1 - ctS) + xS
            x2 = beta * (CT2 - ctS) + xS
            p1 = mapper.to_px(x1, CT1); p2 = mapper.to_px(x2, CT2)
            c.create_line(*p1, *p2, fill=ICIF_COL, width=2)

    def render(self, scn: "sim.TwinsScenario"):
        c = self.canvas
        if not hasattr(c, "winfo_width"):
            return
        c.delete("all")

        # 현재 좌표시간/사건
        tS      = scn.traveler.state.t          # S의 좌표시간
        ct_now  = sim.C * tS
        x_ship  = scn.traveler.state.x
        tau     = scn.traveler.state.tau
        beta    = (scn.traveler.state.v / sim.C) if sim.C != 0 else 0.0

        # 보기 범위 대략 잡기
        # (우주선 x 중심을 포함하고, 0(지구)도 포함되도록 버퍼)
        span_x = max(100.0, 1.2*abs(x_ship) + 100.0)
        x_min, x_max = -span_x, +span_x
        ct_min = 0.0
        ct_max = max(1.0, ct_now * 1.15)

        mapper = MinkowskiMapper(c, x_min, x_max, ct_min, ct_max)

        # 축 + 광원뿔 + ICIF 축(S를 지나는 x′, ct′)
        self._axes(mapper, beta, through=(x_ship, ct_now))

        # S의 동시선(수평선) 가이드
        p1 = mapper.to_px(x_min, ct_now)
        p2 = mapper.to_px(x_max, ct_now)
        c.create_line(*p1, *p2, fill=LINE_S, dash=(3, 3))

        # 지구 세계선(x=0) 가이드
        e0 = mapper.to_px(0.0, ct_min)
        e1 = mapper.to_px(0.0, ct_max)
        c.create_line(*e0, *e1, fill="#6ea8ff")

        # 사건 점: E(지구), S(우주선)
        # E: (0, ct_now)
        EP = mapper.to_px(0.0, ct_now)
        c.create_oval(EP[0]-4, EP[1]-4, EP[0]+4, EP[1]+4, fill=EARTH_COL, outline="white")
        c.create_text(EP[0]+8, EP[1]-10,
                      text=f"E: t={tS:.2f}s", fill=EARTH_COL, font=("Consolas", 10, "bold"), anchor="w")

        # S: (x_ship, ct_now)
        SP = mapper.to_px(x_ship, ct_now)
        c.create_oval(SP[0]-5, SP[1]-5, SP[0]+5, SP[1]+5, fill=SHIP_COL, outline="white", width=1)
        c.create_text(SP[0]+8, SP[1]+12,
                      text=f"S: τ={tau:.2f}s, x={x_ship:.1f}m", fill=SHIP_COL, font=("Consolas", 10, "bold"), anchor="w")

        # 범례/상단 정보
        g = sim.gamma(beta) if abs(beta) < 1 else float("inf")
        info = f"β={beta:.2f}, γ={g:.3f}"
        c.create_text(12, 14, text="Minkowski (Twins)", fill=FG_SUB, font=("Segoe UI", 11, "bold"), anchor="w")
        c.create_text(12, 32, text=info, fill=FG_TEXT, font=("Consolas", 10), anchor="w")
