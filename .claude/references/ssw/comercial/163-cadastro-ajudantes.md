# Opcao 163 — Cadastro de Ajudantes

> **Modulo**: Comercial
> **Paginas de ajuda**: 1 pagina consolidada (referencia na opcao 164)
> **Atualizado em**: 2026-02-14

## Funcao
Cadastra ajudantes de entrega/coleta no sistema, permitindo registro de dados pessoais, tipo de vinculo (funcionario ou terceirizado), status (ativo/bloqueado) e informacoes de gerenciamento de risco. Ajudantes cadastrados podem ser relacionados em relatorios atraves da opcao 164.

## Quando Usar
- Cadastrar novo ajudante de entrega ou coleta
- Atualizar dados de ajudante existente
- Registrar informacoes de gerenciamento de risco (validade)
- Classificar tipo de vinculo (funcionario ou terceirizado)
- Bloquear/desbloquear ajudante

## Pre-requisitos
- Dados pessoais do ajudante (CPF, nome, contato)
- Definicao do tipo de vinculo (funcionario ou terceirizado)
- Informacoes de gerenciamento de risco (quando aplicavel)

## Campos / Interface

### Cadastro (Opcao 163)
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| CPF | Sim | CPF do ajudante |
| Nome | Sim | Nome completo do ajudante |
| Relacao com a transportadora | Sim | C=funcionario, T=terceirizado |
| Status | Sim | Ativo ou Bloqueado |
| Data de cadastramento | Automatico | Data de inclusao no sistema |
| Validade gerenciamento de risco | Nao | Data de validade de certificacao/treinamento de risco |
| Unidade | Nao | Unidade de atuacao principal do ajudante |

### Relatorio (Opcao 164)
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Relacao com a transportadora | Sim | C=funcionarios, T=terceirizados, A=todos |
| Bloqueado | Sim | S=bloqueados, N=ativos, T=todos |
| Ultimo movimento - unidade | Nao | Filtrar por unidade de ultimo movimento |
| Ultimo movimento - periodo | Nao | Filtrar por periodo de ultimo movimento |
| Periodo de cadastramento | Nao | Filtrar por periodo de cadastro no sistema |
| Validade de gerenciamento de risco | Nao | Filtrar por periodo de validade de certificacao/risco |
| Arquivo em Excel | Sim | N=texto, S=planilha Excel |

## Fluxo de Uso

### Cadastrar Novo Ajudante
1. Acessar opcao 163
2. Informar CPF e nome completo
3. Selecionar tipo de vinculo (C=funcionario, T=terceirizado)
4. Definir status inicial (ativo)
5. Opcionalmente, informar validade de gerenciamento de risco
6. Salvar cadastro

### Bloquear Ajudante
1. Acessar opcao 163
2. Localizar ajudante pelo CPF ou nome
3. Alterar status para Bloqueado
4. Salvar alteracao

### Gerar Relatorio de Ajudantes
1. Acessar opcao 164
2. Selecionar filtros (vinculo, status, unidade, periodo)
3. Escolher formato de saida (texto ou Excel)
4. Gerar relatorio

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 164 | Relacao de Ajudantes (gera relatorios dos ajudantes cadastrados na opcao 163) |
| Manifestos | Ajudantes podem ser vinculados a Manifestos para entrega/coleta |
| Entregas | Ajudantes participam de operacoes de entrega |
| Coletas | Ajudantes participam de operacoes de coleta |

## Observacoes e Gotchas
- **Vinculo funcionario vs terceirizado**: Classificacao importante para gestao de pessoal, controle de custos e obrigacoes trabalhistas
- **Bloqueio nao remove cadastro**: Ajudante bloqueado permanece no sistema mas nao pode ser utilizado em novas operacoes
- **Gerenciamento de risco**: Campo de validade permite controle de certificacoes/treinamentos obrigatorios para operacao
- **Ultimo movimento rastreado**: Sistema registra automaticamente unidade e data do ultimo movimento do ajudante
- **Relatorio flexivel**: Opcao 164 permite multiplas combinacoes de filtros para consultas especificas
- **Formato Excel facilita analise**: Relatorio em Excel permite ordenacao, filtragem e analise posterior dos dados
- **CPF unico**: Cada CPF so pode ter um cadastro ativo no sistema
- **Data de cadastramento automatica**: Sistema registra automaticamente a data de inclusao do ajudante

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-A09](../pops/POP-A09-cadastrar-motorista.md) | Cadastrar motorista |
