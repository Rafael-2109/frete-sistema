# G038 — `product.l10n_br_origem` ausente bloqueia transmissão SEFAZ via modal Odoo silencioso

**Severidade**: HIGH (bloqueio SEFAZ + Playwright loop sem efeito)
**Status**: ✅ DOCUMENTADO + DETECÇÃO PRE-FLIGHT CODIFICADA (2026-05-27 v22+ — retry pipeline INVENTARIO_2026_05 expôs o gotcha)
**Detecção pre-flight**: ✅ Sub-skill C5 `auditando-cadastro-fiscal-odoo` v22+ (perfil 'inventario') — bloqueia faturamento ANTES de criar picking.
**Escopo**: Qualquer fluxo que crie account.move out_invoice cujo cadastro de produto esteja com `l10n_br_origem in (False, None, '')`.

## Sintoma

1. Pipeline cria picking + libera para CIEL IT → invoice criada (`state=posted`, `l10n_br_situacao_nf='rascunho'`, `l10n_br_show_nfe_btn=True`).
2. Playwright SEFAZ clica em "Transmitir NF-e" no painel.
3. **Modal nativo do Odoo abre**: `Aviso do Odoo — "Produtos sem Origem" [IR PARA PRODUTOS] [Fechar]`.
4. `_tratar_wizard_confirmacao` do Playwright (`app/recebimento/services/playwright_nfe_transmissao.py:216`) **só trata o wizard padrão de confirmação** — não detecta esse modal específico.
5. Playwright tira screenshot pós-click + aguarda 25s + verifica via XML-RPC → `cstat=False, xmotivo=False, situacao=rascunho` (SEFAZ nunca foi acionado — modal interceptou).
6. Loop 15 tentativas × ~2min = ~28min sem efeito. Final: `nao_autorizada_apos_15_tentativas`.

## Causa raiz

O campo `product.product.l10n_br_origem` é OBRIGATÓRIO para NF-e válida (Tabela A do Manual da SEFAZ — "Origem da Mercadoria"):
- `'0'` — Nacional, exceto as indicadas nos códigos 3 a 5
- `'1'` — Estrangeira – Importação direta
- `'2'` — Estrangeira – Adquirida no mercado interno
- `'3'`–`'8'` — Outras situações (importação > 40%, conteúdo nacional, etc.)

Quando o produto está com esse campo VAZIO (False/None/''), o Odoo CIEL IT **intercepta o `action_gerar_nfe` ANTES de transmitir** e abre modal de aviso. O usuário humano vê e corrige; o Playwright NÃO trata e fica em loop.

## Como detectar (PRE-FLIGHT — RECOMENDADO)

Use a Sub-skill C5 ANTES de iniciar pipeline:

```bash
# Auditar pre-flight de um ciclo inteiro
python -m app.odoo.estoque.scripts.cadastro_fiscal_audit \
  --ciclo INVENTARIO_2026_05 --perfil inventario
```

Output esperado quando há produto com G038:

```json
{
  "status_global": "PRE_FLIGHT_BLOQUEADO",
  "pode_faturar": false,
  "bloqueios": {
    "origem_ausente": [
      {"id": 34907, "default_code": "104000046",
       "name": "CORANTE VERMELHO",
       "l10n_br_origem": false, "gotcha": "G038"}
    ],
    "ncm_faltando": [],
    "barcode_invalido": [],
    "duplicacao_pipeline": []
  }
}
```

## Solução (manual — NÃO há auto-fix)

Não há auto-fix porque o orquestrador não sabe a origem correta do produto (depende da operação fiscal: nacional vs importado).

**Operador deve setar via XML-RPC** (ou painel):

```python
from app.odoo.utils.connection import get_odoo_connection
odoo = get_odoo_connection()
odoo.write('product.product', [PRODUCT_ID], {'l10n_br_origem': '0'})  # 0=Nacional
```

Ou via UI Odoo: abrir produto → aba "Compras/Vendas" → "Origem do Produto" → selecionar.

## Como evitar

1. **SEMPRE rodar Sub-skill C5 pre-flight** antes de iniciar pipeline de faturamento. Captura G017+G018+G035+G038+D-OPS-2/3 em 1 query.
2. **Cadastro de produto novo** deve incluir `l10n_br_origem` obrigatório (ou validação em formulário de cadastro).
3. **Caso o Playwright detecte modal "Produtos sem Origem"** futuramente, estender `_tratar_wizard_confirmacao` para abortar com erro CLARO (em vez de loop silencioso). Pendência separada.

## Onde está codificado

- **Sub-skill C5**: `app/odoo/estoque/scripts/cadastro_fiscal_audit.py`
  - `_check_ncm_weight_tracking` (estende read com `l10n_br_origem`, retorna `origem_ausente`)
  - `auditar_perfil_inventario` (adiciona `origem_ausente` em `bloqueios`)
- **Pytest**: `tests/odoo/services/test_cadastro_fiscal_audit.py`
  - `test_check_ncm_weight_tracking_g038_origem_ausente_bloqueia`
  - `test_auditar_perfil_inventario_bloqueia_g038_origem_ausente`
- **Referência rápida**: `.claude/references/odoo/GOTCHAS.md` (tabela G011-G038)

## Caso real (descoberta)

- **Data**: 2026-05-27 (retry pipeline INVENTARIO_2026_05)
- **Produto**: 104000046 CORANTE VERMELHO (id=34907)
- **Estado**: `l10n_br_origem=False` (default cadastro antigo nunca preenchido)
- **Invoice afetada**: 716448 RPI/2026/00238 (FB→LF industrialização)
- **Tempo perdido**: ~28min em loop Playwright sem efeito
- **Fix**: setar `l10n_br_origem='0'` (Nacional) — operação ID-direta CICLAMATO/CORANTE LF/FB todos nacionais.
