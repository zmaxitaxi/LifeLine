"""Offline conversation tools. Every answer is grounded in a fresh model run.

This is deliberately identified as a local, rule-based assistant, not an LLM.
Unrecognized requests ask a question instead of inventing equipment or facts.
"""

import re
from typing import Annotated, Literal
from pydantic import Field, field_serializer
from .models import StrictModel, SimulationRequest, SimulationResponse


class PlanningQuestion(StrictModel):
    kind: Literal['intent', 'equipment', 'deadline', 'duration', 'power', 'start', 'battery']
    prompt: str
    task_id: str | None = None
    equipment_name: str = ''
    power_w: Annotated[float, Field(gt=0, le=100000)] | None = None
    deadline: Annotated[int, Field(ge=1, le=24)] = 12
    duration_h: Annotated[int, Field(ge=1, le=24)] | None = None


class AssistantRequest(StrictModel):
    message: Annotated[str, Field(min_length=1, max_length=2000)]
    plan: SimulationRequest
    pending: PlanningQuestion | None = None


class AssistantResponse(StrictModel):
    mode: Literal['offline'] = 'offline'
    message: str
    question: PlanningQuestion | None = None
    request: SimulationRequest | None = None
    result: SimulationResponse | None = None
    tools_used: list[str] = []

    @field_serializer('request')
    def serialize_request(self, value):
        # Omitted overrides are valid; explicit null overrides are not. Keep
        # the returned request suitable for exact replay by every client.
        return value.model_dump(exclude_unset=True) if value is not None else None


def question(kind, prompt, **context):
    return AssistantResponse(message=prompt, question=PlanningQuestion(kind=kind, prompt=prompt, **context))


def number(text):
    match = re.search(r'(?<![\w.])-?\d+(?:\.\d+)?(?![\w.])', text)
    return float(match.group()) if match else None


def deadline(text):
    if 'noon' in text:
        return 12
    if 'midnight' in text:
        return 24
    match = re.search(r'(?:before|by)\s+(\d{1,2})(?::00)?\s*(am|pm)?\b', text)
    if not match:
        return None
    hour = int(match[1])
    if match[2]:
        if not 1 <= hour <= 12:
            return None
        hour = hour % 12 + (12 if match[2] == 'pm' else 0)
    return hour if 1 <= hour <= 24 else None


def revise(plan, **changes):
    # Revalidate all changes; model_copy(update=...) would bypass validation.
    return SimulationRequest.model_validate(plan.model_dump(exclude_unset=True) | changes)


def prepare(body: AssistantRequest, catalog):
    """Return a question, a new request, or candidate fixed-hour requests."""
    text = body.message.strip().lower().replace('’', "'")
    plan = body.plan
    config = catalog.resolve(plan)
    equipment = [e.model_dump() for e in catalog.equipment_for(plan, config)]
    pending = body.pending
    value = number(text)

    if pending and pending.kind in ('power', 'duration', 'start') and not pending.task_id:
        context = dict(equipment_name=pending.equipment_name, deadline=pending.deadline)
        if pending.kind == 'power':
            rating = re.search(r'(-?\d+(?:\.\d+)?)\s*(kw|kilowatts?|watts?|w)\b', text)
            watts = float(rating[1]) if rating else value
            if watts is not None and rating and rating[2].startswith(('kw', 'kilowatt')):
                watts *= 1000
            if watts is None or not 0 < watts <= 100000:
                return question('power', 'What is the equipment power in watts? Use a number greater than zero from its label.', **context)
            return question('duration', 'How many whole hours must it run? This planner checks hourly energy; it cannot validate sterilization cycles.', power_w=watts, **context)
        if pending.kind == 'duration':
            runtime = re.search(r'(-?\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h)\b', text)
            value = float(runtime[1]) if runtime else value
            if value is None or not value.is_integer() or not 1 <= value <= pending.deadline or 'minute' in text:
                return question('duration', f'Please give a whole number of hours between 1 and {pending.deadline}. Shorter appliance cycles need a separate check.', power_w=pending.power_w, **context)
            return question('start', 'What is the earliest hour this equipment can start? Use local whole-hour time, for example 08:00.',
                            power_w=pending.power_w, duration_h=int(value), **context)
        start_match = re.fullmatch(r'\s*(\d{1,2})(?::00)?\s*(am|pm)?\s*', text)
        earliest = int(start_match[1]) if start_match else None
        if earliest is not None and start_match[2]:
            earliest = earliest % 12 + (12 if start_match[2] == 'pm' else 0) if 1 <= earliest <= 12 else None
        if earliest is None or pending.duration_h is None or not 0 <= earliest <= pending.deadline - pending.duration_h:
            return question('start', 'Please choose a whole-hour start that leaves enough time before the deadline, for example 08:00.',
                            power_w=pending.power_w, duration_h=pending.duration_h, **context)
        if pending.power_w is None or len(equipment) >= 20:
            return question('intent', 'Please review the equipment list in Detailed mode before adding another item.')
        # Keep the new requirement fixed and consecutive. Never pass a medical
        # cycle to the divisible-work optimizer. Compare actual hourly checks.
        duration = pending.duration_h
        name = pending.equipment_name or 'Additional equipment'
        task_id = 'assistant_equipment'
        while any(e['id'] == task_id for e in equipment):
            task_id += '_new'
        candidates = []
        for start in range(earliest, pending.deadline - duration + 1):
            item = dict(id=task_id, name=name, category='critical', power_kw=pending.power_w / 1000,
                        required_hours=list(range(start, start + duration)))
            candidates.append(revise(plan, equipment=equipment + [item], additional_critical_kw=0.) if plan.scenario == 'high_demand'
                              else revise(plan, equipment=equipment + [item]))
        return candidates

    if pending and pending.kind == 'battery':
        if value is None or not 0 <= value <= 100:
            return question('battery', 'What is the battery charge, as a percentage from 0 to 100?')
        return revise(plan, initial_battery_kwh=config.battery_capacity_kwh * value / 100)

    matched = None
    if pending and pending.task_id:
        matched = next((e for e in equipment if e['id'] == pending.task_id), None)
    if matched is None:
        aliases = {'charging': 'device_charging', 'laundry': 'auxiliary_laundry',
                   'refrigerator': 'vaccine_refrigerator', 'fridge': 'vaccine_refrigerator',
                   'lighting': 'essential_lighting', 'communications': 'communications'}
        matched = next((e for e in equipment if e['name'].split(' (')[0].lower() in text
                        or any(alias in text and e['id'] == task_id for alias, task_id in aliases.items())), None)

    if re.search(r'sterili[sz]|autoclave', text) and matched is None:
        return question('power', 'The sterilizer is not in this clinic’s equipment list. What is its rated power in watts?',
                        equipment_name='Sterilizer (hourly energy approximation)', deadline=deadline(text) or 12)

    if matched and (pending or re.search(r'\b(before|by|run|need|change|hours?|duration)\b', text)):
        if matched['category'] == 'critical':
            return question('intent', 'This equipment has fixed essential hours. Use “Change a requirement” to edit those hours explicitly; I will not move them automatically.')
        end = deadline(text)
        if pending and pending.kind == 'deadline' and end is None and value is not None and value.is_integer() and 1 <= value <= 24:
            end = int(value)
        duration_match = re.search(r'(-?\d+(?:\.\d+)?)\s*(?:hours?|hrs?)\b', text)
        if pending and pending.kind == 'duration' and value is not None:
            duration_match_value = value
        else:
            duration_match_value = float(duration_match[1]) if duration_match else None
        if duration_match_value is not None:
            if not 0 < duration_match_value <= 24:
                return question('duration', 'How many hours should this equipment run? Use a number greater than zero and no more than 24.', task_id=matched['id'])
            matched['required_energy_kwh'] = matched['max_power_kw'] * duration_match_value
        if end is not None:
            allowed = [h for h in matched['allowed_hours'] if h < end]
            if not allowed:
                return question('deadline', 'There are no allowed operating hours before that time. Which later deadline should I check?', task_id=matched['id'])
            matched['allowed_hours'] = allowed
        if end is None and duration_match_value is None:
            return question('duration', f'How many hours should {matched["name"].split(" (")[0]} run?', task_id=matched['id'])
        # Rebuild the existing request within the allowed window. Missing energy
        # remains a real, visible deficit rather than an invalid allocation.
        remaining = matched['required_energy_kwh']
        matched['baseline_allocations'] = []
        for h in matched['allowed_hours']:
            amount = min(matched['max_power_kw'], remaining)
            if amount > 1e-10:
                matched['baseline_allocations'].append(dict(hour=h, requested_kwh=amount))
            remaining = max(0., remaining - amount)
        changes = dict(equipment=equipment)
        if plan.scenario == 'high_demand':
            changes['additional_critical_kw'] = 0.
        return revise(plan, **changes)

    if 'battery' in text and re.search(r'\b(at|charge|charged|set|only|has)\b|%', text):
        if value is not None and '%' in text and 0 <= value <= 100:
            return revise(plan, initial_battery_kwh=config.battery_capacity_kwh * value / 100)
        return question('battery', 'What is the battery charge, as a percentage from 0 to 100?')

    if re.search(r'cloud|worse|less sun|25%|quarter', text):
        if re.search(r'\b(days|week|weeks)\b', text):
            return question('intent', 'This planner checks one 24-hour day at a time. Should I test a single day with less sunshine?')
        factors = plan.cloud_factors if plan.cloud_factors is not None else catalog.preset(plan.scenario).cloud_factors
        return revise(plan, cloud_factors=[v * .25 for v in factors])

    if re.search(r'\b(add|new|need|run|schedule|change|set|watts?|kw|hours?)\b', text):
        return question('equipment', 'Which equipment requirement should change? You can say “Run laundry for 3 hours” or use “Change a requirement” to enter its power and hours.')
    if re.search(r'tomorrow|enough|electricity|plan|reliab|battery|power|forecast', text):
        return plan
    return question('intent', 'Should I check tomorrow’s electricity, test cloudier weather, or check the battery? You can also say “Run laundry for 3 hours”.')


def summarize(result: SimulationResponse):
    metrics = result.optimized.metrics
    if metrics.critical_unserved_kwh > 1e-6:
        answer = 'There isn’t enough power for all essential equipment in this model. Changing the schedule alone cannot meet every requirement.'
    elif metrics.critical_requested_kwh <= 1e-6:
        answer = 'No essential equipment requirements are entered. Add them before assessing essential power.'
    elif metrics.reserve_breach_boundaries:
        answer = 'Essential equipment receives power in this model, but the battery may run too low.'
    elif metrics.flexible_deferred_kwh > 1e-6:
        answer = 'Essential equipment receives power in this model, but some other work cannot be completed.'
    else:
        answer = 'Essential equipment and the requested work have enough power in this model.'
    return answer + ' Live forecasting is unavailable; this checks an example day, not tomorrow’s actual conditions.'
