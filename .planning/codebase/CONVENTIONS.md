# Coding Conventions

**Analysis Date:** 2026-01-25

## Naming Patterns

**Files:**
- Python modules: `snake_case.py` (e.g., `credito_service.py`, `nf_remessa.py`, `controle_pallets.py`)
- Test files: `test_*.py` (e.g., `test_migracao.py`, `test_fluxo_nf_credito_solucao.py`)
- Blueprints: `{domain}_{feature}_bp` (e.g., `controle_pallets_bp = Blueprint('controle_pallets', ...)`)

**Functions:**
- Snake case for all functions: `registrar_solucao()`, `criar_credito_ao_importar_nf()`, `marcar_documento_recebido()`
- Prefix with action verbs: `criar_`, `registrar_`, `atualizar_`, `listar_`, `validar_`, `importar_`
- Private methods prefixed with underscore: `_calcular_saldo()`, `_validar_quantidade()`

**Variables:**
- Snake case for all variables: `qtd_original`, `nf_remessa_id`, `cnpj_destinatario`, `usuario`
- Portuguese identifiers throughout codebase (no English mixing)
- Prefixes for clarity: `qtd_` (quantidade), `cnpj_`, `nf_` (nota fiscal), `nfs` (plural)

**Types:**
- Class names: `PascalCase` (e.g., `PalletCredito`, `PalletNFRemessa`, `CreditoService`)
- Database tables: `snake_case_plural` (e.g., `pallet_creditos`, `pallet_nf_remessa`, `pallet_documentos`)
- Enum/constant values: `UPPER_CASE` (e.g., `'PENDENTE'`, `'RESOLVIDO'`, `'CANHOTO'`)

## Code Style

**Formatting:**
- Line length: 120 characters (configured in `pyproject.toml`)
- Black formatter used for Python
- isort configured with Black profile for imports

**Linting:**
- Flake8 used with configuration in `setup.cfg`
- Ignored rules: E501 (long lines), E302/E303 (blank lines), F401 (unused imports), F811 (redefined), F841 (unused variable)
- Max line length: 120

**Tool Configuration:**
```ini
# setup.cfg (flake8)
[flake8]
ignore = E501,E302,E303,E712,E128,W293,W291,W292,F401,F811,F841,F601
max-line-length = 120
exclude = .git,__pycache__,.venv,venv,migrations,node_modules
```

```toml
# pyproject.toml (Black + isort)
[tool.black]
line-length = 120
target-version = ['py38']

[tool.isort]
profile = "black"
multi_line_output = 3
line_length = 120
```

## Import Organization

**Order:**
1. Standard library imports (`os`, `sys`, `datetime`, `decimal`, etc.)
2. Third-party imports (`flask`, `sqlalchemy`, `pytest`, etc.)
3. Application imports (`from app import db`, `from app.pallet.models`, etc.)

**Path Aliases:**
- Not explicitly used; full relative paths from `app/` root
- Example: `from app.pallet.models.credito import PalletCredito`
- Example: `from app.pallet.services import CreditoService`

**Import Style:**
```python
# Standard library first
import os
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

# Third-party
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import func, text

# Application
from app import db
from app.pallet.models import (
    PalletCredito, PalletDocumento, PalletSolucao, PalletNFRemessa
)
from app.pallet.services import CreditoService, SolucaoPalletService
from app.utils.valores_brasileiros import converter_valor_brasileiro
```

## Error Handling

**Patterns:**
- Use specific exceptions (`ValueError`, `NotImplementedError`) not generic `Exception`
- Always log exceptions with context: `logger.warning(f"NF #{nf_remessa_id} já possui crédito #{credito_existente.id}")`
- Raise early with descriptive messages: `raise ValueError(f"NF de remessa #{nf_remessa_id} não encontrada")`
- Fields that must be present: Check and raise `ValueError` with message ending in "é obrigatorio"

**Common Error Pattern:**
```python
@staticmethod
def criar_credito_ao_importar_nf(nf_remessa_id: int, usuario: str = None) -> PalletCredito:
    """..."""
    # Validate input
    nf_remessa = PalletNFRemessa.query.get(nf_remessa_id)
    if not nf_remessa:
        raise ValueError(f"NF de remessa #{nf_remessa_id} não encontrada")

    # Check business rule
    credito_existente = PalletCredito.query.filter(
        PalletCredito.nf_remessa_id == nf_remessa_id,
        PalletCredito.ativo == True
    ).first()

    if credito_existente:
        logger.warning(f"NF #{nf_remessa_id} já possui crédito #{credito_existente.id}")
        return credito_existente

    # Create and return
    ...
```

## Logging

**Framework:** `logging` module with `logging.getLogger(__name__)`

**Pattern:**
- Module-level logger: `logger = logging.getLogger(__name__)` at top of file
- Use different levels: `logger.info()` for operations, `logger.warning()` for issues
- Include context in messages: Always mention IDs or relevant data

**Levels Used:**
```python
logger.info(f"✅ Documento #{documento_id} marcado como recebido por {usuario}")
logger.warning(f"NF #{nf_remessa_id} já possui crédito #{credito_existente.id}")
logger.info(f"Registrando solução tipo {tipo_solucao} de {quantidade} pallets")
```

**Emoji Usage:**
- ✅ for successful operations
- ⚠️ or ❌ for warnings/errors
- Used in production logging statements (not just comments)

## Comments

**When to Comment:**
- Module docstrings: Always (triple-quoted, describe purpose and spec reference)
- Class docstrings: Always (describe responsibility, relationships, status values)
- Method docstrings: Always (describe Args, Returns, Raises with types)
- Inline comments: Only for business logic requiring explanation (e.g., "REGRA 001 (PRD): ...")
- TODO/FIXME: Use when needed but prefer to resolve before commit

**DocString Format:**
```python
def registrar_solucao(
    credito_id: int,
    tipo_solucao: str,
    quantidade: int,
    usuario: str,
    dados_adicionais: Dict = None
) -> Tuple[PalletSolucao, PalletCredito]:
    """
    Registra solução que decrementa saldo do crédito.

    REGRA 002 (PRD): Ao REGISTRAR SOLUÇÃO:
    - CRIAR registro em pallet_solucoes
    - DECREMENTAR qtd_saldo do crédito
    - ATUALIZAR status do crédito

    Args:
        credito_id: ID do crédito
        tipo_solucao: Tipo de solução (BAIXA, VENDA, RECEBIMENTO, SUBSTITUIÇÃO)
        quantidade: Quantidade de pallets
        usuario: Usuário que registra a operação
        dados_adicionais: Dict com dados específicos do tipo de solução

    Returns:
        Tuple[PalletSolucao, PalletCredito]: Solução criada e crédito atualizado

    Raises:
        ValueError: Se crédito não existe ou quantidade inválida
    """
```

## Function Design

**Size:**
- Target: 30-50 lines per function
- Hard limit: 100 lines (split into helper methods)
- Service methods: 20-40 lines typically

**Parameters:**
- Maximum 5 regular parameters (use dict/object for more)
- Use type hints: `def registrar_solucao(credito_id: int, tipo_solucao: str, quantidade: int) -> PalletSolucao:`
- Optional parameters with defaults at end: `usuario: str = None`, `dados_adicionais: Dict = None`

**Return Values:**
- Return single objects for single responsibility: `def criar_credito(...) -> PalletCredito:`
- Return tuples for related updates: `def registrar_solucao(...) -> Tuple[PalletSolucao, PalletCredito]:`
- Use `Optional[]` for nullable returns: `def buscar_nf(...) -> Optional[PalletNFRemessa]:`

**Static Methods:**
- Use `@staticmethod` for utility/factory methods in services
- No access to instance state
- Examples: `CreditoService.criar_credito_ao_importar_nf()`, `NFService.validar_campos_obrigatorios()`

## Module Design

**Exports:**
- Explicit barrel files with `__init__.py` in service/model directories
- Example from `app/pallet/services/__init__.py`:
  ```python
  from app.pallet.services.credito_service import CreditoService
  from app.pallet.services.nf_service import NFService
  from app.pallet.services.solucao_pallet_service import SolucaoPalletService
  ```

**Barrel Files:**
- Used in `app/pallet/models/__init__.py` to re-export models
- Used in `app/pallet/services/__init__.py` to simplify imports
- Enables: `from app.pallet.models import PalletCredito` instead of `from app.pallet.models.credito import PalletCredito`

**Organization:**
- Services (business logic) in `app/{module}/services/{feature}_service.py`
- Models (data) in `app/{module}/models/{feature}.py`
- Routes (Flask) in `app/{module}/routes/{feature}.py`
- Utilities in `app/{module}/utils/{utility}.py` or `app/utils/{shared}.py`

## Database Column Naming

**Field Convention:**
- Foreign keys: `{entity}_{id}` (e.g., `nf_remessa_id`, `credito_id`)
- Quantities: `qtd_{description}` (e.g., `qtd_original`, `qtd_saldo`)
- Names/descriptions: `nome_{context}` or just `{entity}` (e.g., `nome_destinatario`, `nome_produto`)
- Document numbers: `numero_{type}` (e.g., `numero_nf`, `numero_documento`)
- Keys: `chave_{type}` (e.g., `chave_nfe`)
- Dates: `data_{event}` (e.g., `data_emissao`, `data_validade`)
- Status/state: `status` (string enum) or `{state}` (boolean: `recebido`, `ativo`)
- IDs from external systems: `odoo_{model}_{field}` (e.g., `odoo_account_move_id`, `odoo_picking_id`)

**Precision:**
- Monetary values: `Numeric(15, 2)` - stored as integers (cents) in checks
- Quantities: `Numeric(15, 3)` for fractional pallets
- Pure integers: `Integer` for counts

## Type Hints

**Used Throughout:**
```python
def registrar_documento(
    credito_id: int,
    tipo: str,
    quantidade: int,
    usuario: str,
    numero_documento: str,
    data_emissao: date = None,
) -> PalletDocumento:
```

**Import Statement:**
```python
from typing import Dict, List, Optional, Tuple
```

**Nullable Returns:**
```python
def buscar_nf(nf_id: int) -> Optional[PalletNFRemessa]:
    return PalletNFRemessa.query.get(nf_id)
```

## Specification References

**Convention:** Every service/model includes spec reference in docstring:
```python
"""
Service de Crédito de Pallet - Domínio A

Este service gerencia...

Spec: .claude/ralph-loop/specs/prd-reestruturacao-modulo-pallets.md
"""
```

**Rule References:** Use PRD rule format in docstrings:
```python
"""
REGRA 001 (PRD): Ao IMPORTAR NF de remessa do Odoo:
- CRIAR registro em pallet_creditos vinculado automaticamente
- qtd_saldo inicial = quantidade da NF importada
"""
```

---

*Convention analysis: 2026-01-25*
