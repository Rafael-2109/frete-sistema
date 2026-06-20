<!-- doc:meta
tipo: explanation
camada: L1
sot_de: —
hub: CLAUDE.md
superseded_by: —
atualizado: 2026-06-19
-->
# MotoChefe — Guia de Desenvolvimento

> **Papel:** hub de navegacao do modulo MotoChefe (distribuidora B2B de motos eletricas: estoque FIFO por chassi, vendas, financeiro, logistica com rateio de frete, custos). Abra antes de editar `app/motochefe/`.

## Contexto

Blueprint `motochefe_bp` registrado em `app/__init__.py:1303-1305`. ~20.7K LOC; 14 tabelas em `models/` (cadastro, produto [`Moto` = central], vendas, financeiro, logistica, operacional). A documentacao tecnica completa do modulo vive em `app/motochefe/documentacao/` (indexada pelo seu proprio `README.md`). As **Lojas HORA** (`app/hora/`, B2C) e **Motos Assai** (`app/motos_assai/`, B2B Q.P.A. Sendas) referenciam entidades MotoChefe.

## Mapa de Navegacao

| Preciso de... | Vou para |
|---|---|
| **Indice completo da documentacao tecnica** (26 docs: estrutura BD, fluxos, financeiro, UI) | [README da documentacao](app/motochefe/documentacao/README.md) |
| Estrutura do banco (14 tabelas) | `app/motochefe/documentacao/ESTRUTURA_BD.md` |
| Fluxo completo de pedidos / parcelamento FIFO | `app/motochefe/documentacao/FLUXO_COMPLETO_PEDIDOS.md`, `app/motochefe/documentacao/FLUXO_PARCELAMENTO_FIFO.md` |
| Fluxo financeiro (titulos, comissoes, extrato) | `app/motochefe/documentacao/AUDITORIA_FLUXO_FINANCEIRO.md`, `app/motochefe/documentacao/EXTRATO_FINANCEIRO_IMPLEMENTACAO.md` |
| Especificacao original | `app/motochefe/documentacao/escopo.md` |
| **Carga inicial / importacao historica** (campos Excel, titulos, movimentacoes) | `app/motochefe/ANALISE_CAMPOS_IMPORTACAO.md`, `app/motochefe/IMPORTACAO_HISTORICA_README.md`, `app/motochefe/MODELO_IMPORTACAO_TITULOS.md`, `app/motochefe/EXPLICACAO_MOVIMENTACOES_HISTORICO.md` + how-tos em `docs/motochefe/` |

> Referencia compartilhada do projeto: [CLAUDE.md raiz](../../CLAUDE.md). Conteudo dev-only: `.claude/references/REGRAS_DEV_LOCAL.md`.
