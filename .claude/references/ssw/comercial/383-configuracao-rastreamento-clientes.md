# Opcao 383 — Configuracao de Rastreamento de Clientes

> **Modulo**: Comercial
> **Paginas de ajuda**: 2 paginas consolidadas (421 Sub-Regioes, 929 Gera Banco de Dados)
> **Atualizado em**: 2026-02-14

## Funcao
Define configuracoes de rastreamento por cliente, incluindo disparo automatico de e-mails de rastreamento delimitado por sub-regioes geograficas. Permite cadastrar sub-regioes (agrupamento de cidades por UF) para controle de notificacoes.

## Quando Usar
- Configurar envio automatico de e-mails de rastreamento para clientes
- Delimitar disparo de e-mails por sub-regioes geograficas
- Gerar planilha de clientes com suas configuracoes de rastreamento
- Agrupar cidades de uma UF em sub-regioes para controle de notificacoes

## Pre-requisitos
- Cidades atendidas cadastradas no sistema
- Para sub-regioes: definicao de agrupamentos geograficos desejados

## Campos / Interface

### Cadastro de Sub-Regioes (Tela Inicial)
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Sigla da Sub-regiao | Sim | Identificador da sub-regiao a ser cadastrada |
| UF (tela seguinte) | Sim | Estado para listar cidades atendidas pela transportadora |
| Cidades (selecao multipla) | Sim | Marcar cidades que irao compor a sub-regiao |

### Geracao de Banco de Dados (Relatorio)
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Periodo de ultimo movimento | Sim | Periodo de emissao de CTRCs para filtrar clientes ativos |
| Ver fila | Nao | Link que abre opcao 156 para visualizar o relatorio |

## Fluxo de Uso

### Cadastro de Sub-Regiao
1. Informar sigla para nova sub-regiao na tela inicial
2. Clicar no botao ► ao lado
3. Na tela seguinte, clicar sobre a UF desejada
4. Sistema lista todas as cidades atendidas pela transportadora naquela UF
5. Marcar cidades que farao parte da sub-regiao
6. Confirmar clicando no ► no rodape
7. Sub-regiao fica disponivel para uso na opcao 383 (disparo automatico de e-mails)

### Alteracao/Exclusao de Sub-Regiao
1. Sub-regioes cadastradas sao listadas na tela inicial
2. Selecionar sub-regiao para alterar ou excluir
3. Realizar alteracoes necessarias

### Geracao de Relatorio de Clientes
1. Acessar funcao de geracao de banco de dados (opcao 929)
2. Indicar periodo de ultimo movimento (emissao de CTRCs)
3. Gerar planilha com clientes e configuracoes de rastreamento
4. Visualizar relatorio via link "Ver fila" (opcao 156)

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 383 | Configuracao de rastreamento — usa sub-regioes para disparo automatico de e-mails |
| 156 | Visualizacao de relatorios — exibe planilha gerada pela opcao 929 |
| 929 | Geracao de banco de dados de clientes rastreamento |
| 421 | Cadastro de sub-regioes (funcionalidade base) |

## Observacoes e Gotchas
- **Sub-regioes geograficas**: agrupamento de cidades de uma UF sob uma sigla unica
- **Disparo automatico**: sub-regioes permitem delimitar quais clientes recebem e-mails de rastreamento automaticamente
- **Apenas cidades atendidas**: ao selecionar UF, sistema lista APENAS cidades que a transportadora atende
- **Selecao multipla**: e possivel marcar multiplas cidades de uma vez para compor sub-regiao
- **Listagem editavel**: sub-regioes cadastradas aparecem na tela inicial para alteracao/exclusao
- **Relatorio de clientes**: planilha gerada pela opcao 929 lista clientes ativos (conforme periodo de ultimo movimento) com suas configuracoes de rastreamento definidas na opcao 383
- **Link Ver fila**: abre opcao 156 para visualizacao do relatorio gerado (nao e necessario navegar manualmente)
