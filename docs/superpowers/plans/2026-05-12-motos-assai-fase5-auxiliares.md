# Motos Assaí — Fase 5 (Substituir chassi + UI vincular NF + Parser CCe) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar serviços auxiliares: substituir chassi entre lojas (§11 — manual e via NF), UI vincular NF manualmente para casos não cobertos pelo backfill (§15.6 — ferramenta excepcional), parser de Carta de Correção (CCe) com fallback LLM (§7.3). Cancelar pedido (§10) **NÃO** está nesta fase — é roadmap futuro.

**Architecture:** Service `substituir_chassi_entre_seps` em `separacao_service.py`. Detecção de CHASSI_OUTRA_LOJA em `registrar_chassi` (sep) e `escanear_carregamento_item` (carregamento). Service `vincular_nf_manualmente` em `nf_qpa_adapter.py` (atalho de `ajustar_separacao_pela_nf` v2). Parser CCe em novo arquivo `parsers/cce_pdf_extractor.py` + fallback LLM em `parsers/cce_llm_fallback.py` (segue padrão de `qpa_pedido_*` da Fase 2 do plano original do módulo). Service `aplicar_correcao_cce` em `cancelamento_nf_service.py` (mesmo arquivo de cancelar_nf_qpa).

**Tech Stack:** Flask, SQLAlchemy, PostgreSQL, pdfplumber 0.10+, Anthropic SDK 0.98+ (Haiku 4.5 → Sonnet 4.6 fallback).

**Spec referenciada:** `docs/superpowers/specs/2026-05-12-motos-assai-carregamento-divergencia-design.md` (v1.2) §7.3, §11, §15.6

**Pré-requisito:** Planos 1 + 2 + 3 completos e deployados.

---

## File Structure

### Services a criar/modificar

- **MODIFY** `app/motos_assai/services/separacao_service.py` — adicionar `substituir_chassi_entre_seps()` + detecção CHASSI_OUTRA_LOJA em `registrar_chassi()`
- **MODIFY** `app/motos_assai/services/carregamento_service.py` — detecção CHASSI_OUTRA_LOJA em `escanear_carregamento_item()`
- **MODIFY** `app/motos_assai/services/parsers/nf_qpa_adapter.py` — `vincular_nf_manualmente()` (wrapper de ajustar_separacao_pela_nf)
- **MODIFY** `app/motos_assai/services/cancelamento_nf_service.py` — adicionar `aplicar_correcao_cce()`

### Parsers CCe (novos)

- `app/motos_assai/services/parsers/cce_pdf_extractor.py` — parser determinístico
- `app/motos_assai/services/parsers/cce_llm_fallback.py` — fallback Haiku → Sonnet

### Routes a modificar

- `app/motos_assai/routes/separacao.py` — adicionar AJAX `POST /separacao/substituir-chassi`
- `app/motos_assai/routes/carregamento.py` — modificar `escanear_chassi_ajax` para retornar `cenario=CHASSI_OUTRA_LOJA`
- `app/motos_assai/routes/faturamento.py` — adicionar `POST /faturamento/nfs/<id>/vincular-manual`
- `app/motos_assai/routes/divergencias.py` — adicionar `POST /divergencias/<id>/upload-cce`

### Templates a criar/modificar

- `app/templates/motos_assai/separacao/_modal_substituir_chassi.html` (novo — incluído em `tela.html`)
- `app/templates/motos_assai/carregamento/_modal_substituir_chassi.html` (novo — incluído em `escanear.html`)
- `app/templates/motos_assai/faturamento/_modal_vincular_nf.html` (novo)
- `app/templates/motos_assai/faturamento/lista_separacoes.html` (modificar — botão "Vincular" no painel NFs órfãs)
- `app/templates/motos_assai/divergencias/_modal_upload_cce.html` (modificar — placeholder de Plano 3 vira funcional)

### Tests a criar

- `tests/motos_assai/test_substituir_chassi.py`
- `tests/motos_assai/test_vincular_nf_manual.py`
- `tests/motos_assai/test_parser_cce.py`
- `tests/motos_assai/test_aplicar_correcao_cce.py`

---

## Tasks

### Task 1: Service `substituir_chassi_entre_seps` (S20 + A4)

**Files:**
- Modify: `app/motos_assai/services/separacao_service.py`
- Create: `tests/motos_assai/test_substituir_chassi.py`

- [ ] **Step 1: Escrever testes**

```python
"""Testes substituir_chassi_entre_seps (S20=a + A4 + CR-2/CR-10/CR-11)."""
import pytest
from app import create_app, db
from app.motos_assai.models import *
from app.motos_assai.services.moto_evento_service import emitir_evento, status_efetivo


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.rollback()
        db.drop_all()


@pytest.fixture
def setup_2_lojas(app):
    cd = AssaiCd(nome='CD', cnpj='12345678000100')
    loja_a = AssaiLoja(numero=1, cnpj='1', nome='LA')
    loja_b = AssaiLoja(numero=2, cnpj='2', nome='LB')
    modelo = AssaiModelo(codigo='SOL')
    db.session.add_all([cd, loja_a, loja_b, modelo])
    db.session.flush()
    pedido = AssaiPedidoVenda(numero='T', cd_id=cd.id)
    db.session.add(pedido)
    db.session.flush()
    return cd, loja_a, loja_b, modelo, pedido


def test_s20a_eventos_atual_disponivel_separada_quando_origem_separada(setup_2_lojas):
    """S20=a: sequencia de eventos <atual> → DISPONIVEL → SEPARADA."""
    cd, loja_a, loja_b, modelo, pedido = setup_2_lojas

    # Sep_A em LA, status SEPARADA, com chassi C001
    sep_a = AssaiSeparacao(pedido_id=pedido.id, loja_id=loja_a.id, status=SEPARACAO_STATUS_FECHADA)
    db.session.add(sep_a)
    db.session.flush()
    moto = AssaiMoto(chassi='C001', modelo_id=modelo.id, cor='Preto')
    db.session.add(moto)
    db.session.flush()
    db.session.add(AssaiSeparacaoItem(separacao_id=sep_a.id, chassi='C001', modelo_id=modelo.id, valor_unitario_qpa=1000.0))
    for ev in [EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_DISPONIVEL, EVENTO_SEPARADA]:
        emitir_evento('C001', ev, operador_id=1)

    # Sep_B em LB, EM_SEPARACAO, vazia
    sep_b = AssaiSeparacao(pedido_id=pedido.id, loja_id=loja_b.id, status=SEPARACAO_STATUS_EM_SEPARACAO)
    db.session.add(sep_b)
    db.session.commit()

    from app.motos_assai.services.separacao_service import substituir_chassi_entre_seps
    substituir_chassi_entre_seps('C001', sep_a.id, sep_b.id, operador_id=2)
    db.session.commit()

    # Eventos: SEPARADA → DISPONIVEL → SEPARADA (3 novos eventos)
    eventos = (AssaiMotoEvento.query
               .filter_by(chassi='C001')
               .order_by(AssaiMotoEvento.ocorrido_em.desc(), AssaiMotoEvento.id.desc())
               .limit(2).all())
    # Ultimo evento: SEPARADA (no destino)
    assert eventos[0].tipo == EVENTO_SEPARADA
    # Penultimo evento: DISPONIVEL
    assert eventos[1].tipo == EVENTO_DISPONIVEL

    # Item migrado para sep_b
    assert AssaiSeparacaoItem.query.filter_by(separacao_id=sep_a.id, chassi='C001').first() is None
    assert AssaiSeparacaoItem.query.filter_by(separacao_id=sep_b.id, chassi='C001').first() is not None


def test_s20a_excel_origem_regenerado_sempre(setup_2_lojas):
    """S20: Excel da sep_origem SEMPRE regenerado (chassi a menos)."""
    cd, loja_a, loja_b, modelo, pedido = setup_2_lojas

    sep_a = AssaiSeparacao(pedido_id=pedido.id, loja_id=loja_a.id, status=SEPARACAO_STATUS_CARREGADA)
    db.session.add(sep_a)
    db.session.flush()
    moto = AssaiMoto(chassi='C001', modelo_id=modelo.id, cor='Preto')
    db.session.add(moto)
    db.session.flush()
    db.session.add(AssaiSeparacaoItem(separacao_id=sep_a.id, chassi='C001', modelo_id=modelo.id, valor_unitario_qpa=1000.0))
    db.session.add(AssaiPedidoExcel(
        pedido_id=pedido.id, separacao_id=sep_a.id,
        s3_key='legado.xlsx', versao=1, ativo=True,
    ))
    sep_b = AssaiSeparacao(pedido_id=pedido.id, loja_id=loja_b.id, status=SEPARACAO_STATUS_EM_SEPARACAO)
    db.session.add(sep_b)
    db.session.commit()

    from app.motos_assai.services.separacao_service import substituir_chassi_entre_seps
    substituir_chassi_entre_seps('C001', sep_a.id, sep_b.id, operador_id=2)
    db.session.commit()

    # Excel sep_a versao 1 desativada + nova versao 2 ativa
    excels_a = AssaiPedidoExcel.query.filter_by(separacao_id=sep_a.id).order_by(AssaiPedidoExcel.versao).all()
    assert len(excels_a) == 2
    assert excels_a[0].ativo is False
    assert excels_a[1].ativo is True
    assert 'substituicao' in excels_a[1].motivo_regeneracao.lower()


def test_cr11_sep_destino_carregada_eh_aceita(setup_2_lojas):
    """CR-11: sep destino pode estar CARREGADA tambem."""
    cd, loja_a, loja_b, modelo, pedido = setup_2_lojas
    moto = AssaiMoto(chassi='C001', modelo_id=modelo.id, cor='Preto')
    db.session.add(moto)
    db.session.flush()

    sep_a = AssaiSeparacao(pedido_id=pedido.id, loja_id=loja_a.id, status=SEPARACAO_STATUS_FECHADA)
    db.session.add(sep_a)
    db.session.flush()
    db.session.add(AssaiSeparacaoItem(separacao_id=sep_a.id, chassi='C001', modelo_id=modelo.id, valor_unitario_qpa=1000.0))

    sep_b = AssaiSeparacao(pedido_id=pedido.id, loja_id=loja_b.id, status=SEPARACAO_STATUS_CARREGADA)
    db.session.add(sep_b)
    db.session.commit()

    from app.motos_assai.services.separacao_service import substituir_chassi_entre_seps
    substituir_chassi_entre_seps('C001', sep_a.id, sep_b.id, operador_id=1)
    db.session.commit()

    assert AssaiSeparacaoItem.query.filter_by(separacao_id=sep_b.id, chassi='C001').first() is not None


def test_cr2_origem_faturada_cria_divergencia_chassi_outra_loja(setup_2_lojas):
    """CR-2: sep origem FATURADA cria divergencia tipo CHASSI_OUTRA_LOJA (nao CARREGAMENTO_FORA_NF)."""
    cd, loja_a, loja_b, modelo, pedido = setup_2_lojas
    moto = AssaiMoto(chassi='C001', modelo_id=modelo.id, cor='Preto')
    db.session.add(moto)
    db.session.flush()

    sep_a = AssaiSeparacao(pedido_id=pedido.id, loja_id=loja_a.id, status=SEPARACAO_STATUS_FATURADA)
    db.session.add(sep_a)
    db.session.flush()
    db.session.add(AssaiSeparacaoItem(separacao_id=sep_a.id, chassi='C001', modelo_id=modelo.id, valor_unitario_qpa=1000.0))

    nf_a = AssaiNfQpa(
        chave_44='1'*44, numero='N1', loja_id=loja_a.id, separacao_id=sep_a.id,
        status_match=NF_STATUS_BATEU,
    )
    db.session.add(nf_a)

    sep_b = AssaiSeparacao(pedido_id=pedido.id, loja_id=loja_b.id, status=SEPARACAO_STATUS_FECHADA)
    db.session.add(sep_b)
    db.session.commit()

    from app.motos_assai.services.separacao_service import substituir_chassi_entre_seps
    substituir_chassi_entre_seps('C001', sep_a.id, sep_b.id, operador_id=1)
    db.session.commit()

    # CR-2: tipo correto eh CHASSI_OUTRA_LOJA
    div = AssaiDivergencia.query.filter_by(
        tipo=DIVERGENCIA_TIPO_CHASSI_OUTRA_LOJA, chassi='C001',
    ).first()
    assert div is not None
    assert div.nf_id == nf_a.id  # CR-10: query funcionou (sem usar sep_origem.nf)
```

- [ ] **Step 2: Rodar — devem falhar**

```bash
pytest tests/motos_assai/test_substituir_chassi.py -v
```

- [ ] **Step 3: Implementar `substituir_chassi_entre_seps` em `separacao_service.py`**

```python
def substituir_chassi_entre_seps(chassi, sep_origem_id, sep_destino_id, operador_id):
    """Move chassi entre seps com regenerar Excel + atualizar mirror Nacom.

    S20=a: eventos <atual> → DISPONIVEL → SEPARADA (3 eventos sempre).
    CR-11: sep_destino aceita EM_SEPARACAO, FECHADA, CARREGADA. FATURADA bloqueada.
    CR-2: sep_origem FATURADA gera divergencia tipo CHASSI_OUTRA_LOJA.
    CR-10: usa query AssaiNfQpa.query.filter_by (nao usa relationship reverse).
    S10: chama recalcular_status_pedido em ambos pedidos.

    Args:
        chassi: chassi a mover
        sep_origem_id: sep onde chassi esta hoje
        sep_destino_id: sep para onde mover
        operador_id: usuario que solicitou

    Raises:
        SeparacaoValidationError: chassi nao esta na sep origem, ou sep destino invalida
    """
    # Lock pessimista
    moto = AssaiMoto.query.filter_by(chassi=chassi).with_for_update().first()
    if not moto:
        raise SeparacaoValidationError(f'Chassi {chassi} nao cadastrado')

    sep_origem = AssaiSeparacao.query.get(sep_origem_id)
    sep_destino = AssaiSeparacao.query.get(sep_destino_id)

    # Pre-condicoes
    if sep_destino.status not in (
        SEPARACAO_STATUS_EM_SEPARACAO,
        SEPARACAO_STATUS_FECHADA,
        SEPARACAO_STATUS_CARREGADA,
    ):
        raise SeparacaoValidationError(
            f'Sep destino {sep_destino_id} esta {sep_destino.status} — invalida. '
            'Esperado: EM_SEPARACAO, FECHADA ou CARREGADA. '
            'Para FATURADA, cancele a NF (cancelar_nf_qpa) primeiro.'
        )

    item_origem = AssaiSeparacaoItem.query.filter_by(
        separacao_id=sep_origem_id, chassi=chassi,
    ).first()
    if not item_origem:
        raise SeparacaoValidationError(f'Chassi {chassi} nao esta na sep {sep_origem_id}')

    valor_unit_origem = item_origem.valor_unitario_qpa
    db.session.delete(item_origem)

    # S20=a: eventos <atual> → DISPONIVEL → SEPARADA
    estado_atual = status_efetivo(chassi)
    emitir_evento(chassi, EVENTO_DISPONIVEL, operador_id=operador_id,
                  observacao=f'substituicao cross-loja sep {sep_origem_id} → sep {sep_destino_id}',
                  dados_extras={'sep_origem_id': sep_origem_id, 'estado_anterior': estado_atual})

    db.session.add(AssaiSeparacaoItem(
        separacao_id=sep_destino_id, chassi=chassi,
        modelo_id=moto.modelo_id,
        valor_unitario_qpa=valor_unit_origem,
    ))
    emitir_evento(chassi, EVENTO_SEPARADA, operador_id=operador_id,
                  observacao=f'substituicao cross-loja vindo de sep {sep_origem_id}',
                  dados_extras={'sep_destino_id': sep_destino_id})

    # CR-2 + CR-10: sep_origem FATURADA → divergencia CHASSI_OUTRA_LOJA
    if sep_origem.status == SEPARACAO_STATUS_FATURADA:
        nf_origem = AssaiNfQpa.query.filter_by(separacao_id=sep_origem_id).first()
        from app.motos_assai.services.divergencia_service import criar_divergencia
        criar_divergencia(
            tipo=DIVERGENCIA_TIPO_CHASSI_OUTRA_LOJA,
            chassi=chassi, sep_id=sep_origem_id,
            nf_id=nf_origem.id if nf_origem else None,
            detalhes={
                'motivo': 'chassi removido de NF FATURADA por substituicao cross-loja',
                'sep_destino_id': sep_destino_id,
                'loja_origem': sep_origem.loja_id,
                'loja_destino': sep_destino.loja_id,
            },
        )

    # S20: regenerar Excel sep_origem SEMPRE
    from app.motos_assai.services.faturamento_service import regenerar_excel_qpa
    regenerar_excel_qpa(sep_origem_id, operador_id, motivo='substituicao cross-loja: chassi removido')

    # Regenerar Excel sep_destino se ja tinha
    excel_destino = AssaiPedidoExcel.query.filter_by(separacao_id=sep_destino_id, ativo=True).first()
    if excel_destino:
        regenerar_excel_qpa(sep_destino_id, operador_id, motivo='substituicao cross-loja: chassi adicionado')

    # Atualizar mirror Nacom em ambos
    from app.motos_assai.services.separacao_mirror_service import sincronizar_espelho_com_separacao
    sincronizar_espelho_com_separacao(sep_origem_id)
    sincronizar_espelho_com_separacao(sep_destino_id)

    # S10: recalcular pedido
    from app.motos_assai.services.pedido_status_service import recalcular_status_pedido
    recalcular_status_pedido(sep_origem.pedido_id)
    if sep_destino.pedido_id != sep_origem.pedido_id:
        recalcular_status_pedido(sep_destino.pedido_id)

    db.session.flush()
```

- [ ] **Step 4: Rodar testes**

```bash
pytest tests/motos_assai/test_substituir_chassi.py -v
```

- [ ] **Step 5: Commit**

```bash
git add app/motos_assai/services/separacao_service.py tests/motos_assai/test_substituir_chassi.py
git commit -m "feat(motos-assai): substituir_chassi_entre_seps (S20=a + CR-2/CR-10/CR-11)"
```

---

### Task 2: Detecção CHASSI_OUTRA_LOJA em `registrar_chassi` (separacao)

**Files:**
- Modify: `app/motos_assai/services/separacao_service.py`
- Create: `tests/motos_assai/test_registrar_chassi_outra_loja.py`

- [ ] **Step 1: Escrever teste**

```python
def test_registrar_chassi_em_outra_loja_detecta_e_retorna_cenario(app):
    # ... setup com chassi em sep_loja_a ...
    # Tentar registrar em sep_loja_b
    from app.motos_assai.services.separacao_service import registrar_chassi, SeparacaoCrossLojaError

    with pytest.raises(SeparacaoCrossLojaError) as exc:
        registrar_chassi(sep_loja_b.id, 'C001', operador_id=1)

    assert exc.value.sep_origem_id == sep_loja_a.id
    assert exc.value.loja_origem_id == loja_a.id
```

- [ ] **Step 2-5: Implementar nova exception + dispatch em `registrar_chassi`**

```python
class SeparacaoCrossLojaError(SeparacaoError):
    """Chassi esta em sep ativa de outra loja — operador deve confirmar substituicao."""
    def __init__(self, msg, *, sep_origem_id, loja_origem_id, sep_destino_id, loja_destino_id):
        super().__init__(msg)
        self.sep_origem_id = sep_origem_id
        self.loja_origem_id = loja_origem_id
        self.sep_destino_id = sep_destino_id
        self.loja_destino_id = loja_destino_id


def registrar_chassi(sep_id, chassi, operador_id):
    # ... codigo existente ...

    # NOVO: antes de validar status_efetivo, checar CHASSI_OUTRA_LOJA
    sep_destino = AssaiSeparacao.query.get(sep_id)
    sep_outra_loja = (AssaiSeparacao.query
                      .join(AssaiSeparacaoItem)
                      .filter(
                          AssaiSeparacaoItem.chassi == chassi,
                          AssaiSeparacao.status.in_([
                              SEPARACAO_STATUS_EM_SEPARACAO, SEPARACAO_STATUS_FECHADA,
                              SEPARACAO_STATUS_CARREGADA, SEPARACAO_STATUS_FATURADA,
                          ]),
                          AssaiSeparacao.loja_id != sep_destino.loja_id,
                      )
                      .first())
    if sep_outra_loja:
        raise SeparacaoCrossLojaError(
            f'Chassi {chassi} esta em Sep #{sep_outra_loja.id} (Loja {sep_outra_loja.loja_id}). '
            f'Confirme substituicao para Sep #{sep_id} (Loja {sep_destino.loja_id}).',
            sep_origem_id=sep_outra_loja.id,
            loja_origem_id=sep_outra_loja.loja_id,
            sep_destino_id=sep_id,
            loja_destino_id=sep_destino.loja_id,
        )

    # ... resto da logica ...
```

E ajustar route AJAX para retornar 409 com cenário cross_loja:
```python
@separacao_bp.route('/registrar-chassi', methods=['POST'])
def registrar_chassi_ajax():
    try:
        item = registrar_chassi(...)
        return jsonify({'ok': True, ...})
    except SeparacaoCrossLojaError as e:
        return jsonify({
            'ok': False, 'cenario': 'cross_loja',
            'sep_origem_id': e.sep_origem_id, 'loja_origem_id': e.loja_origem_id,
            'sep_destino_id': e.sep_destino_id, 'loja_destino_id': e.loja_destino_id,
            'msg': str(e),
        }), 409
```

Commit.

---

### Task 3: Detecção CHASSI_OUTRA_LOJA em `escanear_carregamento_item`

Mesmo padrão da Task 2, mas em `carregamento_service.escanear_carregamento_item`. Nova exception `CarregamentoCrossLojaError`.

---

### Tasks 4-5: Modais "Substituir chassi" UI (sep + carregamento)

#### Task 4: Modal em `separacao/tela.html`

`_modal_substituir_chassi.html`:

```html
<div class="modal fade" id="modal-substituir-chassi" tabindex="-1">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <h5>Chassi em outra loja</h5>
        <button class="btn-close" data-bs-dismiss="modal"></button>
      </div>
      <div class="modal-body">
        <p>O chassi <strong id="cross-chassi"></strong> esta em <strong id="cross-loja-origem"></strong>.</p>
        <p>Deseja remover de la e adicionar a <strong id="cross-loja-destino"></strong>?</p>
      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
        <button class="btn btn-danger" id="btn-confirmar-substituir">Substituir</button>
      </div>
    </div>
  </div>
</div>
```

JS handler em `separacao_chassi.js`: ao receber 409 com `cenario=cross_loja`, abrir modal preenchendo dados; ao confirmar, AJAX para `POST /motos-assai/separacao/substituir-chassi` com IDs.

#### Task 5: Modal em `carregamento/escanear.html`

Mesmo padrão. JS em `carregamento_escanear.js`.

---

### Task 6: Service `vincular_nf_manualmente` + UI

**Files:**
- Modify: `app/motos_assai/services/parsers/nf_qpa_adapter.py`
- Modify: `app/motos_assai/routes/faturamento.py`
- Modify: `app/templates/motos_assai/faturamento/lista_separacoes.html`
- Create: `app/templates/motos_assai/faturamento/_modal_vincular_nf.html`

- [ ] **Step 1: Implementar `vincular_nf_manualmente`**

```python
def vincular_nf_manualmente(nf_id, pedido_id, loja_id, operador_id):
    """Atalho de ajustar_separacao_pela_nf que aceita pedido_id e loja_id explicitos.

    Usado quando NF NAO_RECONCILIADO precisa ser vinculada manualmente
    (ex: chassi nao existe em assai_moto e operador escolhe pedido+loja diretamente).

    Spec: §15.6 — ferramenta excepcional apos backfill Migration 23.
    """
    nf = AssaiNfQpa.query.get_or_404(nf_id)
    if nf.status_match != NF_STATUS_NAO_RECONCILIADO:
        raise ValueError(f'NF {nf_id} esta {nf.status_match}, nao NAO_RECONCILIADO')

    # Forca loja_id da NF (caso nao tenha sido detectado pelo regex automatico)
    if not nf.loja_id:
        nf.loja_id = loja_id
        db.session.flush()

    # Reusa logica de ajustar_separacao_pela_nf v2 (que cria sep em FATURADA - S1=b)
    return ajustar_separacao_pela_nf(nf.id, operador_id)
```

- [ ] **Step 2: Modal em `lista_separacoes.html`**

Adicionar botão "Vincular" em cada linha do painel "NFs órfãs":

```html
<button class="btn btn-sm btn-warning"
        data-bs-toggle="modal"
        data-bs-target="#modal-vincular-nf"
        data-nf-id="{{ nf.id }}"
        data-nf-numero="{{ nf.numero }}">
  <i class="bi bi-link"></i> Vincular
</button>
```

`_modal_vincular_nf.html`: form com select de pedido + loja + botão confirmar.

- [ ] **Step 3: AJAX endpoint**

```python
@faturamento_bp.route('/nfs/<int:id>/vincular-manual', methods=['POST'])
def vincular_nf_manual_ajax(id):
    pedido_id = int(request.json['pedido_id'])
    loja_id = int(request.json['loja_id'])
    try:
        result = vincular_nf_manualmente(id, pedido_id, loja_id, operador_id=current_user.id)
        db.session.commit()
        return jsonify({'ok': result['ok'], 'sep_id': result.get('sep_id')})
    except ValueError as e:
        db.session.rollback()
        return jsonify({'ok': False, 'msg': str(e)}), 400
```

- [ ] **Step 4: Tests + Commit**

```python
def test_vincular_nf_manualmente_cria_sep(app):
    # ... setup NF NAO_RECONCILIADO + chassis cadastrados ...
    result = vincular_nf_manualmente(nf.id, pedido.id, loja.id, operador_id=1)
    db.session.commit()
    assert result['ok'] is True
    sep = AssaiSeparacao.query.get(result['sep_id'])
    assert sep.status == SEPARACAO_STATUS_FATURADA
```

---

### Task 7: Parser CCe — base structure (`cce_pdf_extractor.py`)

**Files:**
- Create: `app/motos_assai/services/parsers/cce_pdf_extractor.py`
- Create: `tests/motos_assai/test_parser_cce.py`
- Create: `tests/motos_assai/fixtures/cce_exemplo.pdf` (manual ou gerado)

- [ ] **Step 1: Estrutura base do parser**

```python
"""Parser deterministico de Carta de Correcao Eletronica (CCe) de NF-e.

Spec: §7.3
Plano: docs/superpowers/plans/2026-05-12-motos-assai-fase5-auxiliares.md Task 7

Extrai do PDF da CCe:
- numero_cce (formato: CCe-XXX-AAAA)
- numero_nf_referenciada (NF original)
- chassis_corrigidos: list[(chassi_antigo, chassi_novo)]
- justificativa
- data_emissao
"""
import pdfplumber
import re


REGEX_NUMERO_CCE = re.compile(r'CC[Ee][\s\-]*([\dA-Z\-]+)')
REGEX_NUMERO_NF = re.compile(r'(?:NF[\-\s]?e?|Nota Fiscal)[\s\:\-]*(\d+)')
REGEX_CHASSI = re.compile(r'\b([0-9A-HJ-NPR-Z]{17})\b')


class CceParseError(Exception):
    pass


def extrair_cce(pdf_bytes):
    """Extrai dados estruturados de PDF de CCe.

    Returns:
        dict: {numero_cce, numero_nf_referenciada, chassis_corrigidos, justificativa, data_emissao, confianca}

    Raises:
        CceParseError: parser nao conseguiu extrair dados minimos.
    """
    import io
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        texto = '\n'.join(page.extract_text() or '' for page in pdf.pages)

    if not texto.strip():
        raise CceParseError('PDF sem texto extraivel')

    numero_cce_match = REGEX_NUMERO_CCE.search(texto)
    numero_nf_match = REGEX_NUMERO_NF.search(texto)
    chassis = REGEX_CHASSI.findall(texto)

    if not numero_nf_match:
        raise CceParseError('NF referenciada nao encontrada')

    confianca = 0.0
    if numero_cce_match:
        confianca += 0.3
    if numero_nf_match:
        confianca += 0.4
    if len(chassis) >= 2:
        confianca += 0.3

    # Heuristica: chassis em pares (antigo/novo)
    chassis_corrigidos = []
    if len(chassis) >= 2 and len(chassis) % 2 == 0:
        for i in range(0, len(chassis), 2):
            chassis_corrigidos.append((chassis[i], chassis[i+1]))

    return {
        'numero_cce': numero_cce_match.group(1) if numero_cce_match else None,
        'numero_nf_referenciada': numero_nf_match.group(1),
        'chassis_corrigidos': chassis_corrigidos,
        'justificativa': '',  # extracao mais sofisticada precisa LLM
        'data_emissao': None,
        'confianca': confianca,
    }
```

- [ ] **Step 2-5: Tests + Commit**

Testes leem fixture PDF (operador deve providenciar CCe real ou mock). Commit.

---

### Task 8: Parser CCe — fallback LLM

**Files:**
- Create: `app/motos_assai/services/parsers/cce_llm_fallback.py`

Padrão idêntico a `qpa_pedido_llm_fallback.py` da Fase 2 do módulo. Aciona Haiku 4.5 → Sonnet 4.6 quando `confianca < 0.80`.

```python
"""Fallback LLM para parser CCe.

Acionado quando cce_pdf_extractor.confianca < 0.80.
Escalada: Haiku 4.5 → Sonnet 4.6.

Padrao identico a qpa_pedido_llm_fallback.py.
"""
from anthropic import Anthropic

CONFIANCA_LIMIAR = 0.80
MODELO_HAIKU = 'claude-haiku-4-5-20251001'
MODELO_SONNET = 'claude-sonnet-4-6'


def extrair_cce_via_llm(pdf_bytes, modelo=MODELO_HAIKU):
    """Extrai CCe via LLM (PDF como document block nativo)."""
    import base64
    cliente = Anthropic()  # lazy init
    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode()

    prompt = """Extraia da Carta de Correcao Eletronica (CCe):
- numero_cce (formato CCe-XXX ou similar)
- numero_nf_referenciada (NF original sendo corrigida)
- chassis_corrigidos: pares (chassi_antigo, chassi_novo) que estao sendo trocados
- justificativa (texto explicativo da correcao)
- data_emissao (formato DD/MM/AAAA)

Retorne JSON: {numero_cce, numero_nf_referenciada, chassis_corrigidos: [[antigo, novo], ...],
justificativa, data_emissao, confianca: 0.0-1.0}"""

    response = cliente.messages.create(
        model=modelo, max_tokens=2048,
        messages=[{
            'role': 'user',
            'content': [
                {'type': 'document', 'source': {'type': 'base64', 'media_type': 'application/pdf', 'data': pdf_b64}},
                {'type': 'text', 'text': prompt},
            ],
        }],
    )

    import json
    return json.loads(response.content[0].text)
```

---

### Task 9: Service `aplicar_correcao_cce` (atualiza NfQpaItem + re-roda match)

**Files:**
- Modify: `app/motos_assai/services/cancelamento_nf_service.py`

```python
def aplicar_correcao_cce(nf_id, chassis_corrigidos, numero_cce, operador_id):
    """Aplica correcao CCe: substitui chassis em assai_nf_qpa_item.

    Args:
        nf_id: ID da NF original
        chassis_corrigidos: list[(chassi_antigo, chassi_novo)]
        numero_cce: numero da CCe (auditoria)
        operador_id: usuario que aplicou

    NAO commita.
    """
    nf = AssaiNfQpa.query.get_or_404(nf_id)
    if nf.status_match == NF_STATUS_CANCELADA:
        raise ValueError('NF cancelada — nao aplica CCe')

    for chassi_antigo, chassi_novo in chassis_corrigidos:
        item = AssaiNfQpaItem.query.filter_by(nf_id=nf_id, chassi=chassi_antigo).first()
        if not item:
            continue  # chassi antigo nao esta na NF — pular

        # S16: registrar vinculo historico antes de mudar
        if item.separacao_item_id:
            db.session.add(AssaiNfQpaItemVinculoHistorico(
                nf_qpa_item_id=item.id,
                separacao_item_id=item.separacao_item_id,
                motivo='CCE_ALTEROU_CHASSI',
                chassi_no_momento=chassi_antigo,
                registrado_por_id=operador_id,
                detalhes={'numero_cce': numero_cce, 'chassi_novo': chassi_novo},
            ))
            item.separacao_item_id = None  # limpa vinculo antigo

        item.chassi = chassi_novo

    # Re-roda match (S21 + A14)
    from app.motos_assai.services.parsers.nf_qpa_adapter import _calcular_match
    _calcular_match(nf, operador_id)
    db.session.flush()
```

Tests + commit.

---

### Task 10: UI upload PDF CCe (modal de divergência)

**Files:**
- Modify: `app/templates/motos_assai/divergencias/_modal_upload_cce.html`
- Modify: `app/motos_assai/routes/divergencias.py`
- Create: `app/static/motos_assai/js/upload_cce.js`

Modal com input file (.pdf), submete via FormData AJAX para `POST /divergencias/<id>/upload-cce`. Backend usa parser deterministico, fallback LLM se confianca baixa, chama `aplicar_correcao_cce`, marca divergência como resolvida.

```python
@divergencias_bp.route('/<int:id>/upload-cce', methods=['POST'])
def upload_cce_ajax(id):
    div = AssaiDivergencia.query.get_or_404(id)
    if div.tipo != DIVERGENCIA_TIPO_NF_CHASSI_FORA_CARREGAMENTO:
        return jsonify({'ok': False, 'msg': 'CCe so resolve NF_CHASSI_FORA_CARREGAMENTO'}), 400

    pdf_file = request.files.get('cce_pdf')
    if not pdf_file:
        return jsonify({'ok': False, 'msg': 'PDF obrigatorio'}), 400

    pdf_bytes = pdf_file.read()
    try:
        from app.motos_assai.services.parsers.cce_pdf_extractor import extrair_cce, CONFIANCA_LIMIAR as L
        dados = extrair_cce(pdf_bytes)

        if dados['confianca'] < 0.80:
            from app.motos_assai.services.parsers.cce_llm_fallback import extrair_cce_via_llm
            dados = extrair_cce_via_llm(pdf_bytes)

        if not dados.get('chassis_corrigidos'):
            return jsonify({'ok': False, 'msg': 'CCe nao tem chassis corrigidos identificados'}), 400

        from app.motos_assai.services.cancelamento_nf_service import aplicar_correcao_cce
        aplicar_correcao_cce(div.nf_id, dados['chassis_corrigidos'], dados['numero_cce'], current_user.id)

        from app.motos_assai.services.divergencia_service import resolver_divergencia
        resolver_divergencia(
            div.id, tipo_resolucao=DIVERGENCIA_RESOLUCAO_CCE,
            observacao=f'CCe {dados["numero_cce"]} aplicada — {len(dados["chassis_corrigidos"])} chassis trocados',
            operador_id=current_user.id,
        )

        db.session.commit()
        return jsonify({'ok': True, 'numero_cce': dados['numero_cce'], 'chassis_trocados': len(dados['chassis_corrigidos'])})
    except Exception as e:
        db.session.rollback()
        return jsonify({'ok': False, 'msg': str(e)}), 500
```

---

### Tasks 11-13: Smoke tests + Deploy

- Task 11: E2E substituir chassi (manual sep + via NF)
- Task 12: E2E vincular NF manualmente (NF órfã → sep FATURADA)
- Task 13: E2E parser CCe (upload PDF → divergência resolvida)
- Task 14: Deploy

```bash
git push origin feature/motos-assai-fase5-auxiliares
gh pr create --title "feat(motos-assai): Fase 5 — Substituir chassi + Vincular NF + Parser CCe"
```

Não há migrations novas. Apenas código.

---

## Self-review (executor)

- Planos 1+2+3 deployados em prod
- Migration 23 (Plano 3) ja executada
- Estimativa: 15-25h
- Cancelar pedido (§10) NÃO está nesta fase — roadmap futuro

## Próximos passos pós-Fase 5

Sistema Carregamento + Divergências + Cancelar NF + Substituir chassi cross-loja + CCe completos.

Roadmap futuro (sem plano):
- Cancelar pedido (§10 — caso raríssimo)
- Permissões granulares (§DUV3)
- Notificações operador (§DUV6)
- Migration drop coluna `tipo_divergencia` em `assai_nf_qpa_item` (apos garantir nenhum callsite legado)
