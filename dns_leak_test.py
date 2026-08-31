#!/usr/bin/env python3
import asyncio
import socket


async def test_dns_leak():
    resolvers = [
        ("8.8.8.8", 53),
        ("1.1.1.1", 53),
        ("9.9.9.9", 53),
        ("208.67.222.222", 53)
    ]
    
    for ip, port in resolvers:
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port), timeout=5
            )
            writer.close()
            await writer.wait_closed()
            print(f"DNS {ip}:{port} OK")
        except Exception as e:
            print(f"DNS {ip}:{port} FAIL: {e}")


if __name__ == '__main__':
    asyncio.run(test_dns_leak())
