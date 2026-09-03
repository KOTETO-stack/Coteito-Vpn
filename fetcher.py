#!/usr/bin/env python3
import json, base64, re, urllib.request, urllib.error, socket, os
from urllib.parse import urlparse, unquote

SOURCES = "sources.json"
OUT = "raw_nodes.json"

def fetch(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception:
        return b""

def b64_decode(data):
    try:
        return base64.b64decode(data).decode("utf-8","ignore")
    except Exception:
        return ""

def parse_base64(text):
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"): continue
        decoded = b64_decode(line)
        if decoded:
            out.extend([x for x in decoded.splitlines() if x.strip()])
        else:
            out.append(line)
    return out

def parse_yaml(text):
    nodes = []
    try:
        import yaml
        d = yaml.safe_load(text)
        if d and "proxies" in d:
            for p in d["proxies"]:
                t = p.get("type","")
                if t == "vless":
                    nodes.append(f"vless://{p.get('uuid','')}@{p.get('server','')}:{p.get('port','')}?security={p.get('tls','')}&sni={p.get('sni','')}&fp={p.get('client-fingerprint','')}&type={p.get('network','ws')}&path={p.get('ws-opts',{}).get('path','')}#{p.get('name','')}")
                elif t == "vmess":
                    j = {"v":"2","ps":p.get("name",""),"add":p.get("server",""),"port":str(p.get("port","")),"id":p.get("uuid",""),"aid":"0","scy":"auto","net":p.get("network","tcp"),"type":"none","host":p.get("ws-opts",{}).get("headers",{}).get("Host",""),"path":p.get("ws-opts",{}).get("path",""),"tls":p.get("tls",""),"sni":p.get("sni","")}
                    nodes.append("vmess://" + base64.b64encode(json.dumps(j).encode()).decode())
                elif t == "trojan":
                    nodes.append(f"trojan://{p.get('password','')}@{p.get('server','')}:{p.get('port','')}?sni={p.get('sni','')}&fp={p.get('client-fingerprint','')}#{p.get('name','')}")
                elif t == "hysteria2" or t == "hy2":
                    nodes.append(f"hysteria2://{p.get('password','')}@{p.get('server','')}:{p.get('port','')}?sni={p.get('sni','')}#{p.get('name','')}")
                elif t == "ss":
                    nodes.append(f"ss://{base64.b64encode((p.get('cipher','')+':'+p.get('password','')).encode()).decode()}@{p.get('server','')}:{p.get('port','')}#{p.get('name','')}")
    except Exception:
        pass
    return nodes

def extract_nodes(text, src_type="base64"):
    text = text.strip()
    if src_type == "yaml" or text.startswith("proxies:") or text.startswith("port:"):
        return parse_yaml(text)
    lines = parse_base64(text) if src_type == "base64" else text.splitlines()
    nodes = []
    for line in lines:
        line = line.strip()
        if re.match(r"^(vless|vmess|trojan|hysteria2|hy2|ss)://", line):
            nodes.append(line)
    return nodes

def dedup(nodes):
    seen = set()
    out = []
    for n in nodes:
        try:
            u = urlparse(n)
            key = f"{u.hostname}:{u.port}"
            if key and key not in seen:
                seen.add(key)
                out.append(n)
        except Exception:
            out.append(n)
    return out

def main():
    with open(SOURCES) as f:
        cfg = json.load(f)
    all_nodes = []
    for s in cfg.get("sources", []):
        if not s.get("enabled", True):
            continue
        data = fetch(s["url"])
        if not data:
            continue
        try:
            text = data.decode("utf-8","ignore")
        except Exception:
            continue
        nodes = extract_nodes(text, s.get("type","base64"))
        all_nodes.extend(nodes)
    all_nodes = dedup(all_nodes)
    with open(OUT, "w") as f:
        json.dump(all_nodes, f, ensure_ascii=False)
    print(f"Fetched {len(all_nodes)} unique nodes -> {OUT}")

if __name__ == "__main__":
    main()
