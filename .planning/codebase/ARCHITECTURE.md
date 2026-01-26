# Architecture

**Analysis Date:** 2025-01-25

## Pattern Overview

**Overall:** Modular Monolith with Layered Architecture

**Key Characteristics:**
- Module-per-feature organization with clear separation of concerns
- Three-tier layered architecture: Routes → Services → Models
- Odoo ERP integration as critical data source (carteira, separação, pallet management)
- Flask-based web application with REST API endpoints
- PostgreSQL database as primary data store
- Event-driven synchronization with background workers (RQ, APScheduler)
- Multi-tenant support via group empresarial (CNPJ groups)

## Layers

**Presentation Layer (Routes):**
- Purpose: Handle HTTP requests, render templates, coordinate API responses
- Location: `app/[module]/routes/`, `app/[module]/routes.py`
- Contains: Flask Blueprints, request handlers, view functions
- Depends on: Services, Models, Utils, Templates
- Used by: Web browsers, AJAX clients, external API consumers

**Business Logic Layer (Services):**
- Purpose: Implement business rules, data transformations, integrations
- Location: `app/[module]/services/`, `app/[module]/[module]_service.py`
- Contains: Service classes with domain logic, calculations, validations
- Depends on: Models, ORM queries, External APIs (Odoo, CNPJ validation)
- Used by: Routes, CLI commands, Background workers

**Data Access Layer (Models):**
- Purpose: Define database schema, relationships, data validation
- Location: `app/[module]/models.py`, `app/[module]/models/`
- Contains: SQLAlchemy ORM models, hybrid properties, relationships
- Depends on: SQLAlchemy, database driver
- Used by: Services, Routes, Queries

**Integration Layer:**
- Purpose: Bridge between Frete Sistema and external systems
- Location: `app/odoo/`, `app/integracoes/`, `app/utils/odoo_integration.py`
- Contains: Odoo XML-RPC client, API adapters, circuit breaker patterns
- Depends on: Configuration, database
- Used by: Services, background jobs

**Utilities Layer:**
- Purpose: Cross-cutting concerns and helper functions
- Location: `app/utils/`
- Contains: Formatters, validators, calculators, logging, caching
- Depends on: Standard library, third-party libraries
- Used by: All layers

## Data Flow

**Order-to-Fulfillment Pipeline:**

1. **Import from Odoo** (sync_odoo_service.py)
   - Fetch sale.order from Odoo periodically
   - Map to CarteiraPrincipal (source of truth for pending orders)
   - Store write_date for incremental sync

2. **Carteira Management** (carteira_service.py)
   - Query CarteiraPrincipal with saldo > 0
   - Apply filters: data_entrega, vendedor, estado
   - Display via carteira_simples_api.py routes

3. **Separação Creation** (separacao_api.py)
   - Create Separacao from CarteiraPrincipal items
   - Calculate pallet quantity: qtd_saldo / CadastroPalletizacao.palletizacao
   - Assign rota/sub_rota based on UF/city
   - Set status=ABERTO, sincronizado_nf=False

4. **Embarque Processing** (embarques/routes)
   - Group Separações into Embarque
   - Calculate weight, pallets, volume
   - Create EmbarqueItem linking to NF sale
   - Update Separacao.numero_nf when synced

5. **Pallet Management** (pallet/services)
   - Track physical pallets (separate from theoretical pallets)
   - Generate NF remessa for pallets sent to carrier
   - Match pallets received vs. sent for returns

6. **NF Emission** (faturamento/services)
   - Create NF remessa from Embarque
   - Post to Odoo account.move via fiscal service
   - Trigger Separacao.sincronizado_nf=True (critical flag)

7. **Monitoramento (Tracking)** (monitoramento/models)
   - Receive tracking events from Odoo/carrier
   - Update EntregaMonitorada with status changes
   - Calculate delivery metrics (planned vs. actual)

**State Management:**

- **CarteiraPrincipal.qtd_saldo_produto_pedido**: Source of truth for pending quantity
- **Separacao.sincronizado_nf**: Critical flag (False = projects to estoque, True = already in NF)
- **Embarque.status**: Tracks fulfillment stage (PREVISAO → ABERTO → COTADO → EMBARCADO → FATURADO)
- **EmbarqueItem.nf_pallet_***: Tracks physical pallet allocation across multiple NFs

## Key Abstractions

**CarteiraPrincipal (Carteira de Pedidos):**
- Purpose: Single source of truth for all pending orders from Odoo
- Examples: `app/carteira/models.py:12-100+`, `app/odoo/services/carteira_service.py`
- Pattern: Full denormalization of sale.order + address data for fast queries
- Fields sync incrementally from Odoo via odoo_write_date

**Separacao (Picking/Line-Item Level):**
- Purpose: Operational unit for fulfillment (represents picking line with specific quantity)
- Examples: `app/separacao/models.py:7-80+`
- Pattern: Created from CarteiraPrincipal, linked to physical operations
- Critical field: sincronizado_nf (False = pending stock projection, True = in NF)

**Embarque & EmbarqueItem (Shipment Level):**
- Purpose: Group Separações for shipping
- Examples: `app/embarques/models.py`
- Pattern: EmbarqueItem.nf_referencia links to actual NF; nf_pallet_* tracks physical pallet moves
- Relationship: One Embarque contains many EmbarqueItem, each tied to multiple Separação

**OdooConnection & Circuit Breaker:**
- Purpose: Manage XML-RPC connections with automatic fallback
- Examples: `app/odoo/utils/connection.py`, `app/odoo/routes_circuit_breaker.py`
- Pattern: Connection pooling with circuit breaker for timeout/retry logic
- Used by: All services that need Odoo data

**CarteiraMapper & Adapters:**
- Purpose: Transform Odoo data structures to internal models
- Examples: `app/odoo/utils/carteira_mapper.py`
- Pattern: Query-based mapping (no "/" field syntax) to handle computed fields
- Transforms: sale.order (Odoo) → CarteiraPrincipal (local DB)

## Entry Points

**Web Application:**
- Location: `app/__init__.py` (create_app factory)
- Triggers: Flask run command or WSGI server startup
- Responsibilities: Initialize db, blueprints, filters, error handlers, logging

**Main Dashboard:**
- Location: `app/main/routes.py:dashboard`
- Triggers: GET /dashboard
- Responsibilities: Aggregate system statistics, fetch alerts, render main interface

**Carteira API:**
- Location: `app/carteira/routes/carteira_simples_api.py`
- Triggers: GET /carteira/api/... endpoints
- Responsibilities: Query CarteiraPrincipal, apply filters, return JSON for UI

**Odoo Sync Worker:**
- Location: `app/odoo/jobs/` (background jobs)
- Triggers: APScheduler cron or manual RQ job
- Responsibilities: Fetch Odoo data, update CarteiraPrincipal incrementally

**CLI Commands:**
- Location: `app/cli.py`
- Triggers: flask [command] CLI
- Responsibilities: One-off tasks (imports, migrations, diagnostics)

## Error Handling

**Strategy:** Graceful degradation with detailed logging and circuit breaker patterns

**Patterns:**

- **API Errors:** Try-except in routes, return JSON with error details; 404 handled gracefully
- **Service Errors:** Catch in Carteira/Embarque services, log to logger, return empty defaults
- **Odoo Connection Errors:** Circuit breaker in `routes_circuit_breaker.py` - fails fast after N retries
- **Database Errors:** Automatic retry via `database_retry.py` with exponential backoff
- **CSRF Errors:** Custom handler in `app/__init__.py:262-294` returns JSON for AJAX, redirect for forms
- **Validation Errors:** Models validate on save (pre-insert triggers), routes return 400 with message

**Error Logging:**
- Location: `app/utils/logging_config.py`
- Captures: Request info, response time, exceptions, slow queries (>3s)
- Filters: Ignores /static/, /favicon.ico, frequent polling endpoints

## Cross-Cutting Concerns

**Logging:**
- Framework: Python logging module with custom handlers
- Implementation: `app/utils/logging_config.py` initializes logger
- Usage: `logger.info()`, `logger.warning()`, `logger.error()` throughout

**Validation:**
- Fields: Decimal precision (15,3 for qty; 15,2 for values), string length
- Methods: Pre-commit triggers in models for truncation (observ_ped_1 → 700 chars)
- Dates: Brazilian timezone aware formatting via `app/utils/timezone.py`

**Authentication:**
- Framework: Flask-Login with session-based auth
- Protected routes: @login_required decorator
- Roles: perfil in User model (vendedor, operacional, gerencial, admin)
- Session duration: 8 hours (PERMANENT_SESSION_LIFETIME = 28800)

**Formatting:**
- Dates: `formatar_data_brasil()` Jinja2 filter (output: DD/MM/YYYY)
- Numbers: `numero_br()` filter with configurable decimals (output: 1.234,56)
- Templates: Located in `app/templates/[module]/`

**Database Optimization:**
- Indexes: Composite indexes on frequently filtered columns (lote_id + sync, num_pedido + sync)
- Connection pool: size=5, max_overflow=10 for PostgreSQL
- Query strategy: Use joinedload() for relationships to avoid N+1 queries

---

*Architecture analysis: 2025-01-25*
