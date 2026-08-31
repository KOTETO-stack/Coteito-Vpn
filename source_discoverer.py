#!/usr/bin/env python3
import asyncio
import json
import re
from datetime import datetime, timedelta

import aiohttp


DISCOVERY_SEEDS = [
    "https://github.com/search?q=free+vless+subscription&type=repositories&s=updated&o=desc",
    "https://github.com/search?q=free+trojan+nodes&type=repositories&s=updated&o=desc",
    "https://github.com/search?q=v2ray+config+daily&type=repositories&s=updated&o=desc",
    "https://github.com/search?q=proxy+list+auto-update&type=repositories&s=updated&o=desc",
    "https://github.com/search?q=hysteria2+free+nodes&type=repositories&s=updated&o=desc",
]

GITHUB_API = "https://api.github.com"
RAW_GITHUB = "https://raw.githubusercontent.com"

FILE_PATTERNS = [
    r"sub.*\.txt", r"sub.*\.yaml", r"sub.*\.yml", r"sub.*\.json",
    r"all.*\.txt", r"all.*\.yaml", r"all.*\.json",
    r"vless.*\.txt", r"vless.*\.yaml", r"vless.*\.json",
    r"trojan.*\.txt", r"trojan.*\.yaml", r"trojan.*\.json",
    r"hy2.*\.txt", r"hysteria2.*\.txt", r"hysteria.*\.yaml",
    r"vmess.*\.txt", r"vmess.*\.json", r"ss.*\.txt",
    r"free.*\.txt", r"free.*\.yaml", r"proxy.*\.txt",
    r"nodes.*\.txt", r"nodes.*\.yaml", r"config.*\.txt",
    r"subscribe.*\.txt", r"subscribe.*\.yaml", r"subscription.*\.txt",
    r"output.*\.txt", r"output.*\.yaml", r"output.*\.json",
    r"list.*\.txt", r"list.*\.yaml", r"list.*\.json",
    r"mixed.*\.txt", r"splitted.*\.txt", r"split.*\.txt",
    r"base64.*\.txt", r"base64.*\.yaml",
    r"clash.*\.yaml", r"clash.*\.yml", r"singbox.*\.json",
    r"v2ray.*\.txt", r"v2ray.*\.yaml", r"v2ray.*\.json",
]

PROTOCOL_SIGNATURES = {
    "vless": r"vless://[a-f0-9-]+@[^:\s]+:\d+",
    "trojan": r"trojan://[^@\s]+@[^:\s]+:\d+",
    "hysteria2": r"hy(?:steria)?2://[^@\s]+@[^:\s]+:\d+",
    "vmess": r"vmess://[A-Za-z0-9+/=]+",
    "shadowsocks": r"ss://[A-Za-z0-9+/=]+@[^:\s]+:\d+",
    "wireguard": r"wireguard://|\[Interface\]|PrivateKey\s*=",
    "tuic": r"tuic://[a-f0-9-]+@[^:\s]+:\d+",
}


class SourceDiscoverer:
    def __init__(self, github_token=None):
        self.session = None
        self.github_token = github_token
        self.discovered = []
        self.seen_repos = set()
        
    async def init(self):
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "VPN-Sub-Discoverer/1.0"
        }
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"
            
        self.session = aiohttp.ClientSession(
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=30)
        )
        
    async def close(self):
        if self.session:
            await self.session.close()
            
    async def search_github_repos(self, query, per_page=30, pages=3):
        repos = []
        for page in range(1, pages + 1):
            url = f"{GITHUB_API}/search/repositories"
            params = {
                "q": query,
                "sort": "updated",
                "order": "desc",
                "per_page": per_page,
                "page": page
            }
            try:
                async with self.session.get(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        items = data.get("items", [])
                        for item in items:
                            repo = {
                                "name": item["full_name"],
                                "url": item["html_url"],
                                "updated": item["updated_at"],
                                "stars": item["stargazers_count"],
                                "description": item.get("description", ""),
                                "default_branch": item.get("default_branch", "main")
                            }
                            repos.append(repo)
                    elif resp.status == 403:
                        print("GitHub API rate limit. Use token or wait.")
                        break
            except Exception as e:
                print(f"Search error: {e}")
                
            await asyncio.sleep(2)
            
        return repos
        
    async def discover_from_github(self):
        all_repos = []
        for seed in DISCOVERY_SEEDS:
            query = seed.split("q=")[1].split("&")[0]
            repos = await self.search_github_repos(query)
            all_repos.extend(repos)
            
        seen = set()
        unique = []
        for r in all_repos:
            if r["name"] not in seen:
                seen.add(r["name"])
                unique.append(r)
                
        return unique
        
    async def list_repo_files(self, repo_name, branch="main"):
        url = f"{GITHUB_API}/repos/{repo_name}/git/trees/{branch}?recursive=1"
        try:
            async with self.session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("tree", [])
                elif resp.status == 404:
                    if branch == "main":
                        return await self.list_repo_files(repo_name, "master")
        except Exception as e:
            print(f"File list error for {repo_name}: {e}")
        return []
        
    def match_file_patterns(self, filename):
        for pattern in FILE_PATTERNS:
            if re.search(pattern, filename, re.I):
                return True
        return False
        
    async def find_subscription_files(self, repo):
        files = await self.list_repo_files(
            repo["name"], 
            repo.get("default_branch", "main")
        )
        
        candidates = []
        for f in files:
            path = f.get("path", "")
            if f.get("type") == "blob" and self.match_file_patterns(path):
                raw_url = f"{RAW_GITHUB}/{repo['name']}/{repo.get('default_branch', 'main')}/{path}"
                candidates.append({
                    "repo": repo["name"],
                    "path": path,
                    "raw_url": raw_url,
                    "size": f.get("size", 0),
                    "updated": repo["updated"],
                    "stars": repo["stars"]
                })
                
        return candidates
        
    async def probe_content(self, url, timeout=10):
        try:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    size = len(text)
                    if size < 100:
                        return None
                        
                    protocols = {}
                    for proto, pattern in PROTOCOL_SIGNATURES.items():
                        count = len(re.findall(pattern, text))
                        if count > 0:
                            protocols[proto] = count
                            
                    if protocols:
                        return {
                            "url": url,
                            "size": size,
                            "protocols": protocols,
                            "total_nodes": sum(protocols.values()),
                            "sample": text[:200]
                        }
        except Exception as e:
            pass
        return None
        
    async def validate_candidates(self, candidates, max_concurrent=20):
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def probe_with_limit(cand):
            async with semaphore:
                result = await self.probe_content(cand["raw_url"])
                if result:
                    return {
                        **result,
                        "repo": cand["repo"],
                        "path": cand["path"],
                        "stars": cand["stars"],
                        "repo_updated": cand["updated"]
                    }
                return None
                
        tasks = [probe_with_limit(c) for c in candidates]
        results = await asyncio.gather(*tasks)
        
        return [r for r in results if r is not None]
        
    async def score_source(self, source):
        score = 0
        score += min(source.get("stars", 0) * 2, 100)
        score += min(source.get("total_nodes", 0), 100)
        
        updated = source.get("repo_updated", "")
        if updated:
            try:
                dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                days_old = (datetime.utcnow() - dt.replace(tzinfo=None)).days
                if days_old < 1:
                    score += 50
                elif days_old < 7:
                    score += 30
                elif days_old < 30:
                    score += 10
            except:
                pass
                
        protocols = source.get("protocols", {})
        if len(protocols) >= 3:
            score += 30
        elif len(protocols) >= 2:
            score += 15
            
        if source["path"].endswith(".txt"):
            score += 10
            
        return score
        
    async def discover_all(self, min_sources=100):
        print("Phase 1: Discovering repositories...")
        repos = await self.discover_from_github()
        print(f"Found {len(repos)} repositories")
        
        print("Phase 2: Finding subscription files...")
        all_candidates = []
        for repo in repos:
            if repo["name"] in self.seen_repos:
                continue
            self.seen_repos.add(repo["name"])
            candidates = await self.find_subscription_files(repo)
            all_candidates.extend(candidates)
            await asyncio.sleep(0.5)
            
        print(f"Found {len(all_candidates)} candidate files")
        
        print("Phase 3: Probing content...")
        validated = await self.validate_candidates(all_candidates)
        print(f"Validated {len(validated)} live sources")
        
        print("Phase 4: Scoring...")
        for src in validated:
            src["score"] = await self.score_source(src)
            
        validated.sort(key=lambda x: x["score"], reverse=True)
        
        top = validated[:min_sources]
        
        sources = []
        for src in top:
            sources.append({
                "name": f"{src['repo']}/{src['path']}",
                "url": src["url"],
                "protocols": list(src["protocols"].keys()),
                "node_count": src["total_nodes"],
                "score": src["score"],
                "stars": src["stars"],
                "updated": src["repo_updated"],
                "discovered": datetime.utcnow().isoformat()
            })
            
        return sources


async def main():
    discoverer = SourceDiscoverer()
    await discoverer.init()
    
    sources = await discoverer.discover_all(min_sources=50)
    
    with open("discovered_sources.json", "w") as f:
        json.dump(sources, f, indent=2)
        
    print(f"\nDiscovered {len(sources)} sources")
    for s in sources[:10]:
        print(f"  {s['name']}: {s['node_count']} nodes, score={s['score']}")
        
    await discoverer.close()


if __name__ == '__main__':
    asyncio.run(main())
