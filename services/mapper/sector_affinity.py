"""
Sector Affinity Mapper
======================
Detects market sectors from article/tweet titles using keyword matching,
then maps each sector to a list of tickers that are *indirectly* affected.

Example: an energy-price tweet doesn't mention NVDA by name, but data
centres and AI chips are major energy consumers — so NVDA is indirectly
affected by energy market moves.

Usage:
    from sector_affinity import get_indirect_tickers

    tickers = get_indirect_tickers("Oil prices surge as OPEC cuts output")
    # → ['XOM', 'CVX', 'COP', 'PSX', 'OXY', 'NVDA', 'AMD']
"""

# ---------------------------------------------------------------------------
# Sector keyword detection
# ---------------------------------------------------------------------------
# Mirrors the frontend getSectorHints() logic in formatters.js so that
# backend and frontend classifications stay in sync.

SECTOR_KEYWORDS: dict[str, list[str]] = {
    "DEFENSE": [
        "war", "military", "nato", "defense", "defence",
        "pentagon", "arms", "weapon", "missile", "troops",
        "combat", "warfare", "airstrike", "sanctions",
    ],
    "ENERGY": [
        "oil", "gas", "energy", "solar", "wind", "nuclear",
        "opec", "crude", "pipeline", "lng", "refinery",
        "electricity", "power grid", "coal", "petroleum",
    ],
    "FINANCE": [
        "rate hike", "inflation", "federal reserve", "fed ", "mortgage",
        "bond yield", "treasury", "interest rate", "lending rate", " banking",
        "recession", "gdp", "monetary policy", "yield curve",
        "credit rating", "debt ceiling", "cpi", "central bank",
    ],
    "TECH": [
        "chip", "semiconductor", " ai ", "artificial intelligence",
        "software", "cloud", "cyber", "data center", "quantum",
        "gpu", "processor", "silicon", "foundry", "microchip",
    ],
    "HEALTH": [
        "fda", " drug ", "pharma", "vaccine", "clinical",
        "biotech", "medicare", "medicaid", "hospital",
        "clinical trial", "approval", "pandemic", "disease",
    ],
    "RETAIL": [
        "retail store", "e-commerce", "brick and mortar",
        "consumer staples", "grocery", "merchandise",
        "department store", "online shopping", "shopify",
        "walmart", "amazon", "target", "costco", "retail sales",
        "foot traffic", "same-store sales",
    ],
}

# ---------------------------------------------------------------------------
# Sector → indirectly affected tickers
# ---------------------------------------------------------------------------
# These are only linked if the ticker already exists in the stocks table.
# Do NOT auto-create stocks for indirect matches.

SECTOR_TO_TICKERS: dict[str, list[str]] = {
    "DEFENSE": ["RTX", "LMT", "NOC", "GD", "BA", "HII"],
    "ENERGY":  [
        "XOM", "CVX", "COP", "PSX", "OXY",   # energy producers
        "NVDA", "AMD", "TSM",                  # chip/AI: large energy consumers
    ],
    "FINANCE": ["JPM", "GS", "BAC", "WFC", "MS", "BLK", "V", "MA", "C"],
    "TECH":    ["NVDA", "AMD", "INTC", "TSM", "MSFT", "AAPL", "GOOGL", "META", "AMZN"],
    "HEALTH":  ["JNJ", "PFE", "MRK", "UNH", "ABBV", "LLY", "AMGN", "MRNA"],
    "RETAIL":  ["AMZN", "WMT", "TGT", "COST", "HD", "NKE", "SBUX"],
}


def get_sectors(title: str) -> list[str]:
    """
    Return up to 2 matching sector labels for a title string.

    Uses simple substring matching (case-insensitive). Matches are returned
    in SECTOR_KEYWORDS definition order; only the first 2 are kept to avoid
    over-tagging.

    Args:
        title: Article title or tweet text.

    Returns:
        List of sector label strings, e.g. ['ENERGY', 'TECH'].
    """
    if not title:
        return []
    lower = f" {title.lower()} "
    return [
        sector
        for sector, keywords in SECTOR_KEYWORDS.items()
        if any(kw in lower for kw in keywords)
    ][:2]


def get_indirect_tickers(title: str) -> list[str]:
    """
    Return tickers indirectly affected by sectors detected in title.

    Deduplicates preserving order (first sector's tickers come first).
    Only returns tickers that appear in SECTOR_TO_TICKERS; callers are
    responsible for checking which of these actually exist in the DB.

    Args:
        title: Article title or tweet text.

    Returns:
        Ordered, deduplicated list of ticker strings.
    """
    seen: dict[str, None] = {}  # ordered set via dict keys
    for sector in get_sectors(title):
        for ticker in SECTOR_TO_TICKERS.get(sector, []):
            seen[ticker] = None
    return list(seen)
