import json
import math
import os
import re
import urllib.parse
import urllib.request

try:
    import requests
except ImportError:
    requests = None

DEFAULT_CITY = '成都'

CITY_COORDINATES = {
    '北京': (39.9042, 116.4074),
    '上海': (31.2304, 121.4737),
    '广州': (23.1291, 113.2644),
    '深圳': (22.5431, 114.0579),
    '杭州': (30.2741, 120.1551),
    '成都': (30.5728, 104.0668),
    '武汉': (30.5928, 114.3055),
    '西安': (34.3416, 108.9398),
    '重庆': (29.5630, 106.5516),
    '南京': (32.0603, 118.7969),
    '天津': (39.3434, 117.3616),
    '苏州': (31.2989, 120.5853),
    '郑州': (34.7466, 113.6253),
    '长沙': (28.2282, 112.9388),
    '青岛': (36.0671, 120.3826),
    '沈阳': (41.8057, 123.4315),
    '大连': (38.9140, 121.6147),
    '厦门': (24.4798, 118.0894),
    '宁波': (29.8683, 121.5440),
    '昆明': (25.0389, 102.7183),
    '哈尔滨': (45.8038, 126.5350),
    '长春': (43.8171, 125.3235),
    '石家庄': (38.0428, 114.5149),
    '太原': (37.8706, 112.5489),
    '济南': (36.6512, 117.1201),
    '合肥': (31.8206, 117.2272),
    '福州': (26.0745, 119.2965),
    '南昌': (28.6820, 115.8579),
    '贵阳': (26.6470, 106.6302),
    '南宁': (22.8170, 108.3665),
    '海口': (20.0440, 110.1999),
    '拉萨': (29.6520, 91.1721),
    '乌鲁木齐': (43.8256, 87.6168),
    '呼和浩特': (40.8414, 111.7519),
    '银川': (38.4872, 106.2309),
    '西宁': (36.6171, 101.7782),
    '兰州': (36.0611, 103.8343),
}

CHINA_CITIES = set(CITY_COORDINATES.keys())


def normalize_city_name(city):
    if not city:
        return None
    city = city.strip().replace('市', '').replace('省', '')
    if city in CHINA_CITIES:
        return city
    for china_city in CHINA_CITIES:
        if china_city in city or city in china_city:
            return china_city
    return city if city else None


def _get_proxies():
    proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('HTTP_PROXY')
    if not proxy:
        return None
    return {'http': proxy, 'https': proxy}


def _http_get(url, timeout=8, encoding='utf-8', use_proxy=True):
    headers = {'User-Agent': 'WeatherOutfitAgent/1.0'}

    if requests is not None:
        try:
            proxies = _get_proxies() if use_proxy else None
            resp = requests.get(url, headers=headers, proxies=proxies, timeout=timeout)
            resp.raise_for_status()
            if encoding == 'gbk':
                resp.encoding = 'gbk'
            return resp.text
        except Exception as e:
            print(f'requests GET 失败 {url}: {e}')

    try:
        req = urllib.request.Request(url, headers=headers)
        handlers = []
        if use_proxy and _get_proxies():
            p = _get_proxies()['http']
            handlers.append(urllib.request.ProxyHandler({'http': p, 'https': p}))
        opener = urllib.request.build_opener(*handlers)
        with opener.open(req, timeout=timeout) as response:
            raw = response.read()
            return raw.decode(encoding, errors='replace')
    except Exception as e:
        print(f'urllib GET 失败 {url}: {e}')
    return None


def get_nearest_city(lat, lon):
    if lat is None or lon is None:
        return None

    best_city = None
    best_dist = float('inf')

    for city, (city_lat, city_lon) in CITY_COORDINATES.items():
        dist = _haversine_km(float(lat), float(lon), city_lat, city_lon)
        if dist < best_dist:
            best_dist = dist
            best_city = city

    if best_city:
        print(f'最近城市匹配: {best_city} (约 {best_dist:.0f}km)')
    return best_city


def _haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def get_city_from_ip_pconline():
    try:
        text = _http_get('https://whois.pconline.com.cn/ipJson.jsp?json=true', encoding='gbk')
        if not text:
            return None, None

        match = re.search(r'\{.*\}', text, re.DOTALL)
        if not match:
            return None, None

        data = json.loads(match.group())
        city = normalize_city_name(data.get('city', ''))
        if city:
            print(f'IP定位成功 (pconline): {city}')
            return city, 'pconline'

        pro = normalize_city_name(data.get('pro', ''))
        if pro:
            print(f'IP定位成功 (pconline 省份): {pro}')
            return pro, 'pconline'
    except Exception as e:
        print(f'pconline 定位失败: {e}')
    return None, None


def get_city_from_ip_remote():
    apis = [
        ('http://ip-api.com/json/?fields=status,country,city,lat,lon&lang=zh-CN', 'ip-api'),
        ('https://ipwho.is/', 'ipwho'),
        ('https://ip.useragentinfo.com/json', 'useragentinfo'),
    ]

    for url, api_name in apis:
        try:
            text = _http_get(url, use_proxy=True)
            if not text:
                text = _http_get(url, use_proxy=False)
            if not text:
                continue

            data = json.loads(text)
            city = None
            lat = None
            lon = None

            if api_name == 'ip-api':
                if data.get('status') != 'success':
                    continue
                city = data.get('city', '')
                lat = data.get('lat')
                lon = data.get('lon')
            elif api_name == 'ipwho':
                if not data.get('success'):
                    continue
                city = data.get('city', '')
                lat = data.get('latitude')
                lon = data.get('longitude')
            else:
                city = data.get('city', '')
                lat = data.get('lat')
                lon = data.get('lon')

            normalized = normalize_city_name(city)
            if normalized:
                print(f'IP定位成功 ({api_name}): {normalized}')
                return normalized, api_name

            if lat is not None and lon is not None:
                nearest = get_nearest_city(lat, lon)
                if nearest:
                    print(f'IP坐标最近城市 ({api_name}): {nearest}')
                    return nearest, f'{api_name}-nearest'
        except Exception as e:
            print(f'定位API {api_name} 失败: {e}')
    return None, None


def get_city_from_ip():
    city, source = get_city_from_ip_pconline()
    if city:
        return city, source

    city, source = get_city_from_ip_remote()
    if city:
        return city, source

    print(f'所有 IP 定位失败，使用默认城市: {DEFAULT_CITY}')
    return DEFAULT_CITY, 'default'


def get_city_from_coords(lat, lon):
    nearest = get_nearest_city(lat, lon)
    if nearest:
        return nearest, 'nearest'

    try:
        url = (
            'https://api.bigdatacloud.net/data/reverse-geocode-client'
            f'?latitude={lat}&longitude={lon}&localityLanguage=zh'
        )
        text = _http_get(url, use_proxy=True)
        if text:
            data = json.loads(text)
            city = (
                data.get('city')
                or data.get('locality')
                or data.get('principalSubdivision')
                or ''
            )
            normalized = normalize_city_name(city)
            if normalized:
                print(f'坐标反查成功 (bigdatacloud): {normalized}')
                return normalized, 'reverse'

    except Exception as e:
        print(f'坐标反查失败: {e}')

    return DEFAULT_CITY, 'default'
