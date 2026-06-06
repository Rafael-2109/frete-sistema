<!-- doc:meta
tipo: how-to
camada: L3
sot_de: —
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-06
-->
# Transferência de Estoque (Odoo) — tela admin unificada — Implementation Plan

> **Papel:** plano de implementação (how-to) da tela admin de transferência de estoque Odoo em 3 modos (local→local, lote→lote, código→código).

## Indice

- [File Structure](#file-structure)
- [Task 1: Backend — transferir_v2() (Modo 3 generalizado)](#task-1-backend--transferir_v2-modo-3-generalizado)
- [Task 2: Backend — transferir() legado vira wrapper de transferir_v2](#task-2-backend--transferir-legado-vira-wrapper-de-transferir_v2)
- [Task 3: Backend — módulo de rotas + require_admin_json + tela + dados-codigo](#task-3-backend--módulo-de-rotas--require_admin_json--tela--dados-codigo)
- [Task 4: Backend — endpoints de autocomplete (produto + local)](#task-4-backend--endpoints-de-autocomplete-produto--local)
- [Task 5: Backend — endpoints simular + executar (dispatcher 3 modos)](#task-5-backend--endpoints-simular--executar-dispatcher-3-modos)
- [Task 6: Remover rotas/tela antigas (lixo)](#task-6-remover-rotastela-antigas-lixo)
- [Task 7: Frontend — template + JS](#task-7-frontend--template--js)
- [Task 8: Menu admin-only + remover template antigo](#task-8-menu-admin-only--remover-template-antigo)
- [Task 9: Verificação final](#task-9-verificação-final)
- [Self-Review](#self-review-preenchido-pelo-autor-do-plano)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Evoluir `/estoque/transferencia-saldo` para uma tela admin-only com 3 modos de transferência de estoque no Odoo (local→local, lote→lote, código→código), com painel ao vivo (A por local, B reservada, C por lote) e autocomplete.

**Architecture:** Tela Jinja + vanilla JS chama endpoints Flask (`@require_admin`/`require_admin_json`) que reusam os átomos maduros de `app/odoo/estoque/scripts/transfer.py` (Modos 1/2) e generalizam `TransferenciaSaldoCodigoService` (Modo 3, novo `transferir_v2`). Síncrono. Fluxo Simular (dry-run) → Confirmar.

**Tech Stack:** Flask, SQLAlchemy, Odoo XML-RPC (`get_odoo_connection`), Bootstrap 5, vanilla JS, pytest (Odoo mockado).

**Spec:** `docs/superpowers/specs/2026-06-06-transferencia-estoque-odoo-ui-design.md`
**Worktree:** `feat/transferencia-estoque-odoo-ui` (de `origin/main` @ `4258ca3fb`)

**Ambiente de teste (cada Bash começa assim — o shell reseta o cwd entre comandos):**
```bash
cd /home/rafaelnascimento/projetos/frete_sistema_transferencia_estoque
source /home/rafaelnascimento/projetos/frete_sistema/.venv/bin/activate
export SENTRY_DSN="" DISABLE_SENTRY=1   # silencia ruido de teardown (atexit shutdown_state)
```
Para ver só o resultado do pytest (o teardown polui stdout):
`python -m pytest <alvo> -q -p no:cacheprovider 2>/dev/null | grep -iE "passed|failed|error"`

---

## File Structure

| Arquivo | Responsabilidade |
|---------|------------------|
| `app/odoo/services/transferencia_saldo_codigo_service.py` | **modificar** — add `transferir_v2()` (genérico); `transferir()` vira wrapper |
| `app/estoque/transferencia_estoque_routes.py` | **criar** — `require_admin_json` + tela + 5 endpoints (importado por `routes.py`) |
| `app/estoque/routes.py` | **modificar** — remover rotas/tela antigas; importar o módulo novo no final |
| `app/templates/estoque/transferir_estoque_odoo.html` | **criar** — tela unificada 3 modos |
| `app/templates/estoque/transferir_saldo_odoo.html` | **remover** |
| `app/static/js/estoque/transferir_estoque.js` | **criar** — autocomplete + lógica de modo + simular/confirmar |
| `app/templates/_sidebar.html` | **modificar** — link admin-only + label + endpoint novo |
| `tests/odoo/services/test_transferencia_saldo_codigo_service.py` | **modificar** — add testes de `transferir_v2` |
| `tests/estoque/test_transferencia_estoque_routes.py` | **criar** — admin-only, dados-codigo, simular/executar |

> **Sem migrations** (sem DDL; opera Odoo + reusa `MovimentacaoEstoque`).

---

## Task 1: Backend — `transferir_v2()` (Modo 3 generalizado)

**Files:**
- Modify: `app/odoo/services/transferencia_saldo_codigo_service.py` (add método `transferir_v2`)
- Test: `tests/odoo/services/test_transferencia_saldo_codigo_service.py`

- [ ] **Step 1: Escrever os testes que falham**

Anexar ao fim de `tests/odoo/services/test_transferencia_saldo_codigo_service.py`:

```python
# ---------------------------------------------------------------------------
# transferir_v2 — genérico (empresa/local/lote parametrizáveis) + dry-run
# ---------------------------------------------------------------------------

def test_transferir_v2_feliz_lf_locais_distintos(service, odoo_mock, adj_mock, lot_mock):
    service.descobrir_destinos = MagicMock(return_value=[{'codigo': '4759198', 'nome': 'SOJA'}])
    service.resolver_produto = MagicMock(side_effect=[
        _info(27749, '4729198', 'AZEITE'), _info(27735, '4759198', 'SOJA')])
    service._registrar_movimentacao_local = MagicMock()
    lot_mock.buscar_por_nome.return_value = 56426
    odoo_mock.read.return_value = [{'expiration_date': '2028-05-15 00:00:00'}]
    lot_mock.criar_se_nao_existe.return_value = (58503, True)
    adj_mock.ajustar_quant.side_effect = [
        {'status': 'EXECUTADO', 'qty_antes': 290.0, 'qty_apos': 285.0},
        {'status': 'EXECUTADO', 'qty_antes': 0.0, 'qty_apos': 5.0},
    ]
    r = service.transferir_v2(
        company_id=5, cod_origem='4729198', location_id_origem=42,
        lote_nome_origem='135/26', cod_destino='4759198', location_id_destino=53,
        lote_nome_destino='135/26', qty=5.0, usuario='rafael', dry_run=False)
    assert r['status'] == 'EXECUTADO'
    assert r['origem_apos'] == 285.0 and r['destino_apos'] == 5.0
    assert r['lote_criado'] is True
    assert r['aviso_par'] is False
    # company/local propagados ao ajustar_quant
    red_kwargs = adj_mock.ajustar_quant.call_args_list[0].kwargs
    assert red_kwargs['company_id'] == 5 and red_kwargs['location_id'] == 42
    aum_kwargs = adj_mock.ajustar_quant.call_args_list[1].kwargs
    assert aum_kwargs['company_id'] == 5 and aum_kwargs['location_id'] == 53
    service._registrar_movimentacao_local.assert_called_once()


def test_transferir_v2_aviso_par_nao_bloqueia(service, odoo_mock, adj_mock, lot_mock):
    service.descobrir_destinos = MagicMock(return_value=[])  # nenhum par cadastrado
    service.resolver_produto = MagicMock(side_effect=[
        _info(27749, '4729198', 'AZEITE'), _info(27735, '9999', 'OUTRO')])
    service._registrar_movimentacao_local = MagicMock()
    lot_mock.buscar_por_nome.return_value = 56426
    odoo_mock.read.return_value = [{'expiration_date': False}]
    lot_mock.criar_se_nao_existe.return_value = (58503, False)
    adj_mock.ajustar_quant.side_effect = [
        {'status': 'EXECUTADO', 'qty_antes': 100.0, 'qty_apos': 90.0},
        {'status': 'EXECUTADO', 'qty_antes': 0.0, 'qty_apos': 10.0},
    ]
    r = service.transferir_v2(
        company_id=1, cod_origem='4729198', location_id_origem=8,
        lote_nome_origem='135/26', cod_destino='9999', location_id_destino=8,
        lote_nome_destino='135/26', qty=10.0, usuario='rafael', dry_run=False)
    assert r['status'] == 'EXECUTADO'
    assert r['aviso_par'] is True  # avisou, mas executou


def test_transferir_v2_dry_run_nao_escreve_nem_cria_lote(service, odoo_mock, adj_mock, lot_mock):
    service.descobrir_destinos = MagicMock(return_value=[{'codigo': '4759198', 'nome': 'SOJA'}])
    service.resolver_produto = MagicMock(side_effect=[
        _info(27749, '4729198', 'AZEITE'), _info(27735, '4759198', 'SOJA')])
    service._registrar_movimentacao_local = MagicMock()
    lot_mock.buscar_por_nome.side_effect = [56426, None]  # origem existe, destino NÃO
    odoo_mock.read.return_value = [{'expiration_date': '2028-05-15 00:00:00'}]
    adj_mock.ajustar_quant.return_value = {
        'status': 'DRY_RUN_OK', 'qty_antes': 290.0, 'qty_apos': 285.0}
    r = service.transferir_v2(
        company_id=5, cod_origem='4729198', location_id_origem=42,
        lote_nome_origem='135/26', cod_destino='4759198', location_id_destino=42,
        lote_nome_destino='135/26', qty=5.0, usuario='rafael', dry_run=True)
    assert r['status'] == 'DRY_RUN_OK'
    assert r['origem_apos'] == 285.0
    assert r['destino_antes'] == 0.0 and r['destino_apos'] == 5.0
    assert r['lote_criado'] is True  # será criado no executar
    lot_mock.criar_se_nao_existe.assert_not_called()   # NÃO cria em dry-run
    service._registrar_movimentacao_local.assert_not_called()  # NÃO espelha em dry-run
    # só 1 ajustar_quant (reduz origem dry); destino é preview manual (lote novo)
    assert adj_mock.ajustar_quant.call_count == 1


def test_transferir_v2_reducao_falha(service, odoo_mock, adj_mock, lot_mock):
    service.descobrir_destinos = MagicMock(return_value=[{'codigo': '4759198', 'nome': 'SOJA'}])
    service.resolver_produto = MagicMock(side_effect=[
        _info(27749, '4729198', 'AZEITE'), _info(27735, '4759198', 'SOJA')])
    lot_mock.buscar_por_nome.return_value = 56426
    odoo_mock.read.return_value = [{'expiration_date': False}]
    adj_mock.ajustar_quant.return_value = {'status': 'FALHA_RESERVADO', 'erro': 'reservado'}
    r = service.transferir_v2(
        company_id=1, cod_origem='4729198', location_id_origem=8,
        lote_nome_origem='135/26', cod_destino='4759198', location_id_destino=8,
        lote_nome_destino='135/26', qty=5.0, usuario='rafael', dry_run=False)
    assert r['status'] == 'FALHA_REDUCAO'
    assert adj_mock.ajustar_quant.call_count == 1
```

- [ ] **Step 2: Rodar os testes — devem falhar (método não existe)**

Run: `python -m pytest tests/odoo/services/test_transferencia_saldo_codigo_service.py -k transferir_v2 -q -p no:cacheprovider 2>/dev/null | grep -iE "passed|failed|error"`
Expected: FAIL (`AttributeError: ... has no attribute 'transferir_v2'`)

- [ ] **Step 3: Implementar `transferir_v2`**

Em `app/odoo/services/transferencia_saldo_codigo_service.py`, inserir o método ANTES de `def transferir(` (linha ~110):

```python
    def transferir_v2(
        self, *,
        company_id: int,
        cod_origem, location_id_origem: int, lote_nome_origem,
        cod_destino, location_id_destino: int, lote_nome_destino,
        qty, usuario, dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Transferência genérica de saldo entre códigos (qualquer empresa/local/lote).

        Generaliza transferir() (CD-only): parametriza company_id + locations +
        lotes origem/destino. A trava de par vira AVISO (r['aviso_par']) — NÃO
        bloqueia. dry_run=True simula (não cria lote, não grava espelho local).
        Reduz origem → cria/aumenta destino (compensa se o aumento falhar).
        """
        cod_origem, cod_destino = str(cod_origem).strip(), str(cod_destino).strip()
        qty = round(float(qty), CASAS)
        r: Dict[str, Any] = {
            'cod_origem': cod_origem, 'cod_destino': cod_destino,
            'company_id': company_id,
            'location_id_origem': location_id_origem,
            'location_id_destino': location_id_destino,
            'lote_nome_origem': lote_nome_origem,
            'lote_nome_destino': lote_nome_destino,
            'qty': qty, 'usuario': usuario, 'dry_run': dry_run,
            'lote_criado': False, 'aviso_par': False, 'status': None,
        }
        if qty <= 0:
            raise ValueError(f'qty deve ser > 0 (recebido {qty})')

        # 1. aviso de par (NÃO bloqueia — D2)
        destinos = {d['codigo'] for d in self.descobrir_destinos(cod_origem)}
        r['aviso_par'] = cod_destino not in destinos

        # 2. resolver produtos
        origem = self.resolver_produto(cod_origem)
        destino = self.resolver_produto(cod_destino)
        pid_o, pid_d = origem['product_id'], destino['product_id']

        # 3. resolver lote origem + validade (para herdar no destino)
        lot_id_origem: Optional[int] = None
        validade: Optional[str] = None
        if lote_nome_origem:
            lot_id_origem = self.lot_svc.buscar_por_nome(lote_nome_origem, pid_o, company_id)
            if not lot_id_origem:
                raise ValueError(
                    f'lote {lote_nome_origem!r} nao encontrado no produto '
                    f'{cod_origem} (company {company_id})')
            lots = self.odoo.read('stock.lot', [lot_id_origem], ['expiration_date'])
            validade = (lots[0].get('expiration_date') or None) if lots else None

        # 4. reduzir origem
        r_red = self.adjustment_svc.ajustar_quant(
            product_id=pid_o, company_id=company_id, location_id=location_id_origem,
            lot_id=lot_id_origem, delta=-qty, delta_esperado=-qty, tolerancia_delta=0.001,
            validar_nao_negativar=True, validar_nao_abaixo_reserva=True, dry_run=dry_run)
        r['reducao'] = r_red
        if r_red['status'] not in ('EXECUTADO', 'DRY_RUN_OK', 'EXECUTADO_AUTO_CORRIGIDO'):
            r['status'] = 'FALHA_REDUCAO'
            r['erro'] = r_red.get('erro')
            return r
        r['origem_antes'], r['origem_apos'] = r_red.get('qty_antes'), r_red.get('qty_apos')

        # 5. resolver/garantir lote destino no produto destino
        lot_id_destino: Optional[int] = None
        if lote_nome_destino:
            exp = validade if destino['use_expiration_date'] else None
            if dry_run:
                lot_id_destino = self.lot_svc.buscar_por_nome(lote_nome_destino, pid_d, company_id)
                r['lote_criado'] = lot_id_destino is None
            else:
                lot_id_destino, criado = self.lot_svc.criar_se_nao_existe(
                    lote_nome_destino, pid_d, company_id, expiration_date=exp)
                r['lote_criado'] = criado

        # 6. aumentar destino
        if dry_run and lote_nome_destino and lot_id_destino is None:
            # lote será criado no executar; quant nova começa em 0 → preview manual
            r['destino_antes'], r['destino_apos'] = 0.0, qty
            r['aumento'] = {'status': 'DRY_RUN_OK', 'qty_antes': 0.0,
                            'qty_apos': qty, 'acao': 'created'}
            r['status'] = 'DRY_RUN_OK'
            return r

        r_aum = self.adjustment_svc.ajustar_quant(
            product_id=pid_d, company_id=company_id, location_id=location_id_destino,
            lot_id=lot_id_destino, delta=qty, delta_esperado=qty, tolerancia_delta=0.001,
            criar_se_faltar=True, validar_nao_negativar=True,
            validar_nao_abaixo_reserva=True, dry_run=dry_run)
        r['aumento'] = r_aum
        if r_aum['status'] not in ('EXECUTADO', 'DRY_RUN_OK', 'EXECUTADO_AUTO_CORRIGIDO'):
            if not dry_run:
                comp = self.adjustment_svc.ajustar_quant(
                    product_id=pid_o, company_id=company_id, location_id=location_id_origem,
                    lot_id=lot_id_origem, delta=qty,
                    validar_nao_negativar=False, validar_nao_abaixo_reserva=False)
                r['compensacao'] = comp
            r['status'] = 'FALHA_AUMENTO_COMPENSADO'
            r['erro'] = r_aum.get('erro')
            return r
        r['destino_antes'], r['destino_apos'] = r_aum.get('qty_antes'), r_aum.get('qty_apos')

        # 7. espelho local (somente executar real — D8)
        if not dry_run:
            self._registrar_movimentacao_local(
                cod_origem, origem['name'], cod_destino, destino['name'],
                lote_nome_destino or lote_nome_origem, qty, usuario)
        r['status'] = 'DRY_RUN_OK' if dry_run else 'EXECUTADO'
        return r
```

- [ ] **Step 4: Rodar os testes — devem passar**

Run: `python -m pytest tests/odoo/services/test_transferencia_saldo_codigo_service.py -k transferir_v2 -q -p no:cacheprovider 2>/dev/null | grep -iE "passed|failed|error"`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
cd /home/rafaelnascimento/projetos/frete_sistema_transferencia_estoque
git add app/odoo/services/transferencia_saldo_codigo_service.py tests/odoo/services/test_transferencia_saldo_codigo_service.py
git commit -m "feat(estoque): transferir_v2 generico (empresa/local/lote) no TransferenciaSaldoCodigoService

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Backend — `transferir()` legado vira wrapper de `transferir_v2`

**Files:**
- Modify: `app/odoo/services/transferencia_saldo_codigo_service.py` (substituir corpo de `transferir`)
- Test: `tests/odoo/services/test_transferencia_saldo_codigo_service.py` (os 12 legados, sem alterar)

- [ ] **Step 1: Confirmar baseline legado verde antes de mexer**

Run: `python -m pytest tests/odoo/services/test_transferencia_saldo_codigo_service.py -k "transferir and not v2" -q -p no:cacheprovider 2>/dev/null | grep -iE "passed|failed|error"`
Expected: PASS (5 passed — feliz, par_invalido, qty_invalida, reducao_falha, aumento_falha_compensa)

- [ ] **Step 2: Substituir o corpo de `transferir()` por wrapper**

Em `app/odoo/services/transferencia_saldo_codigo_service.py`, substituir o método `transferir` (linhas ~110-198) inteiro por:

```python
    def transferir(self, cod_origem, cod_destino, lote_nome, qty,
                   usuario) -> Dict[str, Any]:
        """LEGADO (CD/Estoque, par obrigatório). Delega a transferir_v2.

        Mantém o contrato histórico: BLOQUEIA se cod_destino não é par em
        UnificacaoCodigos; usa CD/Estoque (company 4, loc 32) e o mesmo lote
        na origem e no destino. Callers: app/estoque/routes.py (tela legada).
        """
        cod_origem, cod_destino = str(cod_origem).strip(), str(cod_destino).strip()
        if round(float(qty), CASAS) <= 0:
            raise ValueError(f'qty deve ser > 0 (recebido {qty})')
        # trava dura legada: bloqueia par não-cadastrado
        destinos = {d['codigo'] for d in self.descobrir_destinos(cod_origem)}
        if cod_destino not in destinos:
            raise ValueError(
                f'{cod_destino} nao e par de {cod_origem} em UnificacaoCodigos ativa')
        return self.transferir_v2(
            company_id=self.CD_COMPANY_ID, cod_origem=cod_origem,
            location_id_origem=self.CD_ESTOQUE_LOC, lote_nome_origem=lote_nome,
            cod_destino=cod_destino, location_id_destino=self.CD_ESTOQUE_LOC,
            lote_nome_destino=lote_nome, qty=qty, usuario=usuario, dry_run=False)
```

> Nota: `transferir_v2` chama `descobrir_destinos` (aviso) e `resolver_produto` 2×. O wrapper chama `descobrir_destinos` 1× (bloqueio). Os mocks dos 12 testes (`MagicMock(return_value=...)` / `side_effect=[2 itens]`) suportam essa contagem — `resolver_produto` é chamado só dentro de `transferir_v2` (2×), e `ajustar_quant` mantém 1×/2×/3× conforme o cenário.

- [ ] **Step 3: Rodar TODOS os testes do service — legados + v2 verdes**

Run: `python -m pytest tests/odoo/services/test_transferencia_saldo_codigo_service.py -q -p no:cacheprovider 2>/dev/null | grep -iE "passed|failed|error"`
Expected: PASS (16 passed — 12 legados + 4 novos)

- [ ] **Step 4: Commit**

```bash
cd /home/rafaelnascimento/projetos/frete_sistema_transferencia_estoque
git add app/odoo/services/transferencia_saldo_codigo_service.py
git commit -m "refactor(estoque): transferir() legado delega a transferir_v2 (retrocompat)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Backend — módulo de rotas + `require_admin_json` + tela + `dados-codigo`

**Files:**
- Create: `app/estoque/transferencia_estoque_routes.py`
- Test: `tests/estoque/test_transferencia_estoque_routes.py`

- [ ] **Step 1: Criar o pacote de testes e escrever testes que falham**

Criar `tests/estoque/__init__.py` (vazio) e `tests/estoque/test_transferencia_estoque_routes.py`:

```python
"""Smoke HTTP da tela de transferencia de estoque: auth (admin/non-admin) + contrato JSON.

Usa o `client` do conftest (LOGIN_DISABLED + CSRF off). current_user via patch do _get_user.
Odoo mockado por patch de get_odoo_connection no modulo de rotas.
"""
from unittest.mock import MagicMock, patch


def _admin():
    u = MagicMock(); u.is_authenticated = True; u.perfil = 'administrador'
    u.id = 1; u.nome = 'Admin'; return u


def _normal():
    u = MagicMock(); u.is_authenticated = True; u.perfil = 'vendedor'
    u.id = 2; u.nome = 'Vendedor'; return u


def test_tela_admin_200(client):
    with patch('flask_login.utils._get_user', return_value=_admin()):
        resp = client.get('/estoque/transferencia-estoque')
    assert resp.status_code == 200


def test_tela_non_admin_redirect(client):
    with patch('flask_login.utils._get_user', return_value=_normal()):
        resp = client.get('/estoque/transferencia-estoque')
    assert resp.status_code == 302  # require_admin redireciona


def test_dados_codigo_non_admin_403(client):
    with patch('flask_login.utils._get_user', return_value=_normal()):
        resp = client.get('/estoque/transferencia-estoque/api/dados-codigo?codigo=1&empresa=FB')
    assert resp.status_code == 403


def test_dados_codigo_agrupa_por_local_e_lote(client):
    fake_quants = {'total_quants': 3, 'quants': [
        {'id': 1, 'cod': '4729098', 'product_name': 'AZEITE', 'tracking': 'lot',
         'pid': 100, 'company_id': 4, 'empresa': 'CD', 'location_id': 32,
         'location_name': 'CD/Estoque', 'lot_id': 56426, 'lote': '139/26',
         'quantity': 800.0, 'reserved_quantity': 200.0, 'available': 600.0},
        {'id': 2, 'cod': '4729098', 'product_name': 'AZEITE', 'tracking': 'lot',
         'pid': 100, 'company_id': 4, 'empresa': 'CD', 'location_id': 32,
         'location_name': 'CD/Estoque', 'lot_id': 56427, 'lote': '140/26',
         'quantity': 400.0, 'reserved_quantity': 0.0, 'available': 400.0},
        {'id': 3, 'cod': '4729098', 'product_name': 'AZEITE', 'tracking': 'lot',
         'pid': 100, 'company_id': 4, 'empresa': 'CD', 'location_id': 31090,
         'location_name': 'CD/Indisponivel', 'lot_id': 30856, 'lote': 'MIGRAÇÃO',
         'quantity': 50.0, 'reserved_quantity': 0.0, 'available': 50.0},
    ]}
    svc = MagicMock(); svc.listar_quants.return_value = fake_quants
    with patch('flask_login.utils._get_user', return_value=_admin()), \
         patch('app.estoque.transferencia_estoque_routes.get_odoo_connection', return_value=MagicMock()), \
         patch('app.estoque.transferencia_estoque_routes.StockQuantQueryService', return_value=svc):
        resp = client.get('/estoque/transferencia-estoque/api/dados-codigo?codigo=4729098&empresa=CD')
    assert resp.status_code == 200
    d = resp.get_json()
    assert d['success'] is True
    assert d['produto']['cod'] == '4729098'
    locais = {l['location_name']: l for l in d['por_local']}
    assert locais['CD/Estoque']['qty'] == 1200.0
    assert locais['CD/Estoque']['disponivel'] == 1000.0
    assert locais['CD/Indisponivel']['is_indisp'] is True
    lotes = {l['lote']: l for l in d['por_lote']}
    assert lotes['MIGRAÇÃO']['is_migracao'] is True
    assert d['reservada_total'] == 200.0
```

- [ ] **Step 2: Rodar — devem falhar (rota não existe → 404)**

Run: `python -m pytest tests/estoque/test_transferencia_estoque_routes.py -q -p no:cacheprovider 2>/dev/null | grep -iE "passed|failed|error"`
Expected: FAIL (404 nas rotas)

- [ ] **Step 3: Criar `app/estoque/transferencia_estoque_routes.py`**

```python
"""Rotas da tela admin de Transferência de Estoque (Odoo) — 3 modos.

Tela em /estoque/transferencia-estoque. Reusa os átomos maduros de
app/odoo/estoque/scripts/transfer.py (Modos 1/2) e transferir_v2 do
TransferenciaSaldoCodigoService (Modo 3). Síncrono + Simular(dry-run)/Confirmar.

Spec: docs/superpowers/specs/2026-06-06-transferencia-estoque-odoo-ui-design.md
"""
import logging
from functools import wraps

from flask import render_template, request, jsonify
from flask_login import login_required, current_user

from app.estoque import estoque_bp
from app.utils.auth_decorators import require_admin
from app.odoo.constants.locations import LOCAIS_INDISPONIVEL
from app.odoo.estoque._utils import EMPRESAS, resolver_empresa, resolver_produto
from app.odoo.utils.connection import get_odoo_connection
from app.odoo.estoque.scripts.consulta_quant import StockQuantQueryService

logger = logging.getLogger(__name__)

_LOCAIS_INDISP = set(LOCAIS_INDISPONIVEL.values())


def require_admin_json(f):
    """Admin-only para endpoints JSON: 403 em vez de redirect."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or current_user.perfil != 'administrador':
            return jsonify({'success': False,
                            'message': 'Acesso restrito a administradores'}), 403
        return f(*args, **kwargs)
    return wrapper


@estoque_bp.route('/transferencia-estoque')
@login_required
@require_admin
def transferencia_estoque():
    """Tela unificada de transferência de estoque (3 modos)."""
    return render_template('estoque/transferir_estoque_odoo.html',
                           empresas=list(EMPRESAS))


@estoque_bp.route('/transferencia-estoque/api/dados-codigo')
@login_required
@require_admin_json
def api_te_dados_codigo():
    """A (por local) + B (reservada) + C (por lote) do código origem na empresa."""
    codigo = (request.args.get('codigo') or '').strip()
    empresa = (request.args.get('empresa') or '').strip().upper()
    if not codigo or not empresa:
        return jsonify({'success': False, 'message': 'Informe codigo e empresa'}), 200
    try:
        odoo = get_odoo_connection()
        res = StockQuantQueryService(odoo).listar_quants(cods=[codigo], empresas=[empresa])
        quants = res['quants']
        if not quants:
            return jsonify({'success': True, 'produto': None, 'por_local': [],
                            'por_lote': [], 'reservada_total': 0.0,
                            'message': 'Sem saldo para este codigo/empresa'})
        produto = {'cod': quants[0]['cod'], 'name': quants[0]['product_name'],
                   'tracking': quants[0]['tracking']}
        por_local, por_lote, reservada_total = {}, {}, 0.0
        for q in quants:
            reservada_total += q['reserved_quantity']
            lk = q['location_id']
            loc = por_local.setdefault(lk, {
                'location_id': lk, 'location_name': q['location_name'],
                'qty': 0.0, 'reservada': 0.0, 'disponivel': 0.0,
                'is_indisp': lk in _LOCAIS_INDISP})
            loc['qty'] += q['quantity']; loc['reservada'] += q['reserved_quantity']
            loc['disponivel'] += q['available']
            lote = q['lote'] or '(sem lote)'
            kk = (lote, q['lot_id'])
            lt = por_lote.setdefault(kk, {
                'lote': lote, 'lot_id': q['lot_id'], 'qty': 0.0,
                'reservada': 0.0, 'disponivel': 0.0,
                'is_migracao': 'MIGRA' in lote.upper()})
            lt['qty'] += q['quantity']; lt['reservada'] += q['reserved_quantity']
            lt['disponivel'] += q['available']
        _round = lambda d, ks: {**d, **{k: round(d[k], 6) for k in ks}}
        ks = ('qty', 'reservada', 'disponivel')
        return jsonify({
            'success': True, 'produto': produto,
            'por_local': [_round(v, ks) for v in por_local.values()],
            'por_lote': [_round(v, ks) for v in por_lote.values()],
            'reservada_total': round(reservada_total, 6)})
    except Exception as e:  # noqa: BLE001
        logger.error(f'api_te_dados_codigo erro: {e}')
        return jsonify({'success': False, 'message': f'Erro ao consultar Odoo: {e}'}), 200
```

- [ ] **Step 4: Registrar o módulo no blueprint (temporário, p/ os testes desta task)**

No FINAL de `app/estoque/routes.py`, adicionar:

```python
# Rotas da tela admin de Transferência de Estoque (3 modos) — registra ao importar
from app.estoque import transferencia_estoque_routes  # noqa: E402,F401
```

- [ ] **Step 5: Rodar — devem passar**

Run: `python -m pytest tests/estoque/test_transferencia_estoque_routes.py -q -p no:cacheprovider 2>/dev/null | grep -iE "passed|failed|error"`
Expected: PASS (4 passed)

- [ ] **Step 6: Commit**

```bash
cd /home/rafaelnascimento/projetos/frete_sistema_transferencia_estoque
git add app/estoque/transferencia_estoque_routes.py app/estoque/routes.py tests/estoque/__init__.py tests/estoque/test_transferencia_estoque_routes.py
git commit -m "feat(estoque): rotas tela transferencia estoque (require_admin_json + dados-codigo)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Backend — endpoints de autocomplete (produto + local)

**Files:**
- Modify: `app/estoque/transferencia_estoque_routes.py` (add 2 endpoints)
- Test: `tests/estoque/test_transferencia_estoque_routes.py` (add testes)

- [ ] **Step 1: Escrever testes que falham**

Anexar a `tests/estoque/test_transferencia_estoque_routes.py`:

```python
def test_autocomplete_produto_filtra_min_chars(client):
    with patch('flask_login.utils._get_user', return_value=_admin()):
        resp = client.get('/estoque/transferencia-estoque/api/autocomplete/produto?q=a')
    assert resp.status_code == 200
    assert resp.get_json() == []  # < 2 chars


def test_autocomplete_produto_ok(client):
    odoo = MagicMock()
    odoo.search_read.return_value = [
        {'id': 100, 'default_code': '4729098', 'name': 'AZEITE', 'tracking': 'lot'},
        {'id': 101, 'default_code': None, 'name': 'SEM CODIGO', 'tracking': 'none'},
    ]
    with patch('flask_login.utils._get_user', return_value=_admin()), \
         patch('app.estoque.transferencia_estoque_routes.get_odoo_connection', return_value=odoo):
        resp = client.get('/estoque/transferencia-estoque/api/autocomplete/produto?q=azeite')
    out = resp.get_json()
    assert len(out) == 1  # sem default_code é descartado
    assert out[0]['cod'] == '4729098' and out[0]['product_id'] == 100
    assert out[0]['label'].startswith('4729098')


def test_autocomplete_local_por_empresa(client):
    odoo = MagicMock()
    odoo.search_read.return_value = [
        {'id': 32, 'complete_name': 'CD/Estoque'},
        {'id': 31090, 'complete_name': 'CD/Indisponivel'},
    ]
    with patch('flask_login.utils._get_user', return_value=_admin()), \
         patch('app.estoque.transferencia_estoque_routes.get_odoo_connection', return_value=odoo):
        resp = client.get('/estoque/transferencia-estoque/api/autocomplete/local?q=cd&empresa=CD')
    out = resp.get_json()
    assert {o['location_id'] for o in out} == {32, 31090}
    # domain usou company_id da empresa CD (4)
    domain = odoo.search_read.call_args[0][1]
    assert ['company_id', '=', 4] in domain


def test_autocomplete_local_empresa_invalida(client):
    with patch('flask_login.utils._get_user', return_value=_admin()):
        resp = client.get('/estoque/transferencia-estoque/api/autocomplete/local?q=x&empresa=ZZ')
    assert resp.status_code == 200 and resp.get_json() == []
```

- [ ] **Step 2: Rodar — falham (404)**

Run: `python -m pytest tests/estoque/test_transferencia_estoque_routes.py -k autocomplete -q -p no:cacheprovider 2>/dev/null | grep -iE "passed|failed|error"`
Expected: FAIL

- [ ] **Step 3: Implementar os 2 endpoints**

Anexar a `app/estoque/transferencia_estoque_routes.py`:

```python
@estoque_bp.route('/transferencia-estoque/api/autocomplete/produto')
@login_required
@require_admin_json
def api_te_ac_produto():
    """Autocomplete de produto por default_code OU name (ilike). Min 2 chars."""
    q = (request.args.get('q') or '').strip()
    if len(q) < 2:
        return jsonify([])
    try:
        odoo = get_odoo_connection()
        rows = odoo.search_read(
            'product.product',
            ['&', ['active', '=', True], '|',
             ['default_code', 'ilike', q], ['name', 'ilike', q]],
            ['id', 'default_code', 'name', 'tracking'], limit=20)
        out = [{'product_id': r['id'], 'cod': r['default_code'],
                'name': r['name'], 'tracking': r.get('tracking') or 'none',
                'label': f"{r['default_code']} — {r['name']}"}
               for r in rows if r.get('default_code')]
        return jsonify(out)
    except Exception as e:  # noqa: BLE001
        logger.error(f'api_te_ac_produto erro: {e}')
        return jsonify([])


@estoque_bp.route('/transferencia-estoque/api/autocomplete/local')
@login_required
@require_admin_json
def api_te_ac_local():
    """Autocomplete de stock.location internas da empresa (ilike complete_name)."""
    q = (request.args.get('q') or '').strip()
    empresa = (request.args.get('empresa') or '').strip().upper()
    try:
        info = resolver_empresa(empresa)
    except ValueError:
        return jsonify([])
    try:
        odoo = get_odoo_connection()
        domain = [['company_id', '=', info['company_id']],
                  ['usage', '=', 'internal'], ['active', '=', True]]
        if q:
            domain.append(['complete_name', 'ilike', q])
        rows = odoo.search_read('stock.location', domain,
                                ['id', 'complete_name'], limit=30)
        return jsonify([{'location_id': r['id'], 'complete_name': r['complete_name'],
                         'label': r['complete_name']} for r in rows])
    except Exception as e:  # noqa: BLE001
        logger.error(f'api_te_ac_local erro: {e}')
        return jsonify([])
```

> Domain produto: `['&', active, '|', code, name]` = `active AND (code OR name)` (prefix notation Odoo).

- [ ] **Step 4: Rodar — passam**

Run: `python -m pytest tests/estoque/test_transferencia_estoque_routes.py -k autocomplete -q -p no:cacheprovider 2>/dev/null | grep -iE "passed|failed|error"`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
cd /home/rafaelnascimento/projetos/frete_sistema_transferencia_estoque
git add app/estoque/transferencia_estoque_routes.py tests/estoque/test_transferencia_estoque_routes.py
git commit -m "feat(estoque): endpoints autocomplete produto + local

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Backend — endpoints `simular` + `executar` (dispatcher 3 modos)

**Files:**
- Modify: `app/estoque/transferencia_estoque_routes.py` (dispatcher + 2 rotas + formatadores)
- Test: `tests/estoque/test_transferencia_estoque_routes.py` (add testes)

- [ ] **Step 1: Escrever testes que falham**

Anexar a `tests/estoque/test_transferencia_estoque_routes.py`:

```python
def test_simular_modo3_propaga_dry_run(client):
    """Simular (modo 3) chama transferir_v2 com dry_run=True e retorna preview."""
    svc3 = MagicMock()
    svc3.transferir_v2.return_value = {
        'status': 'DRY_RUN_OK', 'origem_antes': 800.0, 'origem_apos': 700.0,
        'destino_antes': 0.0, 'destino_apos': 100.0, 'lote_criado': True,
        'aviso_par': True}
    payload = {'modo': '3', 'empresa': 'CD', 'cod_origem': '4729098',
               'cod_destino': '4759098', 'lote_nome_origem': '139/26',
               'lote_nome_destino': '139/26', 'location_id_origem': 32,
               'location_id_destino': 32, 'qty': 100}
    with patch('flask_login.utils._get_user', return_value=_admin()), \
         patch('app.estoque.transferencia_estoque_routes.get_odoo_connection', return_value=MagicMock()), \
         patch('app.estoque.transferencia_estoque_routes.TransferenciaSaldoCodigoService', return_value=svc3):
        resp = client.post('/estoque/transferencia-estoque/api/simular', json=payload)
    assert resp.status_code == 200
    d = resp.get_json()
    assert d['success'] is True and d['aviso_par'] is True
    assert d['preview']['destino']['lote_criado'] is True
    assert svc3.transferir_v2.call_args.kwargs['dry_run'] is True
    assert svc3.transferir_v2.call_args.kwargs['company_id'] == 4


def test_executar_modo1_chama_transferir_entre_locations(client):
    """Executar (modo 1) resolve produto/lote e chama o átomo com dry_run=False."""
    svc1 = MagicMock()
    svc1.transferir_entre_locations.return_value = {
        'status': 'EXECUTADO',
        'reducao_origem': {'qty_antes': 500.0, 'qty_apos': 400.0},
        'aumento_destino': {'qty_antes': 0.0, 'qty_apos': 100.0}}
    payload = {'modo': '1', 'empresa': 'FB', 'cod_origem': '4729098',
               'lote_nome': '139/26', 'location_id_origem': 8,
               'location_id_destino': 4066, 'qty': 100}
    with patch('flask_login.utils._get_user', return_value=_admin()), \
         patch('app.estoque.transferencia_estoque_routes.get_odoo_connection', return_value=MagicMock()), \
         patch('app.estoque.transferencia_estoque_routes.resolver_produto',
               return_value={'pid': 100, 'tracking': 'lot', 'name': 'AZEITE'}), \
         patch('app.estoque.transferencia_estoque_routes.StockLotService') as LotCls, \
         patch('app.estoque.transferencia_estoque_routes.StockInternalTransferService', return_value=svc1):
        LotCls.return_value.buscar_por_nome.return_value = 56426
        resp = client.post('/estoque/transferencia-estoque/api/executar', json=payload)
    assert resp.status_code == 200
    d = resp.get_json()
    assert d['success'] is True
    kw = svc1.transferir_entre_locations.call_args.kwargs
    assert kw['dry_run'] is False and kw['company_id'] == 1
    assert kw['location_id_origem'] == 8 and kw['location_id_destino'] == 4066
    assert kw['lot_id'] == 56426


def test_executar_non_admin_403(client):
    with patch('flask_login.utils._get_user', return_value=_normal()):
        resp = client.post('/estoque/transferencia-estoque/api/executar', json={'modo': '1'})
    assert resp.status_code == 403


def test_simular_qty_invalida(client):
    with patch('flask_login.utils._get_user', return_value=_admin()):
        resp = client.post('/estoque/transferencia-estoque/api/simular',
                           json={'modo': '1', 'empresa': 'FB', 'cod_origem': '1', 'qty': 0})
    assert resp.status_code == 200
    assert resp.get_json()['success'] is False
```

- [ ] **Step 2: Rodar — falham (404)**

Run: `python -m pytest tests/estoque/test_transferencia_estoque_routes.py -k "simular or executar" -q -p no:cacheprovider 2>/dev/null | grep -iE "passed|failed|error"`
Expected: FAIL

- [ ] **Step 3: Implementar dispatcher + formatadores + rotas**

Anexar a `app/estoque/transferencia_estoque_routes.py` (imports lazy dentro do dispatcher para evitar circular import):

```python
def _fmt_origem(qa, qp, cod, lote):
    return {'label': f"{cod} / {lote or '(sem lote)'}", 'antes': qa, 'apos': qp}


def _fmt_destino(qa, qp, cod, lote, lote_criado=False):
    return {'label': f"{cod} / {lote or '(sem lote)'}", 'antes': qa, 'apos': qp,
            'lote_criado': lote_criado}


def _fmt_atomo12(r, cod, lote_o, lote_d, lote_criado=False):
    """Resultado de transferir_entre_locations/lotes_v2 → contrato de UI."""
    red = r.get('reducao_origem') or {}
    aum = r.get('aumento_destino') or {}
    ok = r['status'] in ('EXECUTADO', 'DRY_RUN_OK')
    return {
        'success': ok, 'status': r['status'], 'aviso_par': False,
        'preview': {
            'origem': _fmt_origem(red.get('qty_antes'), red.get('qty_apos'), cod, lote_o),
            'destino': _fmt_destino(aum.get('qty_antes'), aum.get('qty_apos'),
                                    cod, lote_d, lote_criado)},
        'message': r['status'] if ok else f"Falha: {r.get('erro') or r['status']}",
        'resultado': r}


def _fmt_v2(r):
    """Resultado de transferir_v2 (Modo 3) → contrato de UI."""
    ok = r['status'] in ('EXECUTADO', 'DRY_RUN_OK')
    return {
        'success': ok, 'status': r['status'], 'aviso_par': r.get('aviso_par', False),
        'preview': {
            'origem': _fmt_origem(r.get('origem_antes'), r.get('origem_apos'),
                                  r['cod_origem'], r.get('lote_nome_origem')),
            'destino': _fmt_destino(r.get('destino_antes'), r.get('destino_apos'),
                                    r['cod_destino'], r.get('lote_nome_destino'),
                                    r.get('lote_criado', False))},
        'message': r['status'] if ok else f"Falha: {r.get('erro') or r['status']}",
        'resultado': r}


def _despachar_transferencia(data, dry_run, usuario):
    """Dispatcher dos 3 modos. Levanta ValueError em erro de uso/dado."""
    from app.odoo.services.stock_lot_service import StockLotService
    from app.odoo.estoque.scripts.transfer import StockInternalTransferService
    from app.odoo.services.transferencia_saldo_codigo_service import (
        TransferenciaSaldoCodigoService)

    modo = str(data.get('modo'))
    empresa = (data.get('empresa') or '').strip().upper()
    cod_origem = str(data.get('cod_origem') or '').strip()
    qty = float(data.get('qty') or 0)
    if qty <= 0:
        raise ValueError('Quantidade deve ser > 0')
    company_id = resolver_empresa(empresa)['company_id']
    odoo = get_odoo_connection()
    lot_svc = StockLotService(odoo=odoo)

    if modo == '1':  # local -> local (mesmo código, mesmo lote)
        prod = resolver_produto(odoo, cod_origem)
        if not prod:
            raise ValueError(f'Codigo {cod_origem} nao encontrado')
        lote = (data.get('lote_nome') or '').strip() or None
        lot_id = lot_svc.buscar_por_nome(lote, prod['pid'], company_id) if lote else None
        if lote and not lot_id:
            raise ValueError(f'Lote {lote} nao encontrado no produto/empresa')
        svc = StockInternalTransferService(odoo=odoo, lot_svc=lot_svc)
        r = svc.transferir_entre_locations(
            product_id=prod['pid'], company_id=company_id, lot_id=lot_id, qty=qty,
            location_id_origem=int(data['location_id_origem']),
            location_id_destino=int(data['location_id_destino']), dry_run=dry_run)
        return _fmt_atomo12(r, cod_origem, lote, lote)

    if modo == '2':  # lote -> lote (mesmo código, mesmo local)
        prod = resolver_produto(odoo, cod_origem)
        if not prod:
            raise ValueError(f'Codigo {cod_origem} nao encontrado')
        loc_id = int(data['location_id'])
        lote_o = (data.get('lote_nome_origem') or '').strip() or None
        lote_d = (data.get('lote_nome_destino') or '').strip()
        if not lote_d:
            raise ValueError('Lote destino obrigatorio')
        lot_o = lot_svc.buscar_por_nome(lote_o, prod['pid'], company_id) if lote_o else None
        if lote_o and not lot_o:
            raise ValueError(f'Lote origem {lote_o} nao encontrado')
        lot_d = lot_svc.buscar_por_nome(lote_d, prod['pid'], company_id)
        # dry-run com lote destino novo: preview manual (não cria lote)
        if dry_run and lot_d is None:
            from app.odoo.services.stock_quant_adjustment_service import (
                StockQuantAdjustmentService)
            adj = StockQuantAdjustmentService(odoo=odoo, lot_svc=lot_svc)
            r_red = adj.ajustar_quant(
                product_id=prod['pid'], company_id=company_id, location_id=loc_id,
                lot_id=lot_o, delta=-qty, delta_esperado=-qty, tolerancia_delta=0.001,
                dry_run=True)
            return _fmt_atomo12({
                'status': r_red['status'] if r_red['status'] != 'DRY_RUN_OK' else 'DRY_RUN_OK',
                'reducao_origem': r_red,
                'aumento_destino': {'qty_antes': 0.0, 'qty_apos': qty}},
                cod_origem, lote_o, lote_d, lote_criado=True)
        lote_criado = False
        if lot_d is None:  # executar real → cria
            lot_d, lote_criado = lot_svc.criar_se_nao_existe(lote_d, prod['pid'], company_id)
        svc = StockInternalTransferService(odoo=odoo, lot_svc=lot_svc)
        r = svc.transferir_entre_lotes_v2(
            product_id=prod['pid'], company_id=company_id, location_id=loc_id, qty=qty,
            lot_id_origem=lot_o, lot_id_destino=lot_d, dry_run=dry_run)
        return _fmt_atomo12(r, cod_origem, lote_o, lote_d, lote_criado=lote_criado)

    if modo == '3':  # código -> código
        cod_destino = str(data.get('cod_destino') or '').strip()
        if not cod_destino:
            raise ValueError('Codigo destino obrigatorio')
        svc3 = TransferenciaSaldoCodigoService(odoo=odoo, lot_svc=lot_svc)
        r = svc3.transferir_v2(
            company_id=company_id, cod_origem=cod_origem,
            location_id_origem=int(data['location_id_origem']),
            lote_nome_origem=(data.get('lote_nome_origem') or '').strip() or None,
            cod_destino=cod_destino,
            location_id_destino=int(data['location_id_destino']),
            lote_nome_destino=(data.get('lote_nome_destino') or '').strip() or None,
            qty=qty, usuario=usuario, dry_run=dry_run)
        return _fmt_v2(r)

    raise ValueError(f'Modo invalido: {modo}')


@estoque_bp.route('/transferencia-estoque/api/simular', methods=['POST'])
@login_required
@require_admin_json
def api_te_simular():
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(_despachar_transferencia(data, dry_run=True, usuario=current_user.nome))
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 200
    except Exception as e:  # noqa: BLE001
        logger.error(f'api_te_simular erro: {e}')
        return jsonify({'success': False, 'message': f'Erro: {e}'}), 200


@estoque_bp.route('/transferencia-estoque/api/executar', methods=['POST'])
@login_required
@require_admin_json
def api_te_executar():
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(_despachar_transferencia(data, dry_run=False, usuario=current_user.nome))
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 200
    except Exception as e:  # noqa: BLE001
        logger.error(f'api_te_executar erro: {e}')
        return jsonify({'success': False, 'message': f'Erro: {e}'}), 200
```

Adicionar os imports de `StockLotService`, `StockInternalTransferService`, `TransferenciaSaldoCodigoService`, `StockQuantAdjustmentService` ao **topo** do módulo também (além do lazy no dispatcher) — necessário para os `patch(...)` dos testes resolverem o nome no namespace do módulo. No topo, após os imports existentes:

```python
from app.odoo.services.stock_lot_service import StockLotService
from app.odoo.estoque.scripts.transfer import StockInternalTransferService
from app.odoo.services.transferencia_saldo_codigo_service import TransferenciaSaldoCodigoService
```

E remover as reimportações locais correspondentes dentro de `_despachar_transferencia` (manter só `StockQuantAdjustmentService` lazy, pois só é usado no caminho raro do Modo 2 dry-run-lote-novo).

> **Por que imports no topo:** os testes fazem `patch('app.estoque.transferencia_estoque_routes.StockInternalTransferService', ...)`. O patch substitui o nome **no namespace do módulo**, então o nome precisa existir lá (import top-level). Imports do Odoo são seguros no topo aqui porque este módulo só é importado quando o blueprint carrega (não há ciclo com `app.odoo`).

- [ ] **Step 4: Rodar — passam**

Run: `python -m pytest tests/estoque/test_transferencia_estoque_routes.py -q -p no:cacheprovider 2>/dev/null | grep -iE "passed|failed|error"`
Expected: PASS (12 passed — 4 dados-codigo/auth + 4 autocomplete + 4 simular/executar)

- [ ] **Step 5: Commit**

```bash
cd /home/rafaelnascimento/projetos/frete_sistema_transferencia_estoque
git add app/estoque/transferencia_estoque_routes.py tests/estoque/test_transferencia_estoque_routes.py
git commit -m "feat(estoque): endpoints simular/executar dispatcher 3 modos

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Remover rotas/tela antigas (lixo)

**Files:**
- Modify: `app/estoque/routes.py` (remover bloco antigo)

- [ ] **Step 1: Remover o bloco antigo de transferência-saldo**

Em `app/estoque/routes.py`, remover as 3 rotas antigas (o bloco do comentário `# Transferência de saldo entre códigos (Odoo) — mantém lote` até o fim de `api_transferencia_executar`, linhas ~2151-2226): `transferir_saldo_codigo`, `api_transferencia_lotes`, `api_transferencia_executar`. Manter a linha de import do módulo novo (adicionada na Task 3 Step 4).

- [ ] **Step 2: Verificar que nada mais referencia as rotas removidas**

Run:
```bash
cd /home/rafaelnascimento/projetos/frete_sistema_transferencia_estoque
grep -rn "transferir_saldo_codigo\|api_transferencia_lotes\|api_transferencia_executar\|transferencia-saldo/api" app/ tests/ | grep -v "transferencia_estoque_routes\|test_transferencia_saldo_codigo_service"
```
Expected: só restará o link no `_sidebar.html:152` (tratado na Task 8). Nenhuma outra referência de código.

- [ ] **Step 3: Smoke — app sobe e rotas novas registradas**

Run:
```bash
cd /home/rafaelnascimento/projetos/frete_sistema_transferencia_estoque
python -c "from app import create_app; a=create_app(); print([r.rule for r in a.url_map.iter_rules() if 'transferencia-estoque' in r.rule])" 2>/dev/null | tail -1
```
Expected: lista com as 6 rotas (`/estoque/transferencia-estoque` + 5 `/api/...`)

- [ ] **Step 4: Commit**

```bash
cd /home/rafaelnascimento/projetos/frete_sistema_transferencia_estoque
git add app/estoque/routes.py
git commit -m "chore(estoque): remove rotas/tela antigas de transferencia-saldo (substituidas)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: Frontend — template + JS

**Files:**
- Create: `app/templates/estoque/transferir_estoque_odoo.html`
- Create: `app/static/js/estoque/transferir_estoque.js`

- [ ] **Step 1: Criar o template**

`app/templates/estoque/transferir_estoque_odoo.html`:

```html
{% extends "base.html" %}
{% block title %}Transferência de Estoque (Odoo){% endblock %}
{% block content %}
<div class="container-fluid py-3" id="te-app">
  <h4><i class="fas fa-right-left text-warning"></i> Transferência de Estoque (Odoo)
    <span class="badge bg-danger">admin</span></h4>
  <p class="text-muted">Transfere saldo dentro da mesma empresa (não emite NF). Simule antes de confirmar.</p>

  <div class="card mb-3"><div class="card-body">
    <div class="row g-2 align-items-end">
      <div class="col-md-2">
        <label class="form-label">Empresa</label>
        <select id="te-empresa" class="form-select">
          {% for e in empresas %}<option value="{{ e }}">{{ e }}</option>{% endfor %}
        </select>
      </div>
      <div class="col-md-4">
        <label class="form-label">Modo</label>
        <select id="te-modo" class="form-select">
          <option value="1">1 · Local → Local</option>
          <option value="2">2 · Lote → Lote</option>
          <option value="3" selected>3 · Código → Código</option>
        </select>
      </div>
      <div class="col-md-6">
        <label class="form-label">Código origem</label>
        <input type="text" id="te-cod-origem" class="form-control" autocomplete="off"
               placeholder="código ou nome (autocomplete)">
        <input type="hidden" id="te-cod-origem-val">
        <div id="te-prod-origem-info" class="form-text"></div>
      </div>
    </div>
  </div></div>

  <div id="te-alerta"></div>

  <div class="card mb-3 d-none" id="te-painel"><div class="card-body">
    <h6 class="text-muted">Situação do código origem (ao vivo)</h6>
    <div class="row">
      <div class="col-md-6">
        <strong>A · Por Local</strong> &middot; <small>B · reservada</small>
        <table class="table table-sm"><thead><tr>
          <th>Local</th><th class="text-end">Qtd</th><th class="text-end">Reserv.</th>
          <th class="text-end">Disp.</th></tr></thead>
          <tbody id="te-tbl-local"></tbody></table>
      </div>
      <div class="col-md-6">
        <strong>C · Por Lote</strong>
        <table class="table table-sm"><thead><tr>
          <th>Lote</th><th class="text-end">Qtd</th><th class="text-end">Reserv.</th>
          <th class="text-end">Disp.</th></tr></thead>
          <tbody id="te-tbl-lote"></tbody></table>
      </div>
    </div>
  </div></div>

  <div class="card mb-3 d-none" id="te-form"><div class="card-body">
    <h6 id="te-form-titulo" class="text-muted"></h6>
    <div class="row g-2 align-items-end" id="te-campos"></div>
    <div class="mt-3">
      <button id="te-btn-simular" class="btn btn-primary">
        <i class="fas fa-flask"></i> Simular</button>
    </div>
  </div></div>

  <div class="card mb-3 d-none border-success" id="te-preview"><div class="card-body">
    <h6 class="text-success"><i class="fas fa-eye"></i> Preview da transferência</h6>
    <div id="te-preview-body"></div>
    <div class="mt-3">
      <button id="te-btn-confirmar" class="btn btn-success">
        <i class="fas fa-check"></i> Confirmar</button>
      <button id="te-btn-cancelar" class="btn btn-outline-secondary">Cancelar</button>
    </div>
  </div></div>
</div>
<script src="{{ url_for('static', filename='js/estoque/transferir_estoque.js') }}"></script>
{% endblock %}
```

- [ ] **Step 2: Criar o JS**

`app/static/js/estoque/transferir_estoque.js` — autocomplete vanilla + lógica de modo + simular/confirmar:

```javascript
/* Transferência de Estoque (Odoo) — 3 modos. Vanilla JS, sem libs externas. */
(function () {
  'use strict';
  const CSRF = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
  const $ = (id) => document.getElementById(id);
  const BASE = '/estoque/transferencia-estoque';
  let dados = null;        // resposta de /api/dados-codigo
  let ultimoPayload = null;

  function alerta(msg, tipo) {
    $('te-alerta').innerHTML =
      `<div class="alert alert-${tipo} alert-dismissible fade show">${msg}` +
      `<button class="btn-close" data-bs-dismiss="alert"></button></div>`;
  }
  function num(v) { return (v === null || v === undefined) ? '-' : Number(v).toLocaleString('pt-BR'); }

  /* ---------- autocomplete genérico ---------- */
  function autocomplete(input, urlFn, onPick) {
    const dd = document.createElement('div');
    dd.className = 'list-group position-absolute shadow';
    dd.style.cssText = 'z-index:1080;max-height:260px;overflow:auto;display:none;min-width:260px;';
    input.parentNode.style.position = 'relative';
    input.parentNode.appendChild(dd);
    let t;
    function hide() { dd.style.display = 'none'; }
    input.addEventListener('input', () => {
      clearTimeout(t);
      const q = input.value.trim();
      if (q.length < 2) { hide(); return; }
      t = setTimeout(async () => {
        const url = urlFn(q);
        if (!url) { hide(); return; }
        const r = await fetch(url); const items = await r.json();
        dd.innerHTML = '';
        if (!items.length) { hide(); return; }
        items.forEach((it) => {
          const a = document.createElement('button');
          a.type = 'button'; a.className = 'list-group-item list-group-item-action';
          a.textContent = it.label;
          a.addEventListener('click', () => { onPick(it); hide(); });
          dd.appendChild(a);
        });
        dd.style.display = 'block';
      }, 200);
    });
    input.addEventListener('blur', () => setTimeout(hide, 200));
  }

  /* ---------- carregar painel A/B/C ---------- */
  async function carregarDados() {
    const cod = $('te-cod-origem-val').value || $('te-cod-origem').value.trim();
    const empresa = $('te-empresa').value;
    if (!cod) return;
    const r = await fetch(`${BASE}/api/dados-codigo?codigo=${encodeURIComponent(cod)}&empresa=${empresa}`);
    dados = await r.json();
    if (!dados.success) { alerta(dados.message, 'danger'); $('te-painel').classList.add('d-none'); return; }
    if (!dados.produto) { alerta(dados.message || 'Sem saldo', 'warning'); $('te-painel').classList.add('d-none'); renderForm(); return; }
    $('te-prod-origem-info').textContent = `${dados.produto.cod} — ${dados.produto.name} (tracking: ${dados.produto.tracking})`;
    $('te-tbl-local').innerHTML = dados.por_local.map((l) =>
      `<tr><td>${l.location_name}${l.is_indisp ? ' <span class="badge bg-secondary">Indisp.</span>' : ''}</td>` +
      `<td class="text-end">${num(l.qty)}</td><td class="text-end">${num(l.reservada)}</td>` +
      `<td class="text-end fw-bold">${num(l.disponivel)}</td></tr>`).join('');
    $('te-tbl-lote').innerHTML = dados.por_lote.map((l) =>
      `<tr><td>${l.lote}${l.is_migracao ? ' <span class="badge bg-secondary">MIGRAÇÃO</span>' : ''}</td>` +
      `<td class="text-end">${num(l.qty)}</td><td class="text-end">${num(l.reservada)}</td>` +
      `<td class="text-end fw-bold">${num(l.disponivel)}</td></tr>`).join('');
    $('te-painel').classList.remove('d-none');
    renderForm();
  }

  function optLocais() {
    return (dados?.por_local || []).map((l) =>
      `<option value="${l.location_id}">${l.location_name} (disp ${num(l.disponivel)})</option>`).join('');
  }
  function optLotes() {
    return (dados?.por_lote || []).map((l) =>
      `<option value="${l.lote === '(sem lote)' ? '' : l.lote}">${l.lote} (disp ${num(l.disponivel)})</option>`).join('');
  }
  function inputLocalDestino(id) {
    return `<input type="text" id="${id}" class="form-control" autocomplete="off" placeholder="local destino">` +
           `<input type="hidden" id="${id}-val">`;
  }

  /* ---------- formulário por modo ---------- */
  function renderForm() {
    const modo = $('te-modo').value;
    const C = $('te-campos');
    if (modo === '1') {
      $('te-form-titulo').textContent = 'Modo 1 · Local → Local (mesmo código e lote)';
      C.innerHTML =
        `<div class="col-md-3"><label class="form-label">Lote</label><select id="m-lote" class="form-select"><option value="">(sem lote)</option>${optLotes()}</select></div>` +
        `<div class="col-md-3"><label class="form-label">Local origem</label><select id="m-loc-o" class="form-select">${optLocais()}</select></div>` +
        `<div class="col-md-3"><label class="form-label">Local destino</label>${inputLocalDestino('m-loc-d')}</div>` +
        `<div class="col-md-3"><label class="form-label">Qtd</label><input type="number" id="m-qty" class="form-control" min="0" step="0.001"></div>`;
    } else if (modo === '2') {
      $('te-form-titulo').textContent = 'Modo 2 · Lote → Lote (mesmo código e local)';
      C.innerHTML =
        `<div class="col-md-3"><label class="form-label">Local</label><select id="m-loc" class="form-select">${optLocais()}</select></div>` +
        `<div class="col-md-3"><label class="form-label">Lote origem</label><select id="m-lote-o" class="form-select">${optLotes()}</select></div>` +
        `<div class="col-md-3"><label class="form-label">Lote destino</label><input type="text" id="m-lote-d" class="form-control" placeholder="lote destino"></div>` +
        `<div class="col-md-3"><label class="form-label">Qtd</label><input type="number" id="m-qty" class="form-control" min="0" step="0.001"></div>`;
      $('m-lote-o').addEventListener('change', () => { $('m-lote-d').value = $('m-lote-o').value; }); // prefill 3.2
      $('m-lote-d').value = $('m-lote-o')?.value || '';
    } else {
      $('te-form-titulo').textContent = 'Modo 3 · Código → Código';
      C.innerHTML =
        `<div class="col-md-4"><label class="form-label">Código destino</label><input type="text" id="m-cod-d" class="form-control" autocomplete="off" placeholder="código destino"><input type="hidden" id="m-cod-d-val"><div id="m-aviso-par" class="form-text"></div></div>` +
        `<div class="col-md-4"><label class="form-label">Lote origem</label><select id="m-lote-o" class="form-select"><option value="">(sem lote)</option>${optLotes()}</select></div>` +
        `<div class="col-md-4"><label class="form-label">Lote destino</label><input type="text" id="m-lote-d" class="form-control" placeholder="lote destino"></div>` +
        `<div class="col-md-4 mt-2"><label class="form-label">Local origem</label><select id="m-loc-o" class="form-select">${optLocais()}</select></div>` +
        `<div class="col-md-4 mt-2"><label class="form-label">Local destino</label>${inputLocalDestino('m-loc-d')}</div>` +
        `<div class="col-md-4 mt-2"><label class="form-label">Qtd</label><input type="number" id="m-qty" class="form-control" min="0" step="0.001"></div>`;
      // prefills 3.2 / 3.3
      $('m-lote-o').addEventListener('change', () => { $('m-lote-d').value = $('m-lote-o').value; });
      $('m-lote-d').value = $('m-lote-o')?.value || '';
      $('m-loc-o').addEventListener('change', () => {
        const sel = $('m-loc-o'); $('m-loc-d').value = sel.options[sel.selectedIndex].text.split(' (')[0];
        $('m-loc-d-val').value = sel.value;
      });
      if ($('m-loc-o').options.length) { $('m-loc-o').dispatchEvent(new Event('change')); }
      const empresa = $('te-empresa').value;
      autocomplete($('m-cod-d'), (q) => `${BASE}/api/autocomplete/produto?q=${encodeURIComponent(q)}`,
        (it) => { $('m-cod-d').value = it.label; $('m-cod-d-val').value = it.cod; });
      autocomplete($('m-loc-d'), (q) => `${BASE}/api/autocomplete/local?q=${encodeURIComponent(q)}&empresa=${empresa}`,
        (it) => { $('m-loc-d').value = it.complete_name; $('m-loc-d-val').value = it.location_id; });
    }
    $('te-form').classList.remove('d-none');
    $('te-preview').classList.add('d-none');
  }

  /* ---------- montar payload por modo ---------- */
  function montarPayload() {
    const modo = $('te-modo').value;
    const base = { modo, empresa: $('te-empresa').value,
      cod_origem: $('te-cod-origem-val').value || $('te-cod-origem').value.trim(),
      qty: parseFloat($('m-qty').value) };
    if (modo === '1') return { ...base, lote_nome: $('m-lote').value || null,
      location_id_origem: $('m-loc-o').value, location_id_destino: $('m-loc-d-val').value };
    if (modo === '2') return { ...base, location_id: $('m-loc').value,
      lote_nome_origem: $('m-lote-o').value || null, lote_nome_destino: $('m-lote-d').value };
    return { ...base, cod_destino: $('m-cod-d-val').value || $('m-cod-d').value.trim(),
      lote_nome_origem: $('m-lote-o').value || null, lote_nome_destino: $('m-lote-d').value || null,
      location_id_origem: $('m-loc-o').value, location_id_destino: $('m-loc-d-val').value };
  }

  async function chamar(endpoint, payload) {
    const r = await fetch(`${BASE}/api/${endpoint}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
      body: JSON.stringify(payload) });
    return r.json();
  }

  async function simular() {
    ultimoPayload = montarPayload();
    if (!ultimoPayload.qty || ultimoPayload.qty <= 0) { alerta('Informe a quantidade', 'warning'); return; }
    $('te-btn-simular').disabled = true;
    const d = await chamar('simular', ultimoPayload);
    $('te-btn-simular').disabled = false;
    if (!d.success) { alerta(d.message, 'danger'); $('te-preview').classList.add('d-none'); return; }
    const p = d.preview;
    $('te-preview-body').innerHTML =
      (d.aviso_par ? '<div class="alert alert-warning py-1">⚠ Código destino não é par cadastrado em Unificação.</div>' : '') +
      `<p>Origem <code>${p.origem.label}</code>: <b>${num(p.origem.antes)} → ${num(p.origem.apos)}</b></p>` +
      `<p>Destino <code>${p.destino.label}</code>: <b>${num(p.destino.antes)} → ${num(p.destino.apos)}</b>` +
      (p.destino.lote_criado ? ' <span class="badge bg-info">lote será criado</span>' : '') + '</p>';
    $('te-preview').classList.remove('d-none');
  }

  async function confirmar() {
    if (!ultimoPayload) return;
    $('te-btn-confirmar').disabled = true;
    const d = await chamar('executar', ultimoPayload);
    $('te-btn-confirmar').disabled = false;
    alerta(d.success ? `✔ Transferência executada (${d.status}).` : d.message, d.success ? 'success' : 'danger');
    if (d.success) { $('te-preview').classList.add('d-none'); carregarDados(); }
  }

  /* ---------- wiring ---------- */
  document.addEventListener('DOMContentLoaded', () => {
    autocomplete($('te-cod-origem'),
      (q) => `${BASE}/api/autocomplete/produto?q=${encodeURIComponent(q)}`,
      (it) => { $('te-cod-origem').value = it.label; $('te-cod-origem-val').value = it.cod; carregarDados(); });
    $('te-empresa').addEventListener('change', carregarDados);
    $('te-modo').addEventListener('change', renderForm);
    $('te-btn-simular').addEventListener('click', simular);
    $('te-btn-confirmar').addEventListener('click', confirmar);
    $('te-btn-cancelar').addEventListener('click', () => $('te-preview').classList.add('d-none'));
  });
})();
```

- [ ] **Step 3: Smoke — template renderiza sem erro Jinja**

Run:
```bash
cd /home/rafaelnascimento/projetos/frete_sistema_transferencia_estoque
python -c "
from unittest.mock import patch, MagicMock
from app import create_app
a=create_app(); a.config.update(TESTING=True, LOGIN_DISABLED=True, WTF_CSRF_ENABLED=False)
u=MagicMock(); u.is_authenticated=True; u.perfil='administrador'; u.nome='Admin'
with patch('flask_login.utils._get_user', return_value=u):
    c=a.test_client(); r=c.get('/estoque/transferencia-estoque')
    print('status', r.status_code, 'tem te-app:', b'te-app' in r.data)
" 2>/dev/null | tail -1
```
Expected: `status 200 tem te-app: True`

- [ ] **Step 4: Commit**

```bash
cd /home/rafaelnascimento/projetos/frete_sistema_transferencia_estoque
git add app/templates/estoque/transferir_estoque_odoo.html app/static/js/estoque/transferir_estoque.js
git commit -m "feat(estoque): tela + JS transferencia de estoque (3 modos, autocomplete, simular/confirmar)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: Menu admin-only + remover template antigo

**Files:**
- Modify: `app/templates/_sidebar.html:152`
- Delete: `app/templates/estoque/transferir_saldo_odoo.html`

- [ ] **Step 1: Atualizar o link do menu (admin-only + endpoint novo)**

Em `app/templates/_sidebar.html`, substituir o `<li>` da linha 152-154:

```jinja
        <li><a class="nc-sidebar__link" href="{{ url_for('estoque.transferir_saldo_codigo') }}">
          <i class="fas fa-right-left nc-sidebar__icon"></i>
          <span class="nc-sidebar__label">Transferir Saldo (Odoo)</span></a></li>
```

por (envolto em guard admin):

```jinja
        {% if current_user.perfil == 'administrador' %}
        <li><a class="nc-sidebar__link" href="{{ url_for('estoque.transferencia_estoque') }}">
          <i class="fas fa-right-left nc-sidebar__icon"></i>
          <span class="nc-sidebar__label">Transferir Estoque (Odoo)</span>
          <span class="nc-sidebar__badge nc-sidebar__badge--new">NOVO</span></a></li>
        {% endif %}
```

- [ ] **Step 2: Remover o template antigo**

Run:
```bash
cd /home/rafaelnascimento/projetos/frete_sistema_transferencia_estoque
git rm app/templates/estoque/transferir_saldo_odoo.html
```

- [ ] **Step 3: Smoke — menu renderiza p/ admin com link novo e sem url_for quebrado**

Run:
```bash
cd /home/rafaelnascimento/projetos/frete_sistema_transferencia_estoque
python -c "
from unittest.mock import patch, MagicMock
from app import create_app
a=create_app(); a.config.update(TESTING=True, LOGIN_DISABLED=True, WTF_CSRF_ENABLED=False)
u=MagicMock(); u.is_authenticated=True; u.perfil='administrador'; u.nome='Admin'
with patch('flask_login.utils._get_user', return_value=u):
    c=a.test_client(); r=c.get('/estoque/transferencia-estoque')
    print('status', r.status_code, 'link novo:', b'Transferir Estoque (Odoo)' in r.data)
" 2>/dev/null | tail -1
```
Expected: `status 200 link novo: True` (sem `BuildError` de `url_for`)

- [ ] **Step 4: Commit**

```bash
cd /home/rafaelnascimento/projetos/frete_sistema_transferencia_estoque
git add app/templates/_sidebar.html app/templates/estoque/transferir_saldo_odoo.html
git commit -m "feat(estoque): link menu admin-only Transferir Estoque + remove template antigo

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 9: Verificação final

- [ ] **Step 1: Suíte das áreas tocadas verde**

Run:
```bash
cd /home/rafaelnascimento/projetos/frete_sistema_transferencia_estoque
source /home/rafaelnascimento/projetos/frete_sistema/.venv/bin/activate
export SENTRY_DSN="" DISABLE_SENTRY=1
python -m pytest tests/odoo/services/test_transferencia_saldo_codigo_service.py tests/estoque/ -q -p no:cacheprovider 2>/dev/null | grep -iE "passed|failed|error"
```
Expected: PASS (16 + 12 = 28 passed)

- [ ] **Step 2: Rodar mentalmente o fluxo completo** (checklist do spec §15)
  - Request → Route (`@require_admin`/`require_admin_json`) → dispatcher → service/átomo → Odoo → JSON → template/JS.
  - dry-run no `simular`; espelho local só no `executar` Modo 3; qtd ≤ disponível (front) + G027 (back).

- [ ] **Step 3: Lint UI (pre-commit roda automático; rodar explicitamente para checar)**

Run:
```bash
cd /home/rafaelnascimento/projetos/frete_sistema_transferencia_estoque
python scripts/audits/ui_policy_lint.py --enforce-new 2>&1 | tail -3
```
Expected: `0` violações (ou só pré-existentes não relacionadas).

- [ ] **Step 4: Atualizar handoff e oferecer finalização**

A finalização (merge/PR) é decidida com o dono via `superpowers:finishing-a-development-branch`. NÃO fazer merge em `main` sem confirmação (Rafael usa branches paralelas).

---

## Self-Review (preenchido pelo autor do plano)

**1. Spec coverage:** Modo 1 → Task 5 (`transferir_entre_locations`); Modo 2 → Task 5 (`transferir_entre_lotes_v2` + lote-novo); Modo 3 → Tasks 1+5 (`transferir_v2`); A/B/C/D → Task 3 (`dados-codigo`) + Task 7 (painel + select empresa); autocomplete → Task 4 + Task 7; admin-only → Task 3 (`require_admin`/`require_admin_json`) + Task 8 (menu); simular→confirmar → Task 5 + Task 7; reserva só-disponível (D3/G027) → herdado dos átomos (`validar_nao_abaixo_reserva=True`) + trava de qtd no front; aviso de par (D2) → Task 1; espelho local só Modo 3 (D8) → Task 1; lixo removido (§11) → Tasks 6+8. **Sem gaps.**

**2. Placeholder scan:** nenhum TBD/TODO; todo step tem código/comando real.

**3. Type consistency:** `transferir_v2` (kwargs idênticos em Task 1 e Task 5); retorno dos átomos (`reducao_origem`/`aumento_destino`/`status`) consumido por `_fmt_atomo12`; `transferir_v2` (`origem_antes`/`origem_apos`/`destino_*`/`aviso_par`/`lote_criado`) consumido por `_fmt_v2`; endpoints e payloads JS (`montarPayload`) batem campo a campo com o dispatcher.
