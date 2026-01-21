# Ingest Server Testing Guide

## Prerequisites Check

### ❌ **Rust/Cargo Not Installed**

The ingest server requires Rust and Cargo to build. You have two options:

---

## Option 1: Install Rust (Recommended for Development)

### Windows Installation

1. **Download Rust installer:**
   - Visit: https://rustup.rs/
   - Download `rustup-init.exe`

2. **Run installer:**
   ```powershell
   # Run the downloaded installer
   rustup-init.exe
   
   # Follow prompts (accept defaults)
   # This installs:
   # - rustc (Rust compiler)
   # - cargo (package manager)
   # - rustup (toolchain manager)
   ```

3. **Verify installation:**
   ```powershell
   # Restart terminal, then check:
   cargo --version
   # Expected: cargo 1.75.0 (or newer)
   
   rustc --version
   # Expected: rustc 1.75.0 (or newer)
   ```

4. **Install additional tools (optional):**
   ```powershell
   # Protobuf compiler (for signal.proto)
   cargo install protobuf-codegen
   ```

---

## Option 2: Use Pre-built Docker Image (Quick Start)

If you don't want to install Rust, use Docker:

```powershell
# Build Docker image
docker build -t ingest-server:latest ./ingest-server

# Run container
docker run -p 9000:9000 \
  -e REDIS_URL=redis://host.docker.internal:6379 \
  -e DATABASE_URL=postgresql://user:pass@host.docker.internal:5432/execution_control \
  ingest-server:latest
```

---

## Building the Ingest Server

Once Rust is installed:

### Step 1: Navigate to Project

```powershell
cd "d:\Antigravity Project\Fintech Systems Architect\ingest-server"
```

### Step 2: Build Protobuf Definitions

The `build.rs` script will automatically compile `signal.proto`:

```powershell
# Check build script
cat build.rs
```

### Step 3: Build in Debug Mode (Fast)

```powershell
cargo build

# Expected output:
#    Compiling prost v0.12.x
#    Compiling tokio v1.35.x
#    Compiling ingest-server v0.1.0
#     Finished dev [unoptimized + debuginfo] target(s) in 45.2s
```

Binary location: `target/debug/ingest-server.exe`

### Step 4: Build in Release Mode (Optimized)

```powershell
cargo build --release

# Expected output:
#    Compiling ingest-server v0.1.0
#     Finished release [optimized] target(s) in 2m 15s
```

Binary location: `target/release/ingest-server.exe`

**Performance difference:**
- Debug: ~50ms latency
- Release: ~5ms latency (10x faster)

---

## Running the Ingest Server

### Prerequisites

Before running, ensure these services are running:

1. **Redis** (port 6379)
   ```powershell
   # Check if Redis is running
   redis-cli ping
   # Expected: PONG
   ```

2. **PostgreSQL** (port 5432)
   ```powershell
   # Check if PostgreSQL is running
   psql -U postgres -c "SELECT version();"
   ```

### Configuration

Edit `config.toml`:

```toml
[server]
bind_address = "0.0.0.0:9000"
max_packet_size = 4096
rate_limit_per_sec = 100

[redis]
url = "redis://127.0.0.1:6379"
stream_key = "signals:ingest"

[database]
url = "postgresql://execution_user:YOUR_PASSWORD@localhost:5432/execution_control"
```

### Run the Server

```powershell
# Debug mode (with logs)
cargo run

# Release mode (production)
cargo run --release

# Or run the binary directly
.\target\release\ingest-server.exe
```

**Expected output:**
```
2026-01-20T21:30:00Z INFO  ingest_server: Initializing IngestServer on 0.0.0.0:9000
2026-01-20T21:30:00Z INFO  ingest_server: Connected to Redis pool at redis://127.0.0.1:6379
2026-01-20T21:30:00Z INFO  ingest_server: Server listening on 0.0.0.0:9000
```

---

## Testing the Server

### Test 1: TCP Connection

```powershell
# Test if server accepts connections
Test-NetConnection -ComputerName localhost -Port 9000

# Expected:
# TcpTestSucceeded : True
```

### Test 2: Send Test Signal (Python)

Create `test_signal.py`:

```python
import socket
import struct
from datetime import datetime

# Protobuf-encoded signal (simplified)
# In production, use proper Protobuf library

def send_test_signal():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('localhost', 9000))
    
    # Simple test payload (not real Protobuf, just for connection test)
    test_data = b"TEST_SIGNAL"
    
    # Send length prefix (4 bytes) + data
    length = len(test_data)
    sock.send(struct.pack('>I', length))
    sock.send(test_data)
    
    # Receive response
    response = sock.recv(1024)
    print(f"Response: {response}")
    
    sock.close()

if __name__ == "__main__":
    send_test_signal()
```

Run:
```powershell
python test_signal.py
```

### Test 3: Verify Redis Stream

```powershell
# Check if signals are being pushed to Redis
redis-cli XREAD STREAMS signals:ingest 0

# Expected: List of signals (if any were sent)
```

### Test 4: Load Test (Apache Bench)

```powershell
# Install Apache Bench (if not installed)
# Download from: https://www.apachelounge.com/download/

# Run load test (1000 requests, 100 concurrent)
ab -n 1000 -c 100 http://localhost:9000/

# Target metrics:
# - Requests per second: > 10,000
# - p99 latency: < 20ms
# - Failed requests: 0
```

---

## Troubleshooting

### Issue: "Cannot connect to Redis"

**Solution:**
```powershell
# Start Redis (if using Windows Subsystem for Linux)
wsl redis-server

# Or use Redis for Windows
# Download from: https://github.com/microsoftarchive/redis/releases
```

### Issue: "Database connection failed"

**Solution:**
```powershell
# Verify PostgreSQL is running
Get-Service -Name postgresql*

# Test connection
psql -U execution_user -d execution_control -c "SELECT 1;"
```

### Issue: "Compilation error: protoc not found"

**Solution:**
```powershell
# Install Protocol Buffers compiler
# Download from: https://github.com/protocolbuffers/protobuf/releases
# Add to PATH

# Or use cargo plugin
cargo install protobuf-codegen
```

### Issue: "Port 9000 already in use"

**Solution:**
```powershell
# Find process using port 9000
netstat -ano | findstr :9000

# Kill process (replace PID)
taskkill /PID <PID> /F

# Or change port in config.toml
```

---

## Performance Benchmarks

### Expected Performance (Release Build)

| Metric | Target | Actual |
|--------|--------|--------|
| Throughput | 10,000 req/s | TBD |
| p50 Latency | < 5ms | TBD |
| p99 Latency | < 20ms | TBD |
| Memory Usage | < 50MB | TBD |
| CPU Usage | < 10% (idle) | TBD |

### Profiling

```powershell
# Install flamegraph
cargo install flamegraph

# Profile the server
cargo flamegraph --release

# Open flamegraph.svg in browser
```

---

## Integration Testing

### Full Signal Flow Test

1. **Start all services:**
   ```powershell
   # Terminal 1: Redis
   redis-server
   
   # Terminal 2: PostgreSQL (already running)
   
   # Terminal 3: Ingest Server
   cd ingest-server
   cargo run --release
   
   # Terminal 4: Backend API
   cd backend
   uvicorn app.main:app --reload
   ```

2. **Create test user and subscription:**
   ```powershell
   # Register user
   curl -X POST http://localhost:8000/api/v1/auth/register `
     -H "Content-Type: application/json" `
     -d '{"email":"test@example.com","password":"pass123"}'
   
   # Login
   $token = (curl -X POST http://localhost:8000/api/v1/auth/login `
     -H "Content-Type: application/json" `
     -d '{"email":"test@example.com","password":"pass123"}' | ConvertFrom-Json).access_token
   
   # Create subscription
   curl -X POST http://localhost:8000/api/v1/subscriptions `
     -H "Authorization: Bearer $token" `
     -H "Content-Type: application/json" `
     -d '{"master_id":"00000000-0000-0000-0000-000000000001"}'
   ```

3. **Send test signal to ingest server**

4. **Verify signal in Redis:**
   ```powershell
   redis-cli XREAD STREAMS signals:ingest 0
   ```

5. **Check protection logs:**
   ```powershell
   curl -H "Authorization: Bearer $token" `
     http://localhost:8000/api/v1/protection-events
   ```

---

## Next Steps

After successful testing:

1. ✅ Verify signal processing pipeline
2. ✅ Test HMAC signature validation
3. ✅ Load test with 10,000+ concurrent connections
4. ✅ Profile memory and CPU usage
5. ✅ Test Redis connection pool under load
6. ✅ Deploy to staging environment

---

## Quick Reference

```powershell
# Build
cargo build --release

# Run
cargo run --release

# Test
cargo test

# Check
cargo check

# Format
cargo fmt

# Lint
cargo clippy
```

---

## Docker Alternative (No Rust Installation Required)

Create `ingest-server/Dockerfile`:

```dockerfile
FROM rust:1.75 as builder

WORKDIR /app
COPY Cargo.toml Cargo.lock ./
COPY build.rs ./
COPY src/ ./src/
COPY ../signal.proto ./

RUN cargo build --release

FROM debian:bookworm-slim
COPY --from=builder /app/target/release/ingest-server /usr/local/bin/
CMD ["ingest-server"]
```

Build and run:
```powershell
docker build -t ingest-server .
docker run -p 9000:9000 ingest-server
```

This avoids installing Rust locally!
