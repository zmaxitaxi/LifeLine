"""Explicit operator review boundary; the model cannot invoke confirm/reject."""
from fastapi import APIRouter, Request
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from .planning_models import (PlanningState, ActivityProposal, CreatePlanningSession,
    CreateActivityProposal, UpdateActivityProposal, ConfirmActivityProposal,
    RejectActivityProposal, RecomputePlanningState, SelectRecoveryIntervention,
    SessionAgentRequest, SessionAgentResponse)
from .planning_agent import ask_session_agent
from .models import ApiErrorResponse
from .planning_models import PlanningConversation
from .energy_settings_models import (EnergySettingsProposal, CreateEnergySettingsProposal,
                                    UpdateEnergySettingsProposal)

router = APIRouter(prefix='/api/planning/sessions', tags=['Shared planning'],
    responses={status:{'model':ApiErrorResponse} for status in (404,409,422,500,503)})


@router.post('', response_model=PlanningState)
async def create(body: CreatePlanningSession, request: Request):
    try:
        return await request.app.state.planning.create(body, request.app.state.catalog)
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from None


@router.get('/{session_id}', response_model=PlanningState)
async def read(session_id: str, request: Request):
    return request.app.state.planning.read(session_id)


@router.get('/{session_id}/conversation', response_model=PlanningConversation)
async def conversation(session_id: str, request: Request):
    return request.app.state.planning.conversation(session_id)


@router.post('/{session_id}/energy-proposals', response_model=PlanningState)
async def propose_energy(session_id: str, body: CreateEnergySettingsProposal, request: Request):
    return await request.app.state.planning.propose_energy(session_id, body)


@router.get('/{session_id}/energy-proposals/{proposal_id}', response_model=EnergySettingsProposal)
async def inspect_energy(session_id: str, proposal_id: str, request: Request):
    store = request.app.state.planning
    return store.energy_proposal(store.read(session_id), proposal_id)


@router.patch('/{session_id}/energy-proposals/{proposal_id}', response_model=PlanningState)
async def update_energy(session_id: str, proposal_id: str, body: UpdateEnergySettingsProposal, request: Request):
    return await request.app.state.planning.update_energy(session_id, proposal_id, body)


@router.post('/{session_id}/energy-proposals/{proposal_id}/confirm', response_model=PlanningState)
async def confirm_energy(session_id: str, proposal_id: str, body: ConfirmActivityProposal, request: Request):
    previous = request.app.state.planning.read(session_id).computed_plan
    state, changed = await request.app.state.planning.confirm_energy(session_id, proposal_id, body)
    if changed:
        state = await request.app.state.planning.recompute(session_id,
            RecomputePlanningState(expected_revision=state.revision, sunshine_factor=state.sunshine_factor,
                include_recovery=bool(previous and previous.recovery)),
            request.app.state.catalog, request.app.state.forecasts, request.app.state.solve_lock,
            confirmed_input_revision=state.input_revision)
    return state


@router.post('/{session_id}/energy-proposals/{proposal_id}/reject', response_model=PlanningState)
async def reject_energy(session_id: str, proposal_id: str, body: RejectActivityProposal, request: Request):
    return await request.app.state.planning.reject_energy(session_id, proposal_id, body)


@router.post('/{session_id}/proposals', response_model=PlanningState)
async def propose(session_id: str, body: CreateActivityProposal, request: Request):
    return await request.app.state.planning.propose(session_id, body)


@router.get('/{session_id}/proposals/{proposal_id}', response_model=ActivityProposal)
async def inspect(session_id: str, proposal_id: str, request: Request):
    store = request.app.state.planning
    return store.proposal(store.read(session_id), proposal_id)


@router.patch('/{session_id}/proposals/{proposal_id}', response_model=PlanningState)
async def update(session_id: str, proposal_id: str, body: UpdateActivityProposal, request: Request):
    return await request.app.state.planning.update(session_id, proposal_id, body)


@router.post('/{session_id}/proposals/{proposal_id}/confirm', response_model=PlanningState)
async def confirm(session_id: str, proposal_id: str, body: ConfirmActivityProposal, request: Request):
    previous = request.app.state.planning.read(session_id).computed_plan
    state, changed = await request.app.state.planning.confirm(session_id, proposal_id, body)
    if changed:
        state = await request.app.state.planning.recompute(session_id,
            RecomputePlanningState(expected_revision=state.revision, sunshine_factor=state.sunshine_factor,
                include_recovery=bool(previous and previous.recovery)),
            request.app.state.catalog, request.app.state.forecasts, request.app.state.solve_lock,
            confirmed_input_revision=state.input_revision)
    return state


@router.post('/{session_id}/proposals/{proposal_id}/reject', response_model=PlanningState)
async def reject(session_id: str, proposal_id: str, body: RejectActivityProposal, request: Request):
    return await request.app.state.planning.reject(session_id, proposal_id, body)


@router.post('/{session_id}/recompute', response_model=PlanningState)
async def recompute(session_id: str, body: RecomputePlanningState, request: Request):
    return await request.app.state.planning.recompute(session_id, body, request.app.state.catalog,
        request.app.state.forecasts, request.app.state.solve_lock)


@router.post('/{session_id}/recovery-selection', response_model=PlanningState)
async def select(session_id: str, body: SelectRecoveryIntervention, request: Request):
    return await request.app.state.planning.select_recovery(session_id, body)


@router.post('/{session_id}/agent', response_model=SessionAgentResponse)
async def agent(session_id: str, body: SessionAgentRequest, request: Request):
    response = await ask_session_agent(session_id, body, request.app.state.planning,
        request.app.state.catalog, request.app.state.forecasts, request.app.state.solve_lock,
        request.app.state.agent)
    return await request.app.state.planning.record_turn(session_id, body.question, response)
