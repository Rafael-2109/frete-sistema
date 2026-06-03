# DECISÕES — Industrialização FB↔LF

> Registro de decisões aprovadas. Imutável (não editar decisões antigas; criar nova versão).

---

## D01 — Caminho C: 5902 cobre consumo + perda; 5903 cobre apenas sobra
**Data**: 2026-05-28
**Aprovador**: Fiscal + Contábil
**Decisão**: a NF de retorno da LF para FB usará:
- CFOP 5124 para o Produto Acabado (PA) com valor agregado da LF
- CFOP 5902 para os componentes consumidos incluindo a perda real (sem destacar perda)
- CFOP 5903 apenas para sobras íntegras não aplicadas no processo
**Justificativa**: padrão fiscal mais limpo, perda fica embutida no custo do PA, sem necessidade de visibilidade gerencial separada de perda.
**Trade-off**: perda não aparece como linha separada na DRE; visibilidade gerencial fica reduzida.

---

## D02 — Insumos: apenas água é da LF
**Data**: 2026-05-28
**Aprovador**: PCP LF + Operação
**Decisão**: dos 17 componentes da BoM do PA 4870112, apenas o item 104000017 ÁGUA (9,207 L/cx) é insumo próprio LF. Os outros 16 são fornecidos pela FB via remessa de industrialização.

---

## D03 — Valor agregado LF = R$ 35,00/cx
**Data**: 2026-05-28
**Aprovador**: Comercial + Contábil
**Decisão**: o serviço de industrialização cobrado pela LF para FB é R$ 35,00 por caixa de 4870112. Cadastrado em `product.supplierinfo` id 6319.

---

## D04 — CIEL IT mapeia CFOP por linha
**Data**: 2026-05-28
**Aprovador**: TI
**Decisão**: o CIEL IT consegue ler o CFOP por linha do XML da NF de retorno e mapear cada linha para o picking_type apropriado.

---

## D05 — Opção B strict (bloquear consumo > remessa)
**Data**: 2026-05-28
**Aprovador**: Operação
**Decisão**: a BoM (3695 cmp=LF para o piloto) usa `consumption='strict'`. Se operador tentar apontar qty_done > qty_planejada × qty_produced, sistema bloqueia.
**Para casos de perda real**: protocolo PO complementar (D14).

---

## D06 — BoMs subcontract dos outros 29 PAs sem revisão prévia
**Data**: 2026-05-28
**Aprovador**: Operação
**Decisão**: confiar nas 30 BoMs subcontract existentes (ids 14807..14837). Não revisar antes do rollout.

---

## D07 — Escopo apenas FB↔LF
**Data**: 2026-05-28
**Aprovador**: Operação
**Decisão**: SC e CD ficam fora deste projeto. Apenas o fluxo FB→LF→FB é coberto.

---

## D08 — 1 PO piloto de 10 cx
**Data**: 2026-05-28
**Aprovador**: Operação
**Decisão**: piloto único de 10 cx do 4870112. Total estimado < R$ 500. Após validação, virada gradual.

---

## D09 — Virada gradual após validação Fiscal + Contábil
**Data**: 2026-05-28
**Aprovador**: Direção
**Decisão**: após piloto aprovado, virar 1 PA por dia útil, máximo 5 por semana. Cada virada exige PO de teste + validação. Pause se 2 falhas em 5 tentativas.

---

## D10 — Opção 2 (inter-company / MO em cmp=LF)
**Data**: 2026-05-28
**Aprovador**: Operação
**Decisão**: usar módulo `sale_purchase_inter_company_rules` (já instalado). PO FB para LF dispara SO em cmp=LF, que dispara MO em cmp=LF via BoM 3695 (normal) + rota MTO. PCP LF aponta MO no sistema da LF normalmente.
**Justificativa**:
- LF tem rastreabilidade completa (visão própria de MOs em andamento)
- Bloco K SPED LF nativo
- Apontamento no sistema (não só físico/NF)
- Módulos já instalados (sem desenvolvimento)
**Trade-off**:
- BoM subcontract 14833 fica sem uso (será desativada após piloto)
- Setup mais complexo (configurar inter-company + journals + rotas)
- Inter-company nunca foi testado em produção (risco a validar em T13)

---

## D11 — Criar 2 estoques novos (não renomear 30713)
**Data**: 2026-05-28
**Aprovador**: Operação
**Decisão**: criar `LF/Materiais de Terceiros` e `LF/PA de Terceiros` em cmp=LF, em vez de renomear ou reutilizar location 30713 (Locais Fisicos/Local de subcontratação cmp=FB).
**Implicação**: alterar `res.partner.property_stock_subcontractor` da LF (35) para apontar para a nova LF/Materiais de Terceiros.
**Justificativa**: visibilidade gerencial direta para PCP LF (filtro por cmp=5), separação clara entre estoque de matérias-primas em poder da LF e PA produzido aguardando devolução.

---

## D12 — Criar regras nas rotas 162 e 166
**Data**: 2026-05-28
**Aprovador**: Operação
**Decisão**: criar `stock.rule` específicas nas rotas 162 (FB Reposição para subcontratação) e 166 (LF Reposição para subcontratação), em vez de confiar exclusivamente nos automatismos do módulo.
**Atenção**: avaliar em T08/T09 se o subcontracting + inter-company gera as regras automaticamente. Se sim, marcar tasks como ⛔ skipped.

---

## D13 — BoM 14833 confirmada como ativa (mas não usada na Opção 2)
**Data**: 2026-05-28
**Verificado em Odoo**: sequence=25, type=subcontract, subcontractor=[35 LF], active=True, cmp=FB
**Status na Opção 2**: NÃO USADA — a MO em cmp=LF usa BoM 3695 (normal, sequence=61, cmp=LF).
**Decisão futura**: desativar 14833 após piloto bem-sucedido (task T33).

---

## D14 — Remessa complementar via PO complementar (não avulsa)
**Data**: 2026-05-28
**Aprovador**: Operação
**Decisão**: em caso de perda > remessa (Opção B strict trava apontamento), Compras FB cria PO complementar específico para os componentes faltantes. SLA <2h em horário comercial. Protocolo de 9 passos descrito em `ROADMAP_TASKS.md#T20`.
**Métrica de saúde**: se mais de 10% dos POs originais precisarem complementar por 2 meses consecutivos, revisar BoM ou ajustar coeficiente de remessa-com-folga.

---

## D15 — PCP LF revisa BoMs no rollout
**Data**: 2026-05-28
**Aprovador**: Operação
**Decisão**: cada PA virado no rollout passa por revisão do PCP LF para identificar componentes FB vs insumos próprios LF. Não revisar antecipadamente todas as 29 BoMs.

---

## D16 — T08 caminho A (pular criação manual de stock.rule cross-company)
**Data**: 2026-05-28
**Aprovador**: Rafael
**Decisão**: ao invés de criar manualmente a stock.rule da rota 162 (FB Reposição p/ subcontratação) ligando FB/Estoque → LF/Materiais de Terceiros (31092), T08 fica ⛔ skipped. Em T13 (teste end-to-end com produto qualquer), observar se o módulo `mrp_subcontracting + sale_purchase_inter_company_rules` cria as stock.rules necessárias automaticamente.
**Contexto**: Odoo padrão bloqueou create manual com `_check_company` ("Empresas incompatíveis nos registros" — cmp=FB rule + cmp=LF location_dest). Ver `testes/T08-falha-2026-05-28.md`.
**Plano de contingência**: se T13 mostrar que o módulo NÃO cria automaticamente E que falta a regra, reabrir T08 com caminhos B/C/D/E:
- B) stock.rule global (`company_id=False`) — perde semântica "regra da FB"
- C) usar location 30713 (global) — reverter D11
- D) refazer T02 com location global — perde filtro cmp=LF
- E) customização Python — fora de escopo
**Trade-off**: nenhum custo até T13. Se T13 confirma criação automática, D11 sobrevive intacta. Se não, escolhe-se caminho B/C/D/E com Rafael nesse momento.

---

## D17 — Estrutura BoM real do piloto: BATELADA é subprocesso interno LF
**Data**: 2026-05-28 (revisada 2026-05-29 após validação empírica da NF 725676)
**Aprovador**: Rafael
**Decisão**: A BoM real do MOLHO SHOYU PET 12X1,01L (BoM 3695, LF normal, ativa) é hierárquica:
- BoM 3695 (PA) tem 8 linhas: **1 semi-acabado BATELADA DE SHOYU + 7 embalagens**
- BoM 3646 (filha BATELADA) tem 10 linhas: **8 químicos + 1 ÁGUA + 1 MP MOLHO SHOYU TRADICIONAL** (105000022, sem X)

**A BATELADA DE SHOYU (`default_code=3800018`, id=29986, categ=SEMI ACABADOS / MOLHOS / BATELADAS) é apenas um SUBPROCESSO INTERNO da LF**: produzida durante a MO LF a partir dos componentes que a FB enviou (8 químicos + 1 MP + ÁGUA própria LF), consumida na mesma MO LF para virar o PA esperado pela FB. A BATELADA NÃO cruza fronteira FB↔LF — não aparece em NFs entre as duas companies.

**Escopo total da remessa FB→LF (CFOP 5901, NF saída FB no T22)** — CORRIGIDO via NF real 725676:
**16 componentes** = 7 embalagens (nível PA) + 8 químicos + 1 MP shoyu_tradicional (nível BATELADA), excluindo somente ÁGUA (104000017, único insumo próprio LF — D02 ratificada).

> Correção 2026-05-29: a versão original desta decisão dizia "17 componentes" (7 emb + 9 quim + 1 MP). Validação empírica da NF 725676 confirmou **16 linhas** (7 + 8 + 1). A divergência veio de contagem errada do bloco de químicos da BoM 3646 (que tem 10 linhas total = 8 quim + 1 água + 1 MP — não 9 quim + 1 MP). Lista exata dos 8 químicos: BENZOATO, CORANTE, SAL, SORBATO, ACIDO CITRICO, ANTIESPUMANTE, ACUCAR, AROMA.

**Escopo total da NF retorno LF→FB (T25)**:
- 1 linha CFOP 5124 = PA produzido (com R$ 35,00/cx valor agregado — D03)
- 16 linhas CFOP 5902 = componentes consumidos (incluindo perda real, conforme caminho C — D01)
- 0..N linhas CFOP 5903 = sobras íntegras

**Implicações**:
- BATELADA NÃO aparece em nenhuma NF (interna à MO LF)
- BoM 14833 (subcontract antiga, cmp=FB, com 17 linhas planas incluindo SHOYU TRADICIONAL na seq=4) reflete o mesmo escopo total da remessa, só sem hierarquia. Confirma a equivalência conceitual: a remessa FB→LF é IDÊNTICA nos dois modelos (subcontract antigo vs Opção 2 inter-company); muda apenas onde a MO é executada e o caminho fiscal/contábil.
- O consumption=strict (D05) aplicado à BoM 3695 (T10 ✅) também precisará ser replicado na BoM 3646 (filha BATELADA) para garantir bloqueio em ambos os níveis. **NOVA TASK derivada**: T10b — alterar BoM 3646 consumption='strict'.

**Trade-off**:
- A NF tem 17 linhas (não 8). Complexidade fiscal moderada.
- BoM hierárquica = LF Bloco K SPED precisa registrar 2 níveis de MO. Não é problema (Odoo gera).

**Resolve**: A01 (linha 7 BoM 14833 = X105000022) ⛔ resolved — produto arquivado, BoM 14833 será desativada em T33, irrelevante para piloto.

---

## D18 — Antecipar T33 (desativar BoM 14833) + ativar rota 162 antes de T13
**Data**: 2026-05-28
**Aprovador**: Rafael
**Decisão**: executar ANTES de T13:
- Reativar `stock.route` id=162 (FB: Reposição para subcontratação) — estava `active=False`. WH FB (id=1) tem `subcontracting_route=[162]` referenciada; ativar permite que o módulo subcontract use a rota caso decida criar stock.rules automaticamente.
- Desativar `mrp.bom` id=14833 (subcontract antiga FB com subcontractors=[35 LF]) — antecipa a T33 do pós-piloto.
**Motivação**:
- BoMs ativas conflitantes (14833 subcontract FB vs 3695 normal LF) podem fazer Odoo escolher o caminho errado em T13. Risco real de a Opção 2 ser anulada silenciosamente pelo módulo `mrp_subcontracting`.
- Rota 162 inativa impedia que o caminho subcontract+inter-company (caso necessário) tivesse rotas para criar stock.rules.
**Pré-validação (CHK1)**: 0 MOs ativas usando 14833, 0 MOs done recentes, 0 pickings ativos pt=74 → desativação 100% segura.
**Resultado**:
- route 162 active: False → True
- bom 14833 active: True → False
- BoMs ativas do produto piloto: agora apenas 3695 + 3646 (hierarquia Opção 2 limpa)
**Trade-off**: T33 original (pós-piloto) é convertida em ✅ done antecipada. Caso o piloto T13 falhe e seja necessário reverter para subcontract, basta reativar 14833 (rollback documentado em `testes/T33-antecipada-resultado.md`).
**Resolve**: ambiguidade na escolha de BoM em T13; pré-requisito implícito do caminho A do T08 (D16).

---

## D19 — Fusão T13 + T21: piloto direto com 4870112
**Data**: 2026-05-29
**Aprovador**: Rafael
**Decisão**: T13 (originalmente "Teste end-to-end com PRODUTO QUALQUER" para validar config antes de tocar no produto piloto real) e T21 (originalmente "Criar PO piloto FB→LF com 10 cx do 4870112") são **fundidos em um único teste E2E** com o produto piloto real 4870112 desde o início. O piloto vira mais ousado mas pula a etapa de "produto qualquer".
**Motivação**:
- D17 + D18 + diagnóstico exaustivo (`testes/T13-prep-cadastros.md`) confirmaram que toda a infraestrutura S0 está consistente para o produto piloto real.
- Único bloqueio remanescente eram 3 componentes em FB/Estoque 100% reservados; resolvido por ajuste de inventário positivo nesta sessão (ver `testes/T-AJUSTE-ESTOQUE-resultado.md`).
- Testar com produto qualquer adicionaria 1 ciclo extra (2-3 dias) sem reduzir risco material — a configuração já está limpa.
**Trade-off**:
- Maior risco material (PA real, R$ 350 piloto vs R$ trivial de produto qualquer)
- Mas: ciclo único, validação direta da configuração que importa, sem precisar repetir T13→T21
**Resolve**: A03 (janela do piloto) — começa imediatamente. Próximo passo: Rafael cria o PO FB→LF.
**Implicações no roadmap**:
- T13 ⛔ skipped (substituído por T13/T21 fundido com produto piloto)
- T21 deixa de ser etapa independente; o que era T22-T28 fica como o restante do piloto.

---

## D21 — Caminho B Skill 7 para escrituração DFe entrada LF (em vez de aguardar SEFAZ propagar)
**Data**: 2026-05-29
**Aprovador**: Rafael
**Decisão**: ao invés de aguardar o DFe da NF saída SEFAZ-autorizada (chave 35260...6765) propagar pela caixa-postal SEFAZ da LF e ser processado pelo CIEL IT da LF (caminho A — `T23` do roadmap original — pode levar minutos a horas), executar o **caminho B da Skill 7 ABRANGENTE v19+**: criar o DFe diretamente em LF a partir do XML autorizado da NF saída (`account.move.l10n_br_xml_aut_nfe` da invoice 725676).
**Sequência caminho B (3 átomos Skill 7)**:
1. `criar_dfe_a_partir_do_invoice_saida(invoice_id=725676, company_destino=5)` — cria DFe + fix B-V23-1 v23.5+ (alinha `dfe.line.company_id` LF)
2. `escriturar_dfe(dfe_id, l10n_br_tipo_pedido='serv-industrializacao')` — popula campos de entrada
3. `gerar_po_from_dfe(dfe_id)` — dispara `action_gerar_po_dfe` do robô CIEL IT
**Motivação**: ganhar tempo. NF já está autorizada SEFAZ; aguardar canal SEFAZ é puramente passivo.
**Trade-off descoberto**: passo 3 cria a PO na company do USER que executa o XML-RPC (Rafael uid=42 → company principal=FB), em vez de na company do DFe (LF). Ver D22 + A08 (novo).
**Resolve parcialmente**: T23 do roadmap fica formalmente concluído via caminho B; o passo final (PO em LF correta) bloqueia em A08.

---

## D22 — Manter NF 725676 autorizada SEFAZ apesar do gap na PO LF
**Data**: 2026-05-29
**Aprovador**: Rafael
**Decisão**: a NF saída 725676 RPI/2026/00242 (chave SEFAZ 35260561724241000178550010000945901007256765) **NÃO será cancelada** apesar do gap descoberto na geração da PO LF (D21 caminho B passo 3). Cancelamento SEFAZ exige processo formal 24h sem uso + declaração. PO 42676 LF (criada em company errada) é cancelada (state=cancel), DFe 43689 fica com `purchase_id=False` pronto para nova tentativa.
**Motivação**: os componentes (16 itens) já saíram fisicamente da FB para "Em Trânsito Industrialização" via picking saída validado. NF SEFAZ-OK é a base fiscal dessa movimentação. Reverter seria pior do que retomar.
**Próximo passo**: resolver A08 (como gerar PO LF com company_id=5 correto via `action_gerar_po_dfe`) em próxima sessão.

---

## D23 — A05 corrigida: PA da MO LF cai em LF/PA de Terceiros (31093), não LF/Estoque
**Data**: 2026-05-29
**Aprovador**: Rafael
**Decisão**: D20 fechou A05 com `LF/Estoque` por interpretação errada da rule 135 do Odoo. Rafael relembrou que **a spec original (D11 + T03) sempre intencionou o PA cair em `LF/PA de Terceiros (31093)`** para distinguir PA fabricado para FB de PA de revenda própria LF. **MO LF 20154 foi criada com `location_dest_id=31093` forçado** nesta sessão.
**Supersede**: D20 (parcialmente — caminho concorrente continua válido; só o destino foi corrigido).
**Implicação no T07**: pt=98 LF/SAI/IND/RET tem `src=31093` exatamente para essa saída de PA na NF retorno.
**Resolve**: A05 (definitivo).

---

## D20 — Caminho concorrente: MO em LF gerada manualmente (alinhada ao histórico) — *parcialmente superseded por D23*
**Data**: 2026-05-29
**Aprovador**: Rafael
**Status posterior**: parcialmente superseded por D23 (2026-05-29 — destino do PA é LF/PA de Terceiros 31093, não LF/Estoque). Caminho concorrente em si (MO LF manual) continua válido; apenas a parte do destino do PA foi corrigida.
**Decisão**: Não automatizar a criação da MO em LF via MTO chain. Manter o pattern histórico onde PCP LF cria MO manualmente em LF para atender a demanda gerada pela SO inter-company (cmp=5, partner=FB id=1).
**Contexto descoberto**:
- O produto 27834 tem `route_ids=[134 Fabricar LF, 1 MTO global]`
- Rota MTO global (1) tem 46 stock.rules **todas em cmp=FB** (zero em cmp=LF) → não dispara MTO em LF
- A rota que faria MTO funcionar em LF é a **132 "Reabastecer no Pedido (PSE) - LF"** (rules 20/35/36, procure=`mts_else_mto`)
- 0 dos 19 PAs LF amostrados (com BoM normal ativa) têm rota 132. Histórico confirma: MOs do 27834 são criadas manualmente (todas com `origin=False`, `move_dest_ids=[]`, create_uid=Edilane uid=78)
- T11 anterior escolheu a rota errada (1 global em vez de 132 LF local) — pequeno bug do roadmap original, não bloqueante para o piloto com caminho concorrente

**Trade-off**:
- A SO LF 73424 confirma; picking LF/OUT/00020 fica em state=confirmed aguardando saldo em LF/Estoque (que é 0)
- PCP LF cria MO manualmente apontando para o BoM 3695 → MO produz 10 cx → entra em LF/Estoque (via rule 135) → picking OUT reserva e fica `assigned`
- A automação prometida pela D10 (Opção 2 inter-company auto-dispara MO) **fica desligada para PAs LF**. Para os outros 29 PAs no rollout (D34) o pattern será o mesmo: PCP LF cria MO manual.
- D10 não é violada — o **fluxo fiscal** (NF saída FB CFOP 5901 → NF retorno LF→FB CFOPs 5124+5902+5903 → DFe entra FB via pt=52) continua válido. Só o procurement chain interno fica manual.

**Plano de remediação futura (opcional)**: se desejar automatização completa para os 29 PAs do rollout, adicionar rota 132 (PSE LF) aos PAs. Mas como histórico mostra que PCP LF está acostumado com criação manual, não é prioritário.

**Resolve**: A05 (destino do PA na MO LF) — será LF/Estoque por padrão (rule 135 Fabricar → LF/Estoque). Não usar LF/PA de Terceiros (id=31093, criada em T03) por enquanto. Reavaliar pós-piloto.

**Próximo passo do piloto**: criar MO manualmente em LF. Quem cria: Claude via XML-RPC (mantém automação), ou Rafael/PCP LF via UI Odoo. Sub-task derivada: **T21b — Criar MO LF manualmente**.

---

## Histórico de versões deste arquivo

| Versão | Data | Mudança |
|---|---|---|
| 1.0 | 2026-05-28 | Decisões iniciais D01-D15 |
| 1.1 | 2026-05-28 | D16 (caminho A para T08) |
| 1.2 | 2026-05-28 | D17 (BATELADA = subprocesso interno LF, BoM hierárquica 3695→3646; resolve A01) |
| 1.3 | 2026-05-28 | D18 (antecipar T33 + ativar rota 162 antes de T13) |
| 1.4 | 2026-05-29 | D19 (fusão T13+T21 → piloto direto com 4870112; estoque ajustado) |
| 1.5 | 2026-05-29 | D20 (caminho concorrente: MO em LF manual; resolve A05 → LF/Estoque) |
| 1.6 | 2026-05-29 | D21+D22+D23 (caminho B Skill 7 + NF preservada SEFAZ + A05 corrigida 31093) |
