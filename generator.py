#!/usr/bin/env python3
import json, base64, re, os, urllib.request
from urllib.parse import parse_qs

IN = "tested_nodes.json"
OUT = "subscription.json"
WARP_FILE = "warp.json"
GEO_CACHE = "geo_cache.json"

COUNTRIES = {
    "RU":"Россия","US":"США","GB":"Великобритания","DE":"Германия","FR":"Франция",
    "NL":"Нидерланды","SG":"Сингапур","JP":"Япония","KR":"Корея","IN":"Индия",
    "TR":"Турция","PL":"Польша","UA":"Украина","KZ":"Казахстан","BY":"Беларусь",
    "CN":"Китай","HK":"Гонконг","TW":"Тайвань","CA":"Канада","AU":"Австралия",
    "BR":"Бразилия","FI":"Финляндия","SE":"Швеция","NO":"Норвегия","CH":"Швейцария",
    "AT":"Австрия","IT":"Италия","ES":"Испания","PT":"Португалия","BE":"Бельгия",
    "CZ":"Чехия","RO":"Румыния","BG":"Болгария","HU":"Венгрия","LV":"Латвия",
    "LT":"Литва","EE":"Эстония","MD":"Молдова","GE":"Грузия","AM":"Армения",
    "AZ":"Азербайджан","UZ":"Узбекистан","KG":"Кыргызстан","TJ":"Таджикистан",
    "TH":"Таиланд","VN":"Вьетнам","MY":"Малайзия","ID":"Индонезия","PH":"Филиппины",
    "MX":"Мексика","AR":"Аргентина","CL":"Чили","ZA":"ЮАР","AE":"ОАЭ","SA":"Саудовская Аравия",
    "IL":"Израиль","IE":"Ирландия","DK":"Дания","IS":"Исландия","NZ":"Новая Зеландия",
    "PK":"Пакистан","BD":"Бангладеш","LK":"Шри-Ланка","NG":"Нигерия","KE":"Кения",
    "CO":"Колумбия","PE":"Перу","VE":"Венесуэла","EC":"Эквадор","CR":"Коста-Рика",
    "PA":"Панама","UY":"Уругвай","PY":"Парагвай","BO":"Боливия","SR":"Суринам",
    "GY":"Гайана","GF":"Французская Гвиана"
}

def flag(cc):
    if not cc or len(cc) != 2: return ""
    return chr(0x1F1E6 + ord(cc[0]) - ord('A')) + chr(0x1F1E6 + ord(cc[1]) - ord('A'))

def geo(ip):
    cache = {}
    if os.path.exists(GEO_CACHE):
        with open(GEO_CACHE) as f: cache = json.load(f)
    if ip in cache: return cache[ip]
    try:
        req = urllib.request.Request(f"http://ip-api.com/json/{ip}?fields=status,country,countryCode,city&lang=ru", headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=4) as r:
            d = json.loads(r.read().decode())
            if d.get("status") == "success":
                res = (d.get("country","Неизвестно"), d.get("countryCode",""), d.get("city","Неизвестно"))
                cache[ip] = res
                with open(GEO_CACHE,"w") as f: json.dump(cache,f,ensure_ascii=False)
                return res
    except Exception:
        pass
    return ("Неизвестно","", "Неизвестно")

def name_node(host, ping):
    country, cc, city = geo(host)
    cn = COUNTRIES.get(cc, country)
    fl = flag(cc)
    return f"{fl} {cn} | {city} [{ping}ms]"

def parse_vless(u):
    m = re.match(r"vless://([^@]+)@([^:]+):(\d+)\?(.*)", u)
    if not m: return None
    uuid, host, port, q = m.group(1), m.group(2), int(m.group(3)), m.group(4)
    ps = parse_qs(q)
    tls = {"enabled": True, "server_name": ps.get("sni",[""])[0], "utls": {"enabled": True, "fingerprint": ps.get("fp",["chrome"])[0] or "chrome"}}
    if ps.get("security",[""])[0] == "reality":
        tls["reality"] = {"enabled": True, "public_key": ps.get("pbk",[""])[0], "short_id": ps.get("sid",[""])[0]}
    out = {"type":"vless","server":host,"server_port":port,"uuid":uuid,"tls":tls}
    if ps.get("flow"): out["flow"] = ps["flow"][0]
    net = ps.get("type",[""])[0] or "tcp"
    if net in ("ws","grpc","http"):
        out["transport"] = {"type": net}
        if net == "ws":
            out["transport"]["path"] = ps.get("path",[""])[0]
            out["transport"]["headers"] = {"Host": ps.get("host",[ps.get("sni",[""])[0]])[0]}
    out["multiplex"] = {"enabled": True, "protocol": "smux", "max_streams": 16}
    return out

def parse_vmess(u):
    try:
        j = json.loads(base64.b64decode(u[8:]).decode())
        out = {"type":"vmess","server":j["add"],"server_port":int(j["port"]),"uuid":j["id"],"security":j.get("scy","auto"),"alter_id":int(j.get("aid",0))}
        if j.get("tls") == "tls":
            out["tls"] = {"enabled": True, "server_name": j.get("sni", j["add"]), "utls": {"enabled": True, "fingerprint": "chrome"}}
        net = j.get("net","tcp")
        if net in ("ws","grpc","http"):
            out["transport"] = {"type": net}
            if net == "ws":
                out["transport"]["path"] = j.get("path","")
                out["transport"]["headers"] = {"Host": j.get("host", j["add"])}
        out["multiplex"] = {"enabled": True, "protocol": "smux", "max_streams": 16}
        return out
    except Exception:
        return None

def parse_trojan(u):
    m = re.match(r"trojan://([^@]+)@([^:]+):(\d+)(?:\?(.*))?", u)
    if not m: return None
    pw, host, port = m.group(1), m.group(2), int(m.group(3))
    ps = parse_qs(m.group(4) or "")
    out = {"type":"trojan","server":host,"server_port":port,"password":pw,"tls":{"enabled":True,"server_name":ps.get("sni",[host])[0],"utls":{"enabled":True,"fingerprint":ps.get("fp",["chrome"])[0] or "chrome"}}}
    out["multiplex"] = {"enabled": True, "protocol": "smux", "max_streams": 16}
    return out

def parse_hy2(u):
    m = re.match(r"hysteria2://([^@]+)@([^:]+):(\d+)(?:\?(.*))?", u)
    if not m: return None
    pw, host, port = m.group(1), m.group(2), int(m.group(3))
    ps = parse_qs(m.group(4) or "")
    return {"type":"hysteria2","server":host,"server_port":port,"password":pw,"tls":{"enabled":True,"server_name":ps.get("sni",[host])[0]}}

def parse_ss(u):
    m = re.match(r"ss://([^@]+)@([^:]+):(\d+)", u)
    if not m: return None
    b64creds, host, port = m.group(1), m.group(2), int(m.group(3))
    try:
        creds = base64.b64decode(b64creds + "==").decode()
        method, pw = creds.split(":",1)
    except Exception:
        return None
    return {"type":"shadowsocks","server":host,"server_port":port,"method":method,"password":pw}

def node_to_outbound(node, tag):
    if node.startswith("hy2://"):
        node = node.replace("hy2://", "hysteria2://", 1)
    if node.startswith("vless://"): o = parse_vless(node)
    elif node.startswith("vmess://"): o = parse_vmess(node)
    elif node.startswith("trojan://"): o = parse_trojan(node)
    elif node.startswith("hysteria2://"): o = parse_hy2(node)
    elif node.startswith("ss://"): o = parse_ss(node)
    else: return None
    if not o: return None
    o["tag"] = tag
    return o

def build_config(nodes):
    sel = (["WARP"] if os.path.exists(WARP_FILE) else []) + [f"n{i}" for i in range(len(nodes))] + ["direct"]
    outbounds = [{"type":"selector","tag":"Proxy","outbounds":sel},{"type":"direct","tag":"direct"},{"type":"block","tag":"block"}]
    if os.path.exists(WARP_FILE):
        with open(WARP_FILE) as f:
            warp = json.load(f)
            warp["tag"] = "WARP"
            outbounds.append(warp)
    for i, n in enumerate(nodes):
        o = node_to_outbound(n["node"], f"n{i}")
        if o: outbounds.append(o)
    route = {
        "rules": [
            {"geosite":["category-ads-all","category-ads"],"outbound":"block"},
            {"domain":["ya.ru","yandex.ru","yandex.net","yastatic.net","yandex.com","vk.com","vkontakte.ru","mail.ru","ok.ru","gosuslugi.ru","sberbank.ru","tinkoff.ru","avito.ru","wildberries.ru","ozon.ru"],"outbound":"direct"},
            {"geosite":["youtube","google","telegram","tiktok","netflix","disney","twitter","facebook","instagram","whatsapp","wechat"],"outbound":"Proxy"},
            {"domain_keyword":["bip","viber","signal"],"outbound":"Proxy"},
            {"geoip":["google","telegram","netflix"],"outbound":"Proxy"}
        ],
        "final": "Proxy",
        "auto_detect_interface": True,
        "tls_fragment": {"enabled": True, "size": "1-500", "sleep": "0-10"}
    }
    dns = {
        "servers": [
            {"tag":"adguard","address":"https://dns.adguard-dns.com/dns-query","detour":"direct"},
            {"tag":"local","address":"https://223.5.5.5/dns-query","detour":"direct","domain_strategy":"ipv4_only"}
        ],
        "rules": [
            {"geosite":["category-ads-all"],"server":"adguard"},
            {"domain":["ya.ru","yandex.ru","vk.com","mail.ru"],"server":"local"}
        ],
        "final": "adguard",
        "independent_cache": True,
        "fakeip": {"enabled": True, "inet4_range": "198.18.0.0/15"}
    }
    return {"log":{"level":"warn","timestamp":True},"dns":dns,"inbounds":[{"type":"tun","tag":"tun-in","mtu":9000,"inet4_address":"172.19.0.1/30","auto_route":True,"strict_route":True,"stack":"system","sniff":True}],"outbounds":outbounds,"route":route,"experimental":{"cache_file":{"enabled":True}}}

def main():
    with open(IN) as f: nodes = json.load(f)
    nodes = nodes[:150]
    for n in nodes:
        n["tag"] = name_node(n["host"], n["ping"])
    cfg = build_config(nodes)
    with open(OUT,"w") as f: json.dump(cfg,f,ensure_ascii=False,indent=2)
    print(f"Generated {OUT} with {len(nodes)} nodes")

if __name__ == "__main__":
    main()
