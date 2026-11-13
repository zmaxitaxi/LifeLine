"""CLI/integration example for Person 2, not the future HTTP scenario layer."""

from dataclasses import fields
import argparse
import json
from pathlib import Path
from .energy_types import BatteryConfig, FlexibleTask, ModelInput, finite
from .solar_forecast import forecast_solar
from .comparison import compare_schedules

CONFIG_PATH = Path(__file__).resolve().parents[2] / "contracts/scenarios.json"


def load_inputs(scenario_id, overrides=None):
    """Resolve committed presets independently of the caller's working directory.

    Person 2 should reuse these pure model types from validated API models;
    this small adapter documents the mapping without creating HTTP endpoints.
    """
    data = json.loads(CONFIG_PATH.read_text())
    preset = next((s for s in data["scenarios"] if s["id"] == scenario_id), None)
    if preset is None:
        raise ValueError("Unknown scenario")
    overrides = {} if overrides is None else dict(overrides)
    if set(overrides)-set(data["defaults"]):
        raise ValueError("Unknown override")
    if "additional_critical_kw" in overrides and scenario_id != "high_demand":
        raise ValueError("Additional load override is only supported by high_demand")
    config = data["defaults"] | preset["overrides"] | overrides
    battery = BatteryConfig(**{f.name: config[f.name] for f in fields(BatteryConfig)})
    finite(config["additional_critical_kw"], "additional load", high=10)
    pv = forecast_solar(config["pv_capacity_kw"], preset["cloud_factors"], data["pv_model"]["performance_ratio"])
    critical = [0.] * 24
    for equipment in data["critical_equipment"]:
        for h in equipment["required_hours"]:
            critical[h] += equipment["power_kw"]
    for h in preset["additional_critical_hours"]:
        critical[h] += config["additional_critical_kw"]
    tasks = []
    for equipment in data["flexible_equipment"]:
        baseline = [0.] * 24
        for allocation in equipment["baseline_allocations"]:
            baseline[allocation["hour"]] = allocation["requested_kwh"]
        tasks.append(FlexibleTask(equipment["id"], equipment["required_energy_kwh"],
                                  equipment["max_power_kw"], tuple(equipment["allowed_hours"]), tuple(baseline)))
    return ModelInput(battery, pv, tuple(critical), tuple(tasks))


def main():
    parser = argparse.ArgumentParser(description="Synthetic energy model demonstration; no clinical use")
    parser.add_argument("scenario", choices=["scheduling", "normal", "storm", "high_demand"])
    args = parser.parse_args()
    inputs = load_inputs(args.scenario)
    print(json.dumps(compare_schedules(inputs), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
