#!/usr/bin/env python3
import asyncio
import json
import socket

import aiohttp


GEO_APIS = [
    "https://ipapi.co/{ip}/json/",
    "https://ipinfo.io/{ip}/json",
    "https://api.ipgeolocation.io/ipgeo?apiKey=YOUR_KEY&ip={ip}",
    "https://ip-api.com/json/{ip}",
    "https://geolocation-db.com/json/{ip}"
]

CITY_MAP = {
    "US": {
        "New York": (40.7128, -74.0060),
        "Los Angeles": (34.0522, -118.2437),
        "Chicago": (41.8781, -87.6298),
        "Miami": (25.7617, -80.1918),
        "Seattle": (47.6062, -122.3321),
        "Dallas": (32.7767, -96.7970),
        "Atlanta": (33.7490, -84.3880),
        "San Francisco": (37.7749, -122.4194)
    },
    "NL": {
        "Amsterdam": (52.3676, 4.9041),
        "Rotterdam": (51.9244, 4.4777),
        "The Hague": (52.0705, 4.3007)
    },
    "DE": {
        "Frankfurt": (50.1109, 8.6821),
        "Berlin": (52.5200, 13.4050),
        "Munich": (48.1351, 11.5820),
        "Hamburg": (53.5511, 9.9937)
    },
    "SG": {
        "Singapore": (1.3521, 103.8198)
    },
    "JP": {
        "Tokyo": (35.6762, 139.6503),
        "Osaka": (34.6937, 135.5023)
    },
    "KR": {
        "Seoul": (37.5665, 126.9780),
        "Busan": (35.1796, 129.0756)
    },
    "GB": {
        "London": (51.5074, -0.1278),
        "Manchester": (53.4808, -2.2426)
    },
    "FR": {
        "Paris": (48.8566, 2.3522),
        "Marseille": (43.2965, 5.3698)
    },
    "CA": {
        "Toronto": (43.6532, -79.3832),
        "Vancouver": (49.2827, -123.1207)
    },
    "AU": {
        "Sydney": (-33.8688, 151.2093),
        "Melbourne": (-37.8136, 144.9631)
    }
}


class GeoResolver:
    def __init__(self):
        self.cache = {}
        self.session = None
        
    async def init(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10)
        )
        
    async def close(self):
        if self.session:
            await self.session.close()
            
    async def resolve_ip(self, hostname):
        try:
            return socket.gethostbyname(hostname)
        except:
            return None
            
    async def fetch_geo(self, ip):
        if ip in self.cache:
            return self.cache[ip]
            
        for api_url in GEO_APIS:
            try:
                url = api_url.format(ip=ip)
                async with self.session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        result = self.normalize_geo(data)
                        self.cache[ip] = result
                        return result
            except:
                continue
                
        return self.fallback_geo(ip)
        
    def normalize_geo(self, data):
        country = (
            data.get("country_code") or 
            data.get("country") or 
            data.get("countryCode") or
            "US"
        )
        country_name = (
            data.get("country_name") or 
            data.get("country") or
            self.get_country_name(country)
        )
        city = (
            data.get("city") or 
            data.get("region") or
            self.guess_city(country)
        )
        lat = data.get("latitude") or 0
        lon = data.get("longitude") or 0
        
        return {
            "country_code": country.upper()[:2],
            "country_name": country_name,
            "city": city,
            "latitude": float(lat) if lat else 0,
            "longitude": float(lon) if lon else 0
        }
        
    def get_country_name(self, code):
        names = {
            "US": "United States", "NL": "Netherlands", "DE": "Germany",
            "SG": "Singapore", "JP": "Japan", "KR": "South Korea",
            "GB": "United Kingdom", "FR": "France", "CA": "Canada",
            "AU": "Australia", "RU": "Russia", "PL": "Poland",
            "TR": "Turkey", "IN": "India", "BR": "Brazil", "UA": "Ukraine"
        }
        return names.get(code.upper(), "Unknown")
        
    def guess_city(self, country_code):
        cities = CITY_MAP.get(country_code.upper(), {})
        if cities:
            import random
            return random.choice(list(cities.keys()))
        return "Unknown"
        
    def fallback_geo(self, ip):
        octets = ip.split(".")
        if len(octets) == 4:
            first = int(octets[0])
            if first < 128:
                cc = "US"
            elif first < 192:
                cc = "EU"
            else:
                cc = "AS"
        else:
            cc = "US"
            
        return {
            "country_code": cc,
            "country_name": self.get_country_name(cc),
            "city": self.guess_city(cc),
            "latitude": 0,
            "longitude": 0
        }
        
    async def resolve_server_geo(self, hostname):
        ip = await self.resolve_ip(hostname)
        if not ip:
            return self.fallback_geo("0.0.0.0")
        return await self.fetch_geo(ip)
        
    def get_server_name(self, geo_data):
        from update_subscription import COUNTRY_FLAGS
        flag = COUNTRY_FLAGS.get(geo_data["country_code"], "🌍")
        return f"{flag} {geo_data['country_name']} {geo_data['city']}"


async def main():
    resolver = GeoResolver()
    await resolver.init()
    
    test_hosts = ["1.1.1.1", "8.8.8.8", "google.com", "yandex.ru"]
    for host in test_hosts:
        geo = await resolver.resolve_server_geo(host)
        name = resolver.get_server_name(geo)
        print(f"{host} -> {name}")
        print(json.dumps(geo, indent=2))
        print()
        
    await resolver.close()


if __name__ == '__main__':
    asyncio.run(main())
