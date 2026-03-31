# CarVia — Guia de Desenvolvimento

**52 arquivos** | **~33.3K LOC** | **77 templates** | **Atualizado**: 30/03/2026

Gestao de frete subcontratado: importar NF PDFs/XMLs + CTe XMLs, matchear NF-CTe,
subcontratar transportadoras com cotacao via tabelas existentes, gerar faturas cliente e transportadora.

> Campos de tabelas: `.claude/skills/consultando-sql/schemas/tables/{tabela}.json`
> Revisao de gaps: `app/carvia/REVISAO_GAPS.md` — 37 gaps mapeados com fluxogramas (03/03/2026)
> **Integracao Embarque**: `app/carvia/INTEGRACAO_EMBARQUE.md` — fluxo completo, decisoes, progresso
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
  ├── services/        # 26 services (parsers, matching, importacao, cotacao, cotacao_v2, conferencia,
  │                    #   fatura_pdf_parser, linking, fluxo_caixa, carvia_conciliacao, dacte_pdf_parser,
  │                    #   admin, carvia_frete, embarque_carvia, cliente, config, margem, carvia_tabela,
  │                    #   carvia_csv_razao, carvia_ofx, dacte_generator, moto_recognition, gerencial,
  │                    #   nfe_xml_parser, danfe_pdf_parser)
  ├── models.py        # 36 models (NF, NfItem, Operacao, Junction, Subcontrato, 2 Faturas, 2 FaturaItem,
  │                    #   Despesa, ContaMovimentacao, ExtratoLinha, Conciliacao,
  │                    #   CteComplementar, CustoEntrega, CustoEntregaAnexo,
  │                    #   CategoriaMoto, ModeloMoto, PrecoCategoriaMoto, EmpresaCubagem, AdminAudit,
  │                    #   Config, Cliente, ClienteEndereco, Cotacao, CotacaoMoto, Pedido, PedidoItem,
  │                    #   GrupoCliente, GrupoClienteMembro, TabelaFrete, CidadeAtendida, Receita, Frete)
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
Custo Entrega:      PENDENTE → PAGO                              [CANCELADO exceto PAGO via fluxo caixa]
```
NUNCA mover status para tras (ex: CONFIRMADO → COTADO). Cancelar e criar novo.

**Conferencia individual de subcontrato** (`status_conferencia`, eixo independente de `status`):
```
Sub.status_conferencia:  PENDENTE → APROVADO | DIVERGENTE
Fatura.status_conferencia cascade:
  Todos APROVADO → CONFERIDO (auto)
  Algum DIVERGENTE → DIVERGENTE
  Mix → EM_CONFERENCIA
```
Fatura so aceita CONFERIDO manual se TODOS subs tem `status_conferencia=APROVADO`.
Service: `ConferenciaService` em `app/carvia/services/conferencia_service.py`.
API: `POST /carvia/api/conferencia-subcontrato/<id>/calcular` e `.../registrar`.

### R5: Fatura vincula por status elegivel + fatura_id IS NULL
Faturas CarVia selecionam operacoes `status IN (RASCUNHO, COTADO, CONFIRMADO), fatura_cliente_id IS NULL`.
**CTe Complementares** tambem elegiveis: `status IN (RASCUNHO, EMITIDO), fatura_cliente_id IS NULL`.
Fatura pode conter operacoes + CTe Comp. (ou so um tipo). `valor_total = sum(ops.cte_valor) + sum(ctes_comp.cte_valor)`.
Subcontratos disponiveis para fatura transportadora: `status IN (COTADO, CONFIRMADO), fatura_transportadora_id IS NULL`.
Faturas Subcontrato: criacao desacoplada de subcontratos. Subcontratos sao anexados/desanexados
na tela de detalhe via AJAX (nao na criacao). Ao anexar: `status=FATURADO`, `fatura_transportadora_id=fatura.id`.
Ao desanexar (se fatura nao CONFERIDO): `status=CONFIRMADO`, `fatura_transportadora_id=NULL`.
Faturas CarVia: ao vincular, status muda para FATURADO. NUNCA desvincular operacao apos faturamento.

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
- `CarviaCustoEntrega`: `status='PAGO'`, `pago_em`, `pago_por`
- `CarviaReceita`: `status='RECEBIDO'`, `recebido_em`, `recebido_por`

Desconciliacao reverte: status → PENDENTE, limpa campos pago_em/pago_por.

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

### R9: Admin — Hard Delete com Auditoria
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
- Custo Entrega: bloqueado se `status=PAGO`
- Despesa: bloqueado se `status=PAGO`

**Preview editavel**: Importacao em `/carvia/importar` permite click-to-edit, remover items e reclassificar CTes/Faturas ANTES de salvar. APIs mutam dados no Redis (`carvia:importacao:{user_id}:{uuid}`).

---

## Modelos

> Campos: `.claude/skills/consultando-sql/schemas/tables/{tabela}.json`

| Modelo | Tabela | Gotchas |
|--------|--------|---------|
| CarviaNf | `carvia_nfs` | `chave_acesso_nf` UNIQUE mas nullable (manual/referencia). `tipo_fonte`: PDF_DANFE, XML_NFE, MANUAL, FATURA_REFERENCIA (stub criado por backfill/importacao). **`status`**: ATIVA (default), CANCELADA (soft-delete GAP-20). Campos de auditoria: `cancelado_em`, `cancelado_por`, `motivo_cancelamento`. Rotas: `POST /carvia/nfs/<id>/cancelar`, **`POST /carvia/nfs/<id>/criar-cte`** (cria CTe CarVia diretamente da NF). Helpers: `get_faturas_cliente()`, `get_faturas_transportadora()` |
| CarviaNfItem | `carvia_nf_itens` | Itens de produto da NF. FK `nf_id`. Cascade delete-orphan |
| CarviaOperacao | `carvia_operacoes` | `cte_chave_acesso` UNIQUE nullable. `peso_utilizado` e CALCULADO (R3). FK `fatura_cliente_id`. `nfs_referenciadas_json` (JSONB) armazena refs NF do CTe XML para re-linking retroativo. **`gerar_numero_cte()`**: static method, retorna CTe-### (R8) |
| CarviaOperacaoNf | `carvia_operacao_nfs` | Junction N:N com UNIQUE(operacao_id, nf_id) |
| CarviaSubcontrato | `carvia_subcontratos` | `valor_final` e @property (valor_acertado ou valor_cotado). FK `transportadora_id` e `tabela_frete_id`. `numero_sequencial_transportadora` (R7). **`gerar_numero_sub()`**: static method, retorna Sub-### (R8). **Conferencia individual**: `valor_considerado`, `status_conferencia` (PENDENTE/APROVADO/DIVERGENTE), `conferido_por`, `conferido_em`, `detalhes_conferencia` (JSONB snapshot) |
| CarviaFaturaCliente | `carvia_faturas_cliente` | **UNIQUE(numero_fatura, cnpj_cliente)**. Status: PENDENTE, EMITIDA, PAGA, CANCELADA. `pago_por`/`pago_em` preenchidos ao pagar. 14 campos extras SSW (tipo_frete, pagador_*, cancelada, etc). `cnpj_cliente` = CNPJ do PAGADOR (NAO do beneficiario/CarVia). Relationship `itens` → CarviaFaturaClienteItem |
| CarviaFaturaClienteItem | `carvia_fatura_cliente_itens` | Itens CTe de detalhe por fatura. FK `fatura_cliente_id` CASCADE. **FK `operacao_id` e `nf_id`** (nullable, resolvidos por LinkingService). Campos: cte_numero, contraparte_cnpj/nome, nf_numero, valor_mercadoria, peso_kg, frete, icms, iss, st, base_calculo |
| CarviaFaturaTransportadora | `carvia_faturas_transportadora` | **UNIQUE(numero_fatura, transportadora_id)**. **2 status independentes**: `status_conferencia` (conferencia documental: PENDENTE/EM_CONFERENCIA/CONFERIDO/DIVERGENTE) e `status_pagamento` (financeiro: PENDENTE/PAGO). `pago_por`/`pago_em` preenchidos ao pagar. Relationship `itens` → CarviaFaturaTransportadoraItem |
| CarviaFaturaTransportadoraItem | `carvia_fatura_transportadora_itens` | Itens de detalhe por fatura subcontrato. FK `fatura_transportadora_id` CASCADE. **FK `subcontrato_id`, `operacao_id`, `nf_id`** (nullable). Campos: cte_numero, cte_data_emissao, contraparte_cnpj/nome, nf_numero, valor_mercadoria, peso_kg, valor_frete, valor_cotado, valor_acertado |
| CarviaCteComplementar | `carvia_cte_complementares` | CTe complementar emitido ao cliente para cobrar custos extras. `numero_comp` COMP-### (`gerar_numero_comp()`). FK `operacao_id` NOT NULL (CTe pai). FK `fatura_cliente_id` nullable (fatura que inclui). `cte_valor` NOT NULL. Status: RASCUNHO→EMITIDO→FATURADO, CANCELADO exceto FATURADO. **SEM integracao financeira propria** — financeiro e da CarviaFaturaCliente. `cnpj_cliente`/`nome_cliente` herdados da operacao |
| CarviaCustoEntrega | `carvia_custos_entrega` | Custos que CarVia pagou/incorreu (DEBITO). `numero_custo` CE-### (`gerar_numero_custo()`). `TIPOS_CUSTO`: DIARIA, REENTREGA, ARMAZENAGEM, DEVOLUCAO, AVARIA, PEDAGIO_EXTRA, TAXA_DESCARGA, OUTROS. FK `operacao_id` NOT NULL, FK `cte_complementar_id` nullable. `fornecedor_nome`/`fornecedor_cnpj` opcionais. **COM integracao financeira**: FluxoCaixa (por `data_vencimento`), Conciliacao (`tipo_doc='custo_entrega'`, DEBITO), ContaMovimentacao (automatico). Campos `pago_por`/`pago_em`/`total_conciliado`/`conciliado` identicos a CarviaDespesa |
| CarviaCustoEntregaAnexo | `carvia_custo_entrega_anexos` | Comprovantes S3 (1:N por custo). Segue padrao `AnexoOcorrencia` de devolucao. `ativo` Boolean para soft-delete. Upload AJAX (PDF/JPG/PNG/DOC/XLS/MSG, max 10MB). Download via presigned URL S3. `FileStorage` de `app/utils/file_storage.py` |
| CarviaContaMovimentacao | `carvia_conta_movimentacoes` | Movimentacoes financeiras da conta. `tipo_doc`: fatura_cliente/fatura_transportadora/despesa/custo_entrega/saldo_inicial/ajuste. `doc_id`=0 para saldo_inicial. **UNIQUE(tipo_doc, doc_id)** impede duplicata. `tipo_movimento`: CREDITO/DEBITO. `valor` sempre positivo. Saldo calculado por SUM (nao armazenado) |
| CarviaSessaoCotacao | `carvia_sessoes_cotacao` | Sessao de cotacao comercial. `numero_sessao` COTACAO-### (prefixo atualizado de SC-###, backfill aplicado). Status: RASCUNHO→ENVIADO→APROVADO/CONTRA_PROPOSTA, CANCELADO (exceto de APROVADO). `valor_contra_proposta` obrigatorio quando CONTRA_PROPOSTA. **Campos contato cliente**: `cliente_nome`, `cliente_email`, `cliente_telefone`, `cliente_responsavel` (todos opcionais). Properties: `valor_total_frete`, `qtd_demandas`, `todas_demandas_com_frete`. `gerar_numero_sessao()`: static method (busca max de ambos prefixos SC e COTACAO) |
| CarviaSessaoDemanda | `carvia_sessao_demandas` | Demanda de rota dentro de sessao. UNIQUE(sessao_id, ordem). FK `transportadora_id` e `tabela_frete_id` (preenchidos ao selecionar opcao). `detalhes_calculo` JSON com breakdown da CalculadoraFrete. `limpar_frete_selecionado()` zera campos ao editar |
| CarviaExtratoLinha | `carvia_extrato_linhas` | Linhas importadas do extrato bancario OFX. `fitid` UNIQUE. `tipo`: CREDITO/DEBITO. `status_conciliacao`: PENDENTE/CONCILIADO/PARCIAL. `total_conciliado` + `saldo_a_conciliar` (@property). Campos enriquecimento CSV: `razao_social`, `observacao` |
| CarviaConciliacao | `carvia_conciliacoes` | Junction N:N extrato↔documento. UNIQUE(extrato_linha_id, tipo_documento, documento_id). `tipo_documento`: fatura_cliente/fatura_transportadora/despesa/custo_entrega. `valor_alocado` sempre positivo |
| CarviaCategoriaMoto | `carvia_categorias_moto` | Categorias/tipos de moto para precificacao por unidade. `nome` UNIQUE (ex: "Leve", "Pesada", "Scooter"). `ordem` para UI. Soft-delete via `ativo`. Relationships: `modelos` (CarviaModeloMoto), `precos` (CarviaPrecoCategoriaMoto). CRUD em `/carvia/configuracoes/categorias-moto` |
| CarviaModeloMoto | `carvia_modelos_moto` | Modelos de moto para calculo automatico de peso cubado. `nome` UNIQUE. `regex_pattern` para match automatico. Dimensoes (comprimento, largura, altura) + `cubagem_minima`. **`categoria_moto_id`** FK nullable para CarviaCategoriaMoto. CRUD inline em `/carvia/configuracoes/modelos-moto` |
| CarviaPrecoCategoriaMoto | `carvia_precos_categoria_moto` | Preco fixo por unidade para combinacao tabela_frete × categoria_moto. `valor_unitario` NUMERIC(15,2). UNIQUE(tabela_frete_id, categoria_moto_id). Soft-delete via `ativo`. Relationship `tabela_frete` (CarviaTabelaFrete backref `precos_categoria_moto`). CRUD via API em tabelas de frete |
| CarviaEmpresaCubagem | `carvia_empresas_cubagem` | Empresas que utilizam cubagem. `cnpj_empresa` UNIQUE. `considerar_cubagem` Boolean. CRUD inline em `/carvia/configuracoes/empresas-cubagem` |
| CarviaAdminAudit | `carvia_admin_audit` | Auditoria de acoes admin (HARD_DELETE, TYPE_CHANGE, RELINK, FIELD_EDIT, IMPORT_EDIT). `dados_snapshot` JSONB com serializacao completa ANTES da acao. `dados_relacionados` JSONB com filhos cascade-deleted. Indices: acao, (entidade_tipo, entidade_id), executado_em, executado_por |

---

## Importacao — Fluxo de Classificacao

```
Upload (NF-e XML, CTe XML, DACTE PDF, DANFE PDF, Fatura PDF)
    │
    ├── NF-e XML / PDF DANFE → CarviaNf + CarviaNfItem
    │   └── XML: is_nfe() verifica mod==55 (rejeita CTe disfarçado)
    │
    ├── CTe XML / PDF DACTE → Classificar por CNPJ emitente (R6)
    │   ├── CNPJ == CARVIA_CNPJ → CarviaOperacao (CTe CarVia)
    │   │   └── Vincular NFs via junction (matching por chave de acesso)
    │   └── CNPJ != CARVIA_CNPJ → CarviaSubcontrato (CTe Subcontrato)
    │       └── Vincular a CarviaOperacao via NFs compartilhadas
    │           Se nao encontrar operacao → erro/warning
    │
    ├── [PRE-CHECK] Verificar transportadoras para subcontratos + faturas
    │   └── CNPJs nao cadastrados → transportadoras_nao_encontradas (alerta + modal)
    │
    └── Fatura PDF → parse_multi() (1 fatura por pagina)
        │   Parser: regex → Haiku → Sonnet (3 camadas escalonadas)
        │   Extrai: pagador (cliente), beneficiario (CarVia), tipo frete, itens CTe
        │
        ├── Dedup: verifica banco por (numero_fatura, cnpj_cliente/data_emissao)
        │   Se ja existe → log "Fatura ja existe (ignorando)" + return None
        │
        ├── CNPJ beneficiario == transportadora cadastrada → CarviaFaturaTransportadora
        │   └── Warning se CNPJ beneficiario nao cadastrado e != CARVIA_CNPJ
        └── Outro CNPJ → CarviaFaturaCliente + CarviaFaturaClienteItem (itens)
            cnpj_cliente = cnpj_PAGADOR (NAO cnpj_emissor/beneficiario)
```

**Env var necessaria**: `CARVIA_CNPJ` (apenas digitos, ex: `12345678000199`).
Se nao configurada, todos CTes sao classificados como CarVia (compatibilidade) e um aviso e emitido.

**Pre-check de transportadoras** (no review, ANTES de confirmar):
- `processar_arquivos()` verifica se CNPJs de emitentes de CTes subcontrato e beneficiarios de faturas
  estao cadastrados como transportadoras no banco
- Resultado inclui `transportadoras_nao_encontradas` — lista de CNPJs pendentes com nome/uf/cidade
- Template `importar_resultado.html` mostra alerta com botoes de cadastro rapido (modal AJAX)
- Endpoint `POST /carvia/api/cadastrar-transportadora` (CNPJ, razao_social, cidade, UF, freteiro)
  - Dedup: se CNPJ ja existe, retorna transportadora existente sem erro
  - Formata CNPJ automaticamente (XX.XXX.XXX/XXXX-XX)
- Ao cadastrar, badges na tabela de CTes mudam de vermelho para verde via JS

**Classificacao PDF** (ordem de verificacao):
1. **DACTE**: texto "DACTE"/"Conhecimento de Transporte" ou chave com modelo=57 → `PDF_DACTE`
2. **DANFE**: chave 44 digitos com modelo != 57 → `PDF_DANFE`
3. **Fatura**: fallback → `PDF_FATURA`

**CNPJ matriz vs filial**: Faturas podem usar CNPJ matriz (ex: 0001-49) enquanto DACTEs
usam filial (ex: 0002-20). A classificacao de transportadora busca por CNPJ exato cadastrado.

### Fatura PDF — Multi-Pagina (formato SSW)

PDFs SSW (`ssw.inf.br`) contem N faturas por arquivo (1 por pagina).
`parse_multi()` retorna `List[Dict]` (1 dict por pagina). `parse()` retorna apenas 1o resultado (backwards compat).

**Pagador vs Beneficiario**:
- `cnpj_emissor` / `nome_emissor` = beneficiario (CarVia, quem emite a fatura)
- `cnpj_pagador` / `nome_pagador` = cliente (quem paga) — usado como `cnpj_cliente`
- Bug anterior: `cnpj_emissor` era gravado como `cnpj_cliente` (CNPJ da CarVia em TODAS as faturas)

**Campos SSW extras** (14 novos em CarviaFaturaCliente):
- `tipo_frete` (CIF/FOB), `quantidade_documentos`, `valor_mercadoria`, `valor_icms`, `aliquota_icms`, `valor_pedagio`
- `vencimento_original` (antes de reprogramacao), `cancelada` (flag FATURA CANCELADA → status=CANCELADA)
- `pagador_endereco`, `pagador_cep`, `pagador_cidade`, `pagador_uf`, `pagador_ie`, `pagador_telefone`

---

## Parsers — Ordem de Confiabilidade

| Parser | Confiabilidade | Notas |
|--------|---------------|-------|
| `nfe_xml_parser.py` | Alta | Namespace-agnostic. Fonte de verdade para NF-e. Extrai itens de produto. `is_nfe()` verifica mod==55 |
| `cte_xml_parser_carvia.py` | Alta | Herda CTeXMLParser. `get_nfs_referenciadas()` para matching. `get_emitente()` para classificacao |
| `dacte_pdf_parser.py` | Media-Alta | Multi-formato (SSW, Bsoft, ESL, Lonngren, Montenegro). Deteccao automatica via `_detectar_formato()`. Separa chaves modelo=57 (CTe) de modelo=55 (NF-e). Saida identica a `cte_xml_parser_carvia` + campos extras (formato, tipo_servico, cte_carvia_ref, componentes_frete, volumes) |
| `danfe_pdf_parser.py` | Media | Regex-based com pdfplumber+pypdf fallback. Campo `confianca` (0.0-1.0) |
| `fatura_pdf_parser.py` | Variavel | 3 camadas: Regex (alta) -> Haiku (media) -> Sonnet (baixa). Campo `confianca` + `metodo_extracao` |

### DACTE Multi-Formato — Deteccao e Suporte

| Formato | Emitente(s) | Deteccao (footer) | Campos Extras |
|---------|-------------|-------------------|---------------|
| **SSW** | Tocantins, Velocargas, Dago | `SSW.INF.BR` | Referencia completa |
| **Bsoft** | Transmenezes | `Bsoft Internetworks` | Peso via "PESO X/KG" |
| **ESL** | Transperola | `ESL Informatica` | Origem/Destino via "INICIO/TERMINO DA PRESTACAO", UF-Cidade invertido, PESO TAXADO/CUBADO |
| **Lonngren** | CD Uni Brasil | `Lonngren Sistemas` | Frete via "VALOR TOTAL DO SERVICO" |
| **Montenegro** | Montenegro | `Impresso por :` | Chave robusta (sem strip global), fallback "A RECEBER" |

**Chave de acesso (3 niveis)**: 1) 44 digitos consecutivos → 2) Blocos formatados com separadores (limpa por match, NAO global) → 3) Busca localizada na secao "Chave de acesso"

**Confianca ponderada**: chave=2x, frete=2x, rota=1.5x cada, numero/emitente/peso=1x cada (total 10 pontos)

---

## Matching — Algoritmo de 3 Niveis

1. **CHAVE** — Match exato por `chave_acesso_nf` 44 digitos (alta confianca)
2. **CNPJ_NUMERO** — Fallback por `(cnpj_emitente, numero_nf)` (media confianca)
3. **NAO_ENCONTRADA** — NF referenciada no CTe nao importada

---

## Linking — Vinculacao Cross-Documento

`LinkingService` (`app/carvia/services/linking_service.py`) resolve FKs entre documentos:

| Metodo | Funcao |
|--------|--------|
| `resolver_operacao_por_cte(cte_numero)` | Busca CarviaOperacao por CTe, normaliza zeros a esquerda |
| `resolver_nf_por_numero(nf_numero, cnpj)` | Busca CarviaNf por numero + CNPJ (emitente OU destinatario) |
| `vincular_nf_a_operacoes_orfas(nf)` | Re-linking CTe→NF: busca operacoes com nfs_referenciadas_json que referenciam a NF e cria junctions |
| `vincular_operacao_a_itens_fatura_orfaos(operacao)` | Re-linking CTe→Fat: atualiza operacao_id em itens de fatura orfaos + cria junctions |
| `vincular_nf_a_itens_fatura_orfaos(nf)` | Re-linking NF→Fat: atualiza nf_id em itens de fatura orfaos (incl. stubs FATURA_REFERENCIA) + cria junctions |
| `vincular_operacoes_da_fatura(fatura_id)` | **Backward binding**: seta `fatura_cliente_id` e `status=FATURADO` nas operacoes via itens ja resolvidos |
| `vincular_itens_fatura_cliente(fatura_id, auto_criar_nf)` | Resolve `operacao_id` e `nf_id` em itens existentes (3 niveis de fallback) |
| `_criar_nf_referencia(nf_numero, cnpj, ...)` | Cria CarviaNf stub (FATURA_REFERENCIA) — idempotente |
| `_resolver_nf_via_junction(nf_numero, operacao_id)` | Busca NF via junction carvia_operacao_nfs |
| `_criar_junction_se_necessario(operacao_id, nf_id)` | Cria junction se nao existe — idempotente |
| `criar_itens_fatura_transportadora(fatura_id)` | Gera itens a partir de subcontratos vinculados (usado na importacao) |
| `criar_itens_fatura_transportadora_incremental(fatura_id, sub_ids)` | Gera itens apenas para subcontratos especificos (usado ao anexar) |
| `criar_itens_fatura_cliente_from_operacoes(fatura_id)` | Gera itens a partir de operacoes (faturas manuais) |
| `expandir_itens_com_nfs_do_cte(fatura_id)` | Cria itens suplementares para NFs do CTe ausentes (PDF SSW mostra 1 NF/linha, CTe pode ter N NFs). Valores financeiros NULL para evitar dupla contagem |
| `backfill_todas_faturas()` | One-time para dados existentes |

**Matching de CTe**: `ltrim(cte_numero, '0')` normaliza "00000001" == "1".
**Matching de NF**: numero + CNPJ contraparte (emitente OU destinatario), ambos normalizados.
**Fallback 3 niveis**: 1) Match direto → 2) Via junction → 3) Criar NF referencia (se `auto_criar_nf=True`).

**Chamado automaticamente por**:
- `ImportacaoService.salvar_importacao()` — durante import de fatura PDF
- `ImportacaoService.salvar_importacao()` — apos criar NF: `vincular_nf_a_operacoes_orfas` + `vincular_nf_a_itens_fatura_orfaos`
- `ImportacaoService.salvar_importacao()` — apos criar/reusar CTe: `vincular_operacao_a_itens_fatura_orfaos`
- `fatura_routes.nova_fatura_cliente()` — ao criar fatura manualmente
- `fatura_routes.anexar_subcontratos_fatura_transportadora()` — ao anexar subcontratos via AJAX

**Ordem de importacao**: Independente. Re-linking retroativo garante que TODAS as 6 permutacoes (NF, CTe, Fatura) criam vinculos corretos.

---

## Cotacao — Fluxo via CidadeAtendida

`CotacaoService` usa o MESMO fluxo do sistema principal:
```
Cidade nome + UF → buscar_cidade_unificada() → Cidade.codigo_ibge
→ CidadeAtendida → grupo_empresarial → TabelaFrete → TabelaFreteManager → CalculadoraFrete
```

**Reutiliza** (NAO cria novas utils):
- `buscar_cidade_unificada(cidade, uf)` de `app/utils/frete_simulador.py`
- `CidadeAtendida.query.filter(codigo_ibge)` de `app/vinculos/models.py`
- `GrupoEmpresarialService.obter_transportadoras_grupo()` de `app/utils/grupo_empresarial.py`
- `TabelaFreteManager.preparar_dados_tabela()` de `app/utils/tabela_frete_manager.py`
- `CalculadoraFrete.calcular_frete_unificado()` de `app/utils/calculadora_frete.py`

**Retorno enriquecido**: `lead_time` (do vinculo CidadeAtendida), `icms_destino` (da Cidade)
**Fallback**: Se cidade nao encontrada ou sem vinculos, busca por UF (comportamento anterior)

### Cotacao por Categoria de Moto (Preco por Unidade)

Empresas de moto podem ter preco fixo por unidade em vez de calculo por peso.
Deteccao automatica: se `categorias_moto` fornecido E tabela tem `CarviaPrecoCategoriaMoto`, usa preco por categoria.

```
CarviaTabelaService.cotar_carvia(categorias_moto=[{categoria_id, quantidade}]):
  1. Resolver grupo (existente)
  2. Buscar tabelas (existente)
  3. Para cada tabela:
     → TEM precos por categoria? → _calcular_por_categoria_moto()
     → NAO TEM → calcular_com_tabela_carvia() (peso, existente)
  4. Retorno inclui tipo_calculo: 'CATEGORIA_MOTO' | 'PESO'
```

**ICMS**: Aplicado sobre o total por categoria (mesma logica de `icms_incluso`/`icms_proprio`).
**Backward compat**: Tabelas sem `CarviaPrecoCategoriaMoto` continuam usando calculo por peso.

### Dois tipos de cotacao — coexistem, NAO deprecar

| Feature | Modelo | Prefixo | Label UI | Uso |
|---------|--------|---------|----------|-----|
| Cotacao Comercial | `CarviaCotacao` | `COT-###` | "Cotacao Comercial" | Fluxo formal: cliente → pricing → desconto → aprovacao → pedido |
| Cotacao de Rotas | `CarviaSessaoCotacao` | `COTACAO-###` | "Cotacao de Rotas" | Ferramenta pontual: cotar rota para cliente sob demanda |

Ambos coexistem sem colisao de prefixo. NAO deprecar nenhum.

### Cotacao de Rotas (Ferramenta Comercial)

**Prefixo**: `COTACAO-###` (anteriormente SC-###, backfill aplicado)
**Campos contato cliente**: `cliente_nome`, `cliente_email`, `cliente_telefone`, `cliente_responsavel` (opcionais)
**Autocomplete cidade**: Via `GET /localidades/ajax/cidades_por_uf/<uf>` + cache client-side + filtro debounce 200ms

**Fluxo de status**:
```
RASCUNHO ── enviar ──> ENVIADO ── resposta ──> APROVADO
                                           └─> CONTRA_PROPOSTA (com valor)
CANCELADO <── cancelar (de qualquer estado exceto APROVADO)
```

**Rotas** (`sessao_cotacao_routes.py`):
- HTML: `GET /sessoes-cotacao` (listar), `GET|POST /sessoes-cotacao/nova`, `GET /sessoes-cotacao/<id>` (detalhe)
- HTML: `POST .../adicionar-demanda`, `POST .../remover-demanda/<did>`, `POST .../enviar`, `POST .../resposta`, `POST .../cancelar`
- API: `POST /api/sessao-cotacao/<id>/cotar-demanda/<did>` (retorna todas opcoes + lead_time + breakdown), `POST .../selecionar-opcao/<did>` (grava escolha)

**Validacoes**:
- Enviar: TODAS demandas devem ter frete selecionado
- Cancelar: bloqueado se APROVADO
- Contra proposta: `valor_contra_proposta` obrigatorio
- Remover demanda: bloqueado se for a unica

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

- `scripts/migrations/criar_tabelas_carvia.py` + `.sql` — 6 tabelas base, 18 indices
- `scripts/migrations/adicionar_sistema_carvia_usuarios.py` + `.sql` — Campo no Usuario
- `scripts/migrations/adicionar_seq_subcontrato.py` + `.sql` — `numero_sequencial_transportadora` + unique index parcial + backfill
- `scripts/migrations/adicionar_campos_fatura_cliente_v2.py` + `.sql` — 14 novos campos em `carvia_faturas_cliente` + tabela `carvia_fatura_cliente_itens`
- `scripts/migrations/carvia_linking_v1_schema.py` + `.sql` — FK `operacao_id`/`nf_id` em `carvia_fatura_cliente_itens` + tabela `carvia_fatura_transportadora_itens` (15 cols, 4 indices)
- `scripts/migrations/carvia_linking_v2_backfill.py` — Backfill de FKs em itens existentes (requer v1 antes)
- `scripts/migrations/backfill_carvia_nf_linking.py` + `.sql` — Cria CarviaNf stubs (FATURA_REFERENCIA) para NFs referenciadas em faturas que nunca foram importadas, vincula nf_id e cria junctions
- `scripts/migrations/adicionar_status_pagamento_fatura_transportadora.py` + `.sql` — 3 novos campos (`status_pagamento`, `pago_por`, `pago_em`) + indice
- `scripts/migrations/add_nfs_referenciadas_json_operacoes.py` + `.sql` — Campo JSONB `nfs_referenciadas_json` em carvia_operacoes (refs NF do CTe XML)
- `scripts/migrations/backfill_nfs_referenciadas_json.py` + `.sql` — Backfill: popula JSON a partir de junctions existentes
- `scripts/migrations/criar_tabela_carvia_conta_movimentacoes.py` + `.sql` — Tabela `carvia_conta_movimentacoes` (saldo por SUM, UNIQUE tipo_doc+doc_id)
- `scripts/migrations/adicionar_pago_em_por_carvia.py` + `.sql` — `pago_em`/`pago_por` em `carvia_faturas_cliente` e `carvia_despesas`
- `scripts/migrations/backfill_carvia_fatura_operacao_binding.py` + `.sql` — Backfill: seta `fatura_cliente_id` e `status=FATURADO` em operacoes via itens de fatura existentes
- `scripts/migrations/fix_carvia_faturas_duplicadas.py` + `.sql` — Fix: remover 21 faturas cliente duplicadas (importacao 2x do mesmo PDF)
- `scripts/migrations/add_unique_faturas_carvia.py` + `.sql` — UNIQUE(numero_fatura, cnpj_cliente) em faturas_cliente + UNIQUE(numero_fatura, transportadora_id) em faturas_transportadora
- `scripts/migrations/adicionar_status_carvia_nfs.py` + `.sql` — Campo `status` VARCHAR(20) DEFAULT 'ATIVA' + `cancelado_em`, `cancelado_por`, `motivo_cancelamento` + indice
- `scripts/migrations/backfill_numeracao_sequencial_carvia.py` — Backfill: preenche `cte_numero` NULL com CTe-### (operacoes) e Sub-### (subcontratos). Sem DDL
- `scripts/migrations/criar_tabelas_sessao_cotacao_carvia.py` + `.sql` — 2 tabelas (`carvia_sessoes_cotacao` + `carvia_sessao_demandas`), 5 indices, 2 constraints
- `scripts/migrations/adicionar_contato_sessao_cotacao_carvia.py` + `.sql` — 4 campos contato cliente (cliente_nome, cliente_email, cliente_telefone, cliente_responsavel)
- `scripts/migrations/backfill_prefixo_cotacao_carvia.py` + `.sql` — DML: renomeia SC-### → COTACAO-### em numero_sessao
- `scripts/migrations/criar_tabelas_custo_entrega_cte_complementar.py` + `.sql` — 3 tabelas (`carvia_cte_complementares`, `carvia_custos_entrega`, `carvia_custo_entrega_anexos`), 13 indices
- `scripts/migrations/adicionar_conferencia_subcontrato.py` + `.sql` — 5 campos conferencia em `carvia_subcontratos` (`valor_considerado`, `status_conferencia`, `conferido_por`, `conferido_em`, `detalhes_conferencia`) + indice
- `scripts/migrations/criar_tabelas_categoria_moto.py` + `.sql` — 2 tabelas (`carvia_categorias_moto`, `carvia_precos_categoria_moto`) + FK `categoria_moto_id` em `carvia_modelos_moto` + 3 indices
- `scripts/migrations/criar_tabela_carvia_admin_audit.py` + `.sql` — Tabela `carvia_admin_audit` (auditoria admin: snapshot JSONB, 4 indices, check constraint acoes)

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
