# Motos Assaí — Fase 2-3 (Carregamento Service + UI) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar entidade Carregamento completa: service `carregamento_service.py` com 4 operações (criar, escanear, cancelar item, cancelar carregamento) + algoritmo `finalizar_carregamento` em 8 fases (§6 da spec) + service `alterar_carregamento` (S6=a reabre) + atualização de services existentes (`cancelar_separacao`, `mirror_assai_to_separacao`) + UI completa (lista, escaneio, 3 modais) + onboarding tour.

**Architecture:** Service segue padrão `separacao_service.py` (lock pessimista, eventos via `moto_evento_service`). Algoritmo `finalizar_carregamento` implementado fase a fase, cada fase com testes unitários isolados. UI reusa `chassi_autocomplete.js` e padrão Bootstrap modal de `separacao/tela.html`. Onboarding via Driver.js seguindo padrão de Plano 5 (motos_assai existente).

**Tech Stack:** Flask 2.x, SQLAlchemy 2.x, PostgreSQL 14+, Bootstrap 5, html5-qrcode 2.3.8, Driver.js (onboarding).

**Spec referenciada:** `docs/superpowers/specs/2026-05-12-motos-assai-carregamento-divergencia-design.md` (v1.2) §6, §15.1-15.2, §13

**Pré-requisito:** Plano 1 (Fase 1 — Fundação) **completo e deployado em prod**. Validar:
- Tabelas `assai_carregamento` + `assai_carregamento_item` existem (Migration 18)
- Constantes `CARREGAMENTO_STATUS_*`, `EVENTO_CARREGADA`, `SEPARACAO_STATUS_CARREGADA` importam OK
- Service `recalcular_status_pedido` funciona

---

## File Structure

### Services a criar/expandir

- **EXPANDIR** `app/motos_assai/services/carregamento_service.py` — Plano 1 declarou só `CarregamentoExcedenteError`. Aqui adicionamos toda a lógica:
  - `criar_carregamento(pedido_id, loja_id, operador_id) -> AssaiCarregamento`
  - `escanear_carregamento_item(carregamento_id, chassi, operador_id) -> AssaiCarregamentoItem`
  - `cancelar_carregamento_item(item_id, operador_id) -> None`
  - `cancelar_carregamento(carregamento_id, motivo, operador_id) -> None`
  - `finalizar_carregamento(carregamento_id, operador_id) -> AssaiSeparacao`
  - `alterar_carregamento(carregamento_id, operador_id) -> None` (S6=a reabre)
  - `_calcular_count_em_comum(sep_id, chassis) -> int` (helper)

### Services a modificar

- `app/motos_assai/services/separacao_service.py` — `cancelar_separacao` deve aceitar status `CARREGADA` (não apenas `EM_SEPARACAO`/`FECHADA`)
- `app/motos_assai/services/separacao_mirror_service.py` — modificar guarda de `mirror_assai_to_separacao` para aceitar `(FECHADA, CARREGADA, FATURADA)` (S12=a)

### Routes a criar

- `app/motos_assai/routes/carregamento.py` — registrar no blueprint `motos_assai_bp`

Rotas:
| Método | URL | Função |
|---|---|---|
| GET | `/motos-assai/carregamento` | `lista_carregamentos` |
| POST | `/motos-assai/carregamento/iniciar` | `iniciar_carregamento` (form criar) |
| GET | `/motos-assai/carregamento/<id>` | `detalhe_carregamento` (escaneio) |
| POST | `/motos-assai/carregamento/<id>/escanear` | `escanear_chassi_ajax` |
| POST | `/motos-assai/carregamento/item/<item_id>/cancelar` | `cancelar_item_ajax` |
| POST | `/motos-assai/carregamento/<id>/finalizar` | `finalizar_ajax` |
| POST | `/motos-assai/carregamento/<id>/cancelar` | `cancelar_carregamento_ajax` |
| POST | `/motos-assai/carregamento/<id>/alterar` | `alterar_carregamento_ajax` (S6) |

### Templates a criar

- `app/templates/motos_assai/carregamento/lista.html` (lista + form iniciar)
- `app/templates/motos_assai/carregamento/escanear.html` (tela operacional escaneio)
- `app/templates/motos_assai/carregamento/_modal_finalizar.html` (include)
- `app/templates/motos_assai/carregamento/_modal_cancelar.html` (include)
- `app/templates/motos_assai/carregamento/_modal_alterar.html` (include)
- `app/templates/motos_assai/carregamento/_modal_excedente.html` (CarregamentoExcedenteError)

### Static (JS) a criar

- `app/static/motos_assai/js/carregamento_escanear.js` (orquestrador escaneio + modais)

### Modificações UI

- `app/templates/base.html` — adicionar link "Carregamento" no menu Motos Assaí (condicional `pode_acessar_motos_assai()`)

### Onboarding tours

- `app/static/onboarding/tours/motos_assai/carregamento_lista.js`
- `app/static/onboarding/tours/motos_assai/carregamento_escanear.js`
- Atualizar macro `motos_assai.macro` (engine de tours) para registrar 2 mini-tours
- Incluir `<script>` em `app/templates/admin/onboarding_health.html` E `onboarding_preview.html` (regra do CLAUDE.md motos_assai §Onboarding Tours)

### Tests a criar

- `tests/motos_assai/test_carregamento_service_crud.py` (criar, escanear, cancelar item, cancelar)
- `tests/motos_assai/test_carregamento_finalizar_fase1.py` (identificar/criar sep alvo)
- `tests/motos_assai/test_carregamento_finalizar_fase2.py` (sobrescrever)
- `tests/motos_assai/test_carregamento_finalizar_fase3.py` (limite pedido)
- `tests/motos_assai/test_carregamento_finalizar_fase4_5_6.py` (sep CARREGADA + Excel + mirror)
- `tests/motos_assai/test_carregamento_finalizar_fase7_8.py` (divergência NF + recalcular)
- `tests/motos_assai/test_carregamento_alterar.py` (reabrir)
- `tests/motos_assai/test_cancelar_separacao_carregada.py` (atualização cancelar_separacao)
- `tests/motos_assai/test_mirror_aceita_carregada.py` (S12)

---

## Tasks

### Task 1: Service `criar_carregamento` + testes

**Files:**
- Modify: `app/motos_assai/services/carregamento_service.py` (já existe da Fase 1, expandir)
- Create: `tests/motos_assai/test_carregamento_service_crud.py`

- [ ] **Step 1: Escrever teste falhando**

Criar `tests/motos_assai/test_carregamento_service_crud.py`:

```python
"""Testes CRUD basico de carregamento_service.

Spec: §6 (carregamento), §15.1
Plano: Tasks 1-4
"""
import pytest
from app import create_app, db
from app.motos_assai.models import (
    AssaiCd, AssaiLoja, AssaiModelo, AssaiPedidoVenda, AssaiCarregamento,
    CARREGAMENTO_STATUS_EM_CARREGAMENTO, CARREGAMENTO_STATUS_CANCELADO,
    PEDIDO_STATUS_ABERTO,
)
from app.motos_assai.services.carregamento_service import (
    criar_carregamento, CarregamentoValidationError,
)


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.rollback()
        db.drop_all()


@pytest.fixture
def setup_pedido_loja(app):
    cd = AssaiCd(nome='CD', cnpj='12345678000100')
    loja = AssaiLoja(numero=999, cnpj='98765432000100', nome='Loja Teste')
    modelo = AssaiModelo(codigo='SOL')
    db.session.add_all([cd, loja, modelo])
    db.session.flush()
    pedido = AssaiPedidoVenda(numero='TEST001', cd_id=cd.id, status=PEDIDO_STATUS_ABERTO)
    db.session.add(pedido)
    db.session.commit()
    return pedido, loja, modelo


def test_criar_carregamento_sucesso(setup_pedido_loja):
    pedido, loja, _ = setup_pedido_loja
    car = criar_carregamento(pedido.id, loja.id, operador_id=1)
    db.session.commit()

    assert car.id is not None
    assert car.status == CARREGAMENTO_STATUS_EM_CARREGAMENTO
    assert car.pedido_id == pedido.id
    assert car.loja_id == loja.id
    assert car.iniciado_por_id == 1
    assert car.iniciado_em is not None
    assert car.separacao_id is None  # so vincula no finalize
    assert car.finalizado_em is None
    assert car.cancelado_em is None


def test_criar_carregamento_pedido_inexistente(setup_pedido_loja):
    _, loja, _ = setup_pedido_loja
    with pytest.raises(CarregamentoValidationError, match='Pedido'):
        criar_carregamento(99999, loja.id, operador_id=1)


def test_criar_carregamento_loja_inexistente(setup_pedido_loja):
    pedido, _, _ = setup_pedido_loja
    with pytest.raises(CarregamentoValidationError, match='Loja'):
        criar_carregamento(pedido.id, 99999, operador_id=1)


def test_criar_carregamento_dois_paralelos_mesma_loja_OK(setup_pedido_loja):
    """A2: 2 carregamentos paralelos no mesmo (pedido, loja) sao permitidos."""
    pedido, loja, _ = setup_pedido_loja
    car1 = criar_carregamento(pedido.id, loja.id, operador_id=1)
    db.session.flush()
    car2 = criar_carregamento(pedido.id, loja.id, operador_id=2)
    db.session.commit()

    assert car1.id != car2.id
    assert car1.status == car2.status == CARREGAMENTO_STATUS_EM_CARREGAMENTO
```

- [ ] **Step 2: Rodar teste — deve falhar (função `criar_carregamento` não existe)**

```bash
source .venv/bin/activate
pytest tests/motos_assai/test_carregamento_service_crud.py::test_criar_carregamento_sucesso -v
```

Expected: ImportError / `criar_carregamento` not found.

- [ ] **Step 3: Implementar `criar_carregamento` em `carregamento_service.py`**

Localizar arquivo `app/motos_assai/services/carregamento_service.py` (já existe da Fase 1 com apenas `CarregamentoExcedenteError`). Adicionar:

```python
"""Service de Carregamento (Fase 2 + 3).

Spec: §6, §15.1-15.2
Plano: docs/superpowers/plans/2026-05-12-motos-assai-fase2-3-carregamento.md
"""
from sqlalchemy.exc import IntegrityError
from app import db
from app.motos_assai.models import (
    AssaiCarregamento, AssaiCarregamentoItem,
    AssaiPedidoVenda, AssaiLoja, AssaiModelo, AssaiMoto,
    AssaiSeparacao, AssaiSeparacaoItem,
    CARREGAMENTO_STATUS_EM_CARREGAMENTO, CARREGAMENTO_STATUS_FINALIZADO,
    CARREGAMENTO_STATUS_CANCELADO,
    SEPARACAO_STATUS_EM_SEPARACAO, SEPARACAO_STATUS_FECHADA,
    SEPARACAO_STATUS_CARREGADA, SEPARACAO_STATUS_FATURADA,
    EVENTO_DISPONIVEL, EVENTO_SEPARADA, EVENTO_CARREGADA,
)
from app.utils.timezone import agora_brasil_naive


# ============================================================
# Exceptions
# ============================================================

class CarregamentoError(Exception):
    """Erro base de carregamento_service."""


class CarregamentoValidationError(CarregamentoError):
    """Validacao de input falhou (pedido/loja inexistente, etc.)."""


class CarregamentoConflictError(CarregamentoError):
    """Race condition (chassi ja em outro carregamento, etc.) — retorna HTTP 409."""


class CarregamentoStateError(CarregamentoError):
    """Operacao invalida no estado atual (ex: cancelar carregamento ja FINALIZADO sem motivo)."""


class CarregamentoExcedenteError(CarregamentoError):
    """Finalizar carregamento excederia qtd do pedido — operador deve resolver (S14=a)."""

    def __init__(self, msg, *, qtd_excedente=None, seps_bloqueadas=None):
        super().__init__(msg)
        self.qtd_excedente = qtd_excedente
        self.seps_bloqueadas = seps_bloqueadas or []  # lista de sep_ids CARREGADA/FATURADA


# ============================================================
# CRUD basico
# ============================================================

def criar_carregamento(pedido_id, loja_id, operador_id):
    """Cria novo Carregamento em status EM_CARREGAMENTO.

    A2: NAO ha UNIQUE em (pedido, loja, EM_CARREGAMENTO) — N carregamentos
    paralelos sao permitidos.

    Args:
        pedido_id: ID do AssaiPedidoVenda (deve existir)
        loja_id: ID da AssaiLoja (deve existir)
        operador_id: ID do usuario que iniciou

    Returns:
        AssaiCarregamento criado (status EM_CARREGAMENTO).

    Raises:
        CarregamentoValidationError: pedido ou loja nao existem.
    """
    pedido = AssaiPedidoVenda.query.get(pedido_id)
    if not pedido:
        raise CarregamentoValidationError(f'Pedido {pedido_id} nao encontrado')

    loja = AssaiLoja.query.get(loja_id)
    if not loja:
        raise CarregamentoValidationError(f'Loja {loja_id} nao encontrada')

    car = AssaiCarregamento(
        pedido_id=pedido_id,
        loja_id=loja_id,
        status=CARREGAMENTO_STATUS_EM_CARREGAMENTO,
        iniciado_em=agora_brasil_naive(),
        iniciado_por_id=operador_id,
    )
    db.session.add(car)
    db.session.flush()  # garante car.id disponivel; commit fica para o caller
    return car
```

- [ ] **Step 4: Rodar testes — devem passar**

```bash
pytest tests/motos_assai/test_carregamento_service_crud.py -v -k 'criar'
```

Expected: 4 passed (criar_carregamento_sucesso, criar_carregamento_pedido_inexistente, criar_carregamento_loja_inexistente, criar_carregamento_dois_paralelos_mesma_loja_OK).

- [ ] **Step 5: Commit**

```bash
git add app/motos_assai/services/carregamento_service.py tests/motos_assai/test_carregamento_service_crud.py
git commit -m "feat(motos-assai): carregamento_service.criar_carregamento + testes

A2: permite N carregamentos paralelos por (pedido, loja).
4 exceptions definidas: Validation, Conflict, State, Excedente."
```

---

### Task 2: Service `escanear_carregamento_item` (lock pessimista S3=c) + testes

**Files:**
- Modify: `app/motos_assai/services/carregamento_service.py`
- Modify: `tests/motos_assai/test_carregamento_service_crud.py`

- [ ] **Step 1: Adicionar testes**

Adicionar ao `tests/motos_assai/test_carregamento_service_crud.py`:

```python
from app.motos_assai.models import AssaiMoto, EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_DISPONIVEL
from app.motos_assai.services.moto_evento_service import emitir_evento
from app.motos_assai.services.carregamento_service import (
    escanear_carregamento_item, CarregamentoConflictError,
)


@pytest.fixture
def chassi_disponivel(setup_pedido_loja):
    pedido, loja, modelo = setup_pedido_loja
    moto = AssaiMoto(chassi='TESTC001', modelo_id=modelo.id, cor='Preto')
    db.session.add(moto)
    db.session.flush()
    emitir_evento('TESTC001', EVENTO_ESTOQUE, operador_id=1)
    emitir_evento('TESTC001', EVENTO_MONTADA, operador_id=1)
    emitir_evento('TESTC001', EVENTO_DISPONIVEL, operador_id=1)
    db.session.commit()
    return moto


def test_escanear_chassi_disponivel_sucesso(setup_pedido_loja, chassi_disponivel):
    pedido, loja, _ = setup_pedido_loja
    car = criar_carregamento(pedido.id, loja.id, operador_id=1)
    db.session.flush()

    item = escanear_carregamento_item(car.id, 'TESTC001', operador_id=1)
    db.session.commit()

    assert item.id is not None
    assert item.carregamento_id == car.id
    assert item.chassi == 'TESTC001'
    assert item.escaneado_por_id == 1
    # A1: NAO emite evento durante escaneio (apenas no finalize)
    from app.motos_assai.services.moto_evento_service import status_efetivo
    assert status_efetivo('TESTC001') == EVENTO_DISPONIVEL


def test_escanear_chassi_inexistente_falha(setup_pedido_loja):
    pedido, loja, _ = setup_pedido_loja
    car = criar_carregamento(pedido.id, loja.id, operador_id=1)
    db.session.flush()

    with pytest.raises(CarregamentoValidationError, match='Chassi'):
        escanear_carregamento_item(car.id, 'INEXISTENTE', operador_id=1)


def test_escanear_chassi_em_outro_carregamento_ativo_falha(setup_pedido_loja, chassi_disponivel):
    """S3=c: chassi nao pode estar em 2 carregamentos ativos."""
    pedido, loja, _ = setup_pedido_loja
    car1 = criar_carregamento(pedido.id, loja.id, operador_id=1)
    db.session.flush()
    escanear_carregamento_item(car1.id, 'TESTC001', operador_id=1)
    db.session.commit()

    car2 = criar_carregamento(pedido.id, loja.id, operador_id=2)
    db.session.flush()
    with pytest.raises(CarregamentoConflictError, match='outro carregamento'):
        escanear_carregamento_item(car2.id, 'TESTC001', operador_id=2)


def test_escanear_carregamento_finalizado_falha(setup_pedido_loja, chassi_disponivel):
    pedido, loja, _ = setup_pedido_loja
    car = criar_carregamento(pedido.id, loja.id, operador_id=1)
    car.status = CARREGAMENTO_STATUS_FINALIZADO
    db.session.commit()

    with pytest.raises(CarregamentoStateError, match='FINALIZADO'):
        escanear_carregamento_item(car.id, 'TESTC001', operador_id=1)
```

- [ ] **Step 2: Rodar — devem falhar**

```bash
pytest tests/motos_assai/test_carregamento_service_crud.py -v -k 'escanear'
```

- [ ] **Step 3: Implementar `escanear_carregamento_item`**

Adicionar ao `carregamento_service.py`:

```python
def escanear_carregamento_item(carregamento_id, chassi, operador_id):
    """Adiciona chassi ao carregamento ativo.

    S3=c: lock pessimista em assai_moto + valida que chassi NAO esta em outro
    carregamento ativo (EM_CARREGAMENTO).

    A1: NAO emite evento (estado muda apenas no finalize).

    Args:
        carregamento_id: ID do carregamento (deve estar EM_CARREGAMENTO)
        chassi: chassi a adicionar
        operador_id: usuario que escaneou

    Returns:
        AssaiCarregamentoItem criado.

    Raises:
        CarregamentoValidationError: chassi inexistente em assai_moto
        CarregamentoStateError: carregamento nao esta EM_CARREGAMENTO
        CarregamentoConflictError: chassi ja em outro carregamento ativo
    """
    car = AssaiCarregamento.query.get(carregamento_id)
    if not car:
        raise CarregamentoValidationError(f'Carregamento {carregamento_id} nao encontrado')
    if car.status != CARREGAMENTO_STATUS_EM_CARREGAMENTO:
        raise CarregamentoStateError(
            f'Carregamento {carregamento_id} esta {car.status} '
            f'(esperado EM_CARREGAMENTO)'
        )

    # Lock pessimista no chassi (S3=c)
    moto = (AssaiMoto.query
            .filter_by(chassi=chassi)
            .with_for_update()
            .first())
    if not moto:
        raise CarregamentoValidationError(f'Chassi {chassi} nao cadastrado em assai_moto')

    # Validar chassi NAO esta em outro carregamento ativo
    item_em_outro = (AssaiCarregamentoItem.query
                     .join(AssaiCarregamento)
                     .filter(
                         AssaiCarregamentoItem.chassi == chassi,
                         AssaiCarregamento.status == CARREGAMENTO_STATUS_EM_CARREGAMENTO,
                         AssaiCarregamento.id != carregamento_id,
                     )
                     .first())
    if item_em_outro:
        raise CarregamentoConflictError(
            f'Chassi {chassi} ja esta no Carregamento #{item_em_outro.carregamento_id} '
            f'(EM_CARREGAMENTO). Cancele ou finalize o outro antes.'
        )

    # Validar chassi nao ja escaneado no MESMO carregamento (idempotencia)
    ja_escaneado = AssaiCarregamentoItem.query.filter_by(
        carregamento_id=carregamento_id, chassi=chassi,
    ).first()
    if ja_escaneado:
        raise CarregamentoConflictError(
            f'Chassi {chassi} ja foi escaneado neste Carregamento (item #{ja_escaneado.id})'
        )

    item = AssaiCarregamentoItem(
        carregamento_id=carregamento_id,
        chassi=chassi,
        modelo_id=moto.modelo_id,
        escaneado_em=agora_brasil_naive(),
        escaneado_por_id=operador_id,
    )
    db.session.add(item)
    db.session.flush()
    return item
```

- [ ] **Step 4: Rodar testes — devem passar**

```bash
pytest tests/motos_assai/test_carregamento_service_crud.py -v -k 'escanear'
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add app/motos_assai/services/carregamento_service.py tests/motos_assai/test_carregamento_service_crud.py
git commit -m "feat(motos-assai): escanear_carregamento_item com lock pessimista (S3=c) + A1 sem evento"
```

---

### Task 3: Service `cancelar_carregamento_item` + testes

**Files:**
- Modify: `app/motos_assai/services/carregamento_service.py`
- Modify: `tests/motos_assai/test_carregamento_service_crud.py`

- [ ] **Step 1: Adicionar testes**

```python
from app.motos_assai.services.carregamento_service import cancelar_carregamento_item


def test_cancelar_item_sucesso(setup_pedido_loja, chassi_disponivel):
    pedido, loja, _ = setup_pedido_loja
    car = criar_carregamento(pedido.id, loja.id, operador_id=1)
    db.session.flush()
    item = escanear_carregamento_item(car.id, 'TESTC001', operador_id=1)
    db.session.commit()

    cancelar_carregamento_item(item.id, operador_id=1)
    db.session.commit()

    # Item deletado
    assert AssaiCarregamentoItem.query.get(item.id) is None

    # A1: chassi nunca mudou de evento — continua DISPONIVEL
    from app.motos_assai.services.moto_evento_service import status_efetivo
    assert status_efetivo('TESTC001') == EVENTO_DISPONIVEL


def test_cancelar_item_carregamento_finalizado_falha(setup_pedido_loja, chassi_disponivel):
    pedido, loja, _ = setup_pedido_loja
    car = criar_carregamento(pedido.id, loja.id, operador_id=1)
    db.session.flush()
    item = escanear_carregamento_item(car.id, 'TESTC001', operador_id=1)
    car.status = CARREGAMENTO_STATUS_FINALIZADO
    db.session.commit()

    with pytest.raises(CarregamentoStateError, match='FINALIZADO'):
        cancelar_carregamento_item(item.id, operador_id=1)
```

- [ ] **Step 2: Rodar — devem falhar**

```bash
pytest tests/motos_assai/test_carregamento_service_crud.py -v -k 'cancelar_item'
```

- [ ] **Step 3: Implementar**

```python
def cancelar_carregamento_item(item_id, operador_id):
    """Remove item do carregamento (apenas durante EM_CARREGAMENTO).

    A1: NAO emite evento (estado nunca mudou).

    Args:
        item_id: ID do AssaiCarregamentoItem
        operador_id: usuario que cancelou (para audit log futuro)

    Raises:
        CarregamentoValidationError: item nao existe
        CarregamentoStateError: carregamento ja FINALIZADO ou CANCELADO
    """
    item = AssaiCarregamentoItem.query.get(item_id)
    if not item:
        raise CarregamentoValidationError(f'Item {item_id} nao encontrado')

    car = item.carregamento
    if car.status != CARREGAMENTO_STATUS_EM_CARREGAMENTO:
        raise CarregamentoStateError(
            f'Carregamento {car.id} esta {car.status} — nao e possivel cancelar item. '
            f'Use alterar_carregamento (S6=a) para reabrir.'
        )

    db.session.delete(item)
    db.session.flush()
```

- [ ] **Step 4: Rodar — devem passar**

```bash
pytest tests/motos_assai/test_carregamento_service_crud.py -v -k 'cancelar_item'
```

- [ ] **Step 5: Commit**

```bash
git add app/motos_assai/services/carregamento_service.py tests/motos_assai/test_carregamento_service_crud.py
git commit -m "feat(motos-assai): cancelar_carregamento_item (apenas EM_CARREGAMENTO)"
```

---

### Task 4: Service `cancelar_carregamento` (S5 distinção EM_CARREGAMENTO vs FINALIZADO)

**Files:**
- Modify: `app/motos_assai/services/carregamento_service.py`
- Modify: `tests/motos_assai/test_carregamento_service_crud.py`

- [ ] **Step 1: Adicionar testes**

```python
from app.motos_assai.services.carregamento_service import cancelar_carregamento


def test_cancelar_carregamento_em_carregamento_chassi_volta_anterior(setup_pedido_loja, chassi_disponivel):
    """S5: Cancelar Carregamento EM_CARREGAMENTO — chassi volta ao estado anterior (DISPONIVEL)."""
    pedido, loja, _ = setup_pedido_loja
    car = criar_carregamento(pedido.id, loja.id, operador_id=1)
    db.session.flush()
    escanear_carregamento_item(car.id, 'TESTC001', operador_id=1)
    db.session.commit()

    cancelar_carregamento(car.id, motivo='Teste cancel', operador_id=2)
    db.session.commit()

    car_ref = AssaiCarregamento.query.get(car.id)
    assert car_ref.status == CARREGAMENTO_STATUS_CANCELADO
    assert car_ref.motivo_cancelamento == 'Teste cancel'
    assert car_ref.cancelado_por_id == 2
    assert car_ref.cancelado_em is not None

    # Chassi volta DISPONIVEL (era DISPONIVEL antes do escaneio — A1 sem evento)
    from app.motos_assai.services.moto_evento_service import status_efetivo
    assert status_efetivo('TESTC001') == EVENTO_DISPONIVEL


def test_cancelar_carregamento_finalizado_chassis_mantem_separada(setup_pedido_loja, chassi_disponivel):
    """S5=b: Cancelar Carregamento FINALIZADO — chassis MANTEM SEPARADA (nao desfaz adicoes)."""
    pedido, loja, modelo = setup_pedido_loja
    car = criar_carregamento(pedido.id, loja.id, operador_id=1)
    db.session.flush()
    escanear_carregamento_item(car.id, 'TESTC001', operador_id=1)
    db.session.commit()

    # Simular finalizacao manual (sem rodar finalize completo): emitir SEPARADA + CARREGADA
    sep = AssaiSeparacao(
        pedido_id=pedido.id, loja_id=loja.id,
        status=SEPARACAO_STATUS_CARREGADA,
        iniciada_em=agora_brasil_naive(), fechada_em=agora_brasil_naive(),
        fechada_por_id=1,
    )
    db.session.add(sep)
    db.session.flush()
    db.session.add(AssaiSeparacaoItem(
        separacao_id=sep.id, chassi='TESTC001', modelo_id=modelo.id,
        valor_unitario_qpa=1000.0,
    ))
    emitir_evento('TESTC001', EVENTO_SEPARADA, operador_id=1)
    emitir_evento('TESTC001', EVENTO_CARREGADA, operador_id=1)
    car.separacao_id = sep.id
    car.status = CARREGAMENTO_STATUS_FINALIZADO
    car.finalizado_em = agora_brasil_naive()
    db.session.commit()

    cancelar_carregamento(car.id, motivo='Erro de carregamento', operador_id=2)
    db.session.commit()

    car_ref = AssaiCarregamento.query.get(car.id)
    assert car_ref.status == CARREGAMENTO_STATUS_CANCELADO

    # Chassi DEVE manter SEPARADA (S5=b — nao desfaz adicoes na sep)
    from app.motos_assai.services.moto_evento_service import status_efetivo
    assert status_efetivo('TESTC001') == EVENTO_SEPARADA

    # Sep NAO foi cancelada (so o carregamento)
    sep_ref = AssaiSeparacao.query.get(sep.id)
    assert sep_ref.status == SEPARACAO_STATUS_CARREGADA  # mantem


def test_cancelar_carregamento_motivo_obrigatorio(setup_pedido_loja):
    pedido, loja, _ = setup_pedido_loja
    car = criar_carregamento(pedido.id, loja.id, operador_id=1)
    db.session.commit()

    with pytest.raises(CarregamentoValidationError, match='motivo'):
        cancelar_carregamento(car.id, motivo='', operador_id=1)


def test_cancelar_carregamento_ja_cancelado_idempotente(setup_pedido_loja):
    pedido, loja, _ = setup_pedido_loja
    car = criar_carregamento(pedido.id, loja.id, operador_id=1)
    db.session.commit()

    cancelar_carregamento(car.id, motivo='primeiro', operador_id=1)
    db.session.commit()

    # Segunda chamada deve ser no-op (idempotente) — nao raise
    with pytest.raises(CarregamentoStateError, match='ja CANCELADO'):
        cancelar_carregamento(car.id, motivo='segundo', operador_id=1)
```

- [ ] **Step 2: Rodar — devem falhar**

```bash
pytest tests/motos_assai/test_carregamento_service_crud.py -v -k 'cancelar_carregamento'
```

- [ ] **Step 3: Implementar**

```python
def cancelar_carregamento(carregamento_id, motivo, operador_id):
    """Cancela carregamento. Comportamento DEPENDE do status (S5).

    - EM_CARREGAMENTO: items deletam (cascata FK), chassis voltam ao estado anterior
      (sem mudanca de evento — A1).
    - FINALIZADO: chassis mantem SEPARADA na sep alvo (S5=b — nao desfaz adicoes).
      Apenas marca carregamento como CANCELADO. Sep pode ser cancelada separadamente.

    Args:
        carregamento_id: ID do carregamento
        motivo: justificativa (obrigatorio, min 3 chars)
        operador_id: usuario que cancelou

    Raises:
        CarregamentoValidationError: carregamento nao existe ou motivo vazio
        CarregamentoStateError: ja CANCELADO
    """
    if not motivo or len(motivo.strip()) < 3:
        raise CarregamentoValidationError('Motivo obrigatorio (min 3 chars)')

    car = AssaiCarregamento.query.get(carregamento_id)
    if not car:
        raise CarregamentoValidationError(f'Carregamento {carregamento_id} nao encontrado')
    if car.status == CARREGAMENTO_STATUS_CANCELADO:
        raise CarregamentoStateError(f'Carregamento {carregamento_id} ja CANCELADO')

    # S5: comportamento depende do status atual
    if car.status == CARREGAMENTO_STATUS_EM_CARREGAMENTO:
        # Cascata FK ON DELETE CASCADE remove items automaticamente.
        # A1: nenhum evento foi emitido durante escaneio, entao nao ha o que reverter.
        AssaiCarregamentoItem.query.filter_by(carregamento_id=car.id).delete()
    elif car.status == CARREGAMENTO_STATUS_FINALIZADO:
        # S5=b: chassis MANTEM SEPARADA na sep alvo. Nao desfaz adicoes.
        # Sep nao e tocada (pode ser cancelada separadamente via cancelar_separacao).
        pass

    car.status = CARREGAMENTO_STATUS_CANCELADO
    car.cancelado_em = agora_brasil_naive()
    car.cancelado_por_id = operador_id
    car.motivo_cancelamento = motivo
    db.session.flush()
```

- [ ] **Step 4: Rodar — devem passar**

```bash
pytest tests/motos_assai/test_carregamento_service_crud.py -v -k 'cancelar_carregamento'
```

- [ ] **Step 5: Commit**

```bash
git add app/motos_assai/services/carregamento_service.py tests/motos_assai/test_carregamento_service_crud.py
git commit -m "feat(motos-assai): cancelar_carregamento (S5 distincao EM_CARREGAMENTO vs FINALIZADO)"
```

---

### Task 5: `finalizar_carregamento` Fase 1 — identificar/criar sep alvo

**Files:**
- Modify: `app/motos_assai/services/carregamento_service.py`
- Create: `tests/motos_assai/test_carregamento_finalizar_fase1.py`

- [ ] **Step 1: Escrever testes**

```python
"""Testes finalizar_carregamento Fase 1 (identificar/criar sep alvo).

Spec: §6 Fase 1
Plano: Task 5
"""
import pytest
from app import create_app, db
from app.motos_assai.models import (
    AssaiCd, AssaiLoja, AssaiModelo, AssaiPedidoVenda, AssaiPedidoVendaLoja,
    AssaiPedidoVendaItem, AssaiSeparacao, AssaiSeparacaoItem, AssaiMoto,
    AssaiCarregamento, AssaiCarregamentoItem,
    SEPARACAO_STATUS_EM_SEPARACAO, SEPARACAO_STATUS_FECHADA,
    SEPARACAO_STATUS_CARREGADA, SEPARACAO_STATUS_FATURADA,
    CARREGAMENTO_STATUS_EM_CARREGAMENTO, CARREGAMENTO_STATUS_FINALIZADO,
    PEDIDO_STATUS_ABERTO,
    EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_DISPONIVEL,
)
from app.motos_assai.services.moto_evento_service import emitir_evento
from app.motos_assai.services.carregamento_service import (
    criar_carregamento, escanear_carregamento_item, finalizar_carregamento,
)


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.rollback()
        db.drop_all()


@pytest.fixture
def setup_completo(app):
    cd = AssaiCd(nome='CD', cnpj='12345678000100')
    loja = AssaiLoja(numero=999, cnpj='98765432000100', nome='Loja')
    modelo = AssaiModelo(codigo='SOL')
    db.session.add_all([cd, loja, modelo])
    db.session.flush()
    pedido = AssaiPedidoVenda(numero='TEST001', cd_id=cd.id, status=PEDIDO_STATUS_ABERTO)
    db.session.add(pedido)
    db.session.flush()
    pvl = AssaiPedidoVendaLoja(pedido_id=pedido.id, loja_id=loja.id)
    db.session.add(pvl)
    db.session.flush()
    db.session.add(AssaiPedidoVendaItem(
        pedido_id=pedido.id, pedido_loja_id=pvl.id, loja_id=loja.id, modelo_id=modelo.id,
        qtd_pedida=20, valor_unitario=1000.0,
    ))
    db.session.commit()
    return pedido, loja, modelo


def _criar_chassi(modelo, chassi):
    moto = AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='Preto')
    db.session.add(moto)
    db.session.flush()
    emitir_evento(chassi, EVENTO_ESTOQUE, operador_id=1)
    emitir_evento(chassi, EVENTO_MONTADA, operador_id=1)
    emitir_evento(chassi, EVENTO_DISPONIVEL, operador_id=1)
    return moto


def test_fase1_sem_sep_cria_sep_carregada_automatica(setup_completo):
    """Q4/Q6: sem sep previa, finalizar Carregamento cria sep em CARREGADA."""
    pedido, loja, modelo = setup_completo
    _criar_chassi(modelo, 'CHASSI001')
    db.session.commit()

    car = criar_carregamento(pedido.id, loja.id, operador_id=1)
    db.session.flush()
    escanear_carregamento_item(car.id, 'CHASSI001', operador_id=1)
    db.session.commit()

    sep_alvo = finalizar_carregamento(car.id, operador_id=1)
    db.session.commit()

    assert sep_alvo.status == SEPARACAO_STATUS_CARREGADA
    assert sep_alvo.pedido_id == pedido.id
    assert sep_alvo.loja_id == loja.id
    # A9: fechada_em + fechada_por_id usam operador do carregamento
    assert sep_alvo.fechada_em is not None
    assert sep_alvo.fechada_por_id == 1


def test_fase1_uma_sep_em_separacao_e_alvo(setup_completo):
    """Sep EM_SEPARACAO eh alvo (apenas 1 candidata)."""
    pedido, loja, modelo = setup_completo
    _criar_chassi(modelo, 'CHASSI001')
    sep_existente = AssaiSeparacao(
        pedido_id=pedido.id, loja_id=loja.id,
        status=SEPARACAO_STATUS_EM_SEPARACAO,
    )
    db.session.add(sep_existente)
    db.session.commit()

    car = criar_carregamento(pedido.id, loja.id, operador_id=1)
    db.session.flush()
    escanear_carregamento_item(car.id, 'CHASSI001', operador_id=1)
    db.session.commit()

    sep_alvo = finalizar_carregamento(car.id, operador_id=1)
    db.session.commit()

    assert sep_alvo.id == sep_existente.id
    assert sep_alvo.status == SEPARACAO_STATUS_CARREGADA  # transicionou


def test_fase1_n_seps_escolhe_mais_chassis_em_comum(setup_completo):
    """Q5: match por chassis em comum (Sep_A tem 5 dos chassis do car, Sep_B tem 1)."""
    pedido, loja, modelo = setup_completo

    # Carregamento: 6 chassis [C1..C6]
    for i in range(1, 7):
        _criar_chassi(modelo, f'C{i:03d}')

    # Sep_A: tem [C1..C5] (5 em comum)
    sep_a = AssaiSeparacao(pedido_id=pedido.id, loja_id=loja.id, status=SEPARACAO_STATUS_FECHADA)
    db.session.add(sep_a)
    db.session.flush()
    for i in range(1, 6):
        db.session.add(AssaiSeparacaoItem(
            separacao_id=sep_a.id, chassi=f'C{i:03d}', modelo_id=modelo.id, valor_unitario_qpa=1000.0,
        ))

    # Sep_B: tem so [C6] (1 em comum) + [X1, X2, X3]
    sep_b = AssaiSeparacao(pedido_id=pedido.id, loja_id=loja.id, status=SEPARACAO_STATUS_FECHADA)
    db.session.add(sep_b)
    db.session.flush()
    db.session.add(AssaiSeparacaoItem(
        separacao_id=sep_b.id, chassi='C006', modelo_id=modelo.id, valor_unitario_qpa=1000.0,
    ))
    db.session.commit()

    car = criar_carregamento(pedido.id, loja.id, operador_id=1)
    db.session.flush()
    for i in range(1, 7):
        escanear_carregamento_item(car.id, f'C{i:03d}', operador_id=1)
    db.session.commit()

    sep_alvo = finalizar_carregamento(car.id, operador_id=1)
    db.session.commit()

    assert sep_alvo.id == sep_a.id  # Sep_A tem mais chassis em comum (5 vs 1)


def test_fase1_sep_carregada_NAO_eh_alvo(setup_completo):
    """S18=b/A2: sep em CARREGADA NAO entra no match (ja tem carregamento — 1:1)."""
    pedido, loja, modelo = setup_completo
    _criar_chassi(modelo, 'C001')

    sep_carregada = AssaiSeparacao(pedido_id=pedido.id, loja_id=loja.id, status=SEPARACAO_STATUS_CARREGADA)
    db.session.add(sep_carregada)
    db.session.flush()
    db.session.add(AssaiSeparacaoItem(
        separacao_id=sep_carregada.id, chassi='C001', modelo_id=modelo.id, valor_unitario_qpa=1000.0,
    ))
    db.session.commit()

    car = criar_carregamento(pedido.id, loja.id, operador_id=1)
    db.session.flush()
    escanear_carregamento_item(car.id, 'C001', operador_id=1)
    db.session.commit()

    sep_alvo = finalizar_carregamento(car.id, operador_id=1)
    db.session.commit()

    # Sep nova foi criada (CARREGADA existente foi ignorada)
    assert sep_alvo.id != sep_carregada.id
    assert sep_alvo.status == SEPARACAO_STATUS_CARREGADA
```

- [ ] **Step 2: Rodar — devem falhar**

```bash
pytest tests/motos_assai/test_carregamento_finalizar_fase1.py -v
```

- [ ] **Step 3: Implementar Fase 1 do `finalizar_carregamento`**

Adicionar em `carregamento_service.py`:

```python
def _calcular_count_em_comum(sep, chassis):
    """Helper: conta chassis em comum entre uma sep e lista de chassis."""
    chassis_sep = {it.chassi for it in sep.itens}
    return len(chassis_sep & set(chassis))


def finalizar_carregamento(carregamento_id, operador_id):
    """Finaliza Carregamento — algoritmo §6 (8 fases).

    Tasks 5-12 implementam fases 1-8 incrementalmente.
    Esta versao (Task 5) implementa apenas Fase 1.

    Args:
        carregamento_id: ID do carregamento (deve estar EM_CARREGAMENTO)
        operador_id: usuario que finalizou

    Returns:
        AssaiSeparacao alvo (criada ou ajustada).

    Raises:
        CarregamentoValidationError: carregamento nao existe
        CarregamentoStateError: carregamento nao esta EM_CARREGAMENTO
        CarregamentoExcedenteError: Fase 3 — excederia pedido (Task 7)
    """
    car = AssaiCarregamento.query.get(carregamento_id)
    if not car:
        raise CarregamentoValidationError(f'Carregamento {carregamento_id} nao encontrado')
    if car.status != CARREGAMENTO_STATUS_EM_CARREGAMENTO:
        raise CarregamentoStateError(
            f'Carregamento {carregamento_id} esta {car.status} (esperado EM_CARREGAMENTO)'
        )

    chassis_car = [item.chassi for item in car.itens]
    if not chassis_car:
        raise CarregamentoValidationError(
            f'Carregamento {carregamento_id} esta vazio — nao pode ser finalizado'
        )

    # === FASE 1: identificar ou criar Sep alvo ===
    # S18=b/A2: Sep CARREGADA/FATURADA NAO entra no match (1:1).
    seps_ativas = (AssaiSeparacao.query
                   .filter_by(pedido_id=car.pedido_id, loja_id=car.loja_id)
                   .filter(AssaiSeparacao.status.in_([
                       SEPARACAO_STATUS_EM_SEPARACAO,
                       SEPARACAO_STATUS_FECHADA,
                   ]))
                   .all())

    if not seps_ativas:
        # Q4/Q6: criar Sep automaticamente em CARREGADA
        # A9: fechada_em + fechada_por_id usam operador_id
        sep_alvo = AssaiSeparacao(
            pedido_id=car.pedido_id, loja_id=car.loja_id,
            status=SEPARACAO_STATUS_CARREGADA,  # pula EM_SEPARACAO + FECHADA
            iniciada_em=agora_brasil_naive(),
            fechada_em=agora_brasil_naive(),
            fechada_por_id=operador_id,  # A9
        )
        db.session.add(sep_alvo)
        db.session.flush()
    else:
        # Q5: match por chassis em comum (mais matches = sep alvo)
        sep_alvo = max(seps_ativas, key=lambda s: _calcular_count_em_comum(s, chassis_car))
        # NOTA: status final atribuido na Fase 4

    # === FASES 2-8: implementadas em Tasks 6-12 ===
    # Por ora, marcar sep como CARREGADA + finalizar carregamento (esqueleto)
    sep_alvo.status = SEPARACAO_STATUS_CARREGADA
    car.separacao_id = sep_alvo.id
    car.status = CARREGAMENTO_STATUS_FINALIZADO
    car.finalizado_em = agora_brasil_naive()
    car.finalizado_por_id = operador_id
    db.session.flush()

    return sep_alvo
```

NOTA: este código é esqueleto da Fase 1. Tasks 6-12 vão expandir com fases 2-8.

- [ ] **Step 4: Rodar testes Fase 1 — devem passar**

```bash
pytest tests/motos_assai/test_carregamento_finalizar_fase1.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add app/motos_assai/services/carregamento_service.py tests/motos_assai/test_carregamento_finalizar_fase1.py
git commit -m "feat(motos-assai): finalizar_carregamento Fase 1 (identificar/criar sep alvo) + 4 testes

S18=b/A2: sep CARREGADA/FATURADA nao entra no match.
Q4/Q6: sem sep previa, cria automaticamente em CARREGADA.
Q5: match por chassis em comum quando ha N seps."
```

---

### Task 6: `finalizar_carregamento` Fase 2 — sobrescrever sep alvo (S2 realocação)

**Files:**
- Modify: `app/motos_assai/services/carregamento_service.py`
- Create: `tests/motos_assai/test_carregamento_finalizar_fase2.py`

- [ ] **Step 1: Escrever testes Fase 2**

```python
"""Testes finalizar_carregamento Fase 2 (sobrescrever sep alvo + S2 realocacao)."""
import pytest
from app import create_app, db
from app.motos_assai.models import *
from app.motos_assai.services.moto_evento_service import emitir_evento, status_efetivo
from app.motos_assai.services.carregamento_service import (
    criar_carregamento, escanear_carregamento_item, finalizar_carregamento,
)


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.rollback()
        db.drop_all()


@pytest.fixture
def setup(app):
    cd = AssaiCd(nome='CD', cnpj='12345678000100')
    loja = AssaiLoja(numero=999, cnpj='98765432000100', nome='Loja')
    modelo = AssaiModelo(codigo='SOL')
    db.session.add_all([cd, loja, modelo])
    db.session.flush()
    pedido = AssaiPedidoVenda(numero='T001', cd_id=cd.id, status=PEDIDO_STATUS_ABERTO)
    db.session.add(pedido)
    db.session.flush()
    pvl = AssaiPedidoVendaLoja(pedido_id=pedido.id, loja_id=loja.id)
    db.session.add(pvl)
    db.session.flush()
    db.session.add(AssaiPedidoVendaItem(
        pedido_id=pedido.id, pedido_loja_id=pvl.id, loja_id=loja.id, modelo_id=modelo.id,
        qtd_pedida=30, valor_unitario=1000.0,  # qtd alta evita disparar Fase 3
    ))
    db.session.commit()
    return pedido, loja, modelo


def _chassi(modelo, chassi):
    m = AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='Preto')
    db.session.add(m)
    db.session.flush()
    for ev in [EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_DISPONIVEL]:
        emitir_evento(chassi, ev, operador_id=1)
    return m


def test_fase2_chassis_adicionados_emitem_separada(setup):
    """Chassis no Carregamento mas nao na sep alvo recebem evento SEPARADA."""
    pedido, loja, modelo = setup
    _chassi(modelo, 'NEW001')
    db.session.commit()

    car = criar_carregamento(pedido.id, loja.id, operador_id=1)
    db.session.flush()
    escanear_carregamento_item(car.id, 'NEW001', operador_id=1)
    db.session.commit()

    sep_alvo = finalizar_carregamento(car.id, operador_id=1)
    db.session.commit()

    # Item criado na sep
    item = AssaiSeparacaoItem.query.filter_by(separacao_id=sep_alvo.id, chassi='NEW001').first()
    assert item is not None

    # NEW001 estava DISPONIVEL → SEPARADA → CARREGADA (Fase 4 emite CARREGADA)
    # Apos Fase 2 + Fase 4: status efetivo = CARREGADA
    assert status_efetivo('NEW001') == EVENTO_CARREGADA


def test_fase2_chassis_removidos_voltam_disponivel(setup):
    """Chassis na sep mas nao no Carregamento — vao DISPONIVEL (R1.1) ou realocam (S2)."""
    pedido, loja, modelo = setup
    _chassi(modelo, 'OLD001')
    _chassi(modelo, 'OLD002')
    _chassi(modelo, 'NEW001')

    sep_existente = AssaiSeparacao(
        pedido_id=pedido.id, loja_id=loja.id, status=SEPARACAO_STATUS_FECHADA,
    )
    db.session.add(sep_existente)
    db.session.flush()
    for c in ['OLD001', 'OLD002']:
        db.session.add(AssaiSeparacaoItem(
            separacao_id=sep_existente.id, chassi=c, modelo_id=modelo.id, valor_unitario_qpa=1000.0,
        ))
        emitir_evento(c, EVENTO_SEPARADA, operador_id=1)
    db.session.commit()

    # Carregamento substitui OLD001/OLD002 por NEW001
    car = criar_carregamento(pedido.id, loja.id, operador_id=1)
    db.session.flush()
    escanear_carregamento_item(car.id, 'NEW001', operador_id=1)
    db.session.commit()

    sep_alvo = finalizar_carregamento(car.id, operador_id=1)
    db.session.commit()

    # OLD001 e OLD002 expulsos (nao ha outra sep ativa para realocar)
    assert status_efetivo('OLD001') == EVENTO_DISPONIVEL  # R1.1 fallback
    assert status_efetivo('OLD002') == EVENTO_DISPONIVEL
    assert status_efetivo('NEW001') == EVENTO_CARREGADA

    # Sep alvo agora so tem NEW001
    items = AssaiSeparacaoItem.query.filter_by(separacao_id=sep_alvo.id).all()
    chassis_sep = {it.chassi for it in items}
    assert chassis_sep == {'NEW001'}


def test_fase2_chassis_expulsos_realocam_em_outra_sep_com_saldo(setup):
    """S2=b: chassis expulsos da sep alvo realocam em outra sep com saldo (qtd_planejada disponivel)."""
    pedido, loja, modelo = setup
    _chassi(modelo, 'OLD001')
    _chassi(modelo, 'NEW001')

    # Sep_A (alvo): tem OLD001, qtd_planejada=1
    sep_a = AssaiSeparacao(pedido_id=pedido.id, loja_id=loja.id, status=SEPARACAO_STATUS_EM_SEPARACAO)
    db.session.add(sep_a)
    db.session.flush()
    db.session.add(AssaiSeparacaoSaldoModelo(separacao_id=sep_a.id, modelo_id=modelo.id, qtd_planejada=1))
    db.session.add(AssaiSeparacaoItem(separacao_id=sep_a.id, chassi='OLD001', modelo_id=modelo.id, valor_unitario_qpa=1000.0))
    emitir_evento('OLD001', EVENTO_SEPARADA, operador_id=1)

    # Sep_B (outra sep com saldo): qtd_planejada=2 mas vazia (saldo livre = 2)
    sep_b = AssaiSeparacao(pedido_id=pedido.id, loja_id=loja.id, status=SEPARACAO_STATUS_EM_SEPARACAO)
    db.session.add(sep_b)
    db.session.flush()
    db.session.add(AssaiSeparacaoSaldoModelo(separacao_id=sep_b.id, modelo_id=modelo.id, qtd_planejada=2))
    db.session.commit()

    # Carregamento adiciona NEW001, expulsa OLD001 da Sep_A
    car = criar_carregamento(pedido.id, loja.id, operador_id=1)
    db.session.flush()
    escanear_carregamento_item(car.id, 'NEW001', operador_id=1)
    db.session.commit()

    finalizar_carregamento(car.id, operador_id=1)
    db.session.commit()

    # OLD001 deve ter sido REALOCADO em Sep_B (S2=b), nao DISPONIVEL
    assert status_efetivo('OLD001') == EVENTO_SEPARADA  # ainda separada (em Sep_B)
    item_realoc = AssaiSeparacaoItem.query.filter_by(separacao_id=sep_b.id, chassi='OLD001').first()
    assert item_realoc is not None
```

- [ ] **Step 2: Rodar — devem falhar (Fase 2 nao implementada)**

```bash
pytest tests/motos_assai/test_carregamento_finalizar_fase2.py -v
```

- [ ] **Step 3: Implementar Fase 2 — substituir esqueleto**

No `carregamento_service.py`, localizar o bloco `# === FASES 2-8: implementadas em Tasks 6-12 ===` e substituir por:

```python
    # === FASE 2: sobrescrever sep alvo (Q10) ===
    items_atuais = AssaiSeparacaoItem.query.filter_by(separacao_id=sep_alvo.id).all()
    chassis_atuais = {it.chassi for it in items_atuais}
    chassis_novos = set(chassis_car)

    # 2A — Chassis a remover (na sep mas nao no carregamento)
    chassis_remover = chassis_atuais - chassis_novos
    for chassi in chassis_remover:
        item = next(it for it in items_atuais if it.chassi == chassi)
        valor_unit_remover = item.valor_unitario_qpa
        db.session.delete(item)

        # S2=b: tentar realocar em outra sep com saldo
        moto = AssaiMoto.query.filter_by(chassi=chassi).first()
        outras_seps = (AssaiSeparacao.query
                       .filter(
                           AssaiSeparacao.pedido_id == car.pedido_id,
                           AssaiSeparacao.loja_id == car.loja_id,
                           AssaiSeparacao.id != sep_alvo.id,
                           AssaiSeparacao.status.in_([SEPARACAO_STATUS_EM_SEPARACAO, SEPARACAO_STATUS_FECHADA]),
                       )
                       .all())

        sep_destino = None
        for sep_cand in outras_seps:
            saldo = _saldo_pendente_modelo(sep_cand.id, moto.modelo_id)
            if saldo > 0:
                sep_destino = sep_cand
                break

        if sep_destino:
            db.session.add(AssaiSeparacaoItem(
                separacao_id=sep_destino.id, chassi=chassi,
                modelo_id=moto.modelo_id,
                valor_unitario_qpa=valor_unit_remover,
            ))
            emitir_evento(chassi, EVENTO_SEPARADA, operador_id=operador_id,
                          observacao=f'realocado pelo Carregamento {car.id} (S2=b)')
        else:
            # R1.1 fallback: vai DISPONIVEL
            emitir_evento(chassi, EVENTO_DISPONIVEL, operador_id=operador_id,
                          observacao=f'expulso pelo Carregamento {car.id} (sem sep destino)')

    # 2B — Chassis a adicionar (no carregamento mas nao na sep)
    chassis_adicionar = chassis_novos - chassis_atuais
    for chassi in chassis_adicionar:
        moto = AssaiMoto.query.filter_by(chassi=chassi).first()
        # CR-6: emite SEPARADA agora; CARREGADA emitido na Fase 4 (loop unico).
        # Resultado: chassis adicionados pegam (SEPARADA, CARREGADA);
        # chassis que ja estavam na sep pegam apenas CARREGADA.
        db.session.add(AssaiSeparacaoItem(
            separacao_id=sep_alvo.id, chassi=chassi,
            modelo_id=moto.modelo_id,
            valor_unitario_qpa=_resolver_valor_unitario(car, modelo_id=moto.modelo_id),
        ))
        emitir_evento(chassi, EVENTO_SEPARADA, operador_id=operador_id,
                      observacao=f'adicionado pelo Carregamento {car.id}')
```

E adicionar helpers no topo do `carregamento_service.py`:

```python
# Imports adicionais necessarios (H2 fix — colocar com os outros imports do topo do arquivo)
from app.motos_assai.models import AssaiSeparacaoSaldoModelo, AssaiPedidoVendaItem
# (imports ja existentes da Task 1: AssaiCarregamento, AssaiSeparacao, etc — manter)


def _saldo_pendente_modelo(sep_id, modelo_id):
    """Helper: qtd_planejada - qtd_separada para um modelo na sep.

    Retorna 0 se nao ha saldo planejado para o modelo.
    """
    saldo_obj = (db.session.query(AssaiSeparacaoSaldoModelo)
                 .filter_by(separacao_id=sep_id, modelo_id=modelo_id)
                 .first())
    if not saldo_obj:
        return 0

    qtd_separada = (db.session.query(db.func.count(AssaiSeparacaoItem.id))
                    .filter_by(separacao_id=sep_id, modelo_id=modelo_id)
                    .scalar() or 0)
    return max(0, saldo_obj.qtd_planejada - qtd_separada)


def _resolver_valor_unitario(car, modelo_id):
    """Helper: pega valor_unitario do AssaiPedidoVendaItem para esse modelo no pedido."""
    item_pedido = (AssaiPedidoVendaItem.query
                   .filter_by(pedido_id=car.pedido_id, loja_id=car.loja_id, modelo_id=modelo_id)
                   .first())
    return float(item_pedido.valor_unitario) if item_pedido else 0.0
```

**H2 fix**: os imports `AssaiSeparacaoSaldoModelo`, `AssaiPedidoVendaItem` e `emitir_evento` ja estao no bloco de codigo Python acima — incluidos como parte integral do snippet. Adicionar no topo do arquivo `carregamento_service.py` junto com os imports da Task 1.

- [ ] **Step 4: Rodar testes Fase 2 — devem passar**

```bash
pytest tests/motos_assai/test_carregamento_finalizar_fase2.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add app/motos_assai/services/carregamento_service.py tests/motos_assai/test_carregamento_finalizar_fase2.py
git commit -m "feat(motos-assai): finalizar_carregamento Fase 2 (sobrescrever + S2 realocacao)"
```

---

### Task 7: `finalizar_carregamento` Fase 3 — limite pedido (CarregamentoExcedenteError)

**Files:**
- Modify: `app/motos_assai/services/carregamento_service.py`
- Create: `tests/motos_assai/test_carregamento_finalizar_fase3.py`

- [ ] **Step 1: Escrever testes**

```python
"""Testes finalizar_carregamento Fase 3 (limite pedido + LIFO + S14 escalar)."""
import pytest
from app import create_app, db
from app.motos_assai.models import *
from app.motos_assai.services.moto_evento_service import emitir_evento, status_efetivo
from app.motos_assai.services.carregamento_service import (
    criar_carregamento, escanear_carregamento_item, finalizar_carregamento,
    CarregamentoExcedenteError,
)


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.rollback()
        db.drop_all()


@pytest.fixture
def setup_pedido_3(app):
    """Pedido com qtd_pedida=3."""
    cd = AssaiCd(nome='CD', cnpj='12345678000100')
    loja = AssaiLoja(numero=999, cnpj='98765432000100', nome='Loja')
    modelo = AssaiModelo(codigo='SOL')
    db.session.add_all([cd, loja, modelo])
    db.session.flush()
    pedido = AssaiPedidoVenda(numero='T', cd_id=cd.id, status=PEDIDO_STATUS_ABERTO)
    db.session.add(pedido)
    db.session.flush()
    pvl = AssaiPedidoVendaLoja(pedido_id=pedido.id, loja_id=loja.id)
    db.session.add(pvl)
    db.session.flush()
    db.session.add(AssaiPedidoVendaItem(
        pedido_id=pedido.id, pedido_loja_id=pvl.id, loja_id=loja.id, modelo_id=modelo.id,
        qtd_pedida=3, valor_unitario=1000.0,
    ))
    db.session.commit()
    return pedido, loja, modelo


def _chassi(modelo, chassi):
    m = AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='Preto')
    db.session.add(m)
    db.session.flush()
    for ev in [EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_DISPONIVEL]:
        emitir_evento(chassi, ev, operador_id=1)
    return m


def test_fase3_excedente_remove_LIFO_outras_seps(setup_pedido_3):
    """R1.2: excedente remove os mais RECENTES das outras seps."""
    pedido, loja, modelo = setup_pedido_3
    for c in ['A001', 'A002', 'NEW1']:
        _chassi(modelo, c)

    # Sep_outra: tem A001 (mais antigo) + A002 (mais recente). Total=2
    sep_outra = AssaiSeparacao(pedido_id=pedido.id, loja_id=loja.id, status=SEPARACAO_STATUS_EM_SEPARACAO)
    db.session.add(sep_outra)
    db.session.flush()
    import time
    item_old = AssaiSeparacaoItem(
        separacao_id=sep_outra.id, chassi='A001', modelo_id=modelo.id, valor_unitario_qpa=1000.0,
    )
    db.session.add(item_old)
    db.session.flush()
    time.sleep(0.05)
    item_new = AssaiSeparacaoItem(
        separacao_id=sep_outra.id, chassi='A002', modelo_id=modelo.id, valor_unitario_qpa=1000.0,
    )
    db.session.add(item_new)
    emitir_evento('A001', EVENTO_SEPARADA, operador_id=1)
    emitir_evento('A002', EVENTO_SEPARADA, operador_id=1)
    db.session.commit()

    # Carregamento: 2 chassis novos (NEW1 + um chassi adicional). Total = 2+2 = 4 > pedido(3)
    _chassi(modelo, 'NEW2')
    car = criar_carregamento(pedido.id, loja.id, operador_id=1)
    db.session.flush()
    escanear_carregamento_item(car.id, 'NEW1', operador_id=1)
    escanear_carregamento_item(car.id, 'NEW2', operador_id=1)
    db.session.commit()

    finalizar_carregamento(car.id, operador_id=1)
    db.session.commit()

    # Excedente=1. LIFO remove o mais recente (A002). A001 permanece.
    items_outra = AssaiSeparacaoItem.query.filter_by(separacao_id=sep_outra.id).all()
    chassis = {it.chassi for it in items_outra}
    assert chassis == {'A001'}  # A002 removido (LIFO)
    assert status_efetivo('A002') == EVENTO_DISPONIVEL
    assert status_efetivo('A001') == EVENTO_SEPARADA


def test_fase3_escalar_quando_outras_seps_carregada_faturada(setup_pedido_3):
    """S14=a: se excedente nao cabe em (EM_SEPARACAO, FECHADA), escala via CarregamentoExcedenteError."""
    pedido, loja, modelo = setup_pedido_3
    for c in ['CARR001', 'CARR002', 'NEW1', 'NEW2']:
        _chassi(modelo, c)

    # Sep_carregada: tem CARR001 + CARR002. NAO pode tirar (S14=a).
    sep_carr = AssaiSeparacao(pedido_id=pedido.id, loja_id=loja.id, status=SEPARACAO_STATUS_CARREGADA)
    db.session.add(sep_carr)
    db.session.flush()
    for c in ['CARR001', 'CARR002']:
        db.session.add(AssaiSeparacaoItem(separacao_id=sep_carr.id, chassi=c, modelo_id=modelo.id, valor_unitario_qpa=1000.0))
        emitir_evento(c, EVENTO_SEPARADA, operador_id=1)
        emitir_evento(c, EVENTO_CARREGADA, operador_id=1)
    db.session.commit()

    # Carregamento: 2 chassis novos. Total = 2+2 = 4 > pedido(3). Excedente=1.
    car = criar_carregamento(pedido.id, loja.id, operador_id=1)
    db.session.flush()
    escanear_carregamento_item(car.id, 'NEW1', operador_id=1)
    escanear_carregamento_item(car.id, 'NEW2', operador_id=1)
    db.session.commit()

    with pytest.raises(CarregamentoExcedenteError) as exc:
        finalizar_carregamento(car.id, operador_id=1)

    assert exc.value.qtd_excedente == 1
    assert sep_carr.id in exc.value.seps_bloqueadas


def test_fase3_sem_excedente_no_op(setup_pedido_3):
    """Total <= pedido: Fase 3 nao remove nada."""
    pedido, loja, modelo = setup_pedido_3
    for c in ['NEW1', 'NEW2', 'NEW3']:
        _chassi(modelo, c)

    car = criar_carregamento(pedido.id, loja.id, operador_id=1)
    db.session.flush()
    for c in ['NEW1', 'NEW2', 'NEW3']:
        escanear_carregamento_item(car.id, c, operador_id=1)
    db.session.commit()

    sep_alvo = finalizar_carregamento(car.id, operador_id=1)
    db.session.commit()

    items = AssaiSeparacaoItem.query.filter_by(separacao_id=sep_alvo.id).all()
    assert len(items) == 3  # qtd_pedida=3, sem excedente
```

- [ ] **Step 2: Rodar — devem falhar**

```bash
pytest tests/motos_assai/test_carregamento_finalizar_fase3.py -v
```

- [ ] **Step 3: Implementar Fase 3**

No `finalizar_carregamento`, adicionar APÓS a Fase 2:

```python
    # === FASE 3: respeitar limite do pedido (R1.2 + S14=a) ===
    qtd_pedida_total = (db.session.query(db.func.coalesce(db.func.sum(AssaiPedidoVendaItem.qtd_pedida), 0))
                        .filter(AssaiPedidoVendaItem.pedido_id == car.pedido_id)
                        .scalar() or 0)

    qtd_separada_total = (db.session.query(db.func.count(AssaiSeparacaoItem.id))
                          .join(AssaiSeparacao, AssaiSeparacao.id == AssaiSeparacaoItem.separacao_id)
                          .filter(
                              AssaiSeparacao.pedido_id == car.pedido_id,
                              AssaiSeparacao.status != SEPARACAO_STATUS_CANCELADA,
                          )
                          .scalar() or 0)

    if qtd_separada_total > qtd_pedida_total:
        excedente = qtd_separada_total - qtd_pedida_total

        # S14=a: restringir a (EM_SEPARACAO, FECHADA). NAO mexer em CARREGADA/FATURADA.
        candidatos = (AssaiSeparacaoItem.query
                      .join(AssaiSeparacao)
                      .filter(
                          AssaiSeparacao.pedido_id == car.pedido_id,
                          AssaiSeparacao.loja_id == car.loja_id,
                          AssaiSeparacao.id != sep_alvo.id,
                          AssaiSeparacao.status.in_([SEPARACAO_STATUS_EM_SEPARACAO, SEPARACAO_STATUS_FECHADA]),
                      )
                      .order_by(AssaiSeparacaoItem.id.desc())  # LIFO (mais recentes primeiro)
                      .limit(excedente)
                      .all())

        if len(candidatos) < excedente:
            # Escalar: nao tem candidatos suficientes em (EM_SEPARACAO, FECHADA)
            seps_bloqueadas = [
                s.id for s in AssaiSeparacao.query.filter(
                    AssaiSeparacao.pedido_id == car.pedido_id,
                    AssaiSeparacao.loja_id == car.loja_id,
                    AssaiSeparacao.id != sep_alvo.id,
                    AssaiSeparacao.status.in_([SEPARACAO_STATUS_CARREGADA, SEPARACAO_STATUS_FATURADA]),
                ).all()
            ]
            # N-B5 fix: NAO chamar db.session.rollback() — caller (route) faz isso ao capturar a excecao.
            # Rollback aqui invalida transacao multi-fase, perdendo Fases 1-2.
            raise CarregamentoExcedenteError(
                f'Pedido excedido em {excedente} chassis mas apenas {len(candidatos)} '
                f'podem ser removidos automaticamente. Seps CARREGADA/FATURADA bloqueando: {seps_bloqueadas}',
                qtd_excedente=excedente,
                seps_bloqueadas=seps_bloqueadas,
            )

        for it in candidatos:
            chassi = it.chassi
            db.session.delete(it)
            emitir_evento(chassi, EVENTO_DISPONIVEL, operador_id=operador_id,
                          observacao=f'removido por excedente pedido (LIFO) — Carregamento {car.id}')
```

- [ ] **Step 4: Rodar testes Fase 3 — devem passar**

```bash
pytest tests/motos_assai/test_carregamento_finalizar_fase3.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add app/motos_assai/services/carregamento_service.py tests/motos_assai/test_carregamento_finalizar_fase3.py
git commit -m "feat(motos-assai): finalizar_carregamento Fase 3 (limite pedido + LIFO + S14 escalar)"
```

---

### Task 8: `finalizar_carregamento` Fase 4 — sep CARREGADA + emitir CARREGADA

**Files:**
- Modify: `app/motos_assai/services/carregamento_service.py`
- Create: `tests/motos_assai/test_carregamento_finalizar_fase4_5_6.py`

- [ ] **Step 1: Escrever testes**

```python
"""Testes finalizar_carregamento Fase 4 (sep CARREGADA + emitir CARREGADA)."""
import pytest
from app import create_app, db
from app.motos_assai.models import *
from app.motos_assai.services.moto_evento_service import emitir_evento, status_efetivo
from app.motos_assai.services.carregamento_service import (
    criar_carregamento, escanear_carregamento_item, finalizar_carregamento,
)


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.rollback()
        db.drop_all()


@pytest.fixture
def setup(app):
    cd = AssaiCd(nome='CD', cnpj='12345678000100')
    loja = AssaiLoja(numero=999, cnpj='98765432000100', nome='Loja')
    modelo = AssaiModelo(codigo='SOL')
    db.session.add_all([cd, loja, modelo])
    db.session.flush()
    pedido = AssaiPedidoVenda(numero='T', cd_id=cd.id, status=PEDIDO_STATUS_ABERTO)
    db.session.add(pedido)
    db.session.flush()
    pvl = AssaiPedidoVendaLoja(pedido_id=pedido.id, loja_id=loja.id)
    db.session.add(pvl)
    db.session.flush()
    db.session.add(AssaiPedidoVendaItem(
        pedido_id=pedido.id, pedido_loja_id=pvl.id, loja_id=loja.id, modelo_id=modelo.id,
        qtd_pedida=10, valor_unitario=1000.0,
    ))
    db.session.commit()
    return pedido, loja, modelo


def _chassi(modelo, chassi):
    m = AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='Preto')
    db.session.add(m)
    db.session.flush()
    for ev in [EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_DISPONIVEL]:
        emitir_evento(chassi, ev, operador_id=1)
    return m


def test_fase4_sep_alvo_status_carregada_apos_finalize(setup):
    pedido, loja, modelo = setup
    _chassi(modelo, 'C001')
    db.session.commit()

    car = criar_carregamento(pedido.id, loja.id, operador_id=1)
    db.session.flush()
    escanear_carregamento_item(car.id, 'C001', operador_id=1)
    db.session.commit()

    sep_alvo = finalizar_carregamento(car.id, operador_id=1)
    db.session.commit()

    assert sep_alvo.status == SEPARACAO_STATUS_CARREGADA


def test_fase4_carregamento_status_finalizado(setup):
    pedido, loja, modelo = setup
    _chassi(modelo, 'C001')
    db.session.commit()

    car = criar_carregamento(pedido.id, loja.id, operador_id=1)
    db.session.flush()
    escanear_carregamento_item(car.id, 'C001', operador_id=1)
    db.session.commit()

    finalizar_carregamento(car.id, operador_id=1)
    db.session.commit()

    car_ref = AssaiCarregamento.query.get(car.id)
    assert car_ref.status == CARREGAMENTO_STATUS_FINALIZADO
    assert car_ref.finalizado_em is not None
    assert car_ref.finalizado_por_id == 1
    assert car_ref.separacao_id is not None  # vinculo Sep ↔ Carregamento (Q2)


def test_fase4_emite_evento_carregada_para_todos_chassis(setup):
    """Fase 4 emite evento CARREGADA para TODOS chassis do carregamento."""
    pedido, loja, modelo = setup
    for c in ['C001', 'C002', 'C003']:
        _chassi(modelo, c)
    db.session.commit()

    car = criar_carregamento(pedido.id, loja.id, operador_id=1)
    db.session.flush()
    for c in ['C001', 'C002', 'C003']:
        escanear_carregamento_item(car.id, c, operador_id=1)
    db.session.commit()

    finalizar_carregamento(car.id, operador_id=1)
    db.session.commit()

    for c in ['C001', 'C002', 'C003']:
        assert status_efetivo(c) == EVENTO_CARREGADA
```

- [ ] **Step 2: Rodar — devem passar parcialmente** (Fase 1+2+3 ja implementadas; Fase 4 esta no esqueleto)

```bash
pytest tests/motos_assai/test_carregamento_finalizar_fase4_5_6.py -v -k 'fase4'
```

Esperado: alguns passam (sep_alvo CARREGADA já é setado no esqueleto), mas evento CARREGADA pode não estar emitido.

- [ ] **Step 3: Substituir bloco esqueleto por Fase 4 explicita**

Localizar no `carregamento_service.py` o bloco:
```python
    # === FASES 2-8: implementadas em Tasks 6-12 ===
    # Por ora, marcar sep como CARREGADA + finalizar carregamento (esqueleto)
    sep_alvo.status = SEPARACAO_STATUS_CARREGADA
    car.separacao_id = sep_alvo.id
    car.status = CARREGAMENTO_STATUS_FINALIZADO
    car.finalizado_em = agora_brasil_naive()
    car.finalizado_por_id = operador_id
    db.session.flush()

    return sep_alvo
```

Substituir por (já que Fase 2 e 3 foram inseridas antes deste ponto, agora vem Fase 4):

```python
    # === FASE 4: Sep alvo CARREGADA + emitir evento CARREGADA ===
    sep_alvo.status = SEPARACAO_STATUS_CARREGADA
    car.separacao_id = sep_alvo.id
    car.status = CARREGAMENTO_STATUS_FINALIZADO
    car.finalizado_em = agora_brasil_naive()
    car.finalizado_por_id = operador_id

    # Emite CARREGADA para TODOS chassis do carregamento (chassis adicionados na Fase 2
    # ja receberam SEPARADA antes — agora pegam CARREGADA. Chassis que ja estavam na sep
    # pegam apenas CARREGADA.)
    for chassi in chassis_car:
        emitir_evento(chassi, EVENTO_CARREGADA, operador_id=operador_id,
                      observacao=f'Carregamento {car.id} finalizado',
                      dados_extras={'carregamento_id': car.id, 'sep_id': sep_alvo.id})

    db.session.flush()

    # === FASES 5-8: implementadas em Tasks 9-12 ===
    return sep_alvo
```

- [ ] **Step 4: Rodar testes Fase 4 — devem passar**

```bash
pytest tests/motos_assai/test_carregamento_finalizar_fase4_5_6.py -v -k 'fase4'
```

Expected: 3 passed.

Rodar Fase 1, 2 e 3 também para garantir que não quebrou regressão:

```bash
pytest tests/motos_assai/test_carregamento_finalizar_fase1.py tests/motos_assai/test_carregamento_finalizar_fase2.py tests/motos_assai/test_carregamento_finalizar_fase3.py -v
```

- [ ] **Step 5: Commit**

```bash
git add app/motos_assai/services/carregamento_service.py tests/motos_assai/test_carregamento_finalizar_fase4_5_6.py
git commit -m "feat(motos-assai): finalizar_carregamento Fase 4 (sep CARREGADA + emit evento)"
```

---

### Task 9: `finalizar_carregamento` Fase 5 — regenerar Excel (S13 retry + CR-12 lock)

**Files:**
- Modify: `app/motos_assai/services/carregamento_service.py`
- Modify: `tests/motos_assai/test_carregamento_finalizar_fase4_5_6.py`

- [ ] **Step 1: Adicionar testes Fase 5**

```python
def test_fase5_excel_versao_1_quando_nao_havia_anterior(setup):
    pedido, loja, modelo = setup
    _chassi(modelo, 'C001')
    db.session.commit()

    car = criar_carregamento(pedido.id, loja.id, operador_id=1)
    db.session.flush()
    escanear_carregamento_item(car.id, 'C001', operador_id=1)
    db.session.commit()

    sep_alvo = finalizar_carregamento(car.id, operador_id=1)
    db.session.commit()

    excels = AssaiPedidoExcel.query.filter_by(separacao_id=sep_alvo.id).all()
    assert len(excels) == 1
    assert excels[0].versao == 1
    assert excels[0].ativo is True
    assert excels[0].pedido_id == pedido.id
    assert 'Carregamento finalizado' in excels[0].motivo_regeneracao
    assert excels[0].s3_key.startswith('motos_assai/solicitacoes/')


def test_fase5_excel_versao_n_plus_1_quando_havia_anterior(setup):
    pedido, loja, modelo = setup
    _chassi(modelo, 'C001')

    sep_existente = AssaiSeparacao(
        pedido_id=pedido.id, loja_id=loja.id, status=SEPARACAO_STATUS_FECHADA,
    )
    db.session.add(sep_existente)
    db.session.flush()
    db.session.add(AssaiPedidoExcel(
        pedido_id=pedido.id, separacao_id=sep_existente.id,
        s3_key='legado.xlsx', versao=1, ativo=True,
    ))
    db.session.commit()

    car = criar_carregamento(pedido.id, loja.id, operador_id=1)
    db.session.flush()
    escanear_carregamento_item(car.id, 'C001', operador_id=1)
    db.session.commit()

    sep_alvo = finalizar_carregamento(car.id, operador_id=1)
    db.session.commit()

    assert sep_alvo.id == sep_existente.id  # mesma sep
    excels = AssaiPedidoExcel.query.filter_by(separacao_id=sep_alvo.id).order_by(AssaiPedidoExcel.versao).all()
    assert len(excels) == 2
    assert excels[0].versao == 1 and excels[0].ativo is False  # antigo desativado
    assert excels[1].versao == 2 and excels[1].ativo is True   # novo ativo
```

- [ ] **Step 2: Rodar — devem falhar**

```bash
pytest tests/motos_assai/test_carregamento_finalizar_fase4_5_6.py -v -k 'fase5'
```

- [ ] **Step 3: Implementar Fase 5**

Adicionar imports no topo:

```python
from sqlalchemy.exc import IntegrityError
from app.motos_assai.models import AssaiPedidoExcel
from app.motos_assai.services.faturamento_service import gerar_excel_qpa
```

E inserir Fase 5 entre Fase 4 e o `return`:

```python
    # === FASE 5: regenerar Excel Q.P.A. (D-C + S13=a + CR-9/CR-12 race fix) ===
    # CR-12: lock pessimista na sep para serializar regeneracoes concorrentes.
    AssaiSeparacao.query.filter_by(id=sep_alvo.id).with_for_update().first()

    excel_anterior = AssaiPedidoExcel.query.filter_by(
        separacao_id=sep_alvo.id, ativo=True,
    ).first()
    if excel_anterior:
        excel_anterior.ativo = False  # mantem historico

    nova_versao = (excel_anterior.versao + 1) if excel_anterior else 1

    # gerar_excel_qpa retorna (bytes, s3_key) — service existente em faturamento_service
    bytes_xlsx, s3_key = gerar_excel_qpa(sep_alvo.id, operador_id)

    # CR-9 + N-B6 fix: retry defensivo via SAVEPOINT (begin_nested) em vez de rollback completo.
    # Rollback completo desfaz Fases 1-4 inteiras. Savepoint isola apenas o INSERT do Excel.
    try:
        with db.session.begin_nested():
            db.session.add(AssaiPedidoExcel(
                pedido_id=car.pedido_id, separacao_id=sep_alvo.id,
                s3_key=s3_key, versao=nova_versao, ativo=True,
                motivo_regeneracao=f'Carregamento {car.id} finalizado',
                gerado_por_id=operador_id,
            ))
    except IntegrityError:
        # Savepoint reverteu o INSERT. Recalcula MAX e tenta de novo.
        max_versao = (db.session.query(db.func.coalesce(db.func.max(AssaiPedidoExcel.versao), 0))
                      .filter_by(separacao_id=sep_alvo.id)
                      .scalar() or 0)
        nova_versao = max_versao + 1
        db.session.add(AssaiPedidoExcel(
            pedido_id=car.pedido_id, separacao_id=sep_alvo.id,
            s3_key=s3_key, versao=nova_versao, ativo=True,
            motivo_regeneracao=f'Carregamento {car.id} finalizado (retry)',
            gerado_por_id=operador_id,
        ))
        db.session.flush()
```

NOTA: `gerar_excel_qpa` é serviço existente em `faturamento_service.py` (Fase 4 do Plano original — já implementado). Confirmar que assinatura é `(sep_id, operador_id) -> (bytes, s3_key)`.

- [ ] **Step 4: Rodar — devem passar**

```bash
pytest tests/motos_assai/test_carregamento_finalizar_fase4_5_6.py -v -k 'fase5'
```

- [ ] **Step 5: Commit**

```bash
git add app/motos_assai/services/carregamento_service.py tests/motos_assai/test_carregamento_finalizar_fase4_5_6.py
git commit -m "feat(motos-assai): finalizar_carregamento Fase 5 (regenerar Excel + S13 retry)"
```

---

### Task 10: `finalizar_carregamento` Fase 6 — sincronizar mirror Nacom

**Files:**
- Modify: `app/motos_assai/services/carregamento_service.py`
- Modify: `tests/motos_assai/test_carregamento_finalizar_fase4_5_6.py`

- [ ] **Step 1: Adicionar testes Fase 6**

```python
def test_fase6_mirror_nacom_atualizado(setup):
    pedido, loja, modelo = setup
    _chassi(modelo, 'C001')
    db.session.commit()

    car = criar_carregamento(pedido.id, loja.id, operador_id=1)
    db.session.flush()
    escanear_carregamento_item(car.id, 'C001', operador_id=1)
    db.session.commit()

    sep_alvo = finalizar_carregamento(car.id, operador_id=1)
    db.session.commit()

    # Linha em separacao Nacom espelhada
    from app.separacao.models import Separacao
    linhas = Separacao.query.filter_by(separacao_lote_id=f'ASSAI-SEP-{sep_alvo.id}').all()
    assert len(linhas) == 1
    assert linhas[0].chassi_assai == 'C001'
```

- [ ] **Step 2: Rodar — deve falhar**

```bash
pytest tests/motos_assai/test_carregamento_finalizar_fase4_5_6.py -v -k 'fase6'
```

- [ ] **Step 3: Implementar Fase 6**

Adicionar import:
```python
from app.motos_assai.services.separacao_mirror_service import sincronizar_espelho_com_separacao
```

Inserir Fase 6 antes do `return`:

```python
    # === FASE 6: atualizar mirror Nacom (D-B + S12=a) ===
    # S12=a: mirror agora aceita FECHADA + CARREGADA + FATURADA na guarda
    # (atualizado em Task 15).
    sincronizar_espelho_com_separacao(sep_alvo.id)
```

NOTA: `sincronizar_espelho_com_separacao` é service existente em `separacao_mirror_service.py`. Task 15 (atualização do mirror para aceitar CARREGADA) é pré-requisito.

- [ ] **Step 4: Rodar — deve passar (DEPOIS de Task 15)**

Por enquanto pode falhar se mirror ainda não aceita CARREGADA. Marcar como pendente e rodar depois da Task 15.

```bash
pytest tests/motos_assai/test_carregamento_finalizar_fase4_5_6.py -v -k 'fase6'
```

- [ ] **Step 5: Commit**

```bash
git add app/motos_assai/services/carregamento_service.py tests/motos_assai/test_carregamento_finalizar_fase4_5_6.py
git commit -m "feat(motos-assai): finalizar_carregamento Fase 6 (sincronizar mirror Nacom)"
```

---

### Task 11: `finalizar_carregamento` Fase 7 — divergência se NF BATEU (A4 BATEU→DIVERGENTE + A3)

**Files:**
- Modify: `app/motos_assai/services/carregamento_service.py`
- Create: `tests/motos_assai/test_carregamento_finalizar_fase7_8.py`

- [ ] **Step 1: Escrever testes**

```python
"""Testes finalizar_carregamento Fases 7-8 (divergencia NF + recalcular pedido)."""
import pytest
from app import create_app, db
from app.motos_assai.models import *
from app.motos_assai.services.moto_evento_service import emitir_evento
from app.motos_assai.services.carregamento_service import (
    criar_carregamento, escanear_carregamento_item, finalizar_carregamento,
)


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.rollback()
        db.drop_all()


@pytest.fixture
def setup(app):
    cd = AssaiCd(nome='CD', cnpj='12345678000100')
    loja = AssaiLoja(numero=999, cnpj='98765432000100', nome='Loja')
    modelo = AssaiModelo(codigo='SOL')
    db.session.add_all([cd, loja, modelo])
    db.session.flush()
    pedido = AssaiPedidoVenda(numero='T', cd_id=cd.id, status=PEDIDO_STATUS_ABERTO)
    db.session.add(pedido)
    db.session.flush()
    pvl = AssaiPedidoVendaLoja(pedido_id=pedido.id, loja_id=loja.id)
    db.session.add(pvl)
    db.session.flush()
    db.session.add(AssaiPedidoVendaItem(
        pedido_id=pedido.id, pedido_loja_id=pvl.id, loja_id=loja.id, modelo_id=modelo.id,
        qtd_pedida=10, valor_unitario=1000.0,
    ))
    db.session.commit()
    return pedido, loja, modelo


def _chassi(modelo, chassi):
    m = AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='Preto')
    db.session.add(m)
    db.session.flush()
    for ev in [EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_DISPONIVEL]:
        emitir_evento(chassi, ev, operador_id=1)
    return m


def test_fase7_nf_bateu_chassi_fora_carregamento_cria_divergencia(setup):
    """A4: NF BATEU + Carregamento difere → cria divergencia + NF vai para DIVERGENTE."""
    pedido, loja, modelo = setup
    _chassi(modelo, 'C001')
    _chassi(modelo, 'C002')  # estava na NF, mas nao no carregamento

    sep = AssaiSeparacao(pedido_id=pedido.id, loja_id=loja.id, status=SEPARACAO_STATUS_FECHADA)
    db.session.add(sep)
    db.session.flush()
    for c in ['C001', 'C002']:
        db.session.add(AssaiSeparacaoItem(
            separacao_id=sep.id, chassi=c, modelo_id=modelo.id, valor_unitario_qpa=1000.0,
        ))

    nf = AssaiNfQpa(
        chave_44='1' * 44, numero='12345', loja_id=loja.id,
        separacao_id=sep.id, status_match=NF_STATUS_BATEU,
    )
    db.session.add(nf)
    db.session.flush()
    for c in ['C001', 'C002']:
        db.session.add(AssaiNfQpaItem(nf_id=nf.id, chassi=c, modelo_extraido='SOL', valor_extraido=1000.0))
    db.session.commit()

    # Carregamento real: tem C001 + C003 (NEW). C002 NAO foi carregado, C003 NAO esta na NF.
    _chassi(modelo, 'C003')
    car = criar_carregamento(pedido.id, loja.id, operador_id=1)
    db.session.flush()
    escanear_carregamento_item(car.id, 'C001', operador_id=1)
    escanear_carregamento_item(car.id, 'C003', operador_id=1)
    db.session.commit()

    finalizar_carregamento(car.id, operador_id=1)
    db.session.commit()

    # Divergencia para C003 (Carregamento tem mas NF nao)
    div_car = AssaiDivergencia.query.filter_by(
        chassi='C003', tipo=DIVERGENCIA_TIPO_CARREGAMENTO_CHASSI_FORA_NF,
    ).first()
    assert div_car is not None
    assert div_car.nf_id == nf.id

    # Divergencia para C002 (NF tem mas Carregamento nao)
    div_nf = AssaiDivergencia.query.filter_by(
        chassi='C002', tipo=DIVERGENCIA_TIPO_NF_CHASSI_FORA_CARREGAMENTO,
    ).first()
    assert div_nf is not None

    # A4: NF muda de BATEU para DIVERGENTE
    nf_ref = AssaiNfQpa.query.get(nf.id)
    assert nf_ref.status_match == NF_STATUS_DIVERGENTE


def test_fase7_nf_nao_bateu_ignora(setup):
    """S22=a: Carregamento ignora NFs DIVERGENTE/NAO_RECONCILIADO/CANCELADA."""
    pedido, loja, modelo = setup
    _chassi(modelo, 'C001')

    sep = AssaiSeparacao(pedido_id=pedido.id, loja_id=loja.id, status=SEPARACAO_STATUS_FECHADA)
    db.session.add(sep)
    db.session.flush()

    nf = AssaiNfQpa(
        chave_44='2' * 44, numero='99999', loja_id=loja.id,
        separacao_id=sep.id, status_match=NF_STATUS_DIVERGENTE,
    )
    db.session.add(nf)
    db.session.commit()

    car = criar_carregamento(pedido.id, loja.id, operador_id=1)
    db.session.flush()
    escanear_carregamento_item(car.id, 'C001', operador_id=1)
    db.session.commit()

    finalizar_carregamento(car.id, operador_id=1)
    db.session.commit()

    # NAO deve criar divergencia (NF nao esta BATEU)
    divs = AssaiDivergencia.query.filter_by(nf_id=nf.id).all()
    assert len(divs) == 0


def test_fase7_a3_filtra_nf_cancelada(setup):
    """A3: query filtra NFs CANCELADA — busca apenas NF ativa."""
    pedido, loja, modelo = setup
    _chassi(modelo, 'C001')

    sep = AssaiSeparacao(pedido_id=pedido.id, loja_id=loja.id, status=SEPARACAO_STATUS_FECHADA)
    db.session.add(sep)
    db.session.flush()

    # NF cancelada (deve ser ignorada na query)
    nf_cancelada = AssaiNfQpa(
        chave_44='3' * 44, numero='C111', loja_id=loja.id,
        separacao_id=sep.id, status_match=NF_STATUS_CANCELADA,
    )
    db.session.add(nf_cancelada)
    db.session.commit()

    car = criar_carregamento(pedido.id, loja.id, operador_id=1)
    db.session.flush()
    escanear_carregamento_item(car.id, 'C001', operador_id=1)
    db.session.commit()

    finalizar_carregamento(car.id, operador_id=1)
    db.session.commit()

    # NAO deve criar divergencia (NF cancelada nao deve ser confrontada)
    divs = AssaiDivergencia.query.all()
    assert len(divs) == 0
```

- [ ] **Step 2: Rodar — devem falhar**

```bash
pytest tests/motos_assai/test_carregamento_finalizar_fase7_8.py -v -k 'fase7'
```

- [ ] **Step 3: Implementar Fase 7**

Adicionar imports:

```python
from app.motos_assai.models import (
    AssaiNfQpa, AssaiNfQpaItem, AssaiDivergencia,
    NF_STATUS_BATEU, NF_STATUS_DIVERGENTE,
    DIVERGENCIA_TIPO_NF_CHASSI_FORA_CARREGAMENTO,
    DIVERGENCIA_TIPO_CARREGAMENTO_CHASSI_FORA_NF,
)
```

Inserir Fase 7 antes do `return`:

```python
    # === FASE 7: detectar divergencia se NF ja existe e bateu ===
    # A3: filtra status_match != CANCELADA
    # S22=a: ignora NFs nao-BATEU
    # N-B3 fix: lazy import — divergencia_service so e criado no Plano 3 (Fase 4)
    from app.motos_assai.services.divergencia_service import criar_divergencia

    nf = (AssaiNfQpa.query
          .filter_by(separacao_id=sep_alvo.id)
          .filter(AssaiNfQpa.status_match != 'CANCELADA')
          .first())
    if nf and nf.status_match == NF_STATUS_BATEU:
        chassis_nf = {it.chassi for it in nf.itens}
        chassis_so_car = set(chassis_car) - chassis_nf
        chassis_so_nf = chassis_nf - set(chassis_car)
        houve_divergencia = False

        for c in chassis_so_car:
            criar_divergencia(
                tipo=DIVERGENCIA_TIPO_CARREGAMENTO_CHASSI_FORA_NF,
                chassi=c, sep_id=sep_alvo.id, car_id=car.id, nf_id=nf.id,
                detalhes={'origem': 'finalizar_carregamento_fase7'},
            )
            houve_divergencia = True

        for c in chassis_so_nf:
            criar_divergencia(
                tipo=DIVERGENCIA_TIPO_NF_CHASSI_FORA_CARREGAMENTO,
                chassi=c, sep_id=sep_alvo.id, car_id=car.id, nf_id=nf.id,
                detalhes={'origem': 'finalizar_carregamento_fase7'},
            )
            houve_divergencia = True

        # A4: NF.status_match volta de BATEU → DIVERGENTE quando Carregamento gera divergencia
        if houve_divergencia:
            nf.status_match = NF_STATUS_DIVERGENTE
```

- [ ] **Step 4: Rodar — devem passar**

```bash
pytest tests/motos_assai/test_carregamento_finalizar_fase7_8.py -v -k 'fase7'
```

- [ ] **Step 5: Commit**

```bash
git add app/motos_assai/services/carregamento_service.py tests/motos_assai/test_carregamento_finalizar_fase7_8.py
git commit -m "feat(motos-assai): finalizar_carregamento Fase 7 (divergencia NF + A4 BATEU→DIVERGENTE + A3 filtro CANCELADA)"
```

---

### Task 12: `finalizar_carregamento` Fase 8 — recalcular_status_pedido (A13)

**Files:**
- Modify: `app/motos_assai/services/carregamento_service.py`
- Modify: `tests/motos_assai/test_carregamento_finalizar_fase7_8.py`

- [ ] **Step 1: Adicionar teste**

```python
def test_fase8_recalcular_status_pedido_chamado(setup, monkeypatch):
    """A13: finalizar_carregamento chama recalcular_status_pedido defensivamente."""
    from app.motos_assai.services import pedido_status_service
    chamadas = []

    original = pedido_status_service.recalcular_status_pedido
    def spy(pid):
        chamadas.append(pid)
        return original(pid)

    monkeypatch.setattr(pedido_status_service, 'recalcular_status_pedido', spy)
    monkeypatch.setattr(
        'app.motos_assai.services.carregamento_service.recalcular_status_pedido', spy
    )

    pedido, loja, modelo = setup
    _chassi(modelo, 'C001')
    db.session.commit()

    car = criar_carregamento(pedido.id, loja.id, operador_id=1)
    db.session.flush()
    escanear_carregamento_item(car.id, 'C001', operador_id=1)
    db.session.commit()

    finalizar_carregamento(car.id, operador_id=1)
    db.session.commit()

    assert pedido.id in chamadas
```

- [ ] **Step 2: Rodar — deve falhar**

```bash
pytest tests/motos_assai/test_carregamento_finalizar_fase7_8.py -v -k 'fase8'
```

- [ ] **Step 3: Implementar Fase 8**

Adicionar import:
```python
from app.motos_assai.services.pedido_status_service import recalcular_status_pedido
```

Inserir Fase 8 antes do `return`:

```python
    # === FASE 8: recalcular status pedido (A13 — defensivo) ===
    # Carregamento por si nao muda qtd_faturada (so NF muda).
    # Mas se logica futura mudar (ex: sep nasce FATURADA via A11), pode precisar.
    # Custo zero (idempotente), beneficio: cobertura defensiva.
    recalcular_status_pedido(car.pedido_id)

    db.session.flush()
    return sep_alvo
```

- [ ] **Step 4: Rodar todos testes do `finalizar_carregamento`**

```bash
pytest tests/motos_assai/test_carregamento_finalizar_*.py -v
```

Expected: todos passam (Fases 1-8 completas).

- [ ] **Step 5: Commit**

```bash
git add app/motos_assai/services/carregamento_service.py tests/motos_assai/test_carregamento_finalizar_fase7_8.py
git commit -m "feat(motos-assai): finalizar_carregamento Fase 8 (recalcular_status_pedido defensivo A13)

Algoritmo §6 completo (8 fases). Pronto para integracao com UI."
```

---

### Task 13: Service `alterar_carregamento` (S6=a reabre)

**Files:**
- Modify: `app/motos_assai/services/carregamento_service.py`
- Create: `tests/motos_assai/test_carregamento_alterar.py`

- [ ] **Step 1: Escrever testes**

```python
"""Testes alterar_carregamento (S6=a reabre)."""
import pytest
from app import create_app, db
from app.motos_assai.models import *
from app.motos_assai.services.moto_evento_service import emitir_evento
from app.motos_assai.services.carregamento_service import (
    criar_carregamento, escanear_carregamento_item, finalizar_carregamento,
    alterar_carregamento, CarregamentoStateError,
)


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.rollback()
        db.drop_all()


@pytest.fixture
def setup_carregamento_finalizado(app):
    cd = AssaiCd(nome='CD', cnpj='12345678000100')
    loja = AssaiLoja(numero=999, cnpj='98765432000100', nome='Loja')
    modelo = AssaiModelo(codigo='SOL')
    db.session.add_all([cd, loja, modelo])
    db.session.flush()
    pedido = AssaiPedidoVenda(numero='T', cd_id=cd.id, status=PEDIDO_STATUS_ABERTO)
    db.session.add(pedido)
    db.session.flush()
    pvl = AssaiPedidoVendaLoja(pedido_id=pedido.id, loja_id=loja.id)
    db.session.add(pvl)
    db.session.flush()
    db.session.add(AssaiPedidoVendaItem(
        pedido_id=pedido.id, pedido_loja_id=pvl.id, loja_id=loja.id, modelo_id=modelo.id,
        qtd_pedida=10, valor_unitario=1000.0,
    ))

    moto = AssaiMoto(chassi='C001', modelo_id=modelo.id, cor='Preto')
    db.session.add(moto)
    db.session.flush()
    for ev in [EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_DISPONIVEL]:
        emitir_evento('C001', ev, operador_id=1)
    db.session.commit()

    car = criar_carregamento(pedido.id, loja.id, operador_id=1)
    db.session.flush()
    escanear_carregamento_item(car.id, 'C001', operador_id=1)
    db.session.commit()
    finalizar_carregamento(car.id, operador_id=1)
    db.session.commit()

    return car, pedido, loja, modelo


def test_alterar_carregamento_finalizado_volta_em_carregamento(setup_carregamento_finalizado):
    """S6=a: alterar reabre Carregamento (FINALIZADO → EM_CARREGAMENTO)."""
    car, _, _, _ = setup_carregamento_finalizado
    assert car.status == CARREGAMENTO_STATUS_FINALIZADO

    alterar_carregamento(car.id, operador_id=2)
    db.session.commit()

    car_ref = AssaiCarregamento.query.get(car.id)
    assert car_ref.status == CARREGAMENTO_STATUS_EM_CARREGAMENTO
    assert car_ref.finalizado_em is None  # reset
    assert car_ref.finalizado_por_id is None


def test_alterar_carregamento_em_carregamento_falha(setup_carregamento_finalizado):
    car, _, _, _ = setup_carregamento_finalizado
    car.status = CARREGAMENTO_STATUS_EM_CARREGAMENTO
    db.session.commit()

    with pytest.raises(CarregamentoStateError, match='ja EM_CARREGAMENTO'):
        alterar_carregamento(car.id, operador_id=2)


def test_alterar_carregamento_cancelado_falha(setup_carregamento_finalizado):
    car, _, _, _ = setup_carregamento_finalizado
    car.status = CARREGAMENTO_STATUS_CANCELADO
    db.session.commit()

    with pytest.raises(CarregamentoStateError, match='CANCELADO'):
        alterar_carregamento(car.id, operador_id=2)


def test_alterar_carregamento_regrede_sep_carregada_para_fechada(setup_carregamento_finalizado):
    """H3 fix: Sep vinculada CARREGADA regrede para FECHADA quando Carregamento reabre.

    Mantem invariante "Sep CARREGADA ↔ Carregamento FINALIZADO".
    """
    car, _, _, _ = setup_carregamento_finalizado
    sep_id = car.separacao_id
    assert sep_id is not None

    sep_antes = AssaiSeparacao.query.get(sep_id)
    assert sep_antes.status == SEPARACAO_STATUS_CARREGADA

    alterar_carregamento(car.id, operador_id=2)
    db.session.commit()

    # H3: Sep regrediu para FECHADA
    sep_depois = AssaiSeparacao.query.get(sep_id)
    assert sep_depois.status == SEPARACAO_STATUS_FECHADA
    # Carregamento esta EM_CARREGAMENTO
    assert AssaiCarregamento.query.get(car.id).status == CARREGAMENTO_STATUS_EM_CARREGAMENTO
    # Vinculo FK preservado (separacao_id continua apontando para mesma sep)
    assert AssaiCarregamento.query.get(car.id).separacao_id == sep_id
```

- [ ] **Step 2: Rodar — devem falhar**

```bash
pytest tests/motos_assai/test_carregamento_alterar.py -v
```

- [ ] **Step 3: Implementar `alterar_carregamento`**

```python
def alterar_carregamento(carregamento_id, operador_id):
    """Reabre Carregamento FINALIZADO para edicao (S6=a).

    Status: FINALIZADO → EM_CARREGAMENTO.
    Reset campos: finalizado_em, finalizado_por_id.
    Items existentes (assai_carregamento_item) NAO sao tocados — operador
    pode adicionar/remover via escanear_carregamento_item / cancelar_carregamento_item.

    Quando re-finalizar, executa Fase 2-6 do algoritmo §6 novamente
    (sep alvo pode mudar; chassis recalculados; Excel regenerado).

    Args:
        carregamento_id: ID do carregamento (deve estar FINALIZADO)
        operador_id: usuario que solicitou alteracao

    Raises:
        CarregamentoValidationError: carregamento nao existe
        CarregamentoStateError: nao esta FINALIZADO
    """
    car = AssaiCarregamento.query.get(carregamento_id)
    if not car:
        raise CarregamentoValidationError(f'Carregamento {carregamento_id} nao encontrado')

    if car.status == CARREGAMENTO_STATUS_EM_CARREGAMENTO:
        raise CarregamentoStateError(
            f'Carregamento {carregamento_id} ja EM_CARREGAMENTO — nao precisa alterar'
        )
    if car.status == CARREGAMENTO_STATUS_CANCELADO:
        raise CarregamentoStateError(
            f'Carregamento {carregamento_id} esta CANCELADO — nao pode ser reaberto. '
            f'Inicie um novo carregamento.'
        )

    # FINALIZADO → EM_CARREGAMENTO
    car.status = CARREGAMENTO_STATUS_EM_CARREGAMENTO
    car.finalizado_em = None
    car.finalizado_por_id = None

    # H3 fix — regredir Sep vinculada (CARREGADA → FECHADA) para manter invariante
    # "Sep CARREGADA ↔ Carregamento FINALIZADO". Sep mantem chassis (re-finalizar
    # vai re-ajustar via algoritmo §6 Fase 2). Mantem car.separacao_id (vinculo
    # FK preservado para que finalize re-use a mesma sep).
    if car.separacao_id:
        sep = AssaiSeparacao.query.get(car.separacao_id)
        if sep and sep.status == SEPARACAO_STATUS_CARREGADA:
            sep.status = SEPARACAO_STATUS_FECHADA
            # Sep volta a estado "pronta para Carregamento". Chassis nao mudam de evento
            # (ja estao com evento CARREGADA — proximo finalize pode mudar).

    db.session.flush()
```

- [ ] **Step 4: Rodar — devem passar**

```bash
pytest tests/motos_assai/test_carregamento_alterar.py -v
```

- [ ] **Step 5: Commit**

```bash
git add app/motos_assai/services/carregamento_service.py tests/motos_assai/test_carregamento_alterar.py
git commit -m "feat(motos-assai): alterar_carregamento (S6=a reabre FINALIZADO → EM_CARREGAMENTO)"
```

---

### Task 14: Atualizar `cancelar_separacao` para aceitar status `CARREGADA`

**Files:**
- Modify: `app/motos_assai/services/separacao_service.py`
- Create: `tests/motos_assai/test_cancelar_separacao_carregada.py`

- [ ] **Step 1: Escrever teste**

```python
"""Testes: cancelar_separacao deve aceitar sep em status CARREGADA."""
import pytest
from app import create_app, db
from app.motos_assai.models import *
from app.motos_assai.services.moto_evento_service import emitir_evento, status_efetivo
from app.motos_assai.services.separacao_service import cancelar_separacao


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.rollback()
        db.drop_all()


def test_cancelar_separacao_carregada_aceita(app):
    cd = AssaiCd(nome='CD', cnpj='12345678000100')
    loja = AssaiLoja(numero=999, cnpj='98765432000100', nome='Loja')
    modelo = AssaiModelo(codigo='SOL')
    db.session.add_all([cd, loja, modelo])
    db.session.flush()
    pedido = AssaiPedidoVenda(numero='T', cd_id=cd.id, status=PEDIDO_STATUS_ABERTO)
    db.session.add(pedido)
    db.session.flush()

    sep = AssaiSeparacao(pedido_id=pedido.id, loja_id=loja.id, status=SEPARACAO_STATUS_CARREGADA)
    db.session.add(sep)
    db.session.flush()
    db.session.add(AssaiSeparacaoItem(
        separacao_id=sep.id, chassi='C001', modelo_id=modelo.id, valor_unitario_qpa=1000.0,
    ))
    moto = AssaiMoto(chassi='C001', modelo_id=modelo.id, cor='Preto')
    db.session.add(moto)
    db.session.flush()
    for ev in [EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_DISPONIVEL, EVENTO_SEPARADA, EVENTO_CARREGADA]:
        emitir_evento('C001', ev, operador_id=1)
    db.session.commit()

    cancelar_separacao(sep.id, motivo='Teste cancel CARREGADA', operador_id=2)
    db.session.commit()

    sep_ref = AssaiSeparacao.query.get(sep.id)
    assert sep_ref.status == SEPARACAO_STATUS_CANCELADA

    # Chassi volta DISPONIVEL
    assert status_efetivo('C001') == EVENTO_DISPONIVEL


def test_cancelar_separacao_faturada_continua_bloqueada(app):
    """FATURADA continua nao podendo ser cancelada (precisa cancelar NF antes)."""
    cd = AssaiCd(nome='CD', cnpj='12345678000100')
    loja = AssaiLoja(numero=999, cnpj='98765432000100', nome='Loja')
    db.session.add_all([cd, loja])
    db.session.flush()
    pedido = AssaiPedidoVenda(numero='T', cd_id=cd.id)
    db.session.add(pedido)
    db.session.flush()

    sep = AssaiSeparacao(pedido_id=pedido.id, loja_id=loja.id, status=SEPARACAO_STATUS_FATURADA)
    db.session.add(sep)
    db.session.commit()

    from app.motos_assai.services.separacao_service import SeparacaoValidationError
    with pytest.raises(SeparacaoValidationError, match='FATURADA'):
        cancelar_separacao(sep.id, motivo='Tentativa', operador_id=1)
```

- [ ] **Step 2: Rodar — deve falhar (CARREGADA bloqueia hoje)**

```bash
pytest tests/motos_assai/test_cancelar_separacao_carregada.py -v
```

- [ ] **Step 3: Modificar `cancelar_separacao` em `separacao_service.py`**

Localizar a função `cancelar_separacao` em `app/motos_assai/services/separacao_service.py`. Encontrar a guarda de status. Atualizar para aceitar CARREGADA:

```python
def cancelar_separacao(sep_id, motivo, operador_id):
    # ... codigo existente ...

    # Atualizar guarda: aceita EM_SEPARACAO, FECHADA, CARREGADA. Bloqueia FATURADA, CANCELADA.
    if sep.status == SEPARACAO_STATUS_FATURADA:
        raise SeparacaoValidationError(
            f'Sep {sep_id} esta FATURADA. Cancele a NF (cancelar_nf_qpa) antes.'
        )
    if sep.status == SEPARACAO_STATUS_CANCELADA:
        raise SeparacaoValidationError(f'Sep {sep_id} ja CANCELADA')

    # CARREGADA tambem é cancelavel (chassis voltam DISPONIVEL)
    # Comportamento: emitir DISPONIVEL para cada chassi, atualizar sep status

    # ... resto do codigo, certificando que loop de chassis emite DISPONIVEL
    # tambem para chassis em estado CARREGADA
```

NOTA: implementação concreta depende do código atual de `cancelar_separacao`. Verifique linhas exatas e ajuste a guarda + loop de eventos.

- [ ] **Step 4: Rodar testes — devem passar**

```bash
pytest tests/motos_assai/test_cancelar_separacao_carregada.py -v
```

- [ ] **Step 5: Commit**

```bash
git add app/motos_assai/services/separacao_service.py tests/motos_assai/test_cancelar_separacao_carregada.py
git commit -m "feat(motos-assai): cancelar_separacao aceita status CARREGADA"
```

---

### Task 15: Atualizar `mirror_assai_to_separacao` para aceitar `(FECHADA, CARREGADA, FATURADA)` (S12)

**Files:**
- Modify: `app/motos_assai/services/separacao_mirror_service.py`
- Create: `tests/motos_assai/test_mirror_aceita_carregada.py`

- [ ] **Step 1: Escrever teste**

```python
"""Testes: mirror_assai_to_separacao aceita sep em CARREGADA e FATURADA (S12)."""
import pytest
from app import create_app, db
from app.motos_assai.models import *
from app.motos_assai.services.separacao_mirror_service import mirror_assai_to_separacao
from app.separacao.models import Separacao


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.rollback()
        db.drop_all()


def test_mirror_aceita_status_carregada(app):
    cd = AssaiCd(nome='CD', cnpj='12345678000100')
    loja = AssaiLoja(numero=999, cnpj='98765432000100', nome='Loja')
    modelo = AssaiModelo(codigo='SOL')
    db.session.add_all([cd, loja, modelo])
    db.session.flush()
    pedido = AssaiPedidoVenda(numero='T', cd_id=cd.id)
    db.session.add(pedido)
    db.session.flush()

    sep = AssaiSeparacao(pedido_id=pedido.id, loja_id=loja.id, status=SEPARACAO_STATUS_CARREGADA)
    db.session.add(sep)
    db.session.flush()
    db.session.add(AssaiSeparacaoItem(
        separacao_id=sep.id, chassi='C001', modelo_id=modelo.id, valor_unitario_qpa=1000.0,
    ))
    db.session.commit()

    mirror_assai_to_separacao(sep.id)
    db.session.commit()

    linhas = Separacao.query.filter_by(separacao_lote_id=f'ASSAI-SEP-{sep.id}').all()
    assert len(linhas) == 1


def test_mirror_aceita_status_faturada(app):
    """S1=b: sep nasce FATURADA via NF — mirror deve aceitar."""
    cd = AssaiCd(nome='CD', cnpj='12345678000100')
    loja = AssaiLoja(numero=999, cnpj='98765432000100', nome='Loja')
    modelo = AssaiModelo(codigo='SOL')
    db.session.add_all([cd, loja, modelo])
    db.session.flush()
    pedido = AssaiPedidoVenda(numero='T', cd_id=cd.id)
    db.session.add(pedido)
    db.session.flush()

    sep = AssaiSeparacao(pedido_id=pedido.id, loja_id=loja.id, status=SEPARACAO_STATUS_FATURADA)
    db.session.add(sep)
    db.session.flush()
    db.session.add(AssaiSeparacaoItem(
        separacao_id=sep.id, chassi='C002', modelo_id=modelo.id, valor_unitario_qpa=1000.0,
    ))
    db.session.commit()

    mirror_assai_to_separacao(sep.id)
    db.session.commit()

    linhas = Separacao.query.filter_by(separacao_lote_id=f'ASSAI-SEP-{sep.id}').all()
    assert len(linhas) == 1


def test_mirror_rejeita_em_separacao(app):
    """EM_SEPARACAO continua nao espelhando (sep nao finalizada)."""
    cd = AssaiCd(nome='CD', cnpj='12345678000100')
    loja = AssaiLoja(numero=999, cnpj='98765432000100', nome='Loja')
    modelo = AssaiModelo(codigo='SOL')
    db.session.add_all([cd, loja, modelo])
    db.session.flush()
    pedido = AssaiPedidoVenda(numero='T', cd_id=cd.id)
    db.session.add(pedido)
    db.session.flush()

    sep = AssaiSeparacao(pedido_id=pedido.id, loja_id=loja.id, status=SEPARACAO_STATUS_EM_SEPARACAO)
    db.session.add(sep)
    db.session.commit()

    from app.motos_assai.services.separacao_mirror_service import MirrorValidationError
    with pytest.raises((MirrorValidationError, ValueError), match='EM_SEPARACAO'):
        mirror_assai_to_separacao(sep.id)
```

- [ ] **Step 2: Rodar — testes Carregada/Faturada devem falhar (guarda atual aceita só FECHADA)**

```bash
pytest tests/motos_assai/test_mirror_aceita_carregada.py -v
```

- [ ] **Step 3: Modificar `mirror_assai_to_separacao` em `separacao_mirror_service.py`**

Localizar a função e a guarda inicial. Atualizar:

```python
# Antes:
# if sep.status != SEPARACAO_STATUS_FECHADA:
#     raise ValueError(f'Sep {sep_id} status={sep.status} (esperado FECHADA)')

# Depois (S12=a):
ESTADOS_ESPELHAVEIS = {
    SEPARACAO_STATUS_FECHADA,
    SEPARACAO_STATUS_CARREGADA,
    SEPARACAO_STATUS_FATURADA,
}
if sep.status not in ESTADOS_ESPELHAVEIS:
    raise MirrorValidationError(
        f'Sep {sep_id} status={sep.status} — mirror so espelha {ESTADOS_ESPELHAVEIS}'
    )
```

- [ ] **Step 4: Rodar — devem passar**

```bash
pytest tests/motos_assai/test_mirror_aceita_carregada.py -v
```

- [ ] **Step 5: Re-rodar Task 10 (Fase 6 do algoritmo) que depende deste fix**

```bash
pytest tests/motos_assai/test_carregamento_finalizar_fase4_5_6.py -v -k 'fase6'
```

- [ ] **Step 6: Commit**

```bash
git add app/motos_assai/services/separacao_mirror_service.py tests/motos_assai/test_mirror_aceita_carregada.py
git commit -m "feat(motos-assai): mirror_assai_to_separacao aceita CARREGADA + FATURADA (S12=a)"
```

---

## Fase 3 — UI (Tasks 16-25)

### Task 16: Rota e template `lista_carregamentos`

**Files:**
- Create: `app/motos_assai/routes/carregamento.py`
- Create: `app/templates/motos_assai/carregamento/lista.html`
- Modify: `app/motos_assai/__init__.py` (registrar blueprint se necessário)

- [ ] **Step 1: Criar `app/motos_assai/routes/carregamento.py`**

```python
"""Rotas de Carregamento (Fase 3 UI).

Spec: §15.1-15.2
Plano: Tasks 16-25
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.models import (
    AssaiCarregamento, AssaiCarregamentoItem,
    AssaiPedidoVenda, AssaiLoja,
    CARREGAMENTO_STATUS_EM_CARREGAMENTO, CARREGAMENTO_STATUS_FINALIZADO,
    CARREGAMENTO_STATUS_CANCELADO,
)
from app.motos_assai.services.carregamento_service import (
    criar_carregamento, escanear_carregamento_item,
    cancelar_carregamento_item, cancelar_carregamento,
    finalizar_carregamento, alterar_carregamento,
    CarregamentoValidationError, CarregamentoConflictError,
    CarregamentoStateError, CarregamentoExcedenteError,
)


carregamento_bp = Blueprint('motos_assai_carregamento', __name__,
                            url_prefix='/motos-assai/carregamento')


@carregamento_bp.route('/', methods=['GET'])
@login_required
@require_motos_assai
def lista_carregamentos():
    em_andamento = (AssaiCarregamento.query
                    .filter_by(status=CARREGAMENTO_STATUS_EM_CARREGAMENTO)
                    .order_by(AssaiCarregamento.iniciado_em.desc())
                    .all())
    finalizados_recentes = (AssaiCarregamento.query
                            .filter_by(status=CARREGAMENTO_STATUS_FINALIZADO)
                            .order_by(AssaiCarregamento.finalizado_em.desc())
                            .limit(20)
                            .all())
    cancelados_recentes = (AssaiCarregamento.query
                           .filter_by(status=CARREGAMENTO_STATUS_CANCELADO)
                           .order_by(AssaiCarregamento.cancelado_em.desc())
                           .limit(10)
                           .all())

    pedidos_abertos = (AssaiPedidoVenda.query
                       .filter(AssaiPedidoVenda.status.in_(['ABERTO', 'PARCIALMENTE_FATURADO']))
                       .order_by(AssaiPedidoVenda.numero)
                       .all())
    lojas = AssaiLoja.query.order_by(AssaiLoja.numero).all()

    return render_template('motos_assai/carregamento/lista.html',
                           em_andamento=em_andamento,
                           finalizados_recentes=finalizados_recentes,
                           cancelados_recentes=cancelados_recentes,
                           pedidos_abertos=pedidos_abertos,
                           lojas=lojas)
```

E em `app/motos_assai/__init__.py`:

```python
from app.motos_assai.routes.carregamento import carregamento_bp
# ... registrar no app factory ...
app.register_blueprint(carregamento_bp)
```

- [ ] **Step 2: Criar `app/templates/motos_assai/carregamento/lista.html`**

```html
{% extends "base.html" %}
{% block title %}Carregamentos — Motos Assaí{% endblock %}

{% block content %}
<div class="container-fluid py-3">
  <div class="d-flex justify-content-between align-items-center mb-3">
    <h2><i class="bi bi-truck"></i> Carregamentos</h2>
    <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#modal-iniciar"
            id="btn-iniciar-carregamento">
      <i class="bi bi-plus-circle"></i> Iniciar Carregamento
    </button>
  </div>

  {% with messages = get_flashed_messages(with_categories=true) %}
    {% for category, msg in messages %}
      <div class="alert alert-{{ category }}">{{ msg }}</div>
    {% endfor %}
  {% endwith %}

  <h4 class="mt-4">Em andamento ({{ em_andamento|length }})</h4>
  {% if em_andamento %}
  <table class="table table-hover" id="tbl-em-andamento">
    <thead>
      <tr>
        <th>#</th><th>Pedido</th><th>Loja</th><th>Operador</th><th>Iniciado em</th>
        <th>Itens</th><th>Ações</th>
      </tr>
    </thead>
    <tbody>
      {% for c in em_andamento %}
      <tr>
        <td>{{ c.id }}</td>
        <td>{{ c.pedido.numero }}</td>
        <td>L{{ c.loja.numero }} — {{ c.loja.nome }}</td>
        <td>{{ c.iniciado_por_id }}</td>
        <td>{{ c.iniciado_em.strftime('%d/%m %H:%M') }}</td>
        <td>{{ c.itens|length }}</td>
        <td>
          <a href="{{ url_for('motos_assai_carregamento.detalhe_carregamento', id=c.id) }}"
             class="btn btn-sm btn-outline-primary">Continuar</a>
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
  {% else %}
  <p class="text-muted">Nenhum carregamento em andamento.</p>
  {% endif %}

  <h4 class="mt-4">Finalizados recentes</h4>
  <table class="table table-sm" id="tbl-finalizados">
    <thead>
      <tr>
        <th>#</th><th>Pedido</th><th>Loja</th><th>Sep #</th><th>Finalizado em</th><th>Itens</th>
      </tr>
    </thead>
    <tbody>
      {% for c in finalizados_recentes %}
      <tr>
        <td>{{ c.id }}</td>
        <td>{{ c.pedido.numero }}</td>
        <td>L{{ c.loja.numero }}</td>
        <td>
          {% if c.separacao_id %}
            <a href="{{ url_for('motos_assai_separacao.separacao_tela', pid=c.pedido_id, lid=c.loja_id) }}?sep_id={{ c.separacao_id }}">
              {{ c.separacao_id }}
            </a>
          {% else %}—{% endif %}
        </td>
        <td>{{ c.finalizado_em.strftime('%d/%m %H:%M') if c.finalizado_em else '—' }}</td>
        <td>{{ c.itens|length }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>

{% include 'motos_assai/carregamento/_modal_iniciar.html' %}
{% endblock %}
```

- [ ] **Step 3: Criar `_modal_iniciar.html`**

```html
<div class="modal fade" id="modal-iniciar" tabindex="-1">
  <div class="modal-dialog">
    <div class="modal-content">
      <form method="POST" action="{{ url_for('motos_assai_carregamento.iniciar_carregamento') }}">
        <div class="modal-header">
          <h5>Iniciar Carregamento</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
          <div class="mb-3">
            <label>Pedido <span class="text-danger">*</span></label>
            <select name="pedido_id" class="form-select" required>
              <option value="">Selecione...</option>
              {% for p in pedidos_abertos %}
              <option value="{{ p.id }}">{{ p.numero }}</option>
              {% endfor %}
            </select>
          </div>
          <div class="mb-3">
            <label>Loja <span class="text-danger">*</span></label>
            <select name="loja_id" class="form-select" required>
              <option value="">Selecione...</option>
              {% for l in lojas %}
              <option value="{{ l.id }}">L{{ l.numero }} — {{ l.nome }}</option>
              {% endfor %}
            </select>
          </div>
          <p class="small text-muted">A2: pode haver N carregamentos paralelos para o mesmo (pedido, loja).</p>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
          <button type="submit" class="btn btn-primary">Iniciar</button>
        </div>
      </form>
    </div>
  </div>
</div>
```

- [ ] **Step 4: Implementar rota `iniciar_carregamento`**

Adicionar em `routes/carregamento.py`:

```python
@carregamento_bp.route('/iniciar', methods=['POST'])
@login_required
@require_motos_assai
def iniciar_carregamento():
    try:
        pedido_id = int(request.form['pedido_id'])
        loja_id = int(request.form['loja_id'])
    except (KeyError, ValueError):
        flash('Pedido e loja sao obrigatorios', 'danger')
        return redirect(url_for('motos_assai_carregamento.lista_carregamentos'))

    try:
        car = criar_carregamento(pedido_id, loja_id, operador_id=current_user.id)
        db.session.commit()
        flash(f'Carregamento #{car.id} iniciado', 'success')
        return redirect(url_for('motos_assai_carregamento.detalhe_carregamento', id=car.id))
    except CarregamentoValidationError as e:
        db.session.rollback()
        flash(str(e), 'danger')
        return redirect(url_for('motos_assai_carregamento.lista_carregamentos'))
```

- [ ] **Step 5: Smoke test manual**

```bash
python run.py
# Acessar http://localhost:5000/motos-assai/carregamento
# Verificar que página renderiza
# Clicar "Iniciar Carregamento" — modal abre
# Selecionar pedido + loja, submeter — redireciona para /carregamento/<id>
```

- [ ] **Step 6: Commit**

```bash
git add app/motos_assai/routes/carregamento.py app/templates/motos_assai/carregamento/ app/motos_assai/__init__.py
git commit -m "feat(motos-assai): UI lista_carregamentos + modal iniciar"
```

---

### Tasks 17-22: UI restante (escanear, modais finalizar/cancelar/alterar/excedente)

NOTA: para reduzir tamanho deste plano, as tasks 17-25 seguem o **mesmo padrão das tasks anteriores**. Estrutura repetitiva:

#### Task 17: Tela `detalhe_carregamento` (escanear)

- Rota `GET /carregamento/<id>` renderiza `escanear.html`
- Template com header (pedido + loja + status), input chassi (QR/manual), tabela de itens escaneados, botões Finalizar/Cancelar/Alterar
- JS `carregamento_escanear.js` orquestra escaneio AJAX (reusa `chassi_autocomplete.js`)

#### Task 18: AJAX endpoints

```python
@carregamento_bp.route('/<int:id>/escanear', methods=['POST'])
def escanear_chassi_ajax(id):
    chassi = request.json.get('chassi', '').strip().upper()
    try:
        item = escanear_carregamento_item(id, chassi, operador_id=current_user.id)
        db.session.commit()
        return jsonify({'ok': True, 'item': {'id': item.id, 'chassi': item.chassi, 'modelo': item.modelo.codigo}})
    except CarregamentoValidationError as e:
        db.session.rollback()
        return jsonify({'ok': False, 'msg': str(e)}), 400
    except CarregamentoConflictError as e:
        db.session.rollback()
        return jsonify({'ok': False, 'msg': str(e), 'retry': False}), 409
    except CarregamentoStateError as e:
        db.session.rollback()
        return jsonify({'ok': False, 'msg': str(e)}), 422


@carregamento_bp.route('/item/<int:item_id>/cancelar', methods=['POST'])
def cancelar_item_ajax(item_id):
    try:
        cancelar_carregamento_item(item_id, operador_id=current_user.id)
        db.session.commit()
        return jsonify({'ok': True})
    except (CarregamentoValidationError, CarregamentoStateError) as e:
        db.session.rollback()
        return jsonify({'ok': False, 'msg': str(e)}), 400


@carregamento_bp.route('/<int:id>/finalizar', methods=['POST'])
def finalizar_ajax(id):
    try:
        sep = finalizar_carregamento(id, operador_id=current_user.id)
        db.session.commit()
        return jsonify({'ok': True, 'sep_id': sep.id, 'redirect': url_for('motos_assai.faturamento_lista')})
    except CarregamentoExcedenteError as e:
        db.session.rollback()
        return jsonify({
            'ok': False, 'msg': str(e),
            'cenario': 'excedente',
            'qtd_excedente': e.qtd_excedente,
            'seps_bloqueadas': e.seps_bloqueadas,
        }), 409
    except (CarregamentoValidationError, CarregamentoStateError) as e:
        db.session.rollback()
        return jsonify({'ok': False, 'msg': str(e)}), 400


@carregamento_bp.route('/<int:id>/cancelar', methods=['POST'])
def cancelar_carregamento_ajax(id):
    motivo = request.json.get('motivo', '').strip()
    try:
        cancelar_carregamento(id, motivo=motivo, operador_id=current_user.id)
        db.session.commit()
        return jsonify({'ok': True, 'redirect': url_for('motos_assai_carregamento.lista_carregamentos')})
    except (CarregamentoValidationError, CarregamentoStateError) as e:
        db.session.rollback()
        return jsonify({'ok': False, 'msg': str(e)}), 400


@carregamento_bp.route('/<int:id>/alterar', methods=['POST'])
def alterar_carregamento_ajax(id):
    try:
        alterar_carregamento(id, operador_id=current_user.id)
        db.session.commit()
        return jsonify({'ok': True, 'redirect': url_for('motos_assai_carregamento.detalhe_carregamento', id=id)})
    except (CarregamentoValidationError, CarregamentoStateError) as e:
        db.session.rollback()
        return jsonify({'ok': False, 'msg': str(e)}), 400
```

#### Tasks 19-22: Modais

- `_modal_finalizar.html` — confirmação simples
- `_modal_cancelar.html` — motivo obrigatório (textarea min 3 chars)
- `_modal_alterar.html` — confirmação reabrir
- `_modal_excedente.html` — exibe qtd_excedente + seps_bloqueadas + instruções

Template padrão Bootstrap 5. JS handler em `carregamento_escanear.js`.

#### Task 23: Atualizar `app/templates/base.html` — adicionar link no menu

Localizar bloco do menu Motos Assaí, adicionar:

```html
{% if current_user.pode_acessar_motos_assai() %}
  <li><a class="dropdown-item" href="{{ url_for('motos_assai_carregamento.lista_carregamentos') }}">
    <i class="bi bi-truck"></i> Carregamento
  </a></li>
{% endif %}
```

#### Task 24: Onboarding tours

Criar `app/static/onboarding/tours/motos_assai/carregamento_lista.js` e `carregamento_escanear.js` seguindo padrão de Plano 5 (driver.js).

Atualizar `motos_assai.macro` (engine de tours). Incluir `<script>` em `admin/onboarding_health.html` E `onboarding_preview.html`.

#### Task 25: Smoke tests E2E

```python
"""E2E: fluxo completo Carregamento via UI."""
def test_e2e_iniciar_escanear_finalizar(client, setup):
    # Login + criar carregamento via UI
    response = client.post('/motos-assai/carregamento/iniciar', data={
        'pedido_id': pedido.id, 'loja_id': loja.id,
    })
    assert response.status_code == 302  # redirect

    # Escanear chassi via AJAX
    response = client.post(f'/motos-assai/carregamento/{car.id}/escanear', json={
        'chassi': 'C001'
    })
    assert response.status_code == 200
    assert response.get_json()['ok'] is True

    # Finalizar via AJAX
    response = client.post(f'/motos-assai/carregamento/{car.id}/finalizar')
    assert response.status_code == 200
    assert 'sep_id' in response.get_json()
```

#### Task 26: Deploy

PR + review + merge + deploy Render. Sem migrations novas (todas Fase 1). Apenas código novo.

```bash
git push origin feature/motos-assai-fase2-3-carregamento
gh pr create --title "feat(motos-assai): Fase 2-3 Carregamento (service + UI completa)" --body "
- carregamento_service.py: 6 services (criar, escanear, cancelar item, cancelar, finalizar 8 fases, alterar)
- 30+ testes unitários
- UI: /motos-assai/carregamento (lista + escaneio + 4 modais)
- Onboarding tours + integração base.html menu
- Atualizações: cancelar_separacao aceita CARREGADA, mirror aceita CARREGADA+FATURADA
"
```

Após merge, smoke test em prod.

---

## Self-review (executor)

Antes de iniciar Task 1:
- Plano 1 (Fase 1) deployado em prod
- `python -c "from app.motos_assai.models import AssaiCarregamento, CARREGAMENTO_STATUS_EM_CARREGAMENTO; print('OK')"` funciona

Estimativa: **20-30h** (Fase 2 ~12-18h, Fase 3 ~8-12h).
