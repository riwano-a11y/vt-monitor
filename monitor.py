import os
import requests
import json

WEBHOOK = os.environ.get("SLACK_WEBHOOK")
STATE_FILE = "monitor_state.json"

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f: return json.load(f)
        except: return []
    return []

def save_state(state):
    try:
        with open(STATE_FILE, "w") as f: json.dump(state, f, indent=4)
    except: pass

def send_slack_notification(message):
    if not WEBHOOK: return
    payload = {"text": message}
    try: requests.post(WEBHOOK, json=payload, timeout=10)
    except: pass

def main():
    # 🎯 監視対象のメインURL（裏側のAPIなど）
    url = "https://domain-search.valuetool.io/api/v1/domains/search"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Monitor/1.0",
        "Accept": "application/json"
    }
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            send_slack_notification(f"⚠️ 【VT監視警報】サイトへのアクセスがブロックされました（エラーコード: {r.status_code}）")
            return
        data = r.json()
    except Exception as e:
        send_slack_notification(f"⚠️ 【VT監視警報】通信エラーが発生しました: {e}")
        return

    # APIの構造からドメインリストを抽出
    domains = data.get("domains", []) if isinstance(data, dict) else data
    state = load_state()
    new_state = state.copy()
    
    found_count = 0
    for item in domains:
        domain_name = item.get("name") if isinstance(item, dict) else item
        if not domain_name:
            continue
            
        if domain_name in state:
            continue
            
        found_count += 1
        # 🎉 新しいHP公開を検知した場合の通知
        msg = (
            f"🌐 🔥 **VT 新規HP公開検知** 🔥 🌐\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔗 **ドメイン名**: {domain_name}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        send_slack_notification(msg)
        new_state.append(domain_name)
        
    save_state(new_state)

    # 🎯【新機能】もし新着が「0件」だった場合、Slackに生存報告を送ります！
    if found_count == 0:
        send_slack_notification("🟢 【VTアドレス監視】定期巡回完了。新着HP公開は0件でした（システム正常稼働中）")

if __name__ == "__main__":
    main()
