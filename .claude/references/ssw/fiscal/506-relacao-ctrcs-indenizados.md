# Opcao 506 — Relacao de CTRCs Indenizados

> **Modulo**: Fiscal
> **Paginas de ajuda**: 1 pagina consolidada
> **Atualizado em**: 2026-02-14

## Funcao
Gera relacao de CTRCs indenizados que foram lancados via opcao 506. Permite filtrar por cliente/grupo, periodo de emissao do CTRC ou periodo de indenizacao. Relatorio disponivel em formato Excel.

## Quando Usar
- Consultar historico de indenizacoes pagas
- Gerar relatorios de CTRCs indenizados por periodo
- Auditar indenizacoes por cliente ou grupo de clientes
- Exportar dados de indenizacoes para analise externa

## Pre-requisitos
- CTRCs com indenizacoes lancadas (opcao 506)
- Clientes e grupos cadastrados (se for filtrar)

## Campos / Interface
| Campo | Obrigatorio | Descricao |
|-------|-------------|-----------|
| Cliente / Grupo | Nao | Filtro opcional (se nao informado, considera todos) |
| Formato Excel | Nao | Gera relatorio em formato Excel |
| Periodo de emissao do CTRC | Nao* | Filtro por data de emissao do conhecimento |
| OU Periodo de indenizacao | Nao* | Filtro por data de registro da indenizacao (opcao 506) |

*Obs: Informar um dos dois periodos (emissao OU indenizacao)

## Fluxo de Uso
1. Acessar opcao 142 (relacao de CTRCs indenizados)
2. Opcionalmente filtrar por cliente ou grupo
3. Escolher criterio de periodo: emissao do CTRC ou data de indenizacao
4. Informar periodo desejado
5. Opcionalmente marcar formato Excel
6. Executar relatorio

## Integracao com Outras Opcoes
| Opcao | Relacao |
|-------|---------|
| 506 | Lancamento de indenizacoes (origem dos dados) |
| 142 | Geracao do relatorio (opcao atual) |

## Observacoes e Gotchas
- **Filtro de periodo**: pode usar periodo de emissao do CTRC OU periodo de indenizacao (nao ambos simultaneamente)
- **Cliente/Grupo opcional**: se nao informar, relatorio considera todos os clientes
- **Formato Excel**: util para analises externas e manipulacao de dados
- **Fonte dos dados**: apenas CTRCs com indenizacao lancada via opcao 506 aparecem no relatorio
