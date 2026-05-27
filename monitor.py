import os
import requests
import json
import socket
from bs4 import BeautifulSoup

# GitHubの金庫（Secrets）から安全に鍵を読み込みます
WEBHOOK = os.environ.get("SLACK_WEBHOOK")
VT_API_KEY = os.environ.get("VT_API_KEY")
STATE_FILE = "domain_monitor_state.json"

TARGET_IPS = [
    "54.248.170.119",
    "57.182.131.80",
    "18.179.211.152",
    "133.117.152.195"
]

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f: return json.load(f)
        except: return {}
    return {}

def save_state(state):
    try:
        with open(STATE_FILE, "w") as f: json.dump(state, f, indent=4)
    except: pass

def send_slack_notification(message):
    if not WEBHOOK: return
    payload = {"text": message}
    try: requests.post(WEBHOOK, json=payload, timeout=10)
    except: pass

def fetch_crt_sh(ip_or_domain):
    domains = []
    url = f"https://crt.sh/?q={ip_or_domain}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            for row in soup.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) >= 5:
                    domain_text = cells[4].text.strip() if len(cells) > 4 else cells[3].text.strip()
                    for d in domain_text.split('\n'):
                        d = d.strip().replace('*.', '')
                        if d and '.' in d and not d.startswith('http') and d not in domains:
                            domains.append(d)
    except: pass
    return domains

def fetch_virus_total_api(ip):
    domains = []
    if not VT_API_KEY: return domains
    url = f"https://www.virustotal.com/api/v3/ip_addresses/{ip}/resolutions"
    headers = {"x-apikey": VT_API_KEY, "User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            data = r.json()
            for item in data.get("data", []):
                domain = item.get("attributes", {}).get("host_name")
                if domain and domain not in domains:
                    domains.append(domain)
    except: pass
    return domains

def get_clean_domain(domain_str):
    if not domain_str: return ""
    return domain_str.lower().replace("www.", "").strip()

def check_http_published(domain_str):
    urls = [f"https://{domain_str}", f"http://{domain_str}"]
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Domain-Monitor/1.0"}
    for url in urls:
        try:
            r = requests.get(url, headers=headers, timeout=5, allow_redirects=True)
            if r.status_code in [401, 403]: return False
            if r.status_code < 500:
                soup = BeautifulSoup(r.text, "html.parser")
                page_text = r.text.strip().lower()
                if page_text == "web php" or "index of /" in page_text or page_text == "apache" or not page_text:
                    return False
                title = ""
                if soup.title: title = soup.title.text.strip()
                return True, title, url
        except: pass
    return False, "", ""

def main():
    state = load_state()
    new_state = state.copy()
    
    for ip in TARGET_IPS:
        print(f"CHECKING IP: {ip}")
        raw_crt = fetch_crt_sh(ip)
        raw_vt = fetch_virus_total_api(ip)
        
        reverse_dns = ""
        try:
            reverse_dns = socket.gethostbyaddr(ip)[0]
            if reverse_dns and ip not in reverse_dns:
                raw_crt.append(reverse_dns)
                base_domain = ".".join(reverse_dns.split(".")[-2:])
                raw_crt += fetch_crt_sh(base_domain)
        except: pass
            
        unique_clean_domains = {}
        for d in (raw_crt + raw_vt):
            clean = get_clean_domain(d)
            if not clean: continue
            if any(x in clean for x in ["amazon", "aws", "cloudfront", "internal", "local", "ptrcloud", "ptr", "cloud"]) or clean.startswith("cp."):
                continue
            if clean not in unique_clean_domains:
                unique_clean_domains[clean] = {"crt": False, "vt": False}
            if d in raw_crt: unique_clean_domains[clean]["crt"] = True
            if d in raw_vt: unique_clean_domains[clean]["vt"] = True

        for domain, src_info in unique_clean_domains.items():
            if domain in new_state and new_state[domain].get("status") == "published":
                continue
                
            active, title, target_url = check_http_published(domain)
            sources = []
            if src_info["crt"]: sources.append("crt.sh")
            if src_info["vt"]: sources.append("VT")
            source_text = f" [{' / '.join(sources)}]" if sources else ""
            
            # 初めてドメインを発見したとき
            if domain not in new_state:
                if active:
                    # 🚀 パターン1：完全新規でいきなりHP公開状態
                    new_state[domain] = {"status": "published"}
                    msg = (
                        f"🚀 **IPアドレス {ip} から新しいHPが公開されました！**{source_text}\n"
                        f"🌐 **DOMAIN**: {domain}\n"
                        f"📝 **TITLE**: {title}\n"
                        f"🔗 **URL**: {target_url}\n"
                        f"----------------------------------------"
                    )
                    send_slack_notification(msg)
                else:
                    # 🟡 パターン2：HPはないが、ドメイン候補だけ検知
                    new_state[domain] = {"status": "candidate"}
                    msg = (
                        f"🟡 **IPアドレス {ip} から候補が検知されました！**{source_text}\n"
                        f"🌐 **DOMAIN**: {domain}\n"
                        f" STATUS: NO WEBSITE（まだサイトは開いていません）\n"
                        f"----------------------------------------"
                    )
                    send_slack_notification(msg)
                    
            # 🟢 すでに「候補」だったものが、今回「公開状態」に進化（昇格）したとき
            elif new_state[domain].get("status") == "candidate" and active:
                new_state[domain] = {"status": "published"}
                msg = (
                    f"🚀 **IPアドレス {ip} から候補だったHPが公開されました！**{source_text}\n"
                    f"🌐 **DOMAIN**: {domain}\n"
                    f"📝 **TITLE**: {title}\n"
                    f"🔗 **URL**: {target_url}\n"
                    f"----------------------------------------"
                )
                send_slack_notification(msg)
                
    save_state(new_state)

if __name__ == "__main__":
    main()
