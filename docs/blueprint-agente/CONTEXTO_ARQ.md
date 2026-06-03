<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/blueprint-agente/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# Mergulho Arquitetural do Agente — Contexto (LENTE DE TETO)

> **Papel:** Mergulho Arquitetural do Agente — Contexto (LENTE DE TETO).

## Indice

- [POR QUE este mergulho existe (leia com atenção — corrige um erro anterior)](#por-que-este-mergulho-existe-leia-com-atenção-corrige-um-erro-anterior)
- [Mandato de cada arquiteto](#mandato-de-cada-arquiteto)
- [Arquitetura atual do agente (mapa — ponto de partida, APROFUNDE)](#arquitetura-atual-do-agente-mapa-ponto-de-partida-aprofunde)
- [As 6 teses de partida (do mergulho inicial — APROFUNDE as que tocam seu eixo)](#as-6-teses-de-partida-do-mergulho-inicial-aprofunde-as-que-tocam-seu-eixo)
- [Ferramentas disponíveis a você](#ferramentas-disponíveis-a-você)
- [Output](#output)
- [Contexto](#contexto)

> Documento base para os arquitetos. LEIA inteiro antes de começar.

## POR QUE este mergulho existe (leia com atenção — corrige um erro anterior)

Uma avaliação anterior deste mesmo agente FALHOU por usar a lente errada: ela julgou
capacidades "pelo volume de uso" (~9 sessões/dia) e recomendou PODAR recursos
(ex: desligar o Knowledge Graph) por serem "desproporcionais ao volume".

**ISSO ESTÁ PROIBIDO AQUI.** O dono do sistema (Rafael) foi explícito:
> "Se eu quiser ter o sistema mais avançado do mundo apenas para eu usar e apenas 1
> sessão por dia, tem problema? Se tem, não é você quem vai julgar. Volume só importa
> por demanda de INFRAESTRUTURA, não por necessidade de recursos."

**Regra inviolável desta análise**: volume dimensiona INFRAESTRUTURA (nº de workers,
custo de servidor, rate limits) — NUNCA o VALOR ou a legitimidade de uma capacidade.
Você é um ARQUITETO contratado para ELEVAR O TETO do que o agente pode fazer, não um
auditor cortando gordura. Se a sua conclusão for "isso não vale a pena pelo volume",
você entendeu errado a tarefa — DELETE essa conclusão.

## Mandato de cada arquiteto

Para o SEU eixo, entregue um BLUEPRINT com 3 partes, todas ancoradas no código real:

1. **ESTADO ATUAL (com evidência arquivo:linha)** — o que existe HOJE, como flui, e
   ONDE o circuito quebra / fica incompleto / desligado. Mapeie os componentes reais.
   Diga o que está construído mas inativo (flags OFF, fases não chegaram, tabelas vazias).
2. **ALVO ARQUITETURAL (o teto)** — como seria a versão de classe mundial DESTA
   capacidade. Não "uma melhoria"; o ESTADO FINAL ambicioso. Descreva o desenho
   (componentes, fluxo de dados, contratos, onde encaixa nas 5 camadas do SDK).
3. **CAMINHO INCREMENTAL** — fases ordenadas para sair do estado atual até o alvo,
   REAPROVEITANDO o que já existe (cite o que reaproveita). Cada fase: o que destrava,
   esforço relativo (P/M/G), risco, e dependências de OUTROS eixos.

Regras de qualidade (a análise anterior foi superficial — NÃO repita):
- ZERO sugestão genérica/óbvia ("adicione testes", "melhore logs"). Tudo específico ao SISTEMA.
- Cite evidência arquivo:linha SEMPRE. Use Grep + Read direcionado (não leia 2000 linhas inteiras).
- Identifique as DEPENDÊNCIAS entre eixos (este blueprint habilita/depende de qual outro?).
- Diga o que NÃO sabe / não conseguiu verificar. Não invente.
- Pense como arquiteto de produto de IA de ponta, não como faxineiro de código.

## Arquitetura atual do agente (mapa — ponto de partida, APROFUNDE)

- Wrapper do Claude Agent SDK 0.2.87 / anthropic 0.98.1 / Opus 4.8 (1M ctx). 5 camadas:
  system_prompt (v4.3.3) · tools (12 MCP) · skills (~47 SKILL.md) · subagents (13) · hooks (8).
- 2 canais: Web (SSE) + Teams (async). ~42.9K LOC app/agente + 2.5K app/teams.
- **Camada de inteligência/aprendizado** (17 services em app/agente/services/, ver services/CLAUDE.md):
  pattern_analyzer (extração pós-sessão pessoal+empresa, prescritivo>descritivo),
  knowledge_graph_service (3 layers: regex/Voyage/Sonnet; query_graph_memories),
  memory_consolidator (+ cold tier por eficácia), friction_analyzer, sentiment_detector,
  session_summarizer, intersession_briefing, improvement_suggester (diálogo D7/D8 com Claude Code dev),
  insights_service, metrics_dashboard_service, recommendations_engine, suggestion_generator,
  sql_evaluator_falses_service, tool_skill_mapper.
- **Memória**: tabela agent_memories (escopo pessoal/empresa user_id=0), tiers (quente/frio),
  injeção multi-tier no boot (sdk/memory_injection.py + memory_injection_rules.py), embeddings Voyage+pgvector.
- **Telemetria**: cost_tracker (agent_session_costs), AgentInvocationMetric (per-subagent, Fase A "em coleta";
  Fases B-Quality/C/D-loop NUNCA chegaram; escalated_to_human/user_correction "ficam para Fase D").
- **Evals**: golden dataset em .claude/evals/subagents/.
- **Flags relevantes (config/feature_flags.py)**: USE_OPERATIONAL_DIRECTIVES=OFF (promoção de
  heurística→regra ativa, R0d), USE_PATTERN_LEARNING, USE_BEHAVIORAL_PROFILE, USE_MEMORY_CONSOLIDATION,
  USE_COLD_MOVE (COLD_MOVE_MAX_EFFICACY=0.10), USE_IMPROVEMENT_DIALOGUE, AGENT_BUDGET_CONTROL=OFF em PROD.
- **Roteamento/orquestração**: vive como PROSA no system_prompt (routing_strategy, coordination_protocol,
  output_verification). client.py faz o dispatch. Task* tools (SDK 0.2.82+) existem. can_use_tool (permissions.py).

## As 6 teses de partida (do mergulho inicial — APROFUNDE as que tocam seu eixo)

- **A (flywheel)**: rico em SENSORES, pobre em ATUADORES+feedback. USE_OPERATIONAL_DIRECTIVES OFF;
  Fases B/C/D nunca chegaram; sinal de qualidade inexistente → loop não fecha.
- **B (planejador)**: agente é ROTEADOR reativo single-shot; orquestração é prosa no prompt, não harness.
- **C (proatividade)**: 100% pull, zero push/vigilância. (NÃO é foco deste mergulho, mas cite se cruzar.)
- **D (ontologia)**: KG extrai entidades genéricas; teto = ontologia logística (modelo de mundo Nacom).
- **E (qualidade)**: observabilidade mede CUSTO/latência, nunca QUALIDADE da resposta.
- **F (governança)**: 47 skills/13 subagentes/17 services cresceram organicamente; skills_whitelist.py (WIP)
  é sintoma de falta de modelo de escopo/namespacing/lifecycle de skills.

## Ferramentas disponíveis a você
- Read/Grep/Glob no código (app/agente, app/teams, .claude/skills, .claude/agents, .claude/evals).
- Bash (git log, grep -rn, contagens). venv: `source .venv/bin/activate`.
- WebSearch/WebFetch/Context7 via ToolSearch (best practices de agent architecture 2026 — use para
  ancorar o ALVO em padrões reais, ex: agent memory, planning, evals, agentic RAG/ontologia).
- Cite as fontes externas que usar.

## Output
- Escreva o blueprint em `/tmp/agente-arq/blueprints/<seu-eixo>.md` (markdown, com as 3 partes).
- Retorne um resumo de 8-15 linhas: as 3-5 alavancas principais do seu eixo (estado→alvo em 1 frase cada)
  + as dependências cross-eixo + o primeiro passo concreto de maior alavancagem.
- READ-ONLY: não modifique código. Este é um mergulho de DESIGN.

## Contexto

Documento — evolucao do agente logistico. Tema: Mergulho Arquitetural do Agente — Contexto (LENTE DE TETO)
