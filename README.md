# SignalStock

Real-time stock event detection platform. Scrapes financial news every 5 minutes, classifies it with an LLM, maps events to affected stocks, and sends personalized email alerts — built entirely on free-tier services.

![Architecture](https://img.shields.io/badge/stack-Python%20%7C%20React%20%7C%20PostgreSQL%20%7C%20Redis%20%7C%20Docker-blue)
![Cost](https://img.shields.io/badge/infrastructure%20cost-%240-brightgreen)

---

## What It Does

1. **Scrapes** financial news from Finlight, NewsAPI, and Twitter/X (via Apify) every 5 minutes
2. **Classifies** each article using Groq's LLM API (llama-3.1-8b-instant) — event type, sentiment, confidence
3. **Maps** events to affected stocks using ticker regex, company name fuzzy matching, and sector affinity
4. **Alerts** users via email when watchlisted stocks appear in new events, filtered by their preferences

---

## Architecture

```
Finlight / NewsAPI / Twitter (Apify)
           │
           ▼
        Scraper ──► Redis Queue ──► Classifier ──► PostgreSQL
                                                       │
                                                  Stock Mapper
                                                       │
                                              Alert Engine ──► SendGrid ──► Email
                                                       │
                                              FastAPI (port 8000)
                                                       │
                                              React Dashboard (port 5173)
                                                       │
                                              Finnhub API (live prices)
```

### 8-Container Docker Stack

| Container    | Role                                          |
|-------------|-----------------------------------------------|
| `postgres`  | Primary data store (8 tables)                 |
| `redis`     | Article queue + price cache                   |
| `scraper`   | Polls news APIs + Twitter every 5 min         |
| `classifier`| Dequeues articles, calls Groq LLM             |
| `mapper`    | Links classified events to affected stocks    |
| `alerts`    | Monitors watchlists, sends email alerts       |
| `api`       | FastAPI REST gateway                          |
| `frontend`  | Vite + React dashboard                        |

---

## Tech Stack

| Layer        | Technology                                        |
|-------------|---------------------------------------------------|
| Frontend    | React 18, Vite, Tailwind CSS, Framer Motion       |
| API         | FastAPI (Python), JWT auth, Redis cache           |
| Scraper     | Python, Apify (Twitter), Finlight, NewsAPI        |
| Classifier  | Python, Groq API (llama-3.1-8b-instant)           |
| Stock Mapper| Python, regex, rapidfuzz, sector affinity         |
| Alert Engine| Python, SendGrid, HTML email templates            |
| Database    | PostgreSQL 15 (normalized schema, 8 tables)       |
| Queue/Cache | Redis 7 (LIST queue + TTL cache)                  |
| Infra       | Docker Compose, health checks                     |

---

## Quick Start

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Git](https://git-scm.com/)

### 1. Clone

```bash
git clone https://github.com/dricado888/SignalStock.git
cd SignalStock
```

### 2. Configure API keys

Copy the example env files for each service:

```bash
cp services/scraper/.env.example    services/scraper/.env
cp services/classifier/.env.example services/classifier/.env
cp services/mapper/.env.example     services/mapper/.env
cp services/alerts/.env.example     services/alerts/.env
cp services/api/.env.example        services/api/.env
```

Edit each `.env` file and fill in your keys (all free tier):

| Key | Service | Free Tier |
|-----|---------|-----------|
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) | 14,400 req/day, no credit card |
| `FINNHUB_API_KEY` | [finnhub.io](https://finnhub.io) | 60 req/min |
| `FINLIGHT_API_KEY` | [finlight.me](https://finlight.me) | 10K req/month |
| `NEWSAPI_KEY` | [newsapi.org](https://newsapi.org) | 100 req/day |
| `APIFY_API_TOKEN` | [apify.com](https://apify.com) | Optional — leave blank to skip Twitter |
| `SENDGRID_API_KEY` | [sendgrid.com](https://sendgrid.com) | 100 emails/day |

### 3. Run

```bash
docker compose up -d
```

The database schema is applied automatically on first start.

- Dashboard: http://localhost:5173
- API docs: http://localhost:8000/docs

### 4. Seed stock data (optional)

Preloads 50+ common tickers so the mapper has something to match against:

```bash
docker exec -i signalstock-db psql -U signalstock -d signalstock < db/seed_data.sql
```

---

## Running Locally Without Docker

If you have PostgreSQL and Redis running locally:

```bash
# Terminal 1 — API
cd services/api
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The Vite dev server proxies all `/api/*` requests to port 8000.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/events` | Paginated event feed (filters: `has_stocks`, `exclude_neutral`, `sentiment`, `event_type`, `tickers`) |
| `GET` | `/events/stats` | Dashboard aggregates |
| `GET` | `/stocks/prices` | Live prices via Finnhub (Redis 60s cache) |
| `POST` | `/auth/register` | Create account |
| `POST` | `/auth/login` | Get JWT token |
| `GET` | `/preferences` | Get alert preferences (auth required) |
| `PUT` | `/preferences` | Update alert preferences |
| `GET` | `/auth/unsubscribe` | One-click unsubscribe via token |

---

## Database Schema

```
users ──────────── user_preferences
  │                      (email_enabled, sentiment filters,
  │                       event_type filters, unsubscribe_token)
  └── watchlists ── stocks ── event_stocks ── events ── articles
                                                  │
                                             alerts_sent
```

---

## Project Structure

```
signalstock/
├── docker-compose.yml
├── db/
│   ├── init.sql                  # Schema (auto-applied on first docker start)
│   ├── seed_data.sql             # Optional: preload 50+ stock tickers
│   └── migrations/               # Incremental migration scripts
├── services/
│   ├── scraper/                  # News + Twitter scraping
│   ├── classifier/               # Groq LLM classification
│   ├── mapper/                   # Event → stock mapping
│   ├── alerts/                   # Email alert engine
│   └── api/                      # FastAPI REST gateway
└── frontend/                     # React dashboard
    └── src/
        ├── pages/
        │   ├── Dashboard.jsx     # Main event feed + charts
        │   ├── EventsPage.jsx    # Filterable full event list
        │   └── WatchlistPage.jsx # Manage watched stocks
        └── components/           # EventCard, PreferencesModal, etc.
```

---

## License

MIT
