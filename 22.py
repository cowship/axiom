# main.py — SR 길이수축 + 하이퍼스페이스(스타워즈풍) + B612 쌍둥이(반바퀴) 시뮬레이터
from __future__ import annotations
import os, math, random, tkinter as tk
from tkinter import ttk
from typing import List, Tuple, Optional
import sr_sim as sim

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

# ---------- 테마 ----------
APP_TITLE = "SR 시뮬레이션 (길이수축 · 하이퍼스페이스 · B612 쌍둥이)"
SIDEBAR_WIDTH = 380
BG_DARK   = "#0b1220"
BG_CARD   = "#0f172a"
BG_CANVAS = "#060b13"
FG_TEXT   = "#e2e8f0"
FG_SUB    = "#a3aed0"
FG_ACCENT = "#93c5fd"
ACCENT    = "#4f46e5"
ACCENT_HI = "#22d3ee"
OK        = "#22c55e"
PAD       = 10
random.seed(42)

# ---------- 유틸 ----------
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
    if a >= 1e12: return f"{n/1e12:.1f} T"
    if a >= 1e9:  return f"{n/1e9:.1f} G"
    if a >= 1e6:  return f"{n/1e6:.1f} M"
    if a >= 1e3:  return f"{n/1e3:.1f} k"
    if a >= 1:    return f"{n:.0f}"
    return f"{n:.2g}"

# ---------- 우주 쓰레기 ----------
_PALETTES = [
    ("#a5b4fc", "#e0e7ff"),
    ("#93c5fd", "#dbeafe"),
    ("#6ee7b7", "#bbf7d0"),
    ("#fcd34d", "#fef3c7"),
    ("#fca5a5", "#fee2e2"),
    ("#c4b5fd", "#ede9fe"),
]
class Debris:
    def __init__(self, x: float, y_base_px: int, color_pair: Tuple[str,str]):
        self.x = x
        self.y_base_px = y_base_px
        self.fill, self.outline = color_pair
        self.r = random.randint(2, 5)
        self.theta = random.uniform(0, math.tau)
        n = random.randint(5, 7)
        self.shape_pts = []
        for i in range(n):
            ang = (i / n) * math.tau + random.uniform(-0.12, 0.12)
            rad = self.r * random.uniform(0.7, 1.15)
            self.shape_pts.append((rad * math.cos(ang), rad * math.sin(ang)))
        self.wiggle_w = random.uniform(0.3, 1.0)
        self.wiggle_a = random.uniform(0.6, 1.6)

# ---------- View ----------
class ViewPane:
    """동적 월드-픽셀 매핑 지원 (set_temp_domain)."""
    def __init__(self, canvas: tk.Canvas, title: str):
        self.canvas = canvas; self.title = title
        self._temp_domain: Optional[Tuple[float,float]] = None
    def clear(self): self.canvas.delete("all")
    def set_temp_domain(self, x_min: float, x_max: float):
        if x_max - x_min < 1.0:
            m = 100.0
            x_min -= m; x_max += m
        self._temp_domain = (x_min, x_max)
    def clear_domain(self): self._temp_domain = None
    def draw_axes(self):
        c = self.canvas; w = c.winfo_width() or 400; h = c.winfo_height() or 300
        cx, cy = w // 2, h // 2
        c.create_line(0, cy, w, cy, fill="#1f2a40")
        c.create_line(cx, 0, cx, h, fill="#1f2a40")
        for x in range(cx % 50, w, 50): c.create_line(x, cy - 4, x, cy + 4, fill="#1f2a40")
        for y in range(cy % 50, h, 50): c.create_line(cx - 4, y, cx + 4, y, fill="#1f2a40")
        c.create_text(12, 14, text=self.title, fill=FG_ACCENT, font=("Segoe UI", 11, "bold"), anchor="w")
    def _mapper(self) -> LinearMap:
        w = self.canvas.winfo_width() or 400
        if self._temp_domain:
            x_min, x_max = self._temp_domain
        else:
            x_min, x_max = -6e8, 1.5e9
        return LinearMap(x_min, x_max, 20, w - 20)

    def draw_planet_realistic(self, x: float, y: float, r_px=26, label: Optional[str]=None, hue="#1e40af"):
        m = self._mapper(); px = m.to_px(x); c = self.canvas
        for i in range(6, 0, -1):
            rr = r_px + i*3
            c.create_oval(px-rr, y-rr, px+rr, y+rr, outline="", fill=hue)
        for i in range(r_px, 5, -2):
            col = "#1e3a8a" if i%4 else "#0ea5e9"
            c.create_oval(px-i, y-i, px+i, y+i, outline="", fill=col)
        if label: c.create_text(px, y + r_px + 16, text=label, fill=FG_TEXT, font=("Segoe UI", 10))

    def draw_ship_capsule(self, x_center: float, length_m: float, y_mid: int, *, width_px=14, nose_forward=True):
        m = self._mapper(); c = self.canvas
        x1 = m.to_px(x_center - length_m/2); x2 = m.to_px(x_center + length_m/2)
        if x2 < x1: x1, x2 = x2, x1
        y1, y2 = y_mid - width_px, y_mid + width_px
        c.create_rectangle(x1, y1, x2, y2, outline="#a5b4fc", fill="#334155", width=2)
        nose_dx = 16 if nose_forward else -16
        c.create_polygon(x2, y1, x2 + nose_dx, y_mid, x2, y2, outline="#93c5fd", fill="#1f2937", width=2)
        cx = x2 - 26; cy = y_mid - 2
        c.create_oval(cx-6, cy-6, cx+6, cy+6, outline="#e0f2fe", fill="#0ea5e9", width=2)

    def draw_ship_ghost(self, x_center: float, length_m: float, y_mid: int, alpha: float=0.5):
        m = self._mapper(); c = self.canvas
        x1 = m.to_px(x_center - length_m/2); x2 = m.to_px(x_center + length_m/2)
        if x2 < x1: x1, x2 = x2, x1
        y1, y2 = y_mid - 14, y_mid + 14
        a = max(0, min(255, int(255*alpha)))
        col = f"#{a:02x}{a:02x}{a:02x}"
        c.create_rectangle(x1, y1, x2, y2, outline=col, fill="", width=2)

    def draw_flame(self, x_center: float, length_m: float, y_mid: int, power: float=1.0, flip=False):
        m = self._mapper(); c = self.canvas
        ship_tail = m.to_px(x_center - (length_m/2 if not flip else -length_m/2))
        y = y_mid
        for i in range(6):
            L = (22 + i*10) * (0.6 + 0.8*power)
            w = 6 + i*3
            x1 = ship_tail - L if not flip else ship_tail + L
            c.create_line(ship_tail, y, x1, y, fill="#9fb7ff", width=w)

    def draw_debris_poly(self, x: float, y_px: float, pts: List[Tuple[float,float]], theta: float, fill="#9fb2c9", outline="#e2e8f0", width=1):
        m = self._mapper(); px = m.to_px(x); cs, sn = math.cos(theta), math.sin(theta)
        pts_abs = []
        for dx, dy in pts:
            rx = dx * cs - dy * sn; ry = dx * sn + dy * cs
            pts_abs.extend([px + rx, y_px + ry])
        self.canvas.create_polygon(pts_abs, fill=fill, outline=outline, width=width)

    def badge(self, xy: Tuple[int,int], lines: List[Tuple[str,str,str]], big=False, pulse=0.0):
        x0, y0 = xy; c = self.canvas
        pad = 8; line_h = 20 if big else 18
        w = 0
        for lb, val, _ in lines:
            t = f"{lb} {val}"; w = max(w, (10 if big else 8) * max(len(t), 10))
        h = pad*2 + line_h*len(lines)
        if pulse > 0:
            a = int(40 + 80*abs(math.sin(pulse)))
            c.create_rectangle(x0-4, y0-4, x0+w+4, y0+h+4, outline=f"#{a:02x}{a:02x}{a:02x}", width=2)
        c.create_rectangle(x0, y0, x0+w, y0+h, fill="#0e1a33", outline="#213252")
        y = y0 + pad + 2
        for lb, val, col in lines:
            c.create_text(x0+10, y, text=lb, fill=FG_SUB, font=("Segoe UI", 10 if big else 9), anchor="w")
            c.create_text(x0+w-10, y, text=val, fill=col, font=("Consolas", 12 if big else 10, "bold"), anchor="e")
            y += line_h

# ---------- 민코프스키(간략) ----------
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

class MinkowskiInlineLC:
    def __init__(self, canvas: tk.Canvas, get_cluster_xs):
        self.canvas = canvas; self.get_cluster_xs = get_cluster_xs
    def _axes(self, mapper: MinkowskiMapper, beta: float):
        c = self.canvas; w = c.winfo_width() or 320; h = c.winfo_height() or 260
        ox, oy = mapper.to_px(0, 0)
        c.create_rectangle(1,1,w-1,h-1, outline="#213252")
        c.create_line(0, oy, w, oy, fill="#cbd5e1")
        c.create_line(ox, h, ox, 0, fill="#cbd5e1")
        p1 = mapper.to_px(mapper.dom_x_min, mapper.dom_x_min); p2 = mapper.to_px(mapper.dom_x_max, mapper.dom_x_max)
        c.create_line(*p1, *p2, fill="#60a5fa", dash=(2,2))
        p1 = mapper.to_px(mapper.dom_x_min, -mapper.dom_x_min); p2 = mapper.to_px(mapper.dom_x_max, -mapper.dom_x_max)
        c.create_line(*p1, *p2, fill="#60a5fa", dash=(2,2))
        if abs(beta)>1e-9:
            p1 = mapper.to_px(mapper.dom_x_min, beta*mapper.dom_x_min); p2 = mapper.to_px(mapper.dom_x_max, beta*mapper.dom_x_max)
            c.create_line(*p1,*p2, fill="#ef4444", width=2)
            p1 = mapper.to_px(beta*mapper.dom_ct_min, mapper.dom_ct_min); p2 = mapper.to_px(beta*mapper.dom_ct_max, mapper.dom_ct_max)
            c.create_line(*p1,*p2, fill="#ef4444", width=2)
    def render(self, v: float, center_x: float, tS: float, pair: Optional[Tuple[float,float]]):
        c = self.canvas; c.delete("all")
        if not pair: return
        xP, xQ = pair
        ct_now = sim.C * tS
        beta = v / sim.C; g = sim.gamma(beta) if abs(beta)>0 else 1.0
        if abs(beta) > 1e-12:
            boost = sim.LorentzBoost1D(beta=beta)
            ship_now = sim.Event(ct=ct_now, x=center_x)
            ct_p_now = boost.to_other(ship_now).ct
            xP_p = (xP/g) - (beta*ct_p_now); xQ_p = (xQ/g) - (beta*ct_p_now)
            Pp_S = boost.to_self(sim.Event(ct=ct_p_now, x=xP_p))
            Qp_S = boost.to_self(sim.Event(ct=ct_p_now, x=xQ_p))
            Lp = xQ_p - xP_p
        else:
            Pp_S = sim.Event(ct=ct_now, x=xP); Qp_S = sim.Event(ct=ct_now, x=xQ); Lp = xQ-xP
        x_min = min(0.0, xP, Pp_S.x, Qp_S.x) - 0.1*max(1.0, abs(xQ-xP))
        x_max = max(xQ, Pp_S.x, Qp_S.x) + 0.1*max(1.0, abs(xQ-xP))
        ct_min = 0.0; ct_max = max(ct_now, Pp_S.ct, Qp_S.ct)*1.1 if ct_now>0 else 1.0
        mapper = MinkowskiMapper(c, x_min, x_max, ct_min, ct_max)
        self._axes(mapper, beta)
        p1 = mapper.to_px(x_min, ct_now); p2 = mapper.to_px(x_max, ct_now)
        c.create_line(*p1, *p2, fill="#94a3b8", dash=(3,3))
        PP = mapper.to_px(xP, ct_now); QQ = mapper.to_px(xQ, ct_now)
        c.create_oval(PP[0]-3,PP[1]-3,PP[0]+3,PP[1]+3, fill="#111827", outline="#e5e7eb")
        c.create_oval(QQ[0]-3,QQ[1]-3,QQ[0]+3,QQ[1]+3, fill="#111827", outline="#e5e7eb")
        c.create_line(PP[0],PP[1],QQ[0],QQ[1], fill="#e5e7eb", width=2)
        Pp = mapper.to_px(Pp_S.x, Pp_S.ct); Qp = mapper.to_px(Qp_S.x, Qp_S.ct)
        c.create_line(Pp[0],Pp[1],Qp[0],Qp[1], fill="#fca5a5", width=2)
        c.create_oval(Pp[0]-3,Pp[1]-3,Pp[0]+3,Pp[1]+3, fill="#7f1d1d", outline="#fca5a5")
        c.create_oval(Qp[0]-3,Qp[1]-3,Qp[0]+3,Qp[1]+3, fill="#7f1d1d", outline="#fca5a5")
        L = xQ-xP
        c.create_text((PP[0]+QQ[0])//2, PP[1]-12, text=f"L = {si_str(L)} m", fill="#e5e7eb", font=("Consolas",9,"bold"))
        c.create_text((Pp[0]+Qp[0])//2, (Pp[1]+Qp[1])//2+12, text=f"L′ ≈ {si_str(Lp)} m (≈ L/γ)", fill="#fca5a5", font=("Consolas",9,"bold"))

class MinkowskiInlineTwins:
    def __init__(self, canvas: tk.Canvas, get_state):
        self.canvas = canvas; self.get_state = get_state
    def _axes(self, mapper: MinkowskiMapper):
        c = self.canvas; w = c.winfo_width() or 320; h = c.winfo_height() or 260
        ox, oy = mapper.to_px(0,0)
        c.create_rectangle(1,1,w-1,h-1, outline="#213252")
        c.create_line(0, oy, w, oy, fill="#cbd5e1"); c.create_line(ox, h, ox, 0, fill="#cbd5e1")
        p1 = mapper.to_px(-1e9, -1e9); p2 = mapper.to_px(+1e9, +1e9)
        c.create_line(*p1,*p2, fill="#60a5fa", dash=(2,2))
        p1 = mapper.to_px(-1e9, +1e9); p2 = mapper.to_px(+1e9, -1e9)
        c.create_line(*p1,*p2, fill="#60a5fa", dash=(2,2))
    def render(self):
        c = self.canvas; c.delete("all")
        st = self.get_state()
        if not st: return
        t = st["t"]; x = st["x"]; v = st["v"]; beta = v/sim.C
        x_turn = st["x_turn"]; t_turn = st["t_turn"]; t_orb_end = st["t_orb_end"]; t_meet = st["t_meet"]
        ct_now = sim.C * t
        x_min = min(0.0, -0.1*x_turn); x_max = max(x_turn*1.1, 0.0)
        ct_min = 0.0; ct_max = sim.C*max(t_meet*1.05, t*1.05 if t>0 else 1.0)
        mapper = MinkowskiMapper(c, x_min, x_max, ct_min, ct_max)
        self._axes(mapper)
        # 지구 세계선
        p1 = mapper.to_px(0.0, 0.0); p2 = mapper.to_px(0.0, ct_max)
        c.create_line(*p1,*p2, fill="#a5b4fc", width=2)
        # OUT
        p1 = mapper.to_px(0.0, 0.0); p2 = mapper.to_px(x_turn, sim.C*t_turn)
        c.create_line(*p1,*p2, fill="#22d3ee", width=2)
        # ORB
        p3 = mapper.to_px(x_turn, sim.C*t_turn); p4 = mapper.to_px(x_turn, sim.C*t_orb_end)
        c.create_line(*p3,*p4, fill="#10b981", width=2)
        # IN
        p5 = mapper.to_px(x_turn, sim.C*t_orb_end); p6 = mapper.to_px(0.0, sim.C*t_meet)
        c.create_line(*p5,*p6, fill="#22d3ee", width=2)
        # 현재점
        Pc = mapper.to_px(x, ct_now)
        c.create_oval(Pc[0]-3,Pc[1]-3,Pc[0]+3,Pc[1]+3, fill="#22d3ee", outline="#c7d2fe")
        # 정보
        c.create_text(16, 16, text=f"β≈{abs(beta):.2f}, γ≈{sim.gamma(abs(beta)):.3f}", fill="#c7d2fe", anchor="nw", font=("Consolas",10,"bold"))
        c.create_text(16, 36, text=f"turn@ x={si_str(x_turn)}m, t={t_turn:.2f}s", fill="#9fb7ff", anchor="nw", font=("Consolas",10))
        c.create_text(16, 56, text=f"meet@ t={t_meet:.2f}s", fill="#9fb7ff", anchor="nw", font=("Consolas",10))
        # 동시선
        p1 = mapper.to_px(x_min, ct_now); p2 = mapper.to_px(x_max, ct_now)
        c.create_line(*p1,*p2, fill="#94a3b8", dash=(3,3))

# ---------- FX들 ----------
class HyperspaceFX:
    """스타워즈풍 스트릭 + 링 + 중앙 플래시"""
    def __init__(self, canvas: tk.Canvas):
        self.canvas = canvas
        self.active = False
        self.t = 0.0
        self.duration = 1.0
        self.streaks = []; self.rings = []
    def start(self):
        self.active = True; self.t = 0.0; self.streaks.clear(); self.rings.clear()
        for _ in range(200):
            ang = random.uniform(-0.6*math.pi, 0.6*math.pi)
            spd = random.uniform(1000, 2400); l0  = random.uniform(4, 22)
            hue = random.choice(["#9fb7ff", "#b6f0ff", "#c8e4ff"])
            self.streaks.append([ang, spd, l0, hue])
        for r in [12, 24, 36]:
            self.rings.append([r, random.uniform(380, 560)])
    def step(self, dt: float):
        if not self.active: return
        self.t += dt
        if self.t >= self.duration: self.active = False
    def render(self):
        if not self.active: return
        c = self.canvas; w = c.winfo_width() or 800; h = c.winfo_height() or 320
        cx, cy = w//2, h//2
        prog = min(1.0, self.t / self.duration)
        ease = (1 - math.cos(math.pi * prog)) * 0.5
        for ang, spd, l0, hue in self.streaks:
            L = l0 + spd * ease
            x2 = cx + math.cos(ang) * L; y2 = cy + math.sin(ang) * L
            c.create_line(cx, cy, x2, y2, fill=hue, width=2)
        for i in range(len(self.rings)):
            r, vr = self.rings[i]; r2 = r + vr * ease; self.rings[i][0] = r2
            c.create_oval(cx-r2, cy-r2, cx+r2, cy+r2, outline="#9fb7ff", width=1)
        alpha = int(120 + 100*ease); col = f"#{alpha:02x}{alpha:02x}{alpha:02x}"
        r = int(12 + 120*ease); c.create_oval(cx-r, cy-r, cx+r, cy+r, outline="", fill=col)

class FlameFX:
    """위쪽 S에서 점프 중 불꽃을 그려줌(순간이동 느낌 강화)."""
    def __init__(self):
        self.active = False
        self.power = 0.0
        self.ghost: Optional[Tuple[float,float]] = None  # (x_center, L)
    def arm(self, x_center: float, L: float):
        self.active = True; self.power = 0.0; self.ghost = (x_center, L)
    def step(self, dt: float):
        if not self.active: return
        self.power = min(1.0, self.power + 2.0*dt)
    def stop(self):
        self.active = False
        self.power = 0.0

# ---------- Twins(B612) 컨트롤러 ----------
class TwinsB612Controller:
    """지구→B612(등속)→반바퀴 궤도(v_orb)→지구(등속) 왕복. proper time을 ∫dt/γ로 적분."""
    OUT, ORB, IN, DONE = range(4)
    def __init__(self, ship_L0=120.0):
        self.dt = 0.01
        self.L0_ = ship_L0
        self.reset_params()

    def reset_params(self):
        self.x_B612 = 1.35e9
        self.R_orb  = 1.2e7
        self.v_out  = 0.6*sim.C
        self.v_back = 0.6*sim.C
        self.v_orb  = 0.4*sim.C
        self.phase = self.OUT
        self.t = 0.0; self.x = 0.0; self.v = +self.v_out
        self.tau_ship = 0.0; self.tau_earth = 0.0
        self.theta = math.pi
        self.omega = self.v_orb / self.R_orb
        self.t_turn = None; self.t_orb_end = None; self.t_meet = None

    @property
    def beta(self): return self.v/sim.C if self.phase!=self.DONE else 0.0
    @property
    def gamma(self): return sim.gamma(abs(self.beta)) if abs(self.beta)>0 else 1.0
    @property
    def ship_center_x(self): return self.x
    @property
    def L0(self): return self.L0_
    @property
    def L_contracted(self): return self.L0_ / (self.gamma if self.gamma>0 else 1.0)

    def apply_beta(self, beta: float):
        beta = max(0.0, min(0.99, beta))
        if self.phase in (self.OUT, self.IN):
            sgn = 1 if self.v>=0 else -1
            if self.phase==self.OUT: sgn = 1
            elif self.phase==self.IN: sgn = -1
            self.v = sgn * (beta*sim.C)
            if sgn>0: self.v_out = abs(self.v)
            else: self.v_back = abs(self.v)

    def step(self):
        dt = self.dt
        self.t += dt; self.tau_earth += dt
        if self.phase == self.OUT:
            self.x += self.v_out*dt; self.v = +self.v_out
            self.tau_ship += dt/sim.gamma(self.v_out/sim.C)
            if self.x >= (self.x_B612 - self.R_orb):
                self.x = self.x_B612 - self.R_orb
                self.phase = self.ORB
                self.t_turn = self.t
                self.theta = math.pi
        elif self.phase == self.ORB:
            # 반바퀴: θ: π → 0
            self.v = 0.0
            self.theta = max(0.0, math.pi - self.omega*(self.t - self.t_turn))
            self.x = self.x_B612 + self.R_orb * math.cos(self.theta)
            self.tau_ship += dt/sim.gamma(self.v_orb/sim.C)
            if self.theta <= 0.0:
                self.phase = self.IN
                self.v = -self.v_back
                self.t_orb_end = self.t
        elif self.phase == self.IN:
            self.x += (-self.v_back)*dt; self.v = -self.v_back
            self.tau_ship += dt/sim.gamma(self.v_back/sim.C)
            if self.x <= 0.0:
                self.x = 0.0
                self.phase = self.DONE
                self.t_meet = self.t
        else:
            self.v = 0.0

    def mko_state(self):
        x_turn = self.x_B612
        t_turn = self.t_turn or (x_turn/self.v_out)
        t_orb_end = self.t_orb_end or (t_turn + math.pi*self.R_orb/self.v_orb)
        t_meet = self.t_meet or (t_orb_end + x_turn/self.v_back)
        return {"t": self.t, "x": self.x, "v": self.v,
                "x_turn": x_turn, "t_turn": t_turn, "t_orb_end": t_orb_end, "t_meet": t_meet}

# ---------- 메인 앱 ----------
class SRApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self._style()
        self.root.title(APP_TITLE)
        self.root.geometry("1380x980")
        self.root.minsize(1120, 800)
        self.root.configure(bg=BG_DARK)

        # LC 시나리오(기본)
        self.scn = sim.LengthContractionScenario(sim.LengthContractionParams(
            train_rest_length=120.0, train_speed=0.6 * sim.C,
            laser_direction=+1, allow_sub_c_demo=False, demo_speed=sim.C))

        # 모드
        self.mode = tk.StringVar(value="LC")  # LC or TWINS
        self.twins = TwinsB612Controller(ship_L0=120.0)

        # 군집
        self.clusters: List[List[Debris]] = self._generate_clusters()

        # UI
        self._build_sidebar()
        self._build_main()

        # 인라인 민코프스키
        self.minko_lc = MinkowskiInlineLC(self.canvas_M, self._active_cluster_minmax)
        self.minko_tw = MinkowskiInlineTwins(self.canvas_M, self.twins.mko_state)

        # FX
        self.hyper_fx = HyperspaceFX(self.canvas_Sp)
        self.flame_fx = FlameFX()

        # 상태
        self.running = False
        self.base_dt = self.scn.sim.dt
        self._bind_events()
        self.render_all()

    # ----- 데이터 -----
    def _generate_clusters(self) -> List[List[Debris]]:
        clusters = []
        specs = [
            ( 8.0e7,  14, 2.6e7, (-120,  +40)),
            ( 2.2e8,  18, 3.2e7, (-60,  +120)),
            ( 4.1e8,  20, 4.0e7, (-160, +80)),
            ( 7.3e8,  16, 5.2e7, (-90,  +150)),
            ( 1.20e9, 14, 6.0e7, (-140, +60)),
        ]
        for idx, (center, n, gap, (ymin, ymax)) in enumerate(specs):
            base = center - (n//2)*gap
            xs = [base + i*gap + random.uniform(-0.28,0.28)*gap for i in range(n)]
            col = _PALETTES[idx % len(_PALETTES)]
            cl = [Debris(x, random.randint(ymin, ymax), col) for x in xs]
            clusters.append(cl)
        return clusters

    # ----- 스타일/UI -----
    def _style(self):
        style = ttk.Style()
        try: style.theme_use("clam")
        except Exception: pass
        style.configure("Card.TFrame", background=BG_CARD)
        style.configure("TLabel", background=BG_DARK, foreground=FG_TEXT)
        style.configure("Accent.TButton", padding=8, font=("Segoe UI", 10, "bold"),
                        background=ACCENT, foreground="white")
        style.map("Accent.TButton", background=[("active", "#3d36c9"), ("pressed", "#332fb3")])
        style.configure("TScale", troughcolor="#111827", background=BG_DARK)
        style.configure("Combo.TMenubutton", background=BG_DARK, foreground=FG_TEXT)

    def _build_sidebar(self):
        sb = ttk.Frame(self.root, style="Card.TFrame"); sb.grid(row=0, column=0, sticky="nsew")
        tk.Label(sb, text=APP_TITLE, bg=BG_CARD, fg=FG_TEXT, font=("Segoe UI", 13, "bold"),
                 anchor="w").pack(fill="x", padx=PAD, pady=(PAD, 8))

        # 모드 배지
        self.lbl_mode = tk.Label(sb, text="모드: 길이수축 (LC)", bg=BG_CARD, fg=OK, anchor="w", font=("Segoe UI", 10, "bold"))
        self.lbl_mode.pack(fill="x", padx=PAD, pady=(0,6))

        # β
        tk.Label(sb, text="β (v/c)", bg=BG_CARD, fg=FG_SUB, anchor="w").pack(fill="x", padx=PAD)
        self.beta_var = tk.DoubleVar(value=self.scn.params.train_speed / sim.C)
        row = tk.Frame(sb, bg=BG_CARD); row.pack(fill="x", padx=PAD, pady=(2,2))
        self.beta_entry = tk.Entry(row, textvariable=self.beta_var, width=8); self.beta_entry.pack(side="right")
        self.beta_entry.bind("<Return>", lambda e: self.apply_beta())
        self.beta_scale = ttk.Scale(sb, from_=0.0, to=0.99, orient=tk.HORIZONTAL,
                                    variable=self.beta_var, command=self.on_beta_change)
        self.beta_scale.pack(fill="x", padx=PAD, pady=(2, 8))
        self.gamma_label = tk.Label(sb, text=f"γ = {sim.gamma(self.beta_var.get()):.3f}",
                                    bg=BG_CARD, fg=FG_ACCENT, font=("Consolas", 11, "bold"))
        self.gamma_label.pack(fill="x", padx=PAD, pady=(6, 12))

        # 컨트롤
        ctr = tk.Frame(sb, bg=BG_CARD); ctr.pack(fill="x", padx=PAD, pady=(0, 8))
        self.btn_toggle = ttk.Button(ctr, text="▶ 재생", style="Accent.TButton", command=self.toggle_play)
        self.btn_step   = ttk.Button(ctr, text="⏭ 한 프레임", style="Accent.TButton", command=self.step_once)
        self.btn_reset  = ttk.Button(ctr, text="⏲ 초기화", style="Accent.TButton", command=self.reset)
        self.btn_toggle.grid(row=0, column=0, padx=(0,6)); self.btn_step.grid(row=0, column=1, padx=(0,6)); self.btn_reset.grid(row=0, column=2, padx=(0,6))

        # 시간 배율
        tk.Label(sb, text="시간 배율 (재생 속도)", bg=BG_CARD, fg=FG_SUB, anchor="w").pack(fill="x", padx=PAD)
        self.speed_var = tk.DoubleVar(value=0.6)
        ttk.Scale(sb, from_=0.05, to=5.0, orient=tk.HORIZONTAL, variable=self.speed_var)\
            .pack(fill="x", padx=PAD, pady=(2, 10))

        # 군집 선택
        tk.Label(sb, text="측정 군집 선택", bg=BG_CARD, fg=FG_SUB, anchor="w").pack(fill="x", padx=PAD)
        self.cluster_combo = ttk.Combobox(sb, values=[f"군집 {i+1}" for i in range(len(self.clusters))], state="readonly")
        self.cluster_combo.current(0); self.cluster_combo.pack(fill="x", padx=PAD, pady=(2, 6))
        self.cluster_combo.bind("<<ComboboxSelected>>", lambda e: self.render_all())

        # 민코프스키 (인라인)
        self.btn_minko = ttk.Button(sb, text="민코프스키 공간 보기", style="Accent.TButton", command=self.toggle_minkowski)
        self.btn_minko.pack(fill="x", padx=PAD, pady=(6, 6))
        self.minko_cont = ttk.Frame(sb, style="Card.TFrame"); self.minko_cont.pack_propagate(False)
        self.minko_cont.configure(height=300)
        self.minko_visible = False
        self.canvas_M = tk.Canvas(self.minko_cont, bg=BG_CANVAS, highlightthickness=1, highlightbackground="#1f2937")
        self.canvas_M.pack(fill="both", expand=True, padx=PAD, pady=(0, PAD))

        # 하이퍼스페이스 점프
        ttk.Separator(sb, orient="horizontal").pack(fill="x", padx=PAD, pady=(4,6))
        tk.Label(sb, text="B612 쌍둥이 역설", bg=BG_CARD, fg=FG_SUB, anchor="w").pack(fill="x", padx=PAD)
        self.btn_jump = ttk.Button(sb, text="하이퍼스페이스 점프 ✦", style="Accent.TButton", command=self.trigger_jump)
        self.btn_jump.pack(fill="x", padx=PAD, pady=(4, 10))

    def _build_main(self):
        self.root.grid_columnconfigure(0, minsize=SIDEBAR_WIDTH)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        self.main_area = tk.Frame(self.root, bg=BG_DARK)
        self.main_area.grid(row=0, column=1, sticky="nsew")
        for child in self.main_area.winfo_children(): child.destroy()
        self.main_area.grid_columnconfigure(0, weight=1)
        self.main_area.grid_rowconfigure(0, weight=1)
        self.paned = ttk.Panedwindow(self.main_area, orient=tk.VERTICAL)
        self.paned.grid(row=0, column=0, sticky="nsew", padx=PAD, pady=PAD)
        # S
        top = tk.Frame(self.paned, bg=BG_DARK); top.grid_columnconfigure(0, weight=1); top.grid_rowconfigure(1, weight=1)
        tk.Label(top, text="1) 지구 관측자 좌표계 (S)", bg=BG_DARK, fg=FG_ACCENT, font=("Segoe UI",11,"bold"), anchor="w")\
            .grid(row=0, column=0, sticky="ew", padx=PAD, pady=(PAD, 4))
        self.canvas_S = tk.Canvas(top, bg=BG_CANVAS, highlightthickness=0)
        self.canvas_S.grid(row=1, column=0, sticky="nsew", padx=PAD, pady=(0,PAD))
        self.view_S = ViewPane(self.canvas_S, "지구 프레임 S")
        # S'
        mid = tk.Frame(self.paned, bg=BG_DARK); mid.grid_columnconfigure(0, weight=1); mid.grid_rowconfigure(1, weight=1)
        tk.Label(mid, text="2) 우주선 관찰자 좌표계 (S')", bg=BG_DARK, fg=FG_ACCENT, font=("Segoe UI",11,"bold"), anchor="w")\
            .grid(row=0, column=0, sticky="ew", padx=PAD, pady=(PAD, 4))
        self.canvas_Sp = tk.Canvas(mid, bg=BG_CANVAS, highlightthickness=0)
        self.canvas_Sp.grid(row=1, column=0, sticky="nsew", padx=PAD, pady=(0, PAD))
        self.view_Sp = ViewPane(self.canvas_Sp, "우주선 프레임 S'")
        # 궤도 미니맵
        self.orbit_map = tk.Canvas(mid, bg="#09101c", height=140, highlightthickness=0)
        self.orbit_map.grid(row=2, column=0, sticky="ew", padx=PAD, pady=(0, PAD))
        self.paned.add(top, weight=1); self.paned.add(mid, weight=1)

    # ----- 이벤트 -----
    def _bind_events(self):
        self.canvas_S.bind("<Configure>", lambda e: self.render_all())
        self.canvas_Sp.bind("<Configure>", lambda e: self.render_all())
        self.canvas_M.bind("<Configure>", lambda e: self.render_M() if self.minko_visible else None)
        self.root.bind("<space>", lambda e: self.toggle_play())

    # ----- 모드/속도/점프 -----
    def on_beta_change(self, _evt=None):
        beta = max(0.0, min(0.99, float(self.beta_var.get())))
        self.beta_var.set(beta); self.gamma_label.config(text=f"γ = {sim.gamma(beta):.3f}")
        if self.mode.get()=="LC":
            self.scn.train.v = beta * sim.C
        else:
            self.twins.apply_beta(beta)
        self.render_all()
    def apply_beta(self):
        try: _ = float(self.beta_var.get())
        except Exception: return
        self.on_beta_change()

    def toggle_play(self):
        self.running = not self.running
        self.btn_toggle.config(text="⏸ 일시정지" if self.running else "▶ 재생")
        if self.running: self._tick()

    def step_once(self):
        was = self.running; self.running = False; self._tick_once(); self.running = was

    def reset(self):
        self.mode.set("LC"); self.lbl_mode.config(text="모드: 길이수축 (LC)", fg=OK)
        self.scn.sim.t = 0.0; self.scn.train.center_x = -200.0
        self.scn.train.v = self.scn.params.train_speed
        self.scn.ground_observer.state = sim.State(x=0.0, v=0.0, t=0.0, tau=0.0)
        self.scn.train_observer.state  = sim.State(x=self.scn.train.center_x, v=self.scn.train.v, t=0.0, tau=0.0)
        self.twins.reset_params()
        self.hyper_fx.active = False; self.hyper_fx.t = 0.0
        self.flame_fx.stop()
        self.render_all()

    def trigger_jump(self):
        if self.mode.get()=="LC":
            # 위쪽 S: 불꽃 + 잔상
            g = sim.gamma(self.scn.train.v/sim.C) if abs(self.scn.train.v)>0 else 1.0
            L = self.scn.train.rest_length/g
            self.flame_fx.arm(self.scn.train.center_x, L)
            # 아래쪽 S': 스타워즈 스트릭
            self.hyper_fx.start()

    def _perform_jump_if_needed(self):
        if self.mode.get()=="LC" and (not self.hyper_fx.active) and self.hyper_fx.t>0.0:
            # 점프 종료 → TWINS 전환
            self.mode.set("TWINS"); self.lbl_mode.config(text="모드: 쌍둥이 (B612 미션)", fg=FG_ACCENT)
            # 시계 리셋 & 출발
            self.twins.reset_params()
            self.beta_var.set(self.scn.train.v/sim.C)
            self.hyper_fx.t = 0.0
            self.flame_fx.stop()

    # ----- 루프 -----
    def _tick(self):
        if not self.running: return
        self._tick_once(); self.root.after(16, self._tick)

    def _tick_once(self):
        speed = float(self.speed_var.get())
        dt = max(1e-5, min(0.05, self.base_dt * speed))
        if self.mode.get()=="LC":
            self.scn.sim.dt = dt
            for _ in range(2):
                self.scn.sim.step()
            if self.hyper_fx.active: self.hyper_fx.step(2*dt)
            if self.flame_fx.active: self.flame_fx.step(2*dt)
            self._perform_jump_if_needed()
        else:
            self.twins.dt = dt
            for _ in range(2):
                self.twins.step()
        self.render_all()

    # ----- 렌더 -----
    def _active_cluster(self) -> List[Debris]:
        idx = max(0, min(len(self.clusters)-1, self.cluster_combo.current()))
        return self.clusters[idx]
    def _active_cluster_minmax(self):
        cl = self._active_cluster()
        if not cl: return None
        xs = [d.x for d in cl]
        return (min(xs), max(xs))
    def _debris_y(self, base_y: int, tS: float, d: Debris) -> int:
        return int(base_y + d.y_base_px + d.wiggle_a * math.sin(d.wiggle_w * tS + 0.5))

    def render_all(self):
        self.render_S(); self.render_Sp()
        if self.minko_visible: self.render_M()
        self.render_orbit_map()

    def render_S(self):
        self.view_S.clear()
        h = self.canvas_S.winfo_height() or 300; y = h//2
        if self.mode.get()=="LC":
            self.view_S.clear_domain()
            v = self.scn.train.v; g = sim.gamma(v/sim.C) if abs(v)>0 else 1.0
            L0 = self.scn.train.rest_length; L = L0/g
            self.view_S.draw_axes()
            self.view_S.draw_planet_realistic(0.0, y, r_px=28, label="지구(정지)")
            # 잔상(점프 직전 위치)
            if self.flame_fx.active and self.flame_fx.ghost:
                gx, gL = self.flame_fx.ghost
                self.view_S.draw_ship_ghost(gx, gL, y, alpha=0.6)
            self.view_S.draw_ship_capsule(self.scn.train.center_x, L, y, nose_forward=(v>=0))
            if self.flame_fx.active:
                self.view_S.draw_flame(self.scn.train.center_x, L, y, power=self.flame_fx.power, flip=False)

            # 파편
            tS = self.scn.sim.t; sel = set(self._active_cluster())
            for cluster in self.clusters:
                for d in cluster:
                    y_px = self._debris_y(y, tS, d)
                    if d in sel:   self.view_S.draw_debris_poly(d.x, y_px, d.shape_pts, d.theta, fill=d.fill, outline=d.outline, width=2)
                    else:          self.view_S.draw_debris_poly(d.x, y_px, d.shape_pts, d.theta, fill="#0b1322", outline="#475569", width=1)
            # 배지
            self.view_S.badge((12, 20), [
                ("β", f"{v/sim.C:.3f}", FG_ACCENT),
                ("γ", f"{g:.3f}", FG_ACCENT),
                ("L(수축)", f"{si_str(L)} m", "#c7d2fe"),
            ], pulse=self.hyper_fx.t if self.hyper_fx.active else 0.0)

        else:
            # Twins
            # S에서 B612 보여주기
            self.view_S.clear_domain()
            v = self.twins.v; g = self.twins.gamma; L = self.twins.L_contracted
            self.view_S.draw_axes()
            self.view_S.draw_planet_realistic(0.0, y, r_px=28, label="지구(정지)")
            self.view_S.draw_planet_realistic(self.twins.x_B612, y, r_px=22, label="B612", hue="#7e22ce")
            self.view_S.draw_ship_capsule(self.twins.x, L, y, nose_forward=(v>=0))
            # 파편(배경)
            tS = self.twins.t; sel = set(self._active_cluster())
            for cluster in self.clusters:
                for d in cluster:
                    y_px = self._debris_y(y, tS, d)
                    if d in sel:   self.view_S.draw_debris_poly(d.x, y_px, d.shape_pts, d.theta, fill=d.fill, outline=d.outline, width=2)
                    else:          self.view_S.draw_debris_poly(d.x, y_px, d.shape_pts, d.theta, fill="#0b1322", outline="#475569", width=1)
            # 시계/배지(고유시간 강조)
            self.view_S.badge((12, 20), [
                ("β", f"{abs(v)/sim.C:.3f}", FG_ACCENT),
                ("γ", f"{g:.3f}", FG_ACCENT),
                ("τ_지구", f"{self.twins.tau_earth:.2f} s", "#bbf7d0"),
                ("τ_여행자", f"{self.twins.tau_ship:.2f} s", "#fca5a5"),
                ("Δτ", f"{(self.twins.tau_earth - self.twins.tau_ship):.2f} s", "#fde68a"),
            ], big=True)

    def render_Sp(self):
        self.view_Sp.clear()
        h = self.canvas_Sp.winfo_height() or 300; y = h//2
        if self.mode.get()=="LC":
            self.view_Sp.clear_domain()
            self.view_Sp.draw_axes()
            L0 = self.scn.train.rest_length; self.view_Sp.draw_ship_capsule(0.0, L0, y, nose_forward=False)
            beta = self.scn.train.v/sim.C; tS = self.scn.sim.t
            # 점프 중엔 하단 화면은 "순간이동 느낌" → FX만 그리고 나머지는 최소 표시
            if self.hyper_fx.active:
                self.hyper_fx.render()
                self.view_Sp.badge((12, 20), [("β", f"{beta:.3f}", FG_ACCENT), ("γ", f"{sim.gamma(beta):.3f}", FG_ACCENT), ("L0", f"{si_str(L0)} m", "#c7d2fe")])
                return

            boost = sim.LorentzBoost1D(beta=beta) if abs(beta)>1e-12 else None
            e_earth = sim.Event(ct=sim.C*tS, x=0.0)
            x_earth_p = boost.to_other(e_earth).x if boost else 0.0
            self.view_Sp.draw_planet_realistic(x_earth_p, y, r_px=24, label="지구(운동)")
            # 파편
            sel = set(self._active_cluster())
            if boost:
                g = sim.gamma(beta)
                ship_now = sim.Event(ct=sim.C*tS, x=self.scn.train.center_x)
                ct_p_now = boost.to_other(ship_now).ct
                for cluster in self.clusters:
                    for d in cluster:
                        x_p = (d.x/g) - (beta*ct_p_now)
                        y_px = self._debris_y(y, tS, d)
                        if d in sel:   self.view_Sp.draw_debris_poly(x_p, y_px, d.shape_pts, d.theta, fill=d.fill, outline=d.outline, width=2)
                        else:          self.view_Sp.draw_debris_poly(x_p, y_px, d.shape_pts, d.theta, fill="#0b1322", outline="#334155", width=1)
            else:
                for cluster in self.clusters:
                    for d in cluster:
                        y_px = self._debris_y(y, tS, d)
                        if d in sel:   self.view_Sp.draw_debris_poly(d.x, y_px, d.shape_pts, d.theta, fill=d.fill, outline=d.outline, width=2)
                        else:          self.view_Sp.draw_debris_poly(d.x, y_px, d.shape_pts, d.theta, fill="#0b1322", outline="#334155", width=1)
            self.view_Sp.badge((12, 20), [("β", f"{beta:.3f}", FG_ACCENT), ("γ", f"{sim.gamma(beta):.3f}", FG_ACCENT), ("L0", f"{si_str(L0)} m", "#c7d2fe")])

        else:
            # Twins S'
            beta = self.twins.beta; tS = self.twins.t
            boost = sim.LorentzBoost1D(beta=beta) if abs(beta)>1e-12 else None
            # 동적 도메인: 지구와 B612가 항상 시야에
            if boost:
                e_earth = sim.Event(ct=sim.C*tS, x=0.0)
                e_b = sim.Event(ct=sim.C*tS, x=self.twins.x_B612)
                x_earth_p = boost.to_other(e_earth).x
                x_b_p = boost.to_other(e_b).x
            else:
                x_earth_p = -self.twins.x
                x_b_p = self.twins.x_B612 - self.twins.x
            xmin = min(x_earth_p, x_b_p) - 2e8
            xmax = max(x_earth_p, x_b_p) + 2e8
            self.view_Sp.set_temp_domain(xmin, xmax)

            self.view_Sp.draw_axes()
            L0 = self.twins.L0; self.view_Sp.draw_ship_capsule(0.0, L0, y, nose_forward=False)
            self.view_Sp.draw_planet_realistic(x_earth_p, y, r_px=24, label="지구(운동)")
            self.view_Sp.draw_planet_realistic(x_b_p, y, r_px=20, label="B612(운동)", hue="#7e22ce")
            # 파편
            sel = set(self._active_cluster())
            if boost:
                g = sim.gamma(beta)
                ship_now = sim.Event(ct=sim.C*tS, x=self.twins.x)
                ct_p_now = boost.to_other(ship_now).ct
                for cluster in self.clusters:
                    for d in cluster:
                        x_p = (d.x/g) - (beta*ct_p_now)
                        y_px = self._debris_y(y, tS, d)
                        if d in sel:   self.view_Sp.draw_debris_poly(x_p, y_px, d.shape_pts, d.theta, fill=d.fill, outline=d.outline, width=2)
                        else:          self.view_Sp.draw_debris_poly(x_p, y_px, d.shape_pts, d.theta, fill="#0b1322", outline="#334155", width=1)
            else:
                for cluster in self.clusters:
                    for d in cluster:
                        y_px = self._debris_y(y, tS, d)
                        if d in sel:   self.view_Sp.draw_debris_poly(d.x, y_px, d.shape_pts, d.theta, fill=d.fill, outline=d.outline, width=2)
                        else:          self.view_Sp.draw_debris_poly(d.x, y_px, d.shape_pts, d.theta, fill="#0b1322", outline="#334155", width=1)
            self.view_Sp.badge((12, 20), [("β", f"{beta:.3f}", FG_ACCENT), ("γ", f"{self.twins.gamma:.3f}", FG_ACCENT), ("L0", f"{si_str(L0)} m", "#c7d2fe")])
            self.view_Sp.clear_domain()  # 한 프레임 완료 후 원복

    def toggle_minkowski(self):
        self.minko_visible = not self.minko_visible
        if self.minko_visible:
            self.minko_cont.pack(fill="x", padx=PAD, pady=(0, PAD))
            self.btn_minko.config(text="민코프스키 닫기")
            self.render_M()
        else:
            self.minko_cont.forget()
            self.btn_minko.config(text="민코프스키 공간 보기")

    def render_M(self):
        if self.mode.get()=="LC":
            self.minko_lc.render(self.scn.train.v, self.scn.train.center_x, self.scn.sim.t, self._active_cluster_minmax())
        else:
            self.minko_tw.render()

    def render_orbit_map(self):
        c = self.orbit_map; c.delete("all")
        w = c.winfo_width() or 600; h = c.winfo_height() or 140
        cx, cy = w//2, h//2
        # 별
        for _ in range(60):
            r = random.choice([1,1,2]); x = random.randint(0,w); y = random.randint(0,h)
            c.create_oval(x-r,y-r,x+r,y+r, fill="#9fb7ff", outline="")
        if self.mode.get()=="TWINS":
            Rpx = int(min(w,h)*0.35)
            c.create_oval(cx-Rpx, cy-Rpx, cx+Rpx, cy+Rpx, outline="#4338ca", width=2)
            c.create_oval(cx-10, cy-10, cx+10, cy+10, fill="#7e22ce", outline="")
            c.create_text(12, 12, text="B612 궤도(반바퀴)", fill="#c7d2fe", anchor="nw", font=("Segoe UI", 10, "bold"))
            theta = self.twins.theta
            if self.twins.phase==self.twins.OUT: theta = math.pi
            elif self.twins.phase==self.twins.IN: theta = 0.0
            x = cx + Rpx * math.cos(theta); y = cy + Rpx * math.sin(theta)
            c.create_oval(x-6, y-6, x+6, y+6, fill="#22d3ee", outline="#a5b4fc", width=2)
            c.create_arc(cx-Rpx-6, cy-Rpx-6, cx+Rpx+6, cy+Rpx+6,
                         start=180, extent=(180 - theta*180/math.pi), outline="#a5b4fc", width=3, style="arc")

# ---------- 엔트리 ----------
def main():
    root = tk.Tk()
    app = SRApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()