# SignalStock Database

## Schema Overview

PostgreSQL 15 database for real-time stock event detection.

### Table Relationships

```
users
 ├──< watchlists >── stocks
 └──< alerts_sent >── events
                        │
                   articles ──< events >── event_stocks >── stocks
```

```
┌──────────┐     ┌─────────────┐     ┌──────────┐
│  users   │     │  articles   │     │  stocks  │
│──────────│     │─────────────│     │──────────│
│ id (PK)  │     │ id (PK)     │     │ id (PK)  │
│ email    │     │ title       │     │ ticker   │
│ password │     │ content     │     │ company  │
│ created  │     │ url (UQ)    │     └────┬─────┘
└──┬───┬───┘     │ source      │          │
   │   │         │ published   │          │
   │   │         │ scraped     │          │
   │   │         └──────┬──────┘          │
   │   │                │                 │
   │   │         ┌──────┴──────┐   ┌──────┴───────┐
   │   │         │   events    │   │ event_stocks  │
   │   │         │─────────────│   │──────────────-│
   │   │         │ id (PK)     ├───┤ event_id (FK) │
   │   │         │ article_id  │   │ stock_id (FK) │
   │   │         │ event_type  │   └───────────────┘
   │   │         │ sentiment   │
   │   │         │ classified  │
   │   │         └──────┬──────┘
   │   │                │
   │   │    ┌───────────┴──┐
   │   └────┤ alerts_sent  │
   │        │──────────────│
   │        │ user_id (FK) │
   │        │ event_id(FK) │
   │        │ sent_at      │
   │        └──────────────┘
   │
   │     ┌──────────────┐
   └─────┤  watchlists  │
         │──────────────│
         │ user_id (FK) │
         │ stock_id(FK) │
         │ created_at   │
         └──────────────┘
```

### Tables

| Table | Purpose |
|-------|---------|
| `users` | Platform accounts |
| `articles` | Scraped news articles (deduplicated by URL) |
| `events` | AI-classified events extracted from articles |
| `stocks` | Tracked stock tickers |
| `event_stocks` | Many-to-many: which stocks an event mentions |
| `watchlists` | Which stocks each user is watching |
| `alerts_sent` | Tracks delivered alerts to prevent duplicates |

### Design Rationale

- **BIGINT GENERATED ALWAYS AS IDENTITY** for primary keys — standard PostgreSQL approach, avoids serial pitfalls
- **TIMESTAMPTZ** everywhere — stores UTC, renders in client timezone
- **CASCADE deletes** on foreign keys — removing an article removes its events; removing a user removes their watchlist/alerts
- **UNIQUE on `articles.url`** — prevents duplicate scraping
- **UNIQUE on `(user_id, event_id)` in alerts_sent** — guarantees one alert per user per event
- **Composite primary keys** on junction tables (`event_stocks`, `watchlists`) — natural keys, no surrogate needed
- **CHECK constraint on sentiment** — enforces `positive`, `negative`, `neutral`

## Quick Start

```bash
# Start services
docker-compose up -d

# Wait for healthy postgres
docker-compose exec postgres pg_isready -U signalstock

# Load seed data
docker exec -i signalstock-db psql -U signalstock -d signalstock < db/seed_data.sql

# Connect to database
docker exec -it signalstock-db psql -U signalstock -d signalstock
```

## Reset Database

```bash
# Tear down volumes and recreate
docker-compose down -v
docker-compose up -d

# Re-seed after init.sql runs automatically
docker exec -i signalstock-db psql -U signalstock -d signalstock < db/seed_data.sql
```

## Migrations

See [migrations/README.md](migrations/README.md) for the migration strategy.

## Useful Queries

```sql
-- Events for a specific stock
SELECT e.event_type, e.sentiment, a.title, a.published_at
FROM events e
JOIN event_stocks es ON es.event_id = e.id
JOIN stocks s ON s.id = es.stock_id
JOIN articles a ON a.id = e.article_id
WHERE s.ticker = 'AAPL'
ORDER BY e.classified_at DESC;

-- Unsent alerts for a user's watchlist
SELECT u.email, s.ticker, e.event_type, e.sentiment, a.title
FROM users u
JOIN watchlists w ON w.user_id = u.id
JOIN stocks s ON s.id = w.stock_id
JOIN event_stocks es ON es.stock_id = s.id
JOIN events e ON e.id = es.event_id
JOIN articles a ON a.id = e.article_id
LEFT JOIN alerts_sent al ON al.user_id = u.id AND al.event_id = e.id
WHERE al.id IS NULL
  AND u.email = 'alice@example.com';
```
