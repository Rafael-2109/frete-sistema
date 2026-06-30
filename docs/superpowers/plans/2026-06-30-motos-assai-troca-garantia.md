<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-30
-->
# Troca em Garantia (Motos Assaí) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Papel:** plano de implementação bite-sized (TDD, commits frequentes) da Troca em Garantia do módulo Motos Assaí. Derivado do spec aprovado `docs/superpowers/specs/2026-06-30-motos-assai-troca-garantia-design.md`.

**Goal:** Permitir que o Pós-venda registre uma troca em garantia (cliente do Assaí troca a moto defeituosa A por outra B do mesmo modelo, sem NF), trocando A→B dentro da própria NF Q.P.A. — B vira `FATURADA`, A vira `PENDENTE` — e vinculando o registro de pós-venda à NF para o Faturamento identificar a troca.

**Architecture:** Swap cirúrgico in-place (não usa `_calcular_match`, que ignora seps `FATURADA`, nem o delta de espelho, que bloqueia remoção de linha com `numero_nf`). Um serviço dedicado `troca_garantia_service.registrar_troca` muta `AssaiSeparacaoItem.chassi` A→B, religa o `AssaiNfQpaItem`, emite eventos diretos (`FATURADA` p/ B, `PENDENTE` p/ A) e troca `chassi_assai` no espelho Nacom in-place. O registro estruturado é uma `AssaiPosVendaOcorrencia` estendida (`tipo=TROCA_GARANTIA`, `chassi_substituto`, `nf_qpa_id`).

**Tech Stack:** Python 3.12, Flask 3.1, SQLAlchemy 2.0, PostgreSQL 18, pytest. Módulo `app/motos_assai/` (blueprint `motos_assai_bp`, prefix `/motos-assai`).

## Indice

- [Contexto](#contexto)
- [Global Constraints](#global-constraints)
- [File Structure](#file-structure)
- [Task 1: Migration + modelo](#task-1-migration--modelo-colunas-pós-venda--motivo-de-vínculo)
- [Task 2: Helper `trocar_chassi_no_espelho`](#task-2-helper-trocar_chassi_no_espelho)
- [Task 3: Serviço `registrar_troca`](#task-3-serviço-registrar_troca-swap-cirúrgico-ab)
- [Task 4: Picker de substitutos](#task-4-picker-de-substitutos-listar_substitutos)
- [Task 5: Guards + `listar_trocas_da_nf`](#task-5-guards-de-imutabilidade--listar_trocas_da_nf)
- [Task 6: Rotas Pós-venda + template](#task-6-rotas-pós-venda-form--registrar--substitutos-ajax--template)
- [Task 7: Reflexo no Faturamento](#task-7-reflexo-no-faturamento-badge--seção-no-detalhe-da-nf)
- [Task 8: Documentação + suíte](#task-8-documentação--suíte-completa-do-módulo)
- [Self-Review](#self-review-preenchido-pelo-autor-do-plano)

## Contexto

Processo de negócio não mapeado: vendemos motos ao Assaí (com NF Q.P.A.), o Assaí revende ao cliente final; quando a moto dá defeito, fazemos uma **troca em garantia** — pegamos a defeituosa de volta e entregamos outra do mesmo modelo, **sem NF** de devolução nem de saída. Hoje nenhum fluxo cobre isso (`pos_venda` é só relato textual; `devolucao_nfd` exige NFd; CCe troca chassi mas reverte para CARREGADA/SEPARADA e exige o novo chassi já em separação). O dono do produto decidiu modelar como **swap A→B na própria NF** (B vira `FATURADA`, A vira `PENDENTE`), centralizado no Pós-venda, fiscal só controle interno, sem leg nova de frete. Detalhes, decisões (D1–D6) e mecânica em `docs/superpowers/specs/2026-06-30-motos-assai-troca-garantia-design.md`.

## Global Constraints

- **Eventos de moto** emitidos via `app.motos_assai.services.moto_evento_service.emitir_evento(chassi, tipo, operador_id=None, observacao=None, dados_extras=None, ocorrido_em=None)` — **NÃO commita**, faz `flush`. Estado efetivo = `status_efetivo(chassi)` (último evento). Tipos válidos: ver `EVENTOS_VALIDOS` em `models/moto.py`. `PENDENTE`/`SEPARADA`/`FATURADA`/`DISPONIVEL` já existem (sem migration de evento).
- **Timezone**: datas/horas são **Brasil naive** (sem tzinfo) — usar `app.utils.timezone.agora_brasil_naive`. Ver `.claude/references/REGRAS_TIMEZONE.md`.
- **Migration** = par DDL `.sql` + script `.py` idempotente (padrão `scripts/migrations/motos_assai_33_*`). Após alterar coluna, **regenerar** o schema JSON da tabela.
- **Decorator** obrigatório em toda rota: `@login_required` + `@require_motos_assai` (de `app.motos_assai.decorators`).
- **Fiscal = só controle interno**: NÃO tocar `AssaiNfQpaItem.devolvido`; NÃO chamar `recalcular_status_pedido` (B substitui A na mesma NF; saldo do pedido inalterado).
- **`chassi`** sempre normalizado `.strip().upper()` (convenção de `emitir_evento` e dos serviços).
- Rodar testes com venv ativo: `source .venv/bin/activate` antes de `pytest`.

---

## File Structure

| Arquivo | Responsabilidade | Ação |
|---|---|---|
| `scripts/migrations/motos_assai_34_troca_garantia.sql` / `.py` | 3 colunas em `assai_pos_venda_ocorrencia` + `TROCA_GARANTIA` no CHECK `ck_assai_nf_qpa_item_vinculo_motivo` | Criar |
| `app/motos_assai/models/pos_venda.py` | Constantes `TIPO_*` + 3 colunas (`tipo`, `chassi_substituto`, `nf_qpa_id`) | Modificar |
| `app/motos_assai/models/nf_qpa_vinculo.py` | Constante `VINCULO_MOTIVO_TROCA_GARANTIA` + set | Modificar |
| `app/motos_assai/models/__init__.py` | Re-exportar as novas constantes | Modificar |
| `app/motos_assai/services/separacao_mirror_service.py` | Helper `trocar_chassi_no_espelho` | Modificar |
| `app/motos_assai/services/troca_garantia_service.py` | `registrar_troca` + `listar_substitutos` + `TrocaGarantiaError` | Criar |
| `app/motos_assai/services/pos_venda_service.py` | Guards de imutabilidade `TROCA_GARANTIA` + `listar_trocas_da_nf` | Modificar |
| `app/motos_assai/services/__init__.py` | Re-exportar novas funções | Modificar |
| `app/motos_assai/routes/pos_venda.py` | Rotas: form de troca, registrar (POST), substitutos (AJAX) | Modificar |
| `app/motos_assai/routes/faturamento.py` | Carregar trocas na lista + detalhe da NF | Modificar |
| `app/templates/motos_assai/pos_venda/troca_garantia.html` | Tela de registro da troca + picker de B | Criar |
| `app/templates/motos_assai/faturamento/nf_detalhe.html` | Seção "Troca em Garantia" + badge | Modificar |
| `app/templates/motos_assai/faturamento/lista_separacoes.html` | Badge "Troca" por NF | Modificar |
| `tests/motos_assai/test_troca_garantia.py` | Todos os testes (helper `_cenario` compartilhado) | Criar |
| `app/motos_assai/CLAUDE.md` | Documentar o fluxo de troca em garantia | Modificar |

---

## Task 1: Migration + modelo (colunas pós-venda + motivo de vínculo)

**Files:**
- Create: `scripts/migrations/motos_assai_34_troca_garantia.sql`
- Create: `scripts/migrations/motos_assai_34_troca_garantia.py`
- Modify: `app/motos_assai/models/pos_venda.py`
- Modify: `app/motos_assai/models/nf_qpa_vinculo.py`
- Modify: `app/motos_assai/models/__init__.py`
- Test: `tests/motos_assai/test_troca_garantia.py`

**Interfaces:**
- Produces: colunas `assai_pos_venda_ocorrencia.tipo` (varchar20, default `'RELATO'`), `.chassi_substituto` (varchar50, null), `.nf_qpa_id` (FK→`assai_nf_qpa.id`, null); constantes `TIPO_RELATO='RELATO'`, `TIPO_TROCA_GARANTIA='TROCA_GARANTIA'`, `POS_VENDA_TIPOS_VALIDOS`; `VINCULO_MOTIVO_TROCA_GARANTIA='TROCA_GARANTIA'` (+ em `VINCULO_MOTIVOS_VALIDOS`); CHECK `ck_assai_nf_qpa_item_vinculo_motivo` aceita `'TROCA_GARANTIA'`.

- [ ] **Step 1: Escrever a migration SQL**

Create `scripts/migrations/motos_assai_34_troca_garantia.sql`:

```sql
-- Migration 34: Troca em garantia.
-- (1) Estende assai_pos_venda_ocorrencia com tipo/chassi_substituto/nf_qpa_id.
-- (2) Adiciona TROCA_GARANTIA ao CHECK de assai_nf_qpa_item_vinculo_historico.motivo.
-- Padrao idempotente (DROP IF EXISTS + ADD).

BEGIN;

ALTER TABLE assai_pos_venda_ocorrencia
    ADD COLUMN IF NOT EXISTS tipo VARCHAR(20) NOT NULL DEFAULT 'RELATO';
ALTER TABLE assai_pos_venda_ocorrencia
    ADD COLUMN IF NOT EXISTS chassi_substituto VARCHAR(50);
ALTER TABLE assai_pos_venda_ocorrencia
    ADD COLUMN IF NOT EXISTS nf_qpa_id INTEGER REFERENCES assai_nf_qpa(id);

CREATE INDEX IF NOT EXISTS ix_assai_pos_venda_ocorrencia_nf_qpa_id
    ON assai_pos_venda_ocorrencia (nf_qpa_id);

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_assai_nf_qpa_item_vinculo_motivo') THEN
        ALTER TABLE assai_nf_qpa_item_vinculo_historico DROP CONSTRAINT ck_assai_nf_qpa_item_vinculo_motivo;
    END IF;
    ALTER TABLE assai_nf_qpa_item_vinculo_historico
        ADD CONSTRAINT ck_assai_nf_qpa_item_vinculo_motivo
        CHECK (motivo IN (
            'NF_CANCELADA', 'CCE_ALTEROU_CHASSI', 'SUBSTITUICAO_CROSS_LOJA',
            'TROCA_GARANTIA'
        ));
END $$;

COMMIT;
```

> **Nota:** se a CHECK `ck_assai_nf_qpa_item_vinculo_motivo` tiver outro nome no banco, confirme com `psql "$DATABASE_URL" -c "\d assai_nf_qpa_item_vinculo_historico"` e ajuste o `conname`. O bloco `DO $$` é idempotente: cria a CHECK se não existir.

- [ ] **Step 2: Escrever o script Python da migration**

Create `scripts/migrations/motos_assai_34_troca_garantia.py`:

```python
#!/usr/bin/env python3
"""Migration 34 — Troca em garantia.

(1) Estende assai_pos_venda_ocorrencia: tipo / chassi_substituto / nf_qpa_id.
(2) Adiciona TROCA_GARANTIA ao CHECK de assai_nf_qpa_item_vinculo_historico.motivo.
Idempotente; espelha o DDL de motos_assai_34_troca_garantia.sql.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


SQL = """
ALTER TABLE assai_pos_venda_ocorrencia
    ADD COLUMN IF NOT EXISTS tipo VARCHAR(20) NOT NULL DEFAULT 'RELATO';
ALTER TABLE assai_pos_venda_ocorrencia
    ADD COLUMN IF NOT EXISTS chassi_substituto VARCHAR(50);
ALTER TABLE assai_pos_venda_ocorrencia
    ADD COLUMN IF NOT EXISTS nf_qpa_id INTEGER REFERENCES assai_nf_qpa(id);
CREATE INDEX IF NOT EXISTS ix_assai_pos_venda_ocorrencia_nf_qpa_id
    ON assai_pos_venda_ocorrencia (nf_qpa_id);
"""

SQL_CHECK = """
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_assai_nf_qpa_item_vinculo_motivo') THEN
        ALTER TABLE assai_nf_qpa_item_vinculo_historico DROP CONSTRAINT ck_assai_nf_qpa_item_vinculo_motivo;
    END IF;
    ALTER TABLE assai_nf_qpa_item_vinculo_historico
        ADD CONSTRAINT ck_assai_nf_qpa_item_vinculo_motivo
        CHECK (motivo IN (
            'NF_CANCELADA', 'CCE_ALTEROU_CHASSI', 'SUBSTITUICAO_CROSS_LOJA',
            'TROCA_GARANTIA'
        ));
END $$;
"""


def main():
    app = create_app()
    with app.app_context():
        print('Migration 34: troca em garantia (colunas pos-venda + motivo vinculo)...')
        db.session.execute(text(SQL))
        db.session.execute(text(SQL_CHECK))
        db.session.commit()
        print('✅ Migration 34 aplicada')


if __name__ == '__main__':
    main()
```

- [ ] **Step 3: Rodar a migration no banco local de dev**

Run: `source .venv/bin/activate && python scripts/migrations/motos_assai_34_troca_garantia.py`
Expected: `✅ Migration 34 aplicada`

- [ ] **Step 4: Adicionar constantes + colunas ao model `pos_venda.py`**

In `app/motos_assai/models/pos_venda.py`, after the `ANEXO_TIPOS_VALIDOS` block (line 28), add:

```python
TIPO_RELATO = 'RELATO'
TIPO_TROCA_GARANTIA = 'TROCA_GARANTIA'
POS_VENDA_TIPOS_VALIDOS = {TIPO_RELATO, TIPO_TROCA_GARANTIA}
```

In the `AssaiPosVendaOcorrencia` class, after the `descricao` column (line 37), add:

```python
    tipo = db.Column(
        db.String(20), nullable=False, default=TIPO_RELATO, server_default='RELATO',
    )
    chassi_substituto = db.Column(db.String(50))
    nf_qpa_id = db.Column(
        db.Integer, db.ForeignKey('assai_nf_qpa.id'), index=True,
    )
```

- [ ] **Step 5: Adicionar constante de motivo a `nf_qpa_vinculo.py`**

In `app/motos_assai/models/nf_qpa_vinculo.py`, replace the constants block (lines 12-20) with:

```python
VINCULO_MOTIVO_NF_CANCELADA = 'NF_CANCELADA'
VINCULO_MOTIVO_CCE_ALTEROU_CHASSI = 'CCE_ALTEROU_CHASSI'
VINCULO_MOTIVO_SUBSTITUICAO_CROSS_LOJA = 'SUBSTITUICAO_CROSS_LOJA'
VINCULO_MOTIVO_TROCA_GARANTIA = 'TROCA_GARANTIA'

VINCULO_MOTIVOS_VALIDOS = {
    VINCULO_MOTIVO_NF_CANCELADA,
    VINCULO_MOTIVO_CCE_ALTEROU_CHASSI,
    VINCULO_MOTIVO_SUBSTITUICAO_CROSS_LOJA,
    VINCULO_MOTIVO_TROCA_GARANTIA,
}
```

- [ ] **Step 6: Re-exportar as novas constantes em `models/__init__.py`**

In `app/motos_assai/models/__init__.py`, find the import block from `.pos_venda` and add `TIPO_RELATO, TIPO_TROCA_GARANTIA, POS_VENDA_TIPOS_VALIDOS`; find the import block from `.nf_qpa_vinculo` and add `VINCULO_MOTIVO_TROCA_GARANTIA`. Add the same 4 names to the `__all__` list.

Run to verify the imports resolve:
```bash
source .venv/bin/activate && python -c "from app.motos_assai.models import TIPO_TROCA_GARANTIA, VINCULO_MOTIVO_TROCA_GARANTIA, POS_VENDA_TIPOS_VALIDOS; print('ok', TIPO_TROCA_GARANTIA, VINCULO_MOTIVO_TROCA_GARANTIA)"
```
Expected: `ok TROCA_GARANTIA TROCA_GARANTIA`

- [ ] **Step 7: Escrever o teste de round-trip do schema (e helper `_cenario`)**

Create `tests/motos_assai/test_troca_garantia.py`:

```python
"""Testes de Troca em Garantia (Motos Assai)."""
import uuid
from decimal import Decimal

import pytest

from app import db
from app.motos_assai.models import (
    AssaiModelo, AssaiLoja, AssaiMoto, AssaiPedidoVenda,
    AssaiSeparacao, AssaiSeparacaoItem,
    AssaiNfQpa, AssaiNfQpaItem, AssaiNfQpaItemVinculoHistorico,
    AssaiPosVendaOcorrencia,
    EVENTO_FATURADA, EVENTO_PENDENTE, EVENTO_DISPONIVEL,
    NF_STATUS_BATEU, SEPARACAO_STATUS_FATURADA,
    TIPO_RELATO, TIPO_TROCA_GARANTIA, VINCULO_MOTIVO_TROCA_GARANTIA,
    CATEGORIA_CLIENTE,
)
from app.motos_assai.services.moto_evento_service import emitir_evento, status_efetivo
from app.motos_assai.services.separacao_mirror_service import (
    mirror_assai_to_separacao, lote_id_de,
)
from app.separacao.models import Separacao


def _chave_44():
    base = '35260453780554000115550010000099' + str(uuid.uuid4().int)[-20:]
    return base[:44].ljust(44, '0')


def _cenario(admin, *, chassi_a=None, chassi_b=None, mesmo_modelo=True,
             estado_b=EVENTO_DISPONIVEL):
    """Monta cenario completo: venda Q.P.A. faturada (chassi A) + moto livre (B),
    incluindo o espelho Nacom com numero_nf. Retorna dict com handles."""
    suf = uuid.uuid4().hex[:6].upper()
    chassi_a = (chassi_a or f'LA2025TROCAA{suf}').upper()
    chassi_b = (chassi_b or f'LA2025TROCAB{suf}').upper()

    modelo = AssaiModelo(codigo=f'TRC{suf}', nome=f'Modelo {suf}', peso_kg=Decimal('50'))
    db.session.add(modelo)
    db.session.flush()
    modelo_b = modelo
    if not mesmo_modelo:
        modelo_b = AssaiModelo(codigo=f'TRD{suf}', nome=f'Outro {suf}', peso_kg=Decimal('50'))
        db.session.add(modelo_b)
        db.session.flush()

    loja = AssaiLoja(
        numero=f'9{suf[:3]}', nome='Loja Troca', razao_social='Loja Troca LTDA',
        cnpj='12345678000199', cidade='SAO PAULO', uf='SP',
    )
    db.session.add(loja)
    db.session.flush()

    moto_a = AssaiMoto(chassi=chassi_a, modelo_id=modelo.id, cor='PRETO')
    moto_b = AssaiMoto(chassi=chassi_b, modelo_id=modelo_b.id, cor='VERMELHO')
    db.session.add_all([moto_a, moto_b])
    db.session.flush()

    pedido = AssaiPedidoVenda(numero=f'VOE-{suf}')
    db.session.add(pedido)
    db.session.flush()

    sep = AssaiSeparacao(pedido_id=pedido.id, loja_id=loja.id,
                         status=SEPARACAO_STATUS_FATURADA)
    db.session.add(sep)
    db.session.flush()
    sep_item = AssaiSeparacaoItem(
        separacao_id=sep.id, chassi=chassi_a, modelo_id=modelo.id,
        valor_unitario_qpa=Decimal('5000.00'),
    )
    db.session.add(sep_item)
    db.session.flush()

    nf = AssaiNfQpa(
        chave_44=_chave_44(), numero='9' + suf[:4], loja_id=loja.id,
        status_match=NF_STATUS_BATEU, separacao_id=sep.id, importada_por_id=admin.id,
    )
    db.session.add(nf)
    db.session.flush()
    nf_item = AssaiNfQpaItem(
        nf_id=nf.id, chassi=chassi_a, separacao_item_id=sep_item.id,
        valor_extraido=Decimal('5000.00'),
    )
    db.session.add(nf_item)
    db.session.flush()

    emitir_evento(chassi_a, EVENTO_FATURADA, operador_id=admin.id)
    emitir_evento(chassi_b, estado_b, operador_id=admin.id)

    mirror_assai_to_separacao(sep.id)
    for ln in Separacao.query.filter_by(separacao_lote_id=lote_id_de(sep.id)).all():
        ln.numero_nf = nf.numero
    db.session.commit()

    return dict(
        modelo=modelo, modelo_b=modelo_b, loja=loja, moto_a=moto_a, moto_b=moto_b,
        pedido=pedido, sep=sep, sep_item=sep_item, nf=nf, nf_item=nf_item,
        chassi_a=chassi_a, chassi_b=chassi_b,
    )


def test_pos_venda_ocorrencia_aceita_campos_de_troca(app, admin_user):
    """A migration 34 adicionou tipo/chassi_substituto/nf_qpa_id — round-trip."""
    with app.app_context():
        c = _cenario(admin_user)
        oc = AssaiPosVendaOcorrencia(
            chassi=c['chassi_a'], categoria=CATEGORIA_CLIENTE,
            descricao='defeito X', tipo=TIPO_TROCA_GARANTIA,
            chassi_substituto=c['chassi_b'], nf_qpa_id=c['nf'].id,
            criado_por_id=admin_user.id,
        )
        db.session.add(oc)
        db.session.commit()

        lido = AssaiPosVendaOcorrencia.query.get(oc.id)
        assert lido.tipo == TIPO_TROCA_GARANTIA
        assert lido.chassi_substituto == c['chassi_b']
        assert lido.nf_qpa_id == c['nf'].id
```

- [ ] **Step 8: Rodar o teste — deve passar (migration + model já aplicados)**

Run: `source .venv/bin/activate && pytest tests/motos_assai/test_troca_garantia.py::test_pos_venda_ocorrencia_aceita_campos_de_troca -v`
Expected: PASS

- [ ] **Step 9: Regenerar o schema JSON da tabela alterada**

```bash
source .venv/bin/activate && python .claude/skills/consultando-sql/scripts/generate_schemas.py 2>/dev/null || \
  find . -name generate_schemas.py -maxdepth 4
```
Confirme que `.claude/skills/consultando-sql/schemas/tables/assai_pos_venda_ocorrencia.json` agora lista `tipo`, `chassi_substituto`, `nf_qpa_id`.

- [ ] **Step 10: Commit**

```bash
git add scripts/migrations/motos_assai_34_troca_garantia.* app/motos_assai/models/pos_venda.py app/motos_assai/models/nf_qpa_vinculo.py app/motos_assai/models/__init__.py tests/motos_assai/test_troca_garantia.py .claude/skills/consultando-sql/schemas/tables/assai_pos_venda_ocorrencia.json
git commit -m "feat(motos-assai): migration 34 troca em garantia (colunas pos-venda + motivo vinculo)"
```

---

## Task 2: Helper `trocar_chassi_no_espelho`

**Files:**
- Modify: `app/motos_assai/services/separacao_mirror_service.py`
- Modify: `app/motos_assai/services/__init__.py`
- Test: `tests/motos_assai/test_troca_garantia.py`

**Interfaces:**
- Consumes: `lote_id_de(assai_sep_id)`, `Separacao` (Nacom), `db`, `logger` — já no módulo.
- Produces: `trocar_chassi_no_espelho(assai_sep_id: int, chassi_de: str, chassi_para: str) -> int` (retorna nº de linhas atualizadas; **NÃO commita**, faz `flush`).

- [ ] **Step 1: Escrever o teste (falha primeiro)**

Append to `tests/motos_assai/test_troca_garantia.py`:

```python
from app.motos_assai.services.separacao_mirror_service import trocar_chassi_no_espelho


def test_trocar_chassi_no_espelho_preserva_numero_nf(app, admin_user):
    """Troca chassi_assai A->B na linha espelho, preservando numero_nf/status."""
    with app.app_context():
        c = _cenario(admin_user)
        lote = lote_id_de(c['sep'].id)

        antes = Separacao.query.filter_by(separacao_lote_id=lote, chassi_assai=c['chassi_a']).all()
        assert len(antes) == 1
        assert antes[0].numero_nf == c['nf'].numero

        n = trocar_chassi_no_espelho(c['sep'].id, c['chassi_a'], c['chassi_b'])
        db.session.commit()

        assert n == 1
        assert Separacao.query.filter_by(separacao_lote_id=lote, chassi_assai=c['chassi_a']).count() == 0
        linha_b = Separacao.query.filter_by(separacao_lote_id=lote, chassi_assai=c['chassi_b']).one()
        assert linha_b.numero_nf == c['nf'].numero
```

- [ ] **Step 2: Rodar o teste — deve falhar (ImportError)**

Run: `source .venv/bin/activate && pytest tests/motos_assai/test_troca_garantia.py::test_trocar_chassi_no_espelho_preserva_numero_nf -v`
Expected: FAIL — `ImportError: cannot import name 'trocar_chassi_no_espelho'`

- [ ] **Step 3: Implementar o helper**

In `app/motos_assai/services/separacao_mirror_service.py`, after `sincronizar_espelho_com_separacao` (fim da função), add:

```python
def trocar_chassi_no_espelho(assai_sep_id: int, chassi_de: str, chassi_para: str) -> int:
    """Troca `chassi_assai` (de->para) IN-PLACE nas linhas espelho do lote.

    Usado pela troca em garantia: a linha espelho de A ja tem `numero_nf`
    preenchido, entao `sincronizar_espelho_com_separacao` (delta) bloquearia a
    remocao. Aqui apenas renomeamos o chassi na MESMA linha, preservando
    `numero_nf`/status. Como A e B sao do MESMO modelo, os demais campos
    (cod_produto/nome_produto/peso/valor) sao identicos — so `chassi_assai` muda.

    NAO commita (caller decide). Retorna o numero de linhas atualizadas.
    """
    chassi_de = (chassi_de or '').strip().upper()
    chassi_para = (chassi_para or '').strip().upper()
    lote_id = lote_id_de(assai_sep_id)
    linhas = Separacao.query.filter_by(
        separacao_lote_id=lote_id, chassi_assai=chassi_de,
    ).all()
    for ln in linhas:
        ln.chassi_assai = chassi_para
    db.session.flush()
    logger.info(
        'trocar_chassi_no_espelho: lote %s %s->%s em %d linha(s)',
        lote_id, chassi_de, chassi_para, len(linhas),
    )
    return len(linhas)
```

> O caller `registrar_troca` passa o chassi exatamente como está em `AssaiSeparacaoItem.chassi`. No `_cenario` os chassis já vêm em UPPER. Em produção, o filtro casa porque `chassi_assai` foi gravado a partir do mesmo `AssaiSeparacaoItem.chassi`.

- [ ] **Step 4: Exportar em `services/__init__.py`**

In `app/motos_assai/services/__init__.py`, on the `from .separacao_mirror_service import sincronizar_espelho_com_separacao` line (line 78), add `, trocar_chassi_no_espelho`; add `'trocar_chassi_no_espelho'` to `__all__` (near line 156).

- [ ] **Step 5: Rodar o teste — deve passar**

Run: `source .venv/bin/activate && pytest tests/motos_assai/test_troca_garantia.py::test_trocar_chassi_no_espelho_preserva_numero_nf -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/motos_assai/services/separacao_mirror_service.py app/motos_assai/services/__init__.py tests/motos_assai/test_troca_garantia.py
git commit -m "feat(motos-assai): trocar_chassi_no_espelho (swap in-place no espelho Nacom)"
```

---

## Task 3: Serviço `registrar_troca` (swap cirúrgico A→B)

**Files:**
- Create: `app/motos_assai/services/troca_garantia_service.py`
- Modify: `app/motos_assai/services/__init__.py`
- Test: `tests/motos_assai/test_troca_garantia.py`

**Interfaces:**
- Consumes: `emitir_evento`, `status_efetivo` (moto_evento_service); `trocar_chassi_no_espelho` (Task 2); models de Task 1.
- Produces: `registrar_troca(*, nf_id, chassi_a, chassi_b, operador_id, motivo, dry_run=True) -> dict`; `TrocaGarantiaError(Exception)`. Dict no sucesso: `{ok, dry_run, nf_id, nf_numero, chassi_a, chassi_b, sep_id, ocorrencia_id, plano}`. Levanta `TrocaGarantiaError` em qualquer guard.

- [ ] **Step 1: Escrever os testes (falham primeiro)**

Append to `tests/motos_assai/test_troca_garantia.py`:

```python
from app.motos_assai.services.troca_garantia_service import (
    registrar_troca, TrocaGarantiaError,
)


def test_registrar_troca_swap_completo(app, admin_user):
    """B vira FATURADA, A vira PENDENTE, NF/sep/espelho apontam para B, ocorrencia criada."""
    with app.app_context():
        c = _cenario(admin_user)

        res = registrar_troca(
            nf_id=c['nf'].id, chassi_a=c['chassi_a'], chassi_b=c['chassi_b'],
            operador_id=admin_user.id, motivo='Motor com defeito', dry_run=False,
        )
        assert res['ok'] is True
        assert res['dry_run'] is False

        assert status_efetivo(c['chassi_b']) == EVENTO_FATURADA
        assert status_efetivo(c['chassi_a']) == EVENTO_PENDENTE

        nf_item = AssaiNfQpaItem.query.get(c['nf_item'].id)
        assert nf_item.chassi == c['chassi_b']
        assert nf_item.separacao_item_id == c['sep_item'].id

        sep_item = AssaiSeparacaoItem.query.get(c['sep_item'].id)
        assert sep_item.chassi == c['chassi_b']

        lote = lote_id_de(c['sep'].id)
        linha_b = Separacao.query.filter_by(separacao_lote_id=lote, chassi_assai=c['chassi_b']).one()
        assert linha_b.numero_nf == c['nf'].numero

        hist = AssaiNfQpaItemVinculoHistorico.query.filter_by(
            nf_qpa_item_id=c['nf_item'].id, motivo=VINCULO_MOTIVO_TROCA_GARANTIA,
        ).one()
        assert hist.chassi_no_momento == c['chassi_a']

        oc = AssaiPosVendaOcorrencia.query.get(res['ocorrencia_id'])
        assert oc.tipo == TIPO_TROCA_GARANTIA
        assert oc.chassi == c['chassi_a']
        assert oc.chassi_substituto == c['chassi_b']
        assert oc.nf_qpa_id == c['nf'].id
        assert oc.descricao == 'Motor com defeito'

        assert AssaiNfQpa.query.get(c['nf'].id).status_match == NF_STATUS_BATEU
        assert nf_item.devolvido is False


def test_registrar_troca_dry_run_nao_escreve(app, admin_user):
    with app.app_context():
        c = _cenario(admin_user)
        res = registrar_troca(
            nf_id=c['nf'].id, chassi_a=c['chassi_a'], chassi_b=c['chassi_b'],
            operador_id=admin_user.id, motivo='Motor com defeito',
        )
        assert res['ok'] is True
        assert res['dry_run'] is True
        assert res['ocorrencia_id'] is None
        assert isinstance(res['plano'], list) and res['plano']

        assert status_efetivo(c['chassi_a']) == EVENTO_FATURADA
        assert status_efetivo(c['chassi_b']) == EVENTO_DISPONIVEL
        assert AssaiNfQpaItem.query.get(c['nf_item'].id).chassi == c['chassi_a']
        assert AssaiPosVendaOcorrencia.query.filter_by(nf_qpa_id=c['nf'].id).count() == 0


def test_registrar_troca_rejeita_a_nao_faturada(app, admin_user):
    with app.app_context():
        c = _cenario(admin_user)
        emitir_evento(c['chassi_a'], EVENTO_PENDENTE, operador_id=admin_user.id)
        db.session.commit()
        with pytest.raises(TrocaGarantiaError):
            registrar_troca(
                nf_id=c['nf'].id, chassi_a=c['chassi_a'], chassi_b=c['chassi_b'],
                operador_id=admin_user.id, motivo='x', dry_run=False,
            )


def test_registrar_troca_rejeita_b_nao_disponivel(app, admin_user):
    with app.app_context():
        c = _cenario(admin_user, estado_b=EVENTO_FATURADA)
        with pytest.raises(TrocaGarantiaError):
            registrar_troca(
                nf_id=c['nf'].id, chassi_a=c['chassi_a'], chassi_b=c['chassi_b'],
                operador_id=admin_user.id, motivo='x', dry_run=False,
            )


def test_registrar_troca_rejeita_modelo_diferente(app, admin_user):
    with app.app_context():
        c = _cenario(admin_user, mesmo_modelo=False)
        with pytest.raises(TrocaGarantiaError):
            registrar_troca(
                nf_id=c['nf'].id, chassi_a=c['chassi_a'], chassi_b=c['chassi_b'],
                operador_id=admin_user.id, motivo='x', dry_run=False,
            )


def test_registrar_troca_idempotente(app, admin_user):
    with app.app_context():
        c = _cenario(admin_user)
        registrar_troca(
            nf_id=c['nf'].id, chassi_a=c['chassi_a'], chassi_b=c['chassi_b'],
            operador_id=admin_user.id, motivo='x', dry_run=False,
        )
        with pytest.raises(TrocaGarantiaError):
            registrar_troca(
                nf_id=c['nf'].id, chassi_a=c['chassi_a'], chassi_b=c['chassi_b'],
                operador_id=admin_user.id, motivo='x', dry_run=False,
            )
```

- [ ] **Step 2: Rodar — deve falhar (ImportError)**

Run: `source .venv/bin/activate && pytest tests/motos_assai/test_troca_garantia.py -k registrar_troca -v`
Expected: FAIL — `ImportError: cannot import name 'registrar_troca'`

- [ ] **Step 3: Implementar `troca_garantia_service.py`**

Create `app/motos_assai/services/troca_garantia_service.py`:

```python
"""Service de Troca em Garantia (Motos Assai).

Cliente final do Assai troca a moto defeituosa A por outra B (mesmo modelo,
cor pode variar), SEM NF. Modelagem: swap A->B na propria NF Q.P.A. —
B vira FATURADA (assume o slot de A na NF e na separacao), A vira PENDENTE
(volta ao estoque). Registro centralizado no pos-venda
(AssaiPosVendaOcorrencia tipo=TROCA_GARANTIA, com chassi_substituto e nf_qpa_id).

Swap CIRURGICO (spec 2026-06-30 §5.1): NAO usa _calcular_match (ignora seps
FATURADA) nem sincronizar_espelho_com_separacao (delta bloqueado por numero_nf).
"""
from __future__ import annotations

from app import db
from app.motos_assai.models import (
    AssaiMoto, AssaiNfQpa, AssaiNfQpaItem, AssaiNfQpaItemVinculoHistorico,
    AssaiSeparacaoItem, AssaiPosVendaOcorrencia,
    EVENTO_FATURADA, EVENTO_PENDENTE, EVENTO_SEPARADA, EVENTO_DISPONIVEL,
    NF_STATUS_CANCELADA,
    VINCULO_MOTIVO_TROCA_GARANTIA, TIPO_TROCA_GARANTIA, CATEGORIA_CLIENTE,
)
from app.motos_assai.services.moto_evento_service import emitir_evento, status_efetivo
from app.motos_assai.services.separacao_mirror_service import trocar_chassi_no_espelho
from app.utils.timezone import agora_brasil_naive


class TrocaGarantiaError(Exception):
    """Erro de validacao/execucao da troca em garantia."""


def _validar(nf_id, chassi_a, chassi_b):
    """Valida pre-condicoes. Retorna (nf, nf_item, sep_item, moto_a, moto_b)
    ou levanta TrocaGarantiaError."""
    chassi_a = (chassi_a or '').strip().upper()
    chassi_b = (chassi_b or '').strip().upper()
    if not chassi_a or not chassi_b:
        raise TrocaGarantiaError('chassi_a e chassi_b sao obrigatorios')
    if chassi_a == chassi_b:
        raise TrocaGarantiaError('chassi_a e chassi_b nao podem ser iguais')

    nf = AssaiNfQpa.query.get(nf_id)
    if not nf:
        raise TrocaGarantiaError(f'NF {nf_id} nao encontrada')
    if nf.status_match == NF_STATUS_CANCELADA:
        raise TrocaGarantiaError(f'NF {nf_id} esta CANCELADA — nao permite troca')

    nf_item = AssaiNfQpaItem.query.filter_by(nf_id=nf_id, chassi=chassi_a).first()
    if not nf_item:
        raise TrocaGarantiaError(f'chassi {chassi_a} nao consta na NF {nf_id}')
    if not nf_item.separacao_item_id:
        raise TrocaGarantiaError(
            f'chassi {chassi_a} na NF {nf_id} sem vinculo de separacao (separacao_item_id nulo)'
        )
    if status_efetivo(chassi_a) != EVENTO_FATURADA:
        raise TrocaGarantiaError(
            f'chassi {chassi_a} nao esta FATURADA (estado={status_efetivo(chassi_a)})'
        )

    if status_efetivo(chassi_b) != EVENTO_DISPONIVEL:
        raise TrocaGarantiaError(
            f'chassi substituto {chassi_b} nao esta DISPONIVEL '
            f'(estado={status_efetivo(chassi_b)})'
        )

    moto_a = AssaiMoto.query.filter_by(chassi=chassi_a).first()
    moto_b = AssaiMoto.query.filter_by(chassi=chassi_b).first()
    if not moto_a or not moto_b:
        raise TrocaGarantiaError('moto A ou B nao cadastrada em assai_moto')
    if moto_a.modelo_id != moto_b.modelo_id:
        raise TrocaGarantiaError(
            f'modelo divergente: A={moto_a.modelo_id} != B={moto_b.modelo_id}'
        )

    sep_item = AssaiSeparacaoItem.query.get(nf_item.separacao_item_id)
    if not sep_item:
        raise TrocaGarantiaError('AssaiSeparacaoItem do chassi A nao encontrado')

    return nf, nf_item, sep_item, moto_a, moto_b


def registrar_troca(*, nf_id, chassi_a, chassi_b, operador_id, motivo, dry_run=True):
    """Registra uma troca em garantia A->B.

    dry_run=True (default): valida e retorna o plano, sem escrever.
    """
    chassi_a = (chassi_a or '').strip().upper()
    chassi_b = (chassi_b or '').strip().upper()
    motivo = (motivo or '').strip()
    if not motivo:
        raise TrocaGarantiaError('motivo (descricao do defeito) obrigatorio')

    nf, nf_item, sep_item, moto_a, moto_b = _validar(nf_id, chassi_a, chassi_b)
    sep_id = sep_item.separacao_id

    plano = [
        f'NF {nf.numero}: item {chassi_a} -> {chassi_b} (vinculo TROCA_GARANTIA)',
        f'AssaiSeparacaoItem #{sep_item.id}: chassi {chassi_a} -> {chassi_b}',
        f'evento: {chassi_b} SEPARADA + FATURADA',
        f'evento: {chassi_a} PENDENTE (volta ao estoque)',
        f'espelho Nacom (sep {sep_id}): chassi_assai {chassi_a} -> {chassi_b}',
        'cria AssaiPosVendaOcorrencia TROCA_GARANTIA (CLIENTE)',
    ]

    if dry_run:
        return {
            'ok': True, 'dry_run': True, 'nf_id': nf.id, 'nf_numero': nf.numero,
            'chassi_a': chassi_a, 'chassi_b': chassi_b, 'sep_id': sep_id,
            'ocorrencia_id': None, 'plano': plano,
        }

    # Lock pessimista nas duas motos (anti-corrida)
    db.session.query(AssaiMoto).filter(
        AssaiMoto.chassi.in_([chassi_a, chassi_b])
    ).with_for_update().all()

    # 1) Vinculo historico (auditoria do swap na NF) — antes de mudar o item
    db.session.add(AssaiNfQpaItemVinculoHistorico(
        nf_qpa_item_id=nf_item.id,
        separacao_item_id=sep_item.id,
        motivo=VINCULO_MOTIVO_TROCA_GARANTIA,
        chassi_no_momento=chassi_a,
        registrado_por_id=operador_id,
        detalhes={'chassi_novo': chassi_b, 'nf_id': nf.id, 'motivo': motivo},
    ))

    # 2) Muta o slot de separacao A->B (preserva valor/modelo/sep) e religa a NF
    sep_item.chassi = chassi_b
    nf_item.chassi = chassi_b
    nf_item.tipo_divergencia = None
    # nf_item.separacao_item_id mantido — ja aponta para o slot (agora B)

    # 3) Eventos: B passa a ser a vendida (SEPARADA->FATURADA); A volta PENDENTE
    extras_b = {'origem': 'troca_garantia', 'nf_id': nf.id, 'chassi_substituido': chassi_a}
    emitir_evento(chassi_b, EVENTO_SEPARADA, operador_id=operador_id,
                  observacao=f'Troca garantia NF {nf.numero}', dados_extras=extras_b)
    emitir_evento(chassi_b, EVENTO_FATURADA, operador_id=operador_id,
                  observacao=f'Troca garantia NF {nf.numero}', dados_extras=extras_b)
    emitir_evento(chassi_a, EVENTO_PENDENTE, operador_id=operador_id,
                  observacao=f'Troca garantia NF {nf.numero}: substituida por {chassi_b}',
                  dados_extras={'origem': 'troca_garantia', 'nf_id': nf.id,
                                'chassi_substituto': chassi_b})

    # 4) Espelho Nacom in-place (preserva numero_nf — sem leg nova de frete)
    trocar_chassi_no_espelho(sep_id, chassi_a, chassi_b)

    # 5) Registro de pos-venda (centralizado)
    oc = AssaiPosVendaOcorrencia(
        chassi=chassi_a, categoria=CATEGORIA_CLIENTE, descricao=motivo,
        tipo=TIPO_TROCA_GARANTIA, chassi_substituto=chassi_b, nf_qpa_id=nf.id,
        criado_em=agora_brasil_naive(), criado_por_id=operador_id,
    )
    db.session.add(oc)
    db.session.flush()

    db.session.commit()

    return {
        'ok': True, 'dry_run': False, 'nf_id': nf.id, 'nf_numero': nf.numero,
        'chassi_a': chassi_a, 'chassi_b': chassi_b, 'sep_id': sep_id,
        'ocorrencia_id': oc.id, 'plano': plano,
    }
```

- [ ] **Step 4: Exportar em `services/__init__.py`**

Add a new import line near the other service imports:
```python
from .troca_garantia_service import registrar_troca, TrocaGarantiaError
```
and add `'registrar_troca', 'TrocaGarantiaError'` to `__all__`.

- [ ] **Step 5: Rodar os testes — devem passar**

Run: `source .venv/bin/activate && pytest tests/motos_assai/test_troca_garantia.py -k registrar_troca -v`
Expected: PASS (6 testes)

- [ ] **Step 6: Commit**

```bash
git add app/motos_assai/services/troca_garantia_service.py app/motos_assai/services/__init__.py tests/motos_assai/test_troca_garantia.py
git commit -m "feat(motos-assai): troca_garantia_service.registrar_troca (swap A->B na NF)"
```

---

## Task 4: Picker de substitutos (`listar_substitutos`)

**Files:**
- Modify: `app/motos_assai/services/troca_garantia_service.py`
- Modify: `app/motos_assai/services/__init__.py`
- Test: `tests/motos_assai/test_troca_garantia.py`

**Interfaces:**
- Produces: `listar_substitutos(modelo_id: int) -> dict` com `{'disponiveis': [{chassi, cor}], 'outros_estados': {'MONTADA': [...], 'ESTOQUE': [...], 'SEPARADA': [...]}}`. Só `DISPONIVEL` é selecionável; os demais são informativos.

- [ ] **Step 1: Escrever o teste (falha primeiro)**

Append to `tests/motos_assai/test_troca_garantia.py`:

```python
from app.motos_assai.services.troca_garantia_service import listar_substitutos
from app.motos_assai.models import EVENTO_MONTADA, EVENTO_ESTOQUE


def test_listar_substitutos_separa_disponivel_de_outros(app, admin_user):
    with app.app_context():
        import uuid as _uuid
        suf = _uuid.uuid4().hex[:6].upper()
        modelo = AssaiModelo(codigo=f'SUB{suf}', nome=f'Sub {suf}', peso_kg=Decimal('40'))
        db.session.add(modelo)
        db.session.flush()

        disp = AssaiMoto(chassi=f'DISP{suf}AAAA', modelo_id=modelo.id, cor='AZUL')
        mont = AssaiMoto(chassi=f'MONT{suf}BBBB', modelo_id=modelo.id, cor='ROSA')
        est = AssaiMoto(chassi=f'ESTQ{suf}CCCC', modelo_id=modelo.id, cor='CINZA')
        db.session.add_all([disp, mont, est])
        db.session.flush()
        emitir_evento(disp.chassi, EVENTO_DISPONIVEL, operador_id=admin_user.id)
        emitir_evento(mont.chassi, EVENTO_MONTADA, operador_id=admin_user.id)
        emitir_evento(est.chassi, EVENTO_ESTOQUE, operador_id=admin_user.id)
        db.session.commit()

        res = listar_substitutos(modelo.id)
        chassis_disp = {d['chassi'] for d in res['disponiveis']}
        assert disp.chassi.upper() in chassis_disp
        assert mont.chassi.upper() not in chassis_disp
        assert any(o['chassi'] == mont.chassi.upper() for o in res['outros_estados']['MONTADA'])
        assert any(o['chassi'] == est.chassi.upper() for o in res['outros_estados']['ESTOQUE'])
```

- [ ] **Step 2: Rodar — deve falhar (ImportError)**

Run: `source .venv/bin/activate && pytest tests/motos_assai/test_troca_garantia.py::test_listar_substitutos_separa_disponivel_de_outros -v`
Expected: FAIL — `ImportError: cannot import name 'listar_substitutos'`

- [ ] **Step 3: Implementar `listar_substitutos`**

In `app/motos_assai/services/troca_garantia_service.py`, add to the imports at top:
```python
from sqlalchemy import func
from app.motos_assai.models import AssaiMotoEvento, EVENTO_MONTADA, EVENTO_ESTOQUE
```
Then append the function:

```python
def listar_substitutos(modelo_id: int) -> dict:
    """Lista candidatos a moto substituta (B) do mesmo modelo.

    `disponiveis`: motos cujo ULTIMO evento e DISPONIVEL — selecionaveis.
    `outros_estados`: motos em MONTADA/ESTOQUE/SEPARADA (precisam de tratativa
    para virar DISPONIVEL) — exibidas como alerta, NAO selecionaveis.
    """
    sub = (
        db.session.query(
            AssaiMotoEvento.chassi.label('chassi'),
            func.max(AssaiMotoEvento.id).label('ultimo_id'),
        )
        .group_by(AssaiMotoEvento.chassi)
        .subquery()
    )
    rows = (
        db.session.query(AssaiMoto.chassi, AssaiMoto.cor, AssaiMotoEvento.tipo)
        .join(sub, sub.c.chassi == AssaiMoto.chassi)
        .join(AssaiMotoEvento, AssaiMotoEvento.id == sub.c.ultimo_id)
        .filter(AssaiMoto.modelo_id == modelo_id)
        .filter(AssaiMotoEvento.tipo.in_(
            [EVENTO_DISPONIVEL, EVENTO_MONTADA, EVENTO_ESTOQUE, EVENTO_SEPARADA]
        ))
        .order_by(AssaiMoto.chassi.asc())
        .all()
    )
    disponiveis = []
    outros = {EVENTO_MONTADA: [], EVENTO_ESTOQUE: [], EVENTO_SEPARADA: []}
    for chassi, cor, tipo in rows:
        item = {'chassi': chassi, 'cor': cor or ''}
        if tipo == EVENTO_DISPONIVEL:
            disponiveis.append(item)
        else:
            outros[tipo].append(item)
    return {'disponiveis': disponiveis, 'outros_estados': outros}
```

> As chaves de `outros_estados` são as strings `'MONTADA'`/`'ESTOQUE'`/`'SEPARADA'` (valores das constantes `EVENTO_*`), batendo com o que o template e o teste esperam.

- [ ] **Step 4: Exportar em `services/__init__.py`**

Add `listar_substitutos` ao `from .troca_garantia_service import ...` e ao `__all__`.

- [ ] **Step 5: Rodar — deve passar**

Run: `source .venv/bin/activate && pytest tests/motos_assai/test_troca_garantia.py::test_listar_substitutos_separa_disponivel_de_outros -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/motos_assai/services/troca_garantia_service.py app/motos_assai/services/__init__.py tests/motos_assai/test_troca_garantia.py
git commit -m "feat(motos-assai): listar_substitutos (picker DISPONIVEL + outros estados)"
```

---

## Task 5: Guards de imutabilidade + `listar_trocas_da_nf`

**Files:**
- Modify: `app/motos_assai/services/pos_venda_service.py`
- Modify: `app/motos_assai/services/__init__.py`
- Test: `tests/motos_assai/test_troca_garantia.py`

**Interfaces:**
- Produces: `listar_trocas_da_nf(nf_id: int) -> list[AssaiPosVendaOcorrencia]`. Guards: `atualizar_ocorrencia` recusa mudar categoria de uma ocorrência `tipo=TROCA_GARANTIA` (só `descricao` editável); `excluir_ocorrencia` recusa `tipo=TROCA_GARANTIA`.

- [ ] **Step 1: Escrever os testes (falham primeiro)**

Append to `tests/motos_assai/test_troca_garantia.py`:

```python
from app.motos_assai.services.pos_venda_service import (
    excluir_ocorrencia, atualizar_ocorrencia, listar_trocas_da_nf,
    PosVendaValidationError,
)
from app.motos_assai.models import CATEGORIA_LOJA


def test_listar_trocas_da_nf(app, admin_user):
    with app.app_context():
        c = _cenario(admin_user)
        res = registrar_troca(
            nf_id=c['nf'].id, chassi_a=c['chassi_a'], chassi_b=c['chassi_b'],
            operador_id=admin_user.id, motivo='defeito', dry_run=False,
        )
        trocas = listar_trocas_da_nf(c['nf'].id)
        assert len(trocas) == 1
        assert trocas[0].id == res['ocorrencia_id']
        assert trocas[0].chassi_substituto == c['chassi_b']


def test_troca_garantia_nao_pode_ser_excluida(app, admin_user):
    with app.app_context():
        c = _cenario(admin_user)
        res = registrar_troca(
            nf_id=c['nf'].id, chassi_a=c['chassi_a'], chassi_b=c['chassi_b'],
            operador_id=admin_user.id, motivo='defeito', dry_run=False,
        )
        with pytest.raises(PosVendaValidationError):
            excluir_ocorrencia(res['ocorrencia_id'])


def test_troca_garantia_categoria_imutavel_descricao_editavel(app, admin_user):
    with app.app_context():
        c = _cenario(admin_user)
        res = registrar_troca(
            nf_id=c['nf'].id, chassi_a=c['chassi_a'], chassi_b=c['chassi_b'],
            operador_id=admin_user.id, motivo='defeito', dry_run=False,
        )
        with pytest.raises(PosVendaValidationError):
            atualizar_ocorrencia(
                ocorrencia_id=res['ocorrencia_id'], categoria=CATEGORIA_LOJA,
                operador_id=admin_user.id,
            )
        oc = atualizar_ocorrencia(
            ocorrencia_id=res['ocorrencia_id'], descricao='defeito detalhado',
            operador_id=admin_user.id,
        )
        assert oc.descricao == 'defeito detalhado'
```

- [ ] **Step 2: Rodar — deve falhar**

Run: `source .venv/bin/activate && pytest tests/motos_assai/test_troca_garantia.py -k "trocas_da_nf or nao_pode_ser_excluida or categoria_imutavel" -v`
Expected: FAIL — `ImportError: cannot import name 'listar_trocas_da_nf'`

- [ ] **Step 3: Implementar guards + `listar_trocas_da_nf`**

In `app/motos_assai/services/pos_venda_service.py`, add `TIPO_TROCA_GARANTIA` to the model import block (lines 21-27):
```python
from app.motos_assai.models import (
    AssaiMoto, AssaiModelo, AssaiLoja,
    AssaiNfQpa, AssaiNfQpaItem,
    AssaiPosVendaOcorrencia, AssaiPosVendaOcorrenciaAnexo,
    CATEGORIAS_VALIDAS, TIPO_TROCA_GARANTIA,
    ANEXO_TIPO_FOTO, ANEXO_TIPO_VIDEO, ANEXO_TIPO_AUDIO, ANEXO_TIPO_OUTRO,
)
```

In `atualizar_ocorrencia`, right after the `if not oc: raise ... nao encontrada` block (after line 281), add:
```python
    if oc.tipo == TIPO_TROCA_GARANTIA and categoria is not None and categoria != oc.categoria:
        raise PosVendaValidationError(
            'ocorrencia de TROCA_GARANTIA: categoria/chassi sao imutaveis (so descricao e editavel)'
        )
```

In `excluir_ocorrencia`, right after the `if not oc: raise ... nao encontrada` block (after line 311), add:
```python
    if oc.tipo == TIPO_TROCA_GARANTIA:
        raise PosVendaValidationError(
            'ocorrencia de TROCA_GARANTIA nao pode ser excluida (efeito fiscal ja aplicado)'
        )
```

At the end of the "Ocorrencias" section (after `excluir_ocorrencia`, before `# ----- Anexos`), add:
```python
def listar_trocas_da_nf(nf_id: int) -> list[AssaiPosVendaOcorrencia]:
    """Ocorrencias de TROCA_GARANTIA vinculadas a uma NF (para o Faturamento)."""
    return (
        AssaiPosVendaOcorrencia.query
        .filter(
            AssaiPosVendaOcorrencia.nf_qpa_id == nf_id,
            AssaiPosVendaOcorrencia.tipo == TIPO_TROCA_GARANTIA,
        )
        .order_by(AssaiPosVendaOcorrencia.criado_em.desc())
        .all()
    )
```

- [ ] **Step 4: Exportar `listar_trocas_da_nf`**

In `app/motos_assai/services/__init__.py`, add `listar_trocas_da_nf` to the `from .pos_venda_service import (...)` block (line 98) and to `__all__`.

- [ ] **Step 5: Rodar — deve passar**

Run: `source .venv/bin/activate && pytest tests/motos_assai/test_troca_garantia.py -k "trocas_da_nf or nao_pode_ser_excluida or categoria_imutavel" -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/motos_assai/services/pos_venda_service.py app/motos_assai/services/__init__.py tests/motos_assai/test_troca_garantia.py
git commit -m "feat(motos-assai): guards de imutabilidade + listar_trocas_da_nf"
```

---

## Task 6: Rotas Pós-venda (form + registrar + substitutos AJAX) + template

**Files:**
- Modify: `app/motos_assai/routes/pos_venda.py`
- Create: `app/templates/motos_assai/pos_venda/troca_garantia.html`
- Test: `tests/motos_assai/test_troca_garantia.py`

**Interfaces:**
- Consumes: `registrar_troca`, `listar_substitutos`, `TrocaGarantiaError`, `contexto_moto_por_chassi`, `AssaiMoto`, `AssaiNfQpa`.
- Produces: rotas `GET /pos-venda/troca/<chassi_a>` (form), `POST /pos-venda/troca/<chassi_a>` (executa, JSON), `GET /pos-venda/troca/<chassi_a>/substitutos` (AJAX, JSON).

- [ ] **Step 1: Escrever os testes de rota (falham primeiro)**

Append to `tests/motos_assai/test_troca_garantia.py`:

```python
def test_rota_substitutos_json(app, admin_user, login_admin):
    with app.app_context():
        c = _cenario(admin_user)
        chassi_a, chassi_b = c['chassi_a'], c['chassi_b']
    resp = login_admin.get(f'/motos-assai/pos-venda/troca/{chassi_a}/substitutos')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'disponiveis' in data
    assert any(d['chassi'] == chassi_b for d in data['disponiveis'])


def test_rota_registrar_troca(app, admin_user, login_admin):
    with app.app_context():
        c = _cenario(admin_user)
        chassi_a, chassi_b, nf_id = c['chassi_a'], c['chassi_b'], c['nf'].id
    resp = login_admin.post(
        f'/motos-assai/pos-venda/troca/{chassi_a}',
        json={'chassi_b': chassi_b, 'nf_id': nf_id, 'motivo': 'defeito'},
    )
    assert resp.status_code == 200, resp.get_data(as_text=True)
    assert resp.get_json()['ok'] is True
    with app.app_context():
        assert status_efetivo(chassi_b) == EVENTO_FATURADA
        assert status_efetivo(chassi_a) == EVENTO_PENDENTE
```

- [ ] **Step 2: Rodar — deve falhar (404)**

Run: `source .venv/bin/activate && pytest tests/motos_assai/test_troca_garantia.py -k "rota_substitutos or rota_registrar" -v`
Expected: FAIL — 404

- [ ] **Step 3: Implementar as rotas**

In `app/motos_assai/routes/pos_venda.py`, extend the services import block (lines 25-32) com:
```python
    registrar_troca, listar_substitutos, TrocaGarantiaError,
```
e adicione a importação de models (após o bloco existente de models, lines 33-36):
```python
from app.motos_assai.models import AssaiMoto, AssaiNfQpa
```

Add these routes at the end of the "Ocorrencias" section (antes da seção Anexos):

```python
# ---------------------------------------------------------------------------
# Troca em Garantia
# ---------------------------------------------------------------------------

@motos_assai_bp.route('/pos-venda/troca/<chassi_a>', methods=['GET'])
@login_required
@require_motos_assai
def pos_venda_troca_form(chassi_a):
    """Tela de registro de troca em garantia para a moto defeituosa (A)."""
    chassi_a = (chassi_a or '').strip().upper()
    ctx = contexto_moto_por_chassi(chassi_a)
    if not ctx:
        abort(404)
    moto_a = AssaiMoto.query.filter_by(chassi=chassi_a).first()
    if not moto_a:
        abort(404)
    nfs = (
        AssaiNfQpa.query
        .join(AssaiNfQpa.itens)
        .filter_by(chassi=chassi_a)
        .all()
    )
    return render_template(
        'motos_assai/pos_venda/troca_garantia.html',
        chassi_a=chassi_a, ctx=ctx, modelo_id=moto_a.modelo_id, nfs=nfs,
    )


@motos_assai_bp.route('/pos-venda/troca/<chassi_a>/substitutos', methods=['GET'])
@login_required
@require_motos_assai
def pos_venda_troca_substitutos(chassi_a):
    """AJAX: candidatos a substituto (B) do mesmo modelo de A."""
    chassi_a = (chassi_a or '').strip().upper()
    moto_a = AssaiMoto.query.filter_by(chassi=chassi_a).first()
    if not moto_a:
        return jsonify({'ok': False, 'erro': 'moto A nao encontrada'}), 404
    return jsonify(listar_substitutos(moto_a.modelo_id))


@motos_assai_bp.route('/pos-venda/troca/<chassi_a>', methods=['POST'])
@login_required
@require_motos_assai
def pos_venda_troca_registrar(chassi_a):
    """POST AJAX: executa a troca A->B. Body JSON: {chassi_b, nf_id, motivo}."""
    data = request.get_json(silent=True) or request.form
    chassi_b = (data.get('chassi_b') or '').strip().upper()
    motivo = (data.get('motivo') or '').strip()
    try:
        nf_id = int(data.get('nf_id'))
    except (TypeError, ValueError):
        return jsonify({'ok': False, 'erro': 'nf_id invalido'}), 400
    try:
        res = registrar_troca(
            nf_id=nf_id, chassi_a=chassi_a, chassi_b=chassi_b,
            operador_id=current_user.id, motivo=motivo, dry_run=False,
        )
    except TrocaGarantiaError as e:
        return jsonify({'ok': False, 'erro': str(e)}), 400
    except Exception:
        current_app.logger.exception('Erro ao registrar troca em garantia')
        return jsonify({'ok': False, 'erro': 'Erro interno ao registrar troca'}), 500
    return jsonify(res)
```

- [ ] **Step 4: Criar o template `troca_garantia.html`**

Create `app/templates/motos_assai/pos_venda/troca_garantia.html`:

```html
{% extends "base.html" %}
{% block content %}
<div class="container py-3">
  <h4>Troca em Garantia</h4>
  <p class="text-muted">
    Moto defeituosa (A): <strong>{{ chassi_a }}</strong>
    — {{ ctx.modelo_nome }} {{ ctx.cor }} — NF {{ ctx.nf_numero }}
  </p>

  <form id="form-troca">
    <div class="mb-2">
      <label class="form-label">NF de venda</label>
      <select class="form-select" id="nf_id" required>
        {% for nf in nfs %}
        <option value="{{ nf.id }}">NF {{ nf.numero }} ({{ nf.status_match }})</option>
        {% endfor %}
      </select>
    </div>

    <div class="mb-2">
      <label class="form-label">Moto substituta (B) — DISPONIVEL, mesmo modelo</label>
      <select class="form-select" id="chassi_b" required>
        <option value="">Carregando...</option>
      </select>
      <div class="form-text" id="aviso-outros"></div>
    </div>

    <div class="mb-2">
      <label class="form-label">Motivo do defeito</label>
      <textarea class="form-control" id="motivo" required></textarea>
    </div>

    <button type="submit" class="btn btn-primary">Registrar troca</button>
    <div id="resultado" class="mt-2"></div>
  </form>
</div>

<script>
const CHASSI_A = {{ chassi_a|tojson }};
const URL_SUB = `/motos-assai/pos-venda/troca/${CHASSI_A}/substitutos`;
const URL_REG = `/motos-assai/pos-venda/troca/${CHASSI_A}`;

async function carregarSubstitutos() {
  const r = await fetch(URL_SUB);
  const d = await r.json();
  const sel = document.getElementById('chassi_b');
  sel.innerHTML = '';
  if (!d.disponiveis || !d.disponiveis.length) {
    sel.innerHTML = '<option value="">Nenhuma DISPONIVEL deste modelo</option>';
  } else {
    for (const m of d.disponiveis) {
      const o = document.createElement('option');
      o.value = m.chassi;
      o.textContent = `${m.chassi} — ${m.cor}`;
      sel.appendChild(o);
    }
  }
  const outros = d.outros_estados || {};
  const tot = (outros.MONTADA||[]).length + (outros.ESTOQUE||[]).length + (outros.SEPARADA||[]).length;
  document.getElementById('aviso-outros').textContent = tot
    ? `Existem ${tot} unidade(s) deste modelo em outros estados (MONTADA/ESTOQUE/SEPARADA) que precisam de tratativa para virar DISPONIVEL.`
    : '';
}

document.getElementById('form-troca').addEventListener('submit', async (e) => {
  e.preventDefault();
  const body = {
    chassi_b: document.getElementById('chassi_b').value,
    nf_id: document.getElementById('nf_id').value,
    motivo: document.getElementById('motivo').value,
  };
  const r = await fetch(URL_REG, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body),
  });
  const d = await r.json();
  const box = document.getElementById('resultado');
  box.className = d.ok ? 'mt-2 alert alert-success' : 'mt-2 alert alert-danger';
  box.textContent = d.ok
    ? `Troca registrada: ${d.chassi_a} -> ${d.chassi_b} (NF ${d.nf_numero}).`
    : (d.erro || 'Erro');
});

carregarSubstitutos();
</script>
{% endblock %}
```

- [ ] **Step 5: Rodar — deve passar**

Run: `source .venv/bin/activate && pytest tests/motos_assai/test_troca_garantia.py -k "rota_substitutos or rota_registrar" -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/motos_assai/routes/pos_venda.py app/templates/motos_assai/pos_venda/troca_garantia.html tests/motos_assai/test_troca_garantia.py
git commit -m "feat(motos-assai): rotas + tela de registro de troca em garantia"
```

---

## Task 7: Reflexo no Faturamento (badge + seção no detalhe da NF)

**Files:**
- Modify: `app/motos_assai/routes/faturamento.py`
- Modify: `app/templates/motos_assai/faturamento/nf_detalhe.html`
- Modify: `app/templates/motos_assai/faturamento/lista_separacoes.html`
- Test: `tests/motos_assai/test_troca_garantia.py`

**Interfaces:**
- Consumes: `listar_trocas_da_nf` (Task 5).
- Produces: `faturamento_nf_detalhe` passa `trocas_garantia` ao template; `faturamento_lista` passa `trocas_por_nf` (dict `{nf_id: True}`).

- [ ] **Step 1: Escrever o teste de rota (falha primeiro)**

Append to `tests/motos_assai/test_troca_garantia.py`:

```python
def test_faturamento_detalhe_mostra_troca(app, admin_user, login_admin):
    with app.app_context():
        c = _cenario(admin_user)
        registrar_troca(
            nf_id=c['nf'].id, chassi_a=c['chassi_a'], chassi_b=c['chassi_b'],
            operador_id=admin_user.id, motivo='defeito do motor', dry_run=False,
        )
        nf_id, chassi_b = c['nf'].id, c['chassi_b']
    resp = login_admin.get(f'/motos-assai/faturamento/nfs/{nf_id}')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'Troca em Garantia' in html
    assert chassi_b in html
```

- [ ] **Step 2: Rodar — deve falhar (texto ausente)**

Run: `source .venv/bin/activate && pytest tests/motos_assai/test_troca_garantia.py::test_faturamento_detalhe_mostra_troca -v`
Expected: FAIL — `'Troca em Garantia' not in html`

- [ ] **Step 3: Carregar as trocas na rota de detalhe**

In `app/motos_assai/routes/faturamento.py`, em `faturamento_nf_detalhe` (line 440), na linha que importa `listar_devolucoes_da_nf` (line 461-463), troque por:
```python
    from app.motos_assai.services import listar_devolucoes_da_nf, itens_da_nf_para_tela, listar_trocas_da_nf
    devolucoes_da_nf = listar_devolucoes_da_nf(nf_id)
    trocas_garantia = listar_trocas_da_nf(nf_id)
```
E adicione `trocas_garantia=trocas_garantia,` aos kwargs do `render_template(...)` (perto da line 475).

- [ ] **Step 4: Adicionar a seção no template `nf_detalhe.html`**

In `app/templates/motos_assai/faturamento/nf_detalhe.html`, logo após o bloco `devolucoes_da_nf` (~line 133), add:

```html
{% if trocas_garantia %}
<div class="card mt-3">
  <div class="card-header">
    <span class="badge bg-warning text-dark">Troca em Garantia</span>
    Registros de Pós-venda vinculados a esta NF
  </div>
  <div class="card-body p-0">
    <table class="table table-sm mb-0">
      <thead><tr><th>Defeituosa (A)</th><th>Substituta (B)</th><th>Motivo</th><th>Data</th></tr></thead>
      <tbody>
        {% for t in trocas_garantia %}
        <tr>
          <td>{{ t.chassi }}</td>
          <td>{{ t.chassi_substituto }}</td>
          <td>{{ t.descricao }}</td>
          <td>{{ t.criado_em.strftime('%d/%m/%Y %H:%M') if t.criado_em else '' }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endif %}
```

- [ ] **Step 5: Rodar — deve passar**

Run: `source .venv/bin/activate && pytest tests/motos_assai/test_troca_garantia.py::test_faturamento_detalhe_mostra_troca -v`
Expected: PASS

- [ ] **Step 6: Badge na lista de NFs**

In `app/motos_assai/routes/faturamento.py`, em `faturamento_lista` (line 39), perto do batch-load de `cces_por_nf` (lines 137-152), após montar `cces_por_nf` adicione:
```python
    from app.motos_assai.models import AssaiPosVendaOcorrencia, TIPO_TROCA_GARANTIA
    trocas_por_nf = {}
    _nf_ids = list(cces_por_nf.keys()) or [
        l['nf'].id for l in linhas if l.get('nf')
    ]
    if _nf_ids:
        for (nid,) in (
            db.session.query(AssaiPosVendaOcorrencia.nf_qpa_id)
            .filter(AssaiPosVendaOcorrencia.nf_qpa_id.in_(_nf_ids),
                    AssaiPosVendaOcorrencia.tipo == TIPO_TROCA_GARANTIA)
            .distinct().all()
        ):
            trocas_por_nf[nid] = True
```
> Ajuste a fonte de `_nf_ids` para a coleção real de linhas/NFs da função (abra o arquivo e use a mesma lista que alimenta `cces_por_nf`). Passe `trocas_por_nf=trocas_por_nf` em todos os `render_template` da função.

In `app/templates/motos_assai/faturamento/lista_separacoes.html`, onde os badges de CCe são exibidos por linha de NF, adicione (ajustando `nf.id` para a variável da linha no template):
```html
{% if trocas_por_nf.get(nf.id) %}<span class="badge bg-warning text-dark">Troca</span>{% endif %}
```

- [ ] **Step 7: Rodar a suíte de troca completa**

Run: `source .venv/bin/activate && pytest tests/motos_assai/test_troca_garantia.py -v`
Expected: PASS (todos)

- [ ] **Step 8: Commit**

```bash
git add app/motos_assai/routes/faturamento.py app/templates/motos_assai/faturamento/nf_detalhe.html app/templates/motos_assai/faturamento/lista_separacoes.html tests/motos_assai/test_troca_garantia.py
git commit -m "feat(motos-assai): Faturamento exibe troca em garantia (badge + secao NF)"
```

---

## Task 8: Documentação + suíte completa do módulo

**Files:**
- Modify: `app/motos_assai/CLAUDE.md`

- [ ] **Step 1: Documentar o fluxo no CLAUDE.md do módulo**

In `app/motos_assai/CLAUDE.md`, add a new section (após "Guards de import de NF Q.P.A.") documentando:
- O processo de Troca em Garantia (swap A→B na NF; B→FATURADA, A→PENDENTE; só controle interno; sem frete novo).
- A extensão de `assai_pos_venda_ocorrencia` (`tipo`/`chassi_substituto`/`nf_qpa_id`) e o motivo `TROCA_GARANTIA`.
- O serviço `troca_garantia_service.registrar_troca` (cirúrgico, **não** usa `_calcular_match`/`sincronizar_espelho` — explicar por quê) + `trocar_chassi_no_espelho` + `listar_substitutos`.
- Migration 34 (se aplicada manualmente em prod, registrar aqui — padrão das 32/33).
- Ponteiro para a spec `docs/superpowers/specs/2026-06-30-motos-assai-troca-garantia-design.md`.

Atualizar o campo `atualizado:` do header `doc:meta`. Seguir a skill `padronizando-docs`.

- [ ] **Step 2: Rodar a suíte completa do módulo (regressão)**

Run: `source .venv/bin/activate && pytest tests/motos_assai/ -q`
Expected: PASS (incluindo os testes pré-existentes — zero regressão)

- [ ] **Step 3: Commit**

```bash
git add app/motos_assai/CLAUDE.md
git commit -m "docs(motos-assai): documenta troca em garantia (swap-in-place)"
```

---

## Self-Review (preenchido pelo autor do plano)

- **Cobertura da spec:** D1 (fiscal só interno — Task 3 não toca `devolvido`/`qtd_faturada`), D2 (A→PENDENTE — Task 3 step 3), D3 (B→FATURADA — Task 3), D4 (centralizado em pós-venda — Task 1 colunas + Task 3 cria ocorrência + Task 5/7 link), D5 (sem frete novo — Task 2 preserva `numero_nf`), D6 (picker — Task 4 + Task 6). §5.1 bloqueio crítico → Task 3. §5.4 espelho → Task 2. §6.3 Faturamento → Task 7. Migrations §7 → Task 1. Testes §9 → cobertos em Tasks 1-7.
- **Sem placeholders:** todo step de código mostra o código. Os pontos "ajuste a variável" (Task 7 step 6: nome da coleção de NFs/variável da linha em `lista_separacoes.html`) dependem do template/rota existentes — o engenheiro confirma o nome ao abrir o arquivo; a lógica está completa e o fallback `_nf_ids` cobre o caso comum.
- **Consistência de tipos:** `registrar_troca(*, nf_id, chassi_a, chassi_b, operador_id, motivo, dry_run=True)→dict`, `listar_substitutos(modelo_id)→{disponiveis, outros_estados}`, `trocar_chassi_no_espelho(assai_sep_id, chassi_de, chassi_para)→int`, `listar_trocas_da_nf(nf_id)→list`, `TrocaGarantiaError` — idênticos entre tasks. Constantes `TIPO_TROCA_GARANTIA`/`VINCULO_MOTIVO_TROCA_GARANTIA` usadas consistentemente.
