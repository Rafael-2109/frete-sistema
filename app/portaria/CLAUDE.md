<!-- doc:meta
tipo: explanation
camada: L1
sot_de: —
hub: CLAUDE.md
superseded_by: —
atualizado: 2026-06-19
-->
# Portaria — Guia de Desenvolvimento

> **Papel:** guia de desenvolvimento do modulo Portaria — controle de entrada/saida fisica de veiculos no CD. A **SAIDA** do veiculo e o gatilho que carimba `data_embarque` no Embarque, propaga para a Separacao (por CD) e dispara o lancamento automatico de frete.

## Indice

- [Contexto](#contexto)
- [Estrutura](#estrutura)
- [Blueprint e Rotas](#blueprint-e-rotas)
- [Regras Criticas](#regras-criticas)
  - [R1: status do ControlePortaria e @property, nao coluna](#r1-status-do-controleportaria-e-property-nao-coluna)
  - [R2: SAIDA carimba data_embarque numa cadeia de efeitos](#r2-saida-carimba-data_embarque-numa-cadeia-de-efeitos)
  - [R3: Saida e POR-CD — 2 registros por embarque misto](#r3-saida-e-por-cd-2-registros-por-embarque-misto)
  - [R4: A fila NAO filtra por data_embarque do cabecalho](#r4-a-fila-nao-filtra-por-data_embarque-do-cabecalho)
  - [R5: Saida dispara frete (Nacom/CarVia/Op.Assai) por embarque inteiro](#r5-saida-dispara-frete-nacomcarviaopassai-por-embarque-inteiro)
- [Models](#models)
- [Fluxo da Saida](#fluxo-da-saida)
- [Gotchas](#gotchas)
- [Interdependencias](#interdependencias)
- [Acesso](#acesso)
- [Referencias](#referencias)

## Contexto

4 arquivos Python (~1.7K LOC — `routes.py` e o maior). Dois models: `Motorista` (cadastro) e `ControlePortaria` (tabela `controle_portaria`, hub). O modulo e o ponto onde a expedicao FISICA acontece: registra chegada → entrada → saida do veiculo; a saida carimba `data_embarque` e propaga a cadeia downstream (Separacao, EntregaMonitorada, Frete).

> Campos de tabelas: `.claude/skills/consultando-sql/schemas/tables/{controle_portaria,motoristas}.json`
> CD de expedicao (2-CD, SOT): `app/utils/local_cd.py`
> Embarque (hub que recebe data_embarque): `app/embarques/CLAUDE.md`
> Separacao (recebe data_embarque por CD): `app/separacao/CLAUDE.md`

---

## Estrutura

```
app/portaria/
  ├── __init__.py   # VAZIO
  ├── models.py     # Motorista, ControlePortaria (status = @property)
  ├── forms.py      # ControlePortariaForm, FiltroHistoricoForm (local_cd via seletor de contexto)
  └── routes.py     # portaria_bp — dashboard (fila 2CD), registrar_movimento, vincular/desvincular embarque
```

---

## Blueprint e Rotas

Blueprint `portaria` (`/portaria`), registrado em `app/__init__.py:941`+`:1006`.

| Rota | Funcao | Papel |
|------|--------|-------|
| `GET /` | `dashboard` | **Fila do dia por CD** (2CD-aware) — `?local_cd=` (default VM) |
| `POST /registrar_movimento` | `registrar_movimento` | **ROTA CRITICA** — `acao` ∈ chegada/entrada/saida |
| `POST /adicionar_embarque` | `adicionar_embarque` | Vincula embarque; se ja saiu, REPLICA o carimbo de saida. Duplicidade checada por `(embarque_id, local_cd)` — embarque misto admite 1 registro por CD (R3) |
| `POST /excluir_embarque` | `excluir_embarque` | Desvincula — REVERTE data_embarque (Embarque+Separacao+Entrega) |
| `POST /registrar`/`cadastrar`/`editar`/`excluir` motorista | — | CRUD de motorista |
| `GET /historico` | `historico` | Paginado; status reimplementado em SQL (ver R1) |
| `GET /api/embarques`, `/api/embarques_disponiveis` | — | Selects de embarque — **2CD-aware** via `ControlePortaria.embarques_pendentes_do_cd_query` (param `?local_cd=`) |

---

## Regras Criticas

### R1: status do ControlePortaria e @property, nao coluna
O `status` (SAIU > DENTRO > AGUARDANDO > PENDENTE) e uma `@property` derivada dos pares `data_*`/`hora_*` (chegada/entrada/saida) — **nao existe coluna `status`**. NAO filtrar/ordenar por status no SQL: a fila (`veiculos_do_dia`) ordena em Python e o `historico` **reimplementa** a logica em SQL (IS NULL/IS NOT NULL) para paginar. Manter as duas implementacoes coerentes com a property. Os metodos `registrar_entrada()`/`registrar_saida()` fazem `raise ValueError` se chamados fora de ordem (2a barreira alem dos gates `pode_registrar_*`).

### R2: SAIDA carimba data_embarque numa cadeia de efeitos
Ao registrar saida de um registro com embarque vinculado: (1) `Embarque.data_embarque` recebe `data_saida` **se vazio** (a 1a saida de QUALQUER CD carimba o cabecalho); (2) propaga `data_saida` → `Separacao.data_embarque` dos itens do MESMO CD (bulk update por `separacao_lote_id`, idempotente, roda sempre); (3) sincroniza a entrega por NF + reseta `nf_cd`; (4) dispara frete (R5). `data_saida` e `Date` (nao DateTime) — propaga so o DIA. Erro de sync de NF e engolido (try/except) — NAO aborta a saida.

### R3: Saida e POR-CD — 2 registros por embarque misto
Cada registro de portaria pertence a UM `local_cd` e a saida despacha **somente** os `EmbarqueItem` com `(it.local_cd or VM) == local do registro`. Um embarque MISTO (VM+TM) tem 2 registros de `ControlePortaria` (1 por CD); cada CD carimba seus itens com a sua data de saida. `NULL` em `local_cd` conta como VM. Para Nacom puro (1 registro VM) o efeito e identico ao legado.

### R4: "pendente de saida do CD" NAO usa data_embarque do cabecalho
`Embarque.data_embarque` e cabecalho **agregado**: em embarque misto, a 1a saida de QUALQUER CD ja o preenche enquanto o outro CD segue pendente. O criterio "pendente de saida do CD" e **FONTE UNICA** em `ControlePortaria.embarques_pendentes_do_cd_query(local_cd)`: embarque `ativo` AND existe `EmbarqueItem` ativo do CD AND ainda nao ha registro de saida desse CD. Consumido por: fila do dashboard, dropdown de embarque do form de chegada (`ControlePortariaForm(local_cd_ativo=...)`) e APIs `api_embarques*` (param `?local_cd=`). NAO usar `data_embarque IS NULL` para saber se um CD especifico saiu — escondia o embarque misto do 2o CD apos a 1a saida (bug corrigido 2026-06-22: o operador nao conseguia vincular o embarque ao veiculo do 2o CD para registrar a saida).

### R5: Saida dispara frete (Nacom/CarVia/Op.Assai) por embarque inteiro
A saida (e a vinculacao-apos-saida) chama os hooks de frete: Nacom via `processar_lancamento_automatico_fretes` (de `app.fretes.routes`), CarVia via `CarviaFreteService.lancar_frete_carvia`, Op.Assai via sync proprio. **Importante**: o carimbo/propagacao e POR-CD, mas os hooks de frete recebem o `embarque_id` INTEIRO — a saida de um CD ja dispara tentativa de frete do embarque todo (o gate 2-CD que segura o frete ate a ultima saida vive em `app/fretes`). Todos os hooks estao em try/except silencioso (falha de frete NAO aborta a saida). Desvincular chama `apagar_fretes_sem_cte_embarque` (de `app.embarques.routes`).

---

## Models

> Campos completos: `.claude/skills/consultando-sql/schemas/tables/{controle_portaria,motoristas}.json`

| Model | Tabela | Gotcha principal |
|-------|--------|------------------|
| `ControlePortaria` | `controle_portaria` | `status` e @property (R1). Campos sempre em PARES `data_X`+`hora_X` (chegada/entrada/saida); os `data_*` sao `Date` (hora separada). `embarque_id` NULLABLE (registro pode existir sem embarque). `local_cd` NOT NULL default VM (R3). `veiculos_do_dia` usa joinedload de 2 niveis (anti-N+1, Sentry); `historico` faz `cast` do numero do Embarque (Integer) para String |
| `Motorista` | `motoristas` | `cpf` UNIQUE+index. `buscar_por_cpf` faz triplo `replace` (`.`/`-`/`/`) nos 2 lados antes de comparar — busca por CPF cru |

---

## Fluxo da Saida

`registrar_movimento` (POST) e o **unico** endpoint de chegada/entrada/saida (`acao` no form). **CHEGADA** cria o registro (grava `local_cd` do seletor de contexto). **ENTRADA** exige chegada previa. **SAIDA**: gate de idempotencia (`pode_registrar_saida` — tem entrada e nao tem saida; se ja saiu, flash e nao reprocessa) → carimba cabecalho + propaga por CD + sincroniza entregas + hooks de frete → **1 commit** no fim. O redirect preserva `?local_cd`. `adicionar_embarque` REPLICA esse fluxo quando o embarque e vinculado APOS a saida (codigo duplicado — alterar a regra 2CD exige tocar os 2 pontos). `excluir_embarque` reverte tudo (zera `data_embarque` em Embarque + Separacao de TODOS os itens + EntregaMonitorada).

---

## Gotchas

- **G1 — reset de `nf_cd` tem escopo NF, nao lote**: a saida faz um bulk update em `Separacao` filtrando por `numero_nf` (zera `nf_cd`) — afeta QUALQUER Separacao com aquela NF, fora do `separacao_lote_id`/CD.
- **G2 — CarVia/Op.Assai sao pulados na propagacao** (prefixo `CARVIA-`/`ASSAI-`) — tem hooks proprios de monitoramento (NFs nao estao em `RelatorioFaturamentoImportado`). Mas o **desvincular nao pula** — limpa `data_embarque` de todos os itens.
- **G3 — bulk updates usam `synchronize_session='fetch'`** (objetos Separacao podem ja estar na sessao).
- **G4 — CSRF gracioso em producao**: se a validacao CSRF de `registrar_movimento` lancar excecao, em producao apenas faz flash de aviso e CONTINUA (nao bloqueia).
- **G5 — CarVia: saida sem NF** marca `alerta_saida_sem_nf` na `CarviaCotacao`.

---

## Interdependencias

| Importa de | O que | Pattern |
|-----------|-------|---------|
| `app.utils.local_cd` | `LOCAL_CD_DEFAULT`, `normalizar_local_cd`, `LOCAL_CD_CHOICES/LABELS` (SOT 2CD) | top-level |
| `app.embarques.models` | `Embarque`, `EmbarqueItem` (fila + propagacao por CD) | top-level |
| `app.separacao.models` | `Separacao` (alvo da propagacao de `data_embarque`/`nf_cd`) | top-level |
| `app.fretes.routes` | `processar_lancamento_automatico_fretes` | lazy (hook) |
| `app.embarques.routes` | `apagar_fretes_sem_cte_embarque` | lazy (desvincular) |
| `app.carvia...carvia_frete_service` / `app.utils.sincronizar_entregas*` / `app.monitoramento.models` | hooks frete CarVia, sync entrega, `EntregaMonitorada` | lazy |

> **Exporta** `ControlePortaria` para `embarques` (`obter_dados_portaria_embarque`), `pedidos`, `veiculos`, `api`, `utils.api_helper`.

---

## Acesso

Item de menu separado do grupo Logistica (modal de selecao de CD). O `local_cd` ativo vem do seletor de contexto (querystring → form HiddenField com filtro `normalizar_local_cd or VM`); entrada invalida/vazia cai em VM.

---

## Referencias

| Preciso de... | Documento |
|---------------|-----------|
| Embarque (hub; data_embarque cabecalho) | `app/embarques/CLAUDE.md` |
| Separacao (maquina de estados; nf_cd) | `app/separacao/CLAUDE.md` |
| Frete (gate 2CD da ultima saida) | `app/fretes/CLAUDE.md` |
| 2-CD (SOT) | `app/utils/local_cd.py` + `.claude/references/modelos/CD_EXPEDICAO_LOCAL_CD.md` |
| Campos de qualquer tabela | `.claude/skills/consultando-sql/schemas/tables/{tabela}.json` |
