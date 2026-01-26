# External Integrations

**Analysis Date:** 2026-01-25

## APIs & External Services

**Odoo ERP Integration:**
- Service - Core business system integration for orders, invoices, purchases, materials
  - SDK/Client: Direct XML-RPC via Python requests (custom wrapper in `app/odoo/`)
  - Auth: `ODOO_USERNAME` + `ODOO_API_KEY`
  - Env vars: `ODOO_URL`, `ODOO_DATABASE`, `ODOO_USERNAME`, `ODOO_API_KEY`
  - Services: Multiple services in `app/odoo/services/` including:
    - `faturamento_service.py` - Invoice synchronization (Fases 1-4)
    - `carteira_service.py` - Sales order and inventory syncing
    - `pedido_compras_service.py` - Purchase order management
    - `entrada_material_service.py` - Material receipt processing
    - `cte_service.py` - CTe (freight document) issuance
    - `sincronizacao_integrada_service.py` - Orchestrated safe syncing

**Anthropic Claude API:**
- Service - AI-powered agent for logistics decision-making and NLP
  - SDK/Client: `claude-agent-sdk 0.1.10` (official SDK)
  - Auth: `ANTHROPIC_API_KEY`
  - Env vars: `ANTHROPIC_API_KEY`, `ENABLE_CLAUDE_AI`
  - Endpoint: `https://api.anthropic.com/` (HTTPS)
  - Services:
    - `app/agente/sdk/client.py` - Agent SDK wrapper with streaming support
    - `app/devolucao/services/ai_resolver_service.py` - AI-powered issue resolution
  - Features: Extended Thinking (thinking blocks), tool use, streaming responses
  - Model Context Protocol (MCP) integration via skills (`.claude/skills/`)

**Google Maps API:**
- Service - Geocoding, routing, and map display for logistics planning
  - Auth: `GOOGLE_MAPS_API_KEY`
  - Env var: `GOOGLE_MAPS_API_KEY`
  - Services: `app/carteira/services/mapa_service.py`, `app/rastreamento/services/gps_service.py`
  - Features: Distance calculation, address geocoding, route optimization

**Portal Integrations (Retailer Access):**
- Atacadão portal
  - Client: Selenium WebDriver + Chrome Debug Mode
  - Credentials: `ATACADAO_USUARIO`, `ATACADAO_SENHA`
  - Purpose: Automated order placement and status tracking
- Tenda portal
  - Credentials: `TENDA_USUARIO`, `TENDA_SENHA`
  - Purpose: Order management for Tenda chain
- Sendas portal
  - Credentials: `SENDAS_USUARIO`, `SENDAS_SENHA`
  - Purpose: Order management for Sendas chain

**Rastreamento (Tracking) App Integration:**
- Service - Mobile app GPS tracking and delivery verification
  - Env vars: `RASTREAMENTO_BASE_URL` (dev), `RASTREAMENTO_PROD_URL` (prod)
  - Services: `app/rastreamento/services/entrega_rastreada_service.py`, `app/rastreamento/services/odoo_integration_service.py`
  - Features: Geolocation, QR code scanning, delivery proof

## Data Storage

**Databases:**
- Primary (Production): PostgreSQL 12+
  - Connection: `DATABASE_URL` env var (auto-configured by Render)
  - Client: `psycopg2-binary 2.9.10`
  - Pool: 5-10 connections with 180s recycle (optimize for Render timeouts)
  - Custom types registered: DATE, TIME, TIMESTAMP, TIMESTAMPTZ, array types
  - Encoding: UTF-8 explicit configuration for multi-byte character support
  - Configuration: `config.py` with Render-specific optimizations
- Fallback (Development): SQLite 3.x
  - Connection: `sqlite:///sistema_fretes.db`
  - Auto-selected if PostgreSQL unavailable

**Redis:**
- Cache & Job Queue
  - Connection: `REDIS_URL` env var (typically `redis://localhost:6379`)
  - Client: `redis 5.0.8`, `aioredis 2.0.1` (async)
  - Purpose: RQ job queue (background tasks), session caching
  - Configuration: `config.py` sets `RQ_REDIS_URL`, timeouts, queue names
  - Queues: 'high', 'default', 'low', 'atacadao' (dedicated for portal automation)
  - Job TTL: 24 hours (results retained)

**File Storage:**
- Primary (Production): AWS S3
  - Client: `boto3 1.35.0`
  - Auth: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
  - Bucket: `S3_BUCKET_NAME` env var
  - Region: `AWS_REGION` (default: `us-east-1`)
  - Control: `USE_S3` env var (disabled by default in dev, enabled in prod)
- Fallback (Development): Local filesystem
  - Location: Upload directory within project
  - Max size: 32MB per file (`MAX_CONTENT_LENGTH`)

**Caching:**
- Redis (shared with job queue)
- Session storage: Server-side Redis (via Flask-Session)
- Lifetime: 8 hours (`PERMANENT_SESSION_LIFETIME`)

## Authentication & Identity

**Auth Provider:**
- Custom Flask-Login implementation
  - Implementation: `app/__init__.py` with `LoginManager`
  - Session: Flask-Session with Redis backend
  - Protection: CSRF tokens (Flask-WTF), secure cookies
  - Duration: 24 hours remember-me, 8 hours session
  - Features: Strong session protection, HTTP-only cookies, Lax SameSite

**External Auth:**
- Portal credentials (Atacadão, Tenda, Sendas) stored in environment
- Odoo API key auth (token-based, not OAuth)

## Monitoring & Observability

**Error Tracking:**
- None detected in codebase (no Sentry, Rollbar, or similar integration)
- Error handling: Application-level logging with structlog/Python logging

**Logs:**
- Local approach:
  - `structlog 24.4.0` - Structured logging
  - `colorlog 6.8.2` - Colored console output (development)
  - `python-json-logger 2.0.7` - JSON logging (production-ready format)
  - Configuration: `app/utils/logging_config.py`
- File storage: Typically stdout (container logs for Render)

**Monitoring Dashboard:**
- RQ Dashboard (`rq-dashboard 0.6.1`) - Web UI for job queue monitoring
  - Endpoint: Accessible via Flask app (optional)
  - Status: Optional feature (`RQ_DASHBOARD_WEB_BACKGROUND`)

## CI/CD & Deployment

**Hosting:**
- Render.com (primary production)
  - Service type: Web service with Python 3.12 runtime
  - Server: gunicorn + gevent workers
  - Database: Managed PostgreSQL (auto-provided)
  - Redis: Managed Redis instance (optional, for job queue)
  - URL: `https://sistema-fretes.onrender.com`

**CI Pipeline:**
- Not detected in codebase
- Manual deployment to Render.com (likely via git push to Render)

**Local Development:**
- `run.py` - Flask development server with `app.run(debug=True)`
- `python run.py` or `npm run dev` (see package.json scripts)

**Capacitor Mobile Build:**
- `npm run build:android` - Android release build via Gradle
- `npm run build:android:debug` - Android debug build
- `npm run build:ios` - iOS build via Xcode
- Sync command: `npm run sync` - Sync web assets to native platforms

## Environment Configuration

**Required env vars:**
- `DATABASE_URL` - PostgreSQL connection (Render: auto-configured)
- `ANTHROPIC_API_KEY` - Claude API authentication
- `SECRET_KEY` - Flask secret key (must be 32-char hex in production)
- `ODOO_URL` - Odoo instance URL (e.g., `https://odoo.nacomgoya.com.br`)
- `ODOO_DATABASE` - Odoo database name
- `ODOO_USERNAME` - Odoo API user email
- `ODOO_API_KEY` - Odoo API token

**Optional env vars:**
- `REDIS_URL` - Redis connection (default: `redis://localhost:6379`)
- `GOOGLE_MAPS_API_KEY` - For maps and geocoding
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `S3_BUCKET_NAME` - For S3 storage
- `USE_S3` - Enable S3 (default: false in dev)
- `ENVIRONMENT` - Set to `production` to enable prod config
- `FLASK_ENV` - `development` or `production`
- `ATACADAO_USUARIO`, `ATACADAO_SENHA` - Portal credentials
- `TENDA_USUARIO`, `TENDA_SENHA` - Portal credentials
- `SENDAS_USUARIO`, `SENDAS_SENHA` - Portal credentials
- `RASTREAMENTO_BASE_URL` - Local tracking app (dev)
- `RASTREAMENTO_PROD_URL` - Production tracking app
- `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USERNAME`, `EMAIL_PASSWORD` - SMTP configuration
- `SENDGRID_API_KEY` - SendGrid API (alternative email backend)
- `MCP_ENABLED`, `MCP_BASE_URL`, `MCP_AUTH_TOKEN` - Model Context Protocol settings
- `ENABLE_CLAUDE_AI` - Enable/disable Claude integration
- `FILTRAR_FOB_MONITORAMENTO` - Filter FOB invoices in monitoring (default: true)

**Secrets location:**
- Development: `.env` file (Git-ignored, checked into repo with example values)
- Production (Render): Environment variables set in Render dashboard
- Note: Do NOT commit real credentials; use placeholder values in `.env` file

## Webhooks & Callbacks

**Incoming:**
- Not clearly documented in codebase
- Potential: Odoo webhooks for real-time updates (custom XML-RPC polling used instead)
- Render webhook for deployment (auto-configured)

**Outgoing:**
- Odoo: Synchronization callbacks via `SincronizacaoIntegradaService.executar_sincronizacao_completa_segura()`
- Anthropic: Streaming responses with callback handlers in `AgentClient`

## Key Integration Patterns

**Odoo Synchronization Pipeline:**
- Multi-phase integration (Fases 1-4 for purchasing)
- Faturamento first (invoices), then Carteira (orders)
- Safe orchestration via `SincronizacaoIntegradaService` to prevent data loss
- XML-RPC client wrapper for connection pooling and error handling

**Claude Agent SDK Integration:**
- Skill-based architecture (skills in `.claude/skills/`)
- Tool use for executing system commands and reading files
- Extended Thinking for complex problem-solving
- Memory tool for persistent context (DatabaseMemoryTool)
- Permission system for safe command execution

**Portal Automation:**
- Selenium WebDriver for browser control
- Chrome Debug Protocol (preferred over standard WebDriver)
- RQ job queue for background portal tasks
- Credential management via environment variables

**Background Job Processing:**
- RQ (Redis Queue) for async tasks
- APScheduler for periodic jobs (hourly, daily sync, etc.)
- Job timeouts: 30 minutes for long-running portal tasks
- Dashboard monitoring via rq-dashboard

---

*Integration audit: 2026-01-25*
