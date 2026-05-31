# PROMPT — Próxima sessão (Industrialização FB↔LF)

> **Reescrito 2026-05-30.** Substitui integralmente a versão anterior (congelada em 29/05, que apontava para a diretriz `1150200001` ABANDONADA).

## Como começar
Leia nesta ordem (CANÔNICO): **`README.md` → `GOALS.md` → `SOT_OPERACOES.md` (v2.1) → `CICLO_COMPLETO_MAPA.md` → `ACHADOS_TECNICOS.md` → `PROPOSTA_CONFIG_RETORNO.md`** + os `T-*-resultado.md`.
**IGNORE** (referência histórica, NÃO seguir): `DIRETRIZ.md`, `PLANO_EXECUCAO.md`, `00_FLUXO §3`, `PASSO0_LEVANTAMENTO §conta`, `HISTORICO/`.

## Decisões já fechadas (não reabrir)
- **Conta**: família de compensação **`51010xx` (ATIVA) / `51020xx` (PASSIVA)** é a conta FISCAL. **NÃO** `1150200001` (a `DIRETRIZ` errou). `1150200001` é só a **valoração SVL** da LF (camada distinta).
- **Saída FB (remessa) JÁ está correta** (`D 5101010001 / C 1150100002`). O problema é o **RETORNO** não fechar (`5101010001` FB acumula R$60,8M; double-count R$785k).
- **SEM ICMS** em nenhuma etapa (CST51 + CBS/IBS/PIS/COFINS). **Não mexer em imposto.**
- **Tudo é CONFIG** (operação fiscal **por LINHA** `account.move.line.l10n_br_operacao_id` + flag `l10n_br_movimento_estoque`), **não DEV**.

## Estado no Odoo PROD (2 escritas config aplicadas — REVERSÍVEIS)
1. **Op 3252** criada — "Retorno insumo SIMBOLICO (G5b PILOTO) FB-LF" = cópia da op 2027 só com `l10n_br_movimento_estoque=False` + sem `cfop_orig` (isolada, aplicar manual). É o lever G5b. *(reverter: desativar a op)*. Ver `T-G5B-OP-resultado.md`.
2. **L1 aplicado (Design A)** — 14 categorias LF repointadas: valoração→`1150200001`(26140), input→`1150100011`(26845), output→`1150100012`(26855). *(reverter: `python scripts/e2e_l1_repoint_lf.py --revert` — baseline versionado em `scripts/e2e_l1_snapshot_baseline.json`)*. Ver `T-L1-resultado.md`. **⚠️ Design A está aplicado mas NÃO validado no fluxo com NF — validar na Etapa 2 do piloto.**

## Próximo passo: PILOTO E2E do 4870112 (batch = 1 CAIXA = 12 un) — NÃO iniciado
Sequência (cada NF SEFAZ = IRREVERSÍVEL, só com "go" do Rafael):

| Etapa | Ação | Métrica de sucesso (Δ do ciclo, ver GOALS §B) |
|---|---|---|
| 1. Remessa FB→LF | pt53, NF 5901 (16 componentes p/ 1 caixa) | remessa gera `D 5101010001 / C 1150100002` |
| 2. LF recebe | DFe 1901 (pt64 dst 31092 ou pt19) | SVL `D 1150200001 / C 1150100011`; **Δ1150100011 (LF) = 0** (valida Design A); estoque próprio LF não sobe |
| 3. MO LF | BoM 3695→3646 (1 caixa) | consumo+produção net-zero; PA em 31093 |
| 4. LF retorno | pt98, NF mista 5902+5903+5124 | **Δ5101020001 (LF) = 0**; 0 lanç. em "SAÍDA-PERDAS" |
| 5. FB recebe | pt52; **aplicar op 3252 na linha 1902** (`l10n_br_operacao_manual=True` + `l10n_br_operacao_id=3252`) | **0 SVL de componentes** (MP/EMB não re-entram); **Δ5101010001 (FB) = 0**; estoque FB sobe só em PA(+sobra) |

**Meta-final** (ciclo fechado, Δ): `5101010001=0 · 5101020001=0 · 26489(produto 4870112)=0 · FORNECEDORES(FB)=Receita(LF)=S · 0 double-count`.

## RESOLVER ANTES/DURANTE o piloto (achados do reviewer 2026-05-30)
1. **Runbook da Etapa 1 (falta)**: definir os 16 componentes + **quantidades** (p/ 1 caixa; ver `e2e_dimensionar_batch.py`) + **lotes**; **picking type de CRIAÇÃO** da remessa; as **pré-condições de `liberar_faturamento`** (ACHADOS §4: incoterm=6, carrier_id=996, operação+CFOP na linha, warehouse_id) como checklist; decidir **criar remessa nova vs reaproveitar**. *(Os 16 insumos do piloto estão em FB/Estoque desde 29/05 — NF 725676 cancelada, picking 322049 revertido.)*
2. **G5b — resíduo empírico**: confirmar no piloto (Etapa 5) que a **NF mista** gera picking só das linhas `movimento_estoque=True` (1124/1903), pulando a 1902 (op 3252). Granularidade por-linha já confirmada estruturalmente; falta o teste vivo.
3. **L1 Design A**: validar na Etapa 2 que `Δ1150100011 (LF) = 0` (a NF entrada fecha a transitória). Se não fechar → reavaliar A vs B com Contador.
4. **Fixar números do piloto**: Ic (custo dos componentes), S (R$35/cx × qtd), e cenário **com/sem sobra** (Is) — define quais linhas/contas esperar.
5. **Criar script** `g5b_aplicar_op3252_na_linha.py` (dry-run) p/ a aplicação da op 3252 na linha 1902 (hoje só receita manual no T-G5B-OP).

## Pendente Contador (destrava G5a/rollout; pode ir em paralelo ao piloto G5b)
- **G5a**: criar journal de entrada com `account_no_payment_id=5101010001` (não existe — entrada hoje cai em PASSIVA 5101020001/2) p/ o retorno baixar a ATIVA.
- **"3 pernas"**: como o custo `Ic` entra no valor do PA (3 opções na `PROPOSTA §3 PERNAS`).
- **Conta valoração SVL-LF** `1150200001` (colisão com server action 1899) vs par dedicado.
- **Conta PRODUÇÃO** `1150100004` (L3).
- **Regularização** dos acumulados (`5101010001` FB R$60,8M + LF R$8,67M; double-count R$785k; `1150100011` −R$1,49bi). Modo A/B/C.

## Regras invioláveis
- **NF SEFAZ** (Etapas 1 e 4) = IRREVERSÍVEL → só com "go" explícito do Rafael; dry-run + apresentar antes de qualquer escrita Odoo.
- NÃO reativar `rule_type=sale_purchase`. Entrada LF = picking físico (não DFe→PO). MO LF = manual.
- Dados sempre do **Odoo PROD via XML-RPC**. `action_gerar_po_dfe` herda company do user → forçar `allowed_company_ids=[5]` se usar.
- Conexão: `from app.odoo.utils.connection import get_odoo_connection` (search_read NÃO aceita context → usar execute_kw com context p/ campos company-dependent).

## Polish pendente nos docs (baixo, não bloqueia)
Tabela canônica journal→`account_no_payment_id` em ACHADOS; mini-glossário "simbólico/net-zero" no SOT §0; alinhar nota da prova SOT §3 (a perna `D PA / C 5101010001` do 1902 depende da decisão "3 pernas").
