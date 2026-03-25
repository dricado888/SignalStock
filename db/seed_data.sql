-- SignalStock: Seed Data for Development & Testing
-- =================================================

BEGIN;

-- ============================================
-- STOCKS: Core tickers (same as 002_seed_core_stocks.sql)
-- ============================================
INSERT INTO stocks (ticker, company_name) VALUES
    -- Mega-cap tech
    ('AAPL',  'Apple Inc.'),
    ('NVDA',  'NVIDIA Corporation'),
    ('TSLA',  'Tesla, Inc.'),
    ('MSFT',  'Microsoft Corporation'),
    ('GOOGL', 'Alphabet Inc.'),
    -- AI / Chip adjacent
    ('AMD',   'Advanced Micro Devices, Inc.'),
    ('INTC',  'Intel Corporation'),
    ('TSM',   'Taiwan Semiconductor Manufacturing Co.'),
    ('AVGO',  'Broadcom Inc.'),
    ('QCOM',  'Qualcomm Incorporated'),
    ('ARM',   'Arm Holdings plc'),
    ('META',  'Meta Platforms, Inc.'),
    ('AMZN',  'Amazon.com, Inc.'),
    ('NFLX',  'Netflix, Inc.'),
    -- Defense
    ('LMT',   'Lockheed Martin Corporation'),
    ('RTX',   'RTX Corporation'),
    ('NOC',   'Northrop Grumman Corporation'),
    ('GD',    'General Dynamics Corporation'),
    ('BA',    'The Boeing Company'),
    -- Energy
    ('XOM',   'Exxon Mobil Corporation'),
    ('CVX',   'Chevron Corporation'),
    ('COP',   'ConocoPhillips'),
    -- Finance
    ('JPM',   'JPMorgan Chase & Co.'),
    ('GS',    'The Goldman Sachs Group, Inc.'),
    ('MS',    'Morgan Stanley'),
    ('BAC',   'Bank of America Corporation'),
    ('V',     'Visa Inc.'),
    ('MA',    'Mastercard Incorporated'),
    -- Health
    ('JNJ',   'Johnson & Johnson'),
    ('PFE',   'Pfizer Inc.'),
    ('MRK',   'Merck & Co., Inc.'),
    ('LLY',   'Eli Lilly and Company'),
    -- Retail
    ('WMT',   'Walmart Inc.'),
    ('TGT',   'Target Corporation'),
    ('COST',  'Costco Wholesale Corporation'),
    ('NKE',   'Nike, Inc.')
ON CONFLICT (ticker) DO NOTHING;

-- ============================================
-- USERS: 3 test accounts (password is 'password123' hashed with bcrypt)
-- ============================================
INSERT INTO users (email, password_hash) VALUES
    ('alice@example.com',   '$2b$10$abcdefghijklmnopqrstuuABCDEFGHIJKLMNOPQRSTUVWXYZ012'),
    ('bob@example.com',     '$2b$10$abcdefghijklmnopqrstuuABCDEFGHIJKLMNOPQRSTUVWXYZ013'),
    ('charlie@example.com', '$2b$10$abcdefghijklmnopqrstuuABCDEFGHIJKLMNOPQRSTUVWXYZ014');

-- ============================================
-- ARTICLES: 10 sample news articles
-- ============================================
INSERT INTO articles (title, content, url, source, published_at) VALUES
    ('Apple Reports Record Q4 Earnings',
     'Apple Inc. reported quarterly revenue of $94.9 billion, beating analyst expectations by 3%. iPhone sales drove the majority of growth.',
     'https://example.com/apple-q4-earnings',
     'reuters', '2026-01-28 16:30:00+00'),

    ('NVIDIA Unveils Next-Gen AI Chip',
     'NVIDIA announced its new Blackwell Ultra GPU architecture, promising 4x performance improvements for AI training workloads.',
     'https://example.com/nvidia-blackwell-ultra',
     'cnbc', '2026-02-01 09:00:00+00'),

    ('Tesla Recalls 500K Vehicles Over Steering Issue',
     'Tesla is recalling approximately 500,000 Model 3 and Model Y vehicles due to a potential steering rack bolt defect.',
     'https://example.com/tesla-recall-steering',
     'reuters', '2026-02-03 14:15:00+00'),

    ('Microsoft Azure Revenue Surges 35%',
     'Microsoft reported Azure cloud revenue growth of 35% year-over-year, exceeding Wall Street estimates.',
     'https://example.com/msft-azure-growth',
     'bloomberg', '2026-02-05 17:00:00+00'),

    ('Google Announces $5B Stock Buyback',
     'Alphabet announced a new $5 billion share repurchase program alongside strong advertising revenue numbers.',
     'https://example.com/google-buyback',
     'cnbc', '2026-02-06 20:00:00+00'),

    ('Apple Acquires AI Startup for $2B',
     'Apple has acquired machine learning startup NeuralEdge for approximately $2 billion to bolster its on-device AI capabilities.',
     'https://example.com/apple-neuralgedge',
     'techcrunch', '2026-02-07 11:30:00+00'),

    ('NVIDIA Partners with Major Automakers on Self-Driving',
     'NVIDIA signed partnerships with BMW, Mercedes, and Toyota to supply its DRIVE Thor chips for autonomous driving platforms.',
     'https://example.com/nvidia-auto-deals',
     'reuters', '2026-02-08 08:45:00+00'),

    ('Tesla FSD v13 Gets Regulatory Approval in EU',
     'The European Union has granted conditional approval for Tesla Full Self-Driving version 13 on public roads.',
     'https://example.com/tesla-fsd-eu',
     'bloomberg', '2026-02-09 13:00:00+00'),

    ('Microsoft and OpenAI Expand Partnership',
     'Microsoft announced an additional $10 billion investment in OpenAI, deepening the strategic alliance for enterprise AI.',
     'https://example.com/msft-openai-expand',
     'cnbc', '2026-02-10 15:30:00+00'),

    ('Tech Sector Selloff Hits FAANG Stocks',
     'A broad tech selloff driven by rising interest rate concerns sent Apple, Google, Microsoft, NVIDIA, and Tesla shares lower.',
     'https://example.com/tech-selloff-faang',
     'reuters', '2026-02-12 21:00:00+00');

-- ============================================
-- EVENTS: Classified events from each article
-- ============================================
INSERT INTO events (article_id, event_type, sentiment) VALUES
    (1,  'earnings_beat',     'positive'),
    (2,  'product_launch',    'positive'),
    (3,  'product_recall',    'negative'),
    (4,  'earnings_beat',     'positive'),
    (5,  'buyback',           'positive'),
    (6,  'acquisition',       'positive'),
    (7,  'partnership',       'positive'),
    (8,  'regulatory',        'positive'),
    (9,  'partnership',       'positive'),
    (10, 'market_downturn',   'negative');

-- ============================================
-- EVENT_STOCKS: Link events to mentioned stocks
-- ============================================
INSERT INTO event_stocks (event_id, stock_id) VALUES
    (1,  1),   -- Apple earnings → AAPL
    (2,  2),   -- NVIDIA chip → NVDA
    (3,  3),   -- Tesla recall → TSLA
    (4,  4),   -- Azure growth → MSFT
    (5,  5),   -- Google buyback → GOOGL
    (6,  1),   -- Apple acquisition → AAPL
    (7,  2),   -- NVIDIA auto deals → NVDA
    (8,  3),   -- Tesla FSD → TSLA
    (9,  4),   -- MSFT-OpenAI → MSFT
    (10, 1),   -- Selloff → AAPL
    (10, 2),   -- Selloff → NVDA
    (10, 3),   -- Selloff → TSLA
    (10, 4),   -- Selloff → MSFT
    (10, 5);   -- Selloff → GOOGL

-- ============================================
-- WATCHLISTS: Users watching stocks
-- ============================================
INSERT INTO watchlists (user_id, stock_id) VALUES
    (1, 1),  -- alice watches AAPL
    (1, 2),  -- alice watches NVDA
    (1, 3),  -- alice watches TSLA
    (2, 4),  -- bob watches MSFT
    (2, 5),  -- bob watches GOOGL
    (3, 1),  -- charlie watches AAPL
    (3, 2);  -- charlie watches NVDA

-- ============================================
-- ALERTS: Some already-sent alerts
-- ============================================
INSERT INTO alerts_sent (user_id, event_id) VALUES
    (1, 1),  -- alice got Apple earnings alert
    (1, 2),  -- alice got NVIDIA chip alert
    (2, 4),  -- bob got Azure growth alert
    (3, 1);  -- charlie got Apple earnings alert

COMMIT;
