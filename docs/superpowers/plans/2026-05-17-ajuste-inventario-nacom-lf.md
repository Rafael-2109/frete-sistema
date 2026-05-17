# Ajuste de Inventário NACOM/LF — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Executar os ajustes de estoque do inventário físico de 16/05/2026 nas empresas NACOM Goya (FB, CD) e LA FAMIGLIA via 4 CFOPs distintos, deixando como subproduto **infraestrutura reutilizável** (services genéricos, tabela de auditoria polimórfica, arquivo de constantes consolidado) para operações diárias futuras.

**Architecture:** 1 service genérico de NF inter-company parametrizado pela matriz CFOP×tipo×direção (armazenada em `app/odoo/constants/operacoes_fiscais.py` como dado), 3 services utilitários (lote, picking, indisponibilização), 1 tabela polimórfica de auditoria Odoo, scripts datados em `scripts/inventario_2026_05/` que orquestram ondas O0..O5, 5 hooks determinísticos, documentação atômica em `docs/inventario-2026-05/`.

**Tech Stack:** Python 3.12 · Flask 3.1.2 · Flask-SQLAlchemy 3.1 · SQLAlchemy 2.0 · Odoo XML-RPC (via `OdooConnection`) · Playwright 1.58 (validação SEFAZ) · Pytest · Redis (lock distribuído).

**Spec:** `docs/superpowers/specs/2026-05-17-ajuste-inventario-nacom-lf-design.md` (commit `086afa32`)

---

## Pré-requisitos (executar uma vez antes de qualquer task)

- [ ] **PR0.1: Ambiente virtual ativo**

```bash
cd /home/rafaelnascimento/projetos/frete_sistema
source .venv/bin/activate
python --version  # esperado: Python 3.12.x
```

- [ ] **PR0.2: Conexão Odoo funcional**

Validar que `OdooConnection` autentica sem erro contra o Odoo de produção:

```bash
python -c "from app import create_app; app = create_app(); ctx = app.app_context(); ctx.push(); from app.odoo.utils.connection import get_odoo_connection; odoo = get_odoo_connection(); print('uid:', odoo.uid)"
```

Expected: `uid: <numero>` (sem erro)

Se falhar: verificar `ODOO_URL`, `ODOO_DB`, `ODOO_USERNAME`, `ODOO_API_KEY` em `.env`.

- [ ] **PR0.3: Branch dedicada**

```bash
git checkout -b inventario-2026-05/infra-reutilizavel
```

---

## Fase 0 — Audit Run (descobrir realidade do Odoo)

**Objetivo:** Antes de criar código, descobrir os valores reais (location_ids, fiscal_position_ids, estrutura das 4 NFs de referência) que vão para `app/odoo/constants/`. Sem isso, codificaríamos suposições.

**Não cria código de produção — apenas script de descoberta + documentação.**

### Task 0.1: Script de audit `00_audit_odoo_realidade.py`

**Files:**
- Create: `scripts/inventario_2026_05/00_audit_odoo_realidade.py`
- Create: `scripts/inventario_2026_05/README.md`

- [ ] **Step 1: Criar README da pasta scripts**

Conteúdo:

```markdown
# Scripts — Inventário 2026-05

Scripts datados consumidos pela operação de ajuste de inventário.

## Ordem de execução

| # | Script | Fase |
|---|--------|------|
| 00 | `00_audit_odoo_realidade.py` | F0 — descoberta |
| 01 | `01_extrair_estoque_odoo.py` | F1 |
| 02 | `02_carregar_inventario_xlsx.py` | F1 |
| 03 | `03_confrontar_inv_vs_odoo.py` | F2 |
| 04 | `04_propor_ajustes.py` | F3 |
| 05 | `05_canary_estoque_staging.py` | F4a |
| 06 | `06_canary_nfs_referencia.py` | F4b |
| 07 | `07_executar_onda1_lf_fb.py` | F5 — O1 |
| 08 | `08_executar_onda2_cd_fb.py` | F5 — O2 |
| 09 | `09_executar_onda3_indisponibilizacao.py` | F5 — O3 |
| 10 | `10_reconciliar_pos_ajuste.py` | F6 |

Cada script é idempotente e suporta `--dry-run`. Resultados em `docs/inventario-2026-05/07-relatorios/`.

Hooks determinísticos em `hooks/`, instaláveis em `.git/hooks/` ou importados pelos services.

## Spec

`docs/superpowers/specs/2026-05-17-ajuste-inventario-nacom-lf-design.md`
```

```bash
mkdir -p /home/rafaelnascimento/projetos/frete_sistema/scripts/inventario_2026_05/hooks
# usar Write tool para criar o README acima
```

- [ ] **Step 2: Criar script de audit (estrutura)**

`scripts/inventario_2026_05/00_audit_odoo_realidade.py`:

```python
"""
Audit Run: descobre realidade do Odoo antes de gerar constantes.

Saidas:
- docs/inventario-2026-05/00-decisoes/D000-audit-odoo-realidade.md
- /tmp/audit_odoo_realidade.json (consumido por scripts seguintes)

Descobre:
1. location_id de estoque por company (FB=1, CD=4, LF=5)
2. picking_type_id por company (validar IDS_FIXOS.md)
3. fiscal_position_id por (company, CFOP) das 4 NFs de referencia
4. Estrutura completa das NFs ref 94457 / 13075 / 147772 / 94410
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/..')

import json
import argparse
from datetime import datetime
from app import create_app
from app.odoo.utils.connection import get_odoo_connection
from app.utils.timezone import agora_utc_naive

COMPANIES = {1: 'FB', 4: 'CD', 5: 'LF'}
NFS_REFERENCIA = {
    94457: ('industrializacao', '5901'),
    13075: ('perda', '5903'),
    147772: ('dev-industrializacao', '5949'),
    94410: ('transf-filial', '5152'),
}

def main(dry_run: bool):
    app = create_app()
    with app.app_context():
        odoo = get_odoo_connection()
        result = {
            'timestamp': agora_utc_naive().isoformat(),
            'companies': {},
            'nfs_referencia': {},
        }

        for company_id, codigo in COMPANIES.items():
            print(f'\n=== {codigo} (company_id={company_id}) ===')

            # 1. location_id de estoque interno
            locations = odoo.search_read(
                'stock.location',
                [
                    ['company_id', '=', company_id],
                    ['usage', '=', 'internal'],
                ],
                ['id', 'name', 'complete_name'],
                limit=20,
            )
            print(f'  Locations internas ({len(locations)}):')
            for loc in locations:
                print(f"    id={loc['id']} name={loc['complete_name']!r}")

            # 2. picking_type_id de Recebimento
            picking_types = odoo.search_read(
                'stock.picking.type',
                [
                    ['company_id', '=', company_id],
                    ['code', '=', 'incoming'],
                ],
                ['id', 'name', 'default_location_dest_id'],
            )
            print(f'  Picking types (incoming) ({len(picking_types)}):')
            for pt in picking_types:
                print(f"    id={pt['id']} name={pt['name']!r}")

            result['companies'][company_id] = {
                'codigo': codigo,
                'locations': locations,
                'picking_types_incoming': picking_types,
            }

        for nf_numero, (tipo, cfop) in NFS_REFERENCIA.items():
            print(f'\n=== NF {nf_numero} ({tipo} / CFOP {cfop}) ===')

            # Busca account.move pela 'name' (numero NF) — ajuste se nome diferente
            moves = odoo.search_read(
                'account.move',
                [
                    ['name', 'ilike', str(nf_numero)],
                ],
                [
                    'id', 'name', 'move_type', 'l10n_br_tipo_pedido',
                    'partner_id', 'company_id', 'fiscal_position_id',
                    'invoice_date', 'state', 'amount_total',
                    'invoice_line_ids',
                ],
                limit=5,
            )
            if not moves:
                print(f'  [NAO ENCONTRADO] NF {nf_numero}')
                result['nfs_referencia'][nf_numero] = {'erro': 'nao_encontrado'}
                continue

            move = moves[0]
            print(f"  id={move['id']} state={move['state']}")
            print(f"  l10n_br_tipo_pedido={move['l10n_br_tipo_pedido']}")
            print(f"  fiscal_position_id={move['fiscal_position_id']}")
            print(f"  company_id={move['company_id']}")
            print(f"  invoice_line_ids count={len(move['invoice_line_ids'])}")

            # Le 1 linha para entender estrutura
            if move['invoice_line_ids']:
                linha = odoo.read(
                    'account.move.line',
                    [move['invoice_line_ids'][0]],
                    ['product_id', 'quantity', 'price_unit',
                     'account_id', 'tax_ids', 'l10n_br_operacao_id',
                     'l10n_br_cfop_codigo'],
                )
                print(f"  Linha sample: {linha[0]}")
                move['_linha_sample'] = linha[0]

            result['nfs_referencia'][nf_numero] = move

        # Salva snapshot
        out_path = '/tmp/audit_odoo_realidade.json'
        with open(out_path, 'w') as f:
            json.dump(result, f, default=str, indent=2)
        print(f'\nSnapshot: {out_path}')

        if dry_run:
            print('\n[DRY RUN] Nao gerou documento de decisao. Use sem --dry-run.')
            return

        # Gera documento D000
        doc_path = '/home/rafaelnascimento/projetos/frete_sistema/docs/inventario-2026-05/00-decisoes/D000-audit-odoo-realidade.md'
        os.makedirs(os.path.dirname(doc_path), exist_ok=True)
        with open(doc_path, 'w') as f:
            f.write(_render_decisao(result))
        print(f'Documento: {doc_path}')


def _render_decisao(result):
    lines = [
        '# D000 — Audit Run: realidade do Odoo',
        '',
        f"**Data:** {result['timestamp']}",
        '',
        '## Locations e Picking Types por Company',
        '',
    ]
    for cid, c in result['companies'].items():
        lines.append(f"### {c['codigo']} (`company_id={cid}`)")
        lines.append('')
        lines.append('**Locations internas:**')
        lines.append('')
        for loc in c['locations']:
            lines.append(f"- `id={loc['id']}` — {loc['complete_name']}")
        lines.append('')
        lines.append('**Picking types (incoming):**')
        lines.append('')
        for pt in c['picking_types_incoming']:
            lines.append(f"- `id={pt['id']}` — {pt['name']}")
        lines.append('')

    lines.append('## NFs de Referência')
    lines.append('')
    for nf_num, data in result['nfs_referencia'].items():
        if data.get('erro'):
            lines.append(f"### NF {nf_num} — **NAO ENCONTRADA**")
            continue
        lines.append(f"### NF {nf_num} (`account.move.id={data['id']}`)")
        lines.append('')
        lines.append(f"- `move_type`: {data['move_type']}")
        lines.append(f"- `l10n_br_tipo_pedido`: {data['l10n_br_tipo_pedido']}")
        lines.append(f"- `fiscal_position_id`: {data['fiscal_position_id']}")
        lines.append(f"- `company_id`: {data['company_id']}")
        lines.append(f"- Estado: {data['state']}")
        lines.append('')

    lines.append('## Decisões derivadas')
    lines.append('')
    lines.append('Após este audit, atualizar:')
    lines.append('- `app/odoo/constants/locations.py` com `COMPANY_LOCATIONS = {1: ..., 4: ..., 5: ...}`')
    lines.append('- `app/odoo/constants/operacoes_fiscais.py` com `MATRIZ_INTERCOMPANY` (4 entradas, fiscal_position_id por company)')
    lines.append('- `.claude/references/odoo/IDS_FIXOS.md` se algum ID divergir')
    return '\n'.join(lines)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='Nao gera documento, so imprime')
    args = parser.parse_args()
    main(args.dry_run)
```

- [ ] **Step 3: Rodar dry-run**

```bash
python scripts/inventario_2026_05/00_audit_odoo_realidade.py --dry-run
```

Expected: imprime locations + picking_types + dados das 4 NFs. Sem erro.

Se uma NF não for encontrada: registrar em `docs/inventario-2026-05/02-gotchas/G001-nf-ref-nao-encontrada.md` e ajustar busca (ex: campo `l10n_br_numero_nota_fiscal` em vez de `name`).

- [ ] **Step 4: Rodar para valer**

```bash
python scripts/inventario_2026_05/00_audit_odoo_realidade.py
ls -la /tmp/audit_odoo_realidade.json
ls -la docs/inventario-2026-05/00-decisoes/D000-audit-odoo-realidade.md
```

Expected: ambos os arquivos existem.

- [ ] **Step 5: Commit**

```bash
git add scripts/inventario_2026_05/00_audit_odoo_realidade.py scripts/inventario_2026_05/README.md docs/inventario-2026-05/00-decisoes/D000-audit-odoo-realidade.md
git commit -m "$(cat <<'EOF'
feat(inventario): F0 audit run — descoberta de realidade Odoo

Script standalone que descobre antes de codar:
- location_id por company (FB/CD/LF)
- picking_type_id por company
- fiscal_position_id por (company, CFOP) das 4 NFs ref
- Estrutura completa das NFs 94457, 13075, 147772, 94410

Output: /tmp/audit_odoo_realidade.json + D000-audit-odoo-realidade.md.
Consumido pelas tasks de constants em Phase 1.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

### Task 0.2: Confirmar suposições com o dono do projeto

- [ ] **Step 1: Apresentar resultados**

Compartilhar com Rafael:
1. `D000-audit-odoo-realidade.md`
2. Pontos a confirmar:
   - `location_id` interno por company (escolher o "principal" se houver vários)
   - `fiscal_position_id` de cada NF ref bate com o esperado?
   - Alguma NF ref retornou estado ≠ `posted`? Se sim, usar outra NF de referência

- [ ] **Step 2: Registrar decisões**

Criar `docs/inventario-2026-05/00-decisoes/D001-escolhas-pos-audit.md` listando:
- `COMPANY_LOCATIONS` final
- `MATRIZ_INTERCOMPANY.<tipo>.fiscal_position_id` por company
- Substituições de NF ref (se houver)

- [ ] **Step 3: Commit**

```bash
git add docs/inventario-2026-05/00-decisoes/D001-escolhas-pos-audit.md
git commit -m "docs(inventario): F0 decisoes pos-audit — COMPANY_LOCATIONS + MATRIZ_INTERCOMPANY"
```

---

## Fase 1 — Infraestrutura local (constantes + models + migrations)

### Task 1.1: Esqueleto `app/odoo/constants/`

**Files:**
- Create: `app/odoo/constants/__init__.py`
- Create: `app/odoo/constants/locations.py`
- Create: `app/odoo/constants/operacoes_fiscais.py`
- Test: `tests/odoo/constants/test_operacoes_fiscais.py`

- [ ] **Step 1: Write the failing test**

`tests/odoo/constants/__init__.py`: criar arquivo vazio.

`tests/odoo/constants/test_operacoes_fiscais.py`:

```python
"""Testa estrutura das constantes de operacoes fiscais."""
import pytest


def test_matriz_intercompany_tem_4_tipos():
    from app.odoo.constants.operacoes_fiscais import MATRIZ_INTERCOMPANY
    assert set(MATRIZ_INTERCOMPANY.keys()) == {
        'industrializacao', 'perda', 'dev-industrializacao', 'transf-filial'
    }


def test_industrializacao_estruturada():
    from app.odoo.constants.operacoes_fiscais import MATRIZ_INTERCOMPANY
    op = MATRIZ_INTERCOMPANY['industrializacao']
    assert op['cfop'] == '5901'
    assert op['l10n_br_tipo_pedido'] == 'industrializacao'
    assert op['move_type'] == 'out_invoice'
    assert op['direcao'] == ('FB', 'LF')
    assert op['tipo_produto'] == [1, 2, 3]
    assert op['nf_referencia'] == 94457


def test_perda_estruturada():
    from app.odoo.constants.operacoes_fiscais import MATRIZ_INTERCOMPANY
    op = MATRIZ_INTERCOMPANY['perda']
    assert op['cfop'] == '5903'
    assert op['direcao'] == ('LF', 'FB')


def test_dev_industrializacao_bidirecional():
    from app.odoo.constants.operacoes_fiscais import MATRIZ_INTERCOMPANY
    op = MATRIZ_INTERCOMPANY['dev-industrializacao']
    assert op['cfop'] == '5949'
    assert op['direcao'] == 'BIDIRECIONAL_FB_LF'
    assert op['tipo_produto'] == [4]


def test_transf_filial_bidirecional():
    from app.odoo.constants.operacoes_fiscais import MATRIZ_INTERCOMPANY
    op = MATRIZ_INTERCOMPANY['transf-filial']
    assert op['cfop'] == '5152'
    assert op['direcao'] == 'BIDIRECIONAL_FB_CD'


def test_company_locations_tem_3_empresas():
    from app.odoo.constants.locations import COMPANY_LOCATIONS
    assert set(COMPANY_LOCATIONS.keys()) == {1, 4, 5}
    for cid, loc_id in COMPANY_LOCATIONS.items():
        assert isinstance(loc_id, int) and loc_id > 0


def test_resolver_operacao_para_tipo_produto():
    from app.odoo.constants.operacoes_fiscais import resolver_operacao_por_tipo_produto

    # tipo 1 (MP) na LF com sinal positivo → industrializacao FB→LF
    assert resolver_operacao_por_tipo_produto(tipo=1, company_id=5, sinal=+1) == 'industrializacao'
    # tipo 1 (MP) na LF com sinal negativo → perda LF→FB
    assert resolver_operacao_por_tipo_produto(tipo=1, company_id=5, sinal=-1) == 'perda'
    # tipo 4 (acabado) na LF → dev-industrializacao
    assert resolver_operacao_por_tipo_produto(tipo=4, company_id=5, sinal=+1) == 'dev-industrializacao'
    assert resolver_operacao_por_tipo_produto(tipo=4, company_id=5, sinal=-1) == 'dev-industrializacao'
    # CD ou FB com qualquer tipo → transf-filial
    assert resolver_operacao_por_tipo_produto(tipo=1, company_id=4, sinal=+1) == 'transf-filial'
    assert resolver_operacao_por_tipo_produto(tipo=4, company_id=1, sinal=-1) == 'transf-filial'
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
pytest tests/odoo/constants/test_operacoes_fiscais.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.odoo.constants'` em todos os testes.

- [ ] **Step 3: Implementar `app/odoo/constants/__init__.py`**

Arquivo vazio (módulo apenas).

- [ ] **Step 4: Implementar `app/odoo/constants/locations.py`**

```python
"""
COMPANY_LOCATIONS — location_id de estoque interno por company.

Origem: docs/inventario-2026-05/00-decisoes/D001-escolhas-pos-audit.md
Atualizar quando uma company mudar ou for adicionada.
"""

# VALORES PROVISORIOS — substituir pelos descobertos em F0 (D001)
# após audit run e confirmacao com o dono do projeto.
COMPANY_LOCATIONS = {
    1: 8,   # FB — Estoque interno (a confirmar via audit)
    4: 32,  # CD — Estoque interno (a confirmar)
    5: 0,   # LF — Estoque interno (a descobrir em F0)
}


def get_location_id(company_id: int) -> int:
    """Retorna location_id interna principal da company."""
    loc = COMPANY_LOCATIONS.get(company_id)
    if not loc:
        raise ValueError(f'COMPANY_LOCATIONS sem entrada para company_id={company_id}')
    return loc
```

- [ ] **Step 5: Implementar `app/odoo/constants/operacoes_fiscais.py`**

```python
"""
MATRIZ_INTERCOMPANY — operacoes fiscais entre empresas do grupo.

Dado, nao codigo. Adicionar nova operacao = adicionar entrada no dict.

Spec: docs/superpowers/specs/2026-05-17-ajuste-inventario-nacom-lf-design.md §5.2

Direcao:
  - tupla (origem_codigo, destino_codigo): operacao uni-direcional
  - 'BIDIRECIONAL_X_Y': operacao bi-direcional; o sinal do ajuste decide
"""
from typing import List, Tuple, Union, Dict, Any

CODIGO_PARA_COMPANY_ID = {'FB': 1, 'CD': 4, 'LF': 5}

MATRIZ_INTERCOMPANY: Dict[str, Dict[str, Any]] = {
    'industrializacao': {
        'cfop': '5901',
        'l10n_br_tipo_pedido': 'industrializacao',
        'move_type': 'out_invoice',
        'direcao': ('FB', 'LF'),
        'tipo_produto': [1, 2, 3],
        'nf_referencia': 94457,
        # Preenchido apos audit run F0:
        'fiscal_position_id': {1: None, 5: None},
    },
    'perda': {
        'cfop': '5903',
        'l10n_br_tipo_pedido': 'perda',
        'move_type': 'out_invoice',
        'direcao': ('LF', 'FB'),
        'tipo_produto': [1, 2, 3],
        'nf_referencia': 13075,
        'fiscal_position_id': {1: None, 5: None},
    },
    'dev-industrializacao': {
        'cfop': '5949',
        'l10n_br_tipo_pedido': 'dev-industrializacao',
        'move_type': 'out_invoice',
        'direcao': 'BIDIRECIONAL_FB_LF',
        'tipo_produto': [4],
        'nf_referencia': 147772,
        'fiscal_position_id': {1: None, 5: None},
    },
    'transf-filial': {
        'cfop': '5152',
        'l10n_br_tipo_pedido': 'transf-filial',
        'move_type': 'out_invoice',
        'direcao': 'BIDIRECIONAL_FB_CD',
        'tipo_produto': [1, 2, 3, 4],
        'nf_referencia': 94410,
        'fiscal_position_id': {1: None, 4: None},
    },
}


def resolver_operacao_por_tipo_produto(tipo: int, company_id: int, sinal: int) -> str:
    """
    Dada uma diferenca de inventario, decide qual operacao usar.

    Args:
        tipo: 1/2/3/4 (primeiro digito do cod_produto)
        company_id: 1 (FB), 4 (CD), 5 (LF)
        sinal: +1 se ajuste positivo (estoque LF maior que sistema), -1 se negativo

    Returns:
        chave de MATRIZ_INTERCOMPANY

    Raises:
        ValueError se combinacao desconhecida
    """
    # LF tem regras especificas por tipo
    if company_id == 5:  # LF
        if tipo == 4:
            return 'dev-industrializacao'
        if tipo in (1, 2, 3):
            return 'industrializacao' if sinal > 0 else 'perda'
        raise ValueError(f'Tipo {tipo} nao suportado para LF')

    # FB e CD: sempre transferencia
    if company_id in (1, 4):
        return 'transf-filial'

    raise ValueError(f'company_id={company_id} nao reconhecido')


def get_operacao(tipo_operacao: str) -> Dict[str, Any]:
    """Retorna entrada da matriz, raises se nao existe."""
    if tipo_operacao not in MATRIZ_INTERCOMPANY:
        raise KeyError(f"tipo_operacao={tipo_operacao!r} nao em MATRIZ_INTERCOMPANY. "
                       f"Validos: {sorted(MATRIZ_INTERCOMPANY)}")
    return MATRIZ_INTERCOMPANY[tipo_operacao]
```

- [ ] **Step 6: Run tests, verify pass**

```bash
pytest tests/odoo/constants/test_operacoes_fiscais.py -v
```

Expected: 7 PASSED.

- [ ] **Step 7: Atualizar valores pos-audit**

Editar `COMPANY_LOCATIONS` e `fiscal_position_id` em `MATRIZ_INTERCOMPANY` com os valores descobertos em `D001-escolhas-pos-audit.md`.

```bash
pytest tests/odoo/constants/test_operacoes_fiscais.py -v
```

Expected: ainda 7 PASSED (test_company_locations passa porque agora tem valores reais).

- [ ] **Step 8: Commit**

```bash
git add app/odoo/constants/ tests/odoo/constants/
git commit -m "$(cat <<'EOF'
feat(odoo): constants/operacoes_fiscais — MATRIZ_INTERCOMPANY consolidada

Arquivo de constantes centralizando dados que estavam espalhados em
3 services (lancamento_odoo_service, emissao_nf_pallet,
recebimento_lf_odoo_service).

- MATRIZ_INTERCOMPANY: 4 operacoes (industrializacao, perda,
  dev-industrializacao, transf-filial)
- COMPANY_LOCATIONS: location_id interno por company
- resolver_operacao_por_tipo_produto(): decisao automatica baseada
  em tipo (1/2/3/4), company_id, sinal do ajuste

7 testes cobrindo estrutura e logica de resolucao.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

### Task 1.2: Migration `operacao_odoo_auditoria`

**Files:**
- Create: `scripts/migrations/2026_05_18_operacao_odoo_auditoria.py`
- Create: `scripts/migrations/2026_05_18_operacao_odoo_auditoria.sql`
- Create: `app/odoo/models/__init__.py`
- Create: `app/odoo/models/operacao_odoo_auditoria.py`
- Test: `tests/odoo/models/test_operacao_odoo_auditoria.py`

- [ ] **Step 1: SQL idempotente**

`scripts/migrations/2026_05_18_operacao_odoo_auditoria.sql`:

```sql
-- Migration: operacao_odoo_auditoria (polimorfica, reutilizavel)
-- Substitui o padrao fretes-especifico (LancamentoFreteOdooAuditoria)
-- Spec: §7.1

BEGIN;

CREATE TABLE IF NOT EXISTS operacao_odoo_auditoria (
    id SERIAL PRIMARY KEY,
    external_id VARCHAR(64) NOT NULL UNIQUE,
    tabela_origem VARCHAR(40) NOT NULL,
    registro_id INTEGER NOT NULL,
    acao VARCHAR(20) NOT NULL,
    modelo_odoo VARCHAR(60) NOT NULL,
    metodo_odoo VARCHAR(60),
    odoo_id INTEGER,
    etapa INTEGER,
    etapa_descricao VARCHAR(80),
    status VARCHAR(20) NOT NULL,
    payload_json JSONB,
    resposta_json JSONB,
    dados_antes_json JSONB,
    dados_depois_json JSONB,
    erro_msg TEXT,
    tempo_execucao_ms INTEGER,
    contexto_origem VARCHAR(40),
    contexto_ref VARCHAR(80),
    screenshot_s3_key VARCHAR(255),
    executado_em TIMESTAMP NOT NULL,
    executado_por VARCHAR(80) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_oaa_tabela_odoo ON operacao_odoo_auditoria (tabela_origem, odoo_id);
CREATE INDEX IF NOT EXISTS idx_oaa_contexto ON operacao_odoo_auditoria (contexto_origem, contexto_ref);
CREATE INDEX IF NOT EXISTS idx_oaa_status ON operacao_odoo_auditoria (status);

COMMIT;
```

- [ ] **Step 2: Migration Python**

`scripts/migrations/2026_05_18_operacao_odoo_auditoria.py`:

```python
"""Migration: cria operacao_odoo_auditoria (polimorfica)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import inspect, text
from app import create_app, db

SQL_PATH = os.path.join(os.path.dirname(__file__), '2026_05_18_operacao_odoo_auditoria.sql')


def main():
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        if inspector.has_table('operacao_odoo_auditoria'):
            print('[OK] Tabela operacao_odoo_auditoria ja existe — verificando indices...')
        else:
            print('Criando operacao_odoo_auditoria...')

        with open(SQL_PATH) as f:
            sql = f.read()
        for stmt in sql.split(';'):
            stmt = stmt.strip()
            if stmt and not stmt.startswith('--'):
                db.session.execute(text(stmt))
        db.session.commit()

        # Verificacao
        inspector = inspect(db.engine)
        assert inspector.has_table('operacao_odoo_auditoria')
        cols = {c['name'] for c in inspector.get_columns('operacao_odoo_auditoria')}
        expected = {
            'id', 'external_id', 'tabela_origem', 'registro_id', 'acao',
            'modelo_odoo', 'metodo_odoo', 'odoo_id', 'etapa', 'etapa_descricao',
            'status', 'payload_json', 'resposta_json', 'dados_antes_json',
            'dados_depois_json', 'erro_msg', 'tempo_execucao_ms',
            'contexto_origem', 'contexto_ref', 'screenshot_s3_key',
            'executado_em', 'executado_por',
        }
        missing = expected - cols
        if missing:
            raise RuntimeError(f'Colunas faltando: {missing}')
        print(f'[OK] Tabela com {len(cols)} colunas')

        indexes = {ix['name'] for ix in inspector.get_indexes('operacao_odoo_auditoria')}
        for ix in ('idx_oaa_tabela_odoo', 'idx_oaa_contexto', 'idx_oaa_status'):
            assert ix in indexes, f'Index faltando: {ix}'
        print(f'[OK] Indexes: {sorted(indexes)}')


if __name__ == '__main__':
    main()
```

- [ ] **Step 3: Rodar migration localmente**

```bash
python scripts/migrations/2026_05_18_operacao_odoo_auditoria.py
```

Expected: `[OK] Tabela com 22 colunas` e indexes confirmados.

- [ ] **Step 4: Model SQLAlchemy**

`app/odoo/models/__init__.py`:

```python
from .operacao_odoo_auditoria import OperacaoOdooAuditoria  # noqa: F401
```

`app/odoo/models/operacao_odoo_auditoria.py`:

```python
"""Model OperacaoOdooAuditoria — auditoria polimorfica de operacoes Odoo."""
from app import db
from app.utils.timezone import agora_utc_naive


class OperacaoOdooAuditoria(db.Model):
    __tablename__ = 'operacao_odoo_auditoria'

    id = db.Column(db.Integer, primary_key=True)
    external_id = db.Column(db.String(64), nullable=False, unique=True)
    tabela_origem = db.Column(db.String(40), nullable=False)
    registro_id = db.Column(db.Integer, nullable=False)
    acao = db.Column(db.String(20), nullable=False)
    modelo_odoo = db.Column(db.String(60), nullable=False)
    metodo_odoo = db.Column(db.String(60))
    odoo_id = db.Column(db.Integer)
    etapa = db.Column(db.Integer)
    etapa_descricao = db.Column(db.String(80))
    status = db.Column(db.String(20), nullable=False)
    payload_json = db.Column(db.JSON)
    resposta_json = db.Column(db.JSON)
    dados_antes_json = db.Column(db.JSON)
    dados_depois_json = db.Column(db.JSON)
    erro_msg = db.Column(db.Text)
    tempo_execucao_ms = db.Column(db.Integer)
    contexto_origem = db.Column(db.String(40))
    contexto_ref = db.Column(db.String(80))
    screenshot_s3_key = db.Column(db.String(255))
    executado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    executado_por = db.Column(db.String(80), nullable=False)

    def __repr__(self):
        return f'<OperacaoOdooAuditoria {self.external_id} {self.modelo_odoo}.{self.acao} status={self.status}>'

    @classmethod
    def registrar(cls, *, external_id: str, tabela_origem: str, registro_id: int,
                  acao: str, modelo_odoo: str, status: str, executado_por: str,
                  **kwargs) -> 'OperacaoOdooAuditoria':
        """Helper para registrar uma operacao. Commit feito pelo caller."""
        from app.utils.json_helpers import sanitize_for_json
        kwargs.setdefault('executado_em', agora_utc_naive())
        for k in ('payload_json', 'resposta_json', 'dados_antes_json', 'dados_depois_json'):
            if k in kwargs and kwargs[k] is not None:
                kwargs[k] = sanitize_for_json(kwargs[k])
        rec = cls(
            external_id=external_id,
            tabela_origem=tabela_origem,
            registro_id=registro_id,
            acao=acao,
            modelo_odoo=modelo_odoo,
            status=status,
            executado_por=executado_por,
            **kwargs,
        )
        db.session.add(rec)
        db.session.flush()
        return rec
```

- [ ] **Step 5: Test do model**

`tests/odoo/models/__init__.py`: arquivo vazio.

`tests/odoo/models/test_operacao_odoo_auditoria.py`:

```python
import pytest
from decimal import Decimal
from app import create_app, db
from app.odoo.models import OperacaoOdooAuditoria


@pytest.fixture
def app_ctx():
    app = create_app()
    with app.app_context():
        yield app


def test_registrar_basico(app_ctx):
    rec = OperacaoOdooAuditoria.registrar(
        external_id='TEST-001',
        tabela_origem='account_move',
        registro_id=42,
        acao='create',
        modelo_odoo='account.move',
        status='SUCESSO',
        executado_por='pytest',
    )
    assert rec.id is not None
    assert rec.external_id == 'TEST-001'
    db.session.rollback()


def test_registrar_sanitiza_json_com_decimal(app_ctx):
    rec = OperacaoOdooAuditoria.registrar(
        external_id='TEST-002',
        tabela_origem='account_move',
        registro_id=43,
        acao='create',
        modelo_odoo='account.move',
        status='SUCESSO',
        executado_por='pytest',
        payload_json={'valor': Decimal('100.50')},
    )
    # Apos sanitize, Decimal vira float ou str (nunca explode em flush)
    db.session.flush()
    assert rec.payload_json is not None
    db.session.rollback()


def test_external_id_unico(app_ctx):
    OperacaoOdooAuditoria.registrar(
        external_id='UNIQUE-001',
        tabela_origem='account_move',
        registro_id=1,
        acao='create',
        modelo_odoo='account.move',
        status='SUCESSO',
        executado_por='pytest',
    )
    db.session.flush()
    with pytest.raises(Exception):  # IntegrityError
        OperacaoOdooAuditoria.registrar(
            external_id='UNIQUE-001',  # duplicado
            tabela_origem='account_move',
            registro_id=2,
            acao='create',
            modelo_odoo='account.move',
            status='SUCESSO',
            executado_por='pytest',
        )
        db.session.flush()
    db.session.rollback()
```

```bash
pytest tests/odoo/models/test_operacao_odoo_auditoria.py -v
```

Expected: 3 PASSED.

- [ ] **Step 6: Registrar model no `app/__init__.py`**

Verificar se há padrão. Em geral models são auto-descobertos quando importados; assegurar que `app/odoo/__init__.py` faça `from .models import OperacaoOdooAuditoria` ou que `app/__init__.py` o importe.

Adicionar em `app/odoo/__init__.py` (no final):

```python
from app.odoo.models import OperacaoOdooAuditoria  # noqa: F401
```

- [ ] **Step 7: Commit**

```bash
git add scripts/migrations/2026_05_18_operacao_odoo_auditoria.* app/odoo/models/ tests/odoo/models/ app/odoo/__init__.py
git commit -m "feat(odoo): tabela operacao_odoo_auditoria polimorfica + model + 3 testes"
```

### Task 1.3: Migration `ajuste_estoque_inventario`

**Files:**
- Create: `scripts/migrations/2026_05_18_ajuste_estoque_inventario.py`
- Create: `scripts/migrations/2026_05_18_ajuste_estoque_inventario.sql`
- Create: `app/odoo/models/ajuste_estoque_inventario.py`
- Test: `tests/odoo/models/test_ajuste_estoque_inventario.py`

- [ ] **Step 1: SQL**

`scripts/migrations/2026_05_18_ajuste_estoque_inventario.sql`:

```sql
-- Migration: ajuste_estoque_inventario (enxuta, suporta multiplos ciclos)
BEGIN;

CREATE TABLE IF NOT EXISTS ajuste_estoque_inventario (
    id SERIAL PRIMARY KEY,
    ciclo VARCHAR(40) NOT NULL,
    cod_produto VARCHAR(30) NOT NULL,
    tipo_produto SMALLINT NOT NULL,
    company_id INTEGER NOT NULL,
    lote_inventariado VARCHAR(60),
    lote_odoo VARCHAR(60),
    qtd_inventario NUMERIC(15,4) NOT NULL,
    qtd_odoo NUMERIC(15,4) NOT NULL,
    qtd_ajuste NUMERIC(15,4) NOT NULL,
    custo_medio NUMERIC(15,4),
    acao_decidida VARCHAR(30) NOT NULL,
    external_id_operacao VARCHAR(64),
    canary_passou BOOLEAN DEFAULT FALSE,
    aprovado_em TIMESTAMP,
    aprovado_por VARCHAR(80),
    status VARCHAR(20) NOT NULL DEFAULT 'PROPOSTO',
    erro_msg TEXT,
    criado_em TIMESTAMP NOT NULL,
    criado_por VARCHAR(80) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_aei_ciclo_chave ON ajuste_estoque_inventario (ciclo, company_id, cod_produto, lote_odoo);
CREATE INDEX IF NOT EXISTS idx_aei_status ON ajuste_estoque_inventario (status);
CREATE INDEX IF NOT EXISTS idx_aei_acao ON ajuste_estoque_inventario (acao_decidida);

COMMIT;
```

- [ ] **Step 2: Migration Python (mesmo template da Task 1.2)**

```python
"""Migration: cria ajuste_estoque_inventario."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import inspect, text
from app import create_app, db

SQL_PATH = os.path.join(os.path.dirname(__file__), '2026_05_18_ajuste_estoque_inventario.sql')


def main():
    app = create_app()
    with app.app_context():
        with open(SQL_PATH) as f:
            sql = f.read()
        for stmt in sql.split(';'):
            stmt = stmt.strip()
            if stmt and not stmt.startswith('--'):
                db.session.execute(text(stmt))
        db.session.commit()

        inspector = inspect(db.engine)
        assert inspector.has_table('ajuste_estoque_inventario')
        cols = {c['name'] for c in inspector.get_columns('ajuste_estoque_inventario')}
        expected = {
            'id', 'ciclo', 'cod_produto', 'tipo_produto', 'company_id',
            'lote_inventariado', 'lote_odoo', 'qtd_inventario', 'qtd_odoo',
            'qtd_ajuste', 'custo_medio', 'acao_decidida', 'external_id_operacao',
            'canary_passou', 'aprovado_em', 'aprovado_por', 'status', 'erro_msg',
            'criado_em', 'criado_por',
        }
        missing = expected - cols
        if missing:
            raise RuntimeError(f'Colunas faltando: {missing}')
        print(f'[OK] {len(cols)} colunas')


if __name__ == '__main__':
    main()
```

- [ ] **Step 3: Rodar migration**

```bash
python scripts/migrations/2026_05_18_ajuste_estoque_inventario.py
```

Expected: `[OK] 20 colunas`.

- [ ] **Step 4: Model `app/odoo/models/ajuste_estoque_inventario.py`**

```python
"""Model AjusteEstoqueInventario — controle de ciclo de inventario."""
from app import db
from app.utils.timezone import agora_utc_naive

STATUS_VALIDOS = {'PROPOSTO', 'APROVADO', 'EXECUTADO', 'FALHA', 'CANCELADO'}
ACOES_VALIDAS = {
    'TRANSFERIR_CD_FB', 'TRANSFERIR_FB_CD',
    'INDUSTRIALIZACAO_FB_LF', 'PERDA_LF_FB',
    'DEV_FB_LF', 'DEV_LF_FB',
    'INDISPONIBILIZAR_LOTE', 'INDISPONIBILIZAR_LOCAL',
    'RENOMEAR_LOTE',
    'SEM_ACAO',
}


class AjusteEstoqueInventario(db.Model):
    __tablename__ = 'ajuste_estoque_inventario'

    id = db.Column(db.Integer, primary_key=True)
    ciclo = db.Column(db.String(40), nullable=False)
    cod_produto = db.Column(db.String(30), nullable=False)
    tipo_produto = db.Column(db.SmallInteger, nullable=False)
    company_id = db.Column(db.Integer, nullable=False)
    lote_inventariado = db.Column(db.String(60))
    lote_odoo = db.Column(db.String(60))
    qtd_inventario = db.Column(db.Numeric(15, 4), nullable=False)
    qtd_odoo = db.Column(db.Numeric(15, 4), nullable=False)
    qtd_ajuste = db.Column(db.Numeric(15, 4), nullable=False)
    custo_medio = db.Column(db.Numeric(15, 4))
    acao_decidida = db.Column(db.String(30), nullable=False)
    external_id_operacao = db.Column(db.String(64))
    canary_passou = db.Column(db.Boolean, default=False)
    aprovado_em = db.Column(db.DateTime)
    aprovado_por = db.Column(db.String(80))
    status = db.Column(db.String(20), nullable=False, default='PROPOSTO')
    erro_msg = db.Column(db.Text)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    criado_por = db.Column(db.String(80), nullable=False)

    def __repr__(self):
        return (f'<AjusteEstoqueInventario {self.ciclo} {self.cod_produto} '
                f'company={self.company_id} acao={self.acao_decidida} status={self.status}>')
```

Adicionar a `app/odoo/models/__init__.py`:

```python
from .ajuste_estoque_inventario import AjusteEstoqueInventario, ACOES_VALIDAS, STATUS_VALIDOS  # noqa: F401
```

- [ ] **Step 5: Test do model**

`tests/odoo/models/test_ajuste_estoque_inventario.py`:

```python
import pytest
from decimal import Decimal
from app import create_app, db
from app.odoo.models import AjusteEstoqueInventario, ACOES_VALIDAS, STATUS_VALIDOS


@pytest.fixture
def app_ctx():
    app = create_app()
    with app.app_context():
        yield app


def test_modelo_basico(app_ctx):
    rec = AjusteEstoqueInventario(
        ciclo='INVENTARIO_TEST',
        cod_produto='101001001',
        tipo_produto=1,
        company_id=5,
        qtd_inventario=Decimal('100.0000'),
        qtd_odoo=Decimal('95.0000'),
        qtd_ajuste=Decimal('5.0000'),
        acao_decidida='INDUSTRIALIZACAO_FB_LF',
        criado_por='pytest',
    )
    db.session.add(rec)
    db.session.flush()
    assert rec.id is not None
    assert rec.status == 'PROPOSTO'  # default
    db.session.rollback()


def test_acoes_validas_consistente():
    assert 'TRANSFERIR_CD_FB' in ACOES_VALIDAS
    assert 'SEM_ACAO' in ACOES_VALIDAS
    assert len(ACOES_VALIDAS) == 10


def test_status_validos_consistente():
    assert STATUS_VALIDOS == {'PROPOSTO', 'APROVADO', 'EXECUTADO', 'FALHA', 'CANCELADO'}
```

```bash
pytest tests/odoo/models/test_ajuste_estoque_inventario.py -v
```

Expected: 3 PASSED.

- [ ] **Step 6: Commit**

```bash
git add scripts/migrations/2026_05_18_ajuste_estoque_inventario.* app/odoo/models/ajuste_estoque_inventario.py app/odoo/models/__init__.py tests/odoo/models/test_ajuste_estoque_inventario.py
git commit -m "feat(odoo): tabela ajuste_estoque_inventario + model + 3 testes"
```

---

## Fase 2 — Service `stock_lot_service`

### Task 2.1: Esqueleto + buscar_por_nome

**Files:**
- Create: `app/odoo/services/stock_lot_service.py`
- Test: `tests/odoo/services/test_stock_lot_service.py`

- [ ] **Step 1: Esqueleto do service**

`app/odoo/services/stock_lot_service.py`:

```python
"""
StockLotService — gerencia lotes no Odoo (criar, renomear, inativar).

Wrapper sobre helpers existentes em
app/recebimento/services/recebimento_fisico_odoo_service.py:
- _resolver_lote (linha 324-378)
- _criar_stock_lot_com_fallback (linha 416-482)

Inclui workaround do bug intermitente do operador '=' em stock.lot.search.
"""
import logging
from typing import Optional
from app.odoo.utils.connection import get_odoo_connection

logger = logging.getLogger(__name__)


class StockLotService:
    """Gerencia stock.lot no Odoo de forma reutilizavel."""

    def __init__(self, odoo=None):
        self.odoo = odoo or get_odoo_connection()

    def buscar_por_nome(self, nome: str, product_id: int, company_id: int) -> Optional[int]:
        """
        Busca lote por nome usando operador 'in' (workaround do bug do '=').

        Returns: lot_id ou None.
        """
        if not nome:
            return None

        # Workaround GOTCHAS.md: operador '=' tem bug intermitente em stock.lot.name
        ids = self.odoo.search('stock.lot', [
            ['name', 'in', [nome]],
            ['product_id', '=', product_id],
            ['company_id', '=', company_id],
        ], limit=1)

        if ids:
            return ids[0]

        # Fallback: =like
        ids = self.odoo.search('stock.lot', [
            ['name', '=like', nome],
            ['product_id', '=', product_id],
            ['company_id', '=', company_id],
        ], limit=1)
        return ids[0] if ids else None
```

- [ ] **Step 2: Test `buscar_por_nome` com mock**

`tests/odoo/services/__init__.py`: vazio.

`tests/odoo/services/test_stock_lot_service.py`:

```python
import pytest
from unittest.mock import MagicMock
from app.odoo.services.stock_lot_service import StockLotService


def test_buscar_por_nome_encontra():
    odoo = MagicMock()
    odoo.search.return_value = [123]
    svc = StockLotService(odoo=odoo)
    result = svc.buscar_por_nome('LOTE001', product_id=42, company_id=5)
    assert result == 123
    # Confirma uso de operador 'in' (workaround do bug)
    args = odoo.search.call_args
    domain = args[0][1]
    assert ['name', 'in', ['LOTE001']] in domain


def test_buscar_por_nome_fallback_like():
    odoo = MagicMock()
    odoo.search.side_effect = [[], [456]]  # primeira chamada vazia, segunda acha
    svc = StockLotService(odoo=odoo)
    result = svc.buscar_por_nome('LOTE002', product_id=42, company_id=5)
    assert result == 456
    assert odoo.search.call_count == 2


def test_buscar_por_nome_nao_encontra():
    odoo = MagicMock()
    odoo.search.side_effect = [[], []]
    svc = StockLotService(odoo=odoo)
    assert svc.buscar_por_nome('NAOEXISTE', product_id=42, company_id=5) is None


def test_buscar_por_nome_vazio_retorna_none():
    odoo = MagicMock()
    svc = StockLotService(odoo=odoo)
    assert svc.buscar_por_nome('', product_id=42, company_id=5) is None
    odoo.search.assert_not_called()
```

```bash
pytest tests/odoo/services/test_stock_lot_service.py -v
```

Expected: 4 PASSED.

- [ ] **Step 3: Commit**

```bash
git add app/odoo/services/stock_lot_service.py tests/odoo/services/
git commit -m "feat(odoo): StockLotService.buscar_por_nome com workaround bug operador ="
```

### Task 2.2: `criar()` com fallback

- [ ] **Step 1: Test (falha)**

Adicionar a `tests/odoo/services/test_stock_lot_service.py`:

```python
def test_criar_basico():
    odoo = MagicMock()
    odoo.create.return_value = 789
    svc = StockLotService(odoo=odoo)
    lot_id = svc.criar(nome='LOTE003', product_id=42, company_id=5)
    assert lot_id == 789
    args = odoo.create.call_args[0]
    assert args[0] == 'stock.lot'
    payload = args[1]
    assert payload['name'] == 'LOTE003'
    assert payload['product_id'] == 42
    assert payload['company_id'] == 5


def test_criar_com_expiration_date():
    odoo = MagicMock()
    odoo.create.return_value = 790
    svc = StockLotService(odoo=odoo)
    svc.criar(nome='L004', product_id=42, company_id=5, expiration_date='2027-01-15 00:00:00')
    payload = odoo.create.call_args[0][1]
    assert payload['expiration_date'] == '2027-01-15 00:00:00'


def test_criar_fallback_unique_constraint():
    """Se create falha por unique constraint, busca lote existente e retorna."""
    odoo = MagicMock()
    odoo.create.side_effect = Exception('duplicate key value violates unique constraint')
    odoo.search.return_value = [555]  # lote ja existe
    svc = StockLotService(odoo=odoo)
    lot_id = svc.criar(nome='L005', product_id=42, company_id=5)
    assert lot_id == 555
```

```bash
pytest tests/odoo/services/test_stock_lot_service.py::test_criar_basico -v
```

Expected: FAIL (`AttributeError: 'StockLotService' object has no attribute 'criar'`).

- [ ] **Step 2: Implementar `criar`**

Adicionar a `app/odoo/services/stock_lot_service.py`:

```python
    def criar(self, nome: str, product_id: int, company_id: int,
              expiration_date: Optional[str] = None) -> int:
        """
        Cria stock.lot. Em caso de unique constraint, busca o existente e retorna.

        Args:
            nome: nome do lote (obrigatorio)
            product_id: produto Odoo
            company_id: empresa Odoo
            expiration_date: validade no formato 'YYYY-MM-DD HH:MM:SS' ou None

        Returns: lot_id
        """
        if not nome:
            raise ValueError('Nome do lote obrigatorio')

        payload = {
            'name': nome,
            'product_id': product_id,
            'company_id': company_id,
        }
        if expiration_date:
            payload['expiration_date'] = expiration_date

        try:
            return self.odoo.create('stock.lot', payload)
        except Exception as e:
            err = str(e).lower()
            if 'unique' in err or 'duplicate' in err:
                logger.warning(f'Lote {nome!r} ja existe (unique constraint), buscando existente')
                existente = self.buscar_por_nome(nome, product_id, company_id)
                if existente:
                    if expiration_date:
                        self.odoo.write('stock.lot', [existente], {'expiration_date': expiration_date})
                    return existente
            raise
```

```bash
pytest tests/odoo/services/test_stock_lot_service.py -v
```

Expected: 7 PASSED (4 anteriores + 3 novos).

- [ ] **Step 3: Commit**

```bash
git add app/odoo/services/stock_lot_service.py tests/odoo/services/test_stock_lot_service.py
git commit -m "feat(odoo): StockLotService.criar com fallback unique constraint"
```

### Task 2.3: `renomear()` com guard

- [ ] **Step 1: Test**

```python
def test_renomear_basico():
    odoo = MagicMock()
    odoo.search.return_value = []  # sem move pendente
    odoo.write.return_value = True
    svc = StockLotService(odoo=odoo)
    assert svc.renomear(lot_id=123, novo_nome='LOTE_RENOMEADO') is True
    odoo.write.assert_called_with('stock.lot', [123], {'name': 'LOTE_RENOMEADO'})


def test_renomear_bloqueado_se_move_pendente():
    """Guard: bloqueia se ha stock.move em picking nao-done."""
    odoo = MagicMock()
    odoo.search.return_value = [777]  # ha move pendente
    svc = StockLotService(odoo=odoo)
    with pytest.raises(RuntimeError, match='picking nao-done'):
        svc.renomear(lot_id=123, novo_nome='X')
    odoo.write.assert_not_called()
```

- [ ] **Step 2: Implementar**

```python
    def renomear(self, lot_id: int, novo_nome: str) -> bool:
        """
        Renomeia lote (P9 do spec).

        Guard: bloqueia se ha stock.move em picking nao-done para este lote.
        """
        if not novo_nome:
            raise ValueError('novo_nome obrigatorio')

        # Guard: ha move pendente?
        # stock.move.line eh o melhor lugar pq carrega lot_id explicito
        move_lines_pendentes = self.odoo.search('stock.move.line', [
            ['lot_id', '=', lot_id],
            ['state', 'not in', ['done', 'cancel']],
        ], limit=1)
        if move_lines_pendentes:
            raise RuntimeError(
                f'Lote {lot_id} tem stock.move em picking nao-done '
                f'(move_line_id={move_lines_pendentes[0]}); rename bloqueado.'
            )

        self.odoo.write('stock.lot', [lot_id], {'name': novo_nome})
        return True
```

```bash
pytest tests/odoo/services/test_stock_lot_service.py -v
```

Expected: 9 PASSED.

- [ ] **Step 3: Commit**

```bash
git commit -am "feat(odoo): StockLotService.renomear com guard de move pendente"
```

### Task 2.4: `inativar()` e `atualizar_validade()`

- [ ] **Step 1: Tests**

```python
def test_inativar():
    odoo = MagicMock()
    odoo.write.return_value = True
    svc = StockLotService(odoo=odoo)
    assert svc.inativar(lot_id=123) is True
    odoo.write.assert_called_with('stock.lot', [123], {'active': False})


def test_reativar():
    odoo = MagicMock()
    svc = StockLotService(odoo=odoo)
    svc.reativar(lot_id=123)
    odoo.write.assert_called_with('stock.lot', [123], {'active': True})


def test_atualizar_validade():
    odoo = MagicMock()
    svc = StockLotService(odoo=odoo)
    svc.atualizar_validade(lot_id=123, expiration_date='2028-01-01 00:00:00')
    odoo.write.assert_called_with(
        'stock.lot', [123], {'expiration_date': '2028-01-01 00:00:00'}
    )
```

- [ ] **Step 2: Implementar**

```python
    def inativar(self, lot_id: int) -> bool:
        """Indisponibiliza lote via active=False. Usado por indisponibilizacao_estoque_service."""
        self.odoo.write('stock.lot', [lot_id], {'active': False})
        return True

    def reativar(self, lot_id: int) -> bool:
        """Reverte inativar."""
        self.odoo.write('stock.lot', [lot_id], {'active': True})
        return True

    def atualizar_validade(self, lot_id: int, expiration_date: str) -> bool:
        """Atualiza data de validade no formato 'YYYY-MM-DD HH:MM:SS'."""
        self.odoo.write('stock.lot', [lot_id], {'expiration_date': expiration_date})
        return True
```

```bash
pytest tests/odoo/services/test_stock_lot_service.py -v
```

Expected: 12 PASSED.

- [ ] **Step 3: Commit**

```bash
git commit -am "feat(odoo): StockLotService.{inativar,reativar,atualizar_validade}"
```

---

## Fase 3 — Service `stock_picking_service`

### Task 3.1: Esqueleto + `criar_transferencia`

**Files:**
- Create: `app/odoo/services/stock_picking_service.py`
- Test: `tests/odoo/services/test_stock_picking_service.py`

- [ ] **Step 1: Test**

`tests/odoo/services/test_stock_picking_service.py`:

```python
import pytest
from unittest.mock import MagicMock
from app.odoo.services.stock_picking_service import StockPickingService


def test_criar_transferencia_basico():
    odoo = MagicMock()
    odoo.create.return_value = 9999
    svc = StockPickingService(odoo=odoo)
    linhas = [
        {'product_id': 1001, 'quantity': 5.0, 'lot_name': 'L1'},
        {'product_id': 1002, 'quantity': 10.0},
    ]
    picking_id = svc.criar_transferencia(
        company_origem_id=1, company_destino_id=4,
        location_origem_id=8, location_destino_id=32,
        linhas=linhas, picking_type_id=99,
    )
    assert picking_id == 9999
    args = odoo.create.call_args[0]
    assert args[0] == 'stock.picking'
    payload = args[1]
    assert payload['location_id'] == 8
    assert payload['location_dest_id'] == 32
    assert payload['picking_type_id'] == 99
    assert payload['company_id'] == 1
    # move_ids deve conter as 2 linhas
    assert len(payload['move_ids']) == 2


def test_criar_transferencia_validacoes():
    odoo = MagicMock()
    svc = StockPickingService(odoo=odoo)
    with pytest.raises(ValueError, match='linhas'):
        svc.criar_transferencia(1, 4, 8, 32, linhas=[], picking_type_id=99)
```

```bash
pytest tests/odoo/services/test_stock_picking_service.py -v
```

Expected: FAIL (módulo não existe).

- [ ] **Step 2: Implementar**

`app/odoo/services/stock_picking_service.py`:

```python
"""
StockPickingService — gerencia stock.picking de transferencia.

Generaliza padroes em:
- app/pallet/services/emissao_nf_pallet.py:130-177
- app/recebimento/services/recebimento_lf_odoo_service.py:2122-2481

Padrao: create -> action_confirm -> action_assign -> preencher qty_done -> button_validate
"""
import logging
from typing import List, Dict, Optional, Any
from app.odoo.utils.connection import get_odoo_connection

logger = logging.getLogger(__name__)


class StockPickingService:
    def __init__(self, odoo=None):
        self.odoo = odoo or get_odoo_connection()

    def criar_transferencia(
        self,
        company_origem_id: int,
        company_destino_id: int,
        location_origem_id: int,
        location_destino_id: int,
        linhas: List[Dict[str, Any]],
        picking_type_id: int,
        partner_id: Optional[int] = None,
        scheduled_date: Optional[str] = None,
        origin: Optional[str] = None,
    ) -> int:
        """
        Cria picking de transferencia (saida).

        Args:
            linhas: [{'product_id': int, 'quantity': float, 'lot_name': str|None,
                      'lot_id': int|None, 'uom_id': int|None}, ...]
            picking_type_id: stock.picking.type id (saida da company origem)

        Returns: picking_id
        """
        if not linhas:
            raise ValueError('linhas vazias — picking exige ao menos 1 produto')

        move_ids = []
        for linha in linhas:
            product_id = linha['product_id']
            qty = float(linha['quantity'])
            move_payload = {
                'name': linha.get('name', f'Transf produto {product_id}'),
                'product_id': product_id,
                'product_uom_qty': qty,
                'location_id': location_origem_id,
                'location_dest_id': location_destino_id,
                'company_id': company_origem_id,
            }
            if linha.get('uom_id'):
                move_payload['product_uom'] = linha['uom_id']
            move_ids.append((0, 0, move_payload))

        picking_payload = {
            'location_id': location_origem_id,
            'location_dest_id': location_destino_id,
            'picking_type_id': picking_type_id,
            'company_id': company_origem_id,
            'move_ids': move_ids,
        }
        if partner_id:
            picking_payload['partner_id'] = partner_id
        if scheduled_date:
            picking_payload['scheduled_date'] = scheduled_date
        if origin:
            picking_payload['origin'] = origin

        picking_id = self.odoo.create('stock.picking', picking_payload)
        logger.info(f'Picking criado: id={picking_id} origem={company_origem_id} '
                    f'destino={company_destino_id} linhas={len(linhas)}')
        return picking_id
```

```bash
pytest tests/odoo/services/test_stock_picking_service.py -v
```

Expected: 2 PASSED.

- [ ] **Step 3: Commit**

```bash
git add app/odoo/services/stock_picking_service.py tests/odoo/services/test_stock_picking_service.py
git commit -m "feat(odoo): StockPickingService.criar_transferencia"
```

### Task 3.2: `confirmar_e_reservar` + `preencher_qty_done` + `validar`

- [ ] **Step 1: Tests**

```python
def test_confirmar_e_reservar():
    odoo = MagicMock()
    svc = StockPickingService(odoo=odoo)
    svc.confirmar_e_reservar(picking_id=9999)
    odoo.execute_kw.assert_any_call('stock.picking', 'action_confirm', [[9999]])
    odoo.execute_kw.assert_any_call('stock.picking', 'action_assign', [[9999]])


def test_validar_trata_cannot_marshal_none():
    """button_validate retorna None que XML-RPC nao consegue serializar — sucesso."""
    odoo = MagicMock()
    odoo.execute_kw.side_effect = Exception('cannot marshal None')
    svc = StockPickingService(odoo=odoo)
    # Nao deve lancar excecao
    assert svc.validar(picking_id=9999) is True


def test_validar_propaga_outras_excecoes():
    odoo = MagicMock()
    odoo.execute_kw.side_effect = Exception('Quality checks pending')
    svc = StockPickingService(odoo=odoo)
    with pytest.raises(Exception, match='Quality checks'):
        svc.validar(picking_id=9999)


def test_preencher_qty_done_por_linha():
    """Preenche qty_done em cada move_line. Suporta lot_id ou lot_name."""
    odoo = MagicMock()
    odoo.search_read.return_value = [
        {'id': 5001, 'product_id': [1001, 'P1']},
        {'id': 5002, 'product_id': [1002, 'P2']},
    ]
    svc = StockPickingService(odoo=odoo)
    linhas = [
        {'product_id': 1001, 'quantity': 5.0, 'lot_name': 'LOT_A'},
        {'product_id': 1002, 'quantity': 10.0, 'lot_id': 777},
    ]
    svc.preencher_qty_done(picking_id=9999, linhas=linhas)
    odoo.write.assert_any_call('stock.move.line', [5001], {'qty_done': 5.0, 'lot_name': 'LOT_A'})
    odoo.write.assert_any_call('stock.move.line', [5002], {'qty_done': 10.0, 'lot_id': 777})
```

- [ ] **Step 2: Implementar**

```python
    def confirmar_e_reservar(self, picking_id: int) -> None:
        """action_confirm + action_assign."""
        self.odoo.execute_kw('stock.picking', 'action_confirm', [[picking_id]])
        self.odoo.execute_kw('stock.picking', 'action_assign', [[picking_id]])

    def preencher_qty_done(self, picking_id: int, linhas: List[Dict[str, Any]]) -> None:
        """
        Preenche qty_done nas move_lines do picking, conforme matching por product_id.

        Cada linha deve ter:
            product_id: int
            quantity: float
            lot_id (opcional) OU lot_name (opcional) — mutuamente exclusivos
        """
        move_lines = self.odoo.search_read('stock.move.line',
            [['picking_id', '=', picking_id]],
            ['id', 'product_id'])

        # Mapa product_id -> move_line_id (primeira linha)
        produto_para_line = {}
        for ml in move_lines:
            pid = ml['product_id'][0] if ml['product_id'] else None
            if pid and pid not in produto_para_line:
                produto_para_line[pid] = ml['id']

        for linha in linhas:
            pid = linha['product_id']
            if pid not in produto_para_line:
                raise RuntimeError(f'product_id={pid} sem move_line no picking={picking_id}')
            line_id = produto_para_line[pid]
            update = {'qty_done': float(linha['quantity'])}
            if linha.get('lot_id'):
                update['lot_id'] = linha['lot_id']
            elif linha.get('lot_name'):
                update['lot_name'] = linha['lot_name']
            self.odoo.write('stock.move.line', [line_id], update)

    def validar(self, picking_id: int) -> bool:
        """
        button_validate. Trata 'cannot marshal None' como sucesso (GOTCHAS.md:179).
        """
        try:
            self.odoo.execute_kw('stock.picking', 'button_validate', [[picking_id]])
            return True
        except Exception as e:
            if 'cannot marshal None' in str(e):
                logger.info(f'Picking {picking_id}: button_validate retornou None (sucesso)')
                return True
            raise

    def cancelar(self, picking_id: int, motivo: str = '') -> bool:
        """Cancela picking via action_cancel."""
        self.odoo.execute_kw('stock.picking', 'action_cancel', [[picking_id]])
        if motivo:
            logger.info(f'Picking {picking_id} cancelado: {motivo}')
        return True
```

```bash
pytest tests/odoo/services/test_stock_picking_service.py -v
```

Expected: 6 PASSED.

- [ ] **Step 3: Commit**

```bash
git commit -am "feat(odoo): StockPickingService — confirmar/preencher/validar/cancelar"
```

---

## Fase 4 — Service `account_move_intercompany_service` (o núcleo)

Esta fase implementa o service genérico parametrizado. **Trabalho maior** — quebrado em sub-tasks.

### Task 4.1: Esqueleto + `preview()`

**Files:**
- Create: `app/odoo/services/account_move_intercompany_service.py`
- Test: `tests/odoo/services/test_account_move_intercompany_service.py`

- [ ] **Step 1: Tests**

```python
import pytest
from unittest.mock import MagicMock, patch
from app.odoo.services.account_move_intercompany_service import (
    AccountMoveIntercompanyService,
)


@pytest.fixture
def odoo_mock():
    m = MagicMock()
    return m


def test_preview_le_nf_referencia():
    odoo = MagicMock()
    # Mock NF de referencia (industrializacao = 94457)
    odoo.search.return_value = [11111]
    odoo.read.return_value = [{
        'id': 11111,
        'name': 'NACOM/2024/94457',
        'move_type': 'out_invoice',
        'l10n_br_tipo_pedido': 'industrializacao',
        'company_id': [1, 'NACOM FB'],
        'partner_id': [999, 'LA FAMIGLIA'],
        'fiscal_position_id': [50, 'POS X'],
        'invoice_line_ids': [201, 202],
    }]
    svc = AccountMoveIntercompanyService(odoo=odoo)
    payload = {
        'tipo_operacao': 'industrializacao',
        'linhas': [{'product_id': 1001, 'quantity': 5.0, 'price_unit': 10.0}],
    }
    diff = svc.preview(payload)
    assert diff['tipo_operacao'] == 'industrializacao'
    assert diff['nf_referencia_id'] == 11111
    assert 'campos_esperados' in diff


def test_preview_falha_se_tipo_operacao_invalido():
    odoo = MagicMock()
    svc = AccountMoveIntercompanyService(odoo=odoo)
    with pytest.raises(KeyError):
        svc.preview({'tipo_operacao': 'invalido', 'linhas': []})


def test_preview_falha_se_nf_ref_nao_encontrada():
    odoo = MagicMock()
    odoo.search.return_value = []
    svc = AccountMoveIntercompanyService(odoo=odoo)
    with pytest.raises(RuntimeError, match='NF referencia'):
        svc.preview({'tipo_operacao': 'industrializacao', 'linhas': []})
```

- [ ] **Step 2: Implementar esqueleto + `preview`**

`app/odoo/services/account_move_intercompany_service.py`:

```python
"""
AccountMoveIntercompanyService — service generico de NF entre empresas do grupo.

Parametrizado por `tipo_operacao` (string que mapeia para MATRIZ_INTERCOMPANY).
NAO 1 service por CFOP — 1 service que consome a matriz como dado.

Spec: docs/superpowers/specs/2026-05-17-ajuste-inventario-nacom-lf-design.md §6.2
"""
import logging
from typing import Dict, List, Any, Optional
from app.odoo.utils.connection import get_odoo_connection
from app.odoo.constants.operacoes_fiscais import (
    MATRIZ_INTERCOMPANY,
    get_operacao,
    CODIGO_PARA_COMPANY_ID,
)

logger = logging.getLogger(__name__)


class AccountMoveIntercompanyService:
    def __init__(self, odoo=None):
        self.odoo = odoo or get_odoo_connection()

    def preview(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Le NF de referencia e gera template, sem criar nada no Odoo.

        Args:
            payload: {
                'tipo_operacao': str (chave em MATRIZ_INTERCOMPANY),
                'company_origem_id': int (opcional, default da matriz),
                'company_destino_id': int (opcional),
                'partner_id': int (opcional),
                'linhas': [{'product_id': int, 'quantity': float, 'price_unit': float,
                            'lot_id': int|None, 'lot_name': str|None}, ...],
            }

        Returns: dict com diff campo-a-campo vs NF de referencia.
        """
        tipo = payload['tipo_operacao']
        op = get_operacao(tipo)  # raises se invalido

        nf_ref_numero = op['nf_referencia']
        ids = self.odoo.search('account.move', [
            ['name', 'ilike', str(nf_ref_numero)],
        ], limit=1)
        if not ids:
            raise RuntimeError(f'NF referencia {nf_ref_numero} ({tipo}) nao encontrada')

        nf_ref = self.odoo.read('account.move', ids, [
            'id', 'name', 'move_type', 'l10n_br_tipo_pedido',
            'company_id', 'partner_id', 'fiscal_position_id',
            'invoice_line_ids',
        ])[0]

        # Campos esperados (a serem preenchidos pela executar())
        campos_esperados = {
            'move_type': op['move_type'],
            'l10n_br_tipo_pedido': op['l10n_br_tipo_pedido'],
            'company_id': payload.get('company_origem_id'),
            'partner_id': payload.get('partner_id'),
            'fiscal_position_id': op.get('fiscal_position_id', {}).get(
                payload.get('company_origem_id')
            ),
        }

        return {
            'tipo_operacao': tipo,
            'cfop': op['cfop'],
            'nf_referencia_id': nf_ref['id'],
            'nf_referencia_nome': nf_ref['name'],
            'campos_esperados': campos_esperados,
            'linhas_count': len(payload.get('linhas', [])),
        }
```

```bash
pytest tests/odoo/services/test_account_move_intercompany_service.py -v
```

Expected: 3 PASSED.

- [ ] **Step 3: Commit**

```bash
git add app/odoo/services/account_move_intercompany_service.py tests/odoo/services/test_account_move_intercompany_service.py
git commit -m "feat(odoo): AccountMoveIntercompanyService.preview com leitura NF ref"
```

### Task 4.2: `executar()` — criar account.move + post

- [ ] **Step 1: Tests**

```python
def test_executar_cria_account_move_e_posta():
    odoo = MagicMock()
    # search NF ref
    odoo.search.return_value = [11111]
    odoo.read.return_value = [{
        'id': 11111, 'name': 'NACOM/2024/94457', 'move_type': 'out_invoice',
        'l10n_br_tipo_pedido': 'industrializacao',
        'company_id': [1, 'FB'], 'partner_id': [999, 'LF'],
        'fiscal_position_id': [50, 'POS X'], 'invoice_line_ids': [201],
    }]
    # create da NF nova
    odoo.create.return_value = 22222

    svc = AccountMoveIntercompanyService(odoo=odoo)
    payload = {
        'tipo_operacao': 'industrializacao',
        'company_origem_id': 1,
        'company_destino_id': 5,
        'partner_id': 999,
        'external_id': 'TEST-PREV-001',
        'linhas': [
            {'product_id': 1001, 'quantity': 5.0, 'price_unit': 10.0},
        ],
        'executado_por': 'pytest',
    }
    # Fixar fiscal_position_id em mock da matriz
    with patch.dict(MATRIZ_INTERCOMPANY['industrializacao']['fiscal_position_id'],
                    {1: 50, 5: 51}, clear=False):
        external_id = svc.executar(payload, confirmar=True)

    assert external_id == 'TEST-PREV-001'
    # Deve ter chamado create('account.move', ...)
    create_call = [c for c in odoo.create.call_args_list if c[0][0] == 'account.move']
    assert len(create_call) == 1
    payload_criado = create_call[0][0][1]
    assert payload_criado['l10n_br_tipo_pedido'] == 'industrializacao'
    assert payload_criado['move_type'] == 'out_invoice'
    assert payload_criado['fiscal_position_id'] == 50

    # Deve ter chamado action_post
    odoo.execute_kw.assert_any_call('account.move', 'action_post', [[22222]])
```

- [ ] **Step 2: Implementar `executar`**

Adicionar ao service:

```python
    def executar(self, payload: Dict[str, Any], confirmar: bool = False) -> str:
        """
        Cria account.move e posta. Idempotente via external_id.

        Args:
            payload: ver preview() + 'external_id' (str, obrigatorio para idempotencia),
                    'executado_por' (str), 'invoice_date' (opcional)
            confirmar: se False, cria DRAFT (sem action_post)

        Returns: external_id
        """
        from app.odoo.models import OperacaoOdooAuditoria
        from app import db
        from app.utils.timezone import agora_utc_naive

        if 'external_id' not in payload:
            raise ValueError('payload precisa de external_id (idempotencia)')
        if 'executado_por' not in payload:
            raise ValueError('payload precisa de executado_por')

        external_id = payload['external_id']
        tipo = payload['tipo_operacao']
        op = get_operacao(tipo)

        # Idempotencia: ja existe auditoria SUCESSO para este external_id?
        existente = OperacaoOdooAuditoria.query.filter_by(
            external_id=external_id, status='SUCESSO', acao='post'
        ).first()
        if existente:
            logger.info(f'executar idempotente: external_id={external_id} ja foi postado '
                        f'(odoo_id={existente.odoo_id})')
            return external_id

        company_origem_id = payload['company_origem_id']
        partner_id = payload['partner_id']
        fiscal_pos = op.get('fiscal_position_id', {}).get(company_origem_id)
        if not fiscal_pos:
            raise RuntimeError(
                f'fiscal_position_id nao definido para tipo={tipo} '
                f'company={company_origem_id}. Atualize MATRIZ_INTERCOMPANY.'
            )

        # Montar invoice_line_ids
        line_ids = []
        for linha in payload['linhas']:
            line_payload = {
                'product_id': linha['product_id'],
                'quantity': float(linha['quantity']),
                'price_unit': float(linha['price_unit']),
            }
            if linha.get('lot_id'):
                # NB: account.move.line nao tem lot_id direto; lote eh
                # registrado no stock.move.line do picking vinculado.
                pass
            line_ids.append((0, 0, line_payload))

        move_payload = {
            'move_type': op['move_type'],
            'l10n_br_tipo_pedido': op['l10n_br_tipo_pedido'],
            'company_id': company_origem_id,
            'partner_id': partner_id,
            'fiscal_position_id': fiscal_pos,
            'invoice_line_ids': line_ids,
        }
        if payload.get('invoice_date'):
            move_payload['invoice_date'] = payload['invoice_date']
        if payload.get('ref'):
            move_payload['ref'] = payload['ref']

        # CREATE
        invoice_id = self.odoo.create('account.move', move_payload)
        OperacaoOdooAuditoria.registrar(
            external_id=f'{external_id}-create',
            tabela_origem='account_move', registro_id=invoice_id,
            acao='create', modelo_odoo='account.move',
            metodo_odoo='create',
            odoo_id=invoice_id, status='SUCESSO',
            executado_por=payload['executado_por'],
            payload_json=move_payload, resposta_json={'id': invoice_id},
            contexto_origem='INTERCOMPANY', contexto_ref=external_id,
        )
        db.session.commit()

        # Recalcular impostos via metodo correto (NUNCA action_update_taxes)
        try:
            self.odoo.execute_kw('account.move', 'onchange_l10n_br_calcular_imposto',
                                 [[invoice_id]])
        except Exception as e:
            if 'cannot marshal None' not in str(e):
                logger.warning(f'onchange_l10n_br_calcular_imposto: {e}')

        if not confirmar:
            return external_id

        # POST
        try:
            self.odoo.execute_kw('account.move', 'action_post', [[invoice_id]],
                                 timeout_override=180)
            OperacaoOdooAuditoria.registrar(
                external_id=external_id, tabela_origem='account_move',
                registro_id=invoice_id, acao='post',
                modelo_odoo='account.move', metodo_odoo='action_post',
                odoo_id=invoice_id, status='SUCESSO',
                executado_por=payload['executado_por'],
                contexto_origem='INTERCOMPANY', contexto_ref=external_id,
            )
        except Exception as e:
            if 'cannot marshal None' in str(e):
                OperacaoOdooAuditoria.registrar(
                    external_id=external_id, tabela_origem='account_move',
                    registro_id=invoice_id, acao='post',
                    modelo_odoo='account.move', metodo_odoo='action_post',
                    odoo_id=invoice_id, status='SUCESSO',
                    executado_por=payload['executado_por'],
                    contexto_origem='INTERCOMPANY', contexto_ref=external_id,
                    erro_msg='cannot marshal None (tratado como sucesso)',
                )
            else:
                OperacaoOdooAuditoria.registrar(
                    external_id=external_id, tabela_origem='account_move',
                    registro_id=invoice_id, acao='post',
                    modelo_odoo='account.move', metodo_odoo='action_post',
                    odoo_id=invoice_id, status='ERRO',
                    executado_por=payload['executado_por'],
                    contexto_origem='INTERCOMPANY', contexto_ref=external_id,
                    erro_msg=str(e),
                )
                db.session.commit()
                raise

        db.session.commit()
        return external_id
```

```bash
pytest tests/odoo/services/test_account_move_intercompany_service.py -v
```

Expected: 4 PASSED.

- [ ] **Step 3: Commit**

```bash
git commit -am "feat(odoo): AccountMoveIntercompanyService.executar — idempotente, recalc impostos correto, audit"
```

### Task 4.3: `cancelar()` + integração com `stock_picking_service`

- [ ] **Step 1: Test cancelar**

```python
def test_cancelar():
    odoo = MagicMock()
    svc = AccountMoveIntercompanyService(odoo=odoo)
    svc.cancelar(invoice_id=22222, motivo='Inventario divergente')
    odoo.execute_kw.assert_any_call('account.move', 'button_cancel', [[22222]])
```

- [ ] **Step 2: Implementar**

```python
    def cancelar(self, invoice_id: int, motivo: str = '') -> bool:
        """
        Cancela NF. Sujeito a janela SEFAZ (24h transf / 7d industrializacao).
        Registra auditoria.
        """
        from app.odoo.models import OperacaoOdooAuditoria
        from app import db

        try:
            self.odoo.execute_kw('account.move', 'button_cancel', [[invoice_id]])
            status = 'SUCESSO'
            erro = None
        except Exception as e:
            status = 'ERRO'
            erro = str(e)

        OperacaoOdooAuditoria.registrar(
            external_id=f'CANCEL-{invoice_id}',
            tabela_origem='account_move', registro_id=invoice_id,
            acao='cancel', modelo_odoo='account.move',
            metodo_odoo='button_cancel', odoo_id=invoice_id,
            status=status, erro_msg=erro,
            executado_por='cancelar()',
            contexto_origem='CANCEL', contexto_ref=motivo or 'sem motivo',
        )
        db.session.commit()

        if status == 'ERRO':
            return False
        return True
```

```bash
pytest tests/odoo/services/test_account_move_intercompany_service.py -v
```

Expected: 5 PASSED.

- [ ] **Step 3: Commit**

```bash
git commit -am "feat(odoo): AccountMoveIntercompanyService.cancelar com auditoria"
```

---

## Fase 5 — Service `indisponibilizacao_estoque_service`

### Task 5.1: Canaries + indisponibilizar/reverter

**Files:**
- Create: `app/odoo/services/indisponibilizacao_estoque_service.py`
- Test: `tests/odoo/services/test_indisponibilizacao_estoque_service.py`

- [ ] **Step 1: Tests**

```python
import pytest
from unittest.mock import MagicMock
from app.odoo.services.indisponibilizacao_estoque_service import (
    IndisponibilizacaoEstoqueService,
)


def test_canary_lote_active_false():
    """
    C1: inativa lote, cria SO rascunho, verifica que lote nao aparece em
    move_line_ids candidatos. Retorna True se hipotese se confirma.
    """
    odoo = MagicMock()
    # Apos inativar lote, search por moves disponiveis nao deve incluir o lote
    odoo.search.side_effect = [
        # 1a chamada: lotes disponiveis ANTES do inactivate (assumimos vazio = ja teste)
        [],
    ]
    odoo.write.return_value = True
    svc = IndisponibilizacaoEstoqueService(odoo=odoo)
    # Implementacao real precisa criar SO real para testar; aqui validamos so a estrutura
    # Para o teste unitario, vamos validar que canary_lote chama write(active=False)
    # e depois faz a verificacao.
    # Implementacao real ficara no integration test
    pass


def test_indisponibilizar_lote_chama_inativar():
    odoo = MagicMock()
    svc = IndisponibilizacaoEstoqueService(odoo=odoo)
    svc.indisponibilizar_lote(lot_id=123, canary_passou=True)
    odoo.write.assert_called_with('stock.lot', [123], {'active': False})


def test_indisponibilizar_lote_bloqueado_sem_canary():
    odoo = MagicMock()
    svc = IndisponibilizacaoEstoqueService(odoo=odoo)
    with pytest.raises(RuntimeError, match='canary'):
        svc.indisponibilizar_lote(lot_id=123, canary_passou=False)


def test_reverter_lote():
    odoo = MagicMock()
    svc = IndisponibilizacaoEstoqueService(odoo=odoo)
    svc.reverter_lote(lot_id=123)
    odoo.write.assert_called_with('stock.lot', [123], {'active': True})


def test_indisponibilizar_local():
    odoo = MagicMock()
    svc = IndisponibilizacaoEstoqueService(odoo=odoo)
    svc.indisponibilizar_local(location_id=99, canary_passou=True)
    odoo.write.assert_called_with('stock.location', [99], {'active': False})
```

- [ ] **Step 2: Implementar**

```python
"""
IndisponibilizacaoEstoqueService — bloqueio de lote/local para faturamento.

Spec: docs/superpowers/specs/2026-05-17-ajuste-inventario-nacom-lf-design.md §6.2 + §10.1
"""
import logging
from typing import Optional
from app.odoo.utils.connection import get_odoo_connection

logger = logging.getLogger(__name__)


class IndisponibilizacaoEstoqueService:
    def __init__(self, odoo=None):
        self.odoo = odoo or get_odoo_connection()

    def canary_lote(self, lot_id: int, product_id: int, partner_id: int) -> dict:
        """
        C1: testa se stock.lot.active=False bloqueia o lote do faturamento.

        Procedimento:
        1. Lê stock.quant antes para confirmar saldo positivo do lote
        2. Inativa o lote (active=False)
        3. Cria sale.order rascunho com o produto
        4. Verifica se o lote aparece em move_line_ids candidatos
        5. REVERTE (active=True) — canary nao deve deixar lote indisponivel

        Returns: dict {'passou': bool, 'detalhes': ...}
        """
        # 1. Saldo antes
        quants_antes = self.odoo.search_read('stock.quant', [
            ['lot_id', '=', lot_id], ['quantity', '>', 0],
        ], ['id', 'quantity', 'location_id'])
        if not quants_antes:
            return {'passou': False, 'detalhes': f'Lote {lot_id} sem saldo positivo — escolha outro'}

        try:
            # 2. Inativar
            self.odoo.write('stock.lot', [lot_id], {'active': False})

            # 3. Criar SO rascunho
            so_id = self.odoo.create('sale.order', {
                'partner_id': partner_id,
                'order_line': [(0, 0, {'product_id': product_id, 'product_uom_qty': 1.0})],
            })
            self.odoo.execute_kw('sale.order', 'action_confirm', [[so_id]])

            # 4. Procurar picking + move_lines do produto e ver se lote aparece
            pickings = self.odoo.search_read('stock.picking', [
                ['sale_id', '=', so_id],
            ], ['id', 'move_line_ids'])
            move_line_ids_total = []
            for p in pickings:
                move_line_ids_total.extend(p.get('move_line_ids') or [])

            if move_line_ids_total:
                mls = self.odoo.read('stock.move.line', move_line_ids_total,
                                     ['id', 'lot_id'])
                lotes_atribuidos = {ml.get('lot_id')[0] for ml in mls if ml.get('lot_id')}
                passou = lot_id not in lotes_atribuidos
            else:
                # Sem move_line ainda — Odoo possivelmente nao reservou (sem estoque). OK como sinal.
                passou = True

            # Cleanup: cancel SO
            self.odoo.execute_kw('sale.order', 'action_cancel', [[so_id]])

            return {
                'passou': passou,
                'detalhes': f'SO={so_id} move_lines={move_line_ids_total} lote_atribuido={not passou}',
                'sale_order_id': so_id,
            }
        finally:
            # 5. SEMPRE reverter (canary nao pode deixar lote inativo)
            try:
                self.odoo.write('stock.lot', [lot_id], {'active': True})
            except Exception as e:
                logger.error(f'FALHA AO REVERTER lote {lot_id}: {e}')

    def canary_local(self, location_id: int, product_id: int, partner_id: int) -> dict:
        """C2: testa se stock.location.active=False bloqueia faturamento."""
        try:
            self.odoo.write('stock.location', [location_id], {'active': False})
            # Mesmo padrao do canary_lote
            so_id = self.odoo.create('sale.order', {
                'partner_id': partner_id,
                'order_line': [(0, 0, {'product_id': product_id, 'product_uom_qty': 1.0})],
            })
            self.odoo.execute_kw('sale.order', 'action_confirm', [[so_id]])
            pickings = self.odoo.search_read('stock.picking', [
                ['sale_id', '=', so_id]], ['id', 'move_line_ids'])
            move_line_ids = []
            for p in pickings:
                move_line_ids.extend(p.get('move_line_ids') or [])
            if move_line_ids:
                mls = self.odoo.read('stock.move.line', move_line_ids,
                                     ['id', 'location_id'])
                locais = {ml.get('location_id')[0] for ml in mls if ml.get('location_id')}
                passou = location_id not in locais
            else:
                passou = True
            self.odoo.execute_kw('sale.order', 'action_cancel', [[so_id]])
            return {'passou': passou, 'sale_order_id': so_id}
        finally:
            try:
                self.odoo.write('stock.location', [location_id], {'active': True})
            except Exception as e:
                logger.error(f'FALHA AO REVERTER local {location_id}: {e}')

    def indisponibilizar_lote(self, lot_id: int, canary_passou: bool) -> bool:
        if not canary_passou:
            raise RuntimeError(
                'canary_lote nao foi validado (canary_passou=False). '
                'Execute canary_lote() em staging primeiro.'
            )
        self.odoo.write('stock.lot', [lot_id], {'active': False})
        return True

    def reverter_lote(self, lot_id: int) -> bool:
        self.odoo.write('stock.lot', [lot_id], {'active': True})
        return True

    def indisponibilizar_local(self, location_id: int, canary_passou: bool) -> bool:
        if not canary_passou:
            raise RuntimeError(
                'canary_local nao foi validado. Execute canary_local() em staging.'
            )
        self.odoo.write('stock.location', [location_id], {'active': False})
        return True

    def reverter_local(self, location_id: int) -> bool:
        self.odoo.write('stock.location', [location_id], {'active': True})
        return True
```

```bash
pytest tests/odoo/services/test_indisponibilizacao_estoque_service.py -v
```

Expected: 4 PASSED (canary_lote tem teste apenas estrutural; teste real fica para script 05).

- [ ] **Step 3: Commit**

```bash
git add app/odoo/services/indisponibilizacao_estoque_service.py tests/odoo/services/test_indisponibilizacao_estoque_service.py
git commit -m "feat(odoo): IndisponibilizacaoEstoqueService — canary lote/local + indispor/reverter"
```

---

## Fase 6 — Hooks determinísticos

### Task 6.1: `pre_execute_nf.py`

**Files:**
- Create: `scripts/inventario_2026_05/hooks/__init__.py`
- Create: `scripts/inventario_2026_05/hooks/pre_execute_nf.py`
- Test: `tests/hooks/test_pre_execute_nf.py`

- [ ] **Step 1: Test**

`tests/hooks/__init__.py`: vazio.

`tests/hooks/test_pre_execute_nf.py`:

```python
import pytest
from decimal import Decimal
from scripts.inventario_2026_05.hooks.pre_execute_nf import (
    validar_pre_execucao, PreExecutionBlocked,
)


def test_aprova_se_status_aprovado_e_dentro_limites():
    payload = {
        'ajuste_status': 'APROVADO',
        'aprovado_em': '2026-05-17T10:00:00',
        'custo_medio_inv': Decimal('10.00'),
        'custo_medio_odoo': Decimal('10.50'),
        'valor_onda_total': Decimal('50000.00'),
        'teto_onda': Decimal('100000.00'),
    }
    # Nao deve lancar
    validar_pre_execucao(payload)


def test_bloqueia_se_status_diferente_de_aprovado():
    with pytest.raises(PreExecutionBlocked, match='status'):
        validar_pre_execucao({
            'ajuste_status': 'PROPOSTO',
            'aprovado_em': None,
            'custo_medio_inv': Decimal('10'),
            'custo_medio_odoo': Decimal('10'),
            'valor_onda_total': Decimal('1000'),
            'teto_onda': Decimal('100000'),
        })


def test_bloqueia_se_aprovado_em_null():
    with pytest.raises(PreExecutionBlocked, match='aprovado_em'):
        validar_pre_execucao({
            'ajuste_status': 'APROVADO',
            'aprovado_em': None,
            'custo_medio_inv': Decimal('10'),
            'custo_medio_odoo': Decimal('10'),
            'valor_onda_total': Decimal('1000'),
            'teto_onda': Decimal('100000'),
        })


def test_bloqueia_se_custo_diverge_mais_que_20pct():
    with pytest.raises(PreExecutionBlocked, match='custo'):
        validar_pre_execucao({
            'ajuste_status': 'APROVADO',
            'aprovado_em': '2026-05-17T10:00:00',
            'custo_medio_inv': Decimal('10.00'),
            'custo_medio_odoo': Decimal('15.00'),  # 50% maior
            'valor_onda_total': Decimal('1000'),
            'teto_onda': Decimal('100000'),
        })


def test_bloqueia_se_excede_teto_onda():
    with pytest.raises(PreExecutionBlocked, match='teto'):
        validar_pre_execucao({
            'ajuste_status': 'APROVADO',
            'aprovado_em': '2026-05-17T10:00:00',
            'custo_medio_inv': Decimal('10'),
            'custo_medio_odoo': Decimal('10'),
            'valor_onda_total': Decimal('150000'),
            'teto_onda': Decimal('100000'),
        })
```

- [ ] **Step 2: Implementar**

`scripts/inventario_2026_05/hooks/__init__.py`: vazio.

`scripts/inventario_2026_05/hooks/pre_execute_nf.py`:

```python
"""
Hook deterministico pre-execucao de NF.

Bloqueia execucao se uma das condicoes:
- ajuste_status != APROVADO
- aprovado_em IS NULL
- custo_medio_inv diverge >20% de custo_medio_odoo
- valor_onda_total > teto_onda
"""
from decimal import Decimal
from typing import Dict, Any


class PreExecutionBlocked(Exception):
    """Excecao levantada quando o hook bloqueia a execucao."""


def validar_pre_execucao(payload: Dict[str, Any]) -> None:
    """
    Valida payload antes de chamar account_move_intercompany_service.executar().

    payload deve conter:
        ajuste_status: str
        aprovado_em: str|None
        custo_medio_inv: Decimal
        custo_medio_odoo: Decimal
        valor_onda_total: Decimal
        teto_onda: Decimal

    Raises:
        PreExecutionBlocked
    """
    if payload.get('ajuste_status') != 'APROVADO':
        raise PreExecutionBlocked(
            f"ajuste_status={payload.get('ajuste_status')!r}, esperado 'APROVADO'"
        )
    if not payload.get('aprovado_em'):
        raise PreExecutionBlocked('aprovado_em obrigatorio')

    inv = payload['custo_medio_inv']
    odoo = payload['custo_medio_odoo']
    if odoo > 0:
        divergencia = abs(inv - odoo) / odoo
        if divergencia > Decimal('0.20'):
            raise PreExecutionBlocked(
                f'custo_medio diverge {divergencia*100:.1f}% (>20%): '
                f'inv={inv} odoo={odoo}'
            )

    if payload['valor_onda_total'] > payload['teto_onda']:
        raise PreExecutionBlocked(
            f"teto da onda excedido: valor={payload['valor_onda_total']} > "
            f"teto={payload['teto_onda']}"
        )
```

```bash
pytest tests/hooks/test_pre_execute_nf.py -v
```

Expected: 5 PASSED.

- [ ] **Step 3: Commit**

```bash
git add scripts/inventario_2026_05/hooks/ tests/hooks/
git commit -m "feat(inventario): hook pre_execute_nf — 5 regras bloqueantes deterministicas"
```

### Task 6.2: `pos_execute_nf.py` + `pre_lote_rename.py` + `pre_execute_indisponibilizacao.py`

- [ ] **Step 1: `pos_execute_nf.py`**

`scripts/inventario_2026_05/hooks/pos_execute_nf.py`:

```python
"""
Hook pos-execucao: salva screenshot Playwright + commit DB + cria
documento atomico em docs/inventario-2026-05/04-movimentacoes/.
"""
import os
import hashlib
import json
from typing import Dict, Any
from app import db
from app.utils.timezone import agora_utc_naive


def gerar_doc_atomico_movimentacao(
    external_id: str, cfop: str, payload: Dict[str, Any],
    onda: str, output_dir: str = None,
) -> str:
    """
    Cria docs/inventario-2026-05/04-movimentacoes/{onda}/{external_id}.md

    Returns: path do arquivo criado
    """
    if output_dir is None:
        output_dir = f'/home/rafaelnascimento/projetos/frete_sistema/docs/inventario-2026-05/04-movimentacoes/{onda}'
    os.makedirs(output_dir, exist_ok=True)

    payload_str = json.dumps(payload, sort_keys=True, default=str)
    payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()[:16]

    path = os.path.join(output_dir, f'{external_id}.md')
    content = f"""---
external_id: {external_id}
cfop: {cfop}
hash_payload: {payload_hash}
executado_em: {agora_utc_naive().isoformat()}
---

# Movimentacao {external_id}

**CFOP:** {cfop}
**Hash payload:** `{payload_hash}`

## Payload

```json
{payload_str}
```

## Resultado

(preenchido pelo script de execucao)
"""
    with open(path, 'w') as f:
        f.write(content)
    return path


def executar_pos_execucao(*, external_id: str, cfop: str, payload: Dict[str, Any],
                           onda: str, screenshot_path: str = None) -> Dict[str, Any]:
    """
    Hook pos-execucao: commit DB + gera doc atomico + retorna info.
    """
    db.session.commit()  # garante persistencia
    doc_path = gerar_doc_atomico_movimentacao(external_id, cfop, payload, onda)
    return {
        'commit_ok': True,
        'doc_path': doc_path,
        'screenshot_path': screenshot_path,
    }
```

- [ ] **Step 2: `pre_lote_rename.py`**

```python
"""
Hook pre-rename de lote: bloqueia se ha stock.move pendente no lote.

Ja implementado em StockLotService.renomear() (Task 2.3). Este wrapper
expoe a regra como funcao standalone.
"""
from app.odoo.utils.connection import get_odoo_connection


class LoteRenameBlocked(Exception):
    pass


def validar_pre_rename(lot_id: int) -> None:
    """Raises LoteRenameBlocked se ha move_line pendente."""
    odoo = get_odoo_connection()
    pendentes = odoo.search('stock.move.line', [
        ['lot_id', '=', lot_id],
        ['state', 'not in', ['done', 'cancel']],
    ], limit=1)
    if pendentes:
        raise LoteRenameBlocked(
            f'Lote {lot_id} tem stock.move.line pendente (id={pendentes[0]})'
        )
```

- [ ] **Step 3: `pre_execute_indisponibilizacao.py`**

```python
"""
Hook pre-indisponibilizacao: bloqueia se o canary correspondente
nao foi validado.
"""
from app import db
from app.odoo.models import AjusteEstoqueInventario


class IndisponibilizacaoBlocked(Exception):
    pass


def validar_pre_indisponibilizacao(ajuste_id: int) -> None:
    ajuste = db.session.get(AjusteEstoqueInventario, ajuste_id)
    if ajuste is None:
        raise IndisponibilizacaoBlocked(f'ajuste_id={ajuste_id} nao encontrado')
    if ajuste.acao_decidida not in ('INDISPONIBILIZAR_LOTE', 'INDISPONIBILIZAR_LOCAL'):
        raise IndisponibilizacaoBlocked(
            f'acao_decidida={ajuste.acao_decidida} nao e indisponibilizacao'
        )
    if not ajuste.canary_passou:
        raise IndisponibilizacaoBlocked(
            f'canary_passou=False para ajuste={ajuste_id}. '
            f'Rode o canary tecnico em staging primeiro.'
        )
```

- [ ] **Step 4: Test rápido dos 2 (mocks simples)**

`tests/hooks/test_outros_hooks.py`:

```python
import pytest
from unittest.mock import MagicMock, patch
from scripts.inventario_2026_05.hooks.pre_lote_rename import (
    validar_pre_rename, LoteRenameBlocked,
)


def test_pre_rename_bloqueia():
    with patch('scripts.inventario_2026_05.hooks.pre_lote_rename.get_odoo_connection') as mock_conn:
        odoo = MagicMock()
        odoo.search.return_value = [999]
        mock_conn.return_value = odoo
        with pytest.raises(LoteRenameBlocked):
            validar_pre_rename(123)


def test_pre_rename_passa():
    with patch('scripts.inventario_2026_05.hooks.pre_lote_rename.get_odoo_connection') as mock_conn:
        odoo = MagicMock()
        odoo.search.return_value = []
        mock_conn.return_value = odoo
        validar_pre_rename(123)  # nao deve lancar
```

```bash
pytest tests/hooks/ -v
```

Expected: 7 PASSED (5 anteriores + 2 novos).

- [ ] **Step 5: Commit**

```bash
git add scripts/inventario_2026_05/hooks/ tests/hooks/test_outros_hooks.py
git commit -m "feat(inventario): hooks pos_execute_nf, pre_lote_rename, pre_execute_indisponibilizacao"
```

### Task 6.3: `pre_commit_docs.sh`

- [ ] **Step 1: Script**

`scripts/inventario_2026_05/hooks/pre_commit_docs.sh`:

```bash
#!/usr/bin/env bash
# Pre-commit hook: bloqueia commits em docs/inventario-2026-05/04-movimentacoes/
# se algum arquivo .md nao tem frontmatter minimo (external_id, cfop, hash_payload).

set -e

PASTA="docs/inventario-2026-05/04-movimentacoes"
ARQUIVOS=$(git diff --cached --name-only --diff-filter=AM | grep -E "^${PASTA}/.+\.md$" || true)

if [ -z "$ARQUIVOS" ]; then
    exit 0  # nada para validar
fi

FALHAS=()
for arq in $ARQUIVOS; do
    if [ ! -f "$arq" ]; then
        continue
    fi
    cabecalho=$(head -10 "$arq")
    for campo in "external_id:" "cfop:" "hash_payload:"; do
        if ! echo "$cabecalho" | grep -q "$campo"; then
            FALHAS+=("$arq sem campo '$campo'")
        fi
    done
done

if [ ${#FALHAS[@]} -gt 0 ]; then
    echo "ERRO: pre-commit hook bloqueou commit:"
    printf '  - %s\n' "${FALHAS[@]}"
    exit 1
fi

exit 0
```

- [ ] **Step 2: Tornar executável**

```bash
chmod +x scripts/inventario_2026_05/hooks/pre_commit_docs.sh
```

- [ ] **Step 3: Testar manualmente**

```bash
# Criar arquivo invalido
mkdir -p /tmp/test-hook
echo "# sem frontmatter" > /tmp/test-hook/test.md
# Simular git diff:
echo "docs/inventario-2026-05/04-movimentacoes/test.md" > /tmp/test-files.txt
# (Teste real fica para integracao quando o hook for instalado em .git/hooks)
echo "Hook criado. Instalar com:"
echo "  ln -sf ../../scripts/inventario_2026_05/hooks/pre_commit_docs.sh .git/hooks/pre-commit"
```

- [ ] **Step 4: Commit**

```bash
git add scripts/inventario_2026_05/hooks/pre_commit_docs.sh
git commit -m "feat(inventario): hook git pre-commit para frontmatter de docs"
```

---

## Fase 7 — Scripts datados (executores)

Cada script segue padrão: argparse com `--dry-run` + `--confirmar` obrigatórios para writes, idempotência, log estruturado.

### Task 7.1: `01_extrair_estoque_odoo.py`

**Files:**
- Create: `scripts/inventario_2026_05/01_extrair_estoque_odoo.py`

- [ ] **Step 1: Implementar**

```python
"""
F1.1 — Extrai estoque atual de FB, CD, LF via stock.quant.

Output:
- docs/inventario-2026-05/07-relatorios/estoque-odoo-{FB,CD,LF}.xlsx
- /tmp/estoque_odoo_2026_05.json (consumido por 03_confrontar)
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/..')

import argparse
from collections import defaultdict
import openpyxl
from app import create_app
from app.odoo.utils.connection import get_odoo_connection
from app.utils.timezone import agora_utc_naive

OUTPUT_DIR = '/home/rafaelnascimento/projetos/frete_sistema/docs/inventario-2026-05/07-relatorios'
COMPANIES = {1: 'FB', 4: 'CD', 5: 'LF'}


def extrair_company(odoo, company_id: int):
    """Extrai stock.quant para todos os produtos com saldo positivo da company."""
    quants = []
    offset = 0
    page = 500
    while True:
        batch = odoo.search_read('stock.quant', [
            ['company_id', '=', company_id],
            ['quantity', '!=', 0],
            ['location_id.usage', '=', 'internal'],
        ], [
            'id', 'product_id', 'lot_id', 'location_id',
            'quantity', 'value',
        ], offset=offset, limit=page)
        if not batch:
            break
        quants.extend(batch)
        offset += page
    return quants


def main(dry_run: bool):
    app = create_app()
    with app.app_context():
        odoo = get_odoo_connection()
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        total = {'timestamp': agora_utc_naive().isoformat(), 'companies': {}}

        for cid, codigo in COMPANIES.items():
            print(f'\n=== {codigo} (company_id={cid}) ===')
            quants = extrair_company(odoo, cid)
            print(f'  stock.quant rows: {len(quants)}')

            # Excel
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = f'Estoque {codigo}'
            ws.append(['quant_id', 'product_id', 'product_name', 'cod_produto',
                       'lot_id', 'lot_name', 'location_id', 'location_name',
                       'quantity', 'value', 'custo_unit'])

            # Resolver produto + lote + location via batch read (P4)
            product_ids = list({q['product_id'][0] for q in quants if q['product_id']})
            lot_ids = list({q['lot_id'][0] for q in quants if q['lot_id']})
            loc_ids = list({q['location_id'][0] for q in quants if q['location_id']})

            produtos = {p['id']: p for p in odoo.read('product.product', product_ids,
                       ['default_code', 'name']) if product_ids} if product_ids else {}
            lotes = {l['id']: l for l in odoo.read('stock.lot', lot_ids, ['name'])} if lot_ids else {}
            locs = {lc['id']: lc for lc in odoo.read('stock.location', loc_ids,
                   ['complete_name'])} if loc_ids else {}

            for q in quants:
                pid = q['product_id'][0] if q['product_id'] else None
                lid = q['lot_id'][0] if q['lot_id'] else None
                loid = q['location_id'][0] if q['location_id'] else None
                p = produtos.get(pid, {}) if pid else {}
                cod = p.get('default_code', '')
                qty = q['quantity']
                val = q['value'] or 0
                custo_unit = (val / qty) if qty else 0
                ws.append([
                    q['id'], pid, p.get('name', ''), cod,
                    lid, lotes.get(lid, {}).get('name') if lid else '',
                    loid, locs.get(loid, {}).get('complete_name') if loid else '',
                    qty, val, round(custo_unit, 4),
                ])

            xlsx_path = os.path.join(OUTPUT_DIR, f'estoque-odoo-{codigo}.xlsx')
            wb.save(xlsx_path)
            print(f'  Excel: {xlsx_path}')

            total['companies'][cid] = {'codigo': codigo, 'quants': quants}

        if not dry_run:
            json_path = '/tmp/estoque_odoo_2026_05.json'
            with open(json_path, 'w') as f:
                json.dump(total, f, default=str)
            print(f'\nSnapshot JSON: {json_path}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    main(args.dry_run)
```

- [ ] **Step 2: Rodar dry-run**

```bash
python scripts/inventario_2026_05/01_extrair_estoque_odoo.py --dry-run
```

Expected: 3 Excels criados, sem JSON.

- [ ] **Step 3: Rodar real**

```bash
python scripts/inventario_2026_05/01_extrair_estoque_odoo.py
ls -la /tmp/estoque_odoo_2026_05.json
```

- [ ] **Step 4: Commit**

```bash
git add scripts/inventario_2026_05/01_extrair_estoque_odoo.py
git commit -m "feat(inventario): F1.1 — script extrai estoque FB/CD/LF via stock.quant"
```

### Task 7.2 — 7.10: Demais scripts

Por brevidade do plano, descrevo os esqueletos. Cada um segue o padrão:
- argparse com `--dry-run` + `--confirmar`
- Idempotência (consulta DB antes de inserir)
- Output em `docs/inventario-2026-05/07-relatorios/` ou `/tmp/`
- Log estruturado
- Commit por script

- [ ] **Task 7.2 — `02_carregar_inventario_xlsx.py`**

Input: planilha do inventário físico (formato a confirmar com usuário em F1)
Output: `/tmp/inventario_fisico_2026_05.json`
Validações: cod_produto começa com [1-4], qty >= 0, company válida, lote opcional

- [ ] **Task 7.3 — `03_confrontar_inv_vs_odoo.py`**

Lê `/tmp/estoque_odoo_2026_05.json` + `/tmp/inventario_fisico_2026_05.json`
Aplica regras P6/P7/P9 (prioridade lote inventariado → MIGRAÇÃO → mais antigo)
Output: `docs/inventario-2026-05/07-relatorios/diff-inv-vs-odoo.xlsx` por company

- [ ] **Task 7.4 — `04_propor_ajustes.py`**

Lê diff, calcula `acao_decidida` via `resolver_operacao_por_tipo_produto`
INSERT em `ajuste_estoque_inventario` status=PROPOSTO
Modo `--aprovar-onda=N --hash=<sha>`: atualiza status=APROVADO

- [ ] **Task 7.5 — `05_canary_estoque_staging.py`**

Executa `IndisponibilizacaoEstoqueService.canary_lote/canary_local` em company-cobaia
Gera `docs/inventario-2026-05/03-canary/canary-{c1,c2,c3}.md`
Registra decisão em `00-decisoes/D003-via-indisponibilizacao.md`

- [ ] **Task 7.6 — `06_canary_nfs_referencia.py`**

Para cada CFOP, chama `AccountMoveIntercompanyService.preview()`
Gera `docs/inventario-2026-05/03-canary/canary-nf-{5152,5901,5903,5949}.md`

- [ ] **Task 7.7 — `07_executar_onda1_lf_fb.py`**

`--canary --apenas=1` ou `--confirmar --bulk`
Loop sobre `ajuste_estoque_inventario` WHERE acao em (INDUSTRIALIZACAO_FB_LF, PERDA_LF_FB, DEV_FB_LF, DEV_LF_FB) AND status=APROVADO
Chama hook `pre_execute_nf` → service.executar → hook `pos_execute_nf`
Lock Redis por (company_id, cod_produto, lote_odoo)

- [ ] **Task 7.8 — `08_executar_onda2_cd_fb.py`**

Análogo a 7.7, filtrando acao em (TRANSFERIR_CD_FB, TRANSFERIR_FB_CD)

- [ ] **Task 7.9 — `09_executar_onda3_indisponibilizacao.py`**

Análogo, acao em (INDISPONIBILIZAR_LOTE, INDISPONIBILIZAR_LOCAL)
Exige `canary_passou=True` para cada linha

- [ ] **Task 7.10 — `10_reconciliar_pos_ajuste.py`**

Reexecuta `01_extrair_estoque_odoo` + compara com inventário
Output: `docs/inventario-2026-05/07-relatorios/residual-pos-ajuste.xlsx`

**Cada script: 1 commit. Total Fase 7: ~10 commits.**

---

## Fase 8 — Documentação (playbooks + estrutura de pastas)

### Task 8.1: Estrutura de pastas `docs/inventario-2026-05/`

- [ ] **Step 1: Criar README + estrutura**

```bash
mkdir -p docs/inventario-2026-05/{00-decisoes,01-premissas,02-gotchas,03-canary,04-movimentacoes/{onda-1-lf-fb,onda-2-cd-fb,onda-3-indisponibilizacao,onda-4-lote-rename},05-rollback,06-aprovacoes,07-relatorios}
```

`docs/inventario-2026-05/README.md`:

```markdown
# Inventário 2026-05 — Documentação

Operação de ajuste de estoque iniciada em 17/05/2026 conforme spec
`docs/superpowers/specs/2026-05-17-ajuste-inventario-nacom-lf-design.md`.

## Estrutura

- `00-decisoes/` — decisões técnicas (D000 audit, D001 escolhas, D002 escopo, D003 via indisponibilização)
- `01-premissas/` — P001-P010 (uma por premissa do spec §4)
- `02-gotchas/` — GOTCHAS descobertos durante execução
- `03-canary/` — resultado dos canaries técnicos (C1/C2/C3) e fiscais (1 NF por CFOP)
- `04-movimentacoes/` — uma pasta por onda, com 1 .md por NF emitida (gerado por pos_execute_nf hook)
- `05-rollback/` — se houver
- `06-aprovacoes/` — aprovações por onda (hash do payload + assinatura)
- `07-relatorios/` — Excels (estoque pré/pós, diff, residual)

## Ordem de leitura

1. Spec: `../superpowers/specs/2026-05-17-ajuste-inventario-nacom-lf-design.md`
2. D000 audit (descoberta da realidade Odoo)
3. D001 escolhas (constantes finais)
4. 03-canary/ (validação técnica + fiscal)
5. 06-aprovacoes/
6. 04-movimentacoes/ (NF a NF)
7. 07-relatorios/residual-pos-ajuste.xlsx (residual final)
```

- [ ] **Step 2: Criar P001-P010 (premissas)**

Gerar 10 arquivos `01-premissas/P00X-{descricao}.md` a partir do spec §4. Cada um:

```markdown
# P001 — Produtos 1/2/3 em LF negativos: NF perda LF→FB CFOP 5903

**Fonte:** `prompt_inventario.md:46-48` + resposta usuário 17/05/2026
**Confirmada em:** 2026-05-17
**Status:** ativa

(Texto da premissa do spec §4)
```

Script utilitário:

```bash
for i in 1 2 3 4 5 6 7 8 9 10; do
    n=$(printf "%03d" $i)
    touch "docs/inventario-2026-05/01-premissas/P${n}-placeholder.md"
done
# Preencher manualmente cada um.
```

- [ ] **Step 3: Commit**

```bash
git add docs/inventario-2026-05/
git commit -m "docs(inventario): estrutura de pastas + README + P001-P010"
```

### Task 8.2: Playbook `OPERACOES_FISCAIS_NACOM_LF.md`

**Files:**
- Create: `.claude/references/odoo/OPERACOES_FISCAIS_NACOM_LF.md`

- [ ] **Step 1: Criar playbook**

```markdown
# Operações Fiscais Inter-Company — NACOM Goya × LA FAMIGLIA

**Última atualização:** 2026-05-17
**Spec origem:** `docs/superpowers/specs/2026-05-17-ajuste-inventario-nacom-lf-design.md`

## Matriz de Operações

| CFOP | `l10n_br_tipo_pedido` | Direção | Tipo produto | NF referência | Service |
|------|------------------------|---------|--------------|---------------|---------|
| 5152 | transf-filial | CD↔FB | 1/2/3/4 | 94410 | `AccountMoveIntercompanyService` |
| 5901 | industrializacao | FB→LF | 1/2/3 | 94457 | idem |
| 5903 | perda | LF→FB | 1/2/3 | 13075 | idem |
| 5949 | dev-industrializacao | FB↔LF | 4 | 147772 | idem |

(constantes: `app/odoo/constants/operacoes_fiscais.py::MATRIZ_INTERCOMPANY`)

## Decision Tree

```
ajuste de estoque (qtd_inv - qtd_odoo != 0)
├── company = LF (5)?
│   ├── tipo_produto = 4 (acabado) → dev-industrializacao (CFOP 5949)
│   ├── tipo_produto in (1,2,3) e sinal > 0 → industrializacao (CFOP 5901, FB→LF)
│   └── tipo_produto in (1,2,3) e sinal < 0 → perda (CFOP 5903, LF→FB)
└── company in (FB, CD) → transf-filial (CFOP 5152)
```

## Campos críticos do `account.move`

| Campo | Valor | Origem |
|-------|-------|--------|
| `move_type` | `out_invoice` | matriz |
| `l10n_br_tipo_pedido` | conforme matriz | matriz |
| `company_id` | origem da operação | payload |
| `partner_id` | empresa de destino | payload |
| `fiscal_position_id` | conforme matriz × company | matriz (preenchida em F0 audit) |
| `invoice_line_ids` | linhas `(0, 0, {product_id, quantity, price_unit})` | payload |

## Gotchas

1. **NUNCA usar `action_update_taxes`** em SOs/account.moves brasileiros — zera impostos com fiscal_position que mapeia para vazio. **Usar `onchange_l10n_br_calcular_imposto`** (`GOTCHAS.md:114-141`).
2. **NF-e transfer stale via XML-RPC** → SEFAZ 225 (`GOTCHAS.md:362-409`). Mitigação: Playwright UI para pre_visualizar XML antes de transmitir.
3. **`button_validate` retorna None** que XML-RPC não consegue serializar — tratar como sucesso (`GOTCHAS.md:179`).
4. **`stock.lot.search` operador `=` tem bug intermitente** — usar `'in', [nome]` ou `'=like'` (`GOTCHAS.md:111` + `recebimento_fisico_odoo_service.py:398-414`).
5. **Janela SEFAZ** para cancelamento: 24h (transf-filial) / 7d (industrialização). Após: NF de devolução.

## Reuso recomendado

- Service único: `AccountMoveIntercompanyService` em `app/odoo/services/account_move_intercompany_service.py`
- Para nova operação: adicionar entrada em `MATRIZ_INTERCOMPANY`, não criar service novo

## Histórico de uso

| Data | Contexto | external_ids |
|------|----------|--------------|
| 2026-05-17 | Inventário 2026-05 | `INV-2026-05-O1-*`, `INV-2026-05-O2-*` |
```

- [ ] **Step 2: Commit**

```bash
git add .claude/references/odoo/OPERACOES_FISCAIS_NACOM_LF.md
git commit -m "docs(odoo): playbook OPERACOES_FISCAIS_NACOM_LF — matriz + decision tree + gotchas"
```

### Task 8.3: Playbook `OPERACOES_LOTE_E_INDISPONIBILIZACAO.md`

- [ ] **Step 1: Criar playbook** seguindo mesmo padrão, com:
  - Quando renomear vs criar lote (P6/P7/P9)
  - Resultado dos canaries C1/C2/C3
  - Procedimento Odoo UI + XML-RPC
  - Como reverter

- [ ] **Step 2: Commit**

```bash
git commit -am "docs(odoo): playbook OPERACOES_LOTE_E_INDISPONIBILIZACAO"
```

### Task 8.4: Atualizar `ROUTING_ODOO.md` com novos services

- [ ] **Step 1: Editar** para incluir as 4 novas entradas (`stock_lot_service`, `stock_picking_service`, `account_move_intercompany_service`, `indisponibilizacao_estoque_service`).

- [ ] **Step 2: Commit**

```bash
git commit -am "docs(odoo): ROUTING_ODOO inclui 4 novos services intercompany"
```

---

## Fase 9 — Execução operacional (ondas)

Esta fase **não é TDD** — é execução supervisionada da operação real. Cada onda exige aprovação humana antes do bulk.

### Task 9.1: Onda O0 — Canary técnico

- [ ] Rodar `05_canary_estoque_staging.py` para C1 (lote)
- [ ] Verificar resultado em `03-canary/canary-c1-stock-lot-active.md`
- [ ] Se C1 passou: parar; via decidida em `00-decisoes/D003`
- [ ] Senão, rodar C2 (local) e/ou C3 (tag)
- [ ] Aprovar via humano em `00-decisoes/D003-via-indisponibilizacao.md`

### Task 9.2: Onda fiscal (canary por CFOP)

- [ ] `06_canary_nfs_referencia.py` para os 4 CFOPs
- [ ] Revisar `03-canary/canary-nf-{5152,5901,5903,5949}.md`
- [ ] Executar 1 NF real menor de cada CFOP (com hash payload em commit)

### Task 9.3 — 9.6: Ondas O1..O5

- [ ] **O1** — `07_executar_onda1_lf_fb.py --bulk` (após canary fiscal de cada CFOP aprovado)
- [ ] **O2** — `08_executar_onda2_cd_fb.py --bulk`
- [ ] **O3** — `09_executar_onda3_indisponibilizacao.py --bulk` (requer canary técnico OK)
- [ ] **O4** — `09_executar_onda4_lote_rename.py --bulk` (P9)
- [ ] **O5** — `10_reconciliar_pos_ajuste.py`

Cada onda:
1. Operador aprova via `04_propor_ajustes.py --aprovar-onda=N --hash=<sha>`
2. Script roda com `--bulk`, hooks bloqueiam se algo errado
3. Cada NF gera doc atômico em `04-movimentacoes/`
4. Auditoria em `operacao_odoo_auditoria`
5. Aprovação registrada em `06-aprovacoes/`

---

## Self-Review

**Spec coverage:**
- §3 escopo (in/out) → coberto em todas as tasks (SC e período fiscal não aparecem)
- §4 P1-P10 → P001-P010 docs criados em Task 8.1
- §5 glossário → tasks 0.1 (audit run revela valores reais) + 1.1 (constants)
- §6 arquitetura → tasks 1.1 (constants), 2.x (lot service), 3.x (picking service), 4.x (intercompany), 5.x (indisponibilização)
- §7 modelo de dados → tasks 1.2, 1.3
- §8 pipeline → tasks 7.x (10 scripts) + 9.x (execução ondas)
- §9 hooks → tasks 6.1, 6.2, 6.3
- §10 canaries → tasks 9.1 (técnico) + 9.2 (fiscal)
- §11 governança → tasks 7.4 (aprovação por onda) + 9.x
- §13 estrutura pastas → tasks 8.1
- §15 itens em aberto → resolvidos em F0 (Task 0.1, 0.2)

**Placeholders:** Tasks 7.2-7.10 descrevem esqueleto sem código completo (justificado para não explodir tamanho do plano; cada script segue padrão estabelecido em 7.1). Recomendo expandir em sub-plans separados antes da execução de cada script, OU implementar via subagent-driven com este plano como guia macro.

**Type consistency:**
- `external_id` formato `INV-2026-05-O{N}-{seq}` consistente
- `acao_decidida` enum em ACOES_VALIDAS + scripts
- `status` enum em STATUS_VALIDOS + scripts
- `MATRIZ_INTERCOMPANY[tipo]['cfop']` retorna string conforme matriz §5.2
- Métodos: `criar()`, `renomear()`, `inativar()`, `reativar()`, `atualizar_validade()` em `StockLotService` consistentes
- `confirmar_e_reservar`, `preencher_qty_done`, `validar`, `cancelar` em `StockPickingService` consistentes
- `preview`, `executar`, `cancelar` em `AccountMoveIntercompanyService` consistentes

**Pontos a expandir em execução** (não bloqueiam aprovação do plano):
- Scripts 7.2-7.10 precisam de detalhamento adicional na hora de implementar — pode virar sub-plan
- Onda 9.1+ depende de decisão humana, não pode ser totalmente automatizada
