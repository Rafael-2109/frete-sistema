# B5 — Matriz Consolidada de Achados: Rafael × Agente × Evidência

**Data**: 2026-06-09  
**Autor**: Subagente B5  
**Insumos**: avaliacao_rafael.md, avaliacao_agente.md, findings A1–A6

---

## PARTE 1 — MATRIZ COMPLETA (30 itens)

> Colunas: ID | Veredito | Evidência | Sobreposição | Conflitos | Dependências

---

### GRUPO Rafael (R-1 a R-9, RP-1, RP-2)

---

#### R-1 — skill_hints e world_model: "LIXO, pode remover inclusive do código"

| Campo | Valor |
|-------|-------|
| **Veredito** | CONFIRMADO |
| **Evidência** | A1: `hooks.py:1443-1468` — blocos gerados quando flags ON. A3: `.env:254,256` confirma `AGENT_SKILL_RAG=true` e `AGENT_WORLD_MODEL_INJECT=true` em PROD (ambas ativas contra o default `false`). A3: skill_hints sugeriu `carregando-motos-assai` e `operando-portal-atacadao` para query "contexto de boot do agente" — incoerência confirmada por algoritmo token-overlap fraco (`context_enrichment.py:55-115`). world_model classifica ODOO como `[produto]` e SICOOB como `[transportadora]` — erro de qualidade ontológica confirmado. |
| **Sobreposição** | C4 (agente) — mesmo alvo. C4 é "hipótese" para o agente, mas R-1 é decisão firme do Rafael. A3 confirma defeitos concretos. |
| **Conflitos** | C4 do agente pede "ablar com A/B test primeiro". Rafael diz "remover inclusive do código". O agente é cauteloso; Rafael é decisivo. Conflito real: metodologia de validação. Rafael tem autoridade de decisão — o conflito é de processo, não de diagnóstico. |
| **Dependências** | Nenhuma — remoção das env vars é ação independente (zero risco). Remoção de código pode aguardar confirmação mas não bloqueia nada. |

---

#### R-2 — Redundância sobre skills (3 lugares falando da mesma coisa)

| Campo | Valor |
|-------|-------|
| **Veredito** | CONFIRMADO com nuances |
| **Evidência** | A4: Os 3 lugares existem: (A) R7 routing_strategy no system_prompt `contexto_boot.md:811`; (B) ponteiro para ROUTING_SKILLS.md `contexto_boot.md:814`; (C) 28 skills frontmatter Seção 2. A3: truncamento CLI de 16K confirma que o frontmatter de 28 skills já chega parcialmente. A4-Q6: ROUTING_SKILLS.md tem versão condensada no system_prompt + versão completa no arquivo — redundância parcialmente intencional (camada 0 vs camada 1). O changelog de 2000+ chars na linha 32 do ROUTING_SKILLS.md é ruído puro. |
| **Sobreposição** | C1 (agente) — mesmo diagnóstico: "1 fonte canônica + ponteiros". A5: agente cita que "roteamento espalhado" é problema (A5 do agente, não A5 da fase de pesquisa). |
| **Conflitos** | Nenhum conflito — Rafael e agente concordam. Detalhe: a redundância R7 ↔ ROUTING_SKILLS.md é "defensiva saudável" segundo A4, mas o agente (C1) pede "tirar das skills o que já está no routing_strategy". Nuance: o que é "fonte canônica" vs "ponteiro" precisa ser definido pelo padrão arquitetural. |
| **Dependências** | RP-1 (macro-estrutura) deve ser definida antes de decidir o que é canônico onde. |

---

#### R-3 — Skills dev-only aparecendo para o agente web

| Campo | Valor |
|-------|-------|
| **Veredito** | CONFIRMADO |
| **Evidência** | A3: As 4 skills (`consultando-sentry`, `diagnosticando-banco`, `gerindo-agente`, `padronizando-docs`) não constam em `SKILLS_DELEGADAS_SUBAGENTE` (`app/agente/config/skills_whitelist.py:99-104`) — confirmado por execução Python. A5: dados de 90 dias: `diagnosticando-banco`=0 usos, `padronizando-docs`=0 usos, `gerindo-agente`=1 uso (admin, jun/2026), `consultando-sentry`=2 usos (admins, último há 18 dias). Nenhuma tem uso real por usuários finais. |
| **Sobreposição** | R-7 é o mesmo item com ângulo de dados de produção. C6 (agente) menciona "fronteira PRE/POS repetida em cada skill" — diferente, mas relacionado ao ruído das skills. A3 finding 7 (bug whitelist: `carregando-motos-assai` e `consultando-venda-loja` também não excluídas). |
| **Conflitos** | Nenhum. |
| **Dependências** | R-7 fornece os dados que confirmam R-3. Decisão de remoção é independente. |

---

#### R-4 — Redundância entre skills: lendo-arquivos → lendo-documentos

| Campo | Valor |
|-------|-------|
| **Veredito** | PARCIAL — redundância confirmada, unificação tecnicamente viável mas não urgente |
| **Evidência** | A5: `lendo-arquivos`=28 invocações (9 usuários), `lendo-documentos`=10 invocações (3 usuários), ratio 2.8:1. Ambas ativas com demanda real. A5-nota: unificação é "tecnicamente viável sem perda de demanda real". Não foi verificado se as funções são idênticas ou complementares — análise funcional dos SKILL.md não foi feita neste subagente. |
| **Sobreposição** | Nenhuma sobreposição direta com outros itens. |
| **Conflitos** | Nenhum. |
| **Dependências** | Precisa de análise funcional dos SKILL.md das duas skills antes de unificar (verificar se cobrem casos diferentes). Baixa prioridade dado que ambas têm uso real. |

---

#### R-5 — CLAUDE.md raiz possui info dev exibida ao agente web

| Campo | Valor |
|-------|-------|
| **Veredito** | CONFIRMADO com mapeamento detalhado |
| **Evidência** | A4-Q5: Mapeamento seção a seção verificado. DEV-ONLY confirmadas: (1) REGRAS UNIVERSAIS rule 1 "source .venv/bin/activate" (`contexto_boot.md:1641`); (2) FORMATACAO NUMERICA BRASILEIRA — filtros Jinja2 (`contexto_boot.md:1647-1657`), 12 linhas sem utilidade ao agente web; (3) Design System UI/CSS completo com ui_audit.py, pre-commit hooks (`contexto_boot.md:1733-1749`), 16 linhas. Conteúdo MISTO (parcialmente útil): TECH STACK (~50%), CAMINHOS DO SISTEMA (~30%), SUBAGENTES (crítico mas com inconsistência). |
| **Sobreposição** | P1 e P9 do findings A4 cobrem o mesmo problema. R-9 cobre redundância de subagentes especificamente. RP-1 é a raiz conceitual (falta macro-estrutura definindo o que vai onde). |
| **Conflitos** | Rafael menciona "ÍNDICE DE REFERENCIAS — muito bom". A4 confirma ÍNDICE como essencial para o agente web. Sem conflito. Divergência de prioridade: Rafael inclui DADOS e REGRAS UNIVERSAIS como questionáveis — A4 confirma DADOS como crítico mas com formulação confusa. |
| **Dependências** | RP-1 (macro-estrutura) deve preceder edições no CLAUDE.md para evitar caos iterativo. |

---

#### R-6 — Incoerência de tamanho × granularidade nas memórias

| Campo | Valor |
|-------|-------|
| **Veredito** | CONFIRMADO com causa raiz identificada |
| **Evidência** | A2: Causa raiz confirmada: "Não há campo de 'tamanho máximo por memória' no schema" (`memory_injection.py` — Tier 2 entra inteira ou é pulada, sem truncamento individual). A2: O composite score pondera importância/similaridade mas NÃO tamanho. A armadilha de 27 linhas sobre float IBGE entra com mesmo peso de 1 linha de perfil. A1-Tier 1.5: único tier com truncamento (400 chars). Rafael cita especificamente: "tmpdir-divergente.xml" (improvement dialogue determinístico sendo injetado como memória) e "agente-enviou-link-de-arquivo-vazio.xml" (idem) — esses são casos de conteúdo mal categorizado, não apenas tamanho. |
| **Sobreposição** | C5 (agente) — "memórias injetadas em volume (parece injetar a maioria, não RAG por intent)". RP-2 — injeção mais coerente e direcionada. C3 (agente) — stale_empresa + improvement_responses no boot (mesmo problema de conteúdo errado no boot). |
| **Conflitos** | C5 do agente é "Média" confiança (hipótese). A2 confirma o mecanismo e detecta causa raiz — dado objetivo, não hipótese. Rafael tem razão com evidência. |
| **Dependências** | RP-2 (injeção por intent + proveniência) é a solução abrangente. R-6 pode ter quick wins separados (remover improvement dialogue do boot, adicionar teto por memória). |

---

#### R-7 — preferred_skills do routing_context

| Campo | Valor |
|-------|-------|
| **Veredito** | CONFIRMADO pelos dados de produção |
| **Evidência** | A5: `gerindo-agente`=1 uso em 90 dias (admin), `diagnosticando-banco`=0 usos, `consultando-sentry`=2 usos (ambos admins). Nenhuma usada por usuários finais. A3: `_DOMAIN_SKILLS['admin']` em `memory_injection.py:371-378` é mapeamento hardcoded — não derivado de uso histórico real. Rafael dominou domínio `admin` por keyword match em sessões de diagnóstico/bug. |
| **Sobreposição** | R-3 (mesmas 4 skills). A5 confirma ambos R-3 e R-7 com os mesmos dados. |
| **Conflitos** | Nenhum. |
| **Dependências** | R-3 e R-7 têm a mesma solução: remover essas skills do listing e do `_DOMAIN_SKILLS['admin']`. |

---

#### R-8 — debug_mode + sql_admin_context

| Campo | Valor |
|-------|-------|
| **Veredito** | CONFIRMADO como design sub-ótimo |
| **Evidência** | A1: `debug_context` (`hooks.py:1331-1352`) — injetado apenas para admin em debug mode. `sql_admin_context` (`hooks.py:1357-1381`) — apenas para `user_id in {1, 55, 62}`. Ambos já são condicionais por `user_id` ou estado de debug. Rafael pede "barreira determinística que aciona quando NÃO for admin" em vez de injetar para todos + explicar que admin pode fazer. A análise do boot mostra ~20 linhas de sql_admin_context sendo injetadas APENAS para user_id em {1,55,62} — portanto a barreira já existe. O ponto de Rafael é de arquitetura: a lógica de "mostrar contexto só quando relevante" já está implementada, mas a formulação das mensagens pode ser mais limpa (sem explicar para não-admins que existe uma capacidade que eles não têm). |
| **Sobreposição** | D2 (agente) — tensão "não revelar system prompt" vs owner autenticado. Relacionado mas diferente: D2 é sobre revelar o prompt, R-8 é sobre injetar contexto de capacidades admin para não-admins. |
| **Conflitos** | Nenhum conflito substantivo. Rafael e agente concordam que o design atual tem fricção. |
| **Dependências** | Nenhuma. Pode ser endereçado isoladamente. |

---

#### R-9 — Subagentes duplicados e inconsistentes

| Campo | Valor |
|-------|-------|
| **Veredito** | CONFIRMADO |
| **Evidência** | A4-Q5: system_prompt `<subagents>` block (`contexto_boot.md:828-879`) tem 12 subagentes. CLAUDE.md raiz SUBAGENTES (`contexto_boot.md:1779-1817`) tem 13 subagentes + 1 dev-only. O `gestor-estoque-odoo` aparece no CLAUDE.md mas NÃO no system_prompt `<subagents>` block. `desenvolvedor-integracao-odoo` aparece no CLAUDE.md como "dev-only, não exposto ao agente web" — ruído cognitivo. A4 confirma P2 e P8. |
| **Sobreposição** | R-5 (CLAUDE.md tem info para dev, incluindo subagentes duplicados). |
| **Conflitos** | Nenhum. |
| **Dependências** | RP-1 (macro-estrutura) deve definir qual é a lista canônica de subagentes e onde ela mora. |

---

#### RP-1 — Peso igual por linha; falta macro-estrutura

| Campo | Valor |
|-------|-------|
| **Veredito** | CONFIRMADO como diagnóstico raiz de múltiplos outros problemas |
| **Evidência** | A6: 3-layer architecture-alvo definida em `docs/superpowers/plans/2026-06-04-refactor-governanca-prompt-agente.md:102-108` (Camada 0 = princípio/constituição, Camada 1 = procedimento/skill, Camada 2 = memórias/turno). ESTA ARQUITETURA JÁ EXISTE como plano mas não está completamente implementada (R6/R7/R8 do ROADMAP todos abertos). A6: governança FASE 5 existe para tamanho mas NÃO para conteúdo (verificação de altitude apenas via R-EXEC-5 manual). A2: injeção de memórias sem classificação por intent do turno atual. |
| **Sobreposição** | RP-1 é a raiz de: R-2 (redundância skills), R-5 (CLAUDE.md misto), R-6 (memórias sem graduação), R-9 (subagentes duplicados). C2 (agente) — inflação de prioridade. C1 (agente) — redundância por falta de fonte canônica definida. |
| **Conflitos** | Nenhum conflito. A6 confirma que a arquitetura 3-layer foi definida mas não implementada completamente — o diagnóstico do Rafael é consistente com o estado real. |
| **Dependências** | RP-1 é PRÉ-REQUISITO de R-2, R-5, R-9. Deve ser o primeiro entregável do estudo. |

---

#### RP-2 — Injeção de memórias mais coerente + proveniência

| Campo | Valor |
|-------|-------|
| **Veredito** | CONFIRMADO com gaps de implementação identificados |
| **Evidência** | A2: `source_session_id` NÃO existe como coluna em `agent_memories`. Apenas `AgentKnowledgeNode` e `AgentImprovementDialogue` têm `source_session_ids ARRAY(Text)`. Intent do TURNO ATUAL não é usado — domínio é histórico (`_compute_user_domain` usa últimas 10 sessões). Memória "fatura 161-9" entrou no boot sobre "contexto de boot do agente" porque `priority='mandatory'` ou alta similarity com algum termo. A2-bug: duplicação user_rules vs user_memories (`protected_ids` não inclui memórias do L1). |
| **Sobreposição** | R-6 (granularidade memórias), C5 (volume de memórias), A6 agente (sem frescor/confiança). A6-agente menciona `last_confirmed`/`confidence` ausentes. |
| **Conflitos** | Nenhum. |
| **Dependências** | Requer migration de schema (nova coluna `source_session_id`) + mudança em `save_memory`. R5 (golden dataset) seria necessário para validar comportamento pós-mudança. |

---

### GRUPO Agente — Manter (M1 a M6)

---

#### M1 — Blocos `<why>` em todas as regras (MANTER)

| Campo | Valor |
|-------|-------|
| **Veredito** | CONFIRMADO como correto manter |
| **Evidência** | A6: commit `fee8f1f17` (2026-06-05) restaurou `<why>` após serem cortados por perseguir meta de linhas. Mensagem do commit: "QUALITY_REVIEW marca os `<why>` como Top Strength (A2 = 5/5)". Lição documentada em `app/agente/CLAUDE.md:305`. Evidência empírica de que cortar `<why>` degrada — reverção foi necessária. |
| **Sobreposição** | A6 foi o finding que verificou isso. Sem sobreposição com itens Rafael. |
| **Conflitos** | Rafael não menciona os `<why>` explicitamente. Ausência de conflito — Rafael está focado em remover o que não funciona, não em cortar os `<why>`. |
| **Dependências** | Nenhuma. Deve ser respeitado em toda edição futura. |

---

#### M2 — constitutional_hierarchy L1–L4 + exemplo (MANTER)

| Campo | Valor |
|-------|-------|
| **Veredito** | CONFIRMADO como correto manter |
| **Evidência** | A6: implementado em v4.3.0 (`86668052e`, 2026-04-12) como Q2 da QUALITY_REVIEW. Score M (Constitutional Hierarchy) subiu de 3/5 para 3.67/5. Único mecanismo de desempate entre regras conflitantes. |
| **Sobreposição** | C2 (agente, COMPRIMIR) fala de inflação de prioridade — relacionado mas diferente: M2 é a hierarquia estrutural, C2 é sobre rótulos como "CRÍTICO/INVIOLÁVEL" espalhados. |
| **Conflitos** | Nenhum conflito com Rafael. |
| **Dependências** | M2 deve ser consultado ao resolver C2 (inflação de prioridade). |

---

#### M3 — L2 grounding: "fonte que PROVA vs DESCREVE" (MANTER)

| Campo | Valor |
|-------|-------|
| **Veredito** | CONFIRMADO como correto manter |
| **Evidência** | A6: mencionado como "personalizado a uma falha real" do agente. Originado da QUALITY_REVIEW. A4-Q5: MODELOS CRITICOS no CLAUDE.md inclui gotchas `qtd_saldo` que são mecanismo anti-alucinação. Coerente. |
| **Sobreposição** | M4 (campos críticos) é a aplicação específica do princípio geral de M3. |
| **Conflitos** | Nenhum. |
| **Dependências** | Nenhuma. |

---

#### M4 — critical_fields (qtd_saldo) + IDs de company Odoo (MANTER)

| Campo | Valor |
|-------|-------|
| **Veredito** | CONFIRMADO como correto manter |
| **Evidência** | A4-Q5 MODELOS CRITICOS: "gotchas qtd_saldo_produto_pedido vs qtd_saldo são essenciais para queries corretas". Verificado em `contexto_boot.md:1661-1674`. Campo em CLAUDE.md raiz, também presentes no system_prompt como gotchas inline. |
| **Sobreposição** | M3 (princípio geral do grounding). |
| **Conflitos** | Nenhum. |
| **Dependências** | Nenhuma. |

---

#### M5 — R11/R12 — confirmação tipada em escrita Odoo/DB (MANTER)

| Campo | Valor |
|-------|-------|
| **Veredito** | CONFIRMADO como correto manter — e parcialmente já movido para enforcement de código |
| **Evidência** | A6: T2.1 (`8954563fe`) moveu `action_update_taxes` para gate determinístico em código. O princípio de "confirmação antes de escrita irreversível" permanece no system_prompt mas o procedimento específico saiu. Isso é o modelo correto: princípio no system_prompt (M5), procedimento específico no código ou skill. |
| **Sobreposição** | A6 (T2.1) é o prior art de como implementar M5 corretamente. |
| **Conflitos** | Nenhum. |
| **Dependências** | Nenhuma. |

---

#### M6 — session_summaries + pendencias + user_rules (MANTER)

| Campo | Valor |
|-------|-------|
| **Veredito** | CONFIRMADO como correto manter |
| **Evidência** | A1: `session_summaries` e `pendencias` fazem parte do Tier 0 (always injected, fora do budget). A2: mecanismo verificado em `memory_injection.py`. Tier L1 user_rules são memórias `priority='mandatory'` injetadas no topo. Esses componentes sustentam continuidade entre sessões — objetivo crítico do sistema. |
| **Sobreposição** | C3 (agente, RELOCAR) é sobre `stale_empresa` + `improvement_responses` — elementos DIFERENTES das session_summaries e user_rules. M6 protege o núcleo de continuidade; C3 remove o ruído de manutenção. Não há conflito. |
| **Conflitos** | Nenhum. |
| **Dependências** | Nenhuma. |

---

### GRUPO Agente — Comprimir/Cortar (C1 a C6)

---

#### C1 — Redundância (gotcha qtd_saldo em 3 lugares; fronteira PRE/POS em cada skill)

| Campo | Valor |
|-------|-------|
| **Veredito** | CONFIRMADO com evidência |
| **Evidência** | A4: `qtd_saldo` aparece em MODELOS CRITICOS do CLAUDE.md (`contexto_boot.md:1661`) E como gotcha inline no system_prompt (`contexto_boot.md:662`). A3: fronteira PRE/POS não foi verificada skill-a-skill, mas o truncamento CLI (A3) confirma que cláusulas longas de skill são descartadas — portanto repetir "PRE" em cada skill é duplamente ineficiente (verbose + truncado de qualquer forma). |
| **Sobreposição** | R-2 (Rafael) — mesmo tema de redundância. |
| **Conflitos** | Nenhum. |
| **Dependências** | RP-1 define qual é a fonte canônica, então C1 precisa de RP-1 para execução. |

---

#### C2 — Inflação de prioridade (6 rótulos de "máximo")

| Campo | Valor |
|-------|-------|
| **Veredito** | PARCIAL — confirmado como problema real, mas A6 mostrou que dial back em lote é perigoso |
| **Evidência** | A6: Audit R1 (2026-04-12) encontrou 94% das ocorrências CORRETAS (safety L1 + domain L3 + headers). "Dial back em lote CANCELADO (alto risco PM-2.1)". O problema real é que mesmo com 94% corretas, o sinal achata quando muitos itens se anunciam como "máximo". Mas a solução não é remover rótulos em lote — é usar a hierarquia M2 (L1-L4) como filtro antes de adicionar novos rótulos. |
| **Sobreposição** | M2 (hierarquia constitucional) — a solução para C2 é aplicar M2 rigorosamente. |
| **Conflitos** | CONFLITO REAL com A6: o agente pede "colapsar para 3 níveis reais", mas A6 mostrou que o audit confirmou 94% como corretos. A solução não é colapsar os existentes mas parar de adicionar novos sem critério. |
| **Dependências** | A solução de C2 é forward-looking: checklist R-EXEC-5 (governança FASE 5) já mitiga parcialmente. Não é ação de edição em lote. |

---

#### C3 — stale_empresa + improvement_responses no boot operacional (RELOCAR)

| Campo | Valor |
|-------|-------|
| **Veredito** | CONFIRMADO — quick win identificado |
| **Evidência** | A1: `stale_empresa` e `improvement_responses` são sub-blocos do `intersession_briefing` (`intersession_briefing.py:73` e `:83`). `stale_empresa` = memórias empresa > 60 dias sem atualização. `improvement_responses` controlado por flag `AGENT_IMPROVEMENT_DIALOGUE` (default `false`). Rafael (R-6) cita explicitamente esses como improvement dialogue determinístico que não deveria ser injetado como memória operacional. |
| **Sobreposição** | R-6 (Rafael) — cita exatamente esses elementos. M6 protege session_summaries e pendencias — esses são DIFERENTES e podem ser removidos sem afetar continuidade. |
| **Conflitos** | Nenhum. |
| **Dependências** | Nenhuma. Pode ser implementado imediatamente (mover para view do gerindo-agente). |

---

#### C4 — Blocos advisory: world_model, skill_hints, routing_context

| Campo | Valor |
|-------|-------|
| **Veredito** | CONFIRMADO para skill_hints e world_model (R-1); PARCIAL para routing_context |
| **Evidência** | A3: skill_hints e world_model têm defeitos concretos (tokens errados, qualidade de ontologia ruim). R-1 confirma remoção decisiva. routing_context tem problema diferente: preferred_skills inclui dev-only (R-7), mas o conceito de routing_context (active_traps do domínio) tem valor potencial se corrigido. A5: `preferred_skills` da categoria admin é inútil para usuários finais — a parte de preferred_skills de routing_context deve ser corrigida, não o routing_context inteiro. |
| **Sobreposição** | R-1 e R-7 cobrem partes de C4. |
| **Conflitos** | Agente pede "A/B com e sem" para C4 inteiro. Rafael decide remoção de skill_hints e world_model. Conflito de escopo: Rafael é mais específico (remove 2 dos 3 advisory); agente generaliza para os 3. routing_context merece abordagem cirúrgica, não remoção total. |
| **Dependências** | Remoção de skill_hints e world_model: imediata (R-1). Correção do routing_context: depende de R-3 (remover dev-only das skills) e do novo `_DOMAIN_SKILLS` que não inclua as skills removidas. |

---

#### C5 — Memórias injetadas em volume (não RAG por intent)

| Campo | Valor |
|-------|-------|
| **Veredito** | CONFIRMADO com causa raiz identificada |
| **Evidência** | A2: O mecanismo atual usa domínio HISTÓRICO (últimas 10 sessões), não intent do TURNO ATUAL. A2: para prompts com pouco conteúdo útil para embedding (como "me mostra o contexto de boot"), similaridade é baixa → fallback de recência injeta as 15 memórias mais recentes independentemente do topic. A2: intent classifier do turno atual ausente — ausência identificada explicitamente. RP-2 pede exatamente isso. |
| **Sobreposição** | RP-2 (Rafael) — mesma solução. R-6 — problema relacionado. |
| **Conflitos** | C5 é "Média" confiança para o agente (introspecção). A2 confirma com evidência de código — base objetiva, não hipótese. |
| **Dependências** | Solução completa de C5 requer: (1) intent classifier por turno, (2) filtro de Tier 2 por domínio do turno. Solução parcial: corrigir bug de duplicação (adicionar L1 IDs ao protected_ids) — implementável imediatamente sem ML. |

---

#### C6 — Descrições de skill longas/duplicadas

| Campo | Valor |
|-------|-------|
| **Veredito** | CONFIRMADO — o truncamento CLI é evidência indireta |
| **Evidência** | A3: CLI trunca `description` de cada skill a ~150-320 chars quando o total excede 16K. O truncamento descarta cláusulas USAR/NÃO USAR (que ficam no fim da description) — exatamente o conteúdo mais valioso para desambiguação de roteamento. A3: bug no whitelist (`carregando-motos-assai`, `consultando-venda-loja` não excluídas) contribui para inflar o listing. |
| **Sobreposição** | R-3 (skills dev-only também contribuem para o listing inflado). A3 finding 7 (bug whitelist). |
| **Conflitos** | Nenhum. |
| **Dependências** | Remover skills dev-only (R-3) reduz o listing, aliviando o truncamento. Mas a solução completa de C6 requer encolher os exemplos near-duplicados nas descriptions. |

---

### GRUPO Agente — Adicionar (A1 a A6)

---

#### A1 — Sem "estado vivo de hoje" (começo cego ao agora)

| Campo | Valor |
|-------|-------|
| **Veredito** | NAO-VERIFICAVEL-AINDA — feature ausente confirmada, mas impacto e viabilidade não medidos |
| **Evidência** | A1: não existe bloco de "estado vivo" no contexto de boot — confirmado pelo dump `contexto_boot.md` (nenhum bloco com contagem de pedidos abertos ou status Odoo/SSW). A6: gap G4 (adaptive thinking) aberto. A2: `intersession_briefing` tem erros Odoo sync das últimas 6h (`intersession_briefing.py:51`) — proto-versão do que A1 pede. Mas o bloco é de erros de sync, não de "pedidos abertos/rupturas". |
| **Sobreposição** | A2 (agente) — "sem flag de saúde no boot" — relacionado mas diferente: A1 é estado operacional, A2 é saúde de sistemas. |
| **Conflitos** | Agente avisa: "A1 é dinâmico (quebra cache, pode ficar stale) → provavelmente opt-in". A6: pattern de fast-path (F1+F2) mostra que features estáticas podem fazer opt-in sem muito custo. Sem conflito real — A1 é opt-in por design. |
| **Dependências** | Baixa prioridade em relação aos itens de remoção/correção. Implementar apenas após quick wins do C3, R-1, R-3. |

---

#### A2 — Sem flag de saúde no boot (Odoo/SSW/Render)

| Campo | Valor |
|-------|-------|
| **Veredito** | NAO-VERIFICAVEL-AINDA — feature ausente confirmada |
| **Evidência** | A1: circuit breaker de Odoo/SSW existe no código mas seu estado não é injetado no boot. `intersession_briefing.py:51` injeta erros de sync Odoo das últimas 6h — proto-versão parcial. Não foi verificado se existe endpoint de health check do circuit breaker exposto para o hook. |
| **Sobreposição** | A1 (estado vivo) — relacionado mas A2 é mais específico (saúde de sistemas, não dados operacionais). |
| **Conflitos** | Nenhum. |
| **Dependências** | Requer circuit breaker já implementado e acessível no contexto do hook. Não bloqueia nada crítico. |

---

#### A3 — Sem destilação dos erros recorrentes

| Campo | Valor |
|-------|-------|
| **Veredito** | PARCIAL — infra existe mas destilação para o boot não foi feita |
| **Evidência** | A5: `agent_skill_effectiveness` tem 5 linhas (desde jun/2026), ainda embrionária. Loop corretivo (`error_signature` em `agent_memories`) e `agent_improvement_dialogue` têm dados brutos. A6: skill effectiveness avaliador pós-sessão existe (PROD desde 2026-06-07). O "top 3 erros deste usuário/domínio" não existe como bloco injetado — apenas como dados brutos no banco. |
| **Sobreposição** | C3 (agente) — improvement_responses é ruído; A3 pede destilação útil. Eles são opostos: C3 remove o improvement_responses raw do boot, A3 pede um resumo destilado dos erros recorrentes. Compatíveis se implementados corretamente. |
| **Conflitos** | Paradoxo aparente: C3 remove improvement_responses do boot; A3 quer erros destilados. Resolução: o formato é diferente — improvement_responses é um diálogo longo e cru; A3 pede "top 3 erros" compacto e acionável. Não é conflito. |
| **Dependências** | Requer `agent_skill_effectiveness` com mais dados (pelo menos 30 dias de dados) para destilação útil. Baixa prioridade agora. |

---

#### A4 — Sem few-shot nas tarefas de alta frequência

| Campo | Valor |
|-------|-------|
| **Veredito** | NAO-VERIFICAVEL-AINDA — ausência confirmada, impacto hipotético |
| **Evidência** | A6: Q1 do QUALITY_REVIEW (few-shot no system prompt) foi ABERTO — empurrado para R17 em skills específicas. PM-2.2 alerta que few-shot no system_prompt pode causar context bloat. A5: top skills (exportando-arquivos, lendo-arquivos, gerindo-expedicao) são as candidatas para few-shot nas skills, não no system_prompt. |
| **Sobreposição** | A6-prior art: R17 do roadmap é exatamente A4 do agente. |
| **Conflitos** | Agente pede few-shot no boot. PM-2.2 do STUDY e R17 do ROADMAP direcionam few-shot para SKILLS, não para o system_prompt. Conflito de localização: system_prompt vs skills. A solução é few-shot nas skills de alta frequência (R17), não no boot. |
| **Dependências** | R5 (golden dataset) é necessário para validar. R17 é o plano correto. |

---

#### A5 — Roteamento espalhado

| Campo | Valor |
|-------|-------|
| **Veredito** | CONFIRMADO como problema real |
| **Evidência** | A4: routing está em 3 lugares: (1) R7 no system_prompt, (2) ROUTING_SKILLS.md referenciado, (3) frontmatter de 28 skills. Todos falam de roteamento com granularidades diferentes. R-2 (Rafael) é o mesmo problema visto do ângulo de redundância. A3: algoritmo de skill_hints adiciona um 4º caminho de roteamento (via token-overlap), com resultados ruins. |
| **Sobreposição** | R-2 (Rafael) — mesmo diagnóstico. RP-1 — raiz do problema. |
| **Conflitos** | Nenhum. |
| **Dependências** | RP-1 (macro-estrutura) define onde o roteamento fica canonicamente. |

---

#### A6 — Memórias sem frescor/confiança

| Campo | Valor |
|-------|-------|
| **Veredito** | CONFIRMADO — campos ausentes no schema DB |
| **Evidência** | A2: `last_confirmed` — campo inexistente no schema `agent_memories`. `confidence` existe apenas como texto inline em user.xml (gerado pelo pattern_analyzer), não como coluna queryável. Campos de frescor existentes: `last_accessed_at`, `updated_at`, `usage_count`, `effective_count`, `reviewed_at` (nullable). `reviewed_at` é a aproximação mais próxima de `last_confirmed` mas não é automaticamente populado. |
| **Sobreposição** | RP-2 (Rafael) — frescor é parte da proveniência. |
| **Conflitos** | Nenhum. |
| **Dependências** | Requer migration de schema. Pode ser combinada com a migration de `source_session_id` (RP-2). |

---

### GRUPO Agente — Decidir (D1 a D3)

---

#### D1 — Concisão (R1/L4) vs andaime de segurança

| Campo | Valor |
|-------|-------|
| **Veredito** | DECIDIDO implicitamente — A6 fornece a resposta |
| **Evidência** | A6: "tokens baratos (cache hit 10%); ROI de enxugamento BAIXO" (QUALITY_REVIEW citada). A6: PM-2.1 "dial back em lote perigoso". A6: a regra de M2 (L1>L4) resolve o "conflito" — L4 (concisão) cede a L1 (segurança). A lição do STUDY: "linguagem imperativa em L1/safety é MAIS segura que positiva". O andaime de segurança VENCE em operações irreversíveis. |
| **Sobreposição** | M2 (hierarquia constitucional) — o desempate está ali. |
| **Conflitos** | Nenhum — a hierarquia L1-L4 já resolve isso. O que falta é aplicar explicitamente por tipo de tarefa (consulta trivial vs operação irreversível). |
| **Dependências** | M2 deve ser comunicado como resposta. |

---

#### D2 — "não revelar system prompt" vs owner autenticado em debug_mode

| Campo | Valor |
|-------|-------|
| **Veredito** | NAO-VERIFICAVEL-AINDA — tensão real, decisão de design necessária |
| **Evidência** | A4-Q5: o agente usou workaround "apontando para o repo" quando Rafael pediu o transcript. A1: `debug_context` (`hooks.py:1331-1352`) — já há contexto especial para admin em debug. O `security_invariants` no preset (T3.1) é defense-in-depth — projetado contra extração por agentes maliciosos. Rafael, autenticado como owner via hook, não é o threat actor. |
| **Sobreposição** | R-8 — relacionado (contexto admin vs não-admin). |
| **Conflitos** | A tensão é real. A solução do agente ("carve-out explícito para owner/debug") é razoável. |
| **Dependências** | Decisão de design do Rafael. Não bloqueia outras ações. |

---

#### D3 — Ordenação dentro do hook (34KB) — "aja-agora" no meio

| Campo | Valor |
|-------|-------|
| **Veredito** | CONFIRMADO como oportunidade — ordenação hardcoded mas mutável |
| **Evidência** | A1: "A ordem dos blocos NÃO é configurável — está hardcoded no `full_context` string concatenation em `hooks.py:1471`". A ordem atual: resume_fallback → session_context → memories → correction_hint → debug → sql_admin → skill_hints → world_model. O `user_rules` (ação imediata, topo) está dentro do bloco de memories (posição 3), não na última posição antes da mensagem do usuário. Modelos pesam início e fim — D3 aponta que o "aja-agora" (user_rules/pendencias) deveria estar mais próximo do fim (colado à mensagem). |
| **Sobreposição** | M6 (session_summaries/pendencias/user_rules devem ser mantidos). D3 não contradiz M6 — apenas propõe reordenar. |
| **Conflitos** | A1 confirma que a ordem hardcoded pode ser mudada em `hooks.py:1471` sem impacto funcional. Risco: modelos são sensíveis à posição; qualquer reordenação deve ser validada com o golden dataset (R5). |
| **Dependências** | R5 (golden dataset) para validação. Pode ser feito cirurgicamente. |

---

## PARTE 2 — LACUNAS NOVAS (não cobertas por Rafael ou agente, mas reveladas pela Fase A)

---

### N-1 — Bug de duplicação user_rules vs user_memories (omissão de filtragem)

| Campo | Valor |
|-------|-------|
| **Evidência** | A2: `protected_ids` em `_load_user_memories_for_context` contém apenas PROTECTED_PATHS (user.xml, preferences.xml, user_expertise.xml — `memory_injection.py:944`). Memórias com `priority='mandatory'` que entram via Tier L1 NÃO são adicionadas a `protected_ids`, portanto entram novamente via Tier 2 semântico se tiverem alta similarity. Confirmado no dump: memória do subagente system_prompt aparece em `<user_rules>` E em `<user_memories>`. |
| **Impacto** | Duplicação silenciosa de conteúdo no contexto — peso dobrado para certas regras, custo de tokens desnecessário. |
| **Correção** | Adicionar IDs de user_rules ao `protected_ids` após `_build_user_rules()` em `memory_injection.py`. |

---

### N-2 — Bug whitelist: carregando-motos-assai e consultando-venda-loja não excluídas

| Campo | Valor |
|-------|-------|
| **Evidência** | A3: `carregando-motos-assai` não está em `SKILLS_DOMINIO_ASSAI` (`skills_whitelist.py:99-104`). `consultando-venda-loja` não está em `SKILLS_DOMINIO_HORA`. Ambas chegam ao listing do agente principal por omissão. Ambas aparecem em skill_hints sugeridos de forma incoerente. |
| **Impacto** | Skills de domínio especializado (Assai, HORA) expostas ao agente principal generalista. Potencial de invocação indevida por usuários fora desses domínios. |
| **Correção** | Adicionar `carregando-motos-assai` a `SKILLS_DOMINIO_ASSAI` e `consultando-venda-loja` a `SKILLS_DOMINIO_HORA` (ou novo grupo) em `skills_whitelist.py`. |

---

### N-3 — CLAUDE.md raiz não aponta para INDEX.md completo

| Campo | Valor |
|-------|-------|
| **Evidência** | A4: A seção INDICE DO CLAUDE.md raiz é subconjunto do INDEX.md. A instrução `<knowledge_base>` no system_prompt diz "consulte o INDICE DE REFERENCIAS no CLAUDE.md" — mas o CLAUDE.md não diz "para lista completa, ver `.claude/references/INDEX.md`". O agente pode parar no índice parcial sem saber que o completo existe. |
| **Impacto** | Agente perde acesso a 7 documentos não listados no CLAUDE.md INDICE: PADROES_AVANCADOS, PIPELINE_RECEBIMENTO_LF, CONVERSAO_UOM, MAPEAMENTO_CORES, linx/INTEGRACOES, historia_nacom, RECEBIMENTO_MATERIAIS. |
| **Correção** | Adicionar linha "Para lista completa: `.claude/references/INDEX.md`" na seção INDICE do CLAUDE.md raiz. |

---

### N-4 — ROUTING_SKILLS.md tem changelog inline de 2000+ chars

| Campo | Valor |
|-------|-------|
| **Evidência** | A4-Q6: "A linha 32 do ROUTING_SKILLS.md tem um changelog inline gigantesco." Ruído de 2000+ chars para o agente que busca guidance de roteamento. |
| **Impacto** | Dilui atenção em busca de tabela de routing. O arquivo de 262 linhas tem ~8% de conteúdo que é puro changelog dev. |
| **Correção** | Mover changelog para comentário HTML `<!-- -->` ou para arquivo separado ROUTING_SKILLS_CHANGELOG.md. |

---

### N-5 — sistema prompt menciona GOTCHAS inline sem passar pela árvore

| Campo | Valor |
|-------|-------|
| **Evidência** | A4-Q3: "system_prompt menciona GOTCHAS.md diretamente inline (linhas 662 e 669) sem passar pelo caminho de descoberta" — isso cria inconsistência se o GOTCHAS.md for atualizado (o inline no prompt pode ficar stale). Há 4 pontos de entrada para o mesmo GOTCHAS.md. |
| **Impacto** | Risk de divergência entre o gotcha inline no prompt e o conteúdo atual de GOTCHAS.md. |
| **Correção** | Substituir referências inline por ponteiro curto: "Ver `.claude/references/odoo/GOTCHAS.md` para detalhes completos." |

---

### N-6 — gestor-estoque-odoo ausente do system_prompt `<subagents>` block

| Campo | Valor |
|-------|-------|
| **Evidência** | A4: system_prompt `<subagents>` block (`contexto_boot.md:828-879`) não contém `gestor-estoque-odoo`. CLAUDE.md raiz SUBAGENTES contém. Agente web opera via system_prompt principalmente — este subagente pode ser ignorado em delegações de estoque Odoo. |
| **Impacto** | Operações de estoque Odoo podem ser tratadas pelo agente principal em vez de delegadas ao especialista, aumentando risco de operação direta em PROD. |
| **Correção** | Adicionar `gestor-estoque-odoo` ao `<subagents>` block do system_prompt com delegate_when adequado. |

---

### N-7 — Flags advisory ATIVAS em produção apesar de default false

| Campo | Valor |
|-------|-------|
| **Evidência** | A3: `.env:254` tem `AGENT_SKILL_RAG=true` e `.env:256` tem `AGENT_WORLD_MODEL_INJECT=true` — ambas ativas em PROD apesar do default `false` no código. Isso significa que esses blocos bugados (skill_hints com tokens incoerentes, world_model com entidades mal classificadas) ESTÃO sendo injetados em PROD em cada turno. |
| **Impacto** | Ruído ativo em produção. R-1 do Rafael pede remoção — a evidência confirma que a remoção das env vars é ação imediata de alto impacto. |
| **Correção** | Remover `AGENT_SKILL_RAG=true` e `AGENT_WORLD_MODEL_INJECT=true` das env vars do Render. |

---

### N-8 — `_DOMAIN_SKILLS` hardcoded: preferências não refletem uso real

| Campo | Valor |
|-------|-------|
| **Evidência** | A3: `_DOMAIN_SKILLS` em `memory_injection.py:371-378` é mapeamento estático definido por design, não derivado de uso histórico. Para o domínio `admin`, lista 3 skills dev-only que têm 0-2 usos em 90 dias (A5). Para outros domínios, a correspondência pode ser correta, mas não há validação com dados de produção. |
| **Impacto** | Suggestions de roteamento desalinhadas com o que o agente realmente usa. |
| **Correção** | Derivar preferred_skills de dados reais (`agent_step.tools_used` por domínio) em vez de mapeamento estático. Curto prazo: corrigir `admin` para skills que são realmente usadas ou remover o entry `admin`. |

---

## PARTE 3 — AGRUPAMENTO EM ÁREAS DE ATUAÇÃO (para Etapa 4)

---

### AREA 1 — Limpeza imediata de ruído (quick wins, zero risco comportamental)

**Itens**: R-1, R-7 (via N-7), N-2, N-4

**Descrição**: Ações que podem ser executadas agora sem impacto funcional e sem golden dataset.

- R-1 + N-7: Remover `AGENT_SKILL_RAG=true` e `AGENT_WORLD_MODEL_INJECT=true` das env vars do Render. Zero código. Rollback instantâneo.
- N-2: Adicionar `carregando-motos-assai` e `consultando-venda-loja` à deny-list no skills_whitelist.py.
- N-4: Mover changelog inline do ROUTING_SKILLS.md.
- R-7: Corrigir `_DOMAIN_SKILLS['admin']` para não incluir skills dev-only.

**Esforço**: S (horas). **Risco**: mínimo.

---

### AREA 2 — Curadoria do listing de skills (dev-only fora, whitelist correta)

**Itens**: R-3, R-4, C6, N-2 (parcialmente em Área 1)

**Descrição**: Definir explicitamente quais skills estão disponíveis ao agente web generalista vs subagentes especializados.

- R-3: Adicionar `consultando-sentry`, `diagnosticando-banco`, `gerindo-agente`, `padronizando-docs` à deny-list.
- R-4: Avaliar unificação de lendo-arquivos ↔ lendo-documentos.
- C6: Encolher descriptions de skills para respeitar budget CLI sem truncar as cláusulas críticas.

**Esforço**: S-M. **Risco**: baixo.

---

### AREA 3 — Macro-estrutura do contexto (onde mora o quê)

**Itens**: RP-1, R-2, R-5, R-8, R-9, C1, C2, A5, N-3, N-5, N-6

**Descrição**: Definir e documentar formalmente a 3-layer architecture (já existe como plano, não totalmente implementada). Estabelecer regras claras de "o que vai em preset vs system_prompt vs CLAUDE.md vs skills vs hook".

- RP-1: Criar documento de padrão arquitetural de contexto (PAD-CTX).
- R-5: Limpar seções DEV-ONLY do CLAUDE.md raiz (3 seções identificadas).
- R-9 + N-6: Unificar lista de subagentes em fonte canônica (system_prompt) + ponteiro no CLAUDE.md.
- R-2 + C1: Eliminar redundâncias a partir da fonte canônica definida.
- R-8: Redesenhar apresentação de debug_mode/sql_admin_context para não-admins.
- N-3: Adicionar ponteiro para INDEX.md completo no CLAUDE.md.
- N-5: Substituir gotchas inline do system_prompt por ponteiros.

**Esforço**: M-L. **Risco**: médio (requer validação com golden dataset para mudanças no system_prompt).

---

### AREA 4 — Qualidade da injeção de memórias (RAG por intent + proveniência)

**Itens**: RP-2, R-6, C3, C5, A3, A6, N-1, N-8

**Descrição**: Melhorar o pipeline de seleção e injeção de memórias para ser dirigido pelo intent do turno atual, não pelo histórico global.

- C3: Remover stale_empresa + improvement_responses do boot operacional (quick win dentro desta área).
- N-1: Corrigir bug de duplicação user_rules vs user_memories (adicionar L1 IDs ao protected_ids).
- N-8: Derivar preferred_skills de dados reais.
- RP-2 + A6: Adicionar source_session_id e last_confirmed ao schema agent_memories (migration).
- C5: Implementar intent classifier por turno para filtrar Tier 2.
- R-6: Adicionar teto de tamanho por memória individual.
- A3: Destilação de "top 3 erros recorrentes" quando agent_skill_effectiveness tiver dados suficientes.

**Esforço**: M-L. **Risco**: médio-alto (mudanças de schema + comportamento de injeção precisam de R5).

---

### AREA 5 — Governança, métricas e validação

**Itens**: D1, C2, A6-agente roadmap (R5, R6, R8 do ROADMAP), M1, M2, M3, M4, M5

**Descrição**: Preservar o que funciona, fechar os gaps de validação que bloqueiam mudanças seguras.

- M1-M5: Documentar explicitamente o que não deve ser tocado e por quê (lista de "intocáveis").
- C2: Checklist R-EXEC-5 já mitiga; fortalecer a regra "não adicionar novo rótulo de prioridade sem justificativa L1-L4".
- D1: Documentar a resolução: L1 (segurança) > L4 (concisão) em operações irreversíveis.
- R5: Golden dataset 15→50+ casos — pré-requisito para validar mudanças de Área 3 e 4.
- R8 (ROADMAP): Memory injection validation — parte de Área 4.
- D3: Testar reordenação do hook com golden dataset.

**Esforço**: M (para R5 especificamente). **Risco**: alto se mudanças de Área 3/4 forem feitas sem R5.

---

### AREA 6 — Features ausentes (adicionar ao contexto de boot)

**Itens**: A1, A2, A4, D2

**Descrição**: Features novas que o agente identificou como ausentes e que têm valor potencial.

- A4: Few-shot nas skills de alta frequência (R17 do ROADMAP — skills, não system_prompt).
- A1: Painel opt-in de contagens operacionais (pedidos, rupturas, DFEs).
- A2: Estado do circuit breaker (Odoo/SSW) no boot.
- D2: Carve-out explícito para owner/debug no sistema de não-revelação.

**Esforço**: S-M por item. **Risco**: baixo para A4 (nas skills) e A2 (read-only); médio para A1 (quebra cache).

---

## PARTE 4 — TABELA DE CONFLITOS REAIS ENTRE RAFAEL E AGENTE

| Conflito | Item Rafael | Item Agente | Natureza | Resolução |
|----------|-------------|-------------|----------|-----------|
| Remoção vs A/B test | R-1 (remover agora) | C4 (A/B first) | Metodologia | Rafael tem autoridade de decisão. A remoção é reversível (env vars). |
| Quantidade de rótulos | R-5 implica simplificação | C2 (colapsar para 3) | Abordagem | A6 confirma que dial back em lote é perigoso. Solução: não adicionar novos sem L1-L4; não remover existentes em lote. |
| Few-shot localização | A4 (agente pede no boot) | PM-2.2 (bloat risco) | Localização | ROADMAP R17 decide: few-shot em skills, não no system_prompt. Rafael e STUDY concordam. |
| stale vs continuidade | R-6 remove improvement_responses | M6 protege session_summaries | Escopo | Não há conflito real — são elementos distintos. C3 remove apenas improvement_responses/stale_empresa, M6 protege session_summaries/pendencias/user_rules. |

---

## PARTE 5 — DEPENDÊNCIAS CRÍTICAS

```
RP-1 (macro-estrutura definida)
    ├── R-2 (redundância skills) — onde é canônico?
    ├── R-5 (CLAUDE.md misto) — o que vai onde?
    ├── R-9 + N-6 (subagentes) — qual é a lista canônica?
    └── C1 (redundância: qual é a fonte única?)

R5-ROADMAP (golden dataset 50+ casos)
    ├── D3 (reordenação hook) — precisa de validação
    ├── Área 3 (mudanças no system_prompt)
    └── Área 4 (mudanças no pipeline de memórias)

R-3 (remover dev-only da deny-list)
    └── N-2 (bug whitelist) — mesma operação, mesmo arquivo

N-1 (bug duplicação) — pode ser corrigido isoladamente, sem dependências

C3 (stale_empresa + improvement_responses) — pode ser corrigido isoladamente

N-7 (remover env vars advisory) — imediato, sem dependências
```

---

## APÊNDICE — TABELA RESUMIDA DE VEREDITOS

| ID | Descrição curta | Veredito | Área |
|----|----------------|----------|------|
| R-1 | Remover skill_hints e world_model | CONFIRMADO | 1 |
| R-2 | Redundância 3 lugares sobre skills | CONFIRMADO | 3 |
| R-3 | Skills dev-only no listing | CONFIRMADO | 2 |
| R-4 | Unificar lendo-arquivos/documentos | PARCIAL | 2 |
| R-5 | CLAUDE.md serve info dev ao agente | CONFIRMADO | 3 |
| R-6 | Granularidade memórias desigual | CONFIRMADO | 4 |
| R-7 | preferred_skills inclui dev-only | CONFIRMADO | 1 |
| R-8 | debug_mode/sql_admin design sub-ótimo | CONFIRMADO | 3 |
| R-9 | Subagentes duplicados e inconsistentes | CONFIRMADO | 3 |
| RP-1 | Falta macro-estrutura do contexto | CONFIRMADO | 3 |
| RP-2 | Injeção memórias sem intent + proveniência | CONFIRMADO | 4 |
| M1 | Manter `<why>` em regras | CONFIRMADO | 5 |
| M2 | Manter hierarquia constitucional L1-L4 | CONFIRMADO | 5 |
| M3 | Manter L2 grounding | CONFIRMADO | 5 |
| M4 | Manter critical_fields gotchas | CONFIRMADO | 5 |
| M5 | Manter confirmação em escrita Odoo | CONFIRMADO | 5 |
| M6 | Manter session_summaries/user_rules | CONFIRMADO | 5 |
| C1 | Comprimir redundância: fonte canônica | CONFIRMADO | 3 |
| C2 | Inflação de prioridade | PARCIAL | 5 |
| C3 | Relocar stale_empresa/improvement_responses | CONFIRMADO | 4 |
| C4 | Ablar advisory (parcialmente) | CONFIRMADO (parcial) | 1 |
| C5 | Volume de memórias: injetar por intent | CONFIRMADO | 4 |
| C6 | Descriptions de skill longas | CONFIRMADO | 2 |
| A1 | Adicionar estado vivo operacional | NAO-VERIFICAVEL-AINDA | 6 |
| A2 | Adicionar flag saúde sistemas | NAO-VERIFICAVEL-AINDA | 6 |
| A3 | Adicionar top-3 erros destilados | PARCIAL | 4 |
| A4 | Adicionar few-shot tarefas frequentes | NAO-VERIFICAVEL-AINDA | 6 |
| A5 | Unificar roteamento espalhado | CONFIRMADO | 3 |
| A6 | Adicionar frescor/confiança memórias | CONFIRMADO | 4 |
| D1 | Concisão vs segurança: decidir | DECIDIDO (L1>L4) | 5 |
| D2 | Não-revelar vs owner em debug | NAO-VERIFICAVEL-AINDA | 6 |
| D3 | Reordenação hook: aja-agora no fim | CONFIRMADO | 5 |
| N-1 | Bug duplicação user_rules vs memories | NOVO | 4 |
| N-2 | Bug whitelist 2 skills não excluídas | NOVO | 1/2 |
| N-3 | CLAUDE.md sem ponteiro para INDEX.md | NOVO | 3 |
| N-4 | Changelog inline 2000+ chars no ROUTING | NOVO | 1 |
| N-5 | GOTCHAS inline no prompt sem ponteiro | NOVO | 3 |
| N-6 | gestor-estoque-odoo ausente do system_prompt | NOVO | 3 |
| N-7 | Flags advisory ativas em PROD (env vars) | NOVO | 1 |
| N-8 | _DOMAIN_SKILLS hardcoded sem dados reais | NOVO | 1/4 |

---

*Total: 30 itens originais + 8 lacunas novas (N-1 a N-8) = 38 itens mapeados.*
*Distribuição de vereditos: CONFIRMADO=22, PARCIAL=4, NAO-VERIFICAVEL-AINDA=5, DECIDIDO=1.*
