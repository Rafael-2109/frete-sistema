# Opção 031 — CTRCs com Determinada Ocorrência

> **Módulo**: Operacional — Controle de Ocorrências
> **Páginas de ajuda**: 3 páginas consolidadas
> **Atualizado em**: 2026-02-14

## Função
Relaciona CTRCs que receberam determinada ocorrência em qualquer momento do transporte, facilitando identificação de processos específicos como indenizações.

## Quando Usar
- Equipe de indenização precisa identificar CTRCs indenizáveis
- Necessidade de localizar CTRCs com ocorrência específica no período
- Acompanhamento de processos de indenização e sinistros

## Pré-requisitos
- Ocorrências cadastradas na opção 405
- CTRCs com ocorrências registradas via opções 033, 038 ou outros meios

## Campos / Interface
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Período de emissão do CTRC | Sim | Período máximo de 31 dias, CTRCs emitidos nos últimos 90 dias |
| Data de ocorrência | Não | Período em que a ocorrência foi informada no sistema |
| Código de ocorrência | Sim | Localizada em qualquer etapa da operação, não precisa ser a última |
| CNPJ do cliente pagador | Não | Filtro por cliente específico |
| Conferente | Não | Associado ao CTRC na emissão do Manifesto (020) ou Romaneio (035) |
| Situação atual do CTRC | Sim | P=pendentes, B=baixados, T=todos |
| Arquivo Excel | Não | S=gera relatório em Excel |

## Fluxo de Uso - Processo de Indenização
1. **Opção 031**: Identificar CTRCs indenizáveis através de ocorrências específicas
2. **Opção 033**: Registrar pareceres da equipe de indenização
3. **Opção 475**: Lançar mercadoria no Contas a Pagar com documento de despesa do cliente, registrar imagem para venda (opção 586), anotar Número de Lançamento
4. **Opção 506**: Registrar indenização com Número de Lançamento, realizar repasse para unidades causadoras
5. **Opção 586**: Divulgar mercadoria para venda no Menu Principal (link "Venda de Salvados"), liquidar após venda
6. **Opção 142**: Relacionar CTRCs indenizados

## Relatório
| Coluna | Descrição |
|--------|-----------|
| Indenizou | Valores de indenização efetivamente pagos no CTRC (opção 506) |

## Integração com Outras Opções
| Opção | Relação |
|-------|---------|
| 033 | Registrar pareceres de indenização |
| 475 | Lançar mercadoria indenizada no Contas a Pagar |
| 506 | Registrar indenização e repasse de despesas |
| 586 | Venda de mercadorias indenizadas |
| 142 | Relatório de CTRCs indenizados |
| 405 | Cadastro de ocorrências |

## Observações e Gotchas
- **Ocorrência em qualquer momento**: Sistema localiza ocorrência mesmo que não seja a última atribuída ao CTRC
- **Período limitado**: Máximo 31 dias de emissão, últimos 90 dias
- **Processo completo**: Indenização envolve 6 opções diferentes em sequência
- **Imagens facilitam venda**: Opção 586 recomenda múltiplas imagens da mercadoria para facilitar compra
- **Lançamentos automáticos**: Venda de salvados gera lançamentos financeiros, contábeis e fiscais automaticamente
