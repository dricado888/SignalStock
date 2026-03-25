"""Generate preview.html with sample data for visual testing."""
from datetime import datetime
from email_template import build_html

SAMPLES = [
    dict(
        ticker="TSLA",
        company_name="Tesla, Inc.",
        event_type="product_launch",
        sentiment="positive",
        article_title="Lucid Announces Cosmos And Earth EVs To Battle Tesla Model Y - InsideEVs",
        article_url="https://www.insideevs.com/news/example-article",
        published_at=datetime(2026, 3, 13, 23, 17),
        source="InsideEVs",
    ),
    dict(
        ticker="NVDA",
        company_name="Nvidia Corporation",
        event_type="regulatory_action",
        sentiment="negative",
        article_title="US Moves to Restrict Nvidia Chip Exports to China Amid Escalating Tech War",
        article_url="https://www.reuters.com/technology/example",
        published_at=datetime(2026, 3, 14, 9, 45),
        source="Reuters",
    ),
    dict(
        ticker="AAPL",
        company_name="Apple Inc.",
        event_type="earnings_report",
        sentiment="neutral",
        article_title="Apple Reports Q1 2026 Earnings: Revenue In Line With Expectations",
        article_url="https://finance.yahoo.com/news/apple-q1-2026",
        published_at=datetime(2026, 3, 15, 14, 0),
        source="Yahoo Finance",
    ),
]

html_parts = []
for s in SAMPLES:
    html_parts.append(build_html(**s))

# Wrap all three in a single page for comparison
combined = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>body{{background:#d0d7e3;padding:20px}}</style>
</head><body>
{'<div style="margin-bottom:40px">'.join(html_parts)}
</body></html>"""

with open("preview.html", "w", encoding="utf-8") as f:
    f.write(combined)

print("preview.html written")
