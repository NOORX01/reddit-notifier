# notifier.py
import os, json, requests, feedparser
from datetime import datetime, timezone

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

SUBREDDITS = ["Daytrading"]

KEYWORDS = [
    "Depuis", "profits", "money", "eval", "strat", "strategy", "prop firm", "funded account",
    "evaluation fee", "challenge fee", "FTMO", "MyForexFunds", "prop firm scam",
    "failed evaluation", "passed evaluation", "payout rules", "drawdown rules",
    "profit split", "need capital", "trading capital", "get funded",
    "how to get funded", "capital allocation", "managed account", "PAMM",
    "copy trading", "mirror trading", "social trading", "verified track record",
    "transparent trading", "managed forex", "tired of prop firms",
    "prop firm alternative", "better than prop firm", "keep losing evaluations",
    "evaluation passed then failed", "prop firm payout denied",
    "passive income trading", "let someone trade for me", "find a trader",
    "allocate capital", "trader performance",
]

MAX_AGE_MINUTES = 15
STATS_FILE = "stats.json"
HEADERS = {"User-Agent": "reddit-keyword-notifier/1.0 (by u/your_username)"}

def load_stats():
    stats = {s: False for s in SUBREDDITS}
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE) as f:
            stats.update(json.load(f))
    return stats

def save_stats(stats):
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f, indent=2)

def get_age_minutes(entry):
    published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - published).total_seconds() / 60

def is_recent(entry):
    age = get_age_minutes(entry)
    return 0 <= age < MAX_AGE_MINUTES

def matches(title):
    t = title.lower()
    return any(k.lower() in t for k in KEYWORDS)

def notify(entry, sub):
    response = requests.get(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        params={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": f"{entry.title}\nr/{sub}\n{entry.link}",
            "disable_web_page_preview": True,
        },
        timeout=10,
    )
    print(f"TELEGRAM: HTTP {response.status_code} {response.text[:500]}")
    response.raise_for_status()
    result = response.json()
    if not result.get("ok"):
        raise RuntimeError(f"Telegram API error: {result}")

def main():
    stats = load_stats()

    for sub in SUBREDDITS:
        url = f"https://www.reddit.com/r/{sub}/new/.rss"
        print(f"FETCH: {url}")

        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            print(f"FETCH: HTTP {response.status_code}, {len(response.text)} bytes")
            response.raise_for_status()
            feed = feedparser.parse(response.text)
        except Exception as e:
            print(f"FETCH ERROR r/{sub}: {e}")
            continue

        print(f"FEED r/{sub}: {len(feed.entries)} entries received")

        if feed.bozo:
            print(f"FEED WARNING r/{sub}: {feed.bozo_exception}")

        for i, entry in enumerate(feed.entries, 1):
            try:
                age = get_age_minutes(entry)
                recent = is_recent(entry)
                matched = matches(entry.title)
                print(f"POST {i}: age={age:.1f}m recent={recent} match={matched} title={entry.title!r}")

                if recent and matched:
                    print(f"MATCH FOUND: notifying for r/{sub}")
                    notify(entry, sub)
                    stats[sub] = True
                    print(f"NOTIFIED: r/{sub}")
            except Exception as e:
                print(f"POST {i}: ERROR processing entry: {e}")

    save_stats(stats)

if __name__ == "__main__":
    main()
