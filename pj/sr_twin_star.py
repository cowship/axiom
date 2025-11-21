"""
Twins-to-Star Scenario (finite accel/decel → stop at star → turn → return)
- Uses user's sr_sim.py core (Event, State, Observer, Simulation, Recorder, C, gamma)
- Coordinate-acceleration model (simple, educational): dv = a * dt, clamp |v|<C
- Proper time integrates via d tau = dt / gamma(v/C) (as in Observer.update)
- Segments: accel → cruise → decel(to stop at star) → dwell → accel back → cruise → decel to stop at Earth
- Star is fixed in S at +D (m), Earth at 0.

Run:
    python sr_twins_star.py
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple
import math
import sr_sim as sim

# ------------------------------
# Parameters
# ------------------------------
@dataclass
class TwinsStarParams:
    star_distance_m: float = 5.0e10       # 50 billion m (~0.33 AU) as a small demo
    v_cruise: float = 0.8 * sim.C        # target cruise speed
    accel_m_s2: float = 5.0              # coordinate acceleration magnitude (m/s^2)
    dwell_s: float = 0.0                 # pause at star (S-time) before return
    dt: float = 0.01                     # sim step (s)

# ------------------------------
# Scenario
# ------------------------------
class TwinsToStarScenario:
    """Traveler departs Earth (x=0), goes to star at x=+D, stops, turns, returns to Earth, stops.
    Earth stays at x=0; star fixed at +D in S.
    """
    def __init__(self, params: TwinsStarParams):
        self.p = params
        self.frame = sim.InertialFrame1D("S")
        # Observers
        self.earth = sim.Observer(self.frame, sim.State(x=0.0, v=0.0, t=0.0, tau=0.0), label="earth")
        self.trav = sim.Observer(self.frame, sim.State(x=0.0, v=0.0, t=0.0, tau=0.0), label="traveler")
        # Engine
        self.sim = sim.Simulation(frame=self.frame,
                                  observers=[self.earth, self.trav],
                                  dt=self.p.dt)
        self.rec = sim.Recorder()
        self.sim.recorders.append(self.rec)

        # Star position in S
        self.star_x = self.p.star_distance_m
        # Internal phase state
        self.phase = "accel_out"  # accel_out, cruise_out, decel_to_star, dwell, accel_back, cruise_back, decel_to_earth, done
        self.dwell_left = self.p.dwell_s

    # --------------- helpers ---------------
    @staticmethod
    def _sgn(x: float) -> float:
        return -1.0 if x < 0.0 else (1.0 if x > 0.0 else 0.0)

    def _update_trav(self, dt: float):
        s = self.trav.state
        a = self.p.accel_m_s2
        vc = self.p.v_cruise
        # Phase machine
        if self.phase == "accel_out":
            # accelerate +x until |v| reaches v_cruise
            s.v = min(vc, s.v + a*dt)
            # If close to star braking distance, switch to decel phase
            if self._needs_decel_to_stop_at(self.star_x):
                self.phase = "decel_to_star"
        elif self.phase == "cruise_out":
            s.v = self._towards_target_speed(s.v, +vc, a, dt)
            if self._needs_decel_to_stop_at(self.star_x):
                self.phase = "decel_to_star"
        elif self.phase == "decel_to_star":
            # brake so as to stop exactly at star
            need = self._brake_sign_to_stop_at(self.star_x)
            s.v += need * a * dt  # need is -1 for braking when moving +x
            # Clamp sign change
            if self._passed_stop_at(self.star_x):
                s.v = 0.0
                s.x = self.star_x
                self.phase = "dwell" if self.dwell_left > 0 else "accel_back"
        elif self.phase == "dwell":
            s.v = 0.0
            self.dwell_left = max(0.0, self.dwell_left - dt)
            if self.dwell_left <= 0.0:
                self.phase = "accel_back"
        elif self.phase == "accel_back":
            # accelerate -x until reaching -v_cruise
            s.v = max(-vc, s.v - a*dt)
            if self._needs_decel_to_stop_at(0.0):
                self.phase = "decel_to_earth"
        elif self.phase == "cruise_back":
            s.v = self._towards_target_speed(s.v, -vc, a, dt)
            if self._needs_decel_to_stop_at(0.0):
                self.phase = "decel_to_earth"
        elif self.phase == "decel_to_earth":
            need = self._brake_sign_to_stop_at(0.0)
            s.v += need * a * dt  # need = +1 for braking when moving -x
            if self._passed_stop_at(0.0):
                s.v = 0.0
                s.x = 0.0
                self.phase = "done"
        elif self.phase == "done":
            s.v = 0.0
        # Position/clock updates (S-time; proper time via gamma)
        s.t += dt
        s.x += s.v * dt
        g = sim.gamma(s.v / sim.C) if abs(s.v) > 0 else 1.0
        s.tau += dt / g

    def _towards_target_speed(self, v: float, target: float, a: float, dt: float) -> float:
        if abs(target - v) <= a*dt:
            return target
        return v + math.copysign(a*dt, target - v)

    def _needs_decel_to_stop_at(self, x_stop: float) -> bool:
        """Check if we must start braking now to stop at x_stop under max decel a.
        Using v^2 = v0^2 + 2 a s  → stopping distance s = v^2 / (2 a).
        Works in S using coordinate acceleration (educational approximation).
        """
        s = self.trav.state
        a = max(1e-12, self.p.accel_m_s2)
        if s.v == 0.0:
            return False
        dist = x_stop - s.x
        dir_ok = (dist > 0 and s.v > 0) or (dist < 0 and s.v < 0)
        if not dir_ok:
            return False
        s_need = (s.v*s.v) / (2.0*a)
        return abs(dist) <= s_need

    def _brake_sign_to_stop_at(self, x_stop: float) -> float:
        s = self.trav.state
        dist = x_stop - s.x
        # If moving +x and need to stop ahead, accel negative; opposite for -x
        return -self._sgn(s.v) if dist * s.v > 0 else 0.0

    def _passed_stop_at(self, x_stop: float) -> bool:
        s = self.trav.state
        # detect overshoot with sign change or passing position
        if self.phase == "decel_to_star":
            return s.x >= x_stop and s.v <= 0.0
        if self.phase == "decel_to_earth":
            return s.x <= x_stop and s.v >= 0.0
        return False

    # ---------------- run -----------------
    def run(self, t_max: float = 1e7):
        # Bootstrap: accelerate until cruise if far from braking; otherwise go straight to decel.
        while self.phase != "done" and self.sim.t < t_max:
            # If we are accelerating but already at cruise and far from braking, enter cruise phases
            if self.phase == "accel_out" and abs(self.trav.state.v - self.p.v_cruise) < 1e-6 and not self._needs_decel_to_stop_at(self.star_x):
                self.phase = "cruise_out"
            if self.phase == "accel_back" and abs(self.trav.state.v + self.p.v_cruise) < 1e-6 and not self._needs_decel_to_stop_at(0.0):
                self.phase = "cruise_back"

            # Step traveler manually; earth via standard update
            dt = self.sim.dt
            self._update_trav(dt)
            self.earth.update(dt)
            # Record both
            for r in self.sim.recorders:
                r.capture(self.sim)
            # Advance global time
            self.sim.t += dt

        # Summary
        return {
            "t_earth": self.earth.state.t,
            "tau_earth": self.earth.state.tau,
            "t_trav": self.trav.state.t,
            "tau_trav": self.trav.state.tau,
            "phase": self.phase,
            "samples": self.rec.worldline_samples,
        }

# ------------------------------
# Demo
# ------------------------------
if __name__ == "__main__":
    p = TwinsStarParams(
        star_distance_m=3.0e9,   # 3 billion m (about 10 light-seconds) → quick demo
        v_cruise=0.6 * sim.C,
        accel_m_s2=10.0,
        dwell_s=0.0,
        dt=0.005,
    )
    sc = TwinsToStarScenario(p)
    result = sc.run()
    print("Phase:", result["phase"])  # done
    print(f"Earth proper time τ_E = {result['tau_earth']:.3f} s")
    print(f"Traveler proper time τ_T = {result['tau_trav']:.3f} s")
    d_tau = result['tau_earth'] - result['tau_trav']
    print(f"Δτ = τ_E - τ_T = {d_tau:.3f} s")
