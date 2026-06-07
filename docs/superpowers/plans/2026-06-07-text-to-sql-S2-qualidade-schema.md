<!-- doc:meta
tipo: how-to
camada: L3
sot_de: plano S2 — qualidade de schema (descricoes, regras, hints curados)
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-07
-->

# S2 — Qualidade de Schema

> **Papel:** plano executavel da sessao dedicada ao subsistema S2. Enriquece descricoes,
> regras de negocio e query hints das tabelas, de forma que sobreviva a regeneracao,
> elevando a precisao do SQL (do Opus e do fallback). Faz parte do pacote
> `2026-06-07-text-to-sql-arquitetura-MASTER` (ler o MASTER antes). Depende de S0.

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

Medicao da investigacao (MASTER): a qualidade dos schemas e rasa fora do nucleo.
- `business_rules` e `query_hints` existem SO nas 9 tabelas core (vem do `schema.json`,
  feito merge em `SchemaProvider.__init__` em `text_to_sql.py:425`). As 303
  `tables/*.json` individuais tem zero.
- Cobertura de descricao por campo: carteira_principal 88%, separacao 50%,
  faturamento_produto 50% (amostra real medida).
- As descricoes geradas vem de `extract_field_description` (`generate_schemas.py:381`):
  docstring/comment/Column info — pobre para a maioria.

Por que importa: descricao/regra/hint ruins fazem o Opus (e o fallback) escolherem campo
errado-mas-existente — o furo que o validador deterministico nao pega (ver MASTER, F2).
S2 ataca a causa de fundo: dar significado real aos campos.

Risco estrutural: **descricoes curadas dentro de `tables/*.json` GERADO sao apagadas na
proxima regeneracao.** Ja existe precedente de solucao: `schemas/overlays/` (linhagem),
carregado em `SchemaProvider.__init__:393-407` e merge em `get_table_schema`.

## Objetivo e criterio de sucesso

**Objetivo:** as tabelas mais usadas tem descricoes de campo ricas + regras de negocio +
query hints, e essa curadoria sobrevive a `generate_schemas.py`.

**Criterio de sucesso (verificavel):**
1. Curadoria fica em camada que NAO e sobrescrita pela regeneracao (overlay).
2. Top-N tabelas por uso real tem: descricao de tabela, >=90% campos com descricao,
   business_rules e query_hints preenchidos.
3. `consultar_schema` e `get_tables_schema_text` exibem a curadoria (merge correto).

## Escopo

**Inclui:**
- Mecanismo de curadoria que sobrevive a regeneracao (overlay).
- Priorizacao por uso (quais tabelas enriquecer primeiro).
- Permitir business_rules/query_hints por tabela individual (nao so as 9 core).

**Exclui:**
- Idempotencia do gerador (→ S0).
- Como o agente descobre tabela (→ S1; S2 alimenta a qualidade que S1 expoe).
- Logica de geracao de SQL (→ S3).

## Arquivos-alvo

| Arquivo | Mudanca |
|---|---|
| `.claude/skills/consultando-sql/schemas/overlays/` | overlays de curadoria (descricao/regra/hint) |
| `.claude/skills/consultando-sql/scripts/generate_schemas.py` | merge de overlay de curadoria no schema gerado |
| `.claude/skills/consultando-sql/scripts/text_to_sql.py` | `SchemaProvider` ja faz merge de overlay; estender para descricao/regra/hint se preciso |
| `.claude/skills/consultando-sql/schemas/schema.json` | (opcional) migrar regras das 9 core para o mesmo mecanismo |

## Abordagens

**A. Overlay de curadoria que o gerador faz merge (RECOMENDADA).**
Curadoria humana (e/ou assistida) em `schemas/overlays/<tabela>.json` com
`description`, `fields[].description`, `business_rules`, `query_hints`. O gerador, ao
escrever `tables/<tabela>.json`, faz merge do overlay POR CIMA da extracao automatica.
Curadoria nunca e perdida. Trade-off: 2 fontes por tabela; ganho = durabilidade +
separacao gerado/curado. Unifica o que ja existe para linhagem.

**B. Editar `tables/*.json` direto e marcar "nao regenerar".**
Curar no proprio arquivo gerado e o gerador respeitar um flag. Trade-off: fragil
(facil sobrescrever; mistura gerado e curado). REJEITADA.

**C. Geracao assistida por LLM em massa, sem revisao.**
LLM escreve descricoes para as 303. Trade-off: rapido, mas risco de descricao
plausivel-errada (o mesmo mal que queremos curar). REJEITADA como entrega direta;
aceitavel so como RASCUNHO que entra no overlay APOS revisao humana.

Recomendacao: **A**; LLM pode pre-popular rascunho do overlay, sempre com revisao antes
de efetivar.

## Design proposto

- Estender o conceito de `overlays/` (hoje linhagem) para incluir um overlay de
  **curadoria de schema** (description/fields/business_rules/query_hints).
- `generate_schemas.py`: apos extrair o schema automatico, aplicar overlay de curadoria
  (overlay vence em descricao; business_rules/query_hints vem do overlay). Determinismo
  preservado (compativel com S0).
- `SchemaProvider`: garantir que o merge de curadoria aparece em `consultar_schema`
  (`schema_mcp_tool.py:_format_schema`) e em `get_tables_schema_text`
  (`text_to_sql.py:552`).
- **Priorizacao por uso**: derivar ranking de tabelas dos SQLs bem-sucedidos
  (`save_successful_query` / indice de templates) e curar de cima para baixo.

## Edge cases

- **Overlay para tabela inexistente** (modelo removido) → gerador avisa, nao quebra.
- **Conflito overlay x extracao** (descricao em ambos) → overlay vence; documentar a
  precedencia.
- **Campo no overlay que nao existe mais** → avisar; nao injetar campo fantasma.
- **As 9 core (schema.json)** → decidir se migram para overlay (unificar) ou coexistem.
- **query_hints com SQL desatualizado** apos refactor de schema → S0/`--check` ou um
  teste deve sinalizar hints quebrados.

## Pre-mortem

> "3 meses depois, S2 falhou. Por que?"
1. **Curadoria foi perdida numa regeneracao** (overlay nao aplicado em algum caminho) →
   Mitigacao: teste que afirma que um overlay de curadoria aparece no `tables/*.json`
   gerado E em `consultar_schema`.
2. **Descricoes geradas por LLM entraram sem revisao e mentem** → Mitigacao: overlay so
   recebe conteudo revisado; LLM produz rascunho separado.
3. **Curamos 303 tabelas e a maioria nunca e consultada** (esforco desperdicado) →
   Mitigacao: priorizar por uso real; meta inicial = top-N, nao "todas".
4. **query_hints viraram fonte de SQL errado** (hint desatualizado) → Mitigacao:
   validar hints (parse/`EXPLAIN` opcional) no `--check` de S0.

## Decisoes fechadas (2026-06-07)

1. **Curar na FONTE para descricoes + overlay so para regras/hints ricos** (escolha do
   usuario: evitar "2 vias" onde der). Descricao de tabela e de campo mora nos proprios
   modelos SQLAlchemy (docstring + `comment`/`info` da coluna) — extraida automaticamente E
   sobrevive a regeneracao, sem overlay. So `business_rules` e `query_hints` (texto
   rico/multi-linha/SQL de exemplo, que nao cabe em comment de coluna) vivem em overlay
   estruturado. A sessao define a forma exata do overlay de regras/hints.
2. **Unificar as 9 core depois** — `schema.json` migra para o mesmo mecanismo de overlay
   de regras/hints apos o mecanismo provar valor (nao no primeiro passo).
3. **Curar top-40 por uso real** — priorizar pelas ~40 tabelas mais consultadas
   (telemetria de SQL bem-sucedido / indice de templates), nao as 303.
4. **LLM rascunha, humano revisa** — descricoes podem ser pre-escritas por LLM, mas so
   entram na fonte/overlay apos revisao (nunca direto).

## Testes e verificacao

- pytest: overlay de curadoria de 1 tabela → `tables/<t>.json` gerado contem a descricao
  curada; `consultar_schema` retorna ela.
- pytest: cobertura de descricao das top-N tabelas >= meta acordada.
- Idempotencia (S0) preservada com overlays aplicados.

## Conformidade

- Curadoria em `schemas/overlays/` (nunca em arquivo gerado).
- Sem DDL → sem migration (a nao ser que priorizacao por uso exija persistir telemetria).
- Compativel com o determinismo de S0 (overlays ordenados/estaveis).
