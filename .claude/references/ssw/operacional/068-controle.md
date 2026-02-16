# Opcao 068 — Controle (Tabela Comissao de Cotacao)

> **Modulo**: Comercial — Comissionamento
> **Paginas de ajuda**: 1 pagina consolidada
> **Atualizado em**: 2026-02-14

## Funcao
Configura tabela de comissionamento de cotacoes para cotadores. Define percentual de comissao sobre CTRCs autorizados ou liquidados (Opcao 903/Outros).

## Quando Usar
- Cadastrar comissao para cotadores
- Definir periodo de validade da tabela
- Agrupar cotadores em equipes
- Inativar tabelas vencidas

## Pre-requisitos
- Usuario cotador cadastrado (Opcao 925)
- Calculo agendado (Opcao 903/Agendar processamento)

## Campos / Interface

### Tela Inicial
| Campo | Descricao |
|-------|-----------|
| Cadastrar comissao para login | Login do cotador (Opcao 925) |
| Relacionar todos cadastrados | Lista todos cotadores com comissoes |

### Tela Principal
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Login | Auto | Login do cotador |
| Nome | Auto | Nome do cotador |
| Equipe | Nao | Agrupamento definido pela transportadora |
| Periodo atividade | Sim | Periodo validade da comissao |
| Comissao | Sim | Percentual (%) sobre CTRC liquidado |

## Fluxo de Uso
1. Acessar Opcao 068
2. Informar login do cotador
3. Definir periodo atividade
4. Informar percentual comissao
5. Opcional: Definir equipe
6. Gravar tabela

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| 002 | Cotacoes realizadas (so veem as proprias se tem comissao) |
| 056 | Relatorio disponibilizado (131 - Comissao Cotacao) |
| 067 | Comissao supervisor/suporte (pode considerar cotacoes) |
| 068 | Esta opcao |
| 300 | Disponibilizacao restrita para cotador |
| 415 | Vendedores (cotacoes nao calculadas se CTRC tem vendedor) |
| 903 | Agendamento calculo, definicao pagamento (autorizado/liquidado) |
| 925 | Cadastro de usuarios (login cotador) |

## Observacoes e Gotchas

### Comissionado
E o usuario que **contrata** a cotacao (Opcao 002), nao aquele que cadastra.

### Pagamento
Ocorre quando CT-e correspondente e:
- **Autorizado** (Opcao 007), ou
- **Liquidado** (Opcao 048, 457, etc.)
- Definido em Opcao 903/Outros

### Inativacao
Para inativar tabela, alterar "periodo atividade" com data fim vencida. Exclusao nao e possivel.

### Base de Calculo
Da base de calculo e descontado ICMS. Alguns dominios abatem tambem PIS/COFINS (percentuais indicados em Opcao 903/Outros).

### Calculo
- Relatorio 131 - COMISSAO DE COTACAO processado junto com comissao vendedores
- Conforme Opcao 903/Agendar processamento
- Filiais: Opcao 056 disponibiliza relatorio analitico
- MTZ: Opcao 056 disponibiliza resumo (relatorio 132) com todas unidades
- Disponibilizacao restrita para cotador: usar Opcao 300

### Cotadores com Comissao
So tem acesso as suas proprias cotacoes em Opcao 002.

### CTRCs com Vendedores
Cotacoes NAO sao calculadas para CTRCs que possuem vendedores (Opcao 415) vinculados.

### Supervisor/Suporte
Comissao de supervisor (Opcao 067) pode considerar cotacoes como base de calculo, juntamente com vendedores.

### Relatorios
- Relatorio 131: Analitico por CTRC (unidades)
- Relatorio 132: Resumo (MTZ) — supervisores e suporte inclusos
