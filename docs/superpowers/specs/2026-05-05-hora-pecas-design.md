# HORA — Cadastro, Estoque e Faturamento de Peças

**Data**: 2026-05-05
**Status**: spec aprovado, aguardando plano de implementação
**Escopo**: módulo `app/hora` — adicionar peças (não-motos) ao ciclo de compra, recebimento, venda e faturamento NFe via TagPlus

---

## 1. Contexto

O módulo HORA hoje opera **somente motos** (chassi único como chave universal). O usuário quer estender o ciclo para vender também **peças** (capacete, retrovisor, bateria, acessórios) — produtos fungíveis sem chassi, com quantidade.

## 2. Premissas

- Peça **pode existir sem TagPlus** (cadastro independente, mapeamento opcional pra emissão NFe).
- NFe TagPlus pode ser **mista** (motos + peças no mesmo POST `/nfes`).
- Estoque de peça segue **padrão moto** — saldo derivado de movimentações (sem tabela de saldo materializado).
- Preço de peça é **fixo** em `hora_peca.preco_venda_padrao` (sem versionamento histórico — peça não tem variação como moto).
- Cadastro de peça vive em **Cadastros** do menu (perm `pecas_cadastro`).
- Estoque de peça vive em **Movimentação** (perm `pecas_estoque`).
- Módulo `pecas` (existente) continua como "peças faltando em motos" (Ocorrências).

## 3. Decisões aprovadas (Q&A com usuário)

| # | Decisão |
|---|---|
| 1 | Pedidos de compra **e** venda recebem peças |
| 2 | Naming: criar 2 módulos novos `pecas_cadastro` + `pecas_estoque`. Mantém `pecas` = "faltando" |
| 3 | Saldo de peças derivado por `SUM(qtd)` em `hora_peca_movimento` (sem materialização) |
| 4 | Cadastro inclui: codigo_interno, descricao, ncm, cfop_default, unidade, preco_venda_padrao, foto S3, ativo |
| 5 | CFOP por peça (`hora_peca.cfop_default`, com override em `hora_tagplus_peca_map`) |
| 6 | Backfill TagPlus de produtos (catálogo) **e** de NFes de venda (mistas) com proteção de chassi |
| 7 | `hora_venda_item_peca` separada de `hora_venda_item` (preserva NOT NULL existente) |
| 8 | NFe TagPlus mista (motos + peças permitidos) |
| 9 | Peça entra no estoque via NF entrada **e** ajuste manual |
| 10 | 2 módulos de permissão novos |

### Proteção de chassi (CONF-1)
Chassi vinculado a `HoraPedidoItem` OU `HoraNfEntradaItem` é **fonte de verdade**. Backfill de NFe de venda **nunca altera** modelo/cor/motor desse chassi nem cria `HoraMoto` ad-hoc com chassi protegido. Divergência do parser → registra `HoraVendaDivergencia` tipo `CHASSI_PROTEGIDO_PARSER_DIVERGENTE` e segue.

### Backfill por delta (CONF-2)
Rota nova varre `HoraVenda` com `(valor_total - sum(itens.preco_final + itens_peca.preco_final)) > 0` e repuxa via `GET /nfes/{id}` para classificar/criar peças nas vendas legadas.

### Conferência peças (CONF-4)
Embutida em `hora_nf_entrada_item_peca` (1:1 — não vale tabela paralela).

---

## 4. Schema (5 tabelas novas + 1 ALTER)

### 4.1 `hora_peca` — cadastro
```sql
id                   SERIAL PK
codigo_interno       VARCHAR(50) UNIQUE NOT NULL  -- chave de negócio (ex: 'CAP-PRETO-M')
descricao            VARCHAR(255) NOT NULL
ncm                  VARCHAR(10)
cfop_default         VARCHAR(5) NOT NULL DEFAULT '5.102'
unidade              VARCHAR(5) NOT NULL DEFAULT 'UN'
preco_venda_padrao   NUMERIC(15,2) NOT NULL DEFAULT 0
foto_s3_key          VARCHAR(500)
ativo                BOOLEAN NOT NULL DEFAULT TRUE
criado_em, atualizado_em
INDEX ix_hora_peca_ativo (ativo)
```

### 4.2 `hora_tagplus_peca_map` — mapeamento opcional pra TagPlus
```sql
id                   SERIAL PK
peca_id              INTEGER FK UNIQUE NOT NULL -> hora_peca(id)
tagplus_produto_id   VARCHAR(50) NOT NULL
tagplus_codigo       VARCHAR(50)               -- chave de backfill
cfop_default         VARCHAR(5)                -- override de hora_peca.cfop_default
criado_em, atualizado_em
INDEX ix_hora_tagplus_peca_map_codigo (tagplus_codigo)
```

### 4.3 `hora_peca_movimento` — log de movimentações
```sql
id            SERIAL PK
peca_id       INTEGER FK NOT NULL -> hora_peca(id)
loja_id       INTEGER FK NOT NULL -> hora_loja(id)
tipo          VARCHAR(25) NOT NULL
              -- ENTRADA_NF / SAIDA_VENDA / TRANSFERENCIA_OUT / TRANSFERENCIA_IN
              -- AJUSTE_POS / AJUSTE_NEG / DEVOLUCAO_VENDA / DEVOLUCAO_FORNECEDOR
qtd           NUMERIC(15,3) NOT NULL  -- signed (+ entrada, - saída)
ref_tabela    VARCHAR(50)             -- 'hora_nf_entrada_item_peca' / 'hora_venda_item_peca' / etc
ref_id        INTEGER                 -- id na ref_tabela
motivo        VARCHAR(500)
operador      VARCHAR(100)
criado_em     TIMESTAMP NOT NULL DEFAULT now()
INDEX ix_hora_peca_mov_saldo (peca_id, loja_id, criado_em)
INDEX ix_hora_peca_mov_ref (ref_tabela, ref_id)
```

### 4.4 `hora_nf_entrada_item_peca` — peça em NF de entrada
```sql
id                       SERIAL PK
nf_id                    INTEGER FK NOT NULL -> hora_nf_entrada(id)
peca_id                  INTEGER FK NOT NULL -> hora_peca(id)
qtd_nf                   NUMERIC(15,3) NOT NULL
preco_real               NUMERIC(15,2) NOT NULL
modelo_texto_original    VARCHAR(255)
-- conferência embutida (1:1)
qtd_conferida            NUMERIC(15,3)
divergencia_qtd          VARCHAR(20)  -- OK / FALTA / SOBRA / AVARIA
foto_conferencia_s3_key  VARCHAR(500)
conferida_em             TIMESTAMP
conferida_por            VARCHAR(100)
INDEX ix_hora_nf_ent_item_peca_nf (nf_id)
INDEX ix_hora_nf_ent_item_peca_peca (peca_id)
```

### 4.5 `hora_venda_item_peca` — peça em pedido de venda
```sql
id                          SERIAL PK
venda_id                    INTEGER FK NOT NULL -> hora_venda(id)
peca_id                     INTEGER FK NOT NULL -> hora_peca(id)
qtd                         NUMERIC(15,3) NOT NULL
preco_unitario_referencia   NUMERIC(15,2) NOT NULL  -- snapshot de hora_peca.preco_venda_padrao
desconto_aplicado           NUMERIC(15,2) NOT NULL DEFAULT 0
preco_final                 NUMERIC(15,2) NOT NULL  -- = qtd * (preco_unitario_referencia - desconto_aplicado)
INDEX ix_hora_venda_item_peca_venda (venda_id)
INDEX ix_hora_venda_item_peca_peca (peca_id)
```

### 4.6 ALTER `hora_pedido_item` — peça em pedido de compra
```sql
ALTER TABLE hora_pedido_item
  ADD COLUMN peca_id INTEGER REFERENCES hora_peca(id),
  ADD COLUMN qtd_pedida NUMERIC(15,3),
  ADD CONSTRAINT chk_hora_pedido_item_xor CHECK (
      (peca_id IS NULL AND qtd_pedida IS NULL) OR
      (peca_id IS NOT NULL AND modelo_id IS NULL AND numero_chassi IS NULL)
  )
-- modelo_id e numero_chassi continuam nullable (já eram).
-- preco_compra_esperado é compartilhado (custo unitário).
```

---

## 5. Migrations (3 arquivos `.py` + `.sql`)

| # | Arquivo | Conteúdo |
|---|---|---|
| 1 | `hora_21_pecas_cadastro` | `hora_peca`, `hora_tagplus_peca_map` |
| 2 | `hora_22_pecas_movimento_e_itens` | `hora_peca_movimento`, `hora_nf_entrada_item_peca`, `hora_venda_item_peca`, ALTER `hora_pedido_item` |
| 3 | `hora_23_pecas_permissoes` | INSERT em `hora_user_permissao` para `pecas_cadastro`/`pecas_estoque` (data fix; sem DDL) |

Cada arquivo segue regra CLAUDE.md: `.sql` idempotente (`CREATE TABLE IF NOT EXISTS`, `ADD COLUMN IF NOT EXISTS`) + `.py` com `create_app()` + verificação before/after.

---

## 6. Modelos SQLAlchemy

### Novos arquivos
- `app/hora/models/peca.py` — **renomear o atual para `peca_faltando.py`** (refactor, classe continua `HoraPecaFaltando`)
- `app/hora/models/peca.py` (novo): `HoraPeca`, `HoraTagPlusPecaMap`, `HoraPecaMovimento`, `HoraNfEntradaItemPeca`, `HoraVendaItemPeca`
- Constantes: `PECA_MOV_TIPO_*`, `PECA_DIVERGENCIA_*`

### Atualizado
- `app/hora/models/__init__.py` — exports + re-export de `HoraPecaFaltando`/`HoraPecaFaltandoFoto`
- `app/hora/models/compra.py` — `HoraPedidoItem` ganha `peca_id`, `qtd_pedida`, relationship `peca`
- `app/hora/models/permissao.py` — `MODULOS_HORA += [('pecas_cadastro', ...), ('pecas_estoque', ...)]`

---

## 7. Services

### Novos
**`app/hora/services/peca_service.py`** (substitui o atual de "peça faltando" — renomear pra `peca_faltando_service.py`)
- `criar_peca(codigo_interno, descricao, ncm, cfop_default, unidade, preco_venda_padrao, ativo, ...)`
- `editar_peca(peca_id, campos)`
- `inativar_peca(peca_id)`
- `upload_foto(peca_id, file_obj)`, `get_foto_url(peca)`
- `set_tagplus_map(peca_id, tagplus_produto_id, tagplus_codigo, cfop_default)`
- `listar_pecas(busca, ativo, lojas_permitidas_ids, ...)`

**`app/hora/services/peca_estoque_service.py`**
- `saldo(peca_id, loja_id) -> Decimal` — `SELECT COALESCE(SUM(qtd), 0)` em movimentos
- `saldos_por_loja(peca_id) -> dict[loja_id, Decimal]`
- `listar_estoque(loja_id=None, peca_id=None, somente_positivo=True, paginado)` — JOIN com hora_peca + GROUP BY
- `registrar_movimento(peca_id, loja_id, tipo, qtd, ref_tabela=None, ref_id=None, motivo=None, operador=None) -> HoraPecaMovimento`
- `ajuste_manual(peca_id, loja_id, qtd_signed, motivo, operador)` — tipo `AJUSTE_POS` / `AJUSTE_NEG`
- `transferencia(peca_id, loja_origem_id, loja_destino_id, qtd, motivo, operador)` — emite 2 movimentos (`OUT` + `IN`) na mesma transação
- `historico(peca_id, loja_id=None, limit=50)`

**`app/hora/services/chassi_protecao_service.py`**
- `chassi_protegido(numero_chassi: str) -> bool`
- `motivos_protecao(numero_chassi) -> list[dict]` — retorna `[{origem: 'pedido', id: 12, numero: '...'}, {origem: 'nf_entrada', id: 5, chave_44: '...'}]`

### Alterados
**`venda_service.py`**:
- `criar_venda_manual` aceita opcionalmente `itens_peca: list[dict]` (coexistência com `numero_chassi`/moto)
- Novos: `adicionar_item_peca`, `remover_item_peca`, `editar_item_peca` — emite movimento `SAIDA_VENDA` ao adicionar e `DEVOLUCAO_VENDA` ao remover/cancelar
- `cancelar_venda` — devolve estoque (movimento `DEVOLUCAO_VENDA` para cada item peça)
- `confirmar_venda` — sem efeito em estoque (peça já saiu na criação; mantém saída)

**`pedido_service.py`**:
- `adicionar_item_peca_pedido(pedido_id, peca_id, qtd_pedida, preco_compra_esperado)`
- `remover_item_peca_pedido(item_id)`

**`nf_entrada_service.py`**:
- Parser de DANFE distingue motos (com chassi) de peças (sem chassi):
  - Item TagPlus com código mapeado em `hora_tagplus_produto_map` → moto
  - Item TagPlus com código mapeado em `hora_tagplus_peca_map` → peça
  - Item sem mapping → divergência `PRODUTO_NAO_MAPEADO` (operador resolve manualmente)
- Registra `HoraNfEntradaItemPeca` para peças
- Emite `ENTRADA_NF` em `peca_movimento` na confirmação do recebimento (não na chegada da NF)

**`recebimento_service.py`**:
- Wizard inclui passo de conferência de peças (qtd_conferida + foto)
- Ao finalizar conferência, dispara `peca_estoque_service.registrar_movimento(tipo='ENTRADA_NF', qtd=qtd_conferida)`

**`estoque_service.py`** (motos): **NÃO mexer** — continua exclusivo de motos via eventos.

### TagPlus
**`tagplus/payload_builder.py`** — `_montar_itens()`:
- Concatena `venda.itens` (motos) + `venda.itens_peca` (peças)
- Item moto: `qtd: 1`, `detalhes: 'Chassi: X / Motor: Y'`, CFOP via `HoraTagPlusProdutoMap`
- Item peça: `produto_servico: peca_map.tagplus_produto_id`, `qtd: vi.qtd`, sem `detalhes` chassi, CFOP via `peca_map.cfop_default` ou `peca.cfop_default`
- Validação: peça SEM `HoraTagPlusPecaMap` → erro `peca_nao_mapeada`

**`tagplus/backfill_service.py`** — múltiplas mudanças:
1. `_resolver_modelo_id` ganha sibling `_resolver_peca_id` (lookup em `HoraTagPlusPecaMap`)
2. `_criar_itens_da_api` discrimina por código:
   - Bate em `HoraTagPlusProdutoMap` → fluxo moto atual (com `_extrair_chassi_motor`)
   - Bate em `HoraTagPlusPecaMap` → novo fluxo peça (`_criar_item_peca_da_api`)
   - Não bate em nenhum → divergência `PRODUTO_NAO_MAPEADO`
3. **Proteção chassi**: `_atualizar_moto_complementar` e `_atualizar_campos_vazios` consultam `chassi_protegido()` antes de qualquer UPDATE em `HoraMoto`. Se protegido e parser divergir, **não atualiza** + registra `HoraVendaDivergencia` tipo `CHASSI_PROTEGIDO_PARSER_DIVERGENTE`
4. **Não cria** `HoraMoto` ad-hoc para chassi extraído de NFe de venda — só atualiza moto **existente** (criada por NF de entrada). Se chassi não existe, registra divergência `CHASSI_NAO_CADASTRADO` (já existe no sistema)
5. Nova função `executar_backfill_produtos_pecas()` — itera `GET /produtos`, popula `hora_peca` + `hora_tagplus_peca_map`. Critério de detecção peça vs moto: opção (a) operador escolhe na tela qual produtos são peça antes de importar, (b) heurística por NCM (8711* = moto). Recomendo (a) com pré-filtro (b)
6. Nova função `executar_backfill_pecas_faltantes()` — busca `HoraVenda` com `valor_total - sum(itens) > 0`, repuxa via `GET /nfes/{id}`, cria `HoraVendaItemPeca` para itens que não bateram com moto

---

## 8. Routes

### Novas — `app/hora/routes/pecas_cadastro.py`
```
GET  /hora/pecas/cadastro                       pecas_cadastro_lista
GET  /hora/pecas/cadastro/novo                  pecas_cadastro_novo (form)
POST /hora/pecas/cadastro/criar                 pecas_cadastro_criar
GET  /hora/pecas/cadastro/<id>                  pecas_cadastro_detalhe
POST /hora/pecas/cadastro/<id>/editar           pecas_cadastro_editar
POST /hora/pecas/cadastro/<id>/foto             pecas_cadastro_upload_foto
POST /hora/pecas/cadastro/<id>/inativar         pecas_cadastro_inativar
POST /hora/pecas/cadastro/<id>/tagplus-map      pecas_cadastro_set_tagplus_map
GET  /hora/pecas/cadastro/autocomplete          pecas_cadastro_autocomplete (AJAX)
```

### Novas — `app/hora/routes/pecas_estoque.py`
```
GET  /hora/pecas/estoque                        pecas_estoque_lista (filtro: loja, peça, somente positivo)
GET  /hora/pecas/estoque/<peca_id>/<loja_id>    pecas_estoque_detalhe (histórico de movimentos)
POST /hora/pecas/estoque/ajuste                 pecas_estoque_ajuste_manual
POST /hora/pecas/estoque/transferencia          pecas_estoque_transferencia
GET  /hora/pecas/estoque/saldo/<peca_id>        pecas_estoque_saldo_json (AJAX para wizard de venda)
```

### Alterações em `tagplus_routes.py`
```
GET  /hora/tagplus/peca-map                     tagplus_peca_map_lista
POST /hora/tagplus/peca-map/salvar              tagplus_peca_map_salvar
GET  /hora/tagplus/backfill-produtos            tagplus_backfill_produtos (form + lista)
POST /hora/tagplus/backfill-produtos/executar   tagplus_backfill_produtos_executar
GET  /hora/tagplus/backfill-pecas-faltantes     tagplus_backfill_pecas_delta (form + lista)
POST /hora/tagplus/backfill-pecas-faltantes/executar
```

### Alterações em `pedidos.py` (compra)
```
POST /hora/pedidos/<id>/itens-peca/adicionar    pedido_adicionar_item_peca (AJAX)
POST /hora/pedidos/<id>/itens-peca/<item_id>/remover
POST /hora/pedidos/<id>/itens-peca/<item_id>/editar
```

### Alterações em `vendas.py`
```
POST /hora/vendas/<id>/itens-peca/adicionar     venda_adicionar_item_peca (AJAX)
POST /hora/vendas/<id>/itens-peca/<item_id>/remover
POST /hora/vendas/<id>/itens-peca/<item_id>/editar
```

---

## 9. Templates

### Novos
- `pecas_cadastro_lista.html` — DataTable + filtros (busca, ativo)
- `pecas_cadastro_form.html` — criar/editar (campos + foto + mapeamento TagPlus inline)
- `pecas_cadastro_detalhe.html` — read view + botões editar/inativar/foto/upload
- `pecas_estoque_lista.html` — saldo por (peça × loja), com filtros
- `pecas_estoque_detalhe.html` — histórico de movimentos de uma combinação peça×loja
- `pecas_estoque_ajuste_modal.html` — partial pra ajuste manual
- `pecas_estoque_transferencia_modal.html` — partial pra transferência entre lojas
- `tagplus_peca_map_lista.html` — tabela edição inline
- `tagplus_backfill_produtos.html` — preview de produtos TagPlus + checkboxes "é peça?" + executa
- `tagplus_backfill_pecas_delta.html` — lista vendas com delta + reprocessar

### Alterados
- `base.html` — adiciona links nos menus Cadastros, Movimentação, Faturamento
- `pedido_detalhe.html` — nova aba/seção "Peças" (paralela a "Motos") com CRUD AJAX
- `venda_detalhe.html` — nova aba/seção "Peças" (com botão adicionar peça via autocomplete)
- `nf_detalhe.html` — listar `nf.itens_peca` em seção separada de motos
- `recebimento_wizard.html` — passo de conferência de peças (qtd_conferida + foto opcional)

### 9.1 Padrão visual obrigatório (referência: módulo HORA)

Todos os templates novos **DEVEM** seguir o padrão consolidado dos templates existentes:

**Listagem** (referência: `modelos_lista.html`, `transferencias_lista.html`):
- Cabeçalho: `<div class="d-flex align-items-center justify-content-between mb-3 flex-wrap gap-2">` com `<h2>` + botões à direita
- Botões respeitam `{% if current_user.tem_perm_hora('modulo', 'acao') %}`
- Filtros: usar **obrigatoriamente** macros de `hora/_filtros.html`:
  ```jinja
  {% from "hora/_filtros.html" import filtros_form, filtro_texto, filtro_loja, filtro_status, filtro_data, filtros_botoes %}
  {% call filtros_form(url_for('hora.X_lista')) %}
    {{ filtro_texto('busca', 'Busca', filtro_busca) }}
    {{ filtro_loja('loja_id', valor=filtro_loja_id, lojas=lojas) }}
    {{ filtros_botoes(url_for('hora.X_lista')) }}
  {% endcall %}
  ```
- Tabela: `<table class="table table-hover align-middle">`
- Status: `<span class="badge bg-{success/secondary/info/warning/danger}">`
- Ações: `<div class="btn-group btn-group-sm">` com `btn-outline-{primary/warning/success/danger}`
- Forms POST inline: incluem `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">` + `onsubmit="return confirm(...)"`
- Empty state: `<tr><td colspan="N" class="text-center text-muted">Nenhum X cadastrado.</td></tr>`
- Paginação: `{% from "hora/_pagination.html" import render_pagination %}` ao final, **sempre que houver paginação**

**Form criar/editar** (referência: `modelos_novo.html`, `transferencia_nova.html`):
- Form simples: `<form method="post" class="card p-3" style="max-width: 700px;">`
- Form multi-coluna: `<form method="post" class="card p-3">` com `<div class="row g-3">`
- Hint: `<small class="text-muted">` abaixo de inputs com explicação
- Required: `<span class="text-danger">*</span>` no label
- Botões: `<div class="d-flex gap-2">` (ou `justify-content-between` com Cancelar à esquerda) — primary + outline-secondary "Cancelar"

**Detalhe** (referência: `transferencia_detalhe.html`, `venda_detalhe.html`):
- Header: `<div class="d-flex justify-content-between align-items-start mb-3">` com `<h2>` + ícone + badge de status + botões à direita
- Info: `<div class="row">` + `<div class="col-md-6"><div class="card p-3 mb-3"><dl class="row mb-0">` (dt col-sm-4 / dd col-sm-8)
- Itens: `<h5>Itens (N)</h5>` + `<div class="card mb-3"><div class="table-responsive"><table class="table table-sm mb-0">`
- Ações destrutivas: card `border-danger-subtle` com h5 vermelho + botão `btn-danger`
- Auditoria: tabela ao final, padrão `<th>Quando | Quem | Ação | Detalhe</th>`

**Detalhe técnico**:
- Datas longas: `.strftime('%d/%m/%Y %H:%M')`
- Datas em tabelas compactas: `.strftime('%d/%m %H:%M')`
- Chassi: `<code class="chassi-mono">` (CSS global já existe)
- Permissões em torno de TODA ação destrutiva ou de modificação
- Ícones Font Awesome 5 (já carregado): `fa-cogs` para peça, `fa-warehouse` para estoque, `fa-link` para mapeamento, `fa-cloud-download-alt` para backfill

**Modais (ajuste, transferência)**:
- Bootstrap modal padrão
- Form com csrf_token + validação client-side
- Botão fechar + botão primary submit

**JS de autocomplete**:
- Reutilizar `app/static/js/hora/autocomplete.js` (já carregado em `base.html`)
- `data-hora-autocomplete="peca"` deve ser registrado em `autocomplete_service.py` + `autocomplete.py` route

---

## 10. Permissões + Menu

### `MODULOS_HORA`
```python
('pecas_cadastro', 'Cadastro de Peças'),
('pecas_estoque', 'Estoque de Peças'),
```

(Mantém `pecas` = "Peças faltando em motos".)

### Menu (`base.html`)
**Cadastros** — adicionar:
```jinja
{% if current_user.tem_perm_hora('pecas_cadastro', 'ver') %}
  <li><a class="dropdown-item" href="{{ url_for('hora.pecas_cadastro_lista') }}">
    <i class="fas fa-cogs fa-fw"></i> Peças
  </a></li>
{% endif %}
```

**Movimentação** — abaixo de "Estoque" (motos):
```jinja
{% if current_user.tem_perm_hora('pecas_estoque', 'ver') %}
  <li><a class="dropdown-item" href="{{ url_for('hora.pecas_estoque_lista') }}">
    <i class="fas fa-warehouse fa-fw"></i> Estoque de Peças
  </a></li>
{% endif %}
```

**Faturamento** — adicionar:
- Mapeamento de produtos (peças)
- Backfill catálogo TagPlus (produtos → peças)
- Backfill peças faltantes (delta)

---

## 11. Proteção de chassi (detalhamento técnico)

### Helper
```python
# app/hora/services/chassi_protecao_service.py
def chassi_protegido(numero_chassi: str) -> bool:
    """True se chassi está vinculado a HoraPedidoItem ou HoraNfEntradaItem.

    Esses registros são fonte de verdade. Backfill de NFe de venda NUNCA
    sobrescreve atributos de HoraMoto desse chassi — só leitura.
    """
    chassi = (numero_chassi or '').strip().upper()
    if not chassi:
        return False
    em_pedido = db.session.query(HoraPedidoItem.id).filter(
        HoraPedidoItem.numero_chassi == chassi,
    ).limit(1).first() is not None
    if em_pedido:
        return True
    em_nf = db.session.query(HoraNfEntradaItem.id).filter(
        HoraNfEntradaItem.numero_chassi == chassi,
    ).limit(1).first() is not None
    return em_nf
```

### Aplicação no backfill
- `_atualizar_moto_complementar` — antes de `UPDATE hora_moto SET modelo_id=...`, checa `chassi_protegido()`. Se sim e parser sugeriu valor diferente → registra divergência e SKIP
- `_atualizar_campos_vazios` — idem
- Novo tipo `HoraVendaDivergencia.tipo`: `CHASSI_PROTEGIDO_PARSER_DIVERGENTE`
- Importante: backfill de NFe de venda **não cria** `HoraMoto` ad-hoc — registra `CHASSI_NAO_CADASTRADO` (já existe) e segue. Apenas NF de entrada cria moto.

---

## 12. TagPlus — payload misto (moto + peça)

### Item moto (mantido)
```json
{
  "produto_servico": "MT-X12",
  "qtd": 1,
  "valor_unitario": 8500.00,
  "valor_desconto": 200.00,
  "detalhes": "Chassi: ABC123 / Motor: M789",
  "cfop": "5.403"
}
```

### Item peça (novo)
```json
{
  "produto_servico": "CAP-PRETO-M",
  "qtd": 2,
  "valor_unitario": 150.00,
  "valor_desconto": 0,
  "detalhes": null,
  "cfop": "5.102"
}
```

### CFOP por item
TagPlus aceita `cfop` por item dentro de `itens[]`. Payload root mantém CFOP do primeiro item (compatibilidade).

### Faturas
Sem mudanças — `valor_nota = sum(itens motos + itens peças)`.

---

## 13. Backfill TagPlus — fluxo

### Backfill produtos (catálogo)
1. `GET /produtos?tipo=produto&per_page=100` (paginado)
2. Para cada produto: heurística por NCM (`8711*` → moto) sugere classificação, mas operador confirma na tela
3. Salva `hora_peca` (descrição, ncm, cfop_default sugerido) + `hora_tagplus_peca_map` (tagplus_codigo, tagplus_produto_id)
4. Idempotente — re-execução atualiza, não duplica

### Backfill NFes (com peças)
- Fluxo existente continua para motos
- Itens cuja `produto.codigo` bate em `hora_tagplus_peca_map` → cria `hora_venda_item_peca` (qtd vinda de `produto.qtd`, preço de `produto.valor_unitario`)
- Itens sem mapping → divergência `PRODUTO_NAO_MAPEADO`

### Backfill delta (NFes legadas)
1. `SELECT venda.id FROM hora_venda WHERE valor_total - (sum_itens_moto + sum_itens_peca) > 0.01`
2. Para cada: `GET /nfes/{tagplus_nfe_id}` (via `HoraTagPlusNfeEmissao`)
3. Reprocessa itens; classifica peças via mapping; insere `hora_venda_item_peca`
4. Atualiza divergências resolvidas

---

## 14. Plano de implementação (12 fases)

```
P1.  Migrations (3 .py + .sql) + atualiza permissoes data fix
P2.  Modelos SQLAlchemy: peca.py novo, peca_faltando.py renomeado, exports
P3.  Services: peca_service, peca_estoque_service, chassi_protecao_service
P4.  Permissões: MODULOS_HORA, atualiza tela de gestão de permissões
P5.  Cadastros UI: rotas + templates + JS (autocomplete + foto)
P6.  Estoque UI: rotas + templates (lista + detalhe + ajuste + transferência)
P7.  Pedido de Compra: ALTER + service + AJAX + template (pedido_detalhe)
P8.  NF Entrada: parser distingue peça, item peça, recebimento conferência
P9.  Pedido de Venda: service + AJAX + template (venda_detalhe)
P10. TagPlus payload_builder: itens mistos + CFOP por item + testes unit
P11. TagPlus backfill: discriminador + proteção chassi + 2 backfills novos
P12. Menu wiring + smoke tests + atualiza app/hora/CLAUDE.md
```

Cada fase termina com self-audit:
- [ ] Routes registradas
- [ ] Link no menu
- [ ] `require_hora_perm` em todas as rotas
- [ ] CSRF + flash em templates
- [ ] Imports completos
- [ ] Migration: DDL idempotente + verificação
- [ ] Validação frontend + backend
- [ ] `sanitize_for_json` em JSONB (se houver)
- [ ] Tests em `tests/hora/`
- [ ] CLAUDE.md atualizado

---

## 15. Testes (`tests/hora/`)

- `test_peca_cadastro.py` — criar/editar/inativar peça, upload foto, set tagplus_map, validações
- `test_peca_estoque.py` — saldo via SUM, ajuste manual, transferência atômica, idempotência
- `test_chassi_protecao.py` — chassi em pedido = protegido; em NF entrada = protegido; novo = não protegido
- `test_pedido_compra_pecas.py` — XOR moto/peça, qtd_pedida obrigatória se peça
- `test_nf_entrada_pecas.py` — parser distingue, conferência embutida, divergência qtd
- `test_venda_pecas.py` — adicionar/remover/editar peça, cancelamento devolve estoque
- `test_tagplus_payload_misto.py` — moto+peça no mesmo POST, CFOP por item, peça sem map = erro
- `test_tagplus_backfill_protecao.py` — chassi protegido + parser divergente = divergência, sem update
- `test_tagplus_backfill_delta.py` — delta > 0 reprocessa, sem delta não toca

---

## 16. Riscos e mitigações

| Risco | Mitigação |
|---|---|
| Backfill mal-detecta peça vs moto | Discriminador determinístico via mapping. Sem mapping → divergência (operador resolve) |
| Conferência de peça sem foto causa fraude | Foto opcional v1, badge alerta no detail; tornar obrigatório em v2 conforme política |
| Parser DANFE de NF entrada inflar peça fantasma | Item sem chassi + sem mapping = divergência (não cria peça automaticamente) |
| Saldo SUM lento em listagens | Índice `(peca_id, loja_id, criado_em)` resolve até ~100k movimentos |
| Race em transferência (out + in) | Mesma transação SQLAlchemy; commit único |
| Cancelar venda já emitida na SEFAZ devolve estoque indevidamente | `cancelar_venda` só devolve quando NFe **realmente** cancelada SEFAZ (já existe defesa em `cancelador_nfe`) |
| Renomear `peca_service.py` quebra imports | Refactor coordenado: renomear arquivo + atualizar todos os callers em mesmo commit |

---

## 17. Não-objetivos (out of scope v1)

- Versionamento de preço de peça (sem `hora_tabela_preco_peca`)
- Custo médio / FIFO / margem de peça
- Devolução parcial de peça em venda (apenas cancelamento total)
- Inventário cíclico de peças (apenas ajuste manual)
- Multi-emitente NFe (continua matriz HORA)
- Integração com fornecedor de peças não-Motochefe
- Alertas de estoque mínimo

---

## 18. Pós-implementação

Atualizar `app/hora/CLAUDE.md` com nova seção:
- "11. Peças (cadastro, estoque, faturamento)" — descrevendo schema, services, fronteira (peça ≠ moto), proteção chassi
