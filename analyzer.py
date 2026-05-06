from typing import Dict, List
from datetime import datetime


class WeatherAnalyzer:
    def __init__(self, weather_data: Dict):
        self.data = weather_data
        self.city_name = weather_data.get("city", {}).get("name", "未知")
        self.now = weather_data.get("now", {})
        self.forecast = weather_data.get("forecast", [])

    def get_current_weather(self) -> Dict:
        return {
            "city": self.city_name,
            "temp": self.now.get("temp", "N/A"),
            "condition": self.now.get("text", "未知"),
            "humidity": self.now.get("humidity", "N/A"),
            "wind": f"{self.now.get('windDir', '')} {self.now.get('windScale', '')}级",
        }

    def analyze_temperature_trend(self) -> Dict:
        if not self.forecast:
            return {}
        
        temps = [(day["fxDate"], int(day["tempMin"]), int(day["tempMax"])) for day in self.forecast]
        temp_range = [t[1] for t in temps] + [t[2] for t in temps]
        
        trend = "平稳"
        if len(temps) >= 3:
            diff = temps[-1][2] - temps[0][2]
            if diff > 5:
                trend = "升温"
            elif diff < -5:
                trend = "降温"
        
        return {
            "trend": trend,
            "min_temp": min(temp_range),
            "max_temp": max(temp_range),
            "avg_temp": sum(temp_range) // len(temp_range),
        }

    def analyze_conditions(self) -> List[str]:
        conditions = {}
        for day in self.forecast:
            cond = day.get("textDay", "未知")
            conditions[cond] = conditions.get(cond, 0) + 1
        
        sorted_conds = sorted(conditions.items(), key=lambda x: x[1], reverse=True)
        return [f"{c[0]}({c[1]}天)" for c in sorted_conds[:3]]

    def analyze_wind(self) -> Dict:
        wind_scales = []
        for day in self.forecast:
            scale = int(day.get("windScaleDay", "0"))
            wind_scales.append(scale)
        
        avg_scale = sum(wind_scales) // len(wind_scales) if wind_scales else 0
        wind_level = "微风" if avg_scale <= 2 else "较大" if avg_scale <= 4 else "强风"
        
        return {
            "level": wind_level,
            "avg_scale": avg_scale,
            "max_scale": max(wind_scales) if wind_scales else 0,
        }

    def analyze_precipitation(self) -> Dict:
        precip_days = 0
        total_precip = 0
        
        for day in self.forecast:
            precip = float(day.get("precip", "0"))
            if precip > 0:
                precip_days += 1
            total_precip += precip
        
        return {
            "rainy_days": precip_days,
            "total_precip": total_precip,
            "rain_probability": (precip_days / len(self.forecast) * 100) if self.forecast else 0,
        }

    def get_uv_index(self) -> str:
        month = datetime.now().month
        if month in [5, 6, 7, 8]:
            return "高"
        elif month in [3, 4, 9, 10]:
            return "中等"
        return "低"

    def analyze_comfort(self) -> Dict:
        temp = int(self.now.get("temp", 20))
        humidity = int(self.now.get("humidity", 50))
        
        comfort_score = 100
        
        if temp < 5 or temp > 35:
            comfort_score -= 30
        elif temp < 10 or temp > 30:
            comfort_score -= 15
        
        if humidity < 30 or humidity > 80:
            comfort_score -= 20
        elif humidity < 40 or humidity > 70:
            comfort_score -= 10
        
        wind_scale = int(self.now.get("windScale", 0))
        if wind_scale >= 5:
            comfort_score -= 15
        elif wind_scale >= 3:
            comfort_score -= 5
        
        if comfort_score >= 80:
            comfort_level = "舒适"
        elif comfort_score >= 60:
            comfort_level = "较舒适"
        elif comfort_score >= 40:
            comfort_level = "不太舒适"
        else:
            comfort_level = "不舒适"
        
        return {
            "score": comfort_score,
            "level": comfort_level,
            "reasons": [],
        }

    def generate_analysis_report(self) -> str:
        current = self.get_current_weather()
        temp_trend = self.analyze_temperature_trend()
        conditions = self.analyze_conditions()
        wind = self.analyze_wind()
        precip = self.analyze_precipitation()
        comfort = self.analyze_comfort()
        uv = self.get_uv_index()
        
        report = f"""
[LOCATION] City: {current['city']}
[CURRENT] Temperature: {current['temp']}C, {current['condition']}
[HUMIDITY] Humidity: {current['humidity']}%
[WIND] Wind: {current['wind']}

[TEMP TREND] Future 7 days: {temp_trend.get('trend', 'stable')} 
   Range: {temp_trend.get('min_temp', 'N/A')}C ~ {temp_trend.get('max_temp', 'N/A')}C
   Average: {temp_trend.get('avg_temp', 'N/A')}C

[CONDITIONS] Weather: {', '.join(conditions)}

[WIND] Wind Level: {wind.get('level', 'N/A')} (avg {wind.get('avg_scale', 0)} level)

[PRECIPITATION] {precip.get('rainy_days', 0)} days with rain, probability {precip.get('rain_probability', 0):.0f}%

[UV] UV Index: {uv} level

[COMFORT] Comfort: {comfort.get('level', 'N/A')} (Score: {comfort.get('score', 0)}/100)
"""
        return report


def analyze_weather(weather_data: Dict) -> Dict:
    analyzer = WeatherAnalyzer(weather_data)
    return {
        "current": analyzer.get_current_weather(),
        "temp_trend": analyzer.analyze_temperature_trend(),
        "conditions": analyzer.analyze_conditions(),
        "wind": analyzer.analyze_wind(),
        "precipitation": analyzer.analyze_precipitation(),
        "uv": analyzer.get_uv_index(),
        "comfort": analyzer.analyze_comfort(),
        "report": analyzer.generate_analysis_report(),
    }
