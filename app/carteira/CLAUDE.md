<!-- doc:meta
tipo: explanation
camada: L1
sot_de: —
hub: CLAUDE.md
superseded_by: —
atualizado: 2026-06-22
-->
# Carteira — Guia de Desenvolvimento

> **Papel:** guia de desenvolvimento do modulo Carteira — workspace principal do sistema (pedidos agrupados, separacoes, ruptura de estoque, programacao de lote, standby).

## Indice

- [Contexto](#contexto)
- [Estrutura](#estrutura)
- [Regras Criticas](#regras-criticas)
  - [R1: CarteiraPrincipal NAO tem campos de separacao](#r1-carteiraprincipal-nao-tem-campos-de-separacao)
  - [R2: main_routes.py contem apenas dashboard index()](#r2-main_routespy-contem-apenas-dashboard-index)
  - [R3: PreSeparacaoItem e um Adapter](#r3-preseparacaoitem-e-um-adapter)
  - [R4: 11 Blueprints registrados em routes/__init__.py](#r4-11-blueprints-registrados-em-routes__init__py)
  - [R5: agrupamento_service.py usa batch queries (3 queries vs N+1)](#r5-agrupamento_servicepy-usa-batch-queries-3-queries-vs-n1)
  - [R6: carteira_simples/ e pacote modularizado](#r6-carteira_simples-e-pacote-modularizado)
  - [R7: 2 variantes de ruptura — escolher a correta](#r7-2-variantes-de-ruptura-escolher-a-correta)
  - [R8: Template usa `data-pedido` (NAO `data-num-pedido`)](#r8-template-usa-data-pedido-nao-data-num-pedido)
  - [R9: POSTs AJAX precisam de X-CSRFToken](#r9-posts-ajax-precisam-de-x-csrftoken)
  - [R10: Analise de ruptura roda em pool concorrente priorizando visiveis](#r10-analise-de-ruptura-roda-em-pool-concorrente-priorizando-visiveis)
  - [R11: Mapa de pedidos — rotas salvas compartilhadas + botoes da lista](#r11-mapa-de-pedidos-rotas-salvas-compartilhadas-botoes-da-lista)
- [Modelos](#modelos)
- [Padroes do Modulo](#padroes-do-modulo)
  - [Enriquecimento de pedidos (agrupamento_service.py)](#enriquecimento-de-pedidos-agrupamento_servicepy)
  - [Resposta JSON padrao das APIs](#resposta-json-padrao-das-apis)
- [Interdependencias](#interdependencias)
- [Skills Relacionadas](#skills-relacionadas)

## Contexto

~19.9K LOC, 53 arquivos. Exibe pedidos agrupados, gera separacoes, analisa ruptura de estoque, programa lotes (Atacadao/Sendas) e gerencia standby. Campos de tabela vem dos schemas JSON; regras CarteiraPrincipal vs Separacao em `.claude/references/modelos/REGRAS_CARTEIRA_SEPARACAO.md`. `main_routes.py` e apenas o dashboard `index()` — novas rotas em `routes/`.

**LOC**: ~19.9K | **Arquivos**: 53 | **22 JS** (21 templates + 1 static) | **Atualizado**: 22/06/2026

Workspace principal do sistema de fretes. Exibe pedidos agrupados, gera separacoes,
analisa ruptura de estoque, programa lotes (Atacadao/Sendas) e gerencia standby.

> Campos de tabelas: `.claude/skills/consultando-sql/schemas/tables/{tabela}.json`
> Regras CarteiraPrincipal vs Separacao: `.claude/references/modelos/REGRAS_CARTEIRA_SEPARACAO.md`

---

## Estrutura

```
app/carteira/
  ├── routes/                    # 25 APIs (root)
  │   ├── carteira_simples/      # 4 arquivos (dados, separacoes, helpers, __init__)
  │   └── programacao_em_lote/   # 5 arquivos (Atacadao/Sendas: busca, importar, routes, ruptura, __init__)
  ├── services/                  # 7 services (agrupamento, mapa, importacao_nao_odoo, atualizar_dados,
  │                              #   palletizacao — Camada 1 do simulador de conservas, consumido pelo CarVia;
  │                              #   roteirizacao_service + roteirizacao_backends — custo parametrico/selecao
  │                              #   de veiculo/motor de otimizacao, abstracao de backend)
  ├── utils/                     # 3 helpers (separacao, workspace, formatters)
  ├── models.py                  # 7 models (657 linhas)
  ├── models_alertas.py          # AlertaSeparacaoCotada
  ├── models_adapter_presep.py   # Adapter PreSeparacaoItem -> Separacao
  ├── alert_system.py            # AlertaSistemaCarteira (separacoes cotadas pre-sync, integrado com NotificationDispatcher)
  └── main_routes.py             # Apenas dashboard index() — NAO adicionar novas rotas
```

**Templates**: 13 HTML em `app/templates/carteira/` (10 root + 3 em `partials/`)
**JavaScript**: 21 arquivos em `app/templates/carteira/js/` (incluindo `utils/` e `workspace/`) + 1 em `app/static/carteira/js/` (modal-relatorios)
**CSS**: `app/static/css/modules/_carteira.css` + `carteira/carteira-simples.css`

---

## Regras Criticas

### R1: CarteiraPrincipal NAO tem campos de separacao
`expedicao`, `agendamento`, `protocolo`, `agendamento_confirmado`, `rota`, `sub_rota` e
`separacao_lote_id` foram REMOVIDOS de CarteiraPrincipal. Dados vem APENAS de `Separacao`.
Usar `agrupamento_service.py` que enriquece via batch queries.

### R2: main_routes.py contem apenas dashboard index()
227 linhas (limpo na Fase 3). NUNCA adicionar novas rotas em `main_routes.py`.
Novas rotas: criar arquivo em `routes/` e registrar em `routes/__init__.py`.

### R3: PreSeparacaoItem e um Adapter
`models_adapter_presep.py` redireciona para Separacao com `status='PREVISAO'`.
NUNCA importar de `pre_separacao_item` diretamente — usar adapter.

### R4: 11 Blueprints registrados em routes/__init__.py
Blueprint principal `carteira_bp` (`/carteira`) com sub-blueprints:
`carteira_simples_bp`, `standby_bp`, `importante_bp`, `views_nao_odoo_bp`,
`programacao_em_lote_bp`, `alertas_visualizacao_bp`, etc.
Verificar `routes/__init__.py` ANTES de criar novo blueprint.

### R5: agrupamento_service.py usa batch queries (3 queries vs N+1)
`obter_pedidos_agrupados()` carrega rotas, subrotas e separacoes em batch.
NUNCA adicionar queries individuais por pedido no loop de enriquecimento.
Novo dado necessario: adicionar ao batch loading (`_carregar_*_batch`).

### R6: carteira_simples/ e pacote modularizado
Split do monolito (2.1K LOC) em `routes/carteira_simples/`:
- `__init__.py` — Blueprint + imports
- `helpers.py` — validacao JSON, conversao entradas, sync embarque, saidas nao visiveis
- `dados_api.py` — rotas de consulta (dados, autocomplete, rastrear, totais)
- `separacao_api.py` — rotas CRUD (gerar, atualizar qtd, lote, verificar, adicionar itens)
Novas APIs: criar no arquivo do dominio correto (`dados_api.py` ou `separacao_api.py`).

### R7: 2 variantes de ruptura — escolher a correta

| Variante | Arquivo | Quando usar |
|----------|---------|-------------|
| Com cache | `ruptura_api.py` (667L) | Consulta rapida, dados podem ter delay |
| Sem cache | `ruptura_api_sem_cache.py` (575L) | Dados criticos em tempo real |

### R8: Template usa `data-pedido` (NAO `data-num-pedido`)
`agrupados_balanceado.html` usa `data-pedido="{{ pedido.num_pedido }}"`.
No JS, SEMPRE usar `row.dataset.pedido || row.dataset.numPedido` como fallback.
NUNCA usar apenas `dataset.numPedido` — sera `undefined`.

### R9: POSTs AJAX precisam de X-CSRFToken
Todas requisicoes POST/PUT/DELETE devem incluir:
```javascript
headers: { 'X-CSRFToken': document.querySelector('[name=csrf_token]')?.value || '' }
```

### R10: Analise de ruptura roda em pool concorrente priorizando visiveis
`ruptura-estoque.js` (`RupturaEstoqueManager`) NAO processa os pedidos em fila
sequencial. Mantem um **pool de ate `CONCORRENCIA_MAX` (10) analises simultaneas**
contra o endpoint single `/carteira/api/ruptura/sem-cache/analisar-pedido/<num>`,
e um `IntersectionObserver` faz o `selecionarProximoPedido()` escolher sempre um
pedido **visivel no viewport** antes dos nao-visiveis (atualiza os botoes do que o
usuario esta olhando primeiro). Estado por pedido vive em `this.pedidos` (Map:
`status` pendente/analisando/concluido + `visivel`); cada analise libera o slot no
`finally` e re-chama `processarFila()`. NUNCA reverter para fila 1-a-1 nem remover
o observer. Preservar pausar/retomar (clique/modal) e re-enfileiramento de
abortados (volta a `status='pendente'`).

### R11: Mapa de pedidos — rotas salvas compartilhadas + botoes da lista
Mapa em `routes/mapa_routes.py` + `services/mapa_service.py` (template `mapa_pedidos.html`).
Lotes trafegam por `separacao_lote_id`: NACOM (lote real) e CarVia (`CARVIA-NF-{id}`,
`CARVIA-PED-{id}`, `CARVIA-{cot_id}`). As acoes do mapa (salvar rota, simular 3D,
densidade, **cotar frete**) usam `_lotesSelecionados()` — a **selecao viva** dos clientes
marcados — NAO a variavel estatica injetada no load (que vem vazia no fluxo interativo).

- **`cotar_frete_mapa` (`POST /api/cotar-frete`) coteja por LOTE, nao por `num_pedido`**:
  o front (`cotarFrete()`) envia `{lotes: _lotesSelecionados()}` (separacao_lote_id) — antes
  enviava `{pedidos: [num_pedido]}` e o backend resolvia via `Separacao`, **perdendo CarVia**
  (sem registro em `Separacao`, R9 embarques). O endpoint usa `data['lotes']` direto e so cai
  no caminho `pedidos`→`Separacao` como fallback legado. O wizard `cotacao.tela_cotacao` ja
  cota lotes mistos NACOM+CarVia (ramo CarVia do `fechar_frete`). NAO reverter para `num_pedido`.

- **`RotaSalva` e COMPARTILHADA entre todos os usuarios**: `rota_listar`
  (`GET /api/rotas`) NAO filtra por `criado_por`; carregar/excluir/cotar (`/api/rota/<id>`)
  ja operam por id sem dono. Rota = recurso de equipe — NAO re-adicionar filtro por dono.
  `criado_por` (`usuarios.id`, nullable) fica so como autoria/auditoria.
- **Botao "Adicionar a rota" (`btnAddRota`) na lista de pedidos fica SEMPRE habilitado**:
  `adicionarPedidosARota()` (`static/js/pedidos/lista-crud.js`) valida a selecao no
  clique (alerta se 0). `updateCotarButton()` (`lista-checkboxes.js`) atualiza so o
  contador no texto — NAO desabilita (evita o botao preso por JS cacheado). Os demais
  botoes (Cotar/Cotacao Manual/FOB/Ver no Mapa) seguem o padrao habilita-ao-selecionar.
- **Scripts de `lista_pedidos.html` usam o filtro `asset_url`** (`?v=<hash md5>`,
  `app/utils/template_filters.py`), NAO `url_for('static', ...)` puro. Era a causa-raiz
  do botao preso `disabled`: o navegador servia o `lista-checkboxes.js` cacheado (versao
  antiga que setava `disabled`). Ao editar qualquer JS de pedidos, manter `asset_url`
  para o cache invalidar sozinho.
- **"Agrupar c/ rota" no mapa cria uma NOVA rota sem mutar a de origem**: botao chama
  `agruparComRotaSalva()` -> `POST /api/rota/agrupar` (`rota_agrupar`), que une os lotes
  de uma `RotaSalva` existente + os lotes em avaliacao (`_lotesSelecionados()`),
  deduplicando e preservando ordem, e grava uma RotaSalva nova (`status='salva'`). A rota
  base permanece intacta — diferente de `rota_acumular` (`/api/rota/acumular`), que ANEXA
  os lotes a uma rota existente. Ex.: Rota 1 (5) + avaliacao (5) -> Rota 1 intacta + Rota 2 (10).
- **Card de viabilidade CarVia no mapa (2026-06-19)**: `rota_otimizar` (`mapa_routes.py`)
  soma a receita CarVia dos lotes selecionados via
  `app.carvia.services.financeiro.viabilidade_service.receita_carvia_por_lotes` (LAZY import —
  R1: carteira le CarVia, CarVia nao le carteira) e retorna `carvia_receita_total` +
  `viabilidade` (= receita − custo da rota) no JSON de `/api/rota/otimizar`. `mapa_pedidos.html`
  exibe a row `#viabilidadeRow` (card "CarVia (receita)" + "Viabilidade" verde/vermelho) — visivel
  a quem acessa o mapa (NAO admin-only; o admin-only e so o badge no embarque).
- **Motos + NF no pedido_info do mapa (2026-06-19)**: `mapa_service.obter_clientes_para_mapa`
  enriquece cada `pedido` com `qtd_motos` (int) e `nfs` (list[str]) e o `cliente.totais` com
  `qtd_motos` (soma). Fontes: **NACOM** = motos sempre 0 (conservas), `nfs` de `Separacao.numero_nf`
  (distinct, so pos-faturamento); **CarVia** = `qtd_motos` via o service CANONICO CarVia
  `services/documentos/motos_lote_service.qtd_motos_por_lotes(lotes)` (lazy import, R1 — espelha
  `viabilidade_service.receita_carvia_por_lotes`), `nfs` de `CarviaPedidoItem.numero_nf` distinct.
  No front (`mapa_pedidos.html`): o **pointer** ganha selo lateral `🏍 N` (SVG cresce p/ 96px;
  retangulo de peso e omitido quando `peso=0`, ex.: moto) quando `totais.qtd_motos>0`; a **lista
  lateral** e a **InfoWindow** (agora DRY via `renderPedidoSubItem`) mostram chips `🏍`/`NF` por
  pedido (`renderPedidoChips`) + selo de motos no header. Chips usam tokens `--bs-warning/info-*`
  (tematizados light/dark). Contrato JSON aditivo e retrocompativel (front faz `|| 0` / `|| []`).
  Testes: `tests/carteira/test_mapa_motos_nf.py` (NACOM) + `tests/carvia/test_motos_lote_service.py`.
  - **FIX 2026-06-20 (qtd_motos sempre 0)**: a versao 2026-06-19 contava motos por
    `CarviaPedidoItem.modelo_moto_id` — NULL em 100% dos itens de pedido (motos so existem na NF).
    Corrigido: `qtd_motos_por_lotes` resolve `CARVIA-PED` via `numero_nf -> carvia_nf_itens`
    (fonte canonica `_contar_modelos_por_nf`, exclui NF CANCELADA), `CARVIA-{cot}` via
    `qtd_total_motos` (so MOTO), `CARVIA-NF-{id}` direto. Validado em prod: PED-331-1=5, 330-1=12.

---

## Modelos

> Campos: `.claude/skills/consultando-sql/schemas/tables/{tabela}.json`

| Modelo | Tabela | Gotchas |
|--------|--------|---------|
| CarteiraPrincipal | `carteira_principal` | `qtd_saldo_produto_pedido` (NAO `qtd_saldo`). SEM campos de separacao (R1) |
| CarteiraCopia | `carteira_copia` | Espelho para nao-Odoo. Property `baixa_produto_pedido` via FaturamentoProduto |
| SaldoStandby | `saldo_standby` | Filtra pedido INTEIRO da agrupada quando status IN ('ATIVO','BLOQ. COML.','SALDO') |
| PreSeparacaoItem | _(adapter)_ | NAO e tabela real — usa Separacao com status='PREVISAO' (R3) |
| FaturamentoParcialJustificativa | `faturamento_parcial_justificativa` | Model existe em models.py mas API/tela removidos (Fase 3) |
| ControleCruzadoSeparacao | `controle_cruzado_separacao` | Detecta diferencas separacao <-> faturamento |

---

## Padroes do Modulo

### Enriquecimento de pedidos (agrupamento_service.py)
```
_query_agrupamento_base() -> batch load (rotas, subrotas, separacoes)
  -> _enriquecer_pedido_batch() para cada pedido -> sort por rota/subrota/cnpj
```
Adicionar novo campo: incluir na query base, no batch loading se necessario, e no dict de retorno.

### Resposta JSON padrao das APIs
```python
{"success": bool, "data": {}, "error": "mensagem"}
```

---

## Interdependencias

| Importa de | O que | Cuidado |
|-----------|-------|---------|
| `app/separacao/` | `Separacao` | Modelo principal de separacoes (R1) |
| `app/producao/` | `CadastroPalletizacao` | Peso, pallets — JOIN na query base |
| `app/estoque/` | `ServicoEstoqueSimples` | Projecao de estoque (29 dias) |
| `app/localidades/` | `CadastroRota`, `CadastroSubRota` | Batch-loaded em agrupamento_service |
| `app/portal/` | `GrupoEmpresarial` | Identifica Atacadao/Sendas por CNPJ |
| `app/models/` | `Embarque`, `FaturamentoProduto` | FK de embarques e faturamento |

| Exporta para | O que | Cuidado |
|-------------|-------|---------|
| `app/templates/carteira/` | Templates Jinja2 | 13 telas + 21 JS files (templates) + 1 (static) |
| `app/odoo/jobs/` | CarteiraPrincipal model | Sincronizacao incremental importa model |

---

## Skills Relacionadas

| Skill | Opera neste modulo? | Referencia |
|-------|---------------------|-----------|
| `gerindo-expedicao` | Sim | `.claude/skills/gerindo-expedicao/SKILL.md` |
| `cotando-frete` | Parcial (usa rotas) | `.claude/skills/cotando-frete/SKILL.md` |
| `visao-produto` | Parcial (estoque) | `.claude/skills/visao-produto/SKILL.md` |
| `operando-portal-atacadao` | Sim (agendamento) | `.claude/skills/operando-portal-atacadao/SKILL.md` |
| `analise-carteira` | Sim | Subagente `analista-carteira` |
