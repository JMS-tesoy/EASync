# AGENTS.md - Development Guidelines for AI Coding Agents

This file contains build commands, testing procedures, and code style guidelines for agents working in this codebase.

---

## Build Commands

### Python (Backend)
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Rust (Ingest Server)
```bash
cd ingest-server
cargo build              # Debug build
cargo build --release    # Production build (10x faster)
cargo run --release      # Run production binary
```

### JavaScript (Dashboard)
```bash
cd dashboard
npm install
npm run dev              # Development server (Vite)
npm run build            # Production build
npm run preview          # Preview production build
```

---

## Testing

### Python
```bash
cd backend
pytest                   # Run all tests
pytest tests/test_specific.py::test_function  # Run single test
pytest -v               # Verbose output
```

Install test dependencies:
```bash
pip install pytest pytest-asyncio httpx
```

### Rust
```bash
cd ingest-server
cargo test                         # Run all tests
cargo test --lib                   # Run library tests only
cargo test -- --nocapture          # Show print output
```

### Running Single Test - Python
```bash
# Run specific test function
pytest -v path/to/test_file.py::test_function_name

# Run tests in a specific class
pytest path/to/test_file.py::TestClass

# Run tests matching a pattern
pytest -k "test_subscription"
```

---

## Linting and Type Checking

### Python
```bash
# Linting (if ruff is installed)
ruff check .
ruff format .

# Type checking (if mypy is installed)
mypy backend/app/
```

### Rust
```bash
cargo clippy          # Lint
cargo fmt             # Format
cargo check           # Quick compile check
```

### JavaScript
```bash
cd dashboard
npm run lint          # ESLint (if configured)
```

---

## Code Style Guidelines

### Python (Backend)

**Imports:**
- Group imports: stdlib → third-party → local
- Use absolute imports for local modules
- Avoid `from module import *`

```python
# Correct
import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException
from app.config import settings

# Incorrect
from datetime import *
from app.api import *
```

**Type Hints:**
- Always use type hints for function parameters and return values
- Use `Optional[T]` for nullable types
- Use `AsyncGenerator` for async generators

```python
async def get_user(user_id: str) -> Optional[User]:
    pass

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    pass
```

**Error Handling:**
- Use FastAPI's `HTTPException` for API errors
- Always log errors with appropriate level
- Use `context()` from `anyhow` in Rust for error context

```python
try:
    result = await operation()
except DatabaseError as e:
    logger.error(f"Database error: {e}")
    raise HTTPException(status_code=500, detail="Internal error")
```

**Docstrings:**
- Use triple-quoted docstrings at module and function level
- Format as shown in existing files with `=====` separators

```python
"""
Module Purpose Description
==========================

Detailed explanation of what this module does.
"""
```

**Database Operations:**
- Always use async sessions
- Use parameterized queries (SQLAlchemy handles this)
- Commit/rollback in try/except/finally blocks

---

### Rust (Ingest Server)

**Naming Conventions:**
- Structs and types: `PascalCase`
- Functions and methods: `snake_case`
- Constants: `SCREAMING_SNAKE_CASE`
- Private modules: `snake_case`

```rust
pub struct IngestServer { }
pub async fn handle_connection() { }
const MAX_PACKET_SIZE: usize = 4096;
```

**Error Handling:**
- Use `anyhow::Result<T>` for application errors
- Use `bail!()` for early error returns
- Use `.context()` to add error context

```rust
use anyhow::{Result, Context, bail};

let value = operation()
    .context("Failed to process value")?;

if condition {
    bail!("Invalid condition");
}
```

**Async Patterns:**
- Use `tokio::spawn` for concurrent tasks
- Clone Arc references instead of moving
- Use `#[instrument]` for tracing

```rust
#[instrument(skip(connection))]
async fn process_signal(connection: &mut Connection) -> Result<()> {
    // ...
}
```

**Memory Safety:**
- Use `Arc<T>` for shared state across tasks
- Clone pools, not individual connections
- Be explicit about lifetimes when needed

---

### JavaScript/React (Dashboard)

**Imports:**
- Group imports: React → third-party → local components
- Named exports preferred over default

```jsx
import { useState, useEffect } from 'react'
import { BrowserRouter } from 'react-router-dom'
import { Button } from '@/components/ui'
import Dashboard from './pages/Dashboard'
```

**Component Structure:**
- Functional components with hooks
- Destructure props in function signature
- Early returns for conditional rendering

```jsx
function Component({ title, isLoading }) {
  if (isLoading) return <LoadingSpinner />

  return <div>{title}</div>
}
```

**State Management:**
- Use `useState` for local state
- Use `useEffect` for side effects with proper dependencies
- Avoid prop drilling for complex state (use context or state library)

**Styling:**
- Import CSS from `./index.css` or co-located CSS modules
- Tailwind is available (check if configured)

---

## Security Guidelines

- Never log passwords, tokens, or secrets
- Use environment variables for sensitive configuration
- Validate all input on both client and server
- Use parameterized queries for database access
- Hash passwords with bcrypt (Python) or argon2 (Rust)

---

## Database Operations

- Connection pooling: 20 connections, 10 overflow (Python)
- Redis Streams: Use XADD for inserting, XREAD for consuming
- Always commit or rollback transactions
- Use async database operations

---

## Key File Locations

- Backend entry: `backend/app/main.py`
- Rust entry: `ingest-server/src/main.rs`
- Dashboard entry: `dashboard/src/main.jsx`
- Config: `backend/app/config.py`, `ingest-server/config.toml`
- Database: `schema.sql` (PostgreSQL)

---

## Testing Best Practices

- Write unit tests for business logic
- Integration tests should use test databases/fixtures
- Mock external services (Redis, PostgreSQL) in tests
- Test error paths, not just happy paths

---

## Performance Targets

- Rust ingest server: <20ms p99 latency
- API responses: <100ms average
- Database writes: <10ms average

---

## Debugging

- Python: Use `logger.debug()` with `settings.log_level=DEBUG`
- Rust: Use `tracing::debug!()` with `RUST_LOG=debug`
- React: Use `console.log()` or React DevTools

---

## Environment Variables

Required variables in `backend/.env`:
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `SECRET_KEY`: JWT signing key

Required variables for Rust (can be in `config.toml`):
- `REDIS_URL`: Redis connection string
- `DATABASE_URL`: PostgreSQL connection string
