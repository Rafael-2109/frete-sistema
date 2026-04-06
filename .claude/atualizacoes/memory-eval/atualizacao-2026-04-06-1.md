# Atualizacao Memory Eval — 2026-04-06-1

**Data**: 2026-04-06
**Health Score**: 81/100

## Dimensoes do Score

| Dimensao | Valor | Score |
|----------|-------|-------|
| Eficacia media | 46.4% | 15.84/30 |
| Taxa cold | 10.9% | 19.55/20 |
| Stale 60d | 1.6% | 20.00/20 |
| KG coverage | 61.7% | 10.42/15 |
| Correcoes | 0.0 | 15.00/15 |

## Metricas Gerais

- **360** sessoes totais, **194** ultimo mes, **21** usuarios unicos
- **128** memorias ativas, **14** cold, **2** stale >60d
- **599** entidades no KG, **79** memorias linkadas (61.7% coverage)
- **20** memorias com eficacia < 30%
- **84** memorias empresa, nenhuma com reviewed_at preenchido

## Sessoes por Usuario (top, ultimos 30d)

- Rafael: $212.86/mes
- Gabriella: $77.34/mes

## Recomendacoes

1. **REMOVER** 6 memorias com 0% eficacia e alto uso
2. **REVISAR** 3 termos com eficacia < 10% e uso massivo (integracao-nf, confirmar-pedido, cotacao)
3. **MOVER para cold**: download_config e 3 structural/pessoal stale
4. **Implementar ciclo de revisao** (reviewed_at NULL em 100% das memorias empresa)
5. **Aumentar KG coverage** de 61.7% para >80%
6. **Monitorar custo** por usuario
7. **Reformular** 2 memorias permanent com eficacia < 20% e alto uso
