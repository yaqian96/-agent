from typing import Dict, List
from datetime import datetime


class OutfitRecommender:
    def __init__(self, weather_data: Dict, analysis: Dict):
        self.data = weather_data
        self.analysis = analysis
        self.current = analysis.get("current", {})
        self.temp_trend = analysis.get("temp_trend", {})
        self.wind = analysis.get("wind", {})
        self.precipitation = analysis.get("precipitation", {})
        self.uv = analysis.get("uv", {})
        self.comfort = analysis.get("comfort", {})

    def _get_base_outfit(self) -> Dict[str, str]:
        temp = int(self.current.get("temp", 20))
        condition = self.current.get("condition", "晴")
        
        if temp >= 35:
            return {
                "category": "盛夏酷暑",
                "top": "透气短袖/背心",
                "bottom": "轻薄短裤/短裙",
                "shoes": "凉鞋/拖鞋",
                "accessory": "遮阳帽/太阳镜/防晒伞",
                "fabric": "棉麻/透气面料",
            }
        elif temp >= 30:
            return {
                "category": "夏季炎热",
                "top": "短袖T恤/薄衬衫",
                "bottom": "短裤/轻薄长裤",
                "shoes": "透气运动鞋/凉鞋",
                "accessory": "太阳镜/遮阳帽",
                "fabric": "棉麻/雪纺",
            }
        elif temp >= 25:
            return {
                "category": "春末夏初",
                "top": "长袖T恤/薄款卫衣/衬衫",
                "bottom": "长裤/牛仔裤/长裙",
                "shoes": "运动鞋/休闲鞋",
                "accessory": "薄外套(早晚备)",
                "fabric": "棉/混纺",
            }
        elif temp >= 18:
            return {
                "category": "春秋温和",
                "top": "毛衣/针织衫/薄外套",
                "bottom": "牛仔裤/长裤",
                "shoes": "运动鞋/皮鞋",
                "accessory": "可增减衣物",
                "fabric": "棉/羊毛/针织",
            }
        elif temp >= 10:
            return {
                "category": "早春/深秋",
                "top": "厚毛衣/风衣/大衣",
                "bottom": "保暖长裤/加绒裤",
                "shoes": "靴子/保暖鞋",
                "accessory": "围巾/手套",
                "fabric": "羊毛/呢子/加绒",
            }
        elif temp >= 5:
            return {
                "category": "初冬",
                "top": "羽绒服/厚棉服/大衣",
                "bottom": "加绒裤/保暖裤",
                "shoes": "保暖靴子",
                "accessory": "围巾/手套/帽子",
                "fabric": "羽绒服/厚棉",
            }
        else:
            return {
                "category": "严寒冬季",
                "top": "羽绒服(厚款)/滑雪服",
                "bottom": "加厚保暖裤",
                "shoes": "雪地靴/保暖靴",
                "accessory": "厚围巾/手套/帽子/耳罩",
                "fabric": "专业防寒",
            }

    def _get_rain_outfit(self) -> Dict[str, str]:
        rainy_days = self.precipitation.get("rainy_days", 0)
        
        if rainy_days >= 5:
            return {
                "rain": "[RAIN] 本周多雨(5天以上)，务必随身带伞!",
                "items": ["雨伞/折叠伞", "防滑鞋", "防水包"],
                "tips": "建议穿防泼水外套，避免牛仔裤吸湿后变重",
            }
        elif rainy_days >= 3:
            return {
                "rain": "[RAIN] 本周多雨(3天以上)，记得带伞",
                "items": ["雨伞", "防滑鞋"],
                "tips": "带把折叠伞备用",
            }
        elif rainy_days >= 1:
            return {
                "rain": "[RAIN] 可能有雨(1-2天)，建议带伞",
                "items": ["雨伞"],
                "tips": "关注天气预报，有备无患",
            }
        return {
            "rain": "[CLEAR] 本周无明显降水",
            "items": [],
            "tips": "无需特别准备雨具",
        }

    def _get_wind_outfit(self) -> Dict[str, str]:
        wind_level = self.wind.get("level", "微风")
        
        if wind_level == "强风":
            return {
                "wind": "[WIND] 今天风速较大，建议穿防风外套!",
                "tips": "避免穿宽松衣物，建议扎起头发",
            }
        elif wind_level == "较大":
            return {
                "wind": "[WIND] 风速较大，注意防风",
                "tips": "穿有防风设计的外套",
            }
        return {
            "wind": "[CALM] 风力适中，体感舒适",
            "tips": "正常穿着即可",
        }

    def _get_uv_advice(self) -> str:
        uv_level = self.uv
        
        if uv_level == "高":
            return "[UV] 紫外线强度高! 务必涂防晒霜,戴遮阳帽和太阳镜,长时间外出需打伞"
        elif uv_level == "中等":
            return "[UV] 紫外线中等强度,建议涂抹防晒霜,避免长时间直晒"
        return "[UV] 紫外线强度较低,正常活动即可"

    def _get_special_advice(self) -> List[str]:
        advices = []
        temp = int(self.current.get("temp", 20))
        comfort_level = self.comfort.get("level", "舒适")
        
        if comfort_level == "不舒适" or comfort_level == "不太舒适":
            advices.append("[NOTICE] 今日体感较差，建议减少户外活动时间")
        
        if temp >= 28:
            advices.append("[TIP] 多补充水分，建议随身携带水杯")
            advices.append("[TIP] 可适当食用解暑水果")
        elif temp <= 10:
            advices.append("[TIP] 注意护肤，防止皮肤干燥")
            advices.append("[TIP] 建议喝热饮暖身")
        
        if self.precipitation.get("rainy_days", 0) >= 3:
            advices.append("[TIP] 建议携带备用衣物，以防淋湿")
        
        if self.wind.get("max_scale", 0) >= 5:
            advices.append("[SAFETY] 强风天气避免在广告牌或大树下方行走")
        
        return advices

    def _get_trend_advice(self) -> str:
        trend = self.temp_trend.get("trend", "平稳")
        
        if trend == "升温":
            return "[TREND] 气温正在回升，建议穿便于增减的衣物，早晚可备薄外套"
        elif trend == "降温":
            return "[TREND] 气温正在下降，建议增加衣物，注意保暖"
        return "[TREND] 气温变化平稳，穿着无需大幅调整"

    def generate_outfit_recommendation(self) -> str:
        base = self._get_base_outfit()
        rain = self._get_rain_outfit()
        wind = self._get_wind_outfit()
        uv_advice = self._get_uv_advice()
        special = self._get_special_advice()
        trend_advice = self._get_trend_advice()
        
        current = self.current
        city = current.get("city", "")
        temp = current.get("temp", "N/A")
        condition = current.get("condition", "")
        
        recommendation = f"""
==================================================
========== OUTFIT RECOMMENDATION - {city} ==========
==================================================

Date: {datetime.now().strftime('%Y-%m-%d %A')}
Current: {temp}C, {condition}

[BASIC OUTFIT] ({base['category']})
  TOP: {base['top']}
  BOTTOM: {base['bottom']}
  SHOES: {base['shoes']}
  ACCESSORIES: {base['accessory']}
  FABRIC: {base['fabric']}

[RAIN ALERT]
  {rain['rain']}
  Items: {', '.join(rain['items']) if rain['items'] else 'None'}
  Tips: {rain['tips']}

[WIND ADVICE]
  {wind['wind']}
  Tips: {wind['tips']}

[UV PROTECTION]
  {uv_advice}

[TEMPERATURE TREND]
  {trend_advice}

[SPECIAL NOTICES]
"""
        for advice in special:
            recommendation += f"  {advice}\n"
        
        recommendation += f"""
==================================================
[TIP] 早晚温差较大时,建议采用"洋葱式"穿搭法
   便于根据温度变化随时增减衣物
==================================================
"""
        return recommendation

    def get_outfit_summary(self) -> Dict:
        base = self._get_base_outfit()
        rain = self._get_rain_outfit()
        
        return {
            "category": base["category"],
            "outfit": {
                "top": base["top"],
                "bottom": base["bottom"],
                "shoes": base["shoes"],
                "accessory": base["accessory"],
                "fabric": base["fabric"],
            },
            "rain_alert": rain["rain"],
            "must_have_items": rain["items"],
        }


def recommend_outfit(weather_data: Dict, analysis: Dict) -> str:
    recommender = OutfitRecommender(weather_data, analysis)
    return recommender.generate_outfit_recommendation()
