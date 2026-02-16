# Opcao 043 — Agendamento (Ocorrencias por Nota Fiscal)

> **Modulo**: Operacional — Coleta/Entrega
> **Paginas de ajuda**: 1 pagina consolidada
> **Atualizado em**: 2026-02-14

## Funcao
Registra ocorrencias de entrega em Notas Fiscais especificas para envio ao cliente via EDI. Permite informar entrega da NF antes da entrega total do CTRC.

## Quando Usar
- Informar entrega parcial de Notas Fiscais
- Registrar ocorrencias em NF especifica (nao no CTRC inteiro)
- Alimentar EDI com ocorrencias por NF

## Pre-requisitos
- CTRC com multiplas Notas Fiscais
- Codigo de ocorrencia (Opcao 405) do tipo NAO baixa/entrega
- Programa EDI configurado (Opcao 600)

## Campos / Interface

| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| CTRC | Sim | Serie e numero do CTRC |
| Nota Fiscal | Sim | Numero da NF a receber ocorrencia |
| Ocorrencia | Sim | Codigo (nao pode ser baixa/entrega) |
| Data/hora | Sim | Data e hora da ocorrencia |
| Complemento | Nao | Informacao complementar |

## Fluxo de Uso
1. Acessar Opcao 043
2. Informar CTRC
3. Informar numero NF
4. Selecionar codigo ocorrencia (Opcao 405)
5. Informar data/hora e complemento
6. Confirmar

## Formato Registro Complemento
Sistema grava no complemento da ocorrencia:
```
NF 999999999 99/99/99 XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```
Onde:
- 999999999 = numero da NF
- 99/99/99 = data da ocorrencia
- XXX... = texto informado pelo usuario

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| 038 | Baixa de entrega do CTRC (so apos todas NFs entregues) |
| 405 | Tabela de ocorrencias (codigo SSW 14 - NF Entregue) |
| 600 | EDI reconhece ocorrencias e envia ao cliente |

## Observacoes e Gotchas

### Ocorrencia de Entrega da NF
- Codigo correspondente ao SSW 14 - NOTA FISCAL ENTREGUE
- NAO pode ser do tipo baixa/entrega

### Entrega do CTRC
Somente apos **todas** NFs receberem ocorrencia de entrega, o CTRC pode ser baixado de entrega (Opcao 038).

### EDI
Programa EDI deve reconhecer ocorrencias por NF no complemento e incluir em arquivo EDI para cliente.
