# app_ui.py — 스타일, 사이드바, 메인 패널, 이벤트 바인딩
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

def _style(self):
    style = ttk.Style()
    try: style.theme_use("clam")
    except Exception: pass
    style.configure("Card.TFrame", background=BG_CARD)
    style.configure("TLabel", background=BG_DARK, foreground=FG_TEXT)
    style.configure("Accent.TButton", padding=8, font=("Segoe UI", 10, "bold"),
                    background=ACCENT, foreground="white")
    style.map("Accent.TButton", background=[("active", "#3d36c9")])
    style.configure("TScale", troughcolor="#111827", background=BG_DARK)
    style.configure("Combo.TMenubutton", background=BG_DARK, foreground=FG_TEXT)

# ----- 사이드바 -----


def _build_sidebar(self):
    sb = ttk.Frame(self.root, style="Card.TFrame"); sb.grid(row=0, column=0, sticky="nsew")
    tk.Label(sb, text=APP_TITLE, bg=BG_CARD, fg=FG_TEXT, font=("Segoe UI", 13, "bold"),
             anchor="w").pack(fill="x", padx=PAD, pady=(PAD, 8))

    # # 모드 스위치
    # tk.Label(sb, text="모드", bg=BG_CARD, fg=FG_SUB, anchor="w").pack(fill="x", padx=PAD, pady=(0,2))
    # rowm = tk.Frame(sb, bg=BG_CARD); rowm.pack(fill="x", padx=PAD, pady=(0,6))
    # ttk.Radiobutton(rowm, text="길이수축", value="LC",    variable=self.mode,
    #                 command=lambda: self.switch_mode("LC")).pack(side="left")
    # ttk.Radiobutton(rowm, text="쌍둥이",   value="TWINS", variable=self.mode,
    #                 command=lambda: self.switch_mode("TWINS")).pack(side="left", padx=8)
    self.lbl_mode = tk.Label(sb, text="모드: 길이수축 (LC)", bg=BG_CARD, fg=OK,
                     anchor="w", font=("Segoe UI", 10, "bold"))
    self.lbl_mode.pack(fill="x", padx=PAD, pady=(0,6))


    # β (v/c)
    tk.Label(sb, text="β (v/c)", bg=BG_CARD, fg=FG_SUB, anchor="w").pack(fill="x", padx=PAD)
    self.beta_var = tk.DoubleVar(value=self.ctrl.beta)
    row = tk.Frame(sb, bg=BG_CARD); row.pack(fill="x", padx=PAD, pady=(2,2))
    self.beta_entry = tk.Entry(row, textvariable=self.beta_var, width=8); self.beta_entry.pack(side="right")
    self.beta_entry.bind("<Return>", lambda e: self.apply_beta())
    self.beta_scale = ttk.Scale(sb, from_=0.0, to=0.99, orient=tk.HORIZONTAL,
                                variable=self.beta_var, command=self.on_beta_change)
    self.beta_scale.pack(fill="x", padx=PAD, pady=(2, 8))
    self.lbl_gamma = tk.Label(sb, text=f"γ = {self.ctrl.gamma:.3f}",
                              bg=BG_CARD, fg=FG_ACCENT, font=("Consolas", 11, "bold"))
    self.lbl_gamma.pack(fill="x", padx=PAD, pady=(6, 12))

    # c_vis (시연용 광속)
    # tk.Label(sb, text="시연용 광속 c_vis (m/s)", bg=BG_CARD, fg=FG_SUB, anchor="w").pack(fill="x", padx=PAD)
    # self.cvis_scale = ttk.Scale(sb, from_=0.1, to=5000.0, orient=tk.HORIZONTAL,
    #                             variable=self.c_vis_var, command=self.on_cvis_change)
    # self.cvis_scale.pack(fill="x", padx=PAD, pady=(2, 4))
    # crow = tk.Frame(sb, bg=BG_CARD); crow.pack(fill="x", padx=PAD, pady=(0, 8))
    # tk.Entry(crow, textvariable=self.c_vis_var, width=10).pack(side="left")
    # ttk.Button(crow, text="c_vis 적용", command=self.apply_cvis, style="Accent.TButton").pack(side="left", padx=6)
    # tk.Label(sb, text="※ 교육용 스케일(물리적 C와 별개)", bg=BG_CARD, fg=WARN, anchor="w").pack(fill="x", padx=PAD, pady=(0, 8))

    # 컨트롤 버튼
    ctr = tk.Frame(sb, bg=BG_CARD); ctr.pack(fill="x", padx=PAD, pady=(0, 8))
    self.btn_toggle = ttk.Button(ctr, text="▶ 재생", style="Accent.TButton", command=self.toggle_play)
    self.btn_step   = ttk.Button(ctr, text="⏭ 한 프레임", style="Accent.TButton", command=self.step_once)
    self.btn_reset  = ttk.Button(ctr, text="⏲ 초기화", style="Accent.TButton", command=self.reset)
    self.btn_fire   = ttk.Button(ctr, text="⚡ 레이저", style="Accent.TButton", command=self.fire_now)
    self.btn_toggle.grid(row=0, column=0, padx=(0,6)); self.btn_step.grid(row=0, column=1, padx=(0,6))
    self.btn_reset.grid(row=0, column=2, padx=(0,6)); self.btn_fire.grid(row=0, column=3)

    # 속도
    tk.Label(sb, text="시간 배율 (재생 속도)", bg=BG_CARD, fg=FG_SUB, anchor="w").pack(fill="x", padx=PAD)
    self.speed_var = tk.DoubleVar(value=0.6)
    ttk.Scale(sb, from_=0.05, to=5.0, orient=tk.HORIZONTAL, variable=self.speed_var)\
        .pack(fill="x", padx=PAD, pady=(2, 10))

    # 군집 선택
    tk.Label(sb, text="측정 군집 선택", bg=BG_CARD, fg=FG_SUB, anchor="w").pack(fill="x", padx=PAD)
    self.cluster_combo = ttk.Combobox(sb, values=[f"군집 {i+1}" for i in range(len(self.clusters))], state="readonly")
    self.cluster_combo.current(0)
    self.cluster_combo.pack(fill="x", padx=PAD, pady=(2, 6))
    self.cluster_combo.bind("<<ComboboxSelected>>", lambda e: self.render_all())

    # 민코프스키 패널 토글 (LC 전용)
    self.btn_minko = ttk.Button(sb, text="민코프스키 공간 보기", style="Accent.TButton", command=self.toggle_minkowski)
    self.btn_minko.pack(fill="x", padx=PAD, pady=(6, 6))
    self.minko_cont = ttk.Frame(sb, style="Card.TFrame")
    self.minko_cont.pack_propagate(False)
    self.minko_cont.configure(height=280)
    self.minko_visible = False
    self.canvas_M = tk.Canvas(self.minko_cont, bg=BG_CANVAS, highlightthickness=1, highlightbackground="#1f2937")
    self.canvas_M.pack(fill="both", expand=True, padx=PAD, pady=(0, PAD))
    self.minko = MinkowskiInline(self.canvas_M, self._active_cluster_minmax)

    self.minko_twins = MinkowskiTwinsInline(self.canvas_M)

    # 우주 가이드 모드
    ttk.Button(sb, text="우주 가이드 모드 시작 🚀", style="Accent.TButton",
               command=self.enter_guide).pack(fill="x", padx=PAD, pady=(0, 10))

    # 시작 상태(LC)에서 버튼 활성화 정리
    self.btn_fire.state(["!disabled"])
    self.btn_minko.state(["!disabled"])

    self.btn_jump = ttk.Button(sb, text="하이퍼스페이스 점프 ✦",
                       style="Accent.TButton", command=self.trigger_jump)
    self.btn_jump.pack(fill="x", padx=PAD, pady=(4, 10))


# ----- 메인 패널 -----


def _build_main_panels(self):
    for child in self.main_area.winfo_children():
        child.destroy()
    self.main_area.grid_columnconfigure(0, weight=1)
    self.main_area.grid_rowconfigure(0, weight=1)
    self.paned = ttk.Panedwindow(self.main_area, orient=tk.VERTICAL)
    self.paned.grid(row=0, column=0, sticky="nsew", padx=PAD, pady=PAD)

    # S
    top = tk.Frame(self.paned, bg=BG_DARK)
    top.grid_columnconfigure(0, weight=1); top.grid_rowconfigure(1, weight=1)
    tk.Label(top, text="1) 지구 관측자 좌표계 (S)", bg=BG_DARK, fg=FG_ACCENT,
             font=("Segoe UI", 11, "bold"), anchor="w").grid(row=0, column=0, sticky="ew", padx=PAD, pady=(PAD, 4))
    self.canvas_S = tk.Canvas(top, bg=BG_CANVAS, highlightthickness=0)
    self.canvas_S.grid(row=1, column=0, sticky="nsew", padx=PAD, pady=(0, PAD))
    self.view_S = ViewPane(self.canvas_S, "지구 프레임 S")

    # S'
    mid = tk.Frame(self.paned, bg=BG_DARK)
    mid.grid_columnconfigure(0, weight=1); mid.grid_rowconfigure(1, weight=1)
    tk.Label(mid, text="2) 우주선 관측자 좌표계 (S')", bg=BG_DARK, fg=FG_ACCENT,
             font=("Segoe UI", 11, "bold"), anchor="w").grid(row=0, column=0, sticky="ew", padx=PAD, pady=(PAD, 4))
    self.canvas_Sp = tk.Canvas(mid, bg=BG_CANVAS, highlightthickness=0)
    self.canvas_Sp.grid(row=1, column=0, sticky="nsew", padx=PAD, pady=(0, PAD))
    self.view_Sp = ViewPane(self.canvas_Sp, "우주선 프레임 S'")
    self.paned.add(top, weight=1); self.paned.add(mid, weight=1)



def restore_main_layout(self):
    self._build_main_panels()
    self.hyper_fx = HyperspaceFX(self.canvas_Sp)
    self.flame_fx = FlameFX()
    self.render_all()

# ----- 이벤트 -----


def _bind_events(self):
    self.canvas_S.bind("<Configure>", lambda e: self.render_all())
    self.canvas_Sp.bind("<Configure>", lambda e: self.render_all())
    self.canvas_M.bind("<Configure>", lambda e: self.render_M() if self.minko_visible else None)
    self.root.bind("<space>", lambda e: self.toggle_play())
    self.root.bind("<Left>", lambda e: self.stage_director.prev() if self.stage_director.visible else None)
    self.root.bind("<Right>", lambda e: self.stage_director.next() if self.stage_director.visible else None)

# ----- 모드 스위치 -----


