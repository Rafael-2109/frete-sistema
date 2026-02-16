# Scripts — Visao Produto (Detalhes)

Referencia detalhada de parametros, retornos e tabelas consultadas.

---

## Ambiente Virtual

Sempre ativar antes de executar:
```bash
source .venv/bin/activate
```

---

## 1. consultando_produto_completo.py

**Proposito:** Visao 360 de um produto — cadastro, estoque, custo, demanda, faturamento, producao.

```bash
source .venv/bin/activate && \
python .claude/skills/visao-produto/scripts/consultando_produto_completo.py [opcoes]
```

| Parametro | Obrig | Descricao | Exemplo |
|-----------|-------|-----------|---------|
| `--produto` | Sim | Nome ou codigo do produto | `--produto palmito`, `--produto "az verde"` |

**Resolucao de produto:** Usa `resolver_produto_unico` do `resolver_entidades.py`. Se multiplos matches, retorna lista para desambiguacao.

**Retorno JSON com secoes:**

| Secao | Fonte | Descricao |
|-------|-------|-----------|
| `cadastro` | CadastroPalletizacao | peso, palletizacao, categoria, dimensoes |
| `estoque` | MovimentacaoEstoque | saldo atual (entradas - saidas) |
| `custo` | CustoConsiderado | custo considerado atual (custo_atual=true) |
| `demanda_carteira` | CarteiraPrincipal | total pendente (qtd_saldo_produto_pedido > 0) |
| `demanda_separacao` | Separacao | total em separacao (sincronizado_nf=False AND qtd_saldo > 0) |
| `faturamento_recente` | FaturamentoProduto | ultimos 30 dias |
| `producao_programada` | ProgramacaoProducao | proximos 14 dias |

---

## 2. consultando_producao_vs_real.py

**Proposito:** Comparar producao PROGRAMADA (ProgramacaoProducao) vs REALIZADA (MovimentacaoEstoque tipo_movimentacao=PRODUCAO).

```bash
source .venv/bin/activate && \
python .claude/skills/visao-produto/scripts/consultando_producao_vs_real.py [opcoes]
```

| Parametro | Obrig | Descricao | Exemplo |
|-----------|-------|-----------|---------|
| `--produto` | Nao | Nome ou codigo (se omitido, retorna todos) | `--produto palmito` |
| `--de` | Sim | Data inicio (YYYY-MM-DD) | `--de 2026-01-01` |
| `--ate` | Sim | Data fim (YYYY-MM-DD) | `--ate 2026-01-31` |
| `--limite` | Nao | Max resultados (default: 50) | `--limite 20` |

**Resolucao de produto:** Usa `resolver_produto` do `resolver_entidades.py` (aceita multiplos matches).

**Retorno JSON:**
```json
{
  "sucesso": true,
  "comparativo": [
    {
      "cod_produto": "PAL001",
      "nome_produto": "PALMITO PUPUNHA 300G",
      "qtd_programada": 5000,
      "qtd_realizada": 4200,
      "diferenca": -800,
      "percentual_cumprimento": 84.0
    }
  ],
  "resumo": {
    "total_produtos": 15,
    "programado_total": 75000,
    "realizado_total": 68000,
    "cumprimento_geral": 90.7,
    "mensagem": "Producao geral atingiu 90.7% do programado"
  }
}
```

---

## Tabelas do Dominio

| Tabela | Chave | Uso |
|--------|-------|-----|
| `cadastro_palletizacao` | `cod_produto` | Master data (peso, pallet, dimensoes) |
| `movimentacao_estoque` | `cod_produto` | Saldo e movimentos |
| `custo_considerado` | `cod_produto` | Custo final (WHERE custo_atual = true) |
| `carteira_principal` | `cod_produto` | Demanda pendente (qtd_saldo_produto_pedido > 0) |
| `separacao` | `cod_produto` | Em separacao (sincronizado_nf=False AND qtd_saldo > 0) |
| `faturamento_produto` | `cod_produto` | Vendas faturadas |
| `programacao_producao` | `cod_produto` | Agenda de producao |

**NOTA:** TODAS as tabelas usam `cod_produto` (NAO `codigo_produto`).

---

## Exemplos de Uso

### Cenario 1: Visao completa de produto
```
Pergunta: "tudo sobre o palmito"
Comando: consultando_produto_completo.py --produto palmito
```

### Cenario 2: Producao vs realizado de um produto
```
Pergunta: "cumpriram a programacao de palmito em janeiro?"
Comando: consultando_producao_vs_real.py --produto palmito --de 2026-01-01 --ate 2026-01-31
```

### Cenario 3: Producao geral (todos os produtos)
```
Pergunta: "como foi a producao de janeiro?"
Comando: consultando_producao_vs_real.py --de 2026-01-01 --ate 2026-01-31
```
