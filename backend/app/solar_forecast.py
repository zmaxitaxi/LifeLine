"""Synthetic hourly scenario forecast; no trained model or real weather."""

import math
from .energy_types import finite, profile


def forecast_solar(pv_capacity_kw, cloud_factors, performance_ratio=.8):
    """Return 24 kWh-per-hour values for a fixed 06:00–18:00 daylight curve."""
    finite(pv_capacity_kw, "PV capacity", high=100)
    finite(performance_ratio, "performance ratio", high=1, exclusive_low=True)
    profile(cloud_factors, "cloud factors")
    for cloud in cloud_factors:
        finite(cloud, "cloud factor", high=1)
    return tuple(
        pv_capacity_kw * performance_ratio * cloud_factors[h]
        * math.sin(math.pi * (h + .5 - 6) / 12) if 6 <= h < 18 else 0.
        for h in range(24)
    )


def pv_from_irradiance(pv_capacity_kw, irradiance_kwh_m2, performance_ratio=.8):
    """Hourly GHI energy → PV energy, normalized to STC 1 kW/m².

    The existing performance ratio includes aggregate losses. Horizontal GHI
    approximates array-plane irradiance; no tilt, shading, temperature or
    inverter clipping model is added. Weather already includes clouds.
    """
    finite(pv_capacity_kw, 'PV capacity', high=100)
    finite(performance_ratio, 'performance ratio', high=1, exclusive_low=True)
    profile(irradiance_kwh_m2, 'hourly irradiation')
    return tuple(pv_capacity_kw * performance_ratio * value for value in irradiance_kwh_m2)
