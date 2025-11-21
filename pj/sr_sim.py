# sr_sim.py — Slim core for Length Contraction & Twins scenarios
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Callable, Protocol, Dict
import math

# ==============================
# 0) 상수/유틸
# ==============================
C = 3000.0  # 광속 (m/s)

def gamma(beta: float) -> float:
    """로렌츠 감마: 1/sqrt(1 - beta^2) with |beta|<1"""
    if abs(beta) >= 1.0:
        raise ValueError("beta must satisfy |beta|<1.")
    return 1.0 / math.sqrt(1.0 - beta * beta)
def clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(value, max_value))

# ==============================
# 1) 사건·상태·변환
# ==============================
@dataclass
class Event:
    ct: float
    x: float

@dataclass
class State:
    """1+1D 상태: x, v, t(좌표시간), tau(고유시간)"""
    x: float = 0.0
    v: float = 0.0
    t: float = 0.0
    tau: float = 0.0

class Transform(Protocol):
    def to_self(self, e: Event) -> Event: ...
    def to_other(self, e: Event) -> Event: ...

@dataclass
class LorentzBoost1D(Transform):
    """S <-> S' (S'가 +x로 v=beta*c)"""
    beta: float
    _gamma: float = field(init=False)

    def __post_init__(self):
        self._gamma = gamma(self.beta)

    def to_other(self, e: Event) -> Event:
        ct, x = e.ct, e.x
        ct_p = self._gamma * (ct - self.beta * x)
        x_p  = self._gamma * (x - self.beta * ct)
        return Event(ct_p, x_p)

    def to_self(self, e: Event) -> Event:
        ct_p, x_p = e.ct, e.x
        ct = self._gamma * (ct_p + self.beta * x_p)
        x  = self._gamma * (x_p + self.beta * ct_p)
        return Event(ct, x)

@dataclass
class InertialFrame1D:
    name: str = "S"
    origin_offset: Event = field(default_factory=lambda: Event(0.0, 0.0))
    def event(self, t_s: float, x: float) -> Event:
        return Event(ct=C * t_s + self.origin_offset.ct,
                     x=x + self.origin_offset.x)

@dataclass
class Observer:
    frame: InertialFrame1D
    state: State = field(default_factory=State)
    label: str = "observer"

    def update(self, dt: float):
        self.state.t += dt
        self.state.x += self.state.v * dt
        g = gamma(self.state.v / C) if abs(self.state.v) > 0 else 1.0
        self.state.tau += dt / g

    @property
    def event_now(self) -> Event:
        return self.frame.event(self.state.t, self.state.x)

# ==============================
# 2) 광선/레이저/검출기 (c_vis 대응)
# ==============================
@dataclass
class LightPulse:
    emission_event: Event
    direction: int = +1  # +1: +x, -1: -x
    speed: float = C     # 데모용 스케일(allow_sub_c_demo일 때 c_vis 사용)

    def position_at(self, t_s: float) -> float:
        """S에서 좌표시간 t_s의 위치."""
        t0 = self.emission_event.ct / C
        dt = t_s - t0
        return self.emission_event.x + self.direction * self.speed * dt

@dataclass
class LaserEmitter:
    position_x: float
    direction: int = +1
    allow_sub_c_demo: bool = False
    demo_speed: float = C  # allow_sub_c_demo=True일 때만 유효

    def emit(self, frame: InertialFrame1D, t_s: float) -> LightPulse:
        ct = C * t_s
        x = self.position_x
        spd = self.demo_speed if self.allow_sub_c_demo else C
        return LightPulse(Event(ct, x), self.direction, speed=spd)

@dataclass
class Detector:
    position_x: float
    hits: List[Event] = field(default_factory=list)

    def check_hit(self, pulse: LightPulse, t_s: float, eps: float = 1e-6):
        x = pulse.position_at(t_s)
        if abs(x - self.position_x) <= C * eps:
            self.hits.append(Event(C * t_s, self.position_x))

# ==============================
# 3) 강체/기차
# ==============================
@dataclass
class RigidRod1D:
    """S에서 정지 길이 L0, 속도 v."""
    rest_length: float
    center_x: float = 0.0
    v: float = 0.0
    label: str = "rod"

    def endpoints_in_S(self) -> Tuple[float, float]:
        beta = self.v / C
        g = gamma(beta) if abs(beta) > 0 else 1.0
        L = self.rest_length / g
        return (self.center_x - L / 2.0, self.center_x + L / 2.0)

@dataclass
class Train(RigidRod1D):
    lasers: List[LaserEmitter] = field(default_factory=list)

# ==============================
# 4) 시뮬레이션 엔진
# ==============================
@dataclass
class Simulation:
    frame: InertialFrame1D
    observers: List[Observer] = field(default_factory=list)
    trains: List[Train] = field(default_factory=list)
    detectors: List[Detector] = field(default_factory=list)
    light_pulses: List[LightPulse] = field(default_factory=list)
    t: float = 0.0
    dt: float = 0.01
    recorders: List["Recorder"] = field(default_factory=list)

    def step(self):
        # 관찰자/엔티티 업데이트(관성 가정)
        for obs in self.observers:
            obs.update(self.dt)
        for train in self.trains:
            train.center_x += train.v * self.dt

        # 광 펄스 검출 체크
        for det in self.detectors:
            for p in self.light_pulses:
                det.check_hit(p, self.t)

        # 레코드
        for r in self.recorders:
            r.capture(self)

        self.t += self.dt

    def run(self, seconds: float):
        steps = int(seconds / self.dt)
        for _ in range(steps):
            self.step()

@dataclass
class Recorder:
    worldline_samples: Dict[str, List[Event]] = field(default_factory=dict)
    def capture(self, sim: Simulation):
        for obs in sim.observers:
            self.worldline_samples.setdefault(obs.label, []).append(obs.event_now)

# ==============================
# 5) 파라미터 세트
# ==============================
@dataclass
class LengthContractionParams:
    train_rest_length: float = 120.0
    train_speed: float = 0.8 * C
    laser_direction: int = +1
    allow_sub_c_demo: bool = False
    demo_speed: float = C

@dataclass
class TwinsParams:
    v_out: float = 0.8 * C
    v_back: float = 0.8 * C
    accel_profile: str = "instant"   # "instant"만 지원(간단화)
    out_duration_s: float = 5.0
    back_duration_s: float = 5.0
    ship_rest_length: float = 120.0  # UI 뱃지용 L0
    turn_duration_s: float = 2.0

# ==============================
# 6) 시나리오: 길이 수축 + 레이저
# ==============================
@dataclass
class LengthContractionScenario:
    params: LengthContractionParams
    frame: InertialFrame1D = field(default_factory=InertialFrame1D)

    ground_observer: Observer = field(init=False)
    train_observer: Observer = field(init=False)
    train: Train = field(init=False)
    ground_detector: Detector = field(init=False)
    sim: Simulation = field(init=False)

    def __post_init__(self):
        self.ground_observer = Observer(self.frame, State(x=0.0, v=0.0), "ground")

        self.train = Train(
            rest_length=self.params.train_rest_length,
            center_x=-200.0,
            v=self.params.train_speed,
            label="train",
        )
        self.train_observer = Observer(self.frame, State(x=self.train.center_x, v=self.train.v), "on-train")

        # 기차 앞쪽 끝에 레이저 장착
        front_x, _ = self.train.endpoints_in_S()
        self.train.lasers.append(
            LaserEmitter(
                position_x=front_x,
                direction=self.params.laser_direction,
                allow_sub_c_demo=self.params.allow_sub_c_demo,
                demo_speed=self.params.demo_speed,
            )
        )

        self.ground_detector = Detector(position_x=0.0)

        self.sim = Simulation(
            frame=self.frame,
            observers=[self.ground_observer, self.train_observer],
            trains=[self.train],
            detectors=[self.ground_detector],
            dt=0.005,
        )
        self.sim.recorders.append(Recorder())

    def fire_laser(self, at_time_s: float):
        laser = self.train.lasers[0]
        pulse = laser.emit(self.frame, at_time_s)
        self.sim.light_pulses.append(pulse)

    def run(self, seconds: float):
        self.sim.run(seconds)

# ==============================
# 7) 시나리오: 쌍둥이 (프레임별 진행 지원)
# ==============================
@dataclass
class WorldlineSegment:
    duration_s: float
    dynamics: Callable[[float, State], State]
    label: str = ""

# sr_sim.py (TwinsScenario 일부만 발췌/교체)

# sr_sim.py — TwinsScenario 안쪽만 발췌 교체

@dataclass
class TwinsScenario:
    params: TwinsParams
    frame: InertialFrame1D = field(default_factory=InertialFrame1D)

    earth_observer: Observer = field(init=False)
    traveler: Observer = field(init=False)
    sim: Simulation = field(init=False)

    phase: str = "out"
    phase_elapsed: float = 0.0

    def __post_init__(self):
        self.earth_observer = Observer(self.frame, State(x=0.0, v=0.0), "earth")
        self.traveler       = Observer(self.frame, State(x=0.0, v=0.0), "traveler")
        self.sim = Simulation(frame=self.frame,
                              observers=[self.earth_observer, self.traveler],
                              dt=0.005)
        self.sim.recorders.append(Recorder())
        self.phase = "out"
        self.phase_elapsed = 0.0

    def reset(self):
        # 완전 초기화
        self.earth_observer = Observer(self.frame, State(x=0.0, v=0.0), "earth")
        self.traveler       = Observer(self.frame, State(x=0.0, v=0.0), "traveler")
        self.sim = Simulation(frame=self.frame,
                              observers=[self.earth_observer, self.traveler],
                              dt=0.005)
        self.sim.recorders = [Recorder()]
        self.phase = "out"
        self.phase_elapsed = 0.0

    def _capture(self):
        for r in self.sim.recorders:
            r.capture(self.sim)

    def advance_by(self, dt: float):
        p = self.params

        # 1) 현재 페이즈로 목표 v 계산
        v = self.traveler.state.v
        next_elapsed = self.phase_elapsed + dt

        if self.phase == "out":
            v = p.v_out
            if next_elapsed >= p.out_duration_s:
                self.phase_elapsed = 0.0
                if p.accel_profile == "finite" and p.turn_duration_s > 0.0:
                    self.phase = "turn"
                else:
                    self.phase = "back"
            else:
                self.phase_elapsed = next_elapsed

        elif self.phase == "turn":
            # v_out → −v_back 으로 smoothstep 보간
            T = max(1e-9, p.turn_duration_s)
            a = max(0.0, min(1.0, next_elapsed / T))
            alpha = a*a*(3 - 2*a)
            u0, u1 = p.v_out, -p.v_back
            v = (1.0 - alpha) * u0 + alpha * u1
            if next_elapsed >= T:
                self.phase = "back"
                self.phase_elapsed = 0.0
            else:
                self.phase_elapsed = next_elapsed

        elif self.phase == "back":
            v = -p.v_back
            self.phase_elapsed = next_elapsed

        elif self.phase == "done":
            # 정지
            self.earth_observer.update(dt)
            self.traveler.update(dt)
            self.sim.t += dt
            self._capture()
            return

        # 2) x=0(지구) 도달 부분 적분
        prev_x = self.traveler.state.x
        if v < 0.0 and prev_x > 0.0:
            x_next = prev_x + v * dt
            if x_next <= 0.0:
                dt_hit = prev_x / (-v)
                dt_rem = max(0.0, dt - dt_hit)

                # hit까지 진척
                self.traveler.state.v = v
                self.traveler.update(dt_hit)
                self.earth_observer.update(dt_hit)
                self.sim.t += dt_hit
                self._capture()

                # 정확히 0에서 정지
                self.traveler.state.x = 0.0
                self.traveler.state.v = 0.0
                self.phase = "done"

                if dt_rem > 0.0:
                    self.traveler.update(dt_rem)  # v=0
                    self.earth_observer.update(dt_rem)
                    self.sim.t += dt_rem
                    self._capture()
                return

        # 3) 일반 적분
        self.traveler.state.v = v
        self.traveler.update(dt)
        self.earth_observer.update(dt)
        self.sim.t += dt
        self._capture()
