from dataclasses import replace
from types import SimpleNamespace
import random
import pytest
import scipy.optimize
from app import optimizer
from app.energy_types import BatteryConfig, FlexibleTask, ModelInput
from app.energy_simulator import NumericalError, simulate_baseline
from app.model_demo import load_inputs
from app.heuristic import sunshine_first
from app.comparison import compare_schedules
from test_energy_balance import assert_physics


def test_scheduling_preserves_work_and_improves_reserve_and_losses():
    inputs = load_inputs('scheduling')
    original = repr(inputs)
    baseline, heuristic, optimal = simulate_baseline(inputs), sunshine_first(inputs), optimizer.optimize(inputs)
    assert repr(inputs) == original  # every method used precisely the same immutable inputs
    for plan in (baseline, heuristic, optimal):
        assert plan['metrics']['flexible_served_kwh'] == pytest.approx(2.1)
        assert plan['metrics']['critical_coverage_pct'] == pytest.approx(100)
    assert baseline['status'] == 'RESERVE_AT_RISK'
    assert optimal['status'] == 'OK'
    assert optimal['metrics']['min_soc_kwh']-baseline['metrics']['min_soc_kwh'] == pytest.approx(.368421052631574, abs=1e-6)
    assert optimal['metrics']['final_soc_kwh']-baseline['metrics']['final_soc_kwh'] == pytest.approx(2.210526315789473, abs=1e-6)
    assert baseline['metrics']['conversion_loss_kwh']-optimal['metrics']['conversion_loss_kwh'] == pytest.approx(.110526315789473, abs=1e-6)
    for key in ('min_soc_kwh', 'final_soc_kwh', 'conversion_loss_kwh', 'flexible_served_kwh'):
        assert heuristic['metrics'][key] == pytest.approx(optimal['metrics'][key], abs=1e-6)
    for old, new in zip(baseline['flexible_tasks'], optimal['flexible_tasks']):
        assert old['served_kwh'] == pytest.approx(new['served_kwh'])
        assert all(a['hour'] >= 18 for a in old['allocations'])
        assert all(6 <= a['hour'] < 18 for a in new['allocations'] if a['served_kwh'] > 1e-6)


def test_storm_cannot_maintain_reserve_even_with_no_flexible_work():
    inputs = load_inputs('storm')
    result = optimizer.optimize(inputs)
    critical_only = simulate_baseline(replace(inputs, tasks=()))
    assert result['status'] == 'RESERVE_AT_RISK'
    assert result['metrics']['min_soc_kwh'] == pytest.approx(critical_only['metrics']['min_soc_kwh'])
    assert result['metrics']['flexible_deferred_kwh'] == pytest.approx(2.1)
    assert result['metrics']['critical_coverage_pct'] == 100


def test_rate_limited_shortfall_and_fully_deferred_flexible_work():
    inputs = load_inputs('high_demand')
    result = optimizer.optimize(inputs)
    lower_bound = sum(max(0, c-p-inputs.battery.max_discharge_kw) for c,p in zip(inputs.critical_kwh, inputs.pv_kwh))
    assert result['status'] == 'CRITICAL_SHORTAGE'
    assert result['metrics']['critical_unserved_kwh'] == pytest.approx(lower_bound)
    assert result['metrics']['critical_unserved_kwh'] == pytest.approx(1.32)
    assert result['metrics']['critical_shortage_hours'] == [20,21]
    assert result['metrics']['flexible_served_kwh'] == 0


def test_initial_below_reserve_is_counted():
    inputs = load_inputs('normal', {'initial_battery_kwh': 3})
    result = optimizer.optimize(inputs)
    assert result['status'] == 'RESERVE_AT_RISK'
    assert 0 in result['metrics']['reserve_breach_boundaries']
    critical_only = optimizer.optimize(replace(inputs, tasks=()))
    assert result['metrics']['min_soc_kwh'] >= critical_only['metrics']['min_soc_kwh']-1e-6


def test_critical_priority_over_flexible_tasks():
    task = FlexibleTask('optional', 1, 1, (0,), (1.,)+(0.,)*23)
    inputs = ModelInput(BatteryConfig(initial_battery_kwh=1, reserve_kwh=0, discharge_efficiency=1),
                        (0.,)*24, (0., 1.)+(0.,)*22, (task,))
    result = optimizer.optimize(inputs)
    assert result['metrics']['critical_unserved_kwh'] == 0
    assert result['metrics']['flexible_served_kwh'] == 0
    assert simulate_baseline(inputs)['metrics']['critical_unserved_kwh'] == 1


def test_repeated_requests_are_deterministic():
    inputs = load_inputs('scheduling')
    a,b = optimizer.optimize(inputs), optimizer.optimize(inputs)
    assert a == b


@pytest.mark.parametrize('scenario,same_work', [('scheduling',True), ('storm',False)])
def test_comparison_reports_computed_improvements_and_work_tradeoffs(scenario, same_work):
    result = compare_schedules(load_inputs(scenario))
    comparison = result['comparison']
    assert comparison['same_flexible_work_completed'] is same_work
    assert comparison['battery_preserved_at_midnight_kwh'] == pytest.approx(
        result['optimized']['hourly'][-1]['soc_end_kwh']-result['baseline']['hourly'][-1]['soc_end_kwh'])
    if scenario == 'scheduling':
        assert comparison['heuristic_matches_optimizer_metrics'] is True
        assert comparison['evening_minimum_improvement_kwh'] == pytest.approx(2.210526315789473)


def test_optimizer_can_improve_on_greedy_with_constrained_windows():
    # Greedy uses the brightest slot for the flexible-window task, leaving
    # a tightly constrained task drawing on storage. MILP considers both.
    a = FlexibleTask('wide_window', 1, 1, (10,11), (0.,)*10+(1.,)+(0.,)*13)
    b = FlexibleTask('narrow_window', 1, 1, (11,), (0.,)*11+(1.,)+(0.,)*12)
    inputs = ModelInput(BatteryConfig(initial_battery_kwh=1, battery_capacity_kwh=2, reserve_kwh=1),
                        (0.,)*10+(1.,1.1)+(0.,)*12, (0.,)*24, (a,b))
    heuristic, optimal = sunshine_first(inputs), optimizer.optimize(inputs)
    assert_physics(inputs, optimal)
    assert heuristic['metrics']['flexible_served_kwh'] == pytest.approx(2)
    assert optimal['metrics']['flexible_served_kwh'] == pytest.approx(2)
    assert optimal['metrics']['conversion_loss_kwh'] < heuristic['metrics']['conversion_loss_kwh']-.09


def test_impossible_task_energy_is_deferred_without_violating_window():
    task = FlexibleTask('too_much_work', 2, 1, (12,), (0.,)*12+(1.,)+(0.,)*11)
    inputs = ModelInput(BatteryConfig(), (5.,)*24, (0.,)*24, (task,))
    result = optimizer.optimize(inputs)
    assert_physics(inputs, result)
    assert result['metrics']['flexible_served_kwh'] == pytest.approx(1)
    assert result['metrics']['flexible_deferred_kwh'] == pytest.approx(1)


def test_flexible_service_respects_reserve_before_terminal_energy():
    task = FlexibleTask('optional', 2, 1, (11,12), (0.,)*11+(1.,1.)+(0.,)*11)
    inputs = ModelInput(BatteryConfig(initial_battery_kwh=4, reserve_kwh=4),
                        (0.,)*11+(1.,)+(0.,)*12, (0.,)*24, (task,))
    result = optimizer.optimize(inputs)
    assert result['metrics']['flexible_served_kwh'] == pytest.approx(1)
    assert result['metrics']['min_soc_kwh'] >= 4-1e-6


def test_claimed_optimum_with_corrupt_flows_is_rejected(monkeypatch):
    real_solver = scipy.optimize.milp
    def corrupt(*args, **kwargs):
        result = real_solver(*args, **kwargs)
        result.x[0] = float('nan')
        return result
    monkeypatch.setattr(scipy.optimize, 'milp', corrupt)
    with pytest.raises(NumericalError, match='verification'):
        optimizer.optimize(load_inputs('normal'))


@pytest.mark.parametrize('status,code', [(1,'SOLVER_TIME_LIMIT'), (2,'NUMERICAL_ERROR'), (3,'NUMERICAL_ERROR'), (4,'NUMERICAL_ERROR')])
def test_solver_failure_is_not_a_risk_result(monkeypatch, status, code):
    monkeypatch.setattr(scipy.optimize, 'milp', lambda *a,**kw: SimpleNamespace(status=status, success=False, x=None))
    with pytest.raises((optimizer.SolverError, NumericalError)) as err:
        optimizer.optimize(load_inputs('normal'))
    assert err.value.code == code


def test_total_budget_is_shared_between_stages(monkeypatch):
    times = iter([0., 6.])
    monkeypatch.setattr(optimizer, 'monotonic', lambda: next(times))
    with pytest.raises(optimizer.SolverError, match='budget'):
        optimizer.optimize(load_inputs('normal'))


@pytest.mark.parametrize('seed', range(8))
def test_varied_physical_inputs(seed):
    rng = random.Random(seed)
    inputs = ModelInput(BatteryConfig(initial_battery_kwh=rng.uniform(0,20), reserve_kwh=rng.uniform(0,5),
                                     charge_efficiency=rng.uniform(.65,1), discharge_efficiency=rng.uniform(.65,1),
                                     max_charge_kw=rng.uniform(0,4), max_discharge_kw=rng.uniform(0,4)),
                        tuple(rng.uniform(0,3) if 6<=h<18 else 0 for h in range(24)),
                        tuple(rng.uniform(0,1) for _ in range(24)))
    assert_physics(inputs, optimizer.optimize(inputs))
