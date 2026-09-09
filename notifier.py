# notifier.py
import os, json, requests, feedparser
from datetime import datetime, timezone

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

SUBREDDITS = [
    "Forex", "ForexTraders", "Forexnoobs", "Daytrading", "RealDayTrading",
    "algotrading", "Trading", "PropFirm", "FTMO", "fundedtrader",
    "ForexFunding", "investing", "stocks", "SecurityAnalysis", "ValueInvesting",
    "personalfinance", "financialindependence", "passive_income", "FatFIRE",
    "SideProject", "Entrepreneur", "startups", "SaaS", "IndieHackers",
    "solopreneurs", "wallstreetbets", "options", "StockMarket", "fintech",
    "swingtrading", "SwingTradingForex", "PositionTrading", "Scalping",
    "ScalpingForex", "ForexScalping", "TechnicalAnalysis", "PriceAction",
    "RiskManagement", "Tradingstrategies", "Forexstrategy", "ForexAnalysis",
    "ForexSignals", "TradingPsychology", "TradingView", "ForexBrokers",
    "BrokerReviews", "MoneyManagement", "PortfolioManagement", "AssetManagement",
    "WealthManagement", "FinancialPlanning", "OptionsTrading", "OptionStrategies",
    "thetagang", "CoveredCalls", "WheelOptions", "CurrencyTrading", "FX",
    "Commodities", "Economics", "GlobalMarkets", "CryptoCurrency", "CryptoMarkets",
    "CryptoTrading", "CryptoTraders", "CryptoInvesting", "Defi", "Blockchain",
    "QuantTrading", "quantfinance", "EntrepreneurRideAlong", "juststart",
    "Beermoney", "passiveincome", "FIRE", "LeanFIRE", "ChubbyFIRE",
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

MAX_AGE_MINUTES = 15

STATS_FILE = "stats.json"

HEADERS = {"User-Agent": "reddit-keyword-notifier/1.0 (by u/your_username)"}

def load_stats():
    stats = {s: False for s in SUBREDDITS}  # auto-creates all subs
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE) as f:
            stats.update(json.load(f))
    return stats

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

def test_keyword_matcher():
    # Diagnostic only: does not send Telegram messages or affect the real watchlist.
    test_title = "Daily General Discussion and Advice Thread - September 09, 2026"
    test_keyword = "general"
    result = test_keyword in test_title.lower()
    print(f"MATCHER TEST: title={test_title!r}")
    print(f"MATCHER TEST: keyword={test_keyword!r} -> {result}")
    print(f"MATCHER TEST: uppercase keyword='GENERAL' -> {'GENERAL'.lower() in test_title.lower()}")
    print(f"MATCHER TEST: matches(title) with current KEYWORDS -> {matches(test_title)}")

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
    test_keyword_matcher()
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
