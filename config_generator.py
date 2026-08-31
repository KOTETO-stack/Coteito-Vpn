#!/usr/bin/env python3
import base64
import json
import os
import time
import uuid

from geo_resolver import GeoResolver
from xray_protection import XrayProtection


class KaringConfigGenerator:
    def __init__(self):
        self.geo = GeoResolver()
        self.protector = XrayProtection()
        
    async def init(self):
        await self.geo.init()
        
    async def close(self):
        await self.geo.close()
        
    def generate_karing_subscription(self, servers, warp_keys=None):
        servers.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        karing_servers = []
        
        if warp_keys:
            for i, warp in enumerate(warp_keys[:3]):
                karing_servers.append({
                    "name": f"🇺🇸 WARP+ Secure {i+1}",
                    "type": "wireguard",
                    "server": "engage.cloudflareclient.com",
                    "port": 2408,
                    "private-key": warp["private_key"],
                    "public-key": "bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo=",
                    "dns": ["1.1.1.1", "1.0.0.1"],
                    "mtu": 1280,
                    "reserved": [0, 0, 0],
                    "udp": True,
                    "warp_enabled": True
                })
                
        karing_servers.append({
            "name": "🔒 AmneziaFree Backup",
            "type": "amnezia",
            "url": "vpn://AAAA_3icXY3LDoIwEEV_hXStJhhjojsjERN0AbowbkgtAzZA2_QBQcO_2xbduJrMPXfmvBHDLaBtgHYtgxfFwUECoFmAClBEUqEpZ_84IJwxIB7Zpt1KWuUdSDWVlzbEguYTsMEbKZAdJZDrQXgbnt7Ny6_tx4XkmhPe-E5fOWQss68M03Kws_D30qDRWYx-5gXW2Eucs4bB8Yg2qyTM-sUjO16u9SmKUxOt92VI6js_dzyNsz7cqOSGxvEDmaFXJg==",
            "auto_update": True
        })
        
        for srv in servers[:150]:
            geo_data = self.geo.resolve_server_geo(srv.get("address"))
            name = self.geo.get_server_name(geo_data)
            
            config = self.build_server_config(srv, name)
            karing_servers.append(config)
            
        subscription = {
            "version": 3,
            "updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "encryption": {
                "enabled": True,
                "key": base64.b64encode(os.urandom(32)).decode()
            },
            "servers": karing_servers,
            "routing": self.build_routing(),
            "dns": self.build_dns(),
            "xray": self.protector.apply_protection({})["xray_protection"],
            "warp_protection": {
                "enabled": True,
                "mode": "always_on",
                "dns_leak_protection": True
            },
            "adblock": {
                "enabled": True,
                "rules_url": "https://raw.githubusercontent.com/YOUR_REPO/main/adblock_rules.txt"
            },
            "auto_update": {
                "interval": 3600,
                "url": "https://raw.githubusercontent.com/YOUR_REPO/main/subscription.txt"
            }
        }
        
        return subscription
        
    def build_server_config(self, srv, name):
        protocol = srv.get("protocol", "vless")
        base = {
            "name": name,
            "type": protocol,
            "server": srv.get("address"),
            "port": int(srv.get("port", 443))
        }
        
        if protocol == "vless":
            base.update({
                "uuid": srv.get("uuid", str(uuid.uuid4())),
                "tls": True,
                "sni": "www.google.com",
                "flow": srv.get("flow", "xtls-rprx-vision"),
                "network": srv.get("type", "tcp"),
                "path": srv.get("path", "/"),
                "encryption": "none",
                "utls": {
                    "enabled": True,
                    "fingerprint": "chrome"
                }
            })
        elif protocol == "trojan":
            base.update({
                "password": srv.get("password"),
                "tls": True,
                "sni": "www.google.com",
                "network": srv.get("type", "tcp"),
                "path": srv.get("path", "/")
            })
        elif protocol == "hysteria2":
            base.update({
                "password": srv.get("password"),
                "sni": "www.google.com",
                "obfs": srv.get("obfs", ""),
                "obfs-password": srv.get("obfs-password", "")
            })
            
        xray = self.protector.generate_xray_outbound(srv)
        base["xray_settings"] = xray.get("streamSettings", {})
        
        return base
        
    def build_routing(self):
        return {
            "rules": [
                {
                    "domain": [
                        "*.yandex.ru", "*.yandex.net", "*.vk.com",
                        "*.mail.ru", "*.gosuslugi.ru", "*.sberbank.ru",
                        "*.tinkoff.ru", "*.avito.ru", "*.ozon.ru",
                        "*.wildberries.ru", "*.2gis.ru", "*.kontur.ru"
                    ],
                    "outbound": "DIRECT"
                },
                {
                    "domain": [
                        "*.youtube.com", "*.googlevideo.com",
                        "*.ytimg.com", "*.youtubei.googleapis.com"
                    ],
                    "outbound": "PROXY",
                    "adblock": True
                },
                {
                    "domain": [
                        "*.telegram.org", "*.telegram.me", "*.t.me",
                        "*.tdesktop.com", "*.teleguapp.com"
                    ],
                    "outbound": "PROXY"
                },
                {
                    "domain": [
                        "*.tiktok.com", "*.tiktokv.com",
                        "*.musical.ly", "*.tiktokcdn.com"
                    ],
                    "outbound": "PROXY"
                },
                {
                    "domain": [
                        "*.wechat.com", "*.weixin.qq.com",
                        "*.wechatapp.com"
                    ],
                    "outbound": "PROXY"
                },
                {
                    "domain": [
                        "*.whatsapp.com", "*.whatsapp.net",
                        "*.wa.me"
                    ],
                    "outbound": "PROXY"
                },
                {
                    "domain": ["*.bip.com"],
                    "outbound": "PROXY"
                },
                {
                    "protocol": ["dns"],
                    "outbound": "DNS"
                }
            ],
            "adblock": {
                "enabled": True,
                "rules": [
                    "||googleadservices.com^",
                    "||doubleclick.net^",
                    "||google-analytics.com^",
                    "||facebook.com/tr^",
                    "||googlesyndication.com^"
                ]
            }
        }
        
    def build_dns(self):
        return {
            "servers": [
                {
                    "address": "https://dns.google/dns-query",
                    "domains": ["geosite:google"]
                },
                {
                    "address": "https://cloudflare-dns.com/dns-query",
                    "domains": ["geosite:cn"]
                },
                "1.1.1.1",
                "8.8.8.8"
            ],
            "hosts": {
                "dns.google": ["8.8.8.8", "8.8.4.4"],
                "cloudflare-dns.com": ["1.1.1.1", "1.0.0.1"]
            },
            "queryStrategy": "UseIPv4",
            "disableFallback": False,
            "disableFallbackIfMatch": True,
            "tag": "dns"
        }
        
    def export(self, subscription, encrypt=False):
        json_data = json.dumps(subscription, indent=2)
        
        if encrypt:
            from cryptography.fernet import Fernet
            key = base64.urlsafe_b64encode(
                subscription["encryption"]["key"].encode()[:32]
            )
            f = Fernet(key)
            encrypted = f.encrypt(json_data.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
            
        return base64.b64encode(json_data.encode()).decode()


async def main():
    gen = KaringConfigGenerator()
    await gen.init()
    
    test_servers = [
        {
            "protocol": "vless",
            "address": "example.com",
            "port": 443,
            "uuid": "test-uuid",
            "score": 95
        }
    ]
    
    sub = gen.generate_karing_subscription(test_servers)
    print(json.dumps(sub, indent=2))
    
    b64 = gen.export(sub)
    print(f"\nBase64 length: {len(b64)}")
    
    await gen.close()


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
