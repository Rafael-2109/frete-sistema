<!-- doc:meta
tipo: how-to
camada: L3
sot_de: —
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-02
-->
# Transferência de Saldo entre Códigos (Odoo) — Implementation Plan

> **Papel:** Transferência de Saldo entre Códigos (Odoo) — Implementation Plan.

## Indice

- [File Structure](#file-structure)
- [Task 1: Service scaffold + `resolver_produto`](#task-1-service-scaffold-resolver_produto)
- [Task 2: `listar_lotes_cd_estoque`](#task-2-listar_lotes_cd_estoque)
- [Task 3: `descobrir_destinos` (bidirecional)](#task-3-descobrir_destinos-bidirecional)
- [Task 4: `transferir` — orquestração Odoo + compensação + validade](#task-4-transferir-orquestração-odoo-compensação-validade)
- [Task 5: `_registrar_movimentacao_local` (espelho local)](#task-5-_registrar_movimentacao_local-espelho-local)
- [Task 6: Rotas no `estoque_bp` (tela + api/lotes + api/executar)](#task-6-rotas-no-estoque_bp-tela-apilotes-apiexecutar)
- [Task 7: Template + itens de menu](#task-7-template-itens-de-menu)
- [Task 8: Verificação manual (smoke) + checklist do spec](#task-8-verificação-manual-smoke-checklist-do-spec)
- [Notas de implementação](#notas-de-implementação)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tela + endpoint no módulo `app/estoque` para transferir saldo de um código de produto para o código par (`UnificacaoCodigos`) mantendo o mesmo lote, em CD/Estoque (Odoo company 4 / loc 32), criando o lote no destino se não existir.

**Architecture:** Service desacoplado da UI (`app/odoo/services/`, junto dos átomos-irmãos Odoo) que orquestra 2 ajustes atômicos (`StockQuantAdjustmentService`) + criação de lote (`StockLotService`) + espelho local (`MovimentacaoEstoque`). 3 rotas finas no `estoque_bp` consomem o service. O mesmo service servirá a futura skill do subagente `gestor-estoque-odoo`.

**Tech Stack:** Flask 3 + Flask-Login + Flask-WTF (CSRF) · SQLAlchemy · Odoo XML-RPC · pytest + unittest.mock · Jinja2 + Bootstrap 5 + vanilla JS.

**Spec:** `docs/superpowers/specs/2026-05-22-transferencia-saldo-codigos-odoo-design.md`

---

## File Structure

| Arquivo | Responsabilidade |
|---------|------------------|
| `app/odoo/services/transferencia_saldo_codigo_service.py` (CRIAR) | `TransferenciaSaldoCodigoService`: resolver produto, listar lotes CD, descobrir destinos, transferir (Odoo + espelho local). |
| `tests/odoo/services/test_transferencia_saldo_codigo_service.py` (CRIAR) | Testes unitários (mock Odoo + deps injetadas). |
| `app/estoque/routes.py` (MODIFICAR) | 3 rotas no `estoque_bp`: tela (GET), `api/lotes` (GET), `api/executar` (POST). |
| `app/templates/estoque/transferir_saldo_odoo.html` (CRIAR) | UI: input código → tabela lotes + seletor destino + AJAX. |
| `app/templates/base.html` (MODIFICAR, após linha 836) | Item de menu "Carteira & Estoque". |
| `app/templates/_sidebar.html` (MODIFICAR, após linha 141) | Item de menu sidebar. |

**Convenções confirmadas no código:**
- CD = `company_id=4`, `location_id=COMPANY_LOCATIONS[4]` = 32 (`app/odoo/constants/locations.py`).
- `cod_produto` = `product.product.default_code`.
- Rotas `estoque_bp` usam `@login_required` (`app/estoque/routes.py:2`).
- Resposta AJAX: `jsonify({'success': bool, 'message': str, ...})` (padrão `processar_nova_movimentacao`).
- CSRF: `<meta name="csrf-token">` em `base.html:7` → header `X-CSRFToken` (CSRFProtect global).
- Mock de teste: `MagicMock()` para Odoo + deps, `side_effect` para sequenciar (`tests/odoo/services/test_stock_internal_transfer_service.py`).

---

## Task 1: Service scaffold + `resolver_produto`

**Files:**
- Create: `app/odoo/services/transferencia_saldo_codigo_service.py`
- Test: `tests/odoo/services/test_transferencia_saldo_codigo_service.py`

- [ ] **Step 1: Escrever o teste falho**

```python
# tests/odoo/services/test_transferencia_saldo_codigo_service.py
from unittest.mock import MagicMock
import pytest
from app.odoo.services.transferencia_saldo_codigo_service import (
    TransferenciaSaldoCodigoService,
)


@pytest.fixture
def odoo_mock():
    return MagicMock()


@pytest.fixture
def adj_mock():
    return MagicMock()


@pytest.fixture
def lot_mock():
    return MagicMock()


@pytest.fixture
def service(odoo_mock, adj_mock, lot_mock):
    return TransferenciaSaldoCodigoService(
        odoo=odoo_mock, adjustment_svc=adj_mock, lot_svc=lot_mock)


def test_resolver_produto_ok(service, odoo_mock):
    odoo_mock.search_read.return_value = [{
        'id': 27749, 'default_code': '4729198', 'name': 'AZEITE',
        'active': True, 'tracking': 'lot',
        'uom_id': [12, 'CAIXAS'], 'use_expiration_date': True,
    }]
    info = service.resolver_produto('4729198')
    assert info['product_id'] == 27749
    assert info['uom'] == 'CAIXAS'
    assert info['use_expiration_date'] is True
    assert info['tracking'] == 'lot'


def test_resolver_produto_inexistente(service, odoo_mock):
    odoo_mock.search_read.return_value = []
    with pytest.raises(ValueError, match='nao encontrado'):
        service.resolver_produto('999999')


def test_resolver_produto_ambiguo(service, odoo_mock):
    odoo_mock.search_read.return_value = [
        {'id': 1, 'default_code': '4729198', 'name': 'A', 'active': True,
         'tracking': 'lot', 'uom_id': [12, 'CAIXAS'], 'use_expiration_date': True},
        {'id': 2, 'default_code': '4729198', 'name': 'B', 'active': True,
         'tracking': 'lot', 'uom_id': [12, 'CAIXAS'], 'use_expiration_date': True},
    ]
    with pytest.raises(ValueError, match='ambiguo'):
        service.resolver_produto('4729198')
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `pytest tests/odoo/services/test_transferencia_saldo_codigo_service.py -v`
Expected: FAIL (ModuleNotFoundError / ImportError).

- [ ] **Step 3: Implementar scaffold + `resolver_produto`**

```python
# app/odoo/services/transferencia_saldo_codigo_service.py
"""TransferenciaSaldoCodigoService — transfere saldo entre CÓDIGOS mantendo lote.

Em CD/Estoque (company 4, loc 32). É uma TROCA DE CÓDIGO: mesmo nome de lote em
produtos diferentes (origem→destino). Diferente de StockInternalTransferService
(mesmo produto, lotes diferentes). Orquestra 2 ajustes atômicos:
  1. reduzir quant origem (lote X)
  2. garantir lote X no produto destino (criar com validade do origem) + aumentar

Desacoplado da UI (sem flask/request/current_user): `usuario` entra por parâmetro.
Tela web e futura skill do gestor-estoque-odoo consomem o mesmo service.

Spec: docs/superpowers/specs/2026-05-22-transferencia-saldo-codigos-odoo-design.md
"""
import logging
from typing import Any, Dict, List, Optional

from app.odoo.constants.locations import COMPANY_LOCATIONS
from app.odoo.services.stock_lot_service import StockLotService
from app.odoo.services.stock_quant_adjustment_service import (
    StockQuantAdjustmentService,
)
from app.odoo.utils.connection import get_odoo_connection

logger = logging.getLogger(__name__)

CASAS = 6


class TransferenciaSaldoCodigoService:
    """Transfere saldo entre códigos mantendo o lote, em CD/Estoque."""

    CD_COMPANY_ID = 4
    CD_ESTOQUE_LOC = COMPANY_LOCATIONS[4]  # 32

    def __init__(self, odoo=None, adjustment_svc=None, lot_svc=None):
        self.odoo = odoo or get_odoo_connection()
        self.lot_svc = lot_svc or StockLotService(odoo=self.odoo)
        self.adjustment_svc = adjustment_svc or StockQuantAdjustmentService(
            odoo=self.odoo, lot_svc=self.lot_svc)

    def resolver_produto(self, cod) -> Dict[str, Any]:
        """default_code -> dados do produto. Erro se 0 ou >1 ativo."""
        cod = str(cod).strip()
        res = self.odoo.search_read(
            'product.product', [['default_code', '=', cod]],
            ['id', 'default_code', 'name', 'active', 'tracking',
             'uom_id', 'use_expiration_date'], limit=0)
        ativos = [p for p in res if p.get('active')]
        candidatos = ativos or res
        if not candidatos:
            raise ValueError(f'Produto {cod} nao encontrado no Odoo')
        if len(candidatos) > 1:
            raise ValueError(
                f'Produto {cod} ambiguo: {len(candidatos)} produtos')
        p = candidatos[0]
        return {
            'product_id': p['id'], 'cod': p['default_code'], 'name': p.get('name'),
            'tracking': p.get('tracking'),
            'uom': p['uom_id'][1] if p.get('uom_id') else None,
            'use_expiration_date': bool(p.get('use_expiration_date')),
        }
```

- [ ] **Step 4: Rodar e verificar que passa**

Run: `pytest tests/odoo/services/test_transferencia_saldo_codigo_service.py -v`
Expected: PASS (3 testes).

- [ ] **Step 5: Commit**

```bash
git add app/odoo/services/transferencia_saldo_codigo_service.py tests/odoo/services/test_transferencia_saldo_codigo_service.py
git commit -m "feat(estoque): TransferenciaSaldoCodigoService scaffold + resolver_produto"
```

---

## Task 2: `listar_lotes_cd_estoque`

**Files:**
- Modify: `app/odoo/services/transferencia_saldo_codigo_service.py`
- Test: `tests/odoo/services/test_transferencia_saldo_codigo_service.py`

- [ ] **Step 1: Escrever o teste falho**

```python
def test_listar_lotes_cd_estoque(service, odoo_mock):
    service.resolver_produto = MagicMock(return_value={'product_id': 27749})
    odoo_mock.search_read.return_value = [
        {'id': 1, 'lot_id': [56426, '135/26'], 'quantity': 290.0, 'reserved_quantity': 0.0},
        {'id': 2, 'lot_id': [30856, 'MIGRAÇÃO'], 'quantity': 100.0, 'reserved_quantity': 40.0},
        {'id': 3, 'lot_id': False, 'quantity': 5.0, 'reserved_quantity': 0.0},
    ]
    lotes = service.listar_lotes_cd_estoque('4729198')
    assert lotes[0] == {'lote_nome': '135/26', 'lot_id': 56426, 'quantidade': 290.0,
                        'reservado': 0.0, 'disponivel': 290.0, 'is_migracao': False}
    assert lotes[1]['is_migracao'] is True
    assert lotes[1]['disponivel'] == 60.0
    assert lotes[2]['lote_nome'] is None and lotes[2]['lot_id'] is None
    # domain filtra company 4 e loc 32
    domain = odoo_mock.search_read.call_args[0][1]
    assert ['company_id', '=', 4] in domain
    assert ['location_id', '=', 32] in domain
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `pytest tests/odoo/services/test_transferencia_saldo_codigo_service.py::test_listar_lotes_cd_estoque -v`
Expected: FAIL (AttributeError: listar_lotes_cd_estoque).

- [ ] **Step 3: Implementar**

```python
    def listar_lotes_cd_estoque(self, cod) -> List[Dict[str, Any]]:
        """Lotes do código em CD/Estoque com qtd/reservado/disponível/migração."""
        info = self.resolver_produto(cod)
        quants = self.odoo.search_read(
            'stock.quant',
            [['product_id', '=', info['product_id']],
             ['company_id', '=', self.CD_COMPANY_ID],
             ['location_id', '=', self.CD_ESTOQUE_LOC]],
            ['id', 'lot_id', 'quantity', 'reserved_quantity'], limit=0)
        out: List[Dict[str, Any]] = []
        for q in quants:
            lot = q.get('lot_id')
            lote_nome = lot[1] if lot else None
            qty = round(float(q['quantity']), CASAS)
            rsv = round(float(q.get('reserved_quantity') or 0), CASAS)
            out.append({
                'lote_nome': lote_nome,
                'lot_id': lot[0] if lot else None,
                'quantidade': qty, 'reservado': rsv,
                'disponivel': round(qty - rsv, CASAS),
                'is_migracao': bool(lote_nome and 'MIGRA' in lote_nome.upper()),
            })
        return out
```

- [ ] **Step 4: Rodar e verificar que passa**

Run: `pytest tests/odoo/services/test_transferencia_saldo_codigo_service.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -u && git commit -m "feat(estoque): listar_lotes_cd_estoque (qtd/reservado/disponivel/migracao)"
```

---

## Task 3: `descobrir_destinos` (bidirecional)

**Files:**
- Modify: `app/odoo/services/transferencia_saldo_codigo_service.py`
- Test: `tests/odoo/services/test_transferencia_saldo_codigo_service.py`

- [ ] **Step 1: Escrever o teste falho**

```python
from unittest.mock import patch


# fixture `app` (conftest, session scope) garante que app.estoque.models é importável
def test_descobrir_destinos_bidirecional(service, app):
    service.resolver_produto = MagicMock(side_effect=[
        {'product_id': 27735, 'name': 'SOJA'},
    ])
    with patch('app.estoque.models.UnificacaoCodigos.get_todos_codigos_relacionados',
               return_value=['4729198', '4759198']):
        destinos = service.descobrir_destinos('4729198')
    assert destinos == [{'codigo': '4759198', 'nome': 'SOJA'}]


def test_descobrir_destinos_vazio(service, app):
    with patch('app.estoque.models.UnificacaoCodigos.get_todos_codigos_relacionados',
               return_value=['4729198']):
        assert service.descobrir_destinos('4729198') == []
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `pytest tests/odoo/services/test_transferencia_saldo_codigo_service.py::test_descobrir_destinos_bidirecional -v`
Expected: FAIL (AttributeError).

- [ ] **Step 3: Implementar**

```python
    def descobrir_destinos(self, cod) -> List[Dict[str, Any]]:
        """Pares ativos relacionados (bidirecional), excluindo o próprio código."""
        from app.estoque.models import UnificacaoCodigos
        cod = str(cod).strip()
        relacionados = UnificacaoCodigos.get_todos_codigos_relacionados(cod)
        out: List[Dict[str, Any]] = []
        for c in relacionados:
            if str(c) == cod:
                continue
            try:
                info = self.resolver_produto(c)
                nome = info['name']
            except ValueError:
                nome = None
            out.append({'codigo': str(c), 'nome': nome})
        return out
```

- [ ] **Step 4: Rodar e verificar que passa**

Run: `pytest tests/odoo/services/test_transferencia_saldo_codigo_service.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -u && git commit -m "feat(estoque): descobrir_destinos bidirecional via UnificacaoCodigos"
```

---

## Task 4: `transferir` — orquestração Odoo + compensação + validade

**Files:**
- Modify: `app/odoo/services/transferencia_saldo_codigo_service.py`
- Test: `tests/odoo/services/test_transferencia_saldo_codigo_service.py`

- [ ] **Step 1: Escrever os testes falhos**

```python
def _info(pid, cod, name, use_exp=True):
    return {'product_id': pid, 'cod': cod, 'name': name,
            'tracking': 'lot', 'uom': 'CAIXAS', 'use_expiration_date': use_exp}


def test_transferir_feliz(service, odoo_mock, adj_mock, lot_mock):
    service.descobrir_destinos = MagicMock(return_value=[{'codigo': '4759198', 'nome': 'SOJA'}])
    service.resolver_produto = MagicMock(side_effect=[
        _info(27749, '4729198', 'AZEITE'), _info(27735, '4759198', 'SOJA')])
    service._registrar_movimentacao_local = MagicMock()
    lot_mock.buscar_por_nome.return_value = 56426
    odoo_mock.read.return_value = [{'expiration_date': '2028-05-15 00:00:00'}]
    lot_mock.criar_se_nao_existe.return_value = (58503, False)
    adj_mock.ajustar_quant.side_effect = [
        {'status': 'EXECUTADO', 'qty_antes': 290.0, 'qty_apos': 285.0},
        {'status': 'EXECUTADO', 'qty_antes': 2.0, 'qty_apos': 7.0},
    ]
    r = service.transferir('4729198', '4759198', '135/26', 5.0, 'rafael')
    assert r['status'] == 'EXECUTADO'
    assert r['origem_apos'] == 285.0 and r['destino_apos'] == 7.0
    # validade do origem replicada ao criar lote destino
    assert lot_mock.criar_se_nao_existe.call_args.kwargs['expiration_date'] == '2028-05-15 00:00:00'
    service._registrar_movimentacao_local.assert_called_once()


def test_transferir_par_invalido(service):
    service.descobrir_destinos = MagicMock(return_value=[{'codigo': '999', 'nome': 'X'}])
    with pytest.raises(ValueError, match='nao e par'):
        service.transferir('4729198', '4759198', '135/26', 5.0, 'rafael')


def test_transferir_qty_invalida(service):
    with pytest.raises(ValueError, match='qty deve ser > 0'):
        service.transferir('4729198', '4759198', '135/26', 0, 'rafael')


def test_transferir_reducao_falha_nao_aumenta(service, odoo_mock, adj_mock, lot_mock):
    service.descobrir_destinos = MagicMock(return_value=[{'codigo': '4759198', 'nome': 'SOJA'}])
    service.resolver_produto = MagicMock(side_effect=[
        _info(27749, '4729198', 'AZEITE'), _info(27735, '4759198', 'SOJA')])
    lot_mock.buscar_por_nome.return_value = 56426
    odoo_mock.read.return_value = [{'expiration_date': False}]
    adj_mock.ajustar_quant.return_value = {'status': 'FALHA_RESERVADO', 'erro': 'reservado'}
    r = service.transferir('4729198', '4759198', '135/26', 5.0, 'rafael')
    assert r['status'] == 'FALHA_REDUCAO'
    assert adj_mock.ajustar_quant.call_count == 1  # não tentou aumentar


def test_transferir_aumento_falha_compensa(service, odoo_mock, adj_mock, lot_mock):
    service.descobrir_destinos = MagicMock(return_value=[{'codigo': '4759198', 'nome': 'SOJA'}])
    service.resolver_produto = MagicMock(side_effect=[
        _info(27749, '4729198', 'AZEITE'), _info(27735, '4759198', 'SOJA')])
    lot_mock.buscar_por_nome.return_value = 56426
    odoo_mock.read.return_value = [{'expiration_date': '2028-05-15 00:00:00'}]
    lot_mock.criar_se_nao_existe.return_value = (58503, False)
    adj_mock.ajustar_quant.side_effect = [
        {'status': 'EXECUTADO', 'qty_antes': 290.0, 'qty_apos': 285.0},  # reduz ok
        {'status': 'FALHA_ODOO', 'erro': 'boom'},                        # aumento falha
        {'status': 'EXECUTADO', 'qty_antes': 285.0, 'qty_apos': 290.0},  # compensa
    ]
    r = service.transferir('4729198', '4759198', '135/26', 5.0, 'rafael')
    assert r['status'] == 'FALHA_AUMENTO_COMPENSADO'
    assert adj_mock.ajustar_quant.call_count == 3  # reduz + aumenta + compensa
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `pytest tests/odoo/services/test_transferencia_saldo_codigo_service.py -k transferir -v`
Expected: FAIL (AttributeError: transferir).

- [ ] **Step 3: Implementar `transferir`**

```python
    def transferir(self, cod_origem, cod_destino, lote_nome, qty,
                   usuario) -> Dict[str, Any]:
        """Transfere `qty` de cod_origem→cod_destino mantendo `lote_nome` em
        CD/Estoque. Reduz origem → cria/aumenta destino (compensa se falhar).
        Espelha em MovimentacaoEstoque. `lote_nome=None` => quant sem lote.
        """
        cod_origem, cod_destino = str(cod_origem).strip(), str(cod_destino).strip()
        qty = round(float(qty), CASAS)
        r: Dict[str, Any] = {
            'cod_origem': cod_origem, 'cod_destino': cod_destino,
            'lote_nome': lote_nome, 'qty': qty, 'usuario': usuario,
            'lote_criado': False, 'status': None}
        if qty <= 0:
            raise ValueError(f'qty deve ser > 0 (recebido {qty})')

        # 1. validar par bidirecional
        destinos = {d['codigo'] for d in self.descobrir_destinos(cod_origem)}
        if cod_destino not in destinos:
            raise ValueError(
                f'{cod_destino} nao e par de {cod_origem} em UnificacaoCodigos ativa')

        # 2. resolver produtos
        origem = self.resolver_produto(cod_origem)
        destino = self.resolver_produto(cod_destino)
        for info in (origem, destino):
            if info['tracking'] != 'lot':
                raise ValueError(
                    f"produto {info['cod']} tracking={info['tracking']} (esperado lot)")
        pid_o, pid_d = origem['product_id'], destino['product_id']

        # 3. resolver lote origem + validade (replicar no destino)
        lot_id_origem: Optional[int] = None
        validade: Optional[str] = None
        if lote_nome:
            lot_id_origem = self.lot_svc.buscar_por_nome(
                lote_nome, pid_o, self.CD_COMPANY_ID)
            if not lot_id_origem:
                raise ValueError(
                    f'lote {lote_nome!r} nao encontrado no produto {cod_origem} (CD)')
            lots = self.odoo.read('stock.lot', [lot_id_origem], ['expiration_date'])
            validade = (lots[0].get('expiration_date') or None) if lots else None

        # 4. reduzir origem
        r_red = self.adjustment_svc.ajustar_quant(
            product_id=pid_o, company_id=self.CD_COMPANY_ID,
            location_id=self.CD_ESTOQUE_LOC, lot_id=lot_id_origem, delta=-qty,
            validar_nao_negativar=True, validar_nao_abaixo_reserva=True)
        r['reducao'] = r_red
        if r_red['status'] != 'EXECUTADO':
            r['status'] = 'FALHA_REDUCAO'
            r['erro'] = r_red.get('erro')
            return r
        r['origem_antes'], r['origem_apos'] = r_red.get('qty_antes'), r_red.get('qty_apos')

        # 5. garantir lote destino (validade do origem se produto usa validade)
        lot_id_destino: Optional[int] = None
        if lote_nome:
            exp = validade if destino['use_expiration_date'] else None
            lot_id_destino, criado = self.lot_svc.criar_se_nao_existe(
                lote_nome, pid_d, self.CD_COMPANY_ID, expiration_date=exp)
            r['lote_criado'] = criado

        # 6. aumentar destino (compensar se falhar)
        r_aum = self.adjustment_svc.ajustar_quant(
            product_id=pid_d, company_id=self.CD_COMPANY_ID,
            location_id=self.CD_ESTOQUE_LOC, lot_id=lot_id_destino, delta=qty,
            criar_se_faltar=True, validar_nao_negativar=True,
            validar_nao_abaixo_reserva=True)
        r['aumento'] = r_aum
        if r_aum['status'] != 'EXECUTADO':
            comp = self.adjustment_svc.ajustar_quant(
                product_id=pid_o, company_id=self.CD_COMPANY_ID,
                location_id=self.CD_ESTOQUE_LOC, lot_id=lot_id_origem, delta=qty,
                validar_nao_negativar=False, validar_nao_abaixo_reserva=False)
            r['compensacao'] = comp
            r['status'] = 'FALHA_AUMENTO_COMPENSADO'
            r['erro'] = r_aum.get('erro')
            logger.error(
                f'Aumento falhou ({cod_origem}->{cod_destino} lote {lote_nome} '
                f'qty {qty}): {r_aum.get("erro")}; compensacao={comp.get("status")}')
            return r
        r['destino_antes'], r['destino_apos'] = r_aum.get('qty_antes'), r_aum.get('qty_apos')

        # 7. espelho local
        self._registrar_movimentacao_local(
            cod_origem, origem['name'], cod_destino, destino['name'],
            lote_nome, qty, usuario)
        r['status'] = 'EXECUTADO'
        return r
```

> NOTA: `_registrar_movimentacao_local` é implementado na Task 5. Para esta task passar, adicione um stub temporário no fim da classe:
> ```python
>     def _registrar_movimentacao_local(self, *args, **kwargs):
>         pass
> ```

- [ ] **Step 4: Rodar e verificar que passa**

Run: `pytest tests/odoo/services/test_transferencia_saldo_codigo_service.py -v`
Expected: PASS (todos).

- [ ] **Step 5: Commit**

```bash
git add -u && git commit -m "feat(estoque): transferir entre codigos (compensacao + validade replicada)"
```

---

## Task 5: `_registrar_movimentacao_local` (espelho local)

**Files:**
- Modify: `app/odoo/services/transferencia_saldo_codigo_service.py` (substitui o stub)
- Test: `tests/odoo/services/test_transferencia_saldo_codigo_service.py`

- [ ] **Step 1: Escrever o teste falho**

```python
def test_registrar_movimentacao_local(service, app):
    criados = []

    class FakeMov:
        def __init__(self):
            criados.append(self)

    fake_session = MagicMock()
    with patch('app.estoque.models.MovimentacaoEstoque', FakeMov), \
         patch('app.odoo.services.transferencia_saldo_codigo_service._get_db_session',
               return_value=fake_session):
        service._registrar_movimentacao_local(
            '4729198', 'AZEITE', '4759198', 'SOJA', '135/26', 5.0, 'rafael')

    assert len(criados) == 2
    saida, entrada = criados
    assert saida.tipo_movimentacao == 'SAIDA' and saida.cod_produto == '4729198'
    assert entrada.tipo_movimentacao == 'ENTRADA' and entrada.cod_produto == '4759198'
    assert saida.local_movimentacao == 'AJUSTE' and saida.tipo_origem == 'MANUAL'
    assert saida.lote_nome == '135/26' and saida.qtd_movimentacao == 5.0
    assert saida.criado_por == 'rafael'
    assert fake_session.add.call_count == 2
    fake_session.commit.assert_called_once()
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `pytest tests/odoo/services/test_transferencia_saldo_codigo_service.py::test_registrar_movimentacao_local -v`
Expected: FAIL (stub não cria registros / `_get_db_session` não existe).

- [ ] **Step 3: Implementar (substituir o stub) + helper de sessão**

Adicione no topo do arquivo (após `logger = ...`):

```python
def _get_db_session():
    """Acesso lazy à sessão SQLAlchemy (evita import circular app.odoo→app)."""
    from app import db
    return db.session
```

Substitua o stub `_registrar_movimentacao_local` por:

```python
    def _registrar_movimentacao_local(
        self, cod_origem, nome_origem, cod_destino, nome_destino,
        lote_nome, qty, usuario) -> None:
        """Espelha a troca no estoque local: SAIDA(origem) + ENTRADA(destino).

        AJUSTE/MANUAL — não duplica com o sync (entrada_material_service só
        importa picking_type_code='incoming'; inventory adjustment não gera).
        """
        from app.estoque.models import MovimentacaoEstoque
        from app.utils.timezone import agora_utc_naive
        hoje = agora_utc_naive().date()
        obs = (f'Transferencia saldo {cod_origem}->{cod_destino} '
               f'lote {lote_nome or "(sem lote)"} qtd {qty} (CD/Estoque Odoo)')
        session = _get_db_session()
        for cod, nome, tipo in (
            (cod_origem, nome_origem, 'SAIDA'),
            (cod_destino, nome_destino, 'ENTRADA'),
        ):
            mov = MovimentacaoEstoque()
            mov.cod_produto = cod
            mov.nome_produto = nome
            mov.tipo_movimentacao = tipo
            mov.local_movimentacao = 'AJUSTE'
            mov.qtd_movimentacao = qty
            mov.data_movimentacao = hoje
            mov.lote_nome = lote_nome
            mov.tipo_origem = 'MANUAL'
            mov.observacao = obs
            mov.criado_por = usuario
            session.add(mov)
        session.commit()
```

- [ ] **Step 4: Rodar e verificar que passa**

Run: `pytest tests/odoo/services/test_transferencia_saldo_codigo_service.py -v`
Expected: PASS (todos, incluindo `test_transferir_feliz` que agora chama o método real via mock em service).

- [ ] **Step 5: Commit**

```bash
git add -u && git commit -m "feat(estoque): espelho local MovimentacaoEstoque (SAIDA+ENTRADA AJUSTE/MANUAL)"
```

---

## Task 6: Rotas no `estoque_bp` (tela + api/lotes + api/executar)

**Files:**
- Modify: `app/estoque/routes.py` (adicionar ao FINAL do arquivo, antes de qualquer `if __name__`)

- [ ] **Step 1: Adicionar as 3 rotas**

```python
# ============================================================
# Transferência de saldo entre códigos (Odoo) — mantém lote
# ============================================================

@estoque_bp.route('/transferencia-saldo')
@login_required
def transferir_saldo_codigo():
    """Tela de transferência de saldo entre códigos (CD/Estoque, Odoo)."""
    codigo = request.args.get('codigo', '').strip()
    return render_template('estoque/transferir_saldo_odoo.html', codigo=codigo)


@estoque_bp.route('/transferencia-saldo/api/lotes')
@login_required
def api_transferencia_lotes():
    """JSON: lotes do código em CD/Estoque + códigos destino possíveis."""
    from app.odoo.services.transferencia_saldo_codigo_service import (
        TransferenciaSaldoCodigoService,
    )
    codigo = request.args.get('codigo', '').strip()
    if not codigo:
        return jsonify({'success': False, 'message': 'Informe o código'}), 400
    try:
        svc = TransferenciaSaldoCodigoService()
        produto = svc.resolver_produto(codigo)
        lotes = svc.listar_lotes_cd_estoque(codigo)
        destinos = svc.descobrir_destinos(codigo)
        return jsonify({
            'success': True, 'produto': produto,
            'lotes': lotes, 'destinos': destinos,
        })
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 200
    except Exception as e:  # noqa: BLE001
        logger.error(f'api_transferencia_lotes erro: {e}')
        return jsonify({'success': False, 'message': f'Erro ao consultar Odoo: {e}'}), 200


@estoque_bp.route('/transferencia-saldo/api/executar', methods=['POST'])
@login_required
def api_transferencia_executar():
    """Executa 1 transferência (1 lote). JSON in/out."""
    from app.odoo.services.transferencia_saldo_codigo_service import (
        TransferenciaSaldoCodigoService,
    )
    data = request.get_json(silent=True) or {}
    cod_origem = str(data.get('cod_origem', '')).strip()
    cod_destino = str(data.get('cod_destino', '')).strip()
    lote_nome = data.get('lote_nome') or None
    try:
        qty = float(data.get('qty', 0))
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'Quantidade inválida'}), 200
    if not cod_origem or not cod_destino:
        return jsonify({'success': False, 'message': 'Códigos origem e destino obrigatórios'}), 200
    if qty <= 0:
        return jsonify({'success': False, 'message': 'Quantidade deve ser > 0'}), 200
    try:
        svc = TransferenciaSaldoCodigoService()
        r = svc.transferir(cod_origem, cod_destino, lote_nome, qty, current_user.nome)
        if r['status'] == 'EXECUTADO':
            return jsonify({
                'success': True,
                'message': (f'{qty} transferida(s): {cod_origem} '
                            f'({r.get("origem_apos")}) → {cod_destino} '
                            f'({r.get("destino_apos")}), lote {lote_nome or "(sem lote)"}'),
                'resultado': r,
            })
        return jsonify({'success': False,
                        'message': f'Falha ({r["status"]}): {r.get("erro")}',
                        'resultado': r}), 200
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 200
    except Exception as e:  # noqa: BLE001
        logger.error(f'api_transferencia_executar erro: {e}')
        return jsonify({'success': False, 'message': f'Erro: {e}'}), 200
```

- [ ] **Step 2: Smoke test das rotas (cliente de teste)**

O `conftest.py` define `LOGIN_DISABLED=True` e `WTF_CSRF_ENABLED=False`, então o `client` acessa as rotas sem login nem CSRF token. Ambos os testes abaixo validam caminhos que retornam ANTES de tocar `current_user.nome` ou o service. Adicione `tests/odoo/services/test_transferencia_rotas.py`:

```python
def test_rota_lotes_sem_codigo(client):
    resp = client.get('/estoque/transferencia-saldo/api/lotes')
    assert resp.status_code == 400
    assert resp.get_json()['success'] is False


def test_rota_executar_qty_invalida(client):
    # qty<=0 é validado antes de instanciar o service / usar current_user
    resp = client.post('/estoque/transferencia-saldo/api/executar',
                       json={'cod_origem': '1', 'cod_destino': '2', 'qty': 0})
    assert resp.status_code == 200
    assert resp.get_json()['success'] is False


def test_rota_executar_sem_codigos(client):
    resp = client.post('/estoque/transferencia-saldo/api/executar',
                       json={'qty': 5})
    assert resp.get_json()['success'] is False
```

Run: `pytest tests/odoo/services/test_transferencia_rotas.py -v`
Expected: PASS (3 testes).

- [ ] **Step 3: Commit**

```bash
git add app/estoque/routes.py tests/odoo/services/test_transferencia_rotas.py
git commit -m "feat(estoque): rotas transferencia-saldo (tela + api lotes + api executar)"
```

---

## Task 7: Template + itens de menu

**Files:**
- Create: `app/templates/estoque/transferir_saldo_odoo.html`
- Modify: `app/templates/base.html` (após linha 836)
- Modify: `app/templates/_sidebar.html` (após linha 141)

- [ ] **Step 1: Criar o template**

```html
{% extends "base.html" %}
{% block title %}Transferência de Saldo entre Códigos{% endblock %}
{% block content %}
<div class="container-fluid py-3">
  <h4><i class="fas fa-right-left text-warning"></i> Transferência de Saldo entre Códigos (CD/Estoque)</h4>
  <p class="text-muted">Move saldo de um código para o código par (Unificação), mantendo o mesmo lote, em CD/Estoque (Odoo).</p>

  <div class="card mb-3">
    <div class="card-body">
      <div class="row g-2 align-items-end">
        <div class="col-md-4">
          <label class="form-label">Código (origem)</label>
          <input type="number" id="inp-codigo" class="form-control" value="{{ codigo }}" placeholder="Ex: 4729198">
        </div>
        <div class="col-md-2">
          <button id="btn-buscar" class="btn btn-primary"><i class="fas fa-search"></i> Buscar</button>
        </div>
        <div class="col-md-6">
          <label class="form-label">Transferir para (destino)</label>
          <select id="sel-destino" class="form-select" disabled></select>
        </div>
      </div>
      <div id="info-produto" class="mt-2 text-muted small"></div>
    </div>
  </div>

  <div id="alerta"></div>

  <table class="table table-sm table-hover d-none" id="tbl-lotes">
    <thead><tr>
      <th>Lote</th><th class="text-end">Saldo</th><th class="text-end">Reservado</th>
      <th class="text-end">Disponível</th><th style="width:160px">Qtd a transferir</th><th></th>
    </tr></thead>
    <tbody></tbody>
  </table>
</div>

<script>
const CSRF = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

function alerta(msg, tipo) {
  document.getElementById('alerta').innerHTML =
    `<div class="alert alert-${tipo} alert-dismissible fade show">${msg}` +
    `<button class="btn-close" data-bs-dismiss="alert"></button></div>`;
}

async function buscar() {
  const codigo = document.getElementById('inp-codigo').value.trim();
  if (!codigo) { alerta('Informe o código', 'warning'); return; }
  const tbl = document.getElementById('tbl-lotes');
  const tbody = tbl.querySelector('tbody');
  tbody.innerHTML = '<tr><td colspan="6">Consultando Odoo...</td></tr>';
  tbl.classList.remove('d-none');
  const resp = await fetch(`/estoque/transferencia-saldo/api/lotes?codigo=${encodeURIComponent(codigo)}`);
  const data = await resp.json();
  if (!data.success) { alerta(data.message, 'danger'); tbl.classList.add('d-none'); return; }

  document.getElementById('info-produto').textContent =
    `${data.produto.cod} — ${data.produto.name} (uom: ${data.produto.uom})`;

  const sel = document.getElementById('sel-destino');
  sel.innerHTML = '';
  if (!data.destinos.length) {
    sel.innerHTML = '<option value="">(sem par cadastrado)</option>'; sel.disabled = true;
    alerta('Código sem par ativo em Unificação de Códigos.', 'warning');
  } else {
    data.destinos.forEach(d => sel.add(new Option(`${d.codigo} — ${d.nome || ''}`, d.codigo)));
    sel.disabled = false;
  }

  tbody.innerHTML = '';
  data.lotes.forEach(l => {
    const tr = document.createElement('tr');
    const nome = l.lote_nome || '(sem lote)';
    const disabled = (l.disponivel <= 0 || sel.disabled) ? 'disabled' : '';
    tr.innerHTML =
      `<td>${nome}${l.is_migracao ? ' <span class="badge bg-secondary">MIGRAÇÃO</span>' : ''}</td>` +
      `<td class="text-end">${l.quantidade}</td><td class="text-end">${l.reservado}</td>` +
      `<td class="text-end fw-bold">${l.disponivel}</td>` +
      `<td><input type="number" class="form-control form-control-sm qtd" min="0" max="${l.disponivel}" step="0.001" ${disabled}></td>` +
      `<td><button class="btn btn-sm btn-success btn-transf" data-lote="${l.lote_nome ?? ''}" ${disabled}>Transferir</button></td>`;
    tbody.appendChild(tr);
  });
}

async function transferir(btn) {
  const tr = btn.closest('tr');
  const qtd = parseFloat(tr.querySelector('.qtd').value);
  const max = parseFloat(tr.querySelector('.qtd').max);
  const codDestino = document.getElementById('sel-destino').value;
  if (!qtd || qtd <= 0) { alerta('Informe a quantidade', 'warning'); return; }
  if (qtd > max) { alerta(`Máximo disponível: ${max}`, 'warning'); return; }
  if (!codDestino) { alerta('Selecione o código destino', 'warning'); return; }
  btn.disabled = true; btn.textContent = '...';
  const resp = await fetch('/estoque/transferencia-saldo/api/executar', {
    method: 'POST',
    headers: {'Content-Type': 'application/json', 'X-CSRFToken': CSRF},
    body: JSON.stringify({
      cod_origem: document.getElementById('inp-codigo').value.trim(),
      cod_destino: codDestino,
      lote_nome: btn.dataset.lote || null,
      qty: qtd,
    }),
  });
  const data = await resp.json();
  alerta(data.message, data.success ? 'success' : 'danger');
  if (data.success) buscar(); else { btn.disabled = false; btn.textContent = 'Transferir'; }
}

document.getElementById('btn-buscar').addEventListener('click', buscar);
document.getElementById('inp-codigo').addEventListener('keydown', e => { if (e.key === 'Enter') buscar(); });
document.getElementById('tbl-lotes').addEventListener('click', e => {
  if (e.target.classList.contains('btn-transf')) transferir(e.target);
});
if (document.getElementById('inp-codigo').value.trim()) buscar();
</script>
{% endblock %}
```

- [ ] **Step 2: Adicionar item no menu `base.html` (após a linha 836, antes do `<li><hr class="dropdown-divider">`)**

```html
              <li><a class="dropdown-item" href="{{ url_for('estoque.transferir_saldo_codigo') }}">
                  <i class="fas fa-right-left text-warning"></i> Transferir Saldo (Odoo)
                </a></li>
```

- [ ] **Step 3: Adicionar item no menu `_sidebar.html` (após a linha 141, antes do `<li><hr></li>`)**

```html
        <li><a class="nc-sidebar__link" href="{{ url_for('estoque.transferir_saldo_codigo') }}">
          <i class="fas fa-right-left nc-sidebar__icon"></i>
          <span class="nc-sidebar__label">Transferir Saldo (Odoo)</span></a></li>
```

- [ ] **Step 4: Verificar que a app sobe e a rota resolve**

Run: `python -c "from app import create_app; a=create_app(); print([r.rule for r in a.url_map.iter_rules() if 'transferencia-saldo' in r.rule])"`
Expected: lista com as 3 rotas.

- [ ] **Step 5: Commit**

```bash
git add app/templates/estoque/transferir_saldo_odoo.html app/templates/base.html app/templates/_sidebar.html
git commit -m "feat(estoque): tela transferir saldo (Odoo) + itens de menu"
```

---

## Task 8: Verificação manual (smoke) + checklist do spec

- [ ] **Step 1: Subir o app e testar o fluxo no navegador**

```bash
python run.py
```
Acessar `/estoque/transferencia-saldo`, digitar um código com par (ex.: `4729198`), conferir lotes/destinos, transferir uma quantidade pequena e validar no Odoo (read-back).

- [ ] **Step 2: Rodar a suíte do service**

Run: `pytest tests/odoo/services/test_transferencia_saldo_codigo_service.py tests/odoo/services/test_transferencia_rotas.py -v`
Expected: PASS.

- [ ] **Step 3: Conferir o checklist do spec (§11)**

Marcar cada item: rota registrada, link nos 2 menus, `resolver_produto` 0/>1, validade replicada, lote sempre com `company_id=4`, compensação testada, bloqueio `qty>disponível` (front+back), espelho local (2 movs), validações front+back.

- [ ] **Step 4: Commit final (se houver ajustes)**

```bash
git add -u && git commit -m "test(estoque): verificacao transferencia saldo entre codigos"
```

---

## Notas de implementação

- **Não toca o Odoo de produção nos testes** — tudo via `MagicMock`/`patch`.
- **Atomicidade**: ordem reduzir→aumentar com compensação (re-aumenta origem se aumento falhar). Pior caso = log de erro + estado revertido.
- **Validade do lote** (`use_expiration_date=True`): replicada do lote origem ao criar no destino. Se o lote já existe no destino, `criar_se_nao_existe` não sobrescreve.
- **Multi-company**: lote sempre resolvido/criado com `product_id` + `company_id=4` (nome de lote existe em 56 lotes nas 3 empresas).
- **CSRF**: header `X-CSRFToken` do `<meta name="csrf-token">` (CSRFProtect global).
- **Reuso futuro**: o service é a base da skill do `gestor-estoque-odoo` — manter sem dependência de `flask`/`request`/`current_user`.
