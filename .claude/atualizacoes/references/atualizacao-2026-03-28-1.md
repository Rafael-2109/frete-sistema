# Atualizacao References — 2026-03-28-1

**Data**: 2026-03-28
**Grupos revisados**: P0, P1, P2 (P3-P4 scan rapido)
**Arquivos modificados**: 3

## Resumo

Auditoria completa de references P0-P2. 3 correcoes aplicadas: datetime.utcnow() em exemplos Odoo, status Sentry desatualizado, caminho CSS incorreto. Nenhum caminho quebrado encontrado nos 30 arquivos auditados.

## Alteracoes por Grupo

### Root (P0)
- `BEST_PRACTICES_2026.md`: Sentry MCP estava como "Requer infra primeiro" — atualizado para INTEGRADO (ativo desde 2026-03-11, 20 tools)
- Versoes verificadas: anthropic==0.84.0, mcp>=1.26.0 — corretas

### modelos/ (P1)
- Sem alteracoes necessarias
- NOTA: REGRAS_CARTEIRA_SEPARACAO.md tem line numbers ~10 linhas deslocados (cosmetico)
- NOTA: PreSeparacaoItem marcado DEPRECATED mas app/portal/routes.py tem 5 usos ativos

### negocio/ (P1)
- Sem alteracoes necessarias

### odoo/ (P2)
- `PADROES_AVANCADOS.md`: 2 instancias de datetime.utcnow() em codigo de storage substituidas por agora_brasil_naive() (conformidade com REGRAS_TIMEZONE.md)

### design/ (P3)
- `MAPEAMENTO_CORES.md`: Caminho _design-tokens.css corrigido (raiz -> tokens/_design-tokens.css)

## Itens para Revisao Manual
- INFRAESTRUTURA.md: plano Postgres discrepancia (Basic 1GB vs basic_4gb) — requer check no Render
- ROUTING_SKILLS.md: contagem skills 30 vs real ~34 (cosmetico)
- QUERIES_MAPEAMENTO.md: Q1 usa qtd_saldo em vez de qtd_saldo_produto_pedido (exemplo)
