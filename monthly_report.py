# monthly_report.py
import os, json, requests

TELEGRAM_TOKEN = os.environ["8714103847:AAGw-Lh_IS5EwtpbB8z5V_pY96Hvf6uuolE"]
TELEGRAM_CHAT_ID = os.environ["6825628060"]

with open("stats.json") as f:
    stats = json.load(f)

quiet = [s for s, notified in stats.items() if not notified]

if quiet:
    msg = "Subs with zero notifications this month:\n" + "\n".join(f"r/{s}" for s in quiet)
else:
    msg = "Every watched sub notified you at least once this month."

requests.get(
    f"https://api.telegram.org/bot{8714103847:AAGw-Lh_IS5EwtpbB8z5V_pY96Hvf6uuolE}/sendMessage",
    params={"chat_id":6825628060, "text": msg},
    timeout=10,
)

# reset for next month
with open("stats.json", "w") as f:
    json.dump({s: False for s in stats}, f)
