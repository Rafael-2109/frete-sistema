# Pendências — INVENTARIO_2026_05

**Última atualização**: 2026-05-20

Lista de itens pendentes (não executados) que precisam ser tratados antes do fechamento do ciclo.

---

## P1 — Padronização completa de lotes para `MI ###-###/AA`

**Status**: PENDENTE
**Pré-requisitos**: ondas 1+2 D004 concluídas (LF + FB+CD)
**Referência**: `01-premissas/PADRONIZACAO_LOTES.md` §5

### Resumo
Aplicar regex `{["MI",""," "]###[.,-]###/AA}` → `MI ###-###/AA` em todos os `stock.lot` das companies FB (1), CD (4), LF (5).

### Escopo
- Lotes que batem o padrão regex (ver `PADRONIZACAO_LOTES.md` §2)
- Não inclui: `MIGRAÇÃO`, `MIGRACAO`, lotes legados sem prefixo MI mas com formato diferente (`T20241014`, `2507/24`, `12892`, etc.)
- Casos limítrofes (`MI 46 - 197/24` — n1=2 dígitos): decisão manual caso a caso

### Subtarefas
- [ ] Listar todos os `stock.lot` candidatos (regex match) — gerar Excel
- [ ] Identificar colisões (mesmo nome canônico → múltiplos `stock.lot.id`)
- [ ] Decidir merge/manter para cada colisão
- [ ] Aplicar `stock.lot.write({'name': canonico})` em batch (transação reversível com snapshot)
- [ ] Atualizar `ajuste_estoque_inventario.lote_odoo` e `lote_inventariado` (rename refletido)

### Riscos
- Renames de `stock.lot` afetam **histórico** (todos os `stock.move.line` apontam para esse lot.id). É reversível mas afeta auditoria
- Colisões podem forçar consolidação de lotes (mesmo cod, lotes diferentes precisam virar um) — pode envolver transferência interna pré-rename

---

## P2 — Desfazer ajustes emergenciais FB (2026-05-18)

**Status**: PENDENTE (depende da execução prévia dos emergenciais)
**Pré-requisitos**: ondas 1+2 D004 concluídas; antes de P1
**Referência**: `AJUSTES_EMERGENCIAIS_FB.md` §6

### Resumo
Reverter as 9 transferências internas emergenciais E01..E09 da FB. Cada uma gera um picking interno **espelho** (PARA → DE com mesma QTD), ou usa `stock.return.picking` wizard.

### Subtarefas
- [ ] Para cada E01..E09 executado: confirmar `picking.name` na tabela §5 de `AJUSTES_EMERGENCIAIS_FB.md`
- [ ] Criar picking reverso (DE/PARA invertidos)
- [ ] Validar saldo Odoo do lote DE retornou ao estado pré-emergencial
- [ ] Marcar P2 como concluído

### Por quê
Os ajustes emergenciais **não passam pelo fluxo D004**. Eles criam grafias paralelas de lote no Odoo (ex: `MI 027-098/26` emergencial + `MI 027-098/26` original já existente; `MI 138-311/25` emergencial + `MI138-311/25` planejado). Sem reverter:
- Histórico de inventário fica com dois pickings opostos não reconciliados (não destrutivo, mas ruidoso)
- Padronização P1 herda colisões artificiais

### Alternativa: NÃO reverter
Aceitar saldo emergencial como saldo final do lote PARA → necessário recalcular `ajuste_estoque_inventario` da onda 1+2 para esses 9 lotes. Mais trabalhoso que reverter; **não recomendado** salvo decisão explícita do usuário.

---

## P3 — Lote `MI036-124/26` cod `104000002` não inventariado na FB

**Status**: PENDENTE — verificação no Odoo
**Referência**: `AJUSTES_EMERGENCIAIS_FB.md` E02

### Resumo
Usuário citou `MI036-124/26` para cod `104000002` com 143,5 unidades. Esse par (cod, lote_inventariado) **não consta** em `ajuste_estoque_inventario` do ciclo INVENTARIO_2026_05 para FB. Possibilidades:
1. Lote físico real existe no estoque FB, mas não foi contado na contagem de 16/05 → emergencial cobre o gap
2. Erro de digitação do usuário (lote correto pode ser outro, ex: `MI036-124/25` ou semelhante)
3. Lote existe no Odoo mas com saldo zero → criar via emergencial é OK

### Subtarefas
- [ ] Buscar no Odoo: `stock.lot` cod `104000002` com nome ILIKE `036-124`
- [ ] Se existir com saldo: validar com Rafael se o número 143,5 procede
- [ ] Se não existir: criar `stock.lot` antes de executar E02
- [ ] Documentar resultado nesta seção

### Comando de verificação

```python
import sys; sys.path.insert(0, '.')
from app import create_app
from app.odoo.utils.connection import get_odoo_connection
app = create_app()
with app.app_context():
    odoo = get_odoo_connection()
    lots = odoo.search_read('stock.lot',
        [['product_id.default_code', '=', '104000002'],
         ['name', 'ilike', '036']],
        ['id', 'name', 'company_id', 'product_qty'], limit=20)
    print(lots)
```

---

## P4 — Divergências de quantidade (lista usuário 2026-05-18 vs planilha 16/05)

**Status**: ACEITO (decisão usuário aplicar lista nova como emergencial)
**Referência**: `AJUSTES_EMERGENCIAIS_FB.md` §1 (origem das quantidades)

### Resumo
5 dos 9 lotes da lista emergencial têm QTD divergente da planilha original `COMPILADO INV. 16.05.2026.xlsx`:

| Cod | Lote | QTD lista 2026-05-18 | QTD inventário 16/05 | Diferença |
|---|---|---|---|---|
| 104000004 | MI 025-091/26 | 53 | 14,4 | +38,6 |
| 104000018 | MI 168-349/25 | 35,4 | 533,01 | -497,61 |
| 104000006 | MI 138-311/25 | 6,4 | 77,69 | -71,29 |
| 104000001 | MI 031-092/25 | 6,635 | 31,635 | -25 |
| 104000037 | MI 074-177/25 | 5 | 3,676 | +1,324 |

### Hipóteses (não decididas)
- Consumo/produção entre 16/05 e 18/05 movimentou esses lotes
- Recontagem física revisou os números
- Planilha original tinha erro nesses lotes específicos

### Implicação
Após executar os 9 emergenciais, o plano D004 onda 1+2 da FB **ainda usa as quantidades da planilha 16/05**. Para os 5 codes com divergência, o RENOMEAR_LOTE (qty_ajuste=0) ainda planeja renomear 533,01 / 77,69 / 31,635 / 14,4 / 3,676 (não 35,4 / 6,4 / 6,635 / 53 / 5).

### Subtarefas
- [ ] Decidir: regenerar D004 para esses 5 codes usando QTDs novas?
- [ ] OU manter D004 com QTD antiga e aceitar diferença como ajuste de inventário pós-execução (saldo final será divergente)?
- [ ] Documentar decisão aqui

---

## P5 — 104000016 lote `T20241014` — drift de plano após emergencial

**Status**: PENDENTE — depende de execução E06
**Referência**: `AJUSTES_EMERGENCIAIS_FB.md` E06

### Resumo
Lote `T20241014` cod `104000016` tem ajuste D004 planejado `INDISPONIBILIZAR_LOTE` (qtd_inv 280,1 vs qtd_odoo 15.500 → ajuste -15.219,9). Após emergencial E06 (transferir +280,1 do MIGRAÇÃO para `T20241014`):
- Saldo Odoo do lote = 15.500 + 280,1 = 15.780,1
- Plano D004 `INDISPONIBILIZAR_LOTE` ficou com base divergente
- Onda 3 (INDISPONIBILIZAR_*) ainda não foi liberada — há tempo para recalcular

### Subtarefas
- [ ] Após E06: recalcular ajuste D004 desse lote ou aceitar drift
- [ ] Se aceitar: documentar nova qtd alvo (zerar 15.780,1 em vez de 15.219,9)

---

## P7 — E09 emergencial FB ~~PENDENTE~~ RESOLVIDO (2026-05-18 14:38)

**Status**: ✅ RESOLVIDO via ajuste de inventário puro (opção D — decisão usuário)
**Referência**: `AJUSTES_EMERGENCIAIS_FB.md` §5.1

### Solução aplicada
Cod 104000003 não tinha saldo livre em FB/Estoque (todos os lotes 100% reservados em 19 pickings antigos). Decisão usuário foi NÃO mexer em pickings ativos e fazer **ajuste de inventário direto**:

```
quant_id=229239 product_id=30490 cod=104000003 location_id=8 lot_id=57350 ('MI 021-065/26')
inventory_quantity=30 → action_apply_inventory
stock.move 1098999: 'Estoque Virtual/Ajuste de Inventario' → 'FB/Estoque' qty=30
```

### Implicações
- Saldo TOTAL do cod 104000003 na FB aumentou em 30 un (entrada nova, não transferência)
- Origem do estoque: "Estoque Virtual/Ajuste de Inventario" (loc 14) — sem rastreamento fiscal
- Ajuste contábil de inventário fica como pendência (ver P8)

---

## P8 — 19 pickings antigos do cod 104000003 reservando FB/Estoque

**Status**: PENDENTE — rastreamento operacional
**Descoberto durante E09 em 2026-05-18**
**Referência**: `AJUSTES_EMERGENCIAIS_FB.md` §6

### Resumo
Levantamento revelou 19 `stock.picking` em `state=assigned` com `stock.move.line` reservando o cod 104000003 em FB/Estoque (loc 8). O mais antigo (`FB/INT/03746`) tem **252 dias de idade** (criado 09/09/2025). Reservam todo o saldo do produto, travando operações.

### Padrões observados
- 16 pickings tipo `FB/INT/` (interno) com origin `C25.../C26...` — cotações cliente
- 2 pickings tipo `FB/FB/EMB/` (embalagem) com origin `FB/OP/SALMOURA/...` — ordens de produção
- Maioria de 2025-Q4 (out-dez) ou 2026-Q1 (fev) — nenhum recente

### Hipóteses
1. Pickings nunca foram validados após criação automática (cancelamentos esquecidos)
2. Pedidos cliente foram cancelados mas os pickings ficaram órfãos
3. Bug em alguma sincronização que cria picking sem caminho de fechamento

### Subtarefas
- [ ] Para cada um dos 19 picking_id: verificar status do `origin` (`sale.order` ou `mrp.production`)
- [ ] Se origem cancelada: cancelar picking via UI Odoo ou XML-RPC `button_cancel`
- [ ] Se origem ativa mas obsoleta: validar com operação
- [ ] Documentar padrão (origem→ação) para evitar recorrência

### Lista completa
Ver `AJUSTES_EMERGENCIAIS_FB.md` §6 (tabela com 19 entradas).

---

## P10 — Lotes emergenciais em FB/Estoque, não em Linha de Pré-Produção

**Status**: PENDENTE — depende do uso operacional dos lotes
**Descoberto durante consulta usuário em 2026-05-18 14:44**
**Referência**: `AJUSTES_EMERGENCIAIS_FB.md` §5

### Resumo
Os 9 lotes do ajuste emergencial (E01-E09) foram colocados em **FB/Estoque (loc 8)**. Esse é o estoque de "prateleira" / acabado — **não permite apontamento direto de `mrp.production`**.

### Mapa de Linhas de Pré-Produção FB

Fonte: `stock.picking.type` com `code='mrp_operation'` company_id=1.

| Linha | location_id | picking_type_id |
|---|---|---|
| FB/Pré-Produção/Linha Balde | 4068 | 27 (default warehouse FB) |
| FB/Pré-Produção/Linha Vidro | 4066 | 67 |
| FB/Pré-Produção/Linha Salmoura | 27458 | 70 |
| FB/Pré-Produção/Linha Retrabalho | 27457 | 71 |
| FB/Pré-Produção/Linha Manual | 4067 | 72 |
| FB/Pré-Produção/Linha Industrialização LF | 30718 | 85 |

Todas as `mrp.production` da FB têm `location_src_id` numa dessas linhas e `location_dest_id = FB/Pós-Produção (loc 48)`.

### Fluxo correto
```
FB/Estoque (8)
  ↓ stock.picking tipo FB/FB/EMB/* (Odoo gera automaticamente quando OP é confirmada)
FB/Pré-Produção/Linha XXX
  ↓ mrp.production "Produção (FB)"
FB/Pós-Produção (48)
```

### Subtarefas
- [ ] Confirmar para cada um dos 9 lotes emergenciais qual Linha de Pré-Produção é a destino habitual do produto (consultar BoM ou histórico de movimentações)
- [ ] Se for usar em produção: criar `stock.picking` tipo FB/FB/EMB/* movendo o lote de FB/Estoque para a Linha correta — ou deixar Odoo gerar automaticamente ao confirmar a OP

---

## P9 — Ajuste contábil para entrada inventory adjustment E09 (30 un cod 104000003)

**Status**: PENDENTE — financeiro/contábil
**Referência**: `AJUSTES_EMERGENCIAIS_FB.md` §5.1

### Resumo
O ajuste de inventário do E09 entrou 30 un sem origem fiscal (operação puramente operacional Odoo). Para regularizar contabilmente:
- Lançar ajuste de inventário contábil (Inventory Adjustment Entry) reconhecendo a entrada
- Avaliar custo unitário a aplicar (default: custo médio do cod 104000003 no momento)
- Não envolve NF — é ajuste de Patrimônio (Estoque ↑, Resultado de Inventário ↑)

### Subtarefas
- [ ] Definir valor contábil (custo médio cod 104000003 = ?)
- [ ] Lançar entry contábil no Odoo (account.move tipo entry) ou aceitar default do action_apply_inventory
- [ ] Verificar se o `action_apply_inventory` já criou entry automática (provável — Odoo 16 gera valuation move)

---

## P6 — Picking 317346 LF pendente invoice CIEL IT

**Status**: PENDENTE — em rastreio
**Empresa**: LF (cid=5)
**Referência**: `PICKINGS_PENDENTES_INVOICE.md`

### Resumo
Picking `FB/SAI/IND/01559` (id 317346) em `state=done` aguardando robô CIEL IT criar invoice. 21 ajustes INDUSTRIALIZACAO_FB_LF travados em `fase=F5c_LIBERADO`.

> Não relacionado a P1-P5 (escopo FB), mas mantido aqui como pendência global do ciclo.

---

## P11 — 10 produtos sem cadastro Odoo no CD

**Status**: PENDENTE — administrativo
**Empresa**: CD (`company_id=4`)
**Descoberto durante**: execução pré-etapa CD (D007 onda 5)
**Referência**: `CHECKPOINT_2026_05_18_CD_FINALIZADO.md` §3 Cat1_SEM_CADASTRO_ODOO

### Resumo

10 códigos de produto aparecem na planilha de inventário físico do CD mas **não têm `product.product` correspondente no Odoo CIEL IT**. Resultado: 10 ajustes `AJUSTE_CD_POSITIVO_PURO` ficaram em status `FALHA` com `erro_msg='Cat1_SEM_CADASTRO_ODOO'`.

### Lista completa

| cod | qty no inventário físico |
|---|---|
| 20100051 | 7.200 |
| 201230027 | 4.070 |
| 20200416 | 210 |
| 20203001 | 7.465 |
| 26000130 | 2.000 |
| 26000404 | 180 |
| 4310154 | 35 |
| 4320161 | 1 |
| 4360158 | 50 |
| 4866112 | 56 |

### Subtarefas (opção cadastrar)

- [ ] Admin Odoo cadastra `product.product` para cada cod (categoria, NCM, unidade de medida, fiscal_position)
- [ ] Reverter status FALHA → APROVADO:
  ```sql
  UPDATE ajuste_estoque_inventario
  SET status='APROVADO', erro_msg=NULL, fase_pipeline=NULL
  WHERE ciclo='INVENTARIO_2026_05' AND company_id=4 AND status='FALHA'
    AND erro_msg LIKE 'Cat1_SEM_CADASTRO_ODOO%';
  ```
- [ ] Re-rodar:
  ```bash
  python scripts/inventario_2026_05/09b_executar_pre_etapa.py \
      --company-id=4 --confirmar --max-workers=5 --usuario=rafael
  ```

### Alternativa: aceitar pendência

Não cadastrar os 10 produtos no Odoo. Estoque físico continua no CD mas Odoo não reflete. Implica: vendas/separações desses cods não vão funcionar via Odoo enquanto o cadastro estiver pendente. Para uso interno operacional, pode ser aceito temporariamente.

### Relacionado

Esta pendência convive com `Cat1_PRODUTO_ARQUIVADO` (8 ajustes, 4 produtos: 19, 44, 45, 201402) — esses já existem no Odoo mas com `active=False`. Decisão similar: admin reativa OU aceita saldo escondido.

---

## P12 — 9 produtos LF do Pasta17 com lotes dessincronizados (realocação não aplicável)

**Status**: PENDENTE — aguarda planilha regenerada
**Empresa**: LF (`company_id=5`)
**Descoberto em**: 2026-05-20 (realocação Pasta17 — ver [D012](00-decisoes/D012-ajuste-estoque-lf-via-planilha-direta.md))

### Resumo

Dos 147 produtos da Pasta17 (realocação net-zero), **138 foram aplicados**. Os 9 abaixo **não puderam** ser aplicados: a planilha pede reduzir lotes que, no estado atual do Odoo, têm **saldo líquido zero ou negativo** (já movidos/zerados por operação anterior — provavelmente a relotagem de madrugada ou operação paralela). Forçar a redução criaria saldo negativo.

### Lista

| cod | lote da planilha | situação no Odoo |
|---|---|---|
| 104000007 | `1401/25` ; `INV-104000007-20260518` | líquido 0 (par +340 Produção / −340 Ajuste) ; líquido −38,55 |
| 105000017 | `ALE001,12757` | zerado (sem saldo em lugar nenhum) |
| 105000025 | `3250616080` | líquido 0 (488 Estoque − 524 Ajuste + 35 Pré-Prod) |
| 105000031 | `17025025` | líquido −43,42 |
| 209000152 | `649,649/25` | zerado |
| 209000410 | `5096116,11729` | zerado (componente em Produção, não físico) |
| 210030105 | `80574,81002` | zerado |
| 210030321 | `26121,26216` | zerado |
| 210030328 | `25553,10/10/25` | zerado |

### Caminho recomendado

- Regenerar a planilha desses 9 a partir do **estado atual** do Odoo (saldos por lote/local) e reenviar — processa igual aos demais via `ajuste_estoque_lf_pasta17.py`.
- OU confirmar que esses lotes já foram tratados (relotagem anterior) e descartar as linhas.

### Alternativa: NÃO recomendada

Forçar redução de locais virtuais (`--incluir-virtual`) — testado em dry-run: **não cobre** mesmo assim, pois o saldo líquido é zero/negativo. Consumir só os positivos (ignorando os pares negativos) criaria saldo líquido negativo do lote. Não fazer sem investigar a origem dos pares +/-.

---

## Índice rápido

| ID | Tema | Escopo | Bloqueia |
|---|---|---|---|
| P1 | Padronização completa lotes `MI ###-###/AA` | FB+CD+LF | Fechamento ciclo |
| P2 | Desfazer 9 ajustes emergenciais FB | FB | P1 |
| P3 | Verificar lote `MI036-124/26` 104000002 | FB | E02 |
| P4 | Divergências de quantidade (5 lotes) | FB | D004 onda 1+2 FB |
| P5 | Drift `T20241014` 104000016 pós-E06 | FB | Onda 3 |
| P6 | Picking 317346 invoice CIEL IT | LF | Onda 1 LF |
| P7 | ~~E09 emergencial FB~~ ✅ RESOLVIDO via ajuste de inventário | FB | — |
| P8 | 19 pickings antigos cod 104000003 reservando FB/Estoque | FB | Liberação de estoque cod 104000003 |
| P9 | Ajuste contábil para entrada inventory adjustment E09 | FB | Fechamento financeiro |
| P10 | 9 lotes emergenciais estão em FB/Estoque (loc 8) — não disponíveis para apontamento de produção sem transferência prévia para Linha de Pré-Produção | FB | Uso em produção |
| P11 | 10 produtos sem cadastro Odoo no CD (FALHA `Cat1_SEM_CADASTRO_ODOO`) | CD | Faturamento desses cods + fechamento ciclo CD |
| P12 | 9 produtos LF Pasta17 com lotes dessincronizados (saldo líquido 0/negativo) | LF | Realocação completa Pasta17 (138/147 feitos) |
