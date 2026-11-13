from dataclasses import replace
import pytest
from app.energy_types import BatteryConfig, FlexibleTask, ModelInput
from app.model_demo import load_inputs
from app.solar_forecast import forecast_solar


@pytest.mark.parametrize('scenario,total', [('normal',30.645190302), ('storm',2.451615224), ('high_demand',30.645190302), ('scheduling',9.193557091)])
def test_forecast_calibration(scenario,total):
    inputs = load_inputs(scenario)
    assert sum(inputs.pv_kwh) == pytest.approx(total, abs=1e-6)
    assert all(v == 0 for h,v in enumerate(inputs.pv_kwh) if h<6 or h>=18)


def test_zero_overrides_and_bad_cross_fields():
    assert sum(load_inputs('normal', {'pv_capacity_kw':0}).pv_kwh) == 0
    with pytest.raises(ValueError): load_inputs('normal', {'battery_capacity_kwh':1})
    with pytest.raises(ValueError): load_inputs('normal', {'additional_critical_kw':0})
    with pytest.raises(ValueError): load_inputs('missing')
    with pytest.raises(ValueError): load_inputs('normal', {'typo':1})


def test_loading_is_independent_of_current_directory(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    assert len(load_inputs('normal').pv_kwh) == 24


@pytest.mark.parametrize('bad', [True, None, -1, float('nan'), float('inf')])
def test_bad_numeric_values_rejected(bad):
    with pytest.raises(ValueError): BatteryConfig(initial_battery_kwh=bad)
    with pytest.raises(ValueError): forecast_solar(bad, (1.,)*24)


def test_profile_and_task_validation():
    with pytest.raises(ValueError): forecast_solar(5, (1.,)*23)
    with pytest.raises(ValueError): forecast_solar(5, (1.1,)*24)
    with pytest.raises(ValueError): ModelInput(BatteryConfig(), (0.,)*23, (0.,)*24)
    with pytest.raises(ValueError): FlexibleTask('bad', 1, 1, (24,), (0.,)*24)
    with pytest.raises(ValueError): FlexibleTask('bad', 1, 1, (1,1), (0.,)*24)
    with pytest.raises(ValueError): FlexibleTask('bad', 1, 1, (1,), (1.,)+(0.,)*23)
    with pytest.raises(ValueError): FlexibleTask('bad', .5, 1, (1,), (0.,1.)+(0.,)*22)
    task = load_inputs('normal').tasks[0]
    with pytest.raises(ValueError): replace(load_inputs('normal'), tasks=(task,task))


def test_critical_profiles_and_demand_change_are_explicit():
    normal, high = load_inputs('normal'), load_inputs('high_demand')
    assert normal.pv_kwh == high.pv_kwh
    assert normal.battery == high.battery
    assert sum(normal.critical_kwh) == pytest.approx(5.34)
    assert [h for h,(a,b) in enumerate(zip(normal.critical_kwh, high.critical_kwh)) if a!=b] == [20,21]
    assert load_inputs('storm').battery.initial_battery_kwh == 6
