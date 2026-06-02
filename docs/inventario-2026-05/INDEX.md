<!-- doc:meta
tipo: index
camada: L1
sot_de: —
hub: docs/INDEX.md
superseded_by: —
atualizado: 2026-06-02
-->
# Inventario 2026-05 — indice
> **Papel:** mapa do ciclo de inventario 2026-05 (NACOM/LF/CD/FB). So ponteiros (paths a partir da raiz do repo).

## Estado

> **Fonte canonica unica do estado do ciclo = `docs/inventario-2026-05/SOT.md`.** Os demais itens abaixo sao componentes vivos subordinados (PENDENCIAS) ou registros forenses imutaveis (logs e CHECKPOINTs — snapshots historicos, NAO sao o estado atual).

**Vivo (consultar para o estado atual):**
- `docs/inventario-2026-05/SOT.md` — **fonte da verdade do ciclo** (canonica)
- `docs/inventario-2026-05/PENDENCIAS.md` — pendencias abertas (P1-P13)
- `docs/inventario-2026-05/PROMPT_PROXIMA_SESSAO_LF.md` — prompt de retomada LF (numeros podem estar defasados — sempre conferir contra o SOT)
- `docs/inventario-2026-05/PICKINGS_PENDENTES_INVOICE.md` — pickings pendentes de invoice (verificar status ao vivo no Odoo antes de agir)

**Registros forenses (HISTORICO — imutaveis, nao sao estado atual):**
- `docs/inventario-2026-05/AJUSTES_EMERGENCIAIS_FB.md` — ajustes emergenciais FB executados
- `docs/inventario-2026-05/AUDIT_LOG_AJUSTES.md` — log de auditoria dos ajustes
- `docs/inventario-2026-05/CHECKPOINT_2026_05_18_CD_FINALIZADO.md` — checkpoint CD finalizado
- `docs/inventario-2026-05/CHECKPOINT_2026_05_18_LF_FIM_SESSAO2.md` — checkpoint LF (snapshot; serie completa em `99-historia/`, incl. SESSAO3 mais recente)

## Por categoria (subpastas)
- `docs/inventario-2026-05/08-execucoes/README.md` — execucoes (indice da subpasta)
- `docs/inventario-2026-05/99-historia/README.md` — historia (indice da subpasta)
- `docs/inventario-2026-05/00-decisoes/` — decisoes (D0xx)
  - `docs/inventario-2026-05/00-decisoes/D015-gold-script-aposentado-para-atomos.md` — ADR: "gold-script" aposentado em favor de atomos C1/C2 + subagente (2026-05-22)
  - `docs/inventario-2026-05/00-decisoes/D016-evolucao-mecanismo-g1-g2-g3.md` — ADR: evolucao G1 (NF-heavy) -> G2 -> G3 (inventory adjustment direto, sem NF)
- `docs/inventario-2026-05/01-premissas/` — premissas
- `docs/inventario-2026-05/02-gotchas/` — gotchas (Gxxx)
- `docs/inventario-2026-05/07-relatorios/` — relatorios
- `docs/inventario-2026-05/casos-pendentes/` — casos pendentes
- `docs/inventario-2026-05/consolidacao/` — consolidacao de scripts
- `docs/inventario-2026-05/v10-skill2-indisp-em-lote/` — v10 skill2 indisp em lote
