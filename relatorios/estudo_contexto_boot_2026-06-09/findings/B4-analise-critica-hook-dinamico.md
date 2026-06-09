# B4 — Análise Crítica do Hook Dinâmico (Seção 5)
# Missão: classificação de memórias, promoção memória→código, política de orçamento,
#         proveniência, stale_empresa/improvement_responses, intersession_briefing, layout-alvo
# Data: 09/06/2026
# Endereça: R-6, RP-2, C3, C5, D3 (agente), R-6, R-8, RP-1, RP-2 (Rafael)

---

## 1. CLASSIFICAÇÃO DAS MEMÓRIAS INJETADAS (dump linhas 1827–2031)

### Metodologia
Cada item foi classificado por natureza E por pertinência ao turno concreto
("me mostre seu contexto de boot" — pedido de introspecção arquitetural).
Pertinência = HIGH se ativa no domínio do turno | LOW se irrelevante ao pedido.

---

### BLOCO 1 — `<user_rules>` (linhas 1827–1840)

| Path | Natureza | Pertinência neste turno | Observação |
|------|----------|------------------------|------------|
| `corrections/agente-afirmou-que-subagente-carrega-system-prompt-md-do-pai.xml` | REGRA DE CORREÇÃO (comportamento arquitetural) | **HIGH** — o turno É sobre arquitetura de boot; essa regra é load-bearing neste contexto exato | Formato ideal: WHEN/DO curto, acionável. BOM. |
| `corrections/usuario-corrigiu-o-agente-que-havia-assumido-que-161-9-era-f.xml` | REGRA DE CORREÇÃO (domínio financeiro/CarVia) | **LOW** — turno é sobre contexto de boot, não faturas CarVia | Correto no bloco user_rules (sempre carregada); a DUPLICATA em user_memories é o problema |

**Taxa de ruído neste bloco: 1/2 = 50%** — mas como user_rules é sempre injetado (Tier 0/L1), é aceitável. O problema é a duplicata no bloco seguinte.

---

### BLOCO 2 — `<user_memories>` (linhas 1841–1981)

#### Tier 1 — protegidas (sempre)

| Path | Natureza | Pertinência | Tamanho |
|------|----------|-------------|---------|
| `preferences.xml` | PERFIL DE PREFERÊNCIAS OPERACIONAIS | MÉDIO — saber que Rafael prefere Excel e confirmação explícita é sempre relevante, mas não especificamente para este turno | ~27 linhas |
| `user_expertise.xml` | PERFIL DE EXPERTISE TÉCNICA | LOW — expertise em embarque/frete/CarVia não é acionada num pedido de introspecção de boot | ~16 linhas + 3 linhas extraídas |
| `user.xml` | PERFIL DO USUÁRIO (resumo + contextualizações) | MÉDIO — identifica Rafael como admin técnico, contexto geral útil | ~22 linhas |

#### Tier 2 — semântico RAG (7 memórias selecionadas para este turno)

| Path | Natureza | Pertinência | Justificativa de pertinência/ruído |
|------|----------|-------------|-------------------------------------|
| `empresa/heuristicas/comercial/volume-baixo-de-eventos-reduz-confianca-em-cronicidade.xml` | HEURÍSTICA DE DOMÍNIO (análise estatística) | **LOW** — domínio comercial/filiais; nada a ver com boot | Ficou por similarity acidental (palavras "análise", "contexto" no pedido?) |
| `empresa/protocolos/expedicao/gatilho-pend-embarque-e-data_embarque-null.xml` | PROTOCOLO OPERACIONAL (filtro de separação) | **LOW** — domínio expedição; completamente irrelevante | Candidato a remoção por RAG com intent filtering |
| `corrections/usuario-corrigiu-o-agente-...161-9...xml` | REGRA DE CORREÇÃO (fatura CarVia) | **LOW** — **DUPLICATA** de user_rules; pertinência ao turno = zero | BUG: mesma memória no Tier 0 E no Tier 2 |
| `corrections/agente-afirmou-que-subagente...xml` | REGRA DE CORREÇÃO (arquitetura) | **HIGH** — relevante ao turno (mas já está em user_rules) | **DUPLICATA** — deveria estar em protected_ids |
| `empresa/heuristicas/integracao/registro-de-bug-exige-evidencia-concreta.xml` | HEURÍSTICA DE PROCESSO (registrar melhorias) | **MÉDIO** — é sobre o próprio comportamento do agente, tangencialmente relevante | Injetada via Tier 2 mas já é diretiva constitucional — triple redundância |
| `empresa/armadilhas/expedicao/ambiguidade-em-zerar-picking-exige-confirmacao.xml` | ARMADILHA TÉCNICA DETERMINÍSTICA | **LOW** — domínio estoque/picking; irrelevante neste turno | Candidato claro a RAG com intent filtering |
| `empresa/armadilhas/logistica/ibge-float-em-planilha...xml` | ARMADILHA TÉCNICA DETERMINÍSTICA (27 linhas) | **LOW** — domínio importação de tabela de frete; **completamente irrelevante** para este turno | Caso mais grave de ruído: 27 linhas vs 3 linhas de regra arquitetural de igual peso |
| `empresa/armadilhas/integracao/tmpdir-divergente-entre-agente-e-web-server.xml` | ARMADILHA TÉCNICA COM CANDIDATURA A PROMOÇÃO | **LOW** — armadilha de infraestrutura; irrelevante para pedido de introspecção | **Candidato a promoção para código** (ver Seção 2) |
| `corrections/agente-enviou-link-de-arquivo-vazio.xml` | CORREÇÃO PONTUAL EPISÓDICA | **LOW** | **Candidato a promoção para código** (ver Seção 2) |
| `empresa/armadilhas/integracao/tool-sql-reescreve-queries-complexas.xml` | ARMADILHA TÉCNICA DETERMINÍSTICA | **LOW** neste turno | Relevante quando usuário usa SQL; irrelevante aqui |

**Taxa de ruído no Tier 2 (neste turno): 8/10 = 80%**
- Das 10 memórias do Tier 2, apenas 2 têm pertinência ao turno (subagente-system-prompt e registro-de-bug)
- E ambas já estão em outros blocos (user_rules e operational_directives)
- Isso confirma empiricamente o achado C5: "injeta a maioria, não RAG por intent"

---

### BLOCOS 3–6 (continuação do hook, linhas 1982–2031)

| Bloco | Natureza | Pertinência |
|-------|----------|-------------|
| `<recent_sessions count=5>` | JANELA DE SESSÕES (continuidade) | **MÉDIO** — pendências são reais e acionáveis; relevantes para qualquer turno. |
| `<pendencias_acumuladas>` | LISTA DE AÇÃO PENDENTE | **MÉDIO-HIGH** — 3 pendências reais aguardando autorização; correto carregar. |
| `<intersession_briefing>` com `stale_empresa=33` | GOVERNANÇA DE MEMÓRIAS | **LOW** neste turno | Rafael quer falar de boot, não de manutenção de memórias; pertence ao gerindo-agente |
| `<intersession_briefing>` com `improvement_responses count=2` | LOOP DEV/AGENTE (D8) | **LOW** neste turno | Idem: informação de manutenção, não operação |
| `<operational_directives>` (6 diretivas) | DIRETIVAS DE ALTA CONFIANÇA | Misto | registro-melhorias (HIGH), NF-PO (LOW neste turno), validar-contagem (LOW), Sendas-CNPJ (LOW), TEDs (LOW), separacao-avulsa (LOW) |
| `<routing_context>` | ADVISORY | **LOW** | preferred_skills são todas dev-only; active_traps tangencialmente relevantes |
| `<debug_mode_context>` | CAPACIDADES DE DEBUG (admin) | **LOW** — relevante apenas quando Rafael quer investigar outras sessões/usuários | 8 linhas que poderiam ser 1 linha: "Debug mode ativo: target_user_id=N disponível." |
| `<sql_admin_context>` | CAPACIDADES SQL ADMIN | **LOW** — relevante apenas em operações de escrita | 11 linhas para um pedido de introspecção |
| `<skill_hints>` | ADVISORY (roteamento fraco) | **LOW** — skills sugeridas (gerando-artifact, carregando-motos-assai) são absurdas para este turno | LIXO confirmado por Rafael (R-1) |
| `<world_model>` | ADVISORY (entidades do KG) | **LOW** — ODOO como [produto] e SICOOB como [transportadora] são erros de qualidade | LIXO confirmado por Rafael (R-1) |

---

### RESUMO DE RUÍDO

| Categoria | Total injetado | Pertinente ao turno | Taxa de ruído |
|-----------|---------------|---------------------|---------------|
| user_rules (Tier 0/L1) | 2 memórias | 1 | 50% |
| Tier 1 protegidas (preferences/expertise/user.xml) | 3 memórias | 1–1.5 | ~50% |
| Tier 2 semântico | 10 memórias (2 duplicatas) | 2 (ambas duplicatas) | **80%** |
| Session window + pendências | 2 blocos | 2 | 0% — correto |
| Intersession briefing (stale+improvement) | 2 sub-blocos | 0 | **100%** |
| Operational directives (6) | 6 | 1 (registro-melhorias) | **83%** |
| advisory (routing/debug/sql/skill_hints/world_model) | 5 blocos | 0.5 (debug parcialmente) | **90%** |

**TAXA GLOBAL DE RUÍDO NESTE TURNO: ~75%** — 3/4 dos tokens do hook não contribuem para o pedido feito. Isso não é catástrofe (cache cobre custo; o problema é diluição de atenção), mas é evidência de que a injeção é por volume, não por intent.

---

## 2. PROMOÇÃO MEMÓRIA → CÓDIGO: tese Rafael (R-6)

### 2a. Caso: `tmpdir-divergente-entre-agente-e-web-server.xml`

**Conteúdo injetado** (linhas 1966–1971):
```
WHEN: O shell do agente herda um TMPDIR diferente do processo do web server
DO: Forçar TMPDIR=/tmp explicitamente antes de rodar o script de exportação
```

**Tese do Rafael**: isso deveria ser um CHECK no código, não instrução injetada.

**Avaliação com base no código real:**

O código em `app/agente/routes/_constants.py:13-19` JÁ IMPLEMENTOU a correção:
```python
# NAO usar tempfile.gettempdir(): o CLI do Claude Agent SDK seta
# TMPDIR=/tmp/claude-{uid} nos subprocessos Bash...
# AGENTE_FILES_ROOT (default /tmp) e herdado pelo CLI do ambiente do gunicorn,
# mantendo GRAVACAO e LEITURA alinhadas.
AGENTE_FILES_ROOT = os.environ.get('AGENTE_FILES_ROOT', '/tmp')
UPLOAD_FOLDER = os.path.join(AGENTE_FILES_ROOT, 'agente_files')
```

Isso significa: a armadilha `tmpdir-divergente` foi **resolvida no código** — o UPLOAD_FOLDER agora usa `AGENTE_FILES_ROOT` (default `/tmp`), e o CLI herda o mesmo env. A instrução "TMPDIR=/tmp explicitamente" ainda pode ajudar em scripts Python ad-hoc rodados via Bash, mas o caminho primário de exportação via as skills `exportando-arquivos` não precisa mais dessa instrução.

**Conclusão**: esta memória está a meio-caminho de ser promovida. A correção no código resolve 90% dos casos. O que resta é documentar no GOTCHAS do agente web que scripts Bash ad-hoc de exportação devem usar `os.path.join(os.environ.get('AGENTE_FILES_ROOT', '/tmp'), 'agente_files', session_id, filename)` — uma regra que vai para a skill `exportando-arquivos` como instrução interna, não para o hook de boot.

**Veredicto**: PROMOVER PARA SKILL + REMOVER DO HOOK.

---

### 2b. Caso: `corrections/agente-enviou-link-de-arquivo-vazio.xml`

**Conteúdo injetado** (linhas 1972–1975):
```
DO: Quando gerar arquivo para download, verificar que o arquivo existe e tem conteúdo antes de enviar o link.
```

**Verificação no código atual** (`app/agente/routes/files.py:391-396`):
```python
if not os.path.exists(file_path):
    logger.warning(f"[AGENTE] Arquivo não encontrado: {safe_filename}")
    return jsonify({'success': False, 'error': 'Arquivo não encontrado'}), 404
```

O endpoint de download JÁ verifica existência. **O que a memória instrui é que o AGENTE verifique antes de enviar o link.** Isso é um check no runtime do agente (antes de chamar `send_file`), não no servidor.

**O check determinístico possível**: o agente poderia usar a tool Bash para verificar `os.path.exists(path) and os.path.getsize(path) > 0` antes de montar o link. Mas isso exigiria 1 tool call extra por exportação.

**Alternativa mais limpa**: a skill `exportando-arquivos` (que é quem gera os links) deve ter em sua própria instrução (SKILL.md) a regra de verificar existência e tamanho > 0 antes de retornar o link. Isso é SKILL-level instruction, não hook-level injection.

**Veredicto**: PROMOVER PARA SKILL exportando-arquivos + REMOVER DO HOOK.

---

### 2c. Mecanismo de Promoção Memória → Código/Skill (proposta)

#### Critérios de promoção (quando a memória deve virar código/skill):

1. **Determinístico**: a regra é sempre verdadeira (não depende de contexto do turno). Ex: "sempre verificar existência do arquivo antes de enviar link" = determinístico.
2. **Ponto único de falha**: a falha ocorre num único lugar específico do código/skill (não é regra geral de comportamento).
3. **Check binário**: a correção pode ser verificada mecanicamente (exists? size > 0? TMPDIR == '/tmp'?).
4. **Histórico de reincidência**: a memória foi criada de uma correção de erro real que se repetiu ou que o código deveria impedir.

#### Critérios de NÃO-promoção (fica como memória):

1. **Contextual**: a regra depende do domínio do turno (ex: "fatura CarVia = emitida pela CarVia ao cliente").
2. **Comportamental**: instrui como o AGENTE deve raciocinar/comunicar, não o que o código faz.
3. **Heurística**: envolve julgamento de probabilidade (ex: "volume baixo = baixa confiança em cronicidade").

#### Fluxo de promoção via `register_improvement`:

```
[Agente detecta candidato a promoção]
    → register_improvement(
        category="skill_bug",  # ou "instruction_request" se vai para skill
        title="CHECK: verificar arquivo não-vazio antes de enviar link",
        description="Armadilha resolvível no código: ...",
        affected_files=["app/agente/routes/files.py", ".claude/skills/exportando-arquivos/SKILL.md"],
        # NUNCA prescrever a solução — isso é do Claude Code
      )
    → D8 (improvement_suggester) processa
    → Claude Code implementa verificação na skill/código
    → Memória original marcada como deprecated via `directive_status='despromovida'`
    → Remove do Tier 2 (filtered no RAG)
```

---

## 3. POLÍTICA DE INJEÇÃO COM ORÇAMENTO POR BLOCO (R-6, D3)

### Problema central

O hook atual injeta ~34KB por turno sem teto por bloco. O budget de memórias (Sonnet=6000 chars) limita apenas o Tier 2, mas os outros blocos crescem ilimitadamente.

### Política proposta

```
BUDGET TOTAL DO HOOK: ~15KB (down de ~34KB)
├── session_context (data/hora/usuário): ~0.1KB — fixo, imutável
├── user_rules (Tier 0/L1): max 3 regras × 200 chars = ~0.6KB (hoje: 2 regras OK)
├── user_memories:
│   ├── user.xml (Tier 1): max 600 chars (resumo + contextualizacao, comprimido)
│   ├── preferences.xml (Tier 1): max 400 chars (hoje ~700 chars, comprimível)
│   ├── user_expertise.xml (Tier 1): max 400 chars (hoje ~500 chars OK)
│   └── Tier 2 (RAG intent-filtered): max 4 memórias × 300 chars = ~1.2KB
│       [eliminando duplicatas e filtrando por intent do turno]
├── recent_sessions (5 resumos): ~1.2KB — manter, boa relação sinal/ruído
├── pendencias (max 5, max 100 chars/item): ~0.5KB — manter
├── intersession_briefing (CONDICIONAL):
│   ├── last_intent: ~0.1KB — manter (continuidade de tarefa)
│   ├── odoo_errors: ~0.1KB — manter se há erros
│   ├── commits_recentes: ~0.2KB — manter se há commits
│   ├── stale_empresa: MOVER para gerindo-agente (nunca no boot operacional)
│   └── improvement_responses: MOVER para gerindo-agente (nunca no boot operacional)
├── operational_directives: max 3 diretivas × 500 chars = ~1.5KB
│   [diretiva constitucional SEMPRE + 2 orgânicas de mais alta relevância por domínio]
├── routing_context (ADVISORY, CONDICIONAL):
│   ├── preferred_skills: CORRIGIR para skills reais do domínio (não dev-only)
│   ├── active_traps: max 2 armadilhas × 100 chars = ~0.2KB
│   └── SEM world_model (removido via R-1)
├── debug_mode_context (ADMIN ONLY): 1 linha: "Debug ativo: target_user_id disponível"
│   [em vez de 8 linhas de explicação]
├── sql_admin_context (ADMIN ONLY, CONDICIONAL): manter mas comprimir para ~3 linhas
│   [atualmente ~11 linhas com muita redundância)
├── skill_hints: REMOVER (R-1 Rafael)
└── world_model: REMOVER (R-1 Rafael)

TOTAL ESTIMADO: ~6-7KB (vs ~34KB atual → redução de ~80%)
```

### Sobre o "aja-agora colado ao fim" (D3)

O achado D3 do agente (efeito lost-in-the-middle) é empiricamente suportado pela literatura. A recomendação:

```
ORDENAÇÃO PROPOSTA DO HOOK:
1. session_context (identificação)       <- início: ancoragem
2. user_rules (obrigatórias)             <- logo após: regras de correção obrigatórias
3. user_memories (perfil + RAG)          <- contexto do usuário
4. operational_directives                <- "sempre fazer X"
5. intersession_briefing (eventos)       <- o que mudou desde a última sessão
6. routing_context (advisory)            <- sugestões de roteamento
7. debug_mode + sql_admin (condicional)  <- capacidades extras (admin)
8. recent_sessions                       <- janela de sessões recentes
9. pendencias_acumuladas                 <- colado ao fim = "aja-agora"

ELIMINAR: skill_hints, world_model
```

Rationale para pendencias no fim: é o item mais "ação imediata" do hook; colocá-lo colado à mensagem do usuário maximiza a probabilidade de o modelo verificar as pendências antes de responder.

---

## 4. PROVENIÊNCIA (RP-2): DESIGN CONCRETO

### Pré-condição técnica (do A2)

A tabela `agent_memories` NÃO tem `source_session_id`. O campo `origem` no `meta` JSONB (memory_format.py:35) é texto livre.

### O que Rafael quer

> "saber DE QUAL SESSÃO veio a memória. Assim, caso o agente queira entender o contexto raw, ele acessa a sessão, as mensagens relacionadas, tools, scripts etc. e consegue tirar a própria conclusão"

### Design mínimo viável (3 mudanças)

**Mudança 1 — Schema (migration):**
```sql
ALTER TABLE agent_memories
ADD COLUMN source_session_id TEXT;
-- Populado no save_memory quando existe session_id no contexto
```

**Mudança 2 — save_memory (memory_mcp_tool.py):**
No momento do save, o agente tem acesso ao session_id via ContextVar `_current_session_id` (permissions.py:46). Adicionar ao build_meta:
```python
meta['source_session_id'] = get_current_session_id()  # UUID da sessão
```

**Mudança 3 — Formato de injeção no hook:**
```xml
<!-- HOJE -->
<memory path="/memories/empresa/armadilhas/...tmpdir.xml" kind="armadilha">
[armadilha:integracao] TMPDIR divergente...
</memory>

<!-- COM PROVENIÊNCIA -->
<memory path="/memories/empresa/armadilhas/...tmpdir.xml" kind="armadilha"
        session="sess_abc123" date="05/06">
[armadilha:integracao] TMPDIR divergente...
<source>Ver sessão sess_abc123 para contexto completo</source>
</memory>
```

**Mudança 4 — Instrução no system_prompt (link de acesso):**
Adicionar ao system_prompt.md (ou numa skill de memória) a instrução:
```
Quando precisar do contexto completo de origem de uma memória:
- Use search_sessions com o session_id do atributo session=""
- Ou use list_recent_sessions e filtre pela data indicada
```

### O que DEPENDE do A2 para funcionar

- `source_session_id` no schema (migration trivial)
- popular no `save_memory` (1 linha no memory_mcp_tool.py)
- O A2 identificou que o `_current_session_id` já está disponível via ContextVar — nenhuma mudança arquitetural necessária

### Backfill de memórias existentes

Impossível retroativamente (a session_id não foi capturada). Para memórias existentes, `source_session_id = NULL`. O agente pode usar `search_sessions(query=conteúdo_da_memória)` para localizar a sessão-origem heuristicamente quando necessário.

---

## 5. stale_empresa + improvement_responses (C3): RELOCAÇÃO E RISCO

### Confirmação do problema

A linha `<stale_empresa count="33">Memorias empresa maduras sem revisao ha 60+ dias.</stale_empresa>` (contexto_boot.md:1996) e `<improvement_responses count="2" ...>` (linhas 1997–1998) estão em `intersession_briefing.py:73-87` — gerados nas chamadas de `_check_stale_empresa_memories()` e `_check_improvement_responses()`.

**Natureza correta desses blocos:**
- `stale_empresa`: alerta de manutenção (quantas memórias precisam de revisão). Útil no contexto de gerenciamento de memórias, não em tarefa operacional.
- `improvement_responses`: loop dev/agente sobre bugs/sugestões implementados pelo Claude Code. Útil APENAS quando o agente precisa avaliar se as mudanças resolveram o problema. Isso é claramente uma tarefa de `gerindo-agente`.

### Relocação proposta

**De**: `intersession_briefing.build_intersession_briefing()` (chamado em todo boot)
**Para**: `gerindo-agente` skill (acessível on-demand)

**Implementação técnica:**
```python
# intersession_briefing.py — remover seções 6 e 8:
# ANTES:
stale_alert = _check_stale_empresa_memories()  # linha 73
improvement_responses = _check_improvement_responses()  # linhas 85-87

# DEPOIS: ambas removidas do briefing automático
# As mesmas funções continuam disponíveis como endpoints via /api/agente/
# e acessíveis pela skill gerindo-agente quando o usuário quer fazer
# manutenção de memórias ou avaliar melhorias implementadas
```

### Avaliação de risco operacional

**RISCO = BAIXO.**

Argumento: `improvement_responses` continha IMP-2026-06-05-001 (bug comprovante duplicado) e IMP-2026-06-01-001 (CarVia peso_cubado). Esses itens têm `status='responded'` — o Claude Code já implementou a correção. O agente é instado a "avaliar se as mudanças resolveram". Isso NÃO é urgente o suficiente para estar em todo boot operacional. O agente pode acessar quando fizer sentido (via `gerindo-agente` ou ao tratar um bug relacionado).

`stale_empresa=33` é um número de monitoramento de saúde das memórias. Zero impacto em tarefa operacional. Sem risco de remover do boot.

**Condição de retorno**: se o agente detectar `improvement_responses` com categoria `skill_bug` ativa E o turno atual usar essa skill, ENTÃO injetar dinamicamente no hook apenas esse item específico (intent-triggered).

---

## 6. intersession_briefing, pendencias, recent_sessions: avaliação de formato/posição

### `recent_sessions` (5 resumos, linhas 1982–1993)

**Avaliação**: MANTER. É a camada mais valiosa do hook para continuidade real entre sessões. Os 5 resumos têm formato compacto (1 linha por sessão) e incluem pendências.

**Ajuste de formato**: considerar compressão do `alertas=N` para omitir quando alertas=0 (reduz ~10 chars por sessão).

### `pendencias_acumuladas` (linhas 1988–1993)

**Avaliação**: MANTER, com ajuste de posição.

**Problema atual**: estão dentro de `<recent_sessions>` — deveriam ser um bloco separado imediatamente antes da mensagem do usuário (D3: "aja-agora colado ao fim").

**Sugestão de formato:**
```xml
<!-- HOJE: dentro de <recent_sessions> -->
<pendencias_acumuladas>
  <instruction>Para cada item: 1) Verifique se já foi resolvido...</instruction>
  <item>confirmar autorização para zerar os 3 quants negativos...</item>
</pendencias_acumuladas>

<!-- PROPOSTO: bloco separado, último bloco antes do turno do usuário -->
<pending_actions priority="high" count="3">
  <!-- Verificar antes de responder: resolver ou reportar -->
  <action>Autorização para ajuste de inventário FB/Pos-Producao (3 produtos negativos)</action>
  <action>Investigar causa raiz das 5 filiais com 100% Troca NF</action>
  <action>Decisão: reimportar fatura CarVia 123-6 corrigida (R$862,61)</action>
</pending_actions>
```

**Vantagem**: (1) posição no fim maximiza atenção; (2) instrução de verificação pode ser encurtada para 1 linha de prefixo.

### `intersession_briefing` (partes que devem permanecer)

**MANTER** (conteúdo operacionalmente relevante):
- `last_intent`: contexto da última tarefa (continuidade). 1-2 linhas, alto valor.
- `odoo_errors` / `import_failures`: alertas de sistema ativo. Relevante sempre.
- `recent_commits`: mudanças de código desde a última sessão. Relevante para Rafael como dev.

**REMOVER do briefing automático**:
- `stale_empresa`: → gerindo-agente
- `improvement_responses`: → gerindo-agente (condicional por intent)
- `intelligence_report`: relevante apenas quando Rafael vai fazer revisão de saúde do agente → gerindo-agente

---

## 7. LAYOUT ALVO DO HOOK (tabela)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ HOOK UserPromptSubmit — LAYOUT ALVO                                             │
│ Budget total: ~7KB (vs ~34KB atual)                                             │
├──────┬──────────────────────────────┬──────────┬────────────┬───────────────────┤
│ Pos  │ Bloco                        │ Budget   │ Condição   │ Notas             │
├──────┼──────────────────────────────┼──────────┼────────────┼───────────────────┤
│ 1    │ <session_context>            │ ~0.1KB   │ SEMPRE     │ data/hora/usuário │
│      │ data, usuario, pessoal_access│          │            │ imutável por turno│
├──────┼──────────────────────────────┼──────────┼────────────┼───────────────────┤
│ 2    │ <user_rules>                 │ max 0.6KB│ SEMPRE     │ max 3 correções   │
│      │ (Tier 0/L1, priority=mand.)  │          │ se existir │ +fix duplicata    │
│      │                              │          │            │ (protected_ids)   │
├──────┼──────────────────────────────┼──────────┼────────────┼───────────────────┤
│ 3    │ <user_memories>              │ max 3KB  │ SEMPRE     │ Tier 1 comprimido │
│      │ - user.xml (600 chars)       │          │            │ Tier 2 intent-    │
│      │ - preferences.xml (400 chars)│          │            │ filtered, max 4   │
│      │ - user_expertise.xml (400c)  │          │            │ memórias          │
│      │ - Tier 2 RAG (4 × 300 chars) │          │            │ sem duplicatas    │
├──────┼──────────────────────────────┼──────────┼────────────┼───────────────────┤
│ 4    │ <operational_directives>     │ max 1.5KB│ SEMPRE     │ constitucional    │
│      │ - constitucional (SEMPRE)    │          │            │ + 2 orgânicas     │
│      │ - orgânicas top-2 por domínio│          │            │ por domínio atual │
├──────┼──────────────────────────────┼──────────┼────────────┼───────────────────┤
│ 5    │ <intersession_briefing>      │ max 0.5KB│ SE eventos │ só partes         │
│      │ - last_intent                │          │ relevantes │ operacionais:     │
│      │ - odoo_errors (se houver)    │          │            │ SEM stale,        │
│      │ - import_failures (se houver)│          │            │ SEM improvement,  │
│      │ - recent_commits (se houver) │          │            │ SEM intel_report  │
├──────┼──────────────────────────────┼──────────┼────────────┼───────────────────┤
│ 6    │ <routing_context>            │ max 0.3KB│ ADVISORY   │ preferred_skills  │
│      │ - user_domain                │          │            │ = skills REAIS do │
│      │ - preferred_skills (fixado)  │          │            │ domínio (não      │
│      │ - active_traps (max 2)       │          │            │ dev-only)         │
├──────┼──────────────────────────────┼──────────┼────────────┼───────────────────┤
│ 7    │ <debug_mode_context>         │ max 0.1KB│ ADMIN      │ 1 linha; em vez   │
│      │ "Debug ativo: target_user_id │          │ ONLY       │ de 8 linhas       │
│      │  disponível via tools"       │          │            │                   │
├──────┼──────────────────────────────┼──────────┼────────────┼───────────────────┤
│ 8    │ <sql_admin_context>          │ max 0.3KB│ ADMIN      │ comprimido para   │
│      │ (versão comprimida)          │          │ ONLY       │ 3 linhas de regra │
│      │                              │          │            │ (vs 11 atuais)    │
├──────┼──────────────────────────────┼──────────┼────────────┼───────────────────┤
│ 9    │ <recent_sessions count=5>    │ max 0.8KB│ SEMPRE     │ manter formato    │
│      │ (resumos compactos)          │          │            │ atual             │
├──────┼──────────────────────────────┼──────────┼────────────┼───────────────────┤
│ 10   │ <pending_actions>            │ max 0.4KB│ SE pending │ ÚLTIMO bloco      │
│      │ (pendencias ≤ 5, 1 linha/    │          │ existirem  │ "aja-agora"       │
│      │  item; sem instrução longa)  │          │            │ (D3 — colado ao   │
│      │                              │          │            │ turno do usuário) │
├──────┼──────────────────────────────┼──────────┼────────────┼───────────────────┤
│ ❌   │ skill_hints                  │ REMOVIDO │ —          │ R-1 Rafael        │
│ ❌   │ world_model                  │ REMOVIDO │ —          │ R-1 Rafael        │
│ ❌   │ stale_empresa                │ MOVIDO   │ —          │ → gerindo-agente  │
│ ❌   │ improvement_responses        │ MOVIDO   │ —          │ → gerindo-agente  │
│ ❌   │ intelligence_report          │ MOVIDO   │ —          │ → gerindo-agente  │
└──────┴──────────────────────────────┴──────────┴────────────┴───────────────────┘
```

---

## 8. ACHADOS ADICIONAIS (evidência direta do dump)

### BUG 1: Duplicata user_rules → user_memories (confirmado)

As memórias dos paths:
- `corrections/agente-afirmou-que-subagente-carrega-system-prompt-md-do-pai.xml`
- `corrections/usuario-corrigiu-o-agente-que-havia-assumido-que-161-9-era-f.xml`

Aparecem em `<user_rules>` (linhas 1830–1839) E em `<user_memories>` (linhas 1915–1924).

**Causa**: `memory_injection.py` não adiciona os IDs das user_rules ao `protected_ids` antes de iniciar o Tier 2. Correção trivial: após `_build_user_rules()`, adicionar os IDs ao `protected_ids` set.

### BUG 2: preferred_skills são todas dev-only (confirmado A3 + A5)

`routing_context:1:1450` retorna `gerindo-agente, diagnosticando-banco, consultando-sentry` para Rafael porque seu domínio computado é `admin`. As 3 skills têm uso próximo de zero em produção por usuários finais (A5 confirmou: diagnosticando-banco=0, padronizando-docs=0, gerindo-agente=1 em 90 dias). O mapeamento `_DOMAIN_SKILLS` em `memory_injection.py:371-378` é estático e precisa ser revisado.

### BUG 3: Heurística `registro-de-bug` em triple redundância

A heurística `empresa/heuristicas/integracao/registro-de-bug-exige-evidencia-concreta.xml` (linhas 1925–1929) aparece:
1. Em user_memories via Tier 2 (memória do usuário)
2. Em operational_directives como diretiva constitucional `registro-melhorias` (linhas 1999–2006)
3. No system_prompt.md (R9 da regra, hardcoded)

Três instâncias do mesmo princípio. A consolidação ideal: apenas o operational_directives constitucional (bloco 4 no layout alvo) + uma referência no system_prompt. A memória empresa pode ser mantida como registro histórico mas não deve ser injetada via Tier 2.

### OBSERVAÇÃO: debug_mode_context é verboso para uso real

O bloco `<debug_mode_context>` (linhas 2046–2053) tem 8 linhas listando capacidades detalhadas. Para Rafael (admin frequente), esse conteúdo é redundante após as primeiras sessões. Uma versão comprimida (2 linhas) seria suficiente após calibração.

---

## 9. REFERÊNCIAS DE CÓDIGO

| Ponto de toque | Arquivo | Linha |
|----------------|---------|-------|
| stale_empresa no briefing | `app/agente/services/intersession_briefing.py` | 73 |
| improvement_responses no briefing | `app/agente/services/intersession_briefing.py` | 85–87 |
| `_check_stale_empresa_memories` | `app/agente/services/intersession_briefing.py` | 384–415 |
| `_check_improvement_responses` | `app/agente/services/intersession_briefing.py` | 525–576 |
| preferred_skills hardcoded | `app/agente/sdk/memory_injection.py` | 371–378 |
| _CONSTITUTIONAL_DIRECTIVES | `app/agente/sdk/memory_injection.py` | 450–467 |
| UPLOAD_FOLDER / AGENTE_FILES_ROOT | `app/agente/routes/_constants.py` | 13–19 |
| protected_ids (bug duplicata) | `app/agente/sdk/memory_injection.py` | ~944 |
| `_build_operational_directives` | `app/agente/sdk/memory_injection.py` | 470–600+ |
| download sem check de tamanho | `app/agente/routes/files.py` | 391–396 |
| ordem dos blocos no hook | `app/agente/sdk/hooks.py` | 1471 (hardcoded) |
