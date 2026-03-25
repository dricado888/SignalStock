# SignalStock News Scraper

Fetches financial news from [Finlight.me](https://finlight.me/) and [NewsAPI](https://newsapi.org/), deduplicates by URL, stores articles in PostgreSQL, and pushes article IDs to a Redis queue for downstream event classification.

## How It Works

```
  ┌─────────────┐     ┌─────────────┐
  │  Finlight   │     │   NewsAPI   │
  └──────┬──────┘     └──────┬──────┘
         │  fetch articles   │
         └────────┬──────────┘
                  ▼
         deduplicate by URL
                  │
         ┌────────▼────────┐
         │   PostgreSQL    │  INSERT INTO articles
         │  articles table │
         └────────┬────────┘
                  │  new article IDs
         ┌────────▼────────┐
         │     Redis       │  LPUSH articles:pending <id>
         │  articles:pending│
         └─────────────────┘
                  │
         (classifier service picks up IDs)
```

## Getting API Keys

### Finlight.me
1. Sign up at [finlight.me](https://finlight.me/)
2. Navigate to **API Keys** in your dashboard
3. Free tier: **10,000 requests/month**

### NewsAPI
1. Sign up at [newsapi.org](https://newsapi.org/)
2. Your API key is shown immediately after registration
3. Free (Developer) tier: **100 requests/day**
   > Note: The free tier restricts `top-headlines` to English sources and has a 1-month article lookback limit.

## Setup

```bash
cd services/scraper

# Copy and fill in your API keys
cp .env.example .env
# Edit .env with real keys

# Install dependencies (local development)
pip install -r requirements.txt
```

## Running Locally

Requires PostgreSQL and Redis to be running. Start them with docker-compose from the project root:

```bash
# From project root
docker compose up -d postgres redis

# From services/scraper/
python main.py
```

## Running via Docker Compose

Add this service block to the root `docker-compose.yml`:

```yaml
  scraper:
    build: ./services/scraper
    env_file: ./services/scraper/.env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
```

Then:
```bash
docker compose up -d scraper
docker compose logs -f scraper
```

## Configuration

All config is via environment variables (`.env` file or container env):

| Variable | Default | Description |
|---|---|---|
| `FINLIGHT_API_KEY` | — | **Required.** Finlight API key |
| `NEWSAPI_KEY` | — | **Required.** NewsAPI key |
| `DATABASE_URL` | — | **Required.** PostgreSQL DSN |
| `REDIS_URL` | `redis://localhost:6379` | Redis URL |
| `POLL_INTERVAL_SECONDS` | `300` | Seconds between scrape cycles |

## Rate Limiting

Usage is tracked in Redis, keyed by date:

| Source | Limit | Tracked key |
|---|---|---|
| Finlight | 300 req/day (of 333 budget) | `rate_limit:finlight:YYYY-MM-DD` |
| NewsAPI | 90 req/day (of 100 limit) | `rate_limit:newsapi:YYYY-MM-DD` |

Keys expire automatically at midnight UTC.

Check current usage:
```bash
docker exec signalstock-redis redis-cli keys "rate_limit:*"
docker exec signalstock-redis redis-cli get "rate_limit:finlight:$(date -u +%Y-%m-%d)"
docker exec signalstock-redis redis-cli get "rate_limit:newsapi:$(date -u +%Y-%m-%d)"
```
