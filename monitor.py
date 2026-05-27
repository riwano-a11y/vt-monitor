import os
import requests
import json
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
    url = "https://domain-search.valuetool.io/api/v1/domains/search"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Monitor/1.0", "Accept": "application/json"}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200: return
        data = r.json()
    except: return

    domains = data.get("domains", []) if isinstance(data, dict) else data
    state = load_state()
    new_state = state.copy()
    
    found_count = 0
    for item in domains:
        domain_name = item.get("name") if isinstance(item, dict) else item
        if not domain_name or domain_name in state: continue
        found_count += 1
        msg = f"🌐 🔥 **VT 新規HP公開検知** 🔥 🌐\n🔗 **ドメイン名**: {domain_name}"
        send_slack_notification(msg)
        new_state.append(domain_name)
        
    save_state(new_state)
    
    # 🕒 日本の現在時刻をゲット
    tokyo_time = datetime.now(pytz.timezone('Asia/Tokyo')).strftime('%H:%M:%S')
    
    if found_count == 0:
        send_slack_notification(f"🟢 【VTアドレス監視】定期巡回完了（正常稼働中） ➔ タイムスタンプ: 【{tokyo_time}】")

if __name__ == "__main__":
    main()
