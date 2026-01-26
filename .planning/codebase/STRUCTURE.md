# Codebase Structure

**Analysis Date:** 2025-01-25

## Directory Layout

```
frete_sistema/
├── app/                          # Main application package
│   ├── __init__.py              # Flask factory, extensions init, filters setup
│   ├── cli.py                   # CLI commands
│   │
│   ├── auth/                    # Authentication module
│   │   ├── models.py            # User, Role models
│   │   └── routes.py            # Login, logout, registration
│   │
│   ├── main/                    # Main dashboard and core routes
│   │   └── routes.py            # Dashboard, reports, main interface
│   │
│   ├── carteira/                # Order wallet (primary operational module)
│   │   ├── models.py            # CarteiraPrincipal (91 fields, source of truth)
│   │   ├── routes/              # API endpoints for carteira views
│   │   │   ├── carteira_simples_api.py (96K) # Main carteira list API
│   │   │   ├── separacao_api.py (30K)        # Create/manage separações
│   │   │   ├── ruptura_api.py (30K)          # Stock shortage analysis
│   │   │   ├── relatorios_api.py (22K)       # Reports: aging, by vendor
│   │   │   └── [others].py      # Alerts, dashboard, workspace APIs
│   │   ├── services/            # Business logic
│   │   │   ├── mapa_service.py  # Routing/transportation calculations
│   │   │   ├── agrupamento_service.py # Grouping logic
│   │   │   └── importacao_nao_odoo.py # Non-Odoo import
│   │   └── utils/               # Helper functions (separation, routing)
│   │
│   ├── separacao/               # Picking/fulfillment unit
│   │   ├── models.py            # Separacao model (picking line, critical)
│   │   └── [listeners in models.py] # Automatic field sync
│   │
│   ├── embarques/               # Shipment management
│   │   ├── models.py            # Embarque, EmbarqueItem (shipment grouping)
│   │   └── routes.py            # Create, list, edit shipments
│   │
│   ├── pallet/                  # Pallet management (NEW V2 RESTRUCTURE)
│   │   ├── models/              # Modular model structure
│   │   │   ├── __init__.py
│   │   │   ├── vale_pallet.py   # Vale de pallet (credit note)
│   │   │   ├── documento.py     # Documento (registry)
│   │   │   ├── solucao.py       # Solução (resolution/matching)
│   │   │   ├── credito.py       # Crédito (credit tracking)
│   │   │   ├── nf_remessa.py    # NF remessa (shipping invoice)
│   │   │   └── nf_solucao.py    # NF solução (resolution invoice)
│   │   ├── routes/              # V2 refactored routes
│   │   │   ├── controle_pallets.py
│   │   │   ├── tratativa_nfs.py
│   │   │   ├── nf_remessa.py
│   │   │   └── dashboard.py
│   │   ├── services/            # V2 refactored services
│   │   │   ├── match_service.py (36K) # Complex pallet matching
│   │   │   ├── nf_service.py (32K)    # NF generation
│   │   │   ├── solucao_pallet_service.py
│   │   │   ├── credito_service.py
│   │   │   └── sync_odoo_service.py
│   │   └── routes_legacy.py     # Old routes (deprecated, keep for ref)
│   │
│   ├── odoo/                    # Odoo ERP integration (critical)
│   │   ├── services/            # Core integration services (630K LOC)
│   │   │   ├── carteira_service.py (140K) # CarteiraPrincipal sync
│   │   │   ├── faturamento_service.py (91K) # Invoice/fiscal
│   │   │   ├── cte_service.py (39K)        # Cargo tracking
│   │   │   ├── pedido_compras_service.py   # PO operations
│   │   │   ├── requisicao_compras_service.py
│   │   │   └── [others].py      # Material entry, CTe, alocação
│   │   ├── utils/
│   │   │   ├── connection.py    # Odoo XML-RPC connection pool
│   │   │   ├── carteira_mapper.py # Data transformation
│   │   │   └── [others].py      # Field mappers, validators
│   │   ├── routes/              # Integration endpoints
│   │   │   └── [module]_routes.py # DFe, CTe, sync endpoints
│   │   ├── config/              # Integration config
│   │   │   └── odoo_config.py   # Connection strings, timeouts
│   │   ├── jobs/                # Background sync jobs
│   │   └── routes_circuit_breaker.py # Failover patterns
│   │
│   ├── faturamento/             # Invoice generation and NF posting
│   │   ├── models.py            # RelatorioFaturamento, fiscal models
│   │   ├── services/            # Invoice services
│   │   └── routes.py            # Invoice UI/API
│   │
│   ├── devolucao/               # Returns/devolution management
│   │   ├── models.py            # NFDevolucao, ocorrências
│   │   ├── services/            # Return processing logic
│   │   └── routes.py            # Return workflows
│   │
│   ├── fretes/                  # Freight cost management
│   │   ├── models.py            # Frete (freight cost)
│   │   ├── services/            # Freight calculations
│   │   └── routes.py            # Cost approvals, simulation
│   │
│   ├── monitoramento/           # Delivery tracking and events
│   │   ├── models.py            # EntregaMonitorada, EventoEntrega
│   │   └── routes.py            # Tracking dashboard
│   │
│   ├── estoque/                 # Inventory management
│   │   ├── models.py            # Stock balance
│   │   └── routes.py            # Stock queries
│   │
│   ├── producao/                # Production planning
│   │   ├── models.py            # CadastroPalletizacao (pallet factor)
│   │   └── routes.py            # Schedule management
│   │
│   ├── pedidos/                 # Order management (legacy, for reference)
│   │   ├── models.py            # Pedido, PreSeparacaoItem
│   │   └── routes.py            # Deprecated
│   │
│   ├── recebimento/             # Purchase receiving (Phases 1-4)
│   │   ├── models.py            # RFQ, validation models
│   │   ├── services/            # Receiving workflows
│   │   └── routes.py            # Phase-specific routes
│   │
│   ├── agente/                  # AI Agent (Claude SDK integration)
│   │   ├── models.py            # AgentSession, AgentMemory
│   │   ├── routes.py            # Chat API endpoints
│   │   ├── prompts/
│   │   │   └── system_prompt.md # Agent behavior definition
│   │   ├── memory_tool.py       # Anthropic Memory Tool
│   │   └── sdk/
│   │       └── client.py        # Agent SDK client wrapper
│   │
│   ├── api/                     # REST API layer
│   │   ├── routes.py            # Main API endpoints
│   │   ├── routes/              # Organized API sub-routes
│   │   ├── odoo/                # Odoo-specific API
│   │   └── cors.py              # CORS configuration
│   │
│   ├── [other modules]/         # Additional modules
│   │   ├── comercial/           # Sales/commercial
│   │   ├── financeiro/          # Financial (accounts, receivable)
│   │   ├── localidades/         # Cities, regions
│   │   ├── transportadoras/     # Carrier management
│   │   ├── portaria/            # Gate/check-in
│   │   ├── metricas/            # Dashboards and metrics
│   │   ├── bi/                  # Business intelligence ETL
│   │   ├── manufatura/          # Manufacturing integration
│   │   └── [others]/
│   │
│   ├── utils/                   # Cross-cutting utilities (390K LOC)
│   │   ├── logging_config.py    # Logging setup
│   │   ├── timezone.py          # Brazilian timezone helpers
│   │   ├── template_filters.py  # Jinja2 filters (numero_br, valor_br)
│   │   ├── odoo_integration.py  # High-level Odoo helpers
│   │   ├── api_helper.py        # API response helpers
│   │   ├── grupo_empresarial.py # Multi-tenant CNPJ group logic
│   │   ├── frete_simulador.py   # Freight simulation
│   │   ├── calculadora_frete.py # Cost calculations
│   │   ├── database_retry.py    # Connection retry logic
│   │   ├── database_helpers.py  # Query helpers
│   │   ├── [others].py          # Validators, file storage, email
│   │   └── importacao/          # Import utilities
│   │
│   ├── templates/               # Jinja2 HTML templates
│   │   ├── base.html            # Main template with menu/nav
│   │   ├── [module]/            # Module-specific templates
│   │   │   ├── carteira/
│   │   │   │   ├── dashboard.html
│   │   │   │   ├── agrupados_balanceado.html
│   │   │   │   └── [others].html
│   │   │   ├── pallet/v2/       # New pallet v2 templates
│   │   │   │   ├── controle_pallets/
│   │   │   │   ├── tratativa_nfs/
│   │   │   │   └── dashboard.html
│   │   │   ├── embarques/
│   │   │   ├── fretes/
│   │   │   ├── monitoramento/
│   │   │   ├── pedidos/
│   │   │   └── [others]/
│   │   ├── css/                 # Stylesheets per module
│   │   ├── js/                  # JavaScript per module
│   │   └── auth/                # Login templates
│   │
│   ├── static/                  # Static assets
│   │   ├── css/
│   │   ├── js/
│   │   ├── images/
│   │   └── [others]/
│   │
│   ├── database/                # Database utilities
│   │   └── [migration helpers]
│   │
│   └── workers/                 # Background workers
│       └── [RQ job definitions]
│
├── config.py                    # Flask configuration (database, security)
├── config/                      # Environment-specific configs
├── scripts/                     # One-off migration/setup scripts
│   ├── pallet/
│   │   ├── 001_criar_tabelas_pallet_v2.py
│   │   ├── 002_migrar_movimentacao_para_nf_remessa.py
│   │   ├── 003_migrar_vale_pallet_para_documento.py
│   │   └── [others].py
│   ├── devolucao/
│   └── [others]/
│
├── requirements.txt             # Python dependencies
├── run.py                       # WSGI entry point
├── pytest.ini                   # Test configuration
├── .env                         # Environment variables (LOCAL ONLY)
├── .env.example                 # Template for .env
└── .planning/
    └── codebase/                # Documentation (ARCHITECTURE.md, STRUCTURE.md, etc.)
```

## Directory Purposes

**app/ - Main Application Package**
- Purpose: All application code, models, views, services
- Contains: Modules organized by business function
- Key files: `__init__.py` (factory), `cli.py` (commands)

**app/carteira/ - Carteira de Pedidos (Primary)**
- Purpose: Order wallet, the central operational view
- Contains: CarteiraPrincipal model (91 fields), APIs for viewing/filtering
- Key files: `routes/carteira_simples_api.py` (96K, main carteira list)
- Dependency: Pulls data from Odoo sync, feeds to Separação/Embarque

**app/separacao/ - Picking/Fulfillment Unit**
- Purpose: Represents picking line items ready for shipment
- Contains: Separacao model with critical fields (qtd_saldo, sincronizado_nf)
- Key files: `models.py` with listener for automatic field sync
- Dependency: Created from CarteiraPrincipal, linked to Embarque

**app/embarques/ - Shipment Grouping**
- Purpose: Group Separações for physical shipping
- Contains: Embarque (shipment header), EmbarqueItem (line items)
- Key files: `models.py`, `routes.py` for shipment management
- Dependency: Links to Separação, creates EmbarqueItem → NF mapping

**app/pallet/ - Pallet Management (V2 Refactored)**
- Purpose: Track physical pallets, generate pallet NFs, handle returns
- Contains: Vale, Documento, Solução, Crédito, NF Remessa models
- Key files: `match_service.py` (36K complex matching), `nf_service.py` (32K)
- Dependency: Works with Embarque for physical asset tracking
- Note: V2 refactored with modular structure (was monolithic routes_legacy.py)

**app/odoo/ - Odoo ERP Integration**
- Purpose: Synchronize with external Odoo system, primary data source
- Contains: 630K LOC across services (carteira_service.py 140K, faturamento_service.py 91K)
- Key files: `services/carteira_service.py` (fetch sale.order), `utils/connection.py` (XML-RPC pool)
- Dependency: Provides CarteiraPrincipal data, posts NFs back to Odoo
- Critical: Circuit breaker in `routes_circuit_breaker.py` for failover

**app/faturamento/ - Invoice Generation**
- Purpose: Create and post invoices to Odoo
- Contains: Fiscal models, NF generation logic
- Key files: `services/` with faturamento_service.py (91K)
- Dependency: Reads from Embarque, writes to Odoo account.move

**app/utils/ - Shared Utilities**
- Purpose: Cross-cutting concerns, helpers, validators
- Contains: 390K LOC (logging, timezone, formatting, calculations)
- Key files: `logging_config.py`, `timezone.py`, `template_filters.py`, `grupo_empresarial.py`
- Dependency: Used by all layers for formatting, validation, integration

**app/templates/ - HTML Templates**
- Purpose: Jinja2 template files for web UI
- Contains: Module-specific subdirectories mirroring `app/[module]/` structure
- Key files: `base.html` (main layout), `pallet/v2/` (new pallet v2 UI)
- Dependency: Rendered by routes via Flask render_template()

**config.py - Flask Configuration**
- Purpose: Database URI, security settings, environment-based configs
- Contains: Config class with database pool, session, CSRF, CORS settings
- Key: Sets PostgreSQL connection params for Render.com production

**scripts/ - Migration and Setup Scripts**
- Purpose: One-off tasks (table creation, data migration, cleanup)
- Contains: Python scripts prefixed with numbers (001_, 002_) and SQL files
- Examples: `pallet/001_criar_tabelas_pallet_v2.py`, `devolucao/` return handlers
- Note: Should be run in order during database migrations

**.planning/codebase/ - Analysis Documentation**
- Purpose: Auto-generated docs for GSD orchestrator
- Contains: ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, TESTING.md, CONCERNS.md, STACK.md, INTEGRATIONS.md
- Generated by: GSD codebase mapper agent

## Key File Locations

**Entry Points:**

- `app/__init__.py`: Flask factory function create_app(), extensions init
- `run.py`: WSGI application entry point (gunicorn target)
- `config.py`: Database and Flask config
- `app/main/routes.py`: Main dashboard and core routes (GET /dashboard)

**Configuration:**

- `config.py`: Flask settings, database URI, CSRF/session config
- `config/`: Environment-specific overrides
- `.env`: Local variables (DATABASE_URL, SECRET_KEY, ODOO_* credentials)
- `app/odoo/config/odoo_config.py`: Odoo connection strings, timeouts

**Core Logic:**

- `app/odoo/services/carteira_service.py`: Fetch and sync Odoo sale.order to CarteiraPrincipal
- `app/carteira/routes/carteira_simples_api.py`: Main carteira list API (96K)
- `app/carteira/routes/separacao_api.py`: Create/manage Separação from CarteiraPrincipal
- `app/pallet/services/match_service.py`: Complex pallet matching logic (36K)

**Testing:**

- `pytest.ini`: Pytest configuration
- `tests/`: Test directory (auto-created on demand)

## Naming Conventions

**Files:**

- Module routes: `[module]_api.py` (carteira_simples_api.py, separacao_api.py)
- Services: `[module]_service.py` (carteira_service.py, faturamento_service.py)
- Models: `models.py` per module, or `models/` directory for modular structure
- Templates: `[module]/[view].html` (carteira/dashboard.html, pallet/v2/controle_pallets.html)
- Scripts: Numbered prefix for migrations (001_criar_tabelas.py, 002_migrar.py)

**Directories:**

- Modules: Lowercase (carteira, embarques, pallet, odoo)
- Sub-modules: By concern (models/, routes/, services/, utils/)
- Module-specific utils: Inside module directory (app/carteira/utils/)
- Shared utils: In app/utils/

**Python Classes:**

- Models: PascalCase inheriting db.Model (CarteiraPrincipal, Separacao, Embarque)
- Services: PascalCase + "Service" suffix (CarteiraService, FaturamentoService)
- Mappers: PascalCase + "Mapper" suffix (CarteiraMapper, FaturamentoMapper)

**Templates/HTML:**

- Dashboard views: `[module]/dashboard.html`
- List views: `[module]/lista.html` or `[module]_api.html`
- Detail views: `[module]/detalhes.html`
- Modal forms: `[module]/_form_[name].html` (underscore prefix)

## Where to Add New Code

**New Feature (e.g., "Track pallet return from customer"):**

1. **Models:**
   - Add model to `app/pallet/models/` (or existing models.py)
   - Define relationships: `db.ForeignKey()`, `db.relationship()`
   - Create script: `scripts/pallet/NNN_criar_tabela_retorno.py`

2. **Services:**
   - Create `app/pallet/services/retorno_service.py`
   - Implement business logic (pallet validation, matching, status transitions)
   - Call from routes via dependency injection

3. **Routes/API:**
   - Add endpoint in `app/pallet/routes/controle_pallets.py`
   - Use @main_bp.route() decorator
   - Call service, return JSON or redirect

4. **Templates:**
   - Create `app/templates/pallet/v2/retorno/form.html`
   - Add link to menu in `app/templates/base.html` under relevant section
   - Use Jinja2 filters for formatting (numero_br, valor_br)

5. **Tests:**
   - Create `tests/test_pallet_retorno.py`
   - Follow pattern: test_create_retorno(), test_validate_retorno()

**New Component/Module (e.g., "Vendor Returns Management"):**

1. **Create module directory:**
   ```
   app/fornecedor_devolucao/
   ├── __init__.py
   ├── models.py
   ├── routes.py  (or routes/ for multiple)
   ├── services/
   └── utils/
   ```

2. **Register in Flask:**
   - Create Blueprint in `app/fornecedor_devolucao/routes.py`
   - Import and register in `app/__init__.py` (search for `blueprint_list`)

3. **Add to menu:**
   - Edit `app/templates/base.html`
   - Add `<li><a href="{{ url_for(...) }}">...</a></li>` to appropriate dropdown

4. **Add templates:**
   - Create `app/templates/fornecedor_devolucao/` directory
   - Add dashboard, list, detail templates

**Utilities/Helpers:**

- **Shared across modules:** Place in `app/utils/[name].py`
- **Formatting:** Add filter to `app/utils/template_filters.py`, then register in `app/__init__.py:391-442`
- **Validators:** Create `app/utils/validators/[name].py`
- **Calculations:** Create `app/utils/calculadora_[domain].py` (e.g., `calculadora_frete.py`)

## Special Directories

**app/templates/pallet/v2/ - NEW Pallet V2 Templates:**
- Purpose: New refactored pallet module UI (controle, tratativa, dashboard)
- Generated: By pallet v2 refactoring
- Committed: Yes, part of active development

**scripts/pallet/ - Pallet Migration Scripts:**
- Purpose: Database schema and data migrations for pallet v2
- Generated: Manually created for each migration phase
- Committed: Yes, for reproducibility
- Numbering: 001_, 002_, 003_ (run in order)

**app/odoo/jobs/ - Background Sync Jobs:**
- Purpose: APScheduler and RQ job definitions for Odoo sync
- Generated: Manually configured
- Committed: Yes
- Trigger: `app/cli.py` commands or scheduler cron

**flask_session/ - Session Storage:**
- Purpose: Temporary session files (filesystem-based)
- Generated: Automatically by Flask-Session
- Committed: No (in .gitignore)

**.planning/codebase/ - GSD Documentation:**
- Purpose: Auto-generated codebase analysis docs
- Generated: By GSD codebase mapper agent
- Committed: Yes (part of project docs)
- Files: ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, TESTING.md, CONCERNS.md, STACK.md, INTEGRATIONS.md

---

*Structure analysis: 2025-01-25*
