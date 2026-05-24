import os
import logging
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv(override=True)
logger = logging.getLogger(__name__)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS weather_hourly (
    id               SERIAL PRIMARY KEY,
    city             VARCHAR(50)   NOT NULL,
    time             TIMESTAMP     NOT NULL,
    temperature_2m   DECIMAL(5,2),
    relative_humidity_2m INTEGER,
    precipitation    DECIMAL(6,2),
    wind_speed_10m   DECIMAL(6,2),
    surface_pressure DECIMAL(8,2),
    weather_code     INTEGER,
    heat_index       DECIMAL(5,2),
    hour             INTEGER,
    latitude         DECIMAL(8,4),
    longitude        DECIMAL(8,4),
    loaded_at        TIMESTAMP,
    UNIQUE (city, time)
);
"""

class WeatherLoader:
    def __init__(self):
        db_url = os.environ["DATABASE_URL"]
        self.engine = create_engine(db_url)
        self._create_table()

    def _create_table(self):
        with self.engine.connect() as conn:
            conn.execute(text(CREATE_TABLE_SQL))
            conn.commit()
        logger.info("Table weather_hourly ready")

    def load(self, df: pd.DataFrame, city: str) -> int:
        temp_table = f"temp_{city}_load"
        df.to_sql(temp_table, self.engine, if_exists="replace", index=False)

        upsert_sql = f"""
            INSERT INTO weather_hourly (
                city, time, temperature_2m, relative_humidity_2m,
                precipitation, wind_speed_10m, surface_pressure,
                weather_code, heat_index, hour, latitude, longitude, loaded_at
            )
            SELECT
                city, time, temperature_2m, relative_humidity_2m,
                precipitation, wind_speed_10m, surface_pressure,
                weather_code, heat_index, hour, latitude, longitude, loaded_at
            FROM {temp_table}
            ON CONFLICT (city, time)
            DO UPDATE SET
                temperature_2m       = EXCLUDED.temperature_2m,
                relative_humidity_2m = EXCLUDED.relative_humidity_2m,
                precipitation        = EXCLUDED.precipitation,
                wind_speed_10m       = EXCLUDED.wind_speed_10m,
                surface_pressure     = EXCLUDED.surface_pressure,
                heat_index           = EXCLUDED.heat_index,
                loaded_at            = EXCLUDED.loaded_at;
        """

        with self.engine.connect() as conn:
            conn.execute(text(upsert_sql))
            conn.commit()

        with self.engine.connect() as conn:
            conn.execute(text(f"DROP TABLE IF EXISTS {temp_table}"))
            conn.commit()

        rows = len(df)
        logger.info(f"Done: {city}: {rows} rows upserted")
        return rows
