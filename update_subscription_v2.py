#!/usr/bin/env python3
import asyncio
import base64
import json
import os
import re
import time
from datetime import datetime

import aiohttp

from config_generator import KaringConfigGenerator
from geo_resolver import GeoResolver
from speed_test import SpeedTester
from warp_key_generator import WARPKeyGenerator
from xray_protection import XrayProtection


# Fallback sources for first run (no discovery needed)
FALLBACK_SOURCES = [
    "https://raw.githubusercontent.com/Au1rxx/free-vpn-subscriptions/main/output/v2ray-base64.txt",
    "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/All_Configs_Sub.txt",
    "https://raw.githubusercontent.com/gfpcom/free-proxy-list/main/list/vless.txt",
    "https://raw.githubusercontent.com/gfpcom/free-proxy-list/main/list/trojan.txt",
    "https://raw.githubusercontent.com/gfpcom/free-proxy-list/main/list/hysteria2.txt",
    "https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/All_Configs_Sub.txt",
    "https://raw.githubusercontent.com/aiboboxx/v2rayfree/main/v2",
    "https://raw.githubusercontent.com/wrfree/free/main/v2",
    "https://raw.githubusercontent.com/ermaozi/get_subscribe/main/subscribe/v2ray.txt",
    "https://raw.githubusercontent.com/mfuu/v2ray/master/v2ray",
    "https://raw.githubusercontent.com/peasoft/NoMoreWalls/master/list.txt",
    "https://raw.githubusercontent.com/Leon406/SubCrawler/main/sub/share/all3",
    "https://raw.githubusercontent.com/mahdibland/ShadowsocksAggregator/master/sub/sub_merge.txt",
    "https://raw.githubusercontent.com/tbbatbb/Proxy/master/dist/v2ray.config.txt",
    "https://raw.githubusercontent.com/anaer/Sub/main/clash.yaml",
    "https://raw.githubusercontent.com/adiwzx/freenode/main/adispeed.txt",
    "https://raw.githubusercontent.com/learnhard-cn/free_proxy_ss/main/v2ray/v2raysub",
    "https://raw.githubusercontent.com/Surfboardv2ray/TGParse/main/splitted/mixed",
    "https://raw.githubusercontent.com/Surfboardv2ray/TGParse/main/splitted/vless",
    "https://raw.githubusercontent.com/Surfboardv2ray/TGParse/main/splitted/trojan",
    "https://raw.githubusercontent.com/v2cross/Free-subscribe/main/subscribe/v2ray.txt",
    "https://raw.githubusercontent.com/v2cross/Free-subscribe/main/subscribe/clash.yaml",
    "https://raw.githubusercontent.com/itsyebekhe/HiN-VPN/main/subscription/normal/mix",
    "https://raw.githubusercontent.com/itsyebekhe/HiN-VPN/main/subscription/base64/mix",
    "https://raw.githubusercontent.com/LonUp/NodeList/main/V2RAY/Latest.txt",
    "https://raw.githubusercontent.com/chenjw512/FreeNode/master/sub/merged.txt",
    "https://raw.githubusercontent.com/free18/v2ray/main/merge/merge.txt",
    "https://raw.githubusercontent.com/w1770946466/Auto_proxy/main/Long_term_subscription1",
    "https://raw.githubusercontent.com/w1770946466/Auto_proxy/main/Long_term_subscription2",
    "https://raw.githubusercontent.com/w1770946466/Auto_proxy/main/Long_term_subscription3",
    "https://raw.githubusercontent.com/w1770946466/Auto_proxy/main/Long_term_subscription4",
    "https://raw.githubusercontent.com/w1770946466/Auto_proxy/main/Long_term_subscription5",
    "https://raw.githubusercontent.com/w1770946466/Auto_proxy/main/Long_term_subscription6",
    "https://raw.githubusercontent.com/w1770946466/Auto_proxy/main/Long_term_subscription7",
    "https://raw.githubusercontent.com/w1770946466/Auto_proxy/main/Long_term_subscription8",
    "https://raw.githubusercontent.com/w1770946466/Auto_proxy/main/Long_term_subscription9",
    "https://raw.githubusercontent.com/w1770946466/Auto_proxy/main/Long_term_subscription10",
    "https://raw.githubusercontent.com/w1770946466/Auto_proxy/main/Long_term_subscription_num",
    "https://raw.githubusercontent.com/aiboboxx/clashfree/main/clash.yml",
    "https://raw.githubusercontent.com/Pawdroid/Free-servers/main/sub",
    "https://raw.githubusercontent.com/Flik6/get-v2ray/main/jekyll/_includes/subscribe.txt",
    "https://raw.githubusercontent.com/Jsnzkpg/Jsnzkpg/Jsnzkpg/Jsnzkpg",
    "https://raw.githubusercontent.com/zyfxz/V2Ray-subscribe/main/README.md",
    "https://raw.githubusercontent.com/hugetiny/awesome-vpn/master/vpn/China/README.md",
    "https://raw.githubusercontent.com/hugetiny/awesome-vpn/master/vpn/Global/README.md",
    "https://raw.githubusercontent.com/snakem982/proxypool/main/source/subscribe/clash",
    "https://raw.githubusercontent.com/snakem982/proxypool/main/source/subscribe/v2ray",
    "https://raw.githubusercontent.com/snakem982/proxypool/main/source/subscribe/singbox",
    "https://raw.githubusercontent.com/snakem982/proxypool/main/source/subscribe/hysteria2",
    "https://raw.githubusercontent.com/snakem982/proxypool/main/source/subscribe/trojan",
    "https://raw.githubusercontent.com/ermaozi01/free_clash_vpn/main/subscribe/v2ray.txt",
    "https://raw.githubusercontent.com/ermaozi01/free_clash_vpn/main/subscribe/clash.yml",
    "https://raw.githubusercontent.com/ermaozi01/free_clash_vpn/main/subscribe/singbox.json",
    "https://raw.githubusercontent.com/ermaozi01/free_clash_vpn/main/subscribe/hysteria2.txt",
    "https://raw.githubusercontent.com/ermaozi01/free_clash_vpn/main/subscribe/trojan.txt",
    "https://raw.githubusercontent.com/mianfeifq/share/main/data/2026_01_01/2.txt",
    "https://raw.githubusercontent.com/mianfeifq/share/main/data/2026_01_01/3.txt",
    "https://raw.githubusercontent.com/mianfeifq/share/main/data/2026_01_01/4.txt",
    "https://raw.githubusercontent.com/mianfeifq/share/main/data/2026_01_01/5.txt",
    "https://raw.githubusercontent.com/mianfeifq/share/main/data/2026_01_01/6.txt",
    "https://raw.githubusercontent.com/mianfeifq/share/main/data/2026_01_01/7.txt",
    "https://raw.githubusercontent.com/mianfeifq/share/main/data/2026_01_01/8.txt",
    "https://raw.githubusercontent.com/mianfeifq/share/main/data/2026_01_01/9.txt",
    "https://raw.githubusercontent.com/mianfeifq/share/main/data/2026_01_01/10.txt",
    "https://raw.githubusercontent.com/freefq/free/master/v2",
    "https://raw.githubusercontent.com/ripaojiedian/freenode/main/sub",
    "https://raw.githubusercontent.com/ripaojiedian/freenode/main/clash",
    "https://raw.githubusercontent.com/adiwzx/freenode/main/adispeed.txt",
    "https://raw.githubusercontent.com/mianfeifq/share/main/data/2026_01_01/1.txt",
    "https://raw.githubusercontent.com/zyfxz/V2Ray-subscribe/main/README.md",
    "https://raw.githubusercontent.com/Jsnzkpg/Jsnzkpg/Jsnzkpg/Jsnzkpg",
    "https://raw.githubusercontent.com/free18/v2ray/main/merge/merge.txt",
    "https://raw.githubusercontent.com/chenjw512/FreeNode/master/sub/merged.txt",
    "https://raw.githubusercontent.com/LonUp/NodeList/main/V2RAY/Latest.txt",
    "https://raw.githubusercontent.com/itsyebekhe/HiN-VPN/main/subscription/normal/mix",
    "https://raw.githubusercontent.com/itsyebekhe/HiN-VPN/main/subscription/base64/mix",
    "https://raw.githubusercontent.com/v2cross/Free-subscribe/main/subscribe/v2ray.txt",
    "https://raw.githubusercontent.com/Surfboardv2ray/TGParse/main/splitted/mixed",
    "https://raw.githubusercontent.com/Surfboardv2ray/TGParse/main/splitted/vless",
    "https://raw.githubusercontent.com/Surfboardv2ray/TGParse/main/splitted/trojan",
    "https://raw.githubusercontent.com/learnhard-cn/free_proxy_ss/main/v2ray/v2raysub",
    "https://raw.githubusercontent.com/mahdibland/ShadowsocksAggregator/master/sub/sub_merge.txt",
    "https://raw.githubusercontent.com/Leon406/SubCrawler/main/sub/share/all3",
    "https://raw.githubusercontent.com/peasoft/NoMoreWalls/master/list.txt",
    "https://raw.githubusercontent.com/mfuu/v2ray/master/v2ray",
    "https://raw.githubusercontent.com/adiwzx/freenode/main/adispeed.txt",
    "https://raw.githubusercontent.com/anaer/Sub/main/clash.yaml",
    "https://raw.githubusercontent.com/tbbatbb/Proxy/master/dist/v2ray.config.txt",
    "https://raw.githubusercontent.com/wrfree/free/main/v2",
    "https://raw.githubusercontent.com/aiboboxx/v2rayfree/main/v2",
    "https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/All_Configs_Sub.txt",
    "https://raw.githubusercontent.com/gfpcom/free-proxy-list/main/list/vless.txt",
    "https://raw.githubusercontent.com/gfpcom/free-proxy-list/main/list/trojan.txt",
    "https://raw.githubusercontent.com/gfpcom/free-proxy-list/main/list/hysteria2.txt",
    "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/All_Configs_Sub.txt",
    "https://raw.githubusercontent.com/Au1rxx/free-vpn-subscriptions/main/output/v2ray-base64.txt",
    "https://raw.githubusercontent.com/Au1rxx/free-vpn-subscriptions/main/output/clash.yaml",
    "https://raw.githubusercontent.com/Au1rxx/free-vpn-subscriptions/main/output/singbox.json",
    "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/Split/By%20Protocol/Vless.txt",
    "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/Split/By%20Protocol/Trojan.txt",
    "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/Split/By%20Protocol/Hysteria2.txt",
    "https://raw.githubusercontent.com/gfpcom/free-proxy-list/main/list/vmess.txt",
    "https://raw.githubusercontent.com/gfpcom/free-proxy-list/main/list/shadowsocks.txt",
    "https://raw.githubusercontent.com/ermaozi01/free_clash_vpn/main/subscribe/v2ray.txt",
    "https://raw.githubusercontent.com/ermaozi01/free_clash_vpn/main/subscribe/clash.yml",
    "https://raw.githubusercontent.com/ermaozi01/free_clash_vpn/main/subscribe/singbox.json",
    "https://raw.githubusercontent.com/ermaozi01/free_clash_vpn/main/subscribe/hysteria2.txt",
    "https://raw.githubusercontent.com/ermaozi01/free_clash_vpn/main/subscribe/trojan.txt",
    "https://raw.githubusercontent.com/snakem982/proxypool/main/source/subscribe/clash",
    "https://raw.githubusercontent.com/snakem982/proxypool/main/source/subscribe/v2ray",
    "https://raw.githubusercontent.com/snakem982/proxypool/main/source/subscribe/singbox",
    "https://raw.githubusercontent.com/snakem982/proxypool/main/source/subscribe/hysteria2",
    "https://raw.githubusercontent.com/snakem982/proxypool/main/source/subscribe/trojan",
    "https://raw.githubusercontent.com/freefq/free/master/v2",
    "https://raw.githubusercontent.com/ripaojiedian/freenode/main/sub",
    "https://raw.githubusercontent.com/ripaojiedian/freenode/main/clash",
    "https://raw.githubusercontent.com/Pawdroid/Free-servers/main/sub",
    "https://raw.githubusercontent.com/Flik6/get-v2ray/main/jekyll/_includes/subscribe.txt",
    "https://raw.githubusercontent.com/Jsnzkpg/Jsnzkpg/Jsnzkpg/Jsnzkpg",
    "https://raw.githubusercontent.com/zyfxz/V2Ray-subscribe/main/README.md",
    "https://raw.githubusercontent.com/hugetiny/awesome-vpn/master/vpn/China/README.md",
    "https://raw.githubusercontent.com/hugetiny/awesome-vpn/master/vpn/Global/README.md",
    "https://raw.githubusercontent.com/mianfeifq/share/main/data/2026_01_01/1.txt",
    "https://raw.githubusercontent.com/mianfeifq/share/main/data/2026_01_01/2.txt",
    "https://raw.githubusercontent.com/mianfeifq/share/main/data/2026_01_01/3.txt",
    "https://raw.githubusercontent.com/mianfeifq/share/main/data/2026_01_01/4.txt",
    "https://raw.githubusercontent.com/mianfeifq/share/main/data/2026_01_01/5.txt",
    "https://raw.githubusercontent.com/w1770946466/Auto_proxy/main/Long_term_subscription1",
    "https://raw.githubusercontent.com/w1770946466/Auto_proxy/main/Long_term_subscription2",
    "https://raw.githubusercontent.com/w1770946466/Auto_proxy/main/Long_term_subscription3",
    "https://raw.githubusercontent.com/w1770946466/Auto_proxy/main/Long_term_subscription4",
    "https://raw.githubusercontent.com/w1770946466/Auto_proxy/main/Long_term_subscription5",
    "https://raw.githubusercontent.com/chenjw512/FreeNode/master/sub/merged.txt",
    "https://raw.githubusercontent.com/free18/v2ray/main/merge/merge.txt",
    "https://raw.githubusercontent.com/LonUp/NodeList/main/V2RAY/Latest.txt",
    "https://raw.githubusercontent.com/itsyebekhe/HiN-VPN/main/subscription/normal/mix",
    "https://raw.githubusercontent.com/itsyebekhe/HiN-VPN/main/subscription/base64/mix",
    "https://raw.githubusercontent.com/v2cross/Free-subscribe/main/subscribe/v2ray.txt",
    "https://raw.githubusercontent.com/v2cross/Free-subscribe/main/subscribe/clash.yaml",
]


class AutoSubscriptionBuilder:
    def __init__(self):
        self.source_urls = []
        
    def get_source_urls(self):
        try:
            from source_manager import SourceManager
            manager = SourceManager()
            urls = manager.get_source_urls()
            if len(urls) >= 50:
                return urls
        except:
            pass
        return FALLBACK_SOURCES
        
    async def fetch_from_source(self, url):
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=15)
            ) as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        return await resp.text()
        except Exception as e:
            print(f"  Fetch failed: {url[:60]}... - {e}")
        return None
        
    def extract_all_nodes(self, text):
        nodes = []
        patterns = [
            (r"vless://[a-f0-9-]+@[^:\s]+:\d+[^?\s]*(?:\?[^\s#]*)?(?:#[^\s]*)?", "vless"),
            (r"trojan://[^@\s]+@[^:\s]+:\d+[^?\s]*(?:\?[^\s#]*)?(?:#[^\s]*)?", "trojan"),
            (r"hy(?:steria)?2://[^@\s]+@[^:\s]+:\d+[^?\s]*(?:\?[^\s#]*)?(?:#[^\s]*)?", "hysteria2"),
            (r"vmess://[A-Za-z0-9+/=]+", "vmess"),
            (r"ss://[A-Za-z0-9+/=]+@[^:\s]+:\d+", "shadowsocks")
        ]
        for pattern, proto in patterns:
            matches = re.findall(pattern, text)
            for m in matches:
                nodes.append({"raw": m, "protocol": proto})
        return nodes
        
    async def fetch_all_nodes(self, source_urls):
        all_nodes = []
        for i, url in enumerate(source_urls):
            print(f"  [{i+1}/{len(source_urls)}] Fetching {url[:60]}...")
            text = await self.fetch_from_source(url)
            if text:
                nodes = self.extract_all_nodes(text)
                if nodes:
                    print(f"    -> {len(nodes)} nodes found")
                    all_nodes.extend(nodes)
                else:
                    print(f"    -> No nodes")
            else:
                print(f"    -> Failed")
                
        seen = set()
        unique = []
        for n in all_nodes:
            key = n["raw"][:100]
            if key not in seen:
                seen.add(key)
                unique.append(n)
                
        return unique
        
    async def build(self):
        print("=== Auto Subscription Builder ===")
        
        print("\n[1/7] Loading sources...")
        self.source_urls = self.get_source_urls()
        print(f"Using {len(self.source_urls)} sources")
        
        print("\n[2/7] Fetching nodes...")
        nodes = await self.fetch_all_nodes(self.source_urls)
        print(f"Found {len(nodes)} unique nodes")
        
        if len(nodes) < 10:
            print("ERROR: Too few nodes found. Aborting.")
            return None
            
        print("\n[3/7] Parsing nodes...")
        from update_subscription import VPNValidator
        validator = VPNValidator()
        await validator.init_session()
        
        parsed = []
        for n in nodes:
            p = validator.parse_any(n["raw"])
            if p:
                p["raw_url"] = n["raw"]
                parsed.append(p)
                
        print(f"Parsed {len(parsed)} valid nodes")
        
        print("\n[4/7] Speed testing...")
        tester = SpeedTester()
        ranked = await tester.rank_servers(parsed, max_concurrent=50)
        
        for p in parsed:
            for r in ranked:
                if p.get("address") == r["host"]:
                    p["score"] = r["score"]
                    p["latency"] = r["latency_ms"]
                    
        parsed.sort(key=lambda x: x.get("score", 0), reverse=True)
        print(f"Ranked {len(ranked)} servers")
        
        print("\n[5/7] Generating WARP+ keys...")
        warp_gen = WARPKeyGenerator()
        try:
            warp_keys = await warp_gen.generate_warp_plus_keys(count=3)
            print(f"Generated {len(warp_keys)} WARP+ keys")
        except Exception as e:
            print(f"WARP+ generation failed: {e}")
            warp_keys = []
        
        print("\n[6/7] Building Karing config...")
        gen = KaringConfigGenerator()
        await gen.init()
        
        subscription = gen.generate_karing_subscription(parsed[:150], warp_keys)
        subscription = gen.protector.apply_protection(subscription)
        
        print("\n[7/7] Exporting...")
        b64 = gen.export(subscription)
        
        with open("subscription.txt", "w") as f:
            f.write(b64)
        with open("subscription.json", "w") as f:
            json.dump(subscription, f, indent=2)
            
        with open("sources.json", "w") as f:
            json.dump([{"url": u, "active": True} for u in self.source_urls], f, indent=2)
            
        await validator.close()
        await gen.close()
        
        print(f"\nDone! Subscription: {len(b64)} bytes")
        print(f"Servers: {len(subscription['servers'])}")
        return b64


async def main():
    builder = AutoSubscriptionBuilder()
    result = await builder.build()
    if result:
        print("\nSUCCESS: subscription.txt created")
    else:
        print("\nFAILED: Check logs above")
        exit(1)


if __name__ == '__main__':
    asyncio.run(main())
