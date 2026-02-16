# Opção 390 — Cadastro de Espécies de Mercadorias

> **Módulo**: Comercial/Cadastro
> **Referência interna**: Opção 407
> **Páginas de ajuda**: 1 página consolidada
> **Atualizado em**: 2026-02-15

## Função

Cadastra Espécies de Mercadorias para gerenciamento de risco e emissão de CTRCs. Permite associação automática via NCM do XML da NF-e.

## Quando Usar

- Cadastrar novas espécies de mercadorias para gerenciamento de risco
- Configurar NCMs que sugerem automaticamente a espécie na emissão de CTRCs
- Associar espécies a clientes específicos
- Gerenciar agrupamento de mercadorias conforme necessidade do PGR (Plano de Gerenciamento de Risco)

## Campos / Interface

### Tela de Cadastro

**Código**: Código numérico da espécie atribuído pelo usuário

**Ativa**:
- **S** - Indica que a espécie está ativa (pode ser utilizada)
- **N** - Espécie inativa

**Descrição**: Descrição da espécie de mercadoria

**NCM** (opcional): Quando cadastrado, sugere esta espécie de mercadoria na emissão de CTRCs (opção 004, 005 e 006)
- Aceita até **10 NCMs** por espécie
- Pode ser utilizado de **2 a 8 dígitos** (Tabela NCM)
- Inicia pela esquerda

## Integração com Outras Opções

- **Opção 390 (PGR)**: Agrupa mercadorias conforme necessidade do Plano de Gerenciamento de Risco
- **Opção 004/005/006**: Emissão de CTRCs - espécie é atribuída na emissão
- **Opção 207**: Definição automática da espécie pelo NCM do XML da NF-e
- **Opção 483**: Associação de espécies ao cliente

## Observações e Gotchas

### Função Básica

As funções da Espécie de Mercadoria são:
- **Gerenciamento de risco**: Agrupa mercadorias conforme necessidade do PGR
- **Sugestão automática**: Via NCM na emissão de CTRCs

### NCM - Sugestão Automática

Sistema permite configurar NCMs que automaticamente sugerem a espécie na emissão de CTRCs. Flexibilidade de usar de 2 a 8 dígitos permite agrupamentos por:
- **2 dígitos**: Capítulo (ex: 84 = Máquinas)
- **4 dígitos**: Posição (ex: 8471 = Computadores)
- **6 dígitos**: Subposição (ex: 847130 = Computadores portáteis)
- **8 dígitos**: NCM completo (ex: 84713012 = Notebooks)

### Associação ao Cliente

Espécies devem ser associadas ao cliente pela opção 483, permitindo controle específico por cliente.

### Limite de NCMs

Cada espécie pode ter até 10 NCMs associados, permitindo agrupamentos complexos de produtos similares.

### Espécies Inativas

Espécies marcadas como inativas (Ativa = N) não podem ser utilizadas na emissão de novos CTRCs, mas continuam aparecendo em CTRCs antigos.

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-G01](../pops/POP-G01-sequencia-legal-obrigatoria.md) | Sequencia legal obrigatoria |
| [POP-G02](../pops/POP-G02-checklist-gerenciadora-risco.md) | Checklist gerenciadora risco |
