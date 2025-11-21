# app_render.py — S, S', 민코프스키 렌더링 로직
from __future__ import annotations

import os, math, random, tkinter as tk
from tkinter import ttk
from typing import List, Tuple, Optional

import sr_sim as sim

# 외부 모듈
from theme import *
from utils import LinearMap, si_str
from debris import Debris, _PALETTES
from viewpane import ViewPane
from starfield import Starfield
from minkowski_inline import MinkowskiInline, MinkowskiMapper
from controllers import ScenarioController, LCController, TwinsController
from minkowski_twins import MinkowskiTwinsInline

from stage_director import StageDirector
from effects import HyperspaceFX, FlameFX

DEBRIS_SCALE = 1e4

random.seed(42)

def _space_scale(self) -> float:
    c_vis = max(1e-6, float(self.c_vis_var.get())) or 300.0
    return sim.C / c_vis



def _active_cluster(self) -> List[Debris]:
    idx = max(0, min(len(self.clusters)-1, self.cluster_combo.current()))
    return self.clusters[idx]



def _active_cluster_minmax(self):
    cl = self._active_cluster()
    if not cl: return None
    xs = [d.x for d in cl]
    return (min(xs), max(xs))



def _debris_y(self, base_y: int, tS: float, d: Debris) -> int:
    # base_y는 패널 중앙 y, tS는 시나리오의 좌표시간
    return int(base_y + d.y_base_px + d.wiggle_a * math.sin(d.wiggle_w * tS + 0.5))




def render_all(self):
    if not self.stage_director.visible:
        self.render_S(); self.render_Sp()
    if self.minko_visible: self.render_M()



def render_S(self):
    c_vis_scale = self._space_scale()
    beta = self.ctrl.beta
    g    = self.ctrl.gamma
    L0   = self.ctrl.L0 or 120.0
    L    = (self.ctrl.L_contracted or L0)
    x_center = self.ctrl.ship_center_x

    xl = (x_center - L/2) / c_vis_scale
    xr = (x_center + L/2) / c_vis_scale

    self.view_S.clear(); self.view_S.draw_axes()
    h = self.canvas_S.winfo_height() or 300; y = h // 2

    # render_S() 내 LC 분기에서, 우주선 본체 그리기 전에 추가
    if isinstance(self.ctrl, LCController):
        if self.flame_fx.active and self.flame_fx.ghost:
            gx, gL = self.flame_fx.ghost
            xl_g = gx - gL/2
            xr_g = gx + gL/2
            self.view_S.draw_rod(
                xl_g / self._space_scale(), xr_g / self._space_scale(), y,
                color="#64748b", h_px=6, nose=False, width=1
            )

    if isinstance(self.ctrl, TwinsController):
        x_turn = self._twins_turn_x()

        # 시야 자동 스케일: 지구(0)와 B612가 항상 들어오도록 패널 도메인 설정
        margin = max(2e8, 0.12 * abs(x_turn))
        x_min = min(0.0, x_turn) - margin
        x_max = max(0.0, x_turn) + margin
        if hasattr(self.view_S, "set_temp_domain"):
            self.view_S.set_temp_domain(x_min, x_max)

        # 행성 렌더
        h = self.canvas_S.winfo_height() or 300
        y = h // 2
        self.view_S.draw_axes()
        self.view_S.draw_planet(0.0, y, label="지구(정지)")
        # B612를 턴 위치에 표시(보라색 계열)
        try:
            self.view_S.draw_planet(x_turn, y, r_px=16, fill="#7e22ce", label="B612")
        except TypeError:
            # draw_planet 시그니처가 (x,y,label=)만 받는 버전일 수도 있어 fallback
            self.view_S.draw_planet(x_turn, y, label="B612")


        # 이후 기존 우주선/파편/배지 렌더 로직 계속...

    # ---- 본체/행성 ----
    self.view_S.draw_planet(0.0, y, label="지구(정지)")
    self.view_S.draw_rod(xl, xr, y)

    if isinstance(self.ctrl, TwinsController):
        x_b612 = getattr(self.ctrl, "x_B612", 1.30e9)  # controllers에 넣은 값
        self.view_S.draw_planet(x_b612 / self._space_scale(), y, label="B612")
    

    # ---- 배경 군집 (S에서) ----
    if self.mode.get() == "LC":
        tS = self.ctrl.t
        sel = set(self._active_cluster())
        dust_scale = self._space_scale() * DEBRIS_SCALE
        center_x  = 0.0

    # 기존 d.x / c_vis_scale 대신:
    if isinstance(self.ctrl, LCController):
        for cluster in self.clusters:
            for d in cluster:
                y_px = self._debris_y(y, tS, d)
                x_vis = (d.x - center_x) / self._space_scale()
                if d in sel:
                    self.view_S.draw_debris_poly(x_vis, y_px, d.shape_pts, d.theta,
                                                fill="#a7f3d0", outline="#10b981", width=2)
                else:
                    self.view_S.draw_debris_poly(x_vis, y_px, d.shape_pts, d.theta,
                                                fill="#7c8697", outline="#b6c2d4", width=1)

    # ---- 시계(Clock overlays) ----
    mS = self.view_S._mapper()
    # ① 지구 위 시계: 좌표시간 t
    earth_px = mS.to_px(0.0)
    if isinstance(self.ctrl, TwinsController): self.view_S.note(f"t = {tS:.2f} s", int(earth_px) - 20, y - 34, fill="#c7d2fe")

    # ② 우주선 위 시계: 우주선 고유시간 τ_ship
    #    - Twins: traveler.state.tau
    #    - LC:    train_observer.state.tau
    if isinstance(self.ctrl, LCController):
        tau_ship = getattr(self.lc_scn.train_observer.state, "tau", 0.0)
    else:
        tau_ship = getattr(self.tw_scn.traveler.state, "tau", 0.0)

    ship_px = mS.to_px(x_center / c_vis_scale)
    if isinstance(self.ctrl, TwinsController):  self.view_S.note(f"τ_ship = {tau_ship:.2f} s", int(ship_px) - 40, y - 34, fill="#fca5a5")

    # ---- 상단 배지 ----
    self.view_S.badge((12, 18), [
        ("β", f"{beta:.2f}", FG_TEXT),
        ("γ", f"{g:.3f}", FG_ACCENT),
        ("L (수축)", f"{L:.1f} m", OK),
        ("t", f"{tS:.2f} s", FG_TEXT),
    ])

    # 만남(지구와 같은 위치)일 때 시간차 Δ 표기 (검증)
    # S 패널 기준: x_center ≈ 0 이면 만남으로 간주
    if abs(x_center) < 1e-6 and isinstance(self.ctrl, TwinsController):
        # 지구 고유시간 = earth_observer.state.tau (S에서 정지이므로 t와 동일하게 증가)
        tau_earth = getattr(self.tw_scn.earth_observer.state, "tau", tS)
        delta = tau_earth - tau_ship
        self.view_S.badge((12, 18+18*4+8), [
            ("Δ(earth - ship)", f"{delta:.2f} s", FG_ACCENT),
        ])




def render_Sp(self):
    c_vis_scale = self._space_scale()
    beta = self.ctrl.beta
    g    = self.ctrl.gamma
    L0   = self.ctrl.L0 or 120.0

    self.view_Sp.clear(); self.view_Sp.draw_axes()
    h = self.canvas_Sp.winfo_height() or 300; y = h // 2

    # LC 모드에서 전환 FX 중이면 FX만 그리고 종료
    if isinstance(self.ctrl, LCController) and getattr(self, "hyper_fx", None) and self.hyper_fx.active:
        self.view_Sp.clear()
        self.hyper_fx.render()
        self.view_Sp.badge((12, 18), [
            ("β", f"{beta:.2f}", FG_ACCENT),
            ("γ", f"{g:.3f}",    FG_ACCENT),
        ])
        return

    # 우주선(고유길이) — S′에선 항상 L0
    self.view_Sp.draw_rod((-L0/2)/c_vis_scale, (+L0/2)/c_vis_scale, y, nose=False, width=3)

    # 지구의 S′좌표: 컨트롤러 제공 값 사용 (항상 /c_vis_scale 해서 vis 단위로 유지)
    x_earth_p_vis = self.ctrl.earth_x_in_ship_frame() / c_vis_scale
    self.view_Sp.draw_planet(x_earth_p_vis if abs(beta) > 1e-12 else 0.0, y, label="지구(운동)")

    if isinstance(self.ctrl, TwinsController):
        try:
            # S(지구 프레임)에서의 거리 L_S를 컨트롤러에서 가져옴
            L_S = float(getattr(self.ctrl, "x_B612"))
        except Exception:
            # 없으면 턴 위치 추정 사용
            try:
                L_S = float(self._twins_turn_x())
            except Exception:
                L_S = 3.0e8  # 최후 안전값

        gamma_abs = sim.gamma(abs(beta)) if abs(beta) > 0 else 1.0
        L_prime_vis = (L_S / gamma_abs) / c_vis_scale
        x_b612_p_vis = x_earth_p_vis + L_prime_vis

        

        self.view_Sp.draw_planet(x_b612_p_vis, y, label="B612(운동)")


    # ---- 배경 군집(LC에서만; 요청대로 다른 로직은 보존) ----
    tS = self.ctrl.t
    sel = set(self._active_cluster())
    dust_scale = self._space_scale() * DEBRIS_SCALE
    center_x  = self.ctrl.ship_center_x

    # --- LC + S′ 에서 '선택된 군집'만 길이수축으로 보여주기 (간단 패치) ---
    if isinstance(self.ctrl, LCController):
        # 공통 준비
        tS       = self.ctrl.t
        beta     = self.ctrl.beta
        g        = self.ctrl.gamma if abs(beta) > 0 else 1.0
        ship_x   = self.ctrl.ship_center_x
        boost    = sim.LorentzBoost1D(beta=beta) if abs(beta) > 1e-12 else None

        if boost:
            ct_p_now  = boost.to_other(sim.Event(ct=sim.C*tS, x=ship_x)).ct
            x_earth_p = - beta * ct_p_now                 # (0/g) - beta*ct' = -beta*ct'
        else:
            ct_p_now  = 0.0
            x_earth_p = - ship_x                          # 저속 근사

        # 먼지들: 모두 같은 공식/같은 기준으로
        sel = set(self._active_cluster())
        for cluster in self.clusters:
            for d in cluster:
                y_px = self._debris_y(y, tS, d)
                if boost:
                    x_p = (d.x / g) - (beta * ct_p_now)   # ★ 같은 t′=ct′_now
                else:
                    x_p = d.x - ship_x                    # 저속 근사

                # (선택) 지구 앵커 보기
                # x_p -= x_earth_p
                # 선택 군집만 강조(1/γ 효과를 보이게)
                if d in sel:
                    self.view_Sp.draw_debris_poly(x_p / self._space_scale(), y_px, d.shape_pts, d.theta,
                                                fill="#a7f3d0", outline="#10b981", width=2)
                else:
                    # 배경 먼지는 이전처럼 살짝 축소해서 조용히 표시
                    self.view_Sp.draw_debris_poly(x_p / self._space_scale(), y_px, d.shape_pts, d.theta,
                                                fill="#7c8697", outline="#b6c2d4", width=1)


    # --- 시계(노트) & 배지: 기존 단위 일관성 유지 ---
    if isinstance(self.ctrl, LCController):
        tau_ship = getattr(self.lc_scn.train_observer.state, "tau", 0.0)
    else:
        tau_ship = getattr(self.tw_scn.traveler.state, "tau", 0.0)

    # 지구(동시) 시각: t_earth_icif = tS - β x_ship / C
    tS = self.ctrl.t
    x_ship = self.ctrl.ship_center_x
    t_earth_icif = tS - beta * (x_ship / sim.C)
    if t_earth_icif < 0: t_earth_icif = 0.0
    tau_earth_icif = t_earth_icif

    mP = self.view_Sp._mapper()
    ship_px  = mP.to_px(0.0)                 # S′에서 우주선 중심은 0
    earth_px = mP.to_px(x_earth_p_vis)       # 위에서 계산한 vis 단위 좌표 그대로 사용

    if isinstance(self.ctrl, TwinsController): self.view_Sp.note(f"τ_ship = {tau_ship:.2f} s", int(ship_px) - 40,  y - 34, fill="#fca5a5")
    if isinstance(self.ctrl, TwinsController): self.view_Sp.note(f"τ_earth = {tau_earth_icif:.2f} s", int(earth_px) - 44, y - 34, fill="#c7d2fe")

    self.view_Sp.badge((12, 18), [
        ("β", f"{beta:.2f}", FG_TEXT),
        ("γ", f"{g:.3f}", FG_ACCENT),
        ("L0", f"{L0:.1f} m", OK),
        ("τ_ship",  f"{tau_ship:.2f} s", FG_TEXT),
        ("τ_earth", f"{tau_earth_icif:.2f} s", FG_TEXT),
    ])

    if abs(x_earth_p_vis) < 1e-3 and isinstance(self.ctrl, TwinsController):
        delta = tau_earth_icif - tau_ship
        self.view_Sp.badge((12, 18 + 18*5 + 8), [("Δ(earth - ship)", f"{delta:.2f} s", FG_ACCENT)])




def toggle_minkowski(self):
    # ★ 모드 무관하게 토글
    if self.minko_visible:
        self.minko_cont.pack_forget()
        self.btn_minko.config(text="민코프스키 공간 보기")
        self.minko_visible = False
    else:
        self.minko_cont.pack(fill="x", padx=PAD, pady=(0, PAD))
        self.btn_minko.config(text="민코프스키 공간 숨기기")
        self.minko_visible = True
        self.render_M()




def render_M(self):
    if isinstance(self.ctrl, LCController):
        self.minko.render(self.lc_scn)
    elif isinstance(self.ctrl, TwinsController) and hasattr(self, "minko_twins"):
        self.minko_twins.render(self.tw_scn)



# ---------- 엔트리 ----------


