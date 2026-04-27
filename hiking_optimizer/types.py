"""Core datatypes used across the backend modules."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TrackPoint:
    lat: float
    lon: float
    ele_m: float


@dataclass(frozen=True)
class Segment:
    idx: int
    start: TrackPoint
    end: TrackPoint
    distance_m: float
    elev_delta_m: float
    grade_pct: float
    grade_abs_pct: float
    cumulative_distance_m: float


@dataclass(frozen=True)
class Zone:
    start_mile: float
    end_mile: float
    zone_type: str
    avg_speed_mph: float
