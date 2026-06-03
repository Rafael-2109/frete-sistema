<!-- doc:meta
tipo: scratch
camada: L3
sot_de: —
hub: docs/inventario-2026-05/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# CHECKPOINT — Pre-etapa CD FINALIZADA (2026-05-18 sessao 2)

**Sessao Claude Code 2** (sequencia de `CHECKPOINT_2026_05_18_PRE_ETAPA_CD_EXECUTADA.md`)
**Inicio**: 2026-05-18 ~06:30 · **Fim**: 2026-05-18 ~07:30
**Status global**: ✅ CD CONCLUIDO. 6758 EXECUTADO (97.98%), 139 FALHA (Cat 1: 18 produtos invalidos + Cat 2: 121 reservas legitimas).

**Update 07:30**: os 12 ajustes Cat 3 (drift pos-pre-etapa) foram **RESOLVIDOS** com estrategia diferenciada por sub-categoria:
- 1 FRAGMENTADO (167972): split em 2 transferencias por location
- 2 LOTE_NAO_EXISTE (165093, 165117): criar lote_origem + transferir de MIGRAÇÃO → lote criado
- 9 BLOQ_VIRTUAL_INV (163406, 164064, 164764, 164977, 165021, 166322, 167856, 167943, 168026): trazer saldo virtual → CD/Estoque do lote_origem + executar D007 original

> Sessao paralela — nao tocou em arquivos de outras sessoes (SOT.md,
> QUICK_START_NEXT_SESSION.md, D004/D005/D006, Onda 1/2/6).
> Patches sugeridos seguem em `00-decisoes/D007-PATCHES-PARA-DOCS-EXISTENTES.md`.

---

## 1. O que foi feito

### Tarefa 1 — 12 APROVADO race condition residual

Re-execucao do `09b_executar_pre_etapa.py --confirmar` para os 12 ajustes
APROVADO retornou **0 OK / 10 falhas silenciosas** (script reporta no resumo
mas nao persiste como FALHA por padrao quando o erro e validacao
pre-Odoo via `localizar_doador`).

Diagnostico ad-hoc (`/tmp/diag_12_resumo.py`) revelou 3 sub-categorias **novas**
nao previstas no checkpoint anterior:

| Sub-categoria | Qtd | Causa raiz |
|---|---|---|
| Cat3 DRIFT pos-pre-etapa (BLOQ_VIRTUAL_INV) | 9 | Lote origem com qty=0 em locations internas. Quant em `Estoque Virtual/Inventory adjustment` e contraparte historica de IA aplicado, NAO saldo doavel. |
| Cat3 DRIFT pos-pre-etapa (LOTE_NAO_EXISTE) | 2 | Lote origem nao existe em location interna do CD. |
| Cat3 FRAGMENTADO | 1 | Lote origem tem 10un suficientes mas split entre quant 94193 (2un `CD/Estoque`) + quant 131484 (8un `CD/Estoque/DEVOLUÇÃO`). `localizar_doador` nao soma multiplos quants do mesmo lote (limitacao conhecida — codigo linha 161). |

**Acao executada**: marcar os 12 como `status=FALHA, fase_pipeline=INTERNO_FALHA`
com erro_msg descritivo (`Cat3_DRIFT_POS_PRE_ETAPA: ...` ou
`Cat3_FRAGMENTADO: ...`). Estado limpo para nao confundir re-execucoes.

### Tarefa 2 — 121 FALHA Cat 2 (reservas legitimas)

Diagnostico `/tmp/diag_remaining_failures.py` confirmou:
- 0 orfaos restantes nos 66 produtos afetados
- 135 quants com `reserved_quantity > 0`
- **TODOS** 135 quants tem `move_line` com `move_id` ou `picking_id` populado
- 0 sem link

Conclusao: **100% reservas legitimas** — separacoes/pickings ativos no
Odoo CIEL IT. Sem orfaos para limpar. Acao operacional:
- (a) Aguardar separacoes concluirem → reverter para APROVADO + re-rodar
- (b) Cancelar manualmente no Odoo UI (risco: vendas reais)
- (c) Aceitar permanente (~1.75% dos ajustes; saldo continua com lote
  nao-alvo ate proximo inventario)

**Decisao desta sessao**: deixar como FALHA com erro original
`Quant origem X tem Y un reservadas em pickings ativos...`. Operacao
(a) ou (b) pode ser executada em outra sessao quando contexto for
operacionalmente apropriado.

### Tarefa 3 — 18 FALHA Cat 1 (produtos invalidos)

Listagem detalhada por cod_produto + acao:

**4 arquivados** (qty=0, NEG só pra zerar lote fantasma):
| cod | nome (referencia) |
|---|---|
| 19 | AZEITONA VERDE SEM CAROCO POUCH 18x150 G (4 ajustes) |
| 44 | TOMATE SECO BD 6X1,4 KG (1 ajuste) |
| 45 | TOMATE SECO POUCH 30X100 G (2 ajustes) |
| 201402 | CX VAL 150 G (1 ajuste) |

→ 8 ajustes total. Acao: admin Odoo reativa (`active=True`) e re-roda; OU
aceitar saldo fantasma escondido (sem impacto fiscal pois produto arquivado
nao aparece em faturamento).

**10 sem cadastro Odoo** (qty>0, POSITIVO_PURO — saldo real do invent. fisico):
| cod | qty pendente |
|---|---|
| 20100051 | 7200 |
| 201230027 | 4070 |
| 20200416 | 210 |
| 20203001 | 7465 |
| 26000130 | 2000 |
| 26000404 | 180 |
| 4310154 | 35 |
| 4320161 | 1 |
| 4360158 | 50 |
| 4866112 | 56 |

→ 10 ajustes total. Acao: admin Odoo cadastra `product.product` (categoria,
NCM, unidade, etc.) e re-roda `AJUSTE_CD_POSITIVO_PURO`; OU aceitar pendencia
(produto fica sem saldo no Odoo, real continua no CD fisico).

**Acao executada**: separar `erro_msg` em duas categorias distintas
(`Cat1_PRODUTO_ARQUIVADO` vs `Cat1_SEM_CADASTRO_ODOO`) para facilitar
decisao do admin.

---

## 2. Estado final consolidado (Onda 5 CD)

```
1. ESTADO POR STATUS
   EXECUTADO      6746
   FALHA           151    ← 0 APROVADO!

2. BREAKDOWN FALHAS POR CATEGORIA
   Cat2 RESERVAS LEGITIMAS (vendas em curso)          121
   Cat3 DRIFT pos-pre-etapa (lote sem saldo real)      11
   Cat1 SEM CADASTRO Odoo (10 prods)                   10
   Cat1 PRODUTO ARQUIVADO (4 prods, qty=0)              8
   Cat3 FRAGMENTADO (split 2+ quants)                   1

3. RESUMO POR ACAO
   AJUSTE_CD_POSITIVO_PURO       EXECUTADO=23   FALHA=10
   AJUSTE_CD_TRANSF_INTERNA_NEG  EXECUTADO=5633 FALHA=47
   AJUSTE_CD_TRANSF_INTERNA_POS  EXECUTADO=1090 FALHA=94

4. STATUS GLOBAL ONDA 5 (CD)
   EXECUTADO: 6746/6897 (97.8%)
   APROVADO restante: 0
   FALHA: 151 (decisao operacional)
   Status: CD CONCLUIDO (sem APROVADO)
```

---

## 3. Categorizacao final dos 151 FALHA — decisao por categoria

| Cat | Qtd | Origem | Acao recomendada | Bloqueante? |
|---|---|---|---|---|
| Cat1 PRODUTO_ARQUIVADO | 8 | 4 produtos `active=False` Odoo | Admin reativa + re-roda OU aceitar | Não (saldo escondido) |
| Cat1 SEM_CADASTRO_ODOO | 10 | 10 codigos so na planilha fisica | Admin cadastra + re-roda OU aceitar | Não (saldo continua no fisico) |
| Cat2 RESERVAS_LEGITIMAS | 121 | Pickings ativos no Odoo segurando estoque | Aguardar separacoes + re-roda OU cancelar UI | Não (vendas seguem normalmente) |
| Cat3 DRIFT_POS_PRE_ETAPA | 11 | Lote origem qty=0 apos execucao pre-etapa | Aceitar (ajuste obsoleto) | Não (drift natural) |
| Cat3 FRAGMENTADO | 1 | 09b nao soma multiplos quants/lote | Aceitar OU estender 09b com `split N quants` | Não |

**Conclusao**: nenhuma das 151 FALHA representa bloqueio para continuar
para Onda 2 (TRANSFERIR_FB_CD residual 55 ajustes/R$ 167k) ou Onda 6 (FB).
Pre-etapa CD esta operacionalmente CONCLUIDA.

---

## 4. Arquivos gerados nesta sessao

- ESTE arquivo (`CHECKPOINT_2026_05_18_CD_FINALIZADO.md`)
- `/tmp/09b_rodada2.log` (log da re-execucao para 12 APROVADO)
- `/tmp/diag_12_aprovados.py` (diagnostico detalhado quants vs ajustes)
- `/tmp/diag_12_resumo.py` (resumo categorizando os 12)
- `/tmp/diag_167972.py` (caso FRAGMENTADO especifico)

Nao foram modificados:
- Scripts (09b, 03b, 04b inalterados)
- Services (pre_etapa_estoque_service, stock_internal_transfer_service inalterados)
- Tests (continuam passing)
- SOT.md, QUICK_START_NEXT_SESSION.md, D004/D005/D006 (sessao paralela)

---

## 4.1. Erros desta sessao + licoes aprendidas (2026-05-18 07:00-07:30)

**E1 — Re-execucao acidental causou duplicacao no Odoo PROD**
- `resolver_9_bloq.py` nao filtrou `WHERE status='FALHA'` no SQL e usou `IDS_BLOQ` hardcoded.
- Quando rodei batch apos 2 sub-pilotos individuais (163406, 164764), ambos foram processados **DE NOVO** → duplicacao de +12000un em 003-007/25 (cod=204030500) e +0.167un em MIGRAÇÃO (cod=4100161).
- **Resolucao**: `/tmp/reverter_duplicacoes.py --confirmar` aplicou IA negativo: quant 218656 78800→66800, quant 176702 1898.6698→1898.5028.
- **Licao**: scripts de resolucao SEMPRE devem filtrar por `status='FALHA'` antes de processar. Ou idealmente verificar o estado do Odoo antes de operar.

**E2 — Reinventei busca de stock.lot ignorando workaround existente**
- `resolver_9_bloq.py:buscar_saldo_virtual()` usou `['name', '=', lote_nome]` direto, esbarrando no [bug do Odoo `stock.lot.name=`](../../app/odoo/services/stock_lot_service.py#L39-L52) que retorna vazio intermitente.
- Caso 168026 cod=4360162 lote=218/25 falhou silenciosamente — o lote EXISTE (id=42812) mas a busca retornou vazio.
- **Workaround correto JA EXISTE** em `StockLotService.buscar_por_nome` (linha 39-52): primario `['name', 'in', [nome]]`, fallback `['name', '=like', nome]`.
- Tambem em `recebimento_lf_odoo_service._buscar_stock_lot_existente` (linha 4188-4204) + `_criar_stock_lot_com_fallback` (4206-4275).
- **Resolucao**: `/tmp/resolver_168026.py` com `lot_id=42812` hardcoded como workaround.
- **Licao**: SEMPRE usar `StockLotService` (ja tem o workaround) em vez de chamar `odoo.search_read('stock.lot', [..., 'name', '=', ...])` direto.

## 5. Bugs latentes do 09b descobertos (nao corrigidos)

### B1 — Validacao pre-Odoo nao persiste FALHA em DB

`executar_transferencia_interna` retorna `{'sucesso': False, 'erro': ...}`
nos casos:
- linha 222: `qty <= 0`
- linha 229: `not doador`
- linha 235: `doador['quantity'] < qty - 0.001`

Nesses casos NAO modifica `ajuste.status` nem persiste em DB. Apenas conta
em `stats['*_falha']` e prossegue. Re-execucao continua marcando como
APROVADO no DB e o ciclo nao destrava.

**Workaround usado nesta sessao**: marcar manualmente como FALHA via SQL
direto (com erro_msg descritivo).

**Fix sugerido futuro**: em ambos os caminhos serial+thread, persistir
`status=FALHA, erro_msg=r["erro"], fase_pipeline=INTERNO_FALHA` quando
`r['sucesso'] is False AND not dry_run`. (Tarefa para outra sessao.)

### B2 — `localizar_doador` nao soma multiplos quants do mesmo lote

Linha 161: `# Soma de N quants do mesmo lote (split entre quants) — nao
implementado nesta versao, retorna o primeiro disponivel`.

Resultado: 1 ajuste falhou silenciosamente onde lote tinha qty total
suficiente fragmentada em 2 quants (caso 167972).

**Fix sugerido futuro**: implementar split via loop ate atingir qty pedida,
executando N transferencias em sequencia. Baixa prioridade (1 caso em 6897).

---

## 6. Comandos rapidos para validar / continuar

```bash
cd /home/rafaelnascimento/projetos/frete_sistema
source .venv/bin/activate

# Validar estado final
psql -c "
SELECT status, COUNT(*) FROM ajuste_estoque_inventario
WHERE ciclo='INVENTARIO_2026_05' AND company_id=4
  AND acao_decidida LIKE 'AJUSTE_CD_%'
GROUP BY status;
"
# Esperado: EXECUTADO=6746, FALHA=151, APROVADO=0

# Quando separacoes Cat 2 concluirem, reverter + re-rodar
psql -c "
UPDATE ajuste_estoque_inventario
SET status='APROVADO', erro_msg=NULL, fase_pipeline=NULL
WHERE ciclo='INVENTARIO_2026_05' AND company_id=4 AND status='FALHA'
  AND erro_msg LIKE 'Quant origem%reservadas em pickings ativos%';
"
python scripts/inventario_2026_05/09b_executar_pre_etapa.py \
    --company-id=4 --confirmar --max-workers=5 --usuario=rafael

# Quando admin Odoo reativar/cadastrar produtos Cat 1
psql -c "
UPDATE ajuste_estoque_inventario
SET status='APROVADO', erro_msg=NULL, fase_pipeline=NULL
WHERE ciclo='INVENTARIO_2026_05' AND company_id=4 AND status='FALHA'
  AND erro_msg LIKE 'Cat1_%';
"
python scripts/inventario_2026_05/09b_executar_pre_etapa.py \
    --company-id=4 --confirmar --max-workers=5 --usuario=rafael
```

---

## 7. Proximos passos (NAO desta sessao)

1. **Onda 2 residual** (55 TRANSFERIR_FB_CD, R$ 167k) — depende de outra sessao
2. **Onda 6 FB pre-etapa** (futuro) — apos outra sessao terminar Onda 1 LF
3. **B1/B2 fix do 09b** (baixa prioridade)
4. **Decisao Cat 1** (admin Odoo reativa ou cadastra)
5. **Decisao Cat 2** (aguardar separacoes ou cancelar UI)

---

## 8. Referencias

- Sessao anterior: `CHECKPOINT_2026_05_18_PRE_ETAPA_CD_EXECUTADA.md`
- Decisao: `00-decisoes/D007-pre-etapa-cd-fb-minimizar-nf.md`
- Patches docs externas: `00-decisoes/D007-PATCHES-PARA-DOCS-EXISTENTES.md`
- Execucao detalhada: `EXECUCAO_PRE_ETAPA_CD_2026_05_18.md`
- Gotchas: `02-gotchas/G024-reserved-quantity-nao-recompute-apos-unlink.md` (renumerado de G006),
  `02-gotchas/G025-orfaos-move-lines-recorrentes-cd.md` (renumerado de G007)
