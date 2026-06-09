# Findings A4 — CLAUDE.md raiz + arvore de references como caminho de descoberta

**Subagente**: A4 (missao dedicada)  
**Data**: 09/06/2026  
**Scope**: 6 questoes sobre como o CLAUDE.md raiz chega ao agente web, deploy de referencias, caminho de descoberta Odoo GOTCHAS, completude do INDEX, utilidade secao-a-secao do CLAUDE.md e redundancia de REGRAS_OUTPUT/MEMORY_PROTOCOL/ROUTING_SKILLS.

---

## Q1 — Como o CLAUDE.md raiz chega ao agente web (setting_sources)

**Fonte exata**: `app/agente/sdk/client.py:1573-1580`

```python
"cwd": project_cwd,  # /opt/render/project/src (raiz do projeto em Render)
"setting_sources": ["project"] if permission_mode == "acceptEdits" else ["user", "project"],
```

`project_cwd` e calculado em `client.py:1533-1539`:
```python
project_cwd = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
    )
)  # Raiz do projeto: /opt/render/project/src
```

- O SDK lê `CLAUDE.md` da raiz do projeto porque `cwd` aponta para a raiz e `setting_sources=["project"]` ativa a leitura do arquivo de projeto (comportamento nativo do Agent SDK — nao e codigo customizado, e convenção do SDK).
- No Render, `HOME=/tmp` (env injetado em `client.py:1608`), portanto `~/.claude/CLAUDE.md` (o global dev-only) NAO e lido — `setting_sources=["project"]` excluiu `"user"` explicitamente (`client.py:1577-1578`: "NÃO carregar 'user' para evitar que enabledPlugins pessoais causem hang no servidor").
- **Conclusao**: A leitura do CLAUDE.md raiz e um efeito colateral do setting_sources=["project"] + cwd=raiz_do_projeto, que e o comportamento padrao do SDK para descoberta de skills e CLAUDE.md de projeto.

### Ha como servir CLAUDE.md diferente por superficie (dev vs web)?

NAO diretamente via API do SDK. O SDK lê `CLAUDE.md` do `cwd`. Ha 3 caminhos possiveis:

1. **Mudar o `cwd` para um subdiretorio** que tenha um `CLAUDE.md` proprio — impraticavel porque quebraria a descoberta de skills em `.claude/skills/`.
2. **Usar o mecanismo atual**: manter o CLAUDE.md raiz compartilhado e separar conteudo dev-only para `~/.claude/CLAUDE.md` (que nao chega ao agente web porque `setting_sources=["project"]` nao inclui `"user"`). Este e o design atual.
3. **Injetar conteudo via system_prompt** (arquivo `app/agente/prompts/system_prompt.md`) — este e o mecanismo correto para conteudo exclusivo do agente web.

O `app/agente/CLAUDE.md` documenta explicitamente essa separacao:
> `CLAUDE.md` (raiz) — REFERENCIA: indice unificado de docs, gotchas de modelos, subagentes | Regras dev, CSS, caminhos de modulo (em ~/.claude/CLAUDE.md)
> `~/.claude/CLAUDE.md` — DEV-ONLY: Quick Start, migrations, CSS, caminhos, refs dev-only | Visivel apenas ao Claude Code

---

## Q2 — O deploy do Render inclui .claude/references? O agente web consegue Read?

**Evidencia**: `git -C /home/rafaelnascimento/projetos/frete_sistema ls-files --cached .claude/references/ | wc -l` retornou **364 arquivos** rastreados pelo git.

O `.gitignore` exclui apenas:
```
.claude/settings.local.json
.claude/skills/**/__pycache__/
...
.claude/worktrees/
```

O diretorio `.claude/references/` e **completamente rastreado** e portanto incluido no deploy ao Render.

**Confirmaçao** no `contexto_boot.md:1581`: o CLAUDE.md servido ao agente no Render mostra:
```
## Fonte: /opt/render/project/src/CLAUDE.md
```

E na sessao 4 do boot o agente ja recebe o CLAUDE.md raiz com todos os ponteiros para `.claude/references/`. O agente web **tem** a tool `Read` (entre as always-loaded, confirmado no `contexto_boot.md:1543-1580`, secao "12 always-loaded"). Portanto, o agente pode e deve usar `Read` para acessar qualquer arquivo em `.claude/references/`.

**Observacao**: Nao ha `.renderignore` no projeto. NAO foi encontrado arquivo de ignore especifico para Render.

---

## Q3 — Trace do caminho de descoberta dos GOTCHAS Odoo

### Elos do caminho

```
[BOOT] system_prompt.md (v4.3.3)
  └─ <knowledge_base> (linha 910-914 do boot):
     "consulte o INDICE DE REFERENCIAS no CLAUDE.md compartilhado (raiz do projeto) 
      via Read ANTES de responder 'nao sei'. Paths relativos a .claude/references/"
  └─ Linha 811 do boot (rule R7 routing_strategy):
     "Para routing completo, desambiguacao e arvore de decisao Odoo: 
      .claude/references/ROUTING_SKILLS.md"
  └─ CLAUDE.md raiz (linhas 1666+1699 do boot):
     "ANTES de executar qualquer skill ou operacao Odoo: LER .claude/references/ROUTING_SKILLS.md"
     "| Gotchas Odoo (timeouts, erros) | .claude/references/odoo/GOTCHAS.md |"

[SALTO 1] ROUTING_SKILLS.md (262 linhas, 31.8KB)
  └─ Passo 2 (linha 93 do arquivo):
     "GOTCHAS conhecidos (timeouts, erros): .claude/references/odoo/GOTCHAS.md"
  └─ Passo 3: arvore de decisao de skills Odoo

[SALTO 2] ROUTING_ODOO.md (60 linhas, 2.4KB) — documento OPCIONAL no caminho
  └─ Linha 22-25: "Consultar GOTCHAS.md — timeouts, campos inexistentes e commit preventivo"

[SALTO 3] GOTCHAS.md (610 linhas, 28.9KB) — DESTINO
```

### Analise de percorribilidade

O caminho e **percorrivel sem ambiguidade**, mas tem **redundancia de entrada** — ha 4 pontos de entrada distintos para o mesmo GOTCHAS.md:

1. `system_prompt.md` linha 662: mencao direta a `GOTCHAS.md` secao "Recalcular Impostos" (inline no prompt, nao via caminho de descoberta)
2. `system_prompt.md` linha 811: ponteiro para `ROUTING_SKILLS.md` (que chega ao GOTCHAS)
3. `CLAUDE.md` raiz linha 1703: entrada direta no INDICE
4. `ROUTING_ODOO.md`: referencia explicita ao GOTCHAS

**Numero de saltos para o agente chegar ao GOTCHAS sem conhecimento previo**: 2 saltos obrigatorios (system_prompt → ROUTING_SKILLS → GOTCHAS). O `ROUTING_ODOO.md` e um elo intermediario OPCIONAL (a `ROUTING_SKILLS.md` ja aponta para GOTCHAS diretamente no Passo 2).

**Ha atalho melhor?** Sim. O INDICE do CLAUDE.md (linha 1703 do boot) aponta diretamente para `odoo/GOTCHAS.md` sem passar por `ROUTING_SKILLS.md`. E o caminho mais curto: system_prompt → CLAUDE.md (via knowledge_base) → GOTCHAS (1 salto logico). 

**Problema identificado**: o system_prompt menciona `GOTCHAS.md` diretamente inline (linhas 662 e 669) sem passar pela arvore de descoberta — isso e redundancia saudavel para os 2 gotchas mais criticos, mas cria inconsistencia se o GOTCHAS.md for atualizado (o inline no prompt pode ficar stale).

---

## Q4 — Avaliacao do INDEX.md: completude

**Teste executado**: comparacao exaustiva arquivo-por-arquivo.

### Resultado: INDEX.md e COMPLETO para os arquivos existentes

- Todos os 364 arquivos rastreados em `.claude/references/` cujos basenames aparecem no INDEX.md foram verificados: **nenhum arquivo existente esta ausente do INDEX**.
- `find .claude/references -name "*.md" | while read f; do basename_only=$(basename "$f"); grep -qF "$basename_only" INDEX.md || echo "AUSENTE: $f"; done` — output vazio.

### Lacunas do INDEX em relacao ao CLAUDE.md raiz (INDICE secao)

O CLAUDE.md raiz INDICE (secao que o agente le no boot) e um **SUBCONJUNTO** do INDEX completo. Os seguintes documentos estao no INDEX mas **NAO aparecem** na secao INDICE do CLAUDE.md raiz:

| Documento | Categoria |
|-----------|-----------|
| `odoo/PADROES_AVANCADOS.md` | Odoo |
| `odoo/PIPELINE_RECEBIMENTO_LF.md` | Odoo (especifico LF) |
| `odoo/CONVERSAO_UOM.md` | Odoo |
| `design/MAPEAMENTO_CORES.md` | Design |
| `linx/INTEGRACOES.md` | Linx (referencia dev, nao web) |
| `negocio/historia_nacom.md` | Historico |
| `negocio/RECEBIMENTO_MATERIAIS.md` | Negocio |

**Julgamento**: A lacuna e **intencional e correta** — o CLAUDE.md raiz INDICE e um "quick reference" para os documentos mais acessados, enquanto o INDEX completo e o inventario exaustivo para uso do Claude Code (dev). O agente web pode chegar a qualquer documento via INDEX diretamente (a `<knowledge_base>` instrui a consultar o INDEX no CLAUDE.md via Read).

**Inconsistencia real identificada**: O CLAUDE.md raiz secao INDICE **nao menciona** a existencia do INDEX.md completo em `.claude/references/INDEX.md` como ponto de entrada expandido. A instrucao `<knowledge_base>` no system_prompt (linha 912-913 do boot) diz "consulte o INDICE DE REFERENCIAS no CLAUDE.md" — mas o CLAUDE.md raiz nao diz explicitamente "para lista mais completa, ver `.claude/references/INDEX.md`". Isso pode fazer o agente parar no indice incompleto do CLAUDE.md em vez de ir ao INDEX completo.

---

## Q5 — CLAUDE.md raiz secao-a-secao: uso pelo agente web

### TECH STACK (linhas 1607-1628 do boot)

**O agente web usa?** PARCIALMENTE.  
**Evidencia**: O agente web nao escreve codigo, nao faz deploy, nao gerencia workers. Mas precisa saber que o sistema usa Flask+SQLAlchemy para interpretar schemas, que o banco e Postgres 18 para escrever queries corretas, e que Playwright esta disponivel para as skills de automacao.  
**Veredicto**: ~50% util ao agente web. Linhas sobre `Mobile App (GPS)`, `Build/Deploy`, `Artifacts (chat web)` e detalhes de versao exata de bibliotecas de frontend sao DEV-ONLY (o agente nao usa isso para decidir nada operacional). A coluna "Infra (Render, Oregon)" e util (agente usa MCP Render). O bloco todo pesa ~15 linhas.

### DADOS: (linhas 1630-1635 do boot)

**O agente web usa?** SIM — CRITICO.  
**Evidencia**: As 3 regras sao diretamente operacionais para o agente web: fonte de dados = MCP Render (nao banco local), cross-verificacao Odoo. PORÉM a formulacao "Utilize exclusivamente o MCP do Render" pode confundir o agente web sobre seu proprio banco de dados (o agente web conecta via mcp__sql ao banco de producao no Render — que IS o dado real, nao "dado de teste").

### REGRAS UNIVERSAIS (linhas 1638-1645 do boot)

**O agente web usa?** PARCIALMENTE.  
**Evidencia**: Regra 1 "AMBIENTE VIRTUAL: `source .venv/bin/activate`" e **DEV-ONLY** — no Render nao ha `.venv` e o agente nao executa esse comando. Regras 2 e 3 (INFRAESTRUTURA.md, REGRAS_TIMEZONE.md) sao uteis ao agente web. A regra dev-only esta ocupando espaco no contexto do agente web sem utilidade.

### FORMATACAO NUMERICA BRASILEIRA (linhas 1647-1657 do boot)

**O agente web usa?** NAO.  
**Evidencia**: Mostra filtros Jinja2 (`{{ valor|valor_br }}`). O agente web nao cria templates Jinja2 (seu escopo e `cannot_do: modificar codigo-fonte`). Esta secao e **DEV-ONLY**. Ocupa 12 linhas sem utilidade para o agente web.

### MODELOS CRITICOS (linhas 1659-1674 do boot)

**O agente web usa?** SIM — CRITICO.  
**Evidencia**: Gotchas `qtd_saldo_produto_pedido` vs `qtd_saldo` sao essenciais para queries corretas. Os ponteiros para REGRAS_CARTEIRA_SEPARACAO.md, REGRAS_MODELOS.md e ROUTING_SKILLS.md sao usados pelo agente. MAS a instrucao "ANTES de criar/editar doc ou script: LER ARQUITETURA_DE_ARTEFATOS.md ou usar skill `padronizando-docs`" e **DEV-ONLY** (o agente web nao cria scripts de producao).

### INDICE DE REFERENCIAS (linhas 1676-1750 do boot)

**O agente web usa?** SIM — ESSENCIAL.  
**Evidencia**: Este e o principal mecanismo de descoberta progressiva do agente web. A `<knowledge_base>` no system_prompt aponta diretamente para este indice. Sem ele, o agente nao sabe que GOTCHAS.md, IDS_FIXOS.md etc existem.

### Design System (UI/CSS) (linhas 1733-1749 do boot)

**O agente web usa?** NAO.  
**Evidencia**: O agente web nao modifica CSS, nao roda `python scripts/audits/ui_audit.py`, nao instala pre-commit hooks. Esta secao e **100% DEV-ONLY**. Ocupa ~16 linhas de contexto sem utilidade operacional para o agente web. A skill `frontend-design` existe mas e usada pelo Claude Code, nao pelo agente web logistico.

### CAMINHOS DO SISTEMA (linhas 1750-1777 do boot)

**O agente web usa?** MARGINALMENTE.  
**Evidencia**: O agente web pode usar `Read` para acessar arquivos de modulo (ex: `app/carvia/CLAUDE.md`). Os caminhos como `app/carteira/routes/` sao uteis para referenciar arquivos. Mas a secao e predominantemente orientada ao dev que escreve codigo. O agente web nao "desenvolve" nesses caminhos, apenas consulta via Read. Utilidade estimada: 30%. A nota "NAO ESTENDER app/carteira/main_routes.py" e puramente DEV.

### SUBAGENTES (linhas 1779-1817 do boot)

**O agente web usa?** SIM — CRITICO, MAS COM REDUNDANCIA.  
**Evidencia**: O agente web delega para subagentes. Porem a lista de subagentes TAMBEM esta no `system_prompt.md` (linhas 828-879 do boot) com mais detalhes (delegate_when, capabilities). Ha redundancia parcial.  
**Problema especifico (R-9 de Rafael confirmado)**: 
- `gestor-estoque-odoo` aparece no CLAUDE.md SUBAGENTES (linha 1794) mas NAO no system_prompt `<subagents>` block (linhas 828-879). O agente web opera via system_prompt principalmente, entao este subagente pode ser esquecido.  
- `desenvolvedor-integracao-odoo` aparece no CLAUDE.md como "dev-only, nao exposto ao agente web" — referencia correto, mas ainda gera ruido cognitivo.
- A descricao do `gestor-estoque-odoo` no CLAUDE.md e **extremamente longa** (uma linha de 750+ chars com detalhes de skills internas, gotchas, versoes).

### Confiabilidade de Output (linhas 1798-1816 do boot)

**O agente web usa?** SIM — CRITICO.  
**Evidencia**: O protocolo "escrever findings em /tmp/subagent-findings/" e essencial para subagentes. Os ponteiros para SUBAGENT_RELIABILITY.md, AGENT_DESIGN_GUIDE.md etc sao uteis ao agente web quando delega tarefas. Porem `AGENT_DESIGN_GUIDE.md` e `AGENT_TEMPLATES.md` sao principalmente DEV (para criar/editar subagentes), nao para o agente web operacional. O `AGENT_BOILERPLATE.md` e usado pelo desenvolvedor, nao pelo agente web.

---

## Q6 — REGRAS_OUTPUT.md, MEMORY_PROTOCOL.md, ROUTING_SKILLS.md: tamanho, redundancia

### REGRAS_OUTPUT.md

- **Tamanho**: 91 linhas, ultima atualizacao: 2026-06-05
- **Conteudo**: I1 (distinguir pedidos vs clientes), I5 (linguagem operacional), I6 (eficiencia), I7 (entrega atomica de artefatos)
- **Redundancia com system_prompt**:
  - I2, I3, I4 estao **inline no system_prompt** (linhas 708-733 do boot) — corretamente, sao safety-critical
  - I5 e mencionada no system_prompt linha 608 e 640 (referenciada, nao inlinada completamente)
  - I7 tem **principio + gatilho inline** no system_prompt (linha 734-741) + procedimento completo no REGRAS_OUTPUT.md
  - **Padrao correto** sendo seguido: principio no system_prompt (3-5 linhas), procedimento completo na reference. Zero redundancia problematica.

### MEMORY_PROTOCOL.md

- **Tamanho**: 166 linhas, ultima atualizacao: 2026-06-09 (ontem — arquivo vivo)
- **Conteudo**: ciclo de vida, formato canonico meta JSONB, categorias/decay, paths padrao, criterios de qualidade, triggers de salvamento, formato narrativo
- **Redundancia com system_prompt** (R0 em linhas 234-278 do boot):
  - R0 tem: auto_save triggers (7 itens), priority levels (mandatory/advisory/contextual), TIMING, explicit_save, constraints + pointeiro para MEMORY_PROTOCOL.md
  - MEMORY_PROTOCOL.md tem: os mesmos triggers + mais detalhe (decay, paths, implementacao `memory_injection.py:271`, formato sentinela)
  - **Avaliacao**: redundancia INTENCIONAL e CORRETA. R0 e o "principio operacional que o agente executa a cada turno" (gatilho de salvamento imediato). MEMORY_PROTOCOL.md e a "referencia arquitetural" para quando o agente precisa entender o sistema mais profundamente. Nao ha conflito.
  - **Unico ponto de atrito**: o `R0` no system_prompt lista os auto_save triggers completos (8 itens, ~10 linhas) e o MEMORY_PROTOCOL.md lista os mesmos 6 triggers na secao "Automatico (silencioso)". Poderia comprimir o R0 para apenas os criterios mais sucintos + ponteiro, mas o risco de degradacao e alto (M1 do agente = manter `<why>` e triggers).

### ROUTING_SKILLS.md

- **Tamanho**: 262 linhas, 31.8KB, ultima atualizacao: 2026-06-08
- **Conteudo**: Tabela de contextos→skills (43 linhas), Passo 2 Odoo estatico, Passo 3 arvore Odoo, inventario 54 skills
- **Redundancia com system_prompt**:
  - O system_prompt tem `<routing_strategy>` (linhas 795-815 do boot) com tabela de contextos → skills/subagentes — versao RESUMIDA do Passo 1 do ROUTING_SKILLS.md
  - O system_prompt tem `<subagents>` com delegate_when para 12 subagentes
  - ROUTING_SKILLS.md tem o inventario COMPLETO (54 skills) com USAR/NAO USAR PARA
  - **Redundancia real**: a tabela de contextos no system_prompt e o Passo 1 do ROUTING_SKILLS.md sao o mesmo conteudo em densidades diferentes — o system_prompt e a versao condensada para decisao rapida, o ROUTING_SKILLS.md e a versao completa para desambiguacao
  - **Amostra concreta**: `CONSULTA ANALITICA -> consultando-sql` aparece na linha 799 do boot (system_prompt) e na linha 43 do ROUTING_SKILLS.md. Redundancia INTENCIONAL — a version inline e mais rapida, a referencia e mais completa. Porem o `SAUDE DO BANCO -> diagnosticando-banco` aparece na linha 805 do boot (system_prompt) — uma skill que Rafael identificou como dev-only. Este e um caso de redundancia PROBLEMATICA: a skill de dev aparece no routing do system_prompt operacional.
  - **Update History (uma linha de 2000+ chars)**: A linha 32 do ROUTING_SKILLS.md tem um changelog inline gigantesco. Isso e ruido puro — nao beneficia o agente web que le este arquivo buscando routing guidance.

---

## Resumo dos problemas identificados (priorizados)

| ID | Problema | Evidencia | Impacto |
|----|----------|-----------|---------|
| P1 | CLAUDE.md serve conteudo DEV-ONLY ao agente web (3 secoes: REGRAS UNIVERSAIS rule 1, FORMATACAO NUMERICA BRASILEIRA, Design System UI/CSS) | `contexto_boot.md:1641` (`source .venv`), `1647-1657` (filtros Jinja2), `1733-1749` (ui_audit.py) | Ruido cognitivo; ~30 linhas sem utilidade operacional |
| P2 | `gestor-estoque-odoo` ausente do `<subagents>` block do system_prompt, presente apenas no CLAUDE.md | `contexto_boot.md:828-879` (nao contem gestor-estoque-odoo) vs `1794` | Agente pode nao delegar operacoes de estoque Odoo corretamente |
| P3 | CLAUDE.md INDICE nao pontua para o INDEX.md completo (`.claude/references/INDEX.md`) | Ausencia de entrada "Para lista completa: INDEX.md" | Agente para no indice parcial do CLAUDE.md |
| P4 | ROUTING_SKILLS.md tem changelog inline de 2000+ chars (linha 32) | Arquivo ROUTING_SKILLS.md linha 32 | Dilui a atencao do agente em busca de routing guidance |
| P5 | `skill_hints` e `world_model` (advisory) injetados em TODO boot | `contexto_boot.md:2065-2085` | Rafael (R-1) e agente (C4) concordam: ruido confirmado por Rafael |
| P6 | `stale_empresa` + `improvement_responses` injetados em boot operacional | `contexto_boot.md:1995-1997` | Governanca do sistema no boot operacional (C3 do agente) |
| P7 | `preferred_skills` inclui dev-only (gerindo-agente, diagnosticando-banco, consultando-sentry) | `contexto_boot.md:2035` | R-7 de Rafael: verificar uso real em producao |
| P8 | Subagentes duplicados CLAUDE.md + system_prompt com listas INCONSISTENTES | system_prompt tem 12 subagentes; CLAUDE.md tem 13+1 dev-only | R-9 de Rafael confirmado |
| P9 | REGRAS UNIVERSAIS rule 1 (`source .venv`) e rule 3 (ANTES de escrever codigo) sao dev-only | `contexto_boot.md:1641-1643` | Ruido; o agente web nao ativa virtualenvs |

---

## Conclusao sobre o caminho Odoo GOTCHAS

O caminho e percorrivel: system_prompt → ROUTING_SKILLS.md (Passo 2) → GOTCHAS.md em **2 saltos**. Ha um atalho de 1 salto via CLAUDE.md INDICE diretamente. O elo ROUTING_ODOO.md (60 linhas) e util mas opcional — ele adiciona contexto de "Regra Zero" mas nao e obrigatorio para chegar aos GOTCHAS.

O caminho sem ambiguidade porem tem **4 pontos de entrada distintos** para o mesmo GOTCHAS.md, o que e redundancia defensiva razoavel para um documento critico.
