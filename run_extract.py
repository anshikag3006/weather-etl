from etl.extract.weather_extractor import WeatherExtractor

extractor = WeatherExtractor(forecast_days=7)
results = extractor.extract(cities=["delhi"])  # start with one city

# inspect the shape
delhi = results["delhi"]
print(f"Keys: {list(delhi.keys())}")
print(f"Hourly records: {len(delhi['hourly']['time'])}")
print(f"First timestamp: {delhi['hourly']['time'][0]}")
print(f"First temp: {delhi['hourly']['temperature_2m'][0]}°C")