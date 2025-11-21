# main.py — 우주 가이드 모드(스테이지 전환) + 인앱 튜토리얼 + LC/Twins 컨트롤러 스위치
from __future__ import annotations
import os, math, random, tkinter as tk
from tkinter import ttk
from typing import List, Tuple, Optional
import sr_sim as sim

# 외부 모듈(분리 파일)
from theme import *
from utils import LinearMap, si_str
from debris import Debris
from viewpane import ViewPane
from starfield import Starfield
from minkowski_inline import MinkowskiInline, MinkowskiMapper
from controllers import ScenarioController, LCController, TwinsController  # ★ Twins 포함

# ---------- 콘솔 숨김 (Windows) ----------
def _hide_console_if_windows():
    if os.name == "nt":
        try:
            import ctypes
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 0)
        except Exception:
            pass
_hide_console_if_windows()

# ---------- 테마 / 상수 ----------
APP_TITLE = "SR 시뮬레이션 UI (길이수축 · c_vis · 우주 가이드)"
SIDEBAR_WIDTH = 380
BG_DARK   = "#0b1220"
BG_CARD   = "#0f172a"
BG_CANVAS = "#060b13"
FG_TEXT   = "#e2e8f0"
FG_SUB    = "#a3aed0"
FG_ACCENT = "#93c5fd"
ACCENT    = "#4f46e5"
ACCENT_HI = "#22d3ee"
WARN      = "#f59e0b"
OK        = "#22c55e"
PAD       = 10

random.seed(42)

# ---------- 튜토리얼 감독 ----------
class StageDirector:
    """
    메인 영역 위에 '오버레이 캔버스 + 네비 바'를 place()로 덮어씌워
    같은 창 안에서 튜토리얼을 표시한다.
    """
    def __init__(self, host: "SRApp", container: tk.Frame):
        self.host = host
        self.container = container
        self.visible = False
        self.stage = 0
        self.max_stage = 4
        self._after_id = None

        # 오버레이 루트 프레임 (처음엔 숨김)
        self.overlay = tk.Frame(self.container, bg=BG_CANVAS)
        self.overlay.place_forget()

        # 캔버스(별 배경 + 콘텐츠)
        self.canvas = tk.Canvas(self.overlay, bg=BG_CANVAS, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.starfield = Starfield(self.canvas, density=140)

        # 네비 바 (오버레이 내 하단 고정)
        self.nav = tk.Frame(self.overlay, bg=BG_CARD)
        self.nav.pack(fill="x", side="bottom")
        self.btn_prev = ttk.Button(self.nav, text="◀ 이전", style="Accent.TButton", command=self.prev)
        self.btn_next = ttk.Button(self.nav, text="다음 ▶", style="Accent.TButton", command=self.next)
        self.btn_exit = ttk.Button(self.nav, text="메인으로", style="Accent.TButton", command=self.hide)
        self.btn_prev.pack(side="left", padx=8, pady=6)
        self.btn_next.pack(side="left", padx=8, pady=6)
        self.btn_exit.pack(side="right", padx=8, pady=6)

        # 리사이즈 시 재렌더 (플랫폼별 0x0 초기 사이즈 보호)
        self.canvas.bind("<Configure>", lambda e: self.render() if self.visible else None)

    def show(self):
        if self.visible: return
        self.visible = True
        self.overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._bind_keys(True)
        self._loop()

    def hide(self):
        if not self.visible: return
        self.visible = False
        self.overlay.place_forget()
        self._bind_keys(False)
        if self._after_id and hasattr(self.host, "root"):
            try: self.host.root.after_cancel(self._after_id)
            except Exception: pass
        self._after_id = None
        self.host.render_all()

    def next(self):
        self.stage = min(self.max_stage, self.stage + 1)
        self.render()

    def prev(self):
        self.stage = max(0, self.stage - 1)
        self.render()

    def _bind_keys(self, enable: bool):
        if enable:
            self.host.root.bind("<Left>", self._on_left)
            self.host.root.bind("<Right>", self._on_right)
        else:
            try:
                self.host.root.unbind("<Left>")
                self.host.root.unbind("<Right>")
            except Exception:
                pass

    def _on_left(self, _e): self.prev()
    def _on_right(self, _e): self.next()

    def _loop(self):
        if not self.visible: return
        self.starfield.step()
        self.render()
        if hasattr(self.host, "root"):
            self._after_id = self.host.root.after(33, self._loop)

    def render(self):
        c = self.canvas
        c.delete("all")
        w = c.winfo_width() or 1100
        h = c.winfo_height() or 700

        # 별 배경
        self.starfield.draw()

        # 카드 함수
        def card(x0, y0, x1, y1): c.create_rectangle(x0,y0,x1,y1, fill="#0d1629", outline="#1b2a45", width=2)

        # 공통 타이틀
        c.create_text(20, 20, text="우주 가이드 — 민코프스키 공간", anchor="nw",
                      fill=FG_ACCENT, font=("Segoe UI", 18, "bold"))

        # ★ 컨트롤러에서 β, γ, 시간 뽑기
        beta = getattr(self.host.ctrl, "beta", 0.0)
        g    = getattr(self.host.ctrl, "gamma", 1.0)
        tS   = getattr(self.host.ctrl, "t", 0.0)
        ct_now = sim.C * tS
        ship_x = getattr(self.host.ctrl, "ship_center_x", 0.0)

        # === 스테이지 ===
        if self.stage == 0:
            card(60, 80, w-60, h-100)
            c.create_text(w//2, 140, text="Stage 1. 사건과 세계선", fill=FG_TEXT, font=("Segoe UI", 20, "bold"))
            txt = ("· 점 = 사건(event)\n"
                   "· 수직선 = 정지 물체의 세계선 (x=상수)\n"
                   "· 사선 = 등속 운동 물체의 세계선 (x=vt)\n"
                   "· 45° = 빛의 세계선 (c)\n\n"
                   "이제 다음으로 넘어가 x/ct 축과 S′ 축을 만나 봅시다.")
            c.create_text(w//2, h//2, text=txt, fill=FG_TEXT, font=("Segoe UI", 12), justify="center")
            cx, cy = w//2, h//2 + 120
            c.create_line(cx-220, cy, cx+220, cy, fill="#cbd5e1")
            c.create_line(cx, cy+140, cx, cy-140, fill="#cbd5e1")
            c.create_line(cx-140, cy-140, cx+140, cy+140, fill="#60a5fa", dash=(2,2))
            c.create_line(cx-140, cy+140, cx+140, cy-140, fill="#60a5fa", dash=(2,2))
            c.create_line(cx, cy+120, cx+160, cy-40, fill="#34d399", width=2)
            c.create_oval(cx-4,cy-4,cx+4,cy+4, fill="#ffd166", outline="")
        elif self.stage == 1:
            card(60, 80, w-60, h-100)
            c.create_text(w//2, 120, text="Stage 2. 두 축: (x, ct) vs (x′, ct′)", fill=FG_TEXT, font=("Segoe UI", 20, "bold"))
            txt = ("· 검은 축: S의 x, ct\n· 빨간 축: S′의 x′, ct′  (S′은 +x로 v=βc)\n· β가 커질수록 S′ 축이 더 기울어집니다.")
            c.create_text(120, 180, text=txt, fill=FG_TEXT, font=("Segoe UI", 12), anchor="nw")
            x_min, x_max, ct_min, ct_max = -150, 150, 0.0, 200
            mapper = MinkowskiMapper(c, x_min, x_max, ct_min, ct_max)
            ox, oy = mapper.to_px(0,0)
            c.create_line(80, oy, w-80, oy, fill="#cbd5e1")
            c.create_line(ox, h-140, ox, 140, fill="#cbd5e1")
            if abs(beta) > 1e-9:
                p1 = mapper.to_px(x_min, beta*x_min); p2 = mapper.to_px(x_max, beta*x_max)
                c.create_line(*p1, *p2, fill="#ef4444", width=3)
                p1 = mapper.to_px(beta*ct_min, ct_min); p2 = mapper.to_px(beta*ct_max, ct_max)
                c.create_line(*p1, *p2, fill="#ef4444", width=3)
            c.create_text(ox+18, 150, text=f"β = {beta:.2f}, γ = {g:.3f}", fill=FG_ACCENT, font=("Consolas", 12,"bold"))
        elif self.stage == 2:
            card(60, 80, w-60, h-100)
            c.create_text(w//2, 120, text="Stage 3. 동시선", fill=FG_TEXT, font=("Segoe UI", 20, "bold"))
            txt = ("· S의 동시선: ct=상수 → 수평선\n· S′의 동시선: x′축과 평행한 기울어진 선\n· 이 차이가 '동시성의 상대성'입니다.")
            c.create_text(120, 180, text=txt, fill=FG_TEXT, font=("Segoe UI", 12), anchor="nw")
            mapper = MinkowskiMapper(c, -300, 300, 0, max(300, ct_now*1.2 if ct_now>0 else 300))
            self._axes_demo(c, mapper, beta)
            p1 = mapper.to_px(-300, ct_now); p2 = mapper.to_px(300, ct_now)
            c.create_line(*p1, *p2, fill="#94a3b8", dash=(4,4))
            c.create_text(p2[0]-60, p2[1]-12, text="S: t=const", fill="#94a3b8", font=("Segoe UI", 10))
            if abs(beta) > 1e-12:
                ship_now_ct = ct_now
                xs = [-300, 300]; pts=[]
                for X in xs:
                    ct = beta * X + (ship_now_ct - beta*ship_x)
                    pts.append(mapper.to_px(X, ct))
                c.create_line(*pts[0], *pts[1], fill="#fca5a5", dash=(4,4))
                c.create_text((pts[0][0]+pts[1][0])//2, (pts[0][1]+pts[1][1])//2 - 14, text="S′: t′=const", fill="#fca5a5", font=("Segoe UI", 10))
        elif self.stage == 3:
            card(60, 80, w-60, h-100)
            c.create_text(w//2, 120, text="Stage 4. 길이수축 L′ = L/γ", fill=FG_TEXT, font=("Segoe UI", 20, "bold"))
            c.create_text(120, 180, text=f"현재 β={beta:.2f}, γ={g:.3f}", fill=FG_ACCENT, font=("Consolas", 12, "bold"), anchor="nw")
        else:
            card(60, 80, w-60, h-100)
            c.create_text(w//2, 140, text="Stage 5. 실험으로 돌아가기", fill=FG_TEXT, font=("Segoe UI", 20, "bold"))
            c.create_text(w//2, h//2, text="메인으로 복귀해 S / S′ / 민코프스키 패널을 조작해보세요.",
                          fill=FG_TEXT, font=("Segoe UI", 12))

        c.create_text(20, h-56, text="←/→ 또는 [이전]/[다음] 이동 · [메인으로]는 시뮬레이터 복귀", anchor="w",
                      fill="#b6c3dd", font=("Segoe UI", 10))

    def _axes_demo(self, c, mapper: "MinkowskiMapper", beta: float):
        w = c.winfo_width() or 1100; h = c.winfo_height() or 700
        ox, oy = mapper.to_px(0,0)
        c.create_line(80, oy, w-80, oy, fill="#cbd5e1")
        c.create_line(ox, h-140, ox, 140, fill="#cbd5e1")
        p1 = mapper.to_px(mapper.dom_x_min, mapper.dom_x_min); p2 = mapper.to_px(mapper.dom_x_max, mapper.dom_x_max)
        c.create_line(*p1, *p2, fill="#60a5fa", dash=(2,2))
        p1 = mapper.to_px(mapper.dom_x_min, -mapper.dom_x_min); p2 = mapper.to_px(mapper.dom_x_max, -mapper.dom_x_max)
        c.create_line(*p1, *p2, fill="#60a5fa", dash=(2,2))
        if abs(beta) > 1e-9:
            p1 = mapper.to_px(mapper.dom_x_min, beta*mapper.dom_x_min)
            p2 = mapper.to_px(mapper.dom_x_max, beta*mapper.dom_x_max)
            c.create_line(*p1, *p2, fill="#ef4444", width=3)
            p1 = mapper.to_px(beta*mapper.dom_ct_min, mapper.dom_ct_min)
            p2 = mapper.to_px(beta*mapper.dom_ct_max, mapper.dom_ct_max)
            c.create_line(*p1, *p2, fill="#ef4444", width=3)

# ---------- 메인 앱 ----------
class SRApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self._style()
        self.root.title(APP_TITLE)
        self.root.geometry("1380x960")
        self.root.minsize(1120, 780)
        self.root.configure(bg=BG_DARK)

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

        # 튜토리얼(스테이지 감독)
        self.stage_director = StageDirector(self, self.main_area)
        self._bind_events()
        self.render_all()

    # ----- 데이터 -----
    def _generate_clusters(self) -> List[List[Debris]]:
        clusters = []
        specs = [( 60_000_000.0,10,2.6e7),(160_000_000.0,14,1.8e7),
                 (300_000_000.0,9,3.2e7),(420_000_000.0,12,2.2e7)]
        for center, n, gap in specs:
            base = center - (n//2)*gap
            xs = [base + i*gap + random.uniform(-0.2,0.2)*gap for i in range(n)]
            clusters.append([Debris(x) for x in xs])
        return clusters

    # ----- 스타일 -----
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

        # 모드 스위치
        tk.Label(sb, text="모드", bg=BG_CARD, fg=FG_SUB, anchor="w").pack(fill="x", padx=PAD, pady=(0,2))
        rowm = tk.Frame(sb, bg=BG_CARD); rowm.pack(fill="x", padx=PAD, pady=(0,6))
        ttk.Radiobutton(rowm, text="길이수축", value="LC",    variable=self.mode,
                        command=lambda: self.switch_mode("LC")).pack(side="left")
        ttk.Radiobutton(rowm, text="쌍둥이",   value="TWINS", variable=self.mode,
                        command=lambda: self.switch_mode("TWINS")).pack(side="left", padx=8)

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

        # 우주 가이드 모드
        ttk.Button(sb, text="우주 가이드 모드 시작 🚀", style="Accent.TButton",
                   command=self.enter_guide).pack(fill="x", padx=PAD, pady=(0, 10))

        # 시작 상태(LC)에서 버튼 활성화 정리
        self.btn_fire.state(["!disabled"])
        self.btn_minko.state(["!disabled"])

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
    def switch_mode(self, name: str):
        if self.running:
            self.toggle_play()  # 일시정지

        if name == "LC":
            self.ctrl = LCController(self.lc_scn)
            self.beta_var.set(self.ctrl.beta)
            self.btn_fire.state(["!disabled"])
            self.btn_minko.state(["!disabled"])
        else:
            self.ctrl = TwinsController(self.tw_scn, ship_L0=120.0)
            self.beta_var.set(self.ctrl.beta)
            self.btn_fire.state(["disabled"])
            self.btn_minko.state(["disabled"])
            if self.minko_visible:
                self.toggle_minkowski()

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
        for _ in range(2):
            self.ctrl.step()
        self.render_all()

    # ----- 렌더 -----
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
        return int(base_y - 60 + d.yoff + d.wiggle_a * math.sin(d.wiggle_w * tS + 0.5))

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
        self.view_S.draw_planet(0.0, y, label="지구(정지)")
        self.view_S.draw_rod(xl, xr, y)

        # 배경 군집 (S에서)
        tS = self.ctrl.t
        sel = set(self._active_cluster())
        for cluster in self.clusters:
            for d in cluster:
                y_px = self._debris_y(y, tS, d)
                if d in sel:
                    self.view_S.draw_debris_poly(d.x / c_vis_scale, y_px, d.shape_pts, d.theta,
                                                 fill="#a7f3d0", outline="#10b981", width=2)
                else:
                    self.view_S.draw_debris_poly(d.x / c_vis_scale, y_px, d.shape_pts, d.theta,
                                                 fill="#7c8697", outline="#b6c2d4", width=1)

        self.view_S.badge((12, 18), [
            ("β", f"{beta:.2f}", FG_TEXT),
            ("γ", f"{g:.3f}", FG_ACCENT),
            ("L (수축)", f"{L:.1f} m", OK),
            # ("c_vis", f"{self.c_vis_var.get():.0f} m/s", FG_TEXT),
            ("t", f"{tS:.2f} s", FG_TEXT),
        ])
        # main.py — render_S() 마지막 배지 밑에 추가
        if isinstance(self.ctrl, TwinsController):
            phase = getattr(self.ctrl.scn, "phase", "")
            v_c   = self.ctrl.beta
            self.view_S.badge((12, 18 + 18*5 + 6), [
                ("phase", f"{phase}", FG_TEXT),
                ("v_ship", f"{v_c:.3f} c", FG_TEXT),
            ])


    def render_Sp(self):
        c_vis_scale = self._space_scale()
        beta = self.ctrl.beta
        g    = self.ctrl.gamma
        L0   = self.ctrl.L0 or 120.0

        self.view_Sp.clear(); self.view_Sp.draw_axes()
        h = self.canvas_Sp.winfo_height() or 300; y = h // 2
        self.view_Sp.draw_rod((-L0/2)/c_vis_scale, (+L0/2)/c_vis_scale, y, nose=False, width=3)

        # 지구 위치 (S′)
        x_earth_p = self.ctrl.earth_x_in_ship_frame() / c_vis_scale
        self.view_Sp.draw_planet(x_earth_p if abs(beta)>1e-12 else 0.0, y, label="지구(운동)")

        self.view_Sp.badge((12, 18), [
            ("β", f"{beta:.2f}", FG_TEXT),
            ("γ", f"{g:.3f}", FG_ACCENT),
            ("L0", f"{L0:.1f} m", OK),
            # ("c_vis", f"{self.c_vis_var.get():.0f} m/s", FG_TEXT),
        ])

    def toggle_minkowski(self):
        # LC 전용
        if not isinstance(self.ctrl, LCController):
            return
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
        # LC 전용 표시
        if isinstance(self.ctrl, LCController):
            self.minko.render(self.lc_scn)

# ---------- 엔트리 ----------
def main():
    root = tk.Tk()
    app = SRApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
