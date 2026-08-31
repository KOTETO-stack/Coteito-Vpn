#!/usr/bin/env python3
import asyncio
import json
import re
from datetime import datetime, timedelta

import aiohttp


class SourceValidator:
    def __init__(self):
        self.session = None
        self.results = []
        
    async def init(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=15)
        )
        
    async def close(self):
        if self.session:
            await self.session.close()
            
    async def check_url(self, url):
        start = datetime.utcnow()
        try:
            async with self.session.get(url) as resp:
                latency = (datetime.utcnow() - start).total_seconds() * 1000
                if resp.status == 200:
                    text = await resp.text()
                    size = len(text)
                    has_nodes = self.extract_nodes(text)
                    
                    return {
                        "url": url,
                        "status": "alive",
                        "http_code": resp.status,
                        "latency_ms": round(latency, 2),
                        "size": size,
                        "nodes_found": len(has_nodes),
                        "protocols": self.detect_protocols(text),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    return {
                        "url": url,
                        "status": "dead",
                        "http_code": resp.status,
                        "latency_ms": round(latency, 2),
                        "error": f"HTTP {resp.status}",
                        "timestamp": datetime.utcnow().isoformat()
                    }
        except asyncio.TimeoutError:
            return {
                "url": url,
                "status": "dead",
                "error": "timeout",
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "url": url,
                "status": "dead",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
            
    def extract_nodes(self, text):
        patterns = [
            r"vless://[a-f0-9-]+@[^:\s]+:\d+",
            r"trojan://[^@\s]+@[^:\s]+:\d+",
            r"hy(?:steria)?2://[^@\s]+@[^:\s]+:\d+",
            r"vmess://[A-Za-z0-9+/=]+",
            r"ss://[A-Za-z0-9+/=]+@[^:\s]+:\d+"
        ]
        nodes = []
        for p in patterns:
            nodes.extend(re.findall(p, text))
        return nodes
        
    def detect_protocols(self, text):
        protocols = {}
        sigs = {
            "vless": r"vless://",
            "trojan": r"trojan://",
            "hysteria2": r"hy(?:steria)?2://",
            "vmess": r"vmess://",
            "shadowsocks": r"ss://"
        }
        for name, pattern in sigs.items():
            if re.search(pattern, text):
                protocols[name] = len(re.findall(pattern, text))
        return protocols
        
    async def validate_batch(self, sources, max_concurrent=30):
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def check_with_limit(src):
            async with semaphore:
                return await self.check_url(src["url"])
                
        tasks = [check_with_limit(s) for s in sources]
        results = await asyncio.gather(*tasks)
        return results
        
    def filter_alive(self, results, min_nodes=5):
        alive = []
        for r in results:
            if r["status"] == "alive" and r.get("nodes_found", 0) >= min_nodes:
                alive.append(r)
        return alive
        
    def detect_stale(self, results, history_file="source_history.json"):
        try:
            with open(history_file) as f:
                history = json.load(f)
        except:
            history = {}
            
        stale = []
        for r in results:
            url = r["url"]
            if url in history:
                old = history[url]
                old_time = datetime.fromisoformat(old["timestamp"])
                new_time = datetime.fromisoformat(r["timestamp"])
                if (new_time - old_time) > timedelta(hours=24):
                    if old.get("size") == r.get("size"):
                        r["stale_warning"] = True
                        stale.append(r)
                        
        for r in results:
            history[r["url"]] = {
                "size": r.get("size", 0),
                "timestamp": r["timestamp"]
            }
            
        with open(history_file, "w") as f:
            json.dump(history, f, indent=2)
            
        return stale
        
    async def full_validation(self, sources):
        print(f"Validating {len(sources)} sources...")
        results = await self.validate_batch(sources)
        
        alive = self.filter_alive(results)
        stale = self.detect_stale(results)
        
        for a in alive:
            for s in stale:
                if a["url"] == s["url"]:
                    a["stale_warning"] = True
                    
        dead = [r for r in results if r["status"] == "dead"]
        
        return {
            "alive": alive,
            "dead": dead,
            "stale": stale,
            "total": len(results),
            "alive_count": len(alive),
            "dead_count": len(dead),
            "stale_count": len(stale),
            "timestamp": datetime.utcnow().isoformat()
        }


async def main():
    try:
        with open("discovered_sources.json") as f:
            sources = json.load(f)
    except:
        print("No discovered_sources.json found")
        return
        
    validator = SourceValidator()
    await validator.init()
    
    report = await validator.full_validation(sources)
    
    with open("validation_report.json", "w") as f:
        json.dump(report, f, indent=2)
        
    print(f"\nAlive: {report['alive_count']}")
    print(f"Dead: {report['dead_count']}")
    print(f"Stale: {report['stale_count']}")
    
    clean = [{
        "name": s.get("name", ""),
        "url": s["url"],
        "protocols": s.get("protocols", {}),
        "node_count": s.get("nodes_found", 0),
        "latency_ms": s.get("latency_ms", 0)
    } for s in report["alive"] if not s.get("stale_warning")]
    
    with open("live_sources.json", "w") as f:
        json.dump(clean, f, indent=2)
        
    print(f"\nClean sources saved: {len(clean)}")
    
    await validator.close()


if __name__ == '__main__':
    asyncio.run(main())
