#!/usr/bin/env python3
"""Patch ip_monitor.py to rotate VirusTotal API keys safely."""

from pathlib import Path
import os
import re
import shutil
import sys
from datetime import datetime

target = Path(sys.argv[1] if len(sys.argv) > 1 else "ip_monitor.py").resolve()
if not target.exists():
    raise SystemExit(f"Not found: {target}")

text = target.read_text(encoding="utf-8")
if "VT_KEYS_FILE =" in text and "def _rotate_vt_key" in text:
    print("Already patched.")
    raise SystemExit(0)

key_match = re.search(
    r'(?m)^VT_API_KEY\s*=\s*["\']([A-Fa-f0-9]{64})["\']\s*$',
    text,
)
if not key_match:
    raise SystemExit("Could not find the existing 64-character VT_API_KEY.")

existing_key = key_match.group(1)
config = '''BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VT_KEYS_FILE = os.path.join(BASE_DIR, "vt_api_keys.txt")
VT_KEY_INDEX_FILE = os.path.join(BASE_DIR, "vt_api_key_index.txt")


def _load_vt_keys():
    with open(VT_KEYS_FILE, "r", encoding="utf-8") as f:
        keys = [line.strip() for line in f if line.strip() and not line.lstrip().startswith("#")]
    if not keys:
        raise RuntimeError("vt_api_keys.txt has no API keys")
    return keys


def _load_vt_key_index(key_count):
    try:
        with open(VT_KEY_INDEX_FILE, "r", encoding="utf-8") as f:
            return int(f.read().strip()) % key_count
    except (OSError, ValueError):
        return 0


def _save_vt_key_index(index):
    temporary = VT_KEY_INDEX_FILE + ".tmp"
    with open(temporary, "w", encoding="utf-8") as f:
        f.write(str(index))
    os.replace(temporary, VT_KEY_INDEX_FILE)


def _rotate_vt_key(current_index, key_count):
    next_index = (current_index + 1) % key_count
    _save_vt_key_index(next_index)
    return next_index
'''
text = text[:key_match.start()] + config.rstrip() + text[key_match.end():]

replacement = '''def get_domains(ip):
    keys = _load_vt_keys()
    key_index = _load_vt_key_index(len(keys))
    url = f"https://www.virustotal.com/api/v3/ip_addresses/{ip}/resolutions"
    quota_statuses = {401, 403, 429}
    attempted = []

    for _ in range(len(keys)):
        attempted.append(key_index + 1)
        headers = {"x-apikey": keys[key_index]}

        try:
            r = requests.get(url, headers=headers, timeout=20)
        except requests.RequestException:
            raise

        if r.status_code in quota_statuses:
            print(
                f"VT API key #{key_index + 1} unavailable "
                f"(HTTP {r.status_code}); switching key.",
                flush=True,
            )
            key_index = _rotate_vt_key(key_index, len(keys))
            continue

        r.raise_for_status()
        data = r.json()
        domains = set()

        for item in data.get("data", []):
            d = item.get("attributes", {}).get("host_name")
            if not d:
                continue
            d = d.lower()
            if d.startswith("www."):
                d = d[4:]
            domains.add(d)

        return domains

    raise RuntimeError(
        "All VirusTotal API keys are unavailable. "
        f"Attempted keys: {attempted}"
    )


'''
func_match = re.search(
    r'(?ms)^def get_domains\(ip\):.*?(?=^def is_live_domain\(domain\):)',
    text,
)
if not func_match:
    raise SystemExit("Could not locate get_domains() in ip_monitor.py.")

text = text[:func_match.start()] + replacement + text[func_match.end():]
compile(text, str(target), "exec")

timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
backup = target.with_name(f"{target.name}.bak-{timestamp}")
shutil.copy2(target, backup)

keys_file = target.with_name("vt_api_keys.txt")
if not keys_file.exists():
    keys_file.write_text(existing_key + "\n", encoding="utf-8")
    os.chmod(keys_file, 0o600)
elif existing_key not in {
    line.strip() for line in keys_file.read_text(encoding="utf-8").splitlines()
}:
    with keys_file.open("a", encoding="utf-8") as f:
        f.write(existing_key + "\n")

target.write_text(text, encoding="utf-8")
print(f"Patched: {target}")
print(f"Backup:  {backup}")
print(f"Keys:    {keys_file}")
print("Existing key was preserved as key #1.")
