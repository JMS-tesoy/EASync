-- Subscription Licenses Table
-- Links license tokens to subscriptions for EA authentication

CREATE TABLE IF NOT EXISTS subscription_licenses (
    license_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subscription_id UUID NOT NULL REFERENCES subscriptions(subscription_id) ON DELETE CASCADE,
    license_token VARCHAR(255) UNIQUE NOT NULL,
    device_id VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);

-- Index for fast license token lookups
CREATE INDEX IF NOT EXISTS idx_subscription_licenses_token ON subscription_licenses(license_token);
CREATE INDEX IF NOT EXISTS idx_subscription_licenses_subscription ON subscription_licenses(subscription_id);

-- Insert sample license for testing (links to existing subscription)
-- You should generate real tokens via the API in production
INSERT INTO subscription_licenses (subscription_id, license_token, is_active)
SELECT 
    subscription_id,
    'TEST-LICENSE-' || LEFT(subscription_id::text, 8),
    TRUE
FROM subscriptions
ON CONFLICT (license_token) DO NOTHING;
