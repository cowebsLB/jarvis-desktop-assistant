from __future__ import annotations

import logging
from dataclasses import dataclass

import requests


LOGGER = logging.getLogger(__name__)

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

WEATHER_CODES = {
    0: "clear skies",
    1: "mostly clear skies",
    2: "partly cloudy skies",
    3: "overcast skies",
    45: "fog",
    48: "depositing rime fog",
    51: "light drizzle",
    53: "moderate drizzle",
    55: "dense drizzle",
    61: "light rain",
    63: "moderate rain",
    65: "heavy rain",
    66: "light freezing rain",
    67: "heavy freezing rain",
    71: "light snow",
    73: "moderate snow",
    75: "heavy snow",
    77: "snow grains",
    80: "light rain showers",
    81: "moderate rain showers",
    82: "violent rain showers",
    85: "light snow showers",
    86: "heavy snow showers",
    95: "thunderstorms",
    96: "thunderstorms with light hail",
    99: "thunderstorms with heavy hail",
}


@dataclass
class WeatherSummary:
    location_name: str
    spoken: str
    details: str


class WeatherService:
    def __init__(self, default_location: str = "Beirut, Lebanon") -> None:
        self.default_location = default_location

    def get_summary(self, location: str | None = None) -> WeatherSummary:
        resolved_location = location or self.default_location
        geo = self._geocode(resolved_location)
        forecast = self._forecast(geo["latitude"], geo["longitude"], geo.get("timezone", "auto"))

        current = forecast["current"]
        daily = forecast["daily"]
        description = WEATHER_CODES.get(current["weather_code"], "mixed conditions")
        place = self._format_place_name(geo)

        spoken = (
            f"In {place}, conditions are {description}. Currently {round(current['temperature_2m'])} degrees Celsius. "
            f"The high will be {round(daily['temperature_2m_max'][0])}, and the low {round(daily['temperature_2m_min'][0])}."
        )
        if daily["precipitation_probability_max"][0] is not None:
            spoken += f" Rain chance is {round(daily['precipitation_probability_max'][0])} percent."

        details = (
            f"{place}: {description}, current {current['temperature_2m']}C, "
            f"high {daily['temperature_2m_max'][0]}C, low {daily['temperature_2m_min'][0]}C"
        )
        return WeatherSummary(location_name=place, spoken=spoken, details=details)

    def _geocode(self, location: str) -> dict:
        LOGGER.info("Geocoding weather location: %s", location)
        response = requests.get(
            GEOCODING_URL,
            params={"name": location, "count": 1, "language": "en", "format": "json"},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        results = payload.get("results") or []
        if not results:
            raise RuntimeError(f"I couldn't find the location {location}.")
        return results[0]

    def _forecast(self, latitude: float, longitude: float, timezone: str) -> dict:
        LOGGER.info("Fetching weather forecast lat=%s lon=%s", latitude, longitude)
        response = requests.get(
            FORECAST_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "timezone": timezone or "auto",
                "current": "temperature_2m,weather_code",
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                "forecast_days": 1,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _format_place_name(geo: dict) -> str:
        name = geo.get("name")
        country = geo.get("country")
        if name and country and name.lower() == country.lower():
            return name
        parts = [name, country]
        return ", ".join(part for part in parts if part)
