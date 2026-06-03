# Histórico — Inventário 2026-05

Esta pasta arquiva **checkpoints intermediários** e **prompts de próxima sessão antigos** gerados durante o trabalho de ajuste do inventário 2026-05 (NACOM Goya FB+CD + LA FAMIGLIA).

**Não use estes arquivos para retomar trabalho.** São audit trail temporal, não estado atual.

---

## Para retomar trabalho, leia (na raiz `docs/inventario-2026-05/`):

| Documento | Papel |
|---|---|
| `SOT.md` | Estado macro do trabalho (única página sempre atual) |
| `CHECKPOINT_2026_05_18_LF_FIM_SESSAO2.md` | Estado atual LF (34 EXECUTADO + 1682 PROPOSTO + gotchas G016-G020 fixados) |
| `PROMPT_PROXIMA_SESSAO_LF.md` | Tarefas concretas próxima sessão LF |
| `PENDENCIAS.md` | P1-P10 pendências cross-empresa |
| `PICKINGS_PENDENTES_INVOICE.md` | Pickings done aguardando invoice CIEL IT |
| `AUDIT_LOG_AJUSTES.md` | Documentação da trilha forense (ajuste_estoque_inventario_audit) |
| `AJUSTES_EMERGENCIAIS_FB.md` | 10 ajustes E01-E10 emergenciais FB (referência P2-P10) |
| `CHECKPOINT_2026_05_18_CD_FINALIZADO.md` | Estado final CD onda 5 (6.746/6.897 executados — referência sessão paralela) |

---

## Ordem cronológica dos arquivos nesta pasta

1. **`CHECKPOINT_2026_05_17_FIM_DIA.md`** (2026-05-17 fim do dia)
   Pré-piloto, pipeline F7.1-7.4 completo, 23.639 ajustes PROPOSTO, caso piloto 210030325 LF definido.

2. **`CHECKPOINT_2026_05_18_PILOTO_COMPLETO.md`** (2026-05-18 madrugada, ~02:15)
   Pós-piloto NF SEFAZ autorizada (chave 35260518...8607), 6 ajustes EXECUTADO, D004 generalizada FB+CD, 5 fixes L1-L5.

3. **`CHECKPOINT_2026_05_18_BULK_PRONTO.md`** (2026-05-18 ~02:50)
   Entrada FB do piloto via RecebimentoLf, MIGRAÇÃO padronizado, bulk script 09 validado em dry-run.

4. **`CHECKPOINT_2026_05_18_SUBPILOTO_FINAL.md`** (2026-05-18 ~04:30)
   Sub-piloto 10 produtos com 13 fixes L6-L17 detalhados (ponteiros file:line já migrados para gotchas G021-G023), 2 NFs autorizadas, picking 317346 pendente invoice.

5. **`QUICK_START_NEXT_SESSION.md`** (2026-05-18 ~05:00)
   Prompt para sessão pós-sub-piloto. Obsoleto — 11 PROPOSTO pendentes já tratados.

6. **`CHECKPOINT_2026_05_18_PRE_ETAPA_CD_EXECUTADA.md`** (2026-05-18 manhã, sessão paralela)
   Execução pré-etapa CD onda 5 — 6.879 ajustes EXECUTADO (97.8%). Substituído pelo `CD_FINALIZADO` (na raiz).

7. **`CHECKPOINT_2026_05_18_FIXES_L18_L23.md`** (2026-05-18 manhã)
   Re-execução sub-piloto com L18-L23: G014 FEFO, G015 price_unit, G016 marcado PENDENTE. 2 NFs autorizadas (626032 com XML vazio, 627348 OK).

8. **`PROMPT_PROXIMA_SESSAO_2026_05_18B.md`** (2026-05-18 ~07:20)
   Prompt intermediário apontando para NCM_PENDENTE. Ações descritas (cancelar NF 626032, cadastrar NCM ALHO EM PO) já executadas — ver `EXECUCAO_CADASTRO_NCM_WEIGHT_2026_05_18.md` em `08-execucoes/`.

9. **`CHECKPOINT_2026_05_18_NCM_PENDENTE.md`** (2026-05-18 manhã)
   Diagnóstico G017 NCM=False como root cause da NF 626032 rejeitada. Audit fiscal LF revelando 109 produtos sem weight. **Explicitamente substituído** pelo `LF_FIM_SESSAO2` (na raiz).

---

## Decisão de arquivamento (2026-05-18)

Estes 9 arquivos foram arquivados porque:

- 7 são checkpoints intermediários do mesmo dia (2026-05-18), todos suplantados pelo `LF_FIM_SESSAO2` (na raiz) que tem o estado atual consolidado
- 2 são prompts de próxima sessão antigos, suplantados pelo `PROMPT_PROXIMA_SESSAO_LF` (na raiz)

**Informação crítica única** que estava em alguns destes arquivos foi migrada para gotchas/decisões permanentes antes do arquivamento:

- Ponteiros file:line dos fixes L6-L17 → ver `02-gotchas/G021-etapa-a-reporta-prematuro.md`, `G022`, `G023`, `G026` (este último criado a partir do `SUBPILOTO_FINAL`)
- E1/E2 (duplicação acidental, workaround stock.lot.name ignorado) → ver `00-decisoes/D008-licoes-seguranca-operacional-e1-e2.md` (criado a partir do `CD_FINALIZADO`)
- B1/B2 (bugs latentes 09b) → ver `02-gotchas/G027-09b-bugs-latentes-b1-b2.md` (criado a partir do `CD_FINALIZADO`)
- Lista de 10 produtos sem cadastro Odoo no CD → ver `PENDENCIAS.md` P11
