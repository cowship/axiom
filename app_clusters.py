# app_clusters.py — 잔해(클러스터) 생성 관련 기능
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

def _generate_clusters(self) -> List[List[Debris]]:
    clusters = []
    specs = [
        ( 8.0e2,  14, 2.6e2, (-120,  +40)),
        ( 2.2e3,  18, 3.2e2, (-60,  +120)),
        ( 4.1e3,  20, 4.0e2, (-160, +80)),
        ( 7.3e3,  16, 5.2e2, (-90,  +150)),
        ( 1.20e4, 14, 6.0e2, (-140, +60)),
    ]
    for idx, (center, n, gap, (ymin, ymax)) in enumerate(specs):
        base = center - (n//2)*gap
        xs = [base + i*gap + random.uniform(-0.28,0.28)*gap for i in range(n)]
        col = _PALETTES[idx % len(_PALETTES)]
        cl = [Debris(x, random.randint(ymin, ymax), col) for x in xs]
        clusters.append(cl)
    return clusters


# ----- 스타일 -----


