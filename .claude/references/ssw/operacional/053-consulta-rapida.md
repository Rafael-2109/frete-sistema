# Opcao 053 — Consulta Rapida (Recebimento de Reembolsos)

> **Modulo**: Financeiro — Reembolso
> **Paginas de ajuda**: 1 pagina consolidada
> **Atualizado em**: 2026-02-14

## Funcao
Permite recebimento de reembolsos apos entrega da mercadoria ao destinatario. Tambem cancela reembolsos antes do recebimento. Emite Capa de Lote de Cheques pre-datados para envio ao cliente.

## Quando Usar
- Receber reembolso (dinheiro ou cheque) apos entrega
- Cancelar reembolso informado errado
- Emitir Capa de Lote de Cheques para remessa

## Pre-requisitos
- CTRC com reembolso cadastrado
- Baixa de entrega realizada (Opcao 038)
- Unidade de destino do CTRC

## Campos / Interface (Opcao 053 - Recebimento)

| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| CTRC | Sim | Serie e numero do CTRC |
| Valor da mercadoria | Auto | Valor a receber do destinatario |
| Dinheiro | Condicional | Valor recebido em dinheiro |
| Cheque | Condicional | Banco, Numero, Valor, Bom-Para |

### Cancelamento
| Campo | Descricao |
|-------|-----------|
| CTRC | Serie e numero para estornar reembolso |

## Campos / Interface (Opcao 041 - Capa de Lote)

### Gerar Nova Capa
| Campo | Descricao |
|-------|-----------|
| Periodo do recebimento | Periodo de registro Opcao 053 |

### Reimprimir Capa
| Campo | Descricao |
|-------|-----------|
| Capa numero | Numero da capa a reimprimir |

## Fluxo de Uso

### Receber Reembolso
1. Motorista recebe dinheiro/cheque na entrega
2. Acessar Opcao 053
3. Informar CTRC (serie + numero)
4. Informar valor dinheiro e/ou dados cheque
5. Confirmar recebimento

### Cancelar Reembolso
1. Acessar Opcao 053
2. Usar campo "Cancelamento"
3. Informar CTRC a estornar
4. Confirmar

### Emitir Capa de Lote
1. Acessar Opcao 041
2. Informar periodo recebimento
3. Sistema gera Capa relacionando cheques pre-datados
4. Anexar cheques e comprovantes depositos (vista/nao pre-datados)
5. Enviar Capa ao cliente

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| 038 | Baixa de entrega (pre-requisito) |
| 041 | Emissao Capa de Lote de Cheques |
| 053 | Recebimento de reembolsos |
| 101 | Consulta situacao reembolso e numero Capa |
| 392 | Consulta situacao reembolso e numero Capa |

## Observacoes e Gotchas

### Somente Unidade de Destino
Reembolso so pode ser registrado pela unidade de destino do CTRC e apos baixa de entrega (Opcao 038).

### Recebimento Misto
Reembolso pode ser parte em dinheiro e parte em cheque se comprador decidir pagar assim.

### Capa de Lote
- Relaciona cheques pre-datados
- Tambem relaciona recebimentos a vista ou em cheques nao pre-datados
- Para nao pre-datados: anexar comprovantes deposito
- Numero da Capa consultavel em Opcao 101/Frete ou Opcao 392

### CTRCs na Capa
Inclui:
- Cheques pre-datados para deposito futuro
- Recebimentos a vista (anexar comprovante deposito)
- Cheques nao pre-datados (vias ja entregues ao cliente)
