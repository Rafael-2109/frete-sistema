# CarVia — Guia de Desenvolvimento

**102 arquivos** | **~62.7K LOC** | **103 templates** | **Atualizado**: 2026-04-27

Gestao de frete subcontratado: importar NF PDFs/XMLs + CTe XMLs, matchear NF-CTe, subcontratar transportadoras com cotacao via tabelas existentes, gerar faturas cliente e transportadora. Tambem emite CTe diretamente no SSW via Playwright.

---

## Sub-docs (progressive disclosure)

Sempre prefira ler o sub-doc correspondente ao topico ao inves de reconstruir contexto a partir do codigo.

| Sub-doc | Cobre |
|---------|-------|
| [CONFERENCIA.md](CONFERENCIA.md) | Bifurcacao venda/compra, lifecycle de status, conferencia `CarviaFrete` (Phase C), gates FT |
| [FINANCEIRO.md](FINANCEIRO.md) | Conciliacao, propagacao FT→CE, pre-vinculo extrato↔cotacao (R16), historico de match (R17) |
| [FLUXOS_CRIACAO.md](FLUXOS_CRIACAO.md) | Orquestrador `CarviaFreteService`, hook portaria, fluxo unico cotacao→embarque→NF, condicoes comerciais |
| [IMPORTACAO.md](IMPORTACAO.md) | Pipeline upload → classificacao → parsing → matching → linking retroativo |
| [COTACAO.md](COTACAO.md) | `CidadeAtendida`, categorias moto, cotacoes comerciais e de rotas |
| [SSW_INTEGRATION.md](SSW_INTEGRATION.md) | Emissao CTe via Playwright (004+222+437), SSL drop resilience, macro `carvia_ref` |
| [AUDIT_ADMIN_SERVICE.md](AUDIT_ADMIN_SERVICE.md) | Hard delete, bypass de guards, gaps de auditoria |
| [INTEGRACAO_EMBARQUE.md](INTEGRACAO_EMBARQUE.md) | Fluxo embarque legado, decisoes, progresso (historico) |
| [REVISAO_GAPS.md](REVISAO_GAPS.md) | 37 gaps mapeados com fluxogramas (12/14 corrigidos) |
| [FLUXOGRAMA_COMPLETO.md](FLUXOGRAMA_COMPLETO.md) | Mermaid completo do processo E2E (atualizado) |
| [MIGRATIONS.md](MIGRATIONS.md) | Historico de migrations especificas do CarVia |
| [fluxograma_refatoracao.md](fluxograma_refatoracao.md) | Mermaid do processo E2E (historico) |

> Campos de tabelas: `.claude/skills/consultando-sql/schemas/tables/{tabela}.json`

---

## Estrutura

```
app/carvia/
  routes/          # 29 sub-rotas (dashboard, importacao, nf, nf_transferencia, operacao,
                   #   subcontrato, fatura, despesa, fluxo_caixa, conciliacao, cte_complementar,
                   #   custo_entrega, admin, cliente, cotacao_v2, pedido, frete, gerencial,
                   #   aprovacao, comissao, config, conta_corrente, exportacao, receita,
                   #   scanner, simulador, tabela_carvia, importacao_config, api)
  services/        # 39 services em 6 sub-pacotes + 1 root:
                   #   admin/ (admin_service)
                   #   clientes/ (cliente_service)
                   #   documentos/ (carvia_frete, conferencia, embarque_carvia,
                   #                linking, matching, nf_transferencia, operacao_cancel,
                   #                ssw_emissao, aprovacao_frete) — 9
                   #   financeiro/ (conciliacao, csv_razao, historico_match, ofx, pagamento,
                   #                sugestao, comissao, conta_corrente, custo_entrega_cobertura,
                   #                custo_entrega_fatura, fluxo_caixa, gerencial, previnculo,
                   #                rateio_conciliacao_helper) — 14
                   #   parsers/ (importacao, importacao_config, cte_xml, danfe_pdf,
                   #            dacte_pdf, fatura_pdf, nfe_xml) — 7
                   #   pricing/ (cotacao, cotacao_v2, margem, moto_recognition,
                   #            carvia_tabela, config) — 6
                   # + cte_complementar_persistencia.py (root)
  workers/         # 4 workers RQ com SSL-drop resilience (R15):
                   #   _ssw_helpers, ssw_cte_jobs, ssw_cte_complementar_jobs, verificar_ctrc_ssw_jobs
  utils/           # tomador.py, upload_policies.py, excel_export_helper.py, papeis_frete.py
  models/          # Pacote 13 modulos: admin, aprovacao, clientes, comissao, config_moto,
                   #   conta_corrente, cotacao, cte_custos, documentos, faturas, financeiro,
                   #   frete, tabelas
  forms.py         # 4 forms WTForms

app/templates/carvia/  # 103 templates (dashboard, listagens, detalhes, wizards, modais)
```

---

## Regras Criticas

### R1: Modulo isolado — SEM dependencia de Embarque/Frete/Financeiro
CarVia e um subsistema INDEPENDENTE. NAO importar de `app/fretes/`, `app/carteira/`, `app/financeiro/`. Dominio DIFERENTE: frete inbound (CarVia subcontrata) vs frete outbound (Nacom embarca).

Excecoes permitidas: `app/transportadoras/models.py`, `app/tabelas/models.py`, `app/odoo/utils/cte_xml_parser.py`.

### R2: Lazy imports nos routes e services
Imports de services e models de outros modulos sao LAZY (dentro de funcoes). NAO mover para module-level — causa circular imports e startup overhead.

```python
def api_calcular_cotacao():
    from app.carvia.services.cotacao_service import CotacaoService
```

### R3: peso_utilizado = max(bruto, cubado) — SEMPRE recalcular
Apos alterar `peso_bruto` ou `peso_cubado`, OBRIGATORIO chamar `operacao.calcular_peso_utilizado()`. Cotacao usa `peso_utilizado` — valor stale = cotacao errada.

**Distribuicao de peso entre itens e PROPORCIONAL**, NAO exata por unidade. Detalhes: [CONFERENCIA.md](CONFERENCIA.md).

### R4: Fluxo de status e irreversivel (exceto cancelamento)
NUNCA mover status para tras (CONFIRMADO → COTADO e PROIBIDO). Cancelar e criar novo. CarVia opera em **2 dominios independentes** (venda/compra) com conferencia assimetrica (auto no custo, manual na venda). Detalhes completos: [CONFERENCIA.md](CONFERENCIA.md).

### R5: Fatura vincula por status elegivel + fatura_id IS NULL
- Faturas CarVia: operacoes `status IN (RASCUNHO, COTADO, CONFIRMADO), fatura_cliente_id IS NULL`
- CTe Complementares tambem elegiveis: `status IN (RASCUNHO, EMITIDO), fatura_cliente_id IS NULL`
- Fatura Subcontrato: subs `status IN (COTADO, CONFIRMADO), fatura_transportadora_id IS NULL`
- **NUNCA desvincular operacao apos faturamento**. Subcontratos desanexaveis apenas enquanto FT nao CONFERIDO
- Custos de Entrega disponiveis para FT: `status='PENDENTE', fatura_transportadora_id IS NULL` — ao vincular vira `VINCULADO_FT`

### R6: Classificacao de CTe por CNPJ emitente
- CNPJ emitente == `CARVIA_CNPJ` (env var) → `CarviaOperacao` (CTe CarVia)
- CNPJ emitente != `CARVIA_CNPJ` → `CarviaSubcontrato`

Se `CARVIA_CNPJ` nao configurado, todos CTes tratados como CarVia (compatibilidade legada).

### R7: numero_sequencial_transportadora — auto-increment logico
Gerado via `MAX(numero_sequencial_transportadora) + 1` filtrado por `transportadora_id`. Unique index parcial: `(transportadora_id, numero_sequencial_transportadora) WHERE NOT NULL`.

### R8: Numeracao sequencial CTe-### / Sub-### / COMP-###
- `CarviaOperacao.cte_numero` = `CTe-001, CTe-002...` via `gerar_numero_cte()`
- `CarviaSubcontrato.cte_numero` = `Sub-001, Sub-002...` via `gerar_numero_sub()`
- `CarviaCteComplementar.numero_comp` = `COMP-###` via `gerar_numero_comp()`
- **UI exibe `cte_numero + ctrc_numero`** via macro `carvia_ref` (ver [SSW_INTEGRATION.md](SSW_INTEGRATION.md))

### R10-R13: Orquestrador e condicoes comerciais
Novos fretes DEVEM seguir o fluxo unico **Cotacao → Pedido → Embarque → NF → Portaria → `CarviaFreteService.lancar_frete_carvia()`**. Criacao manual de `CarviaOperacao` (wizard/freteiro) esta DEPRECATED. Detalhes: [FLUXOS_CRIACAO.md](FLUXOS_CRIACAO.md).

### R11: Conciliacao quita titulo
Conciliacao 100% de um documento altera automaticamente status (`PAGA`/`PAGO`/`RECEBIDO`) e campos `pago_em`/`pago_por`. Desconciliacao reverte. **Propagacao automatica FT → CE** quando FT e paga. Detalhes: [FINANCEIRO.md](FINANCEIRO.md).

### R14: Admin — Hard Delete com Auditoria
`AdminService` permite hard delete (bypassa status machine) com audit trail em `CarviaAdminAudit`.

**Entidades com hard-delete admin ATIVO** (atualizado 2026-04-18 — B4 sprint hygiene):
- `fatura-cliente` (FC) — bloqueia se `conciliado=True`
- `fatura-transportadora` (FT) — bloqueia se ha `CarviaConciliacao`
- `receita` — sem bloqueio adicional
- `subcontrato-orfao` — apenas legado, sem `frete_id`

**Entidades REMOVIDAS do hard-delete admin** (auditoria W-sessao): `nf`, `operacao`, `subcontrato`, `cte-complementar`, `custo-entrega`, `despesa`, `FIELD_EDIT`. Para estas, usar **fluxo normal de cancelamento**. Se precisar cancelar operacao com dependencias, usar **B3 cascade** (`POST /operacoes/<id>/cascade/cancelar` com feature flag `CARVIA_FEATURE_CASCADE_CANCELAMENTO`).

### R14.1: Cascade de Cancelamento (B3, 2026-04-18)
`app/carvia/services/documentos/operacao_cancel_service.py` fornece cancelamento atomico em ordem topologica (CarviaFrete -> CE -> CTe Comp -> Sub -> Operacao). Bloqueios permanecem (Sub FATURADO, CE PAGO/vinculado FT, CarviaFrete CONFERIDO). Feature flag `CARVIA_FEATURE_CASCADE_CANCELAMENTO` default `False`.

**Gaps de seguranca conhecidos**: [AUDIT_ADMIN_SERVICE.md](AUDIT_ADMIN_SERVICE.md) — 12 gaps mapeados (3 CRITICO, 5 ALTO, 3 MEDIO).

### R15: Emissao SSW — SSL Drop Resilience
Workers Playwright (60-120s+) DEVEM isolar a conexao de banco. PostgreSQL do Render mata conexoes idle; `pool_pre_ping=True` nao ajuda. Padrao canonico: commit+close+dispose ANTES, snapshot ORM em variaveis locais, re-busca + retry 3x backoff DEPOIS.

**Implementacao canonica + fluxos completos**: [SSW_INTEGRATION.md](SSW_INTEGRATION.md).

Aplicar em TODOS os workers que chamam Playwright: `ssw_cte_jobs.py`, `ssw_cte_complementar_jobs.py`, `verificar_ctrc_ssw_jobs.py`.

### R16 + R17: Pre-vinculo e historico de match
Fluxos financeiros avancados (frete pre-pago, aprendizado de match bancario). Detalhes: [FINANCEIRO.md](FINANCEIRO.md).

### R18: NF Triangular (2026-04-20) — vinculo NF Transferencia -> NF Venda
Operacao triangular (industria SP -> filial RJ -> cliente final) emite 2 CTes mas transporta 1 mercadoria. A feature vincula `NF Transferencia -> NF Venda(s)` (1:N) para a UI tratar a operacao como uma unidade.

- **Candidatura**: `cnpj_emitente[:8] == cnpj_destinatario[:8]` (mesma empresa, filiais).
- **Match**: `nf_venda.cnpj_emitente == nf_transf.cnpj_destinatario` (a filial que recebeu a transferencia emite a venda).
- **Peso bruto**: `sum(peso_bruto NFs venda) <= peso_bruto NF transf` — bloqueia se excede.
- **Efetivo vs Candidato**: NF so vira "transferencia efetiva" com pelo menos 1 vinculo ativo. Sem vinculo, e frete comum.
- **Retroatividade**: NF venda em frete CONFERIDO/FATURADO ou fatura -> vinculo permitido com alerta + flag `vinculado_retroativamente` + contexto em JSON.
- **Desvinculo**: bloqueado se NF venda em frete CONFERIDO/FATURADO ou em item de fatura.
- **Impacto nas telas** (default oculta transf efetivas; toggle via query):
  - `/carvia/nfs`: `mostrar_transferencias=1`
  - `/carvia/operacoes`: `incluir_transferencias=1`
  - `/carvia/fretes`: sempre aparece, com badge "Transf. ####" na coluna Emitente. Busca por NF expande para o grupo (transf <-> vendas).
  - `/carvia/pedidos-carvia`: filtra numeros_nf que sao transferencia efetiva.
- **Bloqueio `pode_cancelar`**: NF com vinculos ativos (transf ou venda) nao pode ser cancelada.
- **Arquivos**: `services/documentos/nf_transferencia_service.py`, `routes/nf_transferencia_routes.py`, `templates/carvia/nfs/_modal_inserir_nf_transferencia.html`. Model `CarviaNfVinculoTransferencia` em `models/documentos.py`.

### R19: SOT Tomador/Incoterm = XML do CTe (2026-04-20)
Tomador do frete tem fonte unica: `CarviaOperacao.cte_tomador` (extraido de `<ide>/<toma3>` ou `<toma4>` pelo parser CTe, ou preenchido obrigatoriamente no wizard manual). Campo `tipo_frete` (CIF/FOB) REMOVIDO de `CarviaFaturaCliente` — granularidade errada (fatura agrupa N CTes potencialmente com incoterms diferentes).

- **Fallback FOB/CIF -> tomador removido** (`utils/tomador.py`). Se `cte_tomador=NULL`, UI/Excel exibem vazio — nunca inferem.
- **NF-e `modFrete` capturado** em `carvia_nfs.modalidade_frete` (parser `nfe_xml_parser.get_transporte()`) — exibido na coluna "modFrete" do export NFs, mas nao usado para derivar tomador (SOT = CTe).
- **CTe Comp `motivo`** extraido de `<compl>/<ObsCont>/<xTexto>` com padrao `MOTIVO: ...` (parser `cte_xml_parser_carvia.get_motivo()`). Texto livre preservado (descarga, reentrega, pedagio, etc).

**Exports Excel com DUPLO CABECALHO hierarquico** (linha 1 = grupo mesclado, linha 2 = campos). Helper: `app/carvia/utils/excel_export_helper.py` (`ColunaGrupo`, `Campo`, `grupo_dinamico`).
  - Granularidade: NF=1 linha/item, CTe=1 linha/NF vinculada, CTe Comp=1 linha/comp, Faturas=1 linha/fatura.
  - Agrupamentos: cada export mostra campos da PROPRIA entidade + agrupamentos SUPERIORES (ex.: Fatura aparece no export CTe). NUNCA agrupamento inferior.

---

## Modelos

> Campos de cada tabela: `.claude/skills/consultando-sql/schemas/tables/{tabela}.json`

Lista apenas **gotchas nao-obvios**. Para campos completos, consultar schemas JSON.

| Modelo | Gotcha principal |
|--------|------------------|
| `CarviaNf` | `chave_acesso_nf` UNIQUE mas nullable. `tipo_fonte` inclui `FATURA_REFERENCIA` (stub). `status=CANCELADA` e soft-delete (GAP-20) |
| `CarviaOperacao` | `peso_utilizado` CALCULADO (R3). `nfs_referenciadas_json` (JSONB) para re-linking retroativo. Campos SSW (`ctrc_numero`, paths S3, `icms_aliquota`) em [SSW_INTEGRATION.md](SSW_INTEGRATION.md) |
| `CarviaSubcontrato` | `valor_final` e @property. Conferencia MOVIDA para `CarviaFrete` (Phase C — ver [CONFERENCIA.md](CONFERENCIA.md)) |
| `CarviaFrete` | Unidade de conferencia (Phase C) — ver [CONFERENCIA.md](CONFERENCIA.md) |
| `CarviaFaturaCliente` | **UNIQUE(numero_fatura, cnpj_cliente)**. `cnpj_cliente` = CNPJ do **PAGADOR** (NAO beneficiario/CarVia). `status_conferencia` binario manual (Refator 2.1) |
| `CarviaFaturaTransportadora` | **2 status independentes**: `status_conferencia` (documental) e `status_pagamento` (financeiro). Gate 1 + Gate 2 (ver [CONFERENCIA.md](CONFERENCIA.md)) |
| `CarviaCteComplementar` | SEM integracao financeira propria — financeiro e da `CarviaFaturaCliente`. Campos SSW populados pos-emissao 222 |
| `CarviaCustoEntrega` | **Xerox de DespesaExtra Nacom** (fluxo compra). FK `fatura_transportadora_id` bloqueia conciliacao direta — pagamento via propagacao FT. Service: `CustoEntregaFaturaService` |
| `CarviaEmissaoCte` / `CarviaEmissaoCteComplementar` | Tracking de emissao SSW. Paths LOCAIS temporarios — S3 finais em `CarviaOperacao`/`CarviaCteComplementar`. Ver [SSW_INTEGRATION.md](SSW_INTEGRATION.md) |
| `CarviaContaMovimentacao` | **UNIQUE(tipo_doc, doc_id)** impede duplicata. `doc_id=0` para saldo_inicial. Saldo calculado por SUM, NAO armazenado |
| `CarviaPreVinculoExtratoCotacao` | Vinculo SOFT — linha continua PENDENTE. Status `ATIVO → RESOLVIDO \| CANCELADO`. UNIQUE parcial `WHERE status='ATIVO'`. Ver [FINANCEIRO.md](FINANCEIRO.md) |
| `CarviaHistoricoMatchExtrato` | Append-only log de aprendizado. **Sem UNIQUE** por design (1 descricao → N CNPJs). Ver [FINANCEIRO.md](FINANCEIRO.md) |
| `CarviaAdminAudit` | `dados_snapshot` JSONB com serializacao completa ANTES da acao. Indices em `acao`, `(entidade_tipo, entidade_id)`, `executado_em`, `executado_por` |

---

## Interdependencias

| Importa de | O que | Cuidado |
|-----------|-------|---------|
| `app/transportadoras/models.py` | `Transportadora` | Campo `razao_social` (NAO `nome`), `cnpj`, `freteiro`, `ativo` |
| `app/tabelas/models.py` | `TabelaFrete` | FK de subcontratos. NAO tem campo `ativo` (filtrar via `Transportadora.ativo`) |
| `app/odoo/utils/cte_xml_parser.py` | `CTeXMLParser` | Classe pai de `CTeXMLParserCarvia` |
| `app/utils/calculadora_frete.py` | `CalculadoraFrete` | Calculo unificado de frete |
| `app/utils/frete_simulador.py` | `buscar_cidade_unificada` | Resolve nome+UF → Cidade obj |
| `app/vinculos/models.py` | `CidadeAtendida` | Vinculos cidade→transportadora via `codigo_ibge` |
| `app/utils/grupo_empresarial.py` | `GrupoEmpresarialService` | Filiais mesma transportadora |
| `app/utils/file_storage.py` | `get_file_storage()` | Upload/download anexos `CarviaCustoEntrega` (S3/local) |

| Exporta para | O que |
|-------------|-------|
| `app/__init__.py` | `init_app()` (registro do blueprint) |
| Nenhum outro modulo | Isolado — sem dependentes externos |

---

## Permissao

Toggle `sistema_carvia` no model `Usuario`. Decorator `@require_carvia()` em `app/utils/auth_decorators.py`. Menu condicional em `base.html`: `{% if current_user.sistema_carvia %}`.
