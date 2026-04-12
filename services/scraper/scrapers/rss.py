"""
Free RSS feed scraper for financial news.

No API key required. No rate limits beyond polite scraping.
Runs every scrape cycle alongside Finlight and NewsAPI.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import feedparser

logger = logging.getLogger(__name__)

# Free, publicly accessible financial RSS feeds
RSS_FEEDS: list[tuple[str, str]] = [
    ("Yahoo Finance",    "https://finance.yahoo.com/news/rssindex"),
    ("Reuters Business", "https://feeds.reuters.com/reuters/businessNews"),
    ("CNBC Business",    "https://www.cnbc.com/id/10000664/device/rss/rss.html"),
    ("MarketWatch",      "https://feeds.marketwatch.com/marketwatch/topstories/"),
]


def _parse_published(entry) -> Optional[str]:
    """Convert feedparser's published_parsed struct_time → ISO 8601 string."""
    pt = getattr(entry, "published_parsed", None)
    if pt:
        try:
            return datetime(*pt[:6], tzinfo=timezone.utc).isoformat()
        except Exception:
            pass
    return None


def fetch_articles() -> list[dict]:
    """
    Fetch articles from all configured RSS feeds.

    Returns:
        List of article dicts: {title, content, url, source, published_at}
    """
    articles: list[dict] = []

    for source_name, url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            count = 0
            for entry in feed.entries:
                title = (entry.get("title") or "").strip()
                link  = (entry.get("link")  or "").strip()
                if not title or not link:
                    continue
                summary = entry.get("summary") or entry.get("description") or ""
                articles.append({
                    "title":        title,
                    "content":      summary,
                    "url":          link,
                    "source":       source_name,
                    "published_at": _parse_published(entry),
                })
                count += 1
            logger.info("RSS '%s': %d articles.", source_name, count)
        except Exception as exc:
            logger.error("RSS feed '%s' failed: %s", source_name, exc)

    return articles
