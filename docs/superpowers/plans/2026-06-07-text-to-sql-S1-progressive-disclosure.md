<!-- doc:meta
tipo: how-to
camada: L3
sot_de: plano S1 — progressive disclosure de schema (mapa navegavel p/ o Opus)
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-07
-->

# S1 — Progressive Disclosure de Schema

> **Papel:** plano executavel da sessao dedicada ao subsistema S1. Da ao agente (Opus)
> um caminho de descoberta de schema em camadas — intencao → tabelas candidatas →
> schema detalhado — para que ele escreva SQL sobre as tabelas certas sem adivinhar.
> Faz parte do pacote `2026-06-07-text-to-sql-arquitetura-MASTER` (ler o MASTER antes).
> Depende de S0 (gerador idempotente).
>
> **STATUS: EXECUTADO em 2026-06-07** (worktree `worktree-text-to-sql-S1`; detalhe e
> evidencia no rastreamento append-only do MASTER). Refinamentos da execucao vs as 4
> decisoes fechadas: (1) a fusao virou **semantica primaria + append textual** — a RRF
> inicial DILUIA a semantica (provado por A/B real); (2) freshness = textual fresca +
> reindex diario por `content_hash` (o gatilho do S0 nao toca banco, premissa revista);
> (4) modelo dedicado **voyage-4-large** no catalogo (A/B: top-3 coloquial 73%->93%).

## Indice

- [Contexto herdado](#contexto-herdado)
- [Objetivo e criterio de sucesso](#objetivo-e-criterio-de-sucesso)
- [Escopo](#escopo)
- [Arquivos-alvo](#arquivos-alvo)
- [Abordagens](#abordagens)
- [Design proposto](#design-proposto)
- [Edge cases](#edge-cases)
- [Pre-mortem](#pre-mortem)
- [Decisoes em aberto (perguntar na sessao)](#decisoes-em-aberto-perguntar-na-sessao)
- [Testes e verificacao](#testes-e-verificacao)
- [Conformidade](#conformidade)

## Contexto herdado

Achado central da investigacao (MASTER): **o Opus esta cego para o mapa de 303
tabelas.** O catalogo leve (`catalog.json`) alimenta SO o prompt do Generator Haiku
(`SchemaProvider.get_catalog_text` em `text_to_sql.py:470` → `SQLGenerator`). O agente
Opus descobre schema UMA tabela por vez via `mcp__schema__consultar_schema`
(`schema_mcp_tool.py:328`), mas precisa **adivinhar o nome da tabela primeiro**. Nao ha
"busca de tabela por intencao" exposta ao Opus.

Dois problemas correlatos:
- **key_fields sao lixo semantico**: `generate_schemas.py:538-545` define `key_fields`
  como as 3 PRIMEIRAS colunas do modelo (quase sempre `id, <fk>, <fk>`). Pouco
  informativo para escolher tabela.
- **303 tabelas sem agrupamento**: nao ha eixo de dominio (carteira, faturamento,
  embarque, financeiro...) para navegar.

Ja existe infraestrutura reaproveitavel: `EmbeddingService` + pgvector (usado em
`text_to_sql.py:1989-1996` para `search_sql_templates`) e o `relationships.json`.

## Objetivo e criterio de sucesso

**Objetivo:** dado um pedido em linguagem natural, o agente localiza as tabelas certas
em 1-2 chamadas de tool, sem adivinhar nomes.

**Criterio de sucesso (verificavel):**
1. Nova tool `buscar_tabelas("pedidos pendentes do Atacadao")` retorna
   `carteira_principal` no topo, com descricao e campos relevantes — sem o agente saber
   o nome de antemao.
2. `key_fields` do catalogo passam a refletir campos semanticamente uteis (chaves de
   negocio + filtros comuns), nao as 3 primeiras colunas.
3. O catalogo expoe agrupamento por dominio navegavel.

## Escopo

**Inclui:**
- Tool MCP de descoberta por intencao (camada 1 do disclosure).
- Melhoria de `key_fields` (heuristica de relevancia) no gerador.
- Agrupamento de tabelas por dominio no catalogo.

**Exclui:**
- Enriquecer descricoes/regras (→ S2; S1 consome o que existir).
- Mudar quem escreve o SQL ou o contrato da tool (→ S3).
- Idempotencia do gerador (→ S0; S1 assume S0 pronto).

## Arquivos-alvo

| Arquivo | Mudanca |
|---|---|
| `app/agente/tools/schema_mcp_tool.py` | nova tool `buscar_tabelas` (camada 1) |
| `.claude/skills/consultando-sql/scripts/generate_schemas.py` | `key_fields` por relevancia + campo de dominio/grupo |
| `.claude/skills/consultando-sql/schemas/catalog.json` | (regenerado) estrutura com dominio + key_fields uteis |
| `app/agente/prompts/system_prompt.md` | orientar o fluxo intencao → tabelas → schema |
| `app/agente/config/skills_whitelist.py` / registro de tools | expor a nova tool |

## Abordagens

**A. Busca semantica (embeddings) sobre o catalogo (RECOMENDADA).**
Indexar `nome + descricao + key_fields` de cada tabela em pgvector; `buscar_tabelas`
faz top-N por similaridade. Reusa `EmbeddingService` ja existente. Trade-off: depende de
embeddings ligados; melhor recall para intencao vaga. Fallback textual quando off.

**B. Busca textual (keyword/ILIKE) sobre o catalogo.**
`buscar_tabelas` faz match de termos do dominio contra nome+descricao. Trade-off: zero
dependencia de embeddings; recall pior para sinonimos. Bom como fallback de A.

**C. Catalogo agrupado estatico no prompt (REJEITADA como solucao unica).**
Injetar o catalogo inteiro agrupado por dominio no contexto do Opus. Trade-off: custo de
tokens alto e nao escala a 303 tabelas; serve so como material para a tool, nao como
entrega ao prompt.

Recomendacao: **A com fallback B**; agrupamento por dominio como metadado que enriquece
o resultado das duas.

## Design proposto

- **Camada 1 — `buscar_tabelas(intencao, limite=N)`**: retorna lista de tabelas
  candidatas `{tabela, descricao, key_fields, dominio, score}`. Read-only. Respeita as
  mesmas regras de bloqueio por `user_id` (nao sugerir tabela bloqueada a quem nao pode).
- **Camada 2 — `consultar_schema(tabela)`** (ja existe): detalhe completo. O fluxo vira
  intencao → `buscar_tabelas` → `consultar_schema` → escreve SQL.
- **key_fields por relevancia** (no gerador): heuristica = PK + FKs + campos de filtro
  comuns (ex.: `*status*`, `*data*`, `ativo`, `num_*`, `cod_*`, `cnpj*`) limitado a N.
  Definir a heuristica na sessao; deve ser deterministica (compativel com S0).
- **dominio/grupo**: derivar de um mapa modulo→prefixo de tabela (curado) ou do app de
  origem do modelo; gravar no catalog por tabela.

## Edge cases

- **Intencao ambigua** ("dados do cliente") → retornar top-N de dominios distintos, nao
  so 1; deixar o agente escolher.
- **Tabela bloqueada** para o user → nunca aparecer em `buscar_tabelas` (mesma matriz de
  permissao do executor; ver S3 para a fonte unica de bloqueio).
- **Embeddings off** → cair para busca textual sem erro.
- **Sinonimos de dominio** (palmito = produto) → resolver via `resolvendo-entidades`
  existente ou deixar para o agente; nao reinventar resolucao de entidade aqui.
- **Tabela sem descricao rica** (pre-S2) → `buscar_tabelas` ainda funciona por nome;
  melhora quando S2 enriquecer.

## Pre-mortem

> "3 meses depois, S1 falhou. Por que?"
1. **`buscar_tabelas` retorna ruido** (top-N irrelevante) → agente perde tempo. →
   Mitigacao: medir precisao@N com um golden set pequeno de intencoes reais; ajustar a
   indexacao (incluir key_fields melhora muito).
2. **Heuristica de key_fields ficou arbitraria** e piorou alguns casos → Mitigacao:
   validar contra as tabelas mais usadas (telemetria de `save_successful_query`).
3. **Agente ignora a tool nova** e continua adivinhando → Mitigacao: orientacao no
   system_prompt + a tool de schema sugerir `buscar_tabelas` quando a tabela nao existe.
4. **Dominio mal mapeado** (tabela no grupo errado) → Mitigacao: mapa curado, nao
   inferencia fragil; revisavel.

## Decisoes fechadas (2026-06-07)

1. **Semantica primaria, com fallback textual** — `buscar_tabelas` usa embeddings; cai
   para textual se off. **Dois requisitos do usuario**: (a) FRESHNESS — o indice semantico
   das tabelas e reindexado no MESMO gatilho que regenera schemas (S0), para nunca ficar
   velho; (b) VALIDACAO — golden set de intencoes→tabela mede precisao@N (sem isso, nao
   confiar na semantica).
2. **`key_fields` = conjunto MINIMO para ESCOLHER a tabela** (nivel de detalhe delegado ao
   autor): chave(s) de negocio (ex.: `num_pedido`, `cod_produto`, `numero_nf`) + 1-3
   campos de filtro/dimensao mais comuns (status, data principal, cliente/cnpj), teto ~5.
   NAO incluir `id` tecnico nem campos de auditoria. Racional: o nivel 1 (escolher tabela)
   so precisa de "do que trata e por quais campos filtro"; o detalhe completo vem no nivel
   2 (`consultar_schema`).
3. **Dominio automatico** — derivar do app de origem do modelo (`app/carteira/models*` →
   grupo "Carteira"). Zero curadoria manual.
4. **Tool nova separada** — `buscar_tabelas` e tool propria (responsabilidade unica), nao
   um modo da `mcp__schema`.

## Testes e verificacao

- pytest: golden set de 10-20 intencoes → afirma que a tabela esperada esta no top-N.
- pytest: `key_fields` geradas para tabelas-chave (carteira_principal, separacao,
  faturamento_produto) contem as chaves de negocio esperadas.
- Idempotencia preservada (S0): regenerar com a nova heuristica nao polui alem do
  esperado.

## Conformidade

- Nova tool segue padrao Enhanced MCP (`_mcp_enhanced.py`, `outputSchema` +
  `structuredContent`), como `consultar_schema`.
- Registrar a tool no servidor MCP e na descoberta de tools do agente.
- Sem DDL salvo se a indexacao de embeddings exigir tabela/coluna nova → entao migration
  dupla (Python + SQL) conforme regra do projeto.

## Prompt de arranque da sessao (copiar na nova sessao)

> Estado em 2026-06-07: **S0+S0b e S2 ja estao em PROD** (`dc1c8573e`). S1 e a proxima
> sessao; S3 vem depois de S1. Cole o bloco abaixo numa nova sessao do Claude Code (dev).

```text
Vou executar o subsistema S1 — Progressive Disclosure do pipeline text-to-sql do Agente Web.

LEIA ANTES (nesta ordem):
1. docs/superpowers/specs/2026-06-07-text-to-sql-arquitetura-MASTER-design.md
   (MASTER: achados, tese, 7 invariantes, gates, rastreamento append-only).
2. docs/superpowers/plans/2026-06-07-text-to-sql-S1-progressive-disclosure.md
   (o plano que vou executar — as 4 decisoes ja estao FECHADAS).

JA ESTA EM PROD (NAO refazer):
- S0+S0b (2d92fee57): generate_schemas.py idempotente (--check, write-if-changed, ordenacao
  canonica) + auto-descoberta de modulos (_discover_model_modules) + allow-list
  ORFAOS_VIVOS_PRESERVAR + fix getdoc. S1 ASSUME isso pronto.
- S2 (dc1c8573e): overlay RUNTIME de business_rules/query_hints no SchemaProvider
  (_merge_overlay_into_schema + _enrich_schema) + 46 overlays + descricao na fonte.
  S1 CONSOME essas descricoes (melhoram o recall de buscar_tabelas).

OBJETIVO S1: dar ao Opus descoberta em camadas (intencao -> buscar_tabelas -> consultar_schema
-> SQL) para ele parar de adivinhar nome de tabela. Decisoes JA fechadas no plano: (1) busca
semantica via embeddings com fallback textual + FRESHNESS (reindexar no mesmo gatilho do S0) +
golden set de validacao; (2) key_fields = conjunto MINIMO p/ escolher a tabela (chaves de
negocio + 1-3 filtros, teto ~5, sem id tecnico); (3) dominio derivado do app de origem do
modelo (zero curadoria); (4) buscar_tabelas = tool propria. Refine so o design fino.

COMO TRABALHAR (protocolo do MASTER):
1. Worktree isolada de origin/main:
   git worktree add .claude/worktrees/text-to-sql-S1 -b worktree-text-to-sql-S1 origin/main
2. TDD com pytest DETERMINISTICO (invariante 6: SEM evals LLM caros; golden set = teste pytest).
3. Preserve as 7 invariantes — em especial: rode generate_schemas.py --check apos mexer em
   key_fields/dominio (idempotencia NAO pode regredir); tabela bloqueada por user_id NUNCA
   pode vazar em buscar_tabelas (mesma matriz de permissao do executor).
4. Feche o Gate S1 do MASTER com EVIDENCIA (comando/teste), nao por afirmacao.
5. Registre a linha no rastreamento append-only do MASTER e PARE antes do push
   (push = deploy PROD; aguardar OK do usuario).

ARQUIVOS-ALVO: app/agente/tools/schema_mcp_tool.py (nova tool buscar_tabelas);
generate_schemas.py (key_fields por relevancia + dominio); catalog.json (regenerado);
app/agente/prompts/system_prompt.md (orientar o fluxo); registro de tools no MCP.

GOTCHAS DE AMBIENTE:
- Use o Python do .venv da raiz (/home/rafaelnascimento/projetos/frete_sistema/.venv/bin/python)
  para pytest e gerador; a worktree nao tem .env proprio (testes determinist. nao precisam DB).
- Hook pre-commit UI-lint chama `python` no PATH -> ative o .venv antes do commit
  (o S1 nao toca UI; deve passar com 0 violacoes).
- Se a indexacao de embeddings exigir tabela/coluna nova -> migration DUPLA (Python + SQL
  idempotente). NUNCA use [skip render].
```
