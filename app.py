# app.py — SRApp 본체 (UI, 컨트롤러, 렌더링)
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


import app_clusters
import app_ui
import app_controls
import app_render

class SRApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self._style()
        self.root.title(APP_TITLE)
        self.root.geometry("1380x960")
        self.root.minsize(1120, 780)
        self.root.configure(bg=BG_DARK)
        self.running = False

        # 시나리오(두 개 보유)
        self.c_vis_var = tk.DoubleVar(value=300.0)
        self.lc_scn = sim.LengthContractionScenario(
            sim.LengthContractionParams(
                train_rest_length=120.0, train_speed=0.6 * sim.C,
                laser_direction=+1, allow_sub_c_demo=True, demo_speed=self.c_vis_var.get() or 300.0,
            )
        )
        self.tw_scn = sim.TwinsScenario(sim.TwinsParams(
            v_out=0.6 * sim.C, v_back=0.6 * sim.C,
            accel_profile="finite", out_duration_s=1.5, back_duration_s=1.5, turn_duration_s=0.5
        ))


        # 기본 모드/컨트롤러
        self.mode = tk.StringVar(value="LC")
        self.ctrl: ScenarioController = LCController(self.lc_scn)

        # 메인 영역(오른쪽) — 먼저 생성(튜토리얼/렌더가 참조)
        self.root.grid_columnconfigure(0, minsize=SIDEBAR_WIDTH)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        self.main_area = tk.Frame(self.root, bg=BG_DARK)
        self.main_area.grid(row=0, column=1, sticky="nsew")
        

        # 데이터
        self.clusters: List[List[Debris]] = self._generate_clusters()
        self.cluster_names = [f"군집 {i+1}" for i in range(len(self.clusters))]
        self.running = False
        self.base_dt = self.ctrl.dt

        # 레이아웃/UI
        self._build_sidebar()
        self._build_main_panels()

        self.flame_fx = FlameFX()
        self.hyper_fx = HyperspaceFX(self.view_Sp.canvas, self.view_S.canvas)

        # 튜토리얼(스테이지 감독)
        self.stage_director = StageDirector(self, self.main_area)
        self._bind_events()
        self.render_all()

    # ----- 데이터 -----

    def _generate_clusters(self):
        return app_clusters._generate_clusters(self)

    def _style(self, *args, **kwargs):
        return app_ui._style(self, *args, **kwargs)

    def _build_sidebar(self, *args, **kwargs):
        return app_ui._build_sidebar(self, *args, **kwargs)

    def _build_main_panels(self, *args, **kwargs):
        return app_ui._build_main_panels(self, *args, **kwargs)

    def restore_main_layout(self, *args, **kwargs):
        return app_ui.restore_main_layout(self, *args, **kwargs)

    def _bind_events(self, *args, **kwargs):
        return app_ui._bind_events(self, *args, **kwargs)

    def switch_mode(self, *args, **kwargs):
        return app_controls.switch_mode(self, *args, **kwargs)

    def enter_guide(self, *args, **kwargs):
        return app_controls.enter_guide(self, *args, **kwargs)

    def on_beta_change(self, *args, **kwargs):
        return app_controls.on_beta_change(self, *args, **kwargs)

    def apply_beta(self, *args, **kwargs):
        return app_controls.apply_beta(self, *args, **kwargs)

    def on_cvis_change(self, *args, **kwargs):
        return app_controls.on_cvis_change(self, *args, **kwargs)

    def apply_cvis(self, *args, **kwargs):
        return app_controls.apply_cvis(self, *args, **kwargs)

    def toggle_play(self, *args, **kwargs):
        return app_controls.toggle_play(self, *args, **kwargs)

    def step_once(self, *args, **kwargs):
        return app_controls.step_once(self, *args, **kwargs)

    def reset(self, *args, **kwargs):
        return app_controls.reset(self, *args, **kwargs)

    def fire_now(self, *args, **kwargs):
        return app_controls.fire_now(self, *args, **kwargs)

    def _tick(self, *args, **kwargs):
        return app_controls._tick(self, *args, **kwargs)

    def _tick_once(self, *args, **kwargs):
        return app_controls._tick_once(self, *args, **kwargs)

    def trigger_jump(self, *args, **kwargs):
        return app_controls.trigger_jump(self, *args, **kwargs)

    def _perform_jump_if_needed(self, *args, **kwargs):
        return app_controls._perform_jump_if_needed(self, *args, **kwargs)

    def _twins_turn_x(self, *args, **kwargs):
        return app_controls._twins_turn_x(self, *args, **kwargs)

    def _space_scale(self, *args, **kwargs):
        return app_render._space_scale(self, *args, **kwargs)

    def _active_cluster(self, *args, **kwargs):
        return app_render._active_cluster(self, *args, **kwargs)

    def _active_cluster_minmax(self, *args, **kwargs):
        return app_render._active_cluster_minmax(self, *args, **kwargs)

    def _debris_y(self, *args, **kwargs):
        return app_render._debris_y(self, *args, **kwargs)

    def render_all(self, *args, **kwargs):
        return app_render.render_all(self, *args, **kwargs)

    def render_S(self, *args, **kwargs):
        return app_render.render_S(self, *args, **kwargs)

    def render_Sp(self, *args, **kwargs):
        return app_render.render_Sp(self, *args, **kwargs)

    def toggle_minkowski(self, *args, **kwargs):
        return app_render.toggle_minkowski(self, *args, **kwargs)

    def render_M(self, *args, **kwargs):
        return app_render.render_M(self, *args, **kwargs)


