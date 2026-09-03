#!/usr/bin/env python3
import json, re, socket, concurrent.futures, time

IN = "raw_nodes.json"
OUT = "tested_nodes.json"
MAX_PING = 500
WORKERS = 50

def get_host_port(node):
    try:
        m = re.search(r"@([^:]+):(\d+)", node)
        if m: return m.group(1), int(m.group(2))
        j = json.loads(re.search(r"vmess://(.+)", node).group(1))
        j = json.loads(__import__("base64").b64decode(j).decode())
        return j["add"], int(j["port"])
    except Exception:
        return None, None

def tcp_ping(host, port, to=2):
    try:
        t0 = time.time()
        s = socket.create_connection((host, port), timeout=to)
        s.close()
        return int((time.time() - t0) * 1000)
    except Exception:
        return 9999

def test(node):
    h, p = get_host_port(node)
    if not h: return None
    try: socket.getaddrinfo(h, None)
    except Exception: return None
    ping = tcp_ping(h, p)
    if ping > MAX_PING: return None
    return {"node": node, "ping": ping, "host": h}

def main():
    with open(IN) as f: nodes = json.load(f)
    ok = []
    with concurrent.futures.ThreadPoolExecutor(WORKERS) as ex:
        for r in ex.map(test, nodes):
            if r: ok.append(r)
    ok.sort(key=lambda x: x["ping"])
    with open(OUT, "w") as f: json.dump(ok, f, ensure_ascii=False)
    print(f"Tested {len(nodes)} -> {len(ok)} ok -> {OUT}")

if __name__ == "__main__":
    main()
