import logging
from etl.extract.weather_extractor import WeatherExtractor
from etl.transform.weather_transformer import WeatherTransformer
from etl.load.weather_loader import WeatherLoader

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

def run():
    extractor   = WeatherExtractor(forecast_days=7)
    transformer = WeatherTransformer()
    loader      = WeatherLoader()

    # extract all cities
    raw_data = extractor.extract(cities=["delhi", "mumbai"])

    # transform + load each city
    total_rows = 0
    for city, data in raw_data.items():
        df = transformer.transform(data, city)
        rows = loader.load(df, city)
        total_rows += rows

    print(f"\n Pipeline complete — {total_rows} total rows loaded")

if __name__ == "__main__":
    run()