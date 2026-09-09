# notifier.py
import os, json, requests, feedparser
from datetime import datetime, timezone

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# <-- EDIT: your subreddits, names only, no r/, lowercase
SUBREDDITS = [
    "buildapcsales",
    "gamedeals",
    "hardwareswap",
]

# <-- EDIT: keywords to match in post titles (case-insensitive)
KEYWORDS = ["gpu", "rtx"]

MAX_AGE_MINUTES = 15  # keep above the 5-minute cron interval

STATS_FILE = "stats.json"

HEADERS = {"User-Agent": "reddit-keyword-notifier/1.0 (by u/your_username)"}

def load_stats():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE) as f:
            return json.load(f)
    return {}

def save_stats(stats):
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f, indent=2)

def is_recent(entry):
    published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
    age = (datetime.now(timezone.utc) - published).total_seconds()
    return age < MAX_AGE_MINUTES * 60

def matches(title):
    t = title.lower()
    return any(k.lower() in t for k in KEYWORDS)

def notify(entry, sub):
    requests.get(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        params={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": f"{entry.title}\nr/{sub}\n{entry.link}",
            "disable_web_page_preview": True,
        },
        timeout=10,
    )

def main():
    notified = set()
    stats = load_stats()
    for sub in SUBREDDITS:
        url = f"https://www.reddit.com/r/{sub}/new/.rss"
        try:
            feed = feedparser.parse(requests.get(url, headers=HEADERS, timeout=15).text)
        except Exception as e:
            print(f"r/{sub}: fetch error {e}")
            continue
        for entry in feed.entries:
            if entry.id not in notified and is_recent(entry) and matches(entry.title):
                notify(entry, sub)
                notified.add(entry.id)
                stats[sub] = True
    save_stats(stats)

if __name__ == "__main__":
    main()
