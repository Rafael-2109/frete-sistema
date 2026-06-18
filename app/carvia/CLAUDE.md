<!-- doc:meta
tipo: explanation
camada: L1
sot_de: —
hub: CLAUDE.md
superseded_by: —
atualizado: 2026-06-15
-->
# CarVia — Guia de Desenvolvimento

> **Papel:** guia de desenvolvimento do modulo CarVia — gestao de frete subcontratado (importar NF/CTe, matchear NF-CTe, subcontratar transportadoras, gerar faturas) e emissao de CTe no SSW.

## Indice

- [Contexto](#contexto)
- [Sub-docs (progressive disclosure)](#sub-docs-progressive-disclosure)
- [Estrutura](#estrutura)
- [Regras Criticas](#regras-criticas)
  - [R1: Modulo isolado — SEM dependencia de Embarque/Frete/Financeiro](#r1-modulo-isolado-sem-dependencia-de-embarquefretefinanceiro)
  - [R2: Lazy imports nos routes e services](#r2-lazy-imports-nos-routes-e-services)
  - [R3: peso_utilizado = max(bruto, cubado) — SEMPRE recalcular](#r3-peso_utilizado-maxbruto-cubado-sempre-recalcular)
  - [R4: Fluxo de status e irreversivel (exceto cancelamento)](#r4-fluxo-de-status-e-irreversivel-exceto-cancelamento)
  - [R5: Fatura vincula por status elegivel + fatura_id IS NULL](#r5-fatura-vincula-por-status-elegivel-fatura_id-is-null)
  - [R6: Classificacao de CTe por CNPJ emitente](#r6-classificacao-de-cte-por-cnpj-emitente)
  - [R7: numero_sequencial_transportadora — auto-increment logico](#r7-numero_sequencial_transportadora-auto-increment-logico)
  - [R8: Numeracao sequencial CTe-### / Sub-### / COMP-###](#r8-numeracao-sequencial-cte--sub--comp-)
  - [R10-R13: Orquestrador e condicoes comerciais](#r10-r13-orquestrador-e-condicoes-comerciais)
  - [R11: Conciliacao quita titulo](#r11-conciliacao-quita-titulo)
  - [R14: Admin — Hard Delete com Auditoria](#r14-admin-hard-delete-com-auditoria)
  - [R14.1: Cascade de Cancelamento (B3, 2026-04-18)](#r141-cascade-de-cancelamento-b3-2026-04-18)
  - [R15: Emissao SSW — SSL Drop Resilience](#r15-emissao-ssw-ssl-drop-resilience)
  - [R16 + R17: Pre-vinculo e historico de match](#r16-r17-pre-vinculo-e-historico-de-match)
  - [R18: NF Triangular (2026-04-20) — vinculo NF Transferencia -> NF Venda](#r18-nf-triangular-2026-04-20-vinculo-nf-transferencia---nf-venda)
  - [R19: SOT Tomador/Incoterm = XML do CTe (2026-04-20)](#r19-sot-tomadorincoterm-xml-do-cte-2026-04-20)
  - [R20: "Anexar" tem 2 semanticas — desambiguar ANTES de implementar](#r20-anexar-tem-2-semanticas-desambiguar-antes-de-implementar)
  - [R21: Comissoes — ajustes (debito/credito) + vendedor = usuario](#r21-comissoes-ajustes-debitocredito-vendedor-usuario)
  - [R22: Comprovantes de Pagamento (N:N) — propagacao + conciliacao invertida](#r22-comprovantes-de-pagamento-nn-propagacao--conciliacao-invertida)
- [Modelos](#modelos)
- [Interdependencias](#interdependencias)
- [Permissao](#permissao)

## Contexto

121 arquivos, ~71.0K LOC, 123 templates. Importa NF PDFs/XMLs + CTe XMLs, faz match NF-CTe, subcontrata com cotacao via tabelas existentes, gera faturas de cliente e transportadora e emite CTe direto no SSW via Playwright. Detalhe por topico nos sub-docs (CONFERENCIA, FINANCEIRO, COMPROVANTES, IMPORTACAO, etc.) — prefira ler o sub-doc a reconstruir o contexto a partir do codigo.

**121 arquivos** | **~71.0K LOC** | **125 templates** | **Atualizado**: 2026-06-18

Gestao de frete subcontratado: importar NF PDFs/XMLs + CTe XMLs, matchear NF-CTe, subcontratar transportadoras com cotacao via tabelas existentes, gerar faturas cliente e transportadora. Tambem emite CTe diretamente no SSW via Playwright.

---

## Sub-docs (progressive disclosure)

Sempre prefira ler o sub-doc correspondente ao topico ao inves de reconstruir contexto a partir do codigo.

| Sub-doc | Cobre |
|---------|-------|
| [CONFERENCIA.md](CONFERENCIA.md) | Bifurcacao venda/compra, lifecycle de status, conferencia `CarviaFrete` (Phase C), gates FT |
| [FINANCEIRO.md](FINANCEIRO.md) | Conciliacao, propagacao FT→CE, pre-vinculo extrato↔cotacao (R16), historico de match (R17) |
| [COMPROVANTES.md](COMPROVANTES.md) | Comprovantes de pagamento (N:N cotacao↔NF↔CTe↔fatura), propagacao, flag "Cotacao Paga", conciliacao invertida por cnpj_pagador (R22) |
| [FLUXOS_CRIACAO.md](FLUXOS_CRIACAO.md) | Orquestrador `CarviaFreteService`, hook portaria, fluxo unico cotacao→embarque→NF, condicoes comerciais |
| [IMPORTACAO.md](IMPORTACAO.md) | Pipeline upload → classificacao → parsing → matching → linking retroativo |
| [COTACAO.md](COTACAO.md) | `CidadeAtendida`, categorias moto, cotacoes comerciais e de rotas |
| [SSW_INTEGRATION.md](SSW_INTEGRATION.md) | Emissao CTe via Playwright (004+222+437), SSL drop resilience, macro `carvia_ref` |
| [AUDIT_ADMIN_SERVICE.md](AUDIT_ADMIN_SERVICE.md) | Hard delete, bypass de guards, gaps de auditoria |
| [INTEGRACAO_EMBARQUE.md](INTEGRACAO_EMBARQUE.md) | Fluxo embarque legado, decisoes, progresso (historico) |
| [REVISAO_GAPS.md](REVISAO_GAPS.md) | 37 gaps mapeados com fluxogramas (12/14 corrigidos) |
| [REVISAO_ARQUITETURA_2026.md](REVISAO_ARQUITETURA_2026.md) | Avaliacao arquitetural (modelo ideal venda+subcontratacao) + gaps conceituais em macro/processo/vinculacao/FK/exibicao, com classificacao epistemica por afirmacao |
| [FLUXOGRAMA_COMPLETO.md](FLUXOGRAMA_COMPLETO.md) | Mermaid completo do processo E2E (atualizado) |
| [MIGRATIONS.md](MIGRATIONS.md) | Historico de migrations especificas do CarVia |
| [fluxograma_refatoracao.md](fluxograma_refatoracao.md) | Mermaid do processo E2E (historico) |

> Campos de tabelas: `.claude/skills/consultando-sql/schemas/tables/{tabela}.json`

---

## Estrutura

```
app/carvia/
  routes/          # 31 sub-rotas (dashboard, importacao, nf, nf_transferencia, operacao,
                   #   subcontrato, fatura, despesa, fluxo_caixa, conciliacao, cte_complementar,
                   #   custo_entrega, admin, cliente, cotacao_v2, pedido, frete, gerencial,
                   #   aprovacao, comissao, config, conta_corrente, exportacao, receita,
                   #   scanner, simulador, tabela_carvia, importacao_config, api, anexo,
                   #   comprovante)
  services/        # 44 services em 6 sub-pacotes + 2 root:
                   #   admin/ (admin_service)
                   #   clientes/ (cliente_service)
                   #   documentos/ (carvia_frete, conferencia, embarque_carvia,
                   #                linking, matching, nf_transferencia, operacao_cancel,
                   #                ssw_emissao, aprovacao_frete, anexo, comprovante) — 11
                   #   financeiro/ (conciliacao, csv_razao, historico_match, ofx, pagamento,
                   #                sugestao, comissao, conta_corrente, custo_entrega_autolink,
                   #                custo_entrega_cobertura, custo_entrega_fatura, fluxo_caixa,
                   #                gerencial, previnculo, rateio_conciliacao_helper,
                   #                lancamento_freteiro [2026-06-12: espelho CarVia do
                   #                fechamento de freteiros Nacom — FT sintetica CONFERIDA,
                   #                consumido por app/fretes via lazy import]) — 16
                   #   parsers/ (importacao, importacao_config, cte_xml, danfe_pdf,
                   #            dacte_pdf, fatura_pdf, nfe_xml) — 7
                   #   pricing/ (cotacao, cotacao_v2, margem, moto_recognition,
                   #            carvia_tabela, config) — 6
                   # + cte_complementar_persistencia.py + cte_complementar_service.py (root)
  workers/         # 4 workers RQ com SSL-drop resilience (R15):
                   #   _ssw_helpers, ssw_cte_jobs, ssw_cte_complementar_jobs, verificar_ctrc_ssw_jobs
  utils/           # tomador.py, upload_policies.py, excel_export_helper.py, papeis_frete.py
  models/          # Pacote 15 modulos: admin, anexos, aprovacao, clientes, comissao,
                   #   comprovante, config_moto, conta_corrente, cotacao, cte_custos,
                   #   documentos, faturas, financeiro, frete, tabelas
  forms.py         # 4 forms WTForms

app/templates/carvia/  # 123 templates (dashboard, listagens, detalhes, wizards, modais)
```

---

## Regras Criticas

### R1: Modulo isolado — SEM dependencia de Embarque/Frete/Financeiro
CarVia e um subsistema INDEPENDENTE. NAO importar de `app/fretes/`, `app/carteira/`, `app/financeiro/`. Dominio DIFERENTE: frete inbound (CarVia subcontrata) vs frete outbound (Nacom embarca).

Excecoes permitidas: `app/transportadoras/models.py`, `app/tabelas/models.py`, `app/odoo/utils/cte_xml_parser.py`.

**Excecao do Simulador 3D** (`routes/simulador_routes.py`): le (LAZY, READ-ONLY) `app/embarques` (Embarque/EmbarqueItem), `app/separacao` (Separacao), `app/carteira` (RotaSalva) e `app/monitoramento` (EntregaMonitorada) APENAS para pre-preencher a simulacao de carga — resolve NFs do embarque / da rota do mapa / nao entregues -> `CarviaNf` -> `CarviaNfVeiculo` -> `CarviaModeloMoto`. Sem escrita; helper unico `_resolver_motos_de_nfs(numeros_nf, nf_ids)`. NAO replicar esse cruzamento em services de negocio.

> **Conservas Nacom (carga mista, 2026-06-18)**: o mesmo simulador tambem monta pallets PBR de conservas Nacom e os arranja no baú junto das motos (pallets no piso, motos por cima — caminho critico). A montagem (regras 1-3, modos A-D, overbooking, folga 5cm) vive em `app/carteira/services/palletizacao_service.py` (Camada 1, Python testavel); o arranjo 3D (perfil multi-slab estrado+coluna, empacotamento em 2 fases) em `app/static/js/simulador-carga/bin-packer.js` (Camada 2). Rotas: `api/simulador-carga/pallets-por-separacao` + pallets Nacom (LOTE_*) no modo embarque (`_resolver_dados_embarque`). LAZY read-only de `app/separacao`+`app/producao` (CadastroPalletizacao). Spec/plano: `docs/superpowers/{specs,plans}/2026-06-18-simulador-3d-conservas-nacom*`.

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
NUNCA mover status para tras. Cancelar e criar novo. CarVia opera em **2 dominios independentes** (venda/compra) com conferencia assimetrica (auto no custo, manual na venda). Detalhes completos: [CONFERENCIA.md](CONFERENCIA.md).

**CTe CarVia (`CarviaOperacao`) — ciclo `RASCUNHO → FATURADO → CANCELADO`** (2026-06): os status intermediarios `COTADO`/`CONFIRMADO` da operacao foram DEPRECADOS — a operacao nao espelha mais o ciclo dos subcontratos (permanece RASCUNHO ate ser faturada; desvincular/excluir fatura reverte a RASCUNHO, nao a CONFIRMADO). `CarviaSubcontrato` e `CarviaPedido` MANTEM seus proprios `COTADO`/`CONFIRMADO` (entidades distintas). Migracao de dados unica: `scripts/migrations/carvia_operacao_deprecar_cotado_confirmado.sql`.

### R5: Fatura vincula por status elegivel + fatura_id IS NULL
- Faturas CarVia: operacoes `status NOT IN (FATURADO, CANCELADO), fatura_cliente_id IS NULL` (2026-06: era `RASCUNHO/COTADO/CONFIRMADO`; COTADO/CONFIRMADO da operacao deprecados — ver R4)
- CTe Complementares tambem elegiveis: `status IN (RASCUNHO, EMITIDO), fatura_cliente_id IS NULL`
- Fatura Subcontrato: subs `status IN (COTADO, CONFIRMADO), fatura_transportadora_id IS NULL`
- **NUNCA desvincular operacao apos faturamento**. Subcontratos desanexaveis apenas enquanto FT nao CONFERIDO
- Custos de Entrega disponiveis para FT: `status='PENDENTE', fatura_transportadora_id IS NULL` — ao vincular vira `VINCULADO_FT`
- **Custo de Entrega pode ter `frete_id=NULL`** (2026-05-05): permitido criar CE direto da operacao quando CarviaFrete ainda nao existe (gap operacional). Auto-link best-effort via `tentar_vincular_frete` em todos os pontos de criacao. Para FT: `ces_disponiveis_para_fatura` cobre os 2 cenarios (com ou sem `frete_id`).

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
- **N CTe Complementares por CTe pai sao permitidos** (2026-05-05). Mutex via `CteComplementarService.criar_para_emissao_ssw` bloqueia apenas concorrencia (status PENDENTE/EM_PROCESSAMENTO ja existe para mesma `operacao_id`). Sequenciais sao livres — o SSW opcao 222 e fila unica por CTRC, exigencia da SEFAZ.

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

### R20: "Anexar" tem 2 semanticas — desambiguar ANTES de implementar

No CarVia, "anexar" significa DUAS coisas distintas:

1. **Upload de ARQUIVO** — anexo fisico (`CarviaCustoEntregaAnexo`, `CarviaAnexo`; rotas `/carvia/api/anexo/.../upload`).
2. **VINCULAR entidade a um container** — ex.: "Anexar Subcontratos" = vincular `CarviaSubcontrato` a `CarviaFaturaTransportadora` (rota `anexar_subcontratos_fatura_transportadora`); nenhum arquivo envolvido.

Desambiguar ANTES de implementar qualquer pedido com "anexar"; se ambiguo, perguntar com opcoes concretas ("upload de arquivo OU vincular X a Y?").

**Regra de negocio associada (2026-05-20)**: `pode_anexar_item()` permite VINCULAR mesmo com fatura `CONFERIDA`/`PAGA`/conciliada; `pode_editar()`/`pode_desanexar_subcontrato()` continuam travando nesses status. Vincular NAO recalcula `valor_total` nem re-concilia.

> Promovida da memoria empresa "CarVia anexar = 2 semanticas" (T1.4, 2026-06-12).

### R21: Comissoes — ajustes (debito/credito) + vendedor = usuario (2026-06-15)

Snapshot congela cada CTe no fechamento. Se o `cte_valor` de um CTe ja comissionado muda
(`editar_cte_valor`) ou o CTe/operacao e cancelado, o sistema gera um `CarviaComissaoAjuste`
(delta = (novo − base) × percentual_snapshot; >0 credito, <0 debito) abatido no PROXIMO fechamento
do mesmo vendedor — o fechamento de origem NUNCA muda.

- **Vendedor = `Usuario`**: `vendedor_usuario_id` (FK `usuarios`) e a chave canonica e de matching;
  `vendedor_nome`/`vendedor_email` sao snapshot de exibicao. O select na criacao filtra
  `acesso_comissao_carvia=True AND status='ativo'`.
- **Gatilho** (`ComissaoService.sincronizar_ajustes_cte`, flush-only) em 3 pontos:
  `operacao_routes.editar_cte_valor`, cancelamento direto (`operacao_routes`) e o cascade
  (`operacao_cancel_service`). Base corrente = ultimo ajuste nao-cancelado ou o snapshot.
- **Nunca negativo**: ao criar, ajustes PENDENTE do vendedor sao incorporados
  (`_incorporar_ajustes_pendentes`); se o total ficaria < 0, BLOQUEIA a criacao (debitos acumulam
  ate haver comissao suficiente). Guards tambem em `excluir_cte`/`marcar_pago`.
- **Filtro de criacao = apenas data final (corte)**: `cte_data_emissao <= data_fim` (as comissoes
  "matam o passado" via exclusao de ja-comissionados). `data_inicio` do registro e derivada do CTe
  mais antigo.
- **Criar e Editar usam `<select>` de usuario** (mesmo filtro). `editar_comissao` troca o vendedor
  via `vincular_vendedor` (NUNCA texto livre) — mantem `vendedor_usuario_id` consistente com o snapshot.
- Fechamentos sem vinculo: resolver via `POST /comissoes/<id>/vincular-vendedor` (botao no detalhe).
- Arquivos: `models/comissao.py`, `services/financeiro/comissao_service.py`,
  `routes/comissao_routes.py`, `routes/exportacao_routes.py`,
  `templates/carvia/comissoes/{criar,detalhe,editar}.html`.
  Migration: `scripts/migrations/carvia_comissao_ajustes.{sql,py}` (ver [MIGRATIONS.md](MIGRATIONS.md)).

### R22: Comprovantes de Pagamento (N:N) — propagacao + conciliacao invertida (2026-06-16)

Comprovante (PIX/boleto/TED) anexavel na cadeia **cotacao → NF → CTe → fatura cliente**.
SOT: [COMPROVANTES.md](COMPROVANTES.md).

- **N:N polimorfico**: `CarviaComprovantePagamento` (arquivo S3 1x via `get_file_storage`) +
  `CarviaComprovanteVinculo` (`entidade_tipo` ∈ `cotacao/nf/operacao/fatura_cliente`, sem FK
  fisica). UNIQUE (comprovante, tipo, id). `origem` `MANUAL`/`PROPAGADO`. Soft-delete via `ativo`.
- **Propagacao** `CarviaComprovanteService.sincronizar_cadeia` — idempotente, eixo = NFs;
  chamada no upload (retroativo) e no **hook da criacao de fatura** (heranca futura, isolado
  por SAVEPOINT, espelha o pre-vinculo R16). So propaga para **Fatura Cliente** (decisao Rafael —
  pagamento e do cliente = receita).
- **`cnpj_pagador`** (no comprovante) pode diferir do `cnpj_cliente` da fatura — e o sinal que
  destrava a conciliacao de pagamento despadronizado (antecipado, CNPJ ≠ fatura, N fretes num pgto).
- **Conciliacao invertida** (DESTINO): pagina `GET /carvia/conciliacao/por-comprovante` parte das
  faturas com comprovante e busca a linha do extrato; `api_matches_por_documento` da boost por
  `cnpj_pagador`. Reusa `api_conciliar` — NAO substitui a conciliacao por extrato (R11/R16/R17).
  Ver [FINANCEIRO.md](FINANCEIRO.md).
- UI: card nas 4 telas de detalhe (cotacao/NF/CTe/fatura) + toggle "Cotacao Paga" na cotacao +
  emoji 💳 nas 4 listagens. Widget `templates/carvia/_comprovantes_card.html` +
  `static/carvia/js/comprovantes_widget.js`.
- Arquivos: `models/comprovante.py`, `services/documentos/comprovante_service.py`,
  `routes/comprovante_routes.py`. Migration `scripts/migrations/carvia_comprovante_pagamento.{sql,py}`.

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
| `CarviaComissaoFechamento` / `CarviaComissaoFechamentoCte` / `CarviaComissaoAjuste` | Vendedor = FK `usuarios` (`vendedor_usuario_id`); `vendedor_nome/email` = snapshot. Junction congela o CTe (snapshot). Alterar/cancelar CTe ja comissionado gera `CarviaComissaoAjuste` (delta) abatido no proximo fechamento. `total_comissao` = CTes + `total_ajustes`; NUNCA negativo. Ver R21 |
| `CarviaComprovantePagamento` / `CarviaComprovanteVinculo` | Comprovante de pagamento **N:N** (arquivo S3 1x via `get_file_storage` + vinculo polimorfico `entidade_tipo`∈`cotacao/nf/operacao/fatura_cliente`, sem FK fisica). `origem` `MANUAL`/`PROPAGADO`; `cnpj_pagador` pode != CNPJ da fatura. `sincronizar_cadeia` propaga pela cadeia (idempotente). Soft-delete via `ativo`. Conciliacao invertida usa `cnpj_pagador`. Ver [COMPROVANTES.md](COMPROVANTES.md) |
| `CarviaColeta` / `CarviaColetaNf` | **Coleta "papel de pao"** (redesign stream 3): agrupa N NFs (rascunho: numero+cliente livre) em 1 veiculo (contratado texto+FK opcional, placa, valor, **destino `local_cd` VM/TM**, `data_prevista`=prev. coleta + `data_prevista_chegada`=prev. chegada). `CarviaColetaService.vincular_nf` consolida rascunho->NF real **e propaga `coleta.local_cd` -> `CarviaNf.local_cd`** (= fonte CarVia da flag de CD, stream 1); `editar_coleta` RE-propaga ao mudar destino. **UNIQUE(`carvia_nf_id`)**: 1 NF em no max 1 coleta (guard em `vincular_nf` + `sugerir_nf` exclui ja-vinculadas). `marcar_coletada` cria `CarviaDespesa` tipo `COLETA` a conciliar (bloqueado se CANCELADA). Congela apos COLETADA; sem delete (GAP-20). Rotas `coleta_routes.py`, templates `carvia/coletas/`. `_parse_decimal` trata milhar BR. |
| `CarviaColetaRecebimento` / `CarviaColetaRecebimentoChassi` | **Recebimento por chassi** (redesign stream 4): confere a coleta MOTO A MOTO (`qr_code_lido`+`foto_s3_key` opcional, padrao HORA/Assai REPLICADO — R1). Escaneio LIVRE: chassi casa com `CarviaNfVeiculo` das NFs vinculadas -> VINCULADO, senao ALERTA. **`reconciliar` faz BACKFILL** (chamado por `vincular_nf`). NF "recebida" = todos os seus chassis VINCULADO. `remover_chassi` exige recebimento EM_RECEBIMENTO; `conferir_chassi` bloqueia coleta CANCELADA. Scanner `coletas/recebimento.html`. **Acesso operador**: `usuarios.acesso_recebimento_carvia` (flag) libera SO `/coletas/recebimento` (lista sem valores) + scanner sem ter `sistema_carvia` — `_guard_recebimento` / `pode_acessar_recebimento_carvia`. |
| `CarviaPortalUsuario` / `CarviaPortalUsuarioCnpj` | **Portal do Cliente** (redesign stream 5): usuario EXTERNO ISOLADO do `Usuario` interno (login proprio por sessao em `app/carvia/portal_cliente.py`, blueprint `/portal-cliente` — NUNCA usa Flask-Login interno). Auto-registro PENDENTE (com `grupo_empresa` declarado, hint de vinculo) -> admin aprova (define escopo). Escopo (topico 8): CNPJ_DIRETO (lista em `CarviaPortalUsuarioCnpj`) ou CLIENTE_COMERCIAL (FK `CarviaCliente`, CNPJs via `CarviaClienteEndereco`). `CarviaPortalStatusService`: 5 etapas + `dados_detalhe` (motos por modelo, 4 docs Danfe/DACTE/Fatura/Canhoto, previsoes) — toda query ESCOPADA por CNPJ (seguranca); download via `arquivo_path`->presigned S3. UI cliente: `cvp-*` CSS (`static/css/carvia/portal_cliente.css`), timeline 5 fases. Gestao interna `routes/portal_admin_routes.py` + **acesso interno read-only** (`/carvia/portal-usuarios/<uid>/ver`): usuario CarVia ve a MESMA tela do cliente (templates reusados via flag `interno`). |

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
