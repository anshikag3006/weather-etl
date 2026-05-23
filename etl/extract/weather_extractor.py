import os
import json
import logging
from datetime import datetime, date
from pathlib import Path

import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
from dotenv import load_dotenv

load_dotenv()

# structured logger — every ETL module gets one
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── constants ────────────────────────────────────────────────
BASE_URL = "https://api.open-meteo.com/v1/forecast"
RAW_DIR  = Path("data/raw")          # save raw JSON here

CITIES = {
    "delhi":  {"latitude": 28.6139, "longitude": 77.2090},
    "mumbai": {"latitude": 19.0760, "longitude": 72.8777},
    "bangalore": {"latitude": 12.9716, "longitude": 77.5946},
}

HOURLY_VARS = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "wind_speed_10m",
    "surface_pressure",
    "weather_code",
]


# ── extractor class ──────────────────────────────────────────
class WeatherExtractor:
    """Fetches hourly forecast data from Open-Meteo API."""

    def __init__(self, forecast_days: int = 7):
        self.forecast_days = forecast_days
        self.session = requests.Session()   # reuse TCP connection
        RAW_DIR.mkdir(parents=True, exist_ok=True)

    # ── retry decorator ──────────────────────────────────────
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(
            (requests.ConnectionError, requests.Timeout)
        ),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def _fetch_city(self, city: str) -> dict:
        """Single API call for one city. Retried on network errors."""
        coords = CITIES[city]
        params = {
            "latitude":    coords["latitude"],
            "longitude":   coords["longitude"],
            "hourly":      ",".join(HOURLY_VARS),
            "timezone":    "Asia/Kolkata",
            "forecast_days": self.forecast_days,
        }
        logger.info(f"Fetching weather for {city}")
        response = self.session.get(BASE_URL, params=params, timeout=15)
        response.raise_for_status()   # raises on 4xx / 5xx
        return response.json()

    def _save_raw(self, city: str, data: dict) -> Path:
        """Save raw JSON to disk. Never transform without saving first."""
        today = date.today().isoformat()
        path = RAW_DIR / f"{city}_{today}.json"
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Raw data saved → {path}")
        return path

    def extract(self, cities: list[str] = None) -> dict[str, dict]:
        """
        Main entry point. Fetches all cities, saves raw JSON.
        Returns dict of {city_name: api_response}.
        """
        cities = cities or list(CITIES.keys())
        results = {}

        for city in cities:
            try:
                data = self._fetch_city(city)
                self._save_raw(city, data)
                records = len(data["hourly"]["time"])
                logger.info(f"✓ {city}: {records} hourly records")
                results[city] = data
            except Exception as e:
                # one city failing should NOT stop the others
                logger.error(f"✗ {city} failed: {e}")

        logger.info(f"Extraction complete: {len(results)}/{len(cities)} cities")
        return results