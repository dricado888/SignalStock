-- SignalStock: Real-time Stock Event Detection Platform
-- PostgreSQL 15 Schema
-- ==============================================

BEGIN;

-- ============================================
-- USERS: Platform accounts
-- ============================================
CREATE TABLE users (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email           VARCHAR(255) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- ============================================
-- ARTICLES: Scraped news articles
-- ============================================
CREATE TABLE articles (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title           VARCHAR(500)  NOT NULL,
    content         TEXT          NOT NULL,
    url             VARCHAR(2048) NOT NULL UNIQUE,  -- deduplicate by URL
    source          VARCHAR(100)  NOT NULL,          -- e.g. 'reuters', 'cnbc'
    published_at    TIMESTAMPTZ,                     -- nullable: not always known
    scraped_at      TIMESTAMPTZ   NOT NULL DEFAULT now()
);

CREATE INDEX idx_articles_source      ON articles (source);
CREATE INDEX idx_articles_published   ON articles (published_at DESC);
CREATE INDEX idx_articles_scraped     ON articles (scraped_at DESC);

-- ============================================
-- EVENTS: AI-classified events from articles
-- ============================================
CREATE TABLE events (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    article_id      BIGINT       NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    event_type      VARCHAR(50)  NOT NULL,  -- e.g. 'earnings_beat', 'fda_approval', 'ceo_change'
    sentiment       VARCHAR(20)  NOT NULL CHECK (sentiment IN ('positive', 'negative', 'neutral')),
    classified_at   TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX idx_events_article    ON events (article_id);
CREATE INDEX idx_events_type       ON events (event_type);
CREATE INDEX idx_events_classified ON events (classified_at DESC);

-- ============================================
-- STOCKS: Tracked tickers
-- ============================================
CREATE TABLE stocks (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ticker          VARCHAR(10)  NOT NULL UNIQUE,
    company_name    VARCHAR(255) NOT NULL
);

-- ============================================
-- EVENT_STOCKS: Many-to-many link between events and stocks
-- An event can mention multiple stocks; a stock can appear in many events.
-- ============================================
CREATE TABLE event_stocks (
    event_id    BIGINT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    stock_id    BIGINT NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    PRIMARY KEY (event_id, stock_id)
);

CREATE INDEX idx_event_stocks_stock ON event_stocks (stock_id);

-- ============================================
-- WATCHLISTS: Users watching specific stocks
-- ============================================
CREATE TABLE watchlists (
    user_id     BIGINT      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    stock_id    BIGINT      NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, stock_id)
);

CREATE INDEX idx_watchlists_stock ON watchlists (stock_id);

-- ============================================
-- ALERTS_SENT: Track which alerts were delivered to avoid duplicates
-- ============================================
CREATE TABLE alerts_sent (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id     BIGINT      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    event_id    BIGINT      NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    sent_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, event_id)  -- never send the same alert twice
);

CREATE INDEX idx_alerts_sent_user  ON alerts_sent (user_id);
CREATE INDEX idx_alerts_sent_event ON alerts_sent (event_id);

-- ============================================
-- USER_PREFERENCES: Per-user email alert settings
-- ============================================
CREATE TABLE user_preferences (
    user_id             BIGINT      PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    email_enabled       BOOLEAN     NOT NULL DEFAULT TRUE,
    notify_positive     BOOLEAN     NOT NULL DEFAULT TRUE,
    notify_negative     BOOLEAN     NOT NULL DEFAULT TRUE,
    notify_neutral      BOOLEAN     NOT NULL DEFAULT FALSE,
    notify_event_types  TEXT[]      NOT NULL DEFAULT ARRAY[
        'earnings_report','merger_acquisition','product_launch',
        'regulatory_action','executive_change','lawsuit','partnership'
    ],
    unsubscribe_token   UUID        NOT NULL DEFAULT gen_random_uuid(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX idx_prefs_unsub_token ON user_preferences (unsubscribe_token);

COMMIT;
