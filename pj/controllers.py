# controllers.py
from __future__ import annotations
from abc import ABC, abstractmethod
import sr_sim as sim

class ScenarioController(ABC):
    dt: float

    @abstractmethod
    def step(self): ...
    @property
    @abstractmethod
    def beta(self) -> float: ...
    @property
    @abstractmethod
    def gamma(self) -> float: ...
    @property
    @abstractmethod
    def t(self) -> float: ...
    @property
    @abstractmethod
    def L0(self) -> float: ...
    @property
    @abstractmethod
    def L_contracted(self) -> float | None: ...
    @property
    @abstractmethod
    def ship_center_x(self) -> float: ...
    @abstractmethod
    def apply_beta(self, beta: float): ...
    @abstractmethod
    def reset(self): ...
    def fire_laser(self): pass
    def earth_x_in_ship_frame(self) -> float:
        # 기본 구현(정지 상대): 0
        return 0.0

# -------- LC --------
class LCController(ScenarioController):
    def __init__(self, scn: sim.LengthContractionScenario):
        self.scn = scn
        self.dt = scn.sim.dt

    def step(self):
        self.scn.sim.step()

    @property
    def beta(self) -> float:
        return self.scn.train.v / sim.C

    @property
    def gamma(self) -> float:
        b = self.beta
        return sim.gamma(b) if abs(b) < 1.0 else float("inf")

    @property
    def t(self) -> float:
        return self.scn.sim.t

    @property
    def L0(self) -> float:
        return self.scn.train.rest_length

    @property
    def L_contracted(self) -> float:
        g = self.gamma
        if g == float("inf") or g == 0: return self.scn.train.rest_length
        return self.scn.train.rest_length / g

    @property
    def ship_center_x(self) -> float:
        return self.scn.train.center_x

    def apply_beta(self, beta: float):
        v = beta * sim.C
        self.scn.train.v = v
        self.scn.train_observer.state.v = v

    def reset(self):
        self.scn.sim.t = 0.0
        self.scn.train.center_x = -200.0
        self.scn.train.v = self.scn.params.train_speed
        self.scn.train_observer.state.x = self.scn.train.center_x
        self.scn.train_observer.state.v = self.scn.train.v

    def fire_laser(self):
        self.scn.fire_laser(at_time_s=self.scn.sim.t)

    def earth_x_in_ship_frame(self) -> float:
        # LC 화면의 S′(기차 프레임)에서 지구 좌표
        tS = self.scn.sim.t
        eS_earth = sim.Event(ct=sim.C * tS, x=0.0)
        b = self.beta
        if abs(b) < 1e-12:
            return 0.0
        boost = sim.LorentzBoost1D(beta=b)
        return boost.to_other(eS_earth).x

# -------- Twins --------
class TwinsController(ScenarioController):
    def __init__(self, scn: sim.TwinsScenario, ship_L0: float = 120.0):
        self.scn = scn
        self.dt = scn.sim.dt
        self._L0 = ship_L0

    def step(self):
        # ★ 반드시 advance_by만 호출
        self.scn.advance_by(self.dt)

    @property
    def beta(self) -> float:
        return self.scn.traveler.state.v / sim.C

    @property
    def gamma(self) -> float:
        b = self.beta
        return sim.gamma(b) if abs(b) < 1.0 else float("inf")

    @property
    def t(self) -> float:
        return self.scn.sim.t  # advance_by에서 sim.t를 올려야 렌더가 움직임

    @property
    def L0(self) -> float:
        return self._L0

    @property
    def L_contracted(self) -> float | None:
        g = self.gamma
        if g in (0.0, float("inf")): return self._L0
        return self._L0 / g

    @property
    def ship_center_x(self) -> float:
        return self.scn.traveler.state.x

    def apply_beta(self, beta: float):
        # ★ 현재 속도(state.v)를 덮지 말고 목표 속도만 갱신
        v = abs(beta) * sim.C
        self.scn.params.v_out  = v
        self.scn.params.v_back = v
        # self.scn.traveler.state.v = v  # 금지

    def reset(self):
        self.scn.reset()
        self.dt = self.scn.sim.dt

    def earth_x_in_ship_frame(self) -> float:
        # ICIF(순간적 공준 관성계) 동시성: x'_rel = - x_ship / gamma
        x_s = self.scn.traveler.state.x
        g   = self.gamma if self.gamma not in (0.0, float("inf")) else 1.0
        return - x_s / g

