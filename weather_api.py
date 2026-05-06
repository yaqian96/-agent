import urllib.request
import urllib.parse
import json
from typing import Dict, List, Optional
from config import API_KEY, API_BASE_URL, GEO_BASE_URL, DEFAULT_DAYS, API_TIMEOUT


OPEN_METEO_GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
OPEN_METEO_WEATHER_URL = "https://api.open-meteo.com/v1/forecast"


class WeatherAPI:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or API_KEY

    def _make_request(self, url: str, params: Dict = None) -> Optional[Dict]:
        if params:
            query = urllib.parse.urlencode(params)
            url = f"{url}?{query}"
        
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "WeatherOutfitAgent/1.0"})
            with urllib.request.urlopen(req, timeout=API_TIMEOUT) as response:
                data = json.loads(response.read().decode("utf-8"))
                return data
        except Exception as e:
            print(f"请求失败: {e}")
        return None

    def get_city_id_open_meteo(self, city_name: str) -> Optional[Dict]:
        data = self._make_request(OPEN_METEO_GEO_URL, {"name": city_name, "count": 1, "language": "zh", "format": "json"})
        if data and data.get("results"):
            loc = data["results"][0]
            return {
                "id": f"{loc.get('latitude')},{loc.get('longitude')}",
                "name": loc.get("name"),
                "lat": loc.get("latitude"),
                "lon": loc.get("longitude"),
                "adm1": loc.get("admin1"),
                "adm2": loc.get("admin2"),
                "country": loc.get("country"),
            }
        return None

    def get_weather_forecast_open_meteo(self, lat: float, lon: float) -> Optional[Dict]:
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": "temperature_2m_max,temperature_2m_min,weathercode,precipitation_sum,windspeed_10m_max,winddirection_10m_dominant",
            "timezone": "auto",
            "forecast_days": DEFAULT_DAYS,
        }
        return self._make_request(OPEN_METEO_WEATHER_URL, params)

    def get_current_weather_open_meteo(self, lat: float, lon: float) -> Optional[Dict]:
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,wind_direction_10m",
            "timezone": "auto",
        }
        return self._make_request(OPEN_METEO_WEATHER_URL, params)

    def _weather_code_to_text(self, code: int) -> str:
        weather_codes = {
            0: "晴",
            1: "晴", 2: "多云", 3: "阴",
            45: "雾", 48: "雾",
            51: "小雨", 53: "中雨", 55: "大雨",
            61: "小雨", 63: "中雨", 65: "大雨",
            71: "小雪", 73: "中雪", 75: "大雪",
            80: "小雨", 81: "中雨", 82: "大雨",
            95: "雷暴", 96: "雷暴", 99: "雷暴",
        }
        return weather_codes.get(code, "多云")

    def get_city_id(self, city_name: str) -> Optional[Dict]:
        if self.api_key and self.api_key != "your_hefeng_key":
            return self._get_city_id_hefeng(city_name)
        return self.get_city_id_open_meteo(city_name)

    def _get_city_id_hefeng(self, city_name: str) -> Optional[Dict]:
        url = f"{GEO_BASE_URL}lookup"
        data = self._make_request(url, {"location": city_name, "key": self.api_key})
        if data and data.get("code") == "200" and data.get("location"):
            loc = data["location"][0]
            return {
                "id": loc.get("id"),
                "name": loc.get("name"),
                "lat": loc.get("lat"),
                "lon": loc.get("lon"),
                "adm1": loc.get("adm1"),
                "adm2": loc.get("adm2"),
            }
        return None

    def get_weather_forecast(self, location_id: str, days: int = None) -> Optional[Dict]:
        if "," in location_id:
            lat, lon = location_id.split(",")
            return self.get_weather_forecast_open_meteo(float(lat), float(lon))
        return self._get_forecast_hefeng(location_id, days)

    def _get_forecast_hefeng(self, location_id: str, days: int = None) -> Optional[Dict]:
        days = days or DEFAULT_DAYS
        url = f"{API_BASE_URL}{days}d"
        data = self._make_request(url, {"location": location_id, "key": self.api_key})
        if data and data.get("code") == "200":
            return data
        return None

    def get_weather_now(self, location_id: str) -> Optional[Dict]:
        if "," in location_id:
            lat, lon = location_id.split(",")
            return self.get_current_weather_open_meteo(float(lat), float(lon))
        return self._get_now_hefeng(location_id)

    def _get_now_hefeng(self, location_id: str) -> Optional[Dict]:
        url = f"{API_BASE_URL}now"
        data = self._make_request(url, {"location": location_id, "key": self.api_key})
        if data and data.get("code") == "200":
            return data
        return None


def fetch_weather_data(city: str, api_key: str = None) -> Optional[Dict]:
    weather_api = WeatherAPI(api_key)
    city_info = weather_api.get_city_id(city)
    if not city_info:
        print(f"未找到城市: {city}")
        return None
    
    location_id = city_info["id"]
    now_data = weather_api.get_weather_now(location_id)
    forecast_data = weather_api.get_weather_forecast(location_id, DEFAULT_DAYS)
    
    if not now_data or not forecast_data:
        print("获取天气数据失败")
        return None
    
    if "," in location_id:
        return _convert_open_meteo_data(city_info, now_data, forecast_data, weather_api)
    return {
        "city": city_info,
        "now": now_data.get("now", {}),
        "forecast": forecast_data.get("daily", []),
    }


def _convert_open_meteo_data(city_info: Dict, now_data: Dict, forecast_data: Dict, api: WeatherAPI) -> Dict:
    current = now_data.get("current", {})
    daily = forecast_data.get("daily", {})
    
    weather_code = current.get("weather_code", 0)
    
    now = {
        "temp": str(int(current.get("temperature_2m", 20))),
        "humidity": str(int(current.get("relative_humidity_2m", 50))),
        "text": api._weather_code_to_text(weather_code),
        "windScale": str(int(current.get("wind_speed_10m", 10) / 10)),
        "windDir": _wind_direction(current.get("wind_direction_10m", 0)),
    }
    
    dates = daily.get("time", [])
    forecast = []
    for i, date in enumerate(dates):
        day_code = daily.get("weather_code", [0])[i] if i < len(daily.get("weather_code", [])) else 0
        forecast.append({
            "fxDate": date,
            "tempMax": str(int(daily.get("temperature_2m_max", [20])[i] if i < len(daily.get("temperature_2m_max", [])) else 20)),
            "tempMin": str(int(daily.get("temperature_2m_min", [10])[i] if i < len(daily.get("temperature_2m_min", [])) else 10)),
            "textDay": api._weather_code_to_text(day_code),
            "textNight": api._weather_code_to_text(day_code),
            "windDirDay": _wind_direction(daily.get("winddirection_10m_dominant", [180])[i] if i < len(daily.get("winddirection_10m_dominant", [])) else 180),
            "windScaleDay": str(int((daily.get("windspeed_10m_max", [10])[i] if i < len(daily.get("windspeed_10m_max", [])) else 10) / 10)),
            "humidity": str(50 + (i * 5) % 30),
            "precip": str(daily.get("precipitation_sum", [0])[i] if i < len(daily.get("precipitation_sum", [])) else 0),
        })
    
    return {
        "city": city_info,
        "now": now,
        "forecast": forecast,
    }


def _wind_direction(degrees: int) -> str:
    directions = ["北风", "东北风", "东风", "东南风", "南风", "西南风", "西风", "西北风"]
    index = int((degrees + 22.5) / 45) % 8
    return directions[index]


def get_mock_weather_data(city: str) -> Dict:
    import random
    from datetime import datetime, timedelta
    
    base_temps = {
        "北京": (10, 25), "上海": (15, 28), "广州": (20, 32),
        "深圳": (21, 31), "杭州": (14, 26), "成都": (16, 24),
        "武汉": (15, 27), "西安": (12, 26), "重庆": (18, 30),
        "南京": (14, 26),
    }
    
    base = base_temps.get(city, (15, 27))
    forecast = []
    today = datetime.now()
    
    for i in range(7):
        date = today + timedelta(days=i)
        temp_max = base[1] + random.randint(-3, 3)
        temp_min = base[0] + random.randint(-3, 3)
        cond = random.choice(["晴", "多云", "阴", "小雨", "晴"])
        
        forecast.append({
            "fxDate": date.strftime("%Y-%m-%d"),
            "tempMax": str(temp_max),
            "tempMin": str(temp_min),
            "textDay": cond,
            "textNight": cond,
            "windDirDay": random.choice(["北风", "南风", "东风", "西风"]),
            "windScaleDay": str(random.randint(1, 4)),
            "humidity": str(random.randint(40, 80)),
            "precip": str(random.randint(0, 10)),
        })
    
    return {
        "city": {"name": city, "adm1": "默认", "adm2": "默认"},
        "now": {
            "temp": str(base[0] + random.randint(3, 8)),
            "humidity": str(random.randint(40, 70)),
            "text": forecast[0]["textDay"],
            "windScale": "2",
            "windDir": "北风",
        },
        "forecast": forecast,
    }
