from fastapi import APIRouter,Query,Request
from .forecast_models import ForecastLocation
from .weather_outlook_models import WeatherOutlook
from .models import ApiErrorResponse

router=APIRouter()


@router.get('/api/weather/outlook',response_model=WeatherOutlook,responses={422:{'model':ApiErrorResponse,'description':'Unprocessable Entity'},503:{'model':ApiErrorResponse}})
async def weather_outlook(request:Request,latitude:float=Query(ge=-90,le=90),longitude:float=Query(ge=-180,le=180)):
    return await request.app.state.outlooks.get(ForecastLocation(latitude=latitude,longitude=longitude))
