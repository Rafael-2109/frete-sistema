# MAPA COMPLETO DO CICLO — Industrialização FB↔LF (contábil + físico)

> Análise profunda verificada ao vivo no Odoo PROD (2026-05-30). Scripts: `scripts/ciclo_analise_profunda.py`, `scripts/e2e_saida_fb_etapa1.py`. Substitui o entendimento parcial anterior (que olhava só o SVL e a conta `1150200001`).

## TL;DR — o ciclo NÃO fecha por design

A **remessa** (Etapa 1) e o **retorno** (Etapa 5) são contabilizados por **DOIS mecanismos fiscais DESCONECTADOS** que não se reconciliam:
- Remessa → fluxo **"REMESSA P/ INDUSTRIALIZAÇÃO"** (journal 17 / fp 25) → debita `5101010001 REMESSA INDUSTRIALIZAÇÃO (ATIVA)`.
- Retorno → fluxo **"ENTRADA - SERVIÇO DE INDUSTRIALIZAÇÃO"** (ENTSI) → trata como **compra de serviço** + re-recebe TUDO no estoque, e **ignora** `5101010001`.

Resultado: 3 saldos que só crescem (nunca zeram).

---

## 1. Os lançamentos REAIS de cada etapa (evidência)

### Etapa 1 — Remessa FB→LF (CFOP 5901, pt53)
Duas camadas → **NET**:
```
SVL:  D 1150100012 FATUR.FÍSICO / C 1150100002 EMBALAGEM
NF :  D 5101010001 REMESSA IND.(ATIVA) / C 1150100012 FATUR.FÍSICO   (fp25/journal17)
NET:  D 5101010001 REMESSA IND.(ATIVA) / C 1150100002 EMBALAGEM
```
✅ Reclassifica o componente para a conta de controle de remessa (ATIVA). **Correto** — mas nunca é revertido.

### Etapa 5 — Retorno LF→FB (real, ex.: FB/IN/13404 + ENTSI/2026/05/0127)
Duas camadas, **DESCONECTADAS da remessa**:
```
SVL (re-entrada física):
  D 1150100007 PRODUTO-ACABADO   4.414,99   ← PA entra (OK)
  D 1150100001 MATÉRIA-PRIMA       994,50   ← componente RE-ENTRA (DOUBLE-COUNT)
  D 1150100002 MAT. EMBALAGEM      809,67   ← componente RE-ENTRA (DOUBLE-COUNT)
  C 1150100011 RECEB.FÍSICO     6.219,16

NF ENTSI (entrada serviço industrialização):
  D 1150100011 RECEB.FÍSICO  ~/ C 1150100011  (mexe transitória)
  C 2120100001 FORNECEDORES NACIONAIS  4.865,00  ← paga LF pelo serviço (OK)
  D 1140200002/003 PIS/COFINS A RECUPERAR
```
❌ **Não credita `5101010001`** (remessa nunca baixada). ❌ **Re-infla estoque com os componentes** (já consumidos na MO, já incorporados no PA) → double-count.

---

## 2. Os 3 acúmulos quantificados (FB, posted)

| Conta | Saldo | Mecânica |
|---|---:|---|
| `5101010001` REMESSA IND. (ATIVA) | **+R$ 60.818.109,76** | D=R$ 61,0M (remessas) / C=R$ 0,19M. Remessas entram, **nunca baixadas** no retorno. |
| `1150100002/001/...` Estoque | (R$ 785k só MOLHO SHOYU PET) | Componentes do retorno **re-inflam** o Ativo Estoque (double-count). |
| `1150100011` RECEB. FÍSICO FISCAL | **−R$ 1.488.150.962,96** | Transitória nunca conciliada (vários fluxos; o retorno mexe mas não zera). |

`5101010002 RETORNO INDUSTRIALIZAÇÃO (ATIVA)` = **R$ 0** (FB e LF) → a perna de retorno **nunca** é registrada na sua conta de controle.

**Lado LF:** `5101010001` (LF) = +R$ 8,67M (via journal "SAÍDA - PERDAS") — também só acumula. Família PASSIVA `51020xx` tem saldos (REMESSA −17,98M, RETORNO −9,29M) mas **não espelha** a ATIVA → compensação não mantida em pares balanceados.

---

## 3. Operação real (físico)
- Retorno entra **2.880×** pelo `pt1` genérico (FB/Recebimento) vs **10×** pelo `pt52` RECEB/FB/IND (correto). O picking type dedicado está abandonado.
- A NF de entrada do retorno = **ENTSI (ENTRADA - SERVIÇO DE INDUSTRIALIZAÇÃO)** → trata o retorno como **aquisição de serviço + recebimento de mercadoria**, não como retorno de industrialização que baixa a remessa.

---

## 4. Root cause
> A remessa e o retorno são **operações fiscais independentes** no CIEL IT. A remessa abre `5101010001` (ATIVA); o retorno (ENTSI) paga o serviço e re-recebe tudo no estoque — **sem nenhum elo** que baixe `5101010001` nem que trate os componentes como simbólicos. Não há reconciliação remessa↔retorno por design.

---

## 5. O que o desenho CORRETO exige (proposta — validar com Contador)
Alinhado ao `00_FLUXO_ATUAL_VS_IDEAL.md §3.4`:

| Linha do retorno | CFOP | Hoje (errado) | Deveria |
|---|---|---|---|
| Componentes consumidos | 5902/1902 | `D estoque (1150100002/001)` re-infla | **Simbólico**: `C 5101010001` (baixa a remessa) / `D` custo incorporado no PA. NÃO re-entra no estoque. |
| Sobras não aplicadas | 5903/1903 | (mistura) | `D 1150100002` (sobra volta) / `C 5101010001` (baixa parcial). |
| Produto acabado | 5124/1124 | `D 1150100007` (OK) | `D 1150100007 PA` / `C 2120100001 FORNECEDORES` (valor agregado da industrialização). ✅ já ~correto. |

**No fim do ciclo:** `5101010001` zera (remessa baixada no retorno simbólico + sobras); estoque não infla (só PA + sobras); custo dos componentes incorporado no PA.

---

## 6. Decisões / perguntas ao Contador
1. **Conta-alvo:** seguir a família existente `51010xx` (REMESSA/RETORNO ATIVA) — corrigindo o retorno para baixá-la — em vez de migrar para `1150200001` (que a DIRETRIZ assumiu e está zerada)?
2. **Componentes do retorno (5902):** confirmar tratamento simbólico (baixa `5101010001`, não re-entra no estoque).
3. **Regularização:** `5101010001` = R$ 60,8M (FB) + R$ 8,67M (LF) acumulados + double-count de estoque (R$ 785k/produto) + transitória `1150100011` (−R$ 1,49 bi). Modo A/B/C.
4. **Mecanismo no CIEL IT:** a "ENTRADA SERVIÇO INDUSTRIALIZAÇÃO" precisa ser reconfigurada (mapeamento CFOP 1902 → baixa `5101010001` em vez de estoque), OU criar operação fiscal de retorno que feche o ciclo. **Provavelmente exige config fiscal CIEL IT, não só contas de categoria.**

> **Mudança de premissa do projeto:** o problema NÃO é "a saída não contabiliza terceiros" (ela contabiliza, em `5101010001`). O problema é o **retorno não fechar o ciclo** (não baixar `5101010001` + re-inflar estoque). O foco da solução muda da SAÍDA/LF (config de categoria) para o **RETORNO** (config fiscal da operação de entrada de industrialização).
