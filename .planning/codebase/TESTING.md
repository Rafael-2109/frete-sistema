# Testing Patterns

**Analysis Date:** 2026-01-25

## Test Framework

**Runner:**
- pytest 7.x+
- Config: `pytest.ini` at project root
- Database: PostgreSQL (not SQLite - requires JSONB and PostgreSQL types)

**Assertion Library:**
- pytest built-in assertions
- No external assertion library (plain assert statements)

**Run Commands:**
```bash
# Run all tests with verbose output
pytest -v

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/pallet/test_migracao.py -v

# Run specific test class
pytest tests/pallet/test_migracao.py::TestTabelasExistem -v

# Run specific test method
pytest tests/pallet/test_migracao.py::TestTabelasExistem::test_tabelas_v2_existem -v

# Watch mode (requires pytest-watch)
ptw

# Stop after 5 failures
pytest --maxfail=5
```

## Test File Organization

**Location:**
- Tests in `tests/` directory at project root
- Mirror module structure: `tests/{module}/test_{feature}.py`
- Example: `app/pallet/services/credito_service.py` → `tests/pallet/test_credito_service.py`

**Naming:**
- Test files: `test_*.py`
- Test classes: `Test{FeatureName}` (e.g., `TestImportacaoNFRemessa`, `TestSolucaoBaixa`)
- Test methods: `test_{behavior}` (e.g., `test_importar_nf_remessa_cria_credito_automaticamente`)

**Structure:**
```
tests/
├── conftest.py                          # Shared fixtures
├── __init__.py
└── pallet/
    ├── __init__.py
    ├── test_migracao.py                 # Migration validation
    ├── test_fluxo_nf_credito_solucao.py # Complete flow testing
    ├── test_fluxo_nf_devolucao_vinculacao.py
    ├── test_cancelamento_auditoria.py
    └── ...
```

## Test Structure

**Fixture Pattern (conftest.py):**
```python
@pytest.fixture(scope='session')
def app():
    """Cria uma instância da aplicação configurada para testes."""
    app = create_app()
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'WTF_CSRF_ENABLED': False,
        'LOGIN_DISABLED': True,
    })
    return app


@pytest.fixture(scope='function')
def db(app):
    """Fornece o banco de dados com transação revertida após cada teste."""
    with app.app_context():
        _db.session.begin_nested()  # Start savepoint
        yield _db
        _db.session.rollback()  # Revert all changes


@pytest.fixture(scope='function')
def client(app):
    """Cliente de teste para fazer requisições HTTP."""
    return app.test_client()


@pytest.fixture
def criar_nf_remessa(db, dados_nf_remessa):
    """Factory fixture para criar NF de remessa."""
    def _criar(**kwargs):
        from app.pallet.services.nf_service import NFService
        dados = dados_nf_remessa.copy()
        if 'numero_nf' not in kwargs:
            import uuid
            unique_id = str(uuid.uuid4())[:10]
            dados['numero_nf'] = f'T{unique_id}'
            dados['chave_nfe'] = f'3526011234567800011255001000{unique_id}'
        dados.update(kwargs)
        return NFService.importar_nf_remessa_odoo(dados, usuario='test_user')
    return _criar
```

**Test Suite Organization:**
```python
class TestImportacaoNFRemessa:
    """Testa a importação de NF de remessa e criação automática de crédito."""

    def test_importar_nf_remessa_cria_credito_automaticamente(
        self, app, db, dados_nf_remessa
    ):
        """Verifica que ao importar NF de remessa, crédito é criado automaticamente."""
        with app.app_context():
            from app.pallet.services.nf_service import NFService
            from app.pallet.models.credito import PalletCredito

            # Arrange: Prepare test data
            nf_remessa = NFService.importar_nf_remessa_odoo(
                dados_nf_remessa, usuario='test_user'
            )

            # Act: Execute the behavior
            credito = PalletCredito.query.filter_by(
                nf_remessa_id=nf_remessa.id,
                ativo=True
            ).first()

            # Assert: Verify results
            assert credito is not None
            assert credito.qtd_original == 30
            assert credito.qtd_saldo == 30
            assert credito.status == 'PENDENTE'
```

**Patterns:**
- AAA (Arrange-Act-Assert) structure within each test
- `with app.app_context():` for all tests accessing database or models
- Fixtures injected as parameters to test methods
- Use `@pytest.mark.{category}` for test categorization

## Mocking

**Framework:** unittest.mock (not used extensively, prefer real objects)

**Philosophy:**
- Prefer real database transactions (using rollback isolation)
- Mock only external services (Odoo, APIs) not internal database calls
- Use fixtures for test data factories

**When to Mock:**
- External APIs (Odoo XML-RPC calls) - though many integration tests call real Odoo
- File operations (if testing import logic)
- Email/notification services

**What NOT to Mock:**
- Database models (use real instances in test DB)
- Service methods (test them fully)
- Business logic (test complete flow)

## Fixtures and Factories

**Test Data - From conftest.py:**
```python
@pytest.fixture
def dados_nf_remessa():
    """Dados padrão para criar uma NF de remessa."""
    import uuid
    unique_id = str(uuid.uuid4())[:8]

    return {
        'numero_nf': f'TEST{unique_id}',
        'serie': '1',
        'chave_nfe': f'35260112345678000112550010{unique_id}1234567890',
        'data_emissao': datetime(2026, 1, 25, 10, 0, 0),
        'quantidade': 30,
        'empresa': 'CD',
        'tipo_destinatario': 'TRANSPORTADORA',
        'cnpj_destinatario': '12345678000199',
        'nome_destinatario': 'Transportadora Teste LTDA',
        'cnpj_transportadora': None,
        'nome_transportadora': None,
        'valor_unitario': Decimal('35.00'),
        'valor_total': Decimal('1050.00'),
        'odoo_account_move_id': 12345,
        'odoo_picking_id': 54321,
        'observacao': 'NF de teste',
    }


@pytest.fixture
def criar_credito(db, criar_nf_remessa):
    """Factory fixture para criar crédito a partir de NF de remessa."""
    def _criar(**kwargs):
        from app.pallet.models.credito import PalletCredito

        nf_remessa = criar_nf_remessa(**kwargs)
        credito = PalletCredito.query.filter_by(
            nf_remessa_id=nf_remessa.id,
            ativo=True
        ).first()

        return nf_remessa, credito

    return _criar
```

**Location:**
- Shared fixtures in `tests/conftest.py`
- Module-specific fixtures in `tests/{module}/conftest.py`
- Fixture scope: `session` for app, `function` for db (isolation)

**Factory Pattern:**
- Return callable that accepts kwargs to override defaults
- Generate unique IDs (UUIDs) to avoid collisions in parallel tests
- Used for creating multiple test objects with variations

## Coverage

**Requirements:** No hard minimum enforced (configured in pytest.ini)

**View Coverage:**
```bash
pytest --cov=app --cov-report=html
# Then open htmlcov/index.html
```

**Configuration (pytest.ini):**
```ini
[coverage:run]
source = src
omit =
    */tests/*
    */migrations/*
    */__init__.py
    */config.py

[coverage:report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
    if TYPE_CHECKING:
    @abstract
```

## Test Types

**Unit Tests:**
- Scope: Single service method or model behavior
- Isolation: Real database but transactional rollback
- Speed: Fast (< 100ms per test)
- Location: `tests/{module}/test_{feature}.py`
- Marker: `@pytest.mark.unit`
- Example: `test_registrar_solucao_decrementa_saldo()` in `TestSolucaoBaixa`

**Integration Tests:**
- Scope: Multiple services working together or with Odoo
- Isolation: Real database + real external calls (when needed)
- Speed: Slower (100ms - 5s per test)
- Location: `tests/{module}/test_fluxo_{flow}.py`
- Marker: `@pytest.mark.integration`
- Example: `test_importar_nf_remessa_cria_credito_automaticamente()` in `TestImportacaoNFRemessa`

**E2E Tests:**
- Not currently used (would test HTTP endpoints with real client)
- Would use `@pytest.mark.slow`
- Would use `/routes/` fixtures via Flask test client

## Common Patterns

**Async Testing:**
Not used (Flask/SQLAlchemy are synchronous)

**Error Testing:**
```python
def test_importar_nf_valida_campos_obrigatorios(self, app, db):
    """Verifica que campos obrigatórios são validados na importação."""
    with app.app_context():
        from app.pallet.services.nf_service import NFService

        # Dados incompletos
        dados_incompletos = {'numero_nf': '999999'}

        # Use pytest.raises for exception testing
        with pytest.raises(ValueError) as exc:
            NFService.importar_nf_remessa_odoo(dados_incompletos, usuario='test_user')

        # Verify exception message
        assert 'obrigatorio' in str(exc.value).lower()
```

**Database Assertions:**
```python
def test_saldo_credito_nao_excede_original(self, app, db, criar_nf_remessa):
    """Verifica que o saldo do crédito nunca excede a quantidade original."""
    with app.app_context():
        from app.pallet.models.credito import PalletCredito
        from app.pallet.services.credito_service import CreditoService

        # Create test data
        nf = criar_nf_remessa(quantidade=30)
        credito = PalletCredito.query.filter_by(
            nf_remessa_id=nf.id, ativo=True
        ).first()

        # Assert initial state
        assert credito.qtd_saldo == credito.qtd_original

        # Perform operation
        CreditoService.registrar_solucao(
            credito_id=credito.id,
            tipo_solucao='BAIXA',
            quantidade=10,
            usuario='test_user',
            dados_adicionais={'motivo': 'Teste'}
        )

        # Refresh and assert new state
        db.session.refresh(credito)
        assert credito.qtd_saldo < credito.qtd_original
        assert credito.qtd_saldo == 20
```

**Relationship Testing:**
```python
def test_nf_remessa_para_creditos(self, app, db, criar_nf_remessa):
    """Verifica relationship NF Remessa → Créditos (backref)."""
    with app.app_context():
        from app.pallet.models.nf_remessa import PalletNFRemessa

        nf = criar_nf_remessa(quantidade=30)
        nf_db = PalletNFRemessa.query.get(nf.id)

        # Test backref relationship
        assert hasattr(nf_db, 'creditos')
        creditos_list = list(nf_db.creditos)
        assert len(creditos_list) == 1
        assert creditos_list[0].qtd_original == 30
```

## Markers and Organization

**Markers Defined (pytest.ini):**
```ini
markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (may require external services)
    slow: Slow running tests
    auth: Authentication related tests
    neural: Neural processing tests
    memory: Memory system tests
    cache: Caching system tests
    security: Security feature tests
    mcp: MCP protocol tests
    pallet: Pallet module tests (v2 restructure)
    migracao: Migration tests for pallet module v2
```

**Usage:**
```python
# Mark entire test module
pytestmark = [pytest.mark.unit, pytest.mark.pallet, pytest.mark.migracao]

# Mark individual test
@pytest.mark.slow
def test_computationally_heavy():
    pass

# Run tests by marker
pytest -m unit          # Only unit tests
pytest -m "pallet and migracao"  # Both markers
pytest -m "not slow"    # Exclude slow
```

## Isolation Strategy

**Database Isolation:**
- Each test runs in `nested transaction` (savepoint)
- Changes are rolled back at end of test
- No cleanup needed - database is clean for next test
- Prevents test interdependencies

**Test Configuration (pytest.ini):**
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

addopts =
    -v
    --strict-markers
    --tb=short
    -p no:warnings
    --maxfail=5
    --durations=10

asyncio_mode = auto
timeout = 300
timeout_method = thread

env =
    TESTING=true
    DATABASE_URL=sqlite:///:memory:
    REDIS_URL=redis://localhost:6379/15
    JWT_SECRET=test-secret-key
    ENCRYPTION_KEY=test-encryption-key
```

## Environment Variables

**Test Environment (from pytest.ini):**
```bash
TESTING=true              # Marks running in test mode
DATABASE_URL=...          # Uses local PostgreSQL (not SQLite)
REDIS_URL=...             # Redis for caching/sessions
JWT_SECRET=test-secret-key
ENCRYPTION_KEY=test-encryption-key
```

**Important Notes:**
- PostgreSQL required (not SQLite) for JSONB and PostgreSQL types
- Must have local PostgreSQL running to execute tests
- Tests use transactional rollback, not database recreation

## Test Execution Options

**Pytest Configuration (pytest.ini):**
- Verbose output: `-v`
- Strict markers: `--strict-markers` (fail on unknown markers)
- Short traceback: `--tb=short`
- Suppress warnings: `-p no:warnings`
- Stop after 5 failures: `--maxfail=5`
- Show slowest 10 tests: `--durations=10`
- Test timeout: 300 seconds per test

---

*Testing analysis: 2026-01-25*
