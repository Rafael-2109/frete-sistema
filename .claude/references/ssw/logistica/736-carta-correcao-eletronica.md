# Opção 736 — Emissão da Carta de Correção Eletrônica

> **Módulo**: Logística
> **Páginas de ajuda**: 2 páginas consolidadas
> **Atualizado em**: 2026-02-14

## Função
Emite Carta de Correção (CC-e) para corrigir erros não fiscais em CT-es e NF-es que não podem mais ser cancelados.

## Quando Usar
- Para corrigir erros em CT-es/NF-es que não podem ser cancelados devido a restrições do SEFAZ
- Quando é necessário alterar campos não fiscais do documento
- Para correções após período de cancelamento ter expirado

## Pré-requisitos
- CT-e ou NF-e já autorizado pelo SEFAZ
- Impossibilidade de cancelamento do documento

## Campos / Interface

### Carta de Correção CT-e
Podem ser alterados:
- Origem e Destino da prestação
- Razão Social e endereço do:
  - Remetente
  - Expedidor
  - Pagador (diferente do remetente/destinatário)
  - Destinatário
  - Local de Entrega
- **Corrigir Nota Fiscal**: Corrige as NFs referenciadas no CT-e
- **Observações**: Fica arquivada para próxima CC-e (pode ser corrigida pelo link "Corrigir observações")

### Carta de Correção NF-e
Campos permitidos conforme legislação.

## Fluxo de Uso
1. Acessar opção 736
2. Informar número do CT-e ou NF-e
3. Alterar campos permitidos (não fiscais)
4. Informar observações sobre a correção
5. Confirmar geração da CC-e
6. Para reimpressão, informar novamente a CC-e nesta mesma opção

## Integração com Outras Opções

| Opção | Relação |
|-------|---------|
| 450 | Cancelamento de CTRCs (impossibilidade dispara uso da opção 736) |
| 520 | Anulação de ICMS (alternativa quando cancelamento não é possível) |

## Observações e Gotchas

### Restrições Importantes
- **Campos não fiscais apenas**: Não pode alterar alíquota, valor do ICMS, chave NF-e, UF destino, tomador do frete, etc.
- **Campos inabilitados**: Campos que modificam fiscalmente o documento estarão inabilitados na tela
- **CT-e em contingência SVC**: Não podem receber CC-e
- **Impossibilidade de cancelamento**: CT-e com Carta de Correção (opção 736) não pode ser cancelado

### Características da CC-e
- **Alterações cumulativas**: Todas as alterações numa CC-e já emitida são cumulativas
- **Última versão**: Permanece apenas a última CC-e com todas as alterações
- **Múltiplas alterações**: CC-es podem ser alteradas diversas vezes pela mesma opção 736
- **Reimpressão**: Basta informar novamente a CC-e na mesma opção

### Legislação
- **CC-e de NF-e**: Ajuste SINIEF 07/2005 e Ajuste SINIEF 08/07
- **CC-e de CT-e**: Ajuste SINIEF 09/07 e NT2024,001-v.1.02

### Alternativas
- **Cancelamento não possível**: Se o cancelamento não for possível, pode-se anular o ICMS pela opção 520
- **GNRE emitida**: CTRC com GNRE emitida (opção 160) receberá alerta no cancelamento
- **CTRC unitizado**: Se cancelado (opção 450), será retirado da unitização (opção 609), mas a unitização continua com os demais CTRCs
