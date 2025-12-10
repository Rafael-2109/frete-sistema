---
name: verificar-disponibilidade
description: Verifica disponibilidade de estoque para pedido ou grupo de clientes
---

Verifique a disponibilidade de estoque para atender o pedido ou grupo especificado.

## Script

```bash
source $([ -d venv ] && echo venv || echo .venv)/bin/activate && \
python .claude/skills/gerindo-expedicao/scripts/analisando_disponibilidade_estoque.py $ARGUMENTS
```

## Parametros Principais

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--pedido` | Pedido ou "grupo termo" | `--pedido VCD123` ou `--pedido "atacadao 183"` |
| `--grupo` | Grupo empresarial | `--grupo atacadao`, `--grupo assai` |
| `--loja` | Loja especifica | `--loja 183` |
| `--uf` | Filtrar por UF | `--uf SP` |
| `--data` | Data para analise | `--data amanha`, `--data 15/12` |

## Flags de Analise

| Flag | O que faz |
|------|-----------|
| `--sem-agendamento` | Apenas pedidos sem exigencia de agenda |
| `--sugerir-adiamento` | Sugere pedidos para adiar (liberar estoque) |
| `--diagnosticar-origem` | Distingue falta absoluta vs relativa |
| `--completude` | Calcula % faturado vs pendente |
| `--atrasados` | Analisa pedidos com expedicao vencida |
| `--ranking-impacto` | Ranking de pedidos que mais travam carteira |

## Exemplos

```
/verificar-disponibilidade --pedido VCD123
/verificar-disponibilidade --grupo atacadao --sem-agendamento
/verificar-disponibilidade --uf SP --atrasados --diagnosticar-causa
```

$ARGUMENTS
