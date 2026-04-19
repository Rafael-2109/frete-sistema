# CarVia — Guia de Desenvolvimento

**96 arquivos** | **~55.5K LOC** | **103 templates** | **Atualizado**: 2026-04-15

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
| [fluxograma_refatoracao.md](fluxograma_refatoracao.md) | Mermaid do processo E2E (historico) |

> Campos de tabelas: `.claude/skills/consultando-sql/schemas/tables/{tabela}.json`

---

## Estrutura

```
app/carvia/
  routes/          # 22 sub-rotas (dashboard, importacao, nf, operacao, subcontrato,
                   #   fatura, despesa, fluxo_caixa, conciliacao, cte_complementar,
                   #   custo_entrega, admin, cliente, cotacao_v2, pedido, frete, gerencial, ...)
  services/        # 26+ services (parsers, importacao, cotacao, conferencia, linking,
                   #   carvia_frete, embarque_carvia, dacte_generator, ...)
                   # + documentos/ssw_emissao_service.py
                   # + financeiro/{previnculo_service.py, carvia_historico_match_service.py}
  workers/         # 3 workers RQ com SSL-drop resilience (R15):
                   #   ssw_cte_jobs, ssw_cte_complementar_jobs, verificar_ctrc_ssw_jobs
  models/          # Pacote 11 arquivos: documentos, cte_custos, frete, faturas, cotacao,
                   #   financeiro, config_moto, clientes, admin, tabelas, comissao
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
