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
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except:
            return []
    return []

def save_state(state):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=4)
    except:
        pass

def send_slack_notification(message):
    if not WEBHOOK: return
    payload = {"text": message}
    try: requests.post(WEBHOOK, json=payload, timeout=10)
    except: pass

def main():
    # 🕒 先に日本時間を計算（サイトが空っぽでも絶対に通知を飛ばすため）
    tokyo_time = datetime.now(pytz.timezone('Asia/Tokyo')).strftime('%H:%M:%S')
    
    url = "https://domain-search.valuetool.io/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
        "Referer": "https://www.google.com/"
    }
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            # サイトが落ちていても、エラーにせずSlackに報告する
            send_slack_notification(f"🔵 【VTアドレス監視】7分定期巡回完了 ➔ タイムスタンプ: 【{tokyo_time}】(※現在サイトメンテナンス中)")
            return
    except:
        send_slack_notification(f"🔵 【VTアドレス監視】7分定期巡回完了 ➔ タイムスタンプ: 【{tokyo_time}】(※通信一時混雑)")
        return

    soup = BeautifulSoup(r.text, "html.parser")
    state = load_state()
    new_state = state.copy()
    
    found_count = 0
    
    # サイトにドメインが載っているかチェック
    for tag in soup.find_all(["a", "td", "span", "div"]):
        text = tag.text.strip()
        if "." in text and " " not in text and len(text) > 4:
            domain_name = text.lower()
            if any(x in domain_name for x in ["http", "www", "valuetool", "html", "css", "javascript"]): continue
            if domain_name in state or domain_name in new_state: continue
            
            found_count += 1
            
            # ✨スクショ通りの新規検知通知デザイン
            if "seikotsuin" in domain_name or "h-" in domain_name:
                msg = f"🟡候補を検知しました！ [VT]\niP: 54.248.170.111\nDOMAIN: {domain_name}"
            else:
                msg = f"🚀公開されました！【公開になりました！】 [VT]\niP: 54.248.170.119\nDOMAIN: {domain_name}"
                
            send_slack_notification(msg)
            new_state.append(domain_name)
            
    save_state(new_state)
    
    # 🎯 サイトが何件であろうが、真っ白だろうが、絶対にこの終了通知を強制送信する！
    send_slack_notification(f"🔵 【VTアドレス監視】7分定期巡回完了 ➔ タイムスタンプ: 【{tokyo_time}】")

if __name__ == "__main__":
    main()
