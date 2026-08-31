#!/usr/bin/env python3
import base64
import hashlib
import json
import os
import random
import string


class XrayProtection:
    def __init__(self):
        self.fingerprints = [
            "chrome", "firefox", "safari", "edge", "360",
            "qq", "random", "ios"
        ]
        self.tls_versions = ["1.2", "1.3"]
        
    def generate_random_padding(self, min_len=100, max_len=500):
        length = random.randint(min_len, max_len)
        chars = string.ascii_letters + string.digits
        return ''.join(random.choice(chars) for _ in range(length))
        
    def generate_ja3_fingerprint(self, browser="chrome"):
        ja3_configs = {
            "chrome": {
                "version": "TLSv1.3",
                "ciphers": [
                    "TLS_AES_128_GCM_SHA256",
                    "TLS_AES_256_GCM_SHA384",
                    "TLS_CHACHA20_POLY1305_SHA256",
                    "ECDHE-ECDSA-AES128-GCM-SHA256",
                    "ECDHE-RSA-AES128-GCM-SHA256"
                ],
                "extensions": [
                    "server_name", "extended_master_secret", "renegotiation_info",
                    "supported_groups", "ec_point_formats", "session_ticket",
                    "application_layer_protocol_negotiation", "status_request",
                    "signature_algorithms", "signed_certificate_timestamp",
                    "key_share", "supported_versions", "cookie", "psk_key_exchange_modes",
                    "certificate_authorities", "compress_certificate", "application_settings"
                ],
                "groups": ["X25519", "P-256", "P-384"],
                "points": ["0"]
            },
            "firefox": {
                "version": "TLSv1.3",
                "ciphers": [
                    "TLS_AES_128_GCM_SHA256",
                    "TLS_CHACHA20_POLY1305_SHA256",
                    "TLS_AES_256_GCM_SHA384",
                    "ECDHE-ECDSA-AES128-GCM-SHA256"
                ],
                "extensions": [
                    "server_name", "extended_master_secret", "renegotiation_info",
                    "supported_groups", "ec_point_formats", "application_layer_protocol_negotiation"
                ],
                "groups": ["X25519", "P-256", "P-384", "P-521"],
                "points": ["0", "1", "2"]
            },
            "safari": {
                "version": "TLSv1.3",
                "ciphers": [
                    "TLS_AES_128_GCM_SHA256",
                    "TLS_AES_256_GCM_SHA384",
                    "TLS_CHACHA20_POLY1305_SHA256"
                ],
                "extensions": [
                    "server_name", "extended_master_secret", "renegotiation_info",
                    "supported_groups", "ec_point_formats", "signature_algorithms"
                ],
                "groups": ["X25519", "P-256", "P-384"],
                "points": ["0"]
            }
        }
        return ja3_configs.get(browser, ja3_configs["chrome"])
        
    def generate_utls_config(self, browser="chrome"):
        ja3 = self.generate_ja3_fingerprint(browser)
        return {
            "fingerprint": browser,
            "tls_version": ja3["version"],
            "cipher_suites": ja3["ciphers"],
            "extensions": ja3["extensions"],
            "supported_groups": ja3["groups"],
            "ec_point_formats": ja3["points"],
            "padding": self.generate_random_padding(),
            "utls": {
                "enabled": True,
                "imitate": browser,
                "no_sni": False
            }
        }
        
    def generate_reality_config(self, dest="www.google.com:443"):
        private_key = base64.b64encode(os.urandom(32)).decode()
        public_key = base64.b64encode(os.urandom(32)).decode()
        
        return {
            "enabled": True,
            "dest": dest,
            "xver": 0,
            "server_names": [
                "www.google.com",
                "www.youtube.com",
                "www.facebook.com",
                "www.twitter.com"
            ],
            "private_key": private_key,
            "public_key": public_key,
            "short_id": hashlib.sha256(os.urandom(8)).hexdigest()[:8],
            "spider_x": "",
            "max_time_diff": 0
        }
        
    def generate_xray_inbound(self):
        return {
            "port": random.randint(10000, 65535),
            "protocol": "vless",
            "settings": {
                "clients": [{
                    "id": str(uuid.uuid4()),
                    "flow": "xtls-rprx-vision"
                }],
                "decryption": "none"
            },
            "streamSettings": {
                "network": "tcp",
                "security": "reality",
                "realitySettings": self.generate_reality_config(),
                "tcpSettings": {
                    "header": {
                        "type": "none"
                    }
                }
            },
            "sniffing": {
                "enabled": True,
                "destOverride": ["http", "tls", "quic"]
            }
        }
        
    def generate_xray_outbound(self, server_info):
        browser = random.choice(self.fingerprints)
        utls = self.generate_utls_config(browser)
        
        return {
            "protocol": server_info.get("protocol", "vless"),
            "settings": {
                "vnext": [{
                    "address": server_info.get("address"),
                    "port": int(server_info.get("port", 443)),
                    "users": [{
                        "id": server_info.get("uuid", str(uuid.uuid4())),
                        "encryption": server_info.get("encryption", "none"),
                        "flow": server_info.get("flow", "xtls-rprx-vision")
                    }]
                }]
            },
            "streamSettings": {
                "network": server_info.get("type", "tcp"),
                "security": server_info.get("security", "tls"),
                "tlsSettings": {
                    "serverName": server_info.get("sni", server_info.get("address")),
                    "fingerprint": browser,
                    "alpn": ["h2", "http/1.1"],
                    "allowInsecure": False,
                    "utls": utls["utls"]
                },
                "tcpSettings": {
                    "header": {
                        "type": "none"
                    }
                }
            },
            "mux": {
                "enabled": True,
                "concurrency": random.randint(4, 16),
                "xudpConcurrency": random.randint(4, 16),
                "xudpProxyUDP443": "reject"
            }
        }
        
    def apply_protection(self, config):
        protected = config.copy()
        
        if "servers" in protected:
            for srv in protected["servers"]:
                if "name" in srv:
                    srv["name"] += f" {self.generate_random_padding(5, 15)}"
                    srv["name"] = srv["name"].split()[0]
                    
        protected["xray_protection"] = {
            "enabled": True,
            "fingerprint": random.choice(self.fingerprints),
            "padding": self.generate_random_padding(),
            "reality": self.generate_reality_config(),
            "anti_detection": {
                "fragment": {
                    "packets": "tlshello",
                    "length": "100-200",
                    "interval": "10-20"
                },
                "noise": {
                    "enabled": True,
                    "packet": "rand",
                    "delay": "10-30"
                }
            }
        }
        
        return protected


def main():
    protector = XrayProtection()
    
    print("=== JA3 Chrome ===")
    print(json.dumps(protector.generate_ja3_fingerprint("chrome"), indent=2))
    
    print("\n=== uTLS Config ===")
    print(json.dumps(protector.generate_utls_config("chrome"), indent=2))
    
    print("\n=== REALITY Config ===")
    print(json.dumps(protector.generate_reality_config(), indent=2))


if __name__ == '__main__':
    import uuid
    main()
