"""Independent accounting assertions, including MILP outputs (not its constraint builder)."""

from dataclasses import replace
import pytest
from app.energy_types import BatteryConfig, ModelInput
from app.energy_simulator import simulate_baseline
from app.model_demo import load_inputs
from app.optimizer import optimize
from app.heuristic import sunshine_first

METHODS = [simulate_baseline, sunshine_first, optimize]


def assert_physics(inputs, result):
    b = inputs.battery
    hourly = result['hourly']
    assert len(hourly) == 24
    states = [hourly[0]['soc_start_kwh']] + [r['soc_end_kwh'] for r in hourly]
    assert states[0] == pytest.approx(b.initial_battery_kwh, abs=1e-6)
    for h, r in enumerate(hourly):
        assert r['hour'] == h
        assert r['pv_kwh'] == inputs.pv_kwh[h]
        assert r['critical_requested_kwh'] == inputs.critical_kwh[h]
        assert r['soc_start_kwh'] == pytest.approx(states[h], abs=1e-6)
        assert -1e-6 <= states[h+1] <= b.battery_capacity_kwh+1e-6
        assert 0 <= r['charge_input_kwh'] <= b.max_charge_kw+1e-6
        assert 0 <= r['discharge_output_kwh'] <= b.max_discharge_kw+1e-6
        assert min(r['charge_input_kwh'], r['discharge_output_kwh']) <= 1e-6
        assert 0 <= r['curtailed_kwh'] <= r['pv_kwh']+1e-6
        assert 0 <= r['critical_unserved_kwh'] <= r['critical_requested_kwh']+1e-6
        assert r['critical_served_kwh']+r['critical_unserved_kwh'] == pytest.approx(r['critical_requested_kwh'], abs=1e-6)
        assert r['pv_kwh']+r['discharge_output_kwh'] == pytest.approx(
            r['critical_served_kwh']+r['flexible_served_kwh']+r['charge_input_kwh']+r['curtailed_kwh'], abs=1e-6)
        assert states[h+1] == pytest.approx(states[h]+b.charge_efficiency*r['charge_input_kwh']-r['discharge_output_kwh']/b.discharge_efficiency, abs=1e-6)
    loss = sum((1-b.charge_efficiency)*r['charge_input_kwh']+(1/b.discharge_efficiency-1)*r['discharge_output_kwh'] for r in hourly)
    assert b.initial_battery_kwh+sum(inputs.pv_kwh) == pytest.approx(
        states[-1]+sum(r['critical_served_kwh']+r['flexible_served_kwh']+r['curtailed_kwh'] for r in hourly)+loss, abs=1e-6)
    metrics = result['metrics']
    coverage = metrics['critical_coverage_pct']
    assert coverage is None or 0 <= coverage <= 100
    assert metrics['conversion_loss_kwh'] == pytest.approx(loss, abs=1e-6)
    assert metrics['min_soc_kwh'] == pytest.approx(min(states), abs=1e-6)
    assert metrics['critical_unserved_kwh'] == pytest.approx(sum(r['critical_unserved_kwh'] for r in hourly), abs=1e-6)
    for task, outcome in zip(inputs.tasks, result['flexible_tasks']):
        assert outcome['task_id'] == task.id
        assert outcome['served_kwh']+outcome['deferred_kwh'] == pytest.approx(task.required_energy_kwh, abs=1e-6)
        assert outcome['served_kwh'] == pytest.approx(sum(a['served_kwh'] for a in outcome['allocations']), abs=1e-6)
        for allocation in outcome['allocations']:
            assert allocation['hour'] in task.allowed_hours
            assert 0 <= allocation['served_kwh'] <= task.max_power_kw+1e-6
    assert sum(t['served_kwh'] for t in result['flexible_tasks']) == pytest.approx(sum(r['flexible_served_kwh'] for r in hourly), abs=1e-6)


@pytest.mark.parametrize('scenario', ['scheduling', 'normal', 'storm', 'high_demand'])
@pytest.mark.parametrize('method', METHODS)
def test_presets_conserve_energy(scenario, method):
    inputs = load_inputs(scenario)
    assert_physics(inputs, method(inputs))


@pytest.mark.parametrize('method', METHODS)
def test_empty_battery_without_sun_reports_all_unserved(method):
    inputs = ModelInput(BatteryConfig(initial_battery_kwh=0), (0.,)*24, (1.,)*24)
    result = method(inputs)
    assert_physics(inputs, result)
    assert result['status'] == 'CRITICAL_SHORTAGE'
    assert result['metrics']['critical_unserved_kwh'] == pytest.approx(24)


@pytest.mark.parametrize('method', METHODS)
def test_full_battery_curtailment_and_zero_demand(method):
    inputs = ModelInput(BatteryConfig(initial_battery_kwh=20, reserve_kwh=0), (10.,)*24, (0.,)*24)
    result = method(inputs)
    assert_physics(inputs, result)
    assert result['metrics']['curtailed_kwh'] == pytest.approx(240)
    assert result['metrics']['critical_coverage_pct'] is None
    assert result['status'] == 'OK'


@pytest.mark.parametrize('method', METHODS)
def test_non_unit_efficiency_and_rate_limits(method):
    inputs = ModelInput(BatteryConfig(initial_battery_kwh=0, reserve_kwh=0,
                                     charge_efficiency=.8, discharge_efficiency=.5,
                                     max_charge_kw=2, max_discharge_kw=1),
                        (10.,)+(0.,)*23, (0., 4.)+(0.,)*22)
    result = method(inputs)
    assert_physics(inputs, result)
    assert result['hourly'][0]['soc_end_kwh'] == pytest.approx(1.6)
    assert result['hourly'][1]['critical_served_kwh'] == pytest.approx(.8)


@pytest.mark.parametrize('method', METHODS)
def test_zero_battery_power_limits(method):
    inputs = load_inputs('normal')
    inputs = replace(inputs, battery=replace(inputs.battery, max_charge_kw=0, max_discharge_kw=0))
    result = method(inputs)
    assert_physics(inputs, result)
    assert all(r['soc_end_kwh'] == pytest.approx(14) for r in result['hourly'])
    assert result['status'] == 'CRITICAL_SHORTAGE'
