# SignalStock Event Classifier

Reads article IDs from Redis queue `articles:pending`, classifies each article using **Hugging Face free serverless inference**, and writes structured events to PostgreSQL.

## Why Hugging Face?

| | Hugging Face Free | Gemini Free |
|---|---|---|
| Cost | $0 forever | $0 with daily limit |
| No API key | Yes (public models) | No — key required |
| Daily quota | ~1000/model × 3 models | Strict, burns fast |
| Model quality | Llama 3.2, Mistral 7B | Gemini Flash |

## How It Works

```
Redis BRPOP articles:pending
        |
        v
   fetch article
  (PostgreSQL)
        |
        v
  already classified? --yes--> skip
        | no
        v
  HF Inference API
  Try Llama 3.2 -> Mistral 7B -> Phi-3 (fallback chain)
  -> {event_type, sentiment, confidence}
        |
        +---> INSERT events table
        |
        +-- on failure --> RPUSH back to queue
```

## Models Used (in priority order)

| Model | Why |
|---|---|
| `meta-llama/Llama-3.2-3B-Instruct` | Best quality, fast |
| `mistralai/Mistral-7B-Instruct-v0.3` | Strong fallback |
| `microsoft/Phi-3-mini-4k-instruct` | Lightweight backup |

All are **100% free**, hosted by Hugging Face. No signup or API key required.

## Event Types

| Type | Example |
|---|---|
| `earnings_report` | Quarterly revenue beats/misses |
| `merger_acquisition` | M&A deals, buyouts |
| `product_launch` | New products or services |
| `regulatory_action` | FDA approvals, fines, rulings |
| `executive_change` | CEO/CFO changes |
| `lawsuit` | Legal actions, settlements |
| `partnership` | Joint ventures, strategic deals |
| `other` | Everything else |

## Setup

```bash
cd services/classifier
cp .env.example .env
# No API keys needed — just set DATABASE_URL and REDIS_URL

pip install -r requirements.txt
```

## Running Locally

```bash
# Start postgres and redis first
docker compose up -d postgres redis

# Run classifier (processes queue continuously)
python main.py
```

## Rate Limits

- Each HF model: ~1000 free requests/day
- 3 models in fallback chain = ~3000 effective requests/day
- More than enough for MVP usage
- If a model is rate-limited, the classifier automatically tries the next one
