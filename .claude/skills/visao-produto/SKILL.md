---
name: visao-produto
description: >-
  Esta skill deve ser usada quando o usuario pede "tudo sobre palmito",
  "visao 360 do produto X", "cumpriram a programacao?", "programado vs
  produzido", ou precisa de dados cross-domain de produto (cadastro, estoque,
  custo, faturamento, carteira e producao em consulta unificada).
  Nao usar para apenas estoque sem visao completa (usar gerindo-expedicao),
  apenas cotacao de frete (usar cotando-frete), ou consultas analiticas
  agregadas de varios produtos (usar consultando-sql).

  NAO USAR QUANDO:
  - Apenas estoque sem visao completa: usar gerindo-expedicao
  - Apenas faturamento/vendas: usar consultando-sql
allowed-tools: Read, Bash, Glob, Grep
---

# Skill: visao-produto

## Proposito
Consulta cross-domain de produto. Agrega 7+ tabelas (CadastroPalletizacao, MovimentacaoEstoque, CarteiraPrincipal, Separacao, FaturamentoProduto, CustoConsiderado, ProgramacaoProducao) em uma visao unificada.

## Mapeamento Rapido

| Se a pergunta menciona... | Use este script | Com estes parametros |
|---------------------------|-----------------|----------------------|
| **Resumo completo de produto** ("tudo sobre palmito") | `consultando_produto_completo.py` | `--produto palmito` |
| **Producao vs realizado** ("cumpriram a programacao?") | `consultando_producao_vs_real.py` | `--produto palmito --de 2026-01-01 --ate 2026-01-31` |
| **Producao geral** (sem produto especifico) | `consultando_producao_vs_real.py` | `--de 2026-01-01 --ate 2026-01-31` |

## Regras de Decisao

1. **VISAO 360**: "resumo completo", "tudo sobre", "dados do produto"
   Use: `consultando_produto_completo.py --produto X`

2. **PRODUCAO VS REAL**: "producao", "programado", "realizado", "cumpriu", "OP"
   Use: `consultando_producao_vs_real.py --produto X --de Y --ate Z`

3. SE o usuario menciona APENAS estoque, sem querer visao completa:
   Use: `gerindo-expedicao` (consultando_produtos_estoque.py --produto X --completo)

4. SE o usuario menciona APENAS faturamento/vendas:
   Use: `consultando-sql` (query direta em faturamento_produto)

---

## REGRA CRITICA: Fidelidade ao Output dos Scripts

**NUNCA invente, arredonde ou extrapole dados.**
Apresente EXATAMENTE os valores retornados pelo script. Se o script retornar:
- `sucesso: false` com `ambiguidade: true` — apresente a lista de candidatos e peca ao usuario que especifique
- `sucesso: true` com secoes vazias/nulas — informe "sem dados encontrados para esta secao"
- `comparativo: []` (lista vazia) — informe "nenhum registro de producao encontrado para o periodo" (NAO diga "CRITICO" se nao ha dados)
- Valores numericos — use-os tal qual, sem inventar contexto

---

## Tratamento de Ambiguidade

Quando `consultando_produto_completo.py` retornar `ambiguidade: true`:

1. Apresente os candidatos listados no campo `candidatos` com `cod_produto` e `nome_produto`
2. Peca ao usuario que especifique qual produto deseja (pelo cod_produto ou nome mais completo)
3. NAO escolha um candidato automaticamente — deixe o usuario decidir
4. NAO execute consultas adicionais ate o usuario escolher

Quando `consultando_producao_vs_real.py` com `--produto X` retornar `comparativo: []`:
- Se o resolver encontrou o produto mas nao ha programacao/producao no periodo, informe isso claramente
- NAO confunda "sem registros no periodo" com "produto nao encontrado"

---

## Inferencia de Datas para Producao

O script `consultando_producao_vs_real.py` REQUER `--de` e `--ate` em formato YYYY-MM-DD.

Quando o usuario usar expressoes temporais, calcule as datas:
- "ultima semana" = 7 dias atras ate hoje
- "esse mes" / "este mes" = primeiro dia do mes corrente ate hoje
- "janeiro" = 2026-01-01 ate 2026-01-31 (usar ano corrente)
- "ultimo trimestre" = 3 meses atras ate fim do mes passado

Se o usuario NAO especificar periodo para producao, pergunte antes de executar.

---

## Tratamento de Resultados Vazios

Quando qualquer secao retornar valores zerados ou nulos, apresente com transparencia:

| Secao | Valor Zerado Significa |
|-------|----------------------|
| `estoque.saldo_atual = 0` | Produto sem saldo (pode estar esgotado) |
| `demanda_carteira.qtd_pendente = 0` | Nenhum pedido pendente (bom sinal ou produto descontinuado) |
| `demanda_separacao.qtd_separada = 0` | Nada em separacao atualmente |
| `faturamento_30d.qtd_faturada = 0` | Nenhuma venda nos ultimos 30 dias |
| `producao_14d.total_programado = 0` | Sem producao agendada (pode nao ser produto produzido) |
| `custo = null` | Sem custo considerado cadastrado |
| `cadastro = null` | Produto sem cadastro de palletizacao |
| `comparativo = []` | Nenhum registro de programacao OU producao no periodo |

NAO interprete zeros como erro. Apresente o dado e deixe o usuario tirar conclusoes.

---

## Scripts

### 1. consultando_produto_completo.py

**Proposito:** Visao 360 de um produto — cadastro, estoque, custo, demanda, faturamento, producao.

```bash
source .venv/bin/activate && \
python .claude/skills/visao-produto/scripts/consultando_produto_completo.py [parametros]
```

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--produto` | Nome ou codigo do produto | `--produto palmito`, `--produto "az verde"` |

**Retorna JSON com secoes:**
- `cadastro`: dados de CadastroPalletizacao (peso, palletizacao, categoria, dimensoes)
- `estoque`: saldo atual de MovimentacaoEstoque (entradas - saidas)
- `custo`: custo considerado atual de CustoConsiderado
- `demanda_carteira`: total pendente em CarteiraPrincipal (qtd_saldo_produto_pedido > 0)
- `demanda_separacao`: total em separacao (Separacao com sincronizado_nf=False AND qtd_saldo > 0)
- `faturamento_30d`: ultimos 30 dias de FaturamentoProduto (campo `faturamento_recente` no doc, `faturamento_30d` no JSON)
- `producao_14d`: proximos 14 dias de ProgramacaoProducao (campo `producao_programada` no doc, `producao_14d` no JSON)

---

### 2. consultando_producao_vs_real.py

**Proposito:** Comparar producao PROGRAMADA (ProgramacaoProducao) vs REALIZADA (MovimentacaoEstoque tipo_movimentacao=PRODUCAO).

```bash
source .venv/bin/activate && \
python .claude/skills/visao-produto/scripts/consultando_producao_vs_real.py [parametros]
```

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--produto` | Nome ou codigo do produto (opcional — se omitido, retorna todos) | `--produto palmito` |
| `--de` | Data inicio (YYYY-MM-DD) — OBRIGATORIO | `--de 2026-01-01` |
| `--ate` | Data fim (YYYY-MM-DD) — OBRIGATORIO | `--ate 2026-01-31` |
| `--limite` | Max resultados (default: 50) | `--limite 20` |

**Retorna JSON com:**
- `comparativo`: lista de produtos com qtd_programada, qtd_realizada, diferenca, percentual_cumprimento, status
- `resumo`: totais gerais (total_programado, total_realizado, percentual_geral) e mensagem

**Status possiveis:** CUMPRIDO (100%), EXCEDIDO (>100%), QUASE_OK (80-99%), ATENCAO (50-79%), CRITICO (<50%), NAO_INICIADO (0%), SEM_PROGRAMACAO (produziu sem programar), INATIVO (zero em ambos)

---

## Tabelas do Dominio

| Tabela | Chave de produto | Uso |
|--------|-----------------|-----|
| `cadastro_palletizacao` | `cod_produto` | Master data (peso, pallet, dimensoes) |
| `movimentacao_estoque` | `cod_produto` | Saldo e movimentos |
| `custo_considerado` | `cod_produto` | Custo final (WHERE custo_atual = true) |
| `carteira_principal` | `cod_produto` | Demanda pendente (qtd_saldo_produto_pedido > 0) |
| `separacao` | `cod_produto` | Em separacao (sincronizado_nf=False AND qtd_saldo > 0) |
| `faturamento_produto` | `cod_produto` | Vendas faturadas |
| `programacao_producao` | `cod_produto` | Agenda de producao |

**NOTA**: TODAS as tabelas usam `cod_produto`. Filtros de pendencia: CarteiraPrincipal usa `qtd_saldo_produto_pedido > 0`, Separacao usa `sincronizado_nf = False AND qtd_saldo > 0`.
