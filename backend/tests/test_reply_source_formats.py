"""Regression cases found by genuine model runs, including false positives."""
import json
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.planning_models import PlanningState
from app.planning_conversation import validate_reply_content, reply_context, collect_reply_facts
from app.planning_state import PlanningError
from test_planning_state import create, post, BASE
from test_weather_forecast import service_for


def test_essential_coverage_is_distinct_from_unfinished_flexible_work_and_reserve():
    from app.demo_weather import DemoWeatherService
    with TestClient(create_app(forecast_service=DemoWeatherService())) as client:
        forecast=client.get('/api/forecast?latitude=-0.0917&longitude=34.768').json()
        state=post(client,BASE,{'selected_clinic_id':'source-regression','clinic_name':'Illustrative source regression',
            'location':{'latitude':-.0917,'longitude':34.768},'timezone':forecast['timezone'],
            'planning_date':forecast['days'][1]['date'],'midnight_battery_kwh':6.,'clinic':{'scenario':'scheduling'}})
        state=post(client,f"{BASE}/{state['id']}/recompute",{'expected_revision':state['revision'],'sunshine_factor':.5,'include_recovery':True})
        parsed=model_state(state)
        facts=collect_reply_facts(parsed,('recompute_clinic_plan',))
        task=next(t for t in parsed.computed_plan.simulation.optimized.flexible_tasks if t.task_id=='auxiliary_laundry')
        for allocation in task.allocations:
            if allocation.served_kwh>1e-6:
                assert f'{allocation.hour:02d}:00–{allocation.hour+1:02d}:00 ({allocation.served_kwh:.3f} kWh supplied)' in facts['optimized_schedule']
        assert 'hourly model slots' in facts['optimized_schedule']
        messages=(
            'A test battery capacity of 10 kWh meets modeled essential demand but leaves 2.100 kWh of flexible work unfinished.',
            'A test battery storage capacity of 10 kWh (up from 8 kWh) models essential demand as met but leaves 2.100 kWh of flexible work unfinished, with lowest stored energy at 4.172 kWh.',
            'A test solar capacity of 3.5 kW has a lowest stored battery level of 4.975 kWh above its 4.800 kWh reserve target.',
            'The optimized schedule raises the battery minimum to 4.172 kWh.',
        )
        for message in messages:
            assert validate_reply_content(message,parsed,'Compare recovery options.',('recompute_clinic_plan',))==message
        for bad in ('A test battery capacity of 10 kWh meets modeled essential demand and all flexible requirements.',
                    'A test battery capacity of 10 kWh meets modeled essential demand but all flexible work is completed.',
                    'The optimized schedule lowers the battery minimum to 4.172 kWh.',
                    'A test solar capacity of 3.5 kW has a lowest stored battery level of 4.800 kWh above its 4.800 kWh reserve target.'):
            with pytest.raises(PlanningError):
                validate_reply_content(bad,parsed,'Compare recovery options.',('recompute_clinic_plan',))


def model_state(value):
    return PlanningState.model_validate_json(json.dumps(value))


def test_verified_natural_calendar_dates_and_parenthesized_units_are_allowed():
    with TestClient(create_app()) as client:
        state=model_state(create(client))
    value=state.planning_date
    message=f'The selected date is {value.strftime("%B")} {value.day}, {value.year}.'
    assert validate_reply_content(message,state,'Which date?')==message
    message=f'The selected date is {value.day} {value.strftime("%B %Y")}.'
    assert validate_reply_content(message,state,'Which date?')==message
    message=f'The configured output limit is ({state.energy_settings.max_discharge_kw:g} kW).'
    assert validate_reply_content(message,state,'Which output limit?')==message
    for bad in ('The selected date is November 15, 2039.','The selected date is February 31, 2026.',
                'The configured output limit is (9999 kW).'):
        with pytest.raises(PlanningError):
            validate_reply_content(bad,state,'Tell me the settings.')


def test_denials_do_not_become_assurances_or_false_confirmation_claims():
    with TestClient(create_app()) as client:
        state=model_state(create(client))
    for good in ('This is an electrical planning estimate only and does not establish clinical safety or guarantee availability.',
                 "I can't offer a clinical or availability guarantee.",
                 'It does not decide whether the clinic can provide clinical services safely.',
                 'None of these changes has been adopted.'):
        assert validate_reply_content(good,state,'What are the limits?')==good
    for bad in ('This model does not establish clinical safety, but the clinic is safe to operate.',
                'It does not decide whether the clinic can operate safely, but the clinic is clinically safe.',
                'These changes have been adopted.', 'The model guarantees availability.'):
        with pytest.raises(PlanningError):
            validate_reply_content(bad,state,'What are the limits?')


def test_output_and_storage_options_bind_their_own_tested_size_and_result():
    service,_=service_for()
    with TestClient(create_app(forecast_service=service)) as client:
        state=create(client)
        # Use an output bottleneck with ample energy; all sizes are real solves.
        body={key:state[key] for key in ('selected_clinic_id','clinic_name','location','planning_date','timezone')}
        body.update(midnight_battery_kwh=6.,clinic={'scenario':'normal','battery_capacity_kwh':8.,
            'initial_battery_kwh':6.,'reserve_kwh':1.,'pv_capacity_kw':1.5,'max_discharge_kw':.4,
            'equipment':[{'id':'evening','name':'Essential evening equipment','category':'critical','power_kw':1.,'required_hours':[19,20]}]})
        state=post(client,BASE,body)
        state=post(client,f"{BASE}/{state['id']}/recompute",{'expected_revision':state['revision'],'include_recovery':True})
        parsed=model_state(state)
        good='The tested battery output alternative at 1.4 kW meets the modeled essential demand and leaves 0.000 kWh of essential shortfall.'
        assert validate_reply_content(good,parsed,'Compare the tested alternatives.',('recompute_clinic_plan',))==good
        criteria='Test output: 1.4 kW meets modeled essential demand and is ranked first under the existing criteria.'
        assert validate_reply_content(criteria,parsed,'Compare the tested alternatives.',('recompute_clinic_plan',))==criteria
        negative='The tested battery capacity alternative at 10 kWh did not resolve the modeled essential shortfall of 1.200 kWh.'
        assert validate_reply_content(negative,parsed,'Compare the tested alternatives.',('recompute_clinic_plan',))==negative
        shared='A test battery of 10 kWh and a test solar array of 2 kW each leave 1.200 kWh of essential shortfall.'
        assert validate_reply_content(shared,parsed,'Compare the tested alternatives.',('recompute_clinic_plan',))==shared
        for message in ('Under the current baseline and optimized schedules, 1.200 kWh of essential evening demand (19:00 and 20:00) goes unserved.',
                        'I can compare a larger battery output limit or a larger battery capacity to see whether either closes the 1.200 kWh gap.'):
            assert validate_reply_content(message,parsed,'Explain the result.',('recompute_clinic_plan',))==message
        for bad in ('The tested battery output alternative at 0.9 kW meets the modeled essential demand.',
                    'The tested battery output alternative at 1.4 kW leaves 0.200 kWh of essential shortfall.',
                    'A test output of 1.4 kW and a test solar array of 2 kW each leave 0.000 kWh of essential shortfall.'):
            with pytest.raises(PlanningError):
                validate_reply_content(bad,parsed,'Compare the tested alternatives.',('recompute_clinic_plan',))
        option=next(o for o in parsed.computed_plan.recovery.options if o.kind=='output' and o.config.max_discharge_kw==1.4)
        parsed.selected_recovery_intervention_id=option.id
        data=reply_context(parsed,('explain_current_plan',))['facts']['selected_option']
        assert data['lowest_stored_energy']==f'{option.metrics.minimum_battery_kwh:.3f} kWh'
        assert data['modeled_essential_demand_met'] is True
