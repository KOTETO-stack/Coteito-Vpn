#!/usr/bin/env python3
import asyncio
import base64
import hashlib
import json
import os
import re
import time
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs

import aiohttp
import yaml

COUNTRY_FLAGS = {
    "US": "🇺🇸", "NL": "🇳🇱", "DE": "🇩🇪", "SG": "🇸🇬",
    "JP": "🇯🇵", "KR": "🇰🇷", "GB": "🇬🇧", "FR": "🇫🇷",
    "CA": "🇨🇦", "AU": "🇦🇺", "RU": "🇷🇺", "PL": "🇵🇱",
    "TR": "🇹🇷", "IN": "🇮🇳", "BR": "🇧🇷", "UA": "🇺🇦"
}

AMNEZIA_FREE = "vpn://AAAA_3icXY3LDoIwEEV_hXStJhhjojsjERN0AbowbkgtAzZA2_QBQcO_2xbduJrMPXfmvBHDLaBtgHYtgxfFwUECoFmAClBEUqEpZ_84IJwxIB7Zpt1KWuUdSDWVlzbEguYTsMEbKZAdJZDrQXgbnt7Ny6_tx4XkmhPe-E5fOWQss68M03Kws_D30qDRWYx-5gXW2Eucs4bB8Yg2qyTM-sUjO16u9SmKUxOt92VI6js_dzyNsz7cqOSGxvEDmaFXJg=="
SNI_SPOOF_HOST = "www.google.com"


class VPNValidator:
    def __init__(self):
        self.session = None
        
    async def init_session(self):
        connector = aiohttp.TCPConnector(limit=100, ssl=False)
        timeout = aiohttp.ClientTimeout(total=10)
        self.session = aiohttp.ClientSession(connector=connector, timeout=timeout)
        
    async def close(self):
        if self.session:
            await self.session.close()
            
    def decode_base64(self, data):
        try:
            return base64.b64decode(data + '=' * (-len(data) % 4)).decode('utf-8')
        except:
            return None
            
    def parse_vmess(self, url):
        try:
            if not url.startswith('vmess://'):
                return None
            b64 = url[8:]
            decoded = self.decode_base64(b64)
            if not decoded:
                return None
            return json.loads(decoded)
        except:
            return None
            
    def parse_vless(self, url):
        try:
            if not url.startswith('vless://'):
                return None
            parsed = urlparse(url)
            uuid = parsed.username
            host = parsed.hostname
            port = parsed.port or 443
            params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
            return {
                'protocol': 'vless',
                'uuid': uuid,
                'address': host,
                'port': port,
                'security': params.get('security', 'none'),
                'sni': params.get('sni', host),
                'flow': params.get('flow', ''),
                'type': params.get('type', 'tcp'),
                'path': params.get('path', '/'),
                'encryption': params.get('encryption', 'none')
            }
        except:
            return None
            
    def parse_trojan(self, url):
        try:
            if not url.startswith('trojan://'):
                return None
            parsed = urlparse(url)
            password = parsed.username
            host = parsed.hostname
            port = parsed.port or 443
            params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
            return {
                'protocol': 'trojan',
                'password': password,
                'address': host,
                'port': port,
                'sni': params.get('sni', host),
                'type': params.get('type', 'tcp'),
                'path': params.get('path', '/')
            }
        except:
            return None
            
    def parse_hysteria2(self, url):
        try:
            if not url.startswith('hysteria2://') and not url.startswith('hy2://'):
                return None
            parsed = urlparse(url)
            password = parsed.username
            host = parsed.hostname
            port = parsed.port or 443
            params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
            return {
                'protocol': 'hysteria2',
                'password': password,
                'address': host,
                'port': port,
                'sni': params.get('sni', host),
                'obfs': params.get('obfs', ''),
                'obfs-password': params.get('obfs-password', '')
            }
        except:
            return None
            
    def parse_ss(self, url):
        try:
            if not url.startswith('ss://'):
                return None
            parsed = urlparse(url)
            b64 = parsed.username
            decoded = self.decode_base64(b64)
            if not decoded:
                return None
            method, password = decoded.split(':', 1)
            host = parsed.hostname
            port = parsed.port
            return {
                'protocol': 'shadowsocks',
                'method': method,
                'password': password,
                'address': host,
                'port': port
            }
        except:
            return None
            
    def parse_any(self, url):
        for parser in [self.parse_vmess, self.parse_vless, self.parse_trojan, 
                       self.parse_hysteria2, self.parse_ss]:
            result = parser(url)
            if result:
                return result
        return None
        
    async def ping_server(self, host, port, timeout=3):
        try:
            proc = await asyncio.create_subprocess_exec(
                'ping', '-c', '1', '-W', str(timeout), host,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            await asyncio.wait_for(proc.wait(), timeout=timeout + 1)
            return proc.returncode == 0
        except:
            return False
            
    async def check_tcp_connectivity(self, host, port, timeout=5):
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=timeout
            )
            writer.close()
            await writer.wait_closed()
            return True
        except:
            return False
            
    async def validate_server(self, server_info):
        host = server_info.get('address')
        port = server_info.get('port')
        
        if not host or not port:
            return False
            
        blocked_prefixes = ['10.', '172.16.', '192.168.', '127.']
        if any(host.startswith(p) for p in blocked_prefixes):
            return False
            
        ping_ok = await self.ping_server(host, port)
        if not ping_ok:
            ping_ok = await self.check_tcp_connectivity(host, port)
            
        return ping_ok
        
    async def fetch_source(self, url):
        try:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    return text
        except Exception as e:
            print(f"Failed to fetch {url}: {e}")
        return None
        
    def extract_servers_from_text(self, text):
        servers = []
        patterns = [
            r'vmess://[A-Za-z0-9+/=]+',
            r'vless://[^@\s]+@[^:\s]+:\d+[^?\s]*(?:\?[^\s#]*)?(?:#[^\s]*)?',
            r'trojan://[^@\s]+@[^:\s]+:\d+[^?\s]*(?:\?[^\s#]*)?(?:#[^\s]*)?',
            r'hysteria2://[^@\s]+@[^:\s]+:\d+[^?\s]*(?:\?[^\s#]*)?(?:#[^\s]*)?',
            r'hy2://[^@\s]+@[^:\s]+:\d+[^?\s]*(?:\?[^\s#]*)?(?:#[^\s]*)?',
            r'ss://[A-Za-z0-9+/=]+@[^:\s]+:\d+'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                parsed = self.parse_any(match)
                if parsed:
                    servers.append(parsed)
                    
        return servers
        
    async def fetch_all_sources(self, source_urls):
        all_servers = []
        tasks = [self.fetch_source(url) for url in source_urls]
        results = await asyncio.gather(*tasks)
        
        for text in results:
            if text:
                servers = self.extract_servers_from_text(text)
                all_servers.extend(servers)
                
        seen = set()
        unique = []
        for s in all_servers:
            key = f"{s.get('address')}:{s.get('port')}"
            if key not in seen:
                seen.add(key)
                unique.append(s)
                
        return unique
        
    def get_country_info(self, ip_or_host):
        country_map = {
            'us': ('US', 'United States'),
            'nl': ('NL', 'Netherlands'),
            'de': ('DE', 'Germany'),
            'sg': ('SG', 'Singapore'),
            'jp': ('JP', 'Japan'),
            'kr': ('KR', 'South Korea'),
            'gb': ('GB', 'United Kingdom'),
            'fr': ('FR', 'France'),
            'ca': ('CA', 'Canada'),
            'au': ('AU', 'Australia'),
            'ru': ('RU', 'Russia'),
        }
        
        host_lower = str(ip_or_host).lower()
        for code, (cc, name) in country_map.items():
            if code in host_lower:
                return cc, name
        return 'US', 'United States'
        
    def build_server_name(self, server_info):
        cc, country = self.get_country_info(server_info.get('address', ''))
        flag = COUNTRY_FLAGS.get(cc, '🌍')
        city = self.guess_city(cc)
        return f"{flag} {country} {city}"
        
    def guess_city(self, country_code):
        cities = {
            'US': 'New York', 'NL': 'Amsterdam', 'DE': 'Frankfurt',
            'SG': 'Singapore', 'JP': 'Tokyo', 'KR': 'Seoul',
            'GB': 'London', 'FR': 'Paris', 'CA': 'Toronto', 'AU': 'Sydney'
        }
        return cities.get(country_code, 'Unknown')
        
    def build_karing_config(self, servers):
        configs = []
        
        for i, srv in enumerate(servers[:150]):
            name = self.build_server_name(srv)
            protocol = srv.get('protocol', 'unknown')
            
            config = {
                'name': name,
                'type': protocol,
                'server': srv.get('address'),
                'port': int(srv.get('port', 443)),
            }
            
            if protocol == 'vless':
                config.update({
                    'uuid': srv.get('uuid'),
                    'tls': srv.get('security') == 'tls',
                    'sni': srv.get('sni', srv.get('address')),
                    'flow': srv.get('flow', ''),
                    'network': srv.get('type', 'tcp'),
                    'path': srv.get('path', '/'),
                    'encryption': srv.get('encryption', 'none')
                })
            elif protocol == 'trojan':
                config.update({
                    'password': srv.get('password'),
                    'tls': True,
                    'sni': srv.get('sni', srv.get('address')),
                    'network': srv.get('type', 'tcp'),
                    'path': srv.get('path', '/')
                })
            elif protocol == 'hysteria2':
                config.update({
                    'password': srv.get('password'),
                    'sni': srv.get('sni', srv.get('address')),
                    'obfs': srv.get('obfs', ''),
                    'obfs-password': srv.get('obfs-password', '')
                })
            elif protocol == 'shadowsocks':
                config.update({
                    'cipher': srv.get('method'),
                    'password': srv.get('password')
                })
            elif protocol == 'vmess':
                config.update({
                    'uuid': srv.get('id'),
                    'alterId': srv.get('aid', 0),
                    'cipher': 'auto',
                    'tls': srv.get('tls', '') == 'tls',
                    'network': srv.get('net', 'tcp'),
                    'path': srv.get('path', '/'),
                    'host': srv.get('host', ''),
                    'sni': srv.get('sni', srv.get('host', ''))
                })
                
            config['sni'] = SNI_SPOOF_HOST
            config['host'] = SNI_SPOOF_HOST
            
            configs.append(config)
            
        return configs
        
    def build_warp_config(self):
        return {
            'name': '🇺🇸 WARP+ Secure',
            'type': 'wireguard',
            'server': 'engage.cloudflareclient.com',
            'port': 2408,
            'private-key': 'YOUR_WARP_PRIVATE_KEY',
            'public-key': 'bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo=',
            'dns': ['1.1.1.1', '1.0.0.1', '2606:4700:4700::1111'],
            'mtu': 1280,
            'reserved': [0, 0, 0],
            'udp': True
        }
        
    def build_amnezia_config(self):
        return {
            'name': '🔒 AmneziaFree Backup',
            'type': 'amnezia',
            'url': AMNEZIA_FREE,
            'auto-update': True
        }
        
    def build_routing_rules(self):
        return {
            'rules': [
                {
                    'domain': [
                        '*.yandex.ru', '*.yandex.net', '*.vk.com', '*.mail.ru',
                        '*.gosuslugi.ru', '*.sberbank.ru', '*.tinkoff.ru',
                        '*.avito.ru', '*.ozon.ru', '*.wildberries.ru'
                    ],
                    'outbound': 'DIRECT'
                },
                {
                    'domain': ['*.youtube.com', '*.googlevideo.com', '*.ytimg.com'],
                    'outbound': 'PROXY',
                    'adblock': True
                },
                {
                    'domain': ['*.telegram.org', '*.telegram.me', '*.t.me'],
                    'outbound': 'PROXY'
                },
                {
                    'domain': ['*.tiktok.com', '*.tiktokv.com', '*.musical.ly'],
                    'outbound': 'PROXY'
                },
                {
                    'domain': ['*.wechat.com', '*.weixin.qq.com'],
                    'outbound': 'PROXY'
                },
                {
                    'domain': ['*.whatsapp.com', '*.whatsapp.net'],
                    'outbound': 'PROXY'
                },
                {
                    'domain': ['*.bip.com'],
                    'outbound': 'PROXY'
                },
                {
                    'protocol': ['dns'],
                    'outbound': 'DNS'
                }
            ],
            'adblock': {
                'enabled': True,
                'rules': [
                    '||googleadservices.com^',
                    '||doubleclick.net^',
                    '||google-analytics.com^',
                    '||facebook.com/tr^',
                    '||googlesyndication.com^'
                ]
            },
            'dns': {
                'servers': ['https://dns.google/dns-query', 'https://cloudflare-dns.com/dns-query'],
                'fallback': ['8.8.8.8', '1.1.1.1'],
                'dns-leak-protection': True
            }
        }
        
    async def run(self, source_urls):
        await self.init_session()
        
        print("Fetching servers from sources...")
        servers = await self.fetch_all_sources(source_urls)
        print(f"Found {len(servers)} unique servers")
        
        print("Validating servers...")
        valid = []
        for srv in servers:
            if await self.validate_server(srv):
                valid.append(srv)
                if len(valid) >= 150:
                    break
                    
        print(f"Validated {len(valid)} servers")
        
        karing_servers = self.build_karing_config(valid)
        karing_servers.insert(0, self.build_warp_config())
        karing_servers.insert(1, self.build_amnezia_config())
        
        subscription = {
            'version': 2,
            'updated': datetime.utcnow().isoformat(),
            'encryption': {
                'enabled': True,
                'key': base64.b64encode(os.urandom(32)).decode()
            },
            'servers': karing_servers,
            'routing': self.build_routing_rules(),
            'dns-leak-test': ['https://dns.google/resolve?name=example.com'],
            'warp-protection': {
                'enabled': True,
                'mode': 'always-on',
                'fallback-dns': ['1.1.1.1', '1.0.0.1']
            },
            'xray-protection': {
                'enabled': True,
                'fingerprint': 'chrome',
                'padding': True
            },
            'auto-update': {
                'interval': 3600,
                'url': 'https://raw.githubusercontent.com/YOUR_USERNAME/REPO_NAME/main/subscription.txt'
            }
        }
        
        output = base64.b64encode(json.dumps(subscription, indent=2).encode()).decode()
        
        with open('subscription.json', 'w') as f:
            json.dump(subscription, f, indent=2)
            
        with open('subscription.txt', 'w') as f:
            f.write(output)
            
        print("Subscription generated")
        
        await self.close()
        
        return output


async def main():
    validator = VPNValidator()
    # Use fallback sources
    await validator.run(FALLBACK_SOURCES)


if __name__ == '__main__':
    asyncio.run(main())
