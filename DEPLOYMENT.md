# Distributed Execution Control Plane - Deployment Guide

## Table of Contents
1. [System Architecture Overview](#system-architecture-overview)
2. [Infrastructure Requirements](#infrastructure-requirements)
3. [Hot Path Deployment (Rust Ingest Server)](#hot-path-deployment)
4. [Cold Path Deployment (Backend Services)](#cold-path-deployment)
5. [Database Setup](#database-setup)
6. [Security Hardening](#security-hardening)
7. [Monitoring & Observability](#monitoring--observability)
8. [Operational Runbook](#operational-runbook)

---

## System Architecture Overview

```mermaid
graph TB
    subgraph "Master EA (MT5)"
        M[Master Trader EA]
    end
    
    subgraph "Hot Path - Bare Metal"
        I[Ingest Server<br/>Rust TCP]
        R[Redis Streams<br/>Persistence Enabled]
    end
    
    subgraph "Cold Path - Kubernetes"
        W[Worker Service<br/>Python/Go]
        API[Backend API<br/>FastAPI]
        TF[Toxic Flow Detector<br/>Background Worker]
    end
    
    subgraph "Data Layer"
        PG[(PostgreSQL +<br/>TimescaleDB)]
    end
    
    subgraph "Receiver EA (MT5)"
        S1[Subscriber EA 1]
        S2[Subscriber EA 2]
        SN[Subscriber EA N]
    end
    
    M -->|Protobuf/TCP| I
    I -->|XADD| R
    R -->|Stream Consumer| W
    W -->|Write| PG
    API -->|Query| PG
    TF -->|Analyze| PG
    
    I -.->|License Check| PG
    
    R -->|WebSocket/HTTP| S1
    R -->|WebSocket/HTTP| S2
    R -->|WebSocket/HTTP| SN
    
    S1 -->|Protection Events| API
    S2 -->|Protection Events| API
    SN -->|Protection Events| API
```

---

## Infrastructure Requirements

### Hot Path (Ingest Server)
- **Hardware:** Bare metal server (no virtualization)
  - CPU: 8+ cores (Intel Xeon or AMD EPYC)
  - RAM: 16GB minimum
  - Network: 10Gbps NIC
  - Storage: NVMe SSD (for Redis persistence)
- **OS:** Ubuntu 22.04 LTS (kernel 5.15+)
- **Location:** Co-located with Forex broker data center (minimize latency)

### Cold Path (Backend Services)
- **Kubernetes Cluster:** 3+ nodes
  - CPU: 4 cores per node
  - RAM: 8GB per node
- **Cloud Provider:** AWS, GCP, or Azure

### Database
- **PostgreSQL 14+** with **TimescaleDB 2.x**
- **Instance Size:** 
  - Production: 4 vCPU, 16GB RAM, 500GB SSD
  - Staging: 2 vCPU, 8GB RAM, 100GB SSD
- **Backup:** Automated daily snapshots with 30-day retention

### Redis
- **Version:** Redis 7.x
- **Persistence:** AOF (Append-Only File) enabled
- **Memory:** 8GB minimum
- **Replication:** Master-Replica setup for high availability

---

## Hot Path Deployment

### 1. Prepare Bare Metal Server

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y build-essential pkg-config libssl-dev redis-server

# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env
```

### 2. System Tuning for Low Latency

```bash
# Disable CPU frequency scaling
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# Increase TCP buffer sizes
sudo sysctl -w net.core.rmem_max=134217728
sudo sysctl -w net.core.wmem_max=134217728
sudo sysctl -w net.ipv4.tcp_rmem="4096 87380 134217728"
sudo sysctl -w net.ipv4.tcp_wmem="4096 65536 134217728"

# Enable TCP Fast Open
sudo sysctl -w net.ipv4.tcp_fastopen=3

# Disable transparent huge pages (can cause latency spikes)
echo never | sudo tee /sys/kernel/mm/transparent_hugepage/enabled

# Make changes persistent
sudo tee -a /etc/sysctl.conf <<EOF
net.core.rmem_max=134217728
net.core.wmem_max=134217728
net.ipv4.tcp_rmem=4096 87380 134217728
net.ipv4.tcp_wmem=4096 65536 134217728
net.ipv4.tcp_fastopen=3
EOF
```

### 3. Configure Redis for Persistence

```bash
# Edit Redis configuration
sudo nano /etc/redis/redis.conf
```

Add/modify:
```conf
# Enable AOF persistence
appendonly yes
appendfsync everysec

# Disable eviction (we need all signals)
maxmemory-policy noeviction

# Set max memory (8GB)
maxmemory 8gb

# Enable Redis Streams
stream-node-max-bytes 4096
stream-node-max-entries 100
```

Restart Redis:
```bash
sudo systemctl restart redis-server
sudo systemctl enable redis-server
```

### 4. Build and Deploy Ingest Server

```bash
# Clone repository
cd /opt
sudo git clone https://github.com/yourorg/execution-control-plane.git
cd execution-control-plane/ingest-server

# Build in release mode (optimized)
cargo build --release

# Create systemd service
sudo tee /etc/systemd/system/ingest-server.service <<EOF
[Unit]
Description=Hot Path Ingest Server
After=network.target redis-server.service

[Service]
Type=simple
User=ingest
Group=ingest
WorkingDirectory=/opt/execution-control-plane/ingest-server
ExecStart=/opt/execution-control-plane/ingest-server/target/release/ingest-server
Restart=always
RestartSec=5

# CPU affinity (pin to cores 0-3)
CPUAffinity=0-3

# Environment variables
Environment="RUST_LOG=info"
Environment="REDIS_URL=redis://127.0.0.1:6379"
Environment="BIND_ADDRESS=0.0.0.0:9000"

[Install]
WantedBy=multi-user.target
EOF

# Create dedicated user
sudo useradd -r -s /bin/false ingest
sudo chown -R ingest:ingest /opt/execution-control-plane

# Start service
sudo systemctl daemon-reload
sudo systemctl enable ingest-server
sudo systemctl start ingest-server

# Check status
sudo systemctl status ingest-server
```

### 5. Firewall Configuration

```bash
# Allow only trusted IPs to connect to ingest server
sudo ufw allow from <MASTER_EA_IP> to any port 9000 proto tcp
sudo ufw enable
```

---

## Cold Path Deployment

### 1. Kubernetes Deployment (Backend API)

Create `backend-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend-api
  namespace: execution-control
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend-api
  template:
    metadata:
      labels:
        app: backend-api
    spec:
      containers:
      - name: api
        image: yourorg/backend-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
        - name: REDIS_URL
          value: "redis://redis-service:6379"
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: backend-api-service
  namespace: execution-control
spec:
  selector:
    app: backend-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

Deploy:
```bash
kubectl create namespace execution-control
kubectl apply -f backend-deployment.yaml
```

### 2. Toxic Flow Detector Worker

Create `toxic-flow-worker.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: toxic-flow-worker
  namespace: execution-control
spec:
  replicas: 2
  selector:
    matchLabels:
      app: toxic-flow-worker
  template:
    metadata:
      labels:
        app: toxic-flow-worker
    spec:
      containers:
      - name: worker
        image: yourorg/toxic-flow-worker:latest
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
        - name: CHECK_INTERVAL_SECONDS
          value: "300"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

Deploy:
```bash
kubectl apply -f toxic-flow-worker.yaml
```

---

## Database Setup

### 1. Install PostgreSQL with TimescaleDB

```bash
# Add TimescaleDB repository
sudo sh -c "echo 'deb https://packagecloud.io/timescale/timescaledb/ubuntu/ $(lsb_release -c -s) main' > /etc/apt/sources.list.d/timescaledb.list"
wget --quiet -O - https://packagecloud.io/timescale/timescaledb/gpgkey | sudo apt-key add -

# Install
sudo apt update
sudo apt install -y postgresql-14 timescaledb-2-postgresql-14

# Tune PostgreSQL for TimescaleDB
sudo timescaledb-tune --quiet --yes

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### 2. Initialize Database

```bash
# Create database and user
sudo -u postgres psql <<EOF
CREATE DATABASE execution_control;
CREATE USER execution_user WITH ENCRYPTED PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE execution_control TO execution_user;
EOF

# Enable TimescaleDB extension and run schema
sudo -u postgres psql -d execution_control <<EOF
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
\i /path/to/schema.sql
EOF
```

### 3. Configure Backups

```bash
# Install pgBackRest
sudo apt install -y pgbackrest

# Configure automated backups (daily full, hourly incremental)
sudo tee /etc/pgbackrest.conf <<EOF
[global]
repo1-path=/var/lib/pgbackrest
repo1-retention-full=30

[execution_control]
pg1-path=/var/lib/postgresql/14/main
EOF

# Add to crontab
sudo crontab -e
```

Add:
```cron
0 2 * * * pgbackrest --stanza=execution_control backup --type=full
0 * * * * pgbackrest --stanza=execution_control backup --type=incr
```

---

## Security Hardening

### 1. Network Security

- **Firewall Rules:**
  ```bash
  # Ingest server: Only allow Master EA IPs
  sudo ufw allow from <MASTER_EA_IP_1> to any port 9000
  sudo ufw allow from <MASTER_EA_IP_2> to any port 9000
  
  # PostgreSQL: Only allow backend services
  sudo ufw allow from <BACKEND_SUBNET> to any port 5432
  
  # Redis: Bind to localhost only
  sudo ufw deny 6379
  ```

- **TLS/SSL:** Use TLS for all external connections (Master EA → Ingest Server)

### 2. Authentication & Authorization

- **License Tokens:** 
  - Generate using cryptographically secure random (32+ bytes)
  - Hash with SHA-256 before storing in database
  - Rotate every 30 days
  
- **HMAC Signatures:**
  - Use HMAC-SHA256 for signal integrity
  - Secret keys stored in HashiCorp Vault or AWS Secrets Manager

### 3. Database Security

```sql
-- Revoke public access
REVOKE ALL ON SCHEMA public FROM PUBLIC;

-- Create read-only role for analytics
CREATE ROLE analyst_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO analyst_readonly;

-- Enable row-level security on sensitive tables
ALTER TABLE billing_ledger ENABLE ROW LEVEL SECURITY;
CREATE POLICY user_isolation ON billing_ledger
  USING (user_id = current_setting('app.current_user_id')::uuid);
```

### 4. Secrets Management

```bash
# Store sensitive credentials in Kubernetes secrets
kubectl create secret generic db-credentials \
  --from-literal=url='postgresql://user:pass@host/db' \
  --namespace=execution-control

# Use sealed secrets for GitOps
kubeseal --format=yaml < db-credentials.yaml > sealed-db-credentials.yaml
```

---

## Monitoring & Observability

### 1. Prometheus Metrics

Expose metrics from Ingest Server (`/metrics` endpoint):

```rust
// Add to main.rs
use prometheus::{Encoder, TextEncoder, register_histogram, register_counter};

lazy_static! {
    static ref SIGNAL_LATENCY: Histogram = register_histogram!(
        "signal_ingest_latency_ms",
        "Signal processing latency in milliseconds"
    ).unwrap();
    
    static ref SIGNAL_REJECTIONS: Counter = register_counter!(
        "signal_rejections_total",
        "Total number of rejected signals"
    ).unwrap();
}
```

### 2. Grafana Dashboards

Key metrics to monitor:
- **Latency:** p50, p95, p99 of signal processing time
- **Throughput:** Signals per second
- **Rejection Rate:** Percentage of rejected signals
- **Trust Scores:** Distribution of user trust scores
- **Redis Stream Lag:** Consumer group lag

### 3. Alerting Rules

```yaml
# prometheus-alerts.yaml
groups:
- name: execution_control
  rules:
  - alert: HighLatency
    expr: histogram_quantile(0.99, signal_ingest_latency_ms) > 50
    for: 5m
    annotations:
      summary: "Signal latency p99 > 50ms"
  
  - alert: HighRejectionRate
    expr: rate(signal_rejections_total[5m]) / rate(signal_total[5m]) > 0.05
    for: 10m
    annotations:
      summary: "Rejection rate > 5%"
  
  - alert: DatabaseConnectionFailure
    expr: up{job="postgresql"} == 0
    for: 1m
    annotations:
      summary: "PostgreSQL is down"
```

### 4. Logging

- **Structured Logging:** Use JSON format for all logs
- **Centralized:** Ship logs to ELK stack or Datadog
- **Retention:** 90 days for hot logs, 1 year for cold storage

```bash
# Configure log shipping with Filebeat
sudo apt install -y filebeat
sudo nano /etc/filebeat/filebeat.yml
```

---

## Operational Runbook

### Common Scenarios

#### Scenario 1: High Latency Alert

**Symptoms:** p99 latency > 50ms

**Diagnosis:**
```bash
# Check ingest server CPU usage
top -p $(pgrep ingest-server)

# Check Redis memory
redis-cli INFO memory

# Check network latency
ping <MASTER_EA_IP>
```

**Resolution:**
1. Check if Redis is swapping → Increase memory
2. Check CPU affinity → Ensure process is pinned to dedicated cores
3. Check network → Contact ISP if latency to Master EA is high

#### Scenario 2: Sequence Gap Detected

**Symptoms:** Multiple users in `DEGRADED_GAP` state

**Diagnosis:**
```sql
SELECT user_id, subscription_id, last_sequence_id, state
FROM subscriptions
WHERE state = 'DEGRADED_GAP'
ORDER BY updated_at DESC;
```

**Resolution:**
1. Check Redis Stream for missing entries
2. Trigger full sync for affected subscriptions
3. Investigate Master EA connectivity

#### Scenario 3: Auto-Pause Triggered

**Symptoms:** User trust score < 50, subscriptions paused

**Diagnosis:**
```bash
# Run CLI analysis
python toxic_flow.py --user-id <UUID> --db-url <DB_URL>
```

**Resolution:**
1. Review protection event breakdown
2. Contact user to diagnose VPS/network issues
3. If legitimate, manually reset trust score:
   ```sql
   UPDATE users SET trust_score = 100 WHERE user_id = '<UUID>';
   UPDATE subscriptions SET state = 'SYNCED', paused_at = NULL 
   WHERE subscriber_id = '<UUID>';
   ```

#### Scenario 4: Database Disk Full

**Symptoms:** PostgreSQL write failures

**Diagnosis:**
```bash
df -h /var/lib/postgresql
```

**Resolution:**
1. Run retention policy manually:
   ```sql
   SELECT drop_chunks('protection_logs', INTERVAL '30 days');
   SELECT drop_chunks('signal_archive', INTERVAL '180 days');
   ```
2. Increase disk size
3. Review retention policies

#### Scenario 5: Redis Out of Memory

**Symptoms:** `OOM` errors in Redis logs

**Diagnosis:**
```bash
redis-cli INFO memory | grep used_memory_human
redis-cli XINFO STREAM signals:ingest
```

**Resolution:**
1. Trim old stream entries:
   ```bash
   redis-cli XTRIM signals:ingest MAXLEN ~ 100000
   ```
2. Increase Redis memory limit
3. Ensure consumers are processing streams

---

## Performance Benchmarks

### Target SLAs

| Metric | Target | Critical Threshold |
|--------|--------|-------------------|
| Signal Latency (p99) | < 20ms | > 50ms |
| Rejection Rate | < 2% | > 5% |
| Database Write Latency | < 10ms | > 50ms |
| API Response Time | < 100ms | > 500ms |
| Uptime | 99.9% | < 99.5% |

### Load Testing

```bash
# Use Apache Bench to test ingest server
ab -n 10000 -c 100 -p signal.bin -T application/x-protobuf http://localhost:9000/

# Expected results:
# - Throughput: > 10,000 req/s
# - Latency p99: < 20ms
# - No errors
```

---

## Disaster Recovery

### Backup Strategy

1. **Database:** Daily full backups, hourly incrementals (30-day retention)
2. **Redis:** AOF persistence + daily snapshots
3. **Configuration:** Version-controlled in Git

### Recovery Procedures

**Database Restore:**
```bash
# Stop services
kubectl scale deployment backend-api --replicas=0

# Restore from backup
pgbackrest --stanza=execution_control restore --delta

# Restart services
kubectl scale deployment backend-api --replicas=3
```

**Redis Restore:**
```bash
sudo systemctl stop redis-server
sudo cp /var/lib/redis/dump.rdb.backup /var/lib/redis/dump.rdb
sudo systemctl start redis-server
```

---

## Contact & Escalation

- **On-Call Engineer:** Slack #execution-control-oncall
- **Database Issues:** DBA team (dba@yourorg.com)
- **Infrastructure:** DevOps team (devops@yourorg.com)
- **Security Incidents:** security@yourorg.com (PagerDuty)

---

**Document Version:** 1.0  
**Last Updated:** 2026-01-19  
**Maintained By:** Platform Engineering Team
