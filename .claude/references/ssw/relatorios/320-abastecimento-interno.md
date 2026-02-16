# Opção 321 — Cadastro de Bombas Internas (Abastecimento)

> **Módulo**: Frota
> **Páginas de ajuda**: 1 página consolidada
> **Atualizado em**: 2026-02-14
> **Nota**: Arquivo fonte referencia opção 321, relacionada ao abastecimento interno (opção 320)

## Função
Efetua cadastramento de Bombas Internas para controle de abastecimento de veículos da frota, agregados e carreteiros.

## Quando Usar
- Cadastrar nova bomba interna
- Definir preços por litro para diferentes tipos de veículos
- Ajustar estoque de bomba interna
- Configurar volume inicial ao cadastrar bomba

## Pré-requisitos
- Filial onde a bomba será instalada deve estar cadastrada
- Opção 320 (abastecimento) utiliza as bombas cadastradas

## Campos / Interface

### Tela Principal

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| **Código** | Sim | Número atribuído à bomba interna (informar novo ou existente) |
| **SIGLA FILIAL** | Sim | Sigla da filial onde a bomba está instalada |
| **DESCRIÇÃO** | Sim | Descrição da bomba interna |
| **VOLUME ATUAL (l)** | Sim | Estoque inicial ao cadastrar. Excepcionalmente pode ajustar saldo de bomba já em uso |
| **VALOR SAÍDA (R$/l)** | Sim (3 campos) | Preço por litro cobrado no abastecimento (opção 320), específico para:<br>- Veículos Frota<br>- Veículos Agregado<br>- Veículos Carreteiro |

### Rodapé

| Função | Descrição |
|--------|-----------|
| **AJUSTES DE ESTOQUE** | Permite excepcionalmente ajustar saldo da bomba lançando entradas e saídas diretamente |

## Fluxo de Uso

### Cadastrar Nova Bomba
1. Acesse opção 321
2. Informe código da bomba (novo)
3. Selecione sigla da filial
4. Informe descrição
5. Informe volume inicial (estoque)
6. Defina valores de saída (R$/l) para Frota, Agregado e Carreteiro
7. Confirme cadastro

### Ajustar Estoque
1. Acesse opção 321
2. Informe código da bomba existente
3. Clique em "AJUSTES DE ESTOQUE" (rodapé)
4. Lance entrada ou saída diretamente
5. Confirme

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 320 | Abastecimento do veículo usando bomba cadastrada |

## Observações e Gotchas

### Volume Atual
- **Ao cadastrar**: informar estoque inicial
- **Bomba em uso**: excepcionalmente pode ajustar via campo "VOLUME ATUAL"
- **Forma correta de ajuste**: usar "AJUSTES DE ESTOQUE" no rodapé

### Valores Diferenciados
- Três preços distintos (R$/l):
  - **Frota**: veículos próprios
  - **Agregado**: veículos agregados
  - **Carreteiro**: veículos de carreteiros
- Preços aplicados automaticamente na opção 320 conforme tipo de veículo

### Controle de Estoque
- Estoque atualizado automaticamente ao abastecer via opção 320
- Entradas manuais: via "AJUSTES DE ESTOQUE"
- Saídas manuais: via "AJUSTES DE ESTOQUE" (excepcionalmente)

### Múltiplas Bombas
- Cada filial pode ter múltiplas bombas
- Identificação por código único
- Descrição ajuda a identificar localização/tipo

### Abastecimento
- Realizado via opção 320
- Bomba deve estar cadastrada nesta opção 321
- Sistema aplica automaticamente o valor (R$/l) conforme tipo de veículo

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-G03](../pops/POP-G03-custos-frota.md) | Custos frota |
