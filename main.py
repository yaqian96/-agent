import os
import sys

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import os
import sys
from weather_api import fetch_weather_data, get_mock_weather_data
from analyzer import analyze_weather
from visualizer import create_weather_charts
from outfit_recommender import recommend_outfit


class WeatherOutfitAgent:
    def __init__(self, api_key: str = None, use_mock: bool = False):
        self.api_key = api_key
        self.use_mock = use_mock
        self.weather_data = None
        self.analysis = None
        self.charts = None

    def fetch_data(self, city: str) -> bool:
        print(f"\n[INFO] 正在获取 {city} 的天气数据...")
        
        if self.use_mock:
            self.weather_data = get_mock_weather_data(city)
        else:
            self.weather_data = fetch_weather_data(city, self.api_key)
        
        if not self.weather_data:
            print(f"[ERROR] 获取天气数据失败")
            return False
        
        print(f"[OK] 成功获取天气数据!")
        return True

    def analyze(self):
        print(f"\n[INFO] 正在分析天气数据...")
        self.analysis = analyze_weather(self.weather_data)
        print(f"[OK] 天气分析完成!")

    def visualize(self, output_dir: str = "charts") -> bool:
        print(f"\n[INFO] 正在生成天气趋势图...")
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        self.charts = create_weather_charts(self.weather_data, output_dir)
        
        chart_output = self.charts.get("text", "")
        if os.path.exists(chart_output):
            print(f"[OK] 图表已保存到: {chart_output}")
        else:
            print(f"[OK] 图表生成完成!")
        
        return True

    def recommend_outfit(self) -> str:
        print(f"\n[INFO] 正在生成穿搭建议...")
        recommendation = recommend_outfit(self.weather_data, self.analysis)
        print(f"[OK] 穿搭建议生成完成!")
        return recommendation

    def run(self, city: str, show_charts: bool = True, output_dir: str = "charts"):
        print("=" * 60)
        print("  智能天气穿搭助手")
        print("=" * 60)
        
        if not self.fetch_data(city):
            return None
        
        self.analyze()
        
        print("\n" + "=" * 60)
        print(" 天气分析报告")
        print("=" * 60)
        print(self.analysis.get("report", ""))
        
        if show_charts:
            self.visualize(output_dir)
            chart_text = self.charts.get("text", "")
            if os.path.exists(chart_text):
                with open(chart_text, "r", encoding="utf-8") as f:
                    print(f.read())
            else:
                print(chart_text)
        
        recommendation = self.recommend_outfit()
        
        print("\n" + recommendation)
        
        return {
            "weather_data": self.weather_data,
            "analysis": self.analysis,
            "charts": self.charts,
            "recommendation": recommendation,
        }


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="智能天气穿搭助手")
    parser.add_argument("city", nargs="?", help="城市名称")
    parser.add_argument("--key", "-k", help="和风天气API Key", default=None)
    parser.add_argument("--mock", "-m", help="使用模拟数据(测试用)", action="store_true")
    parser.add_argument("--no-chart", "-n", help="不生成图表", action="store_true")
    parser.add_argument("--output", "-o", help="图表输出目录", default="charts")
    
    args = parser.parse_args()
    
    if not args.city:
        args.city = input("请输入城市名称: ").strip()
    
    if not args.city:
        print("ERROR: 请输入城市名称")
        return
    
    use_mock = args.mock
    if not use_mock and not args.key:
        print("\nWARNING: 未提供API Key，将使用模拟数据")
        print("   如需使用真实数据，请: python main.py <城市> --key <你的API Key>")
        print("   免费API Key申请: https://dev.qweather.com/")
        use_mock = True
    
    agent = WeatherOutfitAgent(api_key=args.key, use_mock=use_mock)
    
    try:
        result = agent.run(
            city=args.city, 
            show_charts=not args.no_chart,
            output_dir=args.output
        )
        
        if result:
            print("\n" + "=" * 60)
            print(" 查询完成! 祝您生活愉快~")
            print("=" * 60)
    except KeyboardInterrupt:
        print("\n\nERROR: 用户取消查询")
    except Exception as e:
        print(f"\nERROR: 发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
