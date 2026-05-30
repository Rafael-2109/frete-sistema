# PENDÊNCIAS — Industrialização FB↔LF

> Decisões e dúvidas aguardando resposta humana (Rafael ou Fiscal).
> Cada item bloqueia 1 ou mais tasks em `ROADMAP_TASKS.md`.

---

## ~~A01~~ — ⛔ RESOLVED 2026-05-28 por D17
**Quem decidiu**: Rafael
**Como foi resolvido**: investigação XML-RPC mostrou que:
- X105000022 (com X, id=27866) está arquivado.
- 105000022 (sem X, id=30761) é MP ativa SEM BoM (produto comprado).
- BoM 3695 (a real do piloto) NÃO usa nem X105000022 nem 105000022 DIRETAMENTE. Usa BATELADA DE SHOYU (semi-acabado LF, BoM filha 3646 que por sua vez usa 105000022 como componente).
- A BoM 14833 (subcontract antiga, FB) que mencionava SHOYU TRADICIONAL na seq=4 será desativada em T33.

**Conclusão (D17)**: BATELADA é subprocesso interno LF (não cruza fronteira FB↔LF). A remessa FB→LF contém 17 componentes (7 emb + 9 quim + 1 MP shoyu_tradicional), excluindo apenas ÁGUA. Detalhe completo em `DECISOES.md#D17`.

---

## ~~A02~~ — ⛔ PARCIALMENTE RESOLVED 2026-05-29 (NF saída) — restante para T25/T26
**Quem decidiu**: Rafael (validação empírica via NF 725676)
**Como foi resolvido**: validação empírica da NF saída FB 725676 (CFOP 5901) revelou que **TODAS as 16 linhas usam `account_id=26846 '1150100012 FATURAMENTO FISICO FISCAL'`** — UMA SÓ conta. As contas previstas no plano original (1150100002 MATERIAL EMBALAGEM, 1150100007 PA, 1150100011 RECEBIMENTO FISICO FISCAL, 1150200001 MATERIAL EM TERCEIROS) **não foram usadas** na NF saída.
**Conta confirmada empírica**: `account.account` id=**26846** code=**1150100012** name="FATURAMENTO FISICO FISCAL" (cmp=FB).
**Pendente**: contas usadas em NF retorno (T25) — 5124/5902/5903 — verificar quando emitida. Pode usar 1150200001 MATERIAL EM TERCEIROS (esperado pelo plano).

---

## A02 — Contas contábeis por categoria de componente (legado)
**Quem decide**: Rafael (consultando Contador se necessário) ou descobrir via teste
**Bloqueia**: T29 (validação matemática completa)
**Contexto**: validamos contas para:
- ROTULO (categ 75) → 1150100002 MATERIAL DE EMBALAGEM
- PA (categ 193) → 1150100007 PRODUTO-ACABADO
- Conta transitória → 1150100011 RECEBIMENTO FISICO FISCAL
- Material em terceiros → 1150200001

Mas a BoM tem componentes de outras categorias:
- 104000xxx → MP química (ácido cítrico, sal, benzoato, sorbato, etc.)
- 105000xxx → outras MP (corante, açúcar, aroma, antiespumante, semi-acabado)
- 207xxx, 208xxx → EMB (etiqueta, filme, fita)
- 210xxx → EMB (frasco, tampa, caixa, rótulo)

**Como descobrir sem Contador**: Claude pode rodar uma consulta no Odoo para listar `property_stock_valuation_account_id` de cada categoria, e Rafael valida visualmente se faz sentido.

Comando (Claude pode rodar a qualquer momento):
```python
conn.search_read('product.category',
    [('id','in',[lista_categorias_da_BoM])],
    ['name','property_stock_valuation_account_id'])
```

---

## ~~A03~~ — ⛔ RESOLVED 2026-05-29 por D19
**Quem decidiu**: Rafael
**Como foi resolvido**: D19 unificou T13+T21 e autorizou execução imediata com produto piloto 4870112 direto. Estoque dos 3 componentes ajustado nesta sessão (`testes/T-AJUSTE-ESTOQUE-resultado.md`).
**Próximo passo**: Rafael cria PO FB→LF (4870112, partner=LF id=35, qty=10 cx, preço unit R$ 35,00).

---

## ~~A05~~ — ⛔ RESOLVED 2026-05-29 por D23 (que supersede a resolução errada de D20)
**Quem decidiu**: Rafael
**Como foi resolvido**:
- D20 inicialmente fechou A05 com `LF/Estoque (42)` — interpretação errada de rule 135.
- D23 (mesma data) corrigiu: PA cai em **`LF/PA de Terceiros (31093)`** conforme spec original (D11 + T03 criou exatamente para isso).
- MO LF 20154 foi criada com `location_dest_id=31093` forçado.
- T07 (pt=98 LF/SAI/IND/RET) tem `src=31093` consistente.

---

## A08 — Como gerar PO via `action_gerar_po_dfe` com `company_id=5 (LF)` correto?
**Quem decide**: Rafael (eventualmente PCP LF / TI)
**Bloqueia**: T23 caminho B (próxima sessão), e por consequência T24-T28 do piloto.
**Contexto**: na sessão 2026-05-29, Skill 7 caminho B chamou `gerar_po_from_dfe(43689)`. Robô CIEL IT criou PO 42676 mas em **company_id=1 (FB)** em vez de 5 (LF), apesar do DFe estar em company=5. Causa raiz suspeitada: `action_gerar_po_dfe` herda contexto do user que executa o XML-RPC (Rafael uid=42 com `company_id` principal=FB). PO 42676 foi cancelada nesta sessão. DFe 43689 está pronto para nova tentativa (`purchase_id=False`).

**4 hipóteses (registradas em `testes/T23-caminho-B-skill7-resultado.md` linhas 86-103)**:
- **A** — Re-executar `gerar_po_from_dfe(43689)` autenticado como user com `company_id` principal=LF (candidato: Edilane uid=78 PCP LF se tiver `purchase.group_purchase_manager`).
- **B** — Forçar context `{'allowed_company_ids': [5], 'force_company': 5}` no execute_kw interno.
- **C** — Aceitar PO criada errada e usar `preencher_po` da Skill 7 com `company_id=5`, `picking_type_id=64`, `fiscal_position_id=131`, `operacao_id=2686` + write 16 linhas com `account_id` LF + `l10n_br_cfop_id=101`.
- **D** — Write XML-RPC direto na PO 42676 (alternativa a C, mais cirúrgica).

**Recomendação**: hipótese **A** (mais limpo, alinhado ao plano original "PCP LF aponta MO no sistema").

---

## Removidos da v1 (não aplicam ao cenário Rafael+Claude)

- ~~A04 (intercompany_user dedicado)~~: usando OdooBot mesmo. Se der erro de permissão no T13, ajustamos.
- ~~A06 (journal específico inter-company)~~: usar journals existentes. Se Fiscal pedir separação no S2, criamos depois.
- ~~A07 (SO travada)~~: Rafael resolve quando aparecer (PCP=Rafael).

---

## Histórico

| Data | Item | Status | Resolução |
|---|---|---|---|
| 2026-05-28 | A01–A03, A05 | aguardando | Rafael responde |
| 2026-05-28 | A04, A06, A07 | descartado | Cenário simplificado Rafael+Claude |
| 2026-05-28 | A01 | ⛔ resolved | D17 — BATELADA é subprocesso interno LF, BoM 3695 não usa X105000022 (arquivado) nem 105000022 (na BoM filha 3646) |
| 2026-05-29 | A03 | ⛔ resolved | D19 — fusão T13+T21, piloto direto com 4870112 (começa imediatamente) |
| 2026-05-29 | A05 | ⛔ resolved | D20 — PA cai em LF/Estoque por default (rule 135 Fabricar) |
| 2026-05-29 | A05 | ↩ corrigido | D23 superseded D20 — PA cai em LF/PA de Terceiros (31093) |
| 2026-05-29 | A08 | aguardando | Gap company na PO criada por `action_gerar_po_dfe` — bloqueia continuidade do piloto |
| 2026-05-29 | A02 | ⛔ parcialmente resolved | NF saída usa só conta 26846 (1150100012). Pendente apenas contas da NF retorno T25. |
