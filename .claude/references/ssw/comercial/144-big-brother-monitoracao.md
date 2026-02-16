# Opção 144 — Big Brother SSW - Monitoração das Ações

> **Módulo**: Administrativo/Gerencial
> **Referência interna**: Opção 145
> **Páginas de ajuda**: 1 página consolidada
> **Atualizado em**: 2026-02-15

## Função

Monitora ações sendo executadas pelos gerentes de filiais. Sistema de controle gerencial que exige execução diária de relatórios e telas específicas para liberação do acesso ao SSW.

## Quando Usar

- Monitorar cumprimento de ações estabelecidas para gerentes de filiais
- Avaliar e discutir ações gerenciais (em conjunto com opção 144)
- Acompanhar execução diária de rotinas críticas por parte dos gerentes
- Controlar acesso ao sistema condicionado à execução de ações obrigatórias

## Campos / Interface

### Tela de Monitoração

**Unidade**: Unidade do usuário que possui ação cadastrada

**Usuário**: Usuário (opção 925) que possui ação cadastrada

**Grupo**: Grupo (opção 918) que possui ação cadastrada

**Qtde ações**: Quantidade de ações cadastradas para o usuário

**Realizadas**: Quantidade de ações realizadas pelo usuário
- Ao clicar na quantidade, nova tela é trazida com identificação detalhada das respectivas ações

## Integração com Outras Opções

- **Opção 144**: Cadastramento de usuários (gerentes de filiais) submetidos ao monitoramento do Big Brother SSW
- **Opção 145**: Monitoração de ações pela alta administração (MTZ)
- **Opção 925**: Cadastro de usuários
- **Opção 918**: Cadastro de grupos

## Observações e Gotchas

### Processo Completo do Big Brother SSW

1. **Cadastramento de usuários**: Gerentes de filiais são cadastrados pela opção 144 para monitoramento
2. **Execução das ações**: Diariamente gerentes devem abrir relatórios e telas específicas para obter senhas
3. **Liberação de acesso**: Senhas devem ser informadas no Menu Principal (primeiro acesso do dia). Sem isto, acesso às demais partes do SSW não é liberado
4. **Monitoração**: Alta administração (MTZ) monitora gerentes por esta opção 145, além de avaliar e discutir ações estabelecidas

### Conceito "Big Brother"

Nome faz referência ao conceito de monitoramento constante, garantindo que ações gerenciais críticas sejam executadas diariamente.

### Bloqueio de Acesso

Sistema bloqueia acesso ao SSW até que ações obrigatórias do dia sejam executadas pelo gerente, garantindo disciplina operacional.

### Detalhamento de Ações

Clicar no número de ações realizadas permite drill-down para identificação detalhada de cada ação específica.
