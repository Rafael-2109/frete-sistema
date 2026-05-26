# Relatório de Confronto de Inventário — Design

**Data**: 2026-05-26
**Autor**: Rafael Nascimento + Claude (Opus 4.7)
**Status**: Aprovado — aguarda escrita do plano de implementação
**Ciclo de referência**: INV-2026-05 (snapshot físico de 16/05/2026 — FB/CD/LF)

---

## 1. Visão e objetivos

Replicar dentro do sistema a planilha externa de referência que Rafael usa hoje para
confrontar o **inventário físico** com **movimentações Odoo pós-inventário**, **estoque
Odoo atual**, **estoque do sistema_fretes** e **movimentações registradas no sistema_fretes**.

**Objetivos primários:**
1. Identificar ajustes de estoque indevidos (Odoo vs Movimentação esperada).
2. Identificar diferenças na estrutura dos produtos (BOM) — via consumo vs PA.
3. Apontar ajustes necessários a serem aplicados.

**Não-objetivos (out of scope):**
- Aplicar ajustes diretamente no Odoo a partir do relatório (Rafael continua usando
  o orquestrador existente — skills `ajustando-quant-odoo`, `transferindo-interno-odoo`).
- Substituir os scripts CLI `scripts/inventario_2026_05/monitor/*` — eles continuam
  válidos para operação offline; o relatório novo é a versão web/UI deles.
- Reconciliação financeira (continua via `auditor-financeiro` / módulo `financeiro`).

---

## 2. Arquitetura

Novo módulo Flask `app/inventario/`, isolado, com Blueprint próprio e URL prefix
`/inventario`. Reaproveita conexão Odoo existente (`app.odoo.utils.connection.get_odoo_connection`)
e tabela `movimentacao_estoque` (módulo `estoque`).

```
app/inventario/
├── __init__.py                       Blueprint 'inventario_bp'
├── models.py                         4 modelos (CicloInventario, InventarioBase,
│                                     AjusteManualInventario, InventarioSnapshotOdoo)
├── routes/
│   ├── __init__.py                   imports + register
│   ├── ciclo_routes.py               CRUD ciclo + upload xlsx do inventário base
│   ├── confronto_routes.py           tela principal + exportar xlsx
│   ├── ajustes_manuais_routes.py     CRUD ajustes manuais (HTMX inline)
│   ├── snapshot_routes.py            botão "Atualizar Odoo" + status job
│   └── movimentacoes_routes.py       drill-down (nova aba) + exportar
├── services/
│   ├── confronto_service.py          agregador principal (monta linhas + diffs)
│   ├── inventario_loader.py          parser xlsx FB/CD/LF (3 abas)
│   ├── snapshot_odoo_service.py      refresh estoque + apontamentos + compras Odoo
│   ├── movimentacoes_odoo_service.py drill-down on-demand paginado
│   └── export_xlsx_service.py        gera xlsx com 6 abas
└── workers/
    └── refresh_snapshot_worker.py    job RQ async (fila 'inventario')

app/templates/inventario/
├── confronto.html                    tela principal
├── ciclos.html                       lista + criar/upload
├── ajustes_manuais.html              CRUD inline
└── movimentacoes.html                drill-down em nova aba

app/static/
├── js/inventario/
│   ├── confronto.js                  filtros, ordenação, exportar
│   ├── ajustes_inline.js             HTMX handlers
│   └── movimentacoes.js              paginação + filtros
└── css/modules/_inventario.css       estilos do módulo

scripts/migrations/
├── inventario_base_create_tables.py  DDL Python + verificação
└── inventario_base_create_tables.sql DDL SQL idempotente para Render Shell

tests/inventario/
├── test_confronto_service.py
├── test_inventario_loader.py
├── test_snapshot_odoo_service.py
├── test_movimentacoes_drill_down.py
├── test_export_xlsx.py
└── conftest.py                       fixtures (ciclo, inventario_base, snapshot)
```

**Integrações com sistema:**
- `worker_render.py` linha ~143 — adicionar `inventario` em `--queues` default.
- `worker_render.py` linha ~211 — adicionar `'inventario'` em `FILAS_PESADAS`
  (refresh Odoo dura 2–5min).
- `start_worker_render.sh` linha ~301 — adicionar `inventario` em `--queues`.
- `app/templates/base.html` — link no menu (Operações > Inventário).
- `app/__init__.py` — registrar `inventario_bp`.

---

## 3. Modelos de dados

```python
# app/inventario/models.py
from app import db
from app.utils.timezone import agora_utc_naive


class CicloInventario(db.Model):
    """Ciclo de inventário (ex.: INV-2026-05-16)."""
    __tablename__ = 'inventario_ciclo'

    id            = db.Column(db.Integer, primary_key=True)
    codigo        = db.Column(db.String(50), unique=True, nullable=False)
    data_snapshot = db.Column(db.Date, nullable=False)
    descricao     = db.Column(db.String(200))
    status        = db.Column(db.String(20), default='ATIVO', nullable=False)
    criado_em     = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)
    criado_por    = db.Column(db.String(100))

    __table_args__ = (
        db.Index('ix_inventario_ciclo_status', 'status'),
    )


class InventarioBase(db.Model):
    """Snapshot físico FB/CD/LF (uma linha por cod + empresa)."""
    __tablename__ = 'inventario_base'

    id           = db.Column(db.Integer, primary_key=True)
    ciclo_id     = db.Column(db.Integer, db.ForeignKey('inventario_ciclo.id'),
                             nullable=False, index=True)
    cod_produto  = db.Column(db.String(50), nullable=False, index=True)
    nome_produto = db.Column(db.String(200))
    empresa      = db.Column(db.String(10), nullable=False)   # FB / CD / LF
    qtd          = db.Column(db.Numeric(15, 3), nullable=False, default=0)

    __table_args__ = (
        db.UniqueConstraint('ciclo_id', 'cod_produto', 'empresa',
                            name='uq_inv_base_ciclo_cod_empresa'),
    )


class AjusteManualInventario(db.Model):
    """Ajustes manuais (Planilha2 — preenchido pelo time)."""
    __tablename__ = 'inventario_ajuste_manual'

    id            = db.Column(db.Integer, primary_key=True)
    ciclo_id      = db.Column(db.Integer, db.ForeignKey('inventario_ciclo.id'),
                              nullable=False, index=True)
    cod_produto   = db.Column(db.String(50), nullable=False, index=True)
    nome_produto  = db.Column(db.String(200))
    local         = db.Column(db.String(20))                  # FB/CD/LF (texto livre)
    qtd           = db.Column(db.Numeric(15, 3), nullable=False)
    tipo_ajuste   = db.Column(db.String(20))                  # POSITIVO / NEGATIVO / OK
    observacao    = db.Column(db.String(500))
    criado_em     = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)
    atualizado_em = db.Column(db.DateTime, default=agora_utc_naive,
                              onupdate=agora_utc_naive, nullable=False)
    criado_por    = db.Column(db.String(100))


class InventarioSnapshotOdoo(db.Model):
    """Cache de estoque + apontamentos + compras do Odoo (botão refresh)."""
    __tablename__ = 'inventario_snapshot_odoo'

    id             = db.Column(db.Integer, primary_key=True)
    ciclo_id       = db.Column(db.Integer, db.ForeignKey('inventario_ciclo.id'),
                               nullable=False, index=True)
    cod_produto    = db.Column(db.String(50), nullable=False, index=True)
    nome_produto   = db.Column(db.String(200))

    # estoque Odoo por empresa (stock.quant, location.usage='internal',
    # excluindo locations cujo nome contém 'Indisponivel')
    estoque_fb     = db.Column(db.Numeric(15, 3), default=0)
    estoque_cd     = db.Column(db.Numeric(15, 3), default=0)
    estoque_lf     = db.Column(db.Numeric(15, 3), default=0)

    # apontamentos (período = data_snapshot do ciclo .. now)
    pa_qtd         = db.Column(db.Numeric(15, 3), default=0)   # mrp.production PA
    componente_qtd = db.Column(db.Numeric(15, 3), default=0)   # consumo (positivo no banco)
    compras_qtd    = db.Column(db.Numeric(15, 3), default=0)   # entrada fornecedor externo

    refresh_em     = db.Column(db.DateTime, default=agora_utc_naive)

    __table_args__ = (
        db.UniqueConstraint('ciclo_id', 'cod_produto',
                            name='uq_inv_snapshot_ciclo_cod'),
    )
```

**Estimativa de volume:**
- `inventario_ciclo`: ~10 linhas (1 ciclo por semestre)
- `inventario_base`: ~3.000 linhas por ciclo (1.000 produtos × 3 empresas)
- `inventario_ajuste_manual`: ~200 linhas por ciclo
- `inventario_snapshot_odoo`: ~1.000 linhas por ciclo (1 por produto)

Total < 25K linhas após 5 anos — sem necessidade de particionamento.

---

## 4. Routes

### 4.1 ciclo_routes.py
```
GET  /inventario/ciclos                    → lista de ciclos (ciclos.html)
GET  /inventario/ciclos/novo               → form criar ciclo
POST /inventario/ciclos/novo               → cria CicloInventario
POST /inventario/ciclos/<id>/upload        → recebe xlsx (multipart) — invoca
                                              inventario_loader.parse_e_inserir
POST /inventario/ciclos/<id>/arquivar      → status=ARQUIVADO
```

### 4.2 confronto_routes.py (rota principal)
```
GET  /inventario/confronto                 → redirect → último ciclo ATIVO
GET  /inventario/confronto/<ciclo_id>      → confronto.html
GET  /inventario/confronto/<ciclo_id>.xlsx → export xlsx (6 abas)
GET  /inventario/confronto/<ciclo_id>/api  → JSON (linhas) — usado por filtros JS
```

### 4.3 ajustes_manuais_routes.py
```
GET    /inventario/ajustes/<ciclo_id>              → lista (HTMX target)
POST   /inventario/ajustes/<ciclo_id>              → cria
PUT    /inventario/ajustes/<ciclo_id>/<aj_id>      → edita
DELETE /inventario/ajustes/<ciclo_id>/<aj_id>      → remove
POST   /inventario/ajustes/<ciclo_id>/import       → upload xlsx em massa
```

### 4.4 snapshot_routes.py
```
POST /inventario/snapshot/<ciclo_id>/refresh       → enfileira job RQ → retorna job_id
GET  /inventario/snapshot/<ciclo_id>/status        → polling do job (status, last_refresh)
```

### 4.5 movimentacoes_routes.py
```
GET /inventario/movimentacoes                      → tela drill-down (movimentacoes.html)
GET /inventario/movimentacoes/api                  → JSON paginado (filtros)
GET /inventario/movimentacoes/export.xlsx          → exporta filtrados (limit 5K linhas)
```

**Filtros aceitos por `movimentacoes_routes`:**
- `cod` (cod_produto, obrigatório para drill-down)
- `empresa` (FB/CD/LF, opcional — se vazio retorna todas)
- `tipo` (ESTOQUE/PRODUCAO — ESTOQUE retorna todos os tipos; PRODUCAO agrupa por MO)
- `data_inicio` (ISO date, default = ciclo.data_snapshot)
- `data_fim` (ISO date, default = today)
- `origem`, `destino` (substring match em location.name)
- `usuario` (substring match em create_uid.name)
- `page` (1-based), `page_size` (100/500/1000)

---

## 5. Services

### 5.1 confronto_service.py

Função principal: `ConfrontoService.montar_linhas(ciclo_id: int) → List[LinhaConfronto]`

Fluxo:
```
1. ciclo = CicloInventario.query.get(ciclo_id)
2. data_inicio = ciclo.data_snapshot

3. AGREGAÇÃO inventario_base (por cod_produto, pivot empresa):
   SELECT cod_produto, nome_produto,
          SUM(qtd) FILTER (WHERE empresa='FB') AS inv_fb,
          SUM(qtd) FILTER (WHERE empresa='CD') AS inv_cd,
          SUM(qtd) FILTER (WHERE empresa='LF') AS inv_lf
   FROM inventario_base
   WHERE ciclo_id = :ciclo_id
   GROUP BY cod_produto, nome_produto

4. AGREGAÇÃO movimentacao_estoque (por cod_produto, considerando UnificacaoCodigos):
   -- Resolver código raiz primeiro
   WITH codigos AS (
       SELECT DISTINCT cod_produto, COALESCE(cod_produto_raiz, cod_produto) AS raiz
       FROM movimentacao_estoque
       WHERE ativo=true AND data_movimentacao >= :data_inicio
   )
   SELECT raiz AS cod_produto,
          SUM(qtd_movimentacao) FILTER (WHERE tipo_movimentacao='ENTRADA'
                                         AND local_movimentacao='COMPRA')   AS compras_sist,
          SUM(qtd_movimentacao) FILTER (WHERE tipo_movimentacao='FATURAMENTO') AS vendas,
          SUM(qtd_movimentacao) FILTER (WHERE tipo_movimentacao='CONSUMO')    AS consumo,
          SUM(qtd_movimentacao) FILTER (WHERE tipo_movimentacao='PRODUÇÃO')   AS producao,
          SUM(qtd_movimentacao)                                                 AS sist_total
   FROM movimentacao_estoque me
   JOIN codigos c ON c.cod_produto = me.cod_produto
   WHERE ativo=true AND data_movimentacao >= :data_inicio
   GROUP BY raiz

5. snapshot = SELECT * FROM inventario_snapshot_odoo WHERE ciclo_id = :ciclo_id

6. ajustes = SELECT * FROM inventario_ajuste_manual WHERE ciclo_id = :ciclo_id
   (agrupado por cod_produto — concatena observações se >1 linha)

7. UNION ALL os cod_produto distintos das 4 fontes → set master

8. Para cada cod no set master:
   linha = LinhaConfronto(
       cod, nome,
       inv_fb, inv_cd, inv_lf, inv_total = soma 3,
       compras = compras_sist (ou snapshot.compras_qtd se houver),  ← decisão (5.1.a)
       pa = snapshot.pa_qtd,
       componente = -snapshot.componente_qtd,  ← apresenta negativo
       vendas = vendas (negativo já vem do banco),
       consumo = consumo (negativo já vem do banco),
       producao = producao (positivo),
       ajuste_local, ajuste_qtd, ajuste_tipo (dos ajustes manuais),
       odoo = est_fb + est_cd + est_lf,
       mov = inv_total + compras + pa + componente,   ← formula da planilha
       sist = sist_total,
       odoo_menos_mov = odoo - mov,
       sist_menos_mov = sist - mov,
       est_fb, est_cd, est_lf,
   )

9. retorna sorted(linhas, key=cod_produto)
```

**5.1.a Decisão (compras_sist vs snapshot.compras_qtd):**
Fonte de verdade = `movimentacao_estoque` no Render (ENTRADA+COMPRA). O campo
`compras_qtd` do snapshot Odoo é mostrado em coluna auxiliar **só se houver
divergência** > 1% — destaque visual (linha amarela). Razão: a planilha
referência usa o Render como fonte; Odoo é para cross-check.

### 5.2 inventario_loader.py

Reaproveita `scripts/inventario_2026_05/02_carregar_inventario_xlsx.py`:
- Espera xlsx com 3 abas (FB, CD, LF — case-sensitive)
- Headers obrigatórios (case-insensitive): `CODIGO`, `LOTE`, `QTD`
- Header opcional: `VALIDADE`, `DESCRICAO`/`PRODUTO`
- Valida `cod_produto` começa com 1/2/3/4 (pula outliers com contagem)
- Resultado: insere linhas em `inventario_base` (deleta linhas existentes do
  `ciclo_id` antes — operação substitutiva).

Diferenças vs script CLI:
- Recebe `werkzeug.FileStorage` em vez de path no disco.
- Retorna dict com `{'inseridos': N, 'pulados': M, 'erros': [...]}`.
- Commit em uma transação só (com savepoint para test isolation — ref:
  memory/gotcha_commit_service_vaza_savepoint.md).

### 5.3 snapshot_odoo_service.py

Adapta `scripts/inventario_2026_05/monitor/relatorio_apontamentos_compras.py` +
`export_excel_completo.py` para uso programático.

Função: `SnapshotOdooService.refresh(ciclo_id: int, job: rq.Job) → dict`

```
1. ciclo = CicloInventario.query.get(ciclo_id)
2. data_inicio = ciclo.data_snapshot.isoformat() + ' 00:00:00'
3. odoo = get_odoo_connection()

4. ESTOQUE atual (stock.quant interno, FB/CD/LF):
   domain = [('company_id', 'in', [1,4,5]), ('location_id.usage','=','internal')]
   quants = odoo.search_read('stock.quant', domain, ['company_id','product_id',
                                                      'location_id','quantity'])
   # excluir locations cujo name ILIKE '%Indisponivel%'
   # agregar por (cod_produto, empresa) → estoque_fb/cd/lf

5. APONTAMENTOS:
   reusa logica do baixar_apontamentos do script CLI
   → pa_qtd (PA), componente_qtd (COMPONENTE consumo)

6. COMPRAS recebidas externas (exclui inter-company):
   reusa logica do baixar_compras
   → compras_qtd por cod_produto

7. DELETE FROM inventario_snapshot_odoo WHERE ciclo_id = :ciclo_id
   INSERT INTO inventario_snapshot_odoo (...) com refresh_em = now()

8. job.meta['progress'] atualizado em cada etapa (0%, 25%, 50%, 75%, 100%)

9. retorna {'inseridos': N, 'duracao_seg': X, 'refresh_em': iso}
```

### 5.4 movimentacoes_odoo_service.py

Função: `MovimentacoesOdooService.buscar_paginado(filtros: dict) → dict`

```
1. Monta domain Odoo baseado em filtros:
   domain = [('date', '>=', data_inicio),
             ('date', '<=', data_fim),
             ('state', '=', 'done'),
             ('company_id', 'in', companies_filtradas)]

   se filtros.cod → resolve product_id por default_code → adiciona
                     ('product_id', '=', product_id)

   se filtros.tipo='PRODUCAO' → adiciona
       ('move_id.raw_material_production_id', '!=', False)
       OR ('move_id.production_id', '!=', False)

   se filtros.origem → ('location_id.name', 'ilike', filtros.origem)
   se filtros.destino → ('location_dest_id.name', 'ilike', filtros.destino)
   se filtros.usuario → resolve user.name → user_id e adiciona
       ('move_id.create_uid', '=', user_id)

2. total = odoo.search_count('stock.move.line', domain)
3. offset = (page - 1) * page_size
4. ids = odoo.search('stock.move.line', domain,
                     offset=offset, limit=page_size, order='date desc')
5. rows = odoo.read('stock.move.line', ids,
                    ['date','company_id','product_id','lot_id','qty_done',
                     'location_id','location_dest_id','move_id','create_uid'])

6. Enriquecer: product.name (sem prefixo), lot.name, location.name, user.name
7. Se filtros.tipo=PRODUCAO: agrupar por mo_id (mrp.production)
   → cada grupo retorna [PA_line, ...COMPONENTE_lines]

8. retorna {'total': N, 'page': P, 'page_size': PS,
            'rows': [...], 'duracao_ms': X}
```

### 5.5 export_xlsx_service.py

Gera XLSX com 6 abas (replica a planilha referência do usuário):
1. **Confronto** (Planilha1 do usuário): linhas do ConfrontoService
2. **Ajustes_Manuais** (Planilha2): SELECT * FROM inventario_ajuste_manual
3. **Apontamentos**: dump da query Odoo de apontamentos (do snapshot_service)
4. **Compras_Recebidas**: dump da query Odoo de compras externas
5. **Movimentacoes_Sistema**: dump de movimentacao_estoque desde data_snapshot
6. **Estoque_por_Local**: dump de stock.quant por (empresa, local, cod, lote)

Engine: `xlsxwriter` (já em uso pelos scripts CLI). Formatação:
- Headers em negrito + background cinza claro
- Colunas numéricas com format `#,##0.000`
- Diferença ODOO-MOV / SIST-MOV: format condicional (vermelho se |diff| > 1)
- Freeze panes na linha 1 da aba Confronto

---

## 6. UI / Templates

### 6.1 confronto.html

```
┌─ Inventário > Confronto ─────────────────────────────────────────────────┐
│ Ciclo: [INV-2026-05 (16/05/2026) ▼]                                      │
│ Snapshot Odoo: 26/05 14:32  [Atualizar Odoo]                             │
│                                                                          │
│ [Filtrar: ___] [Empresa: ▼] [Mostrar só com diferença] [Exportar XLSX]   │
├──────────────────────────────────────────────────────────────────────────┤
│ cod │ produto │ FB │ CD │ LF │ TOT │ COMPRAS │ PA │ COMP. │ VEN │ CON │ │
│     │         │    │    │    │     │         │    │       │     │     │ │
│ PROD │ AJUSTE_LOCAL │ AJUSTE_QTD │ TIPO │ ODOO │ MOV │ SIST │ Δodoo │   │
│ Δsist │ FB(odoo) │ CD(odoo) │ LF(odoo)                                  │
└──────────────────────────────────────────────────────────────────────────┘
```

**Interação:**
- Click em valor de **COMPRAS / PA / VEN / CON / PROD** → abre nova aba
  `/inventario/movimentacoes?cod=X&empresa=ALL&tipo=ESTOQUE|PRODUCAO`
- Click em **FB(odoo) / CD(odoo) / LF(odoo)** → abre nova aba com
  `empresa=FB|CD|LF&tipo=ESTOQUE`
- Botão **Atualizar Odoo** → POST `/inventario/snapshot/<id>/refresh` →
  spinner com progress polling
- Filtros JS client-side (DataTables ou Tabulator — manter padrão do projeto)

**Estilo (dark + light, design tokens):**
- Linhas com |ΔODOO-MOV| > 1 ou |ΔSIST-MOV| > 1: bg amarelo claro
- Linhas só presentes em uma fonte: ícone informativo
- Header sticky + freeze cod/produto à esquerda

### 6.2 movimentacoes.html (drill-down em nova aba)

```
┌─ Movimentações: 4320147 — AZEITONA VERDE FATIADA POUCH 18x150 ──────────┐
│ Empresa: [▼] Tipo: [▼] Data: [__] a [__] Origem: [__] Destino: [__]    │
│ Usuário: [__]                            [Aplicar filtros] [Exportar]   │
│                                                                         │
│ Mostrando 1–100 de 234   [Tamanho: 100▼]    [< Anterior] [Próximo >]   │
├─────────────────────────────────────────────────────────────────────────┤
│ data │ empresa │ cod │ produto │ lote │ qtd │ origem │ destino │ usr   │
├─────────────────────────────────────────────────────────────────────────┤
│ ...  │ ...     │ ... │ ...     │ ...  │ ... │ ...    │ ...     │ ...   │
└─────────────────────────────────────────────────────────────────────────┘
```

Se `tipo=PRODUCAO`: rows agrupados por MO (linha-cabeçalho cinza + filhas).

### 6.3 ciclos.html

Lista simples (DataTable) com colunas: código, data_snapshot, status, criado_em,
linhas no inventario_base, linhas no ajuste_manual, botão "Abrir".

### 6.4 ajustes_manuais.html

Tabela inline editável (HTMX) com colunas: cod, produto, local, qtd, tipo, obs.
Header com: botão "+ Novo", input de upload xlsx em massa.

### 6.5 Menu (app/templates/base.html)

Adicionar item sob "Operações":
```html
{% if current_user.is_authenticated and current_user.tipo in ['administrador','logistica','financeiro'] %}
  <li><a href="{{ url_for('inventario.confronto.index') }}">Inventário — Confronto</a></li>
{% endif %}
```

---

## 7. Worker RQ

### 7.1 refresh_snapshot_worker.py

```python
def refresh_snapshot_worker(ciclo_id: int):
    """Job RQ: refresca estoque + apontamentos + compras Odoo para o ciclo."""
    from app import create_app
    app = create_app()
    with app.app_context():
        from app.inventario.services.snapshot_odoo_service import SnapshotOdooService
        from rq import get_current_job
        job = get_current_job()
        resultado = SnapshotOdooService.refresh(ciclo_id, job)
        return resultado
```

### 7.2 Integração worker_render.py / start_worker_render.sh

Editar **3 lugares** (regra ~/.claude/CLAUDE.md):

1. `worker_render.py` linha ~143:
   ```python
   '--queues', os.environ.get('RQ_QUEUES_DEFAULT',
       'atacadao,high,inventario,impostos,default')
   ```
2. `worker_render.py` linha ~211:
   ```python
   FILAS_PESADAS = {'atacadao', 'impostos', 'inventario'}
   ```
3. `start_worker_render.sh` linha ~301:
   ```bash
   --queues high,atacadao,inventario,impostos,default
   ```

Razão: refresh Odoo dura 2–5min (~10K leituras XML-RPC) → fila pesada para não
travar slot interativo.

---

## 8. Mapeamento de dados (validado em PROD 2026-05-26)

| Coluna planilha   | Fonte                                            | Filtro/agregação                                            |
|-------------------|--------------------------------------------------|-------------------------------------------------------------|
| INV FB/CD/LF      | inventario_base                                  | SUM(qtd) FILTER (empresa=X)                                 |
| COMPRAS           | movimentacao_estoque                             | SUM WHERE tipo_movimentacao='ENTRADA' AND local='COMPRA'    |
| PA                | inventario_snapshot_odoo.pa_qtd                  | (apontamento mrp.production — PA)                           |
| COMPONENTE        | inventario_snapshot_odoo.componente_qtd × (-1)   | (apontamento consumo de matéria-prima)                      |
| VENDAS            | movimentacao_estoque                             | SUM WHERE tipo_movimentacao='FATURAMENTO'                   |
| CONSUMO           | movimentacao_estoque                             | SUM WHERE tipo_movimentacao='CONSUMO'                       |
| PRODUÇÃO          | movimentacao_estoque                             | SUM WHERE tipo_movimentacao='PRODUÇÃO' (com Ç)              |
| AJUSTE Loc/Qtd    | inventario_ajuste_manual                         | linhas brutas                                               |
| ODOO              | inventario_snapshot_odoo                         | estoque_fb + estoque_cd + estoque_lf                        |
| MOV (calculado)   | TOTAL_INV + COMPRAS + PA + COMPONENTE            | derivado                                                    |
| SIST              | movimentacao_estoque                             | SUM(qtd_movimentacao) WHERE ativo=true (todo histórico)     |
| ESTOQUE FB/CD/LF  | inventario_snapshot_odoo                         | estoque_fb / estoque_cd / estoque_lf                        |

**Unificação de códigos:** queries em `movimentacao_estoque` resolvem
`COALESCE(cod_produto_raiz, cod_produto)` antes do GROUP BY. Mesmo procedimento
para joinar com `inventario_base` / `inventario_snapshot_odoo`.

**Schema fix necessário:** `.claude/skills/consultando-sql/schemas/tables/movimentacao_estoque.json` declara `tipo_movimentacao` valores ENTRADA/SAIDA/AJUSTE/PRODUCAO. Realidade do banco (validado em PROD 2026-05-26): ENTRADA/SAIDA/AJUSTE/**PRODUÇÃO** (com Ç), **CONSUMO**, **FATURAMENTO**, **REMESSA**. Atualizar o schema como parte do trabalho.

---

## 9. Tratamento de erros e bordas

1. **Produto só no Odoo (sem MovimentacaoEstoque):** linha aparece, colunas
   SIST/MOV/VENDAS/CONSUMO/PRODUÇÃO ficam `0` (ou `—` na UI).
2. **Produto só no sistema_fretes:** linha aparece, colunas ODOO/FB/CD/LF/PA/
   COMPONENTE ficam `0`.
3. **Snapshot Odoo nunca rodou:** tela carrega mostrando banner amarelo "Snapshot
   ainda não gerado — clique em Atualizar". Linhas mostram só fontes locais
   (inventário base + movimentacao_estoque + ajustes).
4. **Worker travado / falhou:** job tem timeout 600s; UI mostra status "Falhou —
   ver logs" com botão retry.
5. **Upload xlsx inválido (sem abas FB/CD/LF, headers errados):**
   `inventario_loader` retorna erro estruturado, tela mostra detalhes (linhas
   válidas/puladas/erro).
6. **Drill-down com filtro inválido (cod inexistente):** retorna 200 com
   `rows=[]` + mensagem "Nenhuma movimentação encontrada".
7. **Concorrência no refresh:** lock simples via `ciclo.status='REFRESHING'`
   durante o job; segundo botão "Atualizar" retorna 409 com mensagem.
8. **JSON sanitization:** agregações usando `Numeric` retornam `Decimal`.
   Aplicar `sanitize_for_json()` (regra ~/.claude/CLAUDE.md) em todos os retornos
   JSON das routes.
9. **Timezone:** todos timestamps usam `agora_utc_naive()` (regra REGRAS_TIMEZONE).
10. **Locations Indisponivel:** filtrar fora ao buscar `stock.quant`
    (`location.name NOT ILIKE '%Indisponivel%'`).

---

## 10. Testes (estimativa ~30 testes)

### 10.1 Unit tests

- `test_inventario_loader.py`
  - parse xlsx 3 abas válido → insere N linhas
  - aba FB ausente → erro
  - cod_produto inválido (começa com 'X') → pula com contagem
  - qtd negativa → erro
  - re-upload no mesmo ciclo → substitui (deleta old + insere new)

- `test_confronto_service.py`
  - linha só com inventário (sem mov, sem snapshot, sem ajuste) → MOV = INV_TOTAL
  - linha completa → diff calculado corretamente
  - linha com unificação de códigos → agrega no raiz
  - linha com snapshot.compras_qtd ≠ movimentacao_estoque → flag amarela
  - ordenação por cod_produto

- `test_snapshot_odoo_service.py` (mockar conexão Odoo)
  - refresh agrega corretamente PA/COMPONENTE/COMPRAS
  - filtro de Indisponivel funciona
  - re-refresh deleta + insere (idempotente)

- `test_movimentacoes_drill_down.py` (mockar Odoo)
  - paginação respeita page_size 100/500/1000
  - filtro tipo=PRODUCAO retorna grouped por mo_id
  - filtro origem ilike funciona
  - cod inexistente → rows=[]

- `test_export_xlsx.py`
  - gera 6 abas
  - formatação numérica `#,##0.000` correta
  - linha com diff > 1 destacada em amarelo

### 10.2 Integration tests

- `test_routes_inventario.py`
  - GET /inventario/confronto/1 — 200, contém código de produto
  - POST /inventario/ajustes/1 — cria + retorna linha
  - POST /inventario/snapshot/1/refresh — enfileira job (mock RQ)
  - GET /inventario/confronto/1.xlsx — Content-Type application/vnd.openxmlformats
  - permissões: user sem `tipo IN ('administrador','logistica','financeiro')`
    recebe 403

### 10.3 Smoke (manual, doc no fim do plano)

- Subir ciclo INV-TESTE com 5 produtos manuais
- Apertar "Atualizar Odoo" — observar progress
- Validar tela contra MOVS_ESTOQUE_RENDER_2026-05-25.xlsx aba Planilha1
- Click em PA → drill-down abre com MO agrupada
- Exportar XLSX → abrir no Excel → comparar 6 abas com referência

---

## 11. Migrations

Dois artefatos (regra ~/.claude/CLAUDE.md):

**`scripts/migrations/inventario_base_create_tables.py`** — Python com
`create_app()`, `before/after` (`SELECT COUNT(*) FROM information_schema.tables
WHERE table_name LIKE 'inventario_%'`), `db.create_all()` filtrado por modelos.

**`scripts/migrations/inventario_base_create_tables.sql`** — DDL idempotente:
```sql
CREATE TABLE IF NOT EXISTS inventario_ciclo (...);
CREATE TABLE IF NOT EXISTS inventario_base (...);
CREATE TABLE IF NOT EXISTS inventario_ajuste_manual (...);
CREATE TABLE IF NOT EXISTS inventario_snapshot_odoo (...);
CREATE INDEX IF NOT EXISTS ix_inventario_base_cod_produto ON inventario_base(cod_produto);
-- (todos com IF NOT EXISTS)
```

---

## 12. Decisões inviáveis / inviabilidades aceitas

- **Drill-down Odoo é always-fresh (sem cache)** → trade-off: cada navegação custa
  ~500ms-2s no Odoo. Aceito porque é click consciente do usuário, não load
  default. Mitigação: paginação default 100.
- **Apontamentos só após botão "Atualizar Odoo"** → tela inicial pode mostrar
  dados desatualizados (até 1 dia). Mitigação: timestamp visível + sugestão de
  refresh quando > 4h.
- **Ajustes manuais não validados contra produto real do Odoo** → linha pode ter
  cod_produto inexistente. Mitigação: autocomplete na UI usando produtos
  conhecidos (inventario_base ∪ snapshot).
- **Sem suporte multi-empresa fora de FB/CD/LF** (companies 1/4/5 hardcoded).
  Outras companies (3, etc.) não aparecem. Aceito — escopo Nacom Goya.

---

## 13. Riscos e mitigações

| Risco                                                            | Probabilidade | Mitigação                                                          |
|------------------------------------------------------------------|---------------|--------------------------------------------------------------------|
| Refresh Odoo timeout (>10min)                                    | Média         | Timeout 900s no job; logs em Sentry; retry via UI                  |
| Schema PRODUCAO/PRODUÇÃO inconsistente quebra agregação          | Alta          | Validar em PROD ✓ (feito); atualizar schema JSON; cobrir em test   |
| inventario_base xlsx do usuário muda formato no próximo ciclo    | Média         | Loader tolerante a header variants (alias dict como script 02)     |
| Decimal precision em qtd (Numeric(15,3) vs cálculo float)        | Baixa         | sanitize_for_json() sempre; testes com valores extremos            |
| Conflito de ciclo ATIVO (>1 ciclo ATIVO ao mesmo tempo)          | Baixa         | UX: ao criar novo ATIVO, ofecer arquivar o anterior                |
| Snapshot grande (1000 produtos × 1KB = 1MB) sobrecarrega memória | Baixa         | Não — ínfimo para psycopg2                                         |

---

## 14. Estimativa de esforço

| Fase                              | LOC   | Esforço |
|-----------------------------------|-------|---------|
| Modelos + migrations              |   270 |   2h    |
| Services (5 arquivos)             |   900 |  10h    |
| Routes (5 arquivos)               |   600 |   6h    |
| Worker + integração worker_render |   160 |   2h    |
| Templates (4 htmls) + CSS         |   800 |   8h    |
| JS interativo                     |   400 |   4h    |
| Testes                            |   800 |   8h    |
| Schema fix + menu + base.html     |    20 |   0,5h  |
| **TOTAL**                         | **~3950** | **~40h** |

---

## 15. Próximos passos

1. **User aprova este spec** (você lê este arquivo e me dá go/changes).
2. **Eu invoco `superpowers:writing-plans`** → escrevo plano detalhado em
   `docs/superpowers/plans/2026-05-26-relatorio-confronto-inventario-plan.md`
   com tasks numeradas, dependências e checkpoints de review.
3. **Executar** via `superpowers:executing-plans` (com você revisando cada
   checkpoint).

---

**Referências consultadas:**
- `.claude/skills/consultando-sql/schemas/tables/movimentacao_estoque.json`
- `scripts/inventario_2026_05/monitor/relatorio_apontamentos_compras.py`
- `scripts/inventario_2026_05/monitor/export_excel_completo.py`
- `scripts/inventario_2026_05/monitor/_comum.py`
- `scripts/inventario_2026_05/02_carregar_inventario_xlsx.py`
- `docs/inventario-2026-05/07-relatorios/MOVS_ESTOQUE_RENDER_2026-05-25_20-20.xlsx` (planilha referência)
- `app/estoque/{models,routes,services}.py`
- `~/.claude/CLAUDE.md` (regras dev — migrations, worker RQ, JSON sanitization)
- `CLAUDE.md` (projeto — companies FB=1/CD=4/LF=5)
- Validação PROD 2026-05-26: `tipo_movimentacao` valores reais (ENTRADA, FATURAMENTO, CONSUMO, PRODUÇÃO com Ç, etc.)
