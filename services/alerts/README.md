# SignalStock Alert Engine

Polls PostgreSQL every 60 seconds for stock events matching user watchlists
and sends email alerts via SendGrid. Each alert is recorded in `alerts_sent`
so it's never sent twice.

## How It Works

```
Poll: events WHERE stock in user watchlist AND alert not yet sent
        |
        v
  build email (subject + HTML body)
        |
        v
  SendGrid API → user inbox
        |
        v
  INSERT alerts_sent (user_id, event_id)
        |
        v
  sleep 60s, repeat
```

## Setup

### 1. Get a free SendGrid account

1. Go to [sendgrid.com](https://sendgrid.com) — free tier is 100 emails/day
2. Create an account (no credit card required)
3. Go to **Settings > API Keys > Create API Key**
4. Choose "Restricted Access", enable **Mail Send**
5. Copy the key (`SG.xxxx...`) into `.env` as `SENDGRID_API_KEY`

### 2. Verify your sender email

SendGrid requires the `From` address to be verified before it will send.

1. In SendGrid: **Settings > Sender Authentication > Single Sender Verification**
2. Click "Create a Sender" and fill in the form with your email address
3. Click the verification link sent to that address
4. Set the same address as `SENDGRID_FROM_EMAIL` in `.env`

### 3. Configure `.env`

```bash
cd services/alerts
cp .env.example .env
# Fill in SENDGRID_API_KEY and SENDGRID_FROM_EMAIL
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

## Running Locally

```bash
# Start postgres first
docker compose up -d postgres

# Run alert engine
python main.py
```

## Environment Variables

| Variable               | Default | Description                                    |
|------------------------|---------|------------------------------------------------|
| `SENDGRID_API_KEY`     | —       | SendGrid API key (required)                    |
| `SENDGRID_FROM_EMAIL`  | —       | Verified sender address (required)             |
| `DATABASE_URL`         | —       | PostgreSQL connection string (required)        |
| `POLL_INTERVAL`        | `60`    | Seconds between polls                          |
| `BATCH_SIZE`           | `50`    | Max alerts per poll                            |

## Testing: Insert Test Data

Connect to postgres and run:

```sql
-- 1. Create a test user
INSERT INTO users (email, password_hash)
VALUES ('you@example.com', 'placeholder_hash')
RETURNING id;
-- note the returned user id (e.g. 1)

-- 2. Find a stock that has events
SELECT s.id, s.ticker, COUNT(es.event_id) AS event_count
FROM stocks s
JOIN event_stocks es ON s.id = es.stock_id
GROUP BY s.id, s.ticker
ORDER BY event_count DESC
LIMIT 5;
-- note a stock_id (e.g. stock_id = 3 for NVDA)

-- 3. Add that stock to the user's watchlist
INSERT INTO watchlists (user_id, stock_id)
VALUES (1, 3);  -- replace 1 and 3 with actual IDs

-- 4. Verify alertable events exist
SELECT u.email, e.event_type, s.ticker, a.title
FROM users u
JOIN watchlists w ON u.id = w.user_id
JOIN stocks s ON w.stock_id = s.id
JOIN event_stocks es ON s.id = es.stock_id
JOIN events e ON es.event_id = e.id
JOIN articles a ON e.article_id = a.id
WHERE NOT EXISTS (
    SELECT 1 FROM alerts_sent als
    WHERE als.user_id = u.id AND als.event_id = e.id
)
LIMIT 5;
```

Then run `python main.py` — you should receive an email within 60 seconds.

## Verification Queries

```sql
-- How many alerts have been sent?
SELECT COUNT(*) FROM alerts_sent;

-- Alerts sent per user
SELECT u.email, COUNT(*) AS alerts_sent
FROM alerts_sent als
JOIN users u ON als.user_id = u.id
GROUP BY u.email
ORDER BY alerts_sent DESC;

-- Latest alerts sent
SELECT u.email, s.ticker, e.event_type, e.sentiment, als.sent_at
FROM alerts_sent als
JOIN users u ON als.user_id = u.id
JOIN events e ON als.event_id = e.id
JOIN event_stocks es ON e.id = es.event_id
JOIN stocks s ON es.stock_id = s.id
ORDER BY als.sent_at DESC
LIMIT 10;
```

## Email Preview

Subject examples:
- `🟢 Earnings Report alert for AAPL`
- `🔴 Regulatory Action alert for NVDA`
- `🟡 Market News alert for TSLA`
