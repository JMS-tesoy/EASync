-- =====================================================================
-- DISTRIBUTED EXECUTION CONTROL PLANE - DATABASE SCHEMA
-- =====================================================================
-- PostgreSQL 14+ with TimescaleDB 2.x extension
-- Philosophy: Fail-Closed, Adversarial Defense, Operator-Grade Visibility
-- =====================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "timescaledb";

-- =====================================================================
-- ENUM TYPES
-- =====================================================================

CREATE TYPE subscription_state AS ENUM (
    'SYNCED',           -- Normal operation, all sequences in order
    'DEGRADED_GAP',     -- Sequence gap detected, awaiting full sync
    'LOCKED_NO_FUNDS',  -- Insufficient balance, execution halted
    'PAUSED_TOXIC',     -- Auto-paused due to low trust score
    'SUSPENDED_ADMIN'   -- Manually suspended by operator
);

CREATE TYPE protection_event_reason AS ENUM (
    'REPLAY_ATTACK',        -- Incoming_Seq <= Local_Last_Seq
    'DUPLICATE_SEQ',        -- Exact duplicate sequence number
    'SEQUENCE_GAP',         -- Incoming_Seq > Local_Last_Seq + 1
    'TTL_EXPIRED',          -- Signal age > 500ms
    'PRICE_DEVIATION',      -- Price slippage beyond threshold
    'INSUFFICIENT_FUNDS',   -- Wallet balance <= 0
    'STATE_LOCKED',         -- Subscription in non-SYNCED state
    'INVALID_SIGNATURE',    -- Cryptographic validation failed
    'RATE_LIMIT_EXCEEDED'   -- Too many signals per second
);

CREATE TYPE ledger_entry_type AS ENUM (
    'DEPOSIT',              -- User adds platform credits
    'WITHDRAWAL',           -- User withdraws credits
    'FEE_PERFORMANCE',      -- Performance fee (HWM-based)
    'FEE_SUBSCRIPTION',     -- Monthly subscription fee
    'REFUND',               -- Credit refund
    'ADJUSTMENT_ADMIN'      -- Manual adjustment by operator
);

-- =====================================================================
-- TABLE: users
-- =====================================================================
-- Core user identity and authentication
-- =====================================================================

CREATE TABLE users (
    user_id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email               VARCHAR(255) NOT NULL UNIQUE,
    password_hash       VARCHAR(255) NOT NULL,
    role                VARCHAR(50) NOT NULL DEFAULT 'subscriber',
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    trust_score         INTEGER NOT NULL DEFAULT 100 CHECK (trust_score BETWEEN 0 AND 100),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at       TIMESTAMPTZ,
    
    -- Indexes
    CONSTRAINT users_email_lowercase CHECK (email = LOWER(email))
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_trust_score ON users(trust_score) WHERE trust_score < 50;

-- =====================================================================
-- TABLE: user_wallets
-- =====================================================================
-- Pre-paid platform credits with atomic balance operations
-- NO pooled funds - each user has isolated balance
-- =====================================================================

CREATE TABLE user_wallets (
    wallet_id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    balance_usd         DECIMAL(18, 8) NOT NULL DEFAULT 0.00 CHECK (balance_usd >= 0),
    reserved_usd        DECIMAL(18, 8) NOT NULL DEFAULT 0.00 CHECK (reserved_usd >= 0),
    lifetime_deposits   DECIMAL(18, 8) NOT NULL DEFAULT 0.00,
    lifetime_fees       DECIMAL(18, 8) NOT NULL DEFAULT 0.00,
    version             BIGINT NOT NULL DEFAULT 0,  -- Optimistic locking version
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraint: balance + reserved must be consistent
    CONSTRAINT wallet_balance_consistency CHECK (balance_usd + reserved_usd >= 0),
    CONSTRAINT wallet_one_per_user UNIQUE(user_id)
);

CREATE INDEX idx_wallets_user_id ON user_wallets(user_id);

-- Atomic balance check function (used before trade execution)
CREATE OR REPLACE FUNCTION check_wallet_balance(
    p_user_id UUID,
    p_required_amount DECIMAL(18, 8)
) RETURNS BOOLEAN AS $$
DECLARE
    v_available DECIMAL(18, 8);
BEGIN
    -- Use NOWAIT to fail immediately if locked (prevents deadlocks)
    SELECT balance_usd INTO v_available
    FROM user_wallets
    WHERE user_id = p_user_id
    FOR UPDATE NOWAIT;  -- CRITICAL FIX: Added NOWAIT
    
    RETURN COALESCE(v_available, 0) >= p_required_amount;
EXCEPTION
    WHEN lock_not_available THEN
        -- Another transaction is modifying this wallet
        RAISE NOTICE 'Wallet locked for user %, retry later', p_user_id;
        RETURN FALSE;
END;
$$ LANGUAGE plpgsql;

-- =====================================================================
-- TABLE: subscriptions
-- =====================================================================
-- Master-Subscriber relationship with sequence tracking
-- =====================================================================

CREATE TABLE subscriptions (
    subscription_id     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    subscriber_id       UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    master_id           UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    
    -- Execution state
    state               subscription_state NOT NULL DEFAULT 'SYNCED',
    last_sequence_id    BIGINT NOT NULL DEFAULT 0,
    last_signal_at      TIMESTAMPTZ,
    
    -- Financial tracking (HWM = High-Water Mark)
    high_water_mark     DECIMAL(18, 8) NOT NULL DEFAULT 0.00,
    total_profit_usd    DECIMAL(18, 8) NOT NULL DEFAULT 0.00,
    total_fees_paid     DECIMAL(18, 8) NOT NULL DEFAULT 0.00,
    
    -- Configuration
    max_price_deviation DECIMAL(8, 4) NOT NULL DEFAULT 0.0050, -- 50 pips default
    max_ttl_ms          INTEGER NOT NULL DEFAULT 500,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Timestamps
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    paused_at           TIMESTAMPTZ,
    paused_reason       TEXT,
    
    -- Constraints
    CONSTRAINT sub_no_self_follow CHECK (subscriber_id != master_id),
    CONSTRAINT sub_unique_pair UNIQUE(subscriber_id, master_id)
);

CREATE INDEX idx_subs_subscriber ON subscriptions(subscriber_id);
CREATE INDEX idx_subs_master ON subscriptions(master_id);
CREATE INDEX idx_subs_state ON subscriptions(state) WHERE state != 'SYNCED';
CREATE INDEX idx_subs_active ON subscriptions(is_active) WHERE is_active = TRUE;

-- =====================================================================
-- TABLE: protection_logs (TimescaleDB Hypertable)
-- =====================================================================
-- High-volume rejection tracking for adversarial defense
-- Partitioned by time for efficient querying and retention
-- =====================================================================

CREATE TABLE protection_logs (
    event_id            UUID NOT NULL DEFAULT uuid_generate_v4(),
    event_time          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Identity
    subscription_id     UUID NOT NULL REFERENCES subscriptions(subscription_id) ON DELETE CASCADE,
    user_id             UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    
    -- Signal metadata
    signal_sequence     BIGINT NOT NULL,
    signal_generated_at TIMESTAMPTZ NOT NULL,
    server_arrival_time TIMESTAMPTZ NOT NULL,
    
    -- Protection event details
    reason              protection_event_reason NOT NULL,
    latency_ms          INTEGER NOT NULL, -- Age of signal when rejected
    price_deviation     DECIMAL(10, 6), -- Actual deviation if applicable
    expected_sequence   BIGINT, -- What sequence was expected
    
    -- Context
    current_state       subscription_state NOT NULL,
    wallet_balance      DECIMAL(18, 8),
    additional_metadata JSONB,
    
    -- Primary key must include time column for TimescaleDB
    PRIMARY KEY (event_time, event_id)
);

-- Convert to hypertable (partitioned by event_time)
SELECT create_hypertable('protection_logs', 'event_time', 
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Indexes for common query patterns
CREATE INDEX idx_protection_user_time ON protection_logs(user_id, event_time DESC);
CREATE INDEX idx_protection_sub_time ON protection_logs(subscription_id, event_time DESC);
CREATE INDEX idx_protection_reason ON protection_logs(reason, event_time DESC);

-- Retention policy: Keep protection logs for 90 days
SELECT add_retention_policy('protection_logs', INTERVAL '90 days', if_not_exists => TRUE);

-- =====================================================================
-- TABLE: billing_ledger
-- =====================================================================
-- Append-only immutable financial record
-- NO UPDATES, ONLY INSERTS - audit trail for all financial transactions
-- =====================================================================

CREATE TABLE billing_ledger (
    ledger_id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID NOT NULL REFERENCES users(user_id) ON DELETE RESTRICT,
    wallet_id           UUID NOT NULL REFERENCES user_wallets(wallet_id) ON DELETE RESTRICT,
    
    -- Transaction details
    entry_type          ledger_entry_type NOT NULL,
    amount_usd          DECIMAL(18, 8) NOT NULL,
    balance_before      DECIMAL(18, 8) NOT NULL,
    balance_after       DECIMAL(18, 8) NOT NULL,
    
    -- Performance fee specific fields
    profit_amount       DECIMAL(18, 8), -- Profit that triggered fee
    hwm_before          DECIMAL(18, 8), -- High-water mark before
    hwm_after           DECIMAL(18, 8), -- High-water mark after
    fee_percentage      DECIMAL(5, 2), -- e.g., 20.00 for 20%
    
    -- Metadata
    reference_id        UUID, -- Links to subscription_id or external transaction
    description         TEXT NOT NULL,
    metadata            JSONB,
    
    -- Immutability enforcement
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by          UUID REFERENCES users(user_id), -- Admin who created entry
    
    -- Constraints
    CONSTRAINT ledger_balance_math CHECK (
        (entry_type IN ('DEPOSIT', 'REFUND') AND balance_after = balance_before + amount_usd) OR
        (entry_type IN ('WITHDRAWAL', 'FEE_PERFORMANCE', 'FEE_SUBSCRIPTION') AND balance_after = balance_before - amount_usd) OR
        (entry_type = 'ADJUSTMENT_ADMIN')
    )
);

CREATE INDEX idx_ledger_user_time ON billing_ledger(user_id, created_at DESC);
CREATE INDEX idx_ledger_wallet ON billing_ledger(wallet_id, created_at DESC);
CREATE INDEX idx_ledger_type ON billing_ledger(entry_type, created_at DESC);
CREATE INDEX idx_ledger_reference ON billing_ledger(reference_id) WHERE reference_id IS NOT NULL;

-- =====================================================================
-- TABLE: signal_archive (TimescaleDB Hypertable)
-- =====================================================================
-- Complete audit trail of all signals (accepted AND rejected)
-- =====================================================================

CREATE TABLE signal_archive (
    signal_id           UUID NOT NULL DEFAULT uuid_generate_v4(),
    received_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Signal identity
    subscription_id     UUID NOT NULL REFERENCES subscriptions(subscription_id) ON DELETE CASCADE,
    sequence_number     BIGINT NOT NULL,
    
    -- Signal payload
    symbol              VARCHAR(20) NOT NULL,
    order_type          VARCHAR(10) NOT NULL, -- BUY, SELL, CLOSE
    volume              DECIMAL(18, 8) NOT NULL,
    price               DECIMAL(18, 8) NOT NULL,
    stop_loss           DECIMAL(18, 8),
    take_profit         DECIMAL(18, 8),
    
    -- Timing
    generated_at        TIMESTAMPTZ NOT NULL,
    server_arrival_time TIMESTAMPTZ NOT NULL,
    executed_at         TIMESTAMPTZ,
    
    -- Execution result
    was_executed        BOOLEAN NOT NULL DEFAULT FALSE,
    rejection_reason    protection_event_reason,
    mt5_ticket          BIGINT, -- MT5 order ticket if executed
    execution_price     DECIMAL(18, 8),
    slippage_pips       DECIMAL(8, 2),
    
    -- Metadata
    metadata            JSONB,
    
    PRIMARY KEY (received_at, signal_id)
);

SELECT create_hypertable('signal_archive', 'received_at',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

CREATE INDEX idx_signal_subscription ON signal_archive(subscription_id, received_at DESC);
CREATE INDEX idx_signal_sequence ON signal_archive(subscription_id, sequence_number);
CREATE INDEX idx_signal_executed ON signal_archive(was_executed, received_at DESC);

-- Retention: Keep signals for 1 year
SELECT add_retention_policy('signal_archive', INTERVAL '365 days', if_not_exists => TRUE);

-- =====================================================================
-- TABLE: license_tokens
-- =====================================================================
-- Authentication tokens for EA instances
-- =====================================================================

CREATE TABLE license_tokens (
    token_id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    subscription_id     UUID NOT NULL REFERENCES subscriptions(subscription_id) ON DELETE CASCADE,
    token_hash          VARCHAR(255) NOT NULL UNIQUE, -- SHA-256 hash of actual token
    
    -- Metadata
    ea_instance_id      VARCHAR(100), -- Unique identifier from EA
    last_used_at        TIMESTAMPTZ,
    ip_address          INET,
    
    -- Lifecycle
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    expires_at          TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at          TIMESTAMPTZ,
    revoked_reason      TEXT,
    
    CONSTRAINT token_active_check CHECK (
        (is_active = TRUE AND revoked_at IS NULL) OR
        (is_active = FALSE AND revoked_at IS NOT NULL)
    )
);

CREATE INDEX idx_tokens_subscription ON license_tokens(subscription_id);
CREATE INDEX idx_tokens_hash ON license_tokens(token_hash) WHERE is_active = TRUE;

-- =====================================================================
-- FUNCTIONS: High-Water Mark (HWM) Fee Calculation
-- =====================================================================

CREATE OR REPLACE FUNCTION calculate_performance_fee(
    p_subscription_id UUID,
    p_new_profit DECIMAL(18, 8),
    p_fee_percentage DECIMAL(5, 2)
) RETURNS TABLE (
    fee_amount DECIMAL(18, 8),
    new_hwm DECIMAL(18, 8),
    profit_above_hwm DECIMAL(18, 8)
) AS $$
DECLARE
    v_current_hwm DECIMAL(18, 8);
    v_profit_above_hwm DECIMAL(18, 8);
    v_fee DECIMAL(18, 8);
BEGIN
    -- Get current high-water mark
    SELECT high_water_mark INTO v_current_hwm
    FROM subscriptions
    WHERE subscription_id = p_subscription_id;
    
    -- Calculate profit above HWM
    v_profit_above_hwm := GREATEST(0, p_new_profit - v_current_hwm);
    
    -- Calculate fee only on profit above HWM
    v_fee := v_profit_above_hwm * (p_fee_percentage / 100.0);
    
    -- Return results
    RETURN QUERY SELECT 
        v_fee,
        GREATEST(v_current_hwm, p_new_profit),
        v_profit_above_hwm;
END;
$$ LANGUAGE plpgsql;

-- =====================================================================
-- FUNCTIONS: Atomic Wallet Operations
-- =====================================================================

CREATE OR REPLACE FUNCTION debit_wallet(
    p_user_id UUID,
    p_amount DECIMAL(18, 8),
    p_entry_type ledger_entry_type,
    p_description TEXT,
    p_reference_id UUID DEFAULT NULL
) RETURNS UUID AS $$
DECLARE
    v_wallet_id UUID;
    v_balance_before DECIMAL(18, 8);
    v_balance_after DECIMAL(18, 8);
    v_ledger_id UUID;
    v_current_version BIGINT;
    v_rows_updated INTEGER;
BEGIN
    -- Lock wallet row and get current balance + version
    SELECT wallet_id, balance_usd, version 
    INTO v_wallet_id, v_balance_before, v_current_version
    FROM user_wallets
    WHERE user_id = p_user_id
    FOR UPDATE NOWAIT;  -- CRITICAL FIX: Fail fast if locked
    
    -- Validate sufficient balance
    IF v_balance_before < p_amount THEN
        RAISE EXCEPTION 'Insufficient balance: % < %', v_balance_before, p_amount;
    END IF;
    
    -- Calculate new balance
    v_balance_after := v_balance_before - p_amount;
    
    -- Update wallet with optimistic locking (version check)
    UPDATE user_wallets
    SET balance_usd = v_balance_after,
        version = version + 1,  -- Increment version
        updated_at = NOW()
    WHERE wallet_id = v_wallet_id
      AND version = v_current_version  -- CRITICAL FIX: Version check
    RETURNING version INTO v_rows_updated;
    
    -- Check if update succeeded
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Concurrent modification detected - wallet was updated by another transaction';
    END IF;
    
    -- Create ledger entry
    INSERT INTO billing_ledger (
        user_id, wallet_id, entry_type, amount_usd,
        balance_before, balance_after, description, reference_id
    ) VALUES (
        p_user_id, v_wallet_id, p_entry_type, p_amount,
        v_balance_before, v_balance_after, p_description, p_reference_id
    ) RETURNING ledger_id INTO v_ledger_id;
    
    RETURN v_ledger_id;
EXCEPTION
    WHEN lock_not_available THEN
        RAISE EXCEPTION 'Wallet is locked by another transaction - please retry';
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION credit_wallet(
    p_user_id UUID,
    p_amount DECIMAL(18, 8),
    p_entry_type ledger_entry_type,
    p_description TEXT,
    p_reference_id UUID DEFAULT NULL
) RETURNS UUID AS $$
DECLARE
    v_wallet_id UUID;
    v_balance_before DECIMAL(18, 8);
    v_balance_after DECIMAL(18, 8);
    v_ledger_id UUID;
BEGIN
    -- Lock wallet row and get current balance
    SELECT wallet_id, balance_usd INTO v_wallet_id, v_balance_before
    FROM user_wallets
    WHERE user_id = p_user_id
    FOR UPDATE;
    
    -- Calculate new balance
    v_balance_after := v_balance_before + p_amount;
    
    -- Update wallet
    UPDATE user_wallets
    SET balance_usd = v_balance_after,
        lifetime_deposits = lifetime_deposits + p_amount,
        updated_at = NOW()
    WHERE wallet_id = v_wallet_id;
    
    -- Create ledger entry
    INSERT INTO billing_ledger (
        user_id, wallet_id, entry_type, amount_usd,
        balance_before, balance_after, description, reference_id
    ) VALUES (
        p_user_id, v_wallet_id, p_entry_type, p_amount,
        v_balance_before, v_balance_after, p_description, p_reference_id
    ) RETURNING ledger_id INTO v_ledger_id;
    
    RETURN v_ledger_id;
END;
$$ LANGUAGE plpgsql;

-- =====================================================================
-- TRIGGERS: Automatic timestamp updates
-- =====================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_wallets_updated_at BEFORE UPDATE ON user_wallets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_subscriptions_updated_at BEFORE UPDATE ON subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================================
-- VIEWS: Operator Dashboards
-- =====================================================================

-- Real-time protection event summary
CREATE VIEW v_protection_summary_24h AS
SELECT 
    u.user_id,
    u.email,
    u.trust_score,
    COUNT(*) as total_rejections,
    COUNT(*) FILTER (WHERE reason = 'TTL_EXPIRED') as ttl_rejections,
    COUNT(*) FILTER (WHERE reason = 'SEQUENCE_GAP') as gap_rejections,
    COUNT(*) FILTER (WHERE reason = 'PRICE_DEVIATION') as price_rejections,
    AVG(latency_ms) as avg_latency_ms,
    MAX(event_time) as last_rejection_at
FROM protection_logs p
JOIN users u ON p.user_id = u.user_id
WHERE p.event_time > NOW() - INTERVAL '24 hours'
GROUP BY u.user_id, u.email, u.trust_score
ORDER BY total_rejections DESC;

-- Wallet health overview
CREATE VIEW v_wallet_health AS
SELECT 
    u.user_id,
    u.email,
    w.balance_usd,
    w.lifetime_deposits,
    w.lifetime_fees,
    (w.lifetime_fees / NULLIF(w.lifetime_deposits, 0) * 100) as fee_percentage,
    COUNT(s.subscription_id) as active_subscriptions
FROM users u
JOIN user_wallets w ON u.user_id = w.user_id
LEFT JOIN subscriptions s ON u.user_id = s.subscriber_id AND s.is_active = TRUE
GROUP BY u.user_id, u.email, w.balance_usd, w.lifetime_deposits, w.lifetime_fees;

-- =====================================================================
-- GRANTS (Adjust based on your role structure)
-- =====================================================================

-- Example: Read-only analyst role
-- CREATE ROLE analyst_readonly;
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO analyst_readonly;
-- GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO analyst_readonly;

-- =====================================================================
-- COMMENTS (Documentation)
-- =====================================================================

COMMENT ON TABLE subscriptions IS 'Master-Subscriber relationships with sequence tracking and HWM-based billing';
COMMENT ON TABLE protection_logs IS 'TimescaleDB hypertable for high-volume rejection tracking (adversarial defense)';
COMMENT ON TABLE billing_ledger IS 'Append-only immutable financial ledger - NO UPDATES ALLOWED';
COMMENT ON TABLE user_wallets IS 'Pre-paid platform credits with atomic balance operations';
COMMENT ON COLUMN subscriptions.last_sequence_id IS 'Last successfully processed sequence number (monotonic)';
COMMENT ON COLUMN subscriptions.high_water_mark IS 'Maximum profit achieved - fees only charged above this level';
COMMENT ON FUNCTION calculate_performance_fee IS 'Calculates fee based on profit above high-water mark';
