---
name: transferindo-interno-odoo
description: >-
  Skill WRITE (átomo C2) para TRANSFERIR saldo de estoque DENTRO de uma mesma
  empresa no Odoo (NÃO emite NF). Suporta 3 modos atômicos: (a) lote→lote na
  MESMA location (`--lote-origem` → `--lote-destino`); (b) location→location
  com o MESMO lote (`--loc-origem` → `--loc-destino`); (c) **MODO C**
  `--para-indisponivel` cross loc+lote consolidando em MIGRAÇÃO POR PRODUTO
  (NOVO 2026-05-24 v4 — codifica invariante destino=Indisp+MIGRAÇÃO; ver G031).
  Internamente delega a `ajustar_quant` 2x (reduz origem, aumenta destino), propagando
  `delta_esperado` para herdar o guard anti-bug CICLAMATO da Skill 1 (regra
  inviolável 11 do roadmap 2026-05-24). Usar quando o pedido é "transfere
  N un do lote A pro lote B", "move o saldo do lote MIGRAÇÃO para o lote
  canônico", "manda esse saldo pra Indisponível", "mesma empresa, sem NF".
  `--dry-run` é o DEFAULT; só efetiva com `--confirmar`.
  NÃO USAR PARA:
  - ajustar saldo de 1 quant (soma/zera/cria) → ajustando-quant-odoo
  - transferir saldo entre CÓDIGOS de produto → transferencia-saldo-codigo
  - transferir entre EMPRESAS diferentes (emite NF) → faturando-odoo/escriturando-odoo
  - cancelar reserva órfã ANTES de transferir → operando-reservas-odoo (skill 2.4)
  - operação que precisa de PICKING (recebimento, devolução) → operando-picking-odoo
  - só consultar/projetar saldo (não altera) → subagente gestor-estoque-producao
allowed-tools: Read, Bash, Glob, Grep
---

# transferindo-interno-odoo (WRITE — átomo C2)

Átomo de **transferência interna de estoque** no Odoo, dentro da mesma empresa.
Internamente é composição de 2 chamadas a `ajustar_quant` (Skill 1):
1. **Reduzir** quant origem (`delta=-qty`, `delta_esperado=-qty`)
2. **Aumentar** (criar se faltar) quant destino (`delta=+qty`, `delta_esperado=+qty`)

Cada passo herda TODOS os guards da Skill 1 (G002, G028, anti-negativar, anti-reserva,
`delta_esperado`). NÃO emite NF (inventory adjustment puro — gera 2 `stock.move`
auditáveis com origem "Physical Inventory").

Constituição: `app/odoo/estoque/CLAUDE.md`. Service: `app/odoo/estoque/scripts/transfer.py`.

---

## REGRAS CRÍTICAS

1. **`--dry-run` é o DEFAULT.** Sem `--confirmar`, simula ambos passos e mostra plano (exit 4). Sempre apresentar plano antes de `--confirmar`.
2. **`--confirmar` efetiva** no Odoo (2 writes + 2 `action_apply_inventory`). Reversível, mas confirme com o usuário antes.
3. **Verificar no Odoo após efetivar** (não confiar só no output) — operação viva.
4. **Empresas DIFERENTES exigem NF.** Esta skill é APENAS intra-empresa. Para inter-company use `faturando-odoo` (saída) + `escriturando-odoo` (entrada).

## Contrato (átomo componível)

```
objeto:        stock.quant (2 ajustes — composição de Skill 1)
input (modo lote→lote):
  --cod <default_code> --empresa <FB|CD|LF> [--local <id>]
  --qty <float positivo>
  --lote-origem <nome|VAZIO> --lote-destino <nome>
  [--resetar-reserva-origem] [--tolerancia-delta T] [--confirmar]
input (modo loc→loc):
  --cod <default_code> --empresa <FB|CD|LF>
  --qty <float positivo>
  --loc-origem <id> --loc-destino <id>
  [--lote <nome|VAZIO>] (mesmo lote nos 2 lados; default = sem lote)
  [--resetar-reserva-origem] [--tolerancia-delta T] [--confirmar]
input (MODO C — para-indisponivel; NOVO 2026-05-24 v4):
  --cod <default_code> --empresa <FB|CD>
  --qty <float positivo>
  --para-indisponivel  (flag)
  --lote <LOTE_REAL>   (obrigatorio — NUNCA proxy vazio em modo C)
  [--loc-origem <id>]  (default = COMPANY_LOCATIONS[empresa])
  [--resetar-reserva-origem] [--tolerancia-delta T] [--confirmar]
  Invariante: destino = (LOCAIS_INDISPONIVEL[cid], lote 'MIGRAÇÃO' RESOLVIDO
  POR PRODUTO via lot_svc — NUNCA usar LOTES_MIGRACAO_POR_COMPANY como FK
  universal — ver Gotcha G031).
output (JSON): {modo, chave{...}, resultado{
  status, qty_transferida, lot_id_origem, lot_id_destino,
  lote_destino_nome?, lote_destino_criado_agora?,
  reducao_origem{...resultado ajustar_quant...},
  aumento_destino{...resultado ajustar_quant...} (modos A/B)
    OU aumento_destino_migracao{...} (modo C),
  tempo_ms, erro?, location_id_origem?, location_id_destino?, lot_id?
}}
pré-condições:
  - produto existe (1 ativo p/ default_code); tracking != serial
  - lote-origem e lote-destino existem (lote-destino é criado se MIGRAÇÃO ou via wrapper v2)
  - origem tem qty livre >= qty solicitada (ou clamp por tolerancia 0.001)
pós-condições:
  - 2 stock.move 'Physical Inventory' (no --confirmar)
  - quant destino criado se faltar
gotchas-invariante (codificados no service transfer.py):
  - G021 (lot_id de empresa errada): TODA busca de lote filtra company_id
  - G022 (2 lotes MIGRACAO/produto): wildcard 3 grafias (MIGRAÇÃO/MIGRACAO/MIGRAÇAO),
    escolhe o de MAIOR saldo na loc alvo, ou cria canônico 'MIGRAÇÃO'
  - G027 (reserved_quantity vem de saída): default RESPEITA reserva;
    --resetar-reserva-origem zera ANTES do ajuste (defensivo, preserva picking)
  - G028 (consolidar_move_lines): herdado de ajustar_quant
  - G002 (lot.name search '=' instável): herdado de StockLotService (operador 'in')
  - G_proxy_vazio: 'P-15/05' = lote literal + também cobre quant sem lote (lot_id=False)
  - delta_esperado: propagado a CADA chamada (regra inviolável 11 pos-CICLAMATO)
  - G-TRANSFER-01 (bugs em fluxo_c, fluxo_b_vivas): criar_se_nao_existe retorna
    tuple (id, bool); a skill NUNCA usa o retorno como int direto.
modos:         --dry-run (default, exit 4) -> --confirmar (exit 0)
status:        EXECUTADO · DRY_RUN_OK · FALHA_REDUCAO · FALHA_AUMENTO ·
               FALHA_PRODUTO · FALHA_LOTE · FALHA_LOCAL · BLOQUEADO_SERIAL ·
               FALHA_ODOO · FALHA_PRE_COND · FALHA_LOTE_DESTINO_INEXISTENTE (modo C dry-run)
```

## Receitas (caso real → args)

| Preciso de... | Args | Vinha do ad-hoc |
|---------------|------|-----------------|
| Transferir N un de lote A para lote B (mesma loc) | `--cod C --empresa E --qty N --lote-origem A --lote-destino B` | 10 emergenciais, 13 transf_migr, substituir_lote, padronizar_migracao |
| Mover lote MIGRAÇÃO para lote canônico | `--cod C --empresa E --qty N --lote-origem MIGRAÇÃO --lote-destino "MI 027-098/26"` | 10, 13 (446 linhas) |
| Mover saldo do estoque para Indisponível (mesmo lote) | `--cod C --empresa FB --qty N --lote MIGRAÇÃO --loc-origem 8 --loc-destino 31088` | mover_migracao_para_indisponivel |
| Consolidar 2 grafias de MIGRAÇÃO (MIGRACAO sem cedilha→MIGRAÇÃO com cedilha) | `--cod C --empresa E --qty N --lote-origem MIGRACAO --lote-destino MIGRAÇÃO` | padronizar_migracao |
| Devolver de Indisponível para Estoque (mesmo lote, locs diferentes) | `--cod C --empresa CD --qty N --lote MIGRAÇÃO --loc-origem 31090 --loc-destino 32` | mover_migracao reverse |
| Reduzir lote A com reserva órfã + transferir (RESETAR reserva primeiro) | `--cod C --empresa E --qty N --lote-origem A --lote-destino B --resetar-reserva-origem` | corrigir_reserved_negativo |
| **MODO C** — Mover saldo para Indisponivel CONSOLIDANDO em MIGRAÇÃO (átomo único) | `--cod C --empresa FB --qty N --para-indisponivel --lote LOTE_REAL` | ad-hoc batch de "transferir produtos pra Indisponivel" (1ª demanda real 2026-05-24 v4) |
| **PLANILHA cod+qty → Indisponivel em LOTE** (orquestrador alto nivel) | `transferir_para_indisp_em_lote.py --planilha file.csv --empresa FB --resetar-reserva-origem` | demanda real 2026-05-25 v10 (158 cods FB) — descobre lotes origem via Skill 9, distribui qty greedy entre quants (MIGRACAO_FIRST_FIFO) |

## Exemplos

```bash
SK=.claude/skills/transferindo-interno-odoo/scripts/transferir.py

# 1) dry-run (default): mover 35 un do lote MIGRAÇÃO para 'MI 027-098/26' em FB/Estoque
python "$SK" --cod 104000015 --empresa FB --qty 35.0 \
    --lote-origem 'MIGRAÇÃO' --lote-destino 'MI 027-098/26'

# 2) efetivar (após revisar o plano)
python "$SK" --cod 104000015 --empresa FB --qty 35.0 \
    --lote-origem 'MIGRAÇÃO' --lote-destino 'MI 027-098/26' --confirmar

# 3) mover saldo do mesmo lote MIGRAÇÃO de FB/Estoque (8) para FB/Indisponivel (31088)
python "$SK" --cod 104000015 --empresa FB --qty 1175.0 \
    --lote 'MIGRAÇÃO' --loc-origem 8 --loc-destino 31088 --confirmar

# 4) padronizar grafia MIGRACAO (sem cedilha) -> MIGRAÇÃO (com cedilha) no mesmo produto
python "$SK" --cod 210030325 --empresa FB --qty 66532.0 \
    --lote-origem 'MIGRACAO' --lote-destino 'MIGRAÇÃO' --confirmar

# 5) caso com reserva órfã na origem: resetar antes do ajuste
python "$SK" --cod 104000037 --empresa FB --qty 5.0 \
    --lote-origem 'MIGRAÇÃO' --lote-destino 'MI 074-177/25' \
    --resetar-reserva-origem --confirmar

# 6) MODO C — transferir saldo de FB/Estoque para FB/Indisp consolidando em MIGRAÇÃO
#    (lote MIGRAÇÃO destino resolvido POR PRODUTO via lot_svc — não é constant)
python "$SK" --cod 210843125 --empresa FB --qty 223.0 \
    --para-indisponivel --lote '26909' --confirmar

# 7) MODO C com loc origem custom (ex.: FB/Pré-Produção/Linha Manual)
python "$SK" --cod 4869012 --empresa FB --qty 50.0 \
    --para-indisponivel --lote '353/25' --loc-origem 4067 --confirmar

# 8) PLANILHA → Indisponivel em LOTE (orquestrador alto-nivel — caso 158 cods FB v10)
SK_LOTE=.claude/skills/transferindo-interno-odoo/scripts/transferir_para_indisp_em_lote.py

# 8a) dry-run da planilha completa, com resetar-reserva (preview JSON em stdout)
python "$SK_LOTE" --planilha /tmp/demanda.csv --empresa FB \
    --resetar-reserva-origem \
    --csv-out /tmp/audit.csv --csv-pendencias /tmp/pendencias.csv

# 8b) inline (debug, 3 cods)
python "$SK_LOTE" --cods "104000015=100,3800005=50,210030007=1000" --empresa FB

# 8c) efetivar (--confirmar) com CSVs de auditoria
python "$SK_LOTE" --planilha /tmp/demanda.csv --empresa FB \
    --resetar-reserva-origem --confirmar \
    --csv-out /tmp/audit_real.csv --csv-pendencias /tmp/pendencias_real.csv
```

## Orquestrador alto-nivel — planilha → Indisponivel em LOTE

`transferir_para_indisp_em_lote.py` eh um CLI thin wrapper sobre o helper
`StockInternalTransferService.distribuir_para_indisponivel` (alto-nivel
composto sobre `transferir_para_indisponivel`). **Capinado em 2026-05-25 v10
para demanda real de 158 cods FB.**

### Input

- `--planilha CSV_PATH` (CSV/TSV com colunas `cod`, `qty`[, `nome`])
  OU `--cods "C1=Q1,C2=Q2"` inline (debug)
- `--empresa FB|CD|LF` required

### Politica

- `--politica MIGRACAO_FIRST_FIFO` (default) — drena MIGRAÇÃO primeiro,
  depois lotes reais em ordem lex de nome
- `--politica FIFO` — so ordem lex de nome
- `--politica MAIOR_SALDO` — drena lotes grandes primeiro

### Origem default (todas internas exceto Indisp por company)

- FB: `[8, 48, 4066, 4067, 4068, 27458]` (Estoque + Pos-Prod + Pre-Prod Vidro/Manual/Balde/Salmoura)
- CD: `[32]` (Estoque)
- LF: `[42]` (Estoque)
- Override via `--locs-origem "id1,id2,..."`

### Algoritmo

Para cada linha (cod, qty) da planilha:
1. Resolve `product_id` via default_code.
2. Lista quants origem (quantity>0, lote nao-vazio, locs permitidas).
3. Ordena por `politica_ordem`.
4. Greedy: drena quants ate atingir `qty_solicitada`. Cada quant chama
   o atomo `transferir_para_indisponivel` 1x.
5. Coleta resultados: `qty_movida`, `qty_nao_movida`, transferencias,
   quants_pulados.

### Output

- JSON estruturado em stdout (`{sumario, cods: [...]}`)
- `--csv-out PATH`: 1 linha por transferencia interna realizada (audit)
- `--csv-pendencias PATH`: 1 linha por cod com parcial/falha

### Exit codes

- `0` confirmado total (todos cods 100%)
- `4` dry-run total
- `1` falha (FALHA_PRODUTO, FALHA_SEM_QUANT, parcial em real, etc)
- `2` erro de uso

### Status por cod

- `DRY_RUN_OK` / `EXECUTADO_TOTAL` — atingiu qty_solicitada
- `DRY_RUN_PARCIAL` / `EXECUTADO_PARCIAL` — moveu parte (saldo insuficiente
  OU lotes pulados — ex.: lote origem == destino MIGRAÇÃO no caso de
  cod ja consolidado em FB/Estoque)
- `FALHA_PRODUTO` — default_code nao existe em product.product
- `FALHA_SEM_QUANT` — sem saldo em nenhuma loc origem
- `FALHA_PRE_COND` — pre-cond do atomo (raro — geralmente vira parcial)
- `FALHA_PARCIAL_NAO_TOLERADO` — `tolerar_parcial=False` configurado

### Gotchas do orquestrador

- **`--resetar-reserva-origem` DEFENSIVO** — quando reserved>0, o atomo
  internamente RESPEITA reserva por default; passando esta flag, usa
  `quantity` completa (ignora reserved). NAO cancela picking — so zera
  reserved_quantity stale. Para reserva legitima (ML viva), considere
  fluxo 2.6 ANTES.
- **Lote MIGRAÇÃO em FB/Estoque (cod ja parcialmente consolidado)** — o
  atomo `transferir_para_indisponivel` levanta `ValueError` se
  `lot_id_origem == lot_id_destino`. O orquestrador CAPTURA este caso
  e pula o quant (registra em `quants_pulados` com motivo), continuando
  o loop. Caso real: cod `4310176` (1 un MIGRAÇÃO em FB/Estoque +
  1093 un em lotes reais; processado parcial com 1093/1094 movidos).
- **Ordem das variantes MIGRACAO/MIGRAÇÃO** — em `MIGRACAO_FIRST_FIFO`,
  a ordem lexicografica entre as variantes eh `MIGRACAO` (sem cedilha,
  'C' < 'Ç') ANTES de `MIGRAÇÃO` (com cedilha). Determinismo OK.
- **`qty_falta` em FALHA_AUMENTO** — em modo real, se uma transferencia
  interna falha (`FALHA_AUMENTO`: origem reduzida mas destino nao
  creditado), o orquestrador NAO decrementa qty_falta — segue tentando
  outros quants. Estado parcial fica documentado em
  `transferencias[].resultado.qty_reduzida_origem`. Rollback manual via
  `ajustar_quant`+qty no quant origem.
- **Tempo de execucao** — em dry-run, ~50s para 158 cods FB (~3 cods/s).
  Em real, estimativa 30-50 min (action_apply_inventory eh ~3-5s cada;
  493 transferencias estimadas). Sem paralelizacao por hora.

### Demanda real 2026-05-25 (158 cods FB)

- 146 OK total (DRY_RUN_OK)
- 9 parciais (8 arredondamento <0.5% + 1 MIGRAÇÃO origem-destino — fix v10 PARCIAL em vez de FALHA)
- 2 FALHA_PRODUTO (cods inexistentes — 45121452, 501)
- 1 FALHA_SEM_QUANT (104000011 HIPOCLORITO sem saldo em FB,CD,LF)
- Cobertura: 99.68% em dry-run (11.009.776 / 11.045.089 un)
- 493 transferencias internas executadas (media 3 transf/cod)

## Armadilhas

- **Modo lote→lote XOR modo loc→loc** — você fornece (`--lote-origem` + `--lote-destino`) OU (`--loc-origem` + `--loc-destino`), nunca os dois.
- **`--qty` é SEMPRE positivo.** A redução de origem usa `delta=-qty` internamente; aumento de destino usa `delta=+qty`. Negativo levanta erro.
- **`--lote-origem == --lote-destino`** (e nada diferente entre eles) levanta `ValueError`. Idem `--loc-origem == --loc-destino`.
- **Lote destino MIGRAÇÃO** é resolvido com WILDCARD das 3 grafias (G022): se há 2 variantes (com/sem cedilha), consolida no de MAIOR saldo na loc; se nenhuma existe, cria a canônica `'MIGRAÇÃO'`.
- **Lote-origem inexistente** → `FALHA_REDUCAO` (reducao_origem.status=FALHA_QUANT_VAZIO). Verificar se o lote existe ANTES (usar `consultando-quant-odoo`).
- **Reserva ativa na origem**: por default a reducao RESPEITA reserva (se `qty_apos < reservada`, `FALHA_REDUCAO`). Para resetar: `--resetar-reserva-origem`. ATENÇÃO: não cancela picking — só limpa cache stale.
- **`--resetar-reserva-origem` em produção** — usar com cautela; se o picking estiver ATIVO (não fantasma), reservar de novo no `action_assign` futuro pode causar surpresa. Para cirurgia de ML órfãs use **skill 2.4 `operando-reservas-odoo`** ANTES desta.
- **tracking=serial** é bloqueado (`BLOQUEADO_SERIAL`).
- **Empresas diferentes** NÃO suportadas — só intra-empresa. Inter-company emite NF (use `faturando-odoo` + `escriturando-odoo`).
- **Quant origem com qty NEGATIVO** + intenção de reduzir mais ainda → `FALHA_QUANT_NEGATIVO` (skill 1 já protege).
- **action_apply_inventory infla quant negativo** (gotcha conhecido). Se destino tem qty<0 (raro), prefira `transferir_entre_lotes_v2` que valida via `ajustar_quant`.
- **G031 — `stock.lot` é POR PRODUTO** (incidente 2026-05-24 v4): `LOTES_MIGRACAO_POR_COMPANY` em `constants/locations.py` é HISTÓRICO/EXEMPLO — NÃO usar como FK universal. `lot_id=30482` é o lote MIGRAÇÃO de UM produto específico; passar isso para `stock.quant.create` de outro produto gera *"O número de lote/série (MIGRAÇÃO) está vinculado a outro produto."*. **CAMINHO CORRETO**: resolver POR PRODUTO via `lot_svc.buscar_por_nome('MIGRAÇÃO', product_id, company_id)` ou `lot_svc.criar_se_nao_existe(...)`. **MODO C codifica** esta invariante.
- **MODO C `--lote ""` (proxy vazio P-15/05)** é REJEITADO — destino MIGRAÇÃO precisa de lote real conhecido.
- **MODO C estado parcial `FALHA_AUMENTO`** em modo real: origem reduzida, destino não creditado. Reportado em `qty_reduzida_origem`. Rollback: chamar Skill 1 `ajustar_quant +qty_reduzida` no lote origem (PROD 2026-05-24 v4 — 16/16 caso rollback testado e bem-sucedido).
- **MODO C dry-run com lote MIGRAÇÃO inexistente para o produto**: retorna `FALHA_LOTE_DESTINO_INEXISTENTE` em vez de criar (evita poluir Odoo). Em `--confirmar` o lote é criado via `criar_se_nao_existe` (`lote_destino_criado_agora=True` reportado).

## Composição em FLUXOS

Este átomo serve a múltiplos fluxos (folhas da árvore em `app/odoo/estoque/fluxos/`):

- **2.2.a lote→lote mesma loc** (10/13/padronizar/consolidar/transferir_lote): atômico direto.
- **2.2.b local→local mesmo lote** (mover_migracao FB/CD, indisp_p15_cd): modo loc→loc.
- **2.2.c lote→MIGRAÇÃO consolidador** (ajuste_fb_cd_indisponivel SAÍDA): modo lote→lote com destino MIGRAÇÃO.
- **2.2.d MIGRAÇÃO→lote real** (RETORNO Indisponível→Estoque): modo lote→lote com origem MIGRAÇÃO.
- **2.2.e net-zero planilha multi-empresa** (transferir_lote): orquestrador externo chama esta skill 1x por linha (ou usa `ajustar_quant` diretamente em loop).
- **2.2.f wildcard De-Local** (transferir_local_pasta22, ajuste_fb_cd_indisponivel): orquestrador externo + esta skill para a transferência atômica em cada quant resolvido.
- **2.2.g multi-grafia consolidação** (padronizar_migracao, consolidar_lote_104000015): modo lote→lote.
- **2.2.h unreserve→transfer→reassign** (substituir_lote_205030410): composição com **skill 2.4** ANTES de chamar esta.
- **2.2.i para-indisponivel (MODO C, NOVO 2026-05-24 v4)** — átomo único que codifica invariante "destino = (LOCAIS_INDISPONIVEL[cid], MIGRAÇÃO POR PRODUTO)". Cobre fluxo "transferir produtos pra Indisponivel consolidando em MIGRAÇÃO" via `transferir_para_indisponivel()`. **Demanda real validada PROD**: 16 produtos × 4.319,4019 un movidas em 23s, todos consolidados em lote MIGRAÇÃO POR PRODUTO (1 lote criado on-demand, 15 já existiam).

## Validação (este átomo é validado por reprodução dos ad-hoc — ROADMAP C6)

Os scripts ad-hoc são o ground-truth:

- `10_executar_emergenciais_fb`, `13_transferencia_migracao_fb`, `padronizar_migracao`, `consolidar_lote_104000015_sal_fb`: EVAL — `--dry-run` reproduz o plano da execução real (log JSON).
- `15_transferencia_para_migracao` (4.888 linhas D010), `15r_transferencia_reversa`: EVAL — orquestradores de planilha que chamam o atomo 1x por linha. A skill cobre o ATOMO; o orquestrador permanece (folha de fluxo).
- `transferir_lote` (D012 net-zero), `transferir_local_pasta22` (D013 wildcard), `ajuste_fb_cd_indisponivel` (D013 + checkpoint): EVAL como orquestradores externos que compõem este átomo.
- `transferir_fluxo_c`, `executar_fluxo_b_vivas`: COM-BUG (G-TRANSFER-01 — usam `criar_se_nao_existe` retornando tuple como int). A skill faz o CERTO; divergência é melhoria, não falha.
- `substituir_lote_205030410_fb`: EVAL — caso `unreserve→transfer→reassign` (passos 1 e 3 → skill 2.4, passo 2 → esta skill).
- `recuperar_aumentos_falhos`: EVAL — re-aumento sem net-zero (não é transfer atômica, mas confirma o gotcha G021 que esta skill codifica).

Validados migram para `scripts/inventario_2026_05/_validados/transferindo-interno-odoo/` no checkpoint C9.
