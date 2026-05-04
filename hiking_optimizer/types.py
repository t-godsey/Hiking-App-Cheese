"""Core datatypes used across the backend modules."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TrackPoint:
    """One GPX trackpoint with latitude, longitude, elevation (meters)."""

    lat: float
    lon: float
    ele_m: float


@dataclass(frozen=True)
class Segment:
    """Single trail step between consecutive trackpoints (great-circle length and grade)."""

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
    """Contiguous pace zone along the route (after merging short runs), distances in miles."""

    start_mile: float
    end_mile: float
    zone_type: str
    avg_speed_mph: float
