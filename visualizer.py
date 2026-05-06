from typing import Dict, List
from datetime import datetime
import os


class WeatherVisualizer:
    def __init__(self, weather_data: Dict):
        self.data = weather_data
        self.forecast = weather_data.get("forecast", [])
        self.city_name = weather_data.get("city", {}).get("name", "天气")

    def _get_dates(self) -> List[str]:
        dates = []
        for day in self.forecast:
            date_str = day.get("fxDate", "")
            if date_str:
                try:
                    dt = datetime.strptime(date_str, "%Y-%m-%d")
                    dates.append(dt.strftime("%m/%d"))
                except:
                    dates.append(date_str[-5:])
        return dates

    def _get_weather_icon(self, condition: str) -> str:
        icons = {
            "晴": "☀️", "多云": "⛅", "阴": "☁️",
            "小雨": "🌧️", "中雨": "🌧️", "大雨": "⛈️",
            "小雪": "🌨️", "中雪": "❄️", "大雪": "🌨️",
            "雾": "🌫️", "霾": "🌫️", "沙尘": "💨",
        }
        return icons.get(condition, "🌤️")

    def plot_ascii_temperature_chart(self) -> str:
        if not self.forecast:
            return ""
        
        dates = self._get_dates()
        temp_max = [int(day.get("tempMax", 0)) for day in self.forecast]
        temp_min = [int(day.get("tempMin", 0)) for day in self.forecast]
        
        chart = f"\n📊 {self.city_name} 未来7天温度趋势\n"
        chart += "=" * 60 + "\n"
        
        all_temps = temp_max + temp_min
        min_temp = min(all_temps)
        max_temp = max(all_temps)
        temp_range = max_temp - min_temp + 2
        
        height = 8
        for row in range(height, -1, -1):
            temp_line = min_temp + (temp_range * row // height)
            line = f"{temp_line:3}°C |"
            
            for i in range(len(dates)):
                t_min = temp_min[i]
                t_max = temp_max[i]
                
                if temp_line <= t_max and temp_line >= t_min:
                    if temp_line == t_max:
                        line += " ▲ "
                    elif temp_line == t_min:
                        line += " ▼ "
                    else:
                        line += " │ "
                else:
                    line += "   "
            
            chart += line + "\n"
        
        chart += "      +" + "-" * (len(dates) * 3 + 1) + "\n"
        chart += "        "
        
        for i, date in enumerate(dates):
            day_data = self.forecast[i]
            cond = day_data.get("textDay", "")
            icon = self._get_weather_icon(cond)
            chart += f"{date}{icon[:1]}"
        
        chart += "\n"
        chart += "      "
        for i, date in enumerate(dates):
            day_data = self.forecast[i]
            chart += f" {day_data.get('tempMax', 'N/A')}°"
        
        chart += "\n      "
        for i, date in enumerate(dates):
            day_data = self.forecast[i]
            chart += f" {day_data.get('tempMin', 'N/A')}°"
        
        chart += "\n"
        return chart

    def plot_weather_calendar(self) -> str:
        if not self.forecast:
            return ""
        
        dates = self._get_dates()
        
        calendar = f"\n📅 {self.city_name} 天气预报\n"
        calendar += "=" * 60 + "\n"
        
        for i, day in enumerate(self.forecast):
            date = dates[i]
            cond = day.get("textDay", "未知")
            icon = self._get_weather_icon(cond)
            t_max = day.get("tempMax", "N/A")
            t_min = day.get("tempMin", "N/A")
            humidity = day.get("humidity", "N/A")
            wind = f"{day.get('windDirDay', '')}{day.get('windScaleDay', '')}级"
            
            calendar += f"""
┌─ {date} {icon} {cond} ─┐
│  温度: {t_min}°C ~ {t_max}°C   │
│  湿度: {humidity}%          │
│  风力: {wind}          │
└────────────────────┘
"""
        
        return calendar

    def plot_weather_comparison(self) -> str:
        if not self.forecast:
            return ""
        
        dates = self._get_dates()
        
        comparison = f"\n📈 {self.city_name} 天气对比\n"
        comparison += "=" * 60 + "\n"
        comparison += f"{'日期':^8} | {'天气':^6} | {'最高':^6} | {'最低':^6} | {'湿度':^6}\n"
        comparison += "-" * 50 + "\n"
        
        for i, day in enumerate(self.forecast):
            date = dates[i]
            cond = day.get("textDay", "未知")[:4]
            t_max = day.get("tempMax", "N/A")
            t_min = day.get("tempMin", "N/A")
            humidity = day.get("humidity", "N/A")
            
            comparison += f"{date:^8} | {cond:^6} | {t_max+'°':^6} | {t_min+'°':^6} | {humidity+'%':^6}\n"
        
        return comparison

    def generate_all_charts(self) -> str:
        temp_chart = self.plot_ascii_temperature_chart()
        calendar = self.plot_weather_calendar()
        comparison = self.plot_weather_comparison()
        
        return f"{temp_chart}\n{calendar}\n{comparison}"


def create_weather_charts(weather_data: Dict, output_dir: str = None) -> Dict[str, str]:
    visualizer = WeatherVisualizer(weather_data)
    
    chart_text = visualizer.generate_all_charts()
    
    if output_dir:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        file_path = os.path.join(output_dir, "weather_charts.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(chart_text)
        return {"text": file_path}
    
    return {"text": chart_text}
