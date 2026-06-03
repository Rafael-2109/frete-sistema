<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/inventario-2026-05/00-decisoes/INDEX.md
superseded_by: —
atualizado: 2026-06-02
-->
# D016 — evolucao do mecanismo de ajuste G1 -> G2 -> G3 (deprecar NF-heavy)
> **Papel:** ADR que registra por que o mecanismo de ajuste de estoque evoluiu 3 vezes e por que G1 (NF-heavy) foi depreciado. **Contexto deste doc:** estratificacao das 3 geracoes, formalizada na Onda 3 PAD-A.

## Contexto

Ao longo da operacao de inventario 2026-05, o mecanismo de ajuste de estoque evoluiu tres vezes. Cada geracao reduziu a emissao de Notas Fiscais na SEFAZ, diminuindo risco fiscal e dependencia do robo CIEL IT.

**G1 — NF inter-company (heavy):**
Ajuste via NF inter-company por diferenca liquida: `picking` -> `robo CIEL IT` -> `SEFAZ` -> `entrada no destino`. Emite NF. Decisoes formalizadas: D004 e D005.

**G2 — pre-etapa interna com lote MIGRACAO:**
Consolidacao interna usando o lote MIGRACAO como intermediario: transferencia interna + residual minimo. **Sem emissao de NF**. Decisoes formalizadas: D006 e D007.

**G3 — inventory adjustment direto via planilha (mecanismo ATUAL):**
Ajuste via `stock.quant` + `action_apply_inventory`, utilizando locais "Indisponivel" como staging. **Sem emissao de NF**. Decisoes formalizadas: D010 a D013.

## Decisao

Preferir **G2/G3** (sem emissao SEFAZ) sobre G1 sempre que o caso permitir:

- Menos NF emitidas = menos risco fiscal e contabil.
- Menos dependencia do robo CIEL IT (que apresentou instabilidade no ciclo 2026-05).
- Operacao mais rapida: sem aguardar robo + sync DFe.

G1 permanece no repertorio apenas para casos que **genuinamente exigem** NF inter-company (ex: transferencia fiscal com obrigacao legal, casos auditados pelo fiscal).

## Consequencias

- Explica a estratificacao dos ~105 scripts do inventario: muitos pertencem a geracoes anteriores (G1 ou G2) e nao representam a pratica atual.
- Scripts de G1 (ex: `09_executar_onda1_bulk`, familia `fat_lf_*`) ficam classificados como SUPERSEDED/DEAD quando o caso pode usar G3 — varios foram aposentados na Onda 3 PAD-A.
- Refuta a abordagem NF-heavy de D004 como default para ajustes de estoque.
- A Onda 3 PAD-A indexa e sinaliza o status de cada script com base nessa estratificacao G1/G2/G3.

## Fontes

- `docs/inventario-2026-05/consolidacao/MAPA_ASSUNTOS.md` — secao §1 ("As 3 geracoes de mecanismo")
- `docs/inventario-2026-05/00-decisoes/D004-rename-lote-diferenca-liquida.md` — decisao original G1
- `docs/inventario-2026-05/00-decisoes/D005-lote-migracao-consolidador-fantasmas.md` — decisao original G1
- `docs/inventario-2026-05/00-decisoes/D006-transferir-quantidade-entre-lotes-nao-renomear.md` — decisao G2
- `docs/inventario-2026-05/00-decisoes/D007-pre-etapa-cd-fb-minimizar-nf.md` — decisao G2
- `docs/inventario-2026-05/00-decisoes/D010-direcao-transferencia-migracao-por-sinal-diff_qtd.md` — decisao G3
- `docs/inventario-2026-05/00-decisoes/D013-ajuste-fb-cd-indisponivel-via-planilha-de-para.md` — decisao G3
