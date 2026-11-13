from fastapi import APIRouter, Request
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
import asyncio
from .recovery_models import RecoveryRequest, RecoveryResponse
from .recovery_planner import generate_recovery_plan
from .weather_forecast import ForecastError

router = APIRouter()


@router.post('/api/recovery/plan',response_model=RecoveryResponse)
async def recovery(body:RecoveryRequest,request:Request):
    try:
        async with asyncio.timeout(75):
            return await generate_recovery_plan(body,request.app.state.catalog,request.app.state.forecasts,request.app.state.solve_lock)
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from None
    except TimeoutError:
        raise ForecastError('RECOVERY_TIME_LIMIT','Recovery comparisons exceeded the time limit. No new verified comparison is available.',503) from None
