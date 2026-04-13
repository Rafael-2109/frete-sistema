# Plano de Limpeza e Refatoracao — Modulo Carteira

**Criado em**: 2026-04-12
**Status**: Aguardando execucao
**Escopo total estimado**: ~9.000 LOC removidas + 11 tabelas dropadas + 7 bugs latentes corrigidos + novo `SeparacaoCrudService`

> Este plano foi produzido apos exploracao profunda do modulo e deve ser executado em fases A→B→C→D→E com checkpoints humanos entre sub-fases. Nenhuma fase deve ser commitada sem revisao humana. Commits tematicos por fase apos aprovacao.

---

## Context

O modulo `app/carteira/` acumulou tres categorias de divida tecnica:

1. **Desativacoes nao limpas**: TagPlus foi desligado ha meses, a carteira nao-Odoo inteira parou de ser usada, mas o codigo e as tabelas continuam no repositorio. Como TagPlus escrevia em `CarteiraCopia`/`CadastroCliente`, um `grep` ingenuo ainda mostra "uso ativo" — mas a raiz dos callers e codigo morto.
2. **Orfaos cirurgicos**: classes db.Model sem nenhum instancia (`ControleCruzadoSeparacao`), adaptacao legada substituindo classe em runtime (`PreSeparacaoItem` + adapter), rotas zumbi em `portal/routes.py`, arquivos JS esquecidos, endpoints de cache cujo frontend migrou ha tempo.
3. **CRUD de `Separacao` espalhado em 22 locais de criacao + 24 de alteracao**, com 6 padroes duplicados e **7 bugs latentes** (3 rotas nao propagam para `EmbarqueItem`, bulk `.update()` bypassa event listeners, fallback minimo perde campos normalizados, `synchronize_session` inseguro, etc.).

**Objetivo**: reduzir o modulo em ~50% de LOC relacionados, corrigir os 7 bugs latentes via centralizacao arquitetural, uniformizar contrato de API e deixar o modulo em estado auditavel.

---

## Achados Consolidados

### Grupo 1 — Carteira nao-Odoo + TagPlus (deadcode 100%)

**Raiz do problema**: TagPlus foi desativado ha meses. `CarteiraCopia`/`CadastroCliente` so tem escrita ativa de dentro do modulo TagPlus (`app/integracoes/tagplus/`) ou do importador nao-Odoo — ambos mortos.

| Camada | Arquivos a remover | LOC | Tabelas |
|--------|--------------------|-----|---------|
| TagPlus (modulo inteiro) | `app/integracoes/tagplus/` (12 .py + 8 .md); `app/integracoes/tagplus_integracao.py` | ~5.300 | `tagplus_oauth_token`, `nf_pendente_tagplus` |
| Carteira nao-Odoo — rotas/services | `app/carteira/routes/carteira_nao_odoo_api.py` (367), `importacao_nao_odoo_api.py` (506), `views_nao_odoo.py` (24), `cadastro_cliente_api.py` (300); `app/carteira/services/importacao_nao_odoo.py` (700) | ~1.900 | — |
| Models deprecated | `app/carteira/models.py::CarteiraCopia` (~linhas 162–259, ~100 LOC); `::CadastroCliente` (~527–657, ~130 LOC) | ~230 | `carteira_copia`, `cadastro_cliente` |
| Templates | `app/templates/carteira/{carteira_nao_odoo,importacao_carteira,cadastro_cliente}.html`; `app/templates/integracoes/tagplus_*.html` (7 arquivos) | ~1000 | — |
| Dashboard cards | `app/templates/carteira/dashboard.html:476-494` (3 action-cards nao-odoo) | ~20 | — |
| Menu | `app/templates/base.html:471` (link tagplus) | 1 | — |
| Blueprints | `app/carteira/routes/__init__.py:26-29,51-54`; `app/__init__.py:849,1177-1182` | ~10 | — |
| Scripts | `scripts/adicionar_campos_nf_pendente_tagplus.py`, `scripts/buscar_logs_webhooks.py`, `scripts/migrations/criar_tabela_tagplus_oauth_token.{py,sql}`, `scripts/corrigir_dados_importados_nao_odoo.sql`, `scripts/teste_carteira_nao_odoo.sql`, `scripts/verificar_tokens_tagplus.sql`, `scripts/sql/add_campos_nf_pendente_tagplus.sql` | ~400 | — |
| Catalog/docs | `.claude/skills/consultando-sql/schemas/catalog.json` (entries `cadastro_cliente`, `carteira_copia`, `tagplus_oauth_token`, `nf_pendente_tagplus`); schemas files `.claude/skills/consultando-sql/schemas/tables/{carteira_copia,cadastro_cliente,tagplus_oauth_token,nf_pendente_tagplus}.json`; `app/carteira/CLAUDE.md:51,95` | 0 LOC | — |

**Confirmado via grep**: nao ha imports dessas classes/arquivos em modulos ATIVOS. Unico falso positivo: `app/odoo/services/carteira_service.py` usa a palavra `nao_odoo` como nome de variavel local (dict) — nao importa `CarteiraCopia`.

**Pre-verificacao antes de DROP TABLE** (via `mcp__render__query_render_postgres`):

```sql
SELECT COUNT(*), MAX(data_atualizacao) FROM carteira_copia;
SELECT COUNT(*), MAX(atualizado_em)    FROM cadastro_cliente;
SELECT COUNT(*), MAX(updated_at)       FROM tagplus_oauth_token;
SELECT COUNT(*), MAX(updated_at)       FROM nf_pendente_tagplus;
```

Esperado: zero escritas recentes (> 3 meses atras) ou tabelas vazias.

### Grupo 2 — Deadcode cirurgico adicional

| Item | Evidencia | Acao |
|------|-----------|------|
| `ControleCruzadoSeparacao` (classe+tabela) | Zero instanciacoes; unico uso e `main_routes.py:87` em `count()` protegido por `inspector.has_table(...)` | Remover `models.py:261-301` + `main_routes.py:5,83-87` + DROP `controle_cruzado_separacao` |
| `PreSeparacaoItem` (classe db.Model + adapter) | Classe sobrescrita pelo adapter em runtime; adapter redireciona pra `Separacao`. Tabela fisica sem escrita desde 2025-01-29 | Remover `models.py:440-525,638-657`; deletar `models_adapter_presep.py` (arquivo); DROP `pre_separacao_item`, `pre_separacao_itens` |
| Rotas zumbi em `portal/routes.py` | `agendar_lote` (49-103) e `solicitar_agendamento` (105-389) — zero refs do frontend | Remover funcoes inteiras |
| `comparar_portal` em `portal/routes.py` (722-848) | **ATIVA** (callers JS `workspace-montagem.js:1447`, `modal-separacoes.js:609`) | Migrar fallback `PreSeparacaoItem.query` → `Separacao.query` direto |
| `odoo/services/carteira_service.py:141-152` | Cleanup PreSeparacaoItem legado com try/except | Remover bloco |
| `app/carteira/utils/separacao_utils.py::gerar_separacao_workspace_interno` (195-261) | Zero callers; omite `status` (bug se fosse chamada) | Remover funcao |
| `app/templates/carteira/interface_enhancements.js` | Zero refs; arquivo fora do subdir `js/` | Deletar arquivo |
| `app/carteira/routes/programacao_em_lote/ruptura_utils.py` | Zero imports | Deletar arquivo (confirmar grep no momento) |
| Rotas de cache em `ruptura_api.py` | `analisar_ruptura_pedido:47`, `status_cache_ruptura:386`, `limpar_cache_ruptura_endpoint:417` — frontend so usa `ruptura_api_sem_cache.py` | Remover os 3 endpoints (manter `atualizar-visual-separacao` e `obter_detalhes_pedido_completo`) |
| Tabelas orfas no banco | `snapshot_carteira`, `log_atualizacao_carteira`, `vinculacao_carteira_separacao`, `inconsistencia_faturamento`, `controle_descasamento_nf` — sem classe Python ativa | DROP apos COUNT+MAX check |

### Grupo 3 — Centralizacao CRUD de Separacao

**Inventario**: 22 locais criam Separacao + 24 locais alteram — com 6 padroes duplicados.

| # | Padrao | Locais | Bugs latentes |
|---|--------|--------|---------------|
| 1 | Criar Separacao de CarteiraPrincipal | 5 | Advisory lock em 1 so local; `status` omitido em 1 (`gerar_separacao_workspace_interno` — ja deadcode); `truncar_observacao` inconsistente (`[:700]` hardcoded vs helper); uso de `carregar_pallet_map` batch so em 1 local (N+1 nos outros) |
| 2 | Clonar Separacao para novo produto | 4 | Fallback minimo em `ajuste_sincronizacao_service.py:774,874` perde `rota`, `sub_rota`, `cidade_normalizada`, `uf_normalizada`, `codigo_ibge`, `observ_ped_1` |
| 3 | Bulk update agendamento/protocolo em lote | 6 | **3 dos 6 NAO propagam para EmbarqueItem** (`portal/sendas/routes_solicitacao.py:523`, `portal/atacadao/verificacao_protocolo.py:342`, `separacoes_api.py:467`); portal/sendas usa `.update()` sem `synchronize_session`; `separacoes_api.py:467` esquece `expedicao` |
| 4 | Transicao status PREVISAO<->ABERTO | 3 | Inline em 2 locais sem validacao de transicao |
| 5 | Marcar como FATURADO apos NF | 3 | `processar_faturamento.py:958` usa `.update()` bulk que **bypassa event listeners** |
| 6 | Deletar lote de Separacoes | 4 | **3 dos 4 nao propagam para EmbarqueItem**; so 1 grava `motivo_exclusao` |

**Locais de criacao** (22):
- `routes/separacao_api.py:126,394`
- `routes/carteira_simples/separacao_api.py:257,858`
- `routes/programacao_em_lote/busca_dados.py:368`
- `routes/programacao_em_lote/importar_agendamentos.py:495`
- `utils/separacao_utils.py:261` (deadcode)
- `app/odoo/services/ajuste_sincronizacao_service.py:393,734,774,835,874`
- `app/pedidos/services/sincronizar_items_service.py:349`
- `app/faturamento/services/recuperar_separacoes_perdidas.py:140,220`
- `app/separacao/routes.py:166`
- `scripts/corrigir_multiproduto_separacao.py:129`
- `.claude/skills/gerindo-expedicao/scripts/criando_separacao_pedidos.py:607`

**Locais de alteracao** (24):
- `routes/carteira_simples/separacao_api.py:431,448,559`
- `routes/separacao_api.py:363,520,636,700`
- `routes/separacoes_api.py:467-471`
- `routes/agendamento_confirmacao_api.py:46,107`
- `app/portal/atacadao/verificacao_protocolo.py:342-354`
- `app/portal/sendas/routes_solicitacao.py:523-528`
- `app/pedidos/services/sincronizacao_agendamento_service.py:315`
- `app/pedidos/services/sincronizar_items_service.py:133,276`
- `app/pedidos/edit_routes.py:352`
- `app/odoo/services/ajuste_sincronizacao_service.py:424,649`
- `app/faturamento/services/processar_faturamento.py:937,958`
- `app/faturamento/services/reconciliacao_separacao_nf.py:244`
- `app/faturamento/services/recuperar_separacoes_perdidas.py:223-265`
- `app/separacao/models.py:131-150` (`atualizar_status` classmethod — parcial)
- `app/separacao/models.py:175-190` (`atualizar_cotacao` classmethod)
- `app/separacao/routes.py:289,358`

**Solucao proposta**: `app/separacao/services/separacao_crud_service.py` com 7 metodos centralizando os 6 padroes + `atualizar_qtd_item`. Motivo da localizacao: `app/separacao/` e o modulo dono do model; carteira/portal/odoo/pedidos/faturamento importam daqui sem ciclo.

### Grupo 4 — Boilerplate residual

- ~100 ocorrencias `{"success": False, "error": str(e)}` 500 em 10+ arquivos de `routes/`
- `calcular_criticidade_ruptura` 3x copiado (`ruptura_api.py:272-279`, `ruptura_api_sem_cache.py:529-536`, `programacao_em_lote/routes.py:1728-1735`)
- `current_user.nome` fallback em 9 locais
- `datetime.strptime('%Y-%m-%d').date()` 12+ locais sem try/except
- `mapa_routes.py` usa chave PT `'erro'` em 20+ lugares — inconsistente com restante que usa `'error'`
- `validar_numero_json` restrita a `carteira_simples/helpers.py`
- `atualizar_embarque_item_por_separacao` nao promovido de `carteira_simples/helpers.py` para `utils/separacao_utils.py`
- CSRF inline em 10 locais JS (ignorando `window.Security.getCSRFToken()`)

---

## Proposta de Simplificacao — Fases A..E

> **Ordem**: A → B → C → D → E. Justificativa: A elimina o maior volume sem tocar logica ativa; B remove orfaos restantes; C toca logica ativa e deve vir quando o chao esta limpo; D/E sao cleanup final.

### Fase A — Desativacao em bloco: Carteira nao-Odoo + TagPlus

**A1** — Desregistrar blueprints **ANTES** de remover arquivos (evita erro de import no boot):
- `app/carteira/routes/__init__.py:26-29,51-54` — remover imports e `register_blueprint` de `cadastro_cliente_api`, `importacao_nao_odoo_api`, `carteira_nao_odoo_api`, `views_nao_odoo_bp`
- `app/__init__.py:849,1177-1182` — remover imports e `register_blueprint` de `tagplus_bp`

**A2** — Validar boot: `python -c "from app import create_app; create_app()"` deve funcionar sem erro apos A1.

**A3** — Remover arquivos de rotas/services (em ordem):
- `app/carteira/routes/cadastro_cliente_api.py` (deletar)
- `app/carteira/routes/carteira_nao_odoo_api.py` (deletar)
- `app/carteira/routes/importacao_nao_odoo_api.py` (deletar)
- `app/carteira/routes/views_nao_odoo.py` (deletar)
- `app/carteira/services/importacao_nao_odoo.py` (deletar)

**A4** — Remover modulo TagPlus:
- `app/integracoes/tagplus/` (diretorio inteiro — 12 py + 8 md)
- `app/integracoes/tagplus_integracao.py` (arquivo standalone, 411 LOC)

**A5** — Remover classes de models:
- `app/carteira/models.py` — deletar `CarteiraCopia` (~162-259) e `CadastroCliente` (~527-657)
- Confirmar que nenhum import externo quebra: `grep -rn "from app.carteira.models import.*CarteiraCopia\|from app.carteira.models import.*CadastroCliente" app/`

**A6** — Remover templates:
- `app/templates/carteira/carteira_nao_odoo.html`
- `app/templates/carteira/importacao_carteira.html`
- `app/templates/carteira/cadastro_cliente.html`
- `app/templates/integracoes/tagplus_*.html` (7 arquivos)

**A7** — Remover cards e menu:
- `app/templates/carteira/dashboard.html:476-494` — remover os 3 action-cards nao-odoo
- `app/templates/base.html:471` — remover link tagplus

**A8** — Remover scripts deprecated:
- `scripts/adicionar_campos_nf_pendente_tagplus.py`
- `scripts/buscar_logs_webhooks.py` (confirmar se e so tagplus antes de deletar)
- `scripts/corrigir_dados_importados_nao_odoo.sql`
- `scripts/teste_carteira_nao_odoo.sql`
- `scripts/verificar_tokens_tagplus.sql`
- `scripts/migrations/criar_tabela_tagplus_oauth_token.py` + `.sql`
- `scripts/sql/add_campos_nf_pendente_tagplus.sql`

**A9** — Atualizar docs:
- `.claude/skills/consultando-sql/schemas/catalog.json` — remover 4 entries
- `.claude/skills/consultando-sql/schemas/tables/` — deletar 4 JSONs (`carteira_copia`, `cadastro_cliente`, `tagplus_oauth_token`, `nf_pendente_tagplus`)
- `app/carteira/CLAUDE.md:51,95` — remover referencias a `views_nao_odoo_bp` e `CarteiraCopia`

**A10** — Validacao final fase A:

```bash
source .venv/bin/activate
python -c "from app import create_app; create_app(); print('boot OK')"
grep -rn "CarteiraCopia\|CadastroCliente\|tagplus\|carteira_nao_odoo\|importacao_nao_odoo" app/ --include="*.py" | grep -v test_ | wc -l  # esperado: 0
grep -rn "tagplus\|nao_odoo\|nao-odoo" app/templates/ | grep -v test_ | wc -l  # esperado: 0 (ou so em comentarios)
```

**Impacto A**: ~7.400 LOC removidas; 4 tabelas marcadas para drop em E.

### Fase B — Deadcode cirurgico adicional

**B1** — `ControleCruzadoSeparacao`:
- `app/carteira/models.py:261-301` — deletar classe
- `app/carteira/main_routes.py:5` — remover import
- `app/carteira/main_routes.py:83-87` — remover bloco `controles_pendentes`
- Remover referencias no dashboard template se houver (`app/templates/carteira/dashboard.html`)
- Pre-check: `grep -rn "ControleCruzadoSeparacao" app/` — deve retornar apenas `models.py` e `main_routes.py`

**B2** — `PreSeparacaoItem` (remocao completa):
- `app/portal/routes.py:49-103` — deletar funcao `agendar_lote`
- `app/portal/routes.py:105-389` — deletar funcao `solicitar_agendamento`
- `app/portal/routes.py:722-848` (`comparar_portal`) — substituir `PreSeparacaoItem.query.filter_by(separacao_lote_id=lote_id)` por `Separacao.query.filter_by(separacao_lote_id=lote_id)` direto
- `app/portal/routes.py:13` — remover import `PreSeparacaoItem`
- `app/odoo/services/carteira_service.py:141-152` — remover bloco cleanup (try/except)
- `app/carteira/models.py:440-525` — deletar classe `PreSeparacaoItem(db.Model)`
- `app/carteira/models.py:638-657` — remover bloco de ativacao do adapter
- `app/carteira/models_adapter_presep.py` — deletar arquivo inteiro
- Pre-checks:
  - `grep -rn "from app.carteira.models_adapter_presep" app/` → zero
  - `grep -rn "PreSeparacaoItem" app/` → zero (apos os edits)

**B3** — Arquivos e funcoes orfaos:
- `app/carteira/utils/separacao_utils.py:195-261` — deletar `gerar_separacao_workspace_interno`
- `app/templates/carteira/interface_enhancements.js` — deletar arquivo
- `app/carteira/routes/programacao_em_lote/ruptura_utils.py` — deletar arquivo (confirmar grep antes)
- `app/carteira/routes/ruptura_api.py` — deletar funcoes `analisar_ruptura_pedido` (linha 47), `status_cache_ruptura` (386), `limpar_cache_ruptura_endpoint` (417) + imports nao usados
- Pre-checks: `grep -rn "gerar_separacao_workspace_interno\|interface_enhancements\|analisar-ruptura-pedido\|status-cache-ruptura\|limpar-cache-ruptura" app/` → zero

**B4** — Validacao fase B:

```bash
python -c "from app import create_app; create_app(); print('boot OK')"
python -c "from app.carteira.models import PreSeparacaoItem" 2>&1 | grep -q ImportError && echo "PreSep removida OK"
grep -rn "ControleCruzadoSeparacao\|PreSeparacaoItem\|models_adapter_presep" app/ | wc -l  # esperado: 0
```

Smoke manual:
- `GET /carteira/` — dashboard renderiza
- `GET /portal/api/comparar-portal/<lote>` — JSON valido
- `POST /portal/api/solicitar-agendamento-async` — continua funcionando

**Impacto B**: ~1.000 LOC removidas + 7 tabelas marcadas para drop (`pre_separacao_item`, `pre_separacao_itens`, `controle_cruzado_separacao` + 5 orfas).

### Fase C — `SeparacaoCrudService`

**C1** — Criar service (sem tocar callers antigos ainda):
- `app/separacao/services/__init__.py`
- `app/separacao/services/separacao_crud_service.py`

**API** (assinaturas):

```python
class SeparacaoCrudService:

    @staticmethod
    def criar_de_carteira(
        num_pedido: str,
        lote_id: str,
        itens: list,
        expedicao: date,
        agendamento: date | None = None,
        protocolo: str | None = None,
        status: str = 'ABERTO',
        tipo_envio: str | None = None,
        commit: bool = True,
        advisory_lock: bool = True,
    ) -> list: ...

    @staticmethod
    def clonar_para_novo_produto(
        sep_exemplo,
        cod_produto: str,
        nome_produto: str,
        qtd: float,
        valor_saldo: float,
        peso: float,
        pallet: float,
        commit: bool = True,
    ): ...

    @staticmethod
    def atualizar_agendamento_lote(
        lote_id: str,
        agendamento: date | None = None,
        protocolo: str | None = None,
        agendamento_confirmado: bool | None = None,
        expedicao: date | None = None,
        propagar_embarque: bool = True,
        commit: bool = True,
    ) -> int: ...

    @staticmethod
    def transicionar_status_lote(
        lote_id: str,
        novo_status: str,
        validar_transicao: bool = True,
    ) -> int: ...

    @staticmethod
    def marcar_como_faturado(
        lote_id: str,
        numero_nf: str,
        usar_orm: bool = True,
    ) -> int: ...

    @staticmethod
    def excluir_lote(
        lote_id: str,
        motivo: str | None = None,
        gravar_motivo_na_carteira: bool = False,
        propagar_embarque: bool = True,
    ) -> int: ...

    @staticmethod
    def atualizar_qtd_item(
        separacao_id: int,
        nova_qtd: float,
        propagar_embarque: bool = True,
    ): ...
```

**Gotchas criticos do service**:
- ORM por instancia (nao bulk `.update()`) para disparar `@event.listens_for(Separacao, 'before_insert')`
- Advisory lock: `SELECT pg_advisory_xact_lock(hashtext('separacao_' || lote_id))` antes de criar
- Import lazy de `SincronizadorAgendamentoService` (evita circular — pedidos importa separacao, separacao nao pode importar pedidos)
- `truncar_observacao` vindo do helper global
- `carregar_pallet_map` batch (R5 do CLAUDE.md — sem N+1)
- Respeitar `determinar_tipo_envio` existente em `separacao_utils.py`

**C2** — Migrar Padrao 3 (bulk agendamento) — **prioridade maxima pois corrige 3 bugs latentes**:
- Primeiro os com bug: `portal/sendas/routes_solicitacao.py:523`, `portal/atacadao/verificacao_protocolo.py:342`, `separacoes_api.py:467`
- Depois os ok: `carteira_simples/separacao_api.py:559`, `separacao_api.py:520`, `sincronizacao_agendamento_service.py:315`
- Validacao apos cada migracao: via SQL conferir que `EmbarqueItem` esta em sync com `Separacao` para o lote afetado

**C3** — Migrar Padrao 6 (deletar lote):
- Primeiro com bug: `routes/separacao_api.py:700`, `separacao/routes.py:358`, `pedidos/edit_routes.py:352`
- Depois: `carteira_simples/separacao_api.py:431`

**C4** — Migrar Padrao 5 (marcar faturado):
- Primeiro com bug: `processar_faturamento.py:958`
- Depois: `processar_faturamento.py:937`, `sincronizacao_agendamento_service.py:308`

**C5** — Migrar Padrao 2 (clonar):
- Primeiro fallback minimo: `ajuste_sincronizacao_service.py:774,874`
- Depois: `734,835`, `sincronizar_items_service.py:349`, `carteira_simples/separacao_api.py:858`

**C6** — Migrar Padrao 1 (criar de carteira):
- `routes/separacao_api.py:394` (sem advisory lock hoje), `126`, `carteira_simples/separacao_api.py:257`, `programacao_em_lote/busca_dados.py:368`

**C7** — Migrar Padrao 4 (transicao status):
- `portal/atacadao/verificacao_protocolo.py:346`, `routes/separacao_api.py:636`, `programacao_em_lote/importar_agendamentos.py:346`

**C8** — Validacao fase C:

```bash
python -c "from app.separacao.services import SeparacaoCrudService; print('OK')"
grep -rn "Separacao(" app/ --include="*.py" | grep -v "service\|test\|models\|schema" | wc -l  # deve reduzir drasticamente
```

Smoke manual pos-C:
1. Criar separacao via carteira agrupada → `SeparacaoCrudService.criar_de_carteira` e o unico caller
2. Confirmar agendamento (portal Atacadao) → `EmbarqueItem` em sync via SQL
3. Bulk update Sendas → `EmbarqueItem` em sync via SQL
4. Excluir lote admin → `EmbarqueItem` em sync via SQL
5. Marcar FATURADO via `processar_faturamento` → event listeners disparam

**Impacto C**: ~400-600 LOC consolidadas; 7 bugs latentes corrigidos.

### Fase D — Boilerplate residual

**D1** — Criar helpers:
- `app/carteira/utils/response_helpers.py` — `error_response(e, msg=None)`, `success_response(data)`, decorator `@json_route`
- `app/carteira/utils/ruptura_helpers.py` — `calcular_criticidade_ruptura(qtd_itens, percentual)`
- `app/carteira/utils/auth_helpers.py` — `get_usuario_atual(fallback='Sistema')`
- `app/carteira/utils/json_utils.py` — promover `validar_numero_json` de `carteira_simples/helpers.py`
- Modificar `app/carteira/utils/formatters.py` — adicionar `parse_data_iso(valor, obrigatorio=True)` e `parse_data_br(valor)`
- Modificar `app/carteira/utils/separacao_utils.py` — promover `atualizar_embarque_item_por_separacao` para aqui; adicionar `buscar_separacoes_lote`, `carregar_produtos_pedido_map`, `criar_sincronizador`

**D2** — Migrar callers de `error_response` (~100 locais), `current_user.nome` (~9), `strptime` (~12) em:
`separacao_api.py`, `separacoes_api.py`, `programacao_em_lote/routes.py`, `standby_api.py`, `alertas_visualizacao.py`, `alertas_separacao_api.py`, `importante_api.py`, `mapa_routes.py`, `relatorios_api.py`, `agendamento_confirmacao_api.py`, `carteira_simples/separacao_api.py`.

> Obs: `cadastro_cliente_api.py` ja foi removido na Fase A.

**D3** — Padronizar `mapa_routes.py`: trocar `'erro'` → `'error'`.
- Pre-check antes: `grep -rn "\.erro" app/templates/carteira/` para confirmar que nenhum JS faz `response.erro`.

**D4** — Migrar `calcular_criticidade_ruptura` (3 locais → helper):
- `ruptura_api.py:272-279`
- `ruptura_api_sem_cache.py:529-536`
- `programacao_em_lote/routes.py:1728-1735`

**D5** — CSRF JS inline → `window.Security.getCSRFToken()`:
- `app/templates/carteira/js/modal-separacoes.js:527,794,999`
- `app/templates/carteira/js/carteira-agrupada.js:1386,1482,1584,1836,2201`
- `app/templates/carteira/js/portal-atacadao.js:396,601`
- Pre-check: confirmar ordem de `<script>` em `base.html` (security.js carregado antes desses)

**Impacto D**: ~160 LOC; contrato uniforme; inconsistencia `erro`/`error` corrigida.

### Fase E — Migrations DDL

Cada migration tem **dois artefatos** (regra CLAUDE.md dev): `.py` com `create_app()` + before/after verificacao, `.sql` idempotente para Render Shell (`DROP TABLE IF EXISTS`).

**E1** — `scripts/migrations/drop_deprecated_tagplus_nao_odoo.{py,sql}`:
- Pre-verificacao: `SELECT COUNT(*), MAX(<campo_data>)` via MCP Render em cada tabela
- DROP `carteira_copia`, `cadastro_cliente`, `tagplus_oauth_token`, `nf_pendente_tagplus`

**E2** — `scripts/migrations/drop_deadcode_carteira_tables.{py,sql}`:
- DROP `pre_separacao_item`, `pre_separacao_itens` (plural — legacy), `controle_cruzado_separacao`

**E3** — `scripts/migrations/drop_orphan_carteira_tables.{py,sql}`:
- Verificacao vazio primeiro (COUNT+MAX via MCP Render)
- DROP `snapshot_carteira`, `log_atualizacao_carteira`, `vinculacao_carteira_separacao`, `inconsistencia_faturamento`, `controle_descasamento_nf`

**Rollback**: cada `.py` deve ter funcao `reverter()` com `CREATE TABLE IF NOT EXISTS` minimal (schema documentado em comentarios). Idealmente nao sera necessario — os drops sao de tabelas vazias/mortas.

**Ordem de aplicacao**: dev local primeiro (`python scripts/migrations/...py`), depois producao via MCP Render Shell com os `.sql`.

**Impacto E**: libera ~11 tabelas fisicas + ~25 LOC em models.

---

## Estimativa total

| Fase | Risco | LOC | Tabelas dropadas | Bugs corrigidos |
|------|-------|-----|------------------|-----------------|
| A — Nao-odoo + TagPlus | Baixo (sem callers ativos) | ~7.400 | 4 | 0 |
| B — Deadcode cirurgico | Baixo-medio | ~1.000 | 7 | 0 |
| C — SeparacaoCrudService | Alto (toca logica ativa) | +400 novo / −400 duplicado | 0 | 7 |
| D — Boilerplate | Zero | ~160 | 0 | 1 (mapa erro/error) |
| E — Migrations DDL | Medio (DDL) | ~25 | (drops das 11 acima) | 0 |
| **Total** |  | **~9.000 LOC + novo service** | **11** | **8** |

---

## Arquivos Criticos

**A criar**:
- `app/separacao/services/__init__.py` + `separacao_crud_service.py` — **peca central**
- `app/carteira/utils/response_helpers.py`, `ruptura_helpers.py`, `auth_helpers.py`, `json_utils.py`
- `scripts/migrations/drop_deprecated_tagplus_nao_odoo.{py,sql}`
- `scripts/migrations/drop_deadcode_carteira_tables.{py,sql}`
- `scripts/migrations/drop_orphan_carteira_tables.{py,sql}`

**A modificar**:
- `app/__init__.py` (blueprints tagplus)
- `app/carteira/routes/__init__.py` (blueprints nao-odoo)
- `app/carteira/models.py` (remover `CarteiraCopia`, `CadastroCliente`, `PreSeparacaoItem`, `ControleCruzadoSeparacao`, bloco adapter)
- `app/carteira/main_routes.py` (remover `ControleCruzadoSeparacao`)
- `app/portal/routes.py` (remover `agendar_lote`, `solicitar_agendamento`; migrar `comparar_portal`)
- `app/odoo/services/carteira_service.py` (remover cleanup legado PreSeparacaoItem)
- `app/carteira/utils/separacao_utils.py` (remover `gerar_separacao_workspace_interno`; adicionar helpers)
- `app/carteira/utils/formatters.py` (`parse_data_iso`, `parse_data_br`)
- `app/carteira/CLAUDE.md` (refletir remocoes)
- `app/templates/carteira/dashboard.html` (remover 3 cards)
- `app/templates/base.html` (remover link tagplus)
- `.claude/skills/consultando-sql/schemas/catalog.json` + pasta `tables/`
- ~50 arquivos de rota/service afetados pela Fase C (migracoes de callers CRUD)

**A deletar** (arquivos/diretorios inteiros):
- `app/integracoes/tagplus/` (diretorio)
- `app/integracoes/tagplus_integracao.py`
- `app/carteira/routes/cadastro_cliente_api.py`
- `app/carteira/routes/carteira_nao_odoo_api.py`
- `app/carteira/routes/importacao_nao_odoo_api.py`
- `app/carteira/routes/views_nao_odoo.py`
- `app/carteira/services/importacao_nao_odoo.py`
- `app/carteira/models_adapter_presep.py`
- `app/carteira/routes/programacao_em_lote/ruptura_utils.py` (apos confirmar)
- `app/templates/carteira/{carteira_nao_odoo,importacao_carteira,cadastro_cliente}.html`
- `app/templates/integracoes/tagplus_*.html` (7 arquivos)
- `app/templates/carteira/interface_enhancements.js`
- Scripts `scripts/*tagplus*`, `scripts/*nao_odoo*`, `scripts/migrations/*tagplus*`

**Reuso confirmado (nao recriar)**:
- `determinar_tipo_envio`, `carregar_pallet_map`, `calcular_peso_pallet_com_map` em `app/carteira/utils/separacao_utils.py`
- `window.Security.getCSRFToken()` em `app/static/js/utils/security.js`
- `valor_br`, `numero_br` em `app/utils/template_filters.py`

---

## Verificacao End-to-end

### Checkpoints por fase

**Apos A (bloco nao-odoo/tagplus)**:

```bash
source .venv/bin/activate
python -c "from app import create_app; create_app(); print('boot OK')"
grep -rn "CarteiraCopia\|CadastroCliente\|tagplus\|carteira_nao_odoo\|importacao_nao_odoo" app/ --include="*.py" | grep -v test_ | wc -l  # esperado: 0
```

Smoke:
- Login e boot
- `GET /carteira/` dashboard (sem os 3 cards deprecated)
- Todas as rotas ativas de carteira funcionam
- Menu nao tem link tagplus

**Apos B (deadcode cirurgico)**:

```bash
python -c "from app import create_app; create_app(); print('boot OK')"
python -c "from app.carteira.models import PreSeparacaoItem" 2>&1 | grep -q ImportError && echo "PreSep removida OK"
grep -rn "ControleCruzadoSeparacao\|PreSeparacaoItem\|gerar_separacao_workspace_interno\|interface_enhancements\|models_adapter_presep" app/ | wc -l  # esperado: 0
```

Smoke:
- `GET /portal/api/comparar-portal/<lote>` retorna JSON valido (mudou para usar `Separacao` direto)
- `POST /portal/api/solicitar-agendamento-async` funciona

**Apos C (SeparacaoCrudService)** — bugs corrigidos:
1. Criar separacao via carteira agrupada — `service.criar_de_carteira` e o caller
2. Confirmar agendamento (portal Atacadao) — `EmbarqueItem` em sync via SQL
3. Bulk update Sendas — `EmbarqueItem` em sync via SQL
4. Excluir lote admin — `EmbarqueItem` em sync via SQL
5. Marcar FATURADO via `processar_faturamento` — event listeners disparam

**Apos D (boilerplate)**:

```bash
grep -rn "success.*False.*str(e)" app/carteira/routes/ | wc -l  # cai drasticamente
grep -rn "'erro'" app/carteira/routes/mapa_routes.py  # 0
grep -rn "datetime.strptime" app/carteira/routes/ | grep -v "#" | wc -l  # cai ~15
```

**Apos E (DDL)**:

```bash
# Dev local
python scripts/migrations/drop_deprecated_tagplus_nao_odoo.py
python scripts/migrations/drop_deadcode_carteira_tables.py
python scripts/migrations/drop_orphan_carteira_tables.py
python -c "from app import create_app; create_app()"  # boot final
# Producao: rodar os .sql no Render Shell via MCP
```

---

## Estrategia de execucao

| Fase | Executor sugerido | Formato |
|------|-------------------|---------|
| A | Claude principal com checkpoints humanos por sub-fase (A1→A2→...→A10) | Execucao direta com grep pre-check antes de cada delecao |
| B | Claude principal com grep pre-check documentado | Execucao direta |
| C | Claude principal com revisao humana entre C1, C2, C3, ... C8 | C1 cria service completo; C2-C7 migram 1 padrao por vez, com smoke entre cada |
| D | Subagente `code-simplifier:code-simplifier` | Prompt aponta para este plan file + lista exata de linhas |
| E | Claude principal + usuario executa `.sql` via MCP Render | Dois artefatos por migration (regra CLAUDE.md dev) |

**Principios**:
- Nenhuma fase commita sem revisao humana
- Commits tematicos por fase apos aprovacao
- Grep pre-check antes de cada delecao cross-modulo
- `python -c "from app import create_app; create_app()"` apos cada sub-fase

**Ponto de atencao**: a Fase C e a unica que toca logica ativa em producao. As Fases A, B e E so tocam codigo/tabelas mortos (validar via grep e COUNT antes). A Fase D e cosmetica.

---

## Regras criticas a respeitar

Durante a execucao, respeitar as regras R1-R9 do `app/carteira/CLAUDE.md`:

- **R1**: `CarteiraPrincipal` NAO tem campos de separacao — enriquecimento via `agrupamento_service.py`
- **R2**: `main_routes.py` contem apenas `index()` — nao adicionar rotas novas (a remocao de `controles_pendentes` em B1 mantem isso)
- **R3**: `PreSeparacaoItem` e adapter — **removido inteiramente em B2**, portanto a regra deixa de existir apos B2
- **R4**: 11 blueprints em `routes/__init__.py` — Fase A1 desregistra 4 deles (restam 7)
- **R5**: `agrupamento_service.py` usa batch queries — **nao introduzir N+1** ao criar `SeparacaoCrudService`
- **R6**: `carteira_simples/` e pacote modularizado — respeitar ao migrar callers
- **R7**: 2 variantes de ruptura — Fase B3 remove endpoints de cache da variante com cache
- **R8**: Template usa `data-pedido` (fallback `data-num-pedido`) — nao mexer
- **R9**: POSTs AJAX precisam de `X-CSRFToken` — Fase D5 uniformiza via `window.Security.getCSRFToken()`

Tambem respeitar regra CLAUDE.md dev sobre migrations: DDL exige dois artefatos (`.py` + `.sql`).
