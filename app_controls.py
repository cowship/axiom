# app_controls.py — 모드 전환, 재생/일시정지, 점프 등 컨트롤 로직
from __future__ import annotations
from controllers import TwinsController  # ★ 추가

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

def switch_mode(self, name: str):
    if self.running:
        self.toggle_play()

    if name == "LC":
        self.ctrl = LCController(self.lc_scn)
        self.beta_var.set(self.ctrl.beta)
        self.btn_fire.state(["!disabled"])
        self.btn_minko.state(["!disabled"])
        # ▼ 추가: 배지/점프 버튼
        self.lbl_mode.config(text="모드: 길이수축 (LC)", fg=OK)
        self.btn_jump.state(["!disabled"])
    else:
        self.ctrl = TwinsController(self.tw_scn, ship_L0=120.0)
        self.beta_var.set(self.ctrl.beta)
        self.btn_fire.state(["disabled"])
        self.btn_minko.state(["!disabled"])
        if self.minko_visible:
            self.toggle_minkowski()
        # ▼ 추가: 배지/점프 버튼
        self.lbl_mode.config(text="모드: 쌍둥이 (B612 미션)", fg=FG_ACCENT)
        self.btn_jump.state(["disabled"])


    self.lbl_gamma.config(text=f"γ = {self.ctrl.gamma:.3f}")
    self.base_dt = self.ctrl.dt
    self.render_all()

# ----- 가이드 모드 -----


def enter_guide(self):
    if self.running: self.toggle_play()
    self.stage_director.show()

# ----- 핸들러 -----


def on_beta_change(self, _evt=None):
    beta = max(0.0, min(0.99, float(self.beta_var.get())))
    self.beta_var.set(beta)
    self.ctrl.apply_beta(beta)
    self.lbl_gamma.config(text=f"γ = {self.ctrl.gamma:.3f}")
    self.render_all()



def apply_beta(self):
    try: beta = float(self.beta_var.get())
    except Exception: return
    beta = max(0.0, min(0.99, beta)); self.beta_var.set(beta); self.on_beta_change()



def on_cvis_change(self, _evt=None):
    self.apply_cvis(); self.render_all()



def apply_cvis(self):
    c_vis = float(self.c_vis_var.get()) or 300.0
    # LC에서만 광원 데모 스피드 반영
    if isinstance(self.ctrl, LCController):
        for laser in self.lc_scn.train.lasers:
            laser.allow_sub_c_demo = True; laser.demo_speed = c_vis



def toggle_play(self):
    self.running = not self.running
    self.btn_toggle.config(text="⏸ 일시정지" if self.running else "▶ 재생")
    if self.running: self._tick()



def step_once(self):
    was = self.running; self.running = False; self._tick_once(); self.running = was



def reset(self):
    self.ctrl.reset()
    if hasattr(self, "flame_fx"):
        self.flame_fx.stop()
        self.hyper_fx.active = False
        self.hyper_fx.t = 0.0
    self.render_all()



def fire_now(self):
    # 컨트롤러 경유 (Twins는 noop)
    self.ctrl.fire_laser()
    self.apply_cvis()
    self.render_all()

# ----- 루프 -----


def _tick(self):
    if not self.running: return
    self._tick_once(); self.root.after(16, self._tick)



def _tick_once(self):
    speed = float(self.speed_var.get())
    self.ctrl.dt = max(1e-5, min(0.05, self.base_dt * speed))

    # 시뮬 step
    for _ in range(2):
        self.ctrl.step()

    # FX 스텝 (LC일 때만 의미 있으나, 안전하게 항상 호출 가능)
    dt_fx = getattr(self.ctrl, "dt", 0.01) if hasattr(self, "ctrl") else getattr(getattr(self, "scn", None), "sim", type("X", (), {"dt":0.01})()).dt
    if hasattr(self, "hyper_fx") and self.hyper_fx.active:
        self.hyper_fx.step(2 * dt_fx)

    if self.flame_fx.active:
        self.flame_fx.step(2 * self.ctrl.dt)
    if self.hyper_fx.active:
        self.hyper_fx.step(2 * self.ctrl.dt)

    # FX 종료 후 모드 전환 체크
    self._perform_jump_if_needed()

    self.render_all()


# ----- 렌더 -----


def trigger_jump(self, *args):
    """LC → (FX 재생) → TWINS 모드 전환 트리거."""
    # LC에서만 동작
    if isinstance(self.ctrl, TwinsController):
        self.switch_mode("LC")
        self.btn_jump.state(["!disabled"])
        self.render_all()
        return
    if self.mode.get() == "TWINS":
        self.switch_mode("LC")
        self.render_all()
        return
    from controllers import LCController
    if not isinstance(self.ctrl, LCController):
        return
    # 위 S: 현재 수축 길이 L, 선체 잔상 표시
    L0 = self.ctrl.L0 or 120.0
    L  = self.ctrl.L_contracted or L0
    x_center = self.ctrl.ship_center_x
    self.flame_fx.arm(x_center, L)
    # 아래 S': 스트릭 스타트
    self.hyper_fx.start()



def _perform_jump_if_needed(self):
    """FX 종료 감지 → TWINS 모드로 실제 전환."""
    if self.hyper_fx.active:
        return
    # 한 번만 전환하려면, hyper_fx가 방금 끝난 후(t>0) 상태를 체크
    if self.hyper_fx.t > 0.0:
        self.switch_mode("TWINS")
        self.btn_jump.state(["!disabled"])
        # FX 상태 리셋
        self.hyper_fx.t = 0.0
        self.flame_fx.stop()
# SRApp 내부 (메서드로 추가)



def _twins_turn_x(self) -> float:
    """
    Twins 모드에서 B612(턴 지점) 월드 좌표 x를 얻는다.
    1) 컨트롤러에 있으면 우선 사용
    2) 시나리오에 있으면 사용
    3) 없으면 파라미터로 추정: v_out*out_duration_s
    """
    # controllers.TwinsController 를 쓰는 구조
    try:
        scn = getattr(self.ctrl, "scn", None)
        if scn is not None:
            if hasattr(scn, "x_turn_m") and scn.x_turn_m is not None:
                return scn.x_turn_m
            p = getattr(scn, "params", None)
            if p is not None:
                return p.v_out * p.out_duration_s
    except Exception:
        pass

    # self.tw_scn (직접 보유) 구조
    try:
        if hasattr(self, "tw_scn"):
            if hasattr(self.tw_scn, "x_turn_m") and self.tw_scn.x_turn_m is not None:
                return self.tw_scn.x_turn_m
            p = getattr(self.tw_scn, "params", None)
            if p is not None:
                return p.v_out * p.out_duration_s
    except Exception:
        pass

    # 최후의 안전값
    return 3.0e8




