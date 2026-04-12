"""
Stock ticker extraction from financial news article text.

Strategy (applied in order):
  1. Company name substring match against COMPANY_TO_TICKER (title + first 1000
     chars of content) — most reliable signal.
  2. Explicit ticker regex on title + first 3000 chars of content — catches
     tickers that are written in all-caps in the article (e.g. "AAPL surged").
  3. Fuzzy company-name match on capitalised phrases extracted from the title —
     catches minor name variations (e.g. "Nvidia Corp" → NVDA).
"""

import logging
import re
from typing import List

from company_mapping import COMPANY_TO_TICKER, fuzzy_match

logger = logging.getLogger(__name__)

# Split company patterns by specificity:
# - Single-word names (Apple, Zoom, Block) → title only to avoid body false positives
# - Multi-word names (Home Depot, Goldman Sachs) → title + content (specific enough)
_TITLE_ONLY_PATTERNS: list[tuple[re.Pattern, str]] = []
_CONTENT_PATTERNS:    list[tuple[re.Pattern, str]] = []

for _company, _ticker in COMPANY_TO_TICKER.items():
    _pat = re.compile(r"\b" + re.escape(_company) + r"\b", re.IGNORECASE)
    if " " in _company:
        _CONTENT_PATTERNS.append((_pat, _ticker))
    else:
        _TITLE_ONLY_PATTERNS.append((_pat, _ticker))

# ---------------------------------------------------------------------------
# Words that match the ticker regex but are NOT stock tickers
# ---------------------------------------------------------------------------
EXCLUDE_WORDS: set[str] = {
    # C-suite titles
    "CEO", "CFO", "COO", "CTO", "CDO", "CSO", "CIO", "CMO",
    # Regulatory / government
    "SEC", "FDA", "FTC", "DOJ", "FCC", "CFTC", "IRS", "FBI", "CIA", "NSA",
    "FED", "ECB", "IMF", "WTO", "WHO", "UN", "NATO", "EU", "US", "UK",
    # Exchanges & instruments
    "NYSE", "NASDAQ", "LSE", "TSX", "AMEX",
    "ETF", "IPO", "SPAC", "MBS", "CDO", "CLO", "REITs", "REIT",
    # Financial jargon
    "EPS", "GDP", "CPI", "PPI", "PCE", "NFP", "APR", "APY", "IRR", "NPV",
    "YTD", "YOY", "QOQ", "TTM", "EBIT", "EBITDA", "PE", "PB", "PS",
    "BUY", "SELL", "HOLD", "PUT", "CALL",
    "Q1", "Q2", "Q3", "Q4", "FY", "H1", "H2",
    # Currencies
    "USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "CNY", "INR",
    # Technology / industry buzzwords
    "AI", "ML", "IT", "API", "APP", "NET", "IoT",
    "EV", "TV", "PC", "PR", "HR", "IR", "VC", "PE",
    # Common English words that happen to be all caps in headlines
    "THE", "AND", "FOR", "ARE", "WAS", "HAS", "ITS", "BUT", "NOT",
    "WITH", "THIS", "THAT", "FROM", "WILL", "BEEN", "HAVE", "THEY",
    "WERE", "SAID", "MORE", "ALSO", "INTO", "THAN", "THEN", "WHEN",
    "WHAT", "JUST", "OVER", "SUCH", "BOTH", "EACH", "ONLY", "MOST",
    # Corporate suffixes
    "INC", "LLC", "LTD", "CORP", "CO", "PLC", "GROUP", "FUND",
    # Misc finance/news terms
    "NEWS", "NEW", "OLD", "TOP", "BIG", "HIGH", "LOW", "MAX", "MIN",
    "BETA", "ALPHA", "DELTA", "SIGMA",
    "DATA", "CLOUD", "TECH", "BANK", "ASSET", "BOND", "NOTE", "SWAP",
    "RATE", "RISK", "CASH", "DEBT", "LOAN", "LOSS", "GAIN", "PROFIT",
    "SHARE", "STOCK", "INDEX", "PRICE",
    # Abbreviations commonly ALL-CAPS in articles
    "PM", "AM", "EST", "GMT", "UTC",
    "CEO", "CFO", "MD", "COO",
    "CNBC", "CNN", "BBC", "FOX", "WSJ", "FT",
    # News wire agencies
    "AP", "AFP", "UPI", "REUTERS",
    # Airport / location codes that appear in travel/airline articles
    "ORD", "LAX", "SFO", "JFK", "LGA", "DFW", "ATL", "MIA", "SEA",
    "BOS", "DEN", "PHX", "LHR", "CDG", "NRT", "HKG",
    # Common abbreviations that look like tickers
    "LLC", "LTD", "INC", "CORP", "PLC", "CO", "LP",
    "OTC", "ADR", "ADS", "ESG", "DEI", "ROI", "ROE", "EPS",
    # Roman numerals (appear in "Phase II", "Series III", "Q4 FY2024" etc.)
    "I", "II", "III", "IV", "VI", "VII", "VIII", "IX", "XI", "XII",
    # Government agencies / space / non-stock bodies
    "NASA", "FEMA", "NOAA", "DARPA", "DOD", "DOE", "EPA",
    # Commodity benchmarks (not stocks)
    "WTI", "LNG", "LPG", "OPEC",
    # Radio stations / local abbreviations that slip through
    "KUT", "NPR", "PBS", "ABC", "NBC", "CBS",
    # Media company names that appear as source suffixes
    "FORTUNE", "FORBES", "WIRED", "AXIOS", "QUARTZ",
    # Other observed false positives
    "OF", "IN", "AT", "BY", "TO", "OR", "IF", "AS", "BE",
    "UP", "GO", "NO", "SO", "DO", "IS", "IT", "ON", "AN",
}

# Regex: 1-5 uppercase letters surrounded by word boundaries
TICKER_PATTERN = re.compile(r"\b([A-Z]{1,5})\b")

# Regex: capitalised words / phrases in title (potential company names)
CAPITALIZED_PHRASE_PATTERN = re.compile(
    r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b"
)


# Regex to strip news source suffix from titles: " - WSJ", " - Fortune", " - KUT" etc.
_SOURCE_SUFFIX = re.compile(r"\s*[-–]\s*[A-Za-z0-9 ]{1,30}$")


def _clean_title(title: str) -> str:
    """Strip trailing '- Source' attribution from article headlines."""
    return _SOURCE_SUFFIX.sub("", title).strip()


def extract_tickers(title: str, content: str) -> List[str]:
    """
    Extract unique stock ticker symbols from a financial news article.

    Args:
        title:   Article headline.
        content: Article body text.

    Returns:
        Sorted list of unique ticker strings (e.g. ["AAPL", "MSFT"]).
    """
    tickers: set[str] = set()
    clean_title = _clean_title(title)

    # ------------------------------------------------------------------
    # Step 1a: Single-word company names — title only
    # (prevents "zoom" in body → ZM, "shell" → SHEL, "target" → TGT etc.)
    # ------------------------------------------------------------------
    for pattern, ticker in _TITLE_ONLY_PATTERNS:
        if pattern.search(clean_title):
            tickers.add(ticker)
            logger.debug("Title company match: → %s", ticker)

    # ------------------------------------------------------------------
    # Step 1b: Multi-word company names — title + first 1000 chars content
    # (e.g. "Home Depot", "Goldman Sachs" — specific enough to be safe)
    # ------------------------------------------------------------------
    search_text = f"{clean_title} {(content or '')[:1000]}"
    for pattern, ticker in _CONTENT_PATTERNS:
        if pattern.search(search_text):
            tickers.add(ticker)
            logger.debug("Content company match: → %s", ticker)

    # ------------------------------------------------------------------
    # Step 2: Explicit ticker regex
    # Find ALL-CAPS words (2-5 chars) in clean title + first 3000 chars of content,
    # excluding known non-ticker words.
    # ------------------------------------------------------------------
    full_text = f"{clean_title} {(content or '')[:3000]}"
    for match in TICKER_PATTERN.finditer(full_text):
        word = match.group(1)
        if len(word) >= 2 and word not in EXCLUDE_WORDS:
            tickers.add(word)
            logger.debug("Regex ticker match: %s", word)

    # ------------------------------------------------------------------
    # Step 3: Fuzzy match on capitalised phrases from clean title
    # Only applies to the title (short, focused) to avoid false positives.
    # Minimum 7 chars prevents single words like "Home" matching "Home Depot".
    # ------------------------------------------------------------------
    for phrase in CAPITALIZED_PHRASE_PATTERN.findall(clean_title):
        if len(phrase) < 7:  # too short — avoids "Home" → HD false positives
            continue
        matched = fuzzy_match(phrase)
        if matched:
            tickers.add(matched)
            logger.debug("Fuzzy match: '%s' → %s", phrase, matched)

    result = sorted(tickers)
    if result:
        logger.debug("Tickers extracted: %s", result)
    return result
