# Multi-stage build for minimal image size
FROM rust:1.75-slim as builder

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y \
    protobuf-compiler \
    libprotobuf-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy manifests
COPY Cargo.toml Cargo.lock ./
COPY build.rs ./

# Copy source
COPY src/ ./src/
COPY ../signal.proto ./signal.proto

# Build release binary
RUN cargo build --release

# Runtime stage
FROM debian:bookworm-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy binary from builder
COPY --from=builder /app/target/release/ingest-server /usr/local/bin/ingest-server

# Create non-root user
RUN useradd -m -u 1000 ingest && \
    chown -R ingest:ingest /usr/local/bin/ingest-server

USER ingest

# Expose port
EXPOSE 9000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD nc -z localhost 9000 || exit 1

# Run server
CMD ["ingest-server"]
