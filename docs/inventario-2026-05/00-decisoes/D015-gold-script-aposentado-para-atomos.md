<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/inventario-2026-05/INDEX.md
superseded_by: —
atualizado: 2026-06-02
-->
# D015 — "gold-script" aposentado em favor de atomos C1/C2 + subagente
> **Papel:** ADR que registra a substituicao da abordagem "gold-script" pela arquitetura de atomos versateis. **Contexto deste doc:** decisao de design 2026-05-22, formalizada na Onda 3 PAD-A.

## Contexto

A operacao de inventario 2026-05 gerou aproximadamente 105 scripts ad-hoc, resultado do anti-padrao "nao procurar -> recriar" sob pressao operacional. Para enderecar essa proliferacao, a primeira metodologia de consolidacao (adotada em 2026-05-20, decisao do Rafael) foi estruturada como:

> `gold-script` -> `manual` -> `guia` -> `orquestrador`

Nessa abordagem, a ideia era produzir UMA primitiva versatil por assunto em `app/odoo/services/`, depois documentar manuais e guias de uso. O vocabulario "gold-script" designava esse artefato central por assunto.

## Decisao

Em 2026-05-22, o vocabulario e a abordagem "gold-script" foram **aposentados**. A arquitetura adotada passa a ser de **atomos versateis e auto-seguros** (services C1/C2) em `app/odoo/estoque/scripts/`, consumidos por **skills** (`.claude/skills/`) que se compoe em **fluxos** (`app/odoo/estoque/fluxos/`, progressive disclosure), orquestradas pelo subagente **gestor-estoque-odoo**.

A constituicao vigente desta arquitetura esta em `app/odoo/estoque/CLAUDE.md`.

A consolidacao e **demand-driven**: um assunto e capinado (scripts legados aposentados, atomo criado) somente quando surge demanda real, nao em massa.

## Consequencias

- `MAPA_SCRIPTS.md`, `MAPA_ASSUNTOS.md` e `PLANO_MIGRACAO.md` passam a ser artefatos de mineracao transitoria, nao entregaveis permanentes.
- O termo "gold-script" sai do vocabulario corrente do projeto; referencias antigas em docs legados sao deixadas no lugar (sem reescrita retroativa — reescrita exigiria tocar docs gerenciados, disparando C1 desnecessariamente).
- A Onda 3 do PAD-A **governa** (indexa e aposenta os scripts-fonte mortos) sem re-arquitetar codigo vivo. Re-arquitetura de codigo vivo = demand-driven via atomos.
- Refuta a premissa de que consolidacao exige reescrever tudo num pacote de uma vez (big-bang migration).

## Fontes

- `app/odoo/estoque/CLAUDE.md` — constituicao da arquitetura de atomos vigente
- `docs/inventario-2026-05/consolidacao/MAPA_SCRIPTS.md` — nota Onda 2 PAD-A no topo (registra a transicao de vocabulario)
