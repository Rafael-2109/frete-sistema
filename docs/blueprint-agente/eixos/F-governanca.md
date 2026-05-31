# EIXO F — GOVERNANÇA DAS 5 CAMADAS

> Blueprint arquitetural. Lente de TETO: o objetivo é elevar o teto de COERÊNCIA que sustenta crescimento ilimitado de skills/subagentes/services — NÃO podar. Volume só dimensiona infra.
>
> **Tese central**: As 5 camadas do agente (system_prompt · tools · skills · subagents · services) cresceram organicamente e hoje carecem de um *modelo unificado de governança*. Um subdomínio — `app/odoo/estoque/` — JÁ inventou esse modelo (L0-L4, contrato de átomo, antipadrões AP1-AP6, "1 skill = 1 objeto", fluxos>>skills). O `skills_whitelist.py` (WIP) é o primeiro reflexo desse modelo escapando para o sistema todo, disparado por uma falha de orçamento de contexto. O teto é **promover a constituição do estoque a constituição do agente inteiro**, ancorado nos padrões oficiais Anthropic Agent Skills 2026 + Tool-RAG.

---

## PARTE 1 — ESTADO REAL (com evidência arquivo:linha)

### 1.1 O inventário das 5 camadas (números reais, 2026-05-30)

| Camada | Quantidade | Onde | Evidência |
|--------|-----------|------|-----------|
| **L1 system_prompt** | 840 linhas / ~2.1K tok | `app/agente/prompts/system_prompt.md` | `wc -l` = 840; routing como PROSA `system_prompt.md:660-718` |
| **L2 tools (MCP)** | 12 servers | `app/agente/tools/` | `app/agente/CLAUDE.md` seção Estrutura |
| **L3 skills** | 51 dirs / 50 com SKILL.md | `.claude/skills/` | `find` = 50 SKILL.md; `consultando-sql` NÃO tem SKILL.md (data-folder, intencional — memory `consultando_sql_data_folder.md`) |
| **L4 subagents** | 16 (.md) — 13 doc no CLAUDE.md raiz | `.claude/agents/` | `ls` = 16; CLAUDE.md raiz lista 13 (drift: `auditor-sped-ecd` + `orientador-loja` + `gestor-motos-assai` ausentes/parciais da tabela) |
| **L5 services** | 17 (+CLAUDE.md, _utils) | `app/agente/services/` | `ls` = 19 entradas, 17 services reais |
| **hooks** | 8 registrados | `app/agente/sdk/hooks.py` | `app/agente/CLAUDE.md`: "Hooks SDK (8 registrados)" |

### 1.2 O SINTOMA: o listing da meta-tool `Skill` estourou o budget de contexto da CLI

Evidência primária — `app/agente/config/skills_whitelist.py:5-11`:

> "A description da meta-tool `Skill` e montada pela CLI (cli.js funcao `sY7`) concatenando `- nome: description` de TODAS as skills do listing. Com 46 skills (~48.7K chars) isso excede o budget de caracteres da tool (16K default / 8K efetivo via fator `A*0.08`), e o CLI TRUNCA cada description proporcionalmente (~150-320 chars/skill) — descartando as clausulas de desambiguacao (USAR/NAO USAR PARA, que ficam no fim) e degradando o roteamento de skills."

Confirmado em `app/agente/CLAUDE.md` (seção "skills option"): budget `floor(context_model * 0.08)` = 16.000 chars (ctx 200K); 46 skills ~48.7K excedia; CLI truncava ~322 chars/skill.

**Por que isto é o sintoma de um problema MAIOR e não um bug de string**: o truncamento corta exatamente as cláusulas `NÃO USAR PARA` (que vivem no FIM da description), que são o mecanismo de **desambiguação entre skills**. Ou seja: a falta de um modelo de *escopo* (qual skill pertence a qual fronteira/agente) e de *contratos enxutos* fez 46 descriptions verbosas competirem por um orçamento finito de roteamento. Isto é exatamente o problema que a literatura 2026 chama de *"feeding all tools into a single prompt overwhelms the model and degrades performance"* (Red Hat Tool-RAG, fev/2026).

### 1.3 A SOLUÇÃO ATUAL (B-MÉDIO): deny-list por domínio — eficaz mas é UM tampão de UMA camada

`skills_whitelist.py:69-91` define 3 conjuntos removidos do listing do principal:
- `SKILLS_DOMINIO_HORA` (5 skills → agente isolado `app/agente_lojas`)
- `SKILLS_DOMINIO_ASSAI` (6 skills → subagente `gestor-motos-assai`)
- `SKILLS_ODOO_ESTOQUE_SUBAGENTE` (10 skills → subagente `gestor-estoque-odoo`)

Consumido em `client.py:_discover_skills_from_project()` (`client.py:83-126`): `excluidas = SPED_SKILLS_RESERVED | SKILLS_DELEGADAS_SUBAGENTE`. Reduz principal de 46→25 skills.

`SPED_SKILLS_RESERVED` (4 skills) vive **noutro arquivo** — `config/settings.py:40-45` (frozenset ClassVar). **Drift estrutural #1**: existem DOIS mecanismos de exclusão de skill em DOIS arquivos com DUAS estruturas (`frozenset` vs `Set`), unidos só por um operador `|` em `client.py:114`. Não há um registro único de "quem é dono de qual skill".

**O que funciona bem**: a escolha DENY-list (vs allow-list fechada do `agente_lojas`) está corretamente justificada (`skills_whitelist.py:22-26`) — domínio aberto, skills demand-driven, skill nova entra por default. Isto está alinhado com a filosofia "skills nascem de demandas reais" (memory `feedback_skills_demanda_driven.md`).

### 1.4 O EXEMPLAR MADURO: a constituição do `app/odoo/estoque/CLAUDE.md`

Este subdomínio já resolveu, PARA SI, todos os problemas de governança que o resto do agente ainda não tem. É o protótipo do teto:

- **Modelo de 5 camadas próprio** (`estoque/CLAUDE.md:42-55`): L0 constants → L1 services/primitivas → L2 skills-átomos → L3 fluxos (Markdown navegável) → L4 subagente. "Cada camada só conhece a de baixo."
- **Invariante taxonômico "1 SKILL = 1 OBJETO ODOO"** (`estoque/CLAUDE.md:28-40`): uma skill L2 tem EXATAMENTE 1 objeto Odoo principal; 2+ objetos = FLUXO L3, não skill nova. Isto é uma **regra de escopo formal e verificável**.
- **Contrato de átomo componível** (`estoque/CLAUDE.md:57-70`): bloco obrigatório `## Contrato` na SKILL.md com `objeto / input / output / pré-condições / pós-condições / gotchas-invariante / modos`. O `output` de um átomo alimenta o `input` do próximo (composição por pipe). **Isto é um contrato de interface entre skills** — não existe em mais nenhuma das 39 skills não-estoque.
- **Pilar "fluxos >> skills"** (`estoque/CLAUDE.md:109-115`): poucos átomos estáveis (~8) ⟷ muitos fluxos (crescem). Caso de negócio novo = nova folha de fluxo, NÃO skill nova. **Proíbe explosão combinatória 1-skill-por-fluxo.**
- **3 tabelas distintas de catálogo** (`estoque/CLAUDE.md:120-168`): Skills L2 atômicas / Orchestrators C3 macros / Fluxos L3 — separação que IMPEDE confundir um átomo com um orquestrador.
- **Antipadrões com causa-raiz codificada** (`estoque/CLAUDE.md:211-279`, AP1-AP6): cada um documenta CAUSA RAIZ + CONSEQUÊNCIA + COMO EVITAR + RESOLUÇÃO. AP3 é literalmente "orchestrator chamando átomos inline" — o pecado capital de governança de composição.
- **Lifecycle explícito por status**: cada skill carrega `✅ MATURADA / 🟡 mín viável / ⚠️ V1 STRICT (antipadrão documentado) / 🛑 DEPRECATED`. Ex.: `criar_picking_entrada_destino_manual` marcada DEPRECATED como "museum vivo até canary v20+" (`estoque/CLAUDE.md:132`).

**Conclusão da Parte 1**: o agente possui DUAS culturas de governança coexistindo. Uma **madura e formal** (estoque, ~10 skills, contrato+lifecycle+antipadrões) e uma **orgânica e implícita** (as outras ~40 skills + 16 subagentes + 17 services, sem contrato, sem lifecycle, sem dono declarado). O `skills_whitelist.py` é o primeiro ponto onde a cultura madura começou a vazar para o sistema todo — mas só na dimensão "escopo de listing", e via dois arquivos desconexos.

### 1.5 As 4 patologias concretas de drift (todas verificadas)

1. **Drift documental doc↔código** (recorrente, citado na tese F). Exemplos verificados:
   - `ROUTING_SKILLS.md:3` header diz "49 skills invocaveis"; há 50 SKILL.md. O header é um **parágrafo run-on de ~30 linhas** carregando changelog v14b→v19+ inline (anti-pattern: changelog dentro de doc de roteamento).
   - CLAUDE.md raiz "SUBAGENTES" lista 13; `.claude/agents/` tem 16. `auditor-sped-ecd` e `orientador-loja` existem no código mas não na tabela canônica.
   - `skills_whitelist.py:8` diz "46 skills"; hoje são 50/51.

2. **Sem namespacing de domínio.** Nomes são verbo-gerúndio (`consultando-`×6, `operando-`×5, `rastreando-`×3 — survey de prefixos). Domínio aparece só por SUFIXO ad-hoc e inconsistente: `-odoo` (10×), `-assai` (5×), `-loja`/sem-sufixo (HORA). Não há como, a partir do NOME, saber a que fronteira/agente uma skill pertence — a informação vive espalhada em 2 whitelists + 16 frontmatters + prosa do system_prompt.

3. **Mapeamento skill↔subagente é tácito e tríplice.** A verdade "skill X é operada via subagente Y" está replicada em: (a) `skills_whitelist.py` (deny-list, 3 grupos); (b) frontmatter `skills:` de cada `.claude/agents/*.md` (extraído: 16 agentes declaram skills, ex. `gestor-estoque-odoo` declara as 10 skills WRITE); (c) prosa `<delegate_when>` no system_prompt (`system_prompt.md:734-785`). Três fontes, zero validação cruzada. Nada garante que uma skill na deny-list do principal esteja REALMENTE declarada por algum subagente — o comentário em `skills_whitelist.py:18` afirma a invariante mas nada a *enforça*.

4. **Lifecycle só existe no estoque.** As ~40 skills fora do estoque não têm campo de status/maturidade/owner. Existe um processo de maturação (`SKILL_IMPROVEMENT_ROADMAP.md`: 28 DONE / 3 IN_PROGRESS / 4 PENDING) e artefatos parciais de qualidade (21/50 com `evals/`, 14/50 com `SCRIPTS.md`, 42/50 com `scripts/`) — mas é um roadmap one-shot de melhoria, NÃO um lifecycle contínuo (nascimento→maturação→deprecação→remoção). Não há mecanismo de *deprecação* fora do estoque.

---

## PARTE 2 — ALVO ARQUITETURAL (o teto)

> **Princípio do teto**: o agente da Nacom deve poder crescer para 100+ skills e 30+ subagentes SEM degradar roteamento, SEM drift doc↔código, e SEM o desenvolvedor precisar manter coerência manualmente em 4 lugares. A coerência vira **propriedade do sistema, derivada de uma fonte única**, não disciplina humana. Isto é exatamente o que Anthropic descreve como o gargalo aberto de "full lifecycle of creating, editing, discovering, sharing, and using Skills" (eng blog 2026) e o que a academia chama de "Skill Trust and Lifecycle Governance Framework" (arXiv 2602.12430, modelo gate-based de 4 tiers).

### 2.1 Componente 1 — O REGISTRY ÚNICO de skills (fonte da verdade)

Um manifesto declarativo único — `app/agente/config/skill_registry.py` (ou YAML versionado) — que para CADA skill declara:

```python
SkillEntry(
    name="ajustando-quant-odoo",
    domain="odoo.estoque",          # namespace hierárquico (ver 2.2)
    layer="L2",                      # L2 atômica | C3 orchestrator | L3 fluxo | READ
    object_or_subject="stock.quant", # o "1 objeto" — invariante do estoque GENERALIZADO
    owner_agent="gestor-estoque-odoo",  # quem opera; None = principal
    exposure="subagent_only",        # principal | subagent_only | shared | isolated_agent
    lifecycle="matured",             # incubating | minimum_viable | matured | deprecated | retired
    contract_ref=".../SKILL.md#contrato",
    deprecated_by=None,
    superseded_by=None,
)
```

Deste registry DERIVAM (não duplicam):
- a **deny-list** do principal (`exposure != principal/shared`) — substitui `skills_whitelist.py` + `SPED_SKILLS_RESERVED` por UMA fonte;
- o **`skills=` de cada subagente** (cross-check contra o frontmatter — falha de build se divergir);
- as **tabelas de catálogo** no CLAUDE.md (geradas, nunca escritas à mão → mata o drift #1 e #3);
- o **routing index** consumido pelo system_prompt (ver Componente 4).

Encaixe nas 5 camadas: o registry é **metadado da camada Control (L5/hooks+permissions)** que GOVERNA as camadas skills (L3) e subagents (L4). É o análogo da feature `feature_flags.py` mas para *escopo/lifecycle de capacidade* em vez de *toggle de feature*.

### 2.2 Componente 2 — TAXONOMIA + NAMESPACING hierárquico

Adotar namespace `dominio.subdominio` ortogonal ao verbo de ação. O estoque já provou que o "objeto principal" é o eixo natural de organização. Generalizar:

```
logistica.expedicao    → gerindo-expedicao, cotando-frete, visao-produto
logistica.entrega      → monitorando-entregas, analise-performance
odoo.estoque           → ajustando-quant-odoo, transferindo-interno-odoo, ... (já maduro)
odoo.fiscal            → escriturando-odoo, faturando-odoo, validacao-nf-po
odoo.financeiro        → executando-odoo-financeiro, conciliando-*, razao-geral
ssw                    → acessando-ssw, operando-ssw
carvia                 → gerindo-carvia
sped                   → parseando-sped-ecd, auditando-sped-* (reservado a auditor-sped-ecd)
dominio.hora           → consultando-estoque-loja, ... (agente isolado)
dominio.assai          → consultando-estoque-assai, ... (subagente)
infra                  → consultando-sql, diagnosticando-banco, consultando-sentry, exportando-arquivos
meta                   → gerindo-agente, gerando-artifact, resolvendo-entidades
```

Não é preciso RENOMEAR os arquivos (custo alto, baixo valor) — o namespace é um CAMPO no registry. Mas o namespace habilita: filtrar listing por domínio ativo, agrupar catálogos, e — crucialmente — **Tool-RAG por domínio** (ver 2.5).

A **invariante de escopo generalizada** (do estoque para o todo): *toda skill declara seu `object_or_subject` e seu `domain`; uma skill que precisa de 2+ objetos/domínios é um FLUXO (composição), não uma skill nova.* Isto é o freio formal contra a explosão que causou o estouro de budget.

### 2.3 Componente 3 — CONTRATO universal de skill (generalizar o `## Contrato` do estoque)

Toda SKILL.md passa a exigir o bloco de contrato do estoque (`estoque/CLAUDE.md:60-69`), adaptado para skills READ:

```
## Contrato
- dominio:        <namespace>
- objeto/sujeito: <entidade principal — local table OU Odoo model OU "n/a-read">
- input:          <args ou intenção>
- output:         <forma estruturada do retorno — habilita composição>
- exposicao:      principal | subagent_only | shared
- lifecycle:      <status>
- NAO-FAZ:        <fronteiras — o que delega a quem>  ← a cláusula de desambiguação, agora PRIMEIRO-classe
```

Ganho-chave: a cláusula `NÃO-FAZ` (hoje enterrada no fim da YAML description e por isso TRUNCADA) vira um campo estruturado, curto, indexável. O routing não depende mais de ler 600 chars de prosa por skill.

### 2.4 Componente 4 — Routing como ÍNDICE GERADO, não prosa manual

Hoje routing é prosa em 3 lugares (`system_prompt.md:660-718` + `ROUTING_SKILLS.md` 227 linhas + `<delegate_when>` 734-785). O alvo: o system_prompt carrega só a **árvore de decisão de domínio** (`<domain_detection>` já existe, 665-672) — o equivalente aos "galhos" do progressive disclosure do estoque (`estoque/CLAUDE.md:116-118`). A tabela skill-por-skill é GERADA do registry e carregada sob demanda (filesystem) — exatamente o modelo oficial Anthropic: "metadata (~100 tok/skill) no startup, SKILL.md completa só on-demand" (eng blog 2026). Isto resolve o budget estruturalmente: o principal nunca carrega 50 descriptions de uma vez.

### 2.5 Componente 5 — Tool-RAG / Skill-RAG por domínio (o teto de escala)

Quando o catálogo crescer além do que cabe confortavelmente no listing (mesmo com deny-list), adotar recuperação semântica de skills: indexar (name + contrato + NÃO-FAZ) em pgvector (a infra JÁ EXISTE — Voyage+pgvector para memórias, `app/agente/CLAUDE.md` Memória Compartilhada), e expor ao principal apenas as top-K skills relevantes à intenção do turno. Isto é o estado da arte 2026 (Red Hat ToolScope; Toolshed RAG-Tool Fusion arXiv 2410.14594; Graph RAG-Tool Fusion arXiv 2502.07223 para dependências estruturadas — que mapeiam 1:1 nos FLUXOS L3 do estoque, onde skill A depende de skill B). Resolve o budget para SEMPRE, independente de quantas skills existam.

### 2.6 Componente 6 — Lifecycle gate-based (nascimento→maturação→deprecação→remoção)

Adotar o "Skill Trust and Lifecycle Governance Framework" de 4 tiers (arXiv 2602.12430) mapeado ao que o estoque já pratica informalmente:

| Tier/Status | Gate de entrada | Exposição | Exemplo estoque |
|---|---|---|---|
| `incubating` | existe SKILL.md + contrato | dev/Claude Code only | átomos novos pré-canary |
| `minimum_viable` | ≥1 eval + dry-run validado | subagente, com confirmação | 🟡 da Tabela 1 estoque |
| `matured` | evals verdes + ≥1 uso PROD real | principal/subagente livre | ✅ ajustando-quant |
| `deprecated`→`retired` | `superseded_by` preenchido + canary do sucessor OK | removida do listing, código "museum vivo" até remoção | criar_picking_entrada_destino_manual |

O `SKILL_IMPROVEMENT_ROADMAP.md` (processo de maturação one-shot) vira a **transição `incubating→matured`** dentro deste lifecycle contínuo. A deprecação — hoje inexistente fora do estoque — ganha mecanismo formal (`deprecated_by`/`superseded_by` no registry + DeprecationWarning runtime, padrão já usado em `criar_recebimento_orchestrado`).

### 2.7 Componente 7 — Principal vs subagentes: contrato de compartilhamento/isolamento

Formalizar os 4 modos de `exposure` (já existem implicitamente, agora explícitos e validados):
- **`isolated_agent`** (HORA): agente separado, allow-list FECHADA (`agente_lojas/skills_whitelist.py` — precedente correto, domínio restrito). Fronteira contratual em `app/hora/CLAUDE.md`.
- **`subagent_only`** (estoque WRITE, Assai, SPED): fora do listing do principal; declarada via `AgentDefinition.skills` do subagente. O registry VALIDA que toda skill `subagent_only` tem ≥1 `owner_agent` que a declara — fechando o gap do `skills_whitelist.py:18` (invariante hoje só comentada).
- **`shared`** (lendo/exportando-arquivos, consultando-sql, resolvendo-entidades): no principal E nos subagentes. São as "primitivas universais".
- **`principal`** (default, domínio aberto): logística geral.

### 2.8 Anti-drift: doc↔código por GERAÇÃO

Tabelas de catálogo no CLAUDE.md raiz, `ROUTING_SKILLS.md`, e a lista de SUBAGENTES passam a ser **geradas** do registry por um script (`scripts/audits/generate_skill_catalog.py`) + um **CI guard** (pre-commit / pytest) que falha se: (a) existe SKILL.md sem entry no registry; (b) entry no registry sem SKILL.md; (c) skill `subagent_only` não declarada por nenhum agente; (d) catálogo no doc divergente do gerado. Isto MATA estruturalmente as 4 patologias da §1.5. Modelo de referência: o estoque já mantém `ROADMAP_SKILLS.md` + `MAPA_SCRIPTS.md` como inventário vivo; aqui automatizamos.

---

## PARTE 3 — CAMINHO INCREMENTAL (reaproveitando o existente)

> Filosofia: cada fase entrega valor isolado e reaproveita o exemplar do estoque. Nada é big-bang. O registry nasce DESCREVENDO o estado atual (zero comportamento novo) e só depois vira fonte derivadora.

### Fase 0 — Consolidar a deny-list dispersa em 1 arquivo (P, risco baixo)
**Destrava**: elimina o drift estrutural #1 (2 arquivos/2 estruturas). **Reaproveita**: `skills_whitelist.py` + `settings.py:40-45`.
- Mover `SPED_SKILLS_RESERVED` para `skills_whitelist.py` como 4º grupo `SKILLS_DOMINIO_SPED`; `settings.py` importa de lá.
- Resultado: `client.py:114` lê UMA fonte. Comentário-invariante de `:18` ainda não enforçado (Fase 2).
- **Risco**: trivial (refator de import). **Dep**: nenhuma.

### Fase 1 — Registry DESCRITIVO (read-only) + script de catálogo (M, risco baixo)
**Destrava**: fonte única; mata drift #1/#3/#4 documental. **Reaproveita**: frontmatters dos 16 agentes (já parseáveis por `agent_loader._parse_skills`), os status do estoque, o `SKILL_IMPROVEMENT_ROADMAP` (popula `lifecycle`).
- Criar `skill_registry.py` populado com as 50 skills (domain/object/owner/exposure/lifecycle). Boot derivação opcional (flag OFF) — apenas valida que descreve o estado atual sem mudar comportamento.
- `scripts/audits/generate_skill_catalog.py` gera as tabelas do CLAUDE.md/ROUTING_SKILLS a partir do registry. Rodar 1× e commitar o diff (sincroniza doc).
- **Risco**: baixo (read-only). **Dep**: Fase 0.

### Fase 2 — CI guard + derivação ativa da deny-list (M, risco médio)
**Destrava**: coerência vira propriedade do sistema; enforça invariante `skills_whitelist.py:18` (toda `subagent_only` tem dono). **Reaproveita**: registry da Fase 1; `_discover_skills_from_project` (`client.py:83`) passa a derivar do registry.
- pytest/pre-commit: SKILL.md↔registry↔agent-frontmatter consistentes (as 4 checagens da §2.8). Falha o build em divergência.
- `_discover_skills_from_project` lê `exposure` do registry em vez dos 3 sets manuais (mantém deny-list semanticamente).
- **Risco**: médio — guard pode pegar inconsistências reais hoje invisíveis (é o ponto). Rollout report-only→enforce (padrão `ui_policy_lint.py --enforce-new`).
- **Dep**: Fase 1. **Habilita eixo A/B**: planejador/flywheel confiam que o mapa de capacidade é verdadeiro.

### Fase 3 — Contrato universal nas SKILL.md (G, risco baixo, incremental)
**Destrava**: composição entre skills + cláusula NÃO-FAZ indexável (resolve a causa-raiz do truncamento). **Reaproveita**: bloco `## Contrato` do estoque (`estoque/CLAUDE.md:60-69`) — já existe nas ~10 skills de estoque; estender às outras ~40.
- Migração por domínio (não tudo de uma vez): começar pelos domínios já delegados (Assai, fiscal). Cada skill ganha `## Contrato` + `NÃO-FAZ` estruturado; a YAML `description` encolhe (limite oficial 1024, alvo ≤600 — "Solução A" já citada no CLAUDE.md).
- **Risco**: baixo por skill, volume alto (G). Pode rodar via o próprio `SKILL_IMPROVEMENT_ROADMAP` (1 sessão/skill).
- **Dep**: Fase 1 (registry sabe o que migrar).

### Fase 4 — Routing gerado + árvore enxuta no system_prompt (M, risco médio)
**Destrava**: budget resolvido sem deny-list crescer; routing deixa de ser prosa manual. **Reaproveita**: `<domain_detection>` (`system_prompt.md:665-672`) como árvore-galho; progressive disclosure do estoque (`estoque/CLAUDE.md:116-118`).
- system_prompt carrega só a árvore de domínio; tabela skill-a-skill gerada do registry, lida on-demand (filesystem). `ROUTING_SKILLS.md` vira artefato gerado.
- **Risco**: médio — mexe no prompt (testar Web+Teams, regra de export crítico Teams). **Dep**: Fases 1+3.
- **DEPENDÊNCIA CRÍTICA com eixo B (planejador)**: se o roteamento migrar para um harness/planejador estruturado, este routing-index é o INPUT dele. Coordenar: o registry+contrato são o substrato comum.

### Fase 5 — Skill-RAG semântico por domínio (G, risco médio) — o teto
**Destrava**: escala ilimitada de skills sem tocar budget. **Reaproveita**: pgvector+Voyage já em produção para memórias; contratos da Fase 3 como corpus a indexar; namespace da Fase 1 como filtro.
- Indexar (name+contrato+NÃO-FAZ) em pgvector; retrieval top-K por intenção do turno antes de expor skills ao principal. Dependências estruturais (skill A→B) mapeadas nos FLUXOS L3 (Graph RAG-Tool Fusion).
- **Risco**: médio (novo caminho de retrieval; precisa eval de recall de skill). **Dep**: Fases 1+3+4.

---

## RESUMO EXECUTIVO (alavancas, dependências, primeiro passo)

**Alavancas principais (estado → alvo):**
1. **Escopo disperso → registry único**: skill scope hoje vive em 4 lugares (2 whitelists + 16 frontmatters + prosa); alvo = `skill_registry.py` deriva todos. *(Fase 0-2)*
2. **Sem taxonomia → namespace `dominio.objeto` + invariante "1 skill = 1 objeto" generalizada do estoque**: organiza 50→100+ skills e habilita filtragem/RAG por domínio. *(Fase 1)*
3. **Contrato só no estoque → contrato universal**: o bloco `## Contrato` + cláusula `NÃO-FAZ` estruturada (hoje truncada no fim da YAML) vira primeiro-classe, atacando a causa-raiz do estouro de budget. *(Fase 3)*
4. **Routing-prosa em 3 lugares → índice gerado + árvore enxuta + Skill-RAG**: resolve o budget da meta-tool `Skill` estruturalmente (progressive disclosure oficial Anthropic), não por tampão de deny-list. *(Fases 4-5)*
5. **Lifecycle só no estoque → lifecycle gate-based de 4 tiers** (incubating→matured→deprecated→retired) com CI guard anti-drift; deprecação formal passa a existir fora do estoque. *(Fase 2+6)*

**Dependências cross-eixo:**
- **SUSTENTA A (flywheel)** e **B (planejador)**: ambos precisam de um mapa VERDADEIRO e estável das capacidades. Camadas incoerentes = base instável — o planejador não pode orquestrar skills cujo escopo/contrato é ambíguo, e o flywheel não pode medir qualidade por capacidade se não há fronteira de capacidade definida. O registry+contrato (Fases 1+3) são o substrato comum de A e B.
- **SUSTENTA D (ontologia)**: o `object_or_subject` de cada skill é a ponte natural para a ontologia logística — skills passam a se ancorar em entidades do modelo de mundo Nacom.
- **Independe de C (proatividade)** mas o registry serve de catálogo de "atuadores" quando C precisar agir.

**Primeiro passo concreto de maior alavancagem**: **Fase 0 + Fase 1** — criar `app/agente/config/skill_registry.py` populado com as 50 skills (domain/object/owner/exposure/lifecycle, extraindo de frontmatters+whitelists+status do estoque) e o `generate_skill_catalog.py`. Custo P-M, risco baixo (descritivo, read-only), e desbloqueia TODO o resto. Consolidar antes `SPED_SKILLS_RESERVED` (settings.py:40) com a deny-list (skills_whitelist.py) num só arquivo.

---

### Limitações desta análise (o que NÃO verifiquei)
- Não rodei o agente nem medi o tamanho REAL do listing pós-deny-list (25 skills) contra o budget de 16K — confiei nos números documentados em `skills_whitelist.py:8` e `CLAUDE.md`.
- Não inspecionei o conteúdo das 50 SKILL.md individualmente (só o exemplar estoque + os contratos); a estimativa "~40 sem contrato" deriva de `find SCRIPTS.md=14 / evals=21` e de o `## Contrato` ser uma convenção do estoque — não auditei skill-por-skill.
- A função `sY7` da cli.js e o fator `0.08` são citados na doc do projeto (`skills_whitelist.py:8`); não inspecionei o cli.js bundled.
- Os 17 services (camada L5) foram mapeados por inventário mas NÃO governados neste blueprint além de citá-los como camada — a governança de services (flags, dependências) está em `services/CLAUDE.md` e é menos crítica para o sintoma do budget; o foco do eixo F recaiu em skills↔subagentes, onde está o drift e o estouro.

**Fontes externas:**
- [Anthropic — Equipping agents for the real world with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) (progressive disclosure, metadata ~100 tok/skill no startup, "split SKILL.md quando unwieldy")
- [arXiv 2602.12430 — Agent Skills for LLMs: Architecture, Acquisition, Security, Path Forward](https://arxiv.org/html/2602.12430v3) (Skill Trust & Lifecycle Governance Framework, 4-tier gate-based; 26.1% community skills com vulnerabilidades)
- [Red Hat — Tool RAG: The Next Breakthrough in Scalable AI Agents](https://next.redhat.com/2025/11/26/tool-rag-the-next-breakthrough-in-scalable-ai-agents/) (ToolScope; "feeding all tools overwhelms the model")
- [Toolshed: Scale Tool-Equipped Agents with RAG-Tool Fusion (arXiv 2410.14594)](https://arxiv.org/pdf/2410.14594)
- [Graph RAG-Tool Fusion (arXiv 2502.07223)](https://arxiv.org/pdf/2502.07223) (dependências estruturais entre tools ↔ FLUXOS L3 do estoque)
