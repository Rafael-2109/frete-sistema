# Caso pendente: Tratar reservas pre-transferencia (71 cods Indisponivel — 2026-05-24)

**Status:** PAUSADO no meio da execucao (auditoria + plano gerados, NENHUM write em PROD).
**Razao da pausa:** Gap arquitetural identificado — gestor/skills nao tem ferramenta clara para tratar reservas ATIVAS bloqueando transferencias futuras.
**Inputs preservados:** `docs/inventario-2026-05/casos-pendentes/` (TSV original + audit + plano A/B).

---

## 1. Pedido original do usuario

> "Para testar, faça as transferencias abaixo e aproveite e ja valide 2 A e B, ou seja, faça em 2 etapas -> Lote para MIGRAÇÃO e depois local para Indisponivel"

**71 cods** em FB com qty especifica para mover para FB/Indisponivel via:
- **Etapa 1 (Skill 2 modo A):** lote_origem → MIGRAÇÃO em FB/Estoque
- **Etapa 2 (Skill 2 modo B):** MIGRAÇÃO em FB/Estoque → MIGRAÇÃO em FB/Indisponivel

Lista completa em `transferencias_indisp_2026_05_24.tsv` (mesma pasta).

---

## 2. Aviso operacional do usuario (importante)

> "Quando há reserva e a reserva é removida, o picking se mantem como 'assigned' e mesmo que volte 1 etapa, eu não sei se funcionaria, já ocorreu caso de remover a reserva e por algum motivo o picking ficar meio 'travado' (talvez na memória encontre algo)."

**Implicacao:** `--resetar-reserva-origem` (Skill 2) e `zerar_reserved_residual` (Skill 2.4) sao RISCOS conhecidos quando ha picking ativo.

---

## 3. Resultado da auditoria AO VIVO (READ-only via Skill 9)

**71 cods → 190 quants em FB** (chamada batch: `consultar_quants.py --cods <71> --empresas FB --formato json`).

### 3.1 Classificacao

| Categoria | N | Descricao |
|---|---|---|
| GREEN | 58 | Saldo livre cobre qty pedida em FB/Estoque; sem reservas problematicas |
| SKIP — sem saldo | 3 | `103` PEPINO, `46` VINAGRE ALCOOL TRIPLO, `X105000022` MOLHO SHOYU TRADICIONAL |
| SKIP — saldo em sublocation | 1 | `301000003` SALMOURA COGUMELO (2000 em FB/Pos-Producao, 0 em FB/Estoque) |
| FLAG 4a — quase-100% (centavos) | 4 | `105000003`, `105000021`, `105000038`, `602000006` (diff < 11) |
| FLAG 4b — ~50% (pickings ativos) | 5 | `104000054`, `4899027`, `4890128`, `4902852`, `103000117` |
| AJUSTAR QTY (arredondamento) | 2 | `105000102` (500.957→500.943), `4880176` (523→522.833) — incluidos em GREEN |

### 3.2 Padrao suspeito identificado (FLAG 4b)

**Lote `13206` aparece RESERVADO em 3 cods** (mesmo lote em produtos diferentes):
- `4899027` MOLHO SALADA MOSTARDA E GENGIBRE: lote 13206 reserved=269
- `4890128` MOLHO SALADA PARMESAO: lote 13206 reserved=319
- `4902852` MOLHO PESTO: lote 13206 reserved=447

**Lote `MIGRAÇÃO` em FB/Estoque aparece RESERVADO em 5 cods:**
- `103000113` PIMENTA BIQUINHO: MIGRACAO reserved=14.351
- `104000054` ACUCAR MASCAVO: MIGRACAO reserved=255.793
- `105000021` POLPA PIMENTA MALAGUETA: MIGRACAO reserved=0.150
- `105000038` EMULSAO ALHO: MIGRACAO reserved=0.156
- `103000117` PIMENTA BIQUINHO B: MIGRACAO reserved=620.320

**Hipotese:** picking(s) ativo(s) — provavelmente 1 picking unico cobrindo varios cods. Verificar via:
```sql
SELECT picking_id, picking_name FROM stock_move_line
WHERE lot_name='13206' AND state='assigned';
-- OU
SELECT picking_id, picking_name FROM stock_move_line
WHERE quant_id IN (258942, 258987, 259010, 259034, 258944);
-- OU
SELECT picking_id, picking_name FROM stock_move_line
WHERE product_id IN (...5 cods do MIGRACAO...) AND state='assigned'
  AND lot_id IN (...lots MIGRACAO desses produtos...);
```

**(Esta query NAO pode ser respondida pelas Skills 9/2.4 atuais — vide §4 Gaps.)**

---

## 4. GAP ARQUITETURAL identificado

### 4.1 Implementacao faltante

| Faltam | Onde | O que faz |
|---|---|---|
| `listar_pickings_por_quant(quant_ids)` | Skill 9 `consultando-quant-odoo` | Lista pickings + state + name que tem `stock.move.line` apontando para os quants alvo (cross-reference reverso) |
| `listar_move_lines_por_quant(quant_ids)` | Skill 9 ou Skill 2.4 | Lista MLs com state=assigned/partial apontando para quant_ids (detalhe da reserva) |
| `find_orphan_mls(quant_ids)` | Skill 2.4 (atomo previsto ⬜) | Identifica MLs orfas — diferente do acima (orfas = quant zerado), mas relacionado |
| `unreserve_picking(picking_id, reassign=False)` | Skill 2.4 (atomo previsto ⬜) | Equivalente seguro a `picking.do_unreserve` Odoo nativo — libera MLs do picking, picking volta a confirmed/waiting. Com reassign=True, tenta re-reservar com saldo atual. |

### 4.2 Fluxo composto faltante

**Folha proposta:** `app/odoo/estoque/fluxos/2.6-tratar-reserva-bloqueia-transferencia.md`

Sequencia:
```
1) (HOST) Skill 9 — para cada cod a transferir, checar reserved_quantity dos quants candidatos
2) Se reserved > 0 em quant candidato:
   2.1) Skill 9 — listar_pickings_por_quant(quant_id) → identifica pickings ativos
   2.2) HOST classifica picking:
        - state='done' → DEVOLVER via Skill 5
        - state='assigned/confirmed/waiting' → CANCELAR via Skill 5 OU desreservar via Skill 2.4 (futuro)
        - origem da reserva = MO → tratar MO via Skill 4
   2.3) Decisao humana (apresentar ao usuario):
        - Caminho A: cancelar picking (Skill 5 cancelar) — picking some, MLs liberadas
        - Caminho B: devolver picking (Skill 5 devolver) — so se state=done
        - Caminho C: nao mexer no picking, mover OUTRO lote sem reserva (Skill 2 --lote-origem)
        - Caminho D: pular este cod (skip)
3) Apos tratar reservas: prosseguir com Skill 2 modo A/B (transferencia original)
4) Verificar resultado direto no Odoo (regra inviolavel 6)
```

### 4.3 Direcionamento prompt subagente faltante

**Adicionar ao `.claude/agents/gestor-estoque-odoo.md`:**

Como **regra inviolavel nova:**
> **Antes de Skill 2 (transferencia), CHECAR reservas via Skill 9 (`reserved_quantity` real) dos quants candidatos a doar. SE reserved > 0 em quant candidato, INVESTIGAR pickings via fluxo 2.6 ANTES de prosseguir. NUNCA tocar reserva sem clareza do efeito no picking origem.**

### 4.4 Documentacao operacional faltante — "como desreservar de forma segura"

**Adicionar em SKILL.md da Skill 2.4 (`operando-reservas-odoo`)** — secao "Caminhos seguros para desreservar":

| Caminho | Comando | Quando usar | Risco |
|---|---|---|---|
| A. Cancelar picking inteiro | Skill 5 `cancelar` (`operar_picking.py --modo cancelar --picking-id X --confirmar`) | Picking sem valor (fantasma, NF nao emitida, operacao abandonada) | IRREVERSIVEL — picking some. Tratamento fiscal se NF emitida (consultar Fiscal). |
| B. Devolver picking | Skill 5 `devolver` (`--modo devolver --picking-id X --confirmar`) | Picking state=done, precisa estornar saldo | Cria devolucao (novo picking). Estorno fiscal pode ser necessario. |
| C. Desreservar mantendo picking | **NAO EXISTE** atomo na Skill 2.4 (previsto `unreserve_picking`) | Operador quer liberar reserva mas manter picking para re-reservar depois com saldo atual | RISCO: picking pode ficar TRAVADO em assigned (aviso usuario 2026-05-24). Workaround atual: `picking.do_unreserve` direto via XML-RPC — **fora da skill**. |
| D. Nao desreservar, usar OUTRO lote | Skill 2 (`transferir.py --modo A --lote-origem <ALTERNATIVO>`) | Existe outro lote livre com saldo suficiente | Mais seguro. Mas se nao houver lote alternativo livre, nao da. |
| E. Cirurgia em ML orfa | Skill 2.4 `cancelar_moves_orfaos` (cirurgia em ML especifica) | Picking tem MIX de MLs OK + orfas; quer preservar OK | Cobre apenas MLs **orfas** (quant ja zerado). NAO aplica para reserva ATIVA em quant com saldo. |

### 4.5 Resumo do gap

| Dimensao | Estado atual | O que faltou |
|---|---|---|
| **Mapeamento** | Existe consciencia de reservas orfas (Skill 2.4) | Falta consciencia de reservas ATIVAS bloqueando transferencias |
| **Implementacao** | Skill 2.4 cobre orfa post-mortem; Skill 9 retorna `reserved_quantity` real | Faltam atomos `listar_pickings_por_quant`, `listar_move_lines_por_quant`, `unreserve_picking` |
| **Wiring (fluxos)** | Fluxo 2.4 cobre orfa | Falta fluxo 2.6 "tratar reserva ativa pre-transferencia" |
| **Direcionamento (prompt)** | Subagente sabe das Skills 2.4 e 5 | Falta regra "checar reservas via Skill 9 ANTES de Skill 2" |
| **Conhecimento operacional** | Gotcha [[gotcha_resetar_reserva_orfao_negativo]] documenta orfas | Falta tabela "Caminhos seguros para desreservar" (A/B/C/D/E acima) |

---

## 5. Decisoes pendentes (a serem tomadas em sessao futura)

### 5.1 Categoria SKIP (4 cods)
- **103, 46, X105000022:** sem saldo em FB. **Confirmar SKIP definitivo** (X-prefix indica produto descontinuado — provavelmente correto).
- **301000003 SALMOURA COGUMELO:** 2000 em FB/Pos-Producao, 0 em FB/Estoque. **Opcoes:**
  - Skip definitivo
  - Transferir 2000 Pos-Producao → FB/Estoque (Skill 2 modo B) e depois rodar Etapa A+B normal

### 5.2 Categoria FLAG 4a (4 cods quase-100% — diff centavos)
- `105000003, 105000021, 105000038, 602000006`
- **Decisao**: reduzir qty para saldo livre (igual ao tratamento de 105000102/4880176)?

### 5.3 Categoria FLAG 4b (5 cods ~50% — pickings ativos)
- `104000054, 4899027, 4890128, 4902852, 103000117`
- **Bloqueador**: NAO SE PODE DECIDIR sem investigar quais pickings estao reservando o lote 13206 + MIGRACAO de FB/Estoque
- **Pre-requisito**: implementar `listar_pickings_por_quant` (gap 4.1) OU usar `consultando-sql` para query direta no DB local OU XML-RPC search ad-hoc
- **Apos identificar pickings**, decidir caminho A/B/C/D/E da tabela §4.4

### 5.4 Etapa B — MIGRACAO ja em FB/Estoque reservada
- 5 cods tem MIGRACAO ja existente em FB/Estoque com RESERVED alto (mesmos da §5.3)
- **Implicacao**: mesmo que Etapa A consiga adicionar qty na MIGRACAO, Etapa B vai tentar mover qty_total (incluindo reserved) → FALHARA
- **Decisao**: Etapa B move max(0, qty_real - reserved_no_MIGRACAO)? OU pula esses 5 cods?

---

## 6. Plano de execucao gerado (preservado em arquivos)

- `plano_etapa_A.tsv` — 95 chamadas Skill 2 modo A (lote → MIGRACAO em FB/Estoque)
- `plano_etapa_B.tsv` — 67 chamadas Skill 2 modo B (MIGRACAO FB/Estoque → FB/Indisp)
- `audit_indisp_classificado.json` — classificacao completa dos 71 cods
- `audit_fb_indisp.json` — 190 quants brutos retornados pela Skill 9
- `transferencias_indisp_2026_05_24.tsv` — input original

---

## 7. ZERO writes feitos em PROD nesta sessao

Auditoria: 1 chamada `consultar_quants.py` (READ-only via XML-RPC).
Modificacoes Odoo: **zero**.
Modificacoes banco PG PROD: **zero**.
Modificacoes filesystem PROD: **zero**.

---

## 8. Roteiro sugerido para retomar (proxima sessao)

1. **Discutir gap 4.1-4.4 com usuario** (este doc) — decidir prioridade:
   - Opcao P1: implementar atomos faltantes na Skill 9 + Skill 2.4 ANTES de retomar caso
   - Opcao P2: usar `consultando-sql` (ad-hoc) para investigar pickings, retomar caso, depois implementar atomos
2. Se P2: rodar query (Render MCP ou Skill `consultando-sql`):
   ```sql
   SELECT sml.picking_id, sp.name, sml.product_id, sml.lot_id,
          pp.default_code, sl.name as lot_name, sml.quantity, sml.state
   FROM stock_move_line sml
   JOIN stock_picking sp ON sml.picking_id=sp.id
   JOIN product_product pp ON sml.product_id=pp.id
   LEFT JOIN stock_lot sl ON sml.lot_id=sl.id
   WHERE sml.state IN ('assigned','partially_available')
     AND sml.company_id=1  -- FB
     AND (
        (sl.name='13206' AND pp.default_code IN ('4899027','4890128','4902852'))
        OR (sl.name='MIGRAÇÃO' AND pp.default_code IN ('103000113','104000054','105000021','105000038','103000117'))
     );
   ```
3. Identificar pickings, decidir caminho A-E para cada
4. Tratar reservas → retomar Etapa A + Etapa B do caso original
5. Apos: atualizar SKILL.md/fluxos/prompt com aprendizados (gap 4.5)
