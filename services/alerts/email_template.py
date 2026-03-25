"""
Email template helpers for SignalStock alert emails.
"""

from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# Event type -> human-readable display name
# ---------------------------------------------------------------------------
EVENT_TYPE_DISPLAY: dict[str, str] = {
    "earnings_report":    "Earnings Report",
    "merger_acquisition": "Merger & Acquisition",
    "product_launch":     "Product Launch",
    "regulatory_action":  "Regulatory Action",
    "executive_change":   "Executive Change",
    "lawsuit":            "Lawsuit",
    "partnership":        "Partnership",
    "other":              "Market News",
}

# Sentiment -> subject emoji
_SENTIMENT_EMOJI: dict[str, str] = {
    "positive": "\U0001f7e2",  # green circle
    "negative": "\U0001f534",  # red circle
    "neutral":  "\U0001f7e1",  # yellow circle
}

_SENTIMENT_LABEL: dict[str, str] = {
    "positive": "Bullish",
    "negative": "Bearish",
    "neutral":  "Neutral",
}

# Top accent bar gradient changes per sentiment
_SENTIMENT_GRADIENT: dict[str, str] = {
    "positive": "linear-gradient(90deg,#10b981 0%,#34d399 60%,#06b6d4 100%)",
    "negative": "linear-gradient(90deg,#ef4444 0%,#f97316 60%,#eab308 100%)",
    "neutral":  "linear-gradient(90deg,#6366f1 0%,#3b82f6 50%,#06b6d4 100%)",
}

# ---------------------------------------------------------------------------
# HTML template  (CSS braces escaped as {{ / }} for .format())
# ---------------------------------------------------------------------------
_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica,
                 Arial, sans-serif;
    background: #eef2f7;
    color: #1e293b;
    -webkit-font-smoothing: antialiased;
  }}
  .wrap {{
    max-width: 600px;
    margin: 36px auto;
    border-radius: 14px;
    overflow: hidden;
    box-shadow: 0 8px 32px rgba(0,0,0,0.14);
  }}

  /* ── gradient accent bar (colour set inline per-email via sentiment) ── */
  .topbar {{ height: 5px; }}

  /* ── header ── */
  .header {{
    background: #0f172a;
    padding: 18px 30px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }}
  .brand {{ color: #f8fafc; font-size: 14px; font-weight: 700;
            letter-spacing: 1.2px; text-transform: uppercase; }}
  .brand-sub {{ color: #475569; font-size: 10px; margin-top: 2px;
                letter-spacing: 0.5px; text-transform: uppercase; }}
  .alert-pill {{
    background: #1e293b;
    border: 1px solid #334155;
    color: #64748b;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    padding: 4px 10px;
    border-radius: 20px;
  }}

  /* ── hero (dark, ticker) ── */
  .hero {{
    background: #0f172a;
    padding: 28px 30px 30px;
    border-bottom: 1px solid #1e293b;
  }}
  .ticker {{
    font-size: 52px;
    font-weight: 800;
    color: #f8fafc;
    letter-spacing: -2px;
    line-height: 1;
    margin-bottom: 4px;
  }}
  .company {{
    font-size: 13px;
    color: #64748b;
    font-weight: 500;
    margin-bottom: 22px;
    letter-spacing: 0.2px;
  }}
  .chips {{ display: flex; gap: 8px; flex-wrap: wrap; }}
  .chip {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    font-weight: 700;
    padding: 5px 13px;
    border-radius: 20px;
    letter-spacing: 0.3px;
    text-transform: uppercase;
  }}
  .chip-event {{
    background: rgba(99,102,241,0.15);
    color: #a5b4fc;
    border: 1px solid rgba(99,102,241,0.3);
  }}
  .chip-positive {{
    background: rgba(16,185,129,0.15);
    color: #6ee7b7;
    border: 1px solid rgba(16,185,129,0.3);
  }}
  .chip-negative {{
    background: rgba(239,68,68,0.15);
    color: #fca5a5;
    border: 1px solid rgba(239,68,68,0.3);
  }}
  .chip-neutral {{
    background: rgba(245,158,11,0.15);
    color: #fde68a;
    border: 1px solid rgba(245,158,11,0.3);
  }}
  .dot {{
    width: 7px; height: 7px;
    border-radius: 50%;
    display: inline-block;
    flex-shrink: 0;
  }}
  .dot-positive {{ background: #10b981; box-shadow: 0 0 5px rgba(16,185,129,0.7); }}
  .dot-negative {{ background: #ef4444; box-shadow: 0 0 5px rgba(239,68,68,0.7); }}
  .dot-neutral  {{ background: #f59e0b; box-shadow: 0 0 5px rgba(245,158,11,0.7); }}

  /* ── body ── */
  .body {{ background: #ffffff; padding: 30px; }}

  .section-label {{
    font-size: 9px;
    font-weight: 700;
    color: #94a3b8;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 14px;
  }}

  /* article card — border-left-color set via inline style per-email */
  .article-card {{
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-left: 4px solid #6366f1;
    border-radius: 0 10px 10px 0;
    padding: 20px 20px;
    margin-bottom: 28px;
  }}
  .article-title {{
    font-size: 17px;
    font-weight: 700;
    color: #0f172a;
    line-height: 1.55;
    margin-bottom: 12px;
  }}
  .article-meta {{
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
  }}
  .source-badge {{
    background: #e2e8f0;
    color: #475569;
    font-size: 9px;
    font-weight: 800;
    letter-spacing: 1px;
    text-transform: uppercase;
    padding: 3px 9px;
    border-radius: 4px;
  }}
  .pub-date {{ font-size: 12px; color: #94a3b8; }}

  /* CTA */
  .cta {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: #6366f1;
    color: #ffffff !important;
    text-decoration: none;
    padding: 13px 22px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.3px;
  }}

  /* divider */
  .divider {{ border: none; border-top: 1px solid #f1f5f9; margin: 26px 0; }}

  /* ── footer ── */
  .footer {{
    background: #f8fafc;
    border-top: 1px solid #e2e8f0;
    padding: 18px 30px;
    text-align: center;
  }}
  .footer p {{ font-size: 11px; color: #94a3b8; line-height: 1.7; }}
  .footer strong {{ color: #64748b; font-weight: 600; }}
  .footer a {{ color: #94a3b8; text-decoration: underline; }}
</style>
</head>
<body>
<div class="wrap">

  <div class="topbar" style="background:{topbar_gradient}"></div>

  <div class="header">
    <div>
      <div class="brand">SignalStock</div>
      <div class="brand-sub">Market Intelligence</div>
    </div>
    <div class="alert-pill">Live Alert</div>
  </div>

  <div class="hero">
    <div class="ticker">{ticker}</div>
    <div class="company">{company_name}</div>
    <div class="chips">
      <span class="chip chip-event">{event_type_display}</span>
      <span class="chip chip-{sentiment}">
        <span class="dot dot-{sentiment}"></span>
        {sentiment_label}
      </span>
    </div>
  </div>

  <div class="body">
    <div class="section-label">Triggering Article</div>
    <div class="article-card" style="border-left-color:{accent_color}">
      <div class="article-title">{article_title}</div>
      <div class="article-meta">
        <span class="source-badge">{source}</span>
        <span class="pub-date">{published_at}</span>
      </div>
    </div>
    <a href="{article_url}" class="cta">Read Full Article &nbsp;&#8594;</a>
  </div>

  <div class="footer">
    <p>
      You received this because <strong>{ticker}</strong> is on your
      SignalStock watchlist.<br>
      <a href="{unsubscribe_url}">Unsubscribe</a>
      &nbsp;&middot;&nbsp;
      <a href="{manage_url}">Manage preferences</a>
      &nbsp;&middot;&nbsp;
      &copy; {year} SignalStock
    </p>
  </div>

</div>
</body>
</html>
"""


def _extract_source(url: str) -> str:
    """Extract a clean source label from an article URL."""
    try:
        netloc = urlparse(url).netloc.lower()
        netloc = netloc.replace("www.", "")
        # e.g. finance.yahoo.com -> yahoo, reuters.com -> reuters
        parts = netloc.split(".")
        return parts[-2].upper() if len(parts) >= 2 else netloc.upper()
    except Exception:
        return "SOURCE"


def build_subject(event_type: str, sentiment: str, ticker: str) -> str:
    """
    Build the email subject line.

    Args:
        event_type: Raw event type string (e.g. "earnings_report").
        sentiment:  "positive", "negative", or "neutral".
        ticker:     Stock ticker symbol.

    Returns:
        Formatted subject string.
    """
    emoji   = _SENTIMENT_EMOJI.get(sentiment, "\U0001f7e1")
    display = EVENT_TYPE_DISPLAY.get(event_type, "Market News")
    return f"{emoji} {display} alert for {ticker}"


def build_html(
    ticker: str,
    company_name: str,
    event_type: str,
    sentiment: str,
    article_title: str,
    article_url: str,
    published_at: Optional[datetime],
    source: Optional[str] = None,
    unsubscribe_url: str = "",
    manage_url: str = "",
) -> str:
    """
    Render the HTML email body.

    Args:
        ticker:        Stock ticker symbol.
        company_name:  Company display name.
        event_type:    Raw event type string.
        sentiment:     "positive", "negative", or "neutral".
        article_title: News article headline.
        article_url:   Link to the full article.
        published_at:  Article publication timestamp (or None).
        source:        News source name (extracted from URL if not provided).

    Returns:
        Rendered HTML string.
    """
    if published_at:
        pub_str = published_at.strftime("%b %d, %Y &middot; %H:%M UTC")
    else:
        pub_str = "Date unknown"

    source_label = source or _extract_source(article_url)

    # Accent colors per sentiment (used in CSS border and chip)
    _accent = {
        "positive": "#10b981",
        "negative": "#ef4444",
        "neutral":  "#6366f1",
    }

    return _HTML_TEMPLATE.format(
        ticker=ticker,
        company_name=company_name,
        event_type_display=EVENT_TYPE_DISPLAY.get(event_type, "Market News"),
        sentiment=sentiment,
        sentiment_label=_SENTIMENT_LABEL.get(sentiment, sentiment.capitalize()),
        article_title=article_title,
        article_url=article_url,
        published_at=pub_str,
        source=source_label,
        year=datetime.utcnow().year,
        topbar_gradient=_SENTIMENT_GRADIENT.get(sentiment, _SENTIMENT_GRADIENT["neutral"]),
        accent_color=_accent.get(sentiment, "#6366f1"),
        unsubscribe_url=unsubscribe_url,
        manage_url=manage_url,
    )
