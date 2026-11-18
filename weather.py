import os
import sys
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.stormglass.io/v2/weather/point"
PARAMS = "airTemperature,humidity,windSpeed,pressure,cloudCover"

# Stormglass works with coordinates, so we map city names to lat/lng
CITIES = {
    "cairo": (30.0444, 31.2357),
    "banha": (30.4659, 31.1848),
    "alexandria": (31.2001, 29.9187),
    "giza": (30.0131, 31.2089),
    "london": (51.5072, -0.1276),
    "dubai": (25.2048, 55.2708),
}


class WeatherReport:
    """Stores and organizes weather data returned by the API."""

    def __init__(self, city, time, temp, humidity,
                 wind_speed, pressure, cloud_cover):
        self.city = city
        self.time = time
        self.temp = temp
        self.humidity = humidity
        self.wind_speed = wind_speed
        self.pressure = pressure
        self.cloud_cover = cloud_cover

    @staticmethod
    def _value(hour: dict, key: str):
        """Each field is a dict of sources, e.g. {'sg': 22.1, 'noaa': 21.9}."""
        sources = hour.get(key, {})
        return sources.get("sg", next(iter(sources.values()), None))

    @classmethod
    def from_api(cls, city: str, data: dict):
        now = datetime.now(timezone.utc)
        # pick the hour closest to the current time
        hour = min(
            data["hours"],
            key=lambda h: abs(datetime.fromisoformat(h["time"]) - now),
        )
        return cls(
            city=city.title(),
            time=hour["time"],
            temp=cls._value(hour, "airTemperature"),
            humidity=cls._value(hour, "humidity"),
            wind_speed=cls._value(hour, "windSpeed"),
            pressure=cls._value(hour, "pressure"),
            cloud_cover=cls._value(hour, "cloudCover"),
        )

    def summary(self) -> str:
        line = "=" * 40
        return (
            f"{line}\n"
            f"  Weather Report: {self.city}\n"
            f"  Time (UTC)    : {self.time}\n"
            f"{line}\n"
            f"  Temperature : {self.temp} C\n"
            f"  Humidity    : {self.humidity} %\n"
            f"  Wind speed  : {self.wind_speed} m/s\n"
            f"  Pressure    : {self.pressure} hPa\n"
            f"  Cloud cover : {self.cloud_cover} %\n"
            f"{line}"
        )


def fetch_weather(lat: float, lng: float, api_key: str) -> dict:
    params = {"lat": lat, "lng": lng, "params": PARAMS}
    headers = {"Authorization": api_key}
    response = requests.get(BASE_URL, params=params,
                            headers=headers, timeout=15)
    response.raise_for_status()
    return response.json()


def main():
    api_key = os.getenv("STORMGLASS_API_KEY")
    if not api_key:
        sys.exit("Error: STORMGLASS_API_KEY not found. Check your .env file.")

    print("Available cities:", ", ".join(c.title() for c in CITIES))
    city = input("Enter city name: ").strip().lower() or "cairo"

    if city not in CITIES:
        sys.exit(f"City '{city}' is not in the list.")

    lat, lng = CITIES[city]

    try:
        data = fetch_weather(lat, lng, api_key)
        report = WeatherReport.from_api(city, data)
        print(report.summary())
    except requests.exceptions.HTTPError as e:
        code = e.response.status_code
        if code in (401, 403):
            print("Invalid API key.")
        elif code == 402:
            print("Daily request limit reached (free plan = 10/day).")
        else:
            print(f"HTTP error: {e}")
    except requests.exceptions.RequestException as e:
        print(f"Network error: {e}")


if __name__ == "__main__":
    main()