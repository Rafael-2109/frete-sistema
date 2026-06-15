<!-- doc:meta
tipo: explanation
camada: L3
sot_de: design da limpeza de codigo/arquivos/docs deprecados + agregados (organizacao de docs, automacao anti-drift) — 6 ondas, teto Moderado faseado
hub: docs/superpowers/specs/INDEX.md
superseded_by: —
atualizado: 2026-06-15
-->
# Spec — Limpeza de deprecados/obsoletos + reforço de organização (6 ondas)

> **Papel:** design único (umbrella) da limpeza de código, arquivos, módulos e documentação obsoletos + os agregados de organização/anti-drift. Cada onda vira um plano de execução próprio depois da revisão do Rafael. NENHUM código executado até aprovação da ordem.

## Contexto

Pedido do Rafael: limpeza real de código/arquivos/módulos/docs deprecados + aproveitar o movimento para agregar organização de docs, progressive disclosure, padrão de vinculação/indexação e prevenção de re-acúmulo.

Base factual: duas varreduras read-only com viés adversarial (provar VIVO antes de marcar morto). A segunda corrigiu suposições da primeira E do Rafael — os 3 arquivos de `app/utils/` apontados estão VIVOS; `app/seguranca` está integrado e roda diariamente. Evidência detalhada em `/tmp/subagent-findings/deepdive-*.md` e `/tmp/subagent-findings/recon-*.md` (efêmeros — o que importa está consolidado aqui).

Princípio que rege tudo (correção nº 1 do Rafael): **não tocar em módulo em trabalho ativo**. A seção [3](#3-mapa-de-nao-tocar-congelado) é a trava.

## Indice

- [1. Objetivo e escopo](#1-objetivo-e-escopo)
- [2. Decisões travadas](#2-decisoes-travadas)
- [3. Mapa de NÃO-TOCAR (congelado)](#3-mapa-de-nao-tocar-congelado)
- [4. Política de arquivamento (_deprecated)](#4-politica-de-arquivamento-_deprecated)
- [5. Guards universais (verify-before-move)](#5-guards-universais-verify-before-move)
- [6. Onda A — lixo de risco zero](#6-onda-a--lixo-de-risco-zero)
- [7. Onda B — app/utils mortos](#7-onda-b--apputils-mortos)
- [8. Onda C — docs one-shot da raiz](#8-onda-c--docs-one-shot-da-raiz)
- [9. Onda D — .claude/ housekeeping](#9-onda-d--claude-housekeeping)
- [10. Onda E — agregar: fechar lacunas de organização](#10-onda-e--agregar-fechar-lacunas-de-organizacao)
- [11. Onda F — agregar: automação anti-drift](#11-onda-f--agregar-automacao-anti-drift)
- [12. Itens que exigem investigação antes](#12-itens-que-exigem-investigacao-antes)
- [13. Fora de escopo (gated v28+/v29+)](#13-fora-de-escopo-gated-v28v29)
- [14. Sequenciamento, isolamento e verificação](#14-sequenciamento-isolamento-e-verificacao)
- [15. Riscos e mitigações](#15-riscos-e-mitigacoes)

---

## 1. Objetivo e escopo

Reduzir entulho (código morto, arquivos órfãos, scripts one-off, docs de sessão encerrada) **sem tocar em nada em desenvolvimento ativo**, e usar o movimento para fechar lacunas da infraestrutura de organização que JÁ existe (PAD-A) e reforçar a prevenção de re-acúmulo.

Teto autorizado: **Moderado faseado** — consolidação leve + reorganização de docs; **sem** `DROP TABLE`, migration de schema, ou remoção de legado com gate de versão. Itens gated ficam para os próprios gates (seção 13).

Não-meta: caçar o byte, reescrever módulos, ou "deletar o que não entendo". A régua é evidência de uso, não percepção.

## 2. Decisões travadas

| # | Decisão (Rafael) | Efeito no spec |
|---|---|---|
| D1 | **Teto Moderado faseado** | Sem DROP/migration; gated → seção 13 |
| D2 | Agregar = **organização + anti-drift** (sem CI/GitHub Actions, sem wiki-links `[[ ]]`) | Ondas E e F; CI fica fora (fluxo dev-no-Claude-Code) |
| D3 | Docs raiz = **arquivar one-shots + reorganizar reference-vivos** | Onda C |
| D4 | Lixo rastreado pelo git = **arquivar em `_deprecated/`** (mover, não apagar) | Seção 4 (regra geral) |
| D5 | `app/seguranca` = **manter** (Rafael nunca usou, mas fica fora do escopo p/ não desviar foco) | Não-tocar; anotado como candidato a aposentadoria futura (seção 12) |
| D6 | **Spec completo antes de qualquer código** | Este documento; ordem de execução a decidir |

## 3. Mapa de NÃO-TOCAR (congelado)

Trabalho ativo confirmado (commits ≤5 semanas + gate/canary/plano pendente). **Nenhuma onda toca estes caminhos.**

| Caminho | Evidência |
|---|---|
| `docs/industrializacao-fb-lf/` | R2 WIRE + SA durável ativos (sessão 15/06); 3 commits aguardando push |
| `app/odoo/estoque/` + `app/odoo/services/inventario_pipeline_service.py` | canary REAL v29+ pendente (`app/odoo/estoque/CLAUDE.md:436`); "manter até arquivar v29+" |
| `app/agente/` (incl. `sdk/memory_injection.py`) | PAD-CTX F0–F7 em andamento; guardrails A0/A1/B2 recém-feitos |
| `docs/inventario-2026-05/` + `scripts/inventario_2026_05/` (exceto `_deprecated/` já marcado) | P1–P8 abertas; 254 commits |
| `app/motos_assai/`, `app/hora/`, `app/teams/`, `app/relatorios_fiscais/` | múltiplos services/planos ativos |
| `.claude/skills/` (5.426 commits), `.claude/references/`, `app/templates/` | bulk text-to-SQL, PAD-CTX, telas HORA/Assaí |
| `app/seguranca/` | D5 — manter |

Regra: se um item de qualquer onda cair sob um destes prefixos, **não executar** — registrar e perguntar.

## 4. Política de arquivamento (`_deprecated`)

Decisão D4. Convenção já existente no repo (`docs/_deprecated/`, `.claude/_deprecated/`, `scripts/inventario_2026_05/_deprecated/`; `_deprecated/**` está em `ignore_globs` do lint).

- **Arquivos RASTREADOS pelo git que são lixo** → `git mv` para um `_deprecated/` próximo, **nunca `rm`**. Git preserva o histórico; o `_deprecated/` mantém o cemitério visível.
  - Scripts one-off da raiz/`scripts/` → `scripts/_deprecated/oneoff-2026-06/`
  - Docs one-shot da raiz → `docs/_deprecated/raiz-oneshot-2026-06/`
  - `app/utils/` mortos → `app/utils/_deprecated/`
  - `.claude/` loose docs encerrados → `.claude/_deprecated/`
  - Cada destino ganha/atualiza um `README.md` com a tabela `Arquivo | Motivo (evidência)` (padrão `docs/_deprecated/README.md`).
- **Cruft NÃO rastreado (ignorado pelo `.gitignore`)** → `rm` local direto (não é "arquivo do projeto"): `__pycache__/`, `*.pyc`, `flask_session/`, `.pytest_cache/`, `.ruff_cache/`.
- **Reference-vivo mal-localizado** → `git mv` para `docs/<tema>/` (não `_deprecated/`) + `doc:meta` + registro no índice.

## 5. Guards universais (verify-before-move)

Aplicar a TODO item, antes de mover:

1. **Re-grep de uso** na hora (não confiar só no recon): `grep -rn "<basename sem .py>" app/ scripts/ tests/ .claude/ --include=*.py` + checar `url_for`, `href/fetch`, registro de blueprint, cron/worker, `importlib/getattr`.
2. **Não-tocar**: confirmar que o path não cai sob a seção 3.
3. **Pós-move (.py)**: `python -c "import app"` (smoke) + `pytest` das suites relacionadas.
4. **Pós-move (.md)**: `python scripts/audits/doc_audit.py --enforce-touched` verde.
5. **Rodar da raiz do repo** (gotcha cwd: `cd` p/ subdir quebra hooks PAD e bloqueia Write `.md`).
6. **Worktree** (gotcha): se em worktree, passar `DATABASE_URL` da raiz para o pytest e exigir `git branch --show-current` em prompt de subagente.
7. Commits **sem `[skip render]`**.

## 6. Onda A — lixo de risco zero

Não toca módulo ativo. Cruft regenerável = `rm`; resto = arquivar.

| Item | Path(s) | Evidência | Disposição |
|---|---|---|---|
| Caches Python | `**/__pycache__/`, `**/*.pyc` (~2.012 + ~1.691) | ignorados (`.gitignore:2-3`) | `rm` local |
| Sessões dev | `flask_session/` (4, incl. dentro de `.claude/skills/`) | ignorado (`.gitignore:60,112`) | `rm` local |
| Scripts one-off raiz | `agendar_pedido_932955.py`, `recompor_separacoes_perdidas.py`, `executar_analise_indices.py`, `executar_limpeza_historico.py`, `consultar_odoo_direto.py`, `investigar_pesos_nf.py`, `configurar_sessao_atacadao.py`, `atualizar_geracao_lote.py` | 0 callers; ausentes de `render.yaml`/`Procfile`/cron | arquivar |
| Debug ad-hoc | `scripts_debug/` (7 arquivos) | "Simula o que acontece em routes.py"; 0 callers | arquivar |
| POC | `scripts/poc_sdk_client.py` | "POC: ClaudeSDKClient vs query()"; 0 callers | arquivar |
| Scripts one-off tagplus | `app/integracoes/tagplus/{excluir_nfs_teste,listar_nfs_com_datas,listar_nfs_disponiveis}.py` | 0 imports; rodam via `__main__` | arquivar |
| PDF duplicado | `The-Complete-Guide-to-Building-Skill-for-Claude (2).pdf` (+ `:Zone.Identifier`) | duplicata Windows | arquivar |
| Snapshots backup | `tests/visual/snapshots/baseline_backup_*` (5 dirs, ~100MB, >1 mês) | manter só `baseline/` canônico | arquivar |
| Fix path quebrado | `.claude/references/INDEX.md:26` → aponta `./negocio/REGRAS_NEGOCIO.md`, arquivo na raiz | severidade alta, trivial | corrigir |

**🛡️ Preservar (verificado VIVO — NÃO mexer):** `importar_historico_odoo.py` (importado por `app/manufatura/routes/historico_routes.py`), `CARD_SEPARACAO.md` e `REGRAS_NEGOCIO.md` (citados em `~/.claude/CLAUDE.md`).
**Antes de arquivar:** `run_bi_etl.py`, `executar_reconciliacao.py` → seção 12.

## 7. Onda B — app/utils mortos

Módulo `app/utils/` NÃO está na lista de não-tocar (baixa atividade). Correção registrada: os 3 que o Rafael citou estão **vivos**.

| Arquivo | Status | Evidência | Disposição |
|---|---|---|---|
| `database_helpers.py` | **VIVO** | 15 callers (workers CarVia, `carteira_service`, backfills) | manter |
| `database_retry.py` | **VIVO** | 7 callers; coexiste com `_commit_helpers` (backoff vs `engine.dispose`) | manter |
| `csrf_helper.py` | **VIVO parcial** | só `validate_api_csrf` usado (`portaria/routes.py:186`); 5 funções órfãs | **enxugar** (remover 5 órfãs) |
| `route_sync_manual.py` | morto | blueprint `monitoramento` duplicado; real em `app/monitoramento/routes.py` | arquivar |
| `frete_simulador_backup.py` | morto | "BACKUP… 2025-01-19"; código incompleto; 0 callers | arquivar |
| `helpers.py` | morto | `limpar_valor` redefinida inline em `tabelas/routes.py:232`; 0 import | arquivar |
| `utils_frete.py` | morto | `float_or_none removido` (`tabelas/routes.py:14`); 0 import | arquivar |
| `ai_logging.py` | morto | MCP v4.0 nunca integrado, 18KB, 0 callers | arquivar |
| `ml_models.py` | morto | MCP v4.0 simulado; listado como falso-positivo ORM nos próprios testes | arquivar |
| `ml_models_real.py` | morto | ML real implementado, 0 callers | arquivar |
| `agendador.py` | morto | substituído por `iniciar_scheduler_incremental.py`; 0 caller de `iniciar_agendador` | arquivar |
| `app/database/` | vazio | `__init__.py` 0 linhas | arquivar ou documentar intenção |

**Nota `csrf_helper`:** enxugar = remover `validate_csrf_safe`, `ensure_csrf_token`, `is_csrf_error_recoverable`, `log_csrf_error`, `regenerate_csrf_token` (0 callers), manter `validate_api_csrf`. Guard: `pytest` de `portaria`.

## 8. Onda C — docs one-shot da raiz

59 dos 63 `.md` da raiz são zero-hit (não citados em índice/CLAUDE.md). **Correção do Rafael (2026-06-15): zero-hit ≠ inútil** — pode ser falha de citação de um doc que ainda é verdade. Arquivar um órfão verdadeiro = perder conhecimento. Logo a disposição NÃO sai do grep; sai do **protocolo de 4 perguntas**, aplicado a cada doc cruzando contra o **código atual**:

1. **O que o arquivo diz?** (resumo factual)
2. **Isso foi substituído ou complementado por algo?** (código `arquivo:linha` ou doc canônico — com evidência)
3. **Isso continua sendo verdade?** (SIM / PARCIAL / NÃO — verificado contra o código real: a tabela/rota/função citada existe? o comportamento bate?)
4. **Como deveria estar e onde deveria estar?**

Mapa resposta → disposição:

| Q3 (ainda verdade?) | Situação | Disposição |
|---|---|---|
| **NÃO** / superseded total | conhecimento morto | **ARQUIVAR** em `docs/_deprecated/raiz-oneshot-2026-06/` com `superseded_by` |
| **SIM, mas órfão** | falha de citação (doc bom, ninguém linkou) | **REORGANIZAR** → `docs/<tema>/` + `doc:meta` + registrar no índice (conserta a citação, **preserva** o conhecimento) |
| **PARCIAL** | parte verdade, parte obsoleta | **ATUALIZAR** (reconciliar com a verdade atual) → então posicionar + indexar |
| **SIM, já bem-posicionado** | só falta link | **MANTER** + corrigir citação/índice |

Saída: tabela verificada doc-a-doc (Q1–Q4 + evidência), **revisada pelo Rafael antes de mover qualquer arquivo**. Os 18 `TODO/PENDENTE/WIP` entram no mesmo protocolo (Q3 decide concluir/arquivar/atualizar).

- **🛡️ Preservar:** `CARD_SEPARACAO.md`, `REGRAS_NEGOCIO.md` (citados em CLAUDE.md), `README.md`, `CLAUDE.md`.
- **Investigar à parte:** trio `app/integracoes/tagplus/FLUXO_{IMPORTACAO,CORRIGIDO,REAL}.md` (manter só o canônico `FLUXO_REAL`) → seção 12.

## 9. Onda D — .claude/ housekeeping

| Arquivo | Status | Disposição |
|---|---|---|
| `AUDITORIA_SKILLS_ONDA_D_DRIFT_MAP.md` | autodeclarado HISTÓRICO; Onda D mergeada (`473b7c9be`) | arquivar |
| `AUDITORIA_SKILLS_ONDA_D_PROJETO_CONSOLIDACAO.md` | idem | arquivar |
| `AUDITORIA_SKILLS_PROMPT_PROXIMA_SESSAO.md` | descreve estado **falso** (4 branches "não mergeadas" — todas mergeadas) | arquivar |
| `AUDITORIA_SKILLS_PLANO_EXECUCAO.md` | SOT vivo, mas header **stale** (diz D/E/F não mergeadas) | **atualizar** (corrigir header; marcar Onda G + transferencia-saldo-codigo como próximos) |
| `AUDITORIA_SKILLS_2026-05-29.md` | relatório original, citado pelo PLANO_EXECUCAO | manter (arquivar junto quando Onda G fechar) |
| `DOC-1.md`, `DOC-2.md` | citados em `~/.claude/CLAUDE.md:71-72` + STUDY/ROADMAP | manter |
| `TODO.md` | 55 itens de backlog abertos | manter |
| `aplicacao_aristotelica.md`, `teoria_aristotelica_x_ia.md` | citados por `FRAMEWORK_ARISTOTELICO.md` | manter |
| `.claire/` | diretório vazio (só `worktrees/`) | remover se confirmado sem uso por ferramenta → seção 12 |
| `relatorios/arquitetura_x_2026-06-11/`, `relatorios/estudo_contexto_boot_2026-06-09/` | citados por planos VIVOS (`docs/superpowers/plans/`) | **manter** (anexo imutável; mover quebraria links) |
| `memory/memory_evolution.md` | citado em `.claude/references/INDEX.md:56` | manter (opcional: linha de status KG-off) |

## 10. Onda E — agregar: fechar lacunas de organização

Aditivo (cria/estende; não deleta). A infra PAD-A existe — isto fecha lacunas.

1. **Criar** `.claude/references/PROGRESSIVE_DISCLOSURE_PATTERN.md` (`tipo: reference`, L2): SOT dos 3 padrões observados (root+subdir `CLAUDE.md`; árvore de fluxos L3; memória narrativa JSONB) + critério de "quando usar qual". Fonte de verdade para quem edita `CLAUDE.md` de módulo/índice.
2. **Estender** `.claude/references/INDEX.md`: seção "Module → CLAUDE.md" (16 módulos, 1 linha cada) + seção **"Módulos silenciosos mas críticos"** (`embeddings/`, `permissions/`, `resolvedores/`, `supply_chain/` — invocados dinamicamente; `supply_chain` em toda request — *jamais remover*).
3. Corrigir bidirecionalidade dos 3 hubs (`CLAUDE.md ↔ INDEX.md ↔ docs/INDEX.md`).

> Cuidado: edita `.claude/references/` (zona ativa). São edições **aditivas** e devem ser coordenadas com a janela do PAD-CTX (evitar colisão de hunk).

## 11. Onda F — agregar: automação anti-drift

1. **Stop hook (anel 3)**: `scripts/audits/stop_hook.py` advisory — ao fim da sessão reporta órfãos (`hub` quebrado), circularidade `sot_de`, near-dup, link-rot. Wire em `.claude/settings.json` (Stop) ou pre-commit.
2. **Check novo no `doc_audit`**: bidirecionalidade skill→references (`ROUTING_SKILLS.md ↔ INDEX.md ↔ arquivos reais`) — `--check-skills-inventory`.
3. **SOP de baseline** (`.claude/AUDIT_POLICY.md`): quando/quem/como atualizar `ui_audit_baseline.json` (stale de 2026-05-06) e `prompt_size_baseline.json` após limpeza intencional. Necessário porque a própria limpeza mexe nos baselines.

## 12. Itens que exigem investigação antes

Decisão/dado pendente antes de agir (não bloqueiam as outras ondas):

| Item | Pergunta | Como resolver |
|---|---|---|
| `run_bi_etl.py`, `executar_reconciliacao.py` | rodam via cron externo? | checar crontab/OpenClaw cron + `render.yaml` |
| `importar_historico_odoo.py` | `data_fim=2025-06-30` expirou o propósito? | confirmar com Rafael; route ativa importa, mas pode estar morta de fato |
| `DIAGRAMA_FLUXO_AGRUPADOS.md` | referência viva p/ dev? | inspeção de conteúdo |
| trio `tagplus/FLUXO_*.md` | qual é canônico? | `FLUXO_REAL` declara-se a versão precisa → arquivar os outros 2 |
| `.claire/` | alguma ferramenta usa? | confirmar; se não, remover |
| `app/seguranca` (D5) | produz valor em PROD? | `SELECT COUNT(*), MAX(criado_em) FROM seguranca_varreduras WHERE status='CONCLUIDA'` via MCP Render — insumo p/ aposentadoria futura |

## 13. Fora de escopo (gated v28+/v29+)

Respeitando D1 — **não tocar até o gate**:

- `app/odoo/services/inventario_pipeline_service.py` (1346 LOC, LEGADO MINERADO; arquivar v29+ pós-canary REAL)
- `FreteLancado` / `fretes_lancados` + rota `/antigo/<id>` (exige migration de cleanup)
- 4 SHIMs `app/odoo/services/stock_*_service.py` (consolidar callers — toca `app/odoo/estoque/`, zona ativa)
- ramo Selenium em `app/portal/session_manager.py` (transição p/ Playwright incompleta)
- `buscar_ou_criar_modelo()` em `app/hora/` (módulo ativo)

## 14. Sequenciamento, isolamento e verificação

- **Ordem sugerida:** A → B → C → D → E → F (E/F dependem de C/D limpas, senão a automação anti-drift reporta órfãos legados). Ordem final = decisão do Rafael.
- **Isolamento:** tarefa nova → `git worktree add -b chore/limpeza-deprecados <base>` (base a confirmar: `origin/main` padrão vs `main` local que inclui os 3 commits FB-LF não-pushados). Cada onda = 1+ commits na branch; PR/merge ao fim de cada onda ou do conjunto.
- **Verificação por onda:** A/B → `import app` + `pytest`; C/D → `doc_audit --strict`; E → `doc_audit --strict` + creation gate aprova doc novo; F → rodar stop hook + novo check em modo report.
- **Self-audit pós-onda:** comparar itens planejados vs movidos; confirmar guards rodados; nada da seção 3 tocado.

## 15. Riscos e mitigações

| Risco | Mitigação |
|---|---|
| Mover algo que parecia morto mas está vivo | guard nº 1 (re-grep na hora) + viés adversarial já aplicado nas 2 recons |
| Colisão com trabalho ativo | seção 3 (não-tocar) + base de worktree atualizada |
| Quebrar link de doc vivo ao mover | `relatorios/` studies e `memory_evolution` ficam no lugar; reorg só com atualização do índice no mesmo commit |
| Baseline regredir após limpeza | SOP da Onda F + `--update-baseline` documentado |
| Entrelaçar com push pendente do Rafael (FB-LF) | worktree isolado; decidir base (origin/main vs main local) antes de começar |

---

## Apêndice A — Inventário verificado da Onda C (protocolo 4 perguntas, 2026-06-15)

59 docs da raiz verificados contra o código. **Q3 = ainda é verdade?** (SIM/PARCIAL/NAO). Disposição derivada do protocolo da §8. Evidência Q1–Q4 completa nos findings da sessão. Revisar antes de mover.

### ARQUIVAR (22)

| Arquivo | Q3 | Destino / ação |
|---|---|---|
| CHANGELOG_INDUSTRIALIZACAO_E_STANDBY.md | SIM | docs/_deprecated/CHANGELOG_INDUSTRIALIZACAO_E_STANDBY.md — changelog histórico one-shot; as mudanças foram aplicadas e expandidas. Informação histórica sem v... |
| CHECKLIST_PORTAL.md | PARCIAL | docs/_deprecated/CHECKLIST_PORTAL.md — era guia operacional de testes de deploy inicial; a feature está rodando em produção, checklist temporário cumpriu fun... |
| CHROME_WINDOWS_INSTRUCOES.md | PARCIAL | docs/_deprecated/raiz-oneshot-2026-06/ — guia one-shot para setup de ambiente já executado. Scripts auxiliares não existem mais. O campo protocolo já foi mig... |
| COMO_RODAR_RUPTURA_WORKERS.md | NAO | docs/_deprecated/COMO_RODAR_RUPTURA_WORKERS.md — superseded_by: app/carteira/CLAUDE.md (R7) descreve as 2 variantes ativas de ruptura. Não precisa de doc:met... |
| CONCLUSAO_IMPLEMENTACAO_MOTOCHEFE.md | PARCIAL | docs/_deprecated/motochefe/CONCLUSAO_IMPLEMENTACAO_MOTOCHEFE.md — superseded_by: app/motochefe/documentacao/FLUXO_PARCELAMENTO_FIFO.md e app/motochefe/docume... |
| DIAGRAMA_FLUXO_AGRUPADOS.md | PARCIAL | docs/_deprecated/DIAGRAMA_FLUXO_AGRUPADOS.md — análise de refatoração one-shot parcialmente executada; o que resta como dívida técnica deveria ir para docs/f... |
| DOCUMENTACAO_CTE_IMPLEMENTACAO.md | PARCIAL | docs/_deprecated/DOCUMENTACAO_CTE_IMPLEMENTACAO.md (superseded_by: docs/fretes/cte-complementar.md e o código real em app/fretes/models.py + app/odoo/service... |
| INSTRUCOES_ATUALIZAR_FRETE.md | PARCIAL | docs/_deprecated/INSTRUCOES_ATUALIZAR_FRETE.md (instrução operacional one-time de bug já corrigido; script referenciado não existe mais) |
| INSTRUCOES_DEPLOY_FINAL.md | PARCIAL | docs/_deprecated/INSTRUCOES_DEPLOY_FINAL.md (superseded_by: app/motochefe/documentacao/FLUXO_PARCELAMENTO_FIFO.md). Era one-shot deploy guide; CrossDocking e... |
| INSTRUCOES_FRONTEND_FORM.md | NAO | docs/_deprecated/INSTRUCOES_FRONTEND_FORM.md — instrução de refatoração one-shot já executada; o resultado é o form.html atual. |
| INVESTIGACAO_STATUS_INCONSISTENTE.md | PARCIAL | docs/_deprecated/investigacao-status-inconsistente-2025-01.md — é um documento de investigação pontual sobre um pedido específico (VCD2563375) sem implementa... |
| MELHORIAS_CTES_NFS_DASHBOARD.md | SIM | docs/_deprecated/MELHORIAS_CTES_NFS_DASHBOARD.md (registro histórico de sprint; conteúdo vivo está no código e em eventual doc canonico de CTe) |
| MUDANCAS_FOB_MONITORAMENTO.md | SIM | docs/_deprecated/MUDANCAS_FOB_MONITORAMENTO.md (changelog de mudança one-time já incorporada ao código; comportamento documentado está em sincronizar_entrega... |
| PLANO_IMPLEMENTACAO_MOTOCHEFE.md | PARCIAL | docs/_deprecated/motochefe/PLANO_IMPLEMENTACAO_MOTOCHEFE.md — superseded_by: app/motochefe/documentacao/ (IMPLEMENTACAO_CONCLUIDA.md, FLUXO_PARCELAMENTO_FIFO... |
| RASTREAMENTO_PRODUCAO.md | PARCIAL | docs/_deprecated/raiz-oneshot-2026-06/ — doc é snapshot de debugging de um problema pontual de 2025. O bug foi substancialmente resolvido; o doc não tem valo... |
| README_INSTALACAO_ENTREGAS_RASTREADAS.md | PARCIAL | docs/_deprecated/raiz-oneshot-2026-06/ — guia de instalação one-shot cuja tarefa foi concluída (tabela criada via migration). Scripts auxiliares não existem ... |
| README_RUPTURA_ASYNC.md | NAO | docs/_deprecated/README_RUPTURA_ASYNC.md — superseded_by: app/carteira/CLAUDE.md (R7) com as 2 variantes ativas. Não precisa de doc:meta nem índice. |
| RELATORIO_CORRECAO_TIMEZONE.md | PARCIAL | docs/_deprecated/RELATORIO_CORRECAO_TIMEZONE.md — é um relatório de incidente/debugging pontual; a correção foi completamente aplicada em todos os services. ... |
| SISTEMA_ESTOQUE_TEMPO_REAL.md | NAO | docs/_deprecated/SISTEMA_ESTOQUE_TEMPO_REAL.md — superseded_by: app/estoque/api_tempo_real.py (versão migrada) e app/estoque/services/estoque_simples.py. Não... |
| STATUS_FINAL_IMPLEMENTACAO.md | PARCIAL | docs/_deprecated/motochefe/STATUS_FINAL_IMPLEMENTACAO.md — superseded_by: CONCLUSAO_IMPLEMENTACAO_MOTOCHEFE.md (que também deve ser arquivado) |
| TAGPLUS_INTEGRACAO.md | PARCIAL | docs/_deprecated/TAGPLUS_INTEGRACAO.md (superseded_by: app/integracoes/tagplus/DOCUMENTACAO_API_TAGPLUS.md, FLUXO_IMPORTACAO_TAGPLUS.md e demais docs dentro ... |
| V2_QUERY_CLEANUP.md | PARCIAL | docs/_deprecated/V2_QUERY_CLEANUP.md — o próprio doc instrui a deletá-lo quando critérios forem atendidos; manter como referência histórica até limpeza compl... |

### ATUALIZAR (17)

| Arquivo | Q3 | Destino / ação |
|---|---|---|
| CAPACITOR_README.md | PARCIAL | docs/rastreamento/capacitor-readme.md — corrigir nome do APK no Quick Start, adicionar menção a build-dev.sh/build-prod.sh, adicionar doc:meta e registrar em... |
| DIAGNOSTICO_SCHEDULER_ODOO.md | PARCIAL | docs/odoo/scheduler_sincronizacao.md — atualizar JANELA_CARTEIRA para 70 min, STATUS_FATURAMENTO para 2880 (48h), remover snippet Python no final do arquivo,... |
| DOCUMENTACAO_CARGA_INICIAL_MOTOCHEFE.md | PARCIAL | docs/motochefe/carga-inicial.md — adicionar doc:meta, registrar no índice de docs motochefe, mencionar Fase 4 como implementada |
| DOCUMENTACAO_CTE_COMPLEMENTAR.md | PARCIAL | docs/fretes/cte-complementar.md + doc:meta + registro no índice de fretes |
| INSTALACAO_RASTREAMENTO_GPS.md | PARCIAL | docs/rastreamento/instalacao-rastreamento-gps.md — atualizar checklist (itens concluídos), expandir tabela de rotas e modelos para refletir estado real, adic... |
| MAPA_CALCULOS_FRETE.md | PARCIAL | docs/fretes/mapa-calculos-frete.md + doc:meta + registro no índice de fretes |
| MAPA_FLUXOS_COTACAO.md | PARCIAL | docs/cotacao/mapa-fluxos-cotacao.md + doc:meta + registro no índice de cotação |
| MAPEAMENTO_FUNCOES_CARDS.md | PARCIAL | docs/carteira/arquitetura-cards-separacao.md — corrigir numerações de linha, adicionar doc:meta e registrar no índice docs/ |
| MAPEAMENTO_METODOS_JS.md | PARCIAL | docs/carteira/metodos-js-carteira.md — adicionar métodos novos (abrirModalDatas, editarDatas), remover renderizarProdutosDoLote e renderizarDetalhes da lista... |
| MAPEAMENTO_PRESEPARACAOITEM.md | PARCIAL | docs/carteira/migracao-preseparacaoitem.md — atualizar para refletir estado atual (adapter ativo, Fase 3 pendente); adicionar doc:meta e link no índice de do... |
| MELHORIAS_IMPORTACAO_EXCEL.md | PARCIAL | docs/carteira/melhorias-importacao-excel.md — document tracking de melhorias; deve ser atualizado para refletir o que foi implementado vs o que ainda está pe... |
| OTIMIZACOES_NECESSIDADE_PRODUCAO.md | PARCIAL | docs/manufatura/OTIMIZACOES_NECESSIDADE_PRODUCAO.md — adicionar doc:meta, registrar em docs/INDEX.md ou índice de manufatura. Reconciliar TTL inconsistente (... |
| PLANO_OTIMIZACAO_COMERCIAL.md | PARCIAL | docs/comercial/PLANO_OTIMIZACAO_COMERCIAL.md — marcar Fase 1 como concluída com evidências de código, verificar se índices SQL foram criados em produção, adi... |
| PROBLEMA_DATAS_IDENTIFICADO.md | PARCIAL | docs/carteira/bug-date-type-estoque-simples.md — atualizar para refletir que calcular_multiplos_produtos_batch tem o guard mas calcular_entradas_previstas ai... |
| RASTREAMENTO_APP_GUIA_COMPLETO.md | PARCIAL | docs/rastreamento/guia-build-app-android.md — atualizar checklist (marcar build concluído), adicionar doc:meta e registrar em docs/INDEX.md |
| README_CARGA_INICIAL_MOTOCHEFE.md | PARCIAL | docs/motochefe/carga-inicial-readme.md — ou consolidar com DOCUMENTACAO_CARGA_INICIAL_MOTOCHEFE.md em doc único; registrar no índice motochefe; adicionar doc... |
| SOLUCAO_TRUNCAMENTO_OBSERVACOES.md | PARCIAL | docs/carteira/SOLUCAO_TRUNCAMENTO_OBSERVACOES.md — remover referência ao `faturamentos_parciais_api.py` (arquivo removido), adicionar separacao_api.py:856 co... |

### REORGANIZAR (20)

| Arquivo | Q3 | Destino / ação |
|---|---|---|
| BOTAO_CONFIRMACAO_AGENDAMENTO.md | SIM | docs/embarques/botao-confirmacao-agendamento.md — documentação funcional completa e válida; mover para docs/embarques/ com doc:meta e registrar no índice |
| CAPACITOR_SETUP.md | SIM | docs/rastreamento/capacitor-setup.md — mover para docs/rastreamento/, adicionar doc:meta, registrar em docs/INDEX.md como referência técnica do módulo de ras... |
| CIRCUIT_BREAKER_ODOO.md | SIM | docs/odoo/circuit_breaker.md — deve sair da raiz para docs/odoo/. Precisa de doc:meta e registro no índice do hub de docs. |
| CONFIGURAR_QRCODE.md | SIM | docs/rastreamento/configurar-qrcode.md — mover para docs/rastreamento/ com doc:meta, registrar em docs/INDEX.md como guia operacional |
| DIFERENCA_BOTOES_VERIFICACAO.md | SIM | docs/carteira/botoes-verificacao-agendamento.md — é documentação operacional válida sobre UX; mover para docs/carteira/ com doc:meta |
| ETAPA5_PERMISSOES_COMERCIAL.md | SIM | docs/comercial/permissoes-comerciais.md — doc técnico de feature que deveria estar em docs/<módulo>/ e não na raiz. Precisa de header doc:meta e registro no ... |
| EXEMPLO_DADOS_CARGA_MOTOCHEFE.md | SIM | docs/motochefe/exemplos-carga-inicial.md — junto com DOCUMENTACAO_CARGA_INICIAL_MOTOCHEFE.md no mesmo tema, com doc:meta e link no índice |
| EXEMPLO_USO_EXTRATOR_CNPJ.md | SIM | docs/motochefe/extrator_cnpj.md — doc de referência de API interna; sair da raiz para docs/motochefe/. Precisa de doc:meta e registro no índice. |
| EXPLICACAO_RELACAO_REQUISICAO_PEDIDO.md | SIM | docs/odoo/relacao_requisicao_pedido.md — doc de conceito arquitetural; sair da raiz para docs/odoo/ (ou docs/manufatura/). Atualizar referência de linha (581... |
| MELHORIAS_REQUISICOES_COMPRAS.md | SIM | docs/manufatura/melhorias_requisicoes_compras.md — doc de feature/changelog; sair da raiz para docs/manufatura/. Precisa de doc:meta e registro no índice. |
| MUDANCAS_CARTEIRA_SIMPLES.md | SIM | docs/carteira/calculo-estoque-frontend-2025-01.md — doc histórico válido sobre decisão arquitetural; mover para docs/carteira/ com doc:meta e nota sobre path... |
| ONBOARDING.md | PARCIAL | docs/onboarding.md ou .claude/references/ONBOARDING.md — documento valioso para novos membros que está perdido na raiz sem referência. Precisa de doc:meta e ... |
| OTIMIZACOES_PERFORMANCE_PROJECAO.md | SIM | docs/manufatura/OTIMIZACOES_PERFORMANCE_PROJECAO.md — adicionar header doc:meta (tipo: ADR/registro-tecnico, modulo: manufatura/projecao_estoque), registrar ... |
| PROGRESS.md | SIM | docs/chat/PROGRESS.md ou app/chat/PROGRESS.md — atualmente na raiz sem referência; deveria estar junto ao módulo ou em docs/chat/ com link de app/chat/CLAUDE... |
| QUERY_COMPARACAO_PESOS.md | SIM | docs/dados/queries_comparacao_pesos.md (ou sql/queries_comparacao_pesos.sql) — é material de análise/operações, não deveria estar na raiz. Precisa de doc:met... |
| README_MAPEAMENTO_SEMANTICO_COMPLETO.md | PARCIAL | docs/agente/mapeamento-semantico.md — documento de domínio de alto valor para o agente que está completamente orphan na raiz. Precisa ser indexado em .claude... |
| REDIS_QUEUE_GUIA.md | SIM | docs/portal/REDIS_QUEUE_GUIA.md — adicionar header doc:meta (tipo: runbook, modulo: portal/workers), registrar em docs/INDEX.md. O conteúdo é válido mas está... |
| RELATORIO_REFATORACAO_JS.md | SIM | docs/carteira/refatoracao-js-2025-01.md — é um relatório histórico válido; mover da raiz para docs/carteira/ com doc:meta e referência no índice |
| SINCRONIZACAO_TOTAIS_EMBARQUE.md | SIM | docs/embarques/sincronizacao-totais-embarque.md + doc:meta + registro no índice de embarques |
| VERIFICACAO_PEDIDOS_EXCLUIDOS_ODOO.md | SIM | docs/odoo/verificacao_pedidos_excluidos.md — sair da raiz para docs/odoo/. Precisa de doc:meta e registro no índice. |
