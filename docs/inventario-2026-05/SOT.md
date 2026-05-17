# SOT — Inventário 2026-05 NACOM/LF

**Source of Truth macro do trabalho.** Lido por nova sessão Claude Code (ou subagentes) para retomar de onde parou.

**Última atualização:** 2026-05-17
**Status global:** Foundation + F3 + F4 + F5 completas. Services 100% prontos. Próximos: F6-F9 (hooks + scripts + docs + execução).

---

## 1. O QUE É ESTE TRABALHO

Conduzir os ajustes de estoque decorrentes do inventário físico realizado em 16/05/2026 nas empresas:

- **NACOM GOYA** filiais FB (`company_id=1`) e CD (`company_id=4`)
- **LA FAMIGLIA** (`company_id=5`, prestadora de industrialização)
- SC (`company_id=3`) **fora de escopo nesta fase**

Os ajustes saem por NF entre empresas (CFOPs 5901/5903/5949/5152/5151) seguindo o padrão NACOM real: **picking → robô CIEL IT → Playwright SEFAZ** (não `account.move` direto).

**Filosofia:** infraestrutura reutilizável para operações diárias (transferências, devoluções, industrialização) — inventário é o primeiro consumidor, não o caso especial.

---

## 2. DOCUMENTOS-CHAVE (SOT em ordem de leitura)

| Documento | Conteúdo | Lido por |
|-----------|----------|----------|
| Este arquivo (`docs/inventario-2026-05/SOT.md`) | Estado macro, próximos passos | TODOS (humanos, Claude, subagentes) |
| `docs/superpowers/specs/2026-05-17-ajuste-inventario-nacom-lf-design.md` | Spec v3 (pipeline batches) | Antes de qualquer codificação |
| `docs/superpowers/plans/2026-05-17-ajuste-inventario-nacom-lf.md` | Plano detalhado com código por task | Durante implementação (5164 linhas) |
| `app/agente/prompts/prompt_inventario.md` | Prompt inicial do usuário (intenção/regras de negócio) | Para entender o "porquê" |
| `docs/inventario-2026-05/00-decisoes/D000-D003.md` | Decisões formais com fontes | Quando dúvida sobre estrutura |
| `docs/inventario-2026-05/01-premissas/P001-P011.md` | Premissas confirmadas com origem | Quando dúvida sobre regra |
| `docs/inventario-2026-05/02-gotchas/G001-G004.md` | Armadilhas descobertas + solução | Antes de codar área afetada |

---

## 3. ESTADO POR FASE

Leitura: `✅ feito` / `⏳ pendente` / `⚠️ parcial` / `🚫 bloqueado` / `📝 documentado mas não codado`

### Foundation (concluída)

| Fase | Status | Artefato | Tests |
|------|--------|----------|-------|
| **F0** Audit Run | ✅ | 5 scripts em `scripts/inventario_2026_05/00*.py` + D000, D001, D002, D003 + G001, G002, G003, G004 | — (read-only) |
| **F1.1** Constants | ✅ | `app/odoo/constants/operacoes_fiscais.py` + `locations.py` | 17 ✅ |
| **F1.2** Migration `operacao_odoo_auditoria` | ✅ | `scripts/migrations/2026_05_18_operacao_odoo_auditoria.{py,sql}` + `app/odoo/models/operacao_odoo_auditoria.py` | 4 ✅ |
| **F1.3** Migration `ajuste_estoque_inventario` | ✅ | `scripts/migrations/2026_05_18_ajuste_estoque_inventario.{py,sql}` + `app/odoo/models/ajuste_estoque_inventario.py` | 4 ✅ |
| **F1.x** ALTER pipeline | ✅ | `scripts/migrations/2026_05_19_add_fase_pipeline.{py,sql}` (D003) | — (verificação no script) |
| **F1.x** `build.sh` | ✅ | Items 19/20/21 adicionados (commit `6737d907`) | bash -n OK |
| **F2** `stock_lot_service.py` | ✅ | `app/odoo/services/stock_lot_service.py` (criar/renomear/inativar/reativar/atualizar_validade/buscar_por_nome) | 15 ✅ |
| **F3** `stock_picking_service.py` | ✅ | `app/odoo/services/stock_picking_service.py` (criar_transferencia/confirmar_e_reservar/preencher_qty_done/validar/cancelar/liberar_faturamento/aguardar_invoice_do_robo) | 13 ✅ |
| **F4** `inventario_pipeline_service.py` | ✅ | `app/odoo/services/inventario_pipeline_service.py` (f5a_criar_pickings/f5b_validar_pickings/f5c_liberar_faturamento/f5d_aguardar_invoices/f5e_transmitir_sefaz) + helper resolver_location_destino | 25 ✅ |
| **F5** `indisponibilizacao_estoque_service.py` | ✅ | `app/odoo/services/indisponibilizacao_estoque_service.py` (canary_lote/canary_local com try/finally + indisponibilizar_lote/reverter_lote/indisponibilizar_local/reverter_local com canary_passou guard) | 12 ✅ |

### Implementação (pendente)

| Fase | Status | Próximo passo | Bloqueio? |
|------|--------|---------------|-----------|
| **F6** Hooks determinísticos | ⏳ 3 tasks | Task 6.1 (pre_execute_nf.py) | Liberado — F1 (constants) ✅ |
| **F7** Scripts datados (10 scripts) | 📝 7.1 já tem template completo no plano, 7.2-7.10 expandidos | Implementar 7.1 → 7.10 sequencialmente | Liberado — F3+F4+F5 ✅ |
| **F8** Documentação (2 playbooks + estrutura) | ⏳ 4 tasks | Task 8.1 (estrutura pastas — JÁ PARCIAL) | Não |
| **F9** Execução operacional | 🚫 bloqueada | Aguardar F6+F7 | Bloqueio: precisa hooks + scripts |

### Tarefas técnicas pendentes ao final (G003 sugestão de refator)

- [ ] G005: medir tempo robô CIEL IT em paralelo (5 pickings simultâneos) antes de bulk grande — sem isso, F5d (`f5d_aguardar_invoices`) pode levar 25h em vez de 30min
- [ ] G006: validar `action_liberar_faturamento` em outros picking types além de `Expedição Entre Filiais (FB)` (id=51)
- [ ] Mover `_resolver_picking_type` (hardcoded no plano Task 4.1) para `app/odoo/constants/picking_types.py` se virar fonte de gotcha

---

## 4. PRÓXIMA SESSÃO — COMO RETOMAR

### Opção A: Subagent-driven (recomendado para Fases 3 e 4)

Cada task do plano (`docs/superpowers/plans/...`) tem código completo e tests embutidos. Subagente fresco lê plano, executa task isolada, retorna. Vantagens:

- Tasks 3.1 → 3.4 podem rodar **em paralelo limitado** (cuidado: 3.2 depende de 3.1; 3.3 e 3.4 podem rodar em paralelo)
- F5 independente de F3 — pode rodar em paralelo total
- Cada subagente "redescobre" mínimo (lê plano, executa, sai)
- Reduz risco de context window estourar

**Como invocar:** `superpowers:subagent-driven-development` apontando para o plano.

### Opção B: Sessão direta sequencial

Continuar conversação interativa com Claude Code, uma fase por vez. Vantagens:

- Mais simples (zero overhead)
- Decisões intermediárias podem ser tomadas durante (ex: G005 canary do robô)
- Você acompanha em tempo real

**Como invocar:** Nova sessão → "Continue Fase 3 do plano `docs/superpowers/plans/2026-05-17-ajuste-inventario-nacom-lf.md`"

### Opção C: Híbrido (Recomendado por mim)

- **F3 + F5 em sessão direta** (decisões pontuais ainda podem aparecer — ex: confirmar picking_type por direção)
- **F4 (pipeline service)** via subagent-driven já que tem 5 sub-tasks bem definidas
- **F6 + F7 + F8** em sessão direta (operação real próxima)

---

## 5. CHECKLIST PARA NOVA SESSÃO

Ao começar, faça:

1. [ ] `git pull origin main` para garantir sincronia
2. [ ] `git log --oneline -5` para ver últimos commits (incluindo merge da branch foundation)
3. [ ] Leia este arquivo (`docs/inventario-2026-05/SOT.md`) inteiro
4. [ ] Leia o spec (`docs/superpowers/specs/2026-05-17-ajuste-inventario-nacom-lf-design.md`) — focar em §6.2 (arquitetura services) e §8 (pipeline)
5. [ ] Identifique fase a executar e abra plano na seção correspondente
6. [ ] Verifique se há novos GOTCHAS ou ajustes em `02-gotchas/` antes de codar
7. [ ] Rode `pytest tests/odoo/ -v` para confirmar baseline (40 testes devem passar)
8. [ ] Implementar task → testar → commit → próxima task

---

## 6. PROMPT INICIAL (status: ainda válido como referência)

`app/agente/prompts/prompt_inventario.md` (v2 do prompt) continua válido como descrição da **intenção do dono do projeto**. **NÃO é mais SOT operacional** — quem opera deve ler spec/plano/SOT.

O prompt resta útil porque:
- Documenta as **regras de negócio originais** (ordem 1, 2, 3)
- Lista as **NFs de referência** que orientaram o audit (94457, 13075, 147772, 94410)
- Define **filosofia de documentação atômica e regras invioláveis**

O prompt foi **revisado e aprimorado** durante a sessão (v2 inclui ajustes feitos pelo usuário em L1-L8 do brainstorming). Próximas revisões devem ir para o spec (não voltar ao prompt).

---

## 7. RISCOS CONHECIDOS

| Risco | Mitigação |
|-------|-----------|
| Robô CIEL IT serial → F5d toma 25h | Canary G005 antes de bulk grande |
| `action_liberar_faturamento` não existe em todos picking types | Validar via G006 antes de implementar Task 4.3 |
| NF emitida = irreversível após janela SEFAZ | Hooks `pre_execute_nf` bloqueia execução sem aprovação humana |
| `dev-industrializacao FB↔LF` sem precedente histórico | P011 assume fiscal_position por simetria com CD↔LF (74 e 89); validar com canary fiscal antes de bulk |
| `nfe_infnfe_*` stale via XML-RPC → SEFAZ 225 | Playwright UI obrigatório em F5e (já documentado e existe em `playwright_nfe_transmissao.py`) |

### Desvios do plano aplicados em F4 (necessários, não opcionais)

| Desvio | Onde | Motivo |
|--------|------|--------|
| Fixture `app_ctx` → `db` | tests F4 | `app_ctx` não existe em `tests/conftest.py`; `db` fornece `app_context+begin_nested+rollback` |
| `f5b/f5c/f5d/f5e` recebem `List[Ajuste]` (plano: `List[int]`) | service F4 | Plano fazia `AjusteEstoqueInventario.query.filter_by(picking_id_odoo=pid)` — `db.session.commit()` no service vaza dados do savepoint do test para o DB persistente; colisões por `picking_id_odoo` em re-runs |
| F5a refactor: Odoo I/O paralelo + DB write serial no main thread (plano: thread filha commita) | service F4 | `ThreadPoolExecutor` cria threads sem Flask `app_context`; `db.session.commit()` em thread filha falha (`Working outside of application context`); pool de conexão diferente do savepoint |
| `transmitir_nfe_via_playwright(invoice_id, odoo, logger)` retorna `dict` (plano: `transmitir_nfe_playwright(invoice_id)` retorna string) | service F4 / Task 4.5 | Plano alertou: *"investigar antes de implementar 4.5"* — função real tem 3 args e retorna `dict` |
| `PICKING_TYPE_POR_DIRECAO` módulo-level dict (plano: hardcoded em método) | service F4 | Facilita futuro refactor G003 (mover para `constants/picking_types.py`) |

### Bugs encontrados em code-review pós-F4 e corrigidos (3 reviewers paralelos)

| Bug | Severity | Confidence | Status | Onde |
|-----|----------|------------|--------|------|
| **BUG-1**: `location_destino=5` hardcoded — correto apenas para `'perda'`, errado para `TRANSFERIR_*`, `INDUSTRIALIZACAO_*`, `DEV_*` (picking destino errado no Odoo) | HIGH | 95 | ✅ FIX commit `b385dabb` — helper `resolver_location_destino(tipo_op, destino)` + 7 tests novos | service F4 (originou do plano linha 2451) |
| **BUG-2**: `f5e_transmitir_sefaz` sem idempotency guard — re-execução abre Playwright em NF-e já transmitida | HIGH | 95+88 | ✅ FIX commit `5ee53f50` — skip se `fase_pipeline=F5e_SEFAZ_OK` ou `status=EXECUTADO` | service F4 |
| **BUG-3**: Erros de config (`playwright_indisponivel`, env vars ausentes) tratados como falha por-NF — 100 ajustes em batch sem alarme | HIGH | 82 | ✅ FIX commit `5ee53f50` — abort batch via `RuntimeError` quando `tentativas=0 + erro in HARD_FAIL_CONFIG_ERRORS` | service F4 |
| **MED C-2**: `cstat/xmotivo` do `ultimo_estado` (rejeição SEFAZ) não persistido em `erro_msg` | MED | 75 | ✅ FIX commit `5ee53f50` — `erro_msg` agora inclui `cstat=NNN, xmotivo='...'` | service F4 |
| **MED C-1**: `situacao_nf=excecao_autorizado` descartado (relevante audit fiscal) | MED | 76 | ✅ FIX commit `5ee53f50` — registrado em `erro_msg` mesmo em sucesso quando situacao != autorizado | service F4 |
| **MED B-2**: skip silencioso de ajustes sem `picking_id_odoo` em F5b/F5c/F5d (sinal de F5a falho) | MED | 81 | ✅ FIX commit `5ee53f50` — `logger.warning` nos 3 métodos | service F4 |

### Bugs MEDIUM não corrigidos (acceptable risks)

| Bug | Severity | Mitigação |
|-----|----------|-----------|
| **A-MED-1**: `expire_on_commit=True` faz objetos expirarem após commits — refresh implícito em F5b/F5c | MED | Funciona via SELECT implícito; sem regressão observada. Refactor opcional: replicar padrão F5a (pre-index + `db.session.get`) |
| **A-MED-2**: Semaphore compartilhado pode ficar com count reduzido se thread crash sem `__exit__` | MED | `__exit__` no `with self.semaphore:` é garantido em fim normal; crash de thread é raro e affecting apenas instância vigente — re-instanciar service resolve |
| **A-HIGH-3**: Se Odoo cria picking mas `db.session.commit()` falha, próximo F5a re-cria duplicate | HIGH (low likelihood) | Guard `if ajuste.picking_id_odoo: skip` JÁ existe — só protege se commit foi bem-sucedido em pass anterior. Fence token (idempotency_key no Odoo) é melhoria futura |
| **B-MED-1**: Plano F4/F7 ainda mostra `List[int]` no texto | MED | Documentado aqui no SOT como desvio. Plano text não é fonte de verdade — SOT + código são |
| **C-MED-3**: Worst-case duração serial F5e (~45h/100 NFs) não no docstring | LOW | Docstring atualizada em commit `5ee53f50` menciona "Worst case: 100 ajustes × 15 × 120s = ~45h" |

---

## 8. ARTEFATOS PERSISTIDOS

### Em `main` (origin sincronizado)

```
app/odoo/
  constants/
    __init__.py
    locations.py
    operacoes_fiscais.py    # MATRIZ_INTERCOMPANY + helpers
  models/
    __init__.py
    operacao_odoo_auditoria.py
    ajuste_estoque_inventario.py
  services/
    stock_lot_service.py    # F2 (15 tests)
    stock_picking_service.py # F3 (13 tests)
    inventario_pipeline_service.py # F4 (25 tests) — f5a..f5e orquestrador batch (recebe List[Ajuste], DESVIO do plano: plano usava List[int] + lookup por picking_id_odoo, refatorado por bug de pool de conexao em tests). Bugs HIGH post-review (BUG-1 location_destino, BUG-2 idempotency F5e, BUG-3 abort config) e MEDIUMs corrigidos (cstat/xmotivo persistido, situacao_nf audit, WARNING em skip silencioso).
    indisponibilizacao_estoque_service.py # F5 (12 tests) — canary_lote/canary_local com try/finally (SEMPRE reverte) + indisponibilizar_lote/local com canary_passou guard + reverter_lote/local. OPORTUNIDADE refactor: usar StockLotService.inativar/reativar (F2) em vez de odoo.write direto.

scripts/
  migrations/
    2026_05_18_operacao_odoo_auditoria.{py,sql}
    2026_05_18_ajuste_estoque_inventario.{py,sql}
    2026_05_19_add_fase_pipeline.{py,sql}
  inventario_2026_05/
    README.md
    00_audit_odoo_realidade.py
    00b_investigar_gotchas.py
    00c_investigar_g003.py
    00d_investigar_variacoes.py
    00e_investigar_pickings.py
    hooks/                  # placeholder vazio (F6 pendente)

tests/odoo/                 # 90 tests passing
  __init__.py
  constants/__init__.py
  constants/test_operacoes_fiscais.py  # 17 tests
  models/__init__.py
  models/test_operacao_odoo_auditoria.py  # 4 tests
  models/test_ajuste_estoque_inventario.py  # 4 tests
  services/__init__.py
  services/test_stock_lot_service.py  # 15 tests
  services/test_stock_picking_service.py  # 13 tests (F3)
  services/test_inventario_pipeline_service.py  # 25 tests (F4 + post-review fixes)
  services/test_indisponibilizacao_estoque_service.py  # 12 tests (F5)

docs/
  inventario-2026-05/
    SOT.md                  # ESTE ARQUIVO
    README.md
    00-decisoes/
      D000-audit-odoo-realidade.md
      D001-escolhas-pos-audit.md
      D002-matriz-intercompany-final.md
      D003-arquitetura-pipeline-batches.md
    01-premissas/
      P001-P010-placeholder.md  # placeholders — preencher se virarem ativos
      P011-dev-industrializacao-fb-lf-sem-precedente.md
    02-gotchas/
      G001-nfs-referencia-sao-entradas-nao-saidas.md
      G002-picking-type-LF-divergente.md
      G003-cfop-real-divergente-do-prompt.md
      G004-padrao-real-eh-picking-robo-CIEL-IT.md
    03-canary/              # vazio (F4 pendente)
    04-movimentacoes/       # vazio (F5 pendente)
    05-rollback/            # vazio
    06-aprovacoes/          # vazio
    07-relatorios/          # vazio (F1 scripts pendentes)
  superpowers/
    specs/2026-05-17-ajuste-inventario-nacom-lf-design.md
    plans/2026-05-17-ajuste-inventario-nacom-lf.md

build.sh    # items 19/20/21 adicionados

.claude/references/odoo/
  IDS_FIXOS.md              # CORRIGIDO (LF picking_type=19, não 16)
```

### Pendente de criar

```
scripts/inventario_2026_05/
  01_extrair_estoque_odoo.py          # F1 — script de operação
  02_carregar_inventario_xlsx.py
  03_confrontar_inv_vs_odoo.py
  04_propor_ajustes.py
  05_canary_estoque_staging.py
  06_canary_nfs_referencia.py
  07_executar_onda1_lf_fb.py
  08_executar_onda2_cd_fb.py
  09_executar_onda3_indisponibilizacao.py
  10_reconciliar_pos_ajuste.py
  hooks/
    pre_execute_nf.py
    pos_execute_nf.py
    pre_lote_rename.py
    pre_execute_indisponibilizacao.py
    pre_commit_docs.sh

.claude/references/odoo/
  OPERACOES_FISCAIS_NACOM_LF.md       # F8 playbook
  OPERACOES_LOTE_E_INDISPONIBILIZACAO.md  # F8 playbook
```

---

## 9. COMO ATUALIZAR ESTE SOT

Sempre que uma fase mudar de status, atualizar §3 (Estado por fase). Sempre que descobrir novo GOTCHA, atualizar §7 (Riscos). Sempre que criar novo artefato, atualizar §8 (Artefatos).

**Este SOT é a única página que precisa estar sempre atual.** Spec e plano podem ficar desatualizados se decisões mudarem — quando isso acontecer, registrar em `00-decisoes/D00X.md` nova e referenciar aqui.
