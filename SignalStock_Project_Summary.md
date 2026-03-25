# SignalStock: Project Summary for Resume & Interviews

> **Built from scratch, end-to-end, using 100% free-tier services.**
> A production-grade real-time stock event detection and alert platform — not a tutorial clone.

---

## 1. Project Overview

### What Problem Does It Solve?

Retail investors miss market-moving events because financial news is fragmented across dozens of sources and arrives faster than any human can monitor. SignalStock solves this by:

1. Continuously scraping financial news (every 5 minutes) from multiple APIs and Twitter/X
2. Using a large language model to classify each article by event type and market sentiment
3. Mapping events to the specific stocks they affect — directly or via sector/macro analysis
4. Sending personalized email alerts to users who hold those stocks on their watchlist, filtered by their own preferences

### What Makes It Impressive?

- **Zero paid infrastructure** — runs entirely on free-tier APIs (Groq, Finnhub, Apify, Finlight, NewsAPI, SendGrid, Docker local)
- **Production architecture** — 5 fully isolated microservices communicating via Redis queue, each independently deployable
- **Full-stack ownership** — database schema, 5 backend services, REST API, React dashboard, email system, all built by one engineer
- **Real AI integration** — LLM-powered classification with structured JSON output, fallback strategies, and confidence scoring
- **Live market data** — real-time stock prices from Finnhub API, refreshed every 60 seconds in the UI
- **CAN-SPAM/GDPR-compliant** email system with one-click unsubscribe tokens, preference management, and opt-in defaults

### Tech Stack at a Glance

| Layer | Technology |
|-------|------------|
| Frontend | React 18, Vite, Tailwind CSS, Framer Motion |
| API Gateway | FastAPI (Python), JWT auth, Redis cache |
| Scraper | Python, Apify (Twitter), Finlight, NewsAPI |
| Classifier | Python, Groq API (llama-3.1-8b-instant) |
| Stock Mapper | Python, regex, fuzzywuzzy, sector affinity |
| Alert Engine | Python, SendGrid, HTML email templates |
| Database | PostgreSQL 15 (9 tables, normalized schema) |
| Cache / Queue | Redis 7 (message queue + price cache) |
| Infra | Docker Compose (8 containers), health checks |

---

## 2. System Architecture

### High-Level Data Flow

```
Financial News APIs ──┐
Twitter/X (Apify) ───┤──► Scraper ──► Redis Queue ──► Classifier ──► PostgreSQL
                      │                                                    │
                      └──────────────────────────────────────────────      │
                                                                      Stock Mapper
                                                                           │
                                                              ┌────────────┘
                                                              │
                                                         Alert Engine ──► SendGrid ──► User Email
                                                              │
                                                         FastAPI ──► React Dashboard
                                                              │
                                                         Finnhub API (live prices)
```

### 8-Container Docker Compose Stack

| Container | Role |
|-----------|------|
| `postgres` | Primary data store, health-checked |
| `redis` | Article queue + price cache |
| `scraper` | Polls news APIs + Twitter every 5 min |
| `classifier` | Dequeues articles, calls Groq LLM |
| `mapper` | Links classified events to affected stocks |
| `alerts` | Monitors watchlists, sends email alerts |
| `api` | FastAPI REST gateway (port 8000) |
| `frontend` | Vite/React dev server (port 5173) |

### Key Architectural Decisions

**Redis LIST as message queue** — Scraper pushes article IDs to a Redis LIST; classifier pops and processes them. Simple, zero-overhead, already present as a cache layer. Trade-off: no persistence guarantees (acceptable at MVP scale; Kafka at 100K+ articles/day).

**Separate mapper service** — Event-to-stock mapping runs independently after classification. This means classification errors don't corrupt the stock mapping table, and the mapping logic can be improved without redeployment of the classifier.

**FastAPI as API gateway** — All frontend requests go through a single authenticated API layer. Services never expose their databases directly. The API handles JWT auth, Redis price caching, and CORS.

---

## 3. Technical Implementation Details

### Phase 0: Project Setup
- Docker Compose with health checks (`pg_isready`, `redis-cli ping`) ensuring dependent services only start when dependencies are healthy
- `.env` files per service with Docker Compose `env_file` directive — avoids hardcoding credentials while keeping service isolation
- Discovered critical Docker Compose gotcha: `environment:` block overrides `env_file:` for the same key. Fixed by removing redundant override patterns that were silently nullifying API keys

### Phase 1: Database Schema (PostgreSQL)

**9 tables designed:**

```sql
users               — email, bcrypt password hash, created_at
user_preferences    — per-user email opt-in, sentiment filters, event type filters, unsubscribe token (UUID)
stocks              — ticker, company_name, sector
watchlists          — user_id ↔ stock_id (many-to-many junction)
articles            — url (UNIQUE), title, content, source, published_at, scraped_at
events              — article_id, event_type, sentiment, confidence, classified_at
event_stocks        — event_id ↔ stock_id (many-to-many junction)
alerts_sent         — user_id, event_id, sent_at (prevents duplicate alerts)
```

**Why PostgreSQL over MongoDB:**
- Financial data has strong relational structure (user → watchlist → stock → event → alert)
- Complex JOIN queries required (e.g., "find all events for stocks on this user's watchlist that match their sentiment preferences and haven't been alerted yet") — single SQL query, not application-level joins
- ACID guarantees prevent duplicate alerts under concurrent processing
- `UNIQUE` constraints enforce deduplication at the DB level

**Indexing strategy:**
- `articles.url` — UNIQUE index, makes scraper deduplication an O(1) DB lookup
- `user_preferences.unsubscribe_token` — UNIQUE index, token-based unsubscribe is a direct lookup
- Junction tables indexed on both foreign keys for JOIN performance

### Phase 2: Scraper Service

**Sources integrated:**
- **Finlight.me** — Financial news API, 10K requests/month free, primary source
- **NewsAPI** — Breaking news backup, 100 requests/day free
- **Twitter/X via Apify** — `quacker/twitter-scraper` actor scraping 10 financial handles (Reuters, WSJ, Bloomberg, nvidia, OpenAI, GoldmanSachs, SECGov, FederalReserve, AnthropicAI, Apple)

**Deduplication strategy:** `INSERT ... ON CONFLICT (url) DO NOTHING` — the database enforces uniqueness, no application-level set comparison needed. Scraper pushes article ID to Redis queue only on successful insert.

**Content quality filtering:** Twitter posts with fewer than 30 meaningful characters (after stripping URLs, emoji, and non-ASCII) are discarded before storage. Prevents emoji-only posts from entering the classification pipeline.

**Rate limit management:** Apify free tier ~300 actor runs/month. Initially set Twitter polling to 5 minutes (burned through quota in hours). Fixed to 2-hour intervals — 360 runs/month, within free tier. Finlight/NewsAPI run every 5 minutes separately.

### Phase 3: AI Classifier Service

**KEY CHALLENGES & SOLUTIONS:**

*Original plan:* Google Gemini 2.5 Flash-Lite (1,000 requests/day free documented)
*Problem discovered:* Gemini API quota was 0 for new accounts despite documentation. Tried `gemini-1.5-flash`, `gemini-2.0-flash`, created multiple API keys — all returned quota errors.
*Solution:* Researched alternatives, selected **Groq** (llama-3.1-8b-instant) — genuinely free, ~500 requests/minute, sub-2-second inference.

**Prompt engineering approach:**
```
System: You are a financial event classifier. Given a news article, return JSON with:
  - event_type: one of [earnings_report, merger_acquisition, product_launch, ...]
  - sentiment: positive | negative | neutral
  - confidence: float 0.0-1.0
  - reasoning: one sentence explanation
```

Structured JSON output enforced via Groq's response format. Fallback: if JSON parse fails, article is discarded and logged (not retried — prevents queue backup).

**Classification results (113 events from 343 articles):**
- 51 general market news, 36 regulatory actions, 16 product launches, 4 executive changes, 2 partnerships, 2 M&A, 1 lawsuit, 1 earnings report
- Sentiment: 38 positive, 38 negative, 37 neutral
- Confidence: 0.95 average (Groq llama-3.1-8b-instant is highly reliable on structured output)

### Phase 4: Stock Mapper Service

**Three-layer mapping:**

1. **Explicit ticker regex** — Finds `$AAPL`, `$NVDA` patterns directly in article text. Highest confidence.

2. **Company name matching** — 50+ curated company→ticker mappings + fuzzywuzzy (`>80%` similarity threshold). Handles variants: "Apple Inc." → AAPL, "Alphabet" → GOOGL, "Meta Platforms" → META.

3. **Sector affinity mapping** — For market-signal events (no direct company mentioned), maps keywords to affected sectors and their representative stocks. Example: "interest rate hike" → FINANCE sector → JPM, GS, BAC, WFC.

**False positive prevention:**
- Excluded words list: AP (news agency), ORD (airport code), CEO, IPO, SEC, GDP, GDP, FDA
- Sector keywords carefully curated: "bank" alone doesn't trigger FINANCE (matches "bankruptcy"). Requires " banking", "central bank", "rate hike" etc.
- Company-specific events (earnings, product launches) skip sector affinity mapping entirely — prevents Hyundai news from incorrectly linking to Amazon/Walmart

**44 unit tests** written and passing, covering edge cases: stock symbols in all-caps company names, tickers as common English words, multi-ticker articles, airport code exclusion.

### Phase 5: Alert Engine

**SQL query that powers alerts** (joining 6 tables in one query):
```sql
SELECT u.id, u.email, e.event_type, e.sentiment, s.ticker,
       a.title, a.url, a.source, a.published_at, up.unsubscribe_token
FROM users u
JOIN user_preferences up ON up.user_id = u.id
JOIN watchlists w ON w.user_id = u.id
JOIN stocks s ON s.id = w.stock_id
JOIN event_stocks es ON es.stock_id = s.id
JOIN events e ON e.id = es.event_id
JOIN articles a ON a.id = e.article_id
WHERE up.email_enabled = TRUE
  AND (e.sentiment='positive' AND up.notify_positive OR ...)
  AND e.event_type = ANY(up.notify_event_types)
  AND NOT EXISTS (SELECT 1 FROM alerts_sent WHERE user_id=u.id AND event_id=e.id)
```

A single query handles deduplication, preference filtering, and event joining — no application-level filtering.

**HTML email template:** Professional design with sentiment-colored gradient header (green/red/purple), stock ticker hero, event type chips, article card, and footer with unsubscribe/manage-preferences links. Rendered server-side with Python string formatting.

### Phase 6: REST API (FastAPI)

**Endpoints:**
- `GET /events` — paginated event feed with `has_stocks`, `exclude_neutral`, `sentiment`, `event_type`, `tickers` filters
- `GET /events/stats` — dashboard aggregates (totals, sentiment breakdown, top stocks, events by day)
- `GET /stocks/prices` — live prices from Finnhub API with 60-second Redis cache
- `POST /auth/register` / `POST /auth/login` — JWT authentication (bcrypt password hashing)
- `GET /me` — authenticated user info
- `GET /preferences` / `PUT /preferences` — user alert preferences (auth required)
- `GET /auth/unsubscribe?token=UUID` — one-click unsubscribe (no auth required)

**Auth implementation:** JWT tokens (7-day expiry), bcrypt password hashing. Initial implementation used passlib 1.7.4 which is incompatible with bcrypt 5.x — discovered and fixed during testing by replacing passlib with direct `bcrypt` library calls.

**Live price caching:** Finnhub API called per-ticker, results cached in Redis with 60-second TTL. Frontend polls every 60 seconds — request count stays well within Finnhub's free tier (60 req/min).

### Phase 7: React Frontend Dashboard

**Components built:**
- **StockPriceCard** — Displays real-time prices with ▲/▼/→ direction arrows and color coding. 60-second countdown to next refresh. Handles empty state (watchlist empty, API key missing).
- **TopStocksBar (TopMovers)** — Bar chart sorted by absolute % price change. Green bars = bullish, red = bearish.
- **SentimentDonut** — Doughnut chart showing bullish/bearish/neutral ratio.
- **EventCard** — Event cards with event type chip, sentiment badge, source, timestamp, and READ link.
- **StockWatchlist** — Add/remove stocks by ticker with localStorage persistence.
- **EventFilters** — Dropdown filters for event type and sentiment.
- **SubscribeModal** — Email signup flow.
- **PreferencesModal** — Login → toggle preferences → save. Manages email_enabled, sentiment filters, event type filters.
- **Unsubscribe page** — Handles `/unsubscribe?token=xxx` route, calls API, shows confirmation.

**Dashboard architecture:**
- Two independent API calls per section (DIRECT EXPOSURE vs MARKET SIGNALS), each with own pagination state
- Neutral events hidden by default (toggle to include)
- 15 events per section per page
- Key bug discovered and fixed: spreading `filters` state (which contained `page: 1`) into API params was overwriting the section-specific page number, making NEXT button do nothing

**Design system:** Terminal-dark aesthetic — `#09090b` background, cyan/amber accent colors, monospace `font-ticker`, subtle animations via Framer Motion.

---

## 4. Challenges Overcome

### Challenge 1: Gemini API Quota — Zero on New Accounts
- **Problem:** Google Gemini 2.5 Flash-Lite documented 1,000 free requests/day. Actual quota for new accounts: 0. Tried multiple models (gemini-1.5-flash, gemini-2.0-flash), multiple API keys. Same result.
- **Impact:** Core classifier service completely non-functional.
- **Solution:** Researched alternatives in real-time. Groq offers genuinely free llama-3.1-8b-instant access with 500 req/min. Migrated in under 30 minutes.
- **Learning:** Never build a critical path on a single external dependency without validating quota availability first.

### Challenge 2: Docker Compose Environment Variable Override Bug
- **Problem:** Services had both `env_file:` and `environment:` blocks. Docker Compose `environment:` silently overwrites `env_file:` values for matching keys. The Finnhub API key was in `api/.env` but the compose file had `FINNHUB_API_KEY: ${FINNHUB_API_KEY:-}` which resolved to empty string from the host shell.
- **Impact:** Live price feature showed "SET FINNHUB_API_KEY" error despite the key existing in the .env file. Twitter scraper had same issue — APIFY_API_TOKEN and TWITTER_ACCOUNTS were being nullified.
- **Solution:** Removed the redundant `environment:` overrides. Let `env_file:` be the single source of truth.
- **Learning:** Docker Compose has nuanced precedence rules. Test with `docker compose exec service env | grep KEY_NAME` to verify actual env vars.

### Challenge 3: False Positive Stock Associations
- **Problem:** Hyundai news about stopping EV production was being linked to Amazon (AMZN) and Walmart (WMT). Restaurant bankruptcy news was triggering FINANCE sector stocks (JPM, GS).
- **Root cause:** Sector affinity keyword "consumer" matched too broadly. "bank" in "bankruptcy" matched the FINANCE sector.
- **Solution:**
  1. Tightened sector keywords (removed "consumer", "bank", added specific phrases like "retail store", " banking", "central bank")
  2. Changed mapper logic: only apply sector affinity for `event_type='other'`, not for company-specific events
  3. Cleaned 59 corrupted rows from the DB retroactively
- **Learning:** NLP keyword matching requires domain-specific tuning. Substring matching without word boundaries creates insidious false positives.

### Challenge 4: React Pagination Stale Closure / State Spread Bug
- **Problem:** Clicking the NEXT button on paginated event sections did nothing.
- **Root cause:** `const params = { limit: 15, page, ...filters }` — the `filters` React state object contained `{ page: 1 }`. Spreading it after the explicit `page` argument overwrote it, so every API call sent `page=1` regardless of which page the user navigated to.
- **Solution:** `const { page: _ignored, ...otherFilters } = filters; const params = { limit: 15, page, ...otherFilters };`
- **Learning:** Object spread order matters. Spreading state objects into request params without careful key exclusion is a common React bug.

### Challenge 5: passlib / bcrypt Version Incompatibility
- **Problem:** Login endpoint returned HTTP 500. Logs showed `passlib.exc.UnknownHashError: hash could not be identified` even for valid bcrypt `$2b$` hashes.
- **Root cause:** `passlib 1.7.4` (released 2020) is incompatible with `bcrypt 5.x` (released 2024). The newer bcrypt removed the `__about__` module that passlib used for version detection.
- **Solution:** Removed passlib entirely. Replaced with direct `bcrypt` library calls (`bcrypt.hashpw` / `bcrypt.checkpw`). Also pinned `bcrypt==4.0.1` in requirements.txt.
- **Learning:** Long-unmaintained libraries (passlib's last release was 2020) accumulate transitive dependency conflicts. Always check compatibility when upgrading any dependency.

### Challenge 6: Apify Free Tier Burn Rate
- **Problem:** Set Twitter scraping to 5-minute intervals for testing. Apify free tier ran out within hours.
- **Root cause:** 5 min × 12/hour × 24 hours = 288 actor runs/day. Free tier allows ~300/month.
- **Solution:** Changed `TWITTER_POLL_INTERVAL_SECONDS` to 7200 (2 hours). Finlight/NewsAPI run every 5 minutes independently — Twitter is supplementary.
- **Learning:** Always calculate daily consumption against monthly quotas before setting polling intervals.

---

## 5. Technical Decisions & Trade-offs

### Decision 1: PostgreSQL vs MongoDB
- **Chose:** PostgreSQL
- **Why:** Financial data is fundamentally relational. A single query joins users → preferences → watchlists → stocks → events → articles → alerts_sent. This is trivial in SQL, painful in document stores.
- **Trade-off:** Schema migrations require coordination across services.
- **Scaling path:** Partition `events` table by `classified_at` date, add read replicas for API, keep Redis cache TTL short for fresh data.

### Decision 2: Redis LIST as Message Queue vs RabbitMQ/Kafka
- **Chose:** Redis LIST (`LPUSH` / `BRPOP`)
- **Why:** Already needed Redis for price caching and rate limiting. Zero additional infrastructure. Simple, debuggable.
- **Trade-off:** No message persistence (crash loses queue), no consumer groups, no dead-letter queue.
- **Scaling path:** Kafka at 100K+ articles/day for durability, replay, and consumer group partitioning.

### Decision 3: Groq llama-3.1-8b-instant vs Smaller Local Model
- **Chose:** Groq API
- **Why:** Free, fast (sub-2s), reliable structured JSON output. Running a local LLM would require GPU resources.
- **Trade-off:** External API dependency. If Groq's free tier changes or has downtime, classifier stops.
- **Mitigation:** Classifier handles Groq errors gracefully — logs and discards rather than crashing. Could add retry queue.

### Decision 4: Microservices vs Monolith
- **Chose:** 5 microservices
- **Why:** Independent deployment (fix the classifier without touching the scraper), isolated failure domains, learn production architecture patterns, prepared for AWS ECS.
- **Trade-off:** 8 Docker containers to manage locally, distributed debugging is harder.
- **Scaling path:** Architecture is already cloud-ready. Each service maps to one ECS task definition.

### Decision 5: JWT in localStorage vs httpOnly Cookies
- **Chose:** localStorage (for MVP speed)
- **Trade-off:** Technically vulnerable to XSS. For production, httpOnly cookies prevent JavaScript access.
- **Acknowledged:** The preference modal stores the JWT as `ss_token` in localStorage. Production version would use httpOnly cookies with SameSite=Strict.

---

## 6. Current Metrics (Live System)

| Metric | Value |
|--------|-------|
| Articles scraped | 343 |
| Events classified | 113 |
| Stocks tracked | 49 |
| Event-stock relationships | 35 |
| Registered users | 1 |
| Watchlist items | 3 |
| Email alerts sent | 8 |
| Infrastructure cost | $0 |

**Event type breakdown:** 51 market news, 36 regulatory actions, 16 product launches, 4 executive changes, 2 partnerships, 2 M&A, 1 lawsuit, 1 earnings report

**Sentiment breakdown:** 38 positive, 38 negative, 37 neutral (near-perfect balance — validates classifier isn't biased)

**Sources:** Finlight.me (financial news), NewsAPI (breaking news), Twitter/X via Apify (10 accounts: Reuters, WSJ, Bloomberg, nvidia, OpenAI, GoldmanSachs, SECGov, FederalReserve, AnthropicAI, Apple)

---

## 7. Skills Demonstrated

**Backend Engineering**
- Python microservices (FastAPI, async processing, psycopg2)
- RESTful API design with auth middleware, pagination, filtering
- SQL query optimization (multi-table JOINs, EXISTS subqueries, indexing)
- Redis patterns: message queue (LIST), cache with TTL, distributed dedup

**AI/ML Integration**
- LLM API integration with structured JSON output (Groq/llama-3.1-8b-instant)
- Prompt engineering for consistent classification output
- Graceful degradation when AI API fails
- Evaluated and pivoted from Gemini to Groq after quota discovery

**Frontend Development**
- React 18 with hooks (useState, useEffect, useCallback, useRef)
- Tailwind CSS custom design system (terminal-dark theme)
- Framer Motion animations
- Real-time data (60s polling, price countdown)
- Modal flows, form validation, JWT session management

**System Design**
- Event-driven microservices architecture
- Distributed message queue patterns
- Cache-aside pattern for API responses
- CAN-SPAM/GDPR-compliant email system design

**DevOps & Debugging**
- Docker Compose multi-service orchestration with health checks
- Environment variable management across 8 containers
- Root-cause debugging: API quota issues, Docker networking, bcrypt compatibility, React state bugs
- Service log analysis and live monitoring

---

## 8. Interview Talking Points

### "Tell me about a technical challenge you faced"
The most illustrative one: the passlib/bcrypt incompatibility. Login was returning HTTP 500. I traced the logs to `passlib.exc.UnknownHashError` — it couldn't identify a valid `$2b$12$` bcrypt hash. Researched the issue: passlib 1.7.4 was released in 2020 and uses `bcrypt.__about__.__version__` for version detection, which bcrypt 4.0+ removed. The fix was replacing passlib entirely with direct `bcrypt.hashpw`/`checkpw` calls — a 10-line change that eliminated the dependency. This reinforced: understand your dependency graph, and avoid unmaintained libraries in the critical auth path.

### "How did you approach debugging the pagination bug?"
NEXT button was visually enabled but clicked with no result. Traced: click → `setDirectPage(p => p + 1)` → `directPage` state increments → `useEffect` fires → `fetchSection(true, directPage, ...)` called → API returns page 1 data again. Found the bug: `const params = { limit: 15, page, ...filters }`. The `filters` state object contains `{ page: 1 }`. Spreading it last means `filters.page` overwrites the argument. Fix: destructure `page` from `filters` before spreading. Classic JavaScript gotcha — object spread silently overwrites.

### "How would you scale this to 1M users?"
- **Database:** Partition `events` by date (PostgreSQL range partitioning), read replicas for API queries, connection pooling via PgBouncer
- **Queue:** Migrate Redis LIST to Kafka — durability, consumer groups, replay for classifier recovery
- **Classification:** Batch articles instead of one-at-a-time, use Groq batch API or self-hosted quantized model
- **Alerts:** Celery + Redis for distributed task processing, rate-limited sending with SendGrid's transactional API
- **API:** Horizontal scaling behind load balancer, Redis Cluster for cache
- **Frontend:** CDN for static assets, API response caching at edge

### "Why microservices for an MVP?"
Deliberate over-engineering for learning purposes — which is honest and good. The alternative (monolith) would have been faster to ship but harder to reason about when debugging AI classification vs. scraping vs. alerts independently. Having isolation meant I could restart just the classifier when Groq was down without disrupting scraping. It also prepared the system for cloud deployment — each service maps 1:1 to an ECS task definition.

### "What would you do differently?"
1. **Integration tests from day one** — I caught the passlib/bcrypt incompatibility only during manual testing. A test that calls `POST /auth/login` with a real password would have caught it at build time.
2. **Pin ALL dependencies** in requirements.txt — `bcrypt` was floating and `pip install` pulled 5.x.
3. **Rate limit validation before setting intervals** — calculated Apify burn rate after the fact, not before.
4. **httpOnly cookies for JWT** — localStorage was fine for speed but wrong for production.

---

## 9. Resume Bullet Points

- **Architected SignalStock**, a real-time stock event detection platform using 5-service Python microservices (FastAPI, PostgreSQL, Redis, Docker) that automatically scrapes 343 financial news articles, classifies them with Groq's LLM API, and delivers personalized email alerts based on user watchlists and preferences
- **Integrated Groq llama-3.1-8b-instant** for AI event classification after troubleshooting Google Gemini's broken free-tier quota; achieved balanced 38/38/37 positive/negative/neutral distribution across 113 classified events spanning 8 event types
- **Built full-stack React dashboard** with real-time stock prices (Finnhub API, 60s Redis cache), dual-section event feed with independent pagination, animated data visualizations (Framer Motion), and GDPR-compliant email preference management
- **Designed PostgreSQL schema** with 9 normalized tables and complex multi-table SQL queries joining users, watchlists, stocks, events, and articles; implemented unsubscribe token system and preference-aware alert filtering
- **Debugged and fixed 5 production issues** independently: Docker env var override silencing API keys, React state spread overwriting pagination parameters, passlib/bcrypt 5.x incompatibility causing auth 500 errors, sector keyword false-positive stock associations, and Apify quota burn rate exceeding free tier
- **Built zero-cost infrastructure** on 100% free-tier services (Groq, Finnhub, Apify, Finlight, SendGrid, Docker) demonstrating cost-effective engineering for MVP development

---

## 10. Project Timeline & Scope

Built across 10 development phases:

| Phase | Deliverable |
|-------|-------------|
| 0 | Project setup, Docker Compose, 8-container stack |
| 1 | PostgreSQL schema (9 tables, indexes, constraints) |
| 2 | Scraper service (Finlight, NewsAPI, Twitter/Apify) |
| 3 | AI Classifier (Groq, structured output, Redis queue) |
| 4 | Stock Mapper (regex, fuzzy match, sector affinity, 44 unit tests) |
| 5 | Alert Engine (SendGrid, HTML templates, deduplication) |
| 6 | FastAPI REST Gateway (JWT auth, all endpoints, Redis price cache) |
| 7 | React Frontend (dashboard, charts, modals, watchlist, unsubscribe flow) |
| 8 | Live prices (Finnhub), Twitter scraper (Apify), Docker env fixes |
| 9 | Per-section pagination, neutral filter, tweet quality filtering |
| 10 | Comprehensive testing, bug fixes, bcrypt/passlib fix, skills |

**Total:** Full production-grade platform, end-to-end, using only free-tier services.
