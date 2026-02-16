# Opção 733 — Emissão de RPSs

> **Módulo**: Logística
> **Páginas de ajuda**: 2 páginas consolidadas
> **Atualizado em**: 2026-02-14

## Função
Gera RPS (Recibo Provisório de Serviços) para serviços diversos que não se referem a operação de transporte, como armazenagem, Ordens de Serviço em portos, etc.

## Quando Usar
- Para serviços que NÃO sejam transporte (para transporte, usar opção 004)
- Cobrança de serviços de armazenagem (Armazém Geral / Operador Logístico)
- Controle de serviços de coleta, entrega ou devolução de contêineres em portos
- Serviços diversos que precisam de cobrança mas não são transporte

## Pré-requisitos
- Código de Prestação de Serviço cadastrado na Prefeitura
- Cliente cadastrado no sistema (opção 483)

## Campos / Interface

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Última RPS | Informativo | Série e número do último RPS gerado pela unidade |
| CNPJ do consignatário | Sim | CNPJ contratante do serviço (órgão público identificado com CFOP = U) |
| Serviços | Sim | Descrição do serviço prestado (impresso no RPS) |
| Nota fiscal | Não | NF do cliente para qual foi realizado serviço |
| Valor serviços | Sim | Valor dos serviços a ser cobrado do cliente |
| Cód prest serviço | Sim | Código de Prestação Serviço (deve estar cadastrado na Prefeitura) |
| Efetuar retenções | Sim | S para deduzir retenções do valor do serviço |
| CEP (local prestação) | Não | CEP para local de prestação diferente (opcional) |

## Fluxo de Uso
1. Acessar opção 733
2. Informar CNPJ do consignatário
3. Descrever o serviço prestado
4. Informar valor dos serviços
5. Selecionar código de prestação de serviço
6. Definir se haverá retenções
7. Confirmar geração do RPS
8. Gerar arquivo pela opção 014 e transmitir à Prefeitura (em até 10 dias)
9. Importar retorno das NFPSs geradas pela Prefeitura (opção 014)
10. Imprimir NFPS pela opção 009

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 004 | Para serviços de transporte (não usar opção 733) |
| 014 | Geração de arquivo e transmissão à Prefeitura / Importação de retorno |
| 009 | Impressão da NFPS |
| 731 | Digitação de Ordem de Serviço (para controle de movimentação em portos) |
| 701 | Entrada no estoque (armazenagem) |
| 702 | Saída do estoque (armazenagem) |

## Observações e Gotchas

### Retenções
**S** indica que retenções serão deduzidas do valor do serviço:
- **PIS**: Regime cumulativo: 0,65% / Não cumulativo: 1,65% / Órgão público: 0,65%
- **COFINS**: Regime cumulativo: 3% / Não cumulativo: 7,5% / Órgão público: 3%
- **CSLL**: 1%
- **IR**: Conforme código de serviço (1601/1602: 1% / 1104: 4,8% / 1703: 1,5%)
- **INSS**: 11%
- **ISS**: Definido para cidade na opção 402
- **Limite mínimo**: Retenções não ocorrem quando resultado for menor que R$10,00

### Características Importantes
- **Criada baixada**: RPS é criada já baixada operacionalmente (apenas para cobrança)
- **Não pode ser alterada**: Deve ser cancelada e outra gerada
- **Cancelamento**: Usar opção 004 (RPS gerado por opção 733 não pode ser alterado)
- **Distrito Federal**: Emite NF-e em vez de RPS (cancelamento pela opção 014)
- **Prazo**: Normalmente em até 10 dias arquivo deve ser gerado e transmitido à Prefeitura
- **Novos códigos**: Podem ser solicitados ao Suporte SSW quando necessário
- **Função da OS (opção 731)**: Controle de serviços de coleta, entrega ou devolução de contêineres no porto (não possuem valor fiscal e não geram movimentação financeira)
- **Cobrança da OS**: Deve ser realizada com emissão do RPS (opção 733)
