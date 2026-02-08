# Scripts — Cotando Frete (Detalhes)

Referencia detalhada de parametros, retornos esperados e exemplos de uso.

---

## 1. buscar_tabelas_cidade.py

Busca todas as tabelas de frete que atendem uma cidade.

```bash
source .venv/bin/activate && python .claude/skills/cotando-frete/scripts/buscar_tabelas_cidade.py [opcoes]
```

**Parametros:**

| Param | Obrig | Descricao |
|-------|-------|-----------|
| `--cidade` | Sim | Nome da cidade (com ou sem acentos) |
| `--uf` | Condicional | Obrigatorio se cidade existir em multiplos estados |
| `--tipo-carga` | Nao | DIRETA ou FRACIONADA |
| `--uf-origem` | Nao | UF de origem (default: SP) |

**Retorno esperado:**
```json
{
  "sucesso": true,
  "cidade": "MANAUS",
  "uf": "AM",
  "codigo_ibge": "1302603",
  "icms_cidade": 0.07,
  "total_tabelas": 5,
  "tabelas": [
    {
      "transportadora": "BRASPRESS",
      "transportadora_id": 42,
      "optante": false,
      "nome_tabela": "TABELA AM 2025",
      "tipo_carga": "FRACIONADA",
      "modalidade": "FRETE PESO",
      "lead_time": 12,
      "valor_kg": 0.85,
      "percentual_valor": 0.30,
      "frete_minimo_peso": 100,
      "frete_minimo_valor": 350.00,
      "percentual_gris": 0.30,
      "gris_minimo": 25.00,
      "percentual_adv": 0.10,
      "adv_minimo": 0,
      "percentual_rca": 0,
      "pedagio_por_100kg": 5.50,
      "valor_tas": 0,
      "valor_despacho": 50.00,
      "valor_cte": 0,
      "icms_incluso": false
    }
  ]
}
```

---

## 2. calcular_cotacao.py

Calcula cotacao de frete detalhada para peso/valor/destino.

```bash
source .venv/bin/activate && python .claude/skills/cotando-frete/scripts/calcular_cotacao.py [opcoes]
```

**Parametros:**

| Param | Obrig | Descricao |
|-------|-------|-----------|
| `--peso` | Sim | Peso em kg |
| `--valor` | Sim | Valor da mercadoria em R$ |
| `--cidade` | Sim | Nome da cidade destino |
| `--uf` | Condicional | Se cidade ambigua |
| `--tipo-carga` | Nao | DIRETA ou FRACIONADA |
| `--uf-origem` | Nao | UF de origem (default: SP) |
| `--detalhado` | Nao | Flag para breakdown completo |
| `--ordenar` | Nao | menor_valor (default) ou menor_prazo |
| `--limite` | Nao | Max opcoes (default: 10) |

**Retorno esperado:**
```json
{
  "sucesso": true,
  "parametros": {"peso": 5000, "valor": 50000, "cidade": "MANAUS", "uf": "AM"},
  "total_opcoes": 3,
  "melhor_opcao": {
    "transportadora": "BRASPRESS",
    "valor_com_icms": 3495.16,
    "criterio": "menor_valor"
  },
  "opcoes": [
    {
      "posicao": 1,
      "transportadora": "BRASPRESS",
      "nome_tabela": "TABELA AM 2025",
      "tipo_carga": "FRACIONADA",
      "modalidade": "FRETE PESO",
      "lead_time": 12,
      "valor_bruto": 3250.50,
      "valor_com_icms": 3495.16,
      "valor_liquido": 3250.50,
      "frete_por_kg": 0.699,
      "percentual_sobre_valor": 6.99
    }
  ]
}
```

---

## 3. consultar_pedido_frete.py

Consulta dados de frete de pedidos existentes.

```bash
source .venv/bin/activate && python .claude/skills/cotando-frete/scripts/consultar_pedido_frete.py [opcoes]
```

**Parametros:**

| Param | Obrig | Descricao |
|-------|-------|-----------|
| `--pedido` | * | Numero do pedido (VCD/VFB). Busca em separacao E carteira. Se multiplos contextos, retorna `resumo.requer_clarificacao=true` |
| `--separacao` | * | Lote de separacao |
| `--nf` | * | Numero da NF |
| `--recalcular` | Nao | Recalcular com tabelas atuais |

\* Pelo menos um obrigatorio

**Fontes de dados por parametro:**
- `--pedido` → busca UNIFICADA: `separacao` (sincronizado_nf=false, qtd_saldo>0) + `carteira_principal` (qtd_saldo_produto_pedido>0)
- `--separacao` → busca em `separacao` (sincronizado_nf=false, qtd_saldo>0)
- `--nf` → busca em `faturamento_produto`

**Quando --pedido retorna multiplos contextos:**

O mesmo pedido pode ter simultaneamente:
- 1 ou mais separacoes (`separacao_lote_id`) com `sincronizado_nf=False`
- Saldo remanescente na `carteira_principal` (parte nao separada)

Se `resumo.requer_clarificacao = true`:
1. Apresentar os contextos ao usuario
2. Usar AskUserQuestion para o usuario escolher qual contexto
3. NAO calcular frete de todos sem perguntar

Se `resumo.requer_clarificacao = false` (1 unico contexto):
- Usar direto, sem perguntar

---

## 4. consultando_frete_real.py

Consulta frete REAL (historico de gastos, divergencias, pendentes Odoo).

```bash
source .venv/bin/activate && python .claude/skills/cotando-frete/scripts/consultando_frete_real.py [opcoes]
```

**Parametros:**

| Param | Obrig | Descricao |
|-------|-------|-----------|
| `--pedido` | * | Frete real do pedido (via chain embarque) |
| `--cliente` | * | Total frete real por cliente/grupo (entity resolution) |
| `--transportadora` | * | Frete agregado por transportadora |
| `--divergencias` | * | Listar divergencias CTe vs cotacao > R$5 |
| `--pendentes-odoo` | * | Fretes aprovados nao lancados no Odoo |
| `--de` | Nao | Data inicio (YYYY-MM-DD) |
| `--ate` | Nao | Data fim (YYYY-MM-DD) |
| `--com-despesas` | Nao | Incluir breakdown de DespesaExtra |
| `--limite` | Nao | Max resultados (default: 50) |

\* Pelo menos um modo obrigatorio

**Modos de operacao:**
- `--pedido VCD123`: Traversa chain Separacao → EmbarqueItem → Embarque → Frete
- `--cliente "Atacadao"`: Entity resolution por LIKE + agrupamento por prefixo CNPJ (8 digitos = grupo)
- `--transportadora "Braspress"`: Agrega fretes por transportadora com breakdown UF/tipo_carga
- `--divergencias`: Filtra `ABS(valor_cte - valor_cotado) > 5.00`
- `--pendentes-odoo`: Filtra `status='APROVADO' AND lancado_odoo_em IS NULL`

---

## Exemplos de Uso

### Cenario 1: Tabelas para uma cidade
```
Pergunta: "quais transportadoras atendem Manaus?"
Comando: buscar_tabelas_cidade.py --cidade "Manaus" --uf AM
```

### Cenario 2: Cotacao com peso e valor
```
Pergunta: "quanto sai frete de 5 toneladas, R$ 50 mil para Manaus?"
Comando: calcular_cotacao.py --peso 5000 --valor 50000 --cidade "Manaus" --uf AM
```

### Cenario 3: Frete de pedido existente
```
Pergunta: "qual o frete do pedido VCD2565291?"
Comando: consultar_pedido_frete.py --pedido VCD2565291
```

### Cenario 4: Frete real gasto com cliente
```
Pergunta: "quanto gastei de frete com o Atacadao nos ultimos 3 meses?"
Comando: consultando_frete_real.py --cliente "Atacadao" --de 2025-11-01
```

### Cenario 5: Divergencias de CTe
```
Pergunta: "tem alguma divergencia de CTe este mes?"
Comando: consultando_frete_real.py --divergencias --de 2026-02-01
```
