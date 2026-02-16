# Opção 499 — Replicar Configurações do CTRB de Transferência por Veículo

> **Módulo**: Comercial/Operacional
> **Páginas de ajuda**: 1 página consolidada
> **Atualizado em**: 2026-02-15

## Função
Copiar configurações de CTRBs/OSs (Ordens de Serviço) de transferência de um veículo para outros veículos, replicando tabelas cadastradas.

## Quando Usar
Quando for necessário:
- Padronizar configurações de CTRB de transferência entre veículos da frota
- Configurar rapidamente novos veículos usando tabelas existentes
- Aplicar mesma tabela de transferência para veículos do mesmo tipo

## Pré-requisitos
- Veículo origem com tabela de CTRB de transferência já cadastrada (opção 499)
- Veículos destino cadastrados no sistema
- Permissão de acesso à opção

## Campos / Interface

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Replicar do veículo | Sim | Placa do veículo que possui tabela cadastrada (opção 499) |
| Para veículo | Condicional | Placa do veículo que usará mesma tabela — sistema replica automaticamente ao informar |
| Para veículo tipo CAVALO | Condicional | Link abre tela para seleção múltipla de veículos tipo CAVALO |
| Para veículo tipo TRUCK | Condicional | Link abre tela para seleção múltipla de veículos tipo TRUCK |
| Para veículo tipo TOCO | Condicional | Link abre tela para seleção múltipla de veículos tipo TOCO |

## Fluxo de Uso

1. Informar placa do veículo origem (que possui tabela cadastrada)
2. Escolher forma de replicação:
   - **Individual**: Informar placa do veículo destino — sistema replica automaticamente
   - **Por tipo**: Clicar em link CAVALO/TRUCK/TOCO → selecionar múltiplos veículos
3. Sistema copia tabelas de CTRB de transferência para veículos selecionados

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 499 | Cadastro de CTRBs/OSs de transferência por veículo — tabelas replicadas por esta opção |

## Observações e Gotchas

- **Replicação automática**: Ao informar placa de destino, sistema replica automaticamente (não requer confirmação adicional)

- **Seleção múltipla por tipo**: Links permitem replicar para múltiplos veículos de uma vez, desde que sejam do mesmo tipo (CAVALO, TRUCK ou TOCO)

- **Sobrescrita de configurações**: Se veículo destino já possuir tabela, ela será sobrescrita pela do veículo origem — conferir antes de replicar

- **CTRB vs CT-e**: CTRB é o Conhecimento de Transporte Rodoviário de Bens (documento antigo, anterior ao CT-e eletrônico). Esta opção trabalha com transferências internas da transportadora

---

## POPs Relacionados

| POP | Processo |
|-----|----------|
| [POP-D01](../pops/POP-D01-contratar-veiculo.md) | Contratar veiculo |
