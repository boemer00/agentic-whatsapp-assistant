from pydantic import BaseModel

from ..db.redis_client import get_redis
from .base import Tool, ToolContext


class WeatherQuery(BaseModel):
    location: str
    date: str | None = None  # if None -> assume today in the tool


class WeatherReport(BaseModel):
    location_label: str
    date: str
    summary: str
    temp_c: float


class WeatherTool:
    name: str = "weather.get"
    input_model: type[BaseModel] = WeatherQuery
    output_model: type[BaseModel] = WeatherReport

    async def __call__(self, args: BaseModel, ctx: ToolContext) -> BaseModel:
        q = WeatherQuery.model_validate(args.model_dump())
        key = f"wx:{q.location}:{q.date or 'today'}"
        r = await get_redis()
        if cached := await r.get(key):
            return WeatherReport.model_validate_json(cached)

        # STUB DATA (replace with real provider)
        report = WeatherReport(
            location_label=q.location.title(),
            date=q.date or "today",
            summary="Clear",
            temp_c=20.0,
        )
        await r.setex(key, 15 * 60, report.model_dump_json())
        return report


tool: Tool = WeatherTool()
