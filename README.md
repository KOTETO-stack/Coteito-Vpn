# Coteito-Vpn
# Auto VPN Subscription for Karing

Auto-updating VPN subscription with 150+ validated servers.

## Features
- Auto-discovery of new sources from GitHub
- Source validation and stale detection
- Auto-update every hour
- WARP+ data leak protection
- AmneziaFree backup
- SNI spoofing (domain fronting)
- DNS leak protection
- AdGuard ad blocking
- Xray fingerprint protection
- Russian apps direct routing

## Usage
Add subscription URL to Karing:
`https://raw.githubusercontent.com/YOUR_USERNAME/REPO_NAME/main/subscription.txt`

## Encryption Password
Default: `dGhpcyBpcyBhIHNlY3VyZSBrZXkgZm9yIGthcmluZw==`
Change in `update_subscription.py` ENCRYPTION_KEY variable.

## Setup
1. Fork this repo
2. Add `GITHUB_TOKEN` to repository secrets (for source discovery)
3. Enable GitHub Actions
4. Add subscription URL to Karing app

## Files
- `source_discoverer.py` - Auto-find new VPN sources
- `source_validator.py` - Check source health
- `source_manager.py` - Maintain source list
- `update_subscription_v2.py` - Main builder
- `warp_key_generator.py` - WARP+ key generation
- `geo_resolver.py` - IP geolocation
- `xray_protection.py` - Anti-detection
- `speed_test.py` - Latency testing
- `config_generator.py` - Karing config builder
