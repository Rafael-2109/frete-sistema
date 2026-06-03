# PROMPT — Follow-ups da remessa avulsa FB→LF (b + c + ajuste de estoque)

> **Cole este prompt numa sessão nova.** Linha de trabalho SEPARADA do
> `PROMPT_PROXIMA_SESSAO.md` (que é do canary S2 inventário). NÃO confundir.
> **Criado**: 2026-06-02, após o canary REAL da remessa avulsa FB→LF concluído.

---

## §0. CONTEXTO (o que já foi feito — NÃO refazer)

O canary REAL da **remessa avulsa inter-company FB→LF de industrialização**
(`INDUSTRIALIZACAO_FB_LF`, produtos 105000002 + 105000044) foi concluído
end-to-end em 2026-06-02:
- **SAÍDA**: NF `RPI/2026/00248` (move **744869**) AUTORIZADA SEFAZ (CFOP 5901, fp 25).
- **ENTRADA**: NF `ENTIN/2026/06/0004` (move **745414**) posted (CFOP 1901, fp 131);
  picking `LF/IN/01796` (**323318**) done; saldo **LF/Estoque(42)/lote P-02/06 =
  AROMA 30,56 + SALSA 5,36**; PO canônica **42917** com picking+invoice.
- **Fixes commitados LOCAL (não pushados)**: C7 `9715c8f3d` · C9/C9.1 `a8835dbff`
  · C10 `0169e1694` · docs `7738ea879`+`ebfcc579f`.

**LEIA PRIMEIRO** (handoff completo + gaps): memória `capacitacao_gestor_remessa_fb_lf`
+ `app/odoo/estoque/CLAUDE.md §14 D-V30-1` + folha `app/odoo/estoque/fluxos/1.3.1-remessa-avulsa-insumo.md`.

> ⚠️ **Concorrência**: houve 2ª sessão/atividade no mesmo repo+Odoo (commitou C7, fez
> merges pad-a-onda3, criou PO 42917). Antes de pushar, conferir topologia (`git log`,
> `git pull --rebase`). A main local está à frente do que o Rafael tinha + 2 commits
> atrás de origin (Atacadão).

---

## §1. TAREFA (b) — reconciliar/limpar menções OBSOLETAS a `dfe='compra'`

**Contradição a resolver**: documentação antiga afirma que o DFe de
`INDUSTRIALIZACAO_FB_LF` deve ser `'compra'`; o **C6 + canary D-V30-1** provaram que é
**`serv-industrializacao`** (NF saiu, PO gerou, entrada escriturou CFOP 1901). O
`escriturar_dfe` inclusive **REJEITA** `'compra'` (whitelist em `escrituracao.py`).

**Regra ATUAL (verdade de campo)**: `L10N_BR_TIPO_PEDIDO_POR_ACAO['INDUSTRIALIZACAO_FB_LF']
= {'dfe':'serv-industrializacao','po':'serv-industrializacao'}` (já no código,
`inventario_pipeline.py:3316`). As **outras 7 ações continuam `dfe='compra'`** (ver §2).

**Arquivos com menções OBSOLETAS a `dfe='compra'` para INDUSTRIALIZACAO_FB_LF** (limpar/reconciliar,
preservando o histórico como "tentativa F3a revertida por C6", NÃO apagar contexto):
- `app/odoo/estoque/PROTECAO_PROXIMA_SESSAO.md` **N30** ("DFe deve receber tipo 'compra'…").
- `app/odoo/estoque/CLAUDE.md §14` **D-V25-1** (Sintoma 4 F3 + F3a) — hoje CONTRADIZ o D-V30-1 logo acima.
- `app/odoo/estoque/fluxos/1.3-transferencia-completa.md` (linhas ~96, ~132: "dfe='compra' UNIVERSAL").
- `app/odoo/estoque/ROADMAP_SKILLS.md` (linhas ~76, ~123: "dfe='compra' universal").
- `app/odoo/estoque/CIRURGIA_AVULSO_FRASCO_2026_05_27.md` (F3a) — é registro histórico; adicionar nota "revertido por C6 para INDUSTRIALIZACAO_FB_LF" em vez de apagar.

**Cuidado**: a frase "dfe='compra' UNIVERSAL" pode ser correta para as **outras 7 ações**
(decidir em §2 antes de reescrever como "universal=serv-industrializacao"). Não generalizar
o aprendizado de INDUSTRIALIZACAO_FB_LF para todas sem a análise de §2.

**Verificar a folha 1.3-transferencia-completa.md contra a 1.3.1**: a 1.3.1 (avulsa) já está
correta (serv-industrializacao); a 1.3 (com-ciclo) ainda diz 'compra'.

---

## §2. TAREFA (c) — avaliar as 7 ações restantes do mapeamento (`dfe='compra'`)

Mapeamento atual (`inventario_pipeline.py:3312+`, ainda `dfe='compra'`):

| Ação | dfe | po | Direção |
|------|-----|----|---------|
| PERDA_LF_FB | compra | retorno | LF→FB |
| DEV_LF_FB | compra | outro | LF→FB |
| DEV_CD_LF | compra | retorno | CD→LF |
| DEV_LF_CD | compra | outro | LF→CD |
| DEV_FB_LF | compra | retorno | FB→LF |
| TRANSFERIR_FB_CD | compra | transf-filial | FB→CD |
| TRANSFERIR_CD_FB | compra | transf-filial | CD→FB |

**Pergunta central (INCOERÊNCIA potencial)**: `escriturar_dfe` REJEITA `dfe='compra'`
(whitelist = serv-industrializacao/transf-filial/retorno/outro/industrializacao/perda/
dev-industrializacao). Então:
- Se a ação usa **caminho B** (criamos o DFe via `criar_dfe_a_partir_do_invoice_saida` +
  `escriturar_dfe`) → `dfe='compra'` **FALHARIA** no escriturar_dfe → precisa mudar para
  um tipo aceito (provavelmente alinhado ao `po`, ou serv-industrializacao).
- Se a ação usa **caminho A** (DFe chega via SEFAZ, `dfe='compra'` é o default do CIEL IT e
  NÃO passamos por escriturar_dfe) → `dfe='compra'` é só informacional → OK manter.

**Investigar (READ-only primeiro)**: para cada uma das 7 ações, qual caminho (A vs B) o
`executar_fluxo_l3_1_2_x` usa? (a folha 1.3.1 força B só p/ INDUSTRIALIZACAO_FB_LF; as
demais usam A automático quando `buscar_dfe` encontra). Confirmar empiricamente: há DFe
via SEFAZ para PERDA/DEV/TRANSFERIR? Se sim → caminho A → 'compra' OK. Se não → B → 'compra' quebra.

**Decisão (Rafael)**: NÃO alterar o mapeamento sem validar — cada ação tem semântica fiscal
própria (o `po` difere: retorno/outro/transf-filial). Recomendar: validar 1 caso natural de
cada direção em canary READ-only antes de mudar `dfe`. Registrar a conclusão (manter 'compra'
para caminho A; alinhar para serv-industrializacao só onde caminho B for usado).

---

## §3. TAREFA (ajuste de estoque) — remover paliativo + reconciliar trânsito

> Rafael: "Gerei saldo p/ produção, faça o processo normal… depois de concluído eu peço
> p/ ajustar o estoque." O processo normal está concluído. AGORA reconciliar.

**Estado atual no Odoo (confirmar AO VIVO antes de operar — pode ter mudado):**
- **Saldo OFICIAL (do fluxo, MANTER)**: LF/Estoque(42)/lote **P-02/06** = AROMA 105000002 **30,56** + SALSA 105000044 **5,36** (company 5).
- **Saldo PALIATIVO (REMOVER)**: criado por Rafael 15:40 UTC via inventory adjustment —
  LF/Estoque(42) lote **5276665** (AROMA, quant 268069, ~30,0284) + lote **0917/2022**
  (SALSA, quant 268071, ~4,8284). Contrapartidas em Ajuste (q268070=-30,56 / q268072=-5,36).
- ⚠️ **CONSUMO PARCIAL**: 0,5316 de cada já foi consumido por MOs **LF/MO/03506** + **LF/MO/03528**
  (em Estoque Virtual/Produção). O paliativo NÃO pode ser simplesmente zerado sem considerar
  o que já entrou em produção — senão a produção fica sem lastro.
- **TRÂNSITO 26489** (Em Trânsito Industrialização, company False): tem o saldo da SAÍDA
  (AROMA lote MIGRAÇÃO 30,9545 [inclui nosso 30,56 + resíduo 0,3945 não-nosso] + SALSA lote
  MIGRAÇÃO 5,36) + outros lotes de SALSA NÃO-nossos (0612/24, 1501/25, 0110/24 — NÃO tocar).
  Esse trânsito é "lixão acumulativo" (a entrada via Vendors NÃO o drenou).

**Objetivo do ajuste** (decidir COM o Rafael — é decisão fiscal/estoque dele):
1. Eliminar a DUPLICAÇÃO: o saldo da remessa entrou 2x (paliativo lotes 5276665/0917-2022 +
   oficial P-02/06). Manter só o P-02/06 (rastreável ao fluxo fiscal).
2. Tratar o consumo das MOs: o que foi consumido (0,5316 cada) saiu do lote paliativo —
   avaliar se re-aponta para P-02/06 ou se o ajuste compensa.
3. Drenar/reconciliar o trânsito 26489 (consumir os 30,56+5,36 da saída; preservar resíduo
   não-nosso 0,3945 AROMA + lotes alheios de SALSA).

**Ferramentas**: Skill 1 `ajustando-quant-odoo` (zerar/ajustar quants), Skill 2
`transferindo-interno-odoo` (mover saldo entre lotes/locais). SEMPRE `--dry-run` +
confirmação do Rafael antes de `--confirmar`. Este ajuste mexe em saldo PARCIALMENTE
CONSUMIDO POR PRODUÇÃO — máxima cautela; PROPOR o plano e aguardar OK explícito.

---

## §4. SALVAGUARDAS (inviolável)

- `--dry-run` antes de QUALQUER write; confirmação explícita do Rafael nos pontos de escrita.
- Verificar resultado DIRETO no Odoo (não confiar só no output dos scripts).
- NÃO tocar: NF saída 744869 (SEFAZ autorizada), NF entrada 745414, picking LF/IN/01796,
  saldo oficial P-02/06, lotes alheios de SALSA no trânsito.
- Operação de estoque (§3) mexe em saldo em produção → PARAR e reportar se houver risco de
  deixar MO sem lastro. NÃO improvisar XML-RPC fora das skills-átomo.
- Conferir concorrência (2ª sessão) antes de operar/pushar.

---

## §5. REFERÊNCIAS
- Memória: `capacitacao_gestor_remessa_fb_lf` (handoff completo + descobertas + follow-ups).
- `app/odoo/estoque/CLAUDE.md §14 D-V30-1` (canary) + D-V25-1 (F3a — a reconciliar em §1).
- Folhas: `fluxos/1.3.1-remessa-avulsa-insumo.md` (avulsa, correta) + `fluxos/1.3-transferencia-completa.md` (com-ciclo, a revisar §1).
- `app/odoo/estoque/PROTECAO_PROXIMA_SESSAO.md` (escudo — N30 a reconciliar §1).
- Subagente: `gestor-estoque-odoo` (executor WRITE) — delegar operações Odoo.
