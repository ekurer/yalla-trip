import httpx
from typing import Optional, Dict, List
from .logger import get_logger

logger = get_logger(__name__)

__all__ = ["Tools"]


class Tools:
    @staticmethod
    async def get_lat_lon(city_name: str) -> Optional[Dict[str, float]]:
        """
        Geocodes a city name to lat/lon using Open-Meteo Geocoding API.
        Handles common abbreviations and variations.
        """
        # Normalize common city name patterns
        normalized = city_name.strip()
        variations = [normalized]

        # Handle common abbreviations
        if "D.C." in normalized or "DC" in normalized:
            variations.append("Washington")
        if normalized.lower() == "nyc":
            variations.append("New York")
        if "UK" in normalized:
            variations.append(normalized.replace("UK", "United Kingdom"))

        url = "https://geocoding-api.open-meteo.com/v1/search"

        async with httpx.AsyncClient() as client:
            for variation in variations:
                try:
                    params = {
                        "name": variation,
                        "count": 1,
                        "language": "en",
                        "format": "json",
                    }
                    resp = await client.get(url, params=params, timeout=5.0)
                    data = resp.json()
                    if data.get("results"):
                        result = data["results"][0]
                        return {
                            "lat": result["latitude"],
                            "lon": result["longitude"],
                            "name": result["name"],
                        }
                except Exception as e:
                    logger.warning("geocoding_error", variation=variation, error=str(e))

            return None

    @staticmethod
    async def get_weather(lat: float, lon: float) -> str:
        """
        Fetches 7-day forecast from Open-Meteo.
        """
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code",
            "timezone": "auto",
        }

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(url, params=params, timeout=5.0)
                data = resp.json()
                if "daily" not in data:
                    return "Weather data unavailable."

                daily = data["daily"]
                summary = []
                # Return first 5 days
                for i in range(min(5, len(daily["time"]))):
                    date = daily["time"][i]
                    max_temp = daily["temperature_2m_max"][i]
                    min_temp = daily["temperature_2m_min"][i]
                    precip = daily["precipitation_sum"][i]
                    summary.append(
                        f"{date}: High {max_temp}°C, Low {min_temp}°C, Rain {precip}mm"
                    )

                return "Forecast:\n" + "\n".join(summary)
            except Exception as e:
                return f"Error fetching weather: {e}"
