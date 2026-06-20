<!-- doc:meta
tipo: explanation
camada: L1
sot_de: —
hub: CLAUDE.md
superseded_by: —
atualizado: 2026-06-19
-->
# Embarques — Guia de Desenvolvimento

> **Papel:** guia de desenvolvimento do modulo Embarques (CORE) — HUB central da cadeia logistica pos-cotacao. O Embarque agrupa as cargas de um veiculo; nasce da Cotacao, recebe NF do Faturamento, saida da Portaria e dispara o Frete. Ponto de leitura de ~50 modulos.

## Indice

- [Contexto](#contexto)
- [Estrutura](#estrutura)
- [Blueprint e Rotas](#blueprint-e-rotas)
- [Regras Criticas](#regras-criticas)
  - [R1: Embarque nasce SO da cotacao; status setado na rota](#r1-embarque-nasce-so-da-cotacao-status-setado-na-rota)
  - [R2: Totais NAO sao recalculados aqui — listener remoto + service](#r2-totais-nao-sao-recalculados-aqui-listener-remoto-service)
  - [R3: Usar a property `itens` (memoizada), filtrar status ativo](#r3-usar-a-property-itens-memoizada-filtrar-status-ativo)
  - [R4: visualizar_embarque e o HUB e NAO e read-only](#r4-visualizar_embarque-e-o-hub-e-nao-e-read-only)
  - [R5: SAVE = 1 commit no fim + flush antes das sincronizacoes](#r5-save-1-commit-no-fim-flush-antes-das-sincronizacoes)
  - [R6: Cancelamento e SOFT; excluir_item e o unico HARD](#r6-cancelamento-e-soft-excluir_item-e-o-unico-hard)
  - [R7: Tabela de frete CONGELADA (DIRETA no Embarque, FRACIONADA no Item)](#r7-tabela-de-frete-congelada-direta-no-embarque-fracionada-no-item)
  - [R8: 2-CD — local_cd por ITEM; logica mora em app/utils/local_cd.py](#r8-2-cd-local_cd-por-item-logica-mora-em-apputilslocal_cdpy)
  - [R9: separacao_lote_id e VARCHAR; o prefixo roteia o dominio](#r9-separacao_lote_id-e-varchar-o-prefixo-roteia-o-dominio)
  - [R10: EMBARCADO NAO e mais status persistido](#r10-embarcado-nao-e-mais-status-persistido)
  - [R11: Funcoes nao-rota de routes.py sao API publica](#r11-funcoes-nao-rota-de-routespy-sao-api-publica)
- [Models](#models)
- [Fluxo de Vida](#fluxo-de-vida)
- [Integridade 2-CD](#integridade-2-cd)
- [Services](#services)
- [Gotchas](#gotchas)
- [Conexoes na Cadeia](#conexoes-na-cadeia)
- [Interdependencias](#interdependencias)
- [Acesso e Permissao](#acesso-e-permissao)
- [Skills Relacionadas](#skills-relacionadas)
- [Referencias](#referencias)

## Contexto

4 arquivos Python (~4.3K LOC — `routes.py` 3.514, `models.py` 530, `forms.py` 273), 3 services, 12 templates. Modulo CORE: o Embarque e o no central entre Cotacao (upstream) e Portaria/Faturamento/Frete (downstream). 2 models (Embarque, EmbarqueItem) sao importados por ~50 modulos.

> Campos de tabelas: `.claude/skills/consultando-sql/schemas/tables/{embarques,embarque_itens}.json`
> Cotacao (cria o Embarque): `app/cotacao/CLAUDE.md`
> Frete real (consome o Embarque): `app/fretes/CLAUDE.md`
> Logica 2-CD (SOT compartilhado): `app/utils/local_cd.py`

---

## Estrutura

```
app/embarques/
  ├── __init__.py        # VAZIO
  ├── models.py          #  530 LOC — Embarque, EmbarqueItem (SEM event listeners)
  ├── forms.py           #  273 LOC — EmbarqueForm, EmbarqueItemForm
  ├── routes.py          # 3.514 LOC — embarques_bp (~28 rotas) + funcoes nao-rota (R11)
  └── services/
      ├── sync_totais_service.py   # PRIMARIO — sincroniza peso/valor/pallets
      ├── pallet_calculator.py     # admin-only — recalcula SO pallets
      └── docs_carvia_service.py   # PDF consolidado (DANFE+DACTE+Fatura) CarVia
```

**Templates** (`app/templates/embarques/`, 12): `visualizar_embarque.html` (hub, reusado por `editar_embarque`), `listar_embarques.html`, `imprimir_*` (separacao, embarque, completo, docs CarVia), `cancelar_embarque.html`, `dados_tabela.html`.

---

## Blueprint e Rotas

Blueprint `embarques` (`url_prefix=/embarques`), registrado em `app/__init__.py:917` (import) + `:981` (register). Rotas usam `@login_required` + `@require_embarques()` (permissao `pode_acessar_embarques`); `visualizar`/`listar` re-checam `vendedor` item-a-item.

| Grupo | Rotas principais |
|-------|------------------|
| **Hub/CRUD** | `GET\|POST /<id>` (`visualizar_embarque` — hub), `/listar_embarques`, `/<id>/editar` (POST morto), `/<id>/cancelar`, `/novo` (rascunho), `/<id>/novo_item`, `/excluir_item/<item_id>`, `/item/<item_id>/cancelar`, `/<id>/alterar_cotacao` |
| **Impressao** | `/<id>/imprimir_embarque`, `/<id>/imprimir_completo` (por CD), `.../separacao/<lote>/imprimir`, `.../item/<id>/imprimir-docs-carvia`, `/<id>/registrar_impressao` |
| **Sincronizacao** | `/item/<id>/sincronizar_faturamento`, `/item/<id>/confirmar_agendamento`, `/api/sincronizar-totais/<id>` |
| **Admin** | `/admin/desvincular-pedido/<lote>`, `/admin/recalcular-pallets-embarque/<id>`, `/admin/recalcular-pallets-todos` |
| **Atacadao/coleta** | `/api/gerar-pdf-protocolo-atacadao/<item_id>`, `/api/gerar-solicitacao-coleta/<id>` |

---

## Regras Criticas

### R1: Embarque nasce SO da cotacao; status setado na rota
O UNICO ponto de criacao de `Embarque` no fluxo Nacom e `app/cotacao` `fechar_frete` (+ variantes `fechar_frete_grupo`/`incluir_em_embarque` e o caminho manual/FOB `pedidos/routes/cotacao_routes.py`). `Embarque.status` tem so 3 valores — `draft`/`ativo`/`cancelado` — e e setado EXPLICITAMENTE nas rotas (nao ha listener). `numero` e UNIQUE mas NULLABLE: nasce NULL no rascunho e so recebe sequencial (`obter_proximo_numero_embarque`) ao ativar.

### R2: Totais NAO sao recalculados aqui — listener remoto + service
`peso_total`/`valor_total`/`pallet_total` (Embarque) e `peso`/`valor`/`pallets` (Item) sao reescritos por DOIS mecanismos FORA deste model:
1. **Listener remoto** `recalcular_totais_embarque` em `app/separacao/models.py` (`after_update`/`after_delete` de `Separacao`): via SQL cru soma as `Separacao` do lote (`sincronizado_nf=False`) — **mapeamento que engana**: `EmbarqueItem.peso` ← `sum(Separacao.peso)`, `EmbarqueItem.valor` ← `sum(Separacao.valor_saldo)` (nome difere!), `pallets` ← `sum(Separacao.pallet)`. Erro nesse recalc **re-levanta** e DERRUBA o update da Separacao.
2. **Service** `sincronizar_totais_embarque` (`sync_totais_service.py`) — soma os itens ativos para os totais do Embarque, com `commit()` proprio (ver R4).

### R3: Usar a property `itens` (memoizada), filtrar status ativo
A relation real e `_itens` (`lazy='dynamic'`, ou seja query, nao lista). SEMPRE acessar via a property `itens`, que ordena por id e **memoiza** em `self.__dict__['_itens_cache']`. Apos add/remove de item, chamar `invalidar_cache_itens()` — senao serve cache stale. `EmbarqueItem` cancelado PERMANECE na tabela: TODA agregacao (`total_notas`, `itens_ativos`, properties de status) filtra `status == 'ativo'`; replicar esse filtro em qualquer nova agregacao.

### R4: visualizar_embarque e o HUB e NAO e read-only
`GET|POST /embarques/<id>` e o hub (alvo de redirects de cotacao/portaria/save). Logo no inicio (GET **e** POST) chama `sincronizar_totais_embarque(embarque)`, que faz **`commit()`** — ou seja, **abrir a tela reescreve dados no banco**. Nunca tratar como leitura pura. A EDICAO real do embarque acontece no POST `action='save'` DESTE endpoint — NAO em `editar_embarque` (cujo POST so faz `flash('Erro inesperado')`, nome enganoso). `listar_embarques` tambem tem efeito destrutivo: DELETA rascunhos `status='draft'` sem itens e commita.

### R5: SAVE = 1 commit no fim + flush antes das sincronizacoes
O pipeline `action='save'` roda em UMA transacao com unico `commit()` no fim. `db.session.flush()` e OBRIGATORIO depois de atualizar os itens e ANTES das sincronizacoes (senao leem valores antigos). Atualizar `EmbarqueItem` por **ID** (`db.session.get` + checar `embarque_id`), nunca por posicao do FieldList. So `nota_fiscal`/`volumes`/`protocolo_agendamento`/`data_agenda` sao editaveis — CNPJ/peso/valor/tabela/separacao vem da cotacao e NUNCA sao alterados. Transportadora e readonly (form guarda a `razao_social` como STRING, nao o id); trocar so via `alterar_cotacao`.

### R6: Cancelamento e SOFT; excluir_item e o unico HARD
`cancelar_embarque` e `cancelar_item_embarque` marcam `status='cancelado'` (nao deletam) e revertem `Separacao` + cancelam o frete. `excluir_item_embarque` (`/excluir_item/<id>`) e o UNICO hard delete e NAO roda side-effects (nao reverte Separacao, nao cancela frete). Ao reverter, limpar `cotacao_id` da Separacao so se igual a `embarque.cotacao_id` (DIRETA) OU `item.cotacao_id` (FRACIONADA). `cancelar_item` tem guard que `cancelar_embarque` NAO tem: so limpa o lote se nao houver OUTRO embarque ativo com o mesmo lote.

### R7: Tabela de frete CONGELADA (DIRETA no Embarque, FRACIONADA no Item)
DIRETA: a tabela de frete fica congelada nas colunas `tabela_*` + `cotacao_id` do proprio `Embarque`. FRACIONADA: nas colunas `tabela_*` + `cotacao_id` do `EmbarqueItem`. `EmbarqueItem.modalidade` (`FRETE PESO`/`FRETE VALOR`) so faz sentido em FRACIONADA. Alem disso `tipo_carga` aceita **FOB** (alem de DIRETA/FRACIONADA) — deteccao dupla: `tipo_carga=='FOB'` OU transportadora `'FOB - COLETA'`; nao confiar so no campo.

### R8: 2-CD — local_cd por ITEM; logica mora em app/utils/local_cd.py
`EmbarqueItem.local_cd` (NOT NULL, default `VICTORIO_MARCHEZINE`=VM/Nacom; `TENENTE_MARQUES`=TM) e por ITEM — um mesmo Embarque pode ter itens dos 2 CDs (embarque MISTO). TODA a logica 2-CD vive em `app/utils/local_cd.py` (SOT), importado **lazy** e **duck-typed** (NAO importa embarques, para ser usavel ate pelo CarVia). Funcoes: `cds_pendentes_de_saida`, `status_portaria_agregado`, `locais_cd_com_itens_ativos`, `normalizar_local_cd`. As properties `status_portaria`/`locais_cd` so delegam. **`MOTIVO_GATE_CD` e o gate Op.Assai vivem em `app/fretes`, NAO aqui**; Op.Assai (`ASSAI-`) tem ZERO referencias em embarques. Impressao/saida/coleta sao por CD (ver Integridade 2-CD).

### R9: separacao_lote_id e VARCHAR; o prefixo roteia o dominio
`EmbarqueItem.separacao_lote_id` e String(50) (ex `LOTE_20251004_032844_195`), NAO integer. O **prefixo roteia o dominio em TODA a cadeia**: `CARVIA-` = CarVia (sem registro em `Separacao`, hooks proprios de frete/entrega/docs), `ASSAI-` = Op.Assai (hook proprio), resto = Nacom. Propagacao para Separacao e sync de entrega PULAM lotes `CARVIA-`/`ASSAI-`.

### R10: EMBARCADO NAO e mais status persistido
O listener `atualizar_status_automatico` (`app/separacao/models.py`) NAO tem branch que grava `status='EMBARCADO'`; quando a portaria propaga `data_embarque` para a Separacao, o status permanece COTADO/FATURADO. `EMBARCADO` virou **badge visual** e `status_calculado` (property do Pedido VIEW) converte EMBARCADO legado persistido → COTADO. NUNCA escrever codigo que dependa de `Separacao` com status `EMBARCADO`.

### R11: Funcoes nao-rota de routes.py sao API publica
`apagar_fretes_sem_cte_embarque`, `validar_nf_cliente`, `sincronizar_nf_embarque_pedido_completa`, `obter_dados_portaria_embarque` etc. NAO sao rotas — sao funcoes em `routes.py` importadas por outros modulos. `apagar_fretes_sem_cte_embarque` e importada por `cotacao/routes.py` e `portaria/routes.py` (mover/renomear quebra os 3). Ela trata os dominios de forma OPOSTA: Frete Nacom sem CTe e **DELETADO** (sera regerado); `CarviaFrete` sem CTe e **CANCELADO** (cascata em Operacao/Subcontrato) — e NAO faz commit (depende do commit do chamador).

---

## Models

> Campos completos: `.claude/skills/consultando-sql/schemas/tables/{embarques,embarque_itens}.json`. **Sem event listeners neste arquivo** (ver R2).

| Model | Tabela | Gotcha principal |
|-------|--------|------------------|
| `Embarque` | `embarques` | `status` ∈ draft/ativo/cancelado; `numero` unique mas NULLABLE. Muitos campos `#Não utilizado` (placa/motorista/laudo). `transportadora_optante` e SNAPSHOT da cotacao. `__repr__` referencia `self.data` (inexistente → AttributeError). **2 grupos de pallet que nao conversam**: TEORICO (`pallet_total`, via CadastroPalletizacao/listener) vs FISICO/PBR (`nf_pallet_*`, `qtd_pallets_separados/trazidos`, manual) |
| `EmbarqueItem` | `embarque_itens` | `status` ∈ ativo/cancelado (cancelado fica na tabela). `separacao_lote_id` VARCHAR (R9). `local_cd` NOT NULL default VM (R8). `erro_validacao` String(500) com codigos textuais (`NF_PENDENTE_FATURAMENTO`, `NF_DIVERGENTE`, `CLIENTE_NAO_DEFINIDO`) lidos por SUBSTRING. Exclusivos CarVia: `provisorio` (placeholder sem NF — gate do frete CarVia), `carvia_cotacao_id` (sem FK), `hora_agendamento`, `peso_cubado` (NULL=usar peso) |

**Properties calculadas caras** (queries cross-modulo em tempo de LEITURA — N+1 em loop de template; imports lazy p/ evitar ciclo): `status_nfs` (decide por substring em `erro_validacao`: NFs pendentes / Pendente Import. / NFs Lancadas), `status_fretes` (tri-universo Nacom/CarVia/ambiguo; depende de `status_nfs`; consulta `Frete` + `CarviaFrete` excluindo CANCELADO → Pendentes/Emitido/Lancado), `status_portaria` e `locais_cd` (delegam a `local_cd.py`), `receita_carvia`. Item com lote NULL **e** `carvia_cotacao_id` NULL e AMBIGUO de proposito (fica fora dos 2 universos). Auditoria de impressao: `registrar_impressao()` / `marcar_alterado_apos_impressao()` (so marca se ja impresso) / `precisa_reimprimir`.

---

## Fluxo de Vida

1. **VISUALIZAR/SAVE** (`visualizar_embarque`, hub): GET monta o `EmbarqueForm` (datas com guarda anti-corrupcao ano<1900/>2100). POST `action='save'` = pipeline: `apagar_fretes_sem_cte_embarque` → `validate` → atualiza itens por ID → `flush()` → `sincronizar_nf_embarque_pedido_completa` → `validar_cnpj_embarque_faturamento` → `processar_lancamento_automatico_fretes` (Nacom) → sync entregas → **hook CarVia** (`lancar_frete_carvia` + sync entrega CarVia — o save era o unico ponto sem esse hook) → propaga `data_prevista_embarque` para `Separacao`/CarVia → **1 commit**. CR4: item `CARVIA-` provisorio que recebe NF vira `provisorio=False` (senao o frete CarVia nao gera).
2. **CANCELAR** (soft, R6): `status='cancelado'`, remove NFs, cancela itens, reverte Separacao, `cancelar_frete_por_embarque` (Nacom) + cascata CarVia (artefatos FATURADO/CONFERIDO ficam bloqueados).
3. **IMPRIMIR**: por CD via `?local_cd=` (filtra `EmbarqueItem.local_cd`); sem param = todos. `imprimir_completo` exige `data_prevista_embarque` e PULA `CARVIA-` na marcacao de impresso (CarVia nao tem Separacao). `imprimir_separacao`/docs CarVia detectam o dominio pelo prefixo/`carvia_cotacao_id`.

---

## Integridade 2-CD

| Aspecto | Comportamento |
|---------|---------------|
| Gate de frete | `cds_pendentes_de_saida(embarque)` = conjunto VAZIO para embarque de 1 CD (legado, nao exige ControlePortaria); so embarque MISTO recebe a restricao "aguardar ultima saida". O gate em si vive em `app/fretes` |
| Saida | POR-CD: ate 2 `ControlePortaria` (1 por CD). A 1a saida de QUALQUER CD carimba `data_embarque` do cabecalho; a propagacao para Separacao e restrita aos itens daquele `local_cd` |
| Status agregado | `status_portaria_agregado`: SEM_REGISTRO / SAIU / **PARCIAL** (≥1 CD saiu, falta outro — o caso que o gate protege) / DENTRO / AGUARDANDO / PENDENTE. Embarque de 1 CD nunca e PARCIAL |
| `obter_dados_portaria_embarque` | Retorna LISTA (1 dict por CD), `[]` quando vazio — NAO registro unico (antes era `registros[-1]`, que escondia o 2o CD) |
| Impressao/coleta | `?local_cd=` filtra itens; coleta agrupa 1 bloco por CD com endereco proprio (`endereco_local_cd`), ordem VM→TM |

> VM/TM sao siglas de UI; o valor no banco e o nome completo (`VICTORIO_MARCHEZINE`/`TENENTE_MARQUES`). `normalizar_local_cd` retorna `None` (nao default) para entrada nao reconhecida — por isso os call sites so filtram se truthy.

---

## Services

| Service | Papel | Gotcha |
|---------|-------|--------|
| `sync_totais_service` | **PRIMARIO** de sincronia peso/valor/pallets | Chamado AUTOMATICAMENTE no GET de `visualizar_embarque` (commit) + API. PULA itens CarVia |
| `pallet_calculator` (`PalletCalculator`) | Recalculo admin-only de pallets | So mexe em `pallets`/`pallet_total` (peso/valor ficam defasados). **DIVERGE** do sync: filtros e bases diferentes (`ativo=True` vs nao; cadastro vs `Separacao.pallet`) e NAO pula CarVia (pode corromper provisorios). Ferramenta pontual, nao mecanismo de manutencao |
| `docs_carvia_service` | PDF consolidado (DANFE+DACTE+Fatura) de item CarVia | Best-effort (nunca aborta por doc faltante — sinaliza na capa). Resolucao da NF e por `item.nota_fiscal` (lote `CARVIA-NF-` e MINORIA: 9 vs 193 `CARVIA-PED-` em prod) |

---

## Gotchas

- **G1 — visualizar/listar nao sao read-only**: `visualizar_embarque` commita totais a cada chamada; `listar_embarques` deleta rascunhos vazios. Cuidado ao "so abrir" telas em scripts/testes.
- **G2 — gatilhos de frete sao lazy + try/except silencioso**: as 3 funcoes de `fretes.routes` chamadas no save/cancel sao importadas dentro da rota (evita ciclo `embarques↔fretes`, confirmado por `# noqa E402` em `fretes/routes.py:31`) e envoltas em try/except que so loga. **Falha de frete NAO aborta o save** → pode deixar frete orfao/nao-lancado sem erro visivel.
- **G3 — pallet teorico ≠ fisico**: nao usar `pallet_total`/`pallets` (teorico) para NF de pallet/controle PBR; usar o GRUPO 2 (`qtd_pallets_separados/trazidos`, `nf_pallet_*`).
- **G4 — deteccao CarVia e DUPLA**: item e CarVia se `separacao_lote_id` comeca com `CARVIA-` OU tem `carvia_cotacao_id`. Filtrar so pelo prefixo perde itens com cotacao sem lote prefixado. Os 3 pontos (template, sync, docs) devem ficar alinhados.
- **G5 — propagacao de `local_cd` ao anexar NF acontece FORA daqui**: em `app/utils/sincronizar_entregas_carvia.py` (realinha `EmbarqueItem.local_cd` ao `CarviaNf.local_cd`); o routes so chama o sincronizador.

---

## Conexoes na Cadeia

| Direcao | Modulo | Handoff |
|---------|--------|---------|
| UPSTREAM | `cotacao` | `fechar_frete` cria Embarque+Itens (unico ponto). Embarques exporta `apagar_fretes_sem_cte_embarque` de volta (modo alterando_embarque) |
| DOWNSTREAM | `portaria` | `ControlePortaria.embarque_id` (1 por CD); `registrar_saida` carimba `data_embarque` + propaga para Separacao SO dos itens do mesmo `local_cd`. Portaria seleciona embarques `status='ativo' AND data_embarque IS NULL` |
| DOWNSTREAM | `faturamento` | A NF **nao cria** EmbarqueItem — VINCULA ao item existente por `separacao_lote_id`+`pedido` (chave = LOTE; multiplos candidatos → scoring; divergencia → `erro_validacao`) |
| LATERAL | `fretes` | 3 funcoes lazy (`validar_cnpj_embarque_faturamento`, `processar_lancamento_automatico_fretes`, `cancelar_frete_por_embarque`) — ver G2 |
| DOWNSTREAM | `separacao` | `EmbarqueItem.separacao_lote_id` → lote → status COTADO via listener (R10) |

---

## Interdependencias

| Importa de | O que | Pattern |
|-----------|-------|---------|
| `app.cotacao.models` / `app.transportadoras.models` / `app.pedidos.models` / `app.separacao.models` / `app.monitoramento.models` / `app.localidades.models` | `Cotacao`, `Transportadora`, `Pedido`, `Separacao`, `EntregaMonitorada`, `Cidade` | top-level |
| `app.utils.{sincronizar_entregas,embarque_numero,timezone}` / `app.rastreamento.services.qrcode_service` | Helpers de NF/numero/QR | top-level |
| `app.fretes.{routes,models}` | 3 funcoes + `Frete` | **lazy** (ciclo `embarques↔fretes`) |
| `app.utils.local_cd` | gate/status 2-CD | lazy |
| `app.carvia...` / `app.portaria.models` / `app.faturamento.models` | hooks CarVia, `ControlePortaria`, `RelatorioFaturamentoImportado`/`FaturamentoProduto` | lazy |

> **Exporta** `Embarque`/`EmbarqueItem` (leitura) para ~50 modulos (faturamento, portaria, carteira, carvia, monitoramento, pedidos, fretes, odoo, bi). `app/separacao/models.py` importa `Embarque`/`EmbarqueItem` (lazy) no listener de totais (R2).

---

## Acesso e Permissao

Sidebar grupo **Logistica → Operacional → Embarques** (`embarques.listar_embarques`), gated por `sistema_logistica`/`administrador`. Decorator padrao: `@require_embarques()` (`pode_acessar_embarques`). Perfil `vendedor` tem checagem extra item-a-item (`check_vendedor_permission`). Rotas `/admin/*` exigem `current_user.perfil == 'administrador'` (guard manual → 403).

---

## Skills Relacionadas

| Skill / Subagente | Como interage |
|---|---|
| `monitorando-entregas` (skill) | Status pos-faturamento via SQL em `embarques`, `embarque_itens` |
| `analista-performance-logistica` (subagente) | KPIs (concentracao de embarques por dia, lead time) — SQL read-only |
| `cotando-frete` / `gerindo-expedicao` (skills) | Upstream — cotacao que cria o embarque |
| `controlador-custo-frete` (subagente) | Custo real do frete vinculado ao embarque |

---

## Referencias

| Preciso de... | Documento |
|---------------|-----------|
| Cotacao (cria o Embarque) | `app/cotacao/CLAUDE.md` |
| Frete real (CTe, Odoo, pagamento) | `app/fretes/CLAUDE.md` |
| Regras Separacao (status, lote, listener de totais) | `.claude/references/modelos/REGRAS_CARTEIRA_SEPARACAO.md` |
| Cadeia Pedido → Embarque → Frete → Entrega | `.claude/references/modelos/CADEIA_PEDIDO_ENTREGA.md` |
| Status de CD / 2-CD (SOT) | `app/utils/local_cd.py` + `.claude/references/modelos/CD_EXPEDICAO_LOCAL_CD.md` |
| Campos de qualquer tabela | `.claude/skills/consultando-sql/schemas/tables/{tabela}.json` |
