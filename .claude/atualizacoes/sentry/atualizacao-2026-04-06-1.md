# Atualizacao Sentry — 2026-04-06-1

**Data**: 2026-04-06
**Org**: nacom | **Projeto**: python-flask

## Resumo

Triagem completa. **0 erros de aplicacao em producao.** Apenas 2 alertas de performance abertos.

## Issues Avaliadas

| Issue | Tipo | Culprit | Eventos | Usuarios | Classificacao |
|-------|------|---------|---------|----------|---------------|
| PYTHON-FLASK-CH | Consecutive DB Queries | `pedidos.lista_pedidos` | 9 | 2 | FORA DE ESCOPO |
| PYTHON-FLASK-CG | N+1 Query | `embarques.visualizar_embarque` | 1 | 1 | FORA DE ESCOPO |

## Classificacao

- **CRITICO**: 0
- **ALTO**: 0
- **MEDIO**: 0
- **BAIXO**: 0
- **FORA DE ESCOPO**: 2 (alertas de performance — requerem refatoracao de queries)

## Correcoes Aplicadas

Nenhuma — sem bugs tecnicos para corrigir.

## Notas

Ambas issues de performance requerem eager loading / joins otimizados — fora do escopo de correcao automatizada.
