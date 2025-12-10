---
name: consultar-estoque
description: Consulta situacao completa de estoque de um produto
---

Consulte a situacao completa de estoque para o produto especificado.

## Script

```bash
source $([ -d venv ] && echo venv || echo .venv)/bin/activate && \
python .claude/skills/gerindo-expedicao/scripts/consultando_produtos_estoque.py --produto "$ARGUMENTS" --completo
```

## O que retorna (--completo)

1. **Estoque atual** e menor estoque projetado nos proximos 7 dias
2. **Separacoes pendentes** por data de expedicao (detalhado com pedidos)
3. **Demanda total** (Carteira bruta/liquida + Separacoes)
4. **Programacao de producao** (proximos 14 dias)
5. **Projecao dia a dia** (estoque projetado)
6. **Indicadores**: sobra, cobertura em dias, % disponivel, previsao de ruptura

## Abreviacoes Aceitas

| Abrev | Produto |
|-------|---------|
| AZ | Azeitona |
| PF | Preta Fatiada |
| VF | Verde Fatiada |
| VI | Verde Inteira |
| BD | Balde |
| IND | Industrial |
| POUCH | Pouch |

## Exemplos

```
/consultar-estoque palmito
/consultar-estoque "az verde fatiada"
/consultar-estoque pf mezzani
```

$ARGUMENTS
