import asyncio

import feedparser
from urllib.parse import urlparse
import logging
log = logging.getLogger(__name__)
from db import SessionLocal
from analysis_service import analyze_and_store
from rss_sources import RSS_SOURCES
from scraper import parse_article


def is_valid_url(url: str) -> bool:
    if not url:
        return False
    p = urlparse(url)
    return p.scheme in ("http", "https") and bool(p.netloc)


async def run_rss_auto_analysis():
    print("RSS AUTO ANALYSIS START")

    db = SessionLocal()

    for name, feed_url in RSS_SOURCES.items():
        print(f"RSS FEED: {name}")

        try:
            feed = feedparser.parse(feed_url)
        except Exception as e:
            log.error(f"RSS FEED PARSE FEHLER ({name}): {e}")
            continue

        for entry in feed.entries:
            link = getattr(entry, "link", None)

            if not is_valid_url(link):
                log.warning(f"Ungültige URL übersprungen: {link}")
                continue

            try:
               analyze_and_store(link)

            except Exception as e:
                log.error(f"ANALYSE FEHLGESCHLAGEN FÜR {link}: {e}")
                continue

    db.close()
    print("RSS AUTO ANALYSIS END")

