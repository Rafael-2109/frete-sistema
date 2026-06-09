# A3 — Exposição de Skills + Blocos Advisory: Findings Detalhados

**Data**: 09/06/2026
**Escopo**: skills_whitelist, frontmatter CLI, skill_hints, world_model, routing_context
**Autor**: Subagente de análise (A3)

---

## 1. Como as 28 skills da Seção 2 são selecionadas

### Mecanismo

A seleção é feita por **deny-list** em `app/agente/config/skills_whitelist.py`. A função
`_discover_skills_from_project()` em `app/agente/sdk/client.py:83-124` varre
`.claude/skills/*/SKILL.md`, exclui tudo que estiver em `SKILLS_DELEGADAS_SUBAGENTE`
(frozenset, linha 99-104 do whitelist), e retorna a lista ordenada passada ao SDK via
`options_dict["skills"] = _discover_skills_from_project()` (`client.py:1625`).

### Por que deny-list, não allow-list

O comment em `skills_whitelist.py:21-28` explica: o principal é um domínio ABERTO — skills
novas entram por default. Allow-list fechada exigiria manutenção a cada skill nova.
Exemplo de allow-list fechada: `app/agente_lojas/config/skills_whitelist.py`.

### O que é excluído (`SKILLS_DELEGADAS_SUBAGENTE` — 25 skills):

```
SKILLS_DOMINIO_HORA (5):
  consultando-estoque-loja, rastreando-chassi, acompanhando-pedido,
  conferindo-recebimento, consultando-pecas-faltando

SKILLS_DOMINIO_ASSAI (6):
  consultando-estoque-assai, rastreando-chassi-assai,
  acompanhando-pedido-compra-assai, acompanhando-saida-assai,
  conferindo-recibo-assai, registrando-evento-moto-assai

SKILLS_ODOO_ESTOQUE_SUBAGENTE (10):
  ajustando-quant-odoo, transferindo-interno-odoo, operando-reservas-odoo,
  operando-picking-odoo, operando-mo-odoo, escriturando-odoo,
  planejando-pre-etapa-odoo, consultando-quant-odoo,
  auditando-cadastro-fiscal-odoo, faturando-odoo

SKILLS_SPED_RESERVED (4):
  parseando-sped-ecd, auditando-sped-vs-manual,
  auditando-sped-contabil, comparando-sped-ground-truth
```

### Skills dev-only NÃO estão na deny-list

`consultando-sentry`, `diagnosticando-banco`, `gerindo-agente`, `padronizando-docs`
**NÃO constam em `SKILLS_DELEGADAS_SUBAGENTE`** (verificado por execução Python direta:
resultado `False` para os 4). Portanto, chegam ao principal por omissão no deny-list.

Resultado: todas as 28 skills visíveis no contexto de boot incluem essas 4 skills
dev-only **sem nenhum gating por usuário ou perfil no listing da meta-tool Skill**.

### Existe gating por usuário/perfil?

**Parcialmente — apenas para WRITE da skill gerindo-agente.**

`app/agente/config/permissions.py:410-429` implementa `_classify_gerindo_write()`: detecta
execução de subcomandos WRITE (`approve/reject/promote-batch/review/run/respond`) da skill
`gerindo-agente` via Bash e os nega universalmente (`permissions.py:677-687`).

Para as outras 3 skills (`consultando-sentry`, `diagnosticando-banco`, `padronizando-docs`):
**sem gating de execução**. Podem ser invocadas via Skill tool por qualquer usuário.

Não existe gating de listing por `user_id`, `is_admin` ou perfil no `_discover_skills_from_project()`.
O código não faz filtragem por usuário — todas as skills não-excluídas chegam a todos os usuários.

---

## 2. Como o frontmatter chega ao contexto (SDK CLI + truncamento)

### Mecanismo de carga

O SDK CLI (`cli.js`, função `sY7`) carrega automaticamente todos os arquivos
`.claude/skills/*/SKILL.md` que aparecem na lista `skills=` passada nas options.
O campo `description` do frontmatter YAML de cada SKILL.md é concatenado como
`- nome: description` para montar a description da meta-tool `Skill`.

### Truncamento de 16K / 25 skills

Documentado em `skills_whitelist.py:3-34`:

> "A description da meta-tool `Skill` é montada pela CLI (cli.js função `sY7`)
> concatenando `- nome: description` de TODAS as skills do listing. Com 46 skills
> (~48.7K chars) isso excede o budget de caracteres da tool (16K default / 8K
> efetivo via fator `A*0.08`), e o CLI TRUNCA cada description proporcionalmente
> (~150-320 chars/skill) — descartando as cláusulas de desambiguação
> (USAR/NÃO USAR PARA, que ficam no fim) e degradando o roteamento de skills."

O truncamento é do CLI JavaScript, não do Python. A SDK_CHANGELOG.md (mencionado em
`app/agente/CLAUDE.md`) documenta o comportamento na versão 0.1.77 (adoção do campo
`skills` nativo no SDK). A Solução B reduz o principal de 46 para ~25 skills via deny-list.

As 28 skills no contexto de boot são todas as skills do `.claude/skills/` não excluídas
pela deny-list (46 total - 25 excluídas = 21, mas `carregando-motos-assai` e
`consultando-venda-loja` estão no listing, resultando em 28 — o total exato
depende do número real de diretórios com SKILL.md em `.claude/skills/`).

---

## 3. skill_hints: gerador, flag, algoritmo, por que sugere skills incoerentes

### Arquivo:linha do gerador

`app/agente/sdk/context_enrichment.py:122-155` — função `build_skill_hints_block(query, limit=8)`.

Chamada em `app/agente/sdk/hooks.py:1447-1450`:
```python
if USE_AGENT_SKILL_RAG and prompt:
    from .context_enrichment import build_skill_hints_block
    _skill_hints = build_skill_hints_block(prompt)
```

### Flag exata

```
app/agente/config/feature_flags.py:1017
USE_AGENT_SKILL_RAG = os.getenv("AGENT_SKILL_RAG", "false").lower() == "true"
```

**Em produção (verificado em `.env`): `AGENT_SKILL_RAG=true`** — portanto ATIVA.

### Algoritmo

`rank_skills_for_query()` em `context_enrichment.py:55-115`:

1. Chama `capability_registry.build_registry()` para obter skills com `available_to_principal=True`
2. Tokeniza a query (lowercase, split em espaços e pontuação via `re.findall(r'\w+', query.lower())`)
3. Para cada skill: combina `name + description`, tokeniza, calcula score = intersecção de tokens
4. Fallback: se score=0, verifica substring direto para tokens com len>=4
5. Ordena por score decrescente, retorna top-N (default 8)

**Problema central**: algoritmo é puro token-overlap, zero semântica. A query da sessão
boot era algo como "me mostra o contexto de boot do agente" (query capturada no boot de
09h44 do dia 09/06). Palavras como "contexto", "boot", "agente", "mostra" fazem overlap
com descrições de skills que contêm essas palavras (ex: "carregamento" pode ter "carregar"
com overlap em "carga" ou "operando-portal-atacadao" pode ter "portal" + "agente").

### Por que sugeriu skills incoerentes

Skills sugeridas no boot:
`gerando-artifact, exportando-arquivos, operando-portal-atacadao, operando-ssw,
padronizando-docs, acessando-ssw, carregando-motos-assai, consultando-venda-loja`

**Causa raiz em dois níveis**:

1. **Bug de classificação no whitelist** (`carregando-motos-assai`, `consultando-venda-loja`):
   Essas skills são do domínio Assai/HORA mas **não estão em `SKILLS_DELEGADAS_SUBAGENTE`**.
   `carregando-motos-assai` não está em `SKILLS_DOMINIO_ASSAI` (que tem apenas 6 skills).
   `consultando-venda-loja` também não consta na deny-list. Portanto, aparecem no listing
   do principal e são elegíveis para skill_hints.

2. **Algoritmo de token-overlap fraco**: para uma query sobre "contexto/boot/agente",
   as descrições de skills com palavras gerais fazem overlap espúrio. Por exemplo,
   `padronizando-docs` contém "antes de criar/editar doc ou script"; `acessando-ssw`
   contém "SSW" + contexto operacional; `gerando-artifact` contém "artifact" + "skill".

---

## 4. world_model: gerador, flag, por que classifica entidades erradas

### Arquivo:linha do gerador

`app/agente/sdk/context_enrichment.py:177-256` — função `build_world_model_block(user_id, query)`.

Chamada em `app/agente/sdk/hooks.py:1462-1466`:
```python
if USE_AGENT_WORLD_MODEL_INJECT and user_id and prompt:
    from .context_enrichment import build_world_model_block
    _world_model = build_world_model_block(user_id=user_id, query=prompt)
```

A fonte das entidades é `query_ontology_entities()` de `app/agente/tools/ontology_query_tool.py`
(importada no nível de módulo em `context_enrichment.py:48` para permitir monkeypatch em testes).

### Flag exata

```
app/agente/config/feature_flags.py:1031
USE_AGENT_WORLD_MODEL_INJECT = os.getenv("AGENT_WORLD_MODEL_INJECT", "false").lower() == "true"
```

**Em produção (verificado em `.env`): `AGENT_WORLD_MODEL_INJECT=true`** — portanto ATIVA.

### Por que classifica ODOO/CARTEIRA_PRINCIPAL como [produto] e GRAFENO/SICOOB como [transportadora]

O vocabulário controlado de entity_types em `knowledge_graph_service.py:61-65`:

```python
_VALID_ENTITY_TYPES = frozenset({
    'uf', 'pedido', 'cnpj', 'valor', 'transportadora', 'produto',
    'cliente', 'fornecedor', 'usuario', 'processo', 'conceito',
    'campo', 'termo',
})
```

**Origem das entidades incorretas**: os dados vêm da tabela `agent_ontology_entities`
populada pelo `knowledge_graph_service.py` durante a extração de entidades das
sessões (Layer 1 regex + Layer 2 Voyage + Layer 3 Sonnet). O problema é de **qualidade
dos dados do grafo**, não do schema de tipos.

- **ODOO**, **CARTEIRA_PRINCIPAL**, **PEDIDO-DE-VENDA**, **STOCK.QUANT** como `[produto]`:
  O extrator provavelmente classificou esses nomes como "produto" em sessões onde o contexto
  era "trabalhei com o produto Odoo" ou "o produto CARTEIRA_PRINCIPAL existe no sistema".
  O entity_type `produto` é muito genérico e capturou termos de sistema como se fossem
  produtos físicos. Sem schema de tipos mais refinado, `produto` se torna um catch-all.

- **GRAFENO:E**, **SICOOB:A** como `[transportadora]`:
  O sufixo `:E`/`:A` sugere que são entidades com qualifier. SICOOB é um banco, não
  transportadora — foi classificado incorretamente pelo extrator nas sessões.
  GRAFENO pode ser uma transportadora real mas `:E`/`:A` são qualificadores de status
  não documentados. Qualidade dos dados reflete o que o Sonnet extraiu nas sessões.

**Raiz estrutural**: o `build_world_model_block` retorna o top-5 por tipo das entidades
mais mencionadas na ontologia — sem validação de qualidade, apenas por `mention_count`.
Se a ontologia está contaminada com entidades mal classificadas, elas aparecem no bloco.

---

## 5. routing_context (user_domain/preferred_skills/active_traps): gerador, flag, fonte

### Arquivo:linha do gerador

`app/agente/sdk/memory_injection.py:644-770` — função `_build_routing_context(user_id)`.

Chamada em `memory_injection.py:922` dentro do pipeline de injeção de memórias.

Não há feature flag isolada para routing_context — é parte do pipeline de memórias
controlado por `USE_OPERATIONAL_DIRECTIVES` (para o sub-bloco) e pelo pipeline geral.

### user_domain

Computado por `_compute_user_domain(user_id)` (`memory_injection.py:392-436`):
- Consulta últimas 10 `AgentSession` com `summary` preenchido (JSON JSONB)
- Combina `resumo_geral` + `alertas` de cada session summary
- Aplica keyword matching via `_DOMAIN_KEYWORDS` (`memory_injection.py:357-368`)
- Retorna o domínio com mais hits

Para Rafael (user_id=1), as sessões recentes têm keywords de `admin`
("diagnóstico", "auditoria", "memórias", "bug", "investigar") → domínio = `admin`.

### preferred_skills

Vem de `_DOMAIN_SKILLS` (`memory_injection.py:371-378`):

```python
_DOMAIN_SKILLS = {
    'expedicao': ['gerindo-expedicao', 'cotando-frete', 'analista-carteira'],
    'odoo_compras': ['validacao-nf-po', 'conciliando-odoo-po', 'recebimento-fisico-odoo', 'especialista-odoo'],
    'odoo_financeiro': ['executando-odoo-financeiro', 'rastreando-odoo', 'razao-geral-odoo'],
    'frete': ['cotando-frete', 'gerindo-carvia'],
    'ssw': ['acessando-ssw', 'operando-ssw', 'gestor-ssw'],
    'admin': ['gerindo-agente', 'diagnosticando-banco', 'consultando-sentry'],
}
```

**Por que sugeriu `gerindo-agente/diagnosticando-banco/consultando-sentry`**:
É um mapeamento hardcoded em `_DOMAIN_SKILLS['admin']`. O domínio `admin` foi inferido
do histórico de sessões de Rafael (que faz diagnósticos de infra, memoria, bugs). O
mapeamento `admin → [gerindo-agente, diagnosticando-banco, consultando-sentry]` foi
definido explicitamente no código — **não é derivado de uso histórico real de skills**.

É um mapeamento de design intencional (domínio admin → skills de admin), mas Rafael
aponta (R-3, R-7) que essas skills são dev-only e a pergunta é se o agente web as usa
de fato. O mapeamento é estático e não verifica se Rafael/outros usuários invocam essas
skills em produção.

### active_traps

Vem de `AgentMemory.query` filtrando `/memories/empresa/armadilhas/` pelo domínio
computado. Para `admin`, usa path segments `['geral', 'sistema', 'agente']`.
(`_DOMAIN_PATH_SEGMENTS` em `memory_injection.py:382-389`).

---

## 6. Remoção limpa de skill_hints + world_model (decisão R-1 do Rafael)

### Opção A: apenas desligar flags no Render (sem tocar código)

Remover `AGENT_SKILL_RAG=true` e `AGENT_WORLD_MODEL_INJECT=true` do `.env` e das
env vars do Render. Os guards `if USE_AGENT_SKILL_RAG` e `if USE_AGENT_WORLD_MODEL_INJECT`
no `hooks.py:1446,1462` fazem com que os blocos simplesmente não sejam gerados.

Impacto: zero código modificado. Rollback instantâneo.

### Opção B: remoção completa do código (se Rafael confirmar que as flags serão removidas)

Arquivos a tocar:

#### Obrigatórios (geradores):

| Arquivo | Linhas | O que fazer |
|---------|--------|-------------|
| `app/agente/config/feature_flags.py` | 1008-1031 | Remover os 2 blocos de flag (`USE_AGENT_SKILL_RAG` e `USE_AGENT_WORLD_MODEL_INJECT`) |
| `app/agente/sdk/hooks.py` | 1440-1468 | Remover os 2 blocos try/except de skill_hints e world_model; atualizar linha 1470 (condicional) e 1471 (full_context) e 1479-1480 (log) |
| `app/agente/sdk/context_enrichment.py` | arquivo inteiro (~284 linhas) | **Arquivo pode ser removido completamente** se `build_skill_hints_block` e `build_world_model_block` não forem usados em mais nenhum lugar. Confirmar com grep antes. |

#### Testes:

| Arquivo | O que fazer |
|---------|-------------|
| `tests/agente/sdk/test_context_enrichment.py` | Arquivo inteiro pode ser removido (22 testes todos para as funções removidas) |

#### Documentação/scripts (secundário):

| Arquivo | Linhas/seções | O que fazer |
|---------|---------------|-------------|
| `docs/blueprint-agente/EXECUCAO.md` | linhas 122-123, 257-258, 286, 440-441 | Atualizar estado de F4/F5+D5 como "REMOVIDO" |
| `docs/blueprint-agente/BLUEPRINT_MESTRE.md` | seção Onda 4, linha 135+ | Atualizar referências |
| `docs/blueprint-agente/VALIDACAO.md` | linhas 34-35, 78-79, 871-985 | Remover ou marcar como obsoleto |
| `docs/blueprint-agente/PROMPT_PROXIMA_SESSAO_VALIDACAO.md` | linhas 43, 74 | Atualizar referências |
| `docs/blueprint-agente/ROADMAP.md` | linha 132 (O7.4) | Atualizar status |
| `.claude/skills/gerindo-agente/scripts/infra.py` | linhas 78-79 | Remover entradas de `USE_AGENT_SKILL_RAG` e `USE_AGENT_WORLD_MODEL_INJECT` da tabela de flags |
| `app/agente/sdk/_sanitization.py` | linha 50 | `'routing_context'` pode ser mantido (routing_context ≠ world_model/skill_hints) |

#### Nota sobre `rank_skills_for_query` e `capability_registry`:

`rank_skills_for_query()` (`context_enrichment.py:55-115`) e `build_registry()` são usados
EXCLUSIVAMENTE pelo skill_hints. Se o arquivo `context_enrichment.py` for removido,
o `capability_registry.py` pode permanecer (usado por outros caminhos futuros — S0c).
Verificar: `grep -rn "rank_skills_for_query\|build_registry" app/ --include="*.py"` antes de remover.

#### Variáveis de ambiente no Render:

Remover as env vars `AGENT_SKILL_RAG` e `AGENT_WORLD_MODEL_INJECT` do serviço
`sistema-fretes` no Render (se existirem como configuração separada do `.env`).

---

## 7. Problema adicional encontrado: carregando-motos-assai + consultando-venda-loja não excluídas

**`carregando-motos-assai`** (skill do domínio Assai) e **`consultando-venda-loja`**
(skill do domínio Lojas HORA) estão no listing do principal por ausência na deny-list.

Verificado:
- `carregando-motos-assai` NOT in `SKILLS_DELEGADAS_SUBAGENTE` (Python direto)
- `consultando-venda-loja` NOT in `SKILLS_DELEGADAS_SUBAGENTE` (Python direto)

`SKILLS_DOMINIO_ASSAI` tem 6 skills mas não inclui `carregando-motos-assai` nem
`registrando-evento-moto-assai` — wait, `registrando-evento-moto-assai` SIM está.
Confirmar: `carregando-motos-assai` definitivamente ausente.

`SKILLS_DOMINIO_HORA` tem 5 skills mas `consultando-venda-loja` não está.

**Recomendação**: adicionar essas 2 skills às suas respectivas deny-lists:
- `SKILLS_DOMINIO_ASSAI`: adicionar `carregando-motos-assai`
- `SKILLS_DOMINIO_HORA` (ou novo grupo): adicionar `consultando-venda-loja`

---

## Resumo de fontes

| Item | Arquivo:linha |
|------|---------------|
| Deny-list principal | `app/agente/config/skills_whitelist.py:99-104` |
| `_discover_skills_from_project()` | `app/agente/sdk/client.py:83-124` |
| `options_dict["skills"]` set | `app/agente/sdk/client.py:1625` |
| Flag `AGENT_SKILL_RAG` | `app/agente/config/feature_flags.py:1017` |
| Flag `AGENT_WORLD_MODEL_INJECT` | `app/agente/config/feature_flags.py:1031` |
| `build_skill_hints_block()` | `app/agente/sdk/context_enrichment.py:122-155` |
| `build_world_model_block()` | `app/agente/sdk/context_enrichment.py:177-256` |
| Hook que injeta ambos | `app/agente/sdk/hooks.py:1440-1468` |
| `_build_routing_context()` | `app/agente/sdk/memory_injection.py:644-770` |
| `_DOMAIN_SKILLS` (preferred_skills) | `app/agente/sdk/memory_injection.py:371-378` |
| `_compute_user_domain()` | `app/agente/sdk/memory_injection.py:392-436` |
| Gate gerindo-agente WRITE | `app/agente/config/permissions.py:410-429, 677-687` |
| Testes skill_hints/world_model | `tests/agente/sdk/test_context_enrichment.py` (22 testes) |
| `.env` flags ativas em prod | `.env:254,256` (`AGENT_SKILL_RAG=true`, `AGENT_WORLD_MODEL_INJECT=true`) |
