# Security Architecture - Distributed Execution Control Plane

## Threat Model

### Adversarial Assumptions

This system operates under the assumption that:

1. **Network is Hostile:** Signals may be intercepted, replayed, or tampered with
2. **Receiver EA May Be Compromised:** Running on untrusted VPS or malicious actor's machine
3. **Toxic Flow Exists:** Some users intentionally send stale/invalid signals for arbitrage
4. **Financial Incentive for Attack:** Performance fees create motivation for manipulation

### Attack Vectors

| Attack Type | Impact | Mitigation |
|-------------|--------|------------|
| **Replay Attack** | Execute stale signals for profit | Sequence number validation + TTL |
| **Man-in-the-Middle** | Signal tampering | HMAC-SHA256 signatures + TLS |
| **Sequence Gap Injection** | Force DEGRADED state, DoS | Gap detection → Full sync request |
| **Price Manipulation** | Execute at unfavorable prices | Price deviation guard (max 50 pips) |
| **Token Theft** | Unauthorized signal reception | Token rotation + IP whitelisting |
| **SQL Injection** | Data breach | Parameterized queries + ORM |
| **DDoS** | Service unavailability | Rate limiting + CloudFlare |

---

## Defense-in-Depth Strategy

### Layer 1: Network Security

#### TLS/SSL Configuration

```bash
# Generate self-signed certificate (for testing)
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# Production: Use Let's Encrypt
sudo certbot certonly --standalone -d ingest.yourorg.com
```

Update Rust ingest server to use TLS:

```rust
use tokio_rustls::{TlsAcceptor, rustls};
use std::sync::Arc;

let certs = load_certs("cert.pem")?;
let key = load_private_key("key.pem")?;

let config = rustls::ServerConfig::builder()
    .with_safe_defaults()
    .with_no_client_auth()
    .with_single_cert(certs, key)?;

let acceptor = TlsAcceptor::from(Arc::new(config));
```

#### IP Whitelisting

```sql
-- Store allowed IPs in database
CREATE TABLE allowed_ips (
    ip_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    subscription_id UUID NOT NULL REFERENCES subscriptions(subscription_id),
    ip_address INET NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    UNIQUE(subscription_id, ip_address)
);

CREATE INDEX idx_allowed_ips_lookup ON allowed_ips(ip_address, subscription_id)
WHERE expires_at IS NULL OR expires_at > NOW();
```

Validate in ingest server:

```rust
async fn validate_ip(ip: IpAddr, subscription_id: &str, db: &PgPool) -> Result<bool> {
    let result = sqlx::query!(
        "SELECT EXISTS(SELECT 1 FROM allowed_ips 
         WHERE ip_address = $1 AND subscription_id = $2 
         AND (expires_at IS NULL OR expires_at > NOW()))",
        ip,
        subscription_id
    )
    .fetch_one(db)
    .await?;
    
    Ok(result.exists.unwrap_or(false))
}
```

### Layer 2: Authentication & Authorization

#### License Token Generation

```python
import secrets
import hashlib
from datetime import datetime, timedelta

def generate_license_token(subscription_id: str) -> tuple[str, str]:
    """
    Generate a cryptographically secure license token.
    
    Returns:
        (token, token_hash) - Store hash in DB, send token to user
    """
    # Generate 32-byte random token
    token_bytes = secrets.token_bytes(32)
    token = token_bytes.hex()  # 64-character hex string
    
    # Hash for storage (SHA-256)
    token_hash = hashlib.sha256(token_bytes).hexdigest()
    
    return token, token_hash

# Usage
token, token_hash = generate_license_token(subscription_id)

# Store in database
await db.execute(
    """
    INSERT INTO license_tokens (subscription_id, token_hash, expires_at)
    VALUES ($1, $2, $3)
    """,
    subscription_id,
    token_hash,
    datetime.utcnow() + timedelta(days=30)
)

# Send token to user (one-time display)
print(f"Your license token: {token}")
print("IMPORTANT: Store this securely. It will not be shown again.")
```

#### HMAC Signature Verification

**Master EA (Sender):**

```cpp
// MQL5 - Generate HMAC signature
string GenerateSignature(const SignalPacket &packet, string secret_key)
{
    // Construct payload
    string payload = StringFormat(
        "%s|%lld|%lld|%s|%d|%.5f|%.5f",
        packet.subscription_id,
        packet.sequence_number,
        packet.generated_at,
        packet.symbol,
        packet.order_type,
        packet.volume,
        packet.price
    );
    
    // Calculate HMAC-SHA256
    uchar key_bytes[], payload_bytes[], signature_bytes[];
    StringToCharArray(secret_key, key_bytes);
    StringToCharArray(payload, payload_bytes);
    
    CryptEncode(CRYPT_HASH_SHA256, payload_bytes, key_bytes, signature_bytes);
    
    // Convert to hex string
    string signature = "";
    for(int i = 0; i < ArraySize(signature_bytes); i++)
        signature += StringFormat("%02x", signature_bytes[i]);
    
    return signature;
}
```

**Ingest Server (Validator):**

```rust
use hmac::{Hmac, Mac};
use sha2::Sha256;
type HmacSha256 = Hmac<Sha256>;

fn verify_signature(signal: &SignalPacket, secret_key: &str) -> Result<bool> {
    // Reconstruct payload (must match sender's format exactly)
    let payload = format!(
        "{}|{}|{}|{}|{}|{:.5}|{:.5}",
        signal.subscription_id,
        signal.sequence_number,
        signal.generated_at,
        signal.symbol,
        signal.order_type,
        signal.volume,
        signal.price
    );
    
    // Calculate expected signature
    let mut mac = HmacSha256::new_from_slice(secret_key.as_bytes())?;
    mac.update(payload.as_bytes());
    let expected = mac.finalize().into_bytes();
    
    // Compare with received signature (constant-time comparison)
    let received = hex::decode(&signal.signature)?;
    
    Ok(expected.as_slice() == received.as_slice())
}
```

### Layer 3: Input Validation

#### Protobuf Schema Validation

```rust
fn validate_signal(signal: &SignalPacket) -> Result<()> {
    // Validate subscription_id format (UUID)
    uuid::Uuid::parse_str(&signal.subscription_id)
        .context("Invalid subscription_id format")?;
    
    // Validate sequence number (must be positive)
    if signal.sequence_number <= 0 {
        bail!("Sequence number must be positive");
    }
    
    // Validate timestamp (not in future, not too old)
    let now = SystemTime::now().duration_since(UNIX_EPOCH)?.as_millis() as i64;
    if signal.generated_at > now {
        bail!("Signal timestamp is in the future");
    }
    if now - signal.generated_at > 60_000 {  // 60 seconds max age
        bail!("Signal is too old");
    }
    
    // Validate symbol (alphanumeric, max 20 chars)
    if signal.symbol.is_empty() || signal.symbol.len() > 20 {
        bail!("Invalid symbol");
    }
    if !signal.symbol.chars().all(|c| c.is_alphanumeric()) {
        bail!("Symbol contains invalid characters");
    }
    
    // Validate volume (positive, reasonable range)
    if signal.volume <= 0.0 || signal.volume > 100.0 {
        bail!("Invalid volume");
    }
    
    // Validate price (positive)
    if signal.price <= 0.0 {
        bail!("Invalid price");
    }
    
    Ok(())
}
```

### Layer 4: Database Security

#### Parameterized Queries (Prevent SQL Injection)

**WRONG (Vulnerable):**
```python
# NEVER DO THIS
user_id = request.args.get('user_id')
query = f"SELECT * FROM users WHERE user_id = '{user_id}'"
db.execute(query)
```

**CORRECT:**
```python
# Always use parameterized queries
user_id = request.args.get('user_id')
query = "SELECT * FROM users WHERE user_id = $1"
db.execute(query, user_id)
```

#### Row-Level Security (RLS)

```sql
-- Enable RLS on sensitive tables
ALTER TABLE billing_ledger ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own ledger entries
CREATE POLICY user_ledger_isolation ON billing_ledger
    FOR SELECT
    USING (user_id = current_setting('app.current_user_id')::uuid);

-- Policy: Only admins can insert ledger entries
CREATE POLICY admin_ledger_insert ON billing_ledger
    FOR INSERT
    WITH CHECK (
        current_setting('app.user_role') = 'admin'
    );

-- Set user context in application
-- (Before executing queries)
SET app.current_user_id = '<user_uuid>';
SET app.user_role = 'subscriber';
```

#### Encryption at Rest

```bash
# Enable PostgreSQL transparent data encryption (TDE)
# Using pgcrypto extension

sudo -u postgres psql -d execution_control <<EOF
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Encrypt sensitive columns
ALTER TABLE license_tokens 
ADD COLUMN secret_key_encrypted BYTEA;

-- Encrypt data
UPDATE license_tokens
SET secret_key_encrypted = pgp_sym_encrypt(secret_key, 'encryption_key');

-- Decrypt data
SELECT pgp_sym_decrypt(secret_key_encrypted, 'encryption_key') 
FROM license_tokens;
EOF
```

### Layer 5: Rate Limiting

#### Per-Connection Rate Limiting

```rust
use std::collections::HashMap;
use std::net::IpAddr;
use std::time::{Duration, Instant};

struct RateLimiter {
    limits: HashMap<IpAddr, TokenBucket>,
    max_rate: u32,  // requests per second
}

struct TokenBucket {
    tokens: f64,
    last_refill: Instant,
}

impl RateLimiter {
    fn new(max_rate: u32) -> Self {
        Self {
            limits: HashMap::new(),
            max_rate,
        }
    }
    
    fn allow(&mut self, ip: IpAddr) -> bool {
        let bucket = self.limits.entry(ip).or_insert(TokenBucket {
            tokens: self.max_rate as f64,
            last_refill: Instant::now(),
        });
        
        // Refill tokens based on elapsed time
        let now = Instant::now();
        let elapsed = now.duration_since(bucket.last_refill).as_secs_f64();
        bucket.tokens = (bucket.tokens + elapsed * self.max_rate as f64)
            .min(self.max_rate as f64);
        bucket.last_refill = now;
        
        // Check if request is allowed
        if bucket.tokens >= 1.0 {
            bucket.tokens -= 1.0;
            true
        } else {
            false
        }
    }
}
```

#### Global Rate Limiting (Redis)

```python
import redis
from datetime import datetime

async def check_rate_limit(
    redis_client: redis.Redis,
    user_id: str,
    max_requests: int = 100,
    window_seconds: int = 60
) -> bool:
    """
    Sliding window rate limiter using Redis.
    
    Returns:
        True if request is allowed, False if rate limit exceeded
    """
    key = f"rate_limit:{user_id}"
    now = datetime.utcnow().timestamp()
    window_start = now - window_seconds
    
    # Remove old entries
    redis_client.zremrangebyscore(key, 0, window_start)
    
    # Count requests in current window
    request_count = redis_client.zcard(key)
    
    if request_count >= max_requests:
        return False
    
    # Add current request
    redis_client.zadd(key, {str(now): now})
    redis_client.expire(key, window_seconds)
    
    return True
```

### Layer 6: Audit Logging

#### Comprehensive Audit Trail

```sql
-- Audit log table
CREATE TABLE audit_log (
    log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    user_id UUID REFERENCES users(user_id),
    event_type VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50),
    resource_id UUID,
    action VARCHAR(50) NOT NULL,
    ip_address INET,
    user_agent TEXT,
    request_payload JSONB,
    response_status INTEGER,
    error_message TEXT,
    metadata JSONB
);

-- Convert to hypertable for efficient querying
SELECT create_hypertable('audit_log', 'event_time');

-- Indexes
CREATE INDEX idx_audit_user ON audit_log(user_id, event_time DESC);
CREATE INDEX idx_audit_type ON audit_log(event_type, event_time DESC);
CREATE INDEX idx_audit_ip ON audit_log(ip_address, event_time DESC);
```

#### Audit Logging Middleware (FastAPI)

```python
from fastapi import Request
import logging

@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    start_time = datetime.utcnow()
    
    # Extract user info from JWT token
    user_id = request.state.user_id if hasattr(request.state, 'user_id') else None
    
    # Process request
    response = await call_next(request)
    
    # Log to audit table
    await db.execute(
        """
        INSERT INTO audit_log (
            user_id, event_type, action, ip_address, 
            user_agent, response_status
        ) VALUES ($1, $2, $3, $4, $5, $6)
        """,
        user_id,
        "API_REQUEST",
        f"{request.method} {request.url.path}",
        request.client.host,
        request.headers.get("user-agent"),
        response.status_code
    )
    
    return response
```

---

## Security Checklist

### Pre-Deployment

- [ ] All secrets stored in vault (no hardcoded credentials)
- [ ] TLS/SSL certificates configured and valid
- [ ] Database encryption at rest enabled
- [ ] Row-level security policies applied
- [ ] Rate limiting configured
- [ ] IP whitelisting enabled
- [ ] HMAC signature validation implemented
- [ ] Input validation on all endpoints
- [ ] Audit logging enabled
- [ ] Security headers configured (HSTS, CSP, etc.)

### Post-Deployment

- [ ] Penetration testing completed
- [ ] Vulnerability scanning scheduled (weekly)
- [ ] Security incident response plan documented
- [ ] Access control reviewed (principle of least privilege)
- [ ] Backup encryption verified
- [ ] Log retention policy enforced
- [ ] Token rotation schedule established
- [ ] Security training for team completed

### Ongoing

- [ ] Monthly security audits
- [ ] Quarterly dependency updates
- [ ] Annual penetration testing
- [ ] Continuous monitoring for anomalies
- [ ] Incident response drills

---

## Incident Response Plan

### Severity Levels

| Level | Description | Response Time | Escalation |
|-------|-------------|---------------|------------|
| **P0** | Active breach, data loss | Immediate | CTO, Security Team |
| **P1** | Vulnerability exploited | < 1 hour | Security Team |
| **P2** | Suspicious activity | < 4 hours | On-call Engineer |
| **P3** | Policy violation | < 24 hours | Team Lead |

### Response Procedures

#### P0: Active Breach

1. **Isolate:** Immediately disconnect affected systems
2. **Notify:** Alert security team and CTO
3. **Preserve:** Capture logs, memory dumps, network traffic
4. **Investigate:** Determine scope and attack vector
5. **Remediate:** Patch vulnerability, rotate all credentials
6. **Communicate:** Notify affected users (GDPR compliance)
7. **Post-Mortem:** Document incident and prevention measures

#### P1: Vulnerability Exploited

1. **Assess:** Determine if data was accessed/modified
2. **Contain:** Apply temporary mitigation (firewall rules, disable feature)
3. **Patch:** Deploy fix within 4 hours
4. **Verify:** Confirm vulnerability is closed
5. **Monitor:** Watch for repeat attempts

---

## Compliance

### GDPR (General Data Protection Regulation)

- **Data Minimization:** Only collect necessary user data
- **Right to Erasure:** Implement user deletion workflow
- **Data Portability:** Provide export functionality
- **Breach Notification:** Report breaches within 72 hours

### PCI DSS (Payment Card Industry)

- **No Card Storage:** Use payment processor (Stripe, PayPal)
- **Encryption:** All financial data encrypted in transit and at rest
- **Access Control:** Restrict access to financial data

### SOC 2 Type II

- **Security:** Firewalls, encryption, access controls
- **Availability:** 99.9% uptime SLA
- **Confidentiality:** NDA with employees, data classification
- **Processing Integrity:** Input validation, error handling
- **Privacy:** Privacy policy, consent management

---

**Document Version:** 1.0  
**Last Updated:** 2026-01-19  
**Maintained By:** Security Team
