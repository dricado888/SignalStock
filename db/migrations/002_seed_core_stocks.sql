-- Migration 002: Pre-seed core stocks
-- =====================================
-- Inserts ~25 key stocks covering all sectors used by sector_affinity.py.
-- Safe to re-run (ON CONFLICT DO NOTHING).
--
-- Apply: psql $DATABASE_URL -f db/migrations/002_seed_core_stocks.sql

INSERT INTO stocks (ticker, company_name) VALUES
    -- Mega-cap tech (already in seed_data.sql — safe to repeat)
    ('AAPL',  'Apple Inc.'),
    ('NVDA',  'NVIDIA Corporation'),
    ('TSLA',  'Tesla, Inc.'),
    ('MSFT',  'Microsoft Corporation'),
    ('GOOGL', 'Alphabet Inc.'),

    -- AI / Chip adjacent  →  TECH sector affinity
    ('AMD',   'Advanced Micro Devices, Inc.'),
    ('INTC',  'Intel Corporation'),
    ('TSM',   'Taiwan Semiconductor Manufacturing Co.'),
    ('AVGO',  'Broadcom Inc.'),
    ('QCOM',  'Qualcomm Incorporated'),
    ('ARM',   'Arm Holdings plc'),
    ('META',  'Meta Platforms, Inc.'),
    ('AMZN',  'Amazon.com, Inc.'),
    ('NFLX',  'Netflix, Inc.'),

    -- Defense  →  DEFENSE sector affinity
    ('LMT',   'Lockheed Martin Corporation'),
    ('RTX',   'RTX Corporation'),
    ('NOC',   'Northrop Grumman Corporation'),
    ('GD',    'General Dynamics Corporation'),
    ('BA',    'The Boeing Company'),

    -- Energy  →  ENERGY sector affinity
    ('XOM',   'Exxon Mobil Corporation'),
    ('CVX',   'Chevron Corporation'),
    ('COP',   'ConocoPhillips'),

    -- Finance  →  FINANCE sector affinity
    ('JPM',   'JPMorgan Chase & Co.'),
    ('GS',    'The Goldman Sachs Group, Inc.'),
    ('MS',    'Morgan Stanley'),
    ('BAC',   'Bank of America Corporation'),
    ('V',     'Visa Inc.'),
    ('MA',    'Mastercard Incorporated'),

    -- Health  →  HEALTH sector affinity
    ('JNJ',   'Johnson & Johnson'),
    ('PFE',   'Pfizer Inc.'),
    ('MRK',   'Merck & Co., Inc.'),
    ('LLY',   'Eli Lilly and Company'),

    -- Retail / Consumer  →  RETAIL sector affinity
    ('WMT',   'Walmart Inc.'),
    ('TGT',   'Target Corporation'),
    ('COST',  'Costco Wholesale Corporation'),
    ('NKE',   'Nike, Inc.')

ON CONFLICT (ticker) DO NOTHING;
