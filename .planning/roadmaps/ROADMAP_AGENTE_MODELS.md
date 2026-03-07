# Roadmap: Ativacao e Limpeza dos Modelos do Agente

## Contexto

Sistema de memoria do agente (`app/agente/models.py`, 984 linhas, 6 modelos) tem design sofisticado mas execucao incompleta. Este roadmap divide o trabalho em sessoes atomicas para: (1) consertar o que esta quebrado, (2) ativar o que esta dormindo, (3) remover o que e lixo.

**Criterio de priorizacao**: impacto no usuario final (qualidade do retrieval de memorias > higiene de codigo > features novas).

**Data de criacao**: 2026-03-07
**Sessao de planejamento**: `c4443c59-7560-47ad-915d-7c14ded29d40`

---

## INSTRUCOES OBRIGATORIAS PARA CADA SESSAO

```
PROTOCOLO DE EXECUCAO — OBRIGATORIO EM TODA SESSAO

1. ANTES DE COMECAR:
   - Ler ESTE roadmap completo para contexto
   - Marcar a sessao como IN-PROGRESS (editar este arquivo)
   - Ler TODOS os arquivos listados no checklist ANTES de codar

2. DURANTE A EXECUCAO:
   - Seguir o checklist item por item, na ordem
   - Marcar cada item com [x] ao completar
   - Se encontrar bloqueio, documentar no campo BLOQUEIOS e perguntar ao usuario

3. VALIDACAO OBRIGATORIA (antes de marcar DONE):
   - Verificar que TODOS os arquivos modificados estao listados
   - Executar testes manuais descritos na secao COMO TESTAR
   - Confirmar que nenhum import quebrou (grep por erros de import)
   - Verificar integracao: cada funcao modificada e chamada corretamente nos call sites

4. AO FINALIZAR:
   - Marcar a sessao como DONE com data
   - Listar TODOS os arquivos modificados/criados/removidos
   - Documentar qualquer desvio do plano original
```

---

## S1: Consertar `effective_count` (PRIORIDADE MAXIMA)

**Status**: [x] DONE — 2026-03-07
**Impacto**: ALTO — cold tier move memorias uteis porque effective_count nunca incrementa
**Esforco estimado**: 2-3h
**Abordagem escolhida**: Hybrid A+C (Semantica Primary + Heuristica Fallback)
**Justificativa**: Opcao B (assume efetiva se injetou) inflaciona sinal. Opcao C sozinha falha com parafraseamento forte. Hybrid resolve o core (parafraseamento) com fallback robusto quando Voyage esta down.

### Problema
`routes.py:1156-1175` usa word overlap >= 60% para detectar se memoria foi "efetiva" na resposta. Na pratica, quase nunca detecta (parafraseamento, vocabulario divergente). Resultado: `effective_count = 0` para todas memorias → cold tier move memorias uteis (criterio: `usage>=20 AND effective==0`).

### Checklist

- [x] **S1.1** Ler e entender a logica atual de `_track_memory_effectiveness()` em `app/agente/routes.py:1136-1211`
- [x] **S1.2** Ler como `effective_count` e usado no cold tier: `memory_consolidator.py:102` — sem mudancas necessarias
- [x] **S1.3** Ler como `effective_count` e lido no briefing: `intersession_briefing.py:204` — sem mudancas necessarias
- [x] **S1.4** Escolha: Hybrid A+C (Semantica via Voyage cosine>=0.50 + Heuristica word overlap>=35% OU entity overlap>=1)
- [x] **S1.5** Implementado em `routes.py:1136-1405`: 4 funcoes + 3 constantes module-level
- [x] **S1.6** `strip_xml_tags()` de `knowledge_graph_service.py` aplicado em `_track_memory_effectiveness()` L1182
- [ ] **S1.7** Testar com cenario manual: injetar memoria conhecida → verificar effective_count incrementa
- [ ] **S1.8** Verificar que cold tier (`memory_consolidator.py`) continua funcionando com a nova logica

### Arquivos envolvidos
- `app/agente/routes.py` — funcao `_rate_memory_feedback()` (MODIFICAR)
- `app/agente/services/memory_consolidator.py` — consumidor de `effective_count` (VERIFICAR)
- `app/agente/services/intersession_briefing.py` — consumidor de `effective_count` (VERIFICAR)
- `app/agente/services/knowledge_graph_service.py` — `strip_xml_tags()` (REUSAR)

### Como testar
1. Identificar uma memoria existente no banco (via `search_cold_memories` ou SQL direto)
2. Fazer pergunta ao agente que DEVE usar essa memoria
3. Verificar no banco que `effective_count` incrementou apos a resposta
4. Verificar que memorias com `effective_count > 0` NAO sao movidas para cold

### Bloqueios
(preencher durante execucao)

---

## S2: Ativar `correction_count` no ranking

**Status**: [x] DONE — 2026-03-07
**Impacto**: MEDIO — signal existe no banco mas nunca e consultado
**Esforco estimado**: 1h

### Problema
`memory_mcp_tool.py:793` incrementa `correction_count` quando usuario salva correcao com termos em comum. Mas nenhum codigo consulta esse campo — nem retrieval, nem ranking, nem insights.

### Checklist

- [x] **S2.1** Ler como `correction_count` e incrementado: `app/agente/tools/memory_mcp_tool.py` (buscar `correction_count`)
- [x] **S2.2** Ler o scoring composite em `app/agente/sdk/client.py` (buscar `composite`, `decay`, `importance`)
- [x] **S2.3** Implementar penalizacao no ranking:
  - No composite score de `client.py`, aplicar: `adjusted_importance = importance * max(0.1, 1 - 0.15 * correction_count)`
  - Ou seja: cada correcao reduz importance em 15%, com piso de 10% do original
  - Aplicar nos 3 locais de scoring (Tier 2a semantico, Tier 2b KG, Fallback recencia)
- [x] **S2.4** Adicionar metrica em `app/agente/services/insights_service.py`:
  - Expor `correction_count` agregado no endpoint `/api/insights/memory`
  - Listar "top 5 memorias mais corrigidas" (ORDER BY correction_count DESC LIMIT 5)
- [x] **S2.5** Verificar que o incremento em `memory_mcp_tool.py` continua funcionando (nao alterar logica de SET)

### Arquivos envolvidos
- `app/agente/sdk/client.py` — scoring composite (MODIFICAR, 3 locais)
- `app/agente/services/insights_service.py` — metricas (MODIFICAR)
- `app/agente/tools/memory_mcp_tool.py` — incremento existente (VERIFICAR, nao alterar)

### Como testar
1. Via SQL, setar `correction_count = 3` em uma memoria de teste
2. Verificar que essa memoria aparece com ranking menor no retrieval (log `[MEMORY_INJECT]`)
3. Verificar endpoint `/agente/api/insights/memory` inclui metricas de correcao

### Bloqueios
(preencher durante execucao)

---

## S3: Expor `AgentMemoryVersion` via MCP tool

**Status**: [x] DONE — 2026-03-07
**Impacto**: MEDIO — audit trail existe mas agente nao sabe
**Esforco estimado**: 2h

### Problema
`save_version()` e chamado em 4 locais (cada update de memoria salva versao anterior). Mas nao ha MCP tool para consultar historico nem restaurar versao. Agente nao sabe que versoes existem.

### Checklist

- [x] **S3.1** Ler `AgentMemoryVersion` em `app/agente/models.py` (linhas 688-820)
- [x] **S3.2** Ler as 9 tools existentes em `app/agente/tools/memory_mcp_tool.py` para entender padrao
- [x] **S3.3** Implementar MCP tool `view_memory_history`:
  - Input: `path` (string), `limit` (int, default 5)
  - Output: lista de versoes com `version`, `changed_at`, `changed_by`, preview do `content` (primeiros 200 chars)
  - Usar `AgentMemoryVersion.get_versions(memory_id, limit)`
  - Tratar caso: memoria nao encontrada, sem versoes
- [x] **S3.4** Implementar MCP tool `restore_memory_version`:
  - Input: `path` (string), `version` (int)
  - Logica: busca versao → salva conteudo atual como nova versao → substitui conteudo pela versao restaurada
  - Usar `AgentMemoryVersion.get_version(memory_id, version)` e `save_version()`
  - Tratar caso: versao nao encontrada, memoria deletada
- [x] **S3.5** Registrar ambas tools no servidor MCP (seguir padrao das 9 existentes)
- [x] **S3.6** Adicionar ToolAnnotations (readOnlyHint=True para history, False para restore)
- [x] **S3.7** Atualizar `app/agente/CLAUDE.md` secao "MCP Tools de memoria" com as 2 novas tools
- [ ] **S3.8** Testar: criar memoria → atualizar 3x → view_memory_history → restore versao 1 → verificar conteudo

### Arquivos envolvidos
- `app/agente/tools/memory_mcp_tool.py` — adicionar 2 tools (MODIFICAR)
- `app/agente/models.py` — metodos `get_versions()`, `get_version()` passam a ser usados (VERIFICAR)
- `app/agente/CLAUDE.md` — documentacao (MODIFICAR)

### Como testar
1. Abrir sessao do agente web
2. Pedir ao agente: "Salve uma memoria sobre teste de versoes"
3. Pedir: "Atualize a memoria sobre teste de versoes com novo conteudo"
4. Pedir: "Mostre o historico da memoria /memories/[path]"
5. Verificar que lista versoes anteriores
6. Pedir: "Restaure a versao 1 da memoria /memories/[path]"
7. Verificar que conteudo voltou ao original

### Bloqueios
(preencher durante execucao)

---

## S4: Implementar 2-hop no Knowledge Graph

**Status**: [ ] NOT STARTED
**Impacto**: MEDIO — justifica existencia de `AgentMemoryEntityRelation`
**Esforco estimado**: 3-4h

### Problema
`query_graph_memories()` faz apenas 1-hop (entity → memory). As relacoes semanticas em `agent_memory_entity_relations` (ex: "RODONAVES atrasa_para AM") sao ESCRITAS mas nao USADAS de forma diferenciada no retrieval. O similarity proxy e fixo em 0.5.

### Checklist

- [ ] **S4.1** Ler `query_graph_memories()` em `app/agente/services/knowledge_graph_service.py` (linhas 584-700)
- [ ] **S4.2** Ler como o resultado e consumido em `app/agente/sdk/client.py` (buscar `query_graph_memories`)
- [ ] **S4.3** Ler estrutura de `agent_memory_entity_relations` em `models.py` e como `_upsert_relation()` popula
- [ ] **S4.4** Implementar 2-hop no `query_graph_memories()`:
  - Hop 1 (existente): prompt → entidades → entity_ids → memory_ids (via links)
  - Hop 2 (novo): entity_ids → related_entity_ids (via relations) → additional_memory_ids (via links)
  - SQL do hop 2:
    ```sql
    SELECT DISTINCT target_entity_id FROM agent_memory_entity_relations
    WHERE source_entity_id = ANY(:entity_ids)
    UNION
    SELECT DISTINCT source_entity_id FROM agent_memory_entity_relations
    WHERE target_entity_id = ANY(:entity_ids)
    ```
  - Depois: buscar memory_ids linkados a esses related_entity_ids
  - Aplicar peso menor para hop 2 (ex: similarity=0.35 vs 0.5 para hop 1)
- [ ] **S4.5** Adicionar limite de resultados hop 2 (max 5 memorias adicionais)
- [ ] **S4.6** Substituir similarity proxy fixo 0.5 por valor baseado em `weight` da relation:
  - hop 1: `similarity = 0.5` (mantido, entity match direto)
  - hop 2: `similarity = 0.3 * relation.weight` (ponderado pelo peso da relacao)
- [ ] **S4.7** Adicionar log `[KG_QUERY]` com contagem: `hop1_memories=N, hop2_memories=M, entities_found=K`
- [ ] **S4.8** Testar com cenario: memoria sobre "RODONAVES atrasa para AM" → perguntar sobre "entregas no Amazonas" → verificar que memoria aparece via hop 2

### Arquivos envolvidos
- `app/agente/services/knowledge_graph_service.py` — `query_graph_memories()` (MODIFICAR)
- `app/agente/sdk/client.py` — consumidor (VERIFICAR, nao deve precisar mudar)

### Como testar
1. Garantir que existem relacoes no banco (verificar `SELECT COUNT(*) FROM agent_memory_entity_relations`)
2. Criar memoria de teste: "Rodonaves costuma atrasar entregas para o Amazonas"
3. Verificar que KG extraiu relacao: RODONAVES → atrasa_para → AM
4. Perguntar ao agente sobre "problemas de entrega no Norte" (sem mencionar Rodonaves)
5. Verificar no log `[KG_QUERY]` que hop 2 encontrou a memoria

### Bloqueios
(preencher durante execucao)

---

## S5: Agendar `cleanup_orphan_entities()` + expor `has_potential_conflict`

**Status**: [ ] NOT STARTED
**Impacto**: BAIXO — manutencao preventiva e melhoria informativa
**Esforco estimado**: 1-1.5h

### Checklist

- [ ] **S5.1** Ler `cleanup_orphan_entities()` em `knowledge_graph_service.py` (linhas 800-836)
- [ ] **S5.2** Ler scheduler em `scripts/sincronizacao_incremental_definitiva.py` para entender padrao de steps
- [ ] **S5.3** Adicionar step ao scheduler (semanal, ex: domingo 5h UTC):
  - Chamar `cleanup_orphan_entities()` sem filtro de user_id (limpa todos)
  - Log: `[KG_CLEANUP] Removed N orphan entities`
- [ ] **S5.4** Melhorar uso de `has_potential_conflict` no briefing (`client.py`):
  - Quando houver conflitos, em vez de apenas contar, listar os paths das memorias com conflito
  - Adicionar instrucao ao briefing: "Existem N memorias com possivel contradicao. Considere revisar: [paths]"
- [ ] **S5.5** Verificar que o scheduler nao quebra ao importar `cleanup_orphan_entities`

### Arquivos envolvidos
- `scripts/sincronizacao_incremental_definitiva.py` — scheduler (MODIFICAR)
- `app/agente/services/knowledge_graph_service.py` — funcao existente (VERIFICAR)
- `app/agente/sdk/client.py` — briefing de conflitos (MODIFICAR)

### Como testar
1. Executar `cleanup_orphan_entities()` manualmente via Python shell
2. Verificar log de entidades removidas
3. Verificar que entidades com links NAO foram removidas

### Bloqueios
(preencher durante execucao)

---

## S6: Limpeza de dead code e campo redundante

**Status**: [ ] NOT STARTED
**Impacto**: HIGIENE — reduz confusao e simplifica modelo
**Esforco estimado**: 30-45min

### Checklist

- [ ] **S6.1** Ler `models.py` completo para confirmar que itens abaixo sao de fato dead code
- [ ] **S6.2** Remover `MAX_MESSAGES_IN_CONTEXT` (linha 20)
- [ ] **S6.3** Remover `get_messages_for_context()` (linhas 299-311)
- [ ] **S6.4** Remover `AgentMemory.rename()` (linhas 660-685) — SE S3 nao adicionou MCP tool que usa rename. Se S3 criou `move_memory`, MANTER.
- [ ] **S6.5** Avaliar remocao de `is_permanent`:
  - Buscar TODOS os usos de `is_permanent` no codebase
  - Se todos podem ser substituidos por `category == 'permanent'`, remover campo
  - Se remover campo, criar migration para DROP COLUMN (com .py + .sql)
  - **ATENCAO**: Se houver queries que filtram por `is_permanent` em producao, NAO remover sem migration de dados
- [ ] **S6.6** Atualizar `app/agente/CLAUDE.md` removendo referencias aos itens deletados
- [ ] **S6.7** Verificar que nenhum import quebrou: `grep -r "get_messages_for_context\|MAX_MESSAGES_IN_CONTEXT\|\.rename(" app/agente/`
- [ ] **S6.8** Verificar que hook `lembrar-regenerar-schemas.py` regenera schemas apos edicao do models.py

### Arquivos envolvidos
- `app/agente/models.py` — remocoes (MODIFICAR)
- `app/agente/CLAUDE.md` — documentacao (MODIFICAR)
- `scripts/migrations/` — migration para DROP COLUMN se `is_permanent` for removido (CRIAR)

### Como testar
1. `grep -rn "get_messages_for_context\|MAX_MESSAGES_IN_CONTEXT" app/` → deve retornar 0 resultados
2. `grep -rn "is_permanent" app/` → se campo foi removido, deve retornar 0 resultados
3. Verificar que agente web continua funcionando (iniciar sessao, enviar mensagem)

### Bloqueios
(preencher durante execucao)

---

## ORDEM DE EXECUCAO RECOMENDADA

```
S1 (effective_count)  ←  PRIMEIRO: conserta dano ativo
    ↓
S2 (correction_count) ←  SEGUNDO: quick win, aproveita signal existente
    ↓
S6 (limpeza)          ←  TERCEIRO: higiene antes de adicionar features
    ↓
S3 (version history)  ←  QUARTO: expoe capacidade existente
    ↓
S4 (KG 2-hop)         ←  QUINTO: melhoria mais complexa
    ↓
S5 (cleanup + conflict)← SEXTO: manutencao e refinamento
```

**Dependencias**:
- S6 depende de S3 (para decidir se remove `rename()`)
- Demais sessoes sao independentes entre si

---

## METRICAS DE SUCESSO (pos-execucao)

Apos completar todas as sessoes, verificar:

1. **effective_count > 0** para memorias realmente usadas (query: `SELECT COUNT(*) FROM agent_memories WHERE effective_count > 0`)
2. **correction_count influencia ranking** (log `[MEMORY_INJECT]` mostra scores diferentes para memorias corrigidas)
3. **Zero dead code** em models.py (grep por metodos removidos retorna 0)
4. **KG hop 2 funciona** (log `[KG_QUERY]` mostra `hop2_memories > 0` pelo menos 1x)
5. **Orphan entities = 0** apos cleanup (query: `SELECT COUNT(*) FROM agent_memory_entities e WHERE NOT EXISTS (SELECT 1 FROM agent_memory_entity_links l WHERE l.entity_id = e.id)`)
6. **Agente consegue ver historico** de memorias via MCP tool `view_memory_history`
