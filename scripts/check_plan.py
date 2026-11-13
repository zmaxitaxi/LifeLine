#!/usr/bin/env python3
"""Validate planning presets with a reference dispatch, not an optimizer.

Python 3.11+, standard library only. This is deliberately separate from the
future application. It checks the physical facts motivating the build plan;
application acceptance still requires independent solver/API/browser tests.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOL = 1e-6


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def close(actual: float, expected: float, message: str) -> None:
    require(abs(actual - expected) <= TOL, f"{message}: {actual} != {expected}")


def number(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def slots(values: list, label: str) -> None:
    require(len(values) == len(set(values)), f"{label}: duplicate hours")
    require(all(type(h) is int and 0 <= h < 24 for h in values), f"{label}: invalid hour")


def validate(data: dict) -> None:
    require(data["schema_version"] == "1.0", "unsupported configuration version")
    require(data["horizon_hours"] == 24 and data["dt_hours"] == 1, "expected 24 hourly slots")
    require(data["timezone"] == "Africa/Nairobi", "unexpected scenario timezone")
    model = data["pv_model"]
    require(model["sunrise_hour"] == 6 and model["sunset_hour"] == 18, "unexpected daylight")
    require(0 < model["performance_ratio"] <= 1, "invalid performance ratio")
    scenarios = data["scenarios"]
    require([s["id"] for s in scenarios] == ["normal", "storm", "high_demand"], "expected three ordered presets")
    all_ids = [e["id"] for e in data["critical_equipment"] + data["flexible_equipment"]]
    require(len(set(all_ids)) == len(all_ids), "equipment IDs must be unique")
    require("additional_protected_load" not in all_ids, "extra-load ID is reserved")

    for equipment in data["critical_equipment"]:
        require(equipment["category"] == "critical", "incorrect protected equipment category")
        require(number(equipment["power_kw"]) and equipment["power_kw"] >= 0, "invalid critical power")
        slots(equipment["required_hours"], equipment["id"])

    for task in data["flexible_equipment"]:
        require(task["category"] == "flexible" and task["divisible"] is True, "expected divisible flexible task")
        require(number(task["max_power_kw"]) and task["max_power_kw"] > 0, "invalid task power")
        require(number(task["required_energy_kwh"]) and task["required_energy_kwh"] >= 0, "invalid task energy")
        slots(task["allowed_hours"], task["id"])
        allocations = task["baseline_allocations"]
        slots([a["hour"] for a in allocations], task["id"] + " baseline")
        for allocation in allocations:
            require(allocation["hour"] in task["allowed_hours"], "baseline outside allowed window")
            energy = allocation["requested_kwh"]
            require(number(energy) and 0 <= energy <= task["max_power_kw"] * data["dt_hours"], "invalid baseline task allocation")
        close(sum(a["requested_kwh"] for a in allocations), task["required_energy_kwh"], "baseline task requirement")

    for scenario in scenarios:
        require(set(scenario["overrides"]).issubset(data["defaults"]), "unknown preset override")
        config = data["defaults"] | scenario["overrides"]
        require(all(number(v) for v in config.values()), "non-finite or nonnumeric configuration")
        capacity = config["battery_capacity_kwh"]
        require(0 < capacity <= 200, "invalid battery capacity")
        require(0 <= config["initial_battery_kwh"] <= capacity, "invalid initial energy")
        require(0 <= config["reserve_kwh"] <= capacity, "invalid reserve")
        require(0 <= config["pv_capacity_kw"] <= 100, "invalid PV capacity")
        for key in ("charge_efficiency", "discharge_efficiency"):
            require(0 < config[key] <= 1, "invalid efficiency")
        for key in ("max_charge_kw", "max_discharge_kw"):
            require(0 <= config[key] <= 100, "invalid battery rate")
        require(0 <= config["additional_critical_kw"] <= 10, "invalid additional demand")
        if scenario["id"] != "high_demand":
            require(config["additional_critical_kw"] == 0, "extra demand reserved for high_demand")
        slots(scenario["additional_critical_hours"], "additional critical load")
        clouds = scenario["cloud_factors"]
        require(len(clouds) == 24, "cloud profile must contain 24 values")
        require(all(number(c) and 0 <= c <= 1 for c in clouds), "invalid cloud factor")


def profiles(data: dict, scenario: dict, config: dict) -> tuple[list, list, list]:
    model = data["pv_model"]
    start, end = model["sunrise_hour"], model["sunset_hour"]
    pv = []
    critical = [0.0] * 24
    flexible = [0.0] * 24
    for hour in range(24):
        shape = math.sin(math.pi * (hour + 0.5 - start) / (end - start)) if start <= hour < end else 0.0
        pv.append(config["pv_capacity_kw"] * model["performance_ratio"] * shape * scenario["cloud_factors"][hour] * data["dt_hours"])
    for equipment in data["critical_equipment"]:
        for hour in equipment["required_hours"]:
            critical[hour] += equipment["power_kw"] * data["dt_hours"]
    for hour in scenario["additional_critical_hours"]:
        critical[hour] += config["additional_critical_kw"] * data["dt_hours"]
    for task in data["flexible_equipment"]:
        for allocation in task["baseline_allocations"]:
            flexible[allocation["hour"]] += allocation["requested_kwh"]
    require(all(value == 0 for h, value in enumerate(pv) if not start <= h < end), "nonzero nighttime solar")
    return pv, critical, flexible


def reference_dispatch(pv: list, critical: list, flexible: list, config: dict) -> dict:
    """Greedy critical-first physical dispatch for planning calibration only."""
    energy = config["initial_battery_kwh"]
    boundaries = [energy]
    rows = []
    eta_c, eta_d = config["charge_efficiency"], config["discharge_efficiency"]
    capacity = config["battery_capacity_kwh"]
    for hour in range(24):
        before = energy
        available_pv = pv[hour]
        discharge_remaining = min(config["max_discharge_kw"], energy * eta_d)
        critical_served = min(critical[hour], available_pv + discharge_remaining)
        critical_discharge = max(0.0, critical_served - available_pv)
        available_pv = max(0.0, available_pv - critical_served)
        energy -= critical_discharge / eta_d
        discharge_remaining -= critical_discharge
        flexible_served = min(flexible[hour], available_pv + discharge_remaining)
        flexible_discharge = max(0.0, flexible_served - available_pv)
        available_pv = max(0.0, available_pv - flexible_served)
        energy -= flexible_discharge / eta_d
        charge = min(available_pv, config["max_charge_kw"], max(0.0, capacity - energy) / eta_c)
        discharge = critical_discharge + flexible_discharge
        energy += charge * eta_c
        curtail = available_pv - charge
        unmet = max(0.0, critical[hour] - critical_served)

        close(pv[hour] + discharge, critical_served + flexible_served + charge + curtail, f"hour {hour} bus balance")
        close(energy, before + eta_c * charge - discharge / eta_d, f"hour {hour} battery balance")
        require(-TOL <= energy <= capacity + TOL, "battery outside physical bounds")
        require(0 <= charge <= config["max_charge_kw"] + TOL, "charge rate exceeded")
        require(0 <= discharge <= config["max_discharge_kw"] + TOL, "discharge rate exceeded")
        require(min(charge, discharge) <= TOL, "simultaneous charge and discharge")
        require(-TOL <= curtail <= pv[hour] + TOL, "invalid solar curtailment")
        rows.append({"hour": hour, "critical_served": critical_served, "critical_unserved": unmet,
                     "flexible_served": flexible_served, "charge": charge, "discharge": discharge,
                     "curtail": curtail})
        boundaries.append(energy)

    totals = {key: sum(row[key] for row in rows) for key in rows[0] if key != "hour"}
    losses = (1 - eta_c) * totals["charge"] + (1 / eta_d - 1) * totals["discharge"]
    close(config["initial_battery_kwh"] + sum(pv), energy + totals["critical_served"] + totals["flexible_served"] + totals["curtail"] + losses, "daily energy balance")
    status = "CRITICAL_SHORTAGE" if totals["critical_unserved"] > TOL else "RESERVE_AT_RISK" if min(boundaries) < config["reserve_kwh"] - TOL else "OK"
    return {"min_soc_kwh": min(boundaries), "final_soc_kwh": energy,
            "critical_unserved_kwh": totals["critical_unserved"],
            "flexible_served_kwh": totals["flexible_served"],
            "curtailed_kwh": totals["curtail"], "status": status,
            "critical_shortage_hours": [row["hour"] for row in rows if row["critical_unserved"] > TOL]}


def main() -> None:
    data = json.loads((ROOT / "contracts/scenarios.json").read_text())
    validate(data)
    print("Planning-input verification only; the application optimizer is not implemented.")
    for scenario in data["scenarios"]:
        config = data["defaults"] | scenario["overrides"]
        pv, critical, flexible = profiles(data, scenario, config)
        baseline = reference_dispatch(pv, critical, flexible, config)
        critical_only = reference_dispatch(pv, critical, [0.0] * 24, config)
        checks = scenario["reference_checks"]
        close(sum(pv), checks["solar_kwh"], "preset solar calibration")
        close(sum(critical), checks["critical_kwh"], "preset critical calibration")
        close(sum(flexible), 2.1, "flexible demand calibration")
        close(critical_only["min_soc_kwh"], checks["critical_only_min_soc_kwh"], "critical-only minimum calibration")
        close(critical_only["critical_unserved_kwh"], checks["critical_only_unserved_kwh"], "critical-only shortage calibration")
        require(critical_only["status"] == scenario["expected_status"], "unexpected critical-only status")

        if scenario["id"] == "normal":
            require(baseline["status"] == "OK", "normal baseline must meet reserve")
            close(baseline["flexible_served_kwh"], 2.1, "normal baseline serves all flexible work")
        elif scenario["id"] == "storm":
            close(baseline["min_soc_kwh"], 0.7475779629717891, "storm baseline calibration")
            close(critical_only["curtailed_kwh"], 0, "storm critical-only uses all available PV")
            require(critical_only["final_soc_kwh"] < config["reserve_kwh"] - TOL, "storm must remain below reserve without flexible work")
            require(critical_only["min_soc_kwh"] > baseline["min_soc_kwh"] + TOL, "storm deferral must improve reserve")
        else:
            # This lower bound is independent of battery accounting/dispatch:
            # no source can exceed PV + the shared discharge power limit.
            rate_shortfall = sum(max(0.0, c - p - config["max_discharge_kw"]) for c, p in zip(critical, pv))
            close(rate_shortfall, 1.32, "high-demand rate-only lower bound")
            close(critical_only["critical_unserved_kwh"], rate_shortfall, "reference attains lower bound")
            require(critical_only["critical_shortage_hours"] == [20, 21], "wrong shortage hours")

        print(f"{scenario['id']}: solar={sum(pv):.6f} kWh, critical={sum(critical):.6f} kWh, "
              f"baseline min={baseline['min_soc_kwh']:.6f} kWh, critical-only min={critical_only['min_soc_kwh']:.6f} kWh, "
              f"critical-only unmet={critical_only['critical_unserved_kwh']:.6f} kWh, status={critical_only['status']}")
    print("PASS: profiles, task windows, energy balance, battery bounds, rates, losses, and preset calibration.")


if __name__ == "__main__":
    main()
