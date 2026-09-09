# monthly_report.py
import os, json, requests

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

try:
    with open("stats.json") as f:
        stats = json.load(f)
except FileNotFoundError:
    from notifier import SUBREDDITS
    stats = {s: False for s in SUBREDDITS}

quiet = [s for s, notified in stats.items() if not notified]

if quiet:
    msg = "Subs with zero notifications this month:\n" + "\n".join(f"r/{s}" for s in quiet)
else:
    msg = "Every watched sub notified you at least once this month."

requests.get(
    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
    params={"chat_id": TELEGRAM_CHAT_ID, "text": msg},
    timeout=10,
)

with open("stats.json", "w") as f:
    json.dump({s: False for s in stats}, f)
