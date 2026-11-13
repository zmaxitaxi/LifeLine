from dataclasses import replace
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.demos import competing_windows
from app.models import SimulationRequest
from app.scenarios import load_catalog
from app.comparison import compare_schedules
from test_energy_balance import assert_physics


def test_competing_windows_complete_same_requested_work_with_less_unmet_energy():
    catalog=load_catalog()
    demo=competing_windows(catalog)
    request=SimulationRequest.model_validate(demo['request'])
    inputs=catalog.build_inputs(request,catalog.resolve(request))
    with TestClient(create_app()) as client:
        assert client.get('/api/demos/competing-windows').json()==demo
        response=client.post('/api/simulate',json=demo['request'])
        assert response.status_code==200
        result=response.json()
    b,h,o=[result[k]['metrics'] for k in ('baseline','heuristic','optimized')]
    for name in ('baseline','heuristic','optimized'):
        assert_physics(inputs,result[name])
        assert result[name]['metrics']['critical_unserved_kwh']==0
        assert not result[name]['metrics']['reserve_breach_boundaries']
        assert result[name]['metrics']['flexible_requested_kwh']==pytest.approx(3.8)
    assert o['flexible_deferred_kwh']==0
    assert b['flexible_deferred_kwh']==pytest.approx(1.03044)
    assert h['flexible_deferred_kwh']==pytest.approx(.330136)
    assert result['comparison']['same_flexible_work_completed'] is False
    assert o['min_soc_kwh']==pytest.approx(h['min_soc_kwh'])
    assert o['conversion_loss_kwh']<h['conversion_loss_kwh']
    # This is a rate/window bottleneck, not a claim of universal MILP superiority.
    unrestricted=compare_schedules(replace(inputs,battery=replace(inputs.battery,max_discharge_kw=4.)))
    assert unrestricted['heuristic']['metrics']['flexible_deferred_kwh']==0


def test_reversing_greedy_task_order_is_reported_as_a_possible_improvement():
    catalog=load_catalog();request=SimulationRequest.model_validate(competing_windows(catalog)['request'])
    inputs=catalog.build_inputs(request,catalog.resolve(request))
    reversed_result=compare_schedules(replace(inputs,tasks=tuple(reversed(inputs.tasks))))
    for name in ('baseline','heuristic','optimized'):
        assert_physics(replace(inputs,tasks=tuple(reversed(inputs.tasks))),reversed_result[name])
    assert reversed_result['heuristic']['metrics']['flexible_served_kwh']>=3.469864-1e-6
