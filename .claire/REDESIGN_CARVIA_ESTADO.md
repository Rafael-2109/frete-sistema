# Redesign CarVia — ESTADO (coletas, recebimento por chassi, portal, flag local_cd)

> Finalidade-fonte: `.claire/rascunho.md`. Este doc rastreia a DECOMPOSICAO em streams,
> as DECISOES travadas e o STATUS de cada stream. Atualizar a cada avanco.
> Ultima atualizacao: 2026-06-18.

## ⏭️ PONTO DE RETOMADA (proxima sessao — LER PRIMEIRO)

> Atualizado 2026-06-18 (migracao + revisao + 2 rodadas de demandas). SUBSTITUI o estado anterior.

**TUDO PUSHADO E DEPLOYADO** (`origin/main` ate `f45c1c610`). Alem da revisao 🔴🟠🟡, foram entregues:
acesso "Recebimento CarVia" (flag operador `usuarios.acesso_recebimento_carvia` + lista `/coletas/recebimento`
sem valores + menu); `carvia_coletas.data_prevista_chegada`; portal cliente redesenhado (CSS `cvp-*`, timeline
5 fases, motos por modelo expansivel, 4 docs escopados, mini-timeline+filtro na lista, `grupo_empresa` no cadastro);
ACESSO INTERNO ao portal (CarVia ve a tela do cliente read-only: `/carvia/portal-usuarios/<uid>/ver`); botao copiar
URL de cadastro. Migrations no prod: `carvia_coleta_nf_unique`, `carvia_recebimento_flag_e_chegada`,
`carvia_portal_grupo_empresa`. 333 testes. **v12 (TM na VIEW pedidos) DEFERIDO** (branches CarVia = cotacoes/pedidos,
sem link a Coleta — precisa decisao: dar `local_cd` a `carvia_pedidos`/`carvia_cotacoes`).
GOTCHA: ALTER/VIEW exigem migration ANTES do push (model carregado toda request; deploy falha sem a coluna).

### Sessao 2026-06-18 (tarde) — 4 frentes novas (decisao Rafael)

Decisao do campo `local_cd` na VIEW pedidos: **opcao B** (coluna propria em `carvia_pedidos`/`carvia_cotacoes`,
so leitura na VIEW, alimentada por propagacao a partir da Coleta). 4 frentes mapeadas; ordem de execucao = **C primeiro**.

- **Frente C — frete dispara na ULTIMA saida (embarque misto VM+TM): IMPLEMENTADO + TESTADO (NAO commitado/deployado).**
  Antes: a 1a saida (qualquer CD) disparava o frete. Agora, em embarque MISTO, so dispara quando TODOS os CDs deram saida.
  - Helper `cds_pendentes_de_saida(embarque)` em `app/utils/local_cd.py` (+ `locais_cd_com_itens_ativos`, `locais_cd_com_saida`).
    Regra: so restringe se misto (itens em >1 `local_cd`); 1 CD = comportamento legado (sem regressao, nao exige `ControlePortaria`).
  - Gate Nacom: REQUISITO 0.1 em `verificar_requisitos_para_lancamento_frete` (`app/fretes/routes.py`) — cobre os **5 call sites**
    de `processar_lancamento_automatico_fretes` (portaria x2, embarque save x2, faturamento Odoo x1) por ser o gate central.
  - Gate CarVia: early-return em `CarviaFreteService._processar` (`app/carvia/services/documentos/carvia_frete_service.py`; importa so de `app/utils` — R1).
  - Testes: `tests/fretes/test_frete_ultima_saida.py` (12). Regressao: **354 verdes** (carvia+fretes+portaria+foundation). Doc: `app/fretes/CLAUDE.md` gate 1.1.
- **Frente A — campo `local_cd` em `carvia_pedidos`/`carvia_cotacoes` + propagacao da Coleta: IMPLEMENTADO + TESTADO.**
  - **PROD (2026-06-18)**: migration de COLUNAS `2026_06_18_carvia_pedido_cotacao_local_cd` APLICADA (2 ALTER + 2 indices + backfill `UPDATE 36` pedidos / `UPDATE 36` cotacoes = TM). A migration VIEW v12 FALHOU na 1a tentativa por **DEADLOCK** (recriar view+MV na mesma transacao com app lendo ambas) -> ROLLBACK (view continua v11, nada quebrou). v12 tornada DEADLOCK-RESILIENTE (2 transacoes separadas + `lock_timeout`); **REAPLICAR no PROD**: `SKIP_DB_CREATE=true DATABASE_URL=$DATABASE_URL_PROD python scripts/migrations/alterar_view_pedidos_v12_carvia_local_cd_da_coleta.py` (ou `psql "$DATABASE_URL_PROD" -f` no .sql). Codigo ja pode subir (colunas existem).
  - Migration DDL `2026_06_18_carvia_pedido_cotacao_local_cd.{sql,py}` (ALTER 2 tabelas + indices parciais TM + backfill TM via numero_nf). APLICADA local.
  - Models `CarviaCotacao`/`CarviaPedido` (`cotacao.py`) ganharam coluna `local_cd` (default VM, server_default).
  - `coleta_service._propagar_local_cd` + `vincular_nf` agora chamam `_propagar_local_cd_para_documentos(numero_nf, local_cd)`
    -> propaga p/ CarviaPedido + CarviaCotacao via `CarviaPedidoItem.numero_nf` (match normalizado). Cobre vincular (manual/auto/lote), editar e marcar_coletada.
  - Migration VIEW `alterar_view_pedidos_v12_carvia_local_cd_da_coleta.{sql,py}` (Partes 2A/2B leem `COALESCE(cot/ped.local_cd, 'VM')`). APLICADA local + REFRESH OK.
  - Schemas JSON `carvia_pedidos`/`carvia_cotacoes` regenerados. Testes: `tests/carvia/test_coleta_propaga_documentos.py` (4).
- **Frente B — acessos VM/TM no sidebar + filtros + impressao por filial: IMPLEMENTADO + TESTADO (NAO commitado).**
  - Rota `listar_embarques` aceita `?local_cd=` (subquery: embarques com >=1 EmbarqueItem ativo do CD; tela exibe TODOS os itens). Indicador de CD no titulo.
  - `_sidebar.html`: 2 entradas "Embarques VM"/"Embarques TM" (icones amber/roxo) apos "Embarques".
  - **Impressao por filial** (decisao Rafael: pagina/capa IGUAL, itens impressos so da filial): `imprimir_embarque` + `imprimir_embarque_completo`
    aceitam `?local_cd=` -> rota filtra lotes (completo) e templates filtram a particao de itens. Botoes "VM"/"TM" em `visualizar_embarque.html`
    (capa + completo) so quando embarque MISTO. Badge VM/TM para itens Nacom NAO feito (baixo valor; itens ja segregados pela filial).
  - Testes: `tests/embarques/test_listar_filtro_local_cd.py` (3) + `test_imprimir_por_filial.py` (3). Regressao total: **373 verdes**.
- **Frente D — mensagem transportadora: PENDENTE (aguarda texto do Rafael).** Unica msg copiavel = Solicitacao de Coleta,
  `app/embarques/routes.py:3279-3417` (`api_gerar_solicitacao_coleta`, 2 variantes), botoes em `visualizar_embarque.html:670-679`.
  Ponto critico: **endereco de coleta HARDCODED "Victorio Marchezine"** — precisa variar por `local_cd`.

### Sessao 2026-06-18 (UF na coleta + auto-vinculo de NF) — PUSHADO na main (`46c62d727`)

Demanda Rafael (refinamento do stream 3): **campo UF por linha da coleta + vinculo automatico de NF**.
- **`CarviaColetaNf.uf`** (VARCHAR(2)): destino rascunho que se CONSOLIDA com a NF real ao vincular
  (`vincular_nf` sobrescreve `cidade_destino`/`uf` com `cidade_destinatario`/`uf_destinatario` da NF
  quando a NF tem o dado — real vence; nunca apaga rascunho com NF vazia).
- **Auto-vinculo** (`_match_unico`): ao adicionar/editar linha (rotas com `auto_vincular=True`), se ha
  **1 unica** CarviaNf ATIVA nao-vinculada para o numero -> liga sozinha ("antecipa"). Ambiguidade nao
  resolve sozinha. `carvia_nf_id` explicito (hidden do preview) tem prioridade e degrada gracioso se a NF
  foi tomada entre preview e submit (linha entra sem vinculo).
- **Preview dinamico**: `lookup_nf` (rota `GET /coletas/lookup-nf`) classifica unico/ambiguo/nenhum; JS no
  `detalhe.html` consulta ao digitar a NF (debounce 400ms), preenche cliente/cidade/UF e marca p/ vincular.
- **Lote**: `vincular_lote` (rota `POST /coletas/<id>/vincular-lote`, botao "Vincular NFs automaticamente").
- Migration `2026_06_18_carvia_coleta_nf_uf` (coluna + backfill uf/cidade das linhas ja vinculadas).
  **APLICADA local + prod** (Rafael). Schemas JSON (`carvia_coleta_nfs.json` + `catalog.json`) regenerados.
- Testes: +9 em `test_coleta_service.py` (consolidacao UF/cidade, auto-vinculo unico, ambiguidade, id
  explicito, resiliencia, lote, lookup). Suite coletas (service 20 + routes 4 + recebimento 7) = 31 verde.

**MIGRATIONS — TODAS APLICADAS NO PROD (`sistema_fretes`, oregon):**
- mig1 `2026_06_17_local_cd_e_chegada_filial` — APLICADA (5 colunas + chegada_filial + 6 indices;
  backfill 100% VM, 0 NULL). Rodada via `SKIP_DB_CREATE=true DATABASE_URL=$DATABASE_URL_PROD`.
- mig2 `carvia_coletas`, mig3 `carvia_coleta_recebimento`, mig4 `carvia_portal_cliente` — as 6
  tabelas JA EXISTIAM no prod (criadas por `db.create_all()` no boot do deploy — indices `ix_*`
  do SQLAlchemy, nao `idx_*` do .sql; tabelas vazias, schema/constraints corretos). NAO re-rodar
  os .sql (criariam indices `idx_*` duplicados).
- v10 `alterar_view_pedidos_v10_local_cd` + v11 `alterar_view_pedidos_v11_carvia_local_cd` —
  APLICADAS (view+MV com local_cd; LATERAL/v9 preservado; 10.925 lotes, dup=0; REFRESH CONCURRENTLY OK).
- **NOVO** `2026_06_18_carvia_coleta_nf_unique` (UNIQUE carvia_nf_id) — APLICADA local + prod (fix bug 🔴).
- **NOVO** `2026_06_18_carvia_coleta_nf_uf` (coluna `uf` + backfill uf/cidade das linhas vinculadas) — APLICADA local + prod.

**GIT / DEPLOY (realidade — a doc antiga errou):**
- `origin/main` JA TEM os 4 commits dos streams (`b6ee30c40`, `40ce506c6`, `6ea58bdc9`, `fa2de999d`).
  So `101aaf0b6` (refinamentos: v11 + autocomplete + filtro embarque) esta **NAO-pushado** (local 1 a frente).
- Deploy do tip `362b909e4` (carrega todo o codigo dos streams) = **`update_failed`** → Render fez
  rollback. **Prod vivo = `633ed0eee`** (ANTERIOR aos streams) → sem outage; codigo dos streams NAO esta no ar.
- **PROXIMO PASSO = RE-DEPLOY** (nao "deploy"): com as migrations aplicadas, re-disparar o deploy do
  codigo dos streams deve subir. Pushar `101aaf0b6` + os fixes desta sessao quando o usuario autorizar.

**FIXES desta sessao (revisao vs prompt — buckets 🔴🟠🟡, working tree NAO commitado):**
- 🔴 UNIQUE(carvia_nf_id) + guard em `vincular_nf` + `sugerir_nf` exclui ja-vinculadas; `editar_coleta`
  re-propaga `local_cd` para NFs vinculadas.
- 🟠 `remover_chassi` so com recebimento EM_RECEBIMENTO; `marcar_coletada`/`conferir_chassi` bloqueiam
  coleta CANCELADA; `_parse_decimal` corrige milhar BR ("1.500"→1500); foto anexa no QR + camera para no
  pagehide + confirm() ao finalizar com ALERTA.
- 🟡 badge VM/TM na impressao de embarque (`imprimir_embarque`/`imprimir_completo`); `local_cd`+`chegada_filial`
  no export Excel do monitoramento.
- Testes: 330 passando (8 novos). Arquivos: `coleta_service.py`, `coleta_recebimento_service.py`,
  `coleta_routes.py`, `coleta.py`, `monitoramento/routes.py`, 3 templates, +migration UNIQUE.

**DEFERIDOS (decisao do usuario pendente):**
- **v12 (derivar TM da Coleta na VIEW pedidos — 4B/4H)**: BLOQUEADO POR DESIGN. As branches CarVia da
  view (`Parte 2A`/`2B`) saem de `carvia_cotacoes`/`carvia_pedidos`, NAO de `carvia_nfs` — nao ha join
  com a NF nem caminho cotacao/pedido → Coleta → local_cd. Derivar TM exige decisao de modelo de dados
  (ex.: dar local_cd a carvia_pedidos/cotacoes, ou outro link). NAO fabricado.
- Filtro por CD em `/pedidos/lista_pedidos`: baixo valor ate o v12 (hoje tudo VM). Adiado.
- Produto (ja mapeados): cotacao por moto no portal (adiada); entrada propria "Recebimento" no nav.

## Decomposicao (5 streams independentes, cada um com seu ciclo)

| # | Stream | Topicos rascunho | Status |
|---|--------|------------------|--------|
| 1 | **Fundacao** — flag `local_cd` + `chegada_filial` + badge | 4A/B/D/G/H/J, 6 | **CONCLUIDO+TESTADO** (PG local; 26 testes) |
| 2 | **Portaria bifurcada** (2 CDs) | 4C/E/F/I + Etapas 5-7 | **CONCLUIDO+TESTADO** (5 testes; invariante Nacom preservado) |
| 3 | **Coletas CarVia** (papel de pao + despesa) | 1 | **CONCLUIDO+TESTADO** (9 testes; 309 carvia+found+port OK) |
| 4 | **Recebimento por chassi** | 2 | **CONCLUIDO+TESTADO** (6 testes; backfill validado; 315 OK) |
| 5 | **Portal do Cliente** + acesso granular | 3, 7, 8 | **CONCLUIDO+TESTADO** (8 testes; isolamento de escopo; 323 OK) |

> **REDESIGN COMPLETO — 5/5 streams + revisao + 2 rodadas de demandas.** 333 testes. TODAS as migrations
> aplicadas no prod e codigo DEPLOYADO (`origin/main` ate `f45c1c610`, deploy live 2026-06-18). Ver o
> PONTO DE RETOMADA no topo para o estado consolidado.

### Refinamentos pos-revisao (2026-06-17)
- (2) **Autocomplete de chassi** no recebimento: `CarviaColetaRecebimentoService.chassis_esperados`
  (esperados ainda nao conferidos) + rota `/coletas/<id>/recebimento/chassis-esperados` + `<datalist>` no scanner.
- (4B) **Flag CarVia na /pedidos/lista_pedidos**: VIEW **v11** (`alterar_view_pedidos_v11_carvia_local_cd.{sql,py}`)
  expoe `local_cd` CarVia = default `VICTORIO_MARCHEZINE` (antes NULL). Refinamento futuro: derivar TM da Coleta.
- (Etapa 6) **Filtro por local na tela do embarque**: `visualizar_embarque.html` ganhou filtro Todos/VM/TM
  (data-local-cd por item + JS).
- (4C) Seletor previo de portaria CONFIRMADO como o correto (= o que o usuario queria).
- (Etapa 1) cotacao por moto: adiada a pedido do usuario.
- Migration nova PENDENTE no prod: `alterar_view_pedidos_v11_carvia_local_cd` (apos a v10).

> Commit streams 1+2: `b6ee30c40` (main, 39 arquivos, +2054; NAO pushado — migrations so no LOCAL).
> Verificacao streams 1+2 (2026-06-17): app carrega (2586 rotas, rota chegada-filial OK);
> 31 testes passando (`tests/test_local_cd_foundation.py` 26 + `tests/portaria/test_portaria_local_cd.py` 5);
> 9/9 templates tocados compilam (macro `badge_local_cd` resolve em render-time);
> schemas JSON regenerados refletem `local_cd`. NAO commitado (working tree na main).

Topico 5 (roteirizacao/cotacao) = nada muda.

## Decisoes travadas (com o usuario, 2026-06-17)

- **Porteiro x CD**: seletor de contexto na tela (sem campo no `Usuario` por enquanto;
  isolar por campo depois se houver problema operacional).
- **Embarque x CD**: 1 embarque pode ter os 2 CDs. `local_cd` no **EmbarqueItem**. Cada
  portaria (registro com seu `local_cd`) preenche saida/data SOMENTE dos itens do seu local
  (Etapa 7). 2 registros de portaria por embarque (1 por local).
- **Default universal** = `VICTORIO_MARCHEZINE` (Nacom sempre VM; CarVia pode TM via Coleta).
- Cores PADRONIZADAS: VM = amarelo/preto (`--amber-50`); TM = roxo/branco (`--semantic-info`).

## Modelo de dados da Fundacao (stream 1) — APLICADO

Constantes: `app/utils/local_cd.py` (VM/TM, LABELS, CHOICES, `normalizar_local_cd`, `label_local_cd`).

Coluna `local_cd VARCHAR(20) NOT NULL DEFAULT 'VICTORIO_MARCHEZINE'` em:
`separacao`, `embarque_itens`, `controle_portaria`, `carvia_nfs`, `entregas_monitoradas`.
Em `entregas_monitoradas` tambem: `chegada_filial BOOL NOT NULL DEFAULT FALSE` + `chegada_filial_em TIMESTAMP`.

Migrations (`scripts/migrations/`, rodadas no PG local):
- `2026_06_17_local_cd_e_chegada_filial.{sql,py}` — colunas + indices parciais + backfill VM.
- `alterar_view_pedidos_v10_local_cd.{sql,py}` — VIEW pedidos v10 + MV: `local_cd` nas 3
  ramificacoes UNION (Nacom = `min(s.local_cd)`; CarVia 2A/2B = NULL ate a Coleta). REFRESH
  CONCURRENTLY preservado (invariante v9). Runner usa cursor DBAPI cru (psycopg2 nao interpola
  o `%` literal de `LIKE '%'`).

Models alterados: `Separacao`, `EmbarqueItem`, `ControlePortaria`, `CarviaNf`,
`EntregaMonitorada`, `Pedido` (VIEW) + `PedidoMV`.

Validacao PG local: Nacom 2336 pedidos = VM, CarVia 8 = NULL; Separacao/Monitoramento/CarviaNf
todos VM; REFRESH CONCURRENTLY OK; 0 NULL.

## Exibicao (stream 1) + Portaria (stream 2) — arquivos entregues

Badge compartilhado: `app/templates/shared/_macros_badges.html` (`badge_local_cd(local_cd, curto=True)`,
nao renderiza nada p/ None) + classes `.badge-local-cd-victorio`/`.badge-local-cd-tenente` em
`app/static/css/components/_badges.css` (@layer components, cores padronizadas + ajuste light).

Consumidores do badge: `pedidos/_partials/_tabela_pedidos.html` (guard `if p.local_cd`),
`carvia/nfs/detalhe.html` + `listar.html`, `embarques/visualizar_embarque.html` (por item),
`monitoramento/listar_entregas.html` + `visualizar_entrega.html` (so `origem != NACOM`),
`portaria/dashboard.html` + `historico.html`.

chegada_filial (topico 6): rota POST `/monitoramento/<id>/chegada-filial` (toggle, guard
`origem != NACOM` -> 400, jsonify, sem abort) + botoes nos templates + protecao no
`app/utils/sincronizar_entregas_carvia.py` (re-sync nunca toca chegada_filial; atualiza
`local_cd` da fonte CarviaNf).

Portaria bifurcada: `app/portaria/forms.py` (`local_cd` HiddenField + filtro histórico),
`app/portaria/models.py` (`veiculos_do_dia(local_cd=)`, `historico(local_cd=)`),
`app/portaria/routes.py` (dashboard com seletor `?local_cd=`, embarques pendentes por local via
EXISTS/NOT EXISTS, saida propaga `data_embarque`/sync SOMENTE itens do local — `Embarque.data_embarque`
agregado preenche-se-vazio; redirect preserva CD), templates dashboard/historico (seletor + badge).
Invariante: embarque 100% Nacom (1 saida VM) = comportamento IDENTICO ao anterior (testado).

Testes: `tests/test_local_cd_foundation.py` (26), `tests/portaria/test_portaria_local_cd.py` (5).

## Coletas (stream 3) — arquivos entregues

Models `CarviaColeta` + `CarviaColetaNf` (`app/carvia/models/coleta.py`): cabecalho (contratado
texto+FK opcional, placa, valor_coleta, local_cd destino, data_prevista, data_prevista_chegada,
data_coletada bool+hora, despesa_id) + linhas (numero_nf rascunho, nome_cliente_rascunho, cidade_destino,
**uf** destino rascunho, qtd_motos, valor_frete, vendedor, transportadora_embarque, carvia_nf_id FK opcional).
Migrations: `2026_06_17_carvia_coletas.{sql,py}` (base), `2026_06_18_carvia_coleta_nf_unique` (UNIQUE
carvia_nf_id), `2026_06_18_carvia_coleta_nf_uf` (coluna `uf` + backfill). TODAS aplicadas local + prod.

Service `CarviaColetaService` (`services/documentos/coleta_service.py`): criar/editar (so RASCUNHO),
linhas, `vincular_nf` (propaga `coleta.local_cd` -> `CarviaNf.local_cd` = fonte CarVia do Stream 1 +
consolida nome rascunho->real **+ cidade/uf <- cidade_destinatario/uf_destinatario da NF**), `sugerir_nf`
(match por numero normalizado), **`_match_unico`** (1 unica NF ATIVA nao-vinculada p/ o numero),
**`lookup_nf`** (status unico/ambiguo/nenhum p/ preview), **`vincular_lote`** (liga todas as linhas com
match unico), auto-vinculo em `adicionar_linha`/`editar_linha` (`auto_vincular=True` + `carvia_nf_id`
opcional, resiliente), `marcar_coletada` (cria CarviaDespesa tipo COLETA a conciliar + propaga local_cd),
cancelar/reabrir. GAP-20: sem delete.

Rotas `routes/coleta_routes.py` (15): listar/criar/detalhe + CRUD linhas + vincular/desvincular +
sugerir-nf (AJAX) + **lookup-nf (AJAX preview)** + **vincular-lote** + coletar/cancelar/reabrir. Templates
`carvia/coletas/{listar,criar,detalhe}.html` (detalhe = grade papel-de-pao: edicao inline + vincular via
AJAX + **coluna/inputs UF + hint dinamico ao digitar a NF + botao "Vincular NFs automaticamente"**). Nav:
botao "Coletas" em `carvia/_quick_nav.html`. `COLETA` adicionado a TIPOS_DESPESA. Schemas JSON gerados.

Testes: `tests/carvia/test_coleta_service.py` (20) + `test_coleta_routes.py` (4).

Pendente p/ stream 3 (futuro, NAO bloqueante): expor local_cd CarVia na VIEW pedidos (hoje NULL —
viria da coleta), e o bridge coleta->CarviaNfVeiculo (chassis) para o Recebimento por chassi (stream 4).

## Recebimento por chassi (stream 4) — arquivos entregues

Models `CarviaColetaRecebimento` (1:1 coleta) + `CarviaColetaRecebimentoChassi` (1 linha/moto:
chassi, modelo, qr_code_lido, foto_s3_key OPCIONAL, carvia_nf_veiculo_id, status VINCULADO|ALERTA)
em `app/carvia/models/coleta_recebimento.py`. Migration `2026_06_17_carvia_coleta_recebimento.{sql,py}`
(LOCAL; PENDENTE prod). Decisoes: unidade = COLETA; escaneio LIVRE + ALERTA; foto sempre opcional.

Service `CarviaColetaRecebimentoService` (`services/documentos/coleta_recebimento_service.py`):
`conferir_chassi` (casa com CarviaNfVeiculo das NFs vinculadas -> VINCULADO|ALERTA), **`reconciliar`
= BACKFILL** (chamado em `CarviaColetaService.vincular_nf` — conferir antes da NF nao quebra),
`nf_recebida`/`resumo_por_nf` (NF recebida = todos chassis VINCULADO), `finalizar`
(CONCLUIDO|COM_DIVERGENCIA), `remover_chassi`, `reabrir`. GOTCHA: usar `_get_recebimento` (query por
coleta_id) — o backref `coleta.recebimento` nao atualiza apos flush (duplica/None stale).

Rotas (5, em coleta_routes.py): scanner page + conferir (AJAX multipart + foto S3) + remover chassi +
finalizar + reabrir. Template `carvia/coletas/recebimento.html` (camera html5-qrcode + manual + foto +
lista + resumo por NF, mobile). Link "Receber por chassi" no detalhe da coleta.

Testes: `tests/carvia/test_coleta_recebimento_service.py` (5, inclui backfill) + 1 render em test_coleta_routes.

## Portal do Cliente (stream 5) — arquivos entregues

Models `CarviaPortalUsuario` + `CarviaPortalUsuarioCnpj` (`app/carvia/models/portal.py`): usuario
EXTERNO isolado (senha werkzeug, status PENDENTE/ATIVO/REJEITADO/BLOQUEADO, escopo CNPJ_DIRETO |
CLIENTE_COMERCIAL). Migration `2026_06_17_carvia_portal_cliente.{sql,py}` (LOCAL; PENDENTE prod).

Blueprint EXTERNO `app/carvia/portal_cliente.py` (`/portal-cliente`, auth PROPRIA por sessao
`carvia_portal_uid` + `@portal_required` — NUNCA usa Flask-Login interno): login, registrar
(auto-registro PENDENTE), dashboard (NFs escopadas + status), detalhe_nf (timeline 5 etapas), cotar
(reuso `CarviaTabelaService().cotar_carvia`). Registrado em `app/carvia/__init__.py:init_app`.

Services: `CarviaPortalAuthService` (registrar/autenticar/aprovar/set_escopo/rejeitar/status),
`CarviaPortalStatusService` (status_nf = 5 etapas cruzando coleta+recebimento+EntregaMonitorada;
listar_nfs/get_nf_escopada SEMPRE escopados por CNPJ = seguranca). Gestao interna:
`routes/portal_admin_routes.py` + template `carvia/portal_admin/listar.html` + nav "Portal Cliente".

Templates `carvia/portal/{login,registrar,dashboard,detalhe_nf,cotar,_header}.html`.
Testes: `tests/carvia/test_portal_cliente.py` (8, inclui INVARIANTE de isolamento de escopo).

## Pipeline de status do portal (topico 7) — mapeamento de fontes

| Etapa portal | Fonte (campo/evento) |
|---|---|
| Coletado | `CarviaColeta.data_coletada` *(novo — stream 3)* |
| Recebido Matriz SP | recebimento por chassi completo *(novo — stream 4)* |
| Embarcado | `Embarque.data_embarque` / saida portaria (existe) |
| Recebido Filial Entrega | `EntregaMonitorada.chegada_filial` *(stream 1)* |
| Entregue | `EntregaMonitorada.entregue` (existe) |

## Reuso/gotchas chave (do mapeamento)

- **"NF na mao" -> NF real**: reusar stub `CarviaNf.tipo_fonte='FATURA_REFERENCIA'` +
  `LinkingService._criar_nf_referencia` + `importacao_service._merge_nf_sobre_stub` (stream 3).
- **Despesa a conciliar**: `CarviaDespesa`/`CarviaCustoEntrega` + `CarviaConciliacaoService`
  (adicionar tipo COLETA) (stream 3).
- **Recebimento por chassi**: padrao HORA/Assai (`qr_code_lido`+`foto_s3_key`, html5-qrcode,
  `chassi_validator`, autocomplete, evento append-only). Chassi ja em `CarviaNfVeiculo`.
  REGRA: fronteira de modulo proibe importar `hora_*`/`assai_*` — REPLICAR no CarVia (stream 4).
- **Portal externo**: NAO existe usuario externo hoje. `app/portal/` e automacao B2B (nome
  enganoso). Cotacao reusavel: `api_cotar_standalone`. "Cliente Comercial" so existe no CarVia
  (`CarviaCliente` 1->N `CarviaClienteEndereco` por CNPJ destino); Motochefe nao tem (stream 5).
- **VIEW pedidos**: DROP+CREATE atomico; `idx_mv_pedidos_lote` UNIQUE obrigatorio p/ REFRESH
  CONCURRENTLY; `tags_pedido` e a ultima coluna de cada branch (ancora p/ adicionar colunas).
