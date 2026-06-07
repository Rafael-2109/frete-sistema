<!-- doc:meta
tipo: how-to
camada: L2
sot_de: estrategia de atuacao do agente por tipo de erro (insumo do plano de implementacao) — auditoria de sensores 2026-06-06
hub: docs/blueprint-agente/EXECUCAO.md
superseded_by: —
atualizado: 2026-06-06
-->

# Estratégia de Atuação por Tipo de Erro — insumo do plano (próxima sessão)

> **Papel:** fila acionável (o que IMPLEMENTAR / o que REMOVER, com ponteiros arquivo:linha e docs)
> para a próxima sessão transformar em plano TDD. Origem: auditoria de efetividade dos sensores
> (06/06/2026) + diálogo com Rafael. **Não é teoria — é a lista de execução.**

## Indice
- Princípio central
- Taxonomia: erro → atuador que GARANTE
- REMOVER (R1–R6)
- IMPLEMENTAR (I1–I6)
- Sequência de ataque
- Backlog (condicionado a caso-prova)
- Casos-prova (sessões reais PROD)
- Fontes ponteiradas

## Princípio central

**Rotear cada tipo de erro para o atuador que GARANTE — não injetar memória soft para tudo.**
O sinal de base é o **resultado real / a fonte de verdade** (schema, código, arquivo, audit Odoo R9),
**não** like/frustração/judge-cego (esses são diagnóstico lagging, reforçadores no máximo).

Espectro de força do atuador (use o mais forte que o caso permitir):
`hook/código (garante) > skill/procedimento > regra dura no topo > injeção soft no prompt (a mais fraca)`.

Hoje o agente aposta ~tudo na camada mais fraca (injeção soft). Daí "nunca vi influenciar o comportamento".

## Taxonomia: erro → atuador que GARANTE

| Tipo de erro | Exemplo real (sessão) | Atuador CERTO | Canal |
|---|---|---|---|
| **A. Regra de formato/processo ESTÁVEL** | ordem cronológica dos meses no baseline (Marcus 419/477) | **CÓDIGO na skill** (faz sempre) | **D8 improvement_dialogue** (agente registra → Claude Code implementa) |
| **B. Alucinação de ESTRUTURA nova** | tela/botão inexistente (549), "3 motos" sem ver o PDF (630), tipo de fatura (801), parser hardcoded (630) | **GROUNDING**: verificar a fonte ANTES de afirmar + verificador pós | protocolo + tools de verificação + hook |
| **C. Correção específica RECORRENTE** | "X11-M é x11 mini" (630), regra de cliente, escopo/cluster (Marcus) | memória COM **gatilho determinístico** (entidade/tarefa) + promoção ao recorrer | loop corretivo (existe, gatilho errado) |
| **D. Ação de WRITE de RISCO** | escrita Odoo destrutiva (inventário) | **ENFORCEMENT hook** (PreToolUse) ancorado em R9 + dry-run | hook hard |

Memória soft serve bem a ~nenhum. A maioria do valor está em A (código via D8), B (grounding) e D (hook).

---

## REMOVER (sem dó — custo sem retorno / loop aberto / atuador errado)

**R1 — Injeção de PRESSÃO por frustração.** `enrich_message_if_frustrated` prependa "seja mais direto"
ao prompt do turno — efeito imprevisível e PERIGOSO para WRITE (induz pular dry-run/verificação).
Remover a INJEÇÃO; manter `frustration_score` só como rótulo de triagem (não atuador).
PONTEIRO: `app/agente/routes/chat.py:621-628` (callsite enrich) · `app/agente/services/sentiment_detector.py` (enrich_message_if_frustrated, get_last_frustration_score).

**R2 — eval_runner / eval_gate (A3).** Aposentado (ROADMAP O1.4); `invoke_fn` é stub `NotImplementedError`;
`mode='report_only'` nunca bloqueia. Remover, desacoplando de `calibration_sampler` (que usa `AgentEvalCase`)
e do scheduler. NÃO remover a tabela `agent_eval_case` (a calibração usa).
PONTEIRO: `app/agente/workers/eval_runner.py` · `app/agente/services/eval_gate_service.py` · callers: `app/scheduler/sincronizacao_incremental_definitiva.py`, `directive_promotion_service.py`, `workers/calibration_sampler.py`.

**R3 — Fonte JUDGE-DRIVEN da promoção A4.** `propose_directive_from_judge_session` promove diretriz a partir
de judge não-calibrado = reward-hacking (gera "BOM DIA validado pelo judge"; crítica A §C1). Mesmo com o
endurecimento desta sessão (`_meta_tarefa_trivial`, commit d2a97147b), promover por nota cega é frágil.
DESLIGAR essa fonte até existir judge ancorado em outcome (ver I2/I4). Manter a fonte por CORREÇÃO recorrente.
PONTEIRO: `app/agente/services/directive_promotion_service.py:145` (propose_directive_from_judge_session) · gate em `run_directive_promotion_batch`.

**R4 — Injeção AUTOMÁTICA de ~66 diretrizes legado todo turno.** Dilui o contexto; ninguém escolhe o relevante.
Substituir por progressive disclosure (I6). Com `AGENT_OPERATIONAL_DIRECTIVES=ON` em PROD, isto injeta 66 itens
por turno hoje.
PONTEIRO: `app/agente/sdk/memory_injection.py:420` (_build_operational_directives) · filtro NULL/'ativa' ~:471-475.

**R5 — 👍👎 turn-level como BASE.** NÃO construir o contrato 3 camadas (R8) + Teams para trazer like ao turno.
É reforçador escasso (0/244), não fundação. Despriorizado.
PONTEIRO: `app/agente/routes/feedback.py:46` (session-level) · crítica E "lacuna nº1".

**R6 — judge GENÉRICO (nota de turno cega) como sinal de atuação.** `step_judge` roda 244/244 mas é loop aberto
(telemetria + shadow). Ou re-fundar no outcome real (I2/I4) com saída acionável, ou aposentar como atuador
(manter opt-in só telemetria). NÃO usar nota-de-turno cega para promover/rankear.
PONTEIRO: `app/agente/workers/step_judge.py` · `app/agente/sdk/verifiers.py`.

---

## IMPLEMENTAR (o que de fato muda o comportamento)

**I1 — [Categoria A] Regra estável → CÓDIGO + D8. ✅ NÚCLEO JÁ PROVADO (não é alvo pendente).**
Regra de formato/processo estável vira CÓDIGO, não memória. **Verificado:** a ordem cronológica dos
meses do baseline (dor recorrente do Marcus) JÁ está resolvida em código —
`.claude/skills/gerando-baseline-conciliacao/scripts/gerar_baseline.py:66` (`_mes_ano_sort_key`,
usado em :193 e :334). Isso é a **evidência de que a abordagem funciona**, NÃO um TODO. O que falta é
GENERALIZAR o mecanismo (não o baseline):
- **Discernimento sem depender do soft (§3a):** NÃO confiar no agente "decidir registrar no D8" (camada
  soft, falso-negativo silencioso). Recorrência DETERMINÍSTICA — mesma `error_signature` / mesmo
  artefato corrigido de novo pelo mesmo usuário — FORÇA candidata D8 automaticamente. Trilho pronto:
  captura universal de error_signature + loop corretivo medindo por signature (em PROD).
- **Transversal vs específica:** regra transversal com semântica contratável (formatação BR, encoding,
  "se há coluna de data → ordenar asc COM override") → default no atuador genérico
  `.claude/skills/exportando-arquivos/scripts/exportar.py` (detectar + override, NUNCA regra cega).
  Regra de negócio → código da skill, caso a caso.
- **Gate de SAÍDA do D8 autônomo (§3c):** `register_improvement` precisa de dedup + guard de
  trivialidade (gate de ENTRADA, SA5) **E** verificação pós-implementação (gate de SAÍDA: o commit da
  manhã tocou o arquivo certo? o teste passou?). Sem o gate de saída, "implementa sozinho de manhã" é
  vetor de regressão silenciosa.
PONTEIRO: `gerar_baseline.py:66` (prova) · `exportando-arquivos/scripts/exportar.py` (default transversal) · `app/agente/tools/memory_mcp_tool.py:3299` (register_improvement) · `app/agente/services/improvement_suggester.py`.
DoD: recorrência por error_signature gera candidata D8 sem clique do agente; default de ordenação no exportar.py com override; gate de saída valida commit+teste do D8 autônomo.

**I2 — [Categoria B] GROUNDING: verificar a fonte ANTES de afirmar estrutura.** O maior tipo de erro. Duas peças:
(a) protocolo no system_prompt: "afirmação sobre existência de campo/tela/função/comportamento exige verificar a
fonte (schema JSON / rota / código / arquivo) ANTES"; (b) verificador que checa afirmações de estrutura contra a
fonte e FLAGA alucinação (sinal não-gameável = a fonte). O agente JÁ TEM as tools de verificação e não as usa por
padrão.
PONTEIRO: `app/agente/tools/schema_mcp_tool.py` · `app/agente/tools/routes_search_tool.py` · `app/agente/prompts/system_prompt.md` (regra de grounding) · hook PostToolUse em `app/agente/sdk/hooks.py`.
DoD: em sessão de teste, afirmação sobre campo/tela inexistente é detectada/bloqueada antes de chegar ao usuário.

**I3 — [Categoria C] Gatilho DETERMINÍSTICO por tarefa/entidade.** Substituir/complementar a recuperação por
vector sobre o prompt (falha em prompt curto: "atualizar baseline" → semantic=0) por gatilho determinístico:
tipo-de-tarefa + entidades da ação. A regex layer-1 do KG já extrai entidade.
PONTEIRO: `app/agente/sdk/memory_injection.py` (pipeline de retrieval) · `app/agente/services/knowledge_graph_service.py` (layer 1 regex) · `app/agente/services/tool_skill_mapper.py`.
DoD: tarefa "baseline" recupera as regras do baseline 100% das vezes (não depende de similaridade).

**I4 — [Categoria D] ENFORCEMENT hard para WRITE Odoo, ancorado em R9.** Ligar/expandir o guard PreToolUse
(existe, OFF) usando o audit determinístico R9 (operacao_odoo_auditoria) como ground-truth de outcome.
PONTEIRO: `app/agente/sdk/memory_injection.py` (_enforce_mandatory_invariants, flag `USE_MANDATORY_HARD_ENFORCE` OFF) · `app/agente/sdk/hooks.py` (PreToolUse) · `app/utils/odoo_audit_helpers.py` + tabela `operacao_odoo_auditoria` (R9, CLAUDE.md).
DoD: WRITE Odoo de risco sem dry-run/contra guard é bloqueado no hook (teste).

**I5 — Ciclo de vida: reconciliação no write + invalidação por OUTCOME.** Mata o inchaço ("memórias gigantes").
Write-path decide ADD/UPDATE/DELETE/NOOP (estilo Mem0); re-peso/invalidação por outcome real (R9 / reincidência),
não por eco textual. `effective_count` hoje é desacoplado do outcome.
PONTEIRO: `app/agente/services/pattern_analyzer.py` (_save_personal_insight ~:2045, _track_signature_recurrence ~:1998) · `app/agente/services/memory_consolidator.py` · `app/agente/models.py` (colunas outcome).
DoD: memória redundante funde; memória que levou a outcome ruim cai/invalida.

**I6 — Progressive disclosure (substitui R4).** Parar de injetar 66; injetar um ÍNDICE + o agente recupera sob
demanda (estilo Claude Code: CLAUDE.md aponta, abre o que precisa via view_memories). Reduz diluição e custo.
PONTEIRO: `app/agente/sdk/memory_injection.py:420` · `app/agente/tools/memory_mcp_tool.py` (view_memories).
DoD: prompt injeta índice + ≤N itens recuperados por gatilho (I3), não 66 por recência.

---

## Sequência de ataque (ordem de valor × prova de conceito)

> I1 (regra estável → código) JÁ está PROVADO no baseline (`gerar_baseline.py:66`). **NÃO é alvo — é a
> evidência.** O 1º alvo é o atuador do erro DOMINANTE e provado (alucinação de estrutura, 4/4 casos).

1. **I2 grounding — 1º ALVO (erro dominante, 4/4 casos):** verificar a fonte (schema/rota/código/arquivo)
   ANTES de afirmar estrutura. Ataca a alucinação (549/630/692/801) — o maior valor provado.
   **Plano TDD (cobertura ampla — regra constitucional L2 + tool `resolver`, 3 tasks):** `docs/superpowers/plans/2026-06-06-grounding-cobertura-ampla.md`. O plano `*-verificador-turno-principal.md` foi DESCARTADO (premissa "afirma sem verificar" refutada pela mineração PROD: nos casos reais ele verifica, mas com evidência insuficiente).
2. **I4 enforcement WRITE Odoo:** segurança; usa R9 (ground-truth pronto).
3. **I1 generalização (§3a/§3c):** recorrência determinística por error_signature força candidata D8 +
   gate de saída do D8 autônomo + default transversal no `exportar.py`. (O baseline já está feito.)
4. **Limpeza R2/R3/R1/R6:** remover eval_runner/eval_gate, desligar fonte judge-driven A4, cortar injeção de pressão, tirar judge cego do caminho de atuação.
5. **I3 gatilho determinístico + I6 progressive disclosure + I5 ciclo de vida:** refundação do retrieval/memória (maior, estrutural).

## Backlog — condicionado a caso-prova (NÃO é alvo até existir erro real em PROD)

**Categoria E — interpretação/roteamento por contexto do usuário** (ex: "NF" = fornecedor vs cliente
conforme a área de quem pede). **ESPECULATIVA:** zero caso-prova minerado — os 4 casos reais são todos
B (alucinação). Nasce de exemplo hipotético, não de erro observado. **Revisitar SÓ quando surgir um
erro real de interpretação por perfil em PROD** (minerar a sessão antes de virar alvo).
- Se for feita: o atuador é a **regra que CONFIRMA em WRITE** — perfil (`usuarios.perfil`/`cargo`) como
  *prior* que enviesa a leitura e a ordem de verificação, **NUNCA** pula a checagem nem auto-decide em
  ação de risco (senão reproduz o R1: sinal fraco virando pressão que pula o dry-run).
- **NÃO** injetar `usuarios.perfil` no session_context como "atuador forte": injeção no prompt é SOFT,
  independente de o dado ser cadastral. Dado factual ≠ atuador forte — confundir os dois é o erro a evitar.

## Casos-prova (sessões reais PROD — não inventar, citar)
- **549** (08/05, user 1): inventou tela/botão/URL de upload de recibo; só verificou o código após reclamação. → B.
- **630** (20/05, user 1): "3 motos" (DB) vs 60 (PDF real); parser hardcoded formato "Haroldo SP" vs "GP SENDAS"; "X11-M não existe" (era x11 mini). → B + A (bug parser via D8).
- **692** (27/05, user 1): afirmou A (acessou portal) e ¬A (não consigo acessar) na mesma sessão; negou a incoerência. → B (coerência intra-sessão).
- **801** (05/06, user 1): assumiu fatura 161-9 = transportadora; era cliente. → B.
- **419** (15/04, user 18 Marcus): "não colocou os meses do mais antigo para o mais novo". → A/C.
- **477** (26/04, user 18 Marcus): "ordem cronológica e não alfabética" + "aba resumo ficou errada, ordem cronológica correta". → A/C (reincidência da mesma correção).

## Fontes ponteiradas (ler antes de planejar)
- `docs/blueprint-agente/critica/E-qualidade.md` — PRM/step-level, R10 (gravar na thread PRIMARY), feedback session-level, ground-truth = outcome.
- `docs/blueprint-agente/critica/A-flywheel.md` — reward-hacking (C1), credit assignment/attribution, audit R9 como sinal não-gameável.
- `docs/blueprint-agente/ROADMAP.md` + `EXECUCAO.md` — estado dos cards (regra de ouro: medir antes de atuar; mas não "medir para sempre").
- `app/agente/CLAUDE.md` — R9 (audit hook), R10 (persistência), pipeline de injeção, mapa de flags.
- Memória Claude Code: `diagnostico_efetividade_sensores_agente.md` (estado da auditoria + Frentes 1/2 já feitas).
