# Confiabilidade de Subagentes — Protocolo Operacional

**Ultima Atualizacao**: 25/05/2026 (notas historicas Abr/2026 + caso 2026-05-11 max_turns loader fix; contagem atualizada para 15 Nacom Goya com `gestor-estoque-odoo` adicionado em 2026-05-24, alem do `auditor-sped-ecd` adicionado em 2026-05-16)

---

## Por Que Este Documento Existe

Subagentes trabalham com ~100K tokens de contexto mas retornam um **resumo compactado** (~1-2K tokens) ao agente principal. Ratio de compressao: **10:1 a 50:1**. O principal NAO tem acesso ao trace de raciocinio, tool calls intermediarios, hipoteses descartadas ou dados brutos que geraram o resumo.

**Consequencia**: Se o subagente produzir informacao incorreta e o principal nao detectar pela propria experiencia, o erro **propaga silenciosamente**. Nao existe mecanismo automatico de validacao.

---

## Falhas Documentadas

| Tipo | Descricao | Risco |
|------|-----------|-------|
| **Fabricacao de output** | Subagente Bash gera output sem executar comandos (Issue #21585) | Debug de problema inexistente |
| **Alucinacao MCP** | Tools MCP project-scoped falham silenciosamente, resultados fabricados (Issue #13898) | Dados ficticios aceitos como reais |
| **Perda de contexto** | Apos 2-3 resumes, "correcoes" alucinadas aparecem (Issue #11712) | Dados corretos sobrescritos |
| **Alucinacao de input** | Em ~120K tokens, modelo gera `###Human:` fabricado (Issue #10628) | Instrucoes fantasma executadas |

---

## O Que Se Perde na Compressao

| Categoria | Exemplo | Impacto |
|-----------|---------|---------|
| Raciocinio intermediario | Hipoteses descartadas, becos sem saida | Principal nao sabe POR QUE |
| Dados brutos de tools | Conteudo de arquivos, outputs de grep | Impossivel cross-check |
| Sinais de confianca | Incerteza do subagente | Tudo parece igualmente certo |
| Resultados negativos | O que NAO foi encontrado | Principal assume que existe |
| Assuncoes feitas | Interpretacoes de ambiguidade | Herdadas sem saber |

---

## Protocolo de Mitigacao

### M1: File-System como Memoria Compartilhada (PRINCIPAL)

O subagente escreve findings detalhados em arquivo. O principal le o arquivo para verificacao, bypassando a compressao lossy.

**Diretorio padrao**: `/tmp/subagent-findings/`

**Formato do arquivo**:
```markdown
# Findings: {nome-agente} — {timestamp}

## Tarefa
{descricao da tarefa recebida}

## Fatos Verificados
- {afirmacao} — FONTE: {arquivo:linha} ou {modelo.campo = valor}

## Inferencias
- {conclusao deduzida} — BASEADA EM: {fatos que suportam}

## Nao Encontrado
- {item buscado mas nao achado} — BUSCADO EM: {onde procurou}

## Assuncoes
- {decisao tomada sem confirmacao explicita}

## Dados Brutos Relevantes
{outputs de scripts, trechos de arquivos — o que for crucial}
```

### M1.1: Ordem de Leitura (SDK 0.1.60+, 2026-04-17)

Com o SDK 0.1.60, o projeto ganhou `list_subagents()` + `get_subagent_messages()` — fonte canonica do transcript completo de cada subagente em `~/.claude/projects/<proj>/<session>/subagents/`. O protocolo M1 (`/tmp/subagent-findings/`) continua ativo como fallback escrito.

**Ordem recomendada** ao ler findings de um subagente:

1. **Primaria** — `app.agente.sdk.subagent_reader.get_subagent_findings(session_id, agent_type)` — le do JSONL do SDK. Completo, estruturado, sem precisar parsear markdown. Usado pelo agente web.
2. **Fallback** — `/tmp/subagent-findings/{agent_type}-{contexto}.md` — apenas se (1) retornou `None`:
   - SDK nao encontrou o subagent (agent_id invalido)
   - JSONL corrompido (ver `app/agente/CLAUDE.md:161` para risco conhecido)
   - SDK downgrade temporario

**Nao remover** a instrucao de escrita em `/tmp/` dos agents de acao — e rede de seguranca contra falhas do SDK.

**Para o Claude Code (dev) e Agente Web**: M1 (`/tmp/`) ainda e o mecanismo primario ate Fase 4 da feature #2. Quando `get_subagent_findings` ficar comprovadamente estavel em producao, podemos considerar aposentar `/tmp/` (nao feito ainda).

### M2: Prompts Estruturados com Definition of Done

Todo prompt de subagente DEVE incluir criterios de output:
- "Distinga fatos verificados de inferencias"
- "Inclua file_path:line para cada afirmacao"
- "Reporte o que NAO encontrou"
- "Marque assuncoes como [ASSUNCAO]"
- "Escreva findings detalhados em /tmp/subagent-findings/"

### M3: Subagentes Read-Only para Pesquisa

Para tarefas de **pesquisa/diagnostico**, preferir subagentes com tools read-only (Explore, Plan). Limita blast radius de output incorreto.

Para tarefas de **implementacao**, usar agentes com tools completos (general-purpose), mas o principal DEVE verificar o resultado.

### M4: Verificacao pelo Principal

Apos receber output de subagente, o principal DEVE:

1. **Checar arquivo de findings** em `/tmp/subagent-findings/` (se existir)
2. **Cross-check** afirmacoes criticas contra fontes primarias
3. **Desconfiar** de dados que nao pode verificar independentemente
4. **Nunca propagar** dados de subagente sem evidencia propria se a decisao for critica

---

## Guia para o Agente Principal

### Ao Spawnar Subagente via Task Tool

```
PROMPT TEMPLATE (adicionar ao final):

---
PROTOCOLO DE OUTPUT (OBRIGATORIO):
1. Crie /tmp/subagent-findings/ se nao existir
2. Escreva findings detalhados em /tmp/subagent-findings/{nome}-{contexto}.md
3. No resumo retornado, DISTINGA fatos de inferencias
4. REPORTE o que buscou e NAO encontrou
5. MARQUE assuncoes com [ASSUNCAO]
6. CITE fontes (arquivo:linha) para toda afirmacao
---
```

### Quando Verificar (Matriz de Risco)

| Tipo de Tarefa | Risco se Errado | Verificacao Necessaria |
|----------------|-----------------|------------------------|
| Pesquisa exploratoria | Baixo | Ler resumo, confiar |
| Diagnostico de problema | Medio | Ler findings detalhados |
| Levantamento de dados para decisao | Alto | Cross-check dados criticos |
| Implementacao de codigo | Alto | Revisar TODOS os arquivos tocados |
| Operacao no Odoo/producao | Critico | Verificar ANTES de executar |

### Sinais de Alerta no Output do Subagente

Desconfiar quando:
- Output muito "limpo" sem nuances ou incertezas
- Dados numericos suspeitamente redondos
- Afirmacoes sem citacao de fonte
- Ausencia de secao "nao encontrado"
- Resultado contradiz conhecimento previo do principal

---

## Caso 2026-05-11 — JSONL 6 linhas / turns=0: ERA bug de loader (NAO padrao normal)

**Resumo**: o D8 batch das 04:01 BRT (07:01 UTC) leu a sessao 554 (3cc9b481, "investigacao de
18 sessoes com 6 linhas/turns=0") e deduziu erroneamente que o sintoma era "padrao normal para
subagentes sem ferramentas". A causa real ja havia sido descoberta e corrigida pelo Rafael 39
minutos antes do batch (commit `8d2d28f1` em 11/05 00:52 BRT), mas o D8 nao tinha visibilidade
do commit recem-aplicado.

### Causa real

Em `app/agente/config/agent_loader.py`, o parser de frontmatter de subagentes fazia:

```python
max_turns_str = frontmatter.get("max_turns")
max_turns = int(max_turns_str) if max_turns_str and max_turns_str.strip().isdigit() else None
```

Quando o frontmatter tinha **listas YAML** (ex: `skills:` como lista), o parser caia em
`yaml.safe_load`, que retornava `max_turns: N` como **int** (nao str). A chamada `.strip()`
num int explodia `AttributeError` — capturado pelo bloco except do loader como falha de
arquivo, **descartando silenciosamente 7 agents Opus heavy** do dict de agents:

1. `gestor-recebimento`
2. `especialista-odoo`
3. `analista-carteira`
4. `auditor-financeiro`
5. `raio-x-pedido`
6. `gestor-motos-assai`
7. `desenvolvedor-integracao-odoo`

### Cascade da falha

1. Agent ausente do dict `agents={...}` em `ClaudeAgentOptions`
2. Principal chamava `Agent(subagent_type="gestor-recebimento")`
3. CLI bundled caia em **fallback filesystem** (tentava achar o agent em `.claude/agents/*.md` localmente)
4. Fallback fazia spawn parcial que **abortava em ~3s** sem produzir `assistant` message
5. Resultado: **18 SKIPs em 7 dias** com `cost granular SKIP`, `turns=0`, JSONL de 6 linhas

### Fix

Commit `8d2d28f1` (Rafael, 11/05/2026 00:52:36 -0300):

```python
max_turns_raw = frontmatter.get("max_turns")
max_turns: Optional[int] = None
if max_turns_raw is not None:
    if isinstance(max_turns_raw, int) and max_turns_raw > 0:
        max_turns = max_turns_raw
    elif isinstance(max_turns_raw, str) and max_turns_raw.strip().isdigit():
        max_turns = int(max_turns_raw)
```

Apos o fix, os 13 agents Nacom Goya da epoca (hoje 15 com `auditor-sped-ecd` adicionado em
2026-05-16 e `gestor-estoque-odoo` em 2026-05-24) carregam corretamente. **Os 18 SKIPs em 7 dias foram eliminados.**

### Licao para investigacoes futuras

- **NUNCA aceitar "padrao normal" como conclusao sem reproduzir empiricamente.** A sessao 554
  tentou reproduzir e *nao conseguiu* (gerou 7 linhas/turns=1, nao 6 linhas/turns=0); o D8
  transformou a hipotese explicativa em afirmacao categorica.
- **Quando D8 sumariza sessoes recentes, considerar commits ocorridos no intervalo** — uma
  causa pode ter sido corrigida antes da analise.
- **JSONL com 6 linhas / turns=0** NAO e por si só comportamento normal de subagente sem
  tool_use. Pode ser fallback filesystem do CLI quando agent ausente do dict. Investigar
  primeiro o loader antes de descartar.

**Referencia**: `agent_improvement_dialogue.suggestion_key='IMP-2026-05-11-002'` v3 no Render
(correcao registrada apos o usuario apontar a confusao causal).

---

## Fontes

- Anthropic Context Engineering: https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- Claude Code Sub-agents: https://code.claude.com/docs/en/sub-agents
- Fabricacao de output: https://github.com/anthropics/claude-code/issues/21585
- Alucinacao MCP: https://github.com/anthropics/claude-code/issues/13898
- Perda de contexto resume: https://github.com/anthropics/claude-code/issues/11712
- Multi-Agent Failures (arXiv:2503.13657): https://arxiv.org/pdf/2503.13657
- Error Amplification (arXiv:2512.08296): https://arxiv.org/abs/2512.08296

---

## Licoes da Revisao Abr/2026

Revisao completa dos 12 subagents de dominio realizada em 2026-04-09. Principais achados:

### Gaps Detectados e Corrigidos

| Gap | Estado Antes | Estado Depois |
|-----|--------------|---------------|
| **G1**: Pre-mortem ausente em 12/12 | Nenhum | Aplicado em 6 agents de ACAO (analista-carteira, gestor-ssw, dev-odoo, especialista-odoo, auditor-financeiro, gestor-recebimento) |
| **G2**: gestor-ssw sem protocolo de confiabilidade (ironico - maior risco) | Ausente | Adicionado |
| **G3**: Output format ausente em 4 agents | 4/12 sem | 12/12 com formato dedicado |
| **G4**: Boundary check formal ausente em 4 agents | 4/12 sem tabela | 12/12 com tabela formal |
| **G5**: Copy-paste Odoo entre 2 agents (~135 linhas) | Duplicado | Extraido para `.claude/references/odoo/AGENT_BOILERPLATE.md` |
| **G6** (REVISTO): `skills:` frontmatter como string CSV | Nao carregava (string) | Corrigido para lista YAML (carrega conteudo das skills) |
| **G9**: Self-critique loop ausente | 0/12 | Aplicado em 3 agents de decisao critica (analista-carteira, auditor-financeiro, controlador-custo-frete) |
| **G12**: gestor-carvia com protocolo simplificado | 3 bullets | 4 categorias canonicas |

### Descobertas Criticas

1. **`skills:` frontmatter E oficial e OBRIGATORIO ser LISTA YAML**: a documentacao oficial mostra formato `skills:\n  - name1\n  - name2`. Os 12 agents estavam usando `skills: name1, name2` (string CSV), o que fazia o YAML parser retornar uma string em vez de lista. Resultado: skills NAO eram carregadas no contexto do subagent pelo Claude Code CLI oficial. Corrigido em todos os 12.

2. **`agent_loader.py` local tambem tinha essa limitacao**: aceitava apenas string CSV em `_parse_skills` e `_parse_tools`. Modificado para aceitar AMBOS formatos (backwards compat) em `agent_loader.py:174-206`.

3. **`maxTurns` e campo oficial mas decidido NAO aplicar**: risco de cortar operacoes multi-turn em fluxos atomicos criticos (reconcile, POP-A10, dev Odoo). Reavaliar se agents comecarem a looping em producao.

4. **`memory:` frontmatter NAO usado** — em vez disso, **MCP memory habilitado em todos os 12 agents**:
   - Tentativa inicial com `memory: project` foi revertida (`agent_loader.py` nao extrai esse campo em producao)
   - Focus dos agents e producao (agente web), nao Claude Code CLI dev
   - Persistencia em producao usa o MCP memory server existente (`app/agente/tools/memory_mcp_tool.py`, 13 tools)
   - **Solucao aplicada**: expandidos os 12 agents com 6 tools do MCP memory no allowlist (`mcp__memory__view_memories/list_memories/save_memory/update_memory/log_system_pitfall/query_knowledge_graph`)
   - **Instrucoes de uso**: cada agent tem secao `SISTEMA DE MEMORIAS (MCP)` com paths especificos do dominio, referencia ao bloco canonico `.claude/references/AGENT_TEMPLATES.md#memory-usage`
   - **Taxonomia aplicada**: subagents salvam APENAS niveis 3-5 (diagnostico, armadilha, heuristica) em paths padronizados `/memories/empresa/{tipo}/{dominio}/`
   - **Tools NAO incluidas**: `delete_memory`, `clear_memories`, `restore_memory_version`, `view_memory_history`, `resolve_pendencia`, `register_improvement`, `search_cold_memories` (reservadas ao principal)

### Decisoes Arquiteturais

- **Templates externos** (`.claude/references/AGENT_TEMPLATES.md`) para blocos reusaveis (pre-mortem, self-critique, output format, boundary check, reliability protocol, constitutional hierarchy). Uma atualizacao propaga a todos os agents.
- **Boilerplate Odoo** (`.claude/references/odoo/AGENT_BOILERPLATE.md`) para dedup entre especialista-odoo e dev-odoo (REGRA ZERO, SCRIPTS, CONEXAO, CHECKLIST EXTRATO).
- **Pre-mortem DIFERENCIADO**: so em agents de acao. Read-only puros nao recebem (bloat sem ROI).
- **Self-critique DIFERENCIADO**: so em agents de decisao critica. Queries simples nao precisam.
- **Golden dataset offline** em `.claude/evals/subagents/` com 15 casos piloto em 3 agents (analista-carteira, auditor-financeiro, controlador-custo-frete). Runtime = Claude Code CLI, sem API direta.

### Tecnicas Avancadas Aplicadas

| Tecnica | Aplicacao |
|---------|-----------|
| Pre-mortem (Klein 1989) | 6 agents de acao, via referencia ao AGENT_TEMPLATES |
| Self-critique (Reflexion, NeurIPS 2023) | 3 agents de decisao critica |
| Constitutional AI hierarquia (L1-L4) | Documentada no template, usada pelo self-critique |
| Source citation enforcement | Reforcado no protocolo de confiabilidade (ja parcial) |
| MAST taxonomy mitigation (FM-3.2) | Via protocolo de findings + self-critique |

### Tecnicas Rejeitadas (por ROI nao provado nesta revisao)

- **ReAct/CoT XML explicito**: agents ja tem arvores de decisao implicitas. Adicionar tags XML seria bloat.
- **`maxTurns`**: risco de cortar fluxos atomicos. Reavaliar se houver looping em producao.
- **Memory system aplicado a todos**: so em 2 agents de alto beneficio (especialista-odoo, auditor-financeiro).
- **Red-teaming sistematico**: proximo passo apos eval estavel. Fora do escopo desta revisao. **Atualizacao 2026-04-12**: framework planejado em [ROADMAP_PROMPT_ENGINEERING_2026.md](ROADMAP_PROMPT_ENGINEERING_2026.md) R9 (P2, 5 dias esforco). 14 attack patterns identificados em [STUDY_PROMPT_ENGINEERING_2026.md](STUDY_PROMPT_ENGINEERING_2026.md) secao RED TEAM (RT-1 a RT-14).

### Referencias Criadas Nesta Revisao

- `.claude/references/AGENT_TEMPLATES.md` — blocos reusaveis
- `.claude/references/odoo/AGENT_BOILERPLATE.md` — boilerplate Odoo dedup
- `.claude/references/AGENT_DESIGN_GUIDE.md` — manual prescritivo
- `.claude/evals/subagents/` — framework de eval offline (3 agents piloto, 15 casos)
