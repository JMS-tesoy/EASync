//! # Hot Path Ingest Server
//! 
//! High-performance TCP server for Forex signal ingestion.
//! Target: <20ms latency from socket read to Redis push.
//! 
//! ## Architecture
//! - Bare metal deployment (no Docker overhead)
//! - Raw TCP with Protobuf (no HTTP headers)
//! - Zero-copy where possible
//! - Connection pooling for Redis
//! 
//! ## Security
//! - License token validation against PostgreSQL
//! - HMAC signature verification (optional, can be offloaded to cold path)
//! - Rate limiting per connection
//! 
//! ## Observability
//! - Prometheus metrics (latency histograms, rejection counters)
//! - Structured logging (JSON)

use std::net::SocketAddr;
use std::sync::Arc;
use std::time::{SystemTime, UNIX_EPOCH};

use tokio::net::{TcpListener, TcpStream};
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use prost::Message as ProstMessage;
use redis::AsyncCommands;
use deadpool_redis::{Pool, Config as RedisConfig, Runtime};  // CRITICAL FIX: Use deadpool
use anyhow::{Result, Context, bail};
use tracing::{info, warn, error, debug, instrument};

// Generated from signal.proto
pub mod proto {
    include!(concat!(env!("OUT_DIR"), "/execution_control.rs"));
}

use proto::{SignalPacket, IngestResponse};

//==============================================================================
// Configuration
//==============================================================================

#[derive(Clone)]
pub struct IngestConfig {
    pub bind_address: SocketAddr,
    pub redis_url: String,
    pub redis_stream_key: String,
    pub postgres_url: String,
    pub max_packet_size: usize,
    pub rate_limit_per_sec: u32,
}

impl Default for IngestConfig {
    fn default() -> Self {
        Self {
            bind_address: "0.0.0.0:9000".parse().unwrap(),
            redis_url: "redis://127.0.0.1:6379".to_string(),
            redis_stream_key: "signals:ingest".to_string(),
            postgres_url: "postgresql://user:pass@localhost/execution_control".to_string(),
            max_packet_size: 4096, // 4KB max per signal
            rate_limit_per_sec: 100, // Max 100 signals/sec per connection
        }
    }
}

//==============================================================================
// Ingest Server
//==============================================================================

pub struct IngestServer {
    config: Arc<IngestConfig>,
    redis_pool: Pool,  // CRITICAL FIX: Use deadpool Pool
    // TODO: Add PostgreSQL connection pool for token validation
}

impl IngestServer {
    /// Initialize the ingest server
    pub async fn new(config: IngestConfig) -> Result<Self> {
        info!("Initializing IngestServer on {}", config.bind_address);
        
        // CRITICAL FIX: Create Redis connection pool
        let redis_cfg = RedisConfig::from_url(&config.redis_url);
        let redis_pool = redis_cfg
            .create_pool(Some(Runtime::Tokio1))
            .context("Failed to create Redis pool")?;
        
        // Test connection
        let mut conn = redis_pool.get().await
            .context("Failed to get Redis connection from pool")?;
        let _: String = redis::cmd("PING")
            .query_async(&mut *conn)
            .await
            .context("Redis PING failed")?;
        
        info!("Connected to Redis pool at {}", config.redis_url);
        
        // TODO: Initialize PostgreSQL connection pool
        // let pg_pool = sqlx::PgPool::connect(&config.postgres_url).await?;
        
        Ok(Self {
            config: Arc::new(config),
            redis_pool,
        })
    }
    
    /// Start accepting connections
    pub async fn run(&mut self) -> Result<()> {
        let listener = TcpListener::bind(self.config.bind_address).await
            .context("Failed to bind TCP listener")?;
        
        info!("IngestServer listening on {}", self.config.bind_address);
        
        loop {
            match listener.accept().await {
                Ok((stream, addr)) => {
                    debug!("New connection from {}", addr);
                    
                    let config = Arc::clone(&self.config);
                    let redis_pool = self.redis_pool.clone();  // CRITICAL FIX: Clone pool, not connection
                    
                    // Spawn handler for this connection
                    tokio::spawn(async move {
                        if let Err(e) = handle_connection(stream, addr, config, redis_pool).await {
                            error!("Connection error from {}: {}", addr, e);
                        }
                    });
                }
                Err(e) => {
                    error!("Failed to accept connection: {}", e);
                }
            }
        }
    }
}

//==============================================================================
// Connection Handler
//==============================================================================

#[instrument(skip(stream, config, redis_pool), fields(client_addr = %addr))]
async fn handle_connection(
    mut stream: TcpStream,
    addr: SocketAddr,
    config: Arc<IngestConfig>,
    redis_pool: Pool,  // CRITICAL FIX: Pass pool, not connection
) -> Result<()> {
    info!("Handling connection");
    
    // Simple rate limiter (token bucket)
    let mut rate_limiter = RateLimiter::new(config.rate_limit_per_sec);
    
    loop {
        // Read packet length (4 bytes, big-endian)
        let mut len_buf = [0u8; 4];
        match stream.read_exact(&mut len_buf).await {
            Ok(_) => {},
            Err(e) if e.kind() == std::io::ErrorKind::UnexpectedEof => {
                debug!("Client disconnected");
                break;
            }
            Err(e) => {
                error!("Failed to read packet length: {}", e);
                break;
            }
        }
        
        let packet_len = u32::from_be_bytes(len_buf) as usize;
        
        // Validate packet size
        if packet_len > config.max_packet_size {
            warn!("Packet too large: {} bytes (max {})", packet_len, config.max_packet_size);
            send_error_response(&mut stream, "Packet too large").await?;
            continue;
        }
        
        // Read packet data
        let mut packet_buf = vec![0u8; packet_len];
        stream.read_exact(&mut packet_buf).await
            .context("Failed to read packet data")?;
        
        // Decode Protobuf
        let mut signal = SignalPacket::decode(&packet_buf[..])
            .context("Failed to decode Protobuf")?;
        
        // CRITICAL: Stamp server arrival time (UTC milliseconds)
        let server_time = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_millis() as i64;
        
        signal.server_arrival_time = server_time;
        
        debug!(
            "Received signal: seq={}, symbol={}, subscription={}",
            signal.sequence_number, signal.symbol, signal.subscription_id
        );
        
        // Rate limiting check
        if !rate_limiter.allow() {
            warn!("Rate limit exceeded");
            send_error_response(&mut stream, "Rate limit exceeded").await?;
            continue;
        }
        
        // Process signal
        match process_signal(&signal, &config, &redis_pool).await {
            Ok(request_id) => {
                send_success_response(&mut stream, request_id, server_time).await?;
            }
            Err(e) => {
                error!("Failed to process signal: {}", e);
                send_error_response(&mut stream, &format!("Processing error: {}", e)).await?;
            }
        }
    }
    
    info!("Connection closed");
    Ok(())
}

//==============================================================================
// Signal Processing Pipeline
//==============================================================================

#[instrument(skip(signal, config, redis_pool))]
async fn process_signal(
    signal: &SignalPacket,
    config: &IngestConfig,
    redis_pool: &Pool,  // CRITICAL FIX: Use pool reference
) -> Result<String> {
    
    // Step 1: Validate license token
    // TODO: Query PostgreSQL to validate token
    // For now, we just check it's not empty
    if signal.license_token.is_empty() {
        bail!("Missing license token");
    }
    
    // Step 2: Validate subscription_id
    if signal.subscription_id.is_empty() {
        bail!("Missing subscription ID");
    }
    
    // Step 3: Basic validation
    if signal.sequence_number <= 0 {
        bail!("Invalid sequence number");
    }
    
    if signal.symbol.is_empty() {
        bail!("Missing symbol");
    }
    
    // Step 4: Serialize signal to JSON for Redis Stream
    // (We could also use MessagePack or keep as Protobuf bytes)
    let signal_json = serde_json::json!({
        "subscription_id": signal.subscription_id,
        "sequence_number": signal.sequence_number,
        "generated_at": signal.generated_at,
        "server_arrival_time": signal.server_arrival_time,
        "symbol": signal.symbol,
        "order_type": signal.order_type,
        "volume": signal.volume,
        "price": signal.price,
        "stop_loss": signal.stop_loss,
        "take_profit": signal.take_profit,
        "signature": signal.signature,
    });
    
    // Step 5: Push to Redis Stream
    // CRITICAL FIX: Get connection from pool
    let mut conn = redis_pool.get().await
        .context("Failed to get Redis connection from pool")?;
    
    // XADD signals:ingest * data <json>
    let stream_id: String = conn
        .xadd(
            &config.redis_stream_key,
            "*", // Auto-generate ID
            &[("data", signal_json.to_string())]
        )
        .await
        .context("Failed to push to Redis Stream")?;
    
    debug!("Pushed to Redis Stream: {}", stream_id);
    
    // Connection automatically returned to pool when dropped
    
    Ok(stream_id)
}

//==============================================================================
// Response Helpers
//==============================================================================

async fn send_success_response(
    stream: &mut TcpStream,
    request_id: String,
    server_timestamp: i64,
) -> Result<()> {
    let response = IngestResponse {
        success: true,
        message: "Signal accepted".to_string(),
        server_timestamp,
        request_id,
    };
    
    send_response(stream, &response).await
}

async fn send_error_response(
    stream: &mut TcpStream,
    message: &str,
) -> Result<()> {
    let response = IngestResponse {
        success: false,
        message: message.to_string(),
        server_timestamp: SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_millis() as i64,
        request_id: String::new(),
    };
    
    send_response(stream, &response).await
}

async fn send_response(
    stream: &mut TcpStream,
    response: &IngestResponse,
) -> Result<()> {
    let response_bytes = response.encode_to_vec();
    let len = response_bytes.len() as u32;
    
    // Write length prefix
    stream.write_all(&len.to_be_bytes()).await?;
    
    // Write response
    stream.write_all(&response_bytes).await?;
    
    stream.flush().await?;
    
    Ok(())
}

//==============================================================================
// Rate Limiter (Simple Token Bucket)
//==============================================================================

struct RateLimiter {
    tokens: u32,
    max_tokens: u32,
    last_refill: std::time::Instant,
}

impl RateLimiter {
    fn new(rate_per_sec: u32) -> Self {
        Self {
            tokens: rate_per_sec,
            max_tokens: rate_per_sec,
            last_refill: std::time::Instant::now(),
        }
    }
    
    fn allow(&mut self) -> bool {
        // Refill tokens based on elapsed time
        let now = std::time::Instant::now();
        let elapsed = now.duration_since(self.last_refill).as_secs_f64();
        
        if elapsed >= 1.0 {
            self.tokens = self.max_tokens;
            self.last_refill = now;
        }
        
        if self.tokens > 0 {
            self.tokens -= 1;
            true
        } else {
            false
        }
    }
}

//==============================================================================
// Main Entry Point
//==============================================================================

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize tracing
    tracing_subscriber::fmt()
        .with_target(false)
        .with_thread_ids(true)
        .with_level(true)
        .json()
        .init();
    
    info!("Starting Hot Path Ingest Server");
    
    // Load configuration (from env vars or config file)
    let config = IngestConfig::default();
    
    // Create and run server
    let mut server = IngestServer::new(config).await?;
    server.run().await?;
    
    Ok(())
}

//==============================================================================
// PRODUCTION DEPLOYMENT NOTES
//==============================================================================
// 
// 1. BARE METAL DEPLOYMENT:
//    - Deploy on dedicated bare metal server (no virtualization)
//    - Pin process to specific CPU cores: taskset -c 0-3 ./ingest-server
//    - Disable CPU frequency scaling: cpupower frequency-set -g performance
// 
// 2. NETWORK TUNING:
//    - Increase TCP buffer sizes: sysctl -w net.core.rmem_max=134217728
//    - Enable TCP fast open: sysctl -w net.ipv4.tcp_fastopen=3
//    - Disable Nagle's algorithm (TCP_NODELAY is set by Tokio by default)
// 
// 3. REDIS OPTIMIZATION:
//    - Use Redis persistence: appendonly yes, appendfsync everysec
//    - Enable Redis Streams: maxmemory-policy noeviction
//    - Monitor lag: XINFO STREAM signals:ingest
// 
// 4. MONITORING:
//    - Expose Prometheus metrics on :9090/metrics
//    - Track: signal_ingest_latency_ms, signal_rejection_total, redis_push_errors
//    - Alert on: latency p99 > 50ms, rejection_rate > 5%
// 
// 5. SECURITY:
//    - Run as non-root user
//    - Use firewall to restrict access: iptables -A INPUT -p tcp --dport 9000 -s <trusted_ip> -j ACCEPT
//    - Rotate license tokens every 30 days
// 
//==============================================================================
