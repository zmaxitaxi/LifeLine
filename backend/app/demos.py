"""Input-only demonstration cases. Every displayed result is freshly solved."""
from .models import SimulationRequest


def competing_windows(catalog):
    equipment=[e.model_dump() for e in catalog.critical_equipment]
    equipment += [dict(id='shared_device_charging',name='Shared device charging (synthetic aggregate)',category='flexible',
        max_power_kw=.6,required_energy_kwh=1.8,allowed_hours=list(range(8,21)),
        baseline_allocations=[{'hour':h,'requested_kwh':.6} for h in (18,19,20)],divisible=True),
        dict(id='reserve_tank_transfer',name='Reserve-tank transfer (postponable, illustrative)',category='flexible',
        max_power_kw=1.,required_energy_kwh=2.,allowed_hours=[11,12,13,14],
        baseline_allocations=[{'hour':h,'requested_kwh':1.} for h in (11,12)],divisible=True)]
    request=SimulationRequest(scenario='scheduling',equipment=equipment,weather_dataset='kisumu-2025-01-14',
        pv_capacity_kw=1.5,battery_capacity_kwh=8.,initial_battery_kwh=7.,reserve_kwh=4.8,max_discharge_kw=.4,
        cloud_factors=[1.]*24)
    return {'name':'Competing windows and limited battery output',
        'description':'Synthetic clinic requirements with historical NASA POWER irradiance. Device charging competes with a daytime water-transfer window on a limited battery output. No clinic has validated these inputs.',
        'limitations':['Only postpone water transfer when the operator has verified adequate essential water stock; tank levels are not modeled.',
                       'Both tasks are interruptible energy aggregates. No laundry, pumping or medical device cycle is validated.',
                       'The sunshine-first benchmark is input-order-sensitive. More sophisticated deadline-aware rules may close the gap.',
                       'This complements the original equal-work battery-reserve demo; unequal work completion must not be presented as an equal-work battery saving.'],
        'request':request.model_dump(exclude_unset=True)}
