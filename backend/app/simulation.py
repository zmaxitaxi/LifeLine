"""Shared scenario simulation; all callers use the same physics and optimizer."""
from .comparison import compare_schedules
from .diagnosis import diagnose
from .explanations import explain
from .models import SimulationResponse


def simulate_case(catalog, body):
    config = catalog.resolve(body)
    inputs = catalog.build_inputs(body, config)
    results = compare_schedules(inputs)
    equipment = catalog.equipment_for(body, config)
    warnings, recommendations = explain(results, inputs, equipment)
    return SimulationResponse(scenario=body.scenario, scenario_name=catalog.preset(body.scenario).name,
        data_source="mixed" if body.weather_dataset != "synthetic" else ("user_defined" if body.equipment is not None else "synthetic"),
        cloud_factors=body.cloud_factors if body.cloud_factors is not None else catalog.preset(body.scenario).cloud_factors,
        weather_dataset=body.weather_dataset, diagnosis=diagnose(inputs, results),
        input_provenance={"equipment": "user_entered_unverified" if body.equipment is not None else "synthetic",
                          "weather": "NASA_POWER_historical_satellite_derived" if body.weather_dataset != "synthetic" else ("user_entered_scenario_factors" if body.cloud_factors is not None else "synthetic_scenario"),
                          "model": "Horizontal irradiance approximation; not a forecast" if body.weather_dataset != "synthetic" else "Fixed daylight curve; not measured irradiance or an operational weather forecast"},
        pv_performance_ratio=catalog.pv_model.performance_ratio, effective_config=config,
        equipment=equipment, assumptions=[
            'Equipment values are user-entered and unverified.' if body.equipment is not None else catalog.provenance,
            ('Weather is historical satellite-derived irradiance, not a clinic measurement or current forecast.' if body.weather_dataset != 'synthetic' else 'Weather is a synthetic/user-adjusted scenario forecast, not measured or trained-model output.'),
            'Fixed 24 hourly slots in Africa/Nairobi; battery chart boundaries run from 0 through 24.',
            ('NASA POWER historical satellite-derived irradiance; horizontal input is an approximation, not a clinic measurement or forecast.' if body.weather_dataset != 'synthetic' else 'PV uses a synthetic 06:00–18:00 sine curve and the returned performance ratio/cloud profile.'),
            'Critical loads are operator-defined and never rescheduled; flexible tasks are divisible energy approximations.',
            'Reserve is a target above physical zero; losses, rate limits, and capacity are modeled on one idealized energy bus.',
            'Storm starts depleted after hypothetical earlier cloudy days; those days are not simulated.',
            'No thermal dynamics, sub-hour surges, degradation, uncertainty, grid, or generator are modeled.',
            'All three schedules use identical inputs. Same-work comparisons must check completion; heuristic ties are explicit.',
            'Illustrative simulation; not for clinical or operational use.'],
        status=results['optimized']['status'], baseline=results['baseline'], heuristic=results['heuristic'],
        optimized=results['optimized'], comparison=results['comparison'], warnings=warnings,
        recommendations=recommendations)
