import os
import requests
import json
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

WEBHOOK = os.environ.get("SLACK_WEBHOOK")
STATE_FILE = "monitor_state.json"

def load_state():
    if os.path.exists(STATE_FILE):
        try: with open(STATE_FILE, "r") as f: return json.load(f)
        except: return []
    return []

def save_state(state):
    try: with open(STATE_FILE, "w") as f: json.dump(state, f, indent=4)
    except: pass

def send_slack_notification(message):
    if not WEBHOOK: return
    payload = {"text": message}
    try: requests.post(WEBHOOK, json=payload, timeout=10)
    except: pass

def main():
    url = "https://domain-search.valuetool.io/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
        "Referer": "https://www.google.com/"
    }
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200: return
    except: return

    soup = BeautifulSoup(r.text, "html.parser")
    state = load_state()
    new_state = state.copy()
    
    found_count = 0
    for tag in soup.find_all(["a", "td", "span", "div"]):
        text = tag.text.strip()
        if "." in text and " " not in text and len(text) > 4:
            domain_name = text.lower()
            if any(x in domain_name for x in ["http", "www", "valuetool", "html", "css", "javascript"]): continue
            if domain_name in state or domain_name in new_state: continue
            found_count += 1
            msg = f"🌐 🔥 **VT 新規HP公開検知** 🔥 🌐\n🔗 **ドメイン名**: {domain_name}"
            send_slack_notification(msg)
            new_state.append(domain_name)
            
    save_state(new_state)
    
    # 🕒 日本の現在時刻をゲット（これで重複を絶対に防ぎます）
    tokyo_time = datetime.now(pytz.timezone('Asia/Tokyo')).strftime('%H:%M:%S')
    
    if found_count == 0:
        # 🎯【ここをVT専用に修正！】絶対に大吉と被らないメッセージにします
        send_slack_notification(f"🔵 【VTアドレス監視】7分定期巡回完了 ➔ タイムスタンプ: 【{tokyo_time}】")

if __name__ == "__main__":
    main()
