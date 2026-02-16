# Opção 132 — Pneus do Veículo (Movimentação)

> **Módulo**: Frota
> **Páginas de ajuda**: 1 página consolidada
> **Atualizado em**: 2026-02-14
> **Nota**: Arquivo fonte referencia opção 132, mas trata de movimentação de pneus (relacionado à opção 316)

## Função
Mostra os pneus instalados no veículo e permite alterações e inclusões de pneus.

## Quando Usar
- Consultar pneus instalados em um veículo
- Alterar pneu instalado
- Incluir novo pneu ao veículo
- Visualizar posições dos pneus no veículo

## Pré-requisitos
- Veículo cadastrado
- Pneus cadastrados (opção 313)
- Módulo Frota ativado

## Campos / Interface

### Tela

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| **Placa** | Sim | Placa do veículo a consultar |

### Visualização de Pneus

- **Pneus do veículo** são relacionados após informar a placa
- Cada pneu é vinculado via opção 316
- Clicando sobre um pneu, abre o cadastro (opção 313) para manutenção

## Fluxo de Uso

1. Acesse opção 132
2. Informe placa do veículo
3. Sistema lista todos pneus instalados no veículo
4. Para alterar/consultar pneu, clique sobre ele
5. Sistema abre opção 313 (cadastro do pneu)

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 313 | Cadastro de pneus (aberto ao clicar sobre pneu) |
| 316 | Vinculação de pneus aos veículos |
| 317 | Vida do pneu (quilometragem total e histórico de posições) |

## Observações e Gotchas

### Vinculação de Pneus
- Pneus são vinculados ao veículo via opção 316
- Esta opção 132 apenas visualiza e permite acesso ao cadastro

### Posições no Veículo
- Posições definidas conforme padrão (vide opção 317):
  - 1º dígito: eixo (1 a 9, dianteira para traseira)
  - 2º dígito: E (esquerdo) ou D (direito)
  - 3º dígito: I (interno), E (externo) ou branco
  - 4º dígito: T (tração) ou branco
  - S1, S2: estepes
  - CONS: conserto
  - Sigla da filial: almoxarifado

### Histórico de Pneus
- Para histórico completo de posições e quilometragem: opção 317
- Inclui quilometragem por veículo desde fevereiro/2018

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-A08](../pops/POP-A08-cadastrar-veiculo.md) | Cadastrar veiculo |
| [POP-G03](../pops/POP-G03-custos-frota.md) | Custos frota |
