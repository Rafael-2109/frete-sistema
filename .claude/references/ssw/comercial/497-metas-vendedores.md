# Opção 497 — Metas para Vendedores

> **Módulo**: Comercial
> **Páginas de ajuda**: 1 página consolidada
> **Atualizado em**: 2026-02-15

## Função
Cadastramento de metas mensais de vendas (em R$) por vendedor, permitindo o acompanhamento diário de desempenho através de relatórios gerenciais.

## Quando Usar
Quando for necessário:
- Estabelecer metas comerciais mensais para vendedores
- Acompanhar performance de vendedores ao longo do mês
- Gerar indicadores de cumprimento de metas (atingimento)
- Comparar realizado vs meta projetada até a data atual

## Pré-requisitos
- Vendedores cadastrados no sistema
- Opção 903/Frete configurada com tabela de percentuais diários para transformar meta mensal em meta diária
- Permissão de acesso à opção (supervisores/gerentes)

## Campos / Interface

### Tela Inicial — Seleção

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Unidade | Condicional | Sigla da unidade (informar um dos três) |
| Equipe | Condicional | Código da equipe (informar um dos três) |
| Código do vendedor | Condicional | Código do vendedor (informar um dos três) |

### Tela Seguinte — Cadastro de Metas

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Vendedor | - | Exibido automaticamente conforme seleção anterior |
| Meta mensal (R$) | Sim | Valor da meta de vendas a ser atingida no mês |

## Fluxo de Uso

1. Acessar tela inicial
2. Informar um dos campos: unidade, equipe ou código do vendedor
3. Na tela seguinte, informar meta em R$ para cada vendedor listado
4. Salvar metas
5. Acompanhar diariamente através de relatórios da opção 056

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 397 | Metas de clientes — cadastro similar, mas focado em clientes específicos |
| 903/Frete | Tabela de percentuais diários — converte meta mensal em meta diária |
| 056 | Relatórios gerenciais — acompanhamento de metas |
| 056 → Relatório 135 | Monitoração de Clientes — campos META_MES, META_HOJE, REALIZ_HOJE, ACIMA, ABAIXO, OBSERV |
| 056 → Relatório 125 | Produção do Vendedor (Analítico/Resumo) — coluna META_HJ e ATING |
| 056 → Relatório 126 | Produção por Vendedor por Equipe (Sintético) — coluna META_HJ e ATING |

## Observações e Gotchas

- **Diferença entre opção 497 e 397**:
  - **497** (esta opção): Metas para **vendedores** — acompanha TODOS clientes que geram comissão ao vendedor
  - **397**: Metas para **clientes** — acompanha apenas alguns clientes específicos de interesse

- **Metas para o dia**: Sistema transforma meta mensal em meta diária utilizando tabela de percentuais em opção 903/Frete. Fórmula: Meta Hoje = Meta Mensal × Percentual do Dia

- **Relatório 135 — Campos principais**:
  - **META_MES**: Meta estabelecida para o mês (opção 497 para vendedores, 397 para clientes)
  - **META_HOJE**: Meta mensal projetada até hoje (usa percentuais da opção 903/Frete)
  - **REALIZ_HOJE**: Montante de frete emitido no mês até hoje
  - **ACIMA**: Montante que ultrapassou a meta
  - **ABAIXO**: Montante que ficou abaixo da meta
  - **OBSERV**: Indica se cliente está ABAIXO, ACIMA ou FUGIU (parou de operar)

- **Relatórios 125 e 126**: Coluna **META_HJ** mostra meta até hoje, coluna **ATING** mostra percentual atingido

- **Acompanhamento diário**: Supervisores e gerentes podem monitorar metas diariamente através dos relatórios da opção 056
