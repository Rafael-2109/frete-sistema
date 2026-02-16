# 05 — Resultado

> **Fonte**: `visao_geral_resultado.htm` (09/03/2025)
> **Links internos**: 30 | **Imagens**: 1

## Sumario

Modelo de resultado em 5 dimensoes: CTRC → Cliente → Caminhao → Unidade → Transportadora. Principio: "Tudo tem que dar LUCRO".

---

## 1. Resultado do CTRC

CTRC e o elemento basico de transporte. 3 modelos de avaliacao:

| Modelo | Descricao | Opcao |
|--------|-----------|-------|
| **Resultado Comercial** | Unidades cobram pelo servico prestado. Transferencia cobrada por Kg | 101/Resultado |
| **Resultado Real** | Igual ao Comercial, mas transferencia = rateio de custos reais do veiculo | 101/Resultado |
| **Desconto sobre NTC** | Frete como % de desconto sobre tabela NTC ([opção 427](../comercial/427-resultado-por-cliente.md)) | 101/Resultado |

> **Recomendacao**: Usar **Resultado Comercial** — nao penaliza indevidamente cliente transportado em veiculo ocioso.

### Relatorio vital
- **031 — CTRCs COM RESULTADO COMERCIAL NEGATIVO** ([opção 056](../relatorios/056-informacoes-gerenciais.md)): avaliacao diaria obrigatoria

---

## 2. Resultado do Cliente

Soma dos resultados dos CTRCs por cliente.

| Opcao | Descricao |
|-------|-----------|
| 102/Geral | 3 indicadores agrupados por cliente |
| 449 | Por cliente, faixa de peso e rota |
| 511 | Por cliente, sintetico, 24 meses |
| 056/070 | Maiores clientes (relatorio mensal dias 01 e 10) |

---

## 3. Resultado do Caminhao

Caminhao = maior despesa. Acompanhar diariamente.

- **Despesa**: valor da viagem pago ao veiculo (contratacao [opção 072](../operacional/072-contratacao-de-veiculo-de-transferencia.md))
- **Receita**: frete proporcional do Manifesto (trecho percorrido, rateado com demais veiculos)

> Se para transferencia restam 30% do frete, a viagem deve custar MENOS que 30%.

### Relatorios
| Relatorio | Opcao 056 | Descricao |
|-----------|-----------|-----------|
| 020 | Diario | Resultado das viagens concluidas |
| 019 | Diario | Resultado das viagens iniciadas |
| 021 | Mensal (dia 01) | Resultado de transferencias por veiculo/motorista/rota |
| 023 | Diario | Resultado das coletas/entregas |
| 022 | Mensal (dia 01) | Resultado de coletas/entregas (CTRBs emitidos) |

---

## 4. Resultado da Unidade

2 tipos de avaliacao:

| Tipo | Descricao | Opcao |
|------|-----------|-------|
| **Resultado Comercial** | Soma dos resultados dos CTRCs por unidade responsavel ([opção 483](../cadastros/483-cadastro-clientes.md)). Receita = frete do cliente | 056/166, 056/167 |
| **Prestacao de Servicos** | Unidade remunerada pelos servicos prestados ([opção 408](../comercial/408-comissao-unidades.md)). Nao tem receita direta de clientes | 056/168 |

### Relatorios alternativos (so financeiro)
- [**463** — Resultado por unidade](../fiscal/463-resultado-por-unidade-sintetico.md) (receitas fretes vs despesas)
- [**464** — Resultado detalhado por evento](../fiscal/464-resultado-por-unidade-analitico.md)

---

## 5. Resultado da Transportadora

- **001 — SITUACAO GERAL** ([opção 056](../relatorios/056-informacoes-gerenciais.md)): totais de entradas/saidas dos 3 meses anteriores + vigente + 3 dias anteriores

---

## Modelo Visual

```
                    TRANSPORTADORA (001)
                    ┌─────────────────┐
                    │ $entra > $sai   │
                    └───────┬─────────┘
                ┌───────────┼───────────┐
         UNIDADE A    UNIDADE B    UNIDADE C
         (166/168)    (166/168)    (166/168)
            │              │            │
    ┌───────┼───────┐     ...          ...
    │       │       │
 CLIENTE  CLIENTE  CAMINHÃO
 (102)    (449)    (020/023)
    │       │       │
  CTRCs   CTRCs   Viagens
  (101)   (101)   (072)
```

---

## Contexto CarVia

### Opcoes que CarVia usa
*Nenhuma — CarVia nunca implantou analise de resultado no SSW.*

### Opcoes que CarVia NAO usa (mas deveria)
| Opcao | Funcao | Impacto |
|-------|--------|---------|
| [101](../comercial/101-resultado-ctrc.md) | Resultado por CTRC (Comercial/Real/NTC) | Sem analise de resultado, decisoes de preco sao por "feeling" — impossivel identificar CTRCs com prejuizo |
| [056](../relatorios/056-informacoes-gerenciais.md) | Relatorios gerenciais (031 — CTRCs com prejuizo) | Sem avaliacao diaria de lucratividade, prejuizos passam despercebidos |

### Status de Implantacao
- **B04**: NAO IMPLANTADO — nunca analisou lucratividade no SSW
- **B05**: NAO IMPLANTADO — nunca acessou opcao 056 para relatorios de resultado

### Responsaveis
- **Atual**: Ninguem (modulo nao implantado)
- **Futuro**: Rafael (plano de implantacao de analise de resultado)
