# Atualizacao Sentry — 2026-05-25-1

**Data**: 2026-05-25
**Issues avaliadas**: 1
**Issues corrigidas**: 1
**Issues ignoradas**: 0
**Issues fora de escopo**: 0

## Resumo

Triagem encontrou apenas 1 issue unresolved em producao (PYTHON-FLASK-M5,
recorrente desde 17/04). Causa raiz: o validator deterministico do
text-to-SQL so resolvia campos qualificados quando o prefix era nome de
tabela conhecido — aliases como `s.qtd_saldo_produto_pedido` ou
`fp.qtd_faturada` escapavam da validacao e chegavam no PostgreSQL.
Implementado `_extract_alias_map` + extensao de `_check_qualified_fields`
para resolver aliases parseando `FROM/JOIN tabela [AS] alias`. Suite
inline de 6 casos validada com sucesso (2 fixes corretos + 4 sem
falso-positivo).

## Queries Executadas

| Query | Resultado |
|-------|-----------|
| `is:unresolved environment:production` (sort=freq, limit=50) | 1 issue (M5) |
| `is:unresolved` (todos os ambientes, limit=50) | 1 issue (M5) |

Backlog efetivamente zerado. Comparado a 2026-05-18 (57 issues),
56 issues foram aparentemente auto-resolvidas (instabilidade XML-RPC
CIEL IT cessou, migrations transitorias expiraram a janela de
retencao Sentry, e/ou fixes anteriores reduziram surface area).

## Issues Corrigidas

### PYTHON-FLASK-M5: [TEXT_TO_SQL] UndefinedColumn em colunas com alias

- **Frequencia**: 6 eventos production, 0 usuarios afetados
- **First seen**: 2026-04-17
- **Last seen**: 2026-05-25 12:35:51Z (~26 min antes da triagem)
- **Culprit**: `chat claude-haiku-4-5-20251001`
- **Releases afetados**: `a937748b2baf...`, `b156804cb88b...`
- **Eventos amostrais** (mesmo groupID 7420540453):
  - `s.qtd_saldo_produto_pedido does not exist` (Separacao tem `qtd_saldo`)
  - `fp.qtd_faturada does not exist` (FaturamentoProduto tem `qtd_produto_faturado`)
  - `qtd_faturada does not exist` (variante sem prefixo, ja coberta pelo Check 3)

#### Causa Raiz

`SQLDeterministicValidator._check_qualified_fields` em
`.claude/skills/consultando-sql/scripts/text_to_sql.py:917` so validava
campos quando `prefix.field` tinha `prefix` igual a nome de tabela
conhecido. Aliases comuns no SQL gerado por Haiku (`s`, `fp`, `cp`,
`em`) eram pulados sob comentario "assumir alias e pular (Haiku
valida)" — mas o Haiku Evaluator (mesma familia do Generator) tambem
nao detectava o erro de coluna, e o SQL chegava no PostgreSQL e
estourava `UndefinedColumn` em runtime.

O Check 3 (`_check_unqualified_select_fields`, linha 844) ja
cobria o caso de campo sem prefixo MAS apenas quando `tables_used`
tinha exatamente 1 tabela — nao funcionava para SQL com alias ou
JOIN. Comentario inline em `_check_unqualified_select_fields:820`
ja citava explicitamente "Sentry M5" como motivacao, confirmando
que a issue era conhecida mas a cobertura era incompleta.

#### Fix

`.claude/skills/consultando-sql/scripts/text_to_sql.py`:

1. **Novo metodo `SQLDeterministicValidator._extract_alias_map(sql, field_map)`**:
   - Parseia `FROM/JOIN tabela [AS] alias` via regex
   - Constroi mapa `alias_lower -> tabela_lower` so para tabelas
     em `field_map` (com schema conhecido)
   - Filtra palavras-chave SQL (`on`, `where`, `inner`, `left`,
     `join`, `lateral`, ...) que aparecem apos nome de tabela e
     NAO sao aliases
   - Conservador: nao sobrescreve nome de tabela conhecido;
     primeira ocorrencia vence em colisoes raras

2. **`_check_qualified_fields` extendido**:
   - Consulta `alias_map` se prefix nao for tabela direta
   - Mantem fallback conservador (skip + Haiku decide) se
     prefix nao for nem tabela nem alias resolvivel — cobre
     subqueries, CTEs, escopos aninhados
   - Mensagem de erro agora distingue:
     - `tabela.campo` -> "nao consta em fields[] de 'tabela'"
     - `alias.campo` -> "alias 'X' = 'tabela', campo nao consta"

#### Verificacao

Suite inline de 6 casos rodada com sucesso (`source .venv/bin/activate
&& python <<EOF ... EOF`):

| Caso | Resultado |
|------|-----------|
| Sentry M5 cenario 1: `s.qtd_saldo_produto_pedido` | CATCH OK |
| Sentry M5 cenario 2: `fp.qtd_faturada` | CATCH OK |
| SQL valida `AS s`: `s.qtd_saldo` em `separacao AS s` | sem falso-positivo |
| SQL valida JOIN: `s.qtd_saldo` + `fp.qtd_produto_faturado` | sem falso-positivo |
| Sem alias nome direto: `separacao.qtd_saldo` | sem falso-positivo |
| Subquery `x.algum_campo` (sem schema) | SKIP correto |

Tambem validado: `python -c "ast.parse(open(...))"` (sintaxe OK).

#### Arquivos Modificados

- `.claude/skills/consultando-sql/scripts/text_to_sql.py`
  - Linhas 917+ (`SQLDeterministicValidator`): novo metodo
    `_extract_alias_map` + extensao de `_check_qualified_fields`
  - Diff: +~70 linhas, -~10 linhas (substituicao do metodo)

#### Sentry

Marcada como `resolved` via `mcp__sentry__update_issue` com comentario
apontando o fix.

## Issues Ignoradas

(nenhuma)

## Issues Fora de Escopo

(nenhuma — triagem teve apenas 1 issue total)

## Metricas

- Issues abertas antes: 1
- Issues abertas depois: 0
- Reducao: 100%
- Issues criticas/altas no backlog: 0
- Issues 500 errors/data loss: 0

## Comparativo Historico

| Data | Avaliadas | Corrigidas | Ignoradas | Observacao |
|------|-----------|------------|-----------|------------|
| 2026-04-06 | varias | 0 | varias | Backlog limpo, so perf alerts |
| 2026-04-27 | 20 | 2 | 18 | PF cast, P3 ja resolvido |
| 2026-05-05 | 32 | 1 | 26 + 5 ja-fixed | Q6 + commits 2bbfcf23/b6c17646 |
| 2026-05-11 | 6 | 2 | 4 | RN carteira + RK custeio |
| 2026-05-18 | 57 | 0 | 57 | Odoo XML-RPC dominou (216+172 evts) |
| **2026-05-25** | **1** | **1** | **0** | **Backlog zerado + fix M5 def.** |

## Observacoes

- O comentario inline em `_check_unqualified_select_fields:820` ja
  mencionava "Sentry PYTHON-FLASK-M5" como motivacao — confirma que
  o problema ja era conhecido, mas o Check 3 nao cobria o caso de
  alias (so cobre tabela unica). O fix desta sessao fecha a lacuna.
- A regra de negocio `Separacao.qtd_saldo` vs
  `CarteiraPrincipal.qtd_saldo_produto_pedido` ja esta documentada
  em `.claude/references/modelos/REGRAS_CARTEIRA_SEPARACAO.md` e
  tambem em `memory/campos_gotchas.md` (MEMORY.md global). O fix
  nao depende de prompt do LLM — bloqueia o erro deterministicamente
  ANTES de chegar no banco, independente da qualidade do Haiku.
- **Sugestao futura (FORA DO ESCOPO desta triagem)**: adicionar
  testes pytest em `.claude/skills/consultando-sql/` para
  `SQLDeterministicValidator` — atualmente NAO ha testes; um teste
  pytest com os 6 casos validados em sessao garantiria regressao zero
  em proximos refactors do validator.

## Checklist Pre-Commit

- [x] Issues ordenadas por criticidade (1 issue, MEDIO)
- [x] Cada correcao testada localmente (suite inline 6 casos)
- [x] Nenhum fix introduz regressao conhecida (testes 3-6 confirmam)
- [x] Issues corrigidas marcadas como resolvidas no Sentry
- [x] Relatorio gerado com detalhes
- [x] historico.md atualizado
- [ ] Commits atomicos (deferido — usuario decide commit, ver instrucoes)
