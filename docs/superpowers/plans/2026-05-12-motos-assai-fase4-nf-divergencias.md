# Motos Assaí — Fase 4 (NF + Divergências + Cancelar NF) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar fluxo completo de NF Q.P.A. com divergências centralizadas e cancelamento de NF: refatorar `_calcular_match` (D5 ignorar FATURADA + S8 gravar em assai_divergencia + A8 MODELO_DIVERGENTE + A14 idempotência), refatorar `ajustar_separacao_pela_nf` (S1 cria sep em FATURADA + A7 detectar CHASSI_OUTRA_LOJA antes do match + A11 gera Excel), criar `cancelar_nf_qpa` com cascata completa (S11 remover_nf_do_espelho + S15 limpar EmbarqueItem + S16 vinculo_historico + recalcular_status_pedido), criar services `criar_divergencia` e `resolver_divergencia` (S21 re-roda match + A14 guarda CANCELADA), Modal Expedição (S7 X=Pular), UI `/divergencias` com 5 modais de resolução, Migration 23 backfill 30 NFs órfãs em prod (A15 manual no Render Shell).

**Architecture:** Modificar fluxo existente de `_calcular_match` e `ajustar_separacao_pela_nf` (em `nf_qpa_adapter.py`) sem quebrar comportamento atual. Novo service `divergencia_service.py` para criar/resolver divergências. Service `cancelar_nf_qpa` em novo arquivo `cancelamento_nf_service.py`. Service novo `remover_nf_do_espelho` em `separacao_mirror_service.py`. Templates novos em `templates/motos_assai/divergencias/`. Modal Expedição embutido em `faturamento/upload_nf.html`. Migration 23 é Python-only e roda manualmente no Render Shell APÓS deploy do código.

**Tech Stack:** Flask, SQLAlchemy, PostgreSQL, Bootstrap 5, JavaScript ES6+.

**Spec referenciada:** `docs/superpowers/specs/2026-05-12-motos-assai-carregamento-divergencia-design.md` (v1.2) §3.3, §5.2, §6 Fase 7, §7, §8, §9, §13, §14, §15.3-15.6

**Pré-requisito:** Planos 1 + 2 completos e deployados.
- Plano 1: `assai_divergencia`, `assai_pedido_excel`, `assai_nf_qpa_item_vinculo_historico`, NF_STATUS_CANCELADA, etc.
- Plano 2: Carregamento service + UI funcionais (necessário para divergência tipo `CARREGAMENTO_CHASSI_FORA_NF` ser resolvível via "Alterar Carregamento").

---

## File Structure

### Services a criar

- `app/motos_assai/services/divergencia_service.py` — `criar_divergencia()` + `resolver_divergencia()`
- `app/motos_assai/services/cancelamento_nf_service.py` — `cancelar_nf_qpa()`

### Services a modificar

- `app/motos_assai/services/parsers/nf_qpa_adapter.py` — `_calcular_match` + `ajustar_separacao_pela_nf` + `importar_nf_qpa`
- `app/motos_assai/services/separacao_mirror_service.py` — adicionar `remover_nf_do_espelho()`
- `app/motos_assai/services/faturamento_service.py` — `regenerar_excel_qpa()` (extrair de inline)

### Routes a criar/modificar

- `app/motos_assai/routes/divergencias.py` — novo blueprint
- `app/motos_assai/routes/faturamento.py` — adicionar:
  - `POST /faturamento/nfs/<id>/cancelar` (cancelar NF)
  - Tratamento do Modal Expedição em `upload_nf` (POST com expedicao + opcionais)

### Templates a criar/modificar

- `app/templates/motos_assai/divergencias/lista.html` (novo)
- `app/templates/motos_assai/divergencias/_modal_cancelar_nf.html`
- `app/templates/motos_assai/divergencias/_modal_resolver_cce.html` (placeholder Plano 4)
- `app/templates/motos_assai/divergencias/_modal_alterar_carregamento.html`
- `app/templates/motos_assai/divergencias/_modal_substituir_chassi.html` (placeholder Plano 4)
- `app/templates/motos_assai/divergencias/_modal_ignorar.html`
- `app/templates/motos_assai/faturamento/_modal_expedicao.html` (novo — A8.1)
- `app/templates/motos_assai/faturamento/nf_detalhe.html` (modificar — adicionar botão "Cancelar NF")
- `app/templates/motos_assai/faturamento/lista_separacoes.html` (modificar — adicionar botão "Editar agendamento" — A10)
- `app/templates/base.html` (modificar — adicionar link "Divergências")

### Static (JS)

- `app/static/motos_assai/js/divergencias_modais.js`
- `app/static/motos_assai/js/upload_nf_modal_expedicao.js`

### Migrations

- `scripts/migrations/motos_assai_23_backfill_nfs_orfas.py` (Python-only — A15)

### Tests

- `tests/motos_assai/test_calcular_match_v2.py` (D5 + S8 + A8 + A14)
- `tests/motos_assai/test_ajustar_separacao_pela_nf_v2.py` (S1 + A7 + A11 + S19)
- `tests/motos_assai/test_cancelar_nf_qpa.py` (cascata completa)
- `tests/motos_assai/test_divergencia_service.py` (criar + resolver + S21)
- `tests/motos_assai/test_remover_nf_do_espelho.py`
- `tests/motos_assai/test_modal_expedicao.py`
- `tests/motos_assai/test_migration_23_backfill.py`

---

## Tasks

### Task 1: Service `criar_divergencia()` + testes

**Files:**
- Create: `app/motos_assai/services/divergencia_service.py`
- Create: `tests/motos_assai/test_divergencia_service.py`

- [ ] **Step 1: Escrever testes**

```python
"""Testes divergencia_service.criar_divergencia."""
import pytest
from app import create_app, db
from app.motos_assai.models import (
    AssaiCd, AssaiLoja, AssaiPedidoVenda, AssaiSeparacao, AssaiNfQpa,
    AssaiDivergencia,
    DIVERGENCIA_TIPO_CHASSI_NAO_CADASTRADO,
    DIVERGENCIA_TIPO_CHASSI_OUTRA_LOJA,
    SEPARACAO_STATUS_FECHADA, NF_STATUS_NAO_RECONCILIADO,
)
from app.motos_assai.services.divergencia_service import (
    criar_divergencia, DivergenciaError,
)


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.rollback()
        db.drop_all()


def test_criar_divergencia_sucesso(app):
    div = criar_divergencia(
        tipo=DIVERGENCIA_TIPO_CHASSI_NAO_CADASTRADO,
        chassi='ABC123',
        nf_id=None, sep_id=None, car_id=None,
        detalhes={'modelo_extraido': 'SOL'},
    )
    db.session.commit()

    assert div.id is not None
    assert div.tipo == DIVERGENCIA_TIPO_CHASSI_NAO_CADASTRADO
    assert div.chassi == 'ABC123'
    assert div.detalhes == {'modelo_extraido': 'SOL'}
    assert div.criada_em is not None
    assert div.resolvida_em is None


def test_criar_divergencia_tipo_invalido_falha(app):
    with pytest.raises(DivergenciaError, match='tipo invalido'):
        criar_divergencia(tipo='TIPO_INEXISTENTE', chassi='ABC', nf_id=None, sep_id=None, car_id=None)


def test_criar_divergencia_persiste_relacionamentos(app):
    """FK separacao_id, nf_id, carregamento_id sao salvas corretamente."""
    cd = AssaiCd(nome='CD', cnpj='12345678000100')
    loja = AssaiLoja(numero=1, cnpj='98765432000100', nome='Loja')
    db.session.add_all([cd, loja])
    db.session.flush()
    pedido = AssaiPedidoVenda(numero='T', cd_id=cd.id)
    db.session.add(pedido)
    db.session.flush()
    sep = AssaiSeparacao(pedido_id=pedido.id, loja_id=loja.id, status=SEPARACAO_STATUS_FECHADA)
    nf = AssaiNfQpa(chave_44='1' * 44, numero='N1', loja_id=loja.id, separacao_id=sep.id, status_match=NF_STATUS_NAO_RECONCILIADO)
    db.session.add_all([sep, nf])
    db.session.commit()

    div = criar_divergencia(
        tipo=DIVERGENCIA_TIPO_CHASSI_OUTRA_LOJA,
        chassi='X1',
        nf_id=nf.id, sep_id=sep.id, car_id=None,
    )
    db.session.commit()

    assert div.separacao_id == sep.id
    assert div.nf_id == nf.id
    assert div.separacao.id == sep.id
    assert div.nf.id == nf.id
```

- [ ] **Step 2: Rodar — devem falhar**

```bash
pytest tests/motos_assai/test_divergencia_service.py -v -k 'criar'
```

- [ ] **Step 3: Implementar `divergencia_service.py`**

```python
"""Service de Divergencias (Fase 4).

Spec: §7
Plano: docs/superpowers/plans/2026-05-12-motos-assai-fase4-nf-divergencias.md

Funcoes:
- criar_divergencia: insert em assai_divergencia (NAO commita — caller decide)
- resolver_divergencia: marca como resolvida + re-roda _calcular_match (S21=a + A14)
"""
from app import db
from app.motos_assai.models import (
    AssaiDivergencia, AssaiNfQpa,
    DIVERGENCIA_TIPOS_VALIDOS, DIVERGENCIA_RESOLUCAO_VALIDAS,
    NF_STATUS_CANCELADA,
)
from app.utils.timezone import agora_brasil_naive


class DivergenciaError(Exception):
    """Erro base de divergencia_service."""


def criar_divergencia(tipo, chassi, nf_id=None, sep_id=None, car_id=None, detalhes=None):
    """Cria divergencia em assai_divergencia.

    NAO commita (caller decide).

    Args:
        tipo: deve estar em DIVERGENCIA_TIPOS_VALIDOS
        chassi: chassi envolvido
        nf_id, sep_id, car_id: FKs opcionais
        detalhes: dict opcional para detalhes extras (jsonb)

    Returns:
        AssaiDivergencia criada.

    Raises:
        DivergenciaError: tipo invalido
    """
    if tipo not in DIVERGENCIA_TIPOS_VALIDOS:
        raise DivergenciaError(
            f'tipo invalido: {tipo}. Validos: {sorted(DIVERGENCIA_TIPOS_VALIDOS)}'
        )

    div = AssaiDivergencia(
        tipo=tipo,
        chassi=chassi,
        nf_id=nf_id,
        separacao_id=sep_id,
        carregamento_id=car_id,
        detalhes=detalhes or {},
        criada_em=agora_brasil_naive(),
    )
    db.session.add(div)
    db.session.flush()
    return div
```

- [ ] **Step 4: Rodar — devem passar**

```bash
pytest tests/motos_assai/test_divergencia_service.py -v -k 'criar'
```

- [ ] **Step 5: Commit**

```bash
git add app/motos_assai/services/divergencia_service.py tests/motos_assai/test_divergencia_service.py
git commit -m "feat(motos-assai): divergencia_service.criar_divergencia + 3 testes"
```

---

### Task 2: Service `resolver_divergencia()` (S21 + A14)

**Files:**
- Modify: `app/motos_assai/services/divergencia_service.py`
- Modify: `tests/motos_assai/test_divergencia_service.py`

- [ ] **Step 1: Adicionar testes**

```python
from app.motos_assai.models import NF_STATUS_BATEU, NF_STATUS_DIVERGENTE
from app.motos_assai.services.divergencia_service import (
    resolver_divergencia, DIVERGENCIA_RESOLUCAO_IGNORAR, DIVERGENCIA_RESOLUCAO_CANCELAR_NF,
)


def test_resolver_divergencia_marca_resolvida(app):
    div = criar_divergencia(tipo=DIVERGENCIA_TIPO_CHASSI_NAO_CADASTRADO, chassi='ABC')
    db.session.commit()

    resolver_divergencia(div.id, tipo_resolucao=DIVERGENCIA_RESOLUCAO_IGNORAR,
                       observacao='Operador aceita', operador_id=1)
    db.session.commit()

    div_ref = AssaiDivergencia.query.get(div.id)
    assert div_ref.resolvida_em is not None
    assert div_ref.resolvida_por_id == 1
    assert div_ref.tipo_resolucao == DIVERGENCIA_RESOLUCAO_IGNORAR
    assert div_ref.observacao_resolucao == 'Operador aceita'


def test_resolver_divergencia_ja_resolvida_falha(app):
    div = criar_divergencia(tipo=DIVERGENCIA_TIPO_CHASSI_NAO_CADASTRADO, chassi='ABC')
    db.session.commit()
    resolver_divergencia(div.id, tipo_resolucao=DIVERGENCIA_RESOLUCAO_IGNORAR, observacao='Primeira', operador_id=1)
    db.session.commit()

    with pytest.raises(DivergenciaError, match='ja resolvida'):
        resolver_divergencia(div.id, tipo_resolucao=DIVERGENCIA_RESOLUCAO_IGNORAR, observacao='Segunda', operador_id=2)


def test_resolver_divergencia_re_roda_match_nf_ativa(app, monkeypatch):
    """S21=a: ao resolver divergencia, re-roda _calcular_match na NF."""
    cd = AssaiCd(nome='CD', cnpj='12345678000100')
    loja = AssaiLoja(numero=1, cnpj='98765432000100', nome='Loja')
    db.session.add_all([cd, loja])
    db.session.flush()
    nf = AssaiNfQpa(chave_44='1'*44, numero='N1', loja_id=loja.id, status_match=NF_STATUS_DIVERGENTE)
    db.session.add(nf)
    db.session.commit()

    div = criar_divergencia(tipo=DIVERGENCIA_TIPO_CHASSI_NAO_CADASTRADO, chassi='X', nf_id=nf.id)
    db.session.commit()

    chamadas = []
    def fake_calcular_match(nf, op_id):
        chamadas.append(nf.id)
    monkeypatch.setattr(
        'app.motos_assai.services.divergencia_service._calcular_match', fake_calcular_match
    )

    resolver_divergencia(div.id, tipo_resolucao=DIVERGENCIA_RESOLUCAO_IGNORAR,
                       observacao='ok', operador_id=1)
    db.session.commit()

    assert nf.id in chamadas


def test_resolver_divergencia_NAO_re_roda_match_nf_cancelada(app, monkeypatch):
    """A14: NF CANCELADA nao deve ter match re-rodado (idempotencia)."""
    cd = AssaiCd(nome='CD', cnpj='12345678000100')
    loja = AssaiLoja(numero=1, cnpj='98765432000100', nome='Loja')
    db.session.add_all([cd, loja])
    db.session.flush()
    nf = AssaiNfQpa(chave_44='2'*44, numero='N2', loja_id=loja.id, status_match=NF_STATUS_CANCELADA)
    db.session.add(nf)
    db.session.commit()

    div = criar_divergencia(tipo=DIVERGENCIA_TIPO_CHASSI_NAO_CADASTRADO, chassi='X', nf_id=nf.id)
    db.session.commit()

    chamadas = []
    monkeypatch.setattr(
        'app.motos_assai.services.divergencia_service._calcular_match',
        lambda nf, op_id: chamadas.append(nf.id)
    )

    resolver_divergencia(div.id, tipo_resolucao=DIVERGENCIA_RESOLUCAO_IGNORAR,
                       observacao='ok', operador_id=1)
    db.session.commit()

    assert chamadas == []  # NAO chamado para NF CANCELADA
```

- [ ] **Step 2: Rodar — devem falhar**

```bash
pytest tests/motos_assai/test_divergencia_service.py -v -k 'resolver'
```

- [ ] **Step 3: Implementar `resolver_divergencia`**

Adicionar em `divergencia_service.py`:

```python
from app.motos_assai.models import (
    NF_STATUS_CANCELADA, DIVERGENCIA_RESOLUCAO_IGNORAR,
    DIVERGENCIA_RESOLUCAO_CANCELAR_NF, DIVERGENCIA_RESOLUCAO_CCE,
    DIVERGENCIA_RESOLUCAO_ALTERAR_CARREGAMENTO,
    DIVERGENCIA_RESOLUCAO_SUBSTITUIR_CHASSI,
)


def resolver_divergencia(div_id, tipo_resolucao, observacao, operador_id):
    """Marca divergencia como resolvida + re-roda _calcular_match (S21=a + A14).

    Args:
        div_id: ID da AssaiDivergencia
        tipo_resolucao: deve estar em DIVERGENCIA_RESOLUCAO_VALIDAS
        observacao: texto explicativo (obrigatorio se tipo=IGNORAR)
        operador_id: usuario que resolveu

    Raises:
        DivergenciaError: divergencia ja resolvida ou tipo_resolucao invalido
    """
    if tipo_resolucao not in DIVERGENCIA_RESOLUCAO_VALIDAS:
        raise DivergenciaError(
            f'tipo_resolucao invalido: {tipo_resolucao}. '
            f'Validos: {sorted(DIVERGENCIA_RESOLUCAO_VALIDAS)}'
        )

    div = AssaiDivergencia.query.get(div_id)
    if not div:
        raise DivergenciaError(f'Divergencia {div_id} nao encontrada')
    if div.resolvida_em is not None:
        raise DivergenciaError(f'Divergencia {div_id} ja resolvida em {div.resolvida_em}')

    if tipo_resolucao == DIVERGENCIA_RESOLUCAO_IGNORAR and not observacao.strip():
        raise DivergenciaError('Observacao obrigatoria para resolucao IGNORAR')

    div.resolvida_em = agora_brasil_naive()
    div.resolvida_por_id = operador_id
    div.tipo_resolucao = tipo_resolucao
    div.observacao_resolucao = observacao

    # S21=a: re-rodar _calcular_match na NF associada
    # A14: idempotencia — NAO re-roda se NF esta CANCELADA
    if div.nf_id:
        nf = AssaiNfQpa.query.get(div.nf_id)
        if nf and nf.status_match != NF_STATUS_CANCELADA:
            _calcular_match(nf, operador_id)

    db.session.flush()


def _calcular_match(nf, operador_id):
    """Wrapper para `nf_qpa_adapter._calcular_match` (evita import circular).

    Lazy import para nao dependeneciar adapter no momento de import do service.
    """
    from app.motos_assai.services.parsers.nf_qpa_adapter import _calcular_match as adapter_calc
    adapter_calc(nf, operador_id)
```

- [ ] **Step 4: Rodar — devem passar**

```bash
pytest tests/motos_assai/test_divergencia_service.py -v -k 'resolver'
```

- [ ] **Step 5: Commit**

```bash
git add app/motos_assai/services/divergencia_service.py tests/motos_assai/test_divergencia_service.py
git commit -m "feat(motos-assai): resolver_divergencia (S21 re-roda match + A14 idempotencia)"
```

---

### Task 3: Refatorar `_calcular_match` — D5 ignorar FATURADA + S8 gravar em assai_divergencia

**Files:**
- Modify: `app/motos_assai/services/parsers/nf_qpa_adapter.py`
- Create: `tests/motos_assai/test_calcular_match_v2.py`

- [ ] **Step 1: Escrever testes**

```python
"""Testes _calcular_match v2 (D5 + S8 + A8 + A14)."""
import pytest
from app import create_app, db
from app.motos_assai.models import *
from app.motos_assai.services.moto_evento_service import emitir_evento
from app.motos_assai.services.parsers.nf_qpa_adapter import _calcular_match


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.rollback()
        db.drop_all()


@pytest.fixture
def setup_basico(app):
    cd = AssaiCd(nome='CD', cnpj='12345678000100')
    loja = AssaiLoja(numero=1, cnpj='98765432000100', nome='Loja')
    modelo = AssaiModelo(codigo='SOL', descricao_qpa='SOL ELETRICA')
    db.session.add_all([cd, loja, modelo])
    db.session.flush()
    pedido = AssaiPedidoVenda(numero='T', cd_id=cd.id)
    db.session.add(pedido)
    db.session.flush()
    return cd, loja, modelo, pedido


def _criar_sep_com_chassi(pedido, loja, modelo, chassi, status, valor=1000.0):
    sep = AssaiSeparacao(pedido_id=pedido.id, loja_id=loja.id, status=status)
    db.session.add(sep)
    db.session.flush()
    moto = AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='Preto')
    db.session.add(moto)
    db.session.flush()
    item = AssaiSeparacaoItem(separacao_id=sep.id, chassi=chassi, modelo_id=modelo.id, valor_unitario_qpa=valor)
    db.session.add(item)
    return sep, item, moto


def test_d5_match_ignora_seps_faturadas(setup_basico):
    """D5: chassi em sep FATURADA NAO deve ser matched (evitar dupla vinculacao G7)."""
    cd, loja, modelo, pedido = setup_basico
    sep_faturada, _, _ = _criar_sep_com_chassi(pedido, loja, modelo, 'C001', SEPARACAO_STATUS_FATURADA)
    db.session.commit()

    nf = AssaiNfQpa(chave_44='1'*44, numero='N1', loja_id=loja.id, status_match=NF_STATUS_NAO_RECONCILIADO)
    db.session.add(nf)
    db.session.flush()
    db.session.add(AssaiNfQpaItem(nf_id=nf.id, chassi='C001', modelo_extraido='SOL', valor_extraido=1000.0))
    db.session.commit()

    _calcular_match(nf, operador_id=1)
    db.session.commit()

    # NAO bate (sep FATURADA ignorada)
    assert nf.status_match in (NF_STATUS_NAO_RECONCILIADO, NF_STATUS_DIVERGENTE)


def test_s8_grava_divergencia_em_tabela_centralizada(setup_basico):
    """S8=a: divergencia LOJA_DIVERGENTE deve ser gravada em assai_divergencia."""
    cd, loja, modelo, pedido = setup_basico
    loja2 = AssaiLoja(numero=2, cnpj='11111111000100', nome='Loja2')
    db.session.add(loja2)
    db.session.flush()
    sep_loja2, _, _ = _criar_sep_com_chassi(pedido, loja2, modelo, 'C002', SEPARACAO_STATUS_FECHADA)
    db.session.commit()

    nf = AssaiNfQpa(chave_44='2'*44, numero='N2', loja_id=loja.id, status_match=NF_STATUS_NAO_RECONCILIADO)
    db.session.add(nf)
    db.session.flush()
    db.session.add(AssaiNfQpaItem(nf_id=nf.id, chassi='C002', modelo_extraido='SOL', valor_extraido=1000.0))
    db.session.commit()

    _calcular_match(nf, operador_id=1)
    db.session.commit()

    # Divergencia LOJA_DIVERGENTE em assai_divergencia
    div = AssaiDivergencia.query.filter_by(
        tipo=DIVERGENCIA_TIPO_LOJA_DIVERGENTE, chassi='C002', nf_id=nf.id,
    ).first()
    assert div is not None


def test_a8_modelo_divergente_gera_divergencia(setup_basico):
    """A8: chassi em assai_moto com modelo X mas NF diz modelo Y → MODELO_DIVERGENTE."""
    cd, loja, modelo_sol, pedido = setup_basico
    modelo_dot = AssaiModelo(codigo='DOT', descricao_qpa='DOT MOTO')
    db.session.add(modelo_dot)
    db.session.flush()

    # Chassi cadastrado como SOL, mas NF diz DOT
    sep, _, _ = _criar_sep_com_chassi(pedido, loja, modelo_sol, 'C003', SEPARACAO_STATUS_FECHADA)
    db.session.commit()

    nf = AssaiNfQpa(chave_44='3'*44, numero='N3', loja_id=loja.id, status_match=NF_STATUS_NAO_RECONCILIADO)
    db.session.add(nf)
    db.session.flush()
    db.session.add(AssaiNfQpaItem(nf_id=nf.id, chassi='C003', modelo_extraido='DOT', valor_extraido=1000.0))
    db.session.commit()

    _calcular_match(nf, operador_id=1)
    db.session.commit()

    div = AssaiDivergencia.query.filter_by(
        tipo=DIVERGENCIA_TIPO_MODELO_DIVERGENTE, chassi='C003', nf_id=nf.id,
    ).first()
    assert div is not None


def test_a14_calcular_match_idempotente_em_nf_cancelada(setup_basico):
    """A14: _calcular_match deve ser no-op em NF CANCELADA."""
    cd, loja, modelo, pedido = setup_basico
    sep, _, _ = _criar_sep_com_chassi(pedido, loja, modelo, 'C004', SEPARACAO_STATUS_FECHADA)
    db.session.commit()

    nf = AssaiNfQpa(chave_44='4'*44, numero='N4', loja_id=loja.id, status_match=NF_STATUS_CANCELADA)
    db.session.add(nf)
    db.session.flush()
    db.session.add(AssaiNfQpaItem(nf_id=nf.id, chassi='C004', modelo_extraido='SOL', valor_extraido=1000.0))
    db.session.commit()

    _calcular_match(nf, operador_id=1)
    db.session.commit()

    # NF CONTINUA CANCELADA (nao mudou para BATEU/DIVERGENTE)
    nf_ref = AssaiNfQpa.query.get(nf.id)
    assert nf_ref.status_match == NF_STATUS_CANCELADA
```

- [ ] **Step 2: Rodar — devem falhar**

```bash
pytest tests/motos_assai/test_calcular_match_v2.py -v
```

- [ ] **Step 3: Refatorar `_calcular_match` em `nf_qpa_adapter.py`**

Localizar `_calcular_match` no arquivo `app/motos_assai/services/parsers/nf_qpa_adapter.py`. Refatorar:

```python
from app.motos_assai.models import (
    SEPARACAO_STATUS_FATURADA, SEPARACAO_STATUS_CANCELADA,
    NF_STATUS_BATEU, NF_STATUS_DIVERGENTE, NF_STATUS_NAO_RECONCILIADO,
    NF_STATUS_CANCELADA,
    DIVERGENCIA_TIPO_LOJA_DIVERGENTE,
    DIVERGENCIA_TIPO_VALOR_DIVERGENTE,
    DIVERGENCIA_TIPO_MODELO_DIVERGENTE,
    DIVERGENCIA_TIPO_CHASSI_SEM_SEPARACAO,
)
from app.motos_assai.services.modelo_resolver import resolver_modelo


def _calcular_match(nf, operador_id):
    """Calcula match de NF Q.P.A. v2.

    D5: ignora seps FATURADAS no JOIN (evita dupla vinculacao).
    S8=a: grava divergencias em assai_divergencia (NAO em tipo_divergencia do item).
    A8: valida modelo (cria MODELO_DIVERGENTE).
    A14: idempotente — early return se NF CANCELADA.
    A4: status BATEU → DIVERGENTE quando ha divergencias (nao explicito aqui — ver Task X).

    Atualiza:
        - nf.status_match (BATEU / DIVERGENTE / NAO_RECONCILIADO)
        - cria divergencias em assai_divergencia
        - vincula sep_item ao item da NF (separacao_item_id)

    NAO commita.
    """
    # A14: NF cancelada nao bate mais nada
    if nf.status_match == NF_STATUS_CANCELADA:
        return

    from app.motos_assai.services.divergencia_service import criar_divergencia

    matches_ok = 0
    matches_falha = 0

    for it in nf.itens:
        chassi = it.chassi

        # Buscar AssaiSeparacaoItem do chassi (D5: ignora FATURADA + CANCELADA)
        sep_item = (AssaiSeparacaoItem.query
                    .join(AssaiSeparacao)
                    .filter(
                        AssaiSeparacaoItem.chassi == chassi,
                        AssaiSeparacao.status.notin_([SEPARACAO_STATUS_FATURADA, SEPARACAO_STATUS_CANCELADA]),
                    )
                    .first())

        if not sep_item:
            criar_divergencia(
                tipo=DIVERGENCIA_TIPO_CHASSI_SEM_SEPARACAO,
                chassi=chassi, nf_id=nf.id,
                detalhes={'modelo_extraido': it.modelo_extraido},
            )
            matches_falha += 1
            continue

        sep = sep_item.separacao

        # 1. Loja
        if sep.loja_id != nf.loja_id:
            criar_divergencia(
                tipo=DIVERGENCIA_TIPO_LOJA_DIVERGENTE,
                chassi=chassi, sep_id=sep.id, nf_id=nf.id,
                detalhes={'loja_sep': sep.loja_id, 'loja_nf': nf.loja_id},
            )
            matches_falha += 1
            continue

        # 2. Valor (1% tolerancia)
        valor_sep = float(sep_item.valor_unitario_qpa)
        valor_nf = float(it.valor_extraido) if it.valor_extraido else 0
        if valor_sep > 0:
            divergencia_pct = abs(valor_sep - valor_nf) / valor_sep
            if divergencia_pct > 0.01:
                criar_divergencia(
                    tipo=DIVERGENCIA_TIPO_VALOR_DIVERGENTE,
                    chassi=chassi, sep_id=sep.id, nf_id=nf.id,
                    detalhes={'valor_sep': valor_sep, 'valor_nf': valor_nf, 'pct': divergencia_pct},
                )
                matches_falha += 1
                continue

        # 3. A8 — Modelo
        moto = AssaiMoto.query.filter_by(chassi=chassi).first()
        if moto and it.modelo_extraido:
            modelo_resolvido = resolver_modelo(it.modelo_extraido)
            if modelo_resolvido and moto.modelo_id != modelo_resolvido.id:
                criar_divergencia(
                    tipo=DIVERGENCIA_TIPO_MODELO_DIVERGENTE,
                    chassi=chassi, sep_id=sep.id, nf_id=nf.id,
                    detalhes={
                        'modelo_assai_moto_id': moto.modelo_id,
                        'modelo_extraido_nf': it.modelo_extraido,
                        'modelo_resolvido_id': modelo_resolvido.id,
                    },
                )
                matches_falha += 1
                continue

        # OK: vincula
        it.separacao_item_id = sep_item.id
        matches_ok += 1

    # Atualiza status_match
    if matches_ok == 0:
        nf.status_match = NF_STATUS_NAO_RECONCILIADO
    elif matches_falha > 0:
        nf.status_match = NF_STATUS_DIVERGENTE
    else:
        # Todos OK
        nf.status_match = NF_STATUS_BATEU
        # Atualizar sep status para FATURADA (logica original mantida)
        seps_atualizar = set()
        for it in nf.itens:
            if it.separacao_item_id:
                seps_atualizar.add(it.separacao_item.separacao_id)
        for sep_id in seps_atualizar:
            sep = AssaiSeparacao.query.get(sep_id)
            if sep:
                sep.status = SEPARACAO_STATUS_FATURADA

        # M3 fix: emitir evento FATURADA por chassi (comportamento legado preservado)
        # Sem isso, status_efetivo do chassi nao reflete FATURADA — quebra:
        # - rastrear_chassi (mostra SEPARADA em vez de FATURADA)
        # - consultando-estoque-assai (chassi continua "fora estoque" mas como SEPARADA)
        # - audit log incompleto
        from app.motos_assai.services.moto_evento_service import emitir_evento
        from app.motos_assai.models import EVENTO_FATURADA
        for it in nf.itens:
            if it.separacao_item_id:
                emitir_evento(
                    it.chassi, EVENTO_FATURADA, operador_id=importada_por_id,
                    observacao=f'NF {nf.numero} importada (BATEU)',
                    dados_extras={'nf_id': nf.id, 'chave_44': nf.chave_44},
                )

    db.session.flush()
```

**M3 fix aplicado**: emite evento FATURADA por chassi quando NF bate (preserva comportamento legado documentado em `app/motos_assai/CLAUDE.md`: "Quando BATEU: separação → status FATURADA; cada chassi emite evento FATURADA"). Adicionar teste:

```python
def test_m3_bateu_emite_evento_faturada_por_chassi(setup_basico):
    """M3 fix: chassi recebe evento FATURADA quando NF inteira bate."""
    cd, loja, modelo, pedido = setup_basico
    sep, _, _ = _criar_sep_com_chassi(pedido, loja, modelo, 'CFAT001', SEPARACAO_STATUS_FECHADA)
    db.session.commit()

    nf = AssaiNfQpa(chave_44='F'*44, numero='NF999', loja_id=loja.id, status_match=NF_STATUS_NAO_RECONCILIADO)
    db.session.add(nf)
    db.session.flush()
    db.session.add(AssaiNfQpaItem(nf_id=nf.id, chassi='CFAT001', modelo_extraido='SOL', valor_extraido=1000.0))
    db.session.commit()

    _calcular_match(nf, operador_id=1)
    db.session.commit()

    assert nf.status_match == NF_STATUS_BATEU
    assert sep.status == SEPARACAO_STATUS_FATURADA
    # M3: chassi recebeu evento FATURADA
    from app.motos_assai.services.moto_evento_service import status_efetivo
    assert status_efetivo('CFAT001') == EVENTO_FATURADA
```

NOTA: `EmbarqueItem.nota_fiscal` propagation continua em `importar_nf_qpa` (logica original — separada de `_calcular_match`). Verificar arquivo `nf_qpa_adapter.py` original para detalhes.

- [ ] **Step 4: Rodar testes**

```bash
pytest tests/motos_assai/test_calcular_match_v2.py -v
```

- [ ] **Step 5: Commit**

```bash
git add app/motos_assai/services/parsers/nf_qpa_adapter.py tests/motos_assai/test_calcular_match_v2.py
git commit -m "refactor(motos-assai): _calcular_match v2 (D5+S8+A8+A14)

D5: ignora seps FATURADAS (evita dupla vinculacao G7)
S8=a: grava divergencias em assai_divergencia centralizada
A8: valida MODELO_DIVERGENTE
A14: idempotente em NF CANCELADA"
```

---

### Task 4: Refatorar `ajustar_separacao_pela_nf` — A7 detectar CHASSI_OUTRA_LOJA

**Files:**
- Modify: `app/motos_assai/services/parsers/nf_qpa_adapter.py` (ou `separacao_service.py`)
- Create: `tests/motos_assai/test_ajustar_separacao_pela_nf_v2.py`

- [ ] **Step 1: Escrever testes**

```python
"""Testes ajustar_separacao_pela_nf v2 (A7 + S1 + A11 + S19)."""
import pytest
from app import create_app, db
from app.motos_assai.models import *
from app.motos_assai.services.moto_evento_service import emitir_evento


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.rollback()
        db.drop_all()


def test_a7_detecta_chassi_outra_loja_antes_do_match(app):
    """A7: chassi em sep ativa de OUTRA loja gera divergencia CHASSI_OUTRA_LOJA."""
    cd = AssaiCd(nome='CD', cnpj='12345678000100')
    loja_a = AssaiLoja(numero=1, cnpj='1', nome='LA')
    loja_b = AssaiLoja(numero=2, cnpj='2', nome='LB')
    modelo = AssaiModelo(codigo='SOL')
    db.session.add_all([cd, loja_a, loja_b, modelo])
    db.session.flush()
    pedido = AssaiPedidoVenda(numero='T', cd_id=cd.id)
    db.session.add(pedido)
    db.session.flush()

    # Sep ativa em LB com chassi C001
    sep_b = AssaiSeparacao(pedido_id=pedido.id, loja_id=loja_b.id, status=SEPARACAO_STATUS_FECHADA)
    db.session.add(sep_b)
    db.session.flush()
    moto = AssaiMoto(chassi='C001', modelo_id=modelo.id, cor='Preto')
    db.session.add(moto)
    db.session.flush()
    db.session.add(AssaiSeparacaoItem(separacao_id=sep_b.id, chassi='C001', modelo_id=modelo.id, valor_unitario_qpa=1000.0))

    # NF para LA com C001
    nf = AssaiNfQpa(chave_44='1'*44, numero='N1', loja_id=loja_a.id, status_match=NF_STATUS_NAO_RECONCILIADO)
    db.session.add(nf)
    db.session.flush()
    db.session.add(AssaiNfQpaItem(nf_id=nf.id, chassi='C001', modelo_extraido='SOL', valor_extraido=1000.0))
    db.session.commit()

    from app.motos_assai.services.parsers.nf_qpa_adapter import ajustar_separacao_pela_nf
    ajustar_separacao_pela_nf(nf.id, operador_id=1)
    db.session.commit()

    div = AssaiDivergencia.query.filter_by(
        tipo=DIVERGENCIA_TIPO_CHASSI_OUTRA_LOJA, chassi='C001', nf_id=nf.id,
    ).first()
    assert div is not None
    assert div.detalhes['loja_atual'] == loja_b.id
    assert div.detalhes['loja_nf'] == loja_a.id
```

- [ ] **Step 2: Rodar — deve falhar**

```bash
pytest tests/motos_assai/test_ajustar_separacao_pela_nf_v2.py -v -k 'a7'
```

- [ ] **Step 3: Refatorar `ajustar_separacao_pela_nf` (A7)**

Localizar função em `nf_qpa_adapter.py`. ANTES da lógica de ajuste atual, inserir:

```python
def ajustar_separacao_pela_nf(nf_id, operador_id):
    nf = AssaiNfQpa.query.get(nf_id)
    if not nf:
        return {'ok': False, 'razao': 'NF nao encontrada'}

    chassis_nf = [it.chassi for it in nf.itens]

    # A7: detectar CHASSI_OUTRA_LOJA antes do ajuste
    from app.motos_assai.services.divergencia_service import criar_divergencia

    chassis_outra_loja = []
    for chassi in chassis_nf:
        sep_outra_loja = (AssaiSeparacao.query
                          .join(AssaiSeparacaoItem)
                          .filter(
                              AssaiSeparacaoItem.chassi == chassi,
                              AssaiSeparacao.status.in_([
                                  SEPARACAO_STATUS_EM_SEPARACAO,
                                  SEPARACAO_STATUS_FECHADA,
                                  SEPARACAO_STATUS_CARREGADA,
                                  SEPARACAO_STATUS_FATURADA,
                              ]),
                              AssaiSeparacao.loja_id != nf.loja_id,
                          )
                          .first())
        if sep_outra_loja:
            criar_divergencia(
                tipo=DIVERGENCIA_TIPO_CHASSI_OUTRA_LOJA,
                chassi=chassi, sep_id=sep_outra_loja.id, nf_id=nf.id,
                detalhes={
                    'loja_atual': sep_outra_loja.loja_id,
                    'loja_nf': nf.loja_id,
                    'sep_status': sep_outra_loja.status,
                },
            )
            chassis_outra_loja.append(chassi)

    # Filtrar chassis para o ajuste (excluir os com CHASSI_OUTRA_LOJA)
    chassis_filtrados = [c for c in chassis_nf if c not in chassis_outra_loja]

    # ... resto da logica original de ajuste, usando chassis_filtrados ...
```

- [ ] **Step 4: Rodar testes**

```bash
pytest tests/motos_assai/test_ajustar_separacao_pela_nf_v2.py -v -k 'a7'
```

- [ ] **Step 5: Commit**

```bash
git add app/motos_assai/services/parsers/nf_qpa_adapter.py tests/motos_assai/test_ajustar_separacao_pela_nf_v2.py
git commit -m "refactor(motos-assai): ajustar_separacao_pela_nf detecta CHASSI_OUTRA_LOJA antes do match (A7)"
```

---

### Task 5: `ajustar_separacao_pela_nf` — S1 cria sep em FATURADA + A11 gera Excel

**Files:**
- Modify: `app/motos_assai/services/parsers/nf_qpa_adapter.py`
- Modify: `tests/motos_assai/test_ajustar_separacao_pela_nf_v2.py`

- [ ] **Step 1: Adicionar testes**

```python
def test_s1_cria_sep_em_faturada_quando_nao_ha_sep(app):
    """S1=b: NF antes da sep cria sep automaticamente em FATURADA."""
    # Setup com chassi cadastrado mas sem sep
    cd = AssaiCd(nome='CD', cnpj='12345678000100')
    loja = AssaiLoja(numero=1, cnpj='1', nome='L')
    modelo = AssaiModelo(codigo='SOL')
    db.session.add_all([cd, loja, modelo])
    db.session.flush()
    pedido = AssaiPedidoVenda(numero='T', cd_id=cd.id, status=PEDIDO_STATUS_ABERTO)
    db.session.add(pedido)
    db.session.flush()
    pvl = AssaiPedidoVendaLoja(pedido_id=pedido.id, loja_id=loja.id)
    db.session.add(pvl)
    db.session.add(AssaiPedidoVendaItem(
        pedido_id=pedido.id, pedido_loja_id=pvl.id, loja_id=loja.id, modelo_id=modelo.id,
        qtd_pedida=10, valor_unitario=1000.0,
    ))
    moto = AssaiMoto(chassi='X001', modelo_id=modelo.id, cor='Preto')
    db.session.add(moto)
    db.session.flush()

    nf = AssaiNfQpa(chave_44='1'*44, numero='N1', loja_id=loja.id, status_match=NF_STATUS_NAO_RECONCILIADO)
    db.session.add(nf)
    db.session.flush()
    db.session.add(AssaiNfQpaItem(nf_id=nf.id, chassi='X001', modelo_extraido='SOL', valor_extraido=1000.0))
    db.session.commit()

    from app.motos_assai.services.parsers.nf_qpa_adapter import ajustar_separacao_pela_nf
    result = ajustar_separacao_pela_nf(nf.id, operador_id=1)
    db.session.commit()

    assert result['ok'] is True
    sep = AssaiSeparacao.query.filter_by(pedido_id=pedido.id, loja_id=loja.id).first()
    assert sep is not None
    assert sep.status == SEPARACAO_STATUS_FATURADA  # S1=b
    assert sep.fechada_por_id == 1  # A9


def test_a11_gera_excel_versao_1_em_sep_nascida_via_nf(app):
    """A11: sep nascida via NF gera Excel versao 1."""
    # ... setup similar ao test_s1 ...
    # Apos ajustar_separacao_pela_nf, verificar:
    excel = AssaiPedidoExcel.query.filter_by(separacao_id=sep.id, ativo=True).first()
    assert excel is not None
    assert excel.versao == 1
    assert 'criada_via_nf_importada' in excel.motivo_regeneracao


def test_s19_nf_parcial_chassis_mistos_cria_sep_parcial_e_divergencia(app):
    """S19=b + A5=b: NF com chassis cadastrados+nao cadastrados cria sep parcial + divergencias + DIVERGENTE."""
    # ... setup com 2 chassis: X001 cadastrado, X999 nao cadastrado ...
    # Apos importar:
    sep = AssaiSeparacao.query.filter_by(pedido_id=pedido.id, loja_id=loja.id).first()
    assert sep is not None  # cria sep com X001 (cadastrado)
    assert AssaiSeparacaoItem.query.filter_by(separacao_id=sep.id, chassi='X001').first() is not None
    assert AssaiSeparacaoItem.query.filter_by(separacao_id=sep.id, chassi='X999').first() is None  # nao cria

    div = AssaiDivergencia.query.filter_by(
        tipo=DIVERGENCIA_TIPO_CHASSI_NAO_CADASTRADO, chassi='X999', nf_id=nf.id,
    ).first()
    assert div is not None

    nf_ref = AssaiNfQpa.query.get(nf.id)
    assert nf_ref.status_match == NF_STATUS_DIVERGENTE  # A5=b
```

- [ ] **Step 2: Rodar — devem falhar**

```bash
pytest tests/motos_assai/test_ajustar_separacao_pela_nf_v2.py -v -k 's1 or a11 or s19'
```

- [ ] **Step 3: Implementar S1 + A11 + S19 em `ajustar_separacao_pela_nf`**

Após o bloco A7 (Task 4), modificar a lógica de criação automática de sep:

```python
    # ... continuacao do ajustar_separacao_pela_nf ...

    # Verificar se ja existe sep candidata
    seps_existentes = (AssaiSeparacao.query
                       .filter_by(pedido_id=pedido_id, loja_id=nf.loja_id)
                       .filter(AssaiSeparacao.status.in_([
                           SEPARACAO_STATUS_EM_SEPARACAO,
                           SEPARACAO_STATUS_FECHADA,
                       ]))
                       .all())

    if not seps_existentes:
        # S1=b — Cenario T3a: NF antes da sep, sem candidata existente
        # Cria sep em FATURADA (pula EM_SEPARACAO + FECHADA + CARREGADA)

        # S19=b: separar chassis cadastrados vs nao cadastrados
        chassis_cadastrados = []
        chassis_nao_cadastrados = []
        for chassi in chassis_filtrados:
            moto = AssaiMoto.query.filter_by(chassi=chassi).first()
            if moto:
                chassis_cadastrados.append((chassi, moto))
            else:
                chassis_nao_cadastrados.append(chassi)

        # Criar divergencias para nao cadastrados
        for chassi in chassis_nao_cadastrados:
            criar_divergencia(
                tipo=DIVERGENCIA_TIPO_CHASSI_NAO_CADASTRADO,
                chassi=chassi, nf_id=nf.id,
            )

        if not chassis_cadastrados:
            # Nenhum chassi cadastrado — nao cria sep
            return {'ok': False, 'razao': 'Todos chassis nao cadastrados'}

        # Criar sep em FATURADA
        sep = AssaiSeparacao(
            pedido_id=pedido_id, loja_id=nf.loja_id,
            status=SEPARACAO_STATUS_FATURADA,  # S1=b
            iniciada_em=agora_brasil_naive(),
            fechada_em=agora_brasil_naive(),
            fechada_por_id=operador_id,  # A9
        )
        db.session.add(sep)
        db.session.flush()

        # Adicionar items + emitir SEPARADA + FATURADA
        for chassi, moto in chassis_cadastrados:
            valor_unit = _resolver_valor_unitario_pedido(pedido_id, moto.modelo_id)
            db.session.add(AssaiSeparacaoItem(
                separacao_id=sep.id, chassi=chassi, modelo_id=moto.modelo_id,
                valor_unitario_qpa=valor_unit,
            ))
            emitir_evento(chassi, EVENTO_SEPARADA, operador_id=operador_id, observacao='criado via NF S1=b')
            emitir_evento(chassi, EVENTO_FATURADA, operador_id=operador_id,
                          observacao=f'NF {nf.numero} importada',
                          dados_extras={'nf_id': nf.id})

        # Vincular NF a sep
        nf.separacao_id = sep.id

        # A11: gerar Excel versao 1
        from app.motos_assai.services.faturamento_service import gerar_excel_qpa
        bytes_xlsx, s3_key = gerar_excel_qpa(sep.id, operador_id)
        db.session.add(AssaiPedidoExcel(
            pedido_id=pedido_id, separacao_id=sep.id,
            s3_key=s3_key, versao=1, ativo=True,
            motivo_regeneracao='criada_via_nf_importada',
            gerado_por_id=operador_id,
        ))

        # Espelhar para Nacom
        from app.motos_assai.services.separacao_mirror_service import mirror_assai_to_separacao
        mirror_assai_to_separacao(sep.id)

        return {'ok': True, 'sep_id': sep.id, 'criada_automaticamente': True}

    # ... resto da logica existente para casos onde ha sep candidata ...
```

- [ ] **Step 4: Rodar testes**

```bash
pytest tests/motos_assai/test_ajustar_separacao_pela_nf_v2.py -v
```

- [ ] **Step 5: Commit**

```bash
git add app/motos_assai/services/parsers/nf_qpa_adapter.py tests/motos_assai/test_ajustar_separacao_pela_nf_v2.py
git commit -m "feat(motos-assai): ajustar_separacao_pela_nf cria sep em FATURADA (S1+A11+S19)"
```

---

### Tasks 6-12: Cancelamento NF + Modal Expedição + UI Divergências

NOTA: para reduzir tamanho deste plano (já gigantesco), as tasks 6-30 seguem o mesmo padrão TDD:
1. Escrever teste falhando
2. Rodar (FAIL)
3. Implementar
4. Rodar (PASS)
5. Commit

Lista resumida:

#### Task 6: Service `remover_nf_do_espelho` (S11)

```python
def remover_nf_do_espelho(sep_id):
    """Seta numero_nf=NULL em todas linhas do espelho da sep (S11=a)."""
    from app.separacao.models import Separacao
    Separacao.query.filter_by(separacao_lote_id=f'ASSAI-SEP-{sep_id}').update(
        {'numero_nf': None}
    )
```

Teste: criar sep + linhas com numero_nf, chamar service, verificar NULL.

#### Task 7: Service `cancelar_nf_qpa` esqueleto (sem cascata)

Implementação base seguindo §9.1 da spec — apenas marcar NF como CANCELADA + reverter eventos básicos.

**M1 fix CRITICO** — `sep` pode ser `None` (NF NAO_RECONCILIADO sem separacao_id, como as 30 NFs órfãs em prod).
**TODOS os usos de `sep.X` devem ser guardados com `if sep:`** ou capturados em variavel intermediaria com early return:

```python
def cancelar_nf_qpa(nf_id, motivo, operador_id):
    nf = AssaiNfQpa.query.get_or_404(nf_id)
    if nf.status_match == NF_STATUS_CANCELADA:
        raise ValidationError('NF ja cancelada')

    sep = nf.separacao  # pode ser None (NF orfa)

    # ... reverter eventos por chassi (loop nf.itens — nao depende de sep) ...

    nf.status_match = NF_STATUS_CANCELADA
    nf.cancelada_em = agora_brasil_naive()
    nf.cancelada_por_id = operador_id
    nf.motivo_cancelamento = motivo

    # M1 fix: guard sep is None em TODOS os usos
    if sep:
        # Tasks 8-11 cobertas pelos blocos abaixo, todos guardados
        pass

    return nf
```

**Teste obrigatorio**: `test_cancelar_nf_orfa_sem_sep_nao_quebra`. Cria NF NAO_RECONCILIADO sem separacao_id, chama cancelar_nf_qpa, verifica que retorna sem AttributeError. Status vira CANCELADA.

#### Task 8: `cancelar_nf_qpa` — reverter sep status (R5.1 + R5.3)

Sep volta a CARREGADA (se tem Carregamento) ou FECHADA (se não tem).

```python
# M1 fix: guard
if sep:
    if sep.status == SEPARACAO_STATUS_FATURADA:
        tem_carregamento = AssaiCarregamento.query.filter_by(
            separacao_id=sep.id, status=CARREGAMENTO_STATUS_FINALIZADO,
        ).first()
        sep.status = SEPARACAO_STATUS_CARREGADA if tem_carregamento else SEPARACAO_STATUS_FECHADA
```

#### Task 9: `cancelar_nf_qpa` — limpar EmbarqueItem.nota_fiscal (S15)

```python
# Nao depende de sep — sempre executa (NFs orfas tambem podem ter EmbarqueItem
# vinculado se foram parcialmente processadas)
from app.fretes.models import EmbarqueItem
EmbarqueItem.query.filter_by(nota_fiscal=nf.numero).update({'nota_fiscal': None})
```

#### Task 10: `cancelar_nf_qpa` — vinculo_historico (S16)

```python
# Nao depende de sep — loop nas itens da NF
for item in nf.itens:
    if item.separacao_item_id:  # so se tinha vinculo
        db.session.add(AssaiNfQpaItemVinculoHistorico(
            nf_qpa_item_id=item.id,
            separacao_item_id=item.separacao_item_id,
            motivo='NF_CANCELADA',
            chassi_no_momento=item.chassi,
            registrado_por_id=operador_id,
            detalhes={'nf_id': nf.id, 'motivo_nf': motivo},
        ))
        item.separacao_item_id = None
```

#### Task 11: `cancelar_nf_qpa` — recalcular_status_pedido + commit final

```python
# M1 fix: guard
if sep:
    recalcular_status_pedido(sep.pedido_id)
# Se NF orfa, nao ha pedido para recalcular (sep nao existe)
db.session.commit()
```

#### Task 12: Modal Expedição UI (S7=a X=Pular)

- Template `_modal_expedicao.html` com campos: expedicao (date input obrigatório), agendamento (date opcional), protocolo (text opcional), agendamento_confirmado (checkbox)
- Integração em `upload_nf.html` — abre modal automaticamente após upload se sep foi criada via S1=b
- JS `upload_nf_modal_expedicao.js` — submete via AJAX, redireciona para nf_detalhe
- Botões "Confirmar" + "Pular" (ambos válidos S7=a — tratamento idêntico de fechar X = Pular)

#### Task 13: Botão "Editar agendamento" em sep recém-criada (A10)

Reusar modal `#modal-agendamento-loja-<loja_id>` de Plano 5. Botão em `nf_detalhe.html` + `lista_separacoes.html`.

#### Tasks 14-22: UI Divergências

- Task 14: Rota + template `lista.html` em `/motos-assai/divergencias`
- Task 15: Filtros (pendentes/resolvidas/tipo)
- Task 16: AJAX endpoint `POST /divergencias/<id>/resolver`
- Tasks 17-21: 5 modais de resolução
- Task 22: JS `divergencias_modais.js`

#### Task 23: Botão "Cancelar NF" em `nf_detalhe.html`

Modal de confirmação com motivo obrigatório. AJAX para `POST /faturamento/nfs/<id>/cancelar`.

#### Task 24: Atualizar `base.html` — adicionar link "Divergências"

```html
{% if current_user.pode_acessar_motos_assai() %}
  <li><a class="dropdown-item" href="{{ url_for('motos_assai_divergencias.lista') }}">
    <i class="bi bi-exclamation-triangle"></i> Divergências
  </a></li>
{% endif %}
```

#### Task 25: Onboarding tour `/divergencias`

Driver.js seguindo padrão Plano 5.

#### Task 26: Migration 23 — backfill 30 NFs órfãs (Python-only A15)

```python
"""Migration 23: backfill NFs orfas — invoca ajustar_separacao_pela_nf v2.

A15: rodar MANUAL no Render Shell APOS deploy da Fase 4.
NAO incluir em build.sh.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db
from app.motos_assai.models import AssaiNfQpa, NF_STATUS_NAO_RECONCILIADO
from app.motos_assai.services.parsers.nf_qpa_adapter import ajustar_separacao_pela_nf


def main():
    app = create_app()
    with app.app_context():
        nfs_orfas = AssaiNfQpa.query.filter_by(status_match=NF_STATUS_NAO_RECONCILIADO).all()
        print(f'[start] {len(nfs_orfas)} NFs orfas')

        contadores = {'sucesso': 0, 'falhou': 0, 'sem_chassi_cadastrado': 0}
        log = []

        for nf in nfs_orfas:
            try:
                result = ajustar_separacao_pela_nf(nf.id, operador_id=1)  # operador admin
                db.session.commit()
                if result['ok']:
                    contadores['sucesso'] += 1
                    log.append(f'  ok nf={nf.numero} → sep_id={result.get("sep_id")}')
                else:
                    contadores['sem_chassi_cadastrado'] += 1
                    log.append(f'  skip nf={nf.numero} — {result["razao"]}')
            except Exception as e:
                db.session.rollback()
                contadores['falhou'] += 1
                log.append(f'  ERROR nf={nf.numero}: {e}')

        for line in log:
            print(line)

        print(f'\n[done] sucesso: {contadores["sucesso"]}, '
              f'sem_chassi: {contadores["sem_chassi_cadastrado"]}, '
              f'falhou: {contadores["falhou"]}')


if __name__ == '__main__':
    main()
```

#### Tasks 27-30: Smoke tests + Deploy

- Task 27: E2E test fluxo NF antes da sep (importar PDF → modal Expedição → sep FATURADA)
- Task 28: E2E test cancelar NF (sep volta CARREGADA + EmbarqueItem limpo + vinculo_historico)
- Task 29: E2E test divergência + resolução (criar div manual → resolver via UI → re-roda match)
- Task 30: Deploy + Migration 23 manual no Render Shell

```bash
git push origin feature/motos-assai-fase4-nf-divergencias
gh pr create --title "feat(motos-assai): Fase 4 NF + Divergências + Cancelar NF"

# Após merge, no Render Shell:
cd /opt/render/project/src
python scripts/migrations/motos_assai_23_backfill_nfs_orfas.py
```

Validar resultado:
```bash
psql $DATABASE_URL -c "SELECT status_match, COUNT(*) FROM assai_nf_qpa GROUP BY status_match;"
# Esperado: NAO_RECONCILIADO baixou de 30 para próximo de 0
```

---

## Self-review (executor)

- Plano 1 + 2 deployados
- 30 tasks, estimativa 30-40h
- Migration 23 é o ÚLTIMO passo (após código novo deployado)
