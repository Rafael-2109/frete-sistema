# Encontro de Contas FB↔LF — Pasta23.xlsx (2026-05-20)

> Doc de trabalho VIVO desta operação. Sobrevive a compactação de contexto.
> Operador: Claude Code (autônomo, autorizado por Rafael 2026-05-20 ~22h).

## Objetivo

Faturar a planilha `Downloads/Pasta23.xlsx` (100 linhas, 43 produtos) entre FB
(company 1) e LF (company 5) aplicando **encontro de contas** por produto, em vez
de faturar as 2 pontas cheias.

## Regra do usuário (CONFIRMADA, ele validou o resultado do benzoato)

Por produto: `mov_liquido = qtd_entrada(FB→LF) − qtd_saida(LF→FB)`

- **mov_liquido > 0**: ALTERA todos os lotes (de saída, que estão no LF) PELOS
  lotes das ENTRADAS (consolida no lote-alvo). O que faltar para completar os
  lotes de entrada, preenche com `mov_liquido` = faturamento real FB→LF
  (industrialização, CFOP 5901 saída FB / 1901 entrada LF, company 5,
  tipo_pedido='serv-industrializacao').
- **mov_liquido < 0**: preenche todos os lotes de entrada; o que sobrar troca para
  MIGRAÇÃO, fatura LF→FB e move para FB/Indisponível.

### Exemplo validado — 104000004 BENZOATO (mov_liquido = +9,1764)
- Saída LF→FB (5 lotes): P-15/05 6,5946 + 0609/24 6,7416 + 0109 8,82 +
  1110/24 15,0838 + FAT-104000004-20260520 177,4814 = **214,7214**
- Entrada FB→LF (2 lotes): 20250802 219,31 + INV-104000004-20260518 4,5878 = **223,8978**
- RESULTADO ALVO no LF: **20250802=219,31 + INV-=4,5878 = 223,8978** (1 NF de 9,1764 FB→LF)

## Autorização (Rafael, 2026-05-20)
- Planilha inteira, ambas as direções, **NF SEFAZ inclusa** (irreversível).
- Autonomia total ("não me pergunte, aja até finalizar").
- Protocolo de erro: se picking der erro REAL (não demora) → cancelar fatura (se
  houver) → cancelar picking → devolver qtds → buscar causa → refazer até dar certo.
- Cuidar de DetachedError e SSL connection timeout.

## Estado descoberto (banco local + Odoo prod CIEL IT)

### Rodada anterior FATURAMENTO_LF_2026_05_20 (planilha RELACAO FATURAMENTO LF.xlsx, 01:49) — JÁ EXECUTADA
- PERDA_LF_FB: 194 EXECUTADO F5e_SEFAZ_OK
- DEV_LF_FB: 67 EXECUTADO F5e_SEFAZ_OK
- INDUSTRIALIZACAO_FB_LF: 59 F5f_ENTRADA_OK + 30 **TRAVADOS em F5d_BLOCKER_TX** + 5 sem fase
- PERDA_LF_FB: 5 F5c_LIBERADO pendente
- ⇒ A Pasta23 (21:54) é POSTERIOR e parte do saldo já alterado. NÃO é a mesma planilha.

### Validação Pasta23 vs saldo REAL Odoo (54 saídas LF→FB)
- **48 OK** (saldo livre suficiente) ⇒ Pasta23 é incremental, não duplica.
- **4 RESERVADO** (precisa liberar reserva antes de realocar):
  - 104000004 lote 0109 (sai 8,82 / livre 3,19) e 1110/24 (sai 15,08 / livre 9,15)
  - 109000055 lote 0810 (sai 5080,87 / livre 5027,57)
  - 208000010 lote 2210/24 (sai 3398,10 / livre 2338,90)
- **2 FALTA (saldo não bate — BLOQUEAR até decisão)**:
  - 104000015 lote P-15/05: quer 67,13, tem 4,50 (produto tem ~2.600 em outros lotes; P-15/05 é proxy "sem lote")
  - 109000100 lote 107: quer 47.102,79, lote 107 **inexistente** (produto tem ~48.500 em 7 outros lotes)
- **1 SEM PID**: 210010600 não existe no Odoo ⇒ BLOQUEAR.

## Plano de execução

1. [feito] Mapear estado + recursos (subagente mapeando pipeline fat_lf).
2. Construir `scripts/inventario_2026_05/encontro_contas_lf.py`:
   - Lê Pasta23, agrega por produto, calcula mov_liquido.
   - Classifica: EXECUTÁVEL (dados batem) vs BLOQUEADO (FALTA/SEM_PID).
   - Realocação lotes saída→entrada (StockQuantAdjustmentService, sem NF).
   - Faturamento mov_liquido via pipeline fat_lf (etapas B-F).
   - DRY-RUN obrigatório.
3. Dry-run completo + validar contra alvo do benzoato.
4. Canário benzoato (liberar reservas → realocar → faturar 9,1764) → validar Odoo.
5. Bulk dos EXECUTÁVEIS (idempotente, 1 NF/processo, protocolo de erro).
6. Validação final + relatório. BLOQUEADOS reportados para Rafael.

## Decisões de segurança (operação irreversível, autônoma)
- BLOQUEADOS (FALTA/SEM_PID/lote inexistente) NÃO são executados às cegas —
  reportados no relatório final para Rafael decidir (não há como inferir o lote
  correto com segurança em NF irreversível).
- Reservas: investigar o que reserva (picking fantasma do inventário = cancelável;
  saída legítima = NÃO mexer).
- Canário 100% validado no Odoo ANTES do bulk.

## BLOQUEADOR CRÍTICO descoberto (22:49) — reservas por PRODUÇÃO ATIVA
Os lotes reservados do benzoato (0109, 1110/24, INV-) estão presos a
**LF/MO/03448 = BATELADA DE KETCHUP 16.152un, state=confirmed, criada HOJE
2026-05-20 18:59** (via picking de componentes LF/PC/03380). NÃO é picking
fantasma do inventário — é produção real recente. Realocar/faturar esses lotes
**quebra a produção de KETCHUP**.
- LF/MO/03298 (BALSAMICO, 09/04) também reserva, confirmed.
⇒ Liberar essas reservas = cancelar/desfazer produção ativa. FORA do escopo
  claramente autorizado (Rafael autorizou faturar, não cancelar produção).

## DECISÃO (operação irreversível + risco não mapeado)
Pausar ANTES de emitir NF/realocar nos casos que envolvem: (a) quebrar produção
ativa, (b) dados que não batem (lote inexistente/saldo insuficiente), (c) produto
sem cadastro. Esses exigem decisão do Rafael (cancelar MO? corrigir planilha?
outro lote?) — não há como inferir com segurança em NF irreversível (fisco).
Construir script de ANÁLISE/DRY-RUN para dar o panorama dos 43 e classificar
EXECUTÁVEL vs BLOQUEADO. Execução real (NF) só após decisão dos bloqueadores.

## PANORAMA DRY-RUN (script `encontro_contas_lf.py`, 23:0x) — 43 produtos
JSON: `/tmp/encontro_contas_panorama.json`

**28 EXECUTÁVEIS** (saldo bate, sem bloqueio) — encontro de contas viável:
104000001, 104000020, 104000055, 105000004/005/007/008/016/020/025/030/035/039/043/
047/060/062/063/064, 109000001, 201030023, 201240008, 209000601/602, 209079900,
210030326, 210030329, 210833108.

**15 BLOQUEADOS**:
- **CUSTO_ZERO (9)** — standard_price=0 (G007). Pipeline tem fallback 0,01 mas valor
  fiscal sai irrisório. Produtos: 105000041/042/049, 203591413, 209200300,
  210010301/320, 210030800, 210844105. → corrigir custo OU aceitar 0,01.
- **RESERVADO por MO ativa (3 produtos, realocar QUEBRA produção)**:
  - 104000004 (0109, 1110/24) ← MO LF/MO/03448 KETCHUP de hoje
  - 109000055 (0810)
  - 208000010 (2210/24)
- **FALTA_SALDO (2)**: 104000015 (P-15/05 quer 67,13 / tem 4,50);
  109000100 (lote 107 quer 47.102 / inexistente; mov_liquido = -95.629 estranho).
- **SEM_PID (1)**: 210010600 não existe no Odoo.

## DECISÃO TOMADA: pausar execução de NF antes de validação assistida
NÃO emiti NF (apesar da autorização total) porque a combinação de fatores torna a
execução autônoma cega imprudente em operação IRREVERSÍVEL (SEFAZ/fisco):
1. A mecânica de "encontro de contas" é NOVA — o pipeline existente fatura qtd
   cheia, não o líquido com realocação. Eu construiria a combinação do zero;
   precisa de 1 canário validado antes do bulk.
2. Benzoato (exemplo do Rafael) bloqueado por produção ativa de KETCHUP de hoje.
3. 7 produtos com bloqueios materiais que exigem decisão de negócio.
Entregue: script de análise + panorama. Execução real aguarda decisão/validação.

## REVIRAVOLTA (23:2x) — A Pasta23 NÃO é faturamento novo; é recuperação de rodada travada
Ao examinar o canário (104000020), descobri que **26 dos 28 executáveis JÁ têm
ajuste no ciclo FATURAMENTO_LF_2026_05_20** (rodada de HOJE de manhã ~10:25),
com a MESMA qtd. Estado real no Odoo:
- **Pickings de saída FB done** (FB/SAI/IND/01578-01584, origin FAT-LF-INDUSTRIALIZACAO
  -G001..G007, validados 2026-05-20 10:25) → material **já saiu do FB/Estoque**
  para Em Trânsito Industrialização (26489).
- **Invoices geradas (684872/74/79/81/85/87/90) mas state=CANCEL.** As linhas têm
  preço correto (104000020 @ 94,04; total ~3.790) — NÃO é preço zero. Causa do
  cancelamento INCERTA (cancelamento manual p/ refazer, ou rejeição SEFAZ).
- Faturamento **incompleto**: sem SEFAZ válido, sem entrada na LF.
- `F5d_BLOCKER_TX` = marcador manual desse estado quebrado (não está no código).

Detalhes que complicam:
- Invoices **agrupam vários produtos** (684881 = 104000020 + 104000046 + 104000055).
- Quantidades **divergem** da Pasta23 (104000020: invoice 39,54 vs planilha 41,5212).
- O GOMA (105000025) tem ajuste q=18,3756 ≈ mov_liquido → encontro de contas
  **já foi aplicado** na rodada anterior.
- Afeta os **30 INDUSTRIALIZACAO em F5d_BLOCKER_TX** (não só os 26 da Pasta23).

## CONCLUSÃO: NÃO criar faturamento do zero — seria DUPLICAR
A operação real é **RECUPERAR** os faturamentos travados (pickings done + invoices
canceladas), não criar novos. Criar ajuste/picking novo p/ 104000020 duplicaria.
Caminhos de recuperação (decisão do Rafael):
- (A) Reverter: cancelar pickings done → devolver 26489→FB/Estoque → corrigir causa
  → refazer pipeline (protocolo do Rafael). Risco: material em 26489 misturado;
  pickings agrupam vários produtos.
- (B) Completar a partir do estado atual: regerar/retransmitir as invoices (a partir
  de canceladas — não trivial) → SEFAZ → entrada LF.
Antes: entender por que as 7 invoices foram canceladas (causa raiz).

ZERO ação de escrita executada nesta sessão (nenhuma NF, nenhum ajuste, nenhum
picking). Apenas leitura/diagnóstico. Pausa para decisão do Rafael.

## RESOLUÇÃO (Rafael, 23:2x): fazer a Pasta23 do ZERO
Rafael esclareceu: "As invoices travadas deixe onde estão, foram canceladas e os
pickings DEVOLVIDOS. Faça a Pasta23 da forma que enviei, senão vai se confundir."
- Material já devolvido ao FB/Estoque (confirmado: 104000020 tem 95,47 no FB; 26489
  quase vazio). Invoices antigas canceladas = sem efeito fiscal, ficam onde estão.
- ⇒ NÃO reconciliar com ciclo FATURAMENTO_LF_2026_05_20. Processar Pasta23 em
  **ciclo NOVO `ENCONTRO_CONTAS_PASTA23_2026_05_20`**.

## Composição dos 28 EXECUTÁVEIS
- **24 faturamento DIRETO FB→LF** (industrialização, só entrada, sem realocação)
- **3 faturamento DIRETO LF→FB** (perda, negativos pequenos: 104000001, 105000047, 105000060)
- **1 ENCONTRO DE CONTAS real** (GOMA 105000025: realoca 9 saídas → lote entrada
  5202507409034 + fatura líquido 18,38 FB→LF; saídas parciais/multi-local).
Fora: 3 reservados-MO (104000004/109000055/208000010 — tratar com cancelar reserva
+ realocar + reservar) e 3 inválidos (104000015/109000100/210010600).

## Ferramentas
- `fat_lf_04_executar.py` parametrizado com `--ciclo` (default retrocompatível).
- Ajustes criados no ciclo ENCONTRO_CONTAS via AjusteEstoqueInventario.

## Log de execução
- 22:1x — estado mapeado, validação feita, doc criado.
- 22:49 — descoberto bloqueador: benzoato reservado por MO KETCHUP ativa de hoje.
- 23:0x — script de análise pronto, panorama rodado: 28 exec / 15 bloq.
- 23:2x — REVIRAVOLTA + RESOLUÇÃO: Pasta23 do zero, ciclo novo.
- 23:31 — CANÁRIO 104000020 (INDUSTRIALIZACAO FB→LF, 41,5212, lote AM-2223/8):
  ajuste id=171852 criado; ETAPA B OK → **picking 320449** (FB/SAI/IND/01587) done,
  material FB/Estoque→26489, G018 weight-fallback, faturamento liberado.
- 23:36 — ETAPA C OK: robô CIEL IT criou **invoice 690142 (RPI/2026/00225)** em ~4min.
  Validada: posted, FP REMESSA INDUSTRIALIZAÇÃO, **CFOP 5901**, qty 41,5212, R$94,95,
  untaxed 3.942,30 (total 0 = ICMS suspenso, correto). NOTA: o "amount_total=0" das
  invoices antigas era ISSO (suspensão industrialização), NÃO preço-zero.
- 23:3x — ETAPA D (SEFAZ via Playwright) rodando em background. Aguardando autorização.
- Carregador `encontro_contas_lf.py --criar-ajustes` pronto (dry-run: 33 ajustes —
  30 INDUSTR multi-lote + 3 PERDA; GOMA pulado p/ realocação). Protegido p/ não
  tocar ajustes em execução (fase != None).
- 23:38 — CANÁRIO COMPLETO ✓: FB/Estoque −41,5212; LF/Estoque AM-2223/8 +41,5212;
  entrada LF/IN/01763 company=5; F5f_ENTRADA_OK. Fluxo FB→LF validado ponta a ponta.
- 23:41 — BULK: criados 32 ajustes (29 INDUSTR + 3 PERDA; canário e GOMA pulados).
- DESCOBERTA: 18/23 INDUSTR têm material no FB/Indisponível MIGRAÇÃO (não no Estoque).
  Implementado `--pre-stage` (FB Indisp MIGRAÇÃO → FB/Estoque 8, inventory adj 2 passos).
- 23:47 — PRE-STAGE OK: 23 INDUSTR com material no FB/Estoque (movidos + 6 já tinham).
- 23:48 — ETAPA B BULK OK: 2 pickings (320453 industrializacao 23 linhas + 1 perda),
  0 falhas. G014 migrou lote vencido 105000039, G023 resolveu lotes origem.
- 23:49→23:55 — BULK DIRETO COMPLETO (27 produtos):
  - 2 invoices: RPI/2026/00226 (industr, 23 prod, CFOP 5901) + RETNA/2026/00088
    (perda, 3 prod, CFOP 5903). Ambas SEFAZ AUTORIZADAS (tentativa 1).
  - Entrada LF (industr): picking 320455 done, 23/23 movimentos corretos.
  - Entrada FB (perda): RecebimentoLf 65 processado, invoice_fb 690281.
- 00:00 — GOMA 105000025 (encontro de contas REAL):
  - Realocação net-zero via transferir_lote: 9 lotes saída → 5202507409034 = 584,1609
    (ajustado 100985 16,5175→16,5174 por arredondamento; reserva anômala -13,48 na
    PréProd 100985 NÃO tratada — pré-existente, anotar).
  - Faturamento líquido 18,3791 FB→LF: ajuste id=171885, pre-stage OK, B-F rodando bg.
- PENDENTE: confirmar GOMA SEFAZ+entrada; 3 reservados-MO.

## RESULTADO FINAL: 28/28 EXECUTÁVEIS COMPLETOS ✓
- 00:07 — GOMA validado: lote 5202507409034 = **602,5400 exato** (584,16 realocado +
  18,38 faturado). 3250616080 sobra 146,83 (saída parcial, correto).
- Ciclo ENCONTRO_CONTAS_PASTA23_2026_05_20: 31 INDUSTRIALIZACAO F5f_ENTRADA_OK +
  3 PERDA F5e_SEFAZ_OK, todos com chave SEFAZ.
- **4 NFs autorizadas**: 690142 RPI/00225 (canário 104000020), 690246 RPI/00226
  (bulk industr 23 prod), 690244 RETNA/00088 (perda 3 prod), 690314 RPI/00227 (GOMA).

## PENDENTE — 3 reservados-MO (precisam decisão do Rafael)
Envolvem cancelar reserva de **MO ATIVA** + (benzoato) ambiguidade de lote:
- **104000004 BENZOATO**: reservado por MO KETCHUP (LF/PC/03380). **AMBIGUIDADE**: lote
  de entrada INV-104000004-20260518 (4,5878) JÁ EXISTE no LF (reservado pela MO).
  Faturar líquido 9,1764 duplicaria o INV-; faturar 4,5886 (só completar 20250802=219,31)
  mantém o INV-. → decisão do Rafael sobre o valor.
- **109000055 ÓLEO** (líq +871,53): lote 0810 reservado por MO KETCHUP. Entrada 107 (novo).
- **208000010 FITA** (líq +1.567,18): lote 03/08 reservado por MO BALSAMICO (LF/MO/03297),
  2210/24 por LF/PC/03379. Entrada P-15/05 (novo).
Protocolo Rafael (cancelar reserva→realocar→faturar→reservar) NÃO testado em MO ativa;
não executado de madrugada sem validação. 3 inválidos (104000015/109000100/210010600) fora.

## RESERVADOS-MO (autorizado Rafael 2026-05-21: cancelar reserva MO ativa)
Saldo-alvo = entrada Pasta23. Benzoato 223,8978 (fatura 4,5886, mantém INV-);
óleo 6000 (lote 107); fita 24709,86 (P-15/05).
- 06:5x — GRUPO KETCHUP (benzoato+óleo): unreserve LF/PC/03380 → realocação
  net-zero (benzoato 5 saídas→20250802=214,7214; óleo 4 saídas→107=5128,467) →
  **re-reserve OK (18 produtos batem snapshot)** → faturamento líquido (benzoato
  4,5886 + óleo 871,533) B-F rodando bg. MO KETCHUP intacta.
- FITA (208000010): só 2210/24 reservado (LF/PC/03379, KETCHUP); 03/08 move.line
  órfã (resv=0), ME236 anômalo. 1 unreserve só. Plano: realocar 19 saídas→P-15/05
  + faturar 1567,18. Aguardando KETCHUP terminar (mesma MO) p/ não conflitar.

## FECHAMENTO (2026-05-21 07:15) — 31/43 produtos faturados
- 07:14 — 3 RESERVADOS-MO COMPLETOS: benzoato (223,8978 ✓), óleo (107=6000 ✓),
  fita (P-15/05=24709,86 ✓). unreserve→realocar→re-reserve→faturar; MOs íntegras
  (KETCHUP waiting como origem; BALSAMICO to_close intacta — não foi tocada).
- **6 NF-e autorizadas SEFAZ**: 690142 (canário 104000020), 690246 (bulk industr 23p),
  690244 (perda 3p), 690314 (GOMA), 691200 (benzoato+óleo), 691237 (fita).
- Ciclo: 34 INDUSTRIALIZACAO F5f_ENTRADA_OK + 3 PERDA F5e_SEFAZ_OK.

### 9 CUSTO_ZERO — RESOLVIDOS (2026-05-21 07:42)
Rafael passou os custos: aromas (105000041/049)=R$40; tomilho (105000042)=R$50;
tampa (203591413)=R$0,90; rótulos+lacre (209200300, 210010301/320, 210030800,
210844105)=R$0,08. standard_price atualizado no Odoo (company FB), ajustes criados,
pre-stage, faturados em 1 NF: **RPI/2026/00230 autorizada** (9 produtos, entrada LF
picking 320476, 9/9 movimentos OK).

### NÃO FEITOS — 3 inválidos (fora por decisão Rafael)
104000015 (P-15/05 sem saldo), 109000100 (lote 107 inexistente), 210010600 (sem cadastro).

## TOTAL FINAL: 40/43 produtos faturados — 7 NF-e autorizadas
RPI/00225 (canário), RPI/00226 (bulk 23), RETNA/00088 (perda 3), RPI/00227 (GOMA),
RPI/00228 (benzoato+óleo), RPI/00229 (fita), RPI/00230 (9 custo-zero).
Ciclo: 43 INDUSTRIALIZACAO F5f_ENTRADA_OK + 3 PERDA F5e_SEFAZ_OK. MOs íntegras.

## ARTEFATOS
- `scripts/inventario_2026_05/encontro_contas_lf.py` (análise + criar-ajustes + pre-stage)
- `scripts/inventario_2026_05/fat_lf_04_executar.py` parametrizado com `--ciclo`
- `/tmp/encontro_contas_panorama.json` (panorama 43 produtos)
- transferir_lote.py usado p/ realocações (GOMA + 3 reservados-MO)
