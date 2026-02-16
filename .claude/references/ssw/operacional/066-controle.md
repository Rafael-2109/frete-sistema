# Opcao 066 — Controle (Remessa Vias de Cobranca CTRCs)

> **Modulo**: Financeiro — Faturamento
> **Paginas de ajuda**: 1 pagina consolidada
> **Atualizado em**: 2026-02-14

## Funcao
Emite CAPAS DE REMESSA para vias de cobranca dos CTRCs enviarem ao Faturamento da Matriz. Permite rastreabilidade de documentos enviados pelas unidades.

## Quando Usar
- Enviar vias de cobranca de CTRCs para Matriz
- Controlar remessa de documentos para faturamento
- Rastrear CAPAS enviadas

## Pre-requisitos
- CTRCs emitidos com vias de cobranca
- Equipe de Faturamento na Matriz configurada

## Campos / Interface

### Gerar Nova Capa
| Campo | Descricao |
|-------|-----------|
| Periodo de emissao | Periodo emissao CTRCs (sugerido: hoje) |

### Reimprimir Capa
| Campo | Descricao |
|-------|-----------|
| Numero | Numero da Capa a reimprimir (sugerido: ultima gerada) |

## Fluxo de Uso

### Gerar Capa
1. Ao final do dia, acessar Opcao 066
2. Informar periodo emissao CTRC
3. Sistema gera CAPA DE REMESSA
4. Anexar vias de cobranca e CTRCs cancelados
5. Encaminhar a Equipe de Faturamento na Matriz

### Recepcionar Capa (Matriz)
1. Equipe Faturamento recepciona via Opcao 434
2. Permite faturamento de clientes com condicao "COM VIA DE COBRANCA RECEPCIONADA"

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| 066 | Esta opcao (gera Capa) |
| 101 | Consulta numero Capa que CTRC foi incluido |
| 434 | Recepcao de Capas pela Matriz |

## Observacoes e Gotchas

### Precisao e Fundamental
Conferencia rigorosa entre CAPA e vias anexadas e essencial para evitar erros e simplificar trabalho do Faturamento.

### CTRCs Cancelados
- Relacionados na Capa
- Devem ser anexados

### CTRCs A VISTA
- Relacionados na Capa
- Vias de cobranca seguiram com mercadoria (nao anexar)

### Consulta de Inclusao
Opcao 101 informa numero da Capa em que CTRC foi incluido por esta Opcao 066 e situacao dela no momento.

### Processo Completo
1. Expedicao unidades emite Capa (Opcao 066)
2. Anexa vias de cobranca + CTRCs cancelados
3. Envia a Matriz
4. Matriz recepciona (Opcao 434)
5. Faturamento libera clientes com condicao especifica
