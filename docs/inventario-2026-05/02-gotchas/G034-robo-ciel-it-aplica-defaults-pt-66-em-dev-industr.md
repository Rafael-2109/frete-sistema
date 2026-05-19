# G034 — Robô CIEL IT aplica defaults PT 66 em DEV_* (CFOP 5124 errado)

**Status**: ✅ FIXADO (sessão 4, 2026-05-18 19:25)
**Severidade**: CRITICAL (NF saiu com CFOP fiscalmente errado)
**Descoberta**: Batch 5 DEV_LF_FB — NF 629962 VND/2026/00320 SEFAZ excecao_autorizado
**Picking**: 317497 LF/SAI/IND/01868 (5 cods)

## Sintoma

Para ações `DEV_LF_FB` (e simetricamente `DEV_LF_CD`, `DEV_CD_LF`), o
script bulk cria picking com `picking_type=66 LF Expedição Industrialização`.
O robô CIEL IT cria invoice a partir do picking, mas **ignora**
`MATRIZ_INTERCOMPANY[dev-industrializacao]` e aplica os **defaults do PT 66**:

| Campo | Esperado (matriz) | Real (NF 629962) |
|---|---|---|
| `l10n_br_tipo_pedido` | `dev-industrializacao` | **`venda-industrializacao`** ❌ |
| `fiscal_position_id` | 89 SAÍDA - RETRABALHO | **111 SAÍDA - SERVIÇO DE INDUSTRIALIZAÇÃO** ❌ |
| CFOP nas linhas | **5949** (Outra saída) | **5124 - Industrialização efetuada p/ outra empresa** ❌ |
| Journal | 1002 SARET | **847 VND VENDA DE PRODUÇÃO** ❌ |
| Prefixo NF | SARET/AAAA/NNNN | **VND/2026/00320** ❌ |

NF de referência válida (4,5) CD→LF: `590839 RRET/2026/00008` usa journal 987 RRET + FP 74 + tipo `dev-industrializacao` + CFOP 5949.

## Causa raiz

`PICKING_TYPE_POR_DIRECAO[(5, 'dev-industrializacao')] = 66` aponta para um PT que **não tem default fiscal setup** para devolução de retrabalho. PT 66 LF: Expedição Industrialização tem default journal=VND/847 + FP=111 + tipo=`venda-industrializacao` (usado quando LF VENDE serviço de industrialização para terceiro).

Não existe PT LF dedicado para "saída de retrabalho" entre os 12 PTs ativos.

## Fix implementado (v2 — 2026-05-18 19:38)

`app/odoo/services/inventario_pipeline_service.py`:

1. **Constante `FISCAL_SETUP_POR_ACAO`** — mapping ação → {fiscal_position_id, l10n_br_tipo_pedido}:
   ```python
   FISCAL_SETUP_POR_ACAO = {
       'DEV_LF_FB': {fp=89 SAÍDA - RETRABALHO (LF), tipo='dev-industrializacao'},
       'DEV_LF_CD': {fp=89 SAÍDA - RETRABALHO (LF), tipo='dev-industrializacao'},
       'DEV_CD_LF': {fp=74 SAÍDA - REMESSA P/ RETRABALHO (CD), tipo='dev-industrializacao'},
       # DEV_FB_LF: fora (P011 — FP 74 está em CD, não em FB)
   }
   ```

2. **Helper `_garantir_fiscal_setup(invoice_id, aj, executado_por)`** — idempotente:
   - Skip se acao_decidida não está em FISCAL_SETUP_POR_ACAO (PERDA, INDUSTR, RENOMEAR)
   - Skip se invoice já SEFAZ-autorizada (`situacao_nf in autorizado/excecao_autorizado`)
   - Skip se FP/tipo já estão corretos
   - Senão: `button_draft` → `write {fp, tipo}` → `action_post`

3. **Chamado em F5d.7** — logo após F5d.5 (payment_provider) e F5d.6 (price_zero), ANTES de F5e (SEFAZ Playwright).

### Limitação descoberta na 1ª iteração (v1)

**Odoo bloqueia troca de `journal_id` após primeira postagem**: 
> "Você não pode editar o diário de uma movimentação de conta se ela foi lançada uma vez"

Mesmo após `button_draft`, o `journal_id` permanece imutável. v1 tentou setar `journal_id=1002 SARET` no write — falhou. v2 removeu o campo.

**Consequência**: NF retém prefixo `VND/AAAA/NNNN` (do journal VND default do PT 66). Não saí com prefixo `SARET/...` como na NF referência. **Mas CFOP nas linhas vem da FP** (via tax mapping de `account.fiscal.position`) — FP 89 → CFOP 5949. Fiscalmente OK; apenas o prefixo de série fica "estranho".

Para resolver prefixo, opções (fora deste fix):
- Criar PT LF dedicado "Saída Retrabalho" com defaults journal=SARET + FP=89
- Criar invoice manualmente do zero (bypass robô CIEL IT)
- Cancelar e re-emitir manualmente após auto-emissão

### Bug colateral corrigido (v1→v2)

`OperacaoOdooAuditoria.acao` é VARCHAR(20). Valor inicial `'garantir_fiscal_setup'` (21 chars) excedia → crash em flush. Renomeado para `'fix_fiscal_setup'` (16 chars).

## Consequência sem fix

NF SEFAZ-autorizada com CFOP 5124 (industrialização) ao invés de 5949 (devolução de retrabalho). Fiscalmente:
- Receita Federal pode questionar a operação
- ICMS aplicado errado
- ENTRADA na FB (via RecebimentoLf) também sairia com CFOP 1124 espelho ao invés de 1949
- Contadora precisaria fazer carta de correção ou cancelamento

## Recovery do incidente original (batch 5 DEV_LF_FB)

NF 629962 já SEFAZ-autorizada (excecao_autorizado, chave 35260518467441000163550010000131581006299626):

1. Cancelar SEFAZ via UI Odoo (botão "Cancelar NF-e", janela 24h)
2. Criar `stock.return.picking` do 317497 (devolução de estoque)
3. Reset 9 ajustes para PROPOSTO sem fase/picking_id/invoice_id/chave_nfe
4. Re-rodar batch com fix G034 ativo

Pickings 317495 e 317496 não chegaram a ter invoice → revertidos via returns 317501, 317502 (done). 10 ajustes desses já resetados.

## Limitação conhecida

- **DEV_FB_LF não suportado**: FP 74 está cadastrada em CD (company=4), não em FB (company=1). Para habilitar FB→LF, contadora precisa cadastrar FP equivalente em FB (P011). Sem isso, write fiscal_position_id=74 num account.move da FB falha.
- **`name` da invoice muda**: quando journal é trocado via write, sequence é re-aplicada. NF antiga (ex: VND/2026/00320) deixa "buraco" na sequence VND e ganha novo nome SARET/.../NNNN. Isso é OK — só pula um número.

## Referências

- `app/odoo/services/inventario_pipeline_service.py:158-188` (FISCAL_SETUP_POR_ACAO)
- `app/odoo/services/inventario_pipeline_service.py:_garantir_fiscal_setup`
- `app/odoo/services/inventario_pipeline_service.py:f5d_aguardar_invoices` (F5d.7)
- NF referência válida: `account.move 590839 RRET/2026/00008` (CD→LF)
- NF inválida: `account.move 629962 VND/2026/00320` (LF→FB, **deve ser cancelada**)
