"""Validated numerical inputs; HTTP/Pydantic models belong to the API layer."""

from dataclasses import dataclass
import math

HOURS = 24
TOL = 1e-6


def finite(value, name, low=0, high=math.inf, exclusive_low=False):
    if (isinstance(value, bool) or not isinstance(value, (float, int))
            or not math.isfinite(value) or value > high
            or (value <= low if exclusive_low else value < low)):
        raise ValueError(f"Invalid {name}: {value!r}")


def profile(values, name):
    if len(values) != HOURS:
        raise ValueError(f"{name} must have 24 hourly values")
    for value in values:
        finite(value, name)


@dataclass(frozen=True)
class BatteryConfig:
    battery_capacity_kwh: float = 20
    initial_battery_kwh: float = 14
    reserve_kwh: float = 4
    charge_efficiency: float = .95
    discharge_efficiency: float = .95
    max_charge_kw: float = 4
    max_discharge_kw: float = 4

    def __post_init__(self):
        finite(self.battery_capacity_kwh, "capacity", high=200, exclusive_low=True)
        for name in ("initial_battery_kwh", "reserve_kwh"):
            finite(getattr(self, name), name, high=self.battery_capacity_kwh)
        for name in ("charge_efficiency", "discharge_efficiency"):
            finite(getattr(self, name), name, high=1, exclusive_low=True)
        for name in ("max_charge_kw", "max_discharge_kw"):
            finite(getattr(self, name), name, high=100)


@dataclass(frozen=True)
class FlexibleTask:
    id: str
    required_energy_kwh: float
    max_power_kw: float
    allowed_hours: tuple[int, ...]
    baseline_kwh: tuple[float, ...]

    def __post_init__(self):
        if not isinstance(self.id, str) or not self.id:
            raise ValueError("Task ID must be nonempty")
        finite(self.required_energy_kwh, "task energy")
        finite(self.max_power_kw, "task power", exclusive_low=True)
        if (len(set(self.allowed_hours)) != len(self.allowed_hours)
                or any(type(h) is not int or not 0 <= h < HOURS for h in self.allowed_hours)):
            raise ValueError("Task hours must be unique slots in 0..23")
        profile(self.baseline_kwh, "baseline schedule")
        for h, value in enumerate(self.baseline_kwh):
            if value > (self.max_power_kw if h in self.allowed_hours else 0) + TOL:
                raise ValueError("Baseline exceeds task window/power")
        if sum(self.baseline_kwh) > self.required_energy_kwh + TOL:
            raise ValueError("Baseline cannot request more than the task energy")


@dataclass(frozen=True)
class ModelInput:
    battery: BatteryConfig
    pv_kwh: tuple[float, ...]
    critical_kwh: tuple[float, ...]
    tasks: tuple[FlexibleTask, ...] = ()

    def __post_init__(self):
        profile(self.pv_kwh, "PV")
        profile(self.critical_kwh, "critical demand")
        if len({t.id for t in self.tasks}) != len(self.tasks):
            raise ValueError("Task IDs must be unique")
