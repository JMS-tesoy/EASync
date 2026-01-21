# Advanced License Management - Integration Guide

## Overview

This guide explains how to integrate the advanced license management features into your distributed execution control plane.

---

## 🎯 Features Implemented

### 1. **Multi-Device Detection**
- Tracks unique device fingerprints (IP + EA instance ID + MT5 account)
- Allows up to 2 devices per license (primary + backup)
- Detects and prevents license sharing
- Auto-suspends licenses with violations

### 2. **Auto-Renewal**
- Detects licenses expiring in next 7 days
- Attempts automatic renewal via saved payment method
- 3-day grace period after expiration
- Email notifications on success/failure

### 3. **Usage Analytics**
- Detailed usage logging (TimescaleDB hypertable)
- Geographic tracking (IP geolocation)
- Session metrics (signals received/executed/rejected)
- 90-day retention policy

### 4. **Suspicious Activity Detection**
- Multiple IPs in 24 hours
- Rapid IP changes
- Concurrent sessions
- Geographic anomalies
- Automated alerts for operators

### 5. **License Health Monitoring**
- Health score (0-100) calculation
- Usage frequency tracking
- Device count monitoring
- Actionable recommendations

---

## 📦 Installation

### Step 1: Database Schema

Run the license extensions schema:

```bash
# Connect to your database
psql -U execution_user -d execution_control

# Run the extensions
\i schema_license_extensions.sql
```

**What this creates:**
- `user_payment_methods` - Saved payment methods
- `master_pricing` - Pricing configuration
- `license_usage_log` - TimescaleDB hypertable for usage tracking
- `license_renewal_history` - Renewal attempt history
- `suspicious_activity_alerts` - Alert management
- Views for analytics and monitoring
- Helper functions

### Step 2: Python Dependencies

```bash
pip install asyncpg stripe  # or your payment gateway
```

### Step 3: Environment Variables

Add to your `.env` file:

```bash
# Payment Gateway (Stripe example)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...

# License Management
MAX_DEVICES_PER_LICENSE=2
AUTO_RENEWAL_ENABLED=true
RENEWAL_GRACE_PERIOD_DAYS=3
EXPIRY_WARNING_DAYS=7

# Monitoring
SUSPICIOUS_ACTIVITY_THRESHOLD=3
ALERT_EMAIL=security@yourplatform.com
```

---

## 🔧 Integration Steps

### 1. Update Ingest Server (Rust)

Modify `ingest-server/src/main.rs` to track device usage:

```rust
async fn process_signal(
    signal: &SignalPacket,
    config: &IngestConfig,
    redis_conn: &mut ConnectionManager,
    pg_pool: &PgPool,
) -> Result<String> {
    
    // ... existing validation ...
    
    // NEW: Track device usage
    let device_fingerprint = format!(
        "{}|{}|{}",
        client_ip,
        signal.ea_instance_id,
        signal.mt5_account_number
    );
    
    sqlx::query(
        "SELECT record_license_usage($1, $2, $3, $4, $5, 1, 0, 0, NULL)"
    )
    .bind(&token_hash)
    .bind(&signal.subscription_id)
    .bind(client_ip)
    .bind(&signal.ea_instance_id)
    .bind(signal.mt5_account_number)
    .execute(pg_pool)
    .await?;
    
    // ... rest of processing ...
}
```

### 2. Deploy Background Workers

Create systemd service files:

#### `/etc/systemd/system/multi-device-monitor.service`

```ini
[Unit]
Description=Multi-Device Monitor Worker
After=network.target postgresql.service

[Service]
Type=simple
User=execution-control
WorkingDirectory=/opt/execution-control
Environment="DATABASE_URL=postgresql://user:pass@localhost/execution_control"
ExecStart=/usr/bin/python3 -m license_management --worker multi-device
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### `/etc/systemd/system/auto-renewal.service`

```ini
[Unit]
Description=Auto-Renewal Worker
After=network.target postgresql.service

[Service]
Type=simple
User=execution-control
WorkingDirectory=/opt/execution-control
Environment="DATABASE_URL=postgresql://user:pass@localhost/execution_control"
Environment="STRIPE_SECRET_KEY=sk_live_..."
ExecStart=/usr/bin/python3 -m license_management --worker auto-renewal
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start:**

```bash
sudo systemctl enable multi-device-monitor auto-renewal
sudo systemctl start multi-device-monitor auto-renewal
```

### 3. Backend API Integration

Add endpoints to your FastAPI backend:

```python
# backend/app/api/licenses.py

from fastapi import APIRouter, Depends, HTTPException
from license_management import (
    MultiDeviceDetector,
    AutoRenewalManager,
    LicenseHealthMonitor
)

router = APIRouter(prefix="/api/v1/licenses", tags=["licenses"])

@router.get("/{subscription_id}/health")
async def get_license_health(
    subscription_id: str,
    db = Depends(get_db)
):
    """Get license health report"""
    monitor = LicenseHealthMonitor(db)
    report = await monitor.generate_health_report(subscription_id)
    
    return {
        "subscription_id": report.subscription_id,
        "status": report.status.value,
        "health_score": report.health_score,
        "days_until_expiry": report.days_until_expiry,
        "unique_devices": report.unique_devices,
        "suspicious_activities": [a.value for a in report.suspicious_activities],
        "recommendations": report.recommendations
    }

@router.post("/{subscription_id}/renew")
async def renew_license(
    subscription_id: str,
    db = Depends(get_db),
    payment_gateway = Depends(get_payment_gateway)
):
    """Manually renew a license"""
    manager = AutoRenewalManager(db, payment_gateway)
    
    # Get license info
    license_info = await db.fetchrow(
        "SELECT * FROM v_renewal_candidates WHERE subscription_id = $1",
        subscription_id
    )
    
    if not license_info:
        raise HTTPException(404, "License not found")
    
    # Process renewal
    await manager._process_single_renewal(dict(license_info))
    
    return {"message": "Renewal processed successfully"}

@router.get("/{subscription_id}/devices")
async def get_license_devices(
    subscription_id: str,
    db = Depends(get_db)
):
    """Get all devices using this license"""
    query = """
        SELECT 
            ip_address,
            ea_instance_id,
            mt5_account_number,
            country_code,
            city,
            MAX(logged_at) as last_seen,
            COUNT(*) as usage_count
        FROM license_usage_log
        WHERE subscription_id = $1
          AND logged_at > NOW() - INTERVAL '30 days'
        GROUP BY ip_address, ea_instance_id, mt5_account_number, country_code, city
        ORDER BY last_seen DESC
    """
    
    devices = await db.fetch(query, subscription_id)
    
    return {
        "subscription_id": subscription_id,
        "device_count": len(devices),
        "devices": [dict(d) for d in devices]
    }

@router.get("/alerts")
async def get_suspicious_activity_alerts(
    status: str = "OPEN",
    severity: str = None,
    db = Depends(get_db)
):
    """Get suspicious activity alerts"""
    query = """
        SELECT 
            alert_id,
            subscription_id,
            user_id,
            activity_type,
            severity,
            description,
            evidence,
            detected_at,
            status
        FROM suspicious_activity_alerts
        WHERE status = $1
    """
    
    params = [status]
    
    if severity:
        query += " AND severity = $2"
        params.append(severity)
    
    query += " ORDER BY detected_at DESC LIMIT 100"
    
    alerts = await db.fetch(query, *params)
    
    return {
        "total": len(alerts),
        "alerts": [dict(a) for a in alerts]
    }
```

### 4. Frontend Dashboard Integration

Add license health widget to user dashboard:

```javascript
// frontend/components/LicenseHealthWidget.jsx

import React, { useEffect, useState } from 'react';

export function LicenseHealthWidget({ subscriptionId }) {
  const [health, setHealth] = useState(null);
  
  useEffect(() => {
    fetch(`/api/v1/licenses/${subscriptionId}/health`)
      .then(res => res.json())
      .then(data => setHealth(data));
  }, [subscriptionId]);
  
  if (!health) return <div>Loading...</div>;
  
  const getHealthColor = (score) => {
    if (score >= 80) return 'green';
    if (score >= 50) return 'yellow';
    return 'red';
  };
  
  return (
    <div className="license-health-widget">
      <h3>License Health</h3>
      
      <div className="health-score" style={{ color: getHealthColor(health.health_score) }}>
        {health.health_score}/100
      </div>
      
      <div className="health-details">
        <p>Status: <strong>{health.status}</strong></p>
        <p>Devices: {health.unique_devices}/2</p>
        {health.days_until_expiry && (
          <p>Expires in: {health.days_until_expiry} days</p>
        )}
      </div>
      
      {health.suspicious_activities.length > 0 && (
        <div className="alert alert-warning">
          ⚠️ Suspicious activity detected:
          <ul>
            {health.suspicious_activities.map((activity, i) => (
              <li key={i}>{activity}</li>
            ))}
          </ul>
        </div>
      )}
      
      <div className="recommendations">
        {health.recommendations.map((rec, i) => (
          <p key={i}>{rec}</p>
        ))}
      </div>
    </div>
  );
}
```

---

## 🧪 Testing

### Test Multi-Device Detection

```python
# test_multi_device.py

import asyncio
import asyncpg
from license_management import MultiDeviceDetector

async def test_multi_device():
    conn = await asyncpg.connect("postgresql://...")
    detector = MultiDeviceDetector(conn, max_devices=2)
    
    token_hash = "abc123..."
    
    # Device 1 (should be allowed)
    allowed, reason = await detector.track_device_usage(
        token_hash,
        "192.168.1.1",
        "EA-INSTANCE-1",
        12345678
    )
    print(f"Device 1: {allowed}, {reason}")
    
    # Device 2 (should be allowed)
    allowed, reason = await detector.track_device_usage(
        token_hash,
        "192.168.1.2",
        "EA-INSTANCE-2",
        87654321
    )
    print(f"Device 2: {allowed}, {reason}")
    
    # Device 3 (should be REJECTED)
    allowed, reason = await detector.track_device_usage(
        token_hash,
        "192.168.1.3",
        "EA-INSTANCE-3",
        11223344
    )
    print(f"Device 3: {allowed}, {reason}")  # Expected: False, "License suspended: ..."
    
    await conn.close()

asyncio.run(test_multi_device())
```

### Test Auto-Renewal

```python
# test_auto_renewal.py

import asyncio
import asyncpg
from license_management import AutoRenewalManager
from datetime import datetime, timedelta

async def test_auto_renewal():
    conn = await asyncpg.connect("postgresql://...")
    
    # Mock payment gateway
    class MockPaymentGateway:
        async def charge(self, **kwargs):
            return {"status": "succeeded"}
    
    manager = AutoRenewalManager(conn, MockPaymentGateway())
    
    # Create test license expiring in 3 days
    await conn.execute("""
        UPDATE license_tokens
        SET expires_at = NOW() + INTERVAL '3 days',
            metadata = jsonb_set(
                COALESCE(metadata, '{}'::jsonb),
                '{auto_renew}',
                'true'
            )
        WHERE subscription_id = $1
    """, "test-subscription-id")
    
    # Run renewal process
    await manager.process_renewals()
    
    # Check if renewed
    new_expiry = await conn.fetchval(
        "SELECT expires_at FROM license_tokens WHERE subscription_id = $1",
        "test-subscription-id"
    )
    
    print(f"New expiry: {new_expiry}")  # Should be ~33 days from now
    
    await conn.close()

asyncio.run(test_auto_renewal())
```

---

## 📊 Monitoring & Alerts

### Prometheus Metrics

Add to your metrics exporter:

```python
from prometheus_client import Gauge, Counter

# Metrics
license_health_score = Gauge('license_health_score', 'License health score', ['subscription_id'])
suspicious_activities = Counter('suspicious_activities_total', 'Suspicious activities detected', ['type'])
auto_renewals = Counter('auto_renewals_total', 'Auto-renewal attempts', ['status'])
device_violations = Counter('device_violations_total', 'Multi-device violations')

# Update metrics
async def update_license_metrics(db):
    # Health scores
    licenses = await db.fetch("SELECT subscription_id, health_score FROM v_license_health")
    for license in licenses:
        license_health_score.labels(subscription_id=license['subscription_id']).set(
            license['health_score']
        )
```

### Grafana Dashboard

Import this dashboard JSON:

```json
{
  "dashboard": {
    "title": "License Management",
    "panels": [
      {
        "title": "License Health Distribution",
        "targets": [{
          "expr": "histogram_quantile(0.95, license_health_score)"
        }]
      },
      {
        "title": "Suspicious Activities (24h)",
        "targets": [{
          "expr": "increase(suspicious_activities_total[24h])"
        }]
      },
      {
        "title": "Auto-Renewal Success Rate",
        "targets": [{
          "expr": "rate(auto_renewals_total{status=\"success\"}[1h]) / rate(auto_renewals_total[1h])"
        }]
      }
    ]
  }
}
```

---

## 🚨 Troubleshooting

### Issue: Legitimate user suspended for multi-device

**Solution:**
```sql
-- Review the alert
SELECT * FROM suspicious_activity_alerts 
WHERE subscription_id = 'uuid' 
ORDER BY detected_at DESC LIMIT 1;

-- If false positive, reactivate license
UPDATE license_tokens
SET is_active = TRUE,
    revoked_at = NULL,
    revoked_reason = NULL
WHERE subscription_id = 'uuid';

-- Mark alert as false positive
UPDATE suspicious_activity_alerts
SET status = 'FALSE_POSITIVE',
    resolved_at = NOW(),
    resolution_notes = 'User has legitimate backup VPS'
WHERE alert_id = 'alert-uuid';
```

### Issue: Auto-renewal failing

**Check:**
```sql
-- View renewal history
SELECT * FROM license_renewal_history
WHERE subscription_id = 'uuid'
ORDER BY attempted_at DESC
LIMIT 10;

-- Check wallet balance
SELECT balance_usd FROM user_wallets
WHERE user_id = (
    SELECT subscriber_id FROM subscriptions WHERE subscription_id = 'uuid'
);

-- Check payment method
SELECT * FROM user_payment_methods
WHERE user_id = (
    SELECT subscriber_id FROM subscriptions WHERE subscription_id = 'uuid'
)
AND is_default = TRUE;
```

---

## ✅ Checklist

- [ ] Database schema extensions applied
- [ ] Background workers deployed and running
- [ ] Backend API endpoints integrated
- [ ] Frontend dashboard updated
- [ ] Payment gateway configured (Stripe/PayPal)
- [ ] Monitoring metrics exposed
- [ ] Grafana dashboards created
- [ ] Alert notifications configured
- [ ] Testing completed
- [ ] Documentation updated

---

## 📚 Additional Resources

- [Stripe Payment Integration](https://stripe.com/docs/api)
- [TimescaleDB Best Practices](https://docs.timescale.com/timescaledb/latest/how-to-guides/)
- [IP Geolocation API](https://ipapi.com/)
- [Prometheus Metrics](https://prometheus.io/docs/practices/naming/)

---

**Questions?** Contact the platform engineering team or refer to the main [ARCHITECTURE.md](ARCHITECTURE.md) and [DEPLOYMENT.md](DEPLOYMENT.md) documentation.
