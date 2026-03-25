-- Migration 003: User email preferences + unsubscribe tokens
-- Apply with:
--   docker compose exec -T postgres psql -U signalstock -d signalstock < db/migrations/003_user_preferences.sql

BEGIN;

CREATE TABLE IF NOT EXISTS user_preferences (
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

-- Auto-seed a row for every existing user (new users get it via auth.py on register)
INSERT INTO user_preferences (user_id)
SELECT id FROM users
ON CONFLICT (user_id) DO NOTHING;

-- Unique index so we can look up by token without auth
CREATE UNIQUE INDEX IF NOT EXISTS idx_prefs_unsub_token
    ON user_preferences (unsubscribe_token);

COMMIT;
