import logging
from datetime import datetime

import pandas as pd

logger = logging.getLogger(__name__)


class WeatherTransformer:
    """Converts raw Open-Meteo API response into a clean DataFrame."""

    EXPECTED_COLS = [
        "time", "temperature_2m", "relative_humidity_2m",
        "precipitation", "wind_speed_10m",
        "surface_pressure", "weather_code",
    ]

    def transform(self, raw_data: dict, city: str) -> pd.DataFrame:
        """
        Takes raw API response dict for one city.
        Returns a clean DataFrame ready for loading.
        """
        logger.info(f"Transforming data for {city}")

        # ── 1. unpack parallel arrays into DataFrame ────────────
        hourly = raw_data["hourly"]
        df = pd.DataFrame(hourly)
        # pd.DataFrame() on a dict of equal-length lists
        # automatically zips them into rows — magic one-liner

        # ── 2. add metadata columns ──────────────────────────────
        df["city"] = city
        df["latitude"]  = raw_data["latitude"]
        df["longitude"] = raw_data["longitude"]
        df["loaded_at"] = datetime.utcnow()

        # ── 3. type casting ───────────────────────────────────────
        df["time"] = pd.to_datetime(df["time"])
        df["temperature_2m"]        = pd.to_numeric(df["temperature_2m"],        errors="coerce")
        df["relative_humidity_2m"]   = pd.to_numeric(df["relative_humidity_2m"],   errors="coerce")
        df["precipitation"]          = pd.to_numeric(df["precipitation"],          errors="coerce")
        df["wind_speed_10m"]         = pd.to_numeric(df["wind_speed_10m"],         errors="coerce")
        df["surface_pressure"]       = pd.to_numeric(df["surface_pressure"],       errors="coerce")

        # ── 4. derive new columns ─────────────────────────────────
        # heat index: feels-like temperature accounting for humidity
        df["heat_index"] = (
            df["temperature_2m"]
            + 0.33 * (df["relative_humidity_2m"] / 100 * 6.105)
            - 4.0
        ).round(2)

        # hour of day — useful for analysis (peak heat hours etc.)
        df["hour"] = df["time"].dt.hour

        # ── 5. validation — fail loudly on bad data ───────────────
        self._validate(df, city)

        logger.info(f"✓ {city}: {len(df)} rows transformed")
        return df

    def _validate(self, df: pd.DataFrame, city: str):
        """Assert data quality — raise immediately if anything looks wrong."""

        # no nulls in critical columns
        critical = ["time", "city", "temperature_2m"]
        for col in critical:
            null_count = df[col].isna().sum()
            assert null_count == 0, (
                f"{city}: {null_count} nulls in '{col}' — check API response"
            )

        # temperature sanity check — Delhi never hits -50 or +80°C
        assert df["temperature_2m"].between(-50, 80).all(), (
            f"{city}: temperature out of valid range (-50 to 80°C)"
        )

        # humidity must be 0–100%
        assert df["relative_humidity_2m"].between(0, 100).all(), (
            f"{city}: humidity out of valid range (0–100%)"
        )

        # correct number of rows (7 days × 24 hours = 168)
        assert len(df) == 168, (
            f"{city}: expected 168 rows, got {len(df)}"
        )

        logger.info(f"✓ {city}: all validations passed")