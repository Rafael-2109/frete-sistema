# CarVia — Guia de Desenvolvimento

**86 arquivos** | **~48.6K LOC** | **93 templates** | **Atualizado**: 2026-04-13

Gestao de frete subcontratado: importar NF PDFs/XMLs + CTe XMLs, matchear NF-CTe,
subcontratar transportadoras com cotacao via tabelas existentes, gerar faturas cliente e transportadora.
Tambem **emite CTe diretamente no SSW** via Playwright (opcao 004 + 222 + 437).

> Campos de tabelas: `.claude/skills/consultando-sql/schemas/tables/{tabela}.json`
> Revisao de gaps: `app/carvia/REVISAO_GAPS.md` — 37 gaps mapeados com fluxogramas (03/03/2026)
> **Integracao Embarque**: `app/carvia/INTEGRACAO_EMBARQUE.md` — fluxo completo, decisoes, progresso
> **Integracao SSW (Playwright)**: `app/carvia/SSW_INTEGRATION.md` — emissao CTe + CTe Comp. + workers + SSL resilience
> **Importacao/Parsers/Linking**: `app/carvia/IMPORTACAO.md` — pipeline de upload, classificacao, matching, linking retroativo
> **Cotacao/Pricing**: `app/carvia/COTACAO.md` — CidadeAtendida, categorias moto, cotacoes comerciais e de rotas
> **Migrations**: `app/carvia/MIGRATIONS.md` — historico completo de DDL + backfills
> Fluxograma: `app/carvia/fluxograma_refatoracao.md` — Mermaid do processo E2E

---

## Estrutura de Telas (7 documentos + 1 importacao + 1 fluxo caixa + 1 cotacao + 1 config)

| # | Documento | Entidade | URL | Tela |
|---|-----------|----------|-----|------|
| 1 | **NF Venda** | `CarviaNf` | `/carvia/nfs` | Lista + Detalhe (com itens de produto) |
| 2 | **CTe CarVia** | `CarviaOperacao` | `/carvia/operacoes` | Lista (com colunas Transp. Subcontratada + CTe Subcontrato) + Detalhe + Criar/Editar |
| 3 | **CTe Subcontrato** | `CarviaSubcontrato` | `/carvia/subcontratos` | Lista + Detalhe |
| 4 | **CTe Complementar** | `CarviaCteComplementar` | `/carvia/ctes-complementares` | Lista + Criar (via operacao) + Detalhe + Editar |
| 5 | **Custo Entrega** | `CarviaCustoEntrega` | `/carvia/custos-entrega` | Lista + Criar + Detalhe (com anexos AJAX) + Editar |
| 6 | **Fatura CarVia** | `CarviaFaturaCliente` | `/carvia/faturas-cliente` | Lista + Nova (operacoes + CTe Comp.) + Detalhe |
| 7 | **Fatura Subcontrato** | `CarviaFaturaTransportadora` | `/carvia/faturas-transportadora` | Lista + Nova + Detalhe |
| 8 | **Despesas** | `CarviaDespesa` | `/carvia/despesas` | Lista + Criar + Detalhe + Editar |
| 9 | **Importacao** | `ImportacaoService` | `/carvia/importar` | Upload + Review + Confirmar |
| 10 | **Fluxo de Caixa** | `FluxoCaixaService` | `/carvia/fluxo-de-caixa` | Accordions por dia + Pagar/Desfazer + Card Saldo |
| 11 | **Extrato da Conta** | `FluxoCaixaService` | `/carvia/extrato-conta` | Movimentacoes com saldo acumulado + Saldo inicial |
| ~~12~~ | ~~Sessao Cotacao~~ | REMOVIDO (22/03/2026) | — | Feature obsoleta — models, routes, templates deletados |
| 13 | **Conciliacao** | `CarviaConciliacaoService` | `/carvia/conciliacao` | Painel duplo extrato/documentos + Match |
| 14 | **Extrato Bancario** | `CarviaExtratoLinha` | `/carvia/extrato-bancario` | Importar OFX + CSV + Lista linhas |
| 15 | **Configuracoes** | `CarviaModeloMoto` / `CarviaEmpresaCubagem` / `CarviaCategoriaMoto` | `/carvia/configuracoes/modelos-moto` | CRUD inline modelos moto + empresas cubagem + categorias moto |
| 16 | **Admin** | `CarviaAdminAudit` + `AdminService` | `/carvia/admin/auditoria` | Hard delete + Edicao completa + Conversao tipo + Re-link + Auditoria |

### Cross-links entre documentos (navegacao completa)

```
CarviaFaturaCliente (Fatura CarVia)
    |
    |-- 1:N --> CarviaOperacao (CTe CarVia)                [via operacao.fatura_cliente_id]
    |-- 1:N --> CarviaCteComplementar (CTe Complementar)   [via cte_comp.fatura_cliente_id]

CarviaOperacao (CTe CarVia)
    |-- N:M --> CarviaNf (NF Venda)                        [via junction carvia_operacao_nfs]
    |-- 1:N --> CarviaSubcontrato                          [via sub.operacao_id]
    |-- 1:N --> CarviaCteComplementar                      [via cte_comp.operacao_id]
    |-- 1:N --> CarviaCustoEntrega                         [via custo.operacao_id]

CarviaCteComplementar (CTe Complementar)
    |-- 1:N --> CarviaCustoEntrega                         [via custo.cte_complementar_id]

CarviaFaturaTransportadora (Fatura Subcontrato)
    |-- 1:N --> CarviaCustoEntrega                         [via custo.fatura_transportadora_id]
    |                                                        (padrao DespesaExtra.fatura_frete_id do Nacom)

CarviaCustoEntrega (Custo de Entrega)
    |-- 1:N --> CarviaCustoEntregaAnexo                    [via anexo.custo_entrega_id, CASCADE]
```

**Itens de detalhe** sao o elo principal para faturas:
- `CarviaFaturaClienteItem` → FK `operacao_id`, `nf_id`
- `CarviaFaturaTransportadoraItem` → FK `subcontrato_id`, `operacao_id`, `nf_id`

---

## Estrutura de Arquivos

```
app/carvia/
  ├── routes/          # 22 sub-rotas (dashboard, importacao, nf, operacao, subcontrato, fatura, api,
  │                    #   despesa, fluxo_caixa, conciliacao, config, cte_complementar,
  │                    #   custo_entrega, admin, cliente, cotacao_v2, pedido, exportacao, tabela_carvia, receita, frete, gerencial)
  ├── services/        # 26+ services (parsers, matching, importacao, cotacao, cotacao_v2, conferencia,
  │                    #   fatura_pdf_parser, linking, fluxo_caixa, carvia_conciliacao, dacte_pdf_parser,
  │                    #   admin, carvia_frete, embarque_carvia, cliente, config, margem, carvia_tabela,
  │                    #   carvia_csv_razao, carvia_ofx, dacte_generator, moto_recognition, gerencial,
  │                    #   nfe_xml_parser, danfe_pdf_parser)
  │                    # + services/documentos/ssw_emissao_service.py (orquestrador emissao SSW)
  │                    # + services/cte_complementar_persistencia.py (S3 + backfill 222)
  ├── workers/         # 3 workers RQ com SSL-drop resilience (R15):
  │                    #   ssw_cte_jobs.py — emissao 004+007+101+437 (7 etapas)
  │                    #   ssw_cte_complementar_jobs.py — emissao 222 + upload S3
  │                    #   verificar_ctrc_ssw_jobs.py — backfill 101 corretivo (low-priority)
  ├── models/          # Pacote — 11 arquivos (anteriormente models.py monolitico):
  │                    #   documentos.py — CarviaOperacao, CarviaOperacaoNf, CarviaSubcontrato
  │                    #   cte_custos.py — CarviaCteComplementar, CarviaCustoEntrega, CarviaCustoEntregaAnexo,
  │                    #                   CarviaEmissaoCteComplementar (tracking emissao 222)
  │                    #   frete.py — CarviaFrete, CarviaEmissaoCte (tracking emissao SSW 004)
  │                    #   faturas.py — CarviaFaturaCliente, CarviaFaturaTransportadora + items
  │                    #   cotacao.py — CarviaCotacao, CarviaSessaoCotacao, CarviaPedido, etc.
  │                    #   financeiro.py — CarviaContaMovimentacao, CarviaExtratoLinha, CarviaConciliacao,
  │                    #                   CarviaDespesa, CarviaReceita
  │                    #   config_moto.py — CarviaModeloMoto, CarviaCategoriaMoto, CarviaPrecoCategoriaMoto, CarviaEmpresaCubagem
  │                    #   clientes.py — CarviaCliente, CarviaClienteEndereco
  │                    #   admin.py — CarviaAdminAudit
  │                    #   tabelas.py — CarviaTabelaFrete, CidadeAtendida
  │                    #   comissao.py
  │                    #   __init__.py — re-exporta todos os modelos
  └── forms.py         # 4 forms WTForms

app/templates/carvia/
  ├── dashboard.html
  ├── importar.html, importar_resultado.html
  ├── nfs/                     # listar.html, detalhe.html
  ├── listar_operacoes.html, detalhe_operacao.html, criar_manual.html, etc.
  ├── subcontratos/            # listar.html, detalhe.html
  ├── ctes_complementares/     # listar.html, criar.html, detalhe.html, editar.html
  ├── custos_entrega/          # listar.html, criar.html, detalhe.html (com anexos AJAX), editar.html
  ├── faturas_cliente/         # listar.html, nova.html, detalhe.html
  ├── faturas_transportadora/  # listar.html, nova.html, detalhe.html
  ├── despesas/                # listar.html, criar.html, detalhe.html, editar.html
  ├── clientes/                # listar.html, criar.html, detalhe.html, editar.html
  ├── cotacoes/                # listar.html, nova.html, detalhe.html
  ├── pedidos/                 # listar.html, detalhe.html (status_calculado, sem dropdown)
  ├── configuracoes/           # modelos_moto.html, empresas_cubagem.html, categorias_moto.html, parametros.html
  └── admin/                   # auditoria.html, editar_completo.html, converter.html
```

---

## Regras Criticas

### R1: Modulo Isolado — SEM dependencia de Embarque/Frete
CarVia e um subsistema INDEPENDENTE. NAO importar de `app/fretes/`, `app/carteira/`, `app/financeiro/`.
Dominio DIFERENTE: frete inbound (CarVia subcontrata) vs frete outbound (Nacom embarca).
Excecoes permitidas: `app/transportadoras/models.py`, `app/tabelas/models.py`, `app/odoo/utils/cte_xml_parser.py`.

### R2: Lazy Imports nos Routes e Services
Imports de services e models de outros modulos sao LAZY (dentro de funcoes).
NAO mover para module-level — circular imports e startup overhead.
```python
# CORRETO — dentro da funcao
def api_calcular_cotacao():
    from app.carvia.services.cotacao_service import CotacaoService
```

### R3: peso_utilizado = max(bruto, cubado) — SEMPRE recalcular
Apos alterar `peso_bruto` ou `peso_cubado`, OBRIGATORIO chamar `operacao.calcular_peso_utilizado()`.
Cotacao usa `peso_utilizado` — valor stale = cotacao errada.

**Cubado e bruto sao conceitos DISTINTOS** — NAO confundir:
- `peso_bruto`: peso real na balanca
- `peso_cubado`: peso volumetrico (dimensoes × fator cubagem)
- `peso_utilizado`: o MAIOR entre os dois (regra transportadoras)

**Distribuicao de peso entre itens e PROPORCIONAL**, NAO exata por unidade.
Ex: 3 motos de 100kg cada num CTe de 350kg (embalagem) → cada moto = 350/3 = 116.67kg, NAO 100kg.

### R4: Fluxo de Status e Irreversivel (exceto cancelamento)
```
CTe CarVia:         RASCUNHO → COTADO → CONFIRMADO → FATURADO    [CANCELADO exceto FATURADO]
CTe Subcontrato:    PENDENTE → COTADO → CONFIRMADO → FATURADO → CONFERIDO  [CANCELADO exceto FATURADO]
CTe Complementar:   RASCUNHO → EMITIDO → FATURADO                [CANCELADO exceto FATURADO]
Custo Entrega:      PENDENTE → VINCULADO_FT → PAGO               [CANCELADO exceto PAGO via fluxo caixa]
```
NUNCA mover status para tras (ex: CONFIRMADO → COTADO). Cancelar e criar novo.

**Bifurcacao venda/compra — CarVia opera em 2 dominios INDEPENDENTES**
(`app/carvia/models/frete.py:12-19` comenta explicitamente "2 lados: CUSTO + VENDA"):

| Dominio | Artefatos | Precificacao | Conferencia | Gate |
|---------|-----------|--------------|-------------|------|
| **Compra** (custo) | `Sub` → `FaturaTransportadora` | Tabela Nacom | Automatica via `ConferenciaService` com 2 eixos de status | Gate 1: todos subs APROVADO. Gate 2: soma_considerado vs valor_total (tolerancia R$ 1,00) |
| **Venda** (receita) | `Op` → `FaturaCliente` | Tabela CarVia | Manual gerencial binaria (Refator 2.1) | Nenhum gate automatico — decisao humana registrada com auditoria |

**Os dominios NAO tem relacao de bloqueio**. Fatura cliente pode ser emitida com subs
em qualquer status de conferencia. Pagamento (`status=PAGA`) e INDEPENDENTE da conferencia
gerencial (`status_conferencia=CONFERIDO`).

**Conferencia individual de subcontrato** (`status_conferencia`, eixo independente de `status`):
```
Sub.status_conferencia:  PENDENTE → APROVADO | DIVERGENTE
Fatura.status_conferencia cascade:
  Todos APROVADO → CONFERIDO (auto)
  Algum DIVERGENTE → DIVERGENTE
  Mix → EM_CONFERENCIA
```
Fatura Transportadora so aceita CONFERIDO manual se:
1. TODOS subs tem `status_conferencia=APROVADO` (Gate 1)
2. `abs(fatura.valor_total - sum(sub.valor_considerado)) <= R$ 1,00` (Gate 2 — W4 parte 2, espelhando Fretes)

Service: `ConferenciaService` em `app/carvia/services/documentos/conferencia_service.py`.
API conferencia subcontrato: `POST /carvia/api/conferencia-subcontrato/<id>/calcular` e `.../registrar`.
API conferencia fatura: `POST /carvia/faturas-transportadora/<id>/conferencia` com gate de valor.

**Conferencia gerencial da Fatura Cliente** (Refator 2.1 — manual puro):
```
FaturaCliente.status_conferencia:  PENDENTE → CONFERIDO  (binario, manual)
```
Sem gate automatico. Ao aprovar (`POST /faturas-cliente/<id>/aprovar`), grava
`conferido_por/em` + `observacoes_conferencia`. Uma vez CONFERIDO, `pode_editar()`
bloqueia todas as alteracoes (desanexar operacao, editar valor, etc.) ate a
fatura ser reaberta via `POST /faturas-cliente/<id>/reabrir-conferencia` (exige motivo).

### R5: Fatura vincula por status elegivel + fatura_id IS NULL
Faturas CarVia selecionam operacoes `status IN (RASCUNHO, COTADO, CONFIRMADO), fatura_cliente_id IS NULL`.
**CTe Complementares** tambem elegiveis: `status IN (RASCUNHO, EMITIDO), fatura_cliente_id IS NULL`.
Fatura pode conter operacoes + CTe Comp. (ou so um tipo). `valor_total = sum(ops.cte_valor) + sum(ctes_comp.cte_valor)`.
Subcontratos disponiveis para fatura transportadora: `status IN (COTADO, CONFIRMADO), fatura_transportadora_id IS NULL`.
Faturas Subcontrato: criacao desacoplada de subcontratos. Subcontratos sao anexados/desanexados
na tela de detalhe via AJAX (nao na criacao). Ao anexar: `status=FATURADO`, `fatura_transportadora_id=fatura.id`.
Ao desanexar (se fatura nao CONFERIDO): `status=CONFIRMADO`, `fatura_transportadora_id=NULL`.
Faturas CarVia: ao vincular, status muda para FATURADO. NUNCA desvincular operacao apos faturamento.

**Custos de Entrega disponiveis para FT** (padrao DespesaExtra.fatura_frete_id do Nacom):
`status='PENDENTE', fatura_transportadora_id IS NULL`. Ao vincular via `CustoEntregaFaturaService.vincular()`:
`fatura_transportadora_id=ft.id`, `status='VINCULADO_FT'`. Se FT ja esta PAGA, auto-propaga `status='PAGO'`.
Ao desvincular (se FT nao CONFERIDA): `fatura_transportadora_id=NULL`, `status='PENDENTE'`.
**Gate 2 da conferencia FT** inclui CEs: `abs(ft.valor_total - (sum(sub.valor_considerado) + sum(ce.valor))) <= R$ 1,00`.

### R6: Classificacao de CTe por CNPJ emitente
Na importacao, CTes sao classificados automaticamente:
- CNPJ emitente == `CARVIA_CNPJ` (env var) → **CTe CarVia** (CarviaOperacao)
- CNPJ emitente != `CARVIA_CNPJ` → **CTe Subcontrato** (CarviaSubcontrato)
Se `CARVIA_CNPJ` nao configurado, todos CTes sao tratados como CarVia (compatibilidade).

### R7: numero_sequencial_transportadora — auto-increment logico
Cada subcontrato recebe numero sequencial por transportadora.
Gerado via `MAX(numero_sequencial_transportadora) + 1` filtrado por `transportadora_id`.
Unique index parcial: `(transportadora_id, numero_sequencial_transportadora) WHERE NOT NULL`.

### R8: Numeracao sequencial CTe-### e Sub-###
Toda CarviaOperacao recebe `cte_numero = CTe-###` (ex: CTe-001, CTe-002).
Todo CarviaSubcontrato recebe `cte_numero = Sub-###` (ex: Sub-001, Sub-002).
Gerado via `CarviaOperacao.gerar_numero_cte()` e `CarviaSubcontrato.gerar_numero_sub()` — metodos estaticos.
Campo `cte_numero VARCHAR(20)` ja existia — sem DDL, apenas backfill.
Backfill: `scripts/migrations/backfill_numeracao_sequencial_carvia.py`.

### R10: Auto-geracao na saida da portaria (CarviaFreteService orquestrador)
Hook em `portaria/routes.py` chama `CarviaFreteService.lancar_frete_carvia()` (orquestrador unico).
Fluxo atomico por grupo (cnpj_emitente + cnpj_destino):
  1. CarviaOperacao (CTe CarVia — VENDA)
  2. CarviaOperacaoNf (junctions NF→Operacao)
  3. CarviaSubcontrato (CUSTO)
  4. CarviaFrete (com operacao_id + subcontrato_id JA populados)

**Regra de ouro (tabelas)**:
- TABELA CARVIA (preco VENDA) → `CarViaTabelaService.cotar_carvia()` → `CarviaOperacao.cte_valor`
- TABELA NACOM (preco CUSTO) → `CotacaoService.cotar_subcontrato()` → `CarviaSubcontrato.valor_cotado`

**Calculo custo**: DIRETA = rateio (frete_total × peso_grupo/peso_embarque). FRACIONADA = CotacaoService.
**Dedup**: unique constraint `(embarque_id, cnpj_emitente, cnpj_destino)` no banco.
**NF tardia**: se frete ja existe, ATUALIZA totais (nao duplica).
**Nao-bloqueante**: try/except no hook — falha nao impede registro de saida da portaria.
**Pedidos**: CarviaPedido.status atualizado para EMBARCADO apos processamento.
**Vinculacao faturas**: retroativa — ao criar fatura, CarviaFrete.fatura_*_id e atualizado.

### R11: Conciliacao quita titulo
Conciliacao 100% de um documento automaticamente altera status de pagamento:
- `CarviaFaturaCliente`: `status='PAGA'`, `pago_em`, `pago_por`
- `CarviaFaturaTransportadora`: `status_pagamento='PAGO'`, `pago_em`, `pago_por`
- `CarviaDespesa`: `status='PAGO'`, `pago_em`, `pago_por`
- `CarviaCustoEntrega`: `status='PAGO'`, `pago_em`, `pago_por` (apenas se `fatura_transportadora_id IS NULL`; CEs vinculados a FT sao pagos via propagacao automatica da FT)
- `CarviaReceita`: `status='RECEBIDO'`, `recebido_em`, `recebido_por`

Desconciliacao reverte: status → PENDENTE, limpa campos pago_em/pago_por.
**Propagacao FT→CE**: quando FT e paga via conciliacao, `_propagar_status_ces_cobertos()` busca CEs
via `fatura_transportadora_id=ft.id` e marca `status='PAGO'` com `pago_por='auto:...'`.
Ao desconciliar FT: CEs auto-propagados revertem para `VINCULADO_FT` (mantem FK, volta status).

### R12: Fluxo unico para novos fretes (cotacao → embarque → portaria)
Novos fretes CarVia DEVEM passar pelo fluxo:
  CarViaCotacao → CarViaPedido → Embarque (provisorio) → NF → Portaria → CarviaFreteService

**Criacao manual** de CarviaOperacao (wizard/freteiro) e DEPRECATED para novos fluxos.
Templates `criar_manual.html` e `criar_freteiro.html` exibem alerta de deprecacao.

**Import CTe ENRIQUECE** operacao/subcontrato auto-gerado (nao cria duplicata):
- CTe CarVia: busca op `AUTO_PORTARIA` pelas mesmas NFs → se encontra, preenche campos do CTe real
- CTe Subcontrato: busca sub auto pelo mesmo operacao+transportadora → se encontra, preenche campos

**Vinculacao a Fatura permanece MANUAL** (R5):
- Fatura Subcontrato: criada primeiro, depois subcontratos sao anexados via AJAX
- Fatura CarVia: criada vinculando operacoes (CTe antes de Fatura)

### R13: Condicoes Comerciais — Propagacao e Visibilidade
Cotacoes CarVia possuem campos de condicao de pagamento e responsavel do frete (controle financeiro).
5 campos: `condicao_pagamento` (A_VISTA/PRAZO), `prazo_dias` (1-30), `responsavel_frete` (100_REMETENTE/100_DESTINATARIO/50_50/PERSONALIZADO), `percentual_remetente`, `percentual_destinatario`.

**Propagacao automatica**: Cotacao → CarviaFrete (via `CarviaFreteService._criar_frete_completo()`).
Campos existem FISICAMENTE em: `carvia_cotacoes`, `carvia_operacoes`, `carvia_fretes`.
**CarviaOperacao**: campos existem mas NAO sao populados automaticamente (reservados para uso futuro).
**CarviaFaturaCliente NAO tem os campos** — exibicao via lookup (fatura → operacoes → fretes).

**Regra**: campos sao INFORMATIVOS — nao bloqueiam transicao de status em nenhum fluxo.
**Percentuais**: sempre persistidos (ex: 50/50 grava 50.00 e 50.00), mesmo para opcoes fixas.
**Conciliacao**: painel de documentos exibe condicoes comerciais como info extra (sem alterar matching).

### R14: Admin — Hard Delete com Auditoria
GAP-20 previa apenas soft-delete (CANCELADO). `AdminService` permite hard delete com:
1. Verificacao de bloqueios (PAGO, FATURADO com dependentes, conciliado)
2. Serializacao completa (snapshot + filhos cascade) para `CarviaAdminAudit`
3. Limpeza de FKs (nullify), revert de status, limpeza financeira
4. Delete em single transaction
5. Restrito a `@require_admin` (perfil=administrador)

**Acoes auditadas**: HARD_DELETE, FIELD_EDIT, TYPE_CHANGE, RELINK, IMPORT_EDIT
**Bloqueios por entidade**:
- Subcontrato: bloqueado se `fatura_transportadora_id != NULL`
- Fatura Cliente: bloqueado se `conciliado=True`
- Fatura Transportadora: bloqueado se tem `CarviaConciliacao` vinculada
- CTe Complementar: bloqueado se `status=FATURADO`
- Custo Entrega: bloqueado se `status=PAGO` ou `fatura_transportadora_id IS NOT NULL` (desvincular da FT primeiro)
- Despesa: bloqueado se `status=PAGO`

**Preview editavel**: Importacao em `/carvia/importar` permite click-to-edit, remover items e reclassificar CTes/Faturas ANTES de salvar. APIs mutam dados no Redis (`carvia:importacao:{user_id}:{uuid}`).

### R15: Emissao SSW — SSL Drop Resilience (workers Playwright)

Workers que chamam scripts Playwright (60-120s+) **DEVEM** isolar a conexao de banco. PostgreSQL
do Render tem `tcp_keepalive` que mata conexoes idle durante o script. `pool_pre_ping=True` NAO
ajuda — a conexao ja estava checked-out antes do Playwright.

**Padrao canonico** (ver `app/carvia/workers/ssw_cte_jobs.py`):

```python
# ANTES do Playwright (libera conexao do pool):
db.session.commit()   # flush pendencias
db.session.close()    # libera transacao
db.engine.dispose()   # fecha pool (conexoes idle morrem)

# Snapshot de campos ORM em variaveis locais — objeto fica stale durante o Playwright
ctrc_numero_local = emissao.ctrc_numero
filial_local = emissao.filial_ssw

# ... rodar script Playwright via subprocess (60-120s+) ...

# APOS o Playwright (re-buscar + retry):
ensure_connection()                                  # SELECT 1 revive pool
obj = db.session.get(CarviaEmissaoCte, emissao_id)   # re-busca (objeto antigo stale)
# aplicar updates + commit com retry 3x backoff (1s, 2s, 4s) em SSL/DBAPI errors
```

**Implementacao canonica**: `app/carvia/workers/ssw_cte_jobs.py`
- `_liberar_conexao_antes_playwright()` — antes de cada chamada Playwright
- `_commit_pos_playwright(emissao_id, **updates)` — re-busca objeto + retry 3x
- Snapshot ORM em variaveis locais antes de liberar (nao depender de session durante Playwright)

**Quando aplicar**: TODOS os workers que chamam scripts Playwright:
- `ssw_cte_jobs.py` (emissao CTe principal)
- `ssw_cte_complementar_jobs.py` (emissao CTe Complementar opcao 222)
- `verificar_ctrc_ssw_jobs.py` (backfill 101 corretivo)

**Detalhes completos**: `app/carvia/SSW_INTEGRATION.md`

### R16: Pre-Vinculo Extrato <-> Cotacao (frete pre-pago)

Clientes CarVia frequentemente pagam fretes ANTECIPADAMENTE, gerando linhas de
extrato bancario "orfas" (PENDENTE sem documento para conciliar). Quando a
`CarviaFaturaCliente` eh finalmente emitida, fica dificil identificar qual
linha bancaria corresponde a qual fatura no meio de outras transacoes.

**Solucao**: tabela lateral `CarviaPreVinculoExtratoCotacao` permite o usuario
proativamente vincular uma linha de extrato a uma cotacao APROVADA na tela de
detalhe (`cotacoes/detalhe.html`). O pre-vinculo eh SOFT — a linha permanece
`status_conciliacao=PENDENTE`. NAO eh `CarviaConciliacao` (nao polui o modelo
central de conciliacao financeira).

**Fluxo**:
```
ATIVO -> RESOLVIDO (automatico quando fatura chega)
ATIVO -> CANCELADO (usuario desfaz manualmente)
```

**Trigger de resolucao automatica** (`CarviaPreVinculoService.resolver_para_fatura`):
Chamado em 4 pontos de `fatura_routes.py` (try/except nao-bloqueante) apos
criar/editar fatura cliente. Percorre cadeia:
```
CarviaFaturaClienteItem.nf_id -> CarviaNf.numero_nf ->
  CarviaPedidoItem.numero_nf (STRING MATCH — gap Refator 2.5) ->
    CarviaPedido.cotacao_id -> CarviaCotacao
```
Para cada cotacao encontrada com pre-vinculo ATIVO, cria `CarviaConciliacao`
real (`tipo_documento='fatura_cliente'`) e marca pre-vinculo como `RESOLVIDO`
com ponteiros `conciliacao_id` + `fatura_cliente_id` para audit trail.

**Botao manual** "Resolver Pre-Vinculos" no extrato bancario chama
`tentar_resolver_todos_ativos(usuario, dias_lookback=90)` que varre pre-vinculos
ATIVOS e tenta resolver contra faturas cliente dos ultimos 90 dias. Cobre casos
tardios (NF anexada ao pedido apos fatura ja criada).

**UNIQUE parcial**: `(extrato_linha_id, cotacao_id) WHERE status='ATIVO'` — apenas
1 pre-vinculo ATIVO por par (linha, cotacao), permite recriar apos cancelamento.

**Constraint de dominio**: linha deve ser CRÉDITO (pagamento entrante), status
IN (PENDENTE, PARCIAL); cotacao deve estar APROVADO. Cancelamento de RESOLVIDO
eh bloqueado (pedir pra desfazer conciliacao primeiro via Extrato Bancario).

**Nao bloqueante em hooks**: se `resolver_para_fatura` falha (ex: session issue,
cadeia ambigua), a criacao da fatura segue normal. Botao manual cobre.

**Service**: `app/carvia/services/financeiro/previnculo_service.py` (7 metodos).
**Rotas**: `conciliacao_routes.py` — 5 endpoints em `/api/cotacoes/<id>/...` e
`/api/previnculos/...`.
**Templates**: `_modal_previncular_extrato.html`, `_previnculos_cotacao.html`,
includes em `cotacoes/detalhe.html`.

### R17: Historico de Match Extrato <-> Pagador (append-only)

Conciliacoes `fatura_cliente` sao material de aprendizado: a cada conciliacao
criada, o hook em `CarviaConciliacaoService.conciliar()` grava UM EVENTO novo
em `CarviaHistoricoMatchExtrato` com a chave `(descricao_tokens, cnpj_pagador)`
onde:
- `descricao_tokens` = tokens normalizados da **linha de cima** do extrato
  (`CarviaExtratoLinha.descricao`) via `_normalizar()` do sugestao_service
- `cnpj_pagador` = `CarviaFaturaCliente.cnpj_cliente` (pagador efetivo da fatura)

**Tabela e append-only (sem UNIQUE)**: 1 descricao pode fazer match com N
CNPJs (e vice-versa). Contagem de ocorrencias e via `COUNT(*) GROUP BY
cnpj_pagador` na consulta. Sem UniqueViolation por design.

**Boost no scoring**: `pontuar_documentos()` aceita parametro opcional
`cnpjs_historico` (dict `{cnpj: ocorrencias}`). Quando um doc sugerido tem
`cnpj_cliente` presente no dict, o score recebe boost multiplicativo
`score = min(1.0, score * 1.4)`. Preserva calibracao dos 3 sinais originais
(valor 50% / data 30% / nome 20%) — so potencializa docs que ja foram
conciliados antes para a mesma descricao de extrato.

**Escopo atual**: apenas `fatura_cliente` (CREDITO/recebimento). Modelo tem
campo `tipo_documento` preparado para extensao futura (fatura_transportadora,
despesa, custo_entrega, receita).

**Hook nao-bloqueante**: `registrar_aprendizado()` e chamado dentro de
try/except em `conciliar()` — qualquer erro (tabela ausente, cnpj vazio,
tokens vazios) apenas loga warning e segue. Desconciliar NAO remove eventos
(historico e cumulativo, append-only).

**Callsites que aplicam boost**:
- `conciliacao_routes.py::api_documentos_elegiveis` (tela dual-panel)
- `conciliacao_routes.py::api_matches_linha` (modal inline Extrato Bancario)
- `previnculo_service.py::listar_candidatos_extrato` (pre-vinculo cotacao,
  com `cnpj_cliente` preenchido via `cotacao.cliente.cnpj`)

**Fora do escopo**: `api_matches_por_documento` (fluxo inverso doc→linhas)
usa scoring inline proprio e NAO foi modificado — requer refator separado.

**Service**: `app/carvia/services/financeiro/carvia_historico_match_service.py`
**Model**: `CarviaHistoricoMatchExtrato` (pacote `models/financeiro.py`)
**Tabela**: `carvia_historico_match_extrato` (append-only log, sem UNIQUE)
**Migration**: `scripts/migrations/add_carvia_historico_match_extrato.{py,sql}`
**Template**: badge `<i class="fas fa-history">` adicionado em
`_modal_conciliar_inline.html` quando `doc.score_historico=true`

---

## Modelos

> Campos: `.claude/skills/consultando-sql/schemas/tables/{tabela}.json`

| Modelo | Tabela | Gotchas |
|--------|--------|---------|
| CarviaNf | `carvia_nfs` | `chave_acesso_nf` UNIQUE mas nullable (manual/referencia). `tipo_fonte`: PDF_DANFE, XML_NFE, MANUAL, FATURA_REFERENCIA (stub criado por backfill/importacao). **`status`**: ATIVA (default), CANCELADA (soft-delete GAP-20). Campos de auditoria: `cancelado_em`, `cancelado_por`, `motivo_cancelamento`. Rotas: `POST /carvia/nfs/<id>/cancelar`, **`POST /carvia/nfs/<id>/criar-cte`** (cria CTe CarVia diretamente da NF). Helpers: `get_faturas_cliente()`, `get_faturas_transportadora()` |
| CarviaNfItem | `carvia_nf_itens` | Itens de produto da NF. FK `nf_id`. Cascade delete-orphan |
| CarviaOperacao | `carvia_operacoes` | `cte_chave_acesso` UNIQUE nullable. `peso_utilizado` e CALCULADO (R3). FK `fatura_cliente_id`. `nfs_referenciadas_json` (JSONB) armazena refs NF do CTe XML para re-linking retroativo. **`gerar_numero_cte()`**: static method, retorna CTe-### (R8). **Campos SSW**: `ctrc_numero` VARCHAR(30) `CAR-{nCT}-{cDV}`, `cte_xml_path` (S3 `carvia/ctes_xml/`), `cte_pdf_path` (S3 `carvia/ctes_pdf/`), `icms_aliquota` NUMERIC(5,2) (usado para grossing up de complementares). Pacote: `app/carvia/models/documentos.py` |
| CarviaOperacaoNf | `carvia_operacao_nfs` | Junction N:N com UNIQUE(operacao_id, nf_id) |
| CarviaSubcontrato | `carvia_subcontratos` | `valor_final` e @property (valor_acertado ou valor_cotado). FK `transportadora_id` e `tabela_frete_id`. `numero_sequencial_transportadora` (R7). **`gerar_numero_sub()`**: static method, retorna Sub-### (R8). **Conferencia individual**: `valor_considerado`, `status_conferencia` (PENDENTE/APROVADO/DIVERGENTE), `conferido_por`, `conferido_em`, `detalhes_conferencia` (JSONB snapshot) |
| CarviaFaturaCliente | `carvia_faturas_cliente` | **UNIQUE(numero_fatura, cnpj_cliente)**. Status: PENDENTE, EMITIDA, PAGA, CANCELADA. `pago_por`/`pago_em` preenchidos ao pagar. 14 campos extras SSW (tipo_frete, pagador_*, cancelada, etc). `cnpj_cliente` = CNPJ do PAGADOR (NAO do beneficiario/CarVia). Relationship `itens` → CarviaFaturaClienteItem |
| CarviaFaturaClienteItem | `carvia_fatura_cliente_itens` | Itens CTe de detalhe por fatura. FK `fatura_cliente_id` CASCADE. **FK `operacao_id` e `nf_id`** (nullable, resolvidos por LinkingService). Campos: cte_numero, contraparte_cnpj/nome, nf_numero, valor_mercadoria, peso_kg, frete, icms, iss, st, base_calculo |
| CarviaFaturaTransportadora | `carvia_faturas_transportadora` | **UNIQUE(numero_fatura, transportadora_id)**. **2 status independentes**: `status_conferencia` (conferencia documental: PENDENTE/EM_CONFERENCIA/CONFERIDO/DIVERGENTE) e `status_pagamento` (financeiro: PENDENTE/PAGO). `pago_por`/`pago_em` preenchidos ao pagar. Relationship `itens` → CarviaFaturaTransportadoraItem |
| CarviaFaturaTransportadoraItem | `carvia_fatura_transportadora_itens` | Itens de detalhe por fatura subcontrato. FK `fatura_transportadora_id` CASCADE. **FK `subcontrato_id`, `operacao_id`, `nf_id`** (nullable). Campos: cte_numero, cte_data_emissao, contraparte_cnpj/nome, nf_numero, valor_mercadoria, peso_kg, valor_frete, valor_cotado, valor_acertado |
| CarviaCteComplementar | `carvia_cte_complementares` | CTe complementar emitido ao cliente para cobrar custos extras. `numero_comp` COMP-### (`gerar_numero_comp()`) — usado internamente. **UI exibe `cte_numero + ctrc_numero`** via macro `carvia_ref` (commit `672a1836`). FK `operacao_id` NOT NULL (CTe pai). FK `fatura_cliente_id` nullable (fatura que inclui). `cte_valor` NOT NULL. Status: RASCUNHO→EMITIDO→FATURADO, CANCELADO exceto FATURADO. **SEM integracao financeira propria** — financeiro e da CarviaFaturaCliente. `cnpj_cliente`/`nome_cliente` herdados da operacao. **Campos SSW (commit `06f27d0d`)**: `cte_chave_acesso` UNIQUE nullable, `ctrc_numero` VARCHAR(30), `cte_xml_path` (S3), `cte_pdf_path` (S3) — populados pelo worker pos-emissao 222. Pacote: `app/carvia/models/cte_custos.py` |
| CarviaCustoEntrega | `carvia_custos_entrega` | Custos que CarVia pagou/incorreu (DEBITO). `numero_custo` CE-### (`gerar_numero_custo()`). `TIPOS_CUSTO`: DIARIA, REENTREGA, ARMAZENAGEM, DEVOLUCAO, AVARIA, PEDAGIO_EXTRA, TAXA_DESCARGA, OUTROS. **`STATUS_CHOICES`**: PENDENTE, VINCULADO_FT, PAGO, CANCELADO. **FKs**: `operacao_id` NOT NULL, `cte_complementar_id` nullable (se virou CTe Comp para cliente), `frete_id` nullable (populado automatico), **`fatura_transportadora_id` nullable** (FK direta para FT — padrao DespesaExtra.fatura_frete_id do Nacom). `subcontrato_id` ainda existe mas e LEGADO (sera removido em migration destructive). `fornecedor_nome`/`fornecedor_cnpj` opcionais. **COM integracao financeira**: FluxoCaixa (por `data_vencimento`), Conciliacao (`tipo_doc='custo_entrega'`, DEBITO), ContaMovimentacao (automatico). **Integridade CE↔FT**: se `fatura_transportadora_id IS NOT NULL`, CE fica **bloqueado** para conciliacao direta — sera pago via propagacao automatica da FT (`pago_por='auto:...'`). `@property pode_vincular_fatura` (PENDENTE e sem FT). Campos `pago_por`/`pago_em`/`total_conciliado`/`conciliado` identicos a CarviaDespesa. Relationship: `fatura_transportadora` + backref `CarviaFaturaTransportadora.custos_entrega` (dynamic). Service: `CustoEntregaFaturaService` (vincular/desvincular/faturas_disponiveis) |
| CarviaCustoEntregaAnexo | `carvia_custo_entrega_anexos` | Comprovantes S3 (1:N por custo). Segue padrao `AnexoOcorrencia` de devolucao. `ativo` Boolean para soft-delete. Upload AJAX (PDF/JPG/PNG/DOC/XLS/MSG, max 10MB). Download via presigned URL S3. `FileStorage` de `app/utils/file_storage.py` |
| CarviaEmissaoCte | `carvia_emissao_cte` | **Tracking de emissao SSW (opcao 004 + 007 + 101 + 437)**. Status: `PENDENTE → EM_PROCESSAMENTO → SUCESSO/ERRO/CANCELADO`. Etapas: `LOGIN, PREENCHIMENTO, SEFAZ, CONSULTA_101, IMPORTACAO_CTE, FATURA_437, IMPORTACAO_FAT`. FK `nf_id` NOT NULL (NF que motivou), FK `operacao_id` (preenchido por `importar_resultado_cte` via `cte_chave_acesso`). Campos: `placa`, `uf_origem`, `filial_ssw`, `cnpj_tomador`, `frete_valor`, `data_vencimento`, `medidas_json`, `xml_path`/`dacte_path` (LOCAIS temporarios — caminhos S3 finais ficam em `CarviaOperacao.cte_xml_path/cte_pdf_path`), `fatura_numero`, `erro_ssw`, `resultado_json`. Properties `em_andamento` e `finalizado`. Service: `SswEmissaoService`. Worker: `ssw_cte_jobs.emitir_cte_ssw_job(id)` com SSL drop resilience (R15). Pacote: `app/carvia/models/frete.py` |
| CarviaEmissaoCteComplementar | `carvia_emissao_cte_complementar` | **Tracking de emissao CT-e Complementar SSW (opcao 222 + 007 + 101)**. Status: `PENDENTE → EM_PROCESSAMENTO → SUCESSO/ERRO`. Etapas: `PREENCHIMENTO, SEFAZ, CONSULTA_101`. FK `custo_entrega_id` NOT NULL (motiva), FK `cte_complementar_id` NOT NULL (preenchido pos-sucesso), FK `operacao_id` NOT NULL (CTe pai). Campos: `ctrc_pai` VARCHAR(30) `FILIAL-NUMERO-DV`, `motivo_ssw` (C/D/E/R), `filial_ssw`, `valor_calculado` NUMERIC(15,2) (apos grossing up), `icms_aliquota_usada` NUMERIC(5,2) (snapshot do ICMS do pai). Worker: `ssw_cte_complementar_jobs.emitir_cte_complementar_job(id)` — chama script 222 com `valor_base=custo.valor` (auto-calc ICMS via 101 do pai). Pos-sucesso: `_persistir_artefatos_complementar()` faz upload XML/DACTE S3 + backfill `CarviaCteComplementar.ctrc_numero/cte_xml_path/cte_pdf_path`. Retry: `POST /carvia/api/custos-entrega/emissao-comp/<id>/retry` (commit `6ca7b942`). Pacote: `app/carvia/models/cte_custos.py` |
| CarviaContaMovimentacao | `carvia_conta_movimentacoes` | Movimentacoes financeiras da conta. `tipo_doc`: fatura_cliente/fatura_transportadora/despesa/custo_entrega/receita/saldo_inicial/ajuste. `doc_id`=0 para saldo_inicial. **UNIQUE(tipo_doc, doc_id)** impede duplicata. `tipo_movimento`: CREDITO/DEBITO. `valor` sempre positivo. Saldo calculado por SUM (nao armazenado) |
| CarviaSessaoCotacao | `carvia_sessoes_cotacao` | Sessao de cotacao comercial. `numero_sessao` COTACAO-### (prefixo atualizado de SC-###, backfill aplicado). Status: RASCUNHO→ENVIADO→APROVADO/CONTRA_PROPOSTA, CANCELADO (exceto de APROVADO). `valor_contra_proposta` obrigatorio quando CONTRA_PROPOSTA. **Campos contato cliente**: `cliente_nome`, `cliente_email`, `cliente_telefone`, `cliente_responsavel` (todos opcionais). Properties: `valor_total_frete`, `qtd_demandas`, `todas_demandas_com_frete`. `gerar_numero_sessao()`: static method (busca max de ambos prefixos SC e COTACAO) |
| CarviaSessaoDemanda | `carvia_sessao_demandas` | Demanda de rota dentro de sessao. UNIQUE(sessao_id, ordem). FK `transportadora_id` e `tabela_frete_id` (preenchidos ao selecionar opcao). `detalhes_calculo` JSON com breakdown da CalculadoraFrete. `limpar_frete_selecionado()` zera campos ao editar |
| CarviaExtratoLinha | `carvia_extrato_linhas` | Linhas importadas do extrato bancario OFX. `fitid` UNIQUE. `tipo`: CREDITO/DEBITO. `status_conciliacao`: PENDENTE/CONCILIADO/PARCIAL. `total_conciliado` + `saldo_a_conciliar` (@property). Campos enriquecimento CSV: `razao_social`, `observacao` |
| CarviaConciliacao | `carvia_conciliacoes` | Junction N:N extrato↔documento. UNIQUE(extrato_linha_id, tipo_documento, documento_id). `tipo_documento`: fatura_cliente/fatura_transportadora/despesa/custo_entrega/receita. `valor_alocado` sempre positivo |
| CarviaPreVinculoExtratoCotacao | `carvia_previnculos_extrato_cotacao` | **Pre-vinculo soft** entre linha de extrato (CREDITO, PENDENTE/PARCIAL) e cotacao (APROVADO). Nao eh conciliacao financeira — linha continua PENDENTE. Resolvido automaticamente quando fatura cliente chega via cadeia `FaturaItem.nf_id -> NF.numero_nf -> PedidoItem.numero_nf (string) -> Pedido.cotacao_id` (ver R16). Status: `ATIVO -> RESOLVIDO` (auto trigger em fatura_routes.py) OU `ATIVO -> CANCELADO` (soft cancel manual com motivo). UNIQUE PARCIAL `(extrato_linha_id, cotacao_id) WHERE status='ATIVO'`. FKs: `conciliacao_id` (SET NULL) e `fatura_cliente_id` (SET NULL) preenchidos pos-resolucao para audit trail. Service: `app/carvia/services/financeiro/previnculo_service.py`. Pacote: `app/carvia/models/financeiro.py` |
| CarviaHistoricoMatchExtrato | `carvia_historico_match_extrato` | **Log append-only** de eventos de match aprendidos (descricao+CNPJ pagador). Ver R17. Cada conciliacao `fatura_cliente` gera UMA linha. **Sem UNIQUE**: 1 descricao pode ter N CNPJs. Campos: `descricao_linha_raw` (snapshot audit), `descricao_tokens` (chave normalizada via `_normalizar` do sugestao_service), `cnpj_pagador` (`CarviaFaturaCliente.cnpj_cliente`), `tipo_documento` (default `fatura_cliente`), `conciliacao_id` (ponteiro solto), `registrado_em`. Ocorrencias via `COUNT(*) GROUP BY cnpj_pagador`. Boost 1.4x aplicado em `pontuar_documentos()` quando `doc.cnpj_cliente` aparece nos CNPJs aprendidos. Service: `app/carvia/services/financeiro/carvia_historico_match_service.py`. Pacote: `app/carvia/models/financeiro.py` |
| CarviaCategoriaMoto | `carvia_categorias_moto` | Categorias/tipos de moto para precificacao por unidade. `nome` UNIQUE (ex: "Leve", "Pesada", "Scooter"). `ordem` para UI. Soft-delete via `ativo`. Relationships: `modelos` (CarviaModeloMoto), `precos` (CarviaPrecoCategoriaMoto). CRUD em `/carvia/configuracoes/categorias-moto` |
| CarviaModeloMoto | `carvia_modelos_moto` | Modelos de moto para calculo automatico de peso cubado. `nome` UNIQUE. `regex_pattern` para match automatico. Dimensoes (comprimento, largura, altura) + `cubagem_minima`. **`categoria_moto_id`** FK nullable para CarviaCategoriaMoto. CRUD inline em `/carvia/configuracoes/modelos-moto` |
| CarviaPrecoCategoriaMoto | `carvia_precos_categoria_moto` | Preco fixo por unidade para combinacao tabela_frete × categoria_moto. `valor_unitario` NUMERIC(15,2). UNIQUE(tabela_frete_id, categoria_moto_id). Soft-delete via `ativo`. Relationship `tabela_frete` (CarviaTabelaFrete backref `precos_categoria_moto`). CRUD via API em tabelas de frete |
| CarviaEmpresaCubagem | `carvia_empresas_cubagem` | Empresas que utilizam cubagem. `cnpj_empresa` UNIQUE. `considerar_cubagem` Boolean. CRUD inline em `/carvia/configuracoes/empresas-cubagem` |
| CarviaAdminAudit | `carvia_admin_audit` | Auditoria de acoes admin (HARD_DELETE, TYPE_CHANGE, RELINK, FIELD_EDIT, IMPORT_EDIT). `dados_snapshot` JSONB com serializacao completa ANTES da acao. `dados_relacionados` JSONB com filhos cascade-deleted. Indices: acao, (entidade_tipo, entidade_id), executado_em, executado_por |

---

## Importacao, Parsers e Linking

> Detalhes completos: `app/carvia/IMPORTACAO.md`

Pipeline: Upload → Classificacao por CNPJ emitente (R6) → Parsing (5 parsers: XML alta, PDF media-variavel) → Matching 3 niveis (chave → cnpj+numero → nao encontrada) → Linking retroativo (`LinkingService`, 15 metodos, ordem independente).

**Gotchas rapidos**: `cnpj_cliente` = CNPJ do PAGADOR (NAO emissor). Fatura PDF multi-pagina (1/pagina). Pre-check de transportadoras no review.

---

## Cotacao e Pricing

> Detalhes completos: `app/carvia/COTACAO.md`

Dois tipos coexistentes: **Cotacao Comercial** (`COT-###`, fluxo formal) e **Cotacao de Rotas** (`COTACAO-###`, pontual).
Calculo via `CidadeAtendida → TabelaFrete → CalculadoraFrete` (reutiliza utils do sistema principal).
Suporte a preco por categoria de moto (`CarviaPrecoCategoriaMoto`) com deteccao automatica.

---

## Emissao SSW — Integracao Playwright

CarVia emite CTe diretamente no SSW via scripts Playwright standalone (skill `operando-ssw`).
Arquitetura: Route → Service → Model tracking → Worker RQ → Script Playwright → Service importar.

**Detalhes completos** (fluxos, lifecycle, SSL resilience, endpoints, refactor `carvia_ref`):
`app/carvia/SSW_INTEGRATION.md`

**Componentes principais**:
- **Services**: `SswEmissaoService` (`services/documentos/ssw_emissao_service.py`), `cte_complementar_persistencia.py`
- **Workers** (todos com SSL drop resilience R15):
  - `workers/ssw_cte_jobs.py` — emissao CTe principal (opcao 004 + 007 + 101 + 437)
  - `workers/ssw_cte_complementar_jobs.py` — emissao CTe Complementar (opcao 222)
  - `workers/verificar_ctrc_ssw_jobs.py` — backfill 101 corretivo (low-priority)
- **Models de tracking**: `CarviaEmissaoCte` e `CarviaEmissaoCteComplementar` (ver tabela acima)
- **Scripts Playwright**: `.claude/skills/operando-ssw/scripts/emitir_cte_004.py`, `emitir_cte_complementar_222.py`, `consultar_ctrc_101.py`, `gerar_fatura_ssw_437.py`

**Fluxos** (ver `SSW_INTEGRATION.md` para detalhes):
1. **NF → CTe + Fatura**: `POST /carvia/api/nfs/<id>/emitir-cte-ssw` enfileira `CarviaEmissaoCte` PENDENTE → worker executa 004 → SEFAZ → 101 → importar → opcionalmente 437. JS faz polling em `GET /carvia/api/emissao-cte/<id>/status` (5s).
2. **CustoEntrega → CTe Complementar**: `POST /carvia/api/custos-entrega/<id>/emitir-cte-comp` enfileira `CarviaEmissaoCteComplementar` → worker chama script 222 com `valor_base=custo.valor` → auto-calc ICMS via 101 do pai → grossing up → SEFAZ → upload XML/DACTE S3 → backfill `CarviaCteComplementar`.
3. **Retry**: `POST /carvia/api/custos-entrega/emissao-comp/<id>/retry` reseta `status=PENDENTE` e re-enfileira (apenas se ERRO + RASCUNHO).

**Auto-extracao de medidas motos** (`baffaaad`): `SswEmissaoService.extrair_medidas_da_nf(nf_id)` faz GROUP BY `modelo_moto_id` em `CarviaNfItem` se medidas vierem vazias. UI (`nfs/detalhe.html`) mostra preview auto-detectado e mantem campo manual em `<details>` colapsado.

**Regra critica**: ver R15 (SSL Drop Resilience) acima.

---

## Interdependencias

| Importa de | O que | Cuidado |
|-----------|-------|---------|
| `app/transportadoras/models.py` | `Transportadora` | Campo `razao_social` (NAO `nome`), `cnpj`, `freteiro`, `ativo` |
| `app/tabelas/models.py` | `TabelaFrete` | FK de subcontratos. NAO tem campo `ativo` (filtrar por `Transportadora.ativo`) |
| `app/odoo/utils/cte_xml_parser.py` | `CTeXMLParser` | Classe pai de CTeXMLParserCarvia |
| `app/utils/calculadora_frete.py` | `CalculadoraFrete` | Calculo unificado de frete |
| `app/utils/frete_simulador.py` | `buscar_cidade_unificada` | Resolve nome+UF para Cidade obj |
| `app/vinculos/models.py` | `CidadeAtendida` | Vinculos cidade→transportadora via codigo_ibge |
| `app/utils/grupo_empresarial.py` | `GrupoEmpresarialService` | Grupo empresarial (filiais mesma transportadora) |
| `app/utils/tabela_frete_manager.py` | `TabelaFreteManager` | Prepara dict para CalculadoraFrete |
| `app/utils/timezone.py` | `agora_utc_naive` | Todos os models |
| `app/utils/file_storage.py` | `get_file_storage()` | Upload/download de anexos CustoEntrega (S3/local) |

| Exporta para | O que | Cuidado |
|-------------|-------|---------|
| `app/__init__.py` | `init_app()` | Registro do blueprint |
| NINGUEM | — | Modulo isolado, sem dependentes externos |

---

## Permissao

Toggle `sistema_carvia` no model `Usuario`. Decorator `@require_carvia()` em `app/utils/auth_decorators.py`.
Menu condicional em `base.html`: `{% if current_user.sistema_carvia %}`.

---

## Migrations

> Historico completo (24 migrations): `app/carvia/MIGRATIONS.md`

Regra: DDL requer `.py` + `.sql`. Data fixes apenas Python.

---

## Componentes UI

### Wizard Criar CTe CarVia (`criar_manual.html`)
2 cards: **NFs** (selecao com filtro por cliente + checkbox) + **Valor** (R$, obrigatorio).
Sem step de transportadora (removido — CarVia e sempre a transportadora).
NF selecionada popula resumo (peso, valor, destino). Submit cria CarviaOperacao + junctions.

### Criar CTe via NF (`POST /carvia/nfs/<id>/criar-cte`)
Modal no detalhe da NF com valor CTe + observacoes. Cria operacao diretamente da NF (1:1).
Popula automaticamente: cliente (emitente), destino (destinatario), peso, valor mercadoria.

### Autocomplete Transportadora (`selecionar_transportadora.html`)
Input com debounce 300ms + dropdown absoluto `.carvia-autocomplete-results`.
Busca via `GET /carvia/api/opcoes-transportadora?busca=X&uf_destino=Y`.
Ultimo item fixo: "Criar Nova Transportadora" → modal `#modalCriarTransportadora`.
Modal usa `POST /carvia/api/cadastrar-transportadora` (JSON). Apos cadastro: fecha modal + auto-seleciona.
CSS: `css/modules/_carvia.css` (`.carvia-autocomplete-*`)

### Macro `carvia_ref` — Identificador unificado CTe + CTRC

Arquivo: `app/templates/carvia/_macros.html`

Renderiza identificador de `CarviaOperacao` ou `CarviaCteComplementar` no formato unificado
`CTe-### | CTRC SSW {ctrc_numero}` (ex: `"CTe-042 | CTRC SSW CAR-113-9"`).

```jinja
{{ carvia_ref(operacao) }}        {# CTe-042 | CTRC SSW CAR-113-9 #}
{{ carvia_ref(cte_complementar) }} {# CTe Comp. 2037 | CTRC SSW CAR-2037-1 #}
```

Usado em **12 templates** apos refactor `672a1836`:
- `detalhe_operacao.html`, `listar_operacoes.html` (legado)
- `ctes_complementares/{listar,criar,detalhe,editar}.html`
- `subcontratos/{criar,detalhe}.html`
- `faturas_cliente/{nova,detalhe}.html`
- `faturas_transportadora/detalhe.html`
- `custos_entrega/detalhe.html`

**Razao do refactor (commit `672a1836`)**: identificadores internos (`#id` ou `numero_comp = COMP-###`)
sao **incompreensiveis** para o usuario CarVia, que opera no SSW e ve `CTe-042` e `CAR-113-9`.
As UIs agora espelham 1:1 o que o usuario ve no SSW. APIs (`api_routes.py`) enriquecidas com
`ctrc_numero` e `operacao_cte_numero` para alimentar a macro.
