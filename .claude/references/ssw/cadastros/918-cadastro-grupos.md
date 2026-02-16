# Opcao 918 — Cadastro de Grupos

> **Modulo**: Cadastros
> **Paginas de ajuda**: 6 paginas consolidadas
> **Atualizado em**: 2026-02-14

## Funcao

Cadastra grupos de usuarios que controlam acessos a opcoes do sistema SSW. Define permissoes granulares por funcao/cargo na transportadora.

## Quando Usar

- Criar novo grupo de usuarios com perfil de acesso especifico
- Alterar permissoes de acesso de um grupo existente
- Listar opcoes liberadas para grupos
- Controlar acesso a tabelas de frete e resultado
- Configurar perfis por cargo (gerente, vendedor, operacao, cobranca, etc.)

## Pre-requisitos

- Apenas usuario master pode acessar esta opcao
- Planejar estrutura de grupos conforme organograma e necessidades de seguranca

## Campos / Interface

| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Grupo | Sim | Numero do grupo (identificador numerico) |
| Descricao | Sim | Descricao do grupo (ex: Gerentes, Vendedores, Operacao) |
| Acesso tab frete | Sim | N-bloqueia links FRETE e RESULTADO na opcao 101 |
| Permissoes de acesso | Sim | Selecao de opcoes que o grupo tera acesso |
| Liberar opcao | Acao | Libera ou bloqueia opcao se ja estiver liberada |

## Fluxo de Uso

### Criacao de Novo Grupo

1. Acessar opcao 918 (usuario master)
2. Informar numero do grupo (usar numeracao sequencial)
3. Preencher descricao clara e objetiva
4. Definir se grupo tem acesso a tabelas de frete (Acesso tab frete = S/N)
5. Selecionar opcoes que grupo pode acessar (campo Liberar opcao)
6. Salvar configuracao

### Alteracao de Permissoes

1. Acessar opcao 918
2. Selecionar grupo existente
3. Adicionar ou remover opcoes (campo Liberar opcao alterna estado)
4. Salvar

### Relatorio de Grupos

1. No rodape da tela, clicar em "Relacao dos Grupos e opcoes liberadas"
2. Excel e gerado com matriz Grupo x Opcoes

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| 925 | Cadastro de Usuarios vincular usuarios a grupos |
| 902 | Controle de acesso a relatorios gerenciais (opcao 056) |
| 101 | Links FRETE e RESULTADO bloqueados se Acesso tab frete = N |
| 028 | Grupo 092 SSWMOBILE criado automaticamente para motoristas |

## Observacoes e Gotchas

### Grupo 092 SSWMOBILE

- Uso exclusivo do SSW
- Cadastro automatico de motoristas via opcao 028
- NAO deve ser alterado manualmente

### Principio do Menor Privilegio

- Por questoes de seguranca, criar grupos com menor acesso possivel
- Novos acessos devem ser concedidos apos avaliacao rigorosa da alta administracao
- Evitar criar grupos com muitas permissoes desnecessarias

### Acesso a Tabelas de Frete

- Acesso tab frete = N: usuarios do grupo NAO veem links FRETE e RESULTADO na opcao 101
- Util para usuarios operacionais que nao devem ter acesso a informacoes comerciais

### Relatorios Gerenciais

- Controle de acesso a relatorios (opcao 056) e feito pela opcao 902, NAO pela 918
- Opcao 918 controla apenas acesso a opcoes do menu principal

### Usuarios Master

- Ate 6 usuarios master podem ser cadastrados pela Equipe SSW
- Usuario master tem acesso irrestrito ao sistema
- Sempre manter pelo menos 2 usuarios master ativos (redundancia)

### Grupos Tipicos

Exemplos de grupos comuns em transportadoras:

- **Gerencia**: acesso completo exceto configuracoes criticas
- **Vendedores**: opcoes de cliente, cotacao, tabelas de frete (consulta)
- **Operacao**: emissao CTRC, manifestos, entregas, ocorrencias
- **Cobranca**: faturas, inadimplencia, contas a receber
- **Financeiro**: contas a pagar, conciliacao, relatorios financeiros
- **Almoxarifado**: conferencia, etiquetas, manifestos
- **Motorista**: SSWMobile (grupo 092)
- **Cliente**: acesso restrito via opcao 426 (grupo especifico)

### Mudanca de Grupo

- Usuario muda de cargo: alterar grupo na opcao 925
- NAO e necessario recriar usuario, apenas trocar vinculo de grupo

### Auditoria

- Opcao 925/Rastreamento mostra opcoes acessadas por usuario
- Relatorio 146 (opcao 056) mostra estatisticas de acesso por usuario
- Importante para auditoria e identificacao de uso indevido

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-F06](../pops/POP-F06-aprovar-despesas.md) | Aprovar despesas |
