# SignalStock Stock Mapper

Polls PostgreSQL for classified events with no stock linkages, extracts ticker
symbols from each article, and writes rows to `stocks` + `event_stocks`.

## How It Works

```
Poll events WHERE NOT EXISTS event_stocks
        |
        v
  fetch title + content (JOIN articles)
        |
        v
  extract_tickers(title, content)
    ├── Step 1: Company name substring match   ("Apple" → AAPL)
    ├── Step 2: Explicit ticker regex           ("AAPL" in text → AAPL)
    └── Step 3: Fuzzy match on title phrases   ("Nvidia Corp" → NVDA)
        |
        v
  get_or_create stock row in stocks table
        |
        v
  INSERT event_stocks (event_id, stock_id)
        |
        v
  sleep POLL_INTERVAL if queue empty, else continue
```

## Ticker Extraction Strategy

### Step 1 — Company name matching (most reliable)

Checks `title + first 1000 chars of content` against the `COMPANY_TO_TICKER`
dict (~120 known companies). Case-insensitive substring match.

```
"Apple posts record revenue" → "Apple" found → AAPL
```

### Step 2 — Explicit ticker regex

Scans `title + first 3000 chars` for `\b[A-Z]{1,5}\b` patterns, excluding
~80 common non-ticker words (CEO, SEC, FDA, NYSE, etc.).

```
"AAPL surges after earnings" → AAPL
```

### Step 3 — Fuzzy company-name matching (title only)

Extracts capitalised phrases from the headline and fuzzy-matches (≥ 80%
similarity) against all company names in the mapping.

```
"Nvidia Corporation unveils new chip" → "Nvidia Corporation" fuzzy → NVDA
```

## Adding New Company Mappings

Edit `company_mapping.py` and add entries to `COMPANY_TO_TICKER`:

```python
"Palantir Technologies": "PLTR",
"Arm Holdings": "ARM",
```

`TICKER_TO_COMPANY` (used for the `company_name` column in `stocks`) is
auto-generated from `COMPANY_TO_TICKER` — no manual update needed.

## Setup

```bash
cd services/mapper
cp .env.example .env
# Edit .env if needed (DATABASE_URL is the only required setting)

pip install -r requirements.txt
```

## Running Locally

```bash
# Start postgres first
docker compose up -d postgres

# Run mapper (polls continuously)
python main.py
```

## Environment Variables

| Variable       | Default | Description                                     |
|----------------|---------|-------------------------------------------------|
| `DATABASE_URL` | —       | PostgreSQL connection string (required)         |
| `POLL_INTERVAL`| `30`    | Seconds to sleep when no unmapped events found  |
| `BATCH_SIZE`   | `10`    | Max events fetched per DB query                 |

## Verification Queries

```sql
-- How many event-stock links were created?
SELECT COUNT(*) FROM event_stocks;

-- Which stocks are most mentioned?
SELECT s.ticker, s.company_name, COUNT(*) AS event_count
FROM event_stocks es
JOIN stocks s ON es.stock_id = s.id
GROUP BY s.ticker, s.company_name
ORDER BY event_count DESC
LIMIT 20;

-- Which events mention AAPL?
SELECT e.id, e.event_type, e.sentiment, a.title
FROM event_stocks es
JOIN events e ON es.event_id = e.id
JOIN stocks s ON es.stock_id = s.id
JOIN articles a ON e.article_id = a.id
WHERE s.ticker = 'AAPL'
ORDER BY e.classified_at DESC;

-- Events not yet mapped (should shrink over time)
SELECT COUNT(*)
FROM events e
WHERE NOT EXISTS (
    SELECT 1 FROM event_stocks es WHERE es.event_id = e.id
);
```
