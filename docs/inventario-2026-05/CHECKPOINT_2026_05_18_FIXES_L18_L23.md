# CHECKPOINT — Sub-piloto bulk 10 produtos (re-execucao apos fixes L18-L23)

**Sessao Claude Code encerrada**: 2026-05-18 ~06:35
**Status global**: Sub-piloto end-to-end validado com 6 novos fixes (L18-L23).

> Substitui `CHECKPOINT_2026_05_18_SUBPILOTO_FINAL.md`.

---

## 1. Pipeline executado end-to-end

| Etapa | Resultado |
|---|---|
| A — Transferencias lote | 5 SKIP (TRANSF_OK ja feito) |
| B — Pickings | 2 criados (317311 LF perda 10 ajustes + 317313 FB industr 3 ajustes apos G014) |
| C — Aguardar invoices CIEL IT | 2 invoices criadas em ~40s (626032 + 627348) |
| D — SEFAZ Playwright | 2 NFs autorizadas (1ª tentativa em 627348, 6ª em 626032) |
| E — Entrada FB | 1 SKIP (627348 L17) + 1 FALHA G008 (626032 XML vazio) |

**Resultado**: 13 ajustes EXECUTADO + F5e_SEFAZ_OK.

## 2. NFs emitidas (2)

| Invoice | NF | Direcao | State | Chave SEFAZ | XML aut | Entrada FB |
|---|---|---|---|---|---|---|
| 626032 | RETNA/2026/00032 | LF→FB perda | posted | `35260518...26032` | ❌ vazia (G008) | RecLf 8 FALHA |
| 627348 | RPI/2026/00202 | FB→LF industr | posted | `35260561...73480` | ✅ OK | Pulado (L17) |

## 3. 6 novos fixes descobertos (L18-L23)

Vistos em runtime durante esta sessao apos checkpoint anterior:

### L18 (G010) — `tipo_divergencia` invalido no modelo

`scripts/inventario_2026_05/09_executar_onda1_bulk.py` chamava
`AjusteEstoqueInventario(tipo_divergencia=...)` mas o campo nao existe.
Fix: usar `erro_msg=[COMPENSATORIO_FALTA_ESTOQUE] ...`.

### L19 (G011) — `preencher_qty_done` faltando no pipeline (RAIZ CRITICA)

`action_assign` cria move_lines com `qty_done=0`. Sem preencher antes do
`button_validate`, picking falha "Nao e possivel validar sem reservas" e
peso/volumes ficam 0 → action_liberar_faturamento falha.

Fix: `f5b_validar_pickings(linhas_por_picking=...)` chama
`preencher_qty_done` ENTRE `confirmar_e_reservar` e `ajustar_qty_done`.

### L20 (G012) — peso_liquido vazio (consequencia L19)

Resolvido pela cadeia L19. CIEL IT computa peso via `qty_done * weight`.

### L21 (G013) — volumes vazios (consequencia L19)

Resolvido pela cadeia L19. CIEL IT computa volumes via qty_done.

### L22 (G014) — FEFO bloqueia auto-reserva em lotes vencidos

Odoo CIEL IT recusa reservar quants em lotes com `expiration_date < hoje`,
mesmo com livre > 0. PEPINO IND tinha 72k livres mas TODOS vencidos.

**Fix arquitetural**: em `etapa_b_pickings`, antes de criar picking:
1. Separar `quants_validos` vs `quants_vencidos` (consultar `stock.lot.expiration_date`)
2. Se `livre_validos < demand` e `livre_vencidos > 0`:
   - Criar lote novo `INV-{cod}-{YYYYMMDD}` com `exp = hoje + 365 dias`
   - Transferir qty necessaria de lote vencido FIFO → lote novo via
     `StockInternalTransferService.transferir_quantidade_para_lote`
3. Re-consultar quants (lote novo aparece valido)
4. Distribuir FIFO apenas entre `quants_validos`

Validado: PEPINO 168 kg transferido `0110/24 (vencido 2025-10-01)` → `INV-103000011-20260518 (exp 2027-05-18)`.

### L23 (G015) — price_unit=0 auto-fix em invoice pos-CIEL IT

Robo CIEL IT as vezes nao popula `price_unit` em algumas linhas. SEFAZ
rejeita XML schema (vUnCom=0).

**Fix**: `_corrigir_price_zero_em_invoice` em pipeline_service, chamado em
`f5d_aguardar_invoices` (fase F5d.6):
1. Identifica linhas com price_unit<=0
2. Busca `product.standard_price`
3. button_draft + write price_unit + action_post
4. Audit em OperacaoOdooAuditoria fase='F5d.6'

Validacao: Invoice 626032 — 2 linhas corrigidas
(101001001 0 → 12.232, 102020600 0 → 14.154).

## 4. Bug pendente nao corrigido (G016)

**SSL crash no f5e_transmitir_sefaz perde commits** — DB local
desincroniza com Odoo (chave SEFAZ no Odoo, F5d_INVOICE_GERADA no DB).

Solucao proposta (Opcao A + C):
- TCP keepalive na connection string (`?keepalives=1&keepalives_idle=30`)
- Commit antes de cada Playwright + re-busca por ID

**OBRIGATORIO antes do bulk LF completo (660 produtos)** — sem isso, qualquer
SSL drop durante transmissao SEFAZ deixa DB inconsistente.

Doc: `docs/inventario-2026-05/02-gotchas/G016-ssl-crash-no-loop-f5e-perde-commits.md`

## 5. Pickings/invoices criados (recovery)

Pickings cancelados (sem invoice/SEFAZ):
- 317307, 317308 (L18 falha tipo_divergencia)
- 317309, 317310 (L19 reserva 0 + L20/L21 cascata)
- 317312 (L22 PEPINO sem lote valido — antes de G014 fix)

Pickings finais sub-piloto:
- 317311 LF/LF/SAI/RNA/00007 → invoice 626032 RETNA/2026/00032
- 317313 FB/SAI/IND/01558 → invoice 627348 RPI/2026/00202

## 6. Acoes manuais pendentes para fechar sub-piloto

### Bloqueante para LF completo

1. **Implementar G016 (resiliencia SSL)** ANTES de bulk LF completo
   - Adicionar TCP keepalive em SQLALCHEMY_DATABASE_URI
   - Refator `f5e_transmitir_sefaz` com commit antes Playwright

### Acao manual via UI Odoo (24h limit)

2. **Re-consultar SEFAZ NF 626032** (RETNA/2026/00032) para baixar XML
   completo. Sem isso, entrada FB falha permanentemente (G008).

3. **NF 627348 sem entrada FB necessaria** (sentido FB→LF industrializacao).
   Entrada manual na LF se necessario.

## 7. Pre-requisitos para proxima sessao

```bash
cd /home/rafaelnascimento/projetos/frete_sistema
source .venv/bin/activate

# 1. Validar baseline (130 passing apos L18-L23)
pytest tests/odoo/ -p no:randomly -q

# 2. Estado DB pos-sub-piloto
PGPASSWORD=frete_senha_2024 psql -h localhost -U frete_user -d frete_sistema -c "
SELECT acao_decidida, status, fase_pipeline, COUNT(*) qty
FROM ajuste_estoque_inventario
WHERE ciclo='INVENTARIO_2026_05' AND company_id=5
  AND cod_produto IN ('101001001', '102020201', '102020600', '103000011',
                      '103000020')
GROUP BY acao_decidida, status, fase_pipeline
ORDER BY 1, 2, 3;
"

# 3. Estado pickings/invoices Odoo
python3 -c "
import sys; sys.path.insert(0, '.')
from app import create_app
from app.odoo.utils.connection import get_odoo_connection
app = create_app()
with app.app_context():
    odoo = get_odoo_connection()
    pks = odoo.read('stock.picking', [317311, 317313], ['name', 'state'])
    for p in pks: print(p['id'], p['name'], p['state'])
    invs = odoo.read('account.move', [626032, 627348], ['name', 'state', 'l10n_br_chave_nf'])
    for i in invs: print(i['id'], i['name'], i['state'], i.get('l10n_br_chave_nf'))
"
```

## 8. Bugs corrigidos vs pendentes — visao consolidada

### Sessao corrente (2026-05-18 madrugada)

| # | Categoria | Status | Localizacao |
|---|---|---|---|
| L18 | tipo_divergencia inexistente | ✅ FIXADO | 09_executar_onda1_bulk.py |
| L19 | preencher_qty_done no pipeline | ✅ FIXADO | inventario_pipeline_service.py + script |
| L20 | peso_liquido vazio | ✅ FIXADO (via L19) | (cascata) |
| L21 | volumes vazios | ✅ FIXADO (via L19) | (cascata) |
| L22 | Lote vencido bloqueia reserva | ✅ FIXADO | 09_executar_onda1_bulk.py etapa_b |
| L23 | price_unit=0 auto-fix em invoice | ✅ FIXADO | inventario_pipeline_service.py f5d.6 |
| G016 | SSL crash no f5e | ⚠️ PENDENTE | Bloqueante para LF completo |

### Sessoes anteriores

L1-L5 (piloto 210030325), L6-L17 (sub-piloto bulk 10 produtos): ✅ todos FIXADOS

## 9. Arquivos modificados nesta sessao

### Atualizados
- `tests/odoo/services/test_inventario_pipeline_service.py` — 4 tests obsoletos atualizados para refletir G006
- `app/odoo/services/inventario_pipeline_service.py` — L19 (`f5b_validar_pickings` aceita `linhas_por_picking`), G015 (`_corrigir_price_zero_em_invoice` + chamada em f5d.6)
- `scripts/inventario_2026_05/09_executar_onda1_bulk.py` — L17 filtro etapa_e, L18 fix tipo_divergencia, L19 passar linhas para f5b, L22 G014 protection lote vencido

### Novos (gotchas)
- `docs/inventario-2026-05/02-gotchas/G010-tipo-divergencia-nao-existe.md`
- `docs/inventario-2026-05/02-gotchas/G011-preencher-qty-done-faltando.md`
- `docs/inventario-2026-05/02-gotchas/G012-peso-liquido-vazio.md`
- `docs/inventario-2026-05/02-gotchas/G013-quantidade-volumes-vazio.md`
- `docs/inventario-2026-05/02-gotchas/G014-fefo-lotes-vencidos-bloqueia-reserva.md`
- `docs/inventario-2026-05/02-gotchas/G015-protecao-price-zero-automatica.md`
- `docs/inventario-2026-05/02-gotchas/G016-ssl-crash-no-loop-f5e-perde-commits.md` (PENDENTE)

### Atualizado
- `docs/inventario-2026-05/00-decisoes/D006-...md` — secao "Licoes aprendidas L22-L23"

### DB local
- 13 ajustes em F5e_SEFAZ_OK (4 produtos do PEPINO industr + 5 produtos da perda LF→FB)
- Recovery: 10 ajustes sincronizados manualmente apos SSL crash do f5e

### Odoo
- 4 pickings cancelados (317307-317310, 317312) — sem invoice/SEFAZ
- 2 pickings done (317311, 317313)
- 2 invoices posted com SEFAZ autorizado (626032 com xml_vazio G008, 627348 OK)
- 1 RecebimentoLf 8 FALHA (G008 confirmado)
- 1 lote NOVO criado `INV-103000011-20260518` (exp 2027-05-18) — 168 kg PEPINO

## 10. Resumo executivo

**O que funcionou neste sub-piloto**:
- L17 (filtro etapa E) validado em producao
- L18 (tipo_divergencia fix) — 0 falhas pos-fix
- L19 (preencher_qty_done) — pipeline F5b/F5c agora funciona com lotes reais
- G014 (protecao lote vencido) — transferencia automatica funcionou em PEPINO
- G015 (protecao price_unit=0) — implementada e testada manualmente em 626032
- SEFAZ Playwright: 2/2 NFs autorizadas (1ª tentativa em 627348)

**O que precisa fazer na proxima sessao**:
- Implementar G016 (resiliencia SSL) ANTES de bulk LF completo
- Re-consultar SEFAZ 626032 via UI (XML vazio bloqueando entrada FB)
- Considerar trato manual ou re-criacao para 626032 (24h limit cancel)

**Quando estiver tudo OK** (G016 implementado + 626032 tratado):
- Rodar LF completo (~660 produtos restantes) com `--max-produtos-picking=30`
- Audit pre-execucao G014 (quantos produtos com 0 lote valido) e G007 (custos)
