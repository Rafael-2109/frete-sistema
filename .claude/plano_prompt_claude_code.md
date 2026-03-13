│ Plan to implement                                                                           │
│                                                                                             │
│ Plano: Otimização do Sistema de Memórias do Agente (7.5 → 9/10)                             │
│                                                                                             │
│ Contexto                                                                                    │
│                                                                                             │
│ Avaliação detalhada identificou 7 dimensões com notas de 3 a 9. O plano ataca os 5 gaps com │
│  maior ratio impacto/esforço, organizados em 4 fases independentes. Cada fase pode ser      │
│ implementada e testada isoladamente.                                                        │
│                                                                                             │
│ Meta: De 7.5 para 9/10 — priorizando utilidade real sobre sofisticação.                     │
│                                                                                             │
│ ---                                                                                         │
│ Fase 1: Quick Wins (30 min)                                                                 │
│                                                                                             │
│ Baixo esforço, impacto imediato.                                                            │
│                                                                                             │
│ 1A. Fix versão system_prompt                                                                │
│                                                                                             │
│ - Arquivo: app/agente/prompts/system_prompt.md                                              │
│ - Mudança: Linha 1 version="3.6.0" → version="3.8.0". Linha 4 <version>3.7.0</version> →    │
│ <version>3.8.0</version>. Atualizar last_updated para 2026-03-13.                           │
│                                                                                             │
│ 1B. R0 split SILENCIOSO/CONFIRME                                                            │
│                                                                                             │
│ - Arquivo: app/agente/prompts/system_prompt.md, linhas 42-62                                │
│ - Problema: 3 seções sobrepostas (triggers_to_save, role_awareness, reflection_bank)        │
│ definem quando salvar memórias com regras parcialmente contraditórias.                      │
│ - Mudança: Substituir lista de bullets + regra final por duas listas explícitas:            │
│ <triggers_confirme>                                                                         │
│   Pedido explicito ("lembre que...", "salve isso", "nunca esqueca")                         │
│ </triggers_confirme>                                                                        │
│ <triggers_silencioso>                                                                       │
│   Correcao ("na verdade..."), preferencia ("prefiro..."),                                   │
│   regra de negocio ("cliente X sempre..."), padrao repetido (2+ vezes),                     │
│   acao significativa, vocabulario operacional, identidade profissional                      │
│ </triggers_silencioso>                                                                      │
│ - Remover duplicação nos blocos role_awareness (linhas 83-98) — manter apenas os paths, não │
│  re-listar triggers.                                                                        │
│ - Remover redundância no reflection_bank (linha 121) — já coberto pela lista silencioso     │
│ acima.                                                                                      │
│                                                                                             │
│ 1C. Atualizar tipos no insights_service                                                     │
│                                                                                             │
│ - Arquivo: app/agente/services/insights_service.py, linhas 969-985                          │
│ - Problema: _compute_capdo_quality_metrics usa tipos epistemológicos antigos                │
│ (procedimental/conceitual/condicional/causal/relacional) e subdirs antigos                  │
│ (procedimentos/conceitos/regras/causas/perfis). Pós-migração v3, todas as memórias estarão  │
│ em protocolos/armadilhas/heuristicas.                                                       │
│ - Mudança: Atualizar _KNOWLEDGE_SUBDIRS para:                                               │
│ _KNOWLEDGE_SUBDIRS = {                                                                      │
│     "protocolo": "protocolos",                                                              │
│     "armadilha": "armadilhas",                                                              │
│     "heuristica": "heuristicas",                                                            │
│ }                                                                                           │
│                                                                                             │
│ ---                                                                                         │
│ Fase 2: System Prompt Condensation (~125 linhas, ~1h)                                       │
│                                                                                             │
│ Redução de 707 → ~580 linhas (18%). Foco em redundância com tool annotations e SKILL YAMLs. │
│                                                                                             │
│ 2A. Remover assinaturas de parâmetros de tools MCP (linhas 498-515)                         │
│                                                                                             │
│ - Arquivo: system_prompt.md                                                                 │
│ - Cortar: 13 linhas de browser_navigate: {"url": "..."}, browser_snapshot: {}, etc.         │
│ - Manter: 2-3 linhas de routing intent (SSW → browser_ssw_login, Atacadao →                 │
│ browser_atacadao_login)                                                                     │
│ - Economia: ~12 linhas                                                                      │
│ - Justificativa: Tool annotations já proveem assinaturas. O modelo precisa saber QUANDO     │
│ usar, não COMO invocar.                                                                     │
│                                                                                             │
│ 2B. Remover blocos <capabilities> e <usage> de subagentes (linhas 564-615)                  │
│                                                                                             │
│ - Cortar: <capabilities> de analista-carteira (564-569), especialista-odoo (585-594),       │
│ raio-x-pedido (605-615) + 3 blocos <usage> com "Use Task tool..."                           │
│ - Economia: ~30 linhas                                                                      │
│ - Justificativa: <delegate_when> já diz quando usar. <coordination_protocol> já diz como    │
│ invocar.                                                                                    │
│                                                                                             │
│ 2C. Condensar <delegation_format> (linhas 533-547)                                          │
│                                                                                             │
│ - Substituir: 15 linhas de template worked-example por 2 linhas referenciando               │
│ .claude/references/SUBAGENT_RELIABILITY.md                                                  │
│ - Economia: ~13 linhas                                                                      │
│                                                                                             │
│ 2D. Condensar <response_templates> (linhas 669-692)                                         │
│                                                                                             │
│ - Cortar: 2 worked examples com dados fictícios (VCD123, Atacadao 183)                      │
│ - Manter: <formatting> (3 linhas de emoji legend)                                           │
│ - Economia: ~14 linhas                                                                      │
│                                                                                             │
│ 2E. Condensar protocolos SSW/Atacadão em routing_strategy (linhas 392-421)                  │
│                                                                                             │
│ - ssw_routing (19 linhas → 5): Manter regra de desambiguação (perguntas → acessando-ssw,    │
│ escrita → operando-ssw, browser_ssw_login obrigatório). Remover 7-step e 5-step protocols   │
│ que estão nos SKILL.md.                                                                     │
│ - atacadao_routing (11 linhas → 3): Manter trigger rule + nota --dry-run.                   │
│ - Economia: ~17 linhas                                                                      │
│                                                                                             │
│ 2F. Condensar <role_awareness> (linhas 72-110)                                              │
│                                                                                             │
│ - Cortar: Narrativa ("sua rede de segurança", "2 vantagens", "Mesmo assim")                 │
│ - Manter: 4 categorias de aprendizado + paths                                               │
│ - De 39 → 20 linhas. Economia: ~19 linhas                                                   │
│                                                                                             │
│ 2G. Condensar <memory_utility_criteria> (linhas 125-146)                                    │
│                                                                                             │
│ - Substituir: 6 critérios com 2 linhas cada por tabela compacta                             │
│ - Economia: ~7 linhas                                                                       │
│                                                                                             │
│ 2H. Remover <commands> e <admin> duplicados em mcp_tools                                    │
│                                                                                             │
│ - render_logs <commands> → coberto por R7                                                   │
│ - sessions <commands> → coberto por R8                                                      │
│ - memory <commands> → coberto por R0                                                        │
│ - <admin> blocks em memory/sessions → cobertos por <debug_mode>                             │
│ - Economia: ~14 linhas                                                                      │
│                                                                                             │
│ Total estimado: ~126 linhas removidas → 707 - 126 = ~581 linhas                             │
│                                                                                             │
│ ---                                                                                         │
│ Fase 3: Tier 0 Acionável (~1.5h)                                                            │
│                                                                                             │
│ Maior gap qualitativo. Contexto operacional com counts sem contexto → dados acionáveis.     │
│                                                                                             │
│ 3A. Pedidos urgentes com detalhes                                                           │
│                                                                                             │
│ - Arquivo: app/agente/sdk/client.py, linhas 86-100                                          │
│ - Mudança: Substituir SELECT count(*) por query que traz top 5 com detalhes:                │
│ SELECT num_pedido,                                                                          │
│        raz_social_red,                                                                      │
│        SUM(qtd_saldo_produto_pedido * preco_produto_pedido) as valor_total,                 │
│        MIN(data_entrega_pedido) as entrega                                                  │
│ FROM carteira_principal                                                                     │
│ WHERE qtd_saldo_produto_pedido > 0                                                          │
│   AND data_entrega_pedido <= :d2                                                            │
│   AND data_entrega_pedido >= :now                                                           │
│ GROUP BY num_pedido, raz_social_red                                                         │
│ ORDER BY entrega, valor_total DESC                                                          │
│ LIMIT 5                                                                                     │
│ - Output: Mudar de <pedidos_urgentes_d2>7</pedidos_urgentes_d2> para:                       │
│ <pedidos_urgentes_d2 total="7">                                                             │
│   <pedido num="VCD2668123" cliente="ATACADAO 183" valor="R$ 45.200" entrega="14/03"/>       │
│   <pedido num="VCD2668456" cliente="ASSAI GUARULHOS" valor="R$ 22.100" entrega="14/03"/>    │
│   ...mais 3...                                                                              │
│ </pedidos_urgentes_d2>                                                                      │
│ - Limite de chars: Truncar raz_social_red em 30 chars. Cap 5 pedidos (~500 chars max vs ~40 │
│  chars antes).                                                                              │
│ - Campos verificados contra schema JSON: num_pedido (varchar50), raz_social_red             │
│ (varchar100), qtd_saldo_produto_pedido (numeric), preco_produto_pedido (numeric),           │
│ data_entrega_pedido (date).                                                                 │
│                                                                                             │
│ 3B. Separações pendentes com baseline                                                       │
│                                                                                             │
│ - Arquivo: app/agente/sdk/client.py, linhas 102-114                                         │
│ - Mudança: Adicionar cálculo de baseline (média 30 dias). Duas queries:                     │
│   a. Count atual (já existe)                                                                │
│   b. Média diária dos últimos 30 dias: SELECT AVG(daily_count) FROM (SELECT                 │
│ DATE(criado_em), count(*) as daily_count FROM separacao WHERE criado_em >= :30d_ago GROUP   │
│ BY DATE(criado_em))                                                                         │
│ - Output: Mudar de <separacoes_pendentes>1154</separacoes_pendentes> para:                  │
│ <separacoes_pendentes atual="1154" media_30d="1080" status="acima"/>                        │
│   - status: "normal" se dentro de ±15% da média, "acima" ou "abaixo" caso contrário         │
│ - Performance: Query de baseline roda contra separacao com índice em criado_em. Custo ~2ms  │
│ adicional.                                                                                  │
│                                                                                             │
│ 3C. Briefing com contexto sobre memorias empresa                                            │
│                                                                                             │
│ - Arquivo: app/agente/services/intersession_briefing.py, função _check_memory_alerts        │
│ - Mudança: Incluir user_id=0 (empresa) na checagem de conflitos. Hoje só verifica memórias  │
│ do user logado.                                                                             │
│                                                                                             │
│ ---                                                                                         │
│ Fase 4: Prompt de Extração Refatorado (~45 min)                                             │
│                                                                                             │
│ Converter negações em threshold positivo.                                                   │
│                                                                                             │
│ 4A. Refatorar exclusões                                                                     │
│                                                                                             │
│ - Arquivo: app/agente/services/pattern_analyzer.py, linhas 982-996                          │
│ - Problema: 13 linhas de exclusões puras ("NÃO extraia", "NUNCA", "IGNORE COMPLETAMENTE")   │
│ - Mudança: Substituir bloco de 15 linhas de exclusões por regra unificada de threshold:     │
│ REGRA DE QUALIDADE:                                                                         │
│ - Extraia SOMENTE se ≥2 dos 4 criterios formais forem verdadeiros E nivel >= 3              │
│ - Campo 'prescricao' eh OBRIGATORIO (minimo 10 palavras, formato imperativo)                │
│ - Se em duvida entre extrair ou omitir: OMITA                                               │
│ - Prefira 1 item de nivel 5 a 3 itens de nivel 3                                            │
│ - Retorne array vazio se nenhum item atender os criterios                                   │
│ - Manter: A exclusão de meta-discussão (linhas 990-995) — esta é defesa contra falha real   │
│ documentada. Condensar de 6 linhas para 2:                                                  │
│ IGNORE discussoes sobre o proprio sistema de IA (memorias, embeddings, hooks, prompts, SDK, │
│  modelos).                                                                                  │
│ Se a conversa eh INTEIRAMENTE sobre dev/debug do sistema, retorne array vazio.              │
│ - Resultado: De ~15 linhas de exclusões para ~8 linhas de threshold positivo + 2 linhas de  │
│ meta-defesa = 10 linhas total (-5 linhas, mas melhoria qualitativa é o ganho principal).    │
│                                                                                             │
│ ---                                                                                         │
│ Fase 5: Review Cycle Empresa (~1h)                                                          │
│                                                                                             │
│ Fechar o loop de lifecycle para memórias empresa (user_id=0).                               │
│                                                                                             │
│ 5A. Regra de recomendação para memórias stale                                               │
│                                                                                             │
│ - Arquivo: app/agente/services/recommendations_engine.py                                    │
│ - Mudança: Adicionar Regra 8 que consome capdo_quality métricas do insights_service:        │
│ # Regra 8: Memorias empresa stale                                                           │
│ noise_rate = metrics.get('capdo_quality', {}).get('noise_rate', 0)                          │
│ if noise_rate > 20:                                                                         │
│     recommendations.append({                                                                │
│         'severity': 'warning',                                                              │
│         'icon': 'fa-brain',                                                                 │
│         'title': 'Memorias empresa sem uso',                                                │
│         'description': f'{noise_rate:.0f}% das memorias empresa nao foram usadas nos        │
│ ultimos 30 dias. ...',                                                                      │
│         'metric_value': noise_rate,                                                         │
│         'threshold': 20.0,                                                                  │
│         'action': {'type': 'review_memories', 'label': 'Revisar memorias'},                 │
│     })                                                                                      │
│ - Pré-requisito: get_insights_data precisa passar capdo_quality no dict metrics que         │
│ alimenta recommendations_engine. Verificar se já inclui ou adicionar.                       │
│                                                                                             │
│ 5B. Proteger memórias empresa no consolidador                                               │
│                                                                                             │
│ - Arquivo: app/agente/services/memory_consolidator.py                                       │
│ - Problema: Não há proteção especial para user_id=0. Se maybe_consolidate(0) for chamado,   │
│ memórias empresa seriam consolidadas.                                                       │
│ - Mudança: Adicionar guard no início de maybe_consolidate() e maybe_move_to_cold():         │
│ if user_id == 0:                                                                            │
│     logger.debug("[CONSOLIDATOR] Skip empresa memories (user_id=0) — review-only")          │
│     return                                                                                  │
│ - Justificativa: Memórias empresa devem ser gerenciadas por review humano, não por          │
│ consolidação automática.                                                                    │
│                                                                                             │
│ 5C. Endpoint de review de memórias stale                                                    │
│                                                                                             │
│ - Arquivo: app/agente/services/insights_service.py                                          │
│ - Mudança: Adicionar função get_stale_empresa_memories(days=30) que retorna memórias        │
│ empresa com usage_count=0 e created_at <= 30d. Expor no dashboard admin existente.          │
│ - Nota: O dashboard admin já consome get_memory_metrics() — adicionar campo stale_memories: │
│  [{id, path, created_at, content_preview}] no retorno.                                      │
│                                                                                             │
│ ---                                                                                         │
│ Fase 6 (Opcional): Budget Logging Visível                                                   │
│                                                                                             │
│ 6A. Já existe — surfacing                                                                   │
│                                                                                             │
│ - Achado: [MEMORY_INJECT] em client.py:667-690 já loga tier0_chars, tier1_chars,            │
│ tier2_chars, tier2b_chars, total_chars, budget, budget_remaining por turno.                 │
│ - O que falta: Surfacear no dashboard. O insights_service não consome esses logs.           │
│ - Mudança sugerida (baixa prioridade): Adicionar coluna context_budget_used no              │
│ agent_sessions.data JSONB. Persistir no run_post_session_processing. Agregar no             │
│ get_insights_data.                                                                          │
│ - Decisão: Adiar para próxima iteração. O log já existe para debug pontual.                 │
│                                                                                             │
│ ---                                                                                         │
│ Arquivos Modificados (resumo)                                                               │
│                                                                                             │
│ ┌────────────┬───────────────────────────────────────────────┬───────────────────────────┐  │
│ │    Fase    │                    Arquivo                    │      Tipo de mudança      │  │
│ ├────────────┼───────────────────────────────────────────────┼───────────────────────────┤  │
│ │ 1A, 1B,    │ app/agente/prompts/system_prompt.md           │ Editar (condensar ~125    │  │
│ │ 2A-H       │                                               │ linhas)                   │  │
│ ├────────────┼───────────────────────────────────────────────┼───────────────────────────┤  │
│ │ 1C         │ app/agente/services/insights_service.py       │ Editar (tipos CAPDo)      │  │
│ ├────────────┼───────────────────────────────────────────────┼───────────────────────────┤  │
│ │ 3A, 3B     │ app/agente/sdk/client.py                      │ Editar (Tier 0 queries)   │  │
│ ├────────────┼───────────────────────────────────────────────┼───────────────────────────┤  │
│ │ 3C         │ app/agente/services/intersession_briefing.py  │ Editar (incluir empresa)  │  │
│ ├────────────┼───────────────────────────────────────────────┼───────────────────────────┤  │
│ │ 4A         │ app/agente/services/pattern_analyzer.py       │ Editar (prompt extração)  │  │
│ ├────────────┼───────────────────────────────────────────────┼───────────────────────────┤  │
│ │ 5A         │ app/agente/services/recommendations_engine.py │ Editar (regra 8)          │  │
│ ├────────────┼───────────────────────────────────────────────┼───────────────────────────┤  │
│ │ 5B         │ app/agente/services/memory_consolidator.py    │ Editar (guard empresa)    │  │
│ ├────────────┼───────────────────────────────────────────────┼───────────────────────────┤  │
│ │ 5C         │ app/agente/services/insights_service.py       │ Editar (stale memories)   │  │
│ └────────────┴───────────────────────────────────────────────┴───────────────────────────┘  │
│                                                                                             │
│ ---                                                                                         │
│ Verificação                                                                                 │
│                                                                                             │
│ Pré-deploy                                                                                  │
│                                                                                             │
│ 1. Verificar campos carteira_principal contra schema JSON (Fase 3A)                         │
│ 2. Testar query de baseline separacao localmente (Fase 3B)                                  │
│ 3. Contar linhas do system_prompt após edição — meta: ≤ 585                                 │
│                                                                                             │
│ Pós-deploy                                                                                  │
│                                                                                             │
│ 1. System prompt: Iniciar sessão no agente web, verificar que routing de skills funciona    │
│ (SSW, Atacadão, Odoo)                                                                       │
│ 2. Tier 0: Verificar via logs [MEMORY_INJECT] que o XML agora inclui nomes de pedidos       │
│ 3. Extração: Executar sessão com conversa operacional (não sobre IA), verificar que extrai  │
│ ≥1 conhecimento com <prescricao>                                                            │
│ 4. Dashboard: Acessar /agente/admin/insights, verificar que CAPDo metrics mostram tipos     │
│ corretos (protocolo/armadilha/heuristica)                                                   │
│ 5. Stale review: Verificar que o dashboard mostra memórias empresa sem uso                  │
│                                                                                             │
│ Métricas de sucesso                                                                         │
│                                                                                             │
│ - System prompt: ≤ 585 linhas (era 707)                                                     │
│ - Tier 0: XML contém num_pedido + nome_cliente + valor                                      │
│ - Extração: ≤ 10 linhas de exclusão (era 15)                                                │
│ - Dashboard CAPDo: tipos = protocolo/armadilha/heuristica (não mais epistemológicos)        │
│ - noise_rate surfaceado no recommendations_engine  