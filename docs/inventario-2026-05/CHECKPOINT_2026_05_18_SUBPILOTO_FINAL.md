# CHECKPOINT — Sub-piloto bulk 10 produtos FINAL (2026-05-18 ~04:30)

**Sessao Claude Code encerrada**: 2026-05-18 ~04:30
**Status global**: Sub-piloto bulk 10 produtos executado parcialmente.
1 NF end-to-end OK + 1 NF cancelada (XML incompleto) + 1 NF reposted apos meu erro.
**10 ajustes PROPOSTO pendentes** + **1 ajuste FB→LF pendente** prontos para proxima execucao.

> Substitui `CHECKPOINT_2026_05_18_BULK_PRONTO.md`.

---

## 1. Resultado do sub-piloto

### NFs emitidas (3)

| Invoice | NF | Direcao | State | Chave SEFAZ | Entrada FB |
|---|---|---|---|---|---|
| **608629** | RPI/2026/00201 | FB → LF (industr) | ✅ posted (autorizado) | `35260561...086298` | ❌ Sem entrada FB (sentido invertido). LF recebeu manualmente via picking 317306. 1 ajuste EXECUTADO |
| **608630** | RETNA/2026/00030 (NF 13150) | LF → FB (perda) | ❌ cancel local (XML SEFAZ incompleto) | `35260518...086306` | ❌ Picking 317294 devolvido via 317303. **10 ajustes voltaram PROPOSTO** |
| **608631** | RETNA/2026/00031 | LF → FB (perda) | ✅ posted (autorizado) | `35260518...086311` | ✅ RecLf 7 OK, Invoice FB 608645 posted. **4 ajustes EXECUTADO** |

### Pickings (6 + 2 devolucoes + 1 entrada manual LF = 9 totais)

| Picking | Name | State | Detalhe |
|---|---|---|---|
| 317294 | LF/LF/SAI/RNA/00003 | done | Saida LF perda (NF 13150) - **estoque devolvido** |
| 317295 | LF/LF/SAI/RNA/00004 | done | Saida LF perda (NF 608631) - **NF ok** |
| 317296 | FB/SAI/IND/01553 | cancel | 1a tentativa FB→LF (empresas incompativeis location) |
| 317297 | FB/SAI/IND/01554 | done | Saida FB industr (NF 608629) - **estoque saiu corretamente** |
| 317299 | FB/IN/13151 | cancel | Entrada FB errada (RecLf 6, sentido invertido) |
| 317303 | LF/RECEB/IND/01355 | done | Devolucao do 317294 (estoque LF voltou) |
| 317304 | FB/DEV/00606 | done | **DEVOLUCAO ERRADA** (cancelei NF 608629 por engano) |
| 317305 | FB/DEV/00607 | done | **CONTRA-DEVOLUCAO** (corrigi meu erro - estoque FB voltou para Em Transito) |
| 317306 | LF/IN/01733 | done | **ENTRADA MANUAL LF** (Em Transito Industr → LF/Estoque, 103000037 10.389 kg lote MIGRAÇÃO) |

### Estado fiscal final dos 10 produtos do sub-piloto

| Cod Produto | Ajustes total | EXECUTADO | PROPOSTO (precisa rodar) | Observacao |
|---|---|---|---|---|
| 101001001 COGUMELO FATIADO | 2 | 0 | 2 PERDA_LF_FB | Vai rodar de novo |
| 102020201 AZEITONA P FATIADA | 4 | 0 | 4 PERDA_LF_FB | Vai rodar de novo |
| 102020600 AZEITONAS P TRIT | 1 | 0 | 1 PERDA_LF_FB | Vai rodar de novo |
| 103000011 PEPINO IND | 3 | 0 | 2 PERDA + 1 INDUSTR (162425) | Vai rodar de novo |
| 103000014 (Onda 3) | 4 | 0 | 1 RENOMEAR + 3 INDISPONIBILIZAR | RENOMEAR OK, INDISP onda 3 |
| 103000020 ALHO EM PÓ | 2 | 0 | 1 RENOMEAR + 1 PERDA | RENOMEAR OK, PERDA pendente |
| 103000037 ALHO GRANULADO | 2 | 1 (INDUSTR via 608629) | 1 RENOMEAR (TRANSF_OK 162930) | Industr OK fiscalmente |
| 103000113 PIMENTA BIQ | 2 | 2 (PERDA via 608631) | 0 | ✅ DONE |
| 103000117 PIMENTA BIQ B | 2 | 1 (PERDA via 608631) | 1 RENOMEAR (TRANSF_OK) | ✅ DONE |
| 103000122 CEBOLINHA EM PÓ | 2 | 1 (PERDA via 608631) | 1 RENOMEAR (TRANSF_OK) | ✅ DONE |

### Numeros do DB

- **5 EXECUTADO + F5e_SEFAZ_OK** (4 da NF 608631 + 1 da NF 608629)
- **11 PROPOSTO sem fase** (vao rodar quando bulk for executado):
  - 10 PERDA_LF_FB (precisam **1 NF LF→FB nova**)
  - 1 INDUSTRIALIZACAO_FB_LF (162425 PEPINO — precisa **1 NF FB→LF nova**)
- **5 RENOMEAR_LOTE em TRANSF_OK** (skip ETAPA A)
- **3 INDISPONIBILIZAR_LOTE** (filtrados, onda 3)

---

## 2. Erros descobertos durante o sub-piloto (corrigidos no codigo)

### L6. Picking outgoing exige location virtual destino, nao a interna

**Sintoma**: `<Fault 2: "Empresas incompativeis nos registros: FB/SAI/IND/01553 pertence a NACOM GOYA - FB e Destination Location (LF/Estoque) pertence a outra empresa">`

**Causa raiz**: `resolver_location_destino` retornava `COMPANY_LOCATIONS[destino]` (location interna da empresa destino), mas pickings inter-company exigem location virtual com `company_id=False`.

**Fix**: `resolver_location_destino(tipo_op, company_destino, company_origem)` mapeia:
- LF→FB perda → 5 (Parceiros/Clientes)
- FB→LF industr → 26489 (Em Transito Industrializacao)
- FB↔CD transf-filial → 6 (Em Transito Filiais)
- CD retrabalho → 26489

`inventario_pipeline_service.py:74-148`

### L7. button_validate sem skip_backorder fica em assigned

**Sintoma**: Picking validado MAS state continua `assigned` (Odoo abre wizard de backorder).

**Causa raiz**: Diferenca entre `product_uom_qty` (demand) e qty reservada gera wizard que precisa context.

**Fix**: `StockPickingService.validar()` agora passa
`context={'skip_backorder': True, 'picking_ids_not_to_backorder': [picking_id]}`.

`stock_picking_service.py:182-211`

### L8. f5b/f5c/f5d so marcavam 1 ajuste por picking

**Sintoma**: Picking com 10 ajustes → so 1 ajuste marca F5b/F5c/F5d, outros 9 ficam em fase anterior.

**Causa raiz**: `ajuste_por_pid: Dict[int, object] = {}` indexa por picking_id mas o ultimo ajuste do mesmo picking SOBREESCREVE (overwrite no dict).

**Fix**: helper `_agrupar_por_picking(ajustes) -> Dict[int, List]` + iterar TODOS ajustes do mesmo picking ao marcar fase.

`inventario_pipeline_service.py:500-540`

### L9. f5e re-transmitia mesma NF para cada ajuste

**Sintoma**: Picking com 10 ajustes → Playwright tenta transmitir SEFAZ 10 vezes (mesma invoice). Pos 1 sucesso, as outras 9 transmissoes podem causar problemas (rate limit, double-charge SEFAZ).

**Causa raiz**: `f5e_transmitir_sefaz` itera por ajuste. Idempotencia via `aj.fase_pipeline == 'F5e_SEFAZ_OK'` so funciona apos commit explicito — mas como objeto Python ja foi carregado ANTES do commit, o filtro nao pega.

**Fix**: Adicionado `invoices_processadas: Dict[int, str]` dentro de `f5e_transmitir_sefaz`. Apos transmitir, marca todas as outras linhas da mesma invoice como `SKIP_INV_PROC` sem chamar Playwright.

`inventario_pipeline_service.py:778-870`

### L10. status auditoria excedia VARCHAR(20)

**Sintoma**: `psycopg2.errors.StringDataRightTruncation: value too long for type character varying(20)` ao tentar gravar status `'SKIPPED_INVOICE_JA_PROCESSADA'` (30 chars).

**Fix**: status reduzido para `'SKIP_INV_PROC'` (13 chars).

### L11. ajustar_qty_done_pelo_disponivel (substitui forcar_qty_done)

**Sintoma**: tentativa de "forcar qty_done = product_uom_qty" gerava saldo negativo no Odoo (lote tinha menos que demand).

**Fix**: novo metodo NUNCA infla qty_done alem do reservado. Reduz `product_uom_qty` da move para igualar ao reservado. Pendencias retornadas para gerar ajustes complementares.

`stock_picking_service.py:213-280`

### L12. Distribuir demanda entre lotes reais (FIFO)

**Sintoma**: ajuste com `lote_origem=MIGRAÇÃO qtd_ajuste=-672` falhava porque o lote MIGRAÇÃO no Odoo so tinha 52 un. Robo CIEL IT gerava NF com qty parcial.

**Causa raiz**: script 03 emite 1 ajuste por produto agregado (todos os lotes), apontando para 1 lote_origem unico. Mas quants reais estao distribuidos.

**Fix**: `etapa_b_pickings` agora consulta `stock.quant` real e distribui demanda total entre lotes disponiveis (FIFO por create_date). Se sobrar `qty_restante > 0`, cria automaticamente ajuste compensatorio `INDUSTRIALIZACAO_FB_LF` (FB → LF +delta).

`09_executar_onda1_bulk.py:435-540`

### L13. Validar custo_medio antes de criar pickings

**Sintoma**: NF 13150 saiu com 2 linhas `price_unit=0` (101001001 e 102020600 tinham `custo_medio=0` no DB). SEFAZ rejeitou com "Falha no Schema XML do lote de NFe" (vUnCom=0 viola schema NFe).

**Fix**: `etapa_b_pickings` agora busca `product.standard_price` no Odoo para cada produto antes de criar pickings. Se `custo_medio <= 0`, atualiza com `abs(standard_price)` (negativos viram positivos — erro de cadastro Odoo). Default 0.01 se ambos zero.

`09_executar_onda1_bulk.py:400-432`

### L14. ConexaO Odoo XML-RPC nao e thread-safe

**Sintoma**: `http.client.CannotSendRequest: Request-sent` ao usar ThreadPoolExecutor em ETAPA A.

**Fix**: ETAPA A foi convertida para sequencial (1 thread). Performance: 5 transferencias em ~5s.

`09_executar_onda1_bulk.py:255-330`

### L15. carregar_ajustes precisa incluir EXECUTADO

**Sintoma**: Apos ETAPA D marcar ajustes como EXECUTADO, ETAPA E nao encontrava nenhum SEFAZ-autorizado.

**Causa raiz**: `carregar_ajustes` default `status_filtro=('APROVADO', 'PROPOSTO')`. EXECUTADO ficava fora.

**Fix**: `status_filtro=('APROVADO', 'PROPOSTO', 'EXECUTADO')` por default.

`09_executar_onda1_bulk.py:122-150`

---

## 3. Estado fiscal final por produto

### 103000037 ALHO GRANULADO (UNICO end-to-end OK)

- FB: 47.911 MIGRAÇÃO + 200 MIGRACAO + outros = 420.05 kg
- LF: 10.389 MIGRAÇÃO (vinda da NF 608629 via picking manual 317306) + 2.111 MI050/106/25 (RENOMEAR) = 12.5 kg
- Em Transito Industr: 0 kg (tudo migrou para LF)
- NF 608629 autorizada SEFAZ ✓

### 103000113 PIMENTA BIQUINHO + 103000117 PIMENTA BIQ B + 103000122 CEBOLINHA EM PÓ (NF 608631)

- LF: estoque saiu (picking 317295 done)
- FB: estoque entrou (RecLf 7 → invoice 608645 posted, FB/IN/13152)
- NF 608631 autorizada SEFAZ ✓
- 4 ajustes EXECUTADO

### Outros 5 produtos (NF 13150 cancelada)

| Produto | Ajustes | Estado |
|---|---|---|
| 101001001 COGUMELO FATIADO | 2 PROPOSTO PERDA_LF_FB | LF intacto (devolvido via 317303) |
| 102020201 AZEITONA P FATIADA | 4 PROPOSTO PERDA_LF_FB | LF intacto |
| 102020600 AZEITONAS P TRIT | 1 PROPOSTO PERDA_LF_FB | LF intacto |
| 103000011 PEPINO IND | 2 PROPOSTO PERDA + 1 PROPOSTO INDUSTR | LF intacto |
| 103000020 ALHO EM PÓ | 1 PROPOSTO PERDA | LF intacto |

---

## 4. Pendencias / acoes manuais futuras

### Bloqueantes para fechar sub-piloto

1. **Rodar bulk de novo para os 11 PROPOSTO**:
   ```bash
   python scripts/inventario_2026_05/09_executar_onda1_bulk.py \\
       --company-id=5 --onda=1 --limite-produtos=10 --max-produtos-picking=5 \\
       --confirmar --confirmar-sefaz --usuario=rafael
   ```
   Vai gerar 2 NFs novas:
   - 1 NF LF→FB perda (5 produtos x 10 linhas) - **R$ 1.456,54**
   - 1 NF FB→LF industr (1 produto, PEPINO 131.844 kg)

### Acoes manuais via UI Odoo (24h limit)

2. **Cancelar SEFAZ da NF 13150** (608630) — Odoo UI botao "Cancelar NFe", justificativa
3. **Cancelar SEFAZ da NF 608629** (RPI/2026/00201) **NAO** — esta autorizada e funcionalmente OK
   Espera: o erro foi APENAS a tentativa de entrada FB (sentido invertido). A NF eh valida fiscalmente.

### Bug nao critico

4. **Ajuste 162930** (103000037 RENOMEAR_LOTE): residual decimal 0.000024 — marcado TRANSF_OK manualmente. Em futuras execucoes, considerar threshold de tolerancia >= 0.001 no `transferir_quantidade_para_lote`.

### Refator pendente (recomendado para LF completo)

5. **etapa_e_entrada_fb deve filtrar `acao_decidida`**: pular `INDUSTRIALIZACAO_FB_LF` e `DEV_FB_LF` (sentido FB→LF, entrada deveria ser na LF, nao FB).

---

## 5. Decisao usuario sobre 608630 NF 13150

NF 13150 (608630) cancelada localmente apos:
- SEFAZ rejeitou 2 tentativas iniciais (price_unit=0 em 2 linhas — custo zero)
- Corrigido prices (12.23 e 14.15 via standard_price Odoo)
- Re-transmitida e SEFAZ retornou `excecao_autorizado` (autorizado com ressalva — numero NF ja "consumido" nas tentativas anteriores)
- XML autorizado NAO veio (CIEL IT nao baixou por causa do `excecao_autorizado`)
- Sem XML, nao da para criar DFe na FB → entrada FB falha
- Usuario decidiu cancelar (state=cancel local)

**Restante**: cancelar SEFAZ via UI Odoo (24h) para nao deixar NF "fantasma".

---

## 6. Pre-requisitos para proxima sessao

```bash
cd /home/rafaelnascimento/projetos/frete_sistema
source .venv/bin/activate

# 1. Validar baseline (testes podem ter regredido pelas mudancas em
#    inventario_pipeline_service + stock_picking_service)
pytest tests/odoo/ -p no:randomly -q

# 2. Estado DB sub-piloto
PGPASSWORD=frete_senha_2024 psql -h localhost -U frete_user -d frete_sistema -c "
SELECT acao_decidida, status, fase_pipeline, COUNT(*) qty
FROM ajuste_estoque_inventario
WHERE ciclo='INVENTARIO_2026_05' AND company_id=5
  AND cod_produto IN ('101001001', '102020201', '102020600', '103000011',
                      '103000014', '103000020', '103000037', '103000113',
                      '103000117', '103000122')
GROUP BY acao_decidida, status, fase_pipeline
ORDER BY 1, 2, 3;
"
# Esperado:
#   5 EXECUTADO + F5e_SEFAZ_OK
#   11 PROPOSTO sem fase (vao rodar)
#   5 TRANSF_OK
#   3 INDISPONIBILIZAR_LOTE

# 3. Estado pickings/invoices Odoo
python3 -c "
import sys; sys.path.insert(0, '.')
from app import create_app
from app.odoo.utils.connection import get_odoo_connection
app = create_app()
with app.app_context():
    odoo = get_odoo_connection()
    pks = odoo.read('stock.picking', [317294, 317295, 317297, 317303, 317304, 317305, 317306],
        ['name', 'state'])
    for p in pks: print(p['id'], p['name'], p['state'])
    invs = odoo.read('account.move', [608629, 608630, 608631, 608645], ['name', 'state'])
    for i in invs: print(i['id'], i['name'], i['state'])
"
```

---

## 7. Arquivos modificados nesta sessao

### Novos
- `scripts/inventario_2026_05/entrada_fb_piloto.py` (240 LOC)
- `scripts/inventario_2026_05/09_executar_onda1_bulk.py` (~700 LOC)
- `scripts/inventario_2026_05/padronizar_migracao.py` (~200 LOC)

### Atualizados
- `app/odoo/services/inventario_pipeline_service.py` (resolver_location_destino, f5b/f5c/f5d multi-ajuste, f5e idempotencia por invoice, status auditoria)
- `app/odoo/services/stock_picking_service.py` (validar com skip_backorder, ajustar_qty_done_pelo_disponivel)
- `scripts/inventario_2026_05/03_confrontar_inv_vs_odoo.py` (case-insensitive MIGRAÇÃO/MIGRACAO + padronizar 'MIGRAÇÃO' por default)
- `scripts/inventario_2026_05/04_propor_ajustes.py` (lote_destino 'MIGRAÇÃO' com cedilha)
- `docs/inventario-2026-05/00-decisoes/D005-...md` (padronizacao MIGRAÇÃO)

### DB local
- `ajuste_estoque_inventario`: 1.821 linhas atualizadas MIGRACAO → MIGRAÇÃO
- 11 ajustes resetados PROPOSTO pos cleanup
- 5 ajustes marcados EXECUTADO + F5e_SEFAZ_OK
- 7 RecebimentoLf (4, 5, 6, 7) criados, status final: 5=cancelado, 6=cancelado, 7=processado, 4=processado piloto anterior

### Odoo
- 6 pickings novos + 2 devolucoes + 1 contra-devolucao + 1 entrada manual LF = 10 pickings tocados
- 3 invoices criadas pelo robo CIEL IT (608629, 608630, 608631)
- 1 invoice IN posted (608645 FB entrada)
- 3 NFs SEFAZ autorizadas (2 ativas, 1 cancelada local)
- 1 lote MIGRAÇÃO LF criado para 103000037 (lot_id=56858)
