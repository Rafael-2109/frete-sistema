# CRÍTICA ARQUITETURAL — Eixo F (Governança das 5 camadas)

> Revisor: arquiteto sênior cético. Lente de TETO (proibido criticar por volume/over-engineering).
> Base verificada contra código real (não só contra o blueprint).

---

## VEREDITO: SÓLIDO — com 3 ajustes (1 correção de modelo, 2 completudes)

O blueprint é o mais bem-ancorado dos eixos que toca a estrutura do agente: cada
afirmação de "estado atual" que reverifiquei bate com o código. A tese central
— *promover a constituição do `app/odoo/estoque/CLAUDE.md` a constituição do
agente inteiro* — é arquiteturalmente correta e não-óbvia: identifica que o
sistema já tem DUAS culturas de governança coexistindo e que a madura é
replicável. O caminho incremental (registry descritivo → derivador → RAG) é
genuinamente reaproveitador e tem rollback em cada fase. Os 3 ajustes abaixo não
derrubam nada; corrigem um erro de modelo de dados e fecham duas lacunas que, se
ignoradas, fazem o registry NASCER com drift.

---

## 1. COERÊNCIA — encaixe nas 5 camadas e respeito a invariantes

### 1.1 O que está coerente (verificado)

- **A invariante "1 skill = 1 objeto" do estoque é REAL e formal** (`app/odoo/estoque/CLAUDE.md:28-40`), não uma idealização do blueprint. Inclui inclusive o caso-limite tratado (`escriturando-odoo` = account.move "APENAS PARA ENTRADA"; DFe é "meio para chegar nele"). Generalizá-la via campo `object_or_subject` é legítimo.
- **O pilar "fluxos >> skills" é codificado e enforçado** (`estoque/CLAUDE.md:109-115` + as 5 tabelas de catálogo §6) — muito mais maduro do que o blueprint deixou transparecer: há **5 tabelas distintas** (Skills L2 atômicas / READ ancillary / Orchestrators C3 / Sub-skills PRE-FLIGHT / Fluxos L3), com status de lifecycle (`✅ MATURADA` / `🟡 mín viável` / `🛑 DEPRECATED`) por linha. A afirmação do blueprint de que "lifecycle só existe no estoque" (§1.5.4) está, se algo, SUBESTIMADA — o estoque já tem lifecycle multi-tier vivo.
- **A reusabilidade do parsing já existe**: `agent_loader._parse_skills` (`agent_loader.py:239-272`) aceita AMBOS formatos (CSV e lista YAML), e os 16 agentes em `.claude/agents/` declaram `skills:` em frontmatter parseável (verifiquei os 16). A Fase 1 ("registry descritivo extraído de frontmatters") é factível com o parser que JÁ está em produção — não inventa nada.
- **A separação Web/Teams e o agente isolado HORA** são respeitados: o blueprint trata `agente_lojas` como `isolated_agent` (allow-list FECHADA, `app/agente_lojas/config/skills_whitelist.py`) e o principal como deny-list aberta — exatamente o que `skills_whitelist.py:22-30` justifica. Coerente.
- **O encaixe na camada Control** (registry como "metadado de L5/hooks+permissions que governa L3/L4") é defensável: `_discover_skills_from_project` (`client.py:114`) já é o ponto onde `exposure` seria lido, e `feature_flags.py` é o precedente certo de "config que governa comportamento".

### 1.2 ERRO DE MODELO (ajuste #1, o mais importante para coerência)

**O `exposure` não pode ser um enum escalar de 4 valores como o blueprint desenha (§2.7).** Verifiquei o frontmatter real de `gestor-estoque-odoo.md`:

```yaml
skills:
  - ajustando-quant-odoo        # subagent_only (WRITE delegada)
  - ... (8 WRITE)
  - consultando-sql             # SHARED (também no principal)
  - resolvendo-entidades        # SHARED (também no principal)
```

Ou seja: o MESMO agente declara skills `subagent_only` E skills `shared`. Pior:
`consultando-sql` é declarada por **9 dos 16 agentes** (grep confirma: analista-carteira, analista-performance, auditor-financeiro, gestor-devolucoes, gestor-estoque-producao, raio-x-pedido, gestor-estoque-odoo...) E está no listing do principal. Logo `exposure` de uma skill NÃO é uma propriedade 1:1 da skill — é uma **relação N:M skill↔agente**. O modelo `SkillEntry.exposure="shared"` + `owner_agent="X"` (campos escalares, §2.1) NÃO consegue representar "skill compartilhada por 9 agentes E pelo principal".

**Consequência se não corrigir**: a validação da Fase 2 ("toda skill `subagent_only` tem ≥1 `owner_agent` que a declara", §2.8.c) vai dar falso-positivo/falso-negativo em massa, porque a verdade é uma tabela de arestas, não um atributo de nó. O registry nasceria incapaz de exprimir o estado real → drift no dia 1.

**Correção concreta**: o registry precisa de DUAS entidades, não uma:
- `SkillEntry`: name, domain, object_or_subject, layer, lifecycle, contract_ref, deprecated_by (propriedades intrínsecas da skill).
- `SkillBinding` (a aresta): `(skill_name, agent_name | "__principal__")` — derivada da UNIÃO de (frontmatters dos 16 agentes) ∪ (deny-list/listing do principal). `exposure` deixa de ser campo e vira uma **propriedade DERIVADA** das arestas: `principal` se há binding `__principal__`; `subagent_only` se só há bindings de agentes; `shared` se ambos; `isolated_agent` se o único agente é de domínio isolado. Isto, de quebra, torna a invariante de §2.8.c **trivialmente verdadeira por construção** (a aresta É a declaração), que é mais forte que validá-la.

Esse é exatamente o ponto onde o blueprint admite ter raciocinado por nó quando a estrutura é grafo — e é também onde ele já aponta a solução sem perceber: ao citar "Graph RAG-Tool Fusion" para dependências skill→skill (§2.5), está reconhecendo que a topologia certa é grafo. O `exposure` é o primeiro lugar onde o grafo aparece, e o blueprint o modelou como escalar.

---

## 2. REAPROVEITAMENTO — reusa de fato ou reinventa?

Forte no geral. Reusa: a constituição do estoque (modelo), `_parse_skills`
(extração), os 16 frontmatters (fonte), pgvector+Voyage (RAG), `<domain_detection>`
do system_prompt (árvore), o padrão `ui_policy_lint.py --enforce-new`
(rollout report-only→enforce). Tudo verificado e correto.

**Peças existentes NÃO aproveitadas (que deveriam estar no caminho):**

- **`tool_skill_mapper` (service L5, listado no CONTEXTO_ARQ.md linha 54 e no `services/CLAUDE.md`).** O blueprint propõe construir do zero o índice skill→intenção e o Skill-RAG (Fases 4-5), mas existe um service cujo nome literal é "mapeador tool↔skill". Se ele já materializa parte do mapa skill↔capacidade, a Fase 5 reaproveita-o (ou o aposenta conscientemente) em vez de reinventar retrieval. O blueprint NÃO o menciona — lacuna de reúso. *(Não inspecionei o conteúdo do service; aponto como peça a auditar antes da Fase 5, não como fato.)*
- **A árvore de fluxos do estoque (`app/odoo/estoque/fluxos/`) como SCHEMA, não só como inspiração.** O blueprint cita o progressive disclosure do estoque (`estoque/CLAUDE.md:116-118`) como analogia. Mas o estoque já tem uma CONVENÇÃO de folha de fluxo documentada (`fluxos/README.md`, referenciado em `estoque/CLAUDE.md:118`). A Fase 4 ("routing como índice gerado") deveria adotar esse formato de folha como o schema do índice gerado — em vez de inventar um formato novo de árvore. Reúso mais profundo do que "usar como galho".
- **O catálogo de 5 tabelas do estoque já É um registry parcial escrito à mão.** A Fase 1 deveria explicitamente PARSEAR as Tabelas 1-5 de `estoque/CLAUDE.md` (têm colunas estruturadas: Skill | Objeto Odoo | Service | Camada | Status) como seed do registry para o domínio `odoo.estoque` — não re-cadastrar manualmente 10 skills que já estão tabuladas com objeto+camada+status. O blueprint diz "extrair dos frontmatters + status do estoque" (§3 Fase 1) mas não nota que o estoque já tem o registry em forma de Markdown-table, pronto para parse.

---

## 3. REALIZABILIDADE — valor + rollback por fase, acoplamento

Boa decomposição. Fase 0 (consolidar deny-list) e Fase 1 (registry descritivo,
flag OFF) são genuinamente read-only/no-behavior-change com rollback trivial — a
melhor sequência possível para um refactor de governança. Concordo que é o
primeiro passo de maior alavancagem.

**Riscos de acoplamento que o blueprint subdimensionou:**

- **Fase 2 introduz acoplamento de BUILD ao registry** (CI guard falha o build se SKILL.md↔registry↔frontmatter divergem). Isto é desejável, mas o blueprint não diz QUEM atualiza o registry quando nasce uma skill demand-driven. A cultura do sistema é "skill nova entra por DEFAULT" (`skills_whitelist.py:22-26`, memory `feedback_skills_demanda_driven.md`). Se o CI guard exigir entry no registry para toda SKILL.md (§2.8.a), ele **inverte essa cultura**: skill nova passa a FALHAR o build até alguém preencher o registry. Isso colide com a invariante "demand-driven, skill nova é invisível-por-esquecimento é pior que não-cadastrada". **Mitigação não prevista**: o guard precisa de um modo "auto-seed" — uma SKILL.md sem entry gera um entry `incubating`/`principal` DEFAULT automaticamente (warning, não erro), preservando a cultura aberta. Sem isso, a Fase 2 vira atrito contra o fluxo de trabalho do Rafael (memory `feedback_nao_parar_meio.md`).
- **Fase 4 toca o system_prompt — e o system_prompt tem 2 consumidores (Web + Teams) com regra de export crítico no Teams.** O blueprint cita o risco ("testar Web+Teams") mas trata como médio. É o ponto mais perigoso do caminho: o routing hoje é PROSA que carrega `<boundary critical="true">` (faturamento, baseline_financeiro — verifiquei `system_prompt.md:670-700`) com prescrições comportamentais embutidas (ex.: "RECUSAR variação de formato baseline"). Um "índice gerado" que substitua a prosa precisa preservar essas boundaries comportamentais, que NÃO são derivuáveis do registry (são regras de negócio, não metadados de skill). **A Fase 4 deve separar explicitamente**: (a) o CATÁLOGO skill-a-skill (gerável do registry, vai pro filesystem on-demand) de (b) as BOUNDARIES críticas comportamentais (ficam no prompt, escritas à mão). O blueprint as funde em "routing", arriscando que a geração apague regra de negócio. Esta é a fonte de bug mais provável do caminho inteiro.

---

## 4. LACUNAS — o que o blueprint NÃO considerou

### 4.1 (A MAIS IMPORTANTE) A camada L2 tools (MCP) ficou fora da governança

O eixo é "governança das 5 camadas". O blueprint governa L3 (skills) e L4
(subagents) com excelência, toca L1 (prompt) e L5 (services) de raspão, e
**ignora L2 (tools/MCP) por completo**. Mas o problema-raiz que o blueprint
diagnostica — *"feeding all tools into a single prompt overwhelms the model"*
(Red Hat Tool-RAG, que o blueprint cita) — é literalmente sobre TOOLS, e o
agente tem **12 MCP servers** mais as Task* tools. O blueprint aplica Tool-RAG
só a skills, quando a literatura que ele cita é primariamente sobre tools.

Pior: existe `permissions.py` (`can_use_tool`, citado no CONTEXTO_ARQ.md linha 64)
que JÁ é um gate de governança de TOOL por contexto/subagente — o análogo exato,
na camada L2, do que o registry quer ser para L3/L4. O blueprint propõe um
registry de skills mas não unifica com o gate de tools que já existe. **O teto
verdadeiro é um CAPABILITY REGISTRY** (tools + skills + subagents como
capacidades de primeira classe no mesmo grafo de escopo), não um SKILL registry.
Skills e tools são ambas "capacidades expostas ou delegadas por contexto"; tê-las
em registries separados recria, em meta-nível, exatamente o drift que o blueprint
combate (duas fontes de verdade de escopo). Esta é a **lacuna mais importante**.

### 4.2 Confiabilidade de retorno de subagente (cross-eixo omitido)

O CLAUDE.md raiz tem uma seção inteira "Confiabilidade de Output (OBRIGATORIO)"
+ `.claude/references/SUBAGENT_RELIABILITY.md` + o service `subagent_reader`.
Governança de subagentes (L4) NÃO é só "quais skills ele declara" (o que o
blueprint cobre) — é também "o contrato de RETORNO do subagente é verificável?".
O blueprint generaliza o contrato de INPUT/composição (do estoque, pipe
output→input) mas não toca o contrato de OUTPUT verificável de subagente, que já
é uma invariante documentada do sistema. Um registry de capacidades que não
declara o contrato de retorno do subagente deixa metade da governança de L4 de fora.

### 4.3 Citação de lifecycle não verificável (risco de fundação acadêmica frágil)

O Componente 6 (lifecycle gate-based de 4 tiers) ancora-se em **arXiv 2602.12430**
("Skill Trust and Lifecycle Governance Framework"). Não consegui confirmar essa
referência — o ID `2602.*` é fev/2026 e a caracterização ("4-tier gate-based",
"26.1% community skills com vulnerabilidades") é muito específica para um paper
que não pude validar. As fontes Anthropic (progressive disclosure 3-estágios:
Discovery/Activation/Execution) e Red Hat Tool-RAG eu CONFIRMEI por WebSearch.
**Isto não invalida o Componente 6** — o lifecycle de 4 tiers é exatamente o que
o estoque JÁ pratica (`✅/🟡/⚠️/🛑`), então a fundação real é o próprio sistema,
não o paper. **Recomendação**: re-ancorar o Componente 6 no lifecycle EMPÍRICO do
estoque (citável: `estoque/CLAUDE.md` status markers) e tratar o arXiv como
"convergência externa SE confirmado", não como fundação. Arquitetura de produto
não deve apoiar uma decisão de design numa citação não-verificada.

### 4.4 Risco não mapeado: o registry vira gargalo de PR cross-domínio

Se TODO catálogo (CLAUDE.md, ROUTING_SKILLS, SUBAGENTES) passa a ser GERADO
(§2.8), então qualquer mudança de skill exige regenerar artefatos versionados →
todo PR de skill toca arquivos gerados → conflitos de merge em `main` (Rafael
trabalha em branches paralelas, memory `feedback_pedir_permissao_branch.md`). O
blueprint não considerou que centralizar a verdade num arquivo gerado cria um
hotspot de conflito. Mitigação: artefatos gerados ficam fora do controle de
diff-review (gerados em build/pre-commit, não commitados) OU o registry é
particionado por domínio (1 arquivo por namespace) para localizar conflitos.

---

## 5. AMBIÇÃO — é o teto ou ficou tímido?

**Ficou tímido em UM ponto** (a lacuna 4.1 já elevou: registry de SKILLS →
registry de CAPACIDADES tools+skills+subagents). Adiciono uma segunda elevação,
a mais ambiciosa:

### ELEVAÇÃO: O registry como GRAFO EXECUTÁVEL de capacidades, fonte do PLANEJADOR (eixo B)

O blueprint trata o registry como metadado DESCRITIVO/derivador (gera deny-list,
gera catálogo, alimenta RAG). O teto real é o registry como **grafo de
capacidades EXECUTÁVEL** — a estrutura de dados que o PLANEJADOR (eixo B)
consome para ORQUESTRAR, não só para rotear.

Repare na convergência que o próprio sistema já oferece e o blueprint não conectou:
- O estoque já tem **árvore de fluxos L3** = composições skill→skill com pré/pós-condições declaradas (`estoque/CLAUDE.md:57-70`, contrato com pré/pós-condições).
- Cada átomo declara `output` que alimenta `input` do próximo (composição por pipe).
- "Graph RAG-Tool Fusion" (que o blueprint cita en passant em §2.5) é exatamente: dependências estruturais entre capacidades.

Junte os três: se o registry codificar não só `object_or_subject` mas as
**arestas de composição** (quais pré-condições uma skill exige, quais pós-condições
garante — extraíveis dos contratos do estoque que JÁ TÊM esses campos), então o
grafo deixa de ser um mapa para roteamento e vira um **espaço de planejamento**:
o planejador (eixo B) pode fazer busca no grafo (skill X garante pós-condição que
é pré-condição de Y → encadeia X→Y) em vez de depender de fluxos L3 escritos à
mão. Os fluxos L3 deixam de ser DOCUMENTAÇÃO de composição e viram **planos
materializados/cacheados** de caminhos frequentes no grafo.

Isto fecha o que o CONTEXTO_ARQ.md chama de tese B ("agente é roteador reativo
single-shot; orquestração é prosa, não harness"). O registro de capacidades com
pré/pós-condições é o substrato que transforma orquestração-prosa em
orquestração-harness. O blueprint chega à porta disso (§3 dependências: "registry
+ contrato são o substrato comum de A e B") mas para em "substrato comum" — o teto
é o registry ser o **espaço de estados** do planejador, com os contratos do
estoque (pré/pós-condições) como operadores STRIPS-like. É a diferença entre "o
planejador lê o mapa" e "o mapa É o planejador".

---

## SÍNTESE PARA O ORQUESTRADOR

- **Veredito**: SÓLIDO, ajustar 3 coisas — (1) `exposure` é relação N:M skill↔agente, não enum escalar; modelar como `SkillBinding` (aresta) ou o registry nasce com drift no dia 1; (2) o CI guard da Fase 2 precisa de auto-seed `incubating` para não inverter a cultura demand-driven; (3) a Fase 4 deve separar catálogo-gerável de boundaries-comportamentais-críticas do system_prompt (senão a geração apaga regra de negócio Web/Teams).
- **Lacuna mais importante**: a camada L2 (tools/MCP, 12 servers) ficou inteira fora da governança, apesar de o problema-raiz citado (Tool-RAG) ser sobre TOOLS — e já existe `permissions.py::can_use_tool` que é o gate de tool por contexto, não unificado com o registry. O teto é um CAPABILITY registry (tools+skills+subagents no mesmo grafo de escopo), não um SKILL registry.
- **Elevação de ambição**: o registry não é mapa para roteamento, é **grafo executável de capacidades** com pré/pós-condições (já presentes nos contratos do estoque) — o espaço de estados que o planejador do eixo B consome para orquestrar, transformando os fluxos L3 de documentação em planos cacheados. O mapa não é lido pelo planejador; o mapa É o planejador.
