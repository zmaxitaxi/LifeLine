"""Qualified nurse-readable results are checked, not blocked by vocabulary."""
import json
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.planning_conversation import validate_reply_content, collect_reply_facts
from app.planning_models import PlanningState
from app.planning_state import PlanningError
from test_planning_state import BASE, create, post, initial
from test_weather_forecast import service_for


def checked_state(client, state):
    return PlanningState.model_validate_json(json.dumps(post(client,
        f"{BASE}/{state['id']}/recompute", {'expected_revision': state['revision']})))


@pytest.mark.parametrize('message', [
    'In this model, essential electricity needs are covered, with an essential shortfall of 0.000 kWh.',
    'Under the forecast assumptions, we have sufficient electricity for essential needs, with 0.000 kWh unserved.',
    'The optimized schedule covers essential demand in this model. This does not establish real-world availability.',
    'The model can meet essential needs with an essential shortfall of 0.000 kWh.',
    'The configured battery capacity is 4 kWh. In this model, essential demand is covered with an essential shortfall of 0.000 kWh.',
])
def test_true_qualified_coverage_is_allowed_without_forcing_engineering_phrasing(message):
    service, _ = service_for()
    with TestClient(create_app(forecast_service=service)) as client:
        state = checked_state(client, create(client))
        assert state.computed_plan.simulation.baseline.metrics.critical_unserved_kwh == 0.
        assert validate_reply_content(message, state, 'Explain the result.', ['explain_current_plan']) == message


@pytest.mark.parametrize('message', [
    'In this model, essential needs are covered.',
    'According to the model, we have sufficient electricity for essential needs.',
    'The model solves the essential shortage.',
])
def test_qualification_cannot_turn_actual_unmet_demand_into_positive_coverage(message):
    service, _ = service_for()
    with TestClient(create_app(forecast_service=service)) as client:
        body = initial()
        body['midnight_battery_kwh'] = 0.
        body['clinic'] |= {'pv_capacity_kw': 0., 'initial_battery_kwh': 0.}
        state = checked_state(client, post(client, BASE, body))
        assert state.computed_plan.simulation.baseline.metrics.critical_unserved_kwh > 0.
        with pytest.raises(PlanningError):
            validate_reply_content(message, state, 'Explain the result.', ['explain_current_plan'])


@pytest.mark.parametrize('message', [
    'Essential needs are covered.', 'We have sufficient electricity.',
    'The clinic is safe tomorrow.', 'The battery will last through the night.',
])
def test_unqualified_real_availability_or_safety_is_not_a_modeled_finding(message):
    service, _ = service_for()
    with TestClient(create_app(forecast_service=service)) as client:
        state = checked_state(client, create(client))
        with pytest.raises(PlanningError):
            validate_reply_content(message, state, 'Explain the result.', ['explain_current_plan'])


def test_pending_percentage_reading_is_sourced_but_not_adopted():
    service, _ = service_for()
    with TestClient(create_app(forecast_service=service)) as client:
        state = create(client)
        state = post(client, f"{BASE}/{state['id']}/energy-proposals", {
            'expected_revision': state['revision'], 'settings': {'battery_capacity_kwh': 12.},
            'current_battery_reading': {'energy_kwh': 2.4, 'measured_at': '2026-11-14T01:00:00Z'}})
        parsed = PlanningState.model_validate_json(json.dumps(state))
        assert state['current_battery_reading'] is None
        message = 'The pending current reading is 2.4 kWh, still unconfirmed and separate from starting energy.'
        assert validate_reply_content(message, parsed, 'Review the proposed reading.', ['propose_energy_settings']) == message
        assert '2.4 kWh' in collect_reply_facts(parsed)['energy_proposal']


@pytest.mark.parametrize('shortage', [False, True])
def test_negative_qualified_coverage_matches_actual_model_not_just_coverage_vocabulary(shortage):
    service, _ = service_for()
    with TestClient(create_app(forecast_service=service)) as client:
        body = initial()
        if shortage:
            body['midnight_battery_kwh'] = 0.
            body['clinic'] |= {'pv_capacity_kw': 0., 'initial_battery_kwh': 0.}
        state = checked_state(client, post(client, BASE, body))
        message='Under the modeled forecast and assumptions, essential demand is not met. This does not establish real-world availability or clinical safety.'
        assert (state.computed_plan.simulation.baseline.metrics.critical_unserved_kwh > 0.) == shortage
        if shortage:
            assert validate_reply_content(message,state,'Explain the result.',['explain_current_plan']) == message
        else:
            with pytest.raises(PlanningError):
                validate_reply_content(message,state,'Explain the result.',['explain_current_plan'])


@pytest.mark.parametrize('message,valid', [
    ('In the model, existing baseline essential demand is not met. The selected option covers essential demand.', True),
    ('In the model, existing baseline essential demand is covered. The selected option does not meet essential demand.', False),
])
def test_selected_explanation_resolves_explicit_baseline_before_implicit_selected_context(message,valid):
    service,_=service_for()
    with TestClient(create_app(forecast_service=service)) as client:
        body=initial();body['midnight_battery_kwh']=6.
        body['clinic']|={'battery_capacity_kwh':8.,'initial_battery_kwh':6.,'reserve_kwh':1.,'max_discharge_kw':.4,
            'equipment':[{'id':'evening','name':'Evening essential equipment','category':'critical','power_kw':1.,'required_hours':[19,20]}]}
        state=post(client,BASE,body)
        state=post(client,f"{BASE}/{state['id']}/recompute",{'expected_revision':state['revision'],'include_recovery':True})
        plan=state['computed_plan'];assert plan['simulation']['baseline']['metrics']['critical_unserved_kwh']>0
        option=next(o for o in plan['recovery']['options'] if o['kind']=='output' and o['metrics']['essential_unserved_kwh']<=1e-6)
        state=post(client,f"{BASE}/{state['id']}/recovery-selection",{'expected_revision':state['revision'],
            'input_revision':state['input_revision'],'generation':plan['generation'],'option_id':option['id']})
        state=PlanningState.model_validate_json(json.dumps(state))
        if valid:
            assert validate_reply_content(message,state,'Explain selected plan.',['explain_current_plan'])==message
        else:
            with pytest.raises(PlanningError):validate_reply_content(message,state,'Explain selected plan.',['explain_current_plan'])


@pytest.mark.parametrize('shortage', [False, True])
def test_current_plan_negative_have_enough_uses_verified_shortfall(shortage):
    service,_=service_for()
    with TestClient(create_app(forecast_service=service)) as client:
        body=initial()
        if shortage:
            body['midnight_battery_kwh']=0.;body['clinic']|={'pv_capacity_kw':0.,'initial_battery_kwh':0.}
        state=checked_state(client,post(client,BASE,body))
        message='The current plan shows that the clinic will not have enough energy to meet its essential needs tomorrow.'
        if shortage:
            assert validate_reply_content(message,state,'Explain the result.',['explain_current_plan'])==message
        else:
            with pytest.raises(PlanningError):validate_reply_content(message,state,'Explain the result.',['explain_current_plan'])
