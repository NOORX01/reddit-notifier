# notifier.py
import os, json, time, requests, feedparser
from datetime import datetime, timezone

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# 30-sub watchlist. The script checks exactly one subreddit per minute.
SUBREDDITS = [
    "Forex",
    "ForexTraders",
    "Daytrading",
    "RealDayTrading",
    "algotrading",
    "Trading",
    "wallstreetbets",
    "options",
    "swingtrading",
    "Scalping",
    "TechnicalAnalysis",
    "Forexstrategy",
    "ForexSignals",
    "TradingView",
    "OptionsTrading",
    "thetagang",
    "CoveredCalls",
    "WheelOptions",
    "Commodities",
    "quantfinance",
    "PriceAction",
    "FuturesTrading",
    "StockMarket",
    "stocks",
    "Trading212",
    "BitcoinMarkets",
    "CryptoMarkets",
    "OrderFlow_Trading",
    "TradingEdge",
    "MetaTrader",
]

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

# 35 minutes gives each subreddit a 5-minute overlap at the 30-minute cycle boundary.
MAX_AGE_MINUTES = 35
INTERVAL_SECONDS = 60
STATS_FILE = "stats.json"
SEEN_FILE = "seen_posts.json"
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


def load_seen():
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE) as f:
                data = json.load(f)
            return set(data)
        except (json.JSONDecodeError, TypeError):
            print(f"WARNING: could not parse {SEEN_FILE}; starting with empty dedup set")
    return set()


def save_seen(seen):
    # Keep the file bounded so it does not grow forever.
    trimmed = list(seen)[-5000:]
    with open(SEEN_FILE, "w") as f:
        json.dump(trimmed, f)


def get_age_minutes(entry):
    published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - published).total_seconds() / 60


def is_recent(entry):
    age = get_age_minutes(entry)
    return 0 <= age < MAX_AGE_MINUTES


def matched_keyword(title):
    t = title.lower()
    return next((k for k in KEYWORDS if k.lower() in t), None)


def post_id(entry):
    # Reddit RSS entries expose the post ID as id; permalink is a useful fallback.
    return getattr(entry, "id", None) or getattr(entry, "link", None)


def notify(entry, sub, keyword):
    response = requests.get(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        params={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": f"{entry.title}\nr/{sub}\nMatched keyword: {keyword}\n{entry.link}",
            "disable_web_page_preview": True,
        },
        timeout=10,
    )
    print(f"TELEGRAM: HTTP {response.status_code} {response.text[:500]}")
    response.raise_for_status()
    result = response.json()
    if not result.get("ok"):
        raise RuntimeError(f"Telegram API error: {result}")


def check_subreddit(sub, stats, seen):
    url = f"https://www.reddit.com/r/{sub}/new/.rss"
    print(f"FETCH: {url}")

    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        print(f"FETCH: HTTP {response.status_code}, {len(response.text)} bytes")
        response.raise_for_status()
        feed = feedparser.parse(response.text)
    except Exception as e:
        print(f"FETCH ERROR r/{sub}: {e}")
        return

    print(f"FEED r/{sub}: {len(feed.entries)} entries received")

    if feed.bozo:
        print(f"FEED WARNING r/{sub}: {feed.bozo_exception}")

    for i, entry in enumerate(feed.entries, 1):
        try:
            age = get_age_minutes(entry)
            recent = is_recent(entry)
            keyword = matched_keyword(entry.title)
            matched = keyword is not None
            pid = post_id(entry)
            already_seen = pid in seen if pid else False

            print(
                f"POST {i}: age={age:.1f}m recent={recent} match={matched} "
                f"seen={already_seen} keyword={keyword!r} title={entry.title!r}"
            )

            if recent and matched and not already_seen:
                print(f"MATCH FOUND: notifying for r/{sub}, keyword={keyword!r}")
                notify(entry, sub, keyword)
                stats[sub] = True
                if pid:
                    seen.add(pid)
                print(f"NOTIFIED: r/{sub}")
        except Exception as e:
            print(f"POST {i}: ERROR processing entry: {e}")


def main():
    stats = load_stats()
    seen = load_seen()

    print(f"WATCHLIST: {len(SUBREDDITS)} subreddits")
    print(f"SCHEDULE: one subreddit every {INTERVAL_SECONDS}s; full cycle every {len(SUBREDDITS)} minutes")
    print(f"AGE WINDOW: posts younger than {MAX_AGE_MINUTES} minutes")

    for index, sub in enumerate(SUBREDDITS):
        cycle_start = time.monotonic()
        print(f"\n=== {index + 1}/{len(SUBREDDITS)}: r/{sub} ===")
        check_subreddit(sub, stats, seen)
        save_stats(stats)
        save_seen(seen)

        # Keep starts approximately one minute apart, while not delaying if a request itself took >1 minute.
        elapsed = time.monotonic() - cycle_start
        sleep_for = max(0, INTERVAL_SECONDS - elapsed)
        if index < len(SUBREDDITS) - 1:
            print(f"SLEEP: {sleep_for:.1f}s before next subreddit")
            time.sleep(sleep_for)

    print("\nCYCLE COMPLETE: all subreddits checked.")
    save_stats(stats)
    save_seen(seen)


if __name__ == "__main__":
    main()
