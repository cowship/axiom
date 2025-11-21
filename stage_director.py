# stage_director.py — 튜토리얼/오버레이 관리 모듈
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import sr_sim as sim
from theme import BG_CANVAS, BG_CARD, FG_TEXT, FG_ACCENT, ACCENT
from starfield import Starfield
from minkowski_inline import MinkowskiMapper


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

# --- FX: 스타워즈식 하이퍼스페이스 스트릭(아래 S') + 위 S 잔상/불꽃(간소화) ---

