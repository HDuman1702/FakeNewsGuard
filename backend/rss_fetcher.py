import feedparser
from rss_sources import RSS_SOURCES

def fetch_latest_urls(limit_per_source=3):
    urls = []

    for name, feed_url in RSS_SOURCES.items():
        feed = feedparser.parse(feed_url)
        for entry in feed.entries[:limit_per_source]:
            if "link" in entry:
                urls.append(entry.link)

    return urls