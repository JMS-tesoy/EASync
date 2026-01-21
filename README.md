# Distributed Execution Control Plane

> **A production-grade, adversarial-resistant Forex trade replication system**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Rust](https://img.shields.io/badge/rust-1.75%2B-orange.svg)](https://www.rust-lang.org/)
[![PostgreSQL](https://img.shields.io/badge/postgresql-14%2B-blue.svg)](https://www.postgresql.org/)
[![TimescaleDB](https://img.shields.io/badge/timescaledb-2.x-green.svg)](https://www.timescale.com/)

## Overview

The **Distributed Execution Control Plane** is a high-frequency Forex trade replication system designed to operate in hostile environments with network jitter, toxic flow, and potential arbitrage attempts. It enables master traders to broadcast signals to multiple subscriber EAs with <20ms latency while maintaining financial integrity and adversarial defense.

### Key Features

✅ **Fail-Closed Architecture** - Reject trades on any validation failure  
✅ **Sub-20ms Latency** - Bare metal deployment with optimized hot path  
✅ **Adversarial Defense** - Multi-layer protection against replay attacks, stale signals, and price manipulation  
✅ **Financial Integrity** - Append-only ledger with High-Water Mark (HWM) billing  
✅ **Operator Visibility** - Comprehensive protection event logging and trust score system  
✅ **Production-Ready** - Complete deployment guide, security hardening, and monitoring

---

## Architecture

```
┌─────────────┐
│  Master EA  │ (MT5)
└──────┬──────┘
       │ Protobuf/TCP
       ▼
┌─────────────────────────────────────┐
│     HOT PATH (Bare Metal)           │
│  ┌──────────────┐   ┌────────────┐ │
│  │ Ingest Server│──▶│   Redis    │ │
│  │   (Rust)     │   │  Streams   │ │
│  └──────────────┘   └────────────┘ │
└─────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│    COLD PATH (Kubernetes)           │
│  ┌──────────┐  ┌────────────────┐  │
│  │  Worker  │  │ Toxic Flow     │  │
│  │ Service  │  │ Detector       │  │
│  └──────────┘  └────────────────┘  │
│  ┌──────────┐                      │
│  │ Backend  │                      │
│  │   API    │                      │
│  └──────────┘                      │
└─────────────────────────────────────┘
                │
                ▼
        ┌───────────────┐
        │  PostgreSQL + │
        │  TimescaleDB  │
        └───────────────┘
                │
                ▼
    ┌───────────────────────┐
    │  Subscriber EAs (MT5) │
    │  ExecutionGuard       │
    └───────────────────────┘
```

---

## Quick Start

### Prerequisites

- **Hot Path:** Bare metal server (Ubuntu 22.04 LTS)
- **Cold Path:** Kubernetes cluster (3+ nodes)
- **Database:** PostgreSQL 14+ with TimescaleDB 2.x
- **Message Broker:** Redis 7.x

### Installation

1. **Database Setup**
   ```bash
   # Install PostgreSQL + TimescaleDB
   sudo apt install -y postgresql-14 timescaledb-2-postgresql-14
   
   # Initialize schema
   psql -d execution_control -f schema.sql
   ```

2. **Hot Path Deployment**
   ```bash
   # Build Rust ingest server
   cd ingest-server
   cargo build --release
   
   # Deploy as systemd service
   sudo systemctl enable ingest-server
   sudo systemctl start ingest-server
   ```

3. **Cold Path Deployment**
   ```bash
   # Deploy to Kubernetes
   kubectl create namespace execution-control
   kubectl apply -f k8s/
   ```

4. **Receiver EA Setup**
   ```mql5
   // Include ExecutionGuard in your EA
   #include <ExecutionGuard.mqh>
   
   CExecutionGuard* guard;
   
   int OnInit() {
       guard = new CExecutionGuard(
           "subscription-uuid",
           50.0,  // max price deviation (pips)
           500,   // max TTL (ms)
           "secret-key"
       );
       return INIT_SUCCEEDED;
   }
   
   void OnSignal(SignalPacket &packet) {
       guard.OnSignal(packet);
   }
   ```

---

## Components

### 1. Database Schema ([schema.sql](schema.sql))

Production-grade PostgreSQL schema with:
- **subscriptions** - Master-subscriber relationships with sequence tracking
- **user_wallets** - Pre-paid credits with atomic balance operations
- **protection_logs** - TimescaleDB hypertable for high-volume rejection tracking
- **billing_ledger** - Append-only immutable financial record
- **HWM billing functions** - Performance fee calculation

### 2. MQL5 Gatekeeper ([ExecutionGuard.mqh](ExecutionGuard.mqh))

C++/MQL5 class implementing the execution pipeline:
1. **Sequence Guard** - Replay/duplicate detection
2. **TTL Shield** - Anti-lag protection (reject if age > 500ms)
3. **Price Deviation Guard** - Anti-slippage (configurable threshold)
4. **Fund Check** - Wallet balance validation
5. **Signature Validation** - HMAC-SHA256 verification
6. **State Machine** - SYNCED, DEGRADED_GAP, LOCKED_NO_FUNDS, PAUSED_TOXIC

### 3. Hot Path Ingest Server ([ingest-server/](ingest-server/))

High-performance Rust TCP server:
- Raw TCP with Protobuf (no HTTP overhead)
- License token authentication
- Server timestamp stamping
- Redis Streams producer
- Rate limiting (100 signals/sec per connection)
- Target: <20ms p99 latency

### 4. Toxic Flow Detector ([toxic_flow.py](toxic_flow.py))

Python background worker that:
- Analyzes protection_logs in rolling 24-hour window
- Calculates Trust Score (0-100) with weighted penalties
- Auto-pauses users with score < 50
- Implements recovery mechanism (+10 points per incident-free day)

---

## Security

### Defense-in-Depth

1. **Network Layer**
   - TLS/SSL encryption
   - IP whitelisting
   - Firewall rules

2. **Authentication**
   - Cryptographically secure license tokens (SHA-256 hashed)
   - HMAC-SHA256 signal signatures
   - 30-day token rotation

3. **Input Validation**
   - Protobuf schema validation
   - Sequence number monotonicity
   - Timestamp bounds checking

4. **Database Security**
   - Parameterized queries (SQL injection prevention)
   - Row-level security (RLS)
   - Encryption at rest

5. **Audit Logging**
   - Comprehensive audit trail
   - Protection event logging
   - 90-day retention

See [SECURITY.md](SECURITY.md) for complete security documentation.

---

## Performance

### Latency Targets

| Component | Target | Critical |
|-----------|--------|----------|
| Ingest Server (p99) | <20ms | >50ms |
| Database Write | <10ms | >50ms |
| API Response | <100ms | >500ms |
| End-to-End | <200ms | >1000ms |

### Throughput

- **Ingest Server:** 10,000+ signals/sec
- **Database Writes:** 5,000+ inserts/sec
- **Concurrent Subscribers:** 10,000+ EAs

### Availability

- **Uptime SLA:** 99.9%
- **RTO:** <15 minutes
- **RPO:** <1 minute

---

## Monitoring

### Prometheus Metrics

```yaml
# Key metrics exposed
- signal_ingest_latency_ms (histogram)
- signal_rejections_total (counter)
- trust_score_distribution (histogram)
- redis_stream_lag (gauge)
- database_connection_pool (gauge)
```

### Grafana Dashboards

- **Hot Path Performance** - Latency, throughput, rejection rate
- **Trust Score Overview** - User distribution, auto-pause events
- **Financial Metrics** - HWM billing, wallet balances, fee collection
- **System Health** - CPU, memory, disk, network

### Alerting

- High latency (p99 > 50ms)
- High rejection rate (>5%)
- Database connection failures
- Redis out of memory
- Trust score degradation

---

## Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture, data flow, state machines |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Infrastructure setup, deployment procedures |
| [SECURITY.md](SECURITY.md) | Threat model, security hardening, incident response |
| [schema.sql](schema.sql) | Complete database schema with comments |

---

## High-Water Mark (HWM) Billing

Fees are only charged on **new profits** above the previous high-water mark.

**Example:**
```
Trade 1: +$1,000 profit → HWM = $1,000 → Fee = $200 (20%)
Trade 2: -$500 loss    → HWM = $1,000 → Fee = $0
Trade 3: +$1,500 profit → HWM = $1,500 → Fee = $100 (20% of $500 above HWM)
```

This ensures subscribers only pay fees on actual net gains, not on recovered losses.

---

## Trust Score System

### Scoring Rules

| Event | Score Impact |
|-------|--------------|
| Successful Execution | +1 |
| TTL Expired | -5 |
| Price Deviation | -3 |
| Sequence Gap | -20 |
| Replay Attack | -50 |
| Invalid Signature | -40 |

### Auto-Pause

- **Threshold:** Score < 50
- **Action:** Subscription state → PAUSED_TOXIC
- **Recovery:** +10 points per 24 hours without incidents

---

## Operational Runbook

### Common Scenarios

#### High Latency
```bash
# Check ingest server CPU
top -p $(pgrep ingest-server)

# Check Redis memory
redis-cli INFO memory

# Check network latency
ping <MASTER_EA_IP>
```

#### Sequence Gap
```sql
-- Find affected subscriptions
SELECT user_id, subscription_id, last_sequence_id, state
FROM subscriptions
WHERE state = 'DEGRADED_GAP';

-- Trigger full sync
-- (Contact user to restart EA)
```

#### Auto-Pause Triggered
```bash
# Analyze user trust score
python toxic_flow.py --user-id <UUID> --db-url <DB_URL>

# Review protection events
# Contact user to diagnose VPS/network issues
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete runbook.

---

## Technology Stack

- **Hot Path:** Rust, Protobuf, Redis Streams
- **Cold Path:** Python (FastAPI), Kubernetes
- **Database:** PostgreSQL 14+, TimescaleDB 2.x
- **Receiver EA:** MQL5 (C++ compatible)
- **Monitoring:** Prometheus, Grafana
- **Deployment:** Bare metal + Kubernetes

---

## License

MIT License - see [LICENSE](LICENSE) for details

---

## Support

- **Documentation:** [ARCHITECTURE.md](ARCHITECTURE.md), [DEPLOYMENT.md](DEPLOYMENT.md)
- **Security Issues:** security@yourorg.com
- **General Support:** support@yourorg.com

---

## Roadmap

### Phase 2 (Q2 2026)
- Multi-region deployment (US, EU, APAC)
- GraphQL API for analytics
- Machine learning anomaly detection

### Phase 3 (Q3 2026)
- MT4 platform support
- Cryptocurrency trading
- White-label solution for brokers

---

**Built with ❤️ by the Platform Engineering Team**
