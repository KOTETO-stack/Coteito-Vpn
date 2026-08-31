#!/usr/bin/env python3
import base64
import json
import os
import re
import struct
import time
import uuid

import aiohttp


WARP_API = "https://api.cloudflareclient.com/v0a2158"
WARP_HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "okhttp/3.12.1",
    "CF-Client-Version": "a-6.21-2158",
    "Accept-Encoding": "gzip"
}


class WARPKeyGenerator:
    def __init__(self):
        self.device_id = str(uuid.uuid4()).replace("-", "")
        self.access_token = None
        self.private_key = None
        self.public_key = None
        
    def generate_wireguard_keys(self):
        import subprocess
        priv = subprocess.run(
            ["wg", "genkey"], capture_output=True, text=True
        ).stdout.strip()
        pub = subprocess.run(
            ["wg", "pubkey"], input=priv, capture_output=True, text=True
        ).stdout.strip()
        self.private_key = priv
        self.public_key = pub
        return priv, pub
        
    def generate_keys_fallback(self):
        import nacl.public
        import nacl.utils
        priv_key = nacl.public.PrivateKey.generate()
        pub_key = priv_key.public_key
        self.private_key = base64.b64encode(priv_key.encode()).decode()
        self.public_key = base64.b64encode(pub_key.encode()).decode()
        return self.private_key, self.public_key
        
    async def register_device(self):
        if not self.private_key:
            try:
                self.generate_wireguard_keys()
            except:
                self.generate_keys_fallback()
                
        async with aiohttp.ClientSession(headers=WARP_HEADERS) as session:
            data = {
                "install_id": "",
                "tos": datetime.utcnow().isoformat() + "Z",
                "key": self.public_key,
                "fcm_token": "",
                "type": "Android",
                "locale": "en_US",
                "model": "PC",
                "warp_enabled": True
            }
            
            async with session.post(
                f"{WARP_API}/reg", json=data
            ) as resp:
                result = await resp.json()
                self.access_token = result.get("token")
                return result
                
    async def add_referral(self, referrer_id):
        if not self.access_token:
            await self.register_device()
            
        headers = {**WARP_HEADERS, "Authorization": f"Bearer {self.access_token}"}
        
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(
                f"{WARP_API}/reg/{referrer_id}"
            ) as resp:
                return await resp.json()
                
    async def get_account(self):
        if not self.access_token:
            await self.register_device()
            
        headers = {**WARP_HEADERS, "Authorization": f"Bearer {self.access_token}"}
        
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(
                f"{WARP_API}/reg/{self.device_id}"
            ) as resp:
                return await resp.json()
                
    async def generate_warp_plus_keys(self, count=5):
        keys = []
        for _ in range(count):
            await self.register_device()
            account = await self.get_account()
            
            warp_config = {
                "private_key": self.private_key,
                "public_key": self.public_key,
                "device_id": self.device_id,
                "token": self.access_token,
                "warp_enabled": True,
                "account_type": "free",
                "referral_count": account.get("account", {}).get("referral_count", 0),
                "warp_plus": account.get("account", {}).get("warp_plus", False)
            }
            keys.append(warp_config)
            
            self.device_id = str(uuid.uuid4()).replace("-", "")
            self.access_token = None
            self.private_key = None
            
        return keys
        
    def build_wireguard_config(self, warp_data):
        return f"""[Interface]
PrivateKey = {warp_data['private_key']}
Address = 172.16.0.2/32, 2606:4700:110:8f81:d551:a0:532e:b2ba/128
DNS = 1.1.1.1, 1.0.0.1, 2606:4700:4700::1111, 2606:4700:4700::1001
MTU = 1280

[Peer]
PublicKey = bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo=
AllowedIPs = 0.0.0.0/0, ::/0
Endpoint = engage.cloudflareclient.com:2408
PersistentKeepalive = 25
"""


async def main():
    generator = WARPKeyGenerator()
    keys = await generator.generate_warp_plus_keys(count=3)
    
    for i, key in enumerate(keys):
        print(f"=== WARP+ Key {i+1} ===")
        print(json.dumps(key, indent=2))
        print("\nWireGuard Config:")
        print(generator.build_wireguard_config(key))
        print("-" * 50)


if __name__ == '__main__':
    import asyncio
    from datetime import datetime
    asyncio.run(main())
