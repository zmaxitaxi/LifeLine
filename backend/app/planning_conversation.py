"""Authored direct replies, optional scoped presentation and current-fact grounding."""
import json
import re
from typing import Annotated, Literal
from pydantic import Field, ValidationError
from .models import StrictModel
from .planning_state import PlanningError, equipment_from_draft, compile_clinic


class GroundedReply(StrictModel):
    message: Annotated[str, Field(min_length=1, max_length=6000)]
    fact_references: list[str] = []


class PresentationChoice(StrictModel):
    kind: Literal['conversation','activity_review','energy_review','calculation','explanation'] = 'conversation'
    option_ids: Annotated[list[Annotated[str, Field(min_length=1,max_length=120)]], Field(max_length=20)] = []
    show_schedule: bool = False


class UserReply(StrictModel):
    message: Annotated[str, Field(min_length=1,max_length=2400)]
    fact_references: Annotated[list[str], Field(max_length=40)] = []
    presentation: PresentationChoice = Field(default_factory=PresentationChoice)


def reply_definition():
    schema=UserReply.model_json_schema()
    definitions=schema.pop('$defs',{})
    def expand(value):
        if isinstance(value,list): return [expand(item) for item in value]
        if isinstance(value,dict):
            if '$ref' in value: return expand(definitions[value['$ref'].split('/')[-1]])
            return {key:expand(item) for key,item in value.items() if key not in ('title','default')}
        return value
    return dict(name='respond_to_user',description='Optionally send your natural reply with only the relevant review/result cards or schedule. Direct ordinary text is equally valid. Include only tested option IDs you actually want shown; omit cards for conversation, clarification or unevaluated ideas.',parameters=expand(schema))


def fact_references(state, calls):
    """Complete typed fact clauses prevent relabeling a solar figure as a deficit."""
    facts, required = {}, set()
    proposal = next((p for p in state.proposals if p.id == state.active_proposal_id), None)
    calculated = bool(calls) and calls[-1] in ('recompute_clinic_plan','explain_current_plan')
    if proposal and not calculated:
        draft = proposal.details
        facts['draft_details'] = f'Activity name: {draft.name}. Selected date: {state.planning_date.isoformat()}.'
        if draft.start_hour is not None:
            facts['draft_details'] += f' Draft start: {draft.start_hour:02d}:00 local time.'
        if draft.end_hour is not None:
            facts['draft_details'] += f' Draft end: {draft.end_hour:02d}:00 local time.'
        if draft.duration_hours is not None:
            facts['draft_details'] += f' Explicit activity duration: {draft.duration_hours} hours.'
        for item in draft.additional_equipment:
            facts['draft_details'] += f' Proposed device: {item.name}.'
            power=item.power_kw if item.category=='critical' else item.max_power_kw
            if power is not None:
                facts['draft_details'] += f' Device rated power: {power:g} kW.'
            if item.required_duration_hours is not None:
                facts['draft_details'] += f' Explicit device operating duration: {item.required_duration_hours} hours.'
            if item.required_energy_kwh is not None:
                facts['draft_details'] += f' Explicit device required energy: {item.required_energy_kwh:g} kWh.'
            elif item.category=='flexible' and item.required_duration_hours is not None:
                try:
                    parsed=equipment_from_draft(item)
                    facts['draft_details'] += f' Python-derived device energy requirement: {parsed.required_energy_kwh:g} kWh, still unconfirmed.'
                except ValidationError:
                    pass
        facts['draft_status'] = 'This activity is an unconfirmed draft; confirmed equipment requirements have not changed.'
        if proposal.missing_fields:
            field = proposal.missing_fields[0]
            labels = {'name':'the activity name','planning_date':'the selected clinic planning date','start_hour':'the local start time','end_hour':'the local end time','equipment_ids':'which existing equipment is needed, or whether none is needed','category':'whether the device is essential or optional','power_kw':'the device nameplate power rating','max_power_kw':'the device nameplate power rating','required_duration_hours':'how many whole hours the device must operate','required_hours':'the whole-hour slots when the device must run','allowed_hours':'the allowed whole-hour operating window','divisible':'whether the device work can be interrupted and resumed'}
            facts['missing_detail'] = 'Please provide ' + labels.get(field.rsplit('.',1)[-1], field.rsplit('.',1)[-1].replace('_', ' ')) + '.'
            required.add('missing_detail')
        else:
            facts['review_boundary'] = 'Review the draft and use the explicit confirm or reject controls; this conversation has not confirmed it.'
            required.add('review_boundary')
        return facts, required, set()
    if calculated and proposal:
        facts['unconfirmed_notice'] = 'The unconfirmed activity draft is not included in this calculation; review and confirm it before assessing its requirements.'
        required.add('unconfirmed_notice')
    if state.plan_status == 'failed':
        facts['calculation_status'] = 'No new verified electricity plan is available. Confirmed activities are preserved; retry the calculation when weather and the model are available.'
        required.add('calculation_status')
        return facts, required, set()
    plan = state.computed_plan
    if not plan or plan.input_revision != state.input_revision:
        facts['planning_status'] = 'The current planning state is available, but no current verified electricity calculation has been completed.'
        required.add('planning_status')
        return facts, required, set()
    metrics = plan.simulation.baseline.metrics
    facts['essential_summary'] = (f'For the existing baseline schedule in this modeled day, essential equipment requests {metrics.critical_requested_kwh:.3f} kWh; '
        f'{metrics.critical_unserved_kwh:.3f} kWh is unserved. Flexible work left unfinished is {metrics.flexible_deferred_kwh:.3f} kWh.')
    facts['battery_summary'] = (f'The lowest modeled battery level is {metrics.min_soc_kwh:.3f} kWh, '
        f'against the configured {plan.simulation.effective_config.reserve_kwh:.3f} kWh reserve target.')
    facts['weather_basis'] = f'This uses the selected {state.planning_date.isoformat()} forecast and {plan.sunshine_factor*100:g}% of its irradiation, with confirmed clinic requirements retained.'
    facts['scope'] = 'These are electrical model comparisons, not clinical safety or availability guarantees. Hypothetical equipment changes have not been adopted.'
    required.update(('essential_summary', 'scope'))
    options = set()
    if calls and calls[-1] == 'explain_current_plan' and state.selected_recovery_intervention_id:
        if not plan.recovery:
            raise PlanningError('STALE_RESULT','The selected comparison is no longer available; calculate and review a current plan.',409)
        selected = next((o for o in plan.recovery.options + [plan.recovery.existing] if o.id == state.selected_recovery_intervention_id),None)
        if selected is None:
            raise PlanningError('STALE_RESULT','The selected comparison does not belong to the current result.',409)
        m = selected.metrics
        facts['selected_option'] = (f'The exact selected comparison is {selected.label}. Its remaining essential shortfall is {m.essential_unserved_kwh:.3f} kWh, '
            f'original flexible work unfinished is {m.flexible_unfinished_kwh:.3f} kWh, and lowest stored battery energy is {m.minimum_battery_kwh:.3f} kWh.')
        changes = ', '.join(f'{c.field.replace("_", " ")}: {c.before:g} {c.unit} to {c.after:g} {c.unit}' for c in selected.infrastructure_changes)
        if changes:
            facts['selected_option'] += ' Hypothetical selected changes: ' + changes + '.'
        required.add('selected_option')
        return facts, required, options
    if plan.recovery:
        recovery = plan.recovery
        for option in recovery.options:
            key = f'option_{option.kind}'
            if key in options:
                continue  # compact view: highest-ranked tested alternative per kind
            m = option.metrics
            changes = ', '.join(f'{change.field.replace("_", " ")}: {change.before:g} {change.unit} to {change.after:g} {change.unit}' for change in option.infrastructure_changes)
            text = (f'Tested option: {option.label}. It leaves {m.essential_unserved_kwh:.3f} kWh of essential energy unserved '
                f'and {m.flexible_unfinished_kwh:.3f} kWh of original flexible work unfinished; the lowest battery level is {m.minimum_battery_kwh:.3f} kWh.')
            if changes:
                text += ' Hypothetical changes: ' + changes + '.'
            if m.explicitly_postponed_kwh:
                text += f' Explicitly postponed work is {m.explicitly_postponed_kwh:.3f} kWh; it remains unfinished.'
            facts[key] = text
            options.add(key)
        facts['ranked_option'] = f'The existing recovery comparison ranks {next((o.label for o in recovery.options if o.id == recovery.recommended_option_id), recovery.recommended_option_id)} first under its stated criteria.'
    return facts, required, options


NUMBER_WORDS={'zero':0.,'one':1.,'two':2.,'three':3.,'four':4.,'five':5.,'six':6.,'seven':7.,'eight':8.,'nine':9.,'ten':10.,'eleven':11.,'twelve':12.,'half':.5}
QUANTITY = re.compile(r'(?<![\w.])(-?\d+(?:\.\d+)?|zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|half)\s*(kWh|kilowatt[ -]?hours?|Wh|watt[ -]?hours?|kW|kilowatts?|W|watts?|%|percent|hours?|hrs?|h)(?=$|[\s.,;:!?])', re.I)
DATE = re.compile(r'\b\d{4}-\d{2}-\d{2}\b')
TIME = re.compile(r'\b(\d{1,2})(?::(00))?\s*(AM|PM)\b|\b(\d{1,2}):00\b', re.I)


def quantities(text):
    values = []
    covered = []
    for match in DATE.finditer(text):
        values.append((match.group(), 'date', match.start(), match.end()))
        covered.append((match.start(), match.end()))
    for match in TIME.finditer(text):
        value = int(match[1] or match[4])
        if match[3]:
            value = value % 12 + (12 if match[3].upper() == 'PM' else 0)
        values.append((float(value), 'local_hour', match.start(), match.end()))
        covered.append((match.start(), match.end()))
    for match in QUANTITY.finditer(text):
        unit = match[2].lower().replace(' ', '').replace('-', '')
        value = NUMBER_WORDS[match[1].casefold()] if match[1].casefold() in NUMBER_WORDS else float(match[1])
        if unit in ('w','watts','watt'):
            value /= 1000;unit = 'kw'
        elif unit in ('wh','watthour','watthours'):
            value /= 1000;unit = 'kwh'
        elif unit.startswith('kilowatt'):
            unit = 'kwh' if 'hour' in unit else 'kw'
        elif unit == 'percent':
            unit = '%'
        elif unit in ('hour','hours','hr','hrs','h'):
            unit = 'duration_h'
        values.append((value, unit, match.start(), match.end()))
        covered.append((match.start(), match.end()))
    return values, covered


def quantity_role(text, start, end):
    entries, _ = quantities(text)
    previous = max((b for _,_,a,b in entries if b <= start), default=0)
    following = min((a for _,_,a,b in entries if a >= end), default=len(text))
    left = re.split(r'(?<=[.!?])\s+|;|,|\band\b|\bwhile\b', text[previous:start], flags=re.I)[-1][-70:]
    right = re.split(r'(?<=[.!?])\s+|;|,|\band\b|\bwhile\b', text[end:following], flags=re.I)[0][:70]
    clause = (left + ' ' + right).lower()
    if re.match(r'\s*(?:battery|storage)\b',right,re.I) and not re.search(r'lowest|minimum',left,re.I):
        return 'battery_capacity'
    if 'battery' in clause and 'capacity' in clause:
        return 'battery_capacity'
    if 'reserve' in clause:
        return 'reserve'
    if 'battery' in clause and re.search(r'lowest|minimum', clause):
        return 'battery_minimum'
    if re.search(r'flexible|work', clause) and re.search(r'unfinished|deferred', clause):
        return 'flexible_unfinished'
    if re.search(r'unserved|shortfall|shortage|deficit', clause):
        return 'essential_unserved'
    if re.search(r'requests?|needs?|requires?|demand', clause):
        return 'requested'
    if re.fullmatch(r'\s*to\s*',left):
        earlier=next(((a,b) for _,_,a,b in reversed(entries) if b==previous),None)
        if earlier:
            return quantity_role(text,*earlier)
    return None


def validate_grounded_prose(message, facts, selected, *, enforce_topics=True, natural=False):
    if re.search(r'[{}\[\]`<>]|https?://|\bwww\.', message):
        raise PlanningError('INVALID_ACTIVITY', 'Write a concise plain-English explanation without links, markup or placeholders.')
    sentences=[' '.join(s.casefold().split()) for s in re.split(r'(?<=[.!?])\s+|\n+',message) if len(s.strip())>25]
    if len(sentences)!=len(set(sentences)):
        raise PlanningError('INVALID_ACTIVITY','Write a single concise reply without repeating sentences or paragraphs.')
    if re.search(r'[{}\[\]`<>]',message):
        raise PlanningError('INVALID_ACTIVITY','Return natural prose, not an internal template or serialized payload.')
    if re.search(r'\b(?:your clinic has enough|we will have enough|you will have enough|everything is fine|all loads are met)\b',message,re.I):
        raise PlanningError('INVALID_ACTIVITY','Do not assert unqualified electricity availability; describe actual modeled figures or an unevaluated idea.')
    if re.search(r'\b(?:source ids?|fact_references|essential_summary|ranked_option|selected_option|weather_basis|battery_summary|option_(?:output|battery|solar|scheduling|optional))\b',message,re.I):
        raise PlanningError('INVALID_ACTIVITY', 'Remove all source IDs and field names from the message. Cite them only in fact_references; keep the user-facing prose natural.')
    # Clinical disclaimers are permitted; affirmative clinical assurances are not.
    claims = re.sub(r'\b(?:not(?:\s+to)?|no|never|without|cannot|does not)\s+(?:a\s+)?(?:clinical\s+)?(?:safety(?:\s+or\s+availability)?\s+)?guarantee(?:s|d)?(?:\s+(?:clinical\s+)?(?:safety|availability))?|\bnot\s+safe', '', message, flags=re.I)
    if not natural and re.search(r'\b(?:guaranteed|guarantees?|safe(?:ly)?|reliable|enough|sufficient|adequate|plenty|unlimited|resolves?|solves?|eliminates?|fixes|covers?)\b', claims, re.I):
        raise PlanningError('INVALID_ACTIVITY', 'Report modeled quantities and uncertainty; do not assert clinical safety, adequacy or reliability.')
    if re.search(r'\b(?:turn (?:off|on)|switch (?:off|on)|disconnect|unplug|vaccinate|administer|diagnose|i (?:confirmed|have confirmed)|i.ve confirmed)\b',message,re.I):
        raise PlanningError('INVALID_ACTIVITY', 'Do not claim confirmation or give clinical/equipment-control instructions.')
    if not natural and re.search(r'\b(?:rainy?|storm\w*|cloudy|sunny|overcast|temperature|wind)\b',message,re.I):
        raise PlanningError('INVALID_ACTIVITY', 'Only solar irradiation and modeled energy facts are provided here; do not invent qualitative weather conditions.')
    if not natural and re.search(r'\b(?:will|would|can)\s+(?:power|supply|run|operate|keep|cover|meet|restore)\b',message,re.I):
        raise PlanningError('INVALID_ACTIVITY', 'Describe the modeled quantities rather than promising equipment availability.')
    if not natural and re.search(r'\b(?:activity|draft|campaign|changes?)\s+(?:is|are|has been|have been)\s+confirmed\b',message,re.I):
        raise PlanningError('INVALID_ACTIVITY', 'Only explicit operator confirmation can confirm an activity.')
    if re.search(r'(?:^|[.!?]\s+)(?:buy|purchase|install|increase|decrease|charge|move|remove|stop|run|keep|use|connect)\b|\b(?:should|must|need to)\s+(?:buy|install|increase|decrease|charge|move|remove|stop|run|connect)\b',message,re.I):
        raise PlanningError('INVALID_ACTIVITY', 'Explain hypothetical tested alternatives; do not direct equipment operation or purchases.')
    if enforce_topics and 'missing_detail' in selected:
        detail = facts['missing_detail'].lower()
        expected = ('start' if 'start' in detail else 'end' if 'end' in detail else 'equipment' if 'equipment' in detail else None)
        pattern={'start':r'start|begin','end':r'end|finish','equipment':r'equipment|device|appliance|load'}.get(expected)
        if pattern and not re.search(r'\b(?:'+pattern+r')\b',message,re.I):
            raise PlanningError('INVALID_ACTIVITY', 'Ask about the actual required missing draft detail.')
    if any(key.startswith('option_') for key in selected):
        discussed=0
        option_count=sum(key.startswith('option_') for key in selected)
        expressions = {'output':r'output|inverter|discharge', 'scheduling':r'reschedul\w*|scheduling', 'battery':r'battery|storage', 'solar':r'solar|panels?|\bpv\b', 'optional':r'optional|postpon\w*'}
        for key in selected:
            if not key.startswith('option_'):
                continue
            kind = key.removeprefix('option_')
            pattern = expressions.get(kind, r'option\s+'+re.escape(kind)+r'\b')
            sentences = re.split(r'(?<=[.!?])\s+|\n+',message)
            if any(re.search(pattern,sentence,re.I) and (quantities(sentence)[0] or index+1<len(sentences) and quantities(sentences[index+1])[0]) for index,sentence in enumerate(sentences)):
                discussed+=1
    source = ' '.join(facts[key] for key in selected)
    source_values, _ = quantities(source)
    generated, covered = quantities(message)
    for value, unit, start, end in generated:
        if not any(unit == known_unit and (value == known if unit == 'date' else abs(value-known) <= 1e-6) for known,known_unit,_,_ in source_values):
            raise PlanningError('INVALID_ACTIVITY', 'A quantity or unit does not match the cited current tool results.')
    if enforce_topics and 'unconfirmed_notice' in selected and not (re.search(r'\b(?:draft|activity)\b',message,re.I) and re.search(r'not included|excluded|unconfirmed',message,re.I)):
        raise PlanningError('INVALID_ACTIVITY', 'Explain that the unconfirmed activity draft is excluded from this calculation.')
    if enforce_topics and 'review_boundary' in selected and not (re.search(r'review',message,re.I) and re.search(r'confirm|reject|approval',message,re.I)):
        raise PlanningError('INVALID_ACTIVITY', 'Ask the operator to review and explicitly confirm or reject the draft.')
    if enforce_topics and 'selected_option' in selected:
        if not re.search(r'\bbaseline|\bexisting|\bcurrent',message,re.I):
            raise PlanningError('INVALID_ACTIVITY','Compare the chosen option with the existing baseline, not only the selected outcome.')
        if not re.search(r'\bselected|\bchosen',message,re.I):
            raise PlanningError('INVALID_ACTIVITY', 'Explain the exact selected comparison, rather than a recommendation.')
        for change in re.finditer(r'\bto\s+(-?\d+(?:\.\d+)?\s*(?:kWh|kW))',facts['selected_option']):
            after, _ = quantities(change[1])
            for expected, unit, _, _ in after:
                if not any(unit==actual_unit and abs(expected-actual)<=1e-6 for actual,actual_unit,_,_ in generated if actual_unit!='date'):
                    raise PlanningError('INVALID_ACTIVITY', 'Include the actual selected hypothetical size or output, not a different tested option.')
    for match in re.finditer(r'\d+(?:\.\d+)?',message):
        if not any(start <= match.start() and match.end() <= end for start,end in covered):
            raise PlanningError('INVALID_ACTIVITY', 'Every numerical claim needs a verified quantity/unit, local time or date.')
    # Check each numerical sentence against its cited source group. This rejects
    # borrowing the baseline deficit for an option that actually removed it.
    for sentence in re.split(r'(?<=[.!?])\s+|\n+',message):
        numbers, _ = quantities(sentence)
        if not numbers:
            continue
        kinds = [kind for kind in ('output','scheduling','battery','solar','optional') if re.search(r'\b'+(r'(?:reschedul\w*|scheduling)' if kind=='scheduling' else kind)+r'\b',sentence,re.I)]
        candidates = [key for key in selected if key.startswith('option_') and any(kind in key for kind in kinds)]
        if len(candidates) > 1 and len(kinds) > 1:
            raise PlanningError('INVALID_ACTIVITY', 'Use a separate numerical sentence for each tested alternative.')
        if candidates:
            allowed = [entry for key in candidates for entry in quantities(facts[key])[0]]
            # Baseline battery/reserve explanations are not hardware-option claims.
            baseline = bool(re.search(r'lowest|minimum|reserve|current|existing|baseline',sentence,re.I))
            if not baseline and not all(any(unit == source_unit and (value == original if unit=='date' else abs(value-original)<=1e-6)
                    for original,source_unit,_,_ in allowed) for value,unit,_,_ in numbers):
                raise PlanningError('INVALID_ACTIVITY', 'The stated option quantities do not match that computed alternative.')
        role_sources = candidates or [key for key in selected if not key.startswith('option_')]
        if natural and not candidates:
            optimized=bool(re.search(r'\b(?:optimized|optimised|rescheduled)\b',sentence,re.I))
            baseline=bool(re.search(r'\b(?:existing|baseline)\b',sentence,re.I))
            if optimized and not baseline:
                role_sources=[key for key in role_sources if key.startswith('optimized_') or key in ('scheduling_comparison','model_outcome_optimized','energy_settings')]
            elif baseline and not optimized:
                role_sources=[key for key in role_sources if not key.startswith('optimized_') and key!='model_outcome_optimized']
        if 'selected_option' in selected:
            is_selected = bool(re.search(r'\bselected|\bchosen',sentence,re.I))
            is_baseline = bool(re.search(r'\bexisting|\bbaseline|\bcurrent',sentence,re.I))
            if is_selected and not is_baseline:
                role_sources = ['selected_option']
            elif is_baseline and not is_selected:
                role_sources = [key for key in role_sources if key!='selected_option']
        for value, unit, start, end in numbers:
            if unit != 'kwh':
                continue
            role = quantity_role(sentence, start, end)
            if role is None:
                continue
            role_values = [(original, source_unit) for key in role_sources
                for original, source_unit, source_start, source_end in quantities(facts[key])[0]
                if quantity_role(facts[key], source_start, source_end) == role]
            if not any(source_unit == unit and abs(value-original) <= 1e-6 for original,source_unit in role_values):
                raise PlanningError('INVALID_ACTIVITY', 'A quantity was labeled as a different metric than its verified source.')
    if enforce_topics and 'essential_summary' in selected and not re.search(r'\b(?:model\w*|forecast|assumptions?|hypothetical|illustrative|draft|unconfirmed|review)\b',message,re.I):
        raise PlanningError('INVALID_ACTIVITY', 'Explain the modeled or draft basis and the need for review.')


def render_grounded_reply(arguments, facts, required, options):
    reply = GroundedReply.model_validate(arguments)
    used = set(reply.fact_references)
    if len(used) != len(reply.fact_references) or not used <= set(facts) or not required <= used:
        raise PlanningError('INVALID_ACTIVITY', 'Cite distinct current fact IDs, including every required source; do not invent a source.')
    validate_grounded_prose(reply.message, facts, used)
    return reply.message


def synthesis_data(state, facts):
    """Compact typed context, not prewritten paragraphs for the model to copy."""
    data = dict(facts)
    if 'scope' in data:
        data['scope']={'model_comparison_only':True,'operator_review_required':True,'clinical_guarantee':False,'hypothetical_changes_adopted':False}
    plan = state.computed_plan
    if not plan:
        return data
    metrics = plan.simulation.baseline.metrics
    if 'essential_summary' in data:
        data['essential_summary'] = {'basis':'existing baseline schedule before any intervention', 'remaining_unserved_essential_energy':f'{metrics.critical_unserved_kwh:.3f} kWh',
            'flexible_unfinished':f'{metrics.flexible_deferred_kwh:.3f} kWh'}
        if 'battery_summary' in data:
            data['battery_summary'] = {'lowest_stored_energy':f'{metrics.min_soc_kwh:.3f} kWh',
                'reserve_target':f'{plan.simulation.effective_config.reserve_kwh:.3f} kWh'}
        if 'weather_basis' in data:
            data['weather_basis'] = {'planning_date':state.planning_date.isoformat(),
                'forecast_irradiation_used':f'{plan.sunshine_factor*100:g}%'}
    if plan.recovery:
        if 'selected_option' in facts:
            selected = next(o for o in plan.recovery.options + [plan.recovery.existing] if o.id == state.selected_recovery_intervention_id)
            m = selected.metrics
            data['selected_option'] = {'exact_selected_option_id':selected.id,'label':selected.label,'kind':selected.kind,
                'remaining_unserved_essential_energy':f'{m.essential_unserved_kwh:.3f} kWh',
                'flexible_unfinished':f'{m.flexible_unfinished_kwh:.3f} kWh',
                'hypothetical_changes':[{'field':c.field,'before':f'{c.before:g} {c.unit}','after':f'{c.after:g} {c.unit}'} for c in selected.infrastructure_changes]}
        for key in facts:
            if not key.startswith('option_'):
                continue
            suffix=key.removeprefix('option_')
            kind=suffix.split('_case_',1)[0]
            option=plan.recovery.options[int(suffix.rsplit('_case_',1)[1])] if '_case_' in suffix else next(o for o in plan.recovery.options if o.kind==kind)
            m = option.metrics
            data[key] = {'option_id':option.id,'kind':kind, 'label':option.label,
                'remaining_unserved_essential_energy':f'{m.essential_unserved_kwh:.3f} kWh',
                'flexible_unfinished':f'{m.flexible_unfinished_kwh:.3f} kWh',
                'hypothetical_changes':[{
                    'field':c.field,'before':f'{c.before:g} {c.unit}','after':f'{c.after:g} {c.unit}'} for c in option.infrastructure_changes]}
    return data




def collect_reply_facts(state, calls=(), question=''):
    """Facts constrain claims; they do not prescribe which topics to discuss."""
    facts={}
    if state.active_proposal_id:
        facts.update(fact_references(state,['review_activity_proposal'])[0])
    config=state.energy_settings
    facts['energy_settings']=(f'Configured battery capacity: {config.battery_capacity_kwh:g} kWh. '
        f'Assumed day-start stored energy: {config.initial_battery_kwh:g} kWh. Reserve target: {config.reserve_kwh:g} kWh. '
        f'PV rated power: {config.pv_capacity_kw:g} kW. Maximum charging power: {config.max_charge_kw:g} kW. '
        f'Maximum battery output: {config.max_discharge_kw:g} kW. Charge efficiency: {config.charge_efficiency*100:g}%. '
        f'Discharge efficiency: {config.discharge_efficiency*100:g}%.')
    inventory=[]
    effective_equipment=compile_clinic(state).equipment or []
    runtime={}
    for activity in state.confirmed_activities:
        for constraint in activity.details.equipment_constraints:
            duration=getattr(constraint,'required_duration_hours',None)
            if duration is not None:
                runtime[constraint.equipment_id]=max(runtime.get(constraint.equipment_id,0),duration)
        for device in activity.details.additional_equipment:
            if device.required_duration_hours is not None:
                runtime[device.id]=max(runtime.get(device.id,0),device.required_duration_hours)
    for item in effective_equipment:
        if item.category=='critical':
            inventory.append(f'{item.name}: essential, {item.power_kw:g} kW, {len(item.required_hours)} hours required in configured hourly slots '+', '.join(f'{hour:02d}:00' for hour in item.required_hours)+'.')
        else:
            inventory.append(f'{item.name}: flexible, {item.max_power_kw:g} kW, {item.required_energy_kwh:g} kWh required, allowed hourly slots '+', '.join(f'{hour:02d}:00' for hour in item.allowed_hours)+'.')
        if item.id in runtime:
            inventory.append(f'{item.name}: explicit confirmed minimum total daily device runtime {runtime[item.id]} hours, aggregated for this one physical device.')
    facts['equipment_inventory']='Effective confirmed equipment requirements, compiled from baseline and confirmed activities: '+' '.join(inventory)
    facts['clinic_context']=f'Selected clinic: {state.clinic_name}. Planning date: {state.planning_date.isoformat()}. All names and settings are operator data.'
    for activity in state.confirmed_activities:
        detail=activity.details
        text=f'Confirmed activity: {detail.name}, {detail.planning_date.isoformat()}, {detail.start_hour:02d}:00 to {detail.end_hour:02d}:00.'
        for constraint in detail.equipment_constraints:
            device=next((item for item in effective_equipment if item.id==constraint.equipment_id),None)
            duration=getattr(constraint,'required_duration_hours',None)
            if device and duration is not None:
                text+=f' Explicit device constraint for {device.name}: minimum total daily operating runtime {duration} hours.'
        facts['activity_'+activity.id]=text
    if state.current_battery_reading:
        facts['current_battery_reading']=f'Operator-reported current stored energy: {state.current_battery_reading.energy_kwh:g} kWh. This is not the assumed day-start energy.'
    if state.active_energy_proposal_id:
        proposal=next(p for p in state.energy_proposals if p.id==state.active_energy_proposal_id)
        settings=proposal.proposed_energy_settings
        facts['energy_proposal']=(f'Unconfirmed proposed battery capacity: {settings.battery_capacity_kwh:g} kWh. Proposed day-start stored energy: {settings.initial_battery_kwh:g} kWh. '
            f'Proposed reserve: {settings.reserve_kwh:g} kWh. Proposed PV rated power: {settings.pv_capacity_kw:g} kW. '
            f'Proposed charging limit: {settings.max_charge_kw:g} kW. Proposed output limit: {settings.max_discharge_kw:g} kW. '
            f'Proposed charge efficiency: {settings.charge_efficiency*100:g}%. Proposed discharge efficiency: {settings.discharge_efficiency*100:g}%. '
            'These settings are not active until explicit operator confirmation.')
        if proposal.updates_current_battery_reading:
            facts['energy_proposal'] += (f' Pending current stored-energy reading: {proposal.current_battery_reading.energy_kwh:g} kWh; this separate reading is still unconfirmed.'
                if proposal.current_battery_reading else ' Clearing the separate current reading is proposed, not yet confirmed.')
    fresh=state.plan_status=='current' and state.computed_plan is not None and state.computed_plan.input_revision==state.input_revision
    if fresh:
        baseline=state.computed_plan.simulation.baseline.metrics
        optimized=state.computed_plan.simulation.optimized.metrics
        facts['optimized_summary']=(f'For the optimized schedule, essential requested energy is {optimized.critical_requested_kwh:.3f} kWh; '
            f'essential shortfall is {optimized.critical_unserved_kwh:.3f} kWh; flexible work unfinished is {optimized.flexible_deferred_kwh:.3f} kWh.')
        facts['optimized_battery']=f'The optimized schedule lowest battery level is {optimized.min_soc_kwh:.3f} kWh.'
        for label,metrics in (('baseline',baseline),('optimized',optimized)):
            essential=metrics.critical_unserved_kwh<=1e-6
            all_work=essential and metrics.flexible_deferred_kwh<=1e-6
            facts['model_outcome_'+label]=(f'For the {label} schedule under the modeled forecast and assumptions: '
                f'essential demand met: {essential}; all required essential and flexible work met: {all_work}. '
                'This does not establish real-world availability or clinical safety.')
        computed,_,_=fact_references(state,['explain_current_plan'] if calls and calls[-1]=='explain_current_plan' else ['recompute_clinic_plan'])
        facts.update(computed)
        recovery=state.computed_plan.recovery
        if recovery and not (calls and calls[-1]=='explain_current_plan' and state.selected_recovery_intervention_id):
            for index,option in enumerate(recovery.options):
                key=f'option_{option.kind}_case_{index}'
                m=option.metrics
                changes=' '.join(f'{c.field}: {c.before:g} {c.unit} to {c.after:g} {c.unit}.' for c in option.infrastructure_changes)
                facts[key]=(f'Tested {option.kind} option {option.label}: essential shortfall {m.essential_unserved_kwh:.3f} kWh; '
                    f'flexible work unfinished {m.flexible_unfinished_kwh:.3f} kWh; lowest battery {m.minimum_battery_kwh:.3f} kWh. '+changes)
        comparison=state.computed_plan.simulation.comparison
        facts['scheduling_comparison']=(f'Existing to optimized final battery change: {comparison.battery_preserved_at_midnight_kwh:.3f} kWh. '
            f'Minimum battery improvement: {comparison.minimum_battery_improvement_kwh:.3f} kWh. Conversion loss reduction: {comparison.conversion_loss_reduction_kwh:.3f} kWh. '
            +('The schedules complete the same flexible work.' if comparison.same_flexible_work_completed else 'The schedules complete different amounts of flexible work; these differences are not like-for-like savings.')
            +(' The sunshine-first heuristic matches the optimizer metrics.' if comparison.heuristic_matches_optimizer_metrics else ' The sunshine-first heuristic and optimizer metrics differ.'))
    if question:
        facts['operator_supplied']='Current operator words, not adopted or evaluated merely by mentioning them: '+question
    return facts


def reply_context(state,calls=(),question=''):
    facts=collect_reply_facts(state,calls,question)
    data=synthesis_data(state,facts)
    # synthesis_data's exact variants supplement the full source catalog.
    return {'state_revision':state.revision,'input_revision':state.input_revision,
        'generation':state.computed_plan.generation if state.computed_plan else None,
        'plan_status':state.plan_status,'selected_option_id':state.selected_recovery_intervention_id,
        'facts':data,'active_draft':next((p.model_dump(mode='json') for p in state.proposals if p.id==state.active_proposal_id),None),
        'active_energy_proposal':next((p.model_dump(mode='json') for p in state.energy_proposals if p.id==state.active_energy_proposal_id),None)}


def _qualified_coverage(state,sentence,message,calls):
    """Truth-check a qualified single-day outcome, without banning useful words."""
    plan=state.computed_plan
    if state.plan_status!='current' or plan is None or plan.input_revision!=state.input_revision:
        return False
    if not re.search(r'\b(?:model(?:ed|led)?|simulation|simulated|calculated|forecast|assumptions?|tested)\b',message,re.I):
        return False
    contexts=[]
    recovery=plan.recovery
    selected=state.selected_recovery_intervention_id
    if recovery and selected and (re.search(r'\b(?:selected|chosen)\b',sentence,re.I) or calls and calls[-1]=='explain_current_plan'):
        contexts=[option.metrics for option in recovery.options+[recovery.existing] if option.id==selected]
    elif re.search(r'\b(?:optimized|optimised|rescheduled|after)\b',sentence,re.I):
        contexts=[plan.simulation.optimized.metrics]
    elif recovery and re.search(r'\b(?:option|alternative|candidate|upgrade)\b',sentence,re.I):
        exact=[option.metrics for option in recovery.options if option.label.casefold() in sentence.casefold()]
        if exact:
            contexts=exact
        else:
            expressions={'battery':r'\bbattery|\bstorage','solar':r'\bsolar|\bpanels?|\bpv\b',
                'output':r'\boutput|\binverter|\bdischarge','scheduling':r'\bschedul\w*|\breschedul\w*'}
            kinds=[kind for kind,pattern in expressions.items() if re.search(pattern,sentence,re.I)]
            contexts=[option.metrics for option in recovery.options if option.kind in kinds]
    else:
        contexts=[plan.simulation.baseline.metrics]
    essential_only=bool(re.search(r'\b(?:essential|critical|protected)\b',sentence,re.I)) and not re.search(r'\b(?:all loads|all needs|all requirements|flexible)\b',sentence,re.I)
    def covered(metrics):
        if hasattr(metrics,'essential_unserved_kwh'):
            essential,unfinished=metrics.essential_unserved_kwh,metrics.flexible_unfinished_kwh
        else:
            essential,unfinished=metrics.critical_unserved_kwh,metrics.flexible_deferred_kwh
        return essential<=1e-6 and (essential_only or unfinished<=1e-6)
    return bool(contexts) and all(covered(metrics) for metrics in contexts)


def _non_operational_guards(message,state,calls):
    if not isinstance(message,str) or not message.strip() or len(message)>6000:
        raise PlanningError('INVALID_ACTIVITY','Return a short authored reply or choose an available tool.')
    if re.search(r'[{}\[\]`<>]',message):
        raise PlanningError('INVALID_ACTIVITY','Return natural prose, not an internal template or serialized payload.')
    if re.search(r'\b(?:source ids?|fact_references|essential_summary|selected_option|system prompt|tool arguments|rephrase.*verified)\b',message,re.I):
        raise PlanningError('INVALID_ACTIVITY','Speak naturally to the person; keep internal IDs and validation instructions out of the reply.')
    for sentence in re.split(r'(?<=[.!?])\s+|\n+',message):
        uncertain=bool(re.search(r"\b(?:cannot|can't|do not|don't|unable to)\s+(?:yet\s+)?(?:determine|know|tell|judge|assess|confirm)|\b(?:not evaluated|not assessed|not checked|haven't checked|haven't evaluated|uncertain whether)\b",sentence,re.I))
        conditional=bool(re.search(r'\b(?:if|suppose|hypothetical|could|might|may|depends)\b',sentence,re.I))
        question=sentence.rstrip().endswith('?')
        if re.search(r'\bsafe(?:ly)?\b',sentence,re.I) and not uncertain and not question:
            raise PlanningError('INVALID_ACTIVITY','Do not assert clinical or operational safety; acknowledge when it cannot be determined.')
        availability=re.search(r'\b(?:we|you|(?:the|our|your|this)\s+clinic)\s+(?:have|has|will have)\s+(?:enough|sufficient|adequate)\b|\b(?:the|our|your|this)\s+battery\s+(?:will|can)\s+(?:last|power|supply|run)\b|\b(?:electricity|power|energy)\s+(?:is|will be)\s+(?:enough|sufficient|adequate)\b|\ball\s+(?:loads|needs|requirements)\s+(?:are|will be)\s+(?:met|covered|supplied)\b|\beverything is fine\b',sentence,re.I)
        modeled_claim=re.search(r'\b(?:covers?|meets?|supplies)\b.*\b(?:essential|critical|protected|all)\b.*\b(?:needs?|demand|loads?|requirements?)\b|\b(?:essential|critical|protected)\b.*\b(?:needs?|demand|loads?|requirements?)\b.*\b(?:met|covered|supplied)\b|\b(?:resolves?|solves?|eliminates?)\b.*\b(?:shortage|shortfall|deficit)\b',sentence,re.I)
        future_battery=re.search(r'\bbattery\s+(?:will|can)\s+(?:last|power|supply|run)\b',sentence,re.I)
        if (availability or modeled_claim) and not (uncertain or conditional or question) and (future_battery or not _qualified_coverage(state,sentence,message,calls)):
            raise PlanningError('INVALID_ACTIVITY','Do not make an affirmative availability claim without a sourced qualified calculation.')
    pending_activity=next((p for p in state.proposals if p.id==state.active_proposal_id),None)
    pending_energy=state.active_energy_proposal_id is not None
    passive_settings=re.search(r'\b(?:power |energy |battery |solar |proposed |new )?settings\s+(?:are|is|have been|has been)\s+(?:(?:now|already|just)\s+)?(?:active|applied|adopted|confirmed|updated)\b',message,re.I)
    draft_updated=any(name in calls for name in ('propose_energy_settings','update_energy_settings_draft')) and bool(re.search(r'\b(?:proposed|draft|pending)\b.{0,40}\bsettings\b|\bsettings draft\b',message,re.I))
    adopted_claim=bool(re.search(r'\b(?:are|is|have been|has been)\s+(?:(?:now|already|just)\s+)?(?:active|applied|adopted|confirmed)\b',message,re.I))
    truthful_draft_update=draft_updated and not adopted_claim
    if pending_energy and passive_settings and not truthful_draft_update and not (re.search(r'\b(?:existing|original|previous|confirmed)\b',message,re.I) and re.search(r'\b(?:draft|proposal|new settings)\b.*\b(?:not|pending|unconfirmed)\b',message,re.I)):
        raise PlanningError('INVALID_ACTIVITY','The pending energy settings are not active; only explicit operator confirmation can adopt them.')
    passive_activity=re.search(r'\b(?:activity|campaign|draft|proposal|changes?)\s+(?:is|are|has been|have been)\s+(?:(?:now|already|just)\s+)?(?:confirmed|adopted|applied|active)\b',message,re.I)
    if passive_activity:
        named=[activity for activity in state.confirmed_activities if activity.details.name.casefold() in message.casefold()]
        conflicting=pending_activity and (not named or any(activity.id==pending_activity.target_activity_id or activity.details.name==pending_activity.details.name for activity in named))
        if (not state.confirmed_activities) or conflicting or (pending_activity and not named):
            raise PlanningError('INVALID_ACTIVITY','The pending activity is unconfirmed. Distinguish previously confirmed activities from this draft.')
    if re.fullmatch(r'\s*(?:confirmed|approved|applied|done)[.!]?\s*',message,re.I) or re.search(r'\b(?:i have|i.ve|i)\s+(?:confirmed|approved|applied)\b',message,re.I):
        raise PlanningError('INVALID_ACTIVITY','Only explicit operator confirmation can apply reviewed changes.')
    if re.search(r'\b(?:i have|i.ve|i)\s+(?:created|added|updated|changed|staged|scheduled)\b',message,re.I) and not any(name in calls for name in ('propose_activity','update_activity_draft','correct_last_activity_time','propose_activity_revision','propose_energy_settings','update_energy_settings_draft')):
        raise PlanningError('INVALID_ACTIVITY','No planning change has been made in this turn. Use a proposal tool before claiming one.')
    disclaimer=re.sub(r'\b(?:not(?:\s+to)?|no|never|without|cannot|does not|do not)\s+(?:a\s+)?(?:clinical(?:ly)?\s+)?(?:safety(?:\s+or\s+availability)?\s+)?guarantee(?:s|d)?(?:\s+(?:clinical\s+)?(?:safety|availability))?|\bnot\s+safe','',message,flags=re.I)
    if re.search(r'\b(?:guarantee\w*|clinically safe|safe to (?:operate|run)|unlimited|definitely enough|certainly enough)\b',disclaimer,re.I):
        raise PlanningError('INVALID_ACTIVITY','Do not give clinical or availability guarantees.')
    if re.search(r'\b(?:turn (?:off|on)|switch (?:off|on)|disconnect|unplug|shut down|vaccinate|administer|diagnose)\b',message,re.I):
        raise PlanningError('INVALID_ACTIVITY','Do not direct equipment control or clinical treatment.')
    if re.search(r'(?:^|[.!?]\s+)(?:please\s+)?(?:buy|purchase|install|increase|decrease|charge|move|remove|stop|run|connect)\b|\b(?:you should|you must|you need to)\s+(?:buy|install|increase|decrease|charge|move|remove|stop|run|connect)\b',message,re.I):
        raise PlanningError('INVALID_ACTIVITY','Discuss options as unevaluated ideas or actual tested comparisons, not equipment-control or purchasing instructions.')


def validate_reply_content(message,state,question,calls=(),references=None):
    """Validate claims without deciding the user's intent or requiring a tool."""
    _non_operational_guards(message,state,calls)
    facts=collect_reply_facts(state,calls,question)
    if references:
        if len(references)!=len(set(references)) or not set(references)<=set(facts):
            raise PlanningError('INVALID_ACTIVITY','Cite only distinct current fact IDs, or omit references for a direct reply.')
        used=set(references)
    else:
        used=set(facts)
    source=' '.join(facts[key] for key in used)
    source_quantities,_=quantities(source)
    values,covered=quantities(message)
    for value,unit,start,end in values:
        if not any(unit==known_unit and (value==known if unit=='date' else abs(value-known)<=1e-6) for known,known_unit,_,_ in source_quantities):
            raise PlanningError('INVALID_ACTIVITY','A quantity is not present in the current source facts or explicit operator input. Do not invent figures.')
    for match in re.finditer(r'\d+(?:\.\d+)?',message):
        if not any(a<=match.start() and match.end()<=b for a,b in covered):
            if re.match(r'^\s*\d+\.\s',message[message.rfind('\n',0,match.start())+1:]):
                continue
            raise PlanningError('INVALID_ACTIVITY','Numerical claims need verified quantities with units, dates or local times.')
    fresh=state.plan_status=='current' and state.computed_plan is not None and state.computed_plan.input_revision==state.input_revision
    numeric_result=False
    for sentence in re.split(r'(?<=[.!?])\s+|\n+',message):
        proposed_question=bool(re.search(r'\b(?:shall i|would you like|we can|we could|i can)\b.*\b(?:test|compare|evaluate|check)\b',sentence,re.I))
        if proposed_question:
            continue
        numeric_result |= any(unit=='kwh' and quantity_role(sentence,start,end) in ('essential_unserved','battery_minimum','flexible_unfinished') for _,unit,start,end in quantities(sentence)[0])

    result_assertion=bool(re.search(r'\b(?:model shows|calculation shows|simulation shows|we will have|you will have|the clinic will have|your clinic has enough|there is a shortage|all loads are met)\b',message,re.I))
    if (numeric_result or result_assertion) and not fresh:
        raise PlanningError('INVALID_ACTIVITY','That would be a calculated outcome, but no current verified result exists. Run a calculation or clearly discuss it as an unevaluated idea.')
    if numeric_result:
        computed={key:value for key,value in facts.items() if key not in ('operator_supplied','energy_proposal') and not key.startswith('activity_')}
        if references:
            computed={key:value for key,value in computed.items() if key in used}
        validate_grounded_prose(message,computed,set(computed),enforce_topics=False,natural=True)
    # A hypothesis is welcome; an unsupported dated weather forecast is not.
    for sentence in re.split(r'(?<=[.!?])\s+|\n+',message):
        if re.search(r'\b(?:tomorrow|today|forecast|weather)\b.*\b(?:sunny|rainy|cloudy|storm|overcast)\b',sentence,re.I) and not re.search(r'\b(?:if|suppose|hypothetical|what if|not checked|not retrieved)\b',sentence,re.I):
            raise PlanningError('INVALID_ACTIVITY','No qualitative weather outcome is sourced here. Retrieve actual weather or describe the idea as hypothetical.')
    return message


def bind_presentation(choice,state,calls=()):
    from .planning_models import AgentPresentation
    choice=choice if isinstance(choice,PresentationChoice) else PresentationChoice.model_validate(choice)
    if len(choice.option_ids)!=len(set(choice.option_ids)):
        raise PlanningError('INVALID_ACTIVITY','Choose each displayed tested option at most once.')
    if choice.kind=='conversation':
        if choice.option_ids or choice.show_schedule:
            raise PlanningError('INVALID_ACTIVITY','Use a calculated presentation only when intentionally showing a current tested result.')
        return AgentPresentation()
    if choice.kind in ('activity_review','energy_review'):
        active=state.active_proposal_id if choice.kind=='activity_review' else state.active_energy_proposal_id
        if active is None or choice.option_ids or choice.show_schedule:
            raise PlanningError('INVALID_ACTIVITY','A review presentation requires a real pending proposal and no computed option cards.')
        return AgentPresentation(kind=choice.kind)
    plan=state.computed_plan
    if state.plan_status!='current' or plan is None or plan.input_revision!=state.input_revision:
        raise PlanningError('STALE_RESULT','Only the current verified calculation may be presented.',409)
    known={option.id for option in plan.recovery.options+[plan.recovery.existing]} if plan.recovery else set()
    if not set(choice.option_ids)<=known:
        raise PlanningError('INVALID_ACTIVITY','Display only the relevant option IDs from the current tested comparison.')
    if calls and calls[-1]=='explain_current_plan' and state.selected_recovery_intervention_id and not set(choice.option_ids)<={state.selected_recovery_intervention_id,'existing'}:
        raise PlanningError('INVALID_ACTIVITY','The read-only selected-plan explanation must not substitute a different tested option.')
    return AgentPresentation(kind=choice.kind,input_revision=state.input_revision,generation=plan.generation,option_ids=choice.option_ids,show_schedule=choice.show_schedule)
