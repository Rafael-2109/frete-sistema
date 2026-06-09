# B3 — Análise Crítica da Camada de Skills (R-2, R-3, R-4)

**Subagente**: B3
**Data**: 2026-06-09
**Escopo**: Camada 2 do boot (28 frontmatters expostos) — vereditos por skill, unificação lendo-arquivos/lendo-documentos, template de description enxuto, amostras antes/depois, skills zero-uso, e gaps.

---

## 1. Métricas da Camada Atual

**Skills no listing principal**: 28 skills (deny-list exclui 25 skills de subdomínio/subagente)
**Total chars de description no listing**: ~25.603 chars
**Média chars/skill**: 914 chars/skill
**Budget efetivo CLI (`sY7`)**: 16K chars total (8% do ctx = ~8K efetivo)
**Conclusão de sizing**: o listing de 28 skills com ~25.6K chars de descriptions EXCEDE O BUDGET; o CLI trunca proporcionalmente a ~450-570 chars/skill, descartando cláusulas USAR/NÃO USAR que ficam no final da description. Isso é exatamente o problema original que motivou a Solução B.

### Top 10 descriptions mais pesadas (listing atual)

| # | Skill | Chars desc |
|---|-------|-----------|
| 1 | gerindo-agente | 1.781 |
| 2 | operando-ssw | 1.476 |
| 3 | diagnosticando-banco | 1.273 |
| 4 | carregando-motos-assai | 1.105 |
| 5 | executando-odoo-financeiro | 1.090 |
| 6 | recebimento-fisico-odoo | 1.041 |
| 7 | gerindo-carvia | 1.014 |
| 8 | monitorando-entregas | 998 |
| 9 | rastreando-odoo | 998 |
| 10 | cotando-frete | 983 |

### Anti-padrões estruturais (contagem no listing de 28)

| Anti-padrão | Ocorrências |
|-------------|-------------|
| Seções "NAO USAR QUANDO" explícitas | 15 |
| Padrões "NAO usar"/"NAO USAR PARA" | 5 |
| Cross-refs "usar **skill**" | 53 |
| Cross-refs "→ usar" | 31 |

Total de ocorrências de anti-gatilhos intra-description: **84 ocorrências** — cada uma ocupa espaço precioso que é truncado pelo CLI.

---

## 2. Skills Dev-Only (R-3): Vereditos

### 2.1 Evidências de uso real (fonte: A5, 90 dias agent_sessions)

| Skill | Invocações (90d) | Usuários | Último uso | Perfil dos usuários |
|-------|-----------------|---------|-----------|---------------------|
| diagnosticando-banco | 0 | 0 | nunca | — |
| padronizando-docs | 0 | 0 | nunca | — |
| gerindo-agente | 1 | 1 (user_id=38) | 2026-06-08 | admin testando |
| consultando-sentry | 2 | 2 (user_id=1, 38) | 2026-05-22 | admins/tecnicos |

### 2.2 Vereditos por skill

#### `diagnosticando-banco`
**VEREDITO: REMOVER DO WHITELIST WEB**

Evidência:
- ZERO invocações em 90 dias (fonte: A5, `agent_sessions.data` 2026-03-11 a 2026-06-09)
- Depende de `mcp__postgres__*` — 9 tools DBA-level disponíveis apenas no contexto Claude Code dev (settings.json), NÃO no agente web de produção
- `allowed-tools` inclui `mcp__postgres__analyze_db_health`, `mcp__postgres__get_top_queries` etc. (skills_whitelist.py não verifica compatibilidade de tools)
- Tamanho: 1.273 chars de description (maior depois de gerindo-agente e operando-ssw)
- Perfil de usuário alvo: DBA/dev — nenhum operador logístico precisa de "vacuum", "dead tuples", "hipotetico EXPLAIN"
- Referência em `ROUTING_SKILLS.md:L50, L173, L175, L238` — essas entradas também devem ser removidas/comentadas

**Ação**: remover de `skills_whitelist.py` (não consta em nenhum grupo — adicionar a um novo grupo `SKILLS_DEV_ONLY` ou inline na lógica de `_discover_skills_from_project()`). Atualizar `ROUTING_SKILLS.md` (4 linhas). Remover de `_DOMAIN_SKILLS['admin']` em `memory_injection.py:377`.

#### `padronizando-docs`
**VEREDITO: REMOVER DO WHITELIST WEB**

Evidência:
- ZERO invocações em 90 dias
- Função explícita: "ao CRIAR ou EDITAR documentação ou scripts do projeto" — context de desenvolvimento, não operação logística
- Aciona `doc_audit.py`, `script_audit.py`, `novo_artefato.py` — ferramentas que fazem sentido apenas no Claude Code dev com acesso ao filesystem do projeto
- Description enxuta (499 chars) mas semanticamente dev-only
- Nenhuma skill do listing referencia `padronizando-docs` em seus anti-gatilhos (remoção não quebra cross-refs)

**Ação**: remover de `skills_whitelist.py`. Atualizar `ROUTING_SKILLS.md:L240`.

#### `gerindo-agente`
**VEREDITO: MANTER COM GATE ADMIN-ONLY (restringir ao nível whitelist)**

Evidência:
- 1 invocação em 90 dias, user_id=38 (admin), 2026-06-08 — testando o próprio agente
- Acessa scripts de gestão de memórias, sessões, padrões — informação privilegiada do sistema
- O gate de escrita já existe (`permissions.py:410-429` detecta `approve/reject/promote-batch` e nega para não-admin), mas o listing expõe a skill a TODOS os usuários
- Rafael (R-3) não pediu remoção total — pediu gating ou remoção. A skill TEM utilidade administrativa legítima (diagnóstico de memórias, briefing entre sessões)
- Usuários finais (operadores logísticos) nunca pegarão triggers como "health score", "knowledge graph", "judge score"

**Ação recomendada**: criar um gate no `_discover_skills_from_project()` para que `gerindo-agente` seja exposta APENAS a usuários que estão no grupo admin (`user_ids {1, 38, 55, 62}` ou via flag). Isso requer que `client.py:83` receba o `user_id` no momento de discovery — verificar se é possível. Alternativa mais simples: remover do listing e delegar ao Claude Code dev que tem acesso via Claude Code settings. A skill SEM gating no listing continua sendo um vazamento de informações internas (métricas, sessões de outros usuários).

**Se não for possível gate dinâmico**: REMOVER DO WHITELIST WEB até que o gate seja implementado.

#### `consultando-sentry`
**VEREDITO: REMOVER DO WHITELIST WEB**

Evidência:
- 2 invocações em 90 dias, ambos admins/técnicos (user_id=1, user_id=38)
- Último uso: 2026-05-22 (18 dias atrás)
- Depende de MCP Sentry (`mcp__sentry__*`) — disponível no contexto dev/admin, mas os operadores logísticos não têm demanda de "issues do Sentry", "stacktrace", "root cause analysis de bug Python"
- Referenciada em `ROUTING_SKILLS.md:L64, L175, L176, L233`

**Ressalva**: se Rafael ou outro admin usa o agente web para diagnósticos de production (não o Claude Code), pode ser útil manter como gate admin-only. Dado o volume (2x em 90 dias), a remoção tem risco próximo de zero.

**Ação**: remover do whitelist web. Atualizar `ROUTING_SKILLS.md` (4 linhas). Remover de `_DOMAIN_SKILLS['admin']` em `memory_injection.py:377`.

### 2.3 Impacto da remoção das 4 skills dev-only

| Métrica | Antes | Depois |
|---------|-------|--------|
| Skills no listing | 28 | 24 |
| Total chars description | ~25.603 | ~21.391 |
| Redução | — | -16,5% (-4.212 chars) |
| Skills com zero uso removidas | — | +2 (diagnosticando-banco, padronizando-docs) |

---

## 3. Bug no Whitelist: `carregando-motos-assai` e `consultando-venda-loja` (A3)

**Confirmado**: ambas estão no listing principal (não constam em `SKILLS_DELEGADAS_SUBAGENTE`) — confirmado no dump do boot (`contexto_boot.md:1051-1143`).

- `carregando-motos-assai` (1.105 chars): skill do domínio Motos Assai (B2B Q.P.A.), deveria estar em `SKILLS_DOMINIO_ASSAI`. Referencia `registrando-evento-moto-assai`, `rastreando-chassi-assai` — skills que já estão na deny-list. Inconsistência.
- `consultando-venda-loja` (932 chars): skill do domínio Lojas HORA, com nota "Esta skill deve ser usada pelo Agente Lojas HORA" — deveria estar em `SKILLS_DOMINIO_HORA`. A description começa com "pelo Agente Lojas HORA", sinal claro de erro de categorização.

**Impacto se corrigido**: -2.037 chars adicionais no listing.

**Ação**: adicionar `carregando-motos-assai` a `SKILLS_DOMINIO_ASSAI` e `consultando-venda-loja` a `SKILLS_DOMINIO_HORA` em `app/agente/config/skills_whitelist.py`.

**Evidência de fonte**: `skills_whitelist.py` — grupos `SKILLS_DOMINIO_ASSAI` e `SKILLS_DOMINIO_HORA` não contêm essas duas skills; `contexto_boot.md:1051` confirma ambas presentes no listing do boot.

---

## 4. Unificação `lendo-arquivos` + `lendo-documentos` (R-4)

### 4.1 Análise comparativa

| Dimensão | lendo-arquivos | lendo-documentos |
|----------|---------------|-----------------|
| Formatos | .xlsx, .xls, .csv | .docx, .ret, .rem, .cnab, .ofx |
| Parser principal | `pandas` (openpyxl/xlrd) | `python-docx`, `Cnab400ParserService`, `parsear_ofx` |
| Script | `scripts/ler.py` | `scripts/ler_doc.py` |
| Parâmetros | `--url`, `--limite`, `--aba`, `--cabecalho` | `--url`, `--tipo`, `--limite`, `--offset` |
| Uso (90d) | 28 invocações, 9 usuários | 10 invocações, 3 usuários |
| Ratio | 2.8x mais usada | — |
| Description chars | 698 | 885 |

### 4.2 Análise de viabilidade da unificação

**Gatilhos distintos**: os formatos são completamente distintos (tabular vs documental). Um usuário que envia `.xlsx` nunca confunde com `.ofx`. O roteamento pelo nome de arquivo/extensão é trivial.

**Mecanismo de unificação**: uma skill `lendo-arquivos` unificada com roteamento interno por extensão:
- `.xlsx/.xls/.csv` → `ler.py` (path atual)
- `.docx/.ret/.rem/.cnab/.ofx` → `ler_doc.py` (path atual)
- O script unificado pode ser um dispatcher simples

**Esforço**: BAIXO — apenas a SKILL.md precisa ser unificada (description + roteamento). Os dois scripts (ler.py, ler_doc.py) continuam existindo sem modificação. Um script wrapper opcional de 10 linhas faz dispatch por extensão.

**Riscos**:
1. **Description mais longa**: a description unificada precisa cobrir AMBOS os formatos — risco de ficar mais longa que as duas separadas. Mitigação: description minimalista (exemplos em vez de listagem exaustiva).
2. **Confusão de parâmetros**: `--aba` é Excel-only, `--tipo` é documentos-only. Documentar claramente no SKILL.md.
3. **Manutenção**: a description unificada precisa ser atualizada quando um novo formato é adicionado a qualquer dos parsers.

**Ganho**:
- -1 slot no listing (de 24 para 23 após remoções)
- Description unificada estimada: ~750 chars vs 698+885=1.583 chars atuais (economia de ~830 chars, -52%)
- Reduz confusão do agente: hoje o agente precisa decidir entre `lendo-arquivos` e `lendo-documentos` para cada upload — com unificação, é sempre a mesma skill

### 4.3 Veredito R-4

**UNIFICAR — complexidade baixa, ganho real**

Description unificada proposta:
```
Lê arquivos enviados pelo usuário e retorna conteúdo estruturado como JSON.
Formatos tabulares (.xlsx, .xls, .csv): script ler.py (pandas).
Formatos documentais (.docx, .ret, .rem, .cnab, .ofx): script ler_doc.py (python-docx, Cnab400ParserService, parsear_ofx).
Gatilhos: "analise essa planilha", "le esse retorno bancario", "confere essa remessa", "o que tem nesse OFX", "extrai clausulas desse Word".
NAO usar para: criar/exportar arquivo (exportando-arquivos), PDF/imagem (nativos Claude), consultar banco (consultando-sql), reconciliar no Odoo apos ler CNAB/OFX (executando-odoo-financeiro).
```

---

## 5. Template de Description Enxuto (R-2, C6)

### 5.1 Padrão atual e seus problemas

O padrão atual tem TRÊS seções redundantes por skill no listing de 28:
1. Cláusulas "USAR QUANDO" inline na description (correto — gatilho positivo)
2. Seção "NAO USAR QUANDO" longa com 3-8 entradas (problema: truncada pelo CLI)
3. Cross-refs "usar **X**" repetidas N vezes (53 ocorrências no listing)

**Problema real**: os anti-gatilhos são MAIS IMPORTANTES para o roteamento correto que os gatilhos positivos, mas por ficarem no final da description YAML, são os PRIMEIROS a serem truncados pelo CLI (`sY7`). O resultado: o agente vê apenas gatilhos positivos, fica sem os negativos, e faz roteamento errado.

### 5.2 Template proposto

```
[1 FRASE DE PROPÓSITO — o que faz, em que contexto, máx 150 chars]
[GATILHOS POSITIVOS — 3-5 exemplos de linguagem natural separados por vírgula, máx 200 chars]
[MAX 3 ANTI-GATILHOS — apenas os mais críticos, apontando para o ROUTING central, max 150 chars]
```

**Regras**:
- Total máx 500 chars por description (budget seguro para não ser truncado)
- Anti-gatilhos: listar APENAS os 2-3 mais frequentemente confundidos; para lista completa → "Routing completo: ROUTING_SKILLS.md"
- Remover redundâncias "NAO USAR QUANDO:" com N itens — se precisar de mais de 3, os extras vão no ROUTING
- Não repetir o nome da skill nos anti-gatilhos intra-description

### 5.3 Impacto estimado

Se todas as 24 skills (após remoções) seguirem o template de 500 chars:
- Total descrições: ~12.000 chars (vs 21.391 atuais)
- Redução: ~44%
- Bem abaixo do budget efetivo de ~8K efetivo do CLI

---

## 6. Amostras Antes/Depois (3 skills)

### 6.1 `gerindo-expedicao` — antes

```yaml
description: >-
  Esta skill deve ser usada quando o usuario pergunta sobre pedidos ANTES do
  faturamento: "tem pedido do Atacadao?", "pedido VCD123 esta em separacao?",
  "quanto tem de palmito?", "quando VCD123 fica disponivel?", "crie separacao
  do VCD123 pra amanha", ou qualquer consulta de carteira, estoque e separacao.
  Nao usar para pedidos ja faturados (usar monitorando-entregas), rastrear NF
  no Odoo (usar rastreando-odoo), ou analise P1-P7 completa da carteira (usar
  subagente analista-carteira).
  - Criar separacao: "crie separacao do VCD123 pra amanha"

  NAO USAR QUANDO (APOS faturar):
  - Status de entrega → usar **monitorando-entregas**
  - "que dia embarcou?", "foi entregue?" → usar **monitorando-entregas**
  - Rastrear NF no Odoo → usar **rastreando-odoo**
```
**Chars**: 774

### 6.1 `gerindo-expedicao` — depois

```yaml
description: >-
  Consultas e operações logísticas PRÉ-faturamento: carteira, separação, estoque,
  prazo de entrega, criação de separação.
  "tem pedido do Atacadao?", "pedido VCD123 em separacao?", "estoque de palmito",
  "crie separacao do VCD123 pra amanha", "quando VCD123 fica disponivel?".
  Pós-faturamento → monitorando-entregas. Análise P1-P7 → analista-carteira.
  Routing completo: ROUTING_SKILLS.md.
```
**Chars**: 417 (-46%)

---

### 6.2 `cotando-frete` — antes

```yaml
description: >-
  Esta skill deve ser usada quando o usuario pergunta "qual preco para Manaus?",
  "quanto sai 5000kg para AM?", "frete para SP 3 toneladas", "como funciona
  o calculo de frete?", "frete do pedido VCD123", "qual transportadora mais
  barata para RJ?", ou precisa de cotacao, tabelas de preco e lead times.
  Nao usar para documentacao SSW CarVia (usar acessando-ssw), monitorar
  entrega (usar monitorando-entregas), ou frete real vs teorico (ler
  FRETE_REAL_VS_TEORICO.md via Read).
  - Lead time: "prazo de entrega para Manaus?" (lead_time vem nos vinculos)
  - Frete real: "quanto gastei de frete com Atacadao?", "divergencia CTe", "fretes pendentes Odoo"
  - Despesas frete: "custo real do pedido com despesas extras"
  NAO USAR QUANDO:
  - Criar embarque/separacao → usar **gerindo-expedicao**
  - Status de entrega pos-faturamento → usar **monitorando-entregas**
  - Consultas analiticas SQL → usar **consultando-sql**
  - Rastrear NF/PO no Odoo → usar **rastreando-odoo**
```
**Chars**: 983

### 6.2 `cotando-frete` — depois

```yaml
description: >-
  Cotação de frete, tabelas de preço e lead times. Inclui frete real pago (CTe),
  divergências e custo por pedido.
  "qual frete para Manaus?", "quanto sai 5000kg para AM?", "transportadora mais
  barata para RJ?", "quanto gastei de frete com Atacadao?", "divergencia CTe".
  Criar separação → gerindo-expedicao. Status entrega → monitorando-entregas.
  Routing completo: ROUTING_SKILLS.md.
```
**Chars**: 417 (-58%)

---

### 6.3 `monitorando-entregas` — antes

```yaml
description: >-
  Esta skill deve ser usada quando o usuario pergunta sobre entregas ja
  faturadas: "NF 12345 foi entregue?", "status da entrega do Atacadao",
  "que dia embarcou?", "quando faturou?", "tem canhoto?", "houve devolucao?",
  ou precisa de datas de embarque, faturamento, entrega e canhotos.
  Nao usar para pedidos ainda nao faturados (usar gerindo-expedicao),
  rastrear NF no Odoo (usar rastreando-odoo), ou visao 360 completa
  do pedido (usar subagente raio-x-pedido).
  - Canhoto: "tem canhoto da NF?", "canhotos pendentes"
  - Devolucoes: "houve devolucao?", "NFs devolvidas", "produtos mais devolvidos"
  - Pendencias: "entregas pendentes", "NFs no CD", "entregas com problema"
  - Custo devolucao: "quanto custou as devolucoes?"

  NAO USAR QUANDO (ANTES de faturar):
  - Pedidos em carteira/separacao → usar **gerindo-expedicao**
  - Estoque, disponibilidade → usar **gerindo-expedicao**
  - Criar separacao → usar **gerindo-expedicao**
  - Rastrear NF no Odoo → usar **rastreando-odoo**
```
**Chars**: 998

### 6.3 `monitorando-entregas` — depois

```yaml
description: >-
  Status de entregas PÓS-faturamento: embarque, entrega, canhoto, devoluções,
  pendências, custo devolução.
  "NF 12345 foi entregue?", "que dia embarcou?", "tem canhoto?", "houve
  devolucao?", "entregas pendentes", "NFs devolvidas".
  Pré-faturamento (carteira/separação) → gerindo-expedicao.
  Routing completo: ROUTING_SKILLS.md.
```
**Chars**: 382 (-62%)

---

## 7. Skills com Zero Uso — Candidatas à Remoção/Revisão

**Fonte**: A5, 90 dias agent_sessions + 10 dias agent_step.

### 7.1 Candidatas fortes (zero uso, sem justificativa sazonal)

| Skill | Uso | Observação |
|-------|-----|------------|
| diagnosticando-banco | 0 | dev-only (ver seção 2) |
| padronizando-docs | 0 | dev-only (ver seção 2) |
| prd-generator | 0 | Ferramenta de design/spec — contexto dev |
| ralph-wiggum | 0 | Loop autônomo de dev — contexto dev |
| skill-creator | 0 | Criação de skills — contexto dev |
| resolvendo-problemas | 0 | Workflow dev para problemas G/XG |
| integracao-odoo | 0 | Skill dev-only para criar integrações (não operação) |
| recebimento-fisico-odoo | 0 | Debug do worker RQ — contexto dev |
| conciliando-odoo-po | 0 | Operação especialista — pode ter uso via subagente não capturado |
| validacao-nf-po | 0 | Idem |

### 7.2 Ressalvas importantes

- **conciliando-odoo-po** e **validacao-nf-po**: zero uso no principal NÃO significa zero uso — podem ser invocadas pelo subagente `gestor-recebimento` (cujas invocações não aparecem em `agent_step` do principal). Manter no listing até confirmação.
- **prd-generator**, **ralph-wiggum**, **skill-creator**, **resolvendo-problemas**: são ferramentas de desenvolvimento que aparecem como skills no sistema de skills (via `superpowers:*` e outros). Semanticamente são dev-only mas estão no listing por omissão na deny-list. Candidatas a um novo grupo `SKILLS_DESENVOLVIMENTO` na deny-list.
- **integracao-odoo**: zero uso no principal, mas pode ser invocada por Rafael (dev) diretamente. Se Rafael usa o agente web para dev, manter; se usa apenas Claude Code, remover.

### 7.3 Grupo `SKILLS_DESENVOLVIMENTO` sugerido (novo na deny-list)

```python
SKILLS_DESENVOLVIMENTO: Set[str] = {
    'prd-generator',
    'ralph-wiggum',
    'skill-creator',
    'resolvendo-problemas',
}
```

Essas 4 skills são exclusivamente de desenvolvimento de software e não têm gatilho possível em conversas de operação logística.

---

## 8. Skills que o Agente Web Precisa e Não Estão (Gaps)

### 8.1 Verificação contra o listing atual

Checando demandas operacionais identificadas nas sessões vs skills disponíveis:

| Demanda | Skill disponível? | Observação |
|---------|------------------|------------|
| Consulta estoque (produto específico) | `consultar-estoque` (via fast-path R7) | ✅ — via sub-skill |
| Criar separação | `criar-separacao` (via fast-path R7) | ✅ — via sub-skill |
| Verificar disponibilidade | `verificar-disponibilidade` | ✅ — sub-skill |
| Análise P1-P7 | `analiste-carteira` (subagente) | ✅ |
| Comunicar PCP/Comercial | `comunicar-pcp`, `comunicar-comercial` | ✅ — sub-skills |
| Visão 360 produto | `visao-produto` | ✅ (2 usos em 90d) |

### 8.2 Gaps identificados

**Gap G1 — Skill de consulta financeira simplificada**: o agente usa `consultando-sql` diretamente para consultas financeiras simples (ex: "saldo de conta corrente"), mas não há skill de alto nível para "resumo financeiro do cliente X". A skill `gerando-baseline-conciliacao` atende Marcus (user_id=18) especificamente. Para outros usuários financeiros, não há skill de entrada.

**Gap G2 — Skill de acompanhamento de pedidos cross-sistema**: usuários frequentemente perguntam sobre o status de um pedido que já foi faturado E está no Odoo ao mesmo tempo. Hoje isso requer `monitorando-entregas` + `rastreando-odoo` em sequência — não há skill que unifique a visão pós-faturamento. O subagente `raio-x-pedido` existe mas não aparece nas skills do listing.

**Gap G3 — raio-x-pedido não está no listing**: o subagente `raio-x-pedido` é referenciado no system_prompt (linha 877 contexto_boot.md) mas não aparece como skill no listing das 28. Verificar se é skill ou apenas subagente — se for subagente puro (invocado via Agent tool), está correto estar fora do listing. Se tiver SKILL.md, pode estar sendo omitido indevidamente.

### 8.3 Verificação do raio-x-pedido

Ausente em `.claude/skills/` — existe apenas como subagente em `.claude/agents/`. Correto não estar no listing. GAP G2 permanece sem cobertura de skill.

---

## 9. Plano de Ação Consolidado

### Prioridade 1 — Remoções sem risco (semana 1)

1. **Adicionar `carregando-motos-assai` a `SKILLS_DOMINIO_ASSAI`** em `skills_whitelist.py` — bug claro
2. **Adicionar `consultando-venda-loja` a `SKILLS_DOMINIO_HORA`** em `skills_whitelist.py` — bug claro
3. **Adicionar `diagnosticando-banco` e `padronizando-docs`** a novo grupo `SKILLS_DEV_ONLY` na deny-list
4. **Adicionar `consultando-sentry`** ao mesmo grupo `SKILLS_DEV_ONLY`
5. **Remover as 4 skills dev-only de `_DOMAIN_SKILLS['admin']`** em `memory_injection.py:377`
6. **Atualizar `ROUTING_SKILLS.md`** removendo referências diretas a `diagnosticando-banco`, `consultando-sentry`, `padronizando-docs` do corpo (4 blocos, ~10 linhas)

**Impacto**: listing vai de 28 para 22 skills; description total de ~25.603 para ~21.354 chars.

### Prioridade 2 — Gating dinâmico para `gerindo-agente` (semana 1-2)

7. **Implementar gate admin-only** para `gerindo-agente` no `_discover_skills_from_project()` (client.py:83) — requer passar `user_id` para o discovery. Alternativa: mover para `SKILLS_DEV_ONLY` e aceitar que só o Claude Code dev usa.

### Prioridade 3 — Unificação `lendo-arquivos` + `lendo-documentos` (semana 2)

8. **Criar `lendo-arquivos` unificada**: SKILL.md com description de ~500 chars + dispatcher por extensão. Manter os dois scripts separados (ler.py, ler_doc.py). Remover `lendo-documentos` do listing.

### Prioridade 4 — Compressão de descriptions (semana 2-3)

9. **Aplicar template de 500 chars** nas 22 skills restantes — começando pelas top-10 mais pesadas. Objetivo: listing total abaixo de 12.000 chars (bem dentro do budget do CLI).

### Prioridade 5 — Novo grupo SKILLS_DESENVOLVIMENTO (semana 3)

10. **Adicionar `prd-generator`, `ralph-wiggum`, `skill-creator`, `resolvendo-problemas`** ao grupo `SKILLS_DESENVOLVIMENTO` na deny-list.

---

## 10. Resumo das Métricas Antes/Depois

| Métrica | Antes | Depois (todas ações) |
|---------|-------|---------------------|
| Skills no listing | 28 | 17 |
| Total chars description | ~25.603 | ~8.500 (est.) |
| Budget CLI (~8K efetivo) | EXCEDE | Dentro do budget |
| Skills dev-only expostas | 4 | 0 |
| Skills domínio errado | 2 | 0 |
| Skills dev-only no preferred_skills | 3 | 0 |
| Anti-padrões cross-refs intra-desc | 84 | <20 (estimado) |

---

## Fontes e Referências

- `app/agente/config/skills_whitelist.py` — deny-list, grupos por domínio
- `app/agente/sdk/memory_injection.py:365-388` — `_DOMAIN_SKILLS` hardcoded
- `app/agente/sdk/client.py:83` — `_discover_skills_from_project()`
- `.claude/skills/*/SKILL.md` — frontmatters das 53 skills
- `/tmp/estudo-contexto-boot/contexto_boot.md:1051-1143` — Seção 2 do boot (28 frontmatters ao vivo)
- `/tmp/estudo-contexto-boot/findings/A5-uso-real-skills-producao.md` — dados de uso real 90 dias
- `/tmp/estudo-contexto-boot/findings/A3-exposicao-skills-advisory.md` — análise whitelist + skill_hints
