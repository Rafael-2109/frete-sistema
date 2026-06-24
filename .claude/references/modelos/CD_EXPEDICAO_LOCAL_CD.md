<!-- doc:meta
tipo: reference
camada: L2
sot_de: CD de Expedicao (flag local_cd)
hub: .claude/references/INDEX.md
superseded_by: —
atualizado: 2026-06-23
-->
# CD de Expedicao (flag local_cd)

> **Papel:** SOT da flag `local_cd` (Victorio Marchezine / Tenente Marques) — significado, todos os locais que a armazenam, quem e a FONTE, como propaga e a invariante de consistencia. **Abra quando:** for ler/gravar `local_cd`, debugar divergencia de CD, ou mexer na solicitacao de coleta por CD.

## Indice

- [O que e](#o-que-e)
- [Onde vive (tabelas)](#onde-vive-tabelas)
- [Fonte e propagacao](#fonte-e-propagacao)
- [Invariante de consistencia](#invariante-de-consistencia)
- [Mensagem de solicitacao de coleta por CD](#mensagem-de-solicitacao-de-coleta-por-cd)
- [Constantes e helpers](#constantes-e-helpers)
- [Status de portaria agregado por CD](#status-de-portaria-agregado-por-cd)

## O que e

`local_cd` identifica em qual CD fisico um pedido/NF/embarque/entrega e expedido. Dois valores canonicos (VARCHAR(20)):

| Valor | Rotulo | Endereco de coleta |
|-------|--------|--------------------|
| `VICTORIO_MARCHEZINE` | Victorio Marchezine | Rua Victorio Marchezine, nº 61 – Santana de Parnaíba/SP |
| `TENENTE_MARQUES` | Tenente Marques | Est. Tenente Marques, nº 5440 – Santana de Parnaíba/SP |

- **Default universal** = `VICTORIO_MARCHEZINE` (Nacom e historico). Pedidos Nacom sao SEMPRE VM.
- **Pedidos CarVia** podem ter os dois CDs — a flag nasce na **Coleta** (stream Coletas do redesign CarVia).
- Cores padronizadas (macro `badge_local_cd` em `app/templates/shared/_macros_badges.html`): VM = fundo amarelo/texto preto; TM = fundo roxo/texto branco.

## Onde vive (tabelas)

Colunas `local_cd` (`VARCHAR(20)`, `NOT NULL` default VM, exceto onde indicado):

| Tabela | Model | Papel |
|--------|-------|-------|
| `carvia_coletas` | `CarviaColeta` | **FONTE CarVia** — definido na coleta |
| `carvia_nfs` | `CarviaNf` | propagado da coleta |
| `carvia_pedidos` | `CarviaPedido` | propagado da coleta (so LEITURA na VIEW pedidos 2A/2B) |
| `carvia_cotacoes` | `CarviaCotacao` | propagado da coleta |
| `embarque_itens` | `EmbarqueItem` | propagado da coleta (CarVia) / da separacao (Nacom). Usado por badge, **portaria por CD** e impressao VM/TM |
| `entregas_monitoradas` | `EntregaMonitorada` | propagado da coleta (CarVia) / sincronizado (Nacom) |
| `separacao` | `Separacao` | **FONTE Nacom** (sempre VM) |
| `pedidos` | `Pedido` | nullable — vem de `Separacao.local_cd` (Nacom) ou NULL (CarVia) |
| `controle_portaria` | `ControlePortaria` | **NAO** e copia da NF: 1 registro por CD, input do operador na saida (gate "frete dispara na ultima saida") |

## Fonte e propagacao

> **Consolidacao 2026-06-23 (Fases 0-6)**: o `local_cd` do `EmbarqueItem` CarVia agora **nasce correto na CRIACAO** — todo item CarVia e instanciado pelo factory `criar_embarque_item_carvia` (`app/carvia/services/documentos/embarque_carvia_service.py`), que resolve `local_cd` da fonte canonica (NF ATIVA -> cotacao -> DEFAULT) via `resolver_local_cd_carvia`. Fecha a janela "VM-errado" na origem que a propagacao pos-evento NAO cobria (o helper `propagar_local_cd_carvia` casa por `nota_fiscal`, e o provisorio nascia sem NF). A reconciliacao posterior virou **safety-net** dentro do orquestrador unico `reconciliar_embarque_carvia` (passo `local_cd`), chamado por TODAS as portas mutantes (cotacao, pedido, expandir_provisorio, save do embarque, portaria). Teste-guarda `tests/carvia/test_factory_embarque_item_carvia.py::test_guard_*` falha o build se um criador novo nao setar `local_cd`. NAO ha `CHECK` no DB (VM e TM sao ambos validos — nao distinguiria errado de certo; a tranca e o factory + guard). SOT da arquitetura: `docs/superpowers/specs/2026-06-23-carvia-consolidacao-pipeline-expedicao-design.md`.

**Cadeia CarVia** (uma NF de moto): a **Coleta** e a fonte unica. Ao vincular a NF / editar destino / marcar coletada, `local_cd` propaga para todos os locais da NF.

- Ponto unico: `CarviaColetaService._propagar_local_cd_para_documentos(numero_nf, local_cd)` (`app/carvia/services/documentos/coleta_service.py`). Cobre os 3 gatilhos: **vincular NF**, **editar coleta** (re-propaga ao mudar destino), **marcar coletada**.
  - Documentos CarVia (`carvia_pedidos`/`carvia_cotacoes`): match por `CarviaPedidoItem.numero_nf` normalizado.
  - Destinos externos ao CarVia (`embarque_itens` CARVIA-% + `entregas_monitoradas` origem CARVIA): via helper R1-safe `app/utils/propagacao_local_cd.py:propagar_local_cd_carvia` (CarVia nao importa `app/embarques`/`app/monitoramento` direto — ver `app/carvia/CLAUDE.md` R1).
- `EmbarqueItem` CarVia **nasce** com `local_cd` herdado da NF/cotacao (`embarque_carvia_service.expandir_provisorio` + provisorios em `pedido_routes`), em vez do default VM — defesa em profundidade (a coleta re-propaga se o destino mudar depois).
- **Reconciliacao tardia do `EmbarqueItem`** (fix PED-281-1, 2026-06-18): a propagacao da Coleta casa o `EmbarqueItem` **por NF** (`nota_fiscal == numero_nf`); um item **provisorio** (`CARVIA-PED-*`) que recebe a NF **depois** de a Coleta ja ter propagado ficava com o default VM divergente. `app/utils/sincronizar_entregas_carvia.py:sincronizar_entrega_carvia_por_nf` (roda em TODOS os caminhos de anexacao de NF — portaria, form de embarque, import) chama o MESMO helper `propagar_local_cd_carvia` e realinha o item (e a entrega) a `CarviaNf.local_cd`. NAO e um segundo "ponto unico": e reconciliacao a partir da MESMA fonte (CarviaNf), idempotente. Backfill do passado pelo mesmo helper.
- **Reconciliacao INCONDICIONAL no `expandir_provisorio` (fix COL-004, 2026-06-23)**: a reconciliacao acima so' rodava DEPOIS da saida da portaria — `expandir_provisorio` chamava `sincronizar_entrega_carvia_por_nf` apenas dentro do bloco `if embarque.data_embarque`. Com a coleta ainda RASCUNHO (NAO coletada) e o embarque sem saida, o item que recebia a NF ficava com o `local_cd` da criacao (o caminho legado in-place nao o setava; default VM), enquanto a `EntregaMonitorada` (casa por `numero_nf`, nao depende do item ter a NF) ja era reconciliada — divergencia SO' no `embarque_itens`. Agora `expandir_provisorio` chama `propagar_local_cd_carvia(numero_nf, nf_obj.local_cd)` de forma INCONDICIONAL (apos `_recalcular_totais`), idempotente, R1-safe. Teste: `tests/carvia/test_expandir_provisorio_local_cd.py`.

**Cadeia Nacom**: `Separacao` (sempre VM) -> `Pedido.local_cd` / `EmbarqueItem.local_cd` / `EntregaMonitorada`. Sem TM.

## Invariante de consistencia

Para uma mesma NF, `local_cd` **NAO pode divergir** entre os locais que o copiam da fonte (carvia_nfs, carvia_pedidos, carvia_cotacoes, embarque_itens, entregas_monitoradas). Divergencia = bug de propagacao.

- **NAO** setar `local_cd` de `EmbarqueItem`/`EntregaMonitorada` por fora do ponto unico — cria divergencia silenciosa (badge/portaria/impressao no CD errado).
- `controle_portaria.local_cd` esta FORA da invariante (e input do operador por CD, nao copia da NF).
- Backfill historico (corrige passado): `scripts/migrations/2026_06_18_backfill_local_cd_embarque_entrega.py` — idempotente, reusa o helper. Rodar em prod: `SKIP_DB_CREATE=true DATABASE_URL=$DATABASE_URL_PROD python <script> --apply`.
- Origem do bug (2026-06-18): EmbarqueItem nascia default VM e nunca era re-propagado; EntregaMonitorada so era reescrita pelo sincronizador -> 36 embarque_itens + 15 entregas divergentes em prod (corrigido).
  - **2o vetor (mesmo dia, fix PED-281-1)**: NF anexada a item provisorio (`CARVIA-PED-*`) APOS a coleta ja-propagada — a propagacao casa o item por NF e o provisorio ainda nao a tinha. Reconciliado dali pra frente pelo sincronizador de entregas (ver "Fonte e propagacao"); residual aplicado em prod via backfill `--apply` em 2026-06-18 (3 embarque_itens do embarque 5963: NFs 38979/39008/39054 VICTORIO -> TENENTE; divergentes 3 -> 0).
  - **3o vetor (COL-004, 2026-06-23)**: a reconciliacao do `EmbarqueItem` so' rodava no `expandir_provisorio` APOS a saida da portaria (`if embarque.data_embarque`). Coleta TM ainda RASCUNHO + embarque sem saida -> item ficava VM enquanto NF/pedido/cotacao/entrega ja eram TM. Fix de codigo = reconciliacao incondicional no `expandir_provisorio` (ver "Fonte e propagacao"); residual aplicado em prod via backfill `--apply` em 2026-06-23 (2 embarque_itens do embarque 5964: NFs 39059/39010 VICTORIO -> TENENTE; divergentes 2 -> 0).

## Mensagem de solicitacao de coleta por CD

`app/embarques/routes.py:api_gerar_solicitacao_coleta` (botoes "Solicitar Coleta" / "c/ Endereco" em `visualizar_embarque.html`):

- **Cabecalho geral (1x)**: saudacao, data, embarque, total de pallets/peso/valor, horario, ATENCAO, observacoes.
- **Uma secao por CD com itens** (ordem VM -> TM): nome do CD + endereco explicito + subtotal pallets/peso/valor do CD + tabela de pedidos **apenas daquele CD** (com/sem endereco de entrega).
- Itens agrupados por `EmbarqueItem.local_cd` — por isso a propagacao correta da flag e pre-requisito da mensagem classificar certo. Embarque de 1 CD -> 1 secao nomeada.

## Constantes e helpers

`app/utils/local_cd.py` (modulo importavel por TODOS, inclusive CarVia — R1):

- `LOCAL_CD_VICTORIO_MARCHEZINE` / `LOCAL_CD_TENENTE_MARQUES` / `LOCAL_CD_DEFAULT`.
- `LOCAL_CD_LABELS` / `LOCAL_CD_LABELS_CURTO` / `LOCAL_CD_ENDERECOS` (+ `LOCAL_CD_CHOICES` p/ WTForms).
- `normalizar_local_cd(valor)` — entrada livre (form/planilha/import) -> canonico ou None (aceita VM/TM, nome por extenso com/sem acento).
- `label_local_cd(valor, curto=False)` / `endereco_local_cd(valor)`.
- Gate "frete dispara na ULTIMA saida" (embarque misto): `locais_cd_com_itens_ativos` / `locais_cd_com_saida` / `cds_pendentes_de_saida` (duck-typing sobre Embarque, sem importar embarques/portaria).
- `status_portaria_agregado(embarque)` — consolida a portaria de todos os CDs num unico valor canonico (ver secao abaixo).

## Status de portaria agregado por CD

`status_portaria_agregado(embarque)` em `app/utils/local_cd.py` consolida os registros de `ControlePortaria` de todos os CDs de um embarque num unico valor canonico:

| Valor | Significado |
|-------|-------------|
| `SAIU` | Ha registro(s) de portaria e TODOS os CDs com itens ativos ja deram saida |
| `PARCIAL` | Embarque misto: ao menos 1 CD deu saida E ainda falta a saida de outro CD com itens ativos |
| `DENTRO` | Nenhum CD saiu ainda; o status mais avancado entre os registros de portaria e `DENTRO` (algum veiculo entrou) |
| `AGUARDANDO` | Nenhum CD saiu ainda; o status mais avancado entre os registros e `AGUARDANDO` (algum so chegou) |
| `PENDENTE` | Nenhum CD saiu ainda; o status mais avancado entre os registros e `PENDENTE` (registro sem chegada) |
| `SEM_REGISTRO` | Embarque sem nenhum `ControlePortaria` vinculado (ou embarque inexistente) |

**Regra do bucket `PARCIAL`:** acionado quando `locais_cd_com_saida(embarque)` tem ao menos 1 elemento E `cds_pendentes_de_saida(embarque)` tambem tem ao menos 1 elemento — ou seja, o embarque e misto e as saidas estao **incompletas**. O gate "frete dispara na ultima saida" nao dispara enquanto `PARCIAL`.

**Consumidores:**
1. **Coluna "Portaria" na listagem de embarques** — exibe o valor como badge colorido.
2. **Filtro de portaria na listagem** — permite filtrar por um dos 6 valores (com mapeamento `'Sem Registro' → 'SEM_REGISTRO'` no lado do filtro).
3. **Card do detalhe do embarque** — exibe o status agregado no topo do card de portaria.

As properties `Embarque.status_portaria` e `Embarque.locais_cd` (em `app/embarques/models.py`) delegam a este helper e a `locais_cd_com_itens_ativos` respectivamente, expondo os valores diretamente no modelo para uso em templates e serializers.

## Fontes

- Constantes/helpers (incluindo `status_portaria_agregado`): `app/utils/local_cd.py`
- Helper de propagacao externa (R1-safe): `app/utils/propagacao_local_cd.py`
- Propagacao da Coleta (ponto unico): `app/carvia/services/documentos/coleta_service.py`
- Heranca na criacao do EmbarqueItem: `app/carvia/services/documentos/embarque_carvia_service.py`, `app/carvia/routes/pedido_routes.py`
- Sincronizacao de entregas CarVia: `app/utils/sincronizar_entregas_carvia.py`
- Properties `Embarque.status_portaria` / `locais_cd`: `app/embarques/models.py`
- Gate Op. Assai (`verificar_requisitos_op_assai`) + rota manual (`processar_lancamento_frete`): `app/fretes/routes.py`
- Vinculacao pos-saida por CD (`adicionar_embarque` — propaga `data_embarque`/entregas so aos itens do CD do registro; duplicidade por `(embarque_id, local_cd)`): `app/portaria/routes.py`
- Seletores de "embarque pendente de saida POR CD" (fila do dashboard + dropdown do form de chegada + APIs `api_embarques*`): `ControlePortaria.embarques_pendentes_do_cd_query(local_cd)` em `app/portaria/models.py` — criterio 2CD (item ativo do CD + sem saida do CD). NAO usar `data_embarque IS NULL`: o cabecalho agregado e preenchido pela 1a saida de QUALQUER CD e esconderia o embarque misto do CD que ainda nao saiu. Detalhe: `app/portaria/CLAUDE.md` R4.
- Impressao por CD (rotulo de CD no cabecalho + badge por item na secao Nacom): `app/templates/embarques/imprimir_embarque.html`, `app/templates/embarques/imprimir_completo.html`
- Mensagem de coleta por CD: `app/embarques/routes.py` (`api_gerar_solicitacao_coleta`), `app/templates/embarques/visualizar_embarque.html`
- Backfill: `scripts/migrations/2026_06_18_backfill_local_cd_embarque_entrega.py`
- Regra de modulo CarVia: `app/carvia/CLAUDE.md` (entrada `CarviaColeta` / R1)
- Testes: `tests/carvia/test_coleta_propaga_documentos.py`, `tests/test_local_cd_foundation.py`
