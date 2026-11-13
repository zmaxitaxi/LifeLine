from fastapi import APIRouter, Request
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
import asyncio
from .agent_models import AgentRequest, AgentResponse
from .local_agent import ask_agent, definitions

router=APIRouter()


@router.get('/api/agent/status')
async def status(request:Request):
    return await request.app.state.agent.status()


@router.get('/api/agent/tools')
async def tools():
    return {'tools':definitions(),'scope':'Read-only forecasts and hypothetical plans. No physical control or external coordination.'}


@router.post('/api/agent/ask',response_model=AgentResponse)
async def ask(body:AgentRequest,request:Request):
    try:
        async with asyncio.timeout(75):
            return await ask_agent(body,request.app.state.catalog,request.app.state.forecasts,
                                   request.app.state.solve_lock,request.app.state.agent)
    except TimeoutError:
        return AgentResponse(mode='deterministic_guided_fallback',message='The local agent exceeded its time limit. No new verified answer is available. Select guided fallback and retry.',
            needs_clarification=True,tool_calls=[],fallback_reason='LOCAL_AGENT_TIME_LIMIT',input_basis=body.input_basis)
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from None
