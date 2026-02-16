# Opção 585 — Exportar Tabelas de Fretes

> **Módulo**: Comercial/Financeiro
> **Páginas de ajuda**: 1 página consolidada
> **Atualizado em**: 2026-02-15

## Função
Exportar tabelas de fretes de clientes deste domínio para outro domínio SSW (parceiro subcontratante), permitindo replicação de configurações comerciais entre transportadoras parceiras.

## Quando Usar
Quando for necessário:
- Replicar tabelas de fretes de clientes para transportadora subcontratante parceira
- Padronizar configurações comerciais entre parceiros
- Facilitar operação de subcontratação mantendo mesmos valores de frete

## Pré-requisitos
- **Subcontratado cadastrado como parceiro** da subcontratante (opção 408)
- **Subcontratante com aprovação centralizada de tabela de fretes ativada** (opção 013/Frete)
- **Siglas de unidades coincidentes** entre os parceiros (opção 401)
- Permissão de acesso à opção

## Campos / Interface

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Para o domínio | Sim | Sigla do domínio da subcontratante (destino das tabelas) |
| Clientes | Sim | CNPJs dos clientes cujas tabelas serão exportadas |

## Fluxo de Uso

### Preparação (executar uma vez por parceiro)
1. Subcontratante ativa aprovação centralizada de tabelas (opção 013/Frete)
2. Subcontratado cadastra subcontratante como parceiro (opção 408)
3. Verificar se siglas de unidades (opção 401) são coincidentes entre parceiros

### Exportação de tabelas
4. Acessar opção 585
5. Informar sigla do domínio destino (subcontratante)
6. Informar CNPJs dos clientes cujas tabelas serão exportadas
7. Confirmar — sistema exporta tabelas para o parceiro
8. **Subcontratante** ativa tabelas recebidas pela opção 518

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 518 | Ativar tabelas recebidas — usado pela SUBCONTRATANTE para ativar tabelas exportadas |
| 408 | Cadastro de parceiros — subcontratado deve estar cadastrado como parceiro |
| 013/Frete | Aprovação centralizada de tabelas — deve estar ativada na SUBCONTRATANTE |
| 401 | Unidades — siglas devem ser coincidentes entre parceiros |

## Observações e Gotchas

- **Fluxo bidirecional**:
  - **Opção 585**: Exportar (usado por SUBCONTRATADO)
  - **Opção 518**: Ativar (usado por SUBCONTRATANTE)

- **Requisito crítico — Aprovação centralizada**: Subcontratante PRECISA ter aprovação centralizada de tabelas ativada (opção 013/Frete) — exportação NÃO funciona sem isso

- **Sobrescrita automática**: Tabelas de mesma origem/destino/mercadoria da subcontratante serão **sobrescritas** pelas exportadas — não há merge, apenas substituição

- **Siglas de unidades**: Devem ser exatamente iguais entre parceiros (ex: se subcontratado usa "SP01", subcontratante também deve usar "SP01") — inconsistência impede exportação correta

- **Cliente inexistente**: Se cliente não existir no SSW do subcontratante, será **cadastrado automaticamente** durante importação

- **Cadastro de parceiro obrigatório**: Subcontratado precisa estar cadastrado como parceiro da subcontratante (opção 408) — não é possível exportar para domínio não parceiro

- **Validação antes de exportar**: Verificar requisitos (parceiro cadastrado, aprovação centralizada, siglas coincidentes) ANTES de executar exportação para evitar problemas

- **Segurança**: Exportação só funciona entre parceiros cadastrados — não é possível exportar para qualquer domínio SSW
