# Findings B2 — Análise Crítica do CLAUDE.md Raiz como Visto pelo Agente Web

**Subagente**: B2 (missão dedicada)
**Data**: 09/06/2026
**Scope**: R-5 do Rafael — análise seção a seção, CLAUDE.md alvo, quantificação, verificação da promessa "índice completo" (INDEX.md).

---

## 0. Premissas Verificadas

### Como o CLAUDE.md chega ao agente web
Fonte: `app/agente/sdk/client.py:1573-1580`. O SDK recebe `cwd=/opt/render/project/src` e `setting_sources=["project"]`. O CLAUDE.md raiz é lido automaticamente pelo SDK Agent. O `~/.claude/CLAUDE.md` (dev-only) NÃO chega ao agente porque `setting_sources=["project"]` exclui `"user"` explicitamente. Não há como servir arquivos CLAUDE.md diferentes por superfície via SDK sem mudar o `cwd` (o que quebraria a descoberta de skills) — o design atual (raiz compartilhada + conteúdo dev em ~/.claude/CLAUDE.md) é o mecanismo correto documentado.

### MCP Render no contexto do agente web — achado crítico novo
O CLAUDE.md raiz (seção DADOS, linha 50) diz: "**FONTE PARA CONSULTA**: Utilize exclusivamente o MCP do Render, orientações em: `.claude/references/INFRAESTRUTURA.md`"

O INFRAESTRUTURA.md diz: "REGRA: DADOS DE PRODUCAO = RENDER" e instrui a usar `mcp__render__query_render_postgres`.

**Mas o agente web NÃO tem `mcp__render__query_render_postgres`.** As tools mcp__render disponíveis no boot do agente web são (`contexto_boot.md:1570-1571`):
- `mcp__render__consultar_erros` — custom tool em `render_logs_tool.py` (logs/erros)
- `mcp__render__consultar_logs` — idem
- `mcp__render__status_servicos` — idem (métricas CPU/RAM)

A tool `mcp__render__query_render_postgres` é do Render MCP SDK completo, disponível apenas no contexto do Claude Code (dev). O agente web acessa dados de produção via `mcp__sql__consultar_sql` que conecta diretamente ao banco do Render.

**Impacto**: O agente web que segue a instrução DADOS → lê INFRAESTRUTURA.md → encontra `mcp__render__query_render_postgres` → tool não existe no seu contexto → confusão ou fallback silencioso para mcp__sql.

---

## 1. Análise Seção a Seção — Veredictos

### Seção: Header (doc:meta + Contexto) — linhas 1-22

**Veredicto: FICA — pequena revisão**
- O doc:meta (linhas 1-8) é neutro — não prejudica o agente web.
- O parágrafo "Contexto" (linhas 13-17) contém uma instrução problemática: "A fonte de dados de producao e o MCP do Render" — válido para dev (que tem `query_render_postgres`), mas confuso para o agente web (que usa `mcp__sql`).
- **Ação**: reescrever para diferenciar dev (MCP Render completo) de agente web (mcp__sql para dados de negócio, mcp__render para infra).
- **Linhas removidas**: 0. Linhas revisadas: 1.

### Seção: TECH STACK — linhas 24-46 (23 linhas)

**Veredicto: MANTER COMPRIMIDO — 3 linhas dev-only removíveis**

Análise por linha:
- `Infra (Render, Oregon)`: ÚTIL ao agente web — precisa saber nomes de serviços para usar `mcp__render__*`
- `Backend (Python/Flask/SQLAlchemy)`: ÚTIL ao agente web — precisa saber que é Postgres 18 para escrever SQL correto, Flask para interpretar caminhos
- `Workers / Async (RQ)`: SEMI-ÚTIL — o agente web não interage diretamente com filas RQ, mas útil para entender "worker" quando logs aparecem
- `AI / Agente (SDK versions)`: ÚTIL ao agente web — precisa saber as versões do SDK para raciocinar sobre features disponíveis
- `Frontend (Bootstrap/HTMX/jQuery)`: DEV-ONLY — o agente web não cria templates nem escreve CSS
- `Artifacts (React/Parcel)`: DEV-ONLY — o agente web não builda artifacts
- `Mobile App (GPS/Capacitor)`: DEV-ONLY — o agente web não opera o app mobile
- `Browser Automation (Playwright)`: ÚTIL ao agente web — as skills `operando-ssw` e `operando-portal-atacadao` usam Playwright; o agente precisa saber que Playwright está disponível
- `Storage (S3)`: ÚTIL ao agente web — precisa saber que S3 existe para interpretar URLs de screenshots/anexos
- `Observability (Sentry)`: ÚTIL ao agente web — skills de diagnóstico referenciam Sentry
- `Data / Files (pandas)`: DEV-ONLY — o agente web não executa pandas; as skills encapsulam isso
- `Integracoes externas (Odoo/Teams/WhatsApp)`: ÚTIL — o agente web precisa conhecer os sistemas externos
- `Build / Deploy`: DEV-ONLY — o agente web não faz deploy

**Linhas removíveis**: Frontend (1 linha), Artifacts (1 linha), Mobile App (1 linha), Data/Files (1 linha), Build/Deploy (1 linha) = **5 linhas de tabela + manter o cabeçalho da tabela**

**Opção recomendada**: Comprimir TECH STACK para 2 seções: "Plataforma & Dados" (relevante ao agente web) e nota de rodapé "Detalhes de frontend/build/deploy: `.claude/references/INFRAESTRUTURA.md`".

**Linhas atuais**: 23. **Linhas alvo**: 15 (-8, contando header de tabela e separadores).

### Seção: DADOS — linhas 47-54 (8 linhas)

**Veredicto: REESCREVER — contexto incorreto para agente web**

Problema: "Utilize exclusivamente o MCP do Render" é a instrução correta para o Claude Code (que tem `mcp__render__query_render_postgres`), mas induz confusão no agente web (que usa `mcp__sql`).

A seção TAMBÉM está presente nas REGRAS UNIVERSAIS (regra 2, linha 59), criando dupla instrução que o agente web lê duas vezes com informação incorreta em ambas.

**Reescrita proposta** (3 linhas):
```
### OBRIGATÓRIO
1. **DADOS NEGÓCIO** (pedidos, fretes, clientes): `mcp__sql__consultar_sql` — banco de produção.
2. **DADOS INFRA** (logs, deploys, métricas): `mcp__render__consultar_logs/erros/status` — detalhes em `.claude/references/INFRAESTRUTURA.md`.
3. **CROSS-VERIFICACAO ODOO**: inconsistências → seguir `.claude/references/odoo/ROUTING_ODOO.md`.
```

**Linhas atuais**: 8. **Linhas alvo**: 5 (-3).

### Seção: REGRAS UNIVERSAIS — linhas 55-63 (9 linhas)

**Veredicto: MANTER COM 1 REMOÇÃO**

- Regra 1 "AMBIENTE VIRTUAL: `source .venv/bin/activate`": **DEV-ONLY pura** — no Render não existe `.venv`, o agente web nunca executa esse comando. **Remover**.
- Regra 2 "FONTE DE DADOS/DADOS DE PRODUÇÃO": útil ao agente web, mas instrui a ler INFRAESTRUTURA.md (que contém `query_render_postgres` ausente no agente web). Após a reescrita de DADOS acima, esta regra pode simplesmente dizer: "dados de negócio = `mcp__sql`, infra = `mcp__render__*`" — sem apontar para INFRAESTRUTURA.md separadamente (já está em DADOS).
- Regra 3 "TIMEZONE": ÚTIL ao agente web — quando o agente interpreta datas ou cria queries com filtros temporais.

**Linhas removidas**: 1 (regra 1 + formatação). **Linhas revisadas**: 1 (regra 2 simplificada para evitar referência cruzada confusa).

**Linhas atuais**: 9. **Linhas alvo**: 7 (-2).

### Seção: FORMATACAO NUMERICA BRASILEIRA — linhas 64-75 (12 linhas)

**Veredicto: MOVER PARA `~/.claude/CLAUDE.md` — DEV-ONLY 100%**

O agente web não cria templates Jinja2. O escopo do agente web é "cannot_do: modificar código-fonte" (confirmado em `system_prompt.md:71`). Os filtros `valor_br` e `numero_br` são exclusivos para templates HTML — não há situação em que o agente web precise de `{{ valor|valor_br }}`.

**Evidência**: `contexto_boot.md:1647-1657` — a seção aparece íntegra no boot do agente web sem nenhuma utilidade operacional.

**Ação**: Mover para `~/.claude/CLAUDE.md` (já tem "FORMATAÇÃO" nas referências dev-only segundo a nota do dev).

**Linhas removidas do CLAUDE.md raiz**: 12.

### Seção: MODELOS CRITICOS — linhas 76-92 (17 linhas)

**Veredicto: FICA COM 2 LINHAS REMOVIDAS**

- `**Campos de tabelas**: SEMPRE usar schemas...`: ÚTIL ao agente web — orienta a buscar schemas via `mcp__buscar_tabelas` + `mcp__schema__consultar_schema`
- `**ANTES de usar CarteiraPrincipal/Separacao**`: ÚTIL ao agente web — é um gotcha operacional crítico
- `**ANTES de usar Embarque/Faturamento/etc.**`: ÚTIL ao agente web
- `**ANTES de executar qualquer skill ou operacao Odoo**`: ÚTIL ao agente web
- `**ANTES de criar/editar doc ou script**: LER ARQUITETURA_DE_ARTEFATOS.md (padrao PAD-A) ou usar skill padronizando-docs.` — **DEV-ONLY** — o agente web não cria docs ou scripts de produção. Confirma R-5 do Rafael.
- Gotchas `qtd_saldo_produto_pedido` / `qtd_saldo`: CRÍTICO ao agente web

**Linhas removidas**: 1 linha (ARQUITETURA_DE_ARTEFATOS.md/PAD-A).

**Linhas atuais**: 17. **Linhas alvo**: 16 (-1).

### Seção: INDICE DE REFERENCIAS — linhas 93-166 (74 linhas)

**Veredicto: MANTER COM 2 MUDANÇAS ESTRUTURAIS**

Esta seção é a mais valorizada por Rafael ("muito bom"). É o principal mecanismo de descoberta progressiva do agente web.

**Mudança 1 — Subseção Design System (linhas 150-165, ~16 linhas): MOVER PARA `~/.claude/CLAUDE.md`**
Conteúdo: `ui_audit.py`, pre-commit hooks, visual regression, lint policy. 100% DEV-ONLY — o agente web nunca roda `python scripts/audits/ui_audit.py`, nunca instala hooks, nunca faz visual regression. A skill `frontend-design` existe mas é ativada pelo Claude Code, não pelo agente web logístico.
**Linhas removidas**: 16 (cabeçalho + 9 entradas da tabela + separador). Manter apenas ponteiro: `| Design System (badges, tokens, CSS) | `.claude/references/design/GUIA_COMPONENTES_UI.md` |` (1 linha em vez de 16).

**Mudança 2 — Ponteiro para INDEX.md precisa de reposicionamento**
Situação atual: "| Índice completo | `.claude/references/INDEX.md` |" (linha 147) aparece dentro da subseção "Infraestrutura e Agente". O Rafael identificou corretamente (R-5): o INDEX.md é o inventário GERAL de todas as referências, não tem relação com "Infraestrutura e Agente".

Confusão adicional: a instrução `<knowledge_base>` no system_prompt diz "consulte o ÍNDICE DE REFERENCIAS no CLAUDE.md" — o agente pode parar no índice parcial do CLAUDE.md em vez de ir ao INDEX.md completo.

**Ação**: Mover "Índice completo → INDEX.md" para o CABEÇALHO da seção INDICE DE REFERENCIAS (antes das subseções), como chamada de atenção:
```
> **Índice completo** (364 arquivos em `.claude/references/`): `.claude/references/INDEX.md`
> Este índice é um subconjunto rápido dos documentos mais acessados.
```

**Saldo líquido da seção INDICE**: -15 linhas (16 do Design System - 1 nova linha de ponteiro consolidado).

**Linhas atuais**: 74. **Linhas alvo**: 61 (-13, considerando reorganização + compressão Design System).

### Seção: CAMINHOS DO SISTEMA — linhas 167-195 (29 linhas)

**Veredicto: MANTER COM 1 REMOÇÃO — valor marginal ao agente web mas defensável**

O agente web usa `Read` para acessar arquivos de módulos (ex: `Read("app/carvia/CLAUDE.md")`). Os caminhos são necessários para saber onde os CLAUDE.md de módulo estão.

Linha DEV-ONLY identificada:
- `| **NAO ESTENDER** | app/carteira/main_routes.py...` (linha 190): instrução de código puro, zero utilidade ao agente web.

**Linhas removidas**: 1.

O aviso "Para lista completa de módulos e rotas: `.claude/references/INDEX.md`" (linha 192) é correto — manter.

**Linhas atuais**: 29. **Linhas alvo**: 28 (-1).

### Seção: SUBAGENTES — linhas 196-231 (36 linhas)

**Veredicto: MANTER COM 3 CORREÇÕES**

**Correção 1 — Remover `desenvolvedor-integracao-odoo`**
A entrada diz "(dev-only, nao exposto ao agente web)" — se é dev-only, não deve estar na lista do CLAUDE.md raiz (que o agente web lê). Deve ir para `~/.claude/CLAUDE.md`.
**Linhas removidas**: 1.

**Correção 2 — Adicionar `gestor-estoque-odoo` ao `system_prompt.md`**
O `gestor-estoque-odoo` está no CLAUDE.md (linha 211) mas AUSENTE do `<subagents>` block do `system_prompt.md` (linhas 673-722 do boot). O agente web opera principalmente via system_prompt — se o subagente não está lá, o agente pode não delegar operações de estoque Odoo corretamente.
**Esta correção é no `system_prompt.md`, não no CLAUDE.md**. No CLAUDE.md, a entrada pode ficar — mas a descrição atual tem 1139 chars em 1 linha (detalhando G021/G022/G027/G031, versões de skills, etc.). Isso é conteúdo de ROADMAP.md, não de índice de subagentes.

**Correção 3 — Comprimir descrição de `gestor-estoque-odoo`**
Descrição atual: 1139 chars numa linha (G021/G022/G027/G031, `transferindo-interno-odoo` modos, etc.). Isso é conteúdo de `app/odoo/estoque/CLAUDE.md` e `ROADMAP_SKILLS.md` — não de um índice de navegação.
Descrição alvo (1 linha): `| gestor-estoque-odoo | Operações WRITE estoque Odoo (ajuste, transferência, reserva, picking, MO, faturamento). Ver app/odoo/estoque/CLAUDE.md |`

**Seção "Confiabilidade de Output"** (linhas 215-231):
- 3 linhas de dev-only: `AGENT_DESIGN_GUIDE.md`, `AGENT_TEMPLATES.md`, `AGENT_BOILERPLATE.md` são para criar/editar subagentes (Claude Code, não agente web). Manter apenas `SUBAGENT_RELIABILITY.md` e o protocolo operacional (passos 1-4 + sinais de alerta).
- **Linhas removidas**: 3 (as 3 refs dev-only na subseção Confiabilidade).

**Saldo da seção SUBAGENTES**:
- Remover `desenvolvedor-integracao-odoo`: -1 linha
- Comprimir `gestor-estoque-odoo` de 1 linha longa para 1 linha curta: net 0 linhas, mas -~900 chars
- Remover 3 refs dev-only em Confiabilidade: -3 linhas
**Linhas atuais**: 36. **Linhas alvo**: 32 (-4).

---

## 2. Verificação da Promessa "Índice Completo" (INDEX.md) — R-5

### Situação atual

O CLAUDE.md tem na linha 147: `| Indice completo | .claude/references/INDEX.md |` dentro da subseção "Infraestrutura e Agente" do INDICE.

O INDEX.md real tem 364 arquivos rastreados em `.claude/references/`. O subconjunto no CLAUDE.md cobre os mais acessados — a omissão de 7 documentos (PADROES_AVANCADOS, PIPELINE_RECEBIMENTO_LF, CONVERSAO_UOM, MAPEAMENTO_CORES, linx/INTEGRACOES, historia_nacom, RECEBIMENTO_MATERIAIS) é intencional e correta para o índice de navegação rápida.

### Problema identificado (R-5 confirmado)

1. **Categorização incorreta**: "Índice completo" está sob "Infraestrutura e Agente" — semânticamente errado. O INDEX.md é o inventário geral de TODAS as referências, não especificamente de infraestrutura.

2. **Ausência de meta-instrução**: A `<knowledge_base>` no system_prompt diz "consulte o ÍNDICE DE REFERENCIAS no CLAUDE.md" — o agente segue esse ponteiro e encontra o índice parcial do CLAUDE.md. O CLAUDE.md não diz "este é um subconjunto — para a lista completa veja INDEX.md". O agente pode assumir que o que vê no CLAUDE.md é o inventário completo.

3. **"Completo significa completo"** (Rafael R-5): a entrada rotulada como "Índice completo" está aninhada dentro de "Infraestrutura e Agente" — o rótulo "completo" dentro de uma subseção de infraestrutura cria confusão semântica.

### Correção proposta

Adicionar no topo da seção "INDICE DE REFERENCIAS" (antes de qualquer subseção):

```markdown
## INDICE DE REFERENCIAS

> **Índice completo** (todas as 364 referências): `.claude/references/INDEX.md`
> Este índice é a seleção dos documentos mais acessados por contexto. Para descoberta de
> documentos não listados aqui, leia `.claude/references/INDEX.md` diretamente.
> 
> Entradas dev-only (CSS, Best Practices, MCP Capabilities, CLAUDE.md de módulo) estão em `~/.claude/CLAUDE.md`.
```

E remover a linha `| Indice completo | .claude/references/INDEX.md |` da tabela "Infraestrutura e Agente".

---

## 3. CLAUDE.md Alvo — Estrutura Proposta

### Opção recomendada: arquivo único compartilhado (manter design atual)

Razão: não é tecnicamente possível servir arquivos CLAUDE.md diferentes por superfície via Agent SDK sem mudar `cwd` (o que quebraria a descoberta de skills). O design atual (CLAUDE.md raiz compartilhado + conteúdo dev em `~/.claude/CLAUDE.md`) é o padrão correto e documentado.

**Trade-off aceito**: algumas linhas genuinamente dev-only permanecerão visíveis ao agente web (estimado ~2-3 linhas residuais nas seções compartilhadas). O custo de fragmentar o arquivo supera o benefício.

### Estrutura de seções do CLAUDE.md alvo

```
<!-- doc:meta ... -->

# Sistema de Fretes — Referencia Compartilhada
> Papel, instrução sobre ~/.claude/CLAUDE.md, atualizado

## Contexto
[Reescrever para clarificar: agente web usa mcp__sql para dados de negócio, não mcp__render__query_render_postgres]

## TECH STACK (comprimido: ~15 linhas, -8)
[Manter: Infra, Backend, Workers, AI/Agente, Browser Automation, Storage, Observabilidade, Integrações externas]
[Remover: Frontend detalhado, Artifacts dev, Mobile App, Data/Files libs, Build/Deploy]

## DADOS (reescrito: ~5 linhas, -3)
[Clarificar: mcp__sql = dados negócio; mcp__render__* = infra; cross-verificação Odoo]

## REGRAS UNIVERSAIS (~7 linhas, -2)
[Remover regra 1 dev-only (source .venv)]

## MODELOS CRITICOS (~16 linhas, -1)
[Remover linha ARQUITETURA_DE_ARTEFATOS.md/PAD-A]

## INDICE DE REFERENCIAS (~61 linhas, -13)
> [NOVO] Índice completo (INDEX.md) no TOPO da seção, como nota de rodapé proeminente
[Seções: Modelos e Regras de Negócio, Odoo, SSW e CarVia, Infraestrutura e Agente]
[REMOVER: Subseção Design System (16 linhas) → substituir por 1 linha de ponteiro]

## CAMINHOS DO SISTEMA (~28 linhas, -1)
[Remover: "NAO ESTENDER app/carteira/main_routes.py" — dev-only]

## SUBAGENTES (~32 linhas, -4)
[Remover: desenvolvedor-integracao-odoo (dev-only)]
[Comprimir: gestor-estoque-odoo de 1139 chars para ~120 chars]
[Remover: 3 refs dev-only em Confiabilidade (AGENT_DESIGN_GUIDE, AGENT_TEMPLATES, AGENT_BOILERPLATE)]
```

---

## 4. Quantificação

### Resumo de mudanças

| Seção | Linhas atuais | Linhas alvo | Delta | Motivo |
|-------|:---:|:---:|:---:|---|
| Header + Contexto | 22 | 22 | 0 | Manter (1 linha revisada, sem corte) |
| TECH STACK | 23 | 15 | -8 | Remover 5 linhas dev-only de tabela |
| DADOS | 8 | 5 | -3 | Reescrever para clarificar mcp__sql vs mcp__render |
| REGRAS UNIVERSAIS | 9 | 7 | -2 | Remover rule 1 dev-only + simplificar rule 2 |
| FORMATACAO NUMERICA | 12 | 0 | -12 | Mover para ~/.claude/CLAUDE.md (100% dev-only) |
| MODELOS CRITICOS | 17 | 16 | -1 | Remover ARQUITETURA_DE_ARTEFATOS (dev-only) |
| INDICE DE REFERENCIAS | 74 | 61 | -13 | Remover Design System (16 linhas), adicionar ponteiro INDEX.md no topo (1-2 linhas), reposicionar "Índice completo" |
| CAMINHOS DO SISTEMA | 29 | 28 | -1 | Remover "NAO ESTENDER" (dev-only) |
| SUBAGENTES | 36 | 32 | -4 | Remover desenvolvedor-integracao-odoo, comprimir gestor-estoque-odoo, remover 3 refs dev-only |
| **TOTAL** | **231** | **186** | **-45** | |

**Redução**: 45 linhas (-19%), de 231 para ~186 linhas.
**Chars removidos** adicionalmente: ~1100 chars da linha de gestor-estoque-odoo (sem impacto na contagem de linhas).
**Conteúdo que o agente web PERDE**: zero conteúdo operacional. Tudo removido é dev-only ou incorreto para o contexto do agente web.

### O que o agente web perde — análise de segurança por item

| Item removido | O que o agente web perde | Seguro? |
|---|---|---|
| `source .venv/bin/activate` | Nada — o agente web nunca executa isso | SIM |
| Filtros Jinja2 `valor_br` | Nada — o agente web não cria templates | SIM |
| Design System (16 linhas) | Nada — o agente web não modifica CSS/templates | SIM |
| `ARQUITETURA_DE_ARTEFATOS.md` instrução | Nada — o agente web não cria docs/scripts PAD-A | SIM |
| `NAO ESTENDER main_routes.py` | Nada — o agente web não escreve código | SIM |
| `desenvolvedor-integracao-odoo` | Perde referência a subagente dev-only (intencional) | SIM |
| 3 refs dev em Confiabilidade | Perde AGENT_DESIGN_GUIDE/TEMPLATES/BOILERPLATE — usados para criar subagentes (Claude Code) | SIM — o agente web não cria subagentes |
| Mobile App, Build/Deploy linhas de TECH STACK | Perde info sobre Capacitor e build.sh — não operacional para o agente web | SIM |

---

## 5. Correções Adicionais Identificadas (além do escopo de linhas)

### C1 — DADOS seção com instrução incorreta para agente web
**Arquivo**: `CLAUDE.md` linhas 47-54  
**Problema**: "Utilize exclusivamente o MCP do Render" + ponteiro para INFRAESTRUTURA.md que instrui `mcp__render__query_render_postgres` — tool ausente no contexto do agente web.  
**Correção**: reescrever DADOS para distinguir mcp__sql (dados negócio) vs mcp__render (infra).

### C2 — SUBAGENTES: gestor-estoque-odoo ausente do system_prompt.md
**Arquivo**: `app/agente/prompts/system_prompt.md` (linhas 673-722 do boot)  
**Problema**: 12 subagentes no `<subagents>` block; `gestor-estoque-odoo` está no CLAUDE.md mas não no system_prompt — o agente web pode não delegá-lo corretamente.  
**Correção**: adicionar entrada em `system_prompt.md` `<subagents>` block.

### C3 — Contexto header menciona "MCP do Render" sem disambiguação
**Arquivo**: `CLAUDE.md` linha 15  
**Problema**: "A fonte de dados de producao e o MCP do Render" é correto para dev mas confuso para agente web (que usa mcp__sql para dados de negócio).  
**Correção**: "Para dados de negócio: `mcp__sql`. Para infra/logs/deploys: `mcp__render__*`. Detalhes: `.claude/references/INFRAESTRUTURA.md`."

### C4 — INDEX.md categorizado sob "Infraestrutura e Agente"
**Arquivo**: `CLAUDE.md` linha 147  
**Problema**: "Índice completo" está categorizado em subseção errada; a instrução `<knowledge_base>` aponta para o CLAUDE.md sem mencionar que é subconjunto.  
**Correção**: mover ponteiro INDEX.md para o topo da seção INDICE DE REFERENCIAS como nota proeminente.

---

## 6. Recomendação de Implementação

### Prioridade P0 — Corrigir instrução incorreta (bug de confusão semântica)
1. Reescrever seção DADOS (3 linhas) para clarificar mcp__sql vs mcp__render
2. Reescrever linha 15 do Contexto para o mesmo

### Prioridade P1 — Remover dev-only (ruído sem custo de implementação)
3. Remover FORMATACAO NUMERICA BRASILEIRA (12 linhas) → mover para ~/.claude/CLAUDE.md
4. Remover Design System do INDICE (16 linhas) → 1 linha de ponteiro
5. Remover regra 1 "source .venv" das REGRAS UNIVERSAIS (1 linha)
6. Remover "ANTES de criar/editar doc" de MODELOS CRITICOS (1 linha)
7. Remover "NAO ESTENDER main_routes.py" de CAMINHOS (1 linha)
8. Remover `desenvolvedor-integracao-odoo` de SUBAGENTES (1 linha)
9. Remover 3 refs dev-only de Confiabilidade de Subagentes (3 linhas)

### Prioridade P2 — Melhorar descoberta
10. Reposicionar e tornar proeminente o ponteiro INDEX.md no topo da seção INDICE

### Prioridade P3 — Comprimir para reduzir ruído sem perder informação
11. Comprimir TECH STACK (remover Mobile App, Frontend detalhado, Artifacts dev, Data/Files, Build/Deploy)
12. Comprimir gestor-estoque-odoo de 1139 chars para ~120 chars

### Prioridade P4 — Corrigir inconsistência system_prompt.md (fora do CLAUDE.md)
13. Adicionar `gestor-estoque-odoo` ao `<subagents>` block do system_prompt.md
