#!/usr/bin/env python3
import asyncio
import json
import time

import aiohttp


class SpeedTester:
    def __init__(self):
        self.results = []
        
    async def test_latency(self, host, port, timeout=5):
        start = time.time()
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=timeout
            )
            writer.close()
            await writer.wait_closed()
            latency = (time.time() - start) * 1000
            return round(latency, 2)
        except:
            return None
            
    async def test_server(self, server_info):
        host = server_info.get("address")
        port = server_info.get("port", 443)
        
        latency = await self.test_latency(host, port)
        if latency is None:
            return None
            
        return {
            "host": host,
            "port": port,
            "latency_ms": latency,
            "score": self.calculate_score(latency)
        }
        
    def calculate_score(self, latency):
        if latency < 50:
            return 100
        elif latency < 100:
            return 90
        elif latency < 200:
            return 75
        elif latency < 500:
            return 50
        else:
            return 25
            
    async def rank_servers(self, servers, max_concurrent=50):
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def test_with_limit(srv):
            async with semaphore:
                return await self.test_server(srv)
                
        tasks = [test_with_limit(s) for s in servers]
        results = await asyncio.gather(*tasks)
        
        valid = [r for r in results if r is not None]
        valid.sort(key=lambda x: x["latency_ms"])
        
        return valid
        
    def get_fastest(self, ranked, count=10):
        return ranked[:count]


async def main():
    tester = SpeedTester()
    
    test_servers = [
        {"address": "1.1.1.1", "port": 443},
        {"address": "8.8.8.8", "port": 443},
        {"address": "google.com", "port": 443}
    ]
    
    ranked = await tester.rank_servers(test_servers)
    print(json.dumps(ranked, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
