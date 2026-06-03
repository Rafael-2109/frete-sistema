<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/superpowers/specs/INDEX.md
superseded_by: —
atualizado: 2026-06-02
-->
# Carregamento, Divergência e Fluxo NF — Design

> **Papel:** Carregamento, Divergência e Fluxo NF — Design.

## Indice

- [1. Contexto e motivação](#1-contexto-e-motivação)
  - [1.1 Problema observado em produção (2026-05-12)](#11-problema-observado-em-produção-2026-05-12)
  - [1.2 Diagnóstico](#12-diagnóstico)
  - [1.3 Conceito novo: Carregamento](#13-conceito-novo-carregamento)
- [2. Modelo de dados](#2-modelo-de-dados)
  - [2.1 Novas tabelas](#21-novas-tabelas)
  - [2.2 Modificações em tabelas existentes](#22-modificações-em-tabelas-existentes)
- [3. Diagrama de estados](#3-diagrama-de-estados)
  - [3.1 AssaiSeparacao (D-A opção b)](#31-assaiseparacao-d-a-opção-b)
  - [3.2 AssaiCarregamento](#32-assaicarregamento)
  - [3.3 AssaiNfQpa.status_match](#33-assainfqpastatus_match)
  - [3.4 AssaiPedidoVenda (R4.2 + CR-7)](#34-assaipedidovenda-r42-cr-7)
- [4. Cardinalidades e relações](#4-cardinalidades-e-relações)
- [5. SOT — Source of Truth por ordem temporal](#5-sot-source-of-truth-por-ordem-temporal)
  - [5.1 Cenário A — Carregamento antes da NF](#51-cenário-a-carregamento-antes-da-nf)
  - [5.2 Cenário B — NF antes do Carregamento](#52-cenário-b-nf-antes-do-carregamento)
  - [5.3 Cenário C — Carregamento e NF simultâneos (chegam em paralelo)](#53-cenário-c-carregamento-e-nf-simultâneos-chegam-em-paralelo)
- [6. Algoritmo de finalização do Carregamento (R1 confirmado)](#6-algoritmo-de-finalização-do-carregamento-r1-confirmado)
  - [Exemplo numérico (do usuário)](#exemplo-numérico-do-usuário)
  - [Timing dos eventos (A1 — Hipótese A)](#timing-dos-eventos-a1-hipótese-a)
  - [Funções e exceptions auxiliares (CR-8 + CR-13 — referência para implementação)](#funções-e-exceptions-auxiliares-cr-8-cr-13-referência-para-implementação)
- [7. Divergências (Section 5 detalhe)](#7-divergências-section-5-detalhe)
  - [7.1 Quando criar divergência](#71-quando-criar-divergência)
  - [7.2 Resoluções (Q13)](#72-resoluções-q13)
  - [7.2.1 — A8: Validação MODELO_DIVERGENTE em `_calcular_match`](#721-a8-validação-modelo_divergente-em-_calcular_match)
  - [7.3 Parser de CCe (R3 opção a)](#73-parser-de-cce-r3-opção-a)
  - [7.4 — A14: Idempotência em `resolver_divergencia` e `_calcular_match`](#74-a14-idempotência-em-resolver_divergencia-e-_calcular_match)
  - [7.1.1 — A7: Detecção de CHASSI_OUTRA_LOJA em fluxo NF](#711-a7-detecção-de-chassi_outra_loja-em-fluxo-nf)
- [8. Modal Expedição obrigatório](#8-modal-expedição-obrigatório)
  - [8.1 Quando aparece (Q15)](#81-quando-aparece-q15)
  - [8.2 Comportamento do modal](#82-comportamento-do-modal)
  - [8.3 UI](#83-ui)
  - [8.4 — A10: Edição posterior de agendamento (sep sem expedição)](#84-a10-edição-posterior-de-agendamento-sep-sem-expedição)
- [9. Cancelamento de NF (D3 + R5)](#9-cancelamento-de-nf-d3-r5)
  - [9.1 Service `cancelar_nf_qpa(nf_id, motivo, operador_id)`](#91-service-cancelar_nf_qpanf_id-motivo-operador_id)
  - [9.2 Quando "Sep sem Carregamento" tem NF cancelada (R5.2)](#92-quando-sep-sem-carregamento-tem-nf-cancelada-r52)
  - [9.3 Quando Carregamento existe (R5.3)](#93-quando-carregamento-existe-r53)
  - [9.4 Coluna nova em `assai_nf_qpa` (decisão técnica)](#94-coluna-nova-em-assai_nf_qpa-decisão-técnica)
- [10. Cancelamento de Pedido (R4.1) — ROADMAP FUTURO](#10-cancelamento-de-pedido-r41-roadmap-futuro)
- [11. Substituição de chassi entre lojas (Q21)](#11-substituição-de-chassi-entre-lojas-q21)
  - [11.1 Cenário 1 — manual (operador escaneia chassi de outra loja)](#111-cenário-1-manual-operador-escaneia-chassi-de-outra-loja)
  - [11.2 Cenário 2 — via NF importada (chassis batem com Sep de outra loja)](#112-cenário-2-via-nf-importada-chassis-batem-com-sep-de-outra-loja)
  - [11.3 Service `substituir_chassi_entre_seps(chassi, sep_origem_id, sep_destino_id, operador_id)`](#113-service-substituir_chassi_entre_sepschassi-sep_origem_id-sep_destino_id-operador_id)
- [12. Excel Q.P.A. — histórico de versões (D-C opção b)](#12-excel-qpa-histórico-de-versões-d-c-opção-b)
  - [12.1 Modelo](#121-modelo)
  - [12.2 Quando regenerar](#122-quando-regenerar)
  - [12.3 UI](#123-ui)
- [13. Espelhamento Nacom — `mirror_assai_to_separacao` (D-B opção c)](#13-espelhamento-nacom-mirror_assai_to_separacao-d-b-opção-c)
  - [13.1 Quando disparar](#131-quando-disparar)
  - [13.2 Caso Sep nasce diretamente em CARREGADA (Q4/Q6) ou FATURADA (S1=b)](#132-caso-sep-nasce-diretamente-em-carregada-q4q6-ou-faturada-s1b)
- [14. Status do pedido — transição automática (R4.2)](#14-status-do-pedido-transição-automática-r42)
  - [14.1 Service `recalcular_status_pedido(pedido_id)`](#141-service-recalcular_status_pedidopedido_id)
  - [14.2 Quando chamar (S10=a — todos os callsites)](#142-quando-chamar-s10a-todos-os-callsites)
  - [14.3 Migration de dados](#143-migration-de-dados)
  - [14.4 Remoção da atualização `EM_PRODUCAO` (compra_service)](#144-remoção-da-atualização-em_producao-compra_service)
- [15. Telas novas (UI)](#15-telas-novas-ui)
  - [15.1 `/motos-assai/carregamento` — Lista + Iniciar](#151-motos-assaicarregamento-lista-iniciar)
  - [15.2 `/motos-assai/carregamento/<id>` — Escanear chassis](#152-motos-assaicarregamentoid-escanear-chassis)
  - [15.3 `/motos-assai/divergencias` — Lista + resolução](#153-motos-assaidivergencias-lista-resolução)
  - [15.4 Modal Expedição (na importação NF)](#154-modal-expedição-na-importação-nf)
  - [15.5 Modal "Substituir chassi entre lojas"](#155-modal-substituir-chassi-entre-lojas)
  - [15.6 NFs órfãs antigas (S9=c — backfill no deploy)](#156-nfs-órfãs-antigas-s9c-backfill-no-deploy)
- [16. Migrations](#16-migrations)
- [17. Plano de implementação por fase](#17-plano-de-implementação-por-fase)
  - [Pré-requisitos (CR-5)](#pré-requisitos-cr-5)
  - [Fase 1 — Fundação (modelo + status)](#fase-1-fundação-modelo-status)
  - [Fase 2 — Carregamento (operação principal)](#fase-2-carregamento-operação-principal)
  - [Fase 3 — UI Carregamento](#fase-3-ui-carregamento)
  - [Fase 4 — NF + Divergências](#fase-4-nf-divergências)
  - [Fase 5 — Auxiliares](#fase-5-auxiliares)
  - [Fase 6 — Validação em prod](#fase-6-validação-em-prod)
- [18. Open issues / decisões em aberto](#18-open-issues-decisões-em-aberto)
- [19. Decisões aprovadas — rastreamento](#19-decisões-aprovadas-rastreamento)
  - [Decisoes da rodada S1-S22 (revisao pos-spec)](#decisoes-da-rodada-s1-s22-revisao-pos-spec)
  - [Self-review v1.1 — contradicoes residuais corrigidas (CR-1..CR-16)](#self-review-v11-contradicoes-residuais-corrigidas-cr-1cr-16)
  - [Decisões da rodada A1-A18 (revisão pós-v1.1, agente revisor externo)](#decisões-da-rodada-a1-a18-revisão-pós-v11-agente-revisor-externo)
- [20. Referências](#20-referências)
- [Contexto](#contexto)

**Data**: 2026-05-12
**Versão**: v1.2 (rodada A1-A18 do agente revisor externo)
**Autor**: Rafael Nascimento (validado iterativamente com Claude)
**Status**: design aprovado pelo dono do produto, pronto para writing-plans
**Decisões aprovadas via Q&A**: D1-D6 + Q1-Q21 + R1-R5 + D-A/B/C + S1-S22 + A1-A18

---

## 1. Contexto e motivação

### 1.1 Problema observado em produção (2026-05-12)

Consulta no Render mostrou estado anômalo do pipeline Motos Assaí:

| Métrica | Valor | Interpretação |
|---|---|---|
| NFs com `status_match=NAO_RECONCILIADO` | **30** | NF chegou antes da Sep — todas órfãs |
| Pedidos `FATURADO` ou `PARCIALMENTE_FATURADO` | **0** | Status do pedido nunca atualiza |
| Eventos `SEPARADA` ou `FATURADA` | **0** | Pipeline final nunca percorrido |
| Seps duplicadas (CANCELADA + EM_SEPARACAO vazia) | **1 par** | Bug de criação automática (corrigido Migration 17) |

### 1.2 Diagnóstico

O fluxo atual assume linha do tempo `Sep → Excel → NF` (caminho feliz). Na prática:

- **NF pode chegar antes da Sep** (cliente importa PDF da NF Q.P.A. recebida sem ter feito a separação ainda) — 30 órfãs em prod.
- **Carregamento físico pode divergir da Sep planejada** (operador trocou chassis no caminhão sem refletir no sistema).
- **Status do pedido fica defasado** — não há trigger para `FATURADO_PARCIAL`/`FATURADO`.
- **Não há cancelamento de NF** (CCe / devolução / erro emissão).

### 1.3 Conceito novo: Carregamento

Nova entidade entre **Separação** e **NF** que representa o **carregamento físico** das motos no veículo. Funciona como SOT (Source of Truth):

```
Separação (planejamento) → Carregamento (carga real) → NF (faturamento)
```

Quem chega primeiro entre Carregamento e NF define a verdade; o segundo bate ou gera divergência.

---

## 2. Modelo de dados

### 2.1 Novas tabelas

#### `assai_carregamento`

```sql
CREATE TABLE assai_carregamento (
    id SERIAL PRIMARY KEY,
    pedido_id INTEGER NOT NULL REFERENCES assai_pedido_venda(id),
    loja_id INTEGER NOT NULL REFERENCES assai_loja(id),
    separacao_id INTEGER REFERENCES assai_separacao(id),  -- NULL até finalizar
    status VARCHAR(20) NOT NULL DEFAULT 'EM_CARREGAMENTO',
    iniciado_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo'),
    iniciado_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    finalizado_em TIMESTAMP,
    finalizado_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    cancelado_em TIMESTAMP,
    cancelado_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    motivo_cancelamento TEXT
);

-- A2: SEM UNIQUE em (pedido, loja, EM_CARREGAMENTO) — permite N carregamentos
-- paralelos por (pedido, loja). Razao: 2+ caminhoes para mesma loja em paralelo
-- e cenario real (consistente com S18=b que ja permite N seps).
-- Enforcement: lock pessimista por chassi (S3=c) garante que mesmo chassi nao
-- esta em 2 carregamentos ativos. Disputa por sep alvo no finalize via lock
-- pessimista em assai_separacao (ver §6 Fase 1).
-- (UNIQUE uq_assai_carregamento_pedido_loja_ativo REMOVIDO em v1.2)

-- UNIQUE: 1 carregamento FINALIZADO ↔ 1 sep (Q2: cardinalidade 1:1).
CREATE UNIQUE INDEX uq_assai_carregamento_sep
    ON assai_carregamento (separacao_id)
    WHERE separacao_id IS NOT NULL AND status = 'FINALIZADO';
```

Status válidos: `EM_CARREGAMENTO`, `FINALIZADO`, `CANCELADO`.

#### `assai_carregamento_item`

```sql
CREATE TABLE assai_carregamento_item (
    id SERIAL PRIMARY KEY,
    carregamento_id INTEGER NOT NULL REFERENCES assai_carregamento(id) ON DELETE CASCADE,
    chassi VARCHAR(50) NOT NULL,
    modelo_id INTEGER NOT NULL REFERENCES assai_modelo(id),
    escaneado_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo'),
    escaneado_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL
);

CREATE INDEX ix_assai_carregamento_item_carregamento ON assai_carregamento_item(carregamento_id);
CREATE INDEX ix_assai_carregamento_item_chassi ON assai_carregamento_item(chassi);

-- ENFORCEMENT (S3=c — lock pessimista, sem UNIQUE no DB):
-- Subquery em indice parcial NAO e suportada em PostgreSQL. Decisao:
-- enforcement via lock pessimista em assai_moto (mesmo padrao de assai_separacao_item).
-- Antes de INSERT em assai_carregamento_item, carregamento_service faz:
--   1. SELECT * FROM assai_moto WHERE chassi = X FOR UPDATE
--   2. Valida que status_efetivo(chassi) NAO esta em CARREGADA (via assai_moto_evento ultimo)
--   3. Valida que NAO existe outra linha em assai_carregamento_item joinada com
--      carregamento.status = 'EM_CARREGAMENTO' para o mesmo chassi
--   4. INSERT — se race, IntegrityError do passo 2/3 retorna HTTP 409.
-- Padrao identico ao usado em separacao_service.registrar_chassi (with_for_update).
```

#### `assai_divergencia`

```sql
CREATE TABLE assai_divergencia (
    id SERIAL PRIMARY KEY,
    tipo VARCHAR(40) NOT NULL,
    -- Tipos:
    --   NF_CHASSI_FORA_CARREGAMENTO      = NF tem chassi que Carregamento não tem
    --   CARREGAMENTO_CHASSI_FORA_NF      = Carregamento tem chassi que NF não tem
    --   CHASSI_NAO_CADASTRADO            = NF tem chassi não recebido (assai_moto vazio)
    --   CHASSI_OUTRA_LOJA                = chassi em uso em sep de outra loja
    chassi VARCHAR(50),
    separacao_id INTEGER REFERENCES assai_separacao(id),
    carregamento_id INTEGER REFERENCES assai_carregamento(id),
    nf_id INTEGER REFERENCES assai_nf_qpa(id),
    detalhes JSONB DEFAULT '{}'::jsonb,
    -- detalhes contém: {modelo_esperado, modelo_extraido, valor_esperado,
    --                   valor_extraido, loja_origem_id, loja_destino_id, ...}
    criada_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo'),
    resolvida_em TIMESTAMP,
    resolvida_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    tipo_resolucao VARCHAR(40),
    -- Tipos de resolução:
    --   CANCELAR_NF                = NF cancelada via cancelar_nf_qpa
    --   CCE                        = Carta de correção (operador faz upload do PDF)
    --   ALTERAR_CARREGAMENTO       = Operador edita Carregamento
    --   SUBSTITUIR_CHASSI          = Substituir chassi entre lojas
    --   IGNORAR                    = Operador marca como aceita (gerencial)
    observacao_resolucao TEXT,
    CONSTRAINT ck_assai_divergencia_tipo
        CHECK (tipo IN (
            -- Tipos novos (Carregamento × NF + cross-loja):
            'NF_CHASSI_FORA_CARREGAMENTO',
            'CARREGAMENTO_CHASSI_FORA_NF',
            'CHASSI_NAO_CADASTRADO',
            'CHASSI_OUTRA_LOJA',
            -- Tipos legados de _calcular_match (S8=a — centralizar):
            -- migrados de assai_nf_qpa_item.tipo_divergencia via Migration 25.
            'LOJA_DIVERGENTE',
            'VALOR_DIVERGENTE',
            'MODELO_DIVERGENTE',
            'CHASSI_SEM_SEPARACAO'
        )),
    CONSTRAINT ck_assai_divergencia_resolucao
        CHECK (tipo_resolucao IS NULL OR tipo_resolucao IN (
            'CANCELAR_NF', 'CCE', 'ALTERAR_CARREGAMENTO',
            'SUBSTITUIR_CHASSI', 'IGNORAR'
        ))
);

CREATE INDEX ix_assai_divergencia_chassi ON assai_divergencia(chassi);
CREATE INDEX ix_assai_divergencia_pendentes
    ON assai_divergencia(criada_em DESC)
    WHERE resolvida_em IS NULL;
CREATE INDEX ix_assai_divergencia_sep ON assai_divergencia(separacao_id);
CREATE INDEX ix_assai_divergencia_nf ON assai_divergencia(nf_id);
```

#### `assai_nf_qpa_item_vinculo_historico` (S16=c)

```sql
-- Auditoria do vinculo NF-item ↔ Sep-item antes de cancelamento da NF.
-- Quando cancelar_nf_qpa limpa assai_nf_qpa_item.separacao_item_id, registra aqui
-- para preservar historico (qual item da sep foi vinculado a qual item da NF).
CREATE TABLE assai_nf_qpa_item_vinculo_historico (
    id SERIAL PRIMARY KEY,
    nf_qpa_item_id INTEGER NOT NULL REFERENCES assai_nf_qpa_item(id),
    separacao_item_id INTEGER REFERENCES assai_separacao_item(id) ON DELETE SET NULL,
    motivo VARCHAR(40) NOT NULL,  -- 'NF_CANCELADA', 'CCE_ALTEROU_CHASSI', etc.
    chassi_no_momento VARCHAR(50) NOT NULL,
    registrado_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo'),
    registrado_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    detalhes JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX ix_assai_nf_qpa_item_vinculo_hist_nf
    ON assai_nf_qpa_item_vinculo_historico(nf_qpa_item_id);
```

#### `assai_pedido_excel`

```sql
CREATE TABLE assai_pedido_excel (
    id SERIAL PRIMARY KEY,
    pedido_id INTEGER NOT NULL REFERENCES assai_pedido_venda(id),
    separacao_id INTEGER NOT NULL REFERENCES assai_separacao(id),
    s3_key VARCHAR(500) NOT NULL,
    versao INTEGER NOT NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    gerado_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo'),
    gerado_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    motivo_regeneracao TEXT
);

CREATE INDEX ix_assai_pedido_excel_pedido ON assai_pedido_excel(pedido_id);
CREATE INDEX ix_assai_pedido_excel_sep ON assai_pedido_excel(separacao_id);
-- UNIQUE parcial: apenas 1 ativo por sep
CREATE UNIQUE INDEX uq_assai_pedido_excel_sep_ativo
    ON assai_pedido_excel(separacao_id) WHERE ativo = TRUE;
-- UNIQUE total (S13=a — proteger race em versao):
-- duas regeneracoes concorrentes calculam MAX(versao)+1 simultaneo.
-- Constraint catch via IntegrityError + retry com versao+1.
CREATE UNIQUE INDEX uq_assai_pedido_excel_sep_versao
    ON assai_pedido_excel(separacao_id, versao);
```

### 2.2 Modificações em tabelas existentes

#### `assai_separacao` — novo status

Adicionar `CARREGADA` ao enum lógico. Pipeline final:

```
EM_SEPARACAO → FECHADA → CARREGADA → FATURADA (+ CANCELADA lateral)
```

Sem mudança de schema (campo `status VARCHAR(20)` aceita o novo valor). Atualizar constantes em `models/separacao.py`.

#### `assai_nf_qpa` — novo status_match + UNIQUE parcial (A3)

Adicionar `CANCELADA` aos valores possíveis. Sem mudança de schema do enum. Atualizar constantes.

**A3 — UNIQUE parcial novo** (Migration 27): garante apenas 1 NF ativa por sep.
Cenário: Sep nasce FATURADA com NF A; NF A cancelada; NF B chega para a mesma sep.
Sem UNIQUE, queries `filter_by(separacao_id=X).first()` podem pegar a CANCELADA
aleatoriamente.

```sql
CREATE UNIQUE INDEX uq_assai_nf_qpa_separacao_ativa
    ON assai_nf_qpa (separacao_id)
    WHERE separacao_id IS NOT NULL AND status_match != 'CANCELADA';
```

#### `assai_pedido_venda` — simplificar status

Status antigo (6): `ABERTO`, `EM_PRODUCAO`, `SEPARANDO`, `FATURADO_PARCIAL`, `FATURADO`, `CANCELADO`.

Status novo (4): `ABERTO`, `PARCIALMENTE_FATURADO`, `FATURADO`, `CANCELADO`.

**Regra de transição** (calculada automaticamente, R4.2):
- `qtd_faturada == 0` → `ABERTO`
- `0 < qtd_faturada < qtd_pedida` → `PARCIALMENTE_FATURADO`
- `qtd_faturada == qtd_pedida` → `FATURADO`
- Manual: `CANCELADO` (operador cancela)

`qtd_faturada` = COUNT de chassis em seps com status `FATURADA` do pedido.
`qtd_pedida` = SUM de `qtd_pedida` em `AssaiPedidoVendaItem` do pedido.

Hook: recalcular em mudanças de sep (FATURADA / CANCELADA) e em cancelamento de NF.

Migration de dados: backfill todos os pedidos para o novo regime.

#### `assai_moto_evento` — novo tipo

Adicionar `CARREGADA` ao enum lógico de tipos (após `SEPARADA`, antes de `FATURADA`).

Ordem semântica do pipeline:
```
ESTOQUE → MONTADA → DISPONIVEL → SEPARADA → CARREGADA → FATURADA
                  (+ PENDENTE, REVERTIDA_PARA_MONTADA, CANCELADA, MOTO_FALTANDO)
```

#### `assai_separacao.solicitacao_excel_s3_key` — DEPRECATED

Manter coluna por compatibilidade, mas novas gerações de Excel passam a usar `assai_pedido_excel`.

Migration de dados (opcional): copiar valor existente para novas linhas em `assai_pedido_excel` com `versao=1, ativo=TRUE`.

#### `assai_nf_qpa_item.tipo_divergencia` — DEPRECATED (A12=b)

A12=b: após centralizar divergências em `assai_divergencia` (S8=a + Migration 25),
a coluna `tipo_divergencia` em `assai_nf_qpa_item` torna-se NULLable e **não é mais
populada por novos fluxos**. Mantida por compatibilidade durante transição.

**Roadmap futuro**: Migration N+10 (após garantir nenhum callsite legado lendo
`tipo_divergencia`) faz `ALTER TABLE assai_nf_qpa_item DROP COLUMN tipo_divergencia`.
**NÃO drop agora** (regressão).

Código Fase 4: `_calcular_match` só grava em `assai_divergencia`. **NÃO** grava em
`tipo_divergencia` (corte limpo).

---

## 3. Diagrama de estados

### 3.1 AssaiSeparacao (D-A opção b)

```
                         (operador clica Finalizar)
   [ EM_SEPARACAO ] ─────────────────────────────► [ FECHADA ]
        │                                              │
        │                                              │  (Carregamento finaliza
        │                                              │   e ajusta a Sep)
        │                                              ▼
        │                                          [ CARREGADA ]
        │                                              │
        │                                              │  (NF importada
        │                                              │   e BATEU)
        │                                              ▼
        │                                          [ FATURADA ]
        │
        ▼  (operador cancela)
   [ CANCELADA ]  ◄─── pode ser cancelada de qualquer estado != FATURADA
```

**Caminhos alternativos legítimos** (atalhos do pipeline padrão):

**Atalho 1 — Carregamento sem Sep prévia (Q4/Q6)**:
```
(nenhuma Sep) → operador inicia Carregamento → escaneia chassis → finaliza
              → sistema CRIA Sep automaticamente em CARREGADA (pula EM_SEPARACAO + FECHADA)
```

**Atalho 2 — NF antes da Sep (S1=b — sep nasce em FATURADA)**:
```
(nenhuma Sep)  → NF importada e bate com chassis em assai_moto
               → sistema CRIA Sep automaticamente em FATURADA (pula EM_SEPARACAO + FECHADA + CARREGADA)
               → modal Expedição abre na hora (§8); pular = sep sem expedição
```

**Atalho 3 — NF antes do Carregamento, com Sep candidata existente**:
```
Sep em EM_SEPARACAO ou FECHADA → NF importada bate via ajustar_separacao_pela_nf
                                → Sep vira FATURADA (pula CARREGADA — anomalia aceita)
```

> Nota: Atalhos 2 e 3 deixam Sep em **FATURADA sem nunca ter passado por CARREGADA**. Se Carregamento físico ocorrer depois, ele encontra Sep FATURADA e gera divergências (§6 Fase 7 + S22).

### 3.2 AssaiCarregamento

```
   [ EM_CARREGAMENTO ] ──(finalizar)──► [ FINALIZADO ]
            │                                  │
            │                                  │  (operador clica "Alterar")
            │                                  ▼  (S6=a — REABRE)
            │                            [ EM_CARREGAMENTO ]
            │                                  │
            ▼  (cancelar)                      │  ↻ re-finaliza
   [ CANCELADO ]                          (executa Fase 2-6 §6 novamente)
```

**S6=a**: "Alterar Carregamento" reabre via transição `FINALIZADO → EM_CARREGAMENTO`. Operador adiciona/remove chassis. Re-finalizar re-executa algoritmo §6.

**S5=b**: cancelar Carregamento **FINALIZADO** mantém chassis na sep como SEPARADA (não desfaz adições). Cancelar Carregamento **EM_CARREGAMENTO** (antes de finalizar) volta chassis ao estado anterior (DISPONIVEL se nunca foram para sep, SEPARADA se já estavam).

### 3.3 AssaiNfQpa.status_match

```
NAO_RECONCILIADO ──► DIVERGENTE ◄──► BATEU
       │                  │             │
       │                  │             │
       └──────────────────┼─────────────┤
                          │             │
                          ▼             ▼  (cancelar_nf_qpa)
                       CANCELADA  ◄──── (qualquer estado)
```

**CR-1**: cancelamento permitido de **qualquer** estado (NF emitida errada, Sendas devolve antes de bater, devolução cliente após faturar — todos cenários reais). Service `cancelar_nf_qpa` valida apenas `status_match != CANCELADA` (idempotência).

### 3.4 AssaiPedidoVenda (R4.2 + CR-7)

```
            ┌─► CANCELADO (manual via cancelar_pedido_assai — roadmap §10)
            │
ABERTO ◄──┬──► PARCIALMENTE_FATURADO ◄──┬──► FATURADO
          │   ▲                          │   │
          │   │   (recalcular_status_pedido) │
          └───┴──────────────────────────┴───┘

Setas de retorno (CR-7): cancelar_nf_qpa reverte chassis FATURADA → CARREGADA/SEPARADA;
recalcular_status_pedido faz pedido voltar PARCIALMENTE_FATURADO ou ABERTO conforme
qtd_faturada residual. CANCELADO é estado terminal (manual, não reversível automaticamente).
```

---

## 4. Cardinalidades e relações

| De | Para | Cardinalidade | Constraint |
|---|---|---|---|
| Pedido | Sep | 1:N | nenhuma — N seps por (pedido, loja) permitidas (Migration 13) |
| (pedido, loja) | Carregamento ativo | 1:0..1 | UNIQUE `assai_carregamento(pedido_id, loja_id)` WHERE status='EM_CARREGAMENTO' |
| (pedido, loja) | Carregamento finalizado | 1:N | **S18=b** — N carregamentos finalizados ao longo do tempo, cada um vinculado a sep distinta |
| Sep | Carregamento | 1:0..1 | UNIQUE `assai_carregamento(separacao_id)` quando FINALIZADO |
| Sep | NF | 1:0..1 | já existe via `assai_nf_qpa.separacao_id` |
| Carregamento | NF | 1:0..1 | derivado: `Carregamento → Sep → NF` |
| Carregamento | Chassi | 1:N | um carregamento tem N chassis |
| Chassi | Carregamento ativo | 1:0..1 | um chassi não pode estar em 2 carregamentos ativos (S3=c lock) |

**S18=b — multiplos carregamentos por (pedido, loja)**: cenario real (2+ veiculos para mesma loja). Cada carregamento se vincula a sep propria (1:1 sep ↔ carregamento). Sep CARREGADA/FATURADA NAO entra no match de novos carregamentos (algoritmo §6 Fase 1 filtro). Logo, novo carregamento cria nova sep automaticamente se nao houver sep EM_SEPARACAO/FECHADA candidata.

---

## 5. SOT — Source of Truth por ordem temporal

Regra geral: **quem chega primeiro (Carregamento ou NF) é SOT**. O segundo bate ou gera divergência.

### 5.1 Cenário A — Carregamento antes da NF

```
T1: operador inicia Carregamento
T2: operador escaneia chassis (lista persistida em assai_carregamento_item)
T3: operador finaliza Carregamento
    → sistema busca Sep alvo (mais chassis em comum)
    → ajusta Sep (Section 6)
    → Sep vira CARREGADA
    → emite evento CARREGADA para cada chassi
T4: NF chega
    → _calcular_match compara NF com Sep (que já reflete Carregamento)
    → BATEU naturalmente, ou gera divergência por chassi
```

Se NF tem chassis ≠ Carregamento (Sep): divergência tipo `NF_CHASSI_FORA_CARREGAMENTO` por chassi.

### 5.2 Cenário B — NF antes do Carregamento

```
T1: NF importada
T2: sistema busca Sep candidata (ajustar_separacao_pela_nf atual)
T3a: NÃO há Sep → cria automaticamente em FATURADA + abre Modal Expedição (S1=b)
     → NF vira BATEU; sep nasce em FATURADA pulando EM_SEPARACAO + FECHADA + CARREGADA
T3b: HÁ Sep candidata → ajusta + Sep vira FATURADA (PULA CARREGADA — anomalia aceita)
T4: operador inicia Carregamento depois
    → Sep alvo já está FATURADA — cada chassi do Carregamento é confrontado:
      * chassi presente na NF/Sep: OK
      * chassi ausente da NF/Sep: cria divergência CARREGAMENTO_CHASSI_FORA_NF
    → Sep NÃO regride para CARREGADA (já é FATURADA — só divergência fica para resolver)
    → Operador resolve via cancelar NF (volta a CARREGADA via §9), CCe ou alterar Carregamento
```

**S1=b — decisão crítica**: tanto T3a quanto T3b deixam Sep em FATURADA. NF nasce BATEU. Carregamento posterior gera divergências sem regredir status.

### 5.3 Cenário C — Carregamento e NF simultâneos (chegam em paralelo)

Resolvido via lock pessimista em `AssaiMoto`. Quem fizer commit primeiro é SOT. O segundo encontra Sep já ajustada e gera divergência.

---

## 6. Algoritmo de finalização do Carregamento (R1 confirmado)

Pseudocódigo:

```python
def finalizar_carregamento(carregamento_id, operador_id):
    car = AssaiCarregamento.query.get(carregamento_id)
    chassis_car = [item.chassi for item in car.itens]  # ex: [C1..C5, X1..X10]

    # === FASE 1: identificar ou criar Sep alvo ===
    # S18=b — Sep CARREGADA/FATURADA NAO entra no match: ja tem Carregamento (1:1).
    # Permite N seps por (pedido, loja) (Migration 13). Carregamento novo cria
    # nova Sep se nenhuma EM_SEPARACAO/FECHADA candidata existir.
    seps_ativas = AssaiSeparacao.query.filter(
        pedido_id=car.pedido_id, loja_id=car.loja_id,
        status.in_([EM_SEPARACAO, FECHADA]),  # S18=b — exclui CARREGADA + FATURADA
    ).all()

    if not seps_ativas:
        # Q4/Q6: criar Sep automaticamente em CARREGADA, pulando FECHADA.
        # A9: fechada_em + fechada_por_id usam o operador_id do Carregamento
        # (sep nascida em estado avancado nao tem operador "que finalizou" no
        # sentido tradicional; convencao usa o evento criador).
        sep_alvo = AssaiSeparacao(
            pedido_id=car.pedido_id, loja_id=car.loja_id,
            status='CARREGADA',  # pula EM_SEPARACAO + FECHADA
            iniciada_em=now(),
            fechada_em=now(),
            fechada_por_id=operador_id,  # A9
        )
    else:
        # Q5: match por contagem de chassis em comum
        sep_alvo = max(seps_ativas, key=lambda s: count_em_comum(s, chassis_car))

    # === FASE 2: sobrescrever Sep alvo com chassis do Carregamento (Q10) ===
    items_atuais = AssaiSeparacaoItem.query.filter_by(separacao_id=sep_alvo.id).all()
    chassis_atuais = {it.chassi for it in items_atuais}
    chassis_novos = set(chassis_car)

    # Chassis a remover (estavam na Sep mas não no Carregamento)
    chassis_remover = chassis_atuais - chassis_novos
    for chassi in chassis_remover:
        item = next(it for it in items_atuais if it.chassi == chassi)
        db.session.delete(item)
        # S2=b — R1.3 valido: tentar realocar antes de DISPONIVEL
        outras_seps_com_saldo = (
            AssaiSeparacao.query
            .filter(
                AssaiSeparacao.pedido_id == car.pedido_id,
                AssaiSeparacao.loja_id == car.loja_id,
                AssaiSeparacao.id != sep_alvo.id,
                AssaiSeparacao.status.in_(['EM_SEPARACAO', 'FECHADA']),
            )
            .all()
        )
        modelo_id = AssaiMoto.query.filter_by(chassi=chassi).first().modelo_id
        sep_destino = None
        for sep_cand in outras_seps_com_saldo:
            saldo = saldo_pendente_por_modelo(sep_cand.id).get(modelo_id, 0)
            if saldo > 0:
                sep_destino = sep_cand
                break
        if sep_destino:
            # Realoca: cria item na sep_destino + emite SEPARADA
            db.session.add(AssaiSeparacaoItem(
                separacao_id=sep_destino.id, chassi=chassi,
                modelo_id=modelo_id, valor_unitario_qpa=item.valor_unitario_qpa,
            ))
            emitir_evento(chassi, 'SEPARADA', operador_id,
                          observacao='realocado pelo Carregamento (S2=b)')
        else:
            # Não há sep com saldo → vai DISPONIVEL (R1.1 fallback)
            emitir_evento(chassi, 'DISPONIVEL', operador_id,
                          observacao='expulso pelo Carregamento, sem sep destino')

    # Chassis a adicionar (no Carregamento mas não na Sep)
    chassis_adicionar = chassis_novos - chassis_atuais
    for chassi in chassis_adicionar:
        moto = AssaiMoto.query.filter_by(chassi=chassi).first()
        novo_item = AssaiSeparacaoItem(
            separacao_id=sep_alvo.id, chassi=chassi,
            modelo_id=moto.modelo_id, valor_unitario_qpa=...,
        )
        db.session.add(novo_item)
        emitir_evento(chassi, 'SEPARADA', operador_id,
                      observacao='adicionado pelo Carregamento')
        # CR-6: evento CARREGADA sera emitido na Fase 4 abaixo (loop unico para
        # TODOS chassis_car). Resultado: chassis adicionados aqui pegam sequencia
        # (SEPARADA, CARREGADA); chassis que ja estavam na sep pegam apenas CARREGADA.

    # === FASE 3: respeitar limite do pedido (R1.2 + S14=a) ===
    qtd_pedida_total = SUM(qtd_pedida) for items do pedido
    qtd_separada_total = COUNT items em TODAS seps != CANCELADA do pedido

    if qtd_separada_total > qtd_pedida_total:
        excedente = qtd_separada_total - qtd_pedida_total
        outras_seps = [s for s in seps_ativas if s.id != sep_alvo.id]

        # S14=a — restringir a (EM_SEPARACAO, FECHADA): NAO mexer em CARREGADA/FATURADA
        candidatos = (
            AssaiSeparacaoItem.query
            .join(AssaiSeparacao)
            .filter(
                AssaiSeparacao.id.in_([s.id for s in outras_seps]),
                AssaiSeparacao.status.in_(['EM_SEPARACAO', 'FECHADA']),  # S14=a
            )
            .order_by(AssaiSeparacaoItem.registrada_em.desc())  # R1.2 LIFO
            .limit(excedente)
            .all()
        )

        if len(candidatos) < excedente:
            # S14=a — escalar para operador: nao tem candidatos suficientes
            faltam = excedente - len(candidatos)
            raise CarregamentoExcedenteError(
                f'Pedido excedido em {excedente} chassis mas apenas {len(candidatos)} '
                f'podem ser removidos automaticamente (faltam {faltam}). '
                f'Operador deve resolver: cancelar Carregamento, alterar chassis ou '
                f'cancelar seps CARREGADA/FATURADA antes de re-finalizar.'
            )
            # Tela exibe flash + lista de seps CARREGADA/FATURADA do pedido para acao manual

        for it in candidatos:
            chassi = it.chassi
            db.session.delete(it)
            emitir_evento(chassi, 'DISPONIVEL', operador_id,
                          observacao='removido por excedente pedido (LIFO)')

    # === FASE 4: Sep alvo CARREGADA ===
    sep_alvo.status = 'CARREGADA'
    car.separacao_id = sep_alvo.id
    car.status = 'FINALIZADO'
    car.finalizado_em = now()

    # Emitir evento CARREGADA para cada chassi do Carregamento
    for chassi in chassis_car:
        emitir_evento(chassi, 'CARREGADA', operador_id,
                      dados_extras={'carregamento_id': car.id, 'sep_id': sep_alvo.id})

    # === FASE 5: regenerar Excel Q.P.A. (D-C + S13=a + CR-9/CR-12 race fix) ===
    # CR-12: lock pessimista na sep para serializar regeneracoes concorrentes.
    # Evita race em (versao + ativo): dois processos calculando MAX(versao)+1.
    AssaiSeparacao.query.filter_by(id=sep_alvo.id).with_for_update().first()

    excel_anterior = AssaiPedidoExcel.query.filter_by(
        separacao_id=sep_alvo.id, ativo=True,
    ).first()
    if excel_anterior:
        excel_anterior.ativo = False  # mantém histórico

    nova_versao = (excel_anterior.versao + 1) if excel_anterior else 1
    bytes_xlsx, s3_key = gerar_excel_qpa(sep_alvo.id, operador_id)

    # CR-9: retry defensivo se IntegrityError no UNIQUE (separacao_id, versao)
    try:
        db.session.add(AssaiPedidoExcel(
            pedido_id=car.pedido_id, separacao_id=sep_alvo.id,
            s3_key=s3_key, versao=nova_versao, ativo=True,
            motivo_regeneracao='Carregamento finalizado',
        ))
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        # Recalcula MAX e tenta de novo (raro com lock acima, mas defensivo)
        nova_versao = db.session.query(
            func.coalesce(func.max(AssaiPedidoExcel.versao), 0) + 1
        ).filter_by(separacao_id=sep_alvo.id).scalar()
        db.session.add(AssaiPedidoExcel(
            pedido_id=car.pedido_id, separacao_id=sep_alvo.id,
            s3_key=s3_key, versao=nova_versao, ativo=True,
            motivo_regeneracao='Carregamento finalizado (retry)',
        ))

    # === FASE 6: atualizar mirror Nacom (D-B) ===
    sincronizar_espelho_com_separacao(sep_alvo.id)

    # === FASE 7: detectar divergência se NF já existe ===
    # S22=a — Carregamento ignora NFs em DIVERGENTE / NAO_RECONCILIADO / CANCELADA.
    # So compara contra NF que esta BATEU (NF tem visao consistente). NFs nao-BATEU
    # permanecem pendentes de resolucao independente (operador resolve no painel
    # /divergencias). Razao: misturar divergencia de Carregamento com divergencia
    # ja existente de NF confunde diagnostico.
    # A3: UNIQUE parcial garante 1 NF ativa por sep — filtra CANCELADA na query.
    nf = (AssaiNfQpa.query
          .filter_by(separacao_id=sep_alvo.id)
          .filter(AssaiNfQpa.status_match != 'CANCELADA')
          .first())
    if nf and nf.status_match == 'BATEU':  # S22=a
        # NF chegou primeiro, agora Carregamento confronta
        chassis_nf = {it.chassi for it in nf.itens}
        chassis_so_car = set(chassis_car) - chassis_nf
        chassis_so_nf = chassis_nf - set(chassis_car)
        houve_divergencia = False
        for c in chassis_so_car:
            criar_divergencia(tipo='CARREGAMENTO_CHASSI_FORA_NF',
                              chassi=c, sep_id=sep_alvo.id,
                              car_id=car.id, nf_id=nf.id)
            houve_divergencia = True
        for c in chassis_so_nf:
            criar_divergencia(tipo='NF_CHASSI_FORA_CARREGAMENTO',
                              chassi=c, sep_id=sep_alvo.id,
                              car_id=car.id, nf_id=nf.id)
            houve_divergencia = True
        # A4: NF.status_match volta de BATEU → DIVERGENTE quando Carregamento gera
        # divergencia posterior. Sep continua FATURADA (nao regrede).
        # Quando divergencia for resolvida (CCe, alterar_carregamento),
        # resolver_divergencia re-roda _calcular_match que pode voltar a BATEU (S21).
        if houve_divergencia:
            nf.status_match = 'DIVERGENTE'

    # === FASE 8: recalcular status pedido (A13 — defensivo) ===
    # Carregamento por si nao muda qtd_faturada, mas se logica futura mudar
    # (ex: sep nasce FATURADA via A11), o status do pedido pode precisar atualizar.
    # Custo zero (idempotente), beneficio: cobertura defensiva.
    recalcular_status_pedido(car.pedido_id)

    db.session.commit()
    return sep_alvo
```

### Exemplo numérico (do usuário)

```
Estado inicial:
  Sep_A: chassis [C1..C10]  ← qtd_planejada = 10
  Sep_B: chassis [C11..C20] ← qtd_planejada = 10
  Pedido: qtd_pedida = 20
  Carregamento: chassis [C1..C5, X1..X10] (15 chassis)

Após finalizar Carregamento:
  Fase 1: Sep_A é alvo (5 chassis em comum: C1..C5)
  Fase 2:
    - Remove C6..C10 da Sep_A → DISPONIVEL (R1.1)
    - Adiciona X1..X10 na Sep_A → SEPARADA + CARREGADA
    - Sep_A agora: [C1..C5, X1..X10] (15 chassis)
  Fase 3:
    - Total = Sep_A(15) + Sep_B(10) = 25 > pedido(20)
    - Excedente = 5
    - Remove 5 mais recentes da Sep_B (LIFO): C16..C20 → DISPONIVEL
    - Sep_B agora: [C11..C15] (5 chassis)
  Fase 4:
    - Sep_A → CARREGADA
    - Sep_B → permanece EM_SEPARACAO
  Fase 5: Excel regenerado (versão 2 ativa, versão 1 inativa)
  Fase 6: Mirror Nacom atualizado
```

### Timing dos eventos (A1 — Hipótese A)

**Eventos de chassi NÃO são emitidos durante o Carregamento aberto.** Estado muda apenas no FINALIZE.

| Ação | Evento emitido? | Estado do chassi |
|---|---|---|
| Escanear chassi (Carregamento `EM_CARREGAMENTO`) | NÃO | continua o anterior (DISPONIVEL/SEPARADA) |
| Cancelar item antes do finalize | NÃO | DELETE de `assai_carregamento_item`, estado intacto |
| Finalizar Carregamento (algoritmo §6) | SIM | Fase 2: SEPARADA (chassis adicionados); Fase 4: CARREGADA (todos) |
| Cancelar Carregamento `FINALIZADO` (S5=b) | NÃO | chassis mantêm SEPARADA (não desfaz adições) |
| Cancelar Carregamento `EM_CARREGAMENTO` | NÃO | nenhuma mudança de estado (DELETE do carregamento + items) |

**Razão**: append-only sem reverso. Carregamento aberto é "lista de intenção".

**Mitigação da percepção do operador**: painel `/carregamento` mostra chassis em carregamentos ABERTOS — operador vê "chassi X está no Carregamento_5 (Operador A, ainda não finalizado)". Lock S3=c impede uso paralelo do chassi.

### Funções e exceptions auxiliares (CR-8 + CR-13 — referência para implementação)

| Símbolo | Definição | Onde implementar |
|---|---|---|
| `count_em_comum(sep, chassis)` | `len(set([it.chassi for it in sep.itens]) & set(chassis))` — conta interseção de chassis | Helper inline em `carregamento_service.py` (Fase 2) |
| `criar_divergencia(tipo, chassi, sep_id, car_id, nf_id, **detalhes)` | INSERT em `assai_divergencia`. Auto-preenche `criada_em`. `tipo` deve estar no CHECK | `services/divergencia_service.py` (Fase 4) |
| `resolver_divergencia(div_id, tipo_resolucao, observacao, operador_id)` | UPDATE `resolvida_em + resolvida_por_id + tipo_resolucao + observacao_resolucao` + re-roda `_calcular_match` na NF (S21) | `services/divergencia_service.py` (Fase 4) |
| `CarregamentoExcedenteError` | Exception nova. Mensagem inclui qtd excedente + lista de seps CARREGADA/FATURADA. Tratamento na route: HTTP 409 + flash explicativo | `services/carregamento_service.py` (Fase 2) |
| `regenerar_excel_qpa(sep_id, operador_id, motivo)` | Wrapper sobre `gerar_excel_qpa` que aplica regra D-C (desativa anterior, cria nova versão com lock CR-12 + retry CR-9) | `services/faturamento_service.py` (extender Fase 4) |
| `remover_nf_do_espelho(sep_id)` | Seta `numero_nf = NULL` em todas linhas do espelho da sep (S11=a) | `services/separacao_mirror_service.py` (Fase 4) |

---

## 7. Divergências (Section 5 detalhe)

### 7.1 Quando criar divergência

| Cenário | Tipo | Quando detecta |
|---|---|---|
| NF chega com chassi não presente em Carregamento finalizado | `NF_CHASSI_FORA_CARREGAMENTO` | `importar_nf_qpa` após Carregamento existir |
| Carregamento finaliza com chassi não presente em NF que já chegou | `CARREGAMENTO_CHASSI_FORA_NF` | `finalizar_carregamento` Fase 7 |
| NF tem chassi sem `assai_moto` (não recebido) | `CHASSI_NAO_CADASTRADO` | `_calcular_match` antes de buscar sep |
| Operador escaneia chassi já em Sep ativa de outra loja | `CHASSI_OUTRA_LOJA` | `registrar_chassi` (sep), `escanear_carregamento_item` (carregamento), ou `ajustar_separacao_pela_nf` (NF antes do match — A7) |

### 7.2 Resoluções (Q13)

| Tipo de resolução | Implementação |
|---|---|
| `CANCELAR_NF` | Chama `cancelar_nf_qpa(nf_id)` (Section 9) |
| `CCE` | Operador faz upload do PDF da Carta de Correção. Parser extrai chassis corrigidos (R3 opção a). Atualiza `AssaiNfQpaItem` e re-roda match |
| `ALTERAR_CARREGAMENTO` | **S6=a — REABRE Carregamento**: status volta `FINALIZADO → EM_CARREGAMENTO`. Operador acessa tela com QR/campo de chassi (Q14). Adiciona/remove chassis. Ao re-finalizar, re-executa Fase 2-6 do algoritmo §6 (sep alvo pode mudar; chassis sao recalculados). Audit trail em `assai_moto_evento` mostra todas as mutacoes. |
| `SUBSTITUIR_CHASSI` | Resolução do tipo `CHASSI_OUTRA_LOJA` (Section 11) |
| `IGNORAR` | Marca divergência como aceita sem ação. Para casos gerenciais |

### 7.2.1 — A8: Validação MODELO_DIVERGENTE em `_calcular_match`

Hoje `_calcular_match` valida apenas chassi + loja + valor. Spec adicionou `MODELO_DIVERGENTE` ao CHECK (S8=a) mas sem callsite. **A8=a — implementar validação**:

```python
def _calcular_match(nf, importada_por_id):
    # A14: idempotente — NF cancelada não bate mais nada
    if nf.status_match == 'CANCELADA':
        return

    for it in nf.itens:
        # ... checks existentes (chassi, loja, valor) ...

        # A8: validar modelo
        moto = AssaiMoto.query.filter_by(chassi=it.chassi).first()
        if moto and it.modelo_extraido:
            modelo_resolvido = resolver_modelo(it.modelo_extraido)  # modelo_resolver existente
            if modelo_resolvido and moto.modelo_id != modelo_resolvido.id:
                criar_divergencia(
                    tipo='MODELO_DIVERGENTE',
                    chassi=it.chassi,
                    sep_id=sep_item.separacao_id if sep_item else None,
                    nf_id=nf.id,
                    detalhes={
                        'modelo_assai_moto_id': moto.modelo_id,
                        'modelo_extraido_nf': it.modelo_extraido,
                        'modelo_resolvido_id': modelo_resolvido.id,
                    }
                )
                matches_falha += 1
                continue
```

`resolver_modelo` reutiliza `app/motos_assai/services/modelo_resolver.py` (3 camadas de match: alias + substring + código exato).

### 7.3 Parser de CCe (R3 opção a)

- Operador acessa divergência tipo `NF_CHASSI_FORA_CARREGAMENTO`
- Botão "Resolver via CCe" → modal de upload PDF
- Parser determinístico tenta extrair: numero_cce, numero_nf_referenciada, chassis novos, chassis removidos
- Fallback LLM (Haiku 4.5 → Sonnet 4.6) se confiança < 0.80
- Atualiza `AssaiNfQpaItem` (substitui chassi antigo pelo novo)
- Re-roda `_calcular_match` na NF
- Marca divergência como resolvida com `tipo_resolucao=CCE`

Spec detalhada do parser CCe: **escopo de Fase 5** (não primeira leva).

### 7.4 — A14: Idempotência em `resolver_divergencia` e `_calcular_match`

S21=a determina que `resolver_divergencia` re-roda `_calcular_match` na NF correspondente. **A14**: ambos serviços precisam tratar NF CANCELADA como no-op (idempotência + proteção contra re-execução acidental):

```python
def resolver_divergencia(div_id, tipo_resolucao, observacao, operador_id):
    div = AssaiDivergencia.query.get(div_id)
    if div.resolvida_em:
        raise ValidationError('Divergência já resolvida')

    div.resolvida_em = now()
    div.resolvida_por_id = operador_id
    div.tipo_resolucao = tipo_resolucao
    div.observacao_resolucao = observacao

    # A14: re-roda match apenas se NF não está CANCELADA
    if div.nf_id:
        nf = AssaiNfQpa.query.get(div.nf_id)
        if nf.status_match != 'CANCELADA':
            _calcular_match(nf, operador_id)

    db.session.commit()


def _calcular_match(nf, importada_por_id):
    # A14: idempotente — NF cancelada não bate mais nada
    if nf.status_match == 'CANCELADA':
        return
    # ... resto do match ...
```

**Razão**: NF cancelada não precisa re-bater (estado terminal). Tentar bater pode levar a re-criar divergências já resolvidas, ou pior, marcar sep como FATURADA quando ela voltou para CARREGADA via cancelamento.

### 7.1.1 — A7: Detecção de CHASSI_OUTRA_LOJA em fluxo NF

`ajustar_separacao_pela_nf` (chamado por `importar_nf_qpa`) deve detectar chassis em sep ativa de outra loja **ANTES** de tentar o ajuste:

```python
def ajustar_separacao_pela_nf(nf_id, operador_id):
    nf = AssaiNfQpa.query.get(nf_id)
    chassis_nf = [it.chassi for it in nf.itens]

    # A7: detectar CHASSI_OUTRA_LOJA antes do ajuste
    chassis_filtrados = []
    for chassi in chassis_nf:
        sep_outra_loja = (
            AssaiSeparacao.query
            .join(AssaiSeparacaoItem)
            .filter(
                AssaiSeparacaoItem.chassi == chassi,
                AssaiSeparacao.status.in_(['EM_SEPARACAO', 'FECHADA', 'CARREGADA', 'FATURADA']),
                AssaiSeparacao.loja_id != nf.loja_id,
            )
            .first()
        )
        if sep_outra_loja:
            criar_divergencia(
                tipo='CHASSI_OUTRA_LOJA',
                chassi=chassi, sep_id=sep_outra_loja.id, nf_id=nf.id,
                detalhes={
                    'loja_atual': sep_outra_loja.loja_id,
                    'loja_nf': nf.loja_id,
                    'sep_status': sep_outra_loja.status,
                }
            )
            # Pula este chassi no ajuste — operador resolve via 'Substituir chassi' (§11)
        else:
            chassis_filtrados.append(chassi)

    # ... ajuste normal apenas com chassis filtrados ...
```

**`LOJA_DIVERGENTE`** (existente em `_calcular_match`) permanece como fallback genérico para casos onde `ajustar` não detectou (ex: sep CANCELADA com chassi em loja errada — não entra no filtro de seps ativas).

---

## 8. Modal Expedição obrigatório

### 8.1 Quando aparece (Q15)

Na importação de NF Q.P.A., **se** a NF NÃO encontra Sep candidata (cenário "NF antes da Sep"):

1. NF é parseada
2. Sistema busca `AssaiSeparacao` candidata via `ajustar_separacao_pela_nf` (lógica atual)
3. Se NÃO encontra **e** todos chassis NF existem em `assai_moto`:
   - Sistema **cria Sep** automaticamente em **`FATURADA`** (S1=b — pula EM_SEPARACAO + FECHADA + CARREGADA)
   - NF imediatamente vira `BATEU` (chassis batem por construção)
   - **Abre modal** exigindo `expedicao` obrigatória + opcionais (Agendamento, Protocolo, agendamento_confirmado)
4. Se operador clica "Pular" OU fecha modal no X: cria Sep mesmo assim, **sem expedição** (Q15 + S7=a — ambos válidos)
4a. **A11 + A9 — ao criar Sep automaticamente em FATURADA**:
    - `fechada_em = now()`, `fechada_por_id = operador_id` (A9 — convenção: operador da NF)
    - Dispara `gerar_excel_qpa(sep.id, operador_id)` + INSERT em `assai_pedido_excel(versao=1, ativo=True, motivo_regeneracao='criada_via_nf_importada')` (A11)
    - Razão: Sendas/Q.P.A. pode pedir Excel auditando a sep mesmo nesse fluxo
5. Se chassis NF mistos (alguns cadastrados, alguns não): **S19=b decidido** (A16):
   - Cria Sep automaticamente em **FATURADA** (S1=b) com **apenas os chassis cadastrados**
   - **NF nasce em DIVERGENTE** (A5=b — `matches_falha > 0` aciona o status)
   - Para cada chassi não cadastrado, cria divergência `CHASSI_NAO_CADASTRADO`
   - Operador resolve via:
     - Cadastrar moto retroativamente (wizard de recebimento) → `resolver_divergencia` re-roda match
     - Solicitar CCe para chassi corrigido → upload PDF + parser
     - Cancelar NF (A4) → tudo volta a estado anterior

### 8.2 Comportamento do modal

- Se `AssaiPedidoVendaLoja.expedicao` já existe para esse (pedido, loja) → **usa o existente, NÃO abre modal** (Q17)
- Senão, abre modal
- Campo `expedicao` salva em `AssaiSeparacao.expedicao` (Q16 — não no cabeçalho)
- Outros 3 campos opcionais (`agendamento`, `protocolo`, `agendamento_confirmado`) também salvam na Sep
- Botão "Confirmar" + "Pular (criar sem expedição)" — ambos válidos
- Fechar modal pelo X (canto superior direito) **equivale a Pular** (S7=a — sep criada sem expedição). Sem distinção entre Pular e X.

### 8.3 UI

- Modal aparece sobreposto à tela de importação de NF (`/motos-assai/faturamento/upload-nf`)
- Após confirmar/pular, redireciona para detalhe da NF criada

### 8.4 — A10: Edição posterior de agendamento (sep sem expedição)

Quando sep nasce sem expedição (operador pulou modal), precisa de UI para preencher depois. **Reaproveitar** modal `#modal-agendamento-loja-<loja_id>` já existente em `pedidos/detalhe.html` (Plano 5).

**Adição**: oferecer botão "Editar agendamento" no card da sep recém-criada em:
- `faturamento/lista_separacoes.html` (linha da sep no painel)
- `nf_detalhe.html` (botão no header da NF)

Botão abre o modal já existente passando `?sep_id=N` para editar override por sep (Plano 5 já suporta).

**Validação obrigatória em Fase 6** (A10): testar fluxo Nacom completo (cotação + embarque) com sep sem expedição. Plano 5 já trata 4 campos como NULLable em `lista_pedidos.html` (mostra "—"). Cotação/embarque podem precisar de expedição para algum filtro/ordenação. Se quebrar, considerar fallback: usar `agendamento` como expedição se NULL.

---

## 9. Cancelamento de NF (D3 + R5)

### 9.1 Service `cancelar_nf_qpa(nf_id, motivo, operador_id)`

```python
def cancelar_nf_qpa(nf_id, motivo, operador_id):
    nf = AssaiNfQpa.query.get_or_404(nf_id)
    if nf.status_match == 'CANCELADA':
        raise ValidationError('NF já cancelada')

    sep = nf.separacao  # via assai_nf_qpa.separacao_id

    # 1. Reverter eventos FATURADA → CARREGADA OU SEPARADA OU DISPONIVEL
    for item in nf.itens:
        chassi = item.chassi
        status_atual = status_efetivo(chassi)
        if status_atual == 'FATURADA':
            # R5.1: respeita CARREGADA se Sep está CARREGADA
            if sep and sep.status == 'FATURADA':
                # Sep volta para CARREGADA (R5.1)
                novo_evento = 'CARREGADA'
            else:
                # Sep não estava CARREGADA (caso NF antes da Sep, sem Carregamento)
                novo_evento = 'SEPARADA'
            emitir_evento(chassi, novo_evento, operador_id,
                          observacao=f'NF {nf.numero} cancelada: {motivo}')

    # 2. Reverter Sep status
    if sep:
        if sep.status == 'FATURADA':
            # Se Sep tem Carregamento associado: volta para CARREGADA (R5.1)
            tem_carregamento = AssaiCarregamento.query.filter_by(
                separacao_id=sep.id, status='FINALIZADO',
            ).first()
            if tem_carregamento:
                sep.status = 'CARREGADA'  # R5.1
            else:
                sep.status = 'FECHADA'  # caso sem carregamento

    # 3. Marcar NF como cancelada
    nf.status_match = 'CANCELADA'
    nf.cancelada_em = now()
    nf.cancelada_por_id = operador_id
    nf.motivo_cancelamento = motivo

    # 4. Remover NF do espelho Nacom — service novo (S11=a)
    from app.motos_assai.services.separacao_mirror_service import remover_nf_do_espelho
    remover_nf_do_espelho(sep.id)

    # 5. Limpar EmbarqueItem.nota_fiscal (S15=a)
    # _calcular_match BATEU propagou numero_nf para EmbarqueItem; cancelar desfaz.
    from app.fretes.models import EmbarqueItem
    EmbarqueItem.query.filter_by(nota_fiscal=nf.numero).update({'nota_fiscal': None})

    # 6. Auditar e limpar vinculo NF-item ↔ Sep-item (S16=c)
    for item in nf.itens:
        if item.separacao_item_id:
            db.session.add(AssaiNfQpaItemVinculoHistorico(
                nf_qpa_item_id=item.id,
                separacao_item_id=item.separacao_item_id,
                motivo='NF_CANCELADA',
                chassi_no_momento=item.chassi,
                registrado_por_id=operador_id,
                detalhes={'nf_id': nf.id, 'motivo_nf': motivo},
            ))
            item.separacao_item_id = None  # FK limpa apos auditoria registrada

    # 7. Recalcular status do pedido (Section 14)
    recalcular_status_pedido(sep.pedido_id)

    db.session.commit()
    return nf
```

### 9.2 Quando "Sep sem Carregamento" tem NF cancelada (R5.2)

R5.2: "Separação sem carregamento não significa que a Sep foi criada pela NF. Mantenha a Sep."

→ Service mantém a Sep (não deleta). Apenas reverte status para `FECHADA` (ou `EM_SEPARACAO` se nunca foi FECHADA). Chassis voltam para `SEPARADA`.

### 9.3 Quando Carregamento existe (R5.3)

R5.3: Sep transiciona para `CARREGADA` quando Carregamento finaliza. Logo, cancelar NF de Sep com Carregamento → Sep volta de `FATURADA` para `CARREGADA` (não `FECHADA`). Carregamento permanece intacto.

### 9.4 Coluna nova em `assai_nf_qpa` (decisão técnica)

Adicionar 3 campos para auditoria:
- `cancelada_em TIMESTAMP`
- `cancelada_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL`
- `motivo_cancelamento TEXT`

---

## 10. Cancelamento de Pedido (R4.1) — ROADMAP FUTURO

Caso raríssimo (palavra do dono). NÃO faz parte da primeira leva.

Quando implementar:
- Service `cancelar_pedido_assai(pedido_id, motivo, operador_id)`
- Desfaz na ordem (R4.1): **saldo planejado → SEPARADO → CARREGADO**, mantendo `FATURADO`
- Pedido pode ser **cancelado parcialmente** — não cancela items já faturados
- Status do pedido vira `CANCELADO`
- Itens não cancelados mantêm fluxo normal

Documentar em PR separado quando for priorizado.

---

## 11. Substituição de chassi entre lojas (Q21)

### 11.1 Cenário 1 — manual (operador escaneia chassi de outra loja)

```
Sep_A (Loja 1, EM_SEPARACAO): tem chassi X
Sep_B (Loja 2, EM_SEPARACAO): operador escaneia chassi X
```

Hoje: `registrar_chassi` valida `status_efetivo(X) == DISPONIVEL`. Como X está em Sep_A (status SEPARADA), rejeita.

Novo: ao invés de erro genérico, sistema detecta `CHASSI_OUTRA_LOJA` e abre **modal** oferecendo:
- **Substituir**: remove X da Sep_A → emite DISPONIVEL → registra na Sep_B → emite SEPARADA
- **Cancelar**: aborta o registro do chassi

### 11.2 Cenário 2 — via NF importada (chassis batem com Sep de outra loja)

NF tem chassi X que está em Sep de outra loja:
- Cria divergência `CHASSI_OUTRA_LOJA`
- Operador resolve via mesma interface (substituir ou cancelar)

### 11.3 Service `substituir_chassi_entre_seps(chassi, sep_origem_id, sep_destino_id, operador_id)`

Move chassi atomicamente entre seps. Algoritmo (S20=a):

```python
def substituir_chassi_entre_seps(chassi, sep_origem_id, sep_destino_id, operador_id):
    # Lock pessimista no chassi
    moto = AssaiMoto.query.filter_by(chassi=chassi).with_for_update().first()
    sep_origem = AssaiSeparacao.query.get(sep_origem_id)
    sep_destino = AssaiSeparacao.query.get(sep_destino_id)

    # Pre-condicoes (CR-11: ampliar para incluir CARREGADA)
    # FATURADA bloqueada (NF ja foi emitida, alteracao requer cancelar NF antes).
    if sep_destino.status not in ('EM_SEPARACAO', 'FECHADA', 'CARREGADA'):
        raise ValidationError(
            f'Sep destino deve estar EM_SEPARACAO, FECHADA ou CARREGADA. '
            f'Estado atual: {sep_destino.status}. '
            f'Para FATURADA, cancele a NF primeiro via cancelar_nf_qpa.'
        )

    # Remove chassi da sep origem
    item_origem = AssaiSeparacaoItem.query.filter_by(
        separacao_id=sep_origem.id, chassi=chassi,
    ).first()
    db.session.delete(item_origem)

    # S20=a — sequencia de eventos: <estado_atual> → DISPONIVEL → SEPARADA
    # Funciona uniformemente para origem em SEPARADA/CARREGADA/FATURADA
    estado_atual = status_efetivo(chassi)
    emitir_evento(chassi, 'DISPONIVEL', operador_id,
                  observacao=f'substituicao cross-loja: {sep_origem.id} → {sep_destino.id}',
                  dados_extras={'sep_origem_id': sep_origem.id, 'estado_anterior': estado_atual})

    # Adiciona chassi na sep destino
    db.session.add(AssaiSeparacaoItem(
        separacao_id=sep_destino.id, chassi=chassi,
        modelo_id=moto.modelo_id, valor_unitario_qpa=item_origem.valor_unitario_qpa,
    ))
    emitir_evento(chassi, 'SEPARADA', operador_id,
                  observacao=f'substituicao cross-loja: vindo de sep {sep_origem.id}',
                  dados_extras={'sep_destino_id': sep_destino.id})

    # Se sep_origem estava CARREGADA, mantem CARREGADA com qtd menor.
    # Se sep_origem estava FATURADA, registra divergencia (chassi removido de NF ja batida).
    # CR-2: tipo correto e CHASSI_OUTRA_LOJA (substituicao cross-loja, nao Carregamento).
    # CR-10: buscar NF via query (AssaiSeparacao nao tem relationship reverse 'nf').
    if sep_origem.status == 'FATURADA':
        nf_origem = AssaiNfQpa.query.filter_by(separacao_id=sep_origem.id).first()
        criar_divergencia(
            tipo='CHASSI_OUTRA_LOJA',
            chassi=chassi, sep_id=sep_origem.id,
            nf_id=nf_origem.id if nf_origem else None,
            detalhes={
                'motivo': 'chassi removido de NF FATURADA por substituicao cross-loja',
                'sep_destino_id': sep_destino.id,
                'loja_origem': sep_origem.loja_id,
                'loja_destino': sep_destino.loja_id,
            }
        )

    # S20 — REGENERAR Excel da sep_origem (chassi a menos)
    regenerar_excel_qpa(sep_origem.id, operador_id,
                       motivo='substituicao cross-loja: chassi removido')

    # Regenerar Excel da sep_destino se ja tinha Excel ativo
    excel_destino = AssaiPedidoExcel.query.filter_by(
        separacao_id=sep_destino.id, ativo=True,
    ).first()
    if excel_destino:
        regenerar_excel_qpa(sep_destino.id, operador_id,
                           motivo='substituicao cross-loja: chassi adicionado')

    # Atualizar espelho Nacom em ambas seps
    sincronizar_espelho_com_separacao(sep_origem.id)
    sincronizar_espelho_com_separacao(sep_destino.id)

    # Recalcular status pedido (S10) — pode mudar se chassi mudou de pedido
    recalcular_status_pedido(sep_origem.pedido_id)
    if sep_destino.pedido_id != sep_origem.pedido_id:
        recalcular_status_pedido(sep_destino.pedido_id)

    db.session.commit()
```

**S20=a — sequencia de eventos definida**:
- `<estado_atual> → DISPONIVEL → SEPARADA` (3 eventos sempre, independente do estado da origem)
- Funciona uniformemente para CARREGADA/SEPARADA/FATURADA na origem
- Audit trail mantido em `assai_moto_evento` com `dados_extras` contendo `estado_anterior` e `sep_origem_id`/`sep_destino_id`

**Excel da sep_origem SEMPRE regenerado** (chassi a menos = Excel desatualizado para Sendas/Q.P.A.). Excel da sep_destino regenerado se ja tinha Excel ativo (chassi a mais).

---

## 12. Excel Q.P.A. — histórico de versões (D-C opção b)

### 12.1 Modelo

Tabela `assai_pedido_excel` armazena cada versão. `ativo=TRUE` apenas no mais recente. Histórico permite auditar "o que foi enviado para Sendas/Q.P.A. no dia X".

### 12.2 Quando regenerar

- Sep vira FECHADA pela primeira vez (versão 1)
- Carregamento finaliza e ajusta Sep (versão N+1)
- Substituição manual de chassi (versão N+1)
- Cancelamento de NF (não regenera — Excel reflete o estado da sep, não da NF)

### 12.3 UI

- `/motos-assai/faturamento` mostra apenas o Excel **ativo** por sep (botão "Excel")
- Detalhe da sep mostra histórico de versões com download
- Detalhe do pedido mostra todos os Excel ativos das seps do pedido

---

## 13. Espelhamento Nacom — `mirror_assai_to_separacao` (D-B opção c)

### 13.1 Quando disparar

- **Inicial**: quando Sep vira `FECHADA` (mantém comportamento atual)
- **Atualização**: quando Sep vira `CARREGADA` (ajuste pelo Carregamento) → chama `sincronizar_espelho_com_separacao` para reconciliar chassis no espelho
- **Atualização**: quando substituição manual de chassi entre seps → mesmo serviço

### 13.2 Caso Sep nasce diretamente em CARREGADA (Q4/Q6) ou FATURADA (S1=b)

Sep que pula estados intermediarios:
- **Q4/Q6** — Carregamento sem Sep prévia: nasce em `CARREGADA`
- **S1=b** — NF antes da Sep: nasce em `FATURADA`

Em ambos os casos: chamar **`mirror_assai_to_separacao` (inicial)** + **`sincronizar_espelho_com_separacao`** (não há linhas antigas a reconciliar, mas o algoritmo é seguro: skip se vazio).

**S12=a — modificar guarda do mirror**: hoje `mirror_assai_to_separacao` aceita apenas sep em `FECHADA`. Modificar para aceitar `(FECHADA, CARREGADA, FATURADA)` na guarda inicial. Razão: o conceito de "espelhar AssaiSep para `separacao` Nacom" é independente do estado — se há chassis a espelhar, espelha.

---

## 14. Status do pedido — transição automática (R4.2)

### 14.1 Service `recalcular_status_pedido(pedido_id)`

```python
def recalcular_status_pedido(pedido_id):
    pedido = AssaiPedidoVenda.query.get(pedido_id)
    if pedido.status == 'CANCELADO':
        return  # status manual, não muda automaticamente

    qtd_pedida = db.session.query(
        func.sum(AssaiPedidoVendaItem.qtd_pedida)
    ).filter_by(pedido_id=pedido_id).scalar() or 0

    qtd_faturada = (
        db.session.query(func.count(AssaiSeparacaoItem.id))
        .join(AssaiSeparacao, AssaiSeparacao.id == AssaiSeparacaoItem.separacao_id)
        .filter(
            AssaiSeparacao.pedido_id == pedido_id,
            AssaiSeparacao.status == 'FATURADA',
        )
        .scalar() or 0
    )

    if qtd_faturada == 0:
        novo_status = 'ABERTO'
    elif qtd_faturada < qtd_pedida:
        novo_status = 'PARCIALMENTE_FATURADO'
    else:
        novo_status = 'FATURADO'

    if pedido.status != novo_status:
        pedido.status = novo_status
        # NOTA: não commita aqui, caller decide
```

### 14.2 Quando chamar (S10=a — todos os callsites)

**Regra geral S10**: `pedido.status = FATURADO` apenas via fluxo de NF (importação BATEU ou cancelamento). Outras operações chamam `recalcular_status_pedido` defensivamente.

Callsites obrigatórios:
- `_calcular_match` BATEU (sep → FATURADA): `recalcular_status_pedido(sep.pedido_id)` — **único caminho que pode SUBIR para FATURADO**
- `cancelar_nf_qpa`: `recalcular_status_pedido(sep.pedido_id)` — único caminho que pode DESCER de FATURADO
- `cancelar_separacao`: `recalcular_status_pedido(sep.pedido_id)` — sep com chassis FATURADA cancelada (rara)
- `substituir_chassi_entre_seps` (§11.3): `recalcular_status_pedido(sep_origem.pedido_id, sep_destino.pedido_id)` — pode mover chassi FATURADA entre pedidos
- `finalizar_carregamento`: defensivo — Carregamento não muda qtd_faturada por si, mas pode mover chassis entre seps
- `alterar_carregamento` (S6=a): defensivo — re-execução do algoritmo §6 pode mover chassis

### 14.3 Migration de dados

Migration 21 backfill: para cada pedido existente, executar `recalcular_status_pedido` para alinhar com o novo regime.

Status atual `EM_PRODUCAO` → migra para `ABERTO` (todos), `SEPARANDO` → `ABERTO` (chassis não foram faturados ainda).

### 14.4 Remoção da atualização `EM_PRODUCAO` (compra_service)

`compra_service.criar_consolidado` hoje atualiza pedido para `EM_PRODUCAO`. **Remover** essa atualização. Pedido fica `ABERTO` até começar a faturar.

Side effect: tela de compras precisa verificar a relação `AssaiCompraMotochefe ↔ Pedido` por outra via (existência de linha em `assai_compra_motochefe_pedido`).

---

## 15. Telas novas (UI)

### 15.1 `/motos-assai/carregamento` — Lista + Iniciar

- Lista carregamentos em andamento (`EM_CARREGAMENTO`) + finalizados recentes
- Botão "Iniciar novo carregamento" → seleção (pedido, loja) → cria `AssaiCarregamento` em `EM_CARREGAMENTO`
- Cards por status

### 15.2 `/motos-assai/carregamento/<id>` — Escanear chassis

- Header: pedido + loja + status
- Input de chassi (QR / barcode / digitar) — padrão dos templates existentes
- Tabela de chassis escaneados (chassi, modelo, cor, hora, operador)
- Botão "Cancelar item" por linha (volta DISPONIVEL)
- Botão "Finalizar carregamento" → executa algoritmo Section 6 → redireciona para detalhe Sep
- Botão "Cancelar carregamento" → motivo obrigatório. **Comportamento depende do status (S5)**:
  - `EM_CARREGAMENTO` (ainda não finalizado): chassis voltam ao **estado anterior** (DISPONIVEL se nunca foram para sep, SEPARADA se já estavam em sep prévia)
  - `FINALIZADO` (S5=b): chassis **mantêm SEPARADA na sep alvo** (não desfaz adições). Sep pode ser cancelada separadamente. Carregamento vira `CANCELADO` apenas como histórico

### 15.3 `/motos-assai/divergencias` — Lista + resolução

- Filtros: pendentes / resolvidas / tipo / data
- Tabela: tipo, chassi, sep, NF, carregamento, criada_em
- Ações por linha (modal):
  - "Cancelar NF" → confirma + chama service
  - "Resolver via CCe" → upload PDF
  - "Alterar Carregamento" → vai para tela de edição do Carregamento
  - "Substituir chassi" → modal de confirmação
  - "Ignorar" → motivo + marca como resolvida

### 15.4 Modal Expedição (na importação NF)

Já descrito em Section 8.

### 15.5 Modal "Substituir chassi entre lojas"

Detalhado em Section 11.

### 15.6 NFs órfãs antigas (S9=c — backfill no deploy)

**Decisão (S9=c)**: as 30 NFs órfãs ATUAIS em prod (importadas antes deste design) são tratadas via **migration de backfill** na Fase 1, NÃO via UI manual.

**Migration 23 (`motos_assai_23_backfill_nfs_orfas`)**:
1. Para cada `assai_nf_qpa` com `status_match='NAO_RECONCILIADO'`:
   - Verifica que loja_id está preenchido
   - Verifica que todos chassis NF existem em `assai_moto`
   - Se ok: invoca `ajustar_separacao_pela_nf` (NOVA lógica — cria Sep automaticamente em FATURADA, S1=b)
   - Sep nasce **SEM expedição** (operador preenche depois via UI de edição se necessário)
   - Se algum chassi não cadastrado: cria divergência `CHASSI_NAO_CADASTRADO` (S19=b — parcial)
2. Loga resultado por NF: `{nf_id, resultado: BATEU|CRIOU_DIVERGENCIA|FALHOU, motivo}`

**UI de vinculação manual** (botão "Vincular" no painel NFs órfãs do `/motos-assai/faturamento`): permanece como ferramenta excepcional para casos que o backfill NÃO resolveu (ex: chassis não cadastrados onde operador precisa decidir manualmente). Spec detalhada: **Fase 5**.

---

## 16. Migrations

| # | Nome | O que faz |
|---|---|---|
| 18 | `motos_assai_18_carregamento` | Cria `assai_carregamento` + `assai_carregamento_item` (sem UNIQUE parcial — S3=c lock pessimista) |
| 19 | `motos_assai_19_divergencia` | Cria `assai_divergencia` com **9 tipos** no CHECK (4 novos + 4 legados de `_calcular_match` + CHASSI_SEM_SEPARACAO) |
| 20 | `motos_assai_20_pedido_excel` | Cria `assai_pedido_excel` com **UNIQUE (separacao_id, versao)** (S13=a) + migra `solicitacao_excel_s3_key` existente |
| 21 | `motos_assai_21_simplificar_status_pedido` | Backfill status pedido + **remover update EM_PRODUCAO em compra_service + Big Bang em todos callsites de status legado** (S17=c) |
| 22 | `motos_assai_22_nf_cancelamento_campos` | Adiciona `cancelada_em / cancelada_por_id / motivo_cancelamento` em `assai_nf_qpa` |
| **23** | `motos_assai_23_backfill_nfs_orfas` | **S9=c** — Para cada NF NAO_RECONCILIADO, invoca nova `ajustar_separacao_pela_nf` (cria Sep em FATURADA sem expedição). Resolve as 30 órfãs em prod no deploy. **CR-4: Python-only** — invoca service de aplicação, **não tem variante `.sql`**. Roda via `python scripts/migrations/motos_assai_23_backfill_nfs_orfas.py`. Pré-requisito: codigo Fase 4 (services novos) já deployado |
| **24** | `motos_assai_24_check_status_aceitar_novos` | Se houver CHECK constraints em `assai_separacao.status`, `assai_nf_qpa.status_match`, `assai_moto_evento.tipo` — ALTER para incluir `CARREGADA` / `CANCELADA` / etc. Se não houver, migration vira no-op documentado |
| **25** | `motos_assai_25_backfill_divergencias_legadas` | **S8=a** — Para cada `assai_nf_qpa_item.tipo_divergencia` não nulo, cria linha em `assai_divergencia` com tipo correspondente (LOJA/VALOR/MODELO_DIVERGENTE, CHASSI_SEM_SEPARACAO) |
| **26** | `motos_assai_26_vinculo_historico` | **S16=c** — Cria `assai_nf_qpa_item_vinculo_historico` |
| **27** | `motos_assai_27_unique_nf_sep_ativa` | **A3** — Cria UNIQUE parcial em `assai_nf_qpa(separacao_id)` WHERE `status_match != 'CANCELADA'`. Garante apenas 1 NF ativa por sep (cenário: NF cancelada + nova NF mesma sep) |

Cada migration tem `.py` (com `create_app`) + `.sql` (idempotente para Render Shell).

**Ordem de execução crítica** (CR-16: Migration 23 fora do bloco Fase 1):

```
Pré-requisitos:  Migration 17 (limpeza Sep 2 órfã, já existente — falta deploy prod)
Fase 1 (deploy 1):  18 → 19 → 20 → 21 → 22 → 24 → 26 → 27 → 25
                    (estruturais + backfills automaticos sem dependência de código Fase 4)
Fase 4 (deploy 2):  ... código Fase 4 (services criar_divergencia, cancelar_nf_qpa,
                    remover_nf_do_espelho, resolver_divergencia, ajustar_separacao_pela_nf v2,
                    validacao MODELO_DIVERGENTE em _calcular_match, deteccao CHASSI_OUTRA_LOJA) ...
                    23 (Python-only, invoca services Fase 4, A15 manual no Render Shell)
```

CR-16: Migration 23 e ultima migration mas roda DEPOIS do deploy de codigo da Fase 4
(nao esta no bloco Fase 1 estruturais).

---

## 17. Plano de implementação por fase

### Pré-requisitos (CR-5)
- **Rodar Migration 17 em Render** (limpeza Sep 2 órfã — corrigida localmente, falta deploy prod)
- Backup do banco antes de iniciar Fase 1
- Verificar permissões de DBA para CHECK constraints (necessário para Migration 24)

### Fase 1 — Fundação (modelo + status)

**1A — Estruturais (DDL)** [CR-3 + A3]:
- Migrations 18, 19, 20, 22, 24, 26, 27 (estruturais, ordem do §16)

**1B — Constantes/models + guards services existentes** [CR-3 + A6]:
- Atualizar `models/separacao.py` (status `CARREGADA`)
- Atualizar `models/nf_qpa.py` (`status_match=CANCELADA` + 3 campos `cancelada_em/por/motivo`)
- Atualizar `models/moto.py` (evento `CARREGADA`)
- Atualizar `models/pedido.py` (4 status: `ABERTO`, `PARCIALMENTE_FATURADO`, `FATURADO`, `CANCELADO`)
- Declarar `CarregamentoExcedenteError` (CR-8)
- **A6 — atualizar guards em services existentes** para tratar status `CARREGADA` com mensagem específica:
  - `disponibilizar_service.disponibilizar()`: ao detectar `status_efetivo == CARREGADA`, raise com msg `"Chassi {X} carregado em Sep #{id}, Carregamento #{cid}. Para reverter, cancele o Carregamento ou substitua o chassi."`
  - `disponibilizar_service.reverter()`: idem
  - `montagem_service.registrar_montagem()`: idem
  - `montagem_service.resolver_pendencia()`: idem
  - **Helper genérico** `_validar_estado_chassi(chassi, estados_permitidos)`: dispatch por status (DISPONIVEL/SEPARADA/CARREGADA/FATURADA) com ação remediadora específica em cada mensagem

**1C — Status pedido (data)** [CR-3]:
- Service `recalcular_status_pedido` (§14.1)
- Migration 21 (backfill: para cada pedido, executar `recalcular_status_pedido`)

**1D — Big Bang status legado (código)** [CR-3 + A18 — TASK SEPARADA da Migration 21]:

  **1D.1 — Pre-flight scan exaustivo (A18)**: gerar lista de TODOS callsites de status legado.
  ```bash
  # Código Python
  grep -rn "EM_PRODUCAO\|SEPARANDO\|FATURADO_PARCIAL" app/motos_assai/

  # Templates Jinja2 (operador pode comparar status em templates)
  grep -rn "EM_PRODUCAO\|SEPARANDO\|FATURADO_PARCIAL" app/templates/motos_assai/

  # JS (raro mas possível — UI dinâmica baseada em status)
  grep -rn "EM_PRODUCAO\|SEPARANDO\|FATURADO_PARCIAL" app/static/motos_assai/

  # Cross-módulo (ex: route financeiro filtrando pedido Assaí)
  grep -rn "status.*=.*'EM_PRODUCAO'\|status.*=.*'SEPARANDO'\|status.*=.*'FATURADO_PARCIAL'" app/

  # Queries SQL inline (raro)
  grep -rn "WHERE.*EM_PRODUCAO\|WHERE.*SEPARANDO" app/
  ```
  Saída esperada: lista de N arquivos × linhas a refatorar.
  Documentar em `docs/superpowers/plans/2026-05-XX-bigbang-callsites.md` (alimenta o writing-plans posterior).

  **1D.2 — Refatorar callsites** identificados em 1D.1:
  - Routes/services: usar constantes novas (`PEDIDO_STATUS_*`)
  - Templates Jinja2: usar `pedido.status_label` ou comparar com constantes
  - Queries inline SQL: revisar onde filtram por status legado

  **1D.3 — PR dedicado** + testes regressão em telas existentes (lista_pedidos, faturamento, compras).

  **1D.4 — Validação final**: rodar `grep` novamente e confirmar zero matches.

**1E — Backfill divergências legadas**:
- Migration 25 (S8=a — `tipo_divergencia` em `assai_nf_qpa_item` → linhas em `assai_divergencia`)

**1F — Validação**:
- Tests unitários das constantes/services
- Smoke test: criar pedido, importar PDF, validar `status=ABERTO`

**Pré-requisito Fase 1 → Fase 2**: callsites de status legado erradicados; Migrations 18-22 + 24-26 aplicadas; código limpo.

### Fase 2 — Carregamento (operação principal)
- Service `carregamento_service.py` (criar, escanear, finalizar, cancelar, alterar)
- Algoritmo Section 6 completo
- Eventos CARREGADA
- Atualizar `cancelar_separacao` para considerar status CARREGADA
- Atualizar mirror Nacom (Section 13)

### Fase 3 — UI Carregamento
- Templates `/carregamento` (lista, escaneio, detalhe)
- JS de escaneio (reusa `chassi_autocomplete.js`)
- Onboarding tour

### Fase 4 — NF + Divergências
- Atualizar `_calcular_match`: ignorar FATURADA (D5) + **gravar divergências em `assai_divergencia`** ao invés de só `tipo_divergencia` no item (S8=a)
- Atualizar `ajustar_separacao_pela_nf`: criar Sep **em FATURADA** (S1=b) + abrir modal Expedição quando NF é primeira
- Service `cancelar_nf_qpa` (com S15: limpar `EmbarqueItem.nota_fiscal`; S16: registrar `vinculo_historico` antes de limpar FK)
- **Service novo `remover_nf_do_espelho(sep_id)`** em `separacao_mirror_service.py` (S11=a): seta `numero_nf=NULL` em todas as linhas do espelho da sep
- Service `criar_divergencia` + detecção automática
- Service `resolver_divergencia` que ao marcar `resolvida_em` re-roda `_calcular_match` da NF (S21=a)
- Migration 23 (backfill NFs órfãs — S9=c). **A15**: NÃO incluir em `build.sh` auto-run. Rodar **manualmente** via Render Shell APÓS deploy bem-sucedido da Fase 4 (todos services novos carregados): `python scripts/migrations/motos_assai_23_backfill_nfs_orfas.py`. Logar resultado por NF (`{nf_id, resultado, motivo}`) em arquivo para auditoria
- Templates `/divergencias` + modais de resolução
- Modal Expedição (S7=a — X = Pular)

### Fase 5 — Auxiliares
- Substituir chassi entre lojas (Section 11)
- Parser CCe (Section 7.3)
- UI vincular NF manualmente (NFs órfãs antigas — Section 15.6)
- Cancelar pedido (Section 10 — roadmap futuro)

### Fase 6 — Validação em prod
- Importar uma NF de teste para validar fluxo NF antes da Sep
- Rodar Carregamento de teste para validar Fase 2
- Validar Migration 23 backfill: contar NFs órfãs restantes (esperado: apenas chassis não cadastrados)
- Smoke test cancelar NF + verificar Sep volta `CARREGADA` + `EmbarqueItem.nota_fiscal` limpo + `vinculo_historico` registrado
- (CR-5: Migration 17 rodada em Pré-requisitos, não Fase 6)
- **A10**: validar UI Nacom (lista_pedidos, cotação, embarque) com sep nascida em FATURADA sem `expedicao`. Plano 5 já trata 4 campos como NULLable, deve mostrar "—". Cotação/embarque podem precisar de expedição — testar caminho feliz e validar bloqueios sensatos. Se quebrar, considerar fallback: usar `agendamento` como expedição se NULL

---

## 18. Open issues / decisões em aberto

**Decisões fechadas pela rodada S1-S22** (revisão pós-spec):

| ID | Decisão | Onde aplicado |
|---|---|---|
| S1 | Sep nasce em FATURADA quando NF chega antes (T3a + T3b) | §3.1, §5.2, §6, §8.1 |
| S2 | Algoritmo §6 Fase 2 tenta realocar antes de DISPONIVEL (R1.3 valido) | §6 |
| S3 | UNIQUE chassi inviável → lock pessimista em assai_moto | §2.1 |
| S5 | Cancelar Carregamento FINALIZADO mantém SEPARADA; ABERTO volta ao estado anterior | §3.2, §15.2 |
| S6 | "Alterar Carregamento" reabre FINALIZADO → EM_CARREGAMENTO | §3.2, §7.2 |
| S7 | X do modal = Pular | §8.2 |
| S8 | Centralizar todos tipos de divergência em `assai_divergencia` (9 tipos) | §2.1, §17 Fase 4, Migration 25 |
| S9 | NFs órfãs em prod resolvidas via Migration 23 (backfill) | §15.6 |
| S10 | `recalcular_status_pedido` em todos os callsites; FATURADO só via NF | §14.2 |
| S11 | Service novo `remover_nf_do_espelho` | §9.1, §17 Fase 4 |
| S12 | `mirror_assai_to_separacao` aceita FECHADA + CARREGADA + FATURADA | §13.2 |
| S13 | UNIQUE (separacao_id, versao) com retry ON CONFLICT | §2.1 |
| S14 | §6 Fase 3 restringe a (EM_SEPARACAO, FECHADA); escala se não cabe | §6 |
| S15 | Cancelar NF limpa `EmbarqueItem.nota_fiscal` | §9.1 |
| S16 | Cancelar NF limpa FK e registra `vinculo_historico` | §2.1, §9.1, Migration 26 |
| S17 | Big Bang em status pedido (atualizar todos callsites Fase 1) | §14.4, §17 Fase 1 |
| S19 | All-or-nothing parcial: cria sep com cadastrados + divergência | §8.1 |
| S21 | Resolver divergência → re-roda `_calcular_match` automaticamente | §17 Fase 4 |

**S18, S20, S22 — fechadas na rodada final**:

| ID | Decisão | Onde aplicado |
|---|---|---|
| S18 | (b) Multiplos Carregamentos por (pedido, loja); cada um cria sep nova se necessario | §4, §6 Fase 1 |
| S20 | (a) Eventos: `<estado_atual> → DISPONIVEL → SEPARADA` + regenerar Excel da origem sempre | §11.3 |
| S22 | (a) Carregamento ignora NFs DIVERGENTE/NAO_RECONCILIADO/CANCELADA | §6 Fase 7 |

**Itens deliberadamente fora desta primeira leva**:
- Cancelamento de pedido (Section 10) — roadmap futuro
- Parser CCe completo (Section 7.3) — Fase 5
- UI vincular NF órfã antiga manual (Section 15.6) — Fase 5 (apenas como ferramenta excepcional)

**Self-review CR-1 a CR-16 aplicado em v1.1** (16 contradições residuais corrigidas).

**Rodada A1-A18 aplicada em v1.2** (18 ajustes do agente revisor externo — ver §19 tabela completa de rastreamento).

**TODAS AS DECISÕES FECHADAS**. Spec pronta para writing-plans.

---

## 19. Decisões aprovadas — rastreamento

| ID | Pergunta | Decisão | Onde no design |
|---|---|---|---|
| D1 | NF antes Sep | (c) cria Sep automaticamente + modal Expedição | §5.2, §8 |
| D2 | Status pedido FATURADO | (b) qtd_faturada == qtd_pedida; status simplificados ABERTO/PARCIALMENTE_FATURADO/FATURADO/CANCELADO | §2.2, §14 |
| D3 | Cancelar NF | (a) service implementa | §9 |
| D4 | Sep pula FECHADA | (a) forçar passagem por FECHADA — **exceto 3 atalhos** (§3.1): Atalho 1 (Q4/Q6 — Sep nasce em CARREGADA via Carregamento), Atalho 2 (S1=b — Sep nasce em FATURADA via NF antes), Atalho 3 (S1=b T3b — Sep existente FECHADA pula CARREGADA via NF que bate) | §3.1 |
| D5 | Dupla vinculação | (a) ignorar FATURADA no match | §4 (Phase 4) |
| D6 | Chassi não cadastrado | mostrar erro evidente | §7.1, §7.2 |
| Q1 | Carregamento | Nova tabela | §2.1 |
| Q2 | Cardinalidade Sep↔Car | 1:1 | §4 |
| Q3 | Vinculação Carregamento↔Sep | A separação; se N seps, match resolve | §6 |
| Q4 | Carregamento sem Sep | Sim, cria Sep automaticamente | §6 |
| Q5 | Match Carregamento↔Sep | Qtd chassis em comum | §6 Fase 1 |
| Q6 | Carregamento sem Sep finaliza | Cria Sep automaticamente | §6 Fase 1 |
| Q7 | Algoritmo finalização | Mesmo de Q3 + chassis sobrantes alocados em outras seps | §6 |
| Q8 | Evento CARREGADA | Sim | §2.2 |
| Q9 | Cancelar Carregamento | Chassi volta SEPARADA | §15.2 |
| Q10 | Carregamento sobrescreve Sep | Sim, ficam iguais | §6 Fase 2 |
| Q11 | Excel regenerado | Sim, armazena no pedido | §12 |
| Q12 | Divergências | Nova tabela | §2.1 |
| Q13 | Parser de resolução | Construído (CCe) | §7.3 |
| Q14 | Alterar Carregamento | QR/campo de chassi | §7.2, §15.2 |
| Q15 | Modal Expedição | Abre na hora; se fechado, cria sem expedição | §8 |
| Q16 | Modal grava em | `AssaiSeparacao.expedicao` | §8.2 |
| Q17 | Cabeçalho existente | Usa, não pergunta | §8.2 |
| Q18 | Status pedido | Só remove (ABERTO/PARCIALMENTE_FATURADO/FATURADO/CANCELADO) | §2.2, §14 |
| Q19 | Status pedido | (idem Q18) | §2.2 |
| Q20 | Chassi diferente | (a) não cadastrado | §7.1 (CHASSI_NAO_CADASTRADO) |
| Q21 | Substituir chassi entre lojas | Ambos cenários | §11 |
| R1.1 | Chassis expulsos | DISPONIVEL | §6 Fase 2 |
| R1.2 | Remover excedente | LIFO (mais recentes) | §6 Fase 3 |
| R1.3 | Sobras | Alocam em seps com saldo | §6 |
| R2 | Excel | FK pedido + sep | §2.1, §12 |
| R3 | Parser CCe | Operador faz upload | §7.3 |
| R4.1 | Cancelar pedido | Roadmap futuro | §10 |
| R4.2 | Status do pedido | ABERTO até começar a faturar | §14.4 |
| R5 | NF cancelada | `status_match='CANCELADA'` | §3.3 |
| R5.1 | NF cancelada + CARREGADA | Sep volta para CARREGADA | §9.1 |
| R5.2 | Sep sem Carregamento | Mantém Sep | §9.2 |
| R5.3 | Sep transiciona CARREGADA | Sim, quando Carregamento finaliza | §3.1 |
| D-A | Pipeline Sep | (b) EM_SEPARACAO → FECHADA → CARREGADA → FATURADA | §3.1 |
| D-B | Mirror Nacom | (c) ambos: FECHADA + CARREGADA | §13 |
| D-C | Histórico Excel | (b) versionado, ativo=TRUE no mais recente | §12 |

### Decisoes da rodada S1-S22 (revisao pos-spec)

| ID | Pergunta | Decisão | Onde no design |
|---|---|---|---|
| S1 | Status sep no cenario "NF antes da sep" | (b) Sep nasce em FATURADA pulando todos estados intermediarios | §3.1, §5.2, §6, §8.1 |
| S2 | R1.3 (sobras realocam) | (b) Algoritmo tenta realocar antes de DISPONIVEL | §6 Fase 2 |
| S3 | UNIQUE chassi-em-carregamento-ativo | (c) lock pessimista em assai_moto, sem UNIQUE no DB | §2.1 |
| S4 | §18 declarada "Nenhuma" mas tinha aberto | Atualizada com decisoes S1-S22 | §18 |
| S5 | Cancelar Carregamento finalizado | (b) Chassi mantem SEPARADA na sep alvo | §3.2, §15.2 |
| S6 | Alterar Carregamento | (a) REABRE: FINALIZADO → EM_CARREGAMENTO | §3.2, §7.2 |
| S7 | Modal Expedicao "fechado" | (a) X = Pular, ambos validos | §8.2 |
| S8 | Tipos divergencia legados (LOJA/VALOR/MODELO) | (a) Centralizar tudo em assai_divergencia (9 tipos) | §2.1, §17 Fase 4, Migration 25 |
| S9 | 30 NFs orfas em prod | (c) Migration 23 backfill no deploy + UI manual excepcional | §15.6, Migration 23 |
| S10 | recalcular_status_pedido callsites | (a) Todos callsites + regra "FATURADO so via NF" | §14.2 |
| S11 | remover_nf_do_espelho | (a) Service novo em separacao_mirror_service.py | §9.1, §17 Fase 4 |
| S12 | mirror_assai_to_separacao aceita CARREGADA | (a) Modificar guarda para (FECHADA, CARREGADA, FATURADA) | §13.2 |
| S13 | Race condition versao Excel | (a) UNIQUE (separacao_id, versao) + ON CONFLICT retry | §2.1 |
| S14 | §6 Fase 3 filtro de seps | (a) Restringir a (EM_SEPARACAO, FECHADA), escalar via flash | §6 Fase 3 |
| S15 | EmbarqueItem.nota_fiscal ao cancelar NF | (a) Sim, limpar | §9.1 |
| S16 | assai_nf_qpa_item.separacao_item_id ao cancelar NF | (c) Tabela auditoria + FK limpa | §2.1, §9.1, Migration 26 |
| S17 | Callsites de pedido.status legado | (c) Big bang Fase 1 | §14.4, §17 Fase 1 |
| S18 | Sep CARREGADA recebe novo Carregamento | (b) Permite — cria sep nova (Migration 13 ja permite N seps) | §4, §6 Fase 1 |
| S19 | All-or-nothing chassis NF | (b) Cria sep com cadastrados + divergencia para nao cadastrados | §8.1 |
| S20 | Substituir chassi cross-loja: eventos | (a) `<atual> → DISPONIVEL → SEPARADA` + regenerar Excel sempre | §11.3 |
| S21 | DIVERGENTE → BATEU trigger | (a) Resolver divergencia re-roda _calcular_match | §17 Fase 4 |
| S22 | Carregamento finaliza com NF nao-BATEU | (a) Ignora NFs DIVERGENTE/NAO_RECONCILIADO/CANCELADA | §6 Fase 7 |

### Self-review v1.1 — contradicoes residuais corrigidas (CR-1..CR-16)

| ID | Contradição | Fix aplicado | Onde |
|---|---|---|---|
| CR-1 | §3.3 diagrama NF mostrava só BATEU→CANCELADA | Diagrama atualizado: cancelar de qualquer estado | §3.3 |
| CR-2 | §11.3 usava `CARREGAMENTO_CHASSI_FORA_NF` para subst. cross-loja | Trocado para `CHASSI_OUTRA_LOJA` | §11.3 |
| CR-3 | Migration 21 misturava DDL/dados com Big Bang código | Separado em 1A-1F (estruturais, models, dados, código, divergências, validação) | §17 Fase 1 |
| CR-4 | Migration 23 sem nota Python-only | Adicionada nota explícita | §16 |
| CR-5 | Migration 17 estava em Fase 6 (pós-implementação) | Movida para Pré-requisitos antes de Fase 1 | §17 Pré-requisitos + Fase 6 |
| CR-6 | §6 Fase 2 comentário sobre SEPARADA+CARREGADA confuso | Refatorado: explica que CARREGADA vem na Fase 4 | §6 Fase 2 |
| CR-7 | §3.4 diagrama pedido sem setas de retorno | Adicionadas setas e explicação | §3.4 |
| CR-8 | `CarregamentoExcedenteError` sem definição | Adicionada à tabela auxiliar pós-§6 | §6 (auxiliares) |
| CR-9 | §6 Fase 5 não tratava IntegrityError do UNIQUE versão | Adicionado retry defensivo | §6 Fase 5 |
| CR-10 | §11.3 usava `sep_origem.nf` (relationship inexistente) | Trocado por query explícita | §11.3 |
| CR-11 | §11.3 sep_destino só (EM_SEPARACAO, FECHADA) | Ampliado para incluir CARREGADA | §11.3 |
| CR-12 | Race em `ativo=TRUE` UNIQUE parcial | Adicionado `with_for_update` na sep antes da regeneração | §6 Fase 5 |
| CR-13 | `count_em_comum` e `criar_divergencia` sem signature | Tabela auxiliar pós-§6 com 6 helpers definidos | §6 (auxiliares) |
| CR-14 | Falta versionamento da spec | Adicionado "v1.1" no header + lista S1-S22 | header |
| CR-15 | §18 "TODAS DECISOES FECHADAS" antes de §19 | Adicionada nota referenciando §19 | §18 |
| CR-16 | Migration 23 fora da ordem em Fase 1 sem nota | Diagrama de ordem agora separa Pré-req / Fase 1 / Fase 4 | §16 |

### Decisões da rodada A1-A18 (revisão pós-v1.1, agente revisor externo)

| ID | Pergunta | Decisão | Onde no design |
|---|---|---|---|
| A1 | Timing dos eventos durante o Carregamento | (Hipótese A) Escanear NÃO emite evento; estado muda no FINALIZE | §6 (timing dos eventos) |
| A2 | UNIQUE de carregamento ativo bloqueia 2 caminhões | Remover UNIQUE; lock pessimista por chassi (S3=c) já cobre | §2.1 |
| A3 | UNIQUE em `assai_nf_qpa.separacao_id`? | (a) UNIQUE parcial WHERE `status_match != 'CANCELADA'` (Migration 27) | §2.2 |
| A4 | NF BATEU re-avaliada após Carregamento gera divergência | (b) BATEU → DIVERGENTE; sep continua FATURADA | §6 Fase 7, §3.3 |
| A5 | NF parcial (S19=b) → status_match qual? | (b) DIVERGENTE | §8.1 |
| A6 | Services existentes + estado CARREGADA | (b) Bloqueio com mensagem específica indicando sep/carregamento | §17 Fase 1B |
| A7 | CHASSI_OUTRA_LOJA detectado quando? | Em `ajustar_separacao_pela_nf` antes do match | §7.1.1 |
| A8 | MODELO_DIVERGENTE no CHECK sem callsite | (a) Implementar validação em `_calcular_match` | §7.2.1 |
| A9 | Sep nascida em FATURADA/CARREGADA: `fechada_em`/`por_id`? | `operador_id` do evento criador (NF/Carregamento) | §6 Fase 1, §8.1 |
| A10 | Mirror Nacom + sep sem `expedicao` | Validar UI em Fase 6 + botão "Editar agendamento" reaproveitando modal Plano 5 | §8.4, §17 Fase 6 |
| A11 | Sep nascida em FATURADA gera Excel? | Sim, versão 1 ao criar | §8.1 |
| A12 | `tipo_divergencia` em `assai_nf_qpa_item`: deprecia? | (b) Depreciar (NULL após Fase 4); roadmap drop coluna | §2.2 |
| A13 | `recalcular_status_pedido` em `finalizar_carregamento`? | Sim, defensivo (Fase 8 do algoritmo) | §6 Fase 8 |
| A14 | `_calcular_match` em re-execução pega NFs CANCELADA? | Filtrar `status_match != 'CANCELADA'` + early return idempotente | §7.4 |
| A15 | Migration 23: migration ou pós-deploy job? | (b) Python-only com `create_app()`; rodar manual via Render Shell | §17 Fase 4 |
| A16 | §8.1 ponto 5 ainda dizia "PENDENTE S19" | Atualizado: S19=b decidido | §8.1 |
| A17 | §19 row D4 desatualizada | Atualizada com 3 atalhos (Q4 + S1=b + Atalho 3) | §19 |
| A18 | Big Bang sem lista de callsites | Pre-flight scan exaustivo (1D.1) com escopo estendido | §17 Fase 1D |

---

## 20. Referências

- Spec original do módulo: `2026-05-07-motos-assai-design.md`
- Spec recibo + recebimento: `2026-05-07-motos-assai-recibo-recebimento.md`
- Spec saída + faturamento (Plano 4): `2026-05-07-motos-assai-saida-polish.md`
- Spec integração lista_pedidos (Plano 5): `2026-05-12-motos-assai-pedido-loja-plano-design.md`
- Migration 17 (cleanup Sep 2 órfã): `scripts/migrations/motos_assai_17_cleanup_sep_2_orfa.{py,sql}`
- CLAUDE.md do módulo: `app/motos_assai/CLAUDE.md`

## Contexto

_A completar (PAD-A Onda 4)._
