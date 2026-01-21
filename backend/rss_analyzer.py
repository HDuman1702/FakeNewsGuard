import asyncio
import feedparser
from urllib.parse import urlparse

from db import SessionLocal
from analysis_service import analyze_and_store
from rss_sources import RSS_SOURCES


def is_valid_url(url: str) -> bool:
    if not url:
        return False
    p = urlparse(url)
    return p.scheme in ("http", "https") and bool(p.netloc)


async def run_rss_auto_analysis():
    print("RSS AUTO ANALYSIS START")

    db = SessionLocal()
    try:
        for name, feed_url in RSS_SOURCES.items():
            print(f"RSS FEED: {name}")

            feed = feedparser.parse(feed_url)

            for entry in feed.entries[:5]:
                url = entry.get("link")

                if not is_valid_url(url):
                    print(f"RSS übersprungen (ungültige URL): {url}")
                    continue

                try:
                    await analyze_and_store(url, db)
                    print(f"RSS ANALYSE OK: {entry.get('title')}")
                except Exception as e:
                    print(f"RSS FEHLER bei {url}: {e}")

    finally:
        db.close()
        print("RSS AUTO ANALYSIS END")
