# MCP FastAPI Freight System

A high-performance Model Context Protocol (MCP) server built with FastAPI for the freight management system. This system provides intelligent tools, resources, and prompts for freight operations, integrated with Claude AI for enhanced decision-making.

## 🚀 Features

- **FastAPI Backend**: High-performance async API server
- **MCP Integration**: Full Model Context Protocol implementation
- **PostgreSQL Database**: Robust data persistence with SQLAlchemy ORM
- **Redis Caching**: High-speed caching for improved performance
- **JWT Authentication**: Secure token-based authentication
- **Comprehensive Logging**: Structured logging with JSON output
- **OpenTelemetry**: Distributed tracing and metrics
- **Rate Limiting**: Protect APIs from abuse
- **Type Safety**: Full type hints with Pydantic validation

## 📋 Prerequisites

- Python 3.10 or higher
- PostgreSQL 14 or higher
- Redis 6 or higher
- Node.js 18+ (for MCP client)

## 🛠️ Installation

### 1. Clone the repository

```bash
cd mcp-frete-sistema
```

### 2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
# Production dependencies
pip install -r requirements.txt

# Development dependencies (includes testing tools)
pip install -r requirements-dev.txt

# Or install as package
pip install -e ".[dev]"
```

### 4. Configure environment

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 5. Setup database

```bash
# Create database
createdb frete_sistema

# Run migrations
alembic upgrade head

# Seed initial data (optional)
python scripts/seed_database.py
```

### 6. Install Redis

```bash
# Ubuntu/Debian
sudo apt-get install redis-server

# macOS
brew install redis

# Start Redis
redis-server
```

## 🚀 Running the Application

### Development Mode

```bash
# Using uvicorn directly
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Using the package entry point
mcp-frete-server

# With custom settings
APP_ENV=development uvicorn src.main:app --reload
```

### Production Mode

```bash
# Using Gunicorn with Uvicorn workers
gunicorn src.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# With environment
APP_ENV=production gunicorn src.main:app -c gunicorn.conf.py
```

## 🧪 Testing

### Run all tests

```bash
pytest
```

### Run with coverage

```bash
pytest --cov=src --cov-report=html --cov-report=term
```

### Run specific test categories

```bash
# Unit tests only
pytest tests/unit

# Integration tests
pytest tests/integration

# E2E tests
pytest tests/e2e
```

### Run with markers

```bash
# Fast tests only
pytest -m "not slow"

# Database tests
pytest -m database
```

## 📁 Project Structure

```
mcp-frete-sistema/
├── src/
│   ├── api/
│   │   ├── dependencies/    # Dependency injection
│   │   ├── endpoints/       # API endpoints
│   │   └── middleware/      # Custom middleware
│   ├── core/
│   │   ├── config.py       # Configuration
│   │   ├── security.py     # Security utilities
│   │   └── database.py     # Database setup
│   ├── models/
│   │   ├── __init__.py     # SQLAlchemy models
│   │   └── schemas.py      # Pydantic schemas
│   ├── services/
│   │   ├── mcp/           # MCP service layer
│   │   └── freight/       # Business logic
│   ├── utils/
│   │   └── logging.py     # Logging setup
│   └── main.py            # Application entry
├── tests/
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── e2e/              # End-to-end tests
├── alembic/              # Database migrations
├── scripts/              # Utility scripts
├── docs/                 # Documentation
├── prompts/              # MCP prompts
├── resources/            # MCP resources
├── tools/                # MCP tools
├── requirements.txt      # Production deps
├── requirements-dev.txt  # Dev dependencies
├── setup.py             # Package setup
├── .env.example         # Environment template
└── README.md           # This file
```

## 🔧 Configuration

### Environment Variables

Key environment variables (see `.env.example` for full list):

- `APP_ENV`: Application environment (development/staging/production)
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `SECRET_KEY`: Application secret key
- `MCP_SERVER_URL`: MCP server WebSocket URL
- `LOG_LEVEL`: Logging level (DEBUG/INFO/WARNING/ERROR)

### Database Configuration

```python
# Using DATABASE_URL
DATABASE_URL="postgresql://user:pass@localhost:5432/frete_sistema"

# Or using components
DB_HOST="localhost"
DB_PORT=5432
DB_NAME="frete_sistema"
DB_USER="postgres"
DB_PASSWORD="password"
```

## 📚 API Documentation

Once the server is running, access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## 🔌 MCP Integration

### Available Tools

1. **Query Analyzer**: Analyzes freight queries
2. **Data Loader**: Loads freight, order, and delivery data
3. **Context Manager**: Manages conversation context
4. **Response Generator**: Generates optimized responses

### Available Resources

1. **System Status**: Current system health and metrics
2. **Domain Schemas**: Database schemas and relationships
3. **User Context**: User-specific context and preferences

### Available Prompts

1. **Freight Expert**: Specialized freight domain knowledge
2. **Data Analyst**: Data analysis and insights
3. **System Helper**: System navigation and help

## 🐳 Docker Support

### Build image

```bash
docker build -t mcp-freight-system .
```

### Run with Docker Compose

```bash
docker-compose up -d
```

## 🚦 Health Checks

- **Liveness**: `GET /health/live`
- **Readiness**: `GET /health/ready`
- **Full Status**: `GET /health`

## 📊 Monitoring

### Prometheus Metrics

Available at `http://localhost:9090/metrics` when enabled.

### OpenTelemetry Traces

Configure `OTEL_EXPORTER_ENDPOINT` to send traces to your observability platform.

## 🔒 Security

- JWT-based authentication
- Role-based access control (RBAC)
- Rate limiting on all endpoints
- SQL injection protection via SQLAlchemy
- XSS protection headers
- CORS configuration

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is proprietary software. All rights reserved.

## 🆘 Support

For support, email support@freightsystem.com or create an issue in the repository.

## 🔗 Links

- [MCP Protocol Documentation](https://github.com/modelcontextprotocol/spec)
- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [SQLAlchemy Documentation](https://www.sqlalchemy.org)
- [Pydantic Documentation](https://docs.pydantic.dev)