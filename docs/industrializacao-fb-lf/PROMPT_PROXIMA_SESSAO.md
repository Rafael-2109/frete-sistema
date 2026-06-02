# PROMPT — Próxima sessão (Industrialização FB↔LF)

> **Atualizado 2026-06-02 (fim da 6ª sessão — R-UNIF PROVADO: G5a CONVERGE com G4; decisão fiscal ÚNICA pendente).**
> Handoff = só o próximo passo + estado. Estado completo: `README.md`. Desenho/decisões (dona): `SOT_OPERACOES.md`. Mecanismo + IDs + evidências: `ACHADOS_TECNICOS.md §"ACHADO 2026-06-02 (sessão 6)"` (e §sessão 5) — ler o **TL;DR** lá.

## Como começar
Leia nesta ordem: **`README.md`** (índice+estado) → **este handoff** → **`ACHADOS_TECNICOS.md` TL;DR das sessões 5 E 6** (o que já foi PROVADO — não refazer). Desenho/decisões: **`SOT_OPERACOES.md`** (em conflito, ela vence). Execução config: `PROPOSTA_CONFIG_RETORNO.md`. Material da Contadora: `MATERIAL_CONTADORA_G4.md`. Procedimento+gotchas: `RUNBOOK_PILOTO_4870112.md`. Superseded → `HISTORICO/` (não seguir).

## Onde estamos (piloto 1 caixa, produto 4870112, lote PILOTO-3105)
- ✅ **Etapa 1** (Remessa FB→LF, NF `RPI/2026/00245` SEFAZ-OK) · ✅ **dreno físico** 26489→30720 · ✅ **Etapa 2** (Entrada LF Model B, ENTIN 737062) · ✅ **Etapa E** (MO 20252+20254, net-zero terceiros, PA em 31093).
- ✅ **Sessão 5 (READ-ONLY + 2 experimentos NF-teste postada/excluída, ZERO sujeira):** o mecanismo de fechamento do retorno foi **totalmente mapeado e os limites provados**. **Nada escrito no Odoo em definitivo.**

## A DESCOBERTA CENTRAL (provada — NÃO refazer)
**Uma NF mista (5124 serviço + 5902 insumos + 5903 sobra) NÃO baixa a 5902 contra a conta de compensação.** A contrapartida (CLIENTES/no_payment) é **uma linha por DOCUMENTO**, governada pelo `tipo_pedido` do **HEADER** — não por linha, não por operação, não por tipo de produto, não por múltiplos pickings. O `no_payment` só substitui o recebível quando a NF é **100%-simbólica** (sem serviço). Provado por 8 ângulos (`ACHADOS` TL;DR). ⇒ **A 5902 só baixa a PASSIVA num DOCUMENTO separado do serviço.**

**ESPELHO NA ENTRADA (PROVADO sessão 6 — R-UNIF):** o mesmo vale para a FB. Numa NF de entrada **mista** (1124 serviço + 1902 insumos), `no_payment=22800` no j1001 **NÃO baixa** a ATIVA — o `FORNECEDORES` do serviço absorve a 1902 (NF-teste postada/excluída: NET ATIVA=0). **G5a CONVERGE com o G4: a 1902 também precisa vir em documento separado.** Uma só decisão fiscal resolve os 2 lados. (`ACHADOS §"ACHADO 2026-06-02 (sessão 6)"`.)

## A DECISÃO QUE DESTRAVA TUDO (Rafael + Contadora)
**"5124+5902 têm que estar na MESMA NF" é exigência FISCAL (lei/SEFAZ) ou preferência OPERACIONAL?**
- **Operacional** → **Caminho (b): SEPARAR** a 5902 em documento próprio (NF dedicada ou picking_type/journal de retorno-insumos com `no_payment=26667`). **Nativo, sem código, já roda em PROD** (as `SARET` só-5902 baixam via no_payment). Resultado: 2 documentos.
- **Fiscal** → **Caminho V-B: 1 NF mista + lançamento de AJUSTE** (`account.move` entry) **na fonte** (desvio cirúrgico do robô só p/ `partner=LF`, criando a NF + o ajuste atomicamente). Mantém 1 NF fiscal; é remendo (precisa aval da Contadora pois mexe no recebível + idempotência/estorno/filtro no nosso `faturamento_service`; NÃO resolve AVCO/R1).
- ❌ **NÃO reabrir V-A** (button_draft+reclassificar+repost da NF): DESCARTADA — o `action_post` re-deriva o CLIENTES (reverte o ajuste) e repostar NF SEFAZ-autorizada diverge o razão do XML (estudo 4 lentes).

## PRÓXIMO PASSO
1. **Levar `MATERIAL_CONTADORA_G4.md` à Contadora** (pergunta 1: pode separar 5902 do 5124 em 2 documentos? + 4 perguntas anexas). A resposta elimina um dos 2 caminhos.
2. **Se SEPARAR for OK (caminho b):** desenhar/configurar o picking_type|journal de retorno-de-insumos (`tipo_pedido` próprio → `no_payment=26667`); validar no piloto. *(detalhe a confirmar: CFOP da 5902 = 5902, não 5949; ver `ACHADOS` R2b.)*
3. **Se exigir 1 NF (caminho V-B):** rodar o **estudo de design do desvio cirúrgico** (ponto de inserção, lançamento de ajuste exato validado pela Contadora, idempotência, estorno on-cancel, filtro no ETL) ANTES de codar.
4. **G5a — NÃO é mais independente; CONVERGE com o G4 (PROVADO sessão 6):** experimento (NF-teste mista de entrada postada/excluída) mostrou que `no_payment=22800` no j1001 **sozinho NÃO baixa** a ATIVA — o FORNECEDORES do serviço absorve a 1902. ⇒ a 1902 de entrada precisa vir em **documento separado** (mesma decisão fiscal e mesma solução do G4). O script `g5a_aplicar_no_payment_j1001.py` (no_payment no j1001) é **necessário mas insuficiente sozinho** — só funciona se a 1902 chegar à FB em NF separada. Experimento: `scripts/g5a_experimento_entrada_runif.py`. `ACHADOS §"ACHADO 2026-06-02 (sessão 6)"`.

## Regras invioláveis
- **dry-run + "go" FRESCO do Rafael em CADA escrita Odoo** (go DEPOIS da dry-run apresentada). NF SEFAZ só com go explícito. 1 comando por escrita.
- **NUNCA** `action_apply_inventory` cru → Skill 1. Ops LF: contexto `allowed_company_ids=[1,5]`.
- Experimentos Odoo: NF-teste em journal de teste, postar só se necessário, **SEMPRE limpar depois** (deletar NF + journal).

## IDs/constantes-chave
Empresas FB=1/LF=5 · partner LF=35 · trânsito 26489 · 31092 (LF/Mat.Terceiros) · 31093 (LF/PA Terceiros) · 30720 (FB customer terceiros) · pt98 (LF saída retorno 31093→26489) · pt52 (FB entrada retorno src=26489).
Contas: 5101010001 ATIVA FB=**22800**/LF=26652 · 5101020001 PASSIVA FB=22815/LF=**26667**.
Journals: j1001 ENTSI FB-purchase (no_pay VAZIO→setar 22800) · j847 VENDA PRODUÇÃO LF-sale (NF mista de retorno; no_pay vazio) · j1002 RETRABALHO LF-sale (`dev-industrializacao`, no_pay 26863) · j1003 PERDAS LF-sale (perda pura 5903) · j1047 ENTIN LF-purchase (no_pay 26667).
Operações retorno LF: 2702/3039 (5124 venda-ind) · 2864 (5902 venda-ind, usada na NF mista) · **2710 (5902 dev-industrializacao, separa em SARET)** · 2711 (5903 perda). FB entrada: 1902→2027/**3252** (op 3252 mov_estoque=False, mata double-count); 1124→3064/3134. fp da NF retorno LF = **fp 111**; fp entrada FB serviço = **fp 88**.
Lote FB PILOTO-3105 ids 60496-60511 (company 1, imutável).

## Contador — status
✅ Etapas 4-5 + Opção A (Ativo→Ativo, CPV só na venda) + PA=Ic+S confirmados. **PENDENTE (gargalo):** decisão de separar 5902/5124 (`MATERIAL_CONTADORA_G4.md`). Separado/sem prazo: regularização dos acumulados (5101010001 R$60,8M FB; insumos sem baixa R$8,68M LF — `GOALS G9`).
