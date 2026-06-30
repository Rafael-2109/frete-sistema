<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/superpowers/specs/INDEX.md
superseded_by: —
atualizado: 2026-06-30
-->
# Motos Assaí — Estoque de Peças + Pendência Categorizada (Spec 1: back-end)

> **Papel:** desenho de dados e serviços (back-end) para ampliar o "meio" do processo de pendência do módulo Motos Assaí — categorização, origem e tratativa da pendência — e introduzir a entidade de **Estoque de Peças** com movimentação rastreável. UI fica para o **Spec 2**.

## Indice

- [Contexto](#contexto)
  - [1.1 Problema](#11-problema)
  - [1.2 Estado atual (verificado no código)](#12-estado-atual-verificado-no-código)
  - [1.3 Escopo do Spec 1 vs Spec 2](#13-escopo-do-spec-1-vs-spec-2)
- [2. Decisões aprovadas (Q&A com o dono)](#2-decisões-aprovadas-qa-com-o-dono)
- [3. Princípio arquitetural](#3-princípio-arquitetural)
- [4. Modelo de dados (6 tabelas novas)](#4-modelo-de-dados-6-tabelas-novas)
- [5. Taxonomia (SETs Python)](#5-taxonomia-sets-python)
- [6. Ciclo de vida da pendência (duas fases) + acoplamento com o evento](#6-ciclo-de-vida-da-pendência-duas-fases-acoplamento-com-o-evento)
- [7. Matriz tratativa → efeito](#7-matriz-tratativa-efeito)
- [8. Custeio e receita](#8-custeio-e-receita)
- [9. Pontos de integração](#9-pontos-de-integração)
- [10. Compatibilidade e caminho de escrita](#10-compatibilidade-e-caminho-de-escrita)
- [11. Camada de serviços](#11-camada-de-serviços)
- [12. Migração, registro e backfill](#12-migração-registro-e-backfill)
- [13. Pré-mortem (riscos + mitigação)](#13-pré-mortem-riscos-mitigação)
- [14. Decisões da revisão + ainda em aberto](#14-decisões-da-revisão-ainda-em-aberto)
- [15. Fora de escopo (Spec 2)](#15-fora-de-escopo-spec-2)
- [16. Referências](#16-referências)

---

## Contexto

Spec 1 do trabalho "Pendências + Estoque de Peças" no módulo Motos Assaí. Amplia o **meio** do processo de pendência (categoria + origem + tratativa) e cria a entidade de **Estoque de Peças** com movimentação rastreável como elo central. Este documento é só o back-end (modelo de dados + serviços); a UI é o Spec 2. Foi validado seção a seção com o dono (ver §2) e endurecido por crítica adversarial em 3 lentes (cobertura de requisito, consistência interna, aderência ao código).

### 1.1 Problema

Hoje uma pendência de moto **nasce e é "resolvida" só com uma descrição em texto livre**. O dono precisa ampliar o **meio** desse processo com quatro dimensões:

- **(A) Categoria**: `AVARIA`, `FALTA_PECA`, `REVISAO`, `VENDA`.
- **(C) Origem**: `GALPAO`, `TRANSPORTE`, `POS_VENDA_CLIENTE`, `POS_VENDA_LOJA` (+ `DEVOLUCAO`, ver §14 R1).
- **(B) Tratativa** de resolução: usar peça do estoque, usar peça de outra moto (canibalização, transferindo a falta), consertar; e a **provisão** de peça (pedido de compra/garantia à Motochefe) como passo paralelo.
- **(D) Estoque de Peças**: recebimento manual (sem NF), custeio, movimentação rastreável e pedido de compra (GARANTIA/COMPRA). A **movimentação de estoque é o elo central** de toda tratativa que envolve peça.

### 1.2 Estado atual (verificado no código)

- **Pendência não é entidade.** É um evento `assai_moto_evento` com `tipo='PENDENTE'` (`app/motos_assai/models/moto.py:57-71`). O estado da moto = seu último evento. A descrição vive em `observacao` (Text) + `dados_extras['descricao']` (JSONB); o doador em `dados_extras['chassi_doador']`.
- **Resolução** = dois eventos novos (`PENDENCIA_RESOLVIDA` → `MONTADA`) emitidos por `montagem_service.resolver_pendencia` (commita internamente, `montagem_service.py:139`); a rota `POST /pendencias/resolver` (`routes/pendencias.py:101-122`) chama **por `chassi`** e **não** commita. A tela de histórico (`pendencia_service.listar_historico_resolvidas`) conta cada evento `PENDENCIA_RESOLVIDA` como uma resolução, pareando por heurística à `PENDENTE` anterior do mesmo chassi.
- **3 origens informais** de `PENDENTE` já existem (`registrar_montagem` `montagem_service.py:94`, `enviar_para_pendencia` `:239`, `devolucao_service.py:197-208` — esta com FK forte `assai_devolucao_item.evento_pendencia_id → assai_moto_evento.id`).
- **Estoque de peças / peça / avaria não existem** (greenfield total). `avaria_fisica` é só um bool no wizard de recebimento que gera `AssaiDivergencia(tipo=AVARIA_FISICA)`; `assai_avaria` é apenas roadmap.
- **Pós-venda** (`AssaiPosVendaOcorrencia`) é uma ilha: log textual de ocorrências `LOJA`/`CLIENTE` em motos **já vendidas** (gate `chassi_foi_vendido`), sem tocar eventos/estoque/estado.
- **Moldes reusáveis** (a forma, não a tabela): `AssaiDivergencia` (tipo+resolução por set Python, `detalhes` JSONB, status derivado de `resolvida_em`, `criar_*` faz add+flush sem commit, `resolver_*` idempotente); `AssaiCompraMotochefe` (numeração `MA-AAAA-NNNN`, status default ABERTA, cabeçalho+N:N).
- **`pg_advisory_xact_lock`** já tem precedente no projeto (`app/cotacao/routes.py:2019`). O pipeline de motos serializa por `with_for_update(of=AssaiMoto)` (lock de linha) — que **não cruza** com advisory lock (ver §13.10).
- **Convenções**: prefixo `assai_`; `chassi` é `String(50)` indexado **por valor** (sem FK para `assai_moto`); timezone `agora_brasil_naive`; JSONB sempre via `sanitize_for_json`; CHECK só no banco (migration), nunca no model; tabela nova = model + `models/__init__.py` + migration `NN` (próxima = **34**) + schema JSON auto-gerado.

### 1.3 Escopo do Spec 1 vs Spec 2

| | Spec 1 (este) | Spec 2 (próximo) |
|---|---|---|
| **Conteúdo** | 6 tabelas + models + migration 34 + camada de serviços + acoplamento evento↔ficha + religação de compatibilidade + ganchos de integração (nível de serviço) + **shim** de retrocompatibilidade do resolver + backfill | Telas (cadastro de peça, estoque/saldo, recebimento manual de peças, tela de pendência categorizada com ramos de tratativa, botão "gerar pendência" em pós-venda, telas de pedido de compra) + reescrita da rota de resolução para `pendencia_id` + menu |
| **Critério** | tudo testável sem tela (pytest); **nada de prod quebra** durante o gap Spec 1→Spec 2 | tudo que precisa de HTML/JS/rota de UI |

---

## 2. Decisões aprovadas (Q&A com o dono)

| ID | Decisão | Consequência no modelo |
|----|---------|------------------------|
| **D1** | Uma moto pode ter **N pendências simultâneas**; REVISÃO gera filhas; chassi fica PENDENTE até a última fechar. | Entidade `assai_pendencia` com `pendencia_pai_id` (auto-relação). 1 evento `PENDENTE` compartilhado por chassi. |
| **D2** | Pendência de **pós-venda não muda o estado** da moto (segue FATURADA). O evento `PENDENTE` só é emitido por pendência **física** (origem em `ORIGENS_FISICAS`, ou retorno físico) — ver §6. | `assai_pendencia.evento_pendente_id` **nullable** (NULL = não afeta o estado da moto). |
| **D3** | Catálogo de peças **com compatibilidade por modelo**. | `assai_peca` + `assai_peca_modelo` (N:N). |
| **D4** | Back-end (Estoque + Pendência) num spec; UI noutro. | Este = Spec 1. |
| **O1** | Moto **devolvida** que termina a REVISÃO → **MONTADA**. | Resolver emite `MONTADA` ao fechar a última ficha física. |
| **O2** | Retorno físico **nem sempre tem NFd**. | Coluna explícita `retorno_fisico` (Boolean) em `assai_pendencia`; entra no predicado `afeta_estado_moto`. |
| **O3** | Compra de peça é **documento único com itens**; **GARANTIA/COMPRA no cabeçalho**. | `assai_peca_compra` (cabeçalho, `tipo`) + `assai_peca_compra_item`. |
| **O4** | Peça canibalizada entra com **custo zero**; o custo real "viaja" via a **FALTA_PECA aberta na moto doadora**. | Movimento `CANIBALIZACAO` com `custo_unitario=0`; abertura automática de FALTA_PECA no doador. |
| **E1** | Pendência **resolvida 1:1 com a ficha** (cada resolução carrega a sua informação, inclusive a troca de peça). | Resolução mora na ficha (`resolvida_em`, `tratativa`, `resolucao_descricao`) + linhas do ledger ligadas (`pendencia_id`). O evento `PENDENCIA_RESOLVIDA` deixa de ser fonte de dado e vira marcador mecânico. |
| **E2** | Pós-venda **gera pendência** neste projeto (item C). | Gancho de serviço `abrir_pendencia(origem=POS_VENDA_*, pos_venda_ocorrencia_id=...)`. |

---

## 3. Princípio arquitetural

**O evento da moto continua sendo a verdade do estado físico; a ficha de pendência é a verdade do tratamento; o ledger é a verdade da peça.**

- **Evento `PENDENTE`** (já existe): 1 por chassi. Interruptor físico — "esta moto está travada?". Lido pelo dashboard, resumo, gate de disponibilizar, contagem de estoque. **Não muda de forma.**
- **`assai_pendencia`** (nova): N por chassi. Cada ficha = um problema categorizado com sua tratativa e sua resolução (1:1, decisão E1).
- **`assai_estoque_movimento`** (nova): ledger append-only. Toda peça que entra, sai, é canibalizada, descartada ou ajustada vira uma linha; é o elo que carrega custo, receita e rastreabilidade (uso, compra, recebimento, troca, venda).

Divisão de papéis garante que **nada do pipeline existente quebra** (o evento permanece) e que o "meio" do processo ganha a riqueza pedida (a ficha + o ledger).

---

## 4. Modelo de dados (6 tabelas novas)

Convenções: imports `from app import db`, `from app.utils.timezone import agora_brasil_naive`, `from sqlalchemy.dialects.postgresql import JSONB`; auditoria `*_em`/`*_por_id` (FK `usuarios.id` `ondelete='SET NULL'`); `chassi*` é `String(50)` **por valor** (sem FK); validação de `tipo`/`categoria`/`status` por **set Python no service** (sem CHECK no banco, molde Divergência/Compra). `ck_assai_moto_evento_tipo` permanece **intocado**.

### 4.1 `assai_peca` — catálogo

`id` Int PK · `codigo` String(40) nullable index · `nome` String(120) not null · `custo_referencia` Numeric(15,4) nullable (informativo; sugestão na entrada manual e **fallback** do custo médio quando saldo zero, §8) · `ativo` Boolean not null default True · `criado_em` DateTime not null · `criado_por_id` FK usuarios SET NULL · `dados_extras` JSONB default dict.

### 4.2 `assai_peca_modelo` — compatibilidade N:N

Molde `AssaiCompraMotochefePedido`. `id` Int PK · `peca_id` FK `assai_peca` CASCADE not null · `modelo_id` FK `assai_modelo` CASCADE not null · `UniqueConstraint('peca_id','modelo_id', name='uq_assai_peca_modelo')`.

### 4.3 `assai_pendencia` — a ficha categorizada

Molde `AssaiDivergencia`.

| Campo | Tipo | Constraints / função |
|---|---|---|
| `id` | Integer | PK |
| `chassi` | String(50) | not null, index (por valor) |
| `categoria` | String(20) | not null — `PENDENCIA_CATEGORIAS_VALIDAS` (inclui sentinela `INDETERMINADA`, §5/§14 R2) |
| `origem` | String(20) | not null — `PENDENCIA_ORIGENS_VALIDAS` (inclui `DEVOLUCAO`, §5/§14 R1) |
| `tratativa` | String(40) | nullable — `PENDENCIA_TRATATIVAS_VALIDAS`; registra a **ação que RESOLVE** a ficha (preenchida na resolução). O **provisionamento** (pedido de compra/garantia) é objeto à parte (§4.5) ligado por `pendencia_id`, refletido em `fase=AGUARDANDO_PECA` — não é uma `tratativa`. |
| `fase` | String(20) | not null, default `'ABERTA'` — `PENDENCIA_FASES_VALIDAS`; informativa (ABERTA/EM_TRATATIVA/AGUARDANDO_PECA); **nunca decide lógica de estado da moto** |
| `retorno_fisico` | Boolean | not null, default False (O2) |
| `descricao` | Text | not null — descrição do problema (≥3 chars) |
| `pendencia_pai_id` | Integer | FK self SET NULL — D1, só REVISÃO→filha **do mesmo chassi**; a filha **herda `origem` e `evento_pendente_id` da mãe** |
| `evento_pendente_id` | Integer | FK `assai_moto_evento.id` SET NULL, **nullable** — NULL ⇔ a ficha **não afeta o estado da moto** (pós-venda sem retorno físico) |
| `peca_id` | Integer | FK `assai_peca.id` SET NULL, nullable |
| `chassi_doador` | String(50) | nullable — moto que cedeu a peça (tratativa USAR_OUTRA_MOTO) |
| `devolucao_item_id` | Integer | FK `assai_devolucao_item.id` SET NULL |
| `pos_venda_ocorrencia_id` | Integer | FK `assai_pos_venda_ocorrencia.id` SET NULL |
| `divergencia_origem_id` | Integer | FK `assai_divergencia.id` SET NULL |
| `detalhes` | JSONB | default dict — árvore de decisão da AVARIA (`{"avaria":{"conserto_viavel":bool,"decisao":"CONSERTAR|TROCAR","garantia":bool,"repor_estoque":bool}}`), `legacy_backfill`, `canibalizado_para`, etc. |
| `aberta_em` | DateTime | not null, default `agora_brasil_naive` |
| `aberta_por_id` | Integer | FK usuarios SET NULL |
| `resolvida_em` | DateTime | nullable |
| `resolvida_por_id` | Integer | FK usuarios SET NULL |
| `resolucao_descricao` | Text | nullable — texto da resolução (E1, 1:1 com a ficha) |
| `cancelada_em` | DateTime | nullable |
| `cancelada_por_id` | Integer | FK usuarios SET NULL |

- **Status derivado**: `aberta` ⇔ `resolvida_em IS NULL AND cancelada_em IS NULL`.
- Índice parcial: `CREATE INDEX ix_assai_pendencia_aberta ON assai_pendencia(chassi) WHERE resolvida_em IS NULL AND cancelada_em IS NULL;`
- Relationship `pai`/`filhas` (auto-relação, `remote_side=[id]`).

### 4.4 `assai_estoque_movimento` — o ledger (elo)

Append-only; entidade de **peça** — não toca a máquina de estados do chassi.

`id` BigInt PK · `peca_id` FK `assai_peca` **RESTRICT** not null index · `tipo` String(40) not null (`MOVIMENTO_TIPOS_VALIDOS`) · `quantidade` Numeric(15,3) not null (magnitude >0) · `delta_almoxarifado` Numeric(15,3) not null default 0 (impacto **assinado**; **0 = canibalização**) · `chassi_origem` String(50) nullable index · `chassi_destino` String(50) nullable index · `pendencia_id` FK `assai_pendencia` SET NULL nullable index · `compra_item_id` FK `assai_peca_compra_item` SET NULL nullable · `custo_unitario` Numeric(15,4) nullable (congelado) · `custo_total` Numeric(15,2) nullable · `receita_unitaria` Numeric(15,4) nullable (só categoria=VENDA) · `receita_total` Numeric(15,2) nullable · `operador_id` FK usuarios SET NULL · `ocorrido_em` DateTime not null default `agora_brasil_naive` · `observacao` Text nullable · `dados_extras` JSONB default dict (`recebimento_ref`, `custo_estimado`…).

- Append-only; correção = nova linha `AJUSTE`. **Saldo** = `SUM(delta_almoxarifado)` por `peca_id`.

### 4.5 `assai_peca_compra` — pedido de compra (cabeçalho)

Molde `AssaiCompraMotochefe`. **`tipo` no cabeçalho** (O3).

`id` Int PK · `numero` String(20) UNIQUE not null (`'PC-AAAA-NNNN'`) · `tipo` String(20) not null (`COMPRA_PECA_TIPOS_VALIDOS`) · `status` String(30) not null default `'ABERTA'` (`COMPRA_PECA_STATUS_VALIDOS`) · `fornecedor` String(120) not null default `'MOTOCHEFE'` · `criada_em` DateTime not null · `criada_por_id` FK usuarios SET NULL · `observacao` Text nullable · `dados_extras` JSONB default dict. Relationship `itens` (cascade `all, delete-orphan`, `lazy='selectin'`).

### 4.6 `assai_peca_compra_item` — itens do pedido

`id` Int PK · `compra_id` FK `assai_peca_compra` CASCADE not null index · `peca_id` FK `assai_peca` RESTRICT not null · `quantidade` Numeric(15,3) not null · `quantidade_recebida` Numeric(15,3) not null default 0 · `custo_estimado` Numeric(15,4) nullable · `pendencia_id` FK `assai_pendencia` SET NULL nullable (a pendência que motivou **este** item) · `criado_em` DateTime not null.

Receber um item → linha `ENTRADA` no ledger (`compra_item_id`); `quantidade_recebida += recebido`; `status` do cabeçalho recalcula `ABERTA → PARCIAL → RECEBIDA`.

---

## 5. Taxonomia (SETs Python)

```python
# assai_pendencia
PENDENCIA_CATEGORIAS_VALIDAS = {'AVARIA','FALTA_PECA','REVISAO','VENDA','INDETERMINADA'}
# INDETERMINADA = sentinela transitória (backfill legado + montagem/enviar antes da UI de
#   classificação do Spec 2). NÃO é uma categoria de negócio; a UI do Spec 2 reclassifica.

PENDENCIA_ORIGENS_VALIDAS = {'GALPAO','TRANSPORTE','POS_VENDA_CLIENTE','POS_VENDA_LOJA','DEVOLUCAO'}
ORIGENS_FISICAS           = {'GALPAO','TRANSPORTE','DEVOLUCAO'}   # afetam o estado da moto
# DEVOLUCAO (§14 R1) = a moto retornou fisicamente via NFd; toda REVISÃO de devolução usa esta origem.

PENDENCIA_FASES_VALIDAS = {'ABERTA','EM_TRATATIVA','AGUARDANDO_PECA'}   # informativa

# tratativa = AÇÃO QUE RESOLVE a ficha (não inclui o provisionamento)
PENDENCIA_TRATATIVAS_VALIDAS = {'USAR_ESTOQUE','USAR_OUTRA_MOTO','CONSERTAR','REVISAR'}
#   USAR_ESTOQUE   -> CONSUMO (inclui aplicar peça já recebida de uma compra/garantia)
#   USAR_OUTRA_MOTO-> CANIBALIZACAO (+ abre FALTA_PECA no doador)
#   CONSERTAR / REVISAR -> sem movimento de estoque
# Provisão (pedir à Motochefe) NÃO é tratativa: é assai_peca_compra (tipo GARANTIA/COMPRA)
#   ligada por pendencia_id, criada por solicitar_compra() — seta fase=AGUARDANDO_PECA, não resolve.

# assai_estoque_movimento
MOVIMENTO_TIPOS_VALIDOS = {'ENTRADA','CONSUMO','CANIBALIZACAO','DESCARTE','AJUSTE'}

# assai_peca_compra
COMPRA_PECA_TIPOS_VALIDOS  = {'GARANTIA','COMPRA'}
COMPRA_PECA_STATUS_VALIDOS = {'ABERTA','PARCIAL','RECEBIDA','CANCELADA'}
```

(Cada constante literal `PENDENCIA_CATEGORIA_*`, `PENDENCIA_ORIGEM_*`, etc. é declarada individualmente no model, espelhando `divergencia.py`.)

| tipo movimento | `quantidade` | `delta_almoxarifado` | afeta saldo? | receita? |
|---|---|---|---|---|
| `ENTRADA` | + | `+qtd` | sim | – |
| `CONSUMO` | qtd | `−qtd` | sim | iff categoria=VENDA |
| `CANIBALIZACAO` | qtd | **0** | **não** | iff categoria=VENDA |
| `DESCARTE` | qtd | `−qtd` (baixa de saldo) / `0` (peça avariada removida de moto, que nunca foi saldo) | sim/não | – |
| `AJUSTE` | qtd | `±qtd` | sim | – |

---

## 6. Ciclo de vida da pendência (duas fases) + acoplamento com o evento

A ficha tem **duas fases distintas de serviço**, que a crítica mostrou serem necessárias (não dá para "escolher tratativa" e "resolver" no mesmo passo quando se pede peça e aplica depois):

```
abrir_pendencia ──▶ [opcional] solicitar_compra (fase=AGUARDANDO_PECA, NÃO resolve)
                ──▶ resolver_pendencia (tratativa final + movimento + fecha)
                └─▶ cancelar_pendencia (fecha sem resolver)
```

**Predicado físico** (derivado, não-coluna):

```python
def afeta_estado_moto(p) -> bool:
    return (p.origem in ORIGENS_FISICAS) or (p.devolucao_item_id is not None) or p.retorno_fisico
```

Com `DEVOLUCAO ∈ ORIGENS_FISICAS`, toda REVISÃO de devolução é física pela própria origem (não depende mais só do override por `devolucao_item_id`). Pós-venda puro (`POS_VENDA_*`, `retorno_fisico=False`) → não físico.

**Toda emissão/consulta de PENDENTE roda sob `pg_advisory_xact_lock(hashtext(chassi))`** e **exclusivamente** via `_get_or_emit_pendente_event` (os 3 emissores legados — `registrar_montagem`, `enviar_para_pendencia`, `criar_devolucao` — passam a chamar o helper; nenhum emite PENDENTE "na mão").

**`abrir_pendencia(*, chassi, categoria, origem, descricao, operador_id, retorno_fisico=False, evento_pendente_id=None, peca_id=None, pendencia_pai_id=None, devolucao_item_id=None, pos_venda_ocorrencia_id=None, divergencia_origem_id=None, detalhes=None)`**:
1. cria a ficha (flush, sem commit);
2. se `evento_pendente_id` foi **passado explicitamente** (caso dos 3 emissores legados, que já emitiram o PENDENTE): usa-o direto e **pula** `_get_or_emit_pendente_event` (evita 2º PENDENTE);
3. senão, se `afeta_estado_moto(ficha)` → `_get_or_emit_pendente_event(chassi)` (reusa o evento se já há ficha física aberta no chassi; senão emite e grava o id) — **N físicas = 1 evento (D1)**;
4. senão (não físico) → `evento_pendente_id = NULL`, sem evento.

**`solicitar_compra(*, pendencia_id, tipo, itens, operador_id, fornecedor='MOTOCHEFE')`** (provisão): cria/anexa `assai_peca_compra` (cabeçalho `tipo`) + `assai_peca_compra_item(pendencia_id)`; seta `fase=AGUARDANDO_PECA`; **não** grava `resolvida_em`. Usado pelo "pedir à Motochefe / garantia". Recebimento posterior do item alimenta o estoque (`ENTRADA`), e a aplicação da peça recebida é uma resolução `USAR_ESTOQUE`.

**`resolver_pendencia(*, pendencia_id, tratativa, resolucao_descricao, operador_id, **kwargs_da_tratativa)`** (substitui a lógica de `montagem_service.resolver_pendencia`):
1. guard idempotente (já resolvida/cancelada → no-op);
2. grava `resolvida_em`, `resolvida_por_id`, `tratativa`, `resolucao_descricao` (E1) + executa o movimento da tratativa (§7);
3. **se a ficha é física**, conta as **outras** físicas abertas do chassi (sob lock): `>0` → não emite evento (chassi segue PENDENTE); `==0` → emite `PENDENCIA_RESOLVIDA` (marcador) + `MONTADA` (O1);
4. ficha não-física → nunca emite evento de moto.

> **Estado-alvo = MONTADA** em toda resolução física (O1). Para uma moto **vendida que retornou fisicamente** (`retorno_fisico=True`), isso significa que ela **re-entra no estoque como MONTADA** (a NF original permanece como registro histórico; sem dupla contagem, pois o estado é o último evento). (R4 confirmado: estado-alvo físico é sempre MONTADA.)

**`cancelar_pendencia(*, pendencia_id, motivo, operador_id)`**: grava `cancelada_em`/`cancelada_por_id`; mesmo gate do passo 3 (se era a última física, emite `PENDENCIA_RESOLVIDA`+`MONTADA`); não roda movimento de estoque.

**Gate `disponibilizar`: não muda** (já bloqueia em PENDENTE; MONTADA só sai quando a última ficha fecha) + assertiva defensiva `count_fisicas_abertas(chassi) == 0`.

---

## 7. Matriz tratativa → efeito

A árvore de decisão da AVARIA mora em `pendencia.detalhes`. "Provisão" = `solicitar_compra` (não resolve; `fase=AGUARDANDO_PECA`). "Resolve" = `resolver_pendencia`. Tudo na **mesma transação** do passo correspondente (flush; o caller HTTP commita, §10).

| # | Categoria · cenário | Provisão (opcional) | Tratativa que resolve | Movimento no ledger | Efeito moto / doador |
|---|---|---|---|---|---|
| 1 | **FALTA_PECA · tem no estoque** | (norma) `solicitar_compra(COMPRA)` para **repor** o estoque consumido | `USAR_ESTOQUE` | `CONSUMO`(−1, custo médio congelado) | resolve receptora; se última física → MONTADA |
| 2 | **FALTA_PECA · usa de outra moto** | — | `USAR_OUTRA_MOTO` | `CANIBALIZACAO` (delta 0, custo **0**; doador→receptora; `peca_id`) | resolve receptora **+ abre FALTA_PECA root no doador** (a falta "viaja") |
| 3 | **FALTA_PECA · sem estoque/sem doador** | `solicitar_compra(COMPRA)` → `AGUARDANDO_PECA` | depois: `USAR_ESTOQUE` (aplica a peça recebida) | recebimento `ENTRADA`(+) → depois `CONSUMO`(−) | moto segue PENDENTE até aplicar |
| 4 | **AVARIA · conserto** (fio solto) | — | `CONSERTAR` | **nenhum** | resolve |
| 5 | **AVARIA · troca, garantia** | `solicitar_compra(GARANTIA)` **mesmo com estoque** → `AGUARDANDO_PECA` | depois: `USAR_ESTOQUE` (estoque/peça recebida) ou `USAR_OUTRA_MOTO` | aplica: `CONSUMO`/`CANIBALIZACAO`; **peça velha (O-C): operador escolhe `ENTRADA`(+, volta ao estoque p/ conserto) ou `DESCARTE`(δ0, descarta)** | moto PENDENTE até aplicar |
| 6 | **AVARIA · troca, não-garantia** | se `detalhes.avaria.repor_estoque` → `solicitar_compra(COMPRA)` | `USAR_ESTOQUE` ou `USAR_OUTRA_MOTO` | `CONSUMO`(−1) **ou** `CANIBALIZACAO`; **peça velha (O-C): `ENTRADA`(volta ao estoque) ou `DESCARTE`(δ0)** | resolve receptora |
| 7 | **REVISAO** (toda devolução) | — | `REVISAR` | **nenhum** | resolve **ou gera filhas** AVARIA/FALTA_PECA (`pendencia_pai_id`=esta; filhas herdam `origem`+`evento_pendente_id` da mãe); só sai de PENDENTE quando a **última** física fechar |
| 8 | **VENDA · do estoque** | — | `USAR_ESTOQUE` | `CONSUMO`(−1) com `receita_*` preenchida | pós-venda não muda estado (D2), salvo `retorno_fisico` |
| 9 | **VENDA · de outra moto** | — | `USAR_OUTRA_MOTO` | `CANIBALIZACAO` (delta 0, custo 0) com `receita_*` **+ abre FALTA_PECA no doador** | doador PENDENTE (se físico) |

**Canibalização (transação única)**: ① linha `CANIBALIZACAO` (delta 0; `chassi_origem→chassi_destino`+`peca_id` = o elo) → ② `abrir_pendencia(categoria=FALTA_PECA, **origem=GALPAO**, chassi=doador, descricao=f'Peça canibalizada para chassi {destino}', peca_id, operador_id, detalhes={'movimento_origem_id': mov.id, 'canibalizado_para': destino})` — nova pendência **root** no doador (não usa `pendencia_pai_id`). `origem` e `descricao` são preenchidos com os defaults aqui (ambos NOT NULL).

---

## 8. Custeio e receita

**Método: média móvel ponderada por peça, custo congelado por movimento.** FIFO exigiria tabela de lotes (fura o footprint; sem ganho — peças chegam **sem NF**); custo específico exigiria serial (inviável).

- `custo_medio(peca) = SUM(delta_almoxarifado · custo_unitario) / SUM(delta_almoxarifado)` sobre linhas que **afetam** o almoxarifado. **Guarda de divisão por zero**: se `SUM(delta_almoxarifado) <= 0` (ex.: peça só canibalizada, ou saldo líquido nulo) → fallback para `assai_peca.custo_referencia`, senão último `custo_unitario` conhecido de uma `ENTRADA`, senão 0.
- Em `CONSUMO`/`DESCARTE`, grava `custo_unitario = custo_medio` **congelado na linha** (auditável, estável retroativamente).
- **Entrada (sem NF)**: `custo_unitario` manual; `custo_total = qtd·custo`.
- **Canibalização (O4)**: `custo_unitario=0` + `dados_extras['custo_estimado']=true`; o custo real materializa quando a FALTA_PECA do doador for resolvida por COMPRA.
- **Receita (VENDA)**: `receita_*` na própria linha do ledger que atende pendência `categoria=VENDA` (vale `CONSUMO` e `CANIBALIZACAO`). Margem = `receita − custo` na linha.

---

## 9. Pontos de integração

- **Devolução → REVISÃO** (`devolucao_service.py:197-208`): hoje emite `FATURADA→PENDENTE` (via o helper travado, §6) com FK `assai_devolucao_item.evento_pendencia_id`. Logo após, `abrir_pendencia(categoria=REVISAO, origem=DEVOLUCAO, chassi, descricao=motivo, devolucao_item_id=item.id, evento_pendente_id=<o MESMO evento já emitido>, operador_id)` — passa o `evento_pendente_id` explícito → `abrir_pendencia` **pula** o helper (sem 2º PENDENTE). **Nenhum ALTER em `assai_devolucao_item`**.
- **Pós-venda → pendência** (`AssaiPosVendaOcorrencia`): `abrir_pendencia(origem = POS_VENDA_LOJA if oc.categoria=='LOJA' else POS_VENDA_CLIENTE, evento_pendente_id=NULL, pos_venda_ocorrencia_id=oc.id, ...)`. Gate `chassi_foi_vendido`; moto segue FATURADA (D2). O **botão/UI** é Spec 2; o **gancho de serviço** é Spec 1.
- **`DIVERGENCIA_AVARIA_FISICA`** (`models/recibo.py`): camadas distintas — `AssaiDivergencia(tipo=AVARIA_FISICA)` é flag de reconciliação no recebimento; `AssaiPendencia(categoria=AVARIA)` é workflow de conserto. **Não fundir.** Ponte: `abrir_pendencia(categoria=AVARIA, origem=GALPAO, divergencia_origem_id=div.id)`.

---

## 10. Compatibilidade e caminho de escrita

Requisito do dono: o resto do módulo precisa ser **coerente com "1 evento PENDENTE por chassi"**. Como `PENDENCIA_RESOLVIDA` deixa de ser fonte de dado de resolução (passa a marcador, emitido **uma vez** ao fechar a última física), as leituras abaixo passam a ler a **tabela**:

| Função / rota (hoje conta eventos) | Passa a ler |
|---|---|
| `pendencia_service.listar_abertas` | `assai_pendencia` abertas (categoria/origem/tratativa) |
| `pendencia_service.listar_historico_resolvidas` | `assai_pendencia` resolvidas (1:1, com `resolucao_descricao` + movimentos ligados) |
| `pendencia_service.contar_pendencias_abertas` | `COUNT` de fichas abertas |
| `operadores_que_registraram_pendencia` / `modelos_com_pendencias` | distintos a partir de `assai_pendencia` |
| `devolucao_service.pendencias_do_chassi` | fichas do chassi |

**Os 3 emissores** (`registrar_montagem`, `enviar_para_pendencia`, `criar_devolucao`) passam a **também** abrir uma ficha:
- `registrar_montagem` / `enviar_para_pendencia`: `abrir_pendencia(categoria=INDETERMINADA, origem=GALPAO, descricao=<a descrição que já coletam>, evento_pendente_id=<o PENDENTE que acabaram de emitir>, ...)`. A categoria real é capturada/reclassificada na UI do Spec 2.
- `criar_devolucao`: REVISAO/DEVOLUCAO (§9).

**Resolver — retrocompatibilidade (não quebrar prod no gap):** `montagem_service.resolver_pendencia(chassi, descricao_resolucao, operador_id)` é mantido como **shim**: localiza a **única** ficha física aberta do chassi (no gap Spec 1→Spec 2 não há multi-pendência, pois a UI que cria N só chega no Spec 2), chama `pendencia_service.resolver_pendencia(pendencia_id=..., tratativa=None, resolucao_descricao=...)` e **commita internamente** (preserva o comportamento atual — a rota `POST /pendencias/resolver` e `services/__init__.py` seguem intactos; `>1` física aberta levanta erro claro). A reescrita da rota para `pendencia_id` + `tratativa` é Spec 2. Novos orquestradores HTTP (Spec 2) commitam explicitamente (os serviços fazem flush-sem-commit).

---

## 11. Camada de serviços

`criar/abrir/registrar/solicitar_*` fazem `add`+`flush` **sem commit** (caller controla a transação; o shim de §10 e as rotas do Spec 2 commitam); `resolver_*`/`cancelar_*` idempotentes; exceções `PendenciaError`, `EstoqueError`, `CompraPecaError`, `PecaError`.

- **`peca_service`**: `criar_peca`, `editar_peca`, `vincular_modelo`, `desvincular_modelo`, `listar_compativeis(modelo_id)`, `listar`.
- **`pendencia_service`** (reescrito do atual read-only): `abrir_pendencia(...)`, `_get_or_emit_pendente_event(chassi)`, `count_fisicas_abertas(chassi)`, `solicitar_compra(...)`, `resolver_pendencia(...)`, `cancelar_pendencia(...)`, + leituras migradas (§10).
- **`movimento_service`** (ledger): `registrar_entrada(*, peca_id, quantidade, custo_unitario, operador_id, compra_item_id=None, recebimento_ref=None)`; `consumir(*, peca_id, quantidade, pendencia_id, chassi_destino, operador_id, receita_unitaria=None)`; `canibalizar(*, peca_id, quantidade, chassi_origem, chassi_destino, pendencia_id, operador_id, receita_unitaria=None)` (cria a linha **+ abre FALTA_PECA no doador** com origem/descricao default, §7); `descartar(...)`; `ajustar(...)`; `saldo(peca_id)`; `custo_medio(peca_id)` (com guarda de §8).
- **`compra_peca_service`**: `criar_compra(*, tipo, itens, operador_id, fornecedor='MOTOCHEFE')` (gera `PC-AAAA-NNNN` via **sequence/retry, nunca `MAX()+1`**); `adicionar_item`; `receber_item(*, compra_item_id, quantidade, custo_unitario, operador_id)` (→ `registrar_entrada` + recompute status); `cancelar_compra`. `solicitar_compra` (§6) é o wrapper chamado pela pendência.

---

## 12. Migração, registro e backfill

1. **Models**: 6 arquivos novos em `app/motos_assai/models/` (`peca.py` com o N:N, `pendencia.py`, `estoque_movimento.py`, `peca_compra.py` com cabeçalho+item). Registrar classes **e** constantes em `models/__init__.py` (import + `__all__`).
2. **Migration `motos_assai_34_estoque_pecas_pendencia`** (`.sql`+`.py`, molde `motos_assai_28_cce_entidade`): `BEGIN; CREATE TABLE IF NOT EXISTS ...; CREATE INDEX IF NOT EXISTS ...; COMMIT;`. **Sem CHECK** (validação por set Python).
   - **Convenção de deploy (reconciliada com a prática recente)**: as migrations 30/32/33 **não** entraram no `build.sh` — foram aplicadas manualmente em prod (`DATABASE_URL_PROD`) e o arquivo ficou só como registro do DDL (ver `app/motos_assai/CLAUDE.md`). A migration 34 segue **o mesmo padrão**: aplicar manualmente em prod + local, deixar o arquivo versionado como DDL idempotente, e documentar "NÃO consta no build.sh". (Alternativa: re-padronizar e incluir no build.sh — decidir no plano.)
3. **Schema JSON**: `python .claude/skills/consultando-sql/scripts/generate_schemas.py` (auto-descobre os models) → 6 `assai_*.json` + `catalog.json`/`relationships.json`; entrada em `TABLE_DESCRIPTIONS`.
4. **Backfill (obrigatório no deploy)** — para cada chassi cujo **último evento é `PENDENTE`**, criar a ficha apontando `evento_pendente_id` = esse evento, com `--check` de cobertura (zero PENDENTE sem ficha):
   - `dados_extras['origem']=='devolucao_nfd'` → `categoria=REVISAO`, `origem=DEVOLUCAO`, `devolucao_item_id` resolvido pelo `devolucao_id`;
   - caso contrário → `categoria=INDETERMINADA`, `origem=GALPAO`, `descricao = observacao`/`dados_extras['descricao']`, `chassi_doador = dados_extras['chassi_doador']`, `detalhes['legacy_backfill']=true`. (Reclassificação posterior pela UI do Spec 2.)
5. **Doc**: atualizar `app/motos_assai/CLAUDE.md` (29→35 tabelas, constantes, seção nova) e remover o stub `assai_avaria` do roadmap.

---

## 13. Pré-mortem (riscos + mitigação)

1. **Concorrência no PENDENTE compartilhado**: `pg_advisory_xact_lock(hashtext(chassi))` em `abrir`/`resolver`/`cancelar`, com emissão **só** via `_get_or_emit_pendente_event`.
2. **Cascata/ciclo de canibalização** (A→B→A): guard `doador != receptor`; bloquear canibalizar peça já em FALTA_PECA aberta no doador; validar existência do chassi em `assai_moto`.
3. **Margem temporalmente espalhada** (VENDA por canibalização tem COGS deferido): aceito (O4); relatório reconcilia por `peca_id` + cadeia de pendências.
4. **Colisão de `numero` `PC-AAAA-NNNN`**: sequence/retry, **nunca `MAX()+1`**.
5. **`peca_id` NULL na ficha vs NOT NULL no ledger**: exigir `peca_id` só no momento do movimento; cadastro rápido de peça na UI (Spec 2).
6. **Sem CHECK nas tabelas novas**: escrita só via service (trade-off, molde Divergência).
7. **Média móvel com saldo zero/negativo**: guarda de divisão (§8) + consumir com último custo + `custo_estimado=true`.
8. **`SUM(delta)` no caminho quente**: índice `(peca_id)`; cache de `custo_medio`/saldo na peça se escalar (fora do Spec 1).
9. **Backfill incompleto**: parte do deploy, com `--check` de cobertura.
10. **Advisory lock vs `with_for_update(of=AssaiMoto)`**: são mecanismos que **não se cruzam**. O invariante "1 PENDENTE/chassi" só vale se **todos** os emissores passarem pelo helper travado (garantido em §6/§10). Avaliar no plano se o gate de `disponibilizar`/`separacao` precisa do mesmo advisory lock para não correr contra o lock de linha.
11. **Two-phase mal usado**: resolver uma ficha em `AGUARDANDO_PECA` sem a peça aplicada — o `resolver_pendencia` exige a tratativa final e seu movimento; `solicitar_compra` nunca grava `resolvida_em`.

---

## 14. Decisões da revisão + ainda em aberto

**Confirmadas pelo dono (2026-06-30):**
- **R1 ✓ — 5ª origem `DEVOLUCAO`** (física). `DEVOLUCAO ∈ ORIGENS_FISICAS` alinha a origem à realidade e fecha a antiga decisão O-A.
- **R2 ✓ — categoria-sentinela `INDETERMINADA`** para o backfill legado e para montagem/enviar antes da classificação. **Requisito do Spec 2**: ter uma forma explícita de **reclassificar** pendências `INDETERMINADA` para a categoria real (ver §15).
- **R3 ✓ — "pedir compra/garantia" é provisão, não tratativa** (`solicitar_compra` → `AGUARDANDO_PECA`, não fecha a ficha; ela fecha quando a peça é aplicada).
- **O-C ✓ — destino da peça velha (AVARIA)**: o **operador decide na resolução** — `ENTRADA` (volta ao estoque, p/ conserto) ou `DESCARTE` (δ0, descartada). Refletido em §5/§7.
- **R4 ✓ — retorno físico de moto vendida sem NFd → sempre MONTADA.** Ao resolver, a moto re-entra no estoque montado (a NF original fica como registro histórico; sem dupla contagem, pois o estado é o último evento). Estado-alvo de resolução física é **sempre MONTADA**, sem ramo condicional.

Todas as decisões estruturais e de comportamento estão travadas.

---

## 15. Fora de escopo (Spec 2)

Telas e fios de UI: cadastro de peça + compatibilidade; tela de estoque/saldo por peça; recebimento manual de peças (entrada sem NF, em lote via `recebimento_ref`); tela de pendência categorizada com os ramos de tratativa (árvore da AVARIA) + provisão; botão "gerar pendência" na área de pós-venda; telas de pedido de compra (criar, receber itens); **reescrita da rota `POST /pendencias/resolver` para `pendencia_id` + `tratativa`** (Spec 1 mantém o shim por chassi); refactor das telas `pendencias/{abertas,historico}` (mostrar categoria/origem/tratativa); **ação de reclassificar pendências `INDETERMINADA` para a categoria/origem reais** (R2); itens de menu; onboarding tours.

---

## 16. Referências

- Estado atual: `app/motos_assai/models/moto.py`, `services/montagem_service.py` (`:94`,`:139`,`:239`), `services/pendencia_service.py`, `services/devolucao_service.py:197-208`, `routes/pendencias.py:101-122`, `models/pos_venda.py`, `models/divergencia.py` (molde), `models/compra.py` (molde), `models/__init__.py`.
- `pg_advisory_xact_lock`: precedente `app/cotacao/routes.py:2019`.
- Migration/schema: `scripts/migrations/motos_assai_28_cce_entidade.{sql,py}`, `motos_assai_19_divergencia.{sql,py}`, `.claude/skills/consultando-sql/scripts/generate_schemas.py`, `build.sh`.
- Doc do módulo: `app/motos_assai/CLAUDE.md`. Design original: `docs/superpowers/specs/2026-05-07-motos-assai-design.md`.
