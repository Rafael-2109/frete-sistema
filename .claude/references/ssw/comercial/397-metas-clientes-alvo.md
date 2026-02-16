# Opcao 397 — Metas e Clientes Alvo

> **Modulo**: Comercial
> **Paginas de ajuda**: 3 paginas consolidadas
> **Atualizado em**: 2026-02-14

## Funcao
Define clientes alvo e estabelece metas mensais de vendas para vendedores, tanto globalmente quanto por cliente especifico. Permite acompanhamento de performance comercial atraves de relatorios gerenciais.

## Quando Usar
- Estabelecer metas de vendas para vendedores
- Marcar clientes estrategicos como "alvo"
- Definir metas especificas por cliente
- Planejar estrategia comercial mensal

## Pre-requisitos
- Vendedores cadastrados (opcao 067 e 415)
- Clientes cadastrados com vinculos a vendedores (opcao 415)
- Equipes de vendas configuradas (opcao 415)

## Campos / Interface

| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| META DO VENDEDOR | Nao | Meta mensal considerando producao de todos os clientes vinculados ao vendedor via opcao 415 |
| META POR CLIENTE | Nao | Meta mensal de vendas especifica para cada cliente |
| Cliente Alvo | Nao | Marcar "S" para clientes estrategicos que devem ser acompanhados de perto |

## Fluxo de Uso

1. Acessar opcao 397
2. Selecionar vendedor
3. Definir meta global do vendedor (opcional)
4. Para cada cliente vinculado:
   - Definir meta mensal especifica
   - Marcar como cliente alvo (S/N) se for estrategico
5. Gravar configuracoes
6. Acompanhar resultados pelos relatorios 125 e 126

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| 056 | Relatorios Gerenciais - acessa relatorios 125 e 126 para acompanhamento |
| 067 | Cadastro de vendedores/supervisores |
| 119 | Relatorio de visita - filtra por clientes alvo |
| 125 | Producao de vendedor - mostra atingimento analitico (por cliente e vendedor) |
| 126 | Producao de vendedor resumo - mostra atingimento sintetico (por vendedor e equipe) |
| 333 | Acoes de vendas |
| 335 | Agendamento de acoes de vendas |
| 385 | Ocorrencias do cliente |
| 415 | Vinculo cliente-vendedor e equipes |

## Observacoes e Gotchas

- **Relatorio 125** (Producao de vendedor): analitico, totaliza por cliente e vendedor, disponivel para unidades
- **Relatorio 126** (Producao de vendedor - Resumo): sintetico, totaliza por vendedor/equipe/supervisor, apenas matriz
- Clientes marcados como ALVO aparecem destacados nos relatorios e filtros
- Metas sao mensais e acumulam producao diaria ate o dia anterior (ontem)
- Percentual de atingimento e calculado automaticamente nos relatorios
- Vendedores sao vinculados a clientes pela opcao 415
- Sistema permite meta global do vendedor + metas especificas por cliente
