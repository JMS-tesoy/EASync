# Backend API - Distributed Execution Control Plane

## Overview

FastAPI backend service (cold path) for the distributed Forex trade replication platform.

## Features

- **User Authentication:** JWT-based authentication with bcrypt password hashing
- **Subscription Management:** Create and manage subscriptions with license token generation
- **Wallet Operations:** Deposit, withdraw, and view transaction history
- **Protection Events:** Log and query signal rejection events from EAs
- **Async Database:** SQLAlchemy async with PostgreSQL connection pooling
- **API Documentation:** Auto-generated Swagger UI and ReDoc

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Configuration management
│   ├── database.py          # Database connection pool
│   ├── auth.py              # JWT authentication utilities
│   ├── schemas.py           # Pydantic request/response models
│   └── api/                 # API endpoints
│       ├── __init__.py
│       ├── auth.py          # Authentication endpoints
│       ├── subscriptions.py # Subscription management
│       ├── wallets.py       # Wallet operations
│       └── protection.py    # Protection events
├── requirements.txt
├── .env.example
└── README.md
```

## Installation

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your configuration
```

Required environment variables:
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `SECRET_KEY`: JWT secret key (generate with `openssl rand -hex 32`)

### 3. Initialize Database

Ensure PostgreSQL is running and the database schema is created:

```bash
psql -U postgres -c "CREATE DATABASE execution_control;"
psql -U execution_user -d execution_control -f ../schema.sql
```

## Running the Server

### Development Mode (with auto-reload)

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Documentation

Once the server is running, visit:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **Health Check:** http://localhost:8000/health

## API Endpoints

### Authentication

- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login and get JWT token
- `GET /api/v1/auth/me` - Get current user profile

### Subscriptions

- `POST /api/v1/subscriptions` - Create subscription (returns license token)
- `GET /api/v1/subscriptions` - List user's subscriptions
- `GET /api/v1/subscriptions/{id}` - Get subscription details
- `POST /api/v1/subscriptions/{id}/pause` - Pause subscription
- `POST /api/v1/subscriptions/{id}/resume` - Resume subscription

### Wallets

- `GET /api/v1/wallet` - Get wallet balance
- `POST /api/v1/wallet/deposit` - Deposit funds
- `POST /api/v1/wallet/withdraw` - Withdraw funds
- `GET /api/v1/wallet/transactions` - Get transaction history

### Protection Events

- `POST /api/v1/protection-events` - Log protection event (from EA)
- `GET /api/v1/protection-events` - Query protection events
- `GET /api/v1/protection-events/summary` - Get event summary

## Usage Examples

### Register User

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepass123",
    "full_name": "John Doe"
  }'
```

### Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepass123"
  }'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### Create Subscription

```bash
curl -X POST http://localhost:8000/api/v1/subscriptions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{
    "master_id": "master-trader-uuid"
  }'
```

Response:
```json
{
  "subscription_id": "sub-uuid",
  "license_token": "dQw4w9WgXcQ_r7-8N3vZ5kL2mP9xYtBaC1fG4hJ6",
  "expires_at": null,
  "message": "Save this token - it won't be shown again"
}
```

## Testing

```bash
# Install pytest
pip install pytest pytest-asyncio httpx

# Run tests
pytest
```

## Security

- Passwords hashed with bcrypt
- JWT tokens with configurable expiration
- SQL injection prevention (parameterized queries)
- CORS configured for specific origins
- Rate limiting (TODO: implement)

## Performance

- Async I/O with asyncpg
- Connection pooling (20 connections, 10 overflow)
- Database query optimization
- Horizontal scaling ready (stateless)

## Deployment

### Docker

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Kubernetes

See [DEPLOYMENT.md](../DEPLOYMENT.md) for Kubernetes manifests.

## Monitoring

- Health check endpoint: `/health`
- Prometheus metrics (TODO: implement)
- Structured logging (JSON format)

## License

Proprietary - All rights reserved
