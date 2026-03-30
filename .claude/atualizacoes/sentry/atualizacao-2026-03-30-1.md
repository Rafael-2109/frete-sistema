# Atualizacao Sentry Triage — 2026-03-30-1

**Data**: 2026-03-30
**Issues avaliadas**: 42
**Issues corrigidas**: 0
**Issues ignoradas**: 42
**Issues fora de escopo**: 0
**Arquivos modificados**: 0

## Resumo

Todas as 42 issues nao resolvidas em producao caem em categorias excluidas de correcao automatica.

## Detalhamento

### Odoo XML-RPC Faults (39 issues, ~530 eventos)

- Erros Fault 1 do servidor Odoo remoto (connection refused, timeouts, erros internos)
- Sao problemas de infraestrutura/servidor externo, NAO bugs no nosso codigo
- Concentrados nos ultimos 1-2 dias — indica instabilidade do servidor Odoo

### Odoo Socket Timeouts (2 issues — PYTHON-FLASK-9J, 9H)

- Timeouts em action_gerar_po_dfe
- 1 evento cada, 4 dias atras
- Transientes — abaixo do threshold de 3 eventos em 48h

### Migrations Pendentes (1 issue — PYTHON-FLASK-K, 25 eventos)

- UndefinedColumn para peso_cubado_total, updated_at, validacao_dfe_id
- Migrations nao executadas em producao
- Per regras de exclusao: documentado mas NAO corrigido

## Usuarios Afetados

0 usuarios afetados em todas as issues.

## Recomendacoes

1. Verificar estabilidade do servidor Odoo — volume de XML-RPC Faults anormalmente alto
2. Executar migrations pendentes para resolver PYTHON-FLASK-K
