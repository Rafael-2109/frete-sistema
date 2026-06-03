<!-- doc:meta
tipo: how-to
camada: L2
sot_de: —
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# PAD-A Onda 4g — SSW + SELAGEM (registro de execucao)

> **Papel:** registro do que a sub-onda 4g fez (SSW + selagem) e como o gate de docs
> chegou a `block`. Ultima sub-onda da Onda 4 (varredura por cluster); fecha o
> roadmap [2026-06-02-pad-a-onda-4-varredura-cluster.md](2026-06-02-pad-a-onda-4-varredura-cluster.md).

## Contexto

Entrada (origin/main `d0757d7d3`): C1=322, C7=1, C8=277, D4=1, D2=122. A 4a–4f ja
haviam zerado todos os clusters menos o SSW e alguns residuos non-SSW. 4g levou o
`doc_audit --report-only` a **0 blockers GLOBAL** e promoveu C1/C7/C8 a `block`.

## Bloco A — SSW estrutura (zera 274 C8)

- 10 sub-INDEX criados (`completar_index --create`): cadastros, contabilidade, edi,
  embarcador, financeiro, fiscal, logistica, pops, relatorios, visao-geral.
- comercial (+64) e operacional (+29) completados; ssw/INDEX.md ganha secao
  "Sub-indices por diretorio (13)"; references/INDEX.md ganha aresta creditada
  `→ ssw/INDEX.md`. Efeito: C8 SSW 274 → 0.

## Bloco B — SSW carimbo (zera 309 C1)

- **Decisao de tipo (refino da Estrategia A):** pops/opcoes/fluxos/visao-geral (299) →
  `how-to`; 6 transversais raiz → `reference`; ssw/INDEX.md + fluxos/INDEX.md →
  `reference` (landing-pages ricas; permanecem hubs C8 por basename, evitam o check
  HUB index-only). Motivo de `how-to` p/ opcoes: `reference` dispara `banned_hedge`
  (alguns/varios/muitos) em prosa narrativa = lint-teatro sem acesso ao SSW.
- Desmascarados corrigidos: C7 109 (51 `.htm` → URL completa SSW; 58 `subdir/file.md`
  no INDEX → prefixo `./`); C6 2 (TOC em ssw/INDEX e operacional/INDEX); D4 1.

## Bloco C — residuo non-SSW (global-zero)

- 13 docs/raiz avaliados vivo/morto contra o codebase (workflow 13 agentes Explore):
  **8 vivos carimbados** (4 reference + 4 explanation com Contexto honesto),
  **5 mortos arquivados** em `docs/_deprecated/` (fora da auditoria) + README com evidencia.
- C7: criado `docs/inventario-2026-05/07-relatorios/INDEX.md` (`git add -f`, dir gitignored).
- D4: reword em ESTUDO + gerindo-agente/SCRIPTS.md.
- C8 (3): blueprint-agente/INDEX += ROADMAP; superpowers/plans/INDEX += evolucao plan;
  hub do evolucao plan → plans/INDEX (BIDIR).

## Bloco D — SELAGEM

- `checks_reach.py`: C8 `report` → `block` (3 emits) + docstring. C1/C7 ja eram block.
- `tests/audits/test_artefato_checks_reach.py`: severidade `block` + teste de regressao
  `test_severidade_block_altera_exit` (exit_code == 1 se houver orfao).
- SOT `ARQUITETURA_DE_ARTEFATOS.md`: nota da selagem (C1/C7/C8 block).

## Gate de saida

`doc_audit --report-only` exit=0 GLOBAL (0 blockers; **134 D2 advisory permanecem por
design** — references sem `## Fontes`, calibracao da decisao 2). Suite de auditoria/docs
verde. Promocao so afeta audit completo / commits que tocam o grafo (C8 auto-skip parcial).
