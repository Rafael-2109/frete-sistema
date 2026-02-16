# Opcao 036 — Controle (Consulta Romaneios Cancelados)

> **Modulo**: Operacional — Coleta/Entrega
> **Paginas de ajuda**: 1 pagina consolidada
> **Atualizado em**: 2026-02-14

## Funcao
Consulta Romaneios de Entregas cancelados pela Opcao 037.

## Quando Usar
- Consultar historico de Romaneios cancelados
- Auditar cancelamentos

## Pre-requisitos
- Romaneios previamente cancelados (Opcao 037)

## Campos / Interface

| Campo | Descricao |
|-------|-----------|
| Numero Romaneio | Numero do Romaneio cancelado |
| Periodo | Periodo de cancelamento |
| Unidade | Unidade emissora |

## Fluxo de Uso
1. Acessar Opcao 036
2. Informar filtros (numero, periodo ou unidade)
3. Sistema lista Romaneios cancelados

## Integracao com Outras Opcoes

| Opcao | Relacao |
|-------|---------|
| 035 | Emissao de Romaneio de Entregas |
| 037 | Cancelamento de Romaneio |

## Observacoes e Gotchas

### Romaneios Cancelados
- Somente Romaneios sem ocorrencias nos CTRCs podem ser cancelados
- Cancelamento via Opcao 037
- Consulta via Opcao 036
