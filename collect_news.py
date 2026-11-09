
import csv
import feedparser
import re
import requests
from html import unescape
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit


# News feeds grouped by source and category
FEEDS = {
    "Guardian - UK News": "https://www.theguardian.com/uk/rss",
    "Guardian - World": "https://www.theguardian.com/world/rss",
    "Guardian - Science": "https://www.theguardian.com/science/rss",
    "Guardian - Environment": "https://www.theguardian.com/uk/environment/rss",
    "Guardian - Technology": "https://www.theguardian.com/uk/technology/rss",
    "Guardian - Society": "https://www.theguardian.com/society/rss",
    "Guardian - Global Development": "https://www.theguardian.com/global-development/rss",

    "ScienceDaily - Health": "https://www.sciencedaily.com/rss/top/health.xml",
    "ScienceDaily - Environment": "https://www.sciencedaily.com/rss/top/environment.xml",
    "ScienceDaily - Technology": "https://www.sciencedaily.com/rss/top/technology.xml",
    "ScienceDaily - Science": "https://www.sciencedaily.com/rss/top/science.xml",
    "ScienceDaily - Society": "https://www.sciencedaily.com/rss/top/society.xml",

    "Phys.org - Science": "https://phys.org/rss-feed/breaking/",
    "Nature - Science": "https://www.nature.com/nature.rss",

}



def clean_description(text):
    """Remove HTML and keep a short description."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    text = " ".join(text.split())
    return text[:300]


articles = []
seen_urls = set()
total_fetched = 0

for category, feed_url in FEEDS.items():
    print(f"\nFetching {category}...")

    
    
    try:
        if category.startswith("Nature -"):
            # Nature works when parsed from downloaded bytes
            response = requests.get(feed_url, timeout=20)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
        else:
            # Use the original method for other publishers
            feed = feedparser.parse(feed_url)

    except requests.RequestException as error:
        print(f"Could not download feed: {error}")
        continue


    if feed.bozo and not feed.entries:
        print(f"Could not read feed: {feed.bozo_exception}")
        continue

    print(f"Found {len(feed.entries)} articles")
    total_fetched += len(feed.entries)

    added = 0

    for entry in feed.entries:
        url = entry.get("link", "").strip()

        if not url:
            continue

    
        # Prioritise original Nature research
        if category.startswith("Nature -"):
            title = entry.get("title", "").lower()

            if "/articles/s41586-" not in url:
                continue

            if title.startswith((
                "author correction:",
                "publisher correction:",
                "retraction:",
            )):
                continue

        # Remove tracking parameters from URLs
        parsed = urlsplit(url)
        clean_url = urlunsplit((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip("/"),
            "",
            ""
        ))

        if clean_url in seen_urls:
            continue

        seen_urls.add(clean_url)

        articles.append({
            "source": category.split(" - ", 1)[0],
            "category": category.split(" - ", 1)[1],
            "title": entry.get("title", ""),
            "description": clean_description(
                entry.get("summary", "")
            ),
            "published": entry.get("published", ""),
            "url": clean_url,
            "collected_at": datetime.now(
                timezone.utc
            ).isoformat()
        })

        added += 1

    print(f"Added {added} unique articles")


# Export to CSV
filename = "news.csv"

fields = [
    "source",
    "category",
    "title",
    "description",
    "published",
    "url",
    "collected_at"
]

with open(filename, "w", newline="", encoding="utf-8-sig") as file:
    writer = csv.DictWriter(file, fieldnames=fields)
    writer.writeheader()
    writer.writerows(articles)

print("\n------------------------------")
print(f"Total articles fetched: {total_fetched}")
print(f"Unique articles saved: {len(articles)}")
print(f"Duplicates removed: {total_fetched - len(articles)}")
print(f"Output file: {filename}")
print("------------------------------")
