-- =====================================================================
-- LICENSE MANAGEMENT EXTENSIONS
-- =====================================================================
-- Additional tables and functions for advanced license management
-- Features: Multi-device detection, auto-renewal, usage analytics
-- =====================================================================

-- =====================================================================
-- TABLE: user_payment_methods
-- =====================================================================
-- Stores saved payment methods for auto-renewal
-- =====================================================================

CREATE TABLE user_payment_methods (
    payment_method_id   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    
    -- Payment provider details
    payment_provider    VARCHAR(50) NOT NULL,  -- 'stripe', 'paypal', etc.
    provider_customer_id VARCHAR(255) NOT NULL,  -- Customer ID in provider system
    provider_payment_id VARCHAR(255) NOT NULL,  -- Payment method ID in provider
    
    -- Card/Account details (last 4 digits only for display)
    payment_type        VARCHAR(50),  -- 'card', 'bank_account', 'paypal'
    last_four           VARCHAR(4),
    brand               VARCHAR(50),  -- 'visa', 'mastercard', etc.
    expiry_month        INTEGER,
    expiry_year         INTEGER,
    
    -- Status
    is_default          BOOLEAN NOT NULL DEFAULT FALSE,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Metadata
    billing_address     JSONB,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at        TIMESTAMPTZ,
    
    CONSTRAINT payment_method_unique UNIQUE(user_id, provider_payment_id)
);

CREATE INDEX idx_payment_methods_user ON user_payment_methods(user_id);
CREATE INDEX idx_payment_methods_default ON user_payment_methods(user_id, is_default) 
    WHERE is_default = TRUE;

-- Ensure only one default payment method per user
CREATE UNIQUE INDEX idx_payment_methods_one_default 
    ON user_payment_methods(user_id) 
    WHERE is_default = TRUE;

-- =====================================================================
-- TABLE: master_pricing
-- =====================================================================
-- Pricing configuration for master traders
-- =====================================================================

CREATE TABLE master_pricing (
    pricing_id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    master_id           UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    
    -- Fee structure
    performance_fee_pct DECIMAL(5, 2) NOT NULL DEFAULT 20.00,  -- 20%
    monthly_fee_usd     DECIMAL(10, 2) NOT NULL DEFAULT 0.00,  -- $0 (free)
    
    -- Subscription terms
    min_subscription_days INTEGER DEFAULT 30,  -- Minimum commitment
    trial_days          INTEGER DEFAULT 0,     -- Free trial period
    
    -- Limits
    max_subscribers     INTEGER,  -- NULL = unlimited
    min_deposit_usd     DECIMAL(10, 2),  -- Recommended minimum
    
    -- Status
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT pricing_one_per_master UNIQUE(master_id)
);

CREATE INDEX idx_master_pricing_master ON master_pricing(master_id);

-- =====================================================================
-- TABLE: license_usage_log
-- =====================================================================
-- Detailed log of license usage for analytics
-- =====================================================================

CREATE TABLE license_usage_log (
    log_id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    logged_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- License identity
    token_hash          VARCHAR(255) NOT NULL,
    subscription_id     UUID NOT NULL REFERENCES subscriptions(subscription_id),
    
    -- Device information
    ip_address          INET NOT NULL,
    ea_instance_id      VARCHAR(100),
    mt5_account_number  BIGINT,
    
    -- Geographic data (from IP lookup)
    country_code        VARCHAR(2),
    city                VARCHAR(100),
    latitude            DECIMAL(10, 8),
    longitude           DECIMAL(11, 8),
    
    -- Usage metrics
    signals_received    INTEGER DEFAULT 0,
    signals_executed    INTEGER DEFAULT 0,
    signals_rejected    INTEGER DEFAULT 0,
    avg_latency_ms      INTEGER,
    
    -- Session info
    session_duration_sec INTEGER,
    
    CONSTRAINT usage_log_fk_token FOREIGN KEY (token_hash) 
        REFERENCES license_tokens(token_hash) ON DELETE CASCADE
);

-- Partition by time for efficient querying
SELECT create_hypertable('license_usage_log', 'logged_at',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

CREATE INDEX idx_usage_log_subscription ON license_usage_log(subscription_id, logged_at DESC);
CREATE INDEX idx_usage_log_token ON license_usage_log(token_hash, logged_at DESC);
CREATE INDEX idx_usage_log_ip ON license_usage_log(ip_address, logged_at DESC);

-- Retention: Keep usage logs for 90 days
SELECT add_retention_policy('license_usage_log', INTERVAL '90 days', if_not_exists => TRUE);

-- =====================================================================
-- TABLE: license_renewal_history
-- =====================================================================
-- Track all renewal attempts (success and failure)
-- =====================================================================

CREATE TABLE license_renewal_history (
    renewal_id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    attempted_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- License info
    subscription_id     UUID NOT NULL REFERENCES subscriptions(subscription_id),
    user_id             UUID NOT NULL REFERENCES users(user_id),
    
    -- Renewal details
    renewal_type        VARCHAR(50) NOT NULL,  -- 'auto', 'manual'
    amount_usd          DECIMAL(10, 2) NOT NULL,
    previous_expiry     TIMESTAMPTZ,
    new_expiry          TIMESTAMPTZ,
    
    -- Payment info
    payment_method_id   UUID REFERENCES user_payment_methods(payment_method_id),
    payment_provider    VARCHAR(50),
    payment_transaction_id VARCHAR(255),
    
    -- Result
    status              VARCHAR(50) NOT NULL,  -- 'success', 'failed', 'pending'
    failure_reason      TEXT,
    
    -- Metadata
    metadata            JSONB
);

CREATE INDEX idx_renewal_history_subscription ON license_renewal_history(subscription_id, attempted_at DESC);
CREATE INDEX idx_renewal_history_user ON license_renewal_history(user_id, attempted_at DESC);
CREATE INDEX idx_renewal_history_status ON license_renewal_history(status, attempted_at DESC);

-- =====================================================================
-- TABLE: suspicious_activity_alerts
-- =====================================================================
-- Log suspicious activity for operator review
-- =====================================================================

CREATE TABLE suspicious_activity_alerts (
    alert_id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    detected_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Target
    subscription_id     UUID NOT NULL REFERENCES subscriptions(subscription_id),
    user_id             UUID NOT NULL REFERENCES users(user_id),
    token_hash          VARCHAR(255) REFERENCES license_tokens(token_hash),
    
    -- Alert details
    activity_type       VARCHAR(100) NOT NULL,  -- 'MULTIPLE_IPS', 'CONCURRENT_SESSIONS', etc.
    severity            VARCHAR(20) NOT NULL,   -- 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    description         TEXT NOT NULL,
    evidence            JSONB,  -- Supporting data (IPs, timestamps, etc.)
    
    -- Status
    status              VARCHAR(50) NOT NULL DEFAULT 'OPEN',  -- 'OPEN', 'INVESTIGATING', 'RESOLVED', 'FALSE_POSITIVE'
    resolved_at         TIMESTAMPTZ,
    resolved_by         UUID REFERENCES users(user_id),
    resolution_notes    TEXT,
    
    -- Actions taken
    auto_action_taken   VARCHAR(100),  -- 'SUSPENDED', 'NOTIFIED', 'NONE'
    
    CONSTRAINT alert_severity_check CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL'))
);

CREATE INDEX idx_alerts_subscription ON suspicious_activity_alerts(subscription_id, detected_at DESC);
CREATE INDEX idx_alerts_user ON suspicious_activity_alerts(user_id, detected_at DESC);
CREATE INDEX idx_alerts_status ON suspicious_activity_alerts(status) WHERE status = 'OPEN';
CREATE INDEX idx_alerts_severity ON suspicious_activity_alerts(severity, detected_at DESC);

-- =====================================================================
-- FUNCTIONS: License Management
-- =====================================================================

-- Function: Get unique device count for a license
CREATE OR REPLACE FUNCTION get_device_count(p_token_hash VARCHAR)
RETURNS INTEGER AS $$
DECLARE
    v_device_count INTEGER;
BEGIN
    -- Count unique device fingerprints from usage log (last 30 days)
    SELECT COUNT(DISTINCT (ip_address::text || '|' || ea_instance_id || '|' || mt5_account_number::text))
    INTO v_device_count
    FROM license_usage_log
    WHERE token_hash = p_token_hash
      AND logged_at > NOW() - INTERVAL '30 days';
    
    RETURN COALESCE(v_device_count, 0);
END;
$$ LANGUAGE plpgsql;

-- Function: Check if license is expiring soon
CREATE OR REPLACE FUNCTION is_license_expiring_soon(
    p_subscription_id UUID,
    p_days_threshold INTEGER DEFAULT 7
)
RETURNS BOOLEAN AS $$
DECLARE
    v_expires_at TIMESTAMPTZ;
BEGIN
    SELECT expires_at INTO v_expires_at
    FROM license_tokens
    WHERE subscription_id = p_subscription_id
      AND is_active = TRUE;
    
    IF v_expires_at IS NULL THEN
        RETURN FALSE;  -- No expiration = never expires
    END IF;
    
    RETURN v_expires_at <= NOW() + (p_days_threshold || ' days')::INTERVAL;
END;
$$ LANGUAGE plpgsql;

-- Function: Record license usage
CREATE OR REPLACE FUNCTION record_license_usage(
    p_token_hash VARCHAR,
    p_subscription_id UUID,
    p_ip_address INET,
    p_ea_instance_id VARCHAR,
    p_mt5_account BIGINT,
    p_signals_received INTEGER DEFAULT 1,
    p_signals_executed INTEGER DEFAULT 0,
    p_signals_rejected INTEGER DEFAULT 0,
    p_avg_latency_ms INTEGER DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    v_log_id UUID;
BEGIN
    -- Insert usage log entry
    INSERT INTO license_usage_log (
        token_hash,
        subscription_id,
        ip_address,
        ea_instance_id,
        mt5_account_number,
        signals_received,
        signals_executed,
        signals_rejected,
        avg_latency_ms
    ) VALUES (
        p_token_hash,
        p_subscription_id,
        p_ip_address,
        p_ea_instance_id,
        p_mt5_account,
        p_signals_received,
        p_signals_executed,
        p_signals_rejected,
        p_avg_latency_ms
    ) RETURNING log_id INTO v_log_id;
    
    -- Update license_tokens last_used_at and ip_address
    UPDATE license_tokens
    SET last_used_at = NOW(),
        ip_address = p_ip_address
    WHERE token_hash = p_token_hash;
    
    RETURN v_log_id;
END;
$$ LANGUAGE plpgsql;

-- Function: Create suspicious activity alert
CREATE OR REPLACE FUNCTION create_suspicious_activity_alert(
    p_subscription_id UUID,
    p_activity_type VARCHAR,
    p_severity VARCHAR,
    p_description TEXT,
    p_evidence JSONB DEFAULT NULL,
    p_auto_action VARCHAR DEFAULT 'NONE'
)
RETURNS UUID AS $$
DECLARE
    v_alert_id UUID;
    v_user_id UUID;
    v_token_hash VARCHAR;
BEGIN
    -- Get user_id and token_hash
    SELECT s.subscriber_id, lt.token_hash
    INTO v_user_id, v_token_hash
    FROM subscriptions s
    JOIN license_tokens lt ON s.subscription_id = lt.subscription_id
    WHERE s.subscription_id = p_subscription_id;
    
    -- Insert alert
    INSERT INTO suspicious_activity_alerts (
        subscription_id,
        user_id,
        token_hash,
        activity_type,
        severity,
        description,
        evidence,
        auto_action_taken
    ) VALUES (
        p_subscription_id,
        v_user_id,
        v_token_hash,
        p_activity_type,
        p_severity,
        p_description,
        p_evidence,
        p_auto_action
    ) RETURNING alert_id INTO v_alert_id;
    
    RETURN v_alert_id;
END;
$$ LANGUAGE plpgsql;

-- =====================================================================
-- VIEWS: License Analytics
-- =====================================================================

-- View: License health overview
CREATE VIEW v_license_health AS
SELECT 
    lt.subscription_id,
    s.subscriber_id,
    u.email,
    lt.is_active,
    lt.expires_at,
    CASE 
        WHEN NOT lt.is_active THEN 'REVOKED'
        WHEN lt.expires_at < NOW() THEN 'EXPIRED'
        WHEN lt.expires_at < NOW() + INTERVAL '7 days' THEN 'EXPIRING_SOON'
        ELSE 'ACTIVE'
    END as status,
    EXTRACT(DAY FROM (lt.expires_at - NOW())) as days_until_expiry,
    get_device_count(lt.token_hash) as device_count,
    lt.last_used_at,
    EXTRACT(HOUR FROM (NOW() - lt.last_used_at)) as hours_since_use,
    (
        SELECT COUNT(*) 
        FROM suspicious_activity_alerts 
        WHERE subscription_id = lt.subscription_id 
          AND status = 'OPEN'
    ) as open_alerts
FROM license_tokens lt
JOIN subscriptions s ON lt.subscription_id = s.subscription_id
JOIN users u ON s.subscriber_id = u.user_id;

-- View: Usage statistics (last 24 hours)
CREATE VIEW v_license_usage_24h AS
SELECT 
    subscription_id,
    COUNT(DISTINCT ip_address) as unique_ips,
    COUNT(DISTINCT ea_instance_id) as unique_devices,
    SUM(signals_received) as total_signals_received,
    SUM(signals_executed) as total_signals_executed,
    SUM(signals_rejected) as total_signals_rejected,
    AVG(avg_latency_ms) as avg_latency_ms,
    MAX(logged_at) as last_activity
FROM license_usage_log
WHERE logged_at > NOW() - INTERVAL '24 hours'
GROUP BY subscription_id;

-- View: Renewal candidates (expiring in next 7 days)
CREATE VIEW v_renewal_candidates AS
SELECT 
    lt.subscription_id,
    s.subscriber_id,
    u.email,
    lt.expires_at,
    EXTRACT(DAY FROM (lt.expires_at - NOW())) as days_until_expiry,
    COALESCE(mp.monthly_fee_usd, 0) as renewal_fee,
    uw.balance_usd as wallet_balance,
    CASE 
        WHEN uw.balance_usd >= COALESCE(mp.monthly_fee_usd, 0) THEN TRUE
        ELSE FALSE
    END as has_sufficient_balance,
    (
        SELECT payment_method_id 
        FROM user_payment_methods 
        WHERE user_id = u.user_id 
          AND is_default = TRUE 
          AND is_active = TRUE
        LIMIT 1
    ) as default_payment_method,
    lt.metadata->>'auto_renew' = 'true' as auto_renew_enabled
FROM license_tokens lt
JOIN subscriptions s ON lt.subscription_id = s.subscription_id
JOIN users u ON s.subscriber_id = u.user_id
JOIN user_wallets uw ON u.user_id = uw.user_id
LEFT JOIN master_pricing mp ON s.master_id = mp.master_id
WHERE lt.is_active = TRUE
  AND lt.expires_at IS NOT NULL
  AND lt.expires_at > NOW()
  AND lt.expires_at <= NOW() + INTERVAL '7 days';

-- =====================================================================
-- TRIGGERS
-- =====================================================================

-- Trigger: Update payment method updated_at
CREATE TRIGGER update_payment_methods_updated_at 
    BEFORE UPDATE ON user_payment_methods
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Trigger: Update master pricing updated_at
CREATE TRIGGER update_master_pricing_updated_at 
    BEFORE UPDATE ON master_pricing
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================================
-- COMMENTS
-- =====================================================================

COMMENT ON TABLE user_payment_methods IS 'Saved payment methods for auto-renewal';
COMMENT ON TABLE master_pricing IS 'Pricing configuration for master traders';
COMMENT ON TABLE license_usage_log IS 'TimescaleDB hypertable for detailed license usage analytics';
COMMENT ON TABLE license_renewal_history IS 'Complete history of all renewal attempts';
COMMENT ON TABLE suspicious_activity_alerts IS 'Alerts for potential license abuse or sharing';

COMMENT ON FUNCTION get_device_count IS 'Count unique devices using a license (last 30 days)';
COMMENT ON FUNCTION is_license_expiring_soon IS 'Check if license expires within threshold days';
COMMENT ON FUNCTION record_license_usage IS 'Log license usage event with device fingerprint';
COMMENT ON FUNCTION create_suspicious_activity_alert IS 'Create alert for suspicious activity';
