# Technology Stack

**Analysis Date:** 2026-01-25

## Languages

**Primary:**
- Python 3.12.3 - Backend application, business logic, data processing
- JavaScript (ES6+) - Frontend templates, asset management (via Capacitor)
- HTML5/CSS3 - UI templates and styling
- SQL - Database queries and migrations

**Secondary:**
- Java (optional) - Android native code via Capacitor build system
- Swift (optional) - iOS native code via Capacitor build system

## Runtime

**Environment:**
- Python 3.12+ (configured in setup.cfg, pyproject.toml)

**Package Manager:**
- pip (Python dependencies)
- npm (Node.js dependencies for Capacitor CLI)
- Lockfile: `requirements.txt` (Python), `package.json` (Node)

## Frameworks

**Core:**
- Flask 3.1.0 - Web application framework
- Flask-SQLAlchemy 3.1.1 - ORM and database abstraction
- Flask-Login 0.6.3 - User authentication and session management
- Flask-Migrate 4.1.0 - Database migrations using Alembic
- Flask-Session 0.8.0 - Server-side session management
- Flask-WTF 1.2.2 - CSRF protection and form handling
- WTForms 3.2.1 - Form validation and rendering

**API & Async:**
- FastAPI 0.115.5 - Modern async API framework (for agente routes)
- uvicorn[standard] 0.32.1 - ASGI server for async APIs
- httpx 0.28.1 - Async HTTP client
- aioredis 2.0.1 - Async Redis client for FastAPI services

**Mobile/Desktop Integration:**
- Capacitor 6.2.0 - Bridge between web and native mobile platforms
- @capacitor/android 6.2.0 - Android native integration
- @capacitor/ios 6.2.0 - iOS native integration
- @capacitor/geolocation 6.0.1 - Native GPS capabilities
- @capacitor-community/background-geolocation 1.2.17 - Background GPS tracking

**Testing:**
- pytest (implicit dependency chain via test requirements)
- Flask test client (built-in Flask testing)

**Build/Dev:**
- gunicorn 23.0.0 - Production WSGI server
- greenlet 3.1.1 - Lightweight concurrency for Python 3.12+ compatibility
- gevent 24.11.1 - Async I/O support for greenlet

## Key Dependencies

**Critical:**
- psycopg2-binary 2.9.10 - PostgreSQL database adapter (production database)
- pandas 2.2.3 - Data manipulation and analysis for reporting
- SQLAlchemy (via Flask-SQLAlchemy) - Database ORM and query builder

**Infrastructure:**
- redis 5.0.8 - In-memory cache and message broker
- rq 1.16.2 - Redis Queue for background job processing (async tasks)
- rq-dashboard 0.6.1 - Web dashboard for monitoring Redis jobs
- APScheduler 3.11.0 - Task scheduler for periodic jobs

**AI & Claude Integration:**
- anthropic 0.75.0 - Direct Anthropic API client (fallback)
- claude-agent-sdk 0.1.10 - Official Claude Agent SDK for agentic workflows
- mcp >=1.10.0 - Model Context Protocol for tool/skill integration

**Data Processing:**
- openpyxl 3.1.5 - Excel file reading/writing (.xlsx)
- xlrd 2.0.1 - Legacy Excel format support (.xls)
- xlwt 1.3.0 - Legacy Excel format writing
- xlsxwriter 3.2.5 - Advanced Excel file generation
- python-dateutil 2.9.0.post0 - Date/time utilities
- pytz 2025.2 - Timezone handling

**NLP & Text Processing:**
- fuzzywuzzy 0.18.0 - Fuzzy string matching for entity resolution
- rapidfuzz 3.10.1 - Fast Levenshtein matching (replaces python-Levenshtein)
- unidecode 1.4.0 - Unicode normalization and accent removal
- nltk 3.8.1 - Natural Language Toolkit for text analysis
- jellyfish 1.1.0 - Additional string matching algorithms

**Document Processing:**
- pdfplumber 0.11.7 - PDF text/table extraction
- pypdf 5.1.0 - PDF manipulation and reading
- weasyprint 67.0 - HTML to PDF conversion
- extract-msg 0.55.0 - Microsoft Outlook .msg/.eml email parsing
- qrcode 8.0 - QR code generation
- pillow 11.0.0 - Image processing (required by qrcode)

**Browser Automation (Portal Integration):**
- selenium 4.27.1 - Chrome automation (for Atacadão/Tenda/Sendas portals)
- webdriver-manager 4.0.2 - Automatic WebDriver management
- playwright 1.49.0 - Alternative multi-browser automation (modern)
- nest-asyncio 1.6.0 - Fix for Playwright sync in async context

**Cloud & Deployment:**
- boto3 1.35.0 - AWS SDK for S3 file storage
- python-dotenv 1.1.0 - Environment variable management
- psutil 5.9.6 - System and process utilities

**Security & Validation:**
- cryptography 43.0.3 - Encryption for cookies/sessions
- PyJWT 2.8.0 - JSON Web Token handling
- python-jose[cryptography] 3.3.0 - JOSE (JWT/JWS/JWE) support
- email-validator 2.2.0 - Email validation
- dnspython 2.7.0 - DNS utilities for email validation
- python-multipart 0.0.14 - Multipart form data parsing

**Logging & Monitoring:**
- structlog 24.4.0 - Structured logging framework
- colorlog 6.8.2 - Colored terminal output
- python-json-logger 2.0.7 - JSON logging output

**Validation & Data:**
- pydantic 2.11.7 - Data validation and parsing
- anyio 4.9.0 - Async I/O compatibility layer

**Geolocation:**
- haversine 2.9.0 - Haversine formula for GPS distance calculation
- Google Maps API (via GOOGLE_MAPS_API_KEY env var) - Geocoding and mapping

## Configuration

**Environment:**
- `.env` file for local development (PostgreSQL local)
- `.env.render` template for production (Render.com)
- Environment detection: Production mode if `ENVIRONMENT=production` or running on render.com
- Database auto-detection: PostgreSQL or SQLite fallback

**Build:**
- `config.py` - Main configuration class with environment-specific settings
- `setup.cfg` - Python packaging configuration
- `pyproject.toml` - Modern Python project metadata and build settings
- `capacitor.config.json` - Mobile app configuration (web-to-native bridge)
- `capacitor.config.dev.json` - Development environment override
- `capacitor.config.prod.json` - Production environment override

**Key Config Options:**
- `SQLALCHEMY_DATABASE_URI` - Points to PostgreSQL or SQLite
- `REDIS_URL` - Redis connection string for job queue
- `USE_S3` - Enable/disable S3 file storage (defaults to local filesystem in dev)
- `WTF_CSRF_ENABLED` - CSRF protection (enabled in production)
- `SESSION_COOKIE_SECURE` - Secure cookies only in production
- `FILTRAR_FOB_MONITORAMENTO` - Filter FOB invoices in monitoring views

## Platform Requirements

**Development:**
- Python 3.12+
- PostgreSQL 12+ (local) OR SQLite 3.x (fallback)
- Redis 6+ (for job queue)
- Node.js 16+ (for Capacitor CLI)
- Java SDK 11+ (for Android builds via Capacitor)
- Xcode 14+ (for iOS builds via Capacitor, macOS only)

**Production:**
- Render.com (primary deployment target)
  - Managed PostgreSQL database
  - Managed Redis instance
  - Python 3.12 runtime
  - Web service with gunicorn + gevent
- Optional: AWS S3 for file storage (boto3 integration)

**Key Environment Variables (Required):**
- `DATABASE_URL` - PostgreSQL connection string (auto-configured by Render)
- `ANTHROPIC_API_KEY` - Claude API key for agentic features
- `SECRET_KEY` - Flask secret key (must be set in production)
- `ODOO_URL` - Odoo instance URL
- `ODOO_DATABASE` - Odoo database name
- `ODOO_USERNAME` - Odoo API user
- `ODOO_API_KEY` - Odoo API authentication token

---

*Stack analysis: 2026-01-25*
