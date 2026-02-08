# Regras de Prioridade P1-P7 e Envio Parcial

> **SYNC**: Este e um reference critico. Ao editar, verificar tambem:
> - `app/agente/prompts/system_prompt.md` (resumo em `<priorities>` e `<partial_shipping>`)
> - `.claude/agents/analista-carteira.md` (usa regras P1-P7 para priorizacao)

**Fonte**: Extraido do `system_prompt.md` v3.4.0 (2026-02-08)

---

## Hierarquia de Prioridades (P1-P7)

Ordem de decisao para analise e embarque:

| Prioridade | Criterio | Acao |
|------------|----------|------|
| **P1** | Tem `data_entrega_pedido` | EXECUTAR (data ja negociada) |
| **P2** | FOB (cliente coleta) | SEMPRE COMPLETO |
| **P3** | Carga direta >=26 pallets OU >=20.000kg fora SP | Agendar D+3 + leadtime |
| **P4** | Atacadao (EXCETO loja 183) | Priorizar (50% faturamento) |
| **P5** | Assai | 2o maior cliente |
| **P6** | Demais | Ordenar por data_pedido |
| **P7** | Atacadao 183 | POR ULTIMO (causa ruptura) |

### Calculo de Expedicao (P1)

Quando o pedido tem `data_entrega_pedido`:

| Condicao | Data de Expedicao |
|----------|-------------------|
| SP ou RED (incoterm) | D-1 |
| SC/PR + peso > 2.000kg | D-2 |
| Outras regioes | Calcular frete -> usar lead_time |

---

## Envio Parcial — Decisao Automatica vs Consultar Comercial

| Falta (%) | Demora | Valor | Decisao |
|-----------|--------|-------|---------|
| <=10% | >3 dias | Qualquer | **PARCIAL automatico** |
| 10-20% | >3 dias | Qualquer | **Consultar comercial** |
| >20% | >3 dias | >R$10K | **Consultar comercial** |

### Excecoes

- FOB = SEMPRE COMPLETO (nunca parcial)
- Abaixo de R$15K + Falta >=10% = AGUARDAR
- Abaixo de R$15K + Falta abaixo de 10% + Demora <=5 dias = AGUARDAR
- >=30 pallets OU >=25.000kg = PARCIAL obrigatorio (limite carreta)

### Nota

Percentual de falta calculado por **VALOR**, nao por linhas.
