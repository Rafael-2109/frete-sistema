# Industrialização FB↔LF

Industrialização por encomenda dentro do grupo: a **FB** (encomendante) remete insumos para a **LF** (industrializadora), que produz e devolve o produto acabado. O objetivo do projeto é **acertar o fluxo físico + contábil** para que o material de terceiros **não infle o ativo de estoque** (passivo medido: **R$ 785.569,62** só no MOLHO SHOYU PET).

## Mapa (leia nesta ordem)

| Doc | O que é |
|---|---|
| **`00_FLUXO_ATUAL_VS_IDEAL.md`** | O **alvo**. Relatório para Fiscal/Contábil: como é hoje (errado), como deveria ser (§3), o passivo e as perguntas ao Contador. |
| **`DIRETRIZ.md`** | A **decisão** da sessão 2026-05-29: abandona a "Opção 2 / inter-company"; adota a solução por **configuração das contas de categoria por-empresa na LF** (a LF não tem estoque próprio → tudo é terceiros). |
| **`ACHADOS_TECNICOS.md`** | O **mecanismo** verificado: como o Odoo/CIEL IT decide as contas (fatura vs valoração de estoque), por que é configurável, o gotcha do `rule_type`, e o mapa de IDs/contas. |
| **`PLANO_EXECUCAO.md`** | O **plano**: as 5 etapas sobre a infra já criada, o que configurar (Passo 0), as validações e o checklist. |

## Resumo em 4 linhas
- **Problema**: hoje os componentes do retorno são somados ao Ativo Estoque (LF e FB) em vez de baixados como material de terceiros.
- **Decisão**: fluxo baseado em picking (não em PO/SO); na LF, contas de categoria → terceiros (`1150200001`/`1150200002`), net-zero, por configuração.
- **Pendente**: validar as contas com o Contador + tratar o lado FB (Etapa 5, onde está o passivo) + executar quando os insumos do piloto voltarem à FB.
- **Estado**: piloto da abordagem antiga revertido (ver `DIRETRIZ.md` §5).

## ⚠️ `HISTORICO/`
Contém a execução-piloto da **Opção 2 (inter-company automático), revertida em 2026-05-29**. IDs/locations/picking-types/BoMs ali são válidos, mas o **fluxo descrito está ABANDONADO** — não seguir. Fonte do fluxo correto: este README + `DIRETRIZ.md` + `00_FLUXO_ATUAL_VS_IDEAL.md` §3.

> Convenção de testes (quando executar): documentar cada etapa em `T{NN}-resultado.md`.
