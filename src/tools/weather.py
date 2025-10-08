"""
Weather tool using Google Weather API.

Provides daily weather forecasts using Google's official Weather API.
Implements geocoding for city name to lat/lon conversion with permanent caching.
"""

from datetime import date, datetime
import httpx
from pydantic import BaseModel

from src.core.config import settings
from src.core.http_client import get_http_client
from src.db.redis_client import get_redis
from .base import Tool, ToolContext


class WeatherQuery(BaseModel):
    location: str
    date: str | None = None  # if None -> assume today in the tool


class WeatherReport(BaseModel):
    location_label: str
    date: str
    summary: str
    temp_c: float


async def geocode_location(location: str) -> tuple[float, float]:
    """
    Convert city name to latitude/longitude using Google Geocoding API.

    Results are cached permanently in Redis (cities don't move).

    Args:
        location: City name (e.g., "Toronto", "Paris")

    Returns:
        Tuple of (latitude, longitude)

    Raises:
        ValueError: If location not found or API error
    """
    # Check cache first (permanent cache - cities don't move!)
    redis = await get_redis()
    cache_key = f"geo:{location.lower()}"

    if cached := await redis.get(cache_key):
        # Redis may return str or bytes depending on client config
        cached_str = cached.decode() if isinstance(cached, bytes) else cached
        lat, lon = cached_str.split(",")
        return float(lat), float(lon)

    # Call Google Geocoding API
    if not settings.google_weather_api_key:
        raise ValueError("Google Weather API key not configured")

    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": location,
        "key": settings.google_weather_api_key,
    }

    client = get_http_client()
    try:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if data["status"] == "REQUEST_DENIED":
            raise ValueError(
                "Geocoding API not enabled. Enable it at: "
                "https://console.cloud.google.com/apis/library/geocoding-backend.googleapis.com"
            )
        elif data["status"] != "OK" or not data.get("results"):
            raise ValueError(f"Location not found: {location}")

        # Extract lat/lon from first result
        loc = data["results"][0]["geometry"]["location"]
        lat, lon = loc["lat"], loc["lng"]

        # Cache permanently
        await redis.set(cache_key, f"{lat},{lon}")

        return lat, lon

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise ValueError(f"Location not found: {location}")
        raise ValueError(f"Geocoding API error: {e.response.status_code}")
    except httpx.TimeoutException:
        raise ValueError("Geocoding service timed out")
    except Exception as e:
        raise ValueError(f"Geocoding failed: {str(e)}")


async def fetch_weather(lat: float, lon: float, target_date: str | None) -> dict:
    """
    Fetch weather data from Google Weather API.

    Args:
        lat: Latitude
        lon: Longitude
        target_date: ISO date string or None for today

    Returns:
        Parsed weather data dict

    Raises:
        ValueError: If API error occurs
    """
    if not settings.google_weather_api_key:
        raise ValueError("Google Weather API key not configured")

    client = get_http_client()
    base_url = settings.google_weather_api_url

    # Determine if we need current conditions or forecast
    is_today = target_date is None or target_date == "today"

    try:
        if is_today:
            # Use current conditions endpoint
            url = f"{base_url}/currentConditions:lookup"
            params = {
                "key": settings.google_weather_api_key,
                "location.latitude": lat,
                "location.longitude": lon,
            }

            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            # Parse current conditions response
            if "temperature" not in data:
                raise ValueError("Invalid response from weather API")

            # Extract temperature in Celsius
            temp_c = data["temperature"]["degrees"]

            # Extract weather description
            summary = data.get("weatherCondition", {}).get("description", {}).get("text", "Unknown")

            return {
                "temp_c": temp_c,
                "summary": summary,
                "date": "today",
            }

        else:
            # Use forecast endpoint for future dates
            # Calculate days ahead
            try:
                target = datetime.fromisoformat(target_date).date()
                today = date.today()
                days_ahead = (target - today).days

                if days_ahead < 0:
                    # Past date - return error
                    raise ValueError("Cannot fetch weather for past dates")

                if days_ahead > 15:
                    raise ValueError("Forecast only available for next 15 days")

            except ValueError as e:
                raise ValueError(f"Invalid date format: {target_date}")

            url = f"{base_url}/forecast/days:lookup"
            params = {
                "key": settings.google_weather_api_key,
                "location.latitude": lat,
                "location.longitude": lon,
                "days": min(days_ahead + 1, 15),  # Request enough days
            }

            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            # Parse forecast response
            if "forecastDays" not in data or not data["forecastDays"]:
                raise ValueError("No forecast data available")

            # Find the correct day (0-indexed)
            forecasts = data["forecastDays"]
            if days_ahead >= len(forecasts):
                raise ValueError(f"Forecast not available for {days_ahead} days ahead")

            forecast_day = forecasts[days_ahead]

            # Extract temperature (average of min/max)
            temp_max = forecast_day.get("maxTemperature", {}).get("degrees", 25.0)
            temp_min = forecast_day.get("minTemperature", {}).get("degrees", 15.0)
            temp_avg = (temp_max + temp_min) / 2.0

            # Extract weather condition from daytime forecast
            summary = (
                forecast_day.get("daytimeForecast", {})
                .get("weatherCondition", {})
                .get("description", {})
                .get("text", "Unknown")
            )

            return {
                "temp_c": temp_avg,
                "summary": summary,
                "date": target_date,
            }

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            raise ValueError("Weather API rate limit exceeded")
        elif e.response.status_code == 403:
            raise ValueError("Weather API authentication failed")
        raise ValueError(f"Weather API error: {e.response.status_code}")
    except httpx.TimeoutException:
        raise ValueError("Weather service timed out")


class WeatherTool:
    name: str = "weather.get"
    input_model: type[BaseModel] = WeatherQuery
    output_model: type[BaseModel] = WeatherReport

    async def __call__(self, args: BaseModel, ctx: ToolContext) -> BaseModel:
        q = WeatherQuery.model_validate(args.model_dump())

        # Check weather cache first (15 min TTL)
        cache_key = f"wx:{q.location}:{q.date or 'today'}"
        redis = await get_redis()

        if cached := await redis.get(cache_key):
            return WeatherReport.model_validate_json(cached)

        try:
            # 1. Geocode location (cached permanently internally)
            lat, lon = await geocode_location(q.location)

            # 2. Fetch weather data from Google API
            weather_data = await fetch_weather(lat, lon, q.date)

            # 3. Build report
            report = WeatherReport(
                location_label=q.location.title(),
                date=weather_data["date"],
                summary=weather_data["summary"],
                temp_c=weather_data["temp_c"],
            )

            # 4. Cache result (15 min TTL)
            await redis.setex(cache_key, 15 * 60, report.model_dump_json())

            return report

        except ValueError as e:
            # Return friendly error as a "report" (tool doesn't fail, just returns error info)
            # The calling node will handle this gracefully
            error_report = WeatherReport(
                location_label=q.location.title(),
                date=q.date or "today",
                summary=f"Error: {str(e)}",
                temp_c=0.0,
            )
            return error_report


tool: Tool = WeatherTool()
