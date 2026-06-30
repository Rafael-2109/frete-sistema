<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/superpowers/specs/INDEX.md
superseded_by: —
atualizado: 2026-06-30
-->
# Motos Assaí — Estoque de Peças + Pendência Categorizada (Spec 2: UI + fios)

> **Papel:** desenho das telas, rotas e fios de UI que expõem o back-end do **Spec 1** (Estoque de Peças + Pendência categorizada). Cobre a página de resolução por ficha (ramos de tratativa + provisão), o detalhe read-only da pendência, o catálogo/estoque/compra de peças, o gancho de pós-venda, a timeline unificada do chassi, a reescrita da rota de resolução e a unificação da resolução de chão (aposentando o shim). Inclui os follow-ups técnicos do Spec 1 dobrados aqui.

## Indice

- [Contexto](#contexto)
  - [1.1 Base (Spec 1)](#11-base-spec-1)
  - [1.2 Estado atual da UI (verificado no código)](#12-estado-atual-da-ui-verificado-no-código)
  - [1.3 Escopo do Spec 2 vs follow-up](#13-escopo-do-spec-2-vs-follow-up)
- [2. Decisões aprovadas (Q&A desta sessão)](#2-decisões-aprovadas-qa-desta-sessão)
- [3. Arquitetura](#3-arquitetura)
- [4. Frente A — Domínio Pendência](#4-frente-a-domínio-pendência)
- [5. Frente B — Pós-venda (gerar + acompanhar)](#5-frente-b-pós-venda-gerar-acompanhar)
- [6. Frente C — Catálogo de Peça](#6-frente-c-catálogo-de-peça)
- [7. Frente D — Estoque de Peça (ledger)](#7-frente-d-estoque-de-peça-ledger)
- [8. Frente E — Pedido de Compra de Peça](#8-frente-e-pedido-de-compra-de-peça)
- [9. Frente F — Timeline unificada no rastreamento de chassi](#9-frente-f-timeline-unificada-no-rastreamento-de-chassi)
- [10. Menu](#10-menu)
- [11. Follow-ups técnicos dobrados](#11-follow-ups-técnicos-dobrados)
- [12. Rotas (consolidado)](#12-rotas-consolidado)
- [13. Camada de serviços](#13-camada-de-serviços)
- [14. Testes](#14-testes)
- [15. Deploy (bundlado Spec 1 + Spec 2)](#15-deploy-bundlado-spec-1-spec-2)
- [16. Pré-mortem (riscos + mitigação)](#16-pré-mortem-riscos-mitigação)
- [17. Fora de escopo (follow-up)](#17-fora-de-escopo-follow-up)
- [18. Referências](#18-referências)

---

## Contexto

### 1.1 Base (Spec 1)

O Spec 1 (back-end) entregou 6 tabelas + serviços + integração + backfill, **implementado e testado** (373 testes verdes), em commits locais na `main` **não pushados** (deploy bundlado com este Spec 2). As 3 verdades: **evento `assai_moto_evento`** = estado físico (1 `PENDENTE`/chassi); **ficha `assai_pendencia`** = tratamento (N/chassi, categoria/origem/tratativa/fase); **ledger `assai_estoque_movimento`** = peça (saldo = `SUM(delta_almoxarifado)`, custo médio móvel). Os serviços (`pendencia_service`, `movimento_service`, `peca_service`, `compra_peca_service`) fazem **add+flush SEM commit** (o caller HTTP commita). `pendencia_service.resolver_pendencia(pendencia_id, tratativa, ...)` **deliberadamente NÃO movimenta estoque** — o movimento (`consumir`/`canibalizar`) é responsabilidade de chamadas separadas a `movimento_service`.

Esta sessão já aplicou o **follow-up item 1** do handoff: `compra_peca_service._gerar_numero` virou `CREATE SEQUENCE assai_peca_compra_numero_seq` + `nextval()` (emenda na migration 34), eliminando `COUNT()`/retry (§13.4 do Spec 1). Os demais follow-ups técnicos entram aqui (§11).

### 1.2 Estado atual da UI (verificado no código)

- **Pendências**: 3 telas (`pendencias/{landing,abertas,historico}.html`). `abertas.html` tem botão "Resolver" → **modal de texto livre** inline → `POST /pendencias/resolver {chassi, descricao_resolucao}` (JSON) → **shim** `montagem_service.resolver_pendencia(chassi, ...)`. Nenhuma categoria/origem/tratativa exposta. As leituras (`pendencia_service.listar_abertas`/`listar_historico_resolvidas`) **já leem `assai_pendencia`**, mas os dicts retornados ainda usam chaves legadas (`evento_id`, `observacao`) e **não expõem** categoria/origem/tratativa/fase. Filtros hoje: chassi/modelo/data/operador.
- **Pós-venda** (`routes/pos_venda.py` + `pos_venda_service.py`): lista de motos vendidas (gate `chassi_foi_vendido` via `assai_nf_qpa_item`) + modal AJAX de ocorrências LOJA/CLIENTE (texto + anexos S3). Coluna "Ações" só tem "Ocorrências (N)". `AssaiPosVendaOcorrencia.categoria ∈ {LOJA, CLIENTE}`.
- **Menu** (`base_motos_assai.html`): nav **flat** (sem dropdowns), 17 itens `<a class="motos-assai-nav-link" id="menu-X">`, antes do `#help-button`.
- **Rastreamento de chassi** (`rastreamento_chassi_service.rastrear_chassi`, modal `resumo/_modal_rastreamento.html`): visão 360 com recibos/montagem/`pendencias`(derivado dos eventos `PENDENTE`)/separações/carregamentos/nfs/cces/divergências/eventos/contadores. **Não** lê `assai_pendencia` nem `assai_estoque_movimento`.
- **Moldes reusáveis**: CRUD `routes/modelos.py` + `templates/motos_assai/modelos/` (FlaskForm, service commita, flash+redirect); compras `routes/compras.py` + `templates/.../compras/` (multi-select via `getlist`, preview, detalhe cabeçalho+itens, PDF WeasyPrint); registro de rotas por import em `routes/__init__.py`; forms em `forms/`; partials `partials/_filtro_chassi_modelo.html`, `_modal_enviar_pendencia.html`.

### 1.3 Escopo do Spec 2 vs follow-up

| | Spec 2 (este) | Follow-up (fora) |
|---|---|---|
| **Conteúdo** | Página de resolução por ficha + detalhe read-only; catálogo/estoque/compra de peça; gancho pós-venda (gerar + acompanhar); timeline unificada do chassi; reescrita da rota de resolução; **unificação da resolução de chão** (remove o shim); filtros por categoria/origem/tratativa; follow-ups técnicos dobrados | Onboarding tours das telas novas; PDF do PC; painel/contadores de pendências no Resumo/Dashboard; reclassificar `divergencia`→pendência em massa |
| **Critério** | tudo que precisa de HTML/JS/rota; deploy bundlado com o Spec 1; nada de prod quebra | UX/relatórios não-bloqueantes |

---

## 2. Decisões aprovadas (Q&A desta sessão)

| ID | Decisão |
|----|---------|
| **S1** | Resolução de pendência em **página dedicada** `/pendencias/<id>/resolver` (não modal): ficha completa + reclassificação inline (se INDETERMINADA) + tratativa com campos condicionais + provisão (pedir compra). |
| **S2** | Reclassificar INDETERMINADA = **inline na resolução** (obrigatório antes de fechar) **+ ação avulsa** na lista (triagem sem resolver). |
| **S3** | Botão "gerar pendência" no **modal de ocorrências do pós-venda**, vinculado à ocorrência (`pos_venda_ocorrencia_id`); pede categoria (AVARIA/FALTA_PECA/REVISAO) + checkbox "retorno físico". |
| **S4** | Escopo: **unificar a resolução de chão** na tela nova (aposenta o shim). Onboarding tours e PDF do PC = follow-up. |
| **S5** | Saldo insuficiente no `consumir` = **aviso não-bloqueante** (o modelo já tolera saldo negativo com fallback de custo médio, §8 do Spec 1). |
| **S6** | Reclassificação tem **guard de consistência**: se a ficha já tem `evento_pendente_id` e a nova `origem` a tornaria não-física (`afeta_estado_moto`→False), **erro** (não dá para destravar a moto via troca de origem). |
| **S7** | **Remover** o shim `montagem_service.resolver_pendencia` neste deploy (o backfill 35 roda junto). |
| **S8** | Visibilidade extra: **detalhe read-only da pendência** + **pós-venda acompanha a tratativa** + **timeline unificada no rastreamento do chassi** + **filtros por categoria/origem/tratativa** nas listas. Painel no Resumo/Dashboard = follow-up. |

---

## 3. Arquitetura

**Orquestrador fino** (abordagem A aprovada): a lógica de "resolver com tratativa" mora num service novo `resolucao_service`, que **compõe os átomos do Spec 1** (`movimento_service.consumir`/`canibalizar` + `pendencia_service.resolver_pendencia`). A rota só faz HTTP + `db.session.commit()`. Mantém o padrão do módulo ("zero `db.session` na rota; lógica no service") e preserva a ortogonalidade do Spec 1 (não embute movimento dentro de `resolver_pendencia`). Todas as rotas novas de escrita seguem: serviço faz flush-sem-commit → rota commita.

---

## 4. Frente A — Domínio Pendência

### 4.1 `resolucao_service.resolver_com_tratativa` (novo)

`app/motos_assai/services/resolucao_service.py`:

```python
def resolver_com_tratativa(
    *, pendencia_id, tratativa, resolucao_descricao, operador_id,
    peca_id=None, quantidade=None, chassi_doador=None, receita_unitaria=None,
) -> dict
```

Numa transação (rota commita):
1. Carrega a ficha (`db.session.get`); erro se ausente/já fechada (idempotência delegada a `resolver_pendencia`).
2. Executa o **movimento da tratativa** (antes de fechar):
   - `USAR_ESTOQUE` → `movimento_service.consumir(peca_id, quantidade, pendencia_id, chassi_destino=ficha.chassi, operador_id, receita_unitaria)`.
   - `USAR_OUTRA_MOTO` → `movimento_service.canibalizar(peca_id, quantidade, chassi_origem=chassi_doador, chassi_destino=ficha.chassi, pendencia_id, operador_id, receita_unitaria)`.
   - `CONSERTAR` / `REVISAR` → nenhum movimento.
   - Validação: tratativas que movimentam exigem `peca_id` + `quantidade`; `USAR_OUTRA_MOTO` exige `chassi_doador`.
3. `pendencia_service.resolver_pendencia(pendencia_id, tratativa, resolucao_descricao, operador_id)` (fecha a ficha + dispara o gate físico — emite `PENDENCIA_RESOLVIDA`+`MONTADA` se era a última física).
4. Retorna `{ok, pendencia_id, saldo_apos (se houve consumo), custo_movimento, montou (bool — moto voltou a MONTADA)}`.

**Saldo insuficiente (S5):** `consumir` não bloqueia; o service calcula `saldo_apos = movimento_service.saldo(peca_id)` e devolve para a tela alertar (não levanta). `receita_unitaria` só é repassada quando `ficha.categoria == VENDA` (o próprio `consumir`/`canibalizar` já ignora caso contrário).

### 4.2 `pendencia_service.reclassificar` (novo)

```python
def reclassificar(*, pendencia_id, categoria, origem, operador_id) -> AssaiPendencia
```
Valida `categoria ∈ PENDENCIA_CATEGORIAS_VALIDAS` (idealmente ≠ INDETERMINADA no destino) e `origem ∈ PENDENCIA_ORIGENS_VALIDAS`. **Guard S6:** se `ficha.evento_pendente_id is not None` e a nova `origem` tornaria `afeta_estado_moto` False (e `devolucao_item_id`/`retorno_fisico` não a sustentam), levanta `PendenciaError` ("não é possível tornar não-física uma pendência que já trava a moto"). Grava `categoria`/`origem`, registra a troca em `detalhes['reclassificacao']` (de/para, operador, timestamp via `sanitize_for_json`). add+flush, sem commit.

### 4.3 Página de resolução `GET/POST /pendencias/<int:pid>/resolver`

`routes/pendencias.py` (+ template `pendencias/resolver.html`, JS `static/motos_assai/js/pendencia_resolver.js`):

- **GET** monta: a ficha (categoria/origem/fase/descrição/chassi+modelo+cor/peça/doador/filhas/pai), as **peças compatíveis** com o modelo da moto (`peca_service.listar_compativeis(modelo_id)`) com **saldo** de cada (`movimento_service.saldo`), as **compras já solicitadas** (provisão em aberto). Se `categoria == INDETERMINADA`, exibe o bloco de reclassificação **antes** do bloco de tratativa.
- **POST `acao=resolver`** → `resolucao_service.resolver_com_tratativa(...)` + commit → flash + redirect `pendencias_abertas`. Se `categoria == INDETERMINADA`, a rota **exige** os campos de reclassificação e chama `reclassificar(...)` na mesma transação antes de resolver.
- **POST `acao=solicitar-compra`** → `pendencia_service.solicitar_compra(pendencia_id, tipo, itens, operador_id)` + commit → volta à página (fase=AGUARDANDO_PECA; não fecha).
- **POST `acao=reclassificar`** → `pendencia_service.reclassificar(...)` + commit → volta à página.
- JS: mostra/esconde os campos por tratativa (peça+qtd p/ USAR_ESTOQUE; peça+qtd+doador p/ USAR_OUTRA_MOTO; nada p/ CONSERTAR/REVISAR) e alerta quando `qtd > saldo` (não bloqueia). Mobile-friendly (chão usa a mesma página).

### 4.4 Detalhe read-only `GET /pendencias/<int:pid>`

`routes/pendencias.py` (+ template `pendencias/detalhe.html`). Serviço `pendencia_service.detalhe_pendencia(pid)` monta o dict:
- **Cabeçalho**: categoria/origem/fase/status (aberta/resolvida/cancelada), chassi+modelo+cor, descrição, datas+operadores de cada etapa (abriu/resolveu/cancelou), tratativa + `resolucao_descricao`.
- **Origem vinculada**: link p/ devolução (`devolucao_item_id`), ocorrência de pós-venda (`pos_venda_ocorrencia_id`) ou divergência (`divergencia_origem_id`).
- **Movimentos ligados** (`AssaiEstoqueMovimento WHERE pendencia_id == pid`, com peça): tipo · peça · qtd · custo unit./total · receita (se VENDA) · doador→receptor · data/operador, com **custo total da tratativa** somado.
- **Compras (provisão)**: `AssaiPecaCompraItem WHERE pendencia_id == pid` → cabeçalhos `AssaiPecaCompra` distintos (nº · tipo · status · qtd pedida/recebida).
- **Cadeia REVISÃO**: `filhas` (categoria/status/link) e `pai`; se a ficha é a FALTA_PECA aberta no doador por canibalização, expõe `detalhes['canibalizado_para']`.

Quando a ficha está **aberta**, o detalhe tem botão "Resolver" (→ `/resolver`); quando **fechada**, é só leitura.

### 4.5 Reescrita da rota antiga + remoção do modal/JS

- **REMOVE** `POST /pendencias/resolver` (rota JSON do shim) + o modal de texto livre em `abertas.html` + `static/motos_assai/js/pendencias_resolver.js` + a injeção `window.MOTOS_ASSAI_PENDENCIAS`.
- O botão "Resolver" de `abertas.html` vira **link** `url_for('motos_assai.pendencia_resolver_tela', pid=...)`.
- `POST /pendencias/criar` (enviar p/ pendência do chão via `enviar_para_pendencia`) **permanece** (cria INDETERMINADA).

### 4.6 Refactor das leituras + templates + filtros (S8)

- `pendencia_service.listar_abertas`/`listar_historico_resolvidas` passam a expor: `pendencia_id` (era `evento_id`), `categoria`, `origem`, `tratativa`, `fase`. Os **filtros** ganham `categoria`, `origem`, `tratativa` (além de chassi/modelo/data/operador), via `FiltrosPendencias` estendido e `_coletar_filtros` na rota.
- `abertas.html`: colunas **Categoria / Origem / Fase** + badge `INDETERMINADA` destacado; ações **Resolver** (link) e **Reclassificar** (modal pequeno → `POST /pendencias/<pid>/reclassificar`). Selects de categoria/origem/tratativa no formulário de filtro.
- `historico.html`: coluna **Tratativa**; mesmos filtros.

### 4.7 Unificação de chão + remoção do shim (S4/S7)

`montagem_service.resolver_pendencia` (shim) é **removido**. Auditar e limpar todos os callers: a rota JSON antiga (removida em 4.5), `services/__init__.py` (export), e qualquer import morto resultante (`EVENTO_PENDENCIA_RESOLVIDA` em `montagem_service` se ficar órfão). A resolução passa a ter **um único caminho** (a página `/resolver`), usado tanto pela gestão quanto pelo chão. O "enviar p/ pendência" das telas de chão (montagem/disponibilizar/separação) **não muda** (segue criando INDETERMINADA via `enviar_para_pendencia`).

---

## 5. Frente B — Pós-venda (gerar + acompanhar)

**Gerar** — nova rota `POST /pos-venda/ocorrencias/<int:oc_id>/gerar-pendencia` (`routes/pos_venda.py`):
- Resolve o chassi da ocorrência; `origem = POS_VENDA_LOJA if oc.categoria=='LOJA' else POS_VENDA_CLIENTE`; `pendencia_service.abrir_pendencia(categoria=<AVARIA|FALTA_PECA|REVISAO>, origem=..., pos_venda_ocorrencia_id=oc.id, retorno_fisico=<checkbox>, descricao=<default da ocorrência>, operador_id)` + commit.
- Sem `retorno_fisico` → moto segue FATURADA (não trava, D2). Com → vira PENDENTE (R4) — a página de resolução depois leva a MONTADA.
- UI: botão "Gerar pendência" no `pos_venda/_macros.html` (`render_ocorrencia`) → mini-form (categoria + checkbox "retorno físico") tratado por delegação no `pos_venda.js` (`#modal-ocorrencias-body`).

**Acompanhar** (S8):
- `pos_venda_service` ganha `pendencias_da_ocorrencia(oc_id)` (lista `assai_pendencia WHERE pos_venda_ocorrencia_id`) e `contar_pendencias_abertas_por_chassi(chassi)`.
- O fragmento `_modal_ocorrencias.html` / `_macros.html` mostra, sob cada ocorrência, as **pendências geradas** (badge categoria + status + tratativa + link p/ `/pendencias/<id>`).
- A lista `pos_venda/lista.html` ganha, na coluna Ações, um badge "Pendências (N)" (N abertas do chassi).

---

## 6. Frente C — Catálogo de Peça

Molde `routes/modelos.py`. `routes/peca.py` (registrar em `routes/__init__.py`):
- `GET /pecas` — lista (filtro nome/código + `ativo`), saldo opcional na coluna.
- `GET/POST /pecas/novo`, `GET/POST /pecas/<id>/editar` — `forms/peca_forms.py:PecaForm` (nome, código, `custo_referencia`, ativo + **multi-select de modelos compatíveis**). Serviço `peca_service` já tem `criar_peca(modelo_ids=...)`, `editar_peca`, `vincular_modelo`/`desvincular_modelo`. No editar, a rota faz o **diff** dos `modelo_ids` (vincula novos, desvincula removidos). Rota commita.
- `GET /pecas/<id>` — detalhe (dados + modelos compatíveis + saldo/custo médio atuais + atalho p/ o ledger da peça).
- Templates `pecas/{lista,form,detalhe}.html`.

---

## 7. Frente D — Estoque de Peça (ledger)

`routes/estoque_peca.py`:
- `GET /estoque-pecas` — lista de peças com **saldo** (`movimento_service.saldo`) e **custo médio** (`custo_medio`). (Cálculo por peça; aceitável p/ o volume atual — peças, não chassis.)
- `GET /estoque-pecas/<int:peca_id>` — **ledger**: movimentos da peça (`AssaiEstoqueMovimento WHERE peca_id`, mais recentes primeiro), com tipo/qtd/delta/custo/receita/chassi/data/operador; saldo + custo médio no topo.
- `POST /estoque-pecas/entrada` — **recebimento manual avulso** (sem NF): peça + qtd + custo unitário + `recebimento_ref` opcional (lote) → `movimento_service.registrar_entrada(...)`.
- `POST /estoque-pecas/ajustar` — peça + delta (±) + motivo → `ajustar(...)`.
- `POST /estoque-pecas/descartar` — peça + qtd + motivo → `descartar(...)` (baixa de saldo do almoxarifado).
- Templates `estoque_pecas/{lista,detalhe}.html` + modais de ação. FlaskForm leve p/ CSRF. Rota commita.

---

## 8. Frente E — Pedido de Compra de Peça

Molde `routes/compras.py`. `routes/compra_peca.py`:
- `GET /compras-peca` — lista (nº PC · tipo · status · fornecedor · data).
- `GET/POST /compras-peca/nova` — tipo (GARANTIA/COMPRA) + fornecedor + **N linhas** (peça + qtd + custo_estimado) → `compra_peca_service.criar_compra(...)`. Multi-linha (JS p/ adicionar/remover linha, padrão do form de itens).
- `GET /compras-peca/<int:id>` — detalhe cabeçalho + itens (peça · qtd pedida/recebida · custo estimado); status ABERTA/PARCIAL/RECEBIDA/CANCELADA.
- `POST /compras-peca/<int:id>/receber-item` — item + qtd recebida + custo unitário → `receber_item(...)` (→ `ENTRADA` no ledger + recompute status do cabeçalho).
- `POST /compras-peca/<int:id>/cancelar` — `cancelar_compra(...)`.
- Templates `compras_pecas/{lista,nova,detalhe}.html`. **PDF = follow-up.** Numeração `PC-AAAA-NNNN` via a sequence (já implementada).

---

## 9. Frente F — Timeline unificada no rastreamento de chassi

`rastreamento_chassi_service.rastrear_chassi` passa a incluir 2 seções novas no dict (e nos `contadores`):
- **`fichas_pendencia`**: `assai_pendencia WHERE chassi` — categoria/origem/fase/status/tratativa/`resolucao_descricao` + datas/operadores + `pendencia_id` (link p/ `/pendencias/<id>`). Substitui conceitualmente o bloco `pendencias` legado (derivado dos eventos `PENDENTE`); o desenho **mantém ambos** (`pendencias` = eventos físicos; `fichas_pendencia` = tratamento) para não quebrar consumidores.
- **`movimentos_peca`**: `assai_estoque_movimento WHERE chassi_origem == chassi OR chassi_destino == chassi` — peças que entraram/saíram desta moto (consumo/canibalização/descarte) com peça/qtd/custo/data.

`resumo/_modal_rastreamento.html` ganha 2 seções/abas novas + os contadores. Sem nova rota (a `/resumo/rastrear-chassi` já existe).

---

## 10. Menu

`base_motos_assai.html`: 3 itens flat antes do `#help-button`, agrupados logo após "Pendências":
- `Peças` → `peca.lista` (`fa-gears`, `id="menu-pecas"`)
- `Estoque Peça` → `estoque_peca.lista` (`fa-boxes-stacked`, `id="menu-estoque-pecas"`)
- `Compras Peça` → `compra_peca.lista` (`fa-file-invoice-dollar`, `id="menu-compras-pecas"`)

---

## 11. Follow-ups técnicos dobrados

Do handoff do Spec 1 (itens 2-4), corrigidos aqui:

- **`movimento_service.consumir`/`canibalizar`**: chamar `_exigir_peca(peca_id)` no início (hoje `peca_id` inválido → `IntegrityError` cru via FK RESTRICT). `canibalizar`: bloquear quando o **doador já tem FALTA_PECA aberta da mesma peça** (anti-cascata A→B→A, pré-mortem §13.2 do Spec 1); validar que o doador existe em `assai_moto`; `dados_extras` via `sanitize_for_json`.
- **Polish SA2.0**: `.query.get()` → `db.session.get()` nos services do Spec 1 (recorrente: `pendencia_service`, `movimento_service`, `compra_peca_service`, `peca_service`); `pendencia.py` — as 3 relations Usuario `lazy='joined'` → `select` + `joinedload` explícito nas leituras (que já usam `joinedload`). Imports mortos.
- **Hint do schema**: refinar `assai_pendencia.json` (`afeta_estado_moto` — citar `retorno_fisico` e origem física, não só pós-venda). Re-rodar `generate_schemas.py` se algum model mudar (nenhuma mudança de schema prevista neste Spec 2 — só UI/serviço).

---

## 12. Rotas (consolidado)

| Método · rota | Ação |
|---|---|
| `GET /pendencias/<pid>` | detalhe read-only |
| `GET/POST /pendencias/<pid>/resolver` | página de resolução (acao=resolver/solicitar-compra/reclassificar) |
| `POST /pendencias/<pid>/reclassificar` | ação avulsa de reclassificação (lista) |
| ~~`POST /pendencias/resolver`~~ | **removida** (shim por chassi) |
| `POST /pos-venda/ocorrencias/<oc_id>/gerar-pendencia` | gerar pendência da ocorrência |
| `GET /pecas` · `GET/POST /pecas/novo` · `GET/POST /pecas/<id>/editar` · `GET /pecas/<id>` | catálogo |
| `GET /estoque-pecas` · `GET /estoque-pecas/<peca_id>` · `POST /estoque-pecas/{entrada,ajustar,descartar}` | estoque/ledger |
| `GET /compras-peca` · `GET/POST /compras-peca/nova` · `GET /compras-peca/<id>` · `POST /compras-peca/<id>/{receber-item,cancelar}` | compra de peça |

Inalteradas: `GET /pendencias`, `GET /pendencias/{abertas,historico}` (refatoradas), `POST /pendencias/criar`, `GET /resumo/rastrear-chassi` (enriquecida).

## 13. Camada de serviços

- **Novo** `resolucao_service.py`: `resolver_com_tratativa(...)`.
- **Toca** `pendencia_service.py`: `+ reclassificar(...)`, `+ detalhe_pendencia(pid)`, `+ fichas_e_movimentos_do_chassi(chassi)` (p/ rastreamento), leituras enriquecidas + filtros novos.
- **Toca** `movimento_service.py`: guards (§11).
- **Toca** `rastreamento_chassi_service.py`: 2 seções novas (§9).
- **Toca** `montagem_service.py`: remove `resolver_pendencia` (shim).
- **Reusa sem mudança** `peca_service`, `compra_peca_service`, `movimento_service` (entrada/ajuste/descarte/saldo/custo_medio) para as telas C/D/E.
- Exports em `services/__init__.py`; forms em `forms/__init__.py`; rotas em `routes/__init__.py`.

## 14. Testes

Pytest contra o Postgres local (isolamento por SAVEPOINT; admin via fixture). Suíte do módulo segue verde.
- `resolucao_service`: cada tratativa (CONSERTAR/REVISAR sem movimento; USAR_ESTOQUE→CONSUMO; USAR_OUTRA_MOTO→CANIBALIZACAO + FALTA no doador); resolução de INDETERMINADA exige reclassificação; saldo insuficiente devolve `saldo_apos` sem travar; receita só em VENDA.
- `pendencia_service.reclassificar`: troca categoria; guard S6 (origem física→não-física com `evento_pendente_id` levanta).
- `movimento_service` guards (§11): `_exigir_peca` em consumir/canibalizar; anti-cascata (doador com FALTA aberta da peça); doador inexistente.
- Leituras enriquecidas: chaves novas + filtros por categoria/origem/tratativa.
- Pós-venda `gerar-pendencia`: com/sem `retorno_fisico` (estado da moto); origem derivada de LOJA/CLIENTE.
- Rotas novas (peça/estoque/compra/detalhe/resolver): smoke autenticado (molde dos testes de rota existentes).
- Rastreamento: `fichas_pendencia` + `movimentos_peca` presentes.

## 15. Deploy (bundlado Spec 1 + Spec 2)

Sequência manual (padrão 30/32/33/34 — fora do `build.sh`): **migration 34** (já com a sequence) → **deploy do código** → `python scripts/migrations/motos_assai_35_backfill_pendencias.py --confirmar` → `--check` (gate de cobertura). Até o backfill rodar, pendências legadas não têm ficha; como o shim foi removido, a resolução opera só por `pendencia_id` (fichas criadas pelo backfill). **Sem push sem aval do dono.**

## 16. Pré-mortem (riscos + mitigação)

1. **Remoção do shim antes do backfill**: a página `/resolver` opera por `pendencia_id`; sem ficha (pendência legada não-backfillada), a lista não tem o que resolver. Mitigação: o backfill 35 roda no **mesmo deploy** (§15); `--check` falha o deploy se houver `PENDENTE` sem ficha.
2. **Reclassificação destravando moto** (S6): guard no service + teste.
3. **Saldo negativo por consumo** (S5): aceito; média móvel tem fallback (§8 Spec 1); a tela alerta.
4. **Concorrência na resolução**: `resolver_pendencia` já roda sob `pg_advisory_xact_lock` + double-checked (Spec 1). O orquestrador não adiciona corrida (o movimento é append-only no ledger).
5. **Custo de `saldo`/`custo_medio` por peça na lista de estoque**: `SUM` por peça; aceitável no volume de peças. Cache/materialização = fora do escopo.
6. **Cascata de canibalização** (A→B→A): guard anti-cascata (§11) + teste.
7. **`receita_unitaria` em não-VENDA**: já ignorada pelos átomos; a tela só expõe o campo quando `categoria==VENDA`.

## 17. Fora de escopo (follow-up)

Onboarding tours (Driver.js) das telas novas; PDF do pedido de compra de peça (WeasyPrint); painel/contadores de pendências por categoria/origem/fase + custo de tratativas no Resumo/Dashboard; reclassificar `divergencia`→pendência em massa; cache/materialização de saldo de peça.

## 18. Referências

- Spec 1 (back-end): `docs/superpowers/specs/2026-06-30-motos-assai-estoque-pecas-pendencia-design.md`
- Handoff Spec 1: `docs/superpowers/plans/2026-06-30-motos-assai-estoque-pendencia-spec1-handoff.md`
- Doc do módulo: `app/motos_assai/CLAUDE.md` (seção "Estoque de Peças + Pendência categorizada (Spec 1)")
- Serviços base: `app/motos_assai/services/{pendencia,movimento,peca,compra_peca}_service.py`
- Models: `app/motos_assai/models/{pendencia,peca,estoque_movimento,peca_compra}.py`
- Moldes de UI: `routes/modelos.py`, `routes/compras.py`, `templates/motos_assai/{modelos,compras}/`, `base_motos_assai.html`, `routes/__init__.py`, `decorators.py`
- Estado atual: `routes/pendencias.py`, `routes/pos_venda.py`, `services/pos_venda_service.py`, `services/rastreamento_chassi_service.py`, `static/motos_assai/js/{pendencias_resolver,pos_venda}.js`
