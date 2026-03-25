"""
Quick tests for ticker_extractor and company_mapping.
Run: python test_mapper.py
No external test framework needed.
"""

import sys
from ticker_extractor import extract_tickers
from company_mapping import fuzzy_match, COMPANY_TO_TICKER, TICKER_TO_COMPANY

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
failures = 0
total_tests = 0


def check(label: str, result, expected):
    global failures, total_tests
    total_tests += 1
    # For list comparison, order-insensitive
    if isinstance(expected, list):
        ok = sorted(result) == sorted(expected)
    elif isinstance(expected, set):
        ok = set(result) == expected
    else:
        ok = result == expected

    status = PASS if ok else FAIL
    print(f"  [{status}] {label}")
    if not ok:
        print(f"          expected: {expected}")
        print(f"          got:      {result}")
        failures += 1


def section(title: str):
    print(f"\n{'='*55}")
    print(f"  {title}")
    print(f"{'='*55}")


# ---------------------------------------------------------------------------
# company_mapping: TICKER_TO_COMPANY reverse map
# ---------------------------------------------------------------------------
section("TICKER_TO_COMPANY reverse map")

check("AAPL -> Apple",   TICKER_TO_COMPANY.get("AAPL"), "Apple")
check("MSFT -> Microsoft", TICKER_TO_COMPANY.get("MSFT"), "Microsoft")
check("NVDA -> Nvidia",  TICKER_TO_COMPANY.get("NVDA"), "Nvidia")
check("TSLA -> Tesla",   TICKER_TO_COMPANY.get("TSLA"), "Tesla")
check("META -> Meta",    TICKER_TO_COMPANY.get("META"), "Meta")
check("GOOGL -> Google", TICKER_TO_COMPANY.get("GOOGL"), "Google")


# ---------------------------------------------------------------------------
# fuzzy_match
# ---------------------------------------------------------------------------
section("fuzzy_match()")

check("Exact match 'Apple'",           fuzzy_match("Apple"),              "AAPL")
check("Exact match 'Microsoft'",       fuzzy_match("Microsoft"),          "MSFT")
check("Nvidia variant 'Nvidia Corp'",  fuzzy_match("Nvidia Corp"),        "NVDA")
check("Tesla variant 'Tesla Motors'",  fuzzy_match("Tesla Motors"),       "TSLA")
check("Amazon variant 'Amazon.com'",   fuzzy_match("Amazon.com"),         "AMZN")
check("Too short -> None",              fuzzy_match("AI"),                  None)
check("Garbage -> None",                fuzzy_match("Zxqwerty"),            None)
check("Low similarity -> None",         fuzzy_match("Random Corp"),         None)


# ---------------------------------------------------------------------------
# extract_tickers: step 1 — company name substring match
# ---------------------------------------------------------------------------
section("extract_tickers() — company name match")

check(
    "Apple in title",
    extract_tickers("Apple reports record quarterly revenue", ""),
    ["AAPL"],
)
check(
    "Nvidia in title",
    extract_tickers("Nvidia unveils next-gen AI chip architecture", ""),
    ["NVDA"],
)
check(
    "Multiple companies in title",
    extract_tickers("Tesla and Ford race to dominate EV market", ""),
    ["F", "TSLA"],
)
check(
    "Company in content only",
    extract_tickers(
        "Tech sector update",
        "Microsoft announced a major deal with JPMorgan today.",
    ),
    ["JPM", "MSFT"],
)
check(
    "Case-insensitive: lowercase company name",
    extract_tickers("apple shares fall after earnings miss", ""),
    ["AAPL"],
)


# ---------------------------------------------------------------------------
# extract_tickers: step 2 — explicit ticker regex
# ---------------------------------------------------------------------------
section("extract_tickers() — explicit ticker regex")

check(
    "Explicit AAPL in title",
    extract_tickers("AAPL surges 5% after earnings beat", ""),
    ["AAPL"],
)
check(
    "Explicit NVDA and AMD in title",
    extract_tickers("NVDA and AMD battle for data center market share", ""),
    ["AMD", "NVDA"],
)
check(
    "Explicit ticker in content",
    extract_tickers(
        "Chip sector news",
        "Analysts upgraded INTC citing improved margins.",
    ),
    ["INTC"],
)


# ---------------------------------------------------------------------------
# extract_tickers: excluded words (false-positive prevention)
# ---------------------------------------------------------------------------
section("extract_tickers() — excluded words must NOT appear")

result_ap = extract_tickers("AP reports on Iran conflict affecting markets", "")
check("'AP' excluded", "AP" not in result_ap, True)

result_ord = extract_tickers(
    "Southwest Airlines cancels flights at ORD due to weather", ""
)
check("'ORD' excluded", "ORD" not in result_ord, True)
check("'LUV' kept (Southwest ticker)", "LUV" in result_ord, True)

result_noise = extract_tickers(
    "CEO and CFO of major BANK face SEC probe over IPO", ""
)
for word in ["CEO", "CFO", "SEC", "IPO", "BANK"]:
    check(f"'{word}' excluded", word not in result_noise, True)

result_macro = extract_tickers(
    "GDP growth slows as CPI rises; FED holds rates", ""
)
for word in ["GDP", "CPI", "FED"]:
    check(f"'{word}' excluded", word not in result_macro, True)

result_airports = extract_tickers(
    "Delta delays flights at LAX, JFK, and SFO", ""
)
for code in ["LAX", "JFK", "SFO"]:
    check(f"'{code}' excluded", code not in result_airports, True)
check("DAL (Delta) kept", "DAL" in result_airports, True)


# ---------------------------------------------------------------------------
# extract_tickers: step 3 — fuzzy match on title phrases
# ---------------------------------------------------------------------------
section("extract_tickers() — fuzzy match on title phrases")

check(
    "Fuzzy: 'Nvidia Corporation' -> NVDA",
    extract_tickers("Nvidia Corporation reports blowout quarter", ""),
    ["NVDA"],
)
check(
    "Fuzzy: 'Walt Disney' -> DIS",
    extract_tickers("Walt Disney streaming subscribers fall short", ""),
    ["DIS"],
)


# ---------------------------------------------------------------------------
# extract_tickers: edge cases
# ---------------------------------------------------------------------------
section("extract_tickers() — edge cases")

check("Empty title and content", extract_tickers("", ""), [])
check("Only numbers and punctuation", extract_tickers("123 456 789!", ""), [])
check(
    "No financial content",
    extract_tickers("The weather is nice today in Paris", ""),
    [],
)
check(
    "Duplicate tickers deduplicated",
    # "Apple" in title + "AAPL" explicit + "Apple" in content = still just AAPL
    extract_tickers("Apple (AAPL) hits all-time high", "Apple stock surges."),
    ["AAPL"],
)
check(
    "Multiple tickers from real-looking headline",
    extract_tickers(
        "Amazon and Microsoft cloud rivalry intensifies as Google enters AI race",
        "",
    ),
    ["AMZN", "GOOGL", "MSFT"],
)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print(f"\n{'='*55}")
if failures == 0:
    print(f"  \033[92mAll {total_tests} tests passed.\033[0m")
else:
    print(f"  \033[91m{failures}/{total_tests} test(s) FAILED.\033[0m")
print(f"{'='*55}\n")

sys.exit(failures)
