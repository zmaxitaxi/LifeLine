from fastapi import APIRouter, Request
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
import asyncio
import json
import logging
from contextlib import suppress
from time import monotonic
from fastapi.responses import StreamingResponse
from .weather_forecast import ForecastError
from .optimizer import SolverError
from .energy_simulator import NumericalError
from .agent_models import AgentRequest, AgentResponse
from .local_agent import ask_agent, definitions

router=APIRouter()
logger=logging.getLogger(__name__)


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
            result=await ask_agent(body,request.app.state.catalog,request.app.state.forecasts,
                                   request.app.state.solve_lock,request.app.state.agent)
            if result.mode=='local_tool_agent' and getattr(request.app.state.agent,'response_mode',None)=='cloud_tool_agent':
                result.mode='cloud_tool_agent'
            return result
    except TimeoutError:
        return AgentResponse(mode='deterministic_guided_fallback',message='The local agent exceeded its time limit. No new verified answer is available. Select guided fallback and retry.',
            needs_clarification=True,tool_calls=[],fallback_reason='LOCAL_AGENT_TIME_LIMIT',input_basis=body.input_basis)
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from None


@router.post('/api/agent/stream', response_class=StreamingResponse,
             responses={200: {'content': {'text/event-stream': {'schema': {'type': 'string'}}},
                              'description': 'Public execution activity followed by a verified answer or error. Raw model reasoning is never streamed.'}})
async def stream(body:AgentRequest,request:Request):
    async def events():
        queue=asyncio.Queue(maxsize=64)
        started=monotonic()

        async def progress(event):
            await queue.put(event | {'elapsed_ms': round((monotonic()-started)*1000)})

        async def compute():
            try:
                async with asyncio.timeout(75):
                    result=await ask_agent(body,request.app.state.catalog,request.app.state.forecasts,
                                           request.app.state.solve_lock,request.app.state.agent,progress=progress)
                if result.mode=='local_tool_agent' and getattr(request.app.state.agent,'response_mode',None)=='cloud_tool_agent':
                    result.mode='cloud_tool_agent'
                await queue.put({'type':'answer','response':result.model_dump(mode='json')})
            except TimeoutError:
                await queue.put({'type':'error','code':'LOCAL_AGENT_TIME_LIMIT',
                                 'message':'The local model took too long to respond. No new verified answer is available. Please retry.'})
            except ForecastError as exc:
                message=exc.message
                if exc.code=='FORECAST_UNAVAILABLE':
                    message='Live weather could not be retrieved. No forecast or new plan has been invented. Check the connection and try again.'
                await queue.put({'type':'error','code':exc.code,'message':message})
            except ValidationError:
                await queue.put({'type':'error','code':'INVALID_REQUEST',
                                 'message':'Please check the clinic details and the starting battery assumption before calculating.'})
            except (SolverError,NumericalError):
                await queue.put({'type':'error','code':'CALCULATION_UNAVAILABLE',
                                 'message':'The electricity calculation could not be verified. No new plan is available. Please retry.'})
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception('Streaming local-agent request failed')
                await queue.put({'type':'error','code':'INTERNAL_ERROR',
                                 'message':'LifeLine could not finish this request. Please try again.'})
            finally:
                await queue.put(None)

        task=asyncio.create_task(compute())
        try:
            while True:
                try:
                    event=await asyncio.wait_for(queue.get(), timeout=10)
                except TimeoutError:
                    yield ': keepalive\n\n'
                    continue
                if event is None:
                    break
                yield 'data: '+json.dumps(event,ensure_ascii=False,allow_nan=False)+'\n\n'
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    return StreamingResponse(events(),media_type='text/event-stream',
                             headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})
