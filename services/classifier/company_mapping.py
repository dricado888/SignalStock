"""
Company name to stock ticker mapping.

COMPANY_TO_TICKER:  Maps known company names to their primary US ticker.
TICKER_TO_COMPANY:  Auto-generated reverse map (first name wins per ticker).
fuzzy_match():      Return ticker for a name that closely resembles a known entry.
"""

from typing import Optional

# ---------------------------------------------------------------------------
# Primary mapping: company name -> ticker
# ---------------------------------------------------------------------------
COMPANY_TO_TICKER: dict[str, str] = {
    # Mega-cap tech
    "Apple": "AAPL",
    "Microsoft": "MSFT",
    "Nvidia": "NVDA",
    "Amazon": "AMZN",
    "Google": "GOOGL",
    "Alphabet": "GOOGL",
    "Meta": "META",
    "Facebook": "META",
    "Tesla": "TSLA",
    "Broadcom": "AVGO",
    "Eli Lilly": "LLY",
    "TSMC": "TSM",
    "Taiwan Semiconductor": "TSM",
    "Netflix": "NFLX",
    "AMD": "AMD",
    "Advanced Micro Devices": "AMD",
    "Intel": "INTC",
    "Qualcomm": "QCOM",
    "Salesforce": "CRM",
    "Adobe": "ADBE",
    "Oracle": "ORCL",
    "Cisco": "CSCO",
    "ASML": "ASML",
    "Palo Alto Networks": "PANW",
    "CrowdStrike": "CRWD",
    "Fortinet": "FTNT",
    "ServiceNow": "NOW",
    "Workday": "WDAY",
    "Datadog": "DDOG",
    "MongoDB": "MDB",
    "Cloudflare": "NET",
    "Snowflake": "SNOW",
    "Palantir": "PLTR",
    "Twilio": "TWLO",
    "Shopify": "SHOP",
    "Spotify": "SPOT",
    "Zoom": "ZM",

    # Finance
    "JPMorgan": "JPM",
    "JP Morgan": "JPM",
    "JPMorgan Chase": "JPM",
    "Goldman Sachs": "GS",
    "Morgan Stanley": "MS",
    "Bank of America": "BAC",
    "Wells Fargo": "WFC",
    "Citigroup": "C",
    "Citi": "C",
    "American Express": "AXP",
    "Amex": "AXP",
    "Visa": "V",
    "Mastercard": "MA",
    "PayPal": "PYPL",
    "Robinhood": "HOOD",
    "Coinbase": "COIN",
    "Block": "SQ",
    "Square": "SQ",
    "Berkshire Hathaway": "BRK.B",

    # Healthcare & pharma
    "UnitedHealth": "UNH",
    "Johnson & Johnson": "JNJ",
    "J&J": "JNJ",
    "AbbVie": "ABBV",
    "Merck": "MRK",
    "Pfizer": "PFE",
    "Abbott": "ABT",
    "Thermo Fisher": "TMO",
    "AstraZeneca": "AZN",
    "Novo Nordisk": "NVO",
    "Roche": "RHHBY",
    "Moderna": "MRNA",
    "BioNTech": "BNTX",

    # Consumer & retail
    "Walmart": "WMT",
    "Home Depot": "HD",
    "Procter & Gamble": "PG",
    "P&G": "PG",
    "Nike": "NKE",
    "Starbucks": "SBUX",
    "McDonald's": "MCD",
    "Coca-Cola": "KO",
    "PepsiCo": "PEP",
    "Pepsi": "PEP",
    "Costco": "COST",
    "Target": "TGT",

    # Energy
    "Exxon": "XOM",
    "ExxonMobil": "XOM",
    "Chevron": "CVX",
    "Shell": "SHEL",
    "BP": "BP",
    "TotalEnergies": "TTE",

    # Industrial & auto
    "Boeing": "BA",
    "Ford": "F",
    "General Motors": "GM",
    "Rivian": "RIVN",
    "Lucid": "LCID",
    "Caterpillar": "CAT",
    "Deere": "DE",
    "John Deere": "DE",
    "3M": "MMM",
    "General Electric": "GE",
    "Honeywell": "HON",
    "Lockheed Martin": "LMT",
    "Raytheon": "RTX",
    "Northrop Grumman": "NOC",

    # Media & telecom
    "Disney": "DIS",
    "Walt Disney": "DIS",
    "Comcast": "CMCSA",
    "AT&T": "T",
    "Verizon": "VZ",
    "T-Mobile": "TMUS",

    # Transportation
    "Uber": "UBER",
    "Airbnb": "ABNB",
    "DoorDash": "DASH",
    "United Airlines": "UAL",
    "Delta": "DAL",
    "American Airlines": "AAL",
    "Southwest Airlines": "LUV",

    # International (US-listed)
    "Samsung": "SSNLF",
    "Sony": "SONY",
    "Toyota": "TM",
    "Honda": "HMC",
    "LVMH": "LVMUY",
}

# ---------------------------------------------------------------------------
# Auto-generated reverse map: ticker -> first company name in the dict
# ---------------------------------------------------------------------------
TICKER_TO_COMPANY: dict[str, str] = {}
for _company, _ticker in COMPANY_TO_TICKER.items():
    if _ticker not in TICKER_TO_COMPANY:
        TICKER_TO_COMPANY[_ticker] = _company


# ---------------------------------------------------------------------------
# Fuzzy matching
# ---------------------------------------------------------------------------
def fuzzy_match(company_name: str, threshold: int = 80) -> Optional[str]:
    """
    Return a ticker if company_name closely resembles a known company.

    Uses rapidfuzz WRatio scorer for robustness against minor typos or
    word-order differences (e.g. "NVIDIA Corporation" → "Nvidia").

    Args:
        company_name: Candidate name extracted from article text.
        threshold:    Minimum similarity score 0-100 (default 80).

    Returns:
        Ticker string, or None if no close match found.
    """
    if len(company_name) < 4:
        return None
    try:
        from rapidfuzz import process, fuzz
        result = process.extractOne(
            company_name,
            COMPANY_TO_TICKER.keys(),
            scorer=fuzz.WRatio,
        )
        if result and result[1] >= threshold:
            return COMPANY_TO_TICKER[result[0]]
    except ImportError:
        pass
    return None
