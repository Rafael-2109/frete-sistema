<!-- doc:meta
tipo: explanation
camada: L1
sot_de: —
hub: CLAUDE.md
superseded_by: —
atualizado: 2026-06-19
-->
# Fretes — Guia de Desenvolvimento

> **Papel:** guia de desenvolvimento do modulo Fretes (CORE) — frete real Nacom (industria embarca): Cotacao -> Frete -> CTe -> Lancamento Odoo -> Pagamento -> Conta Corrente.

## Indice

- [Contexto](#contexto)
- [Estrutura](#estrutura)
- [Blueprints](#blueprints)
- [Regras Criticas](#regras-criticas)
  - [R1: Anti-detach SQLAlchemy — extrair dados ANTES da Etapa 6](#r1-anti-detach-sqlalchemy-extrair-dados-antes-da-etapa-6)
  - [R2: Etapa 16 — re-fetch com sessao nova](#r2-etapa-16-re-fetch-com-sessao-nova)
  - [R3: Etapa 8 DESABILITADA — nao reativar sem testes](#r3-etapa-8-desabilitada-nao-reativar-sem-testes)
  - [R4: Etapas 12 e 14 sao OPCIONAIS — erros ignorados](#r4-etapas-12-e-14-sao-opcionais-erros-ignorados)
  - [R5: CNPJ tomador → company mapeado](#r5-cnpj-tomador-company-mapeado)
  - [R6: Tolerancia R$ 5,00 e bloqueio de fatura](#r6-tolerancia-r-500-e-bloqueio-de-fatura)
  - [R7: Lock Redis de re-entrada no lancamento (anti duplo-clique)](#r7-lock-redis-de-re-entrada-no-lancamento-anti-duplo-clique)
  - [R8: Dois vinculos CTe ↔ Frete podem divergir](#r8-dois-vinculos-cte-frete-podem-divergir)
- [Models](#models)
- [Origem do Frete — 2 caminhos](#origem-do-frete-2-caminhos)
  - [Caminho 1: Automatico (a maior parte do volume)](#caminho-1-automatico-a-maior-parte-do-volume)
  - [Caminho 2: Manual](#caminho-2-manual)
  - [Caminho 3: Cancelamento](#caminho-3-cancelamento)
- [Lancamento de Freteiros (fluxo paralelo)](#lancamento-de-freteiros-fluxo-paralelo)
  - [Diferencas chave](#diferencas-chave)
  - [Pontos de atencao](#pontos-de-atencao)
- [CalculadoraFrete — visualizacao vs lancamento](#calculadorafrete-visualizacao-vs-lancamento)
- [Fluxo Lancamento Odoo (16 etapas)](#fluxo-lancamento-odoo-16-etapas)
- [Workers RQ](#workers-rq)
- [Funcoes Exportadas (consumidores externos)](#funcoes-exportadas-consumidores-externos)
- [Interdependencias](#interdependencias)
- [Gotchas](#gotchas)
  - [G1: `buscar_ctes_relacionados` carrega TUDO](#g1-buscar_ctes_relacionados-carrega-tudo)
  - [G2: `l10n_br_data_entrada` SEMPRE atualizado (mesmo retomada)](#g2-l10n_br_data_entrada-sempre-atualizado-mesmo-retomada)
  - [G3: `FreteLancado` e dead code](#g3-fretelancado-e-dead-code)
  - [G4: Rotas `*_antigo` nao removidas](#g4-rotas-_antigo-nao-removidas)
  - [G5: FrotaDespesa.odoo_vendor_bill_id reservado mas nunca preenchido](#g5-frotadespesaodoo_vendor_bill_id-reservado-mas-nunca-preenchido)
  - [G6: Commits explicitos antes Etapa 12 e 14](#g6-commits-explicitos-antes-etapa-12-e-14)
  - [G7: 7 docs em `services/documentacao_odoo/`](#g7-7-docs-em-servicesdocumentacao_odoo)
- [Permissao e Menu](#permissao-e-menu)
- [Skills Relacionadas](#skills-relacionadas)
- [Referencias](#referencias)
  - [Docs internos do modulo](#docs-internos-do-modulo)
  - [Cross-modulo](#cross-modulo)

## Contexto

20 arquivos Python, ~19.0K LOC, 43 templates. Modulo CORE com o `lancamento_odoo_service.py` (16 etapas DFe -> PO -> Invoice). Padroes Odoo (P1-P7) em `app/odoo/CLAUDE.md`; frete real vs teorico em `.claude/references/negocio/FRETE_REAL_VS_TEORICO.md`.

**20 arquivos Python** | **~19.0K LOC** | **43 templates** | **Atualizado**: 2026-06-19

Modulo CORE: gestao de frete real Nacom (industria embarca). Fluxo Cotacao → Frete → CTe → Lancamento Odoo (PO + Invoice) → Pagamento → Conta Corrente.

> Campos de tabelas: `.claude/skills/consultando-sql/schemas/tables/{tabela}.json`
> Padroes Odoo (P1-P7): `app/odoo/CLAUDE.md`
> Frete real vs teorico: `.claude/references/negocio/FRETE_REAL_VS_TEORICO.md`

---

## Estrutura

```
app/fretes/
  ├── __init__.py
  ├── models.py                     # 1.255 LOC — 9 models (Frete, FaturaFrete, DespesaExtra, etc.)
  ├── email_models.py               #    57 LOC — EmailAnexado
  ├── frota_models.py               #   139 LOC — FrotaVeiculo, FrotaDespesa
  ├── routes.py                     # 7.462 LOC — fretes_bp (~90 endpoints) + funcoes exportadas
  ├── cte_routes.py                 #   561 LOC — cte_bp (/fretes/ctes)
  ├── frota_routes.py               #   633 LOC — frota_bp (/fretes/frota)
  ├── email_routes.py               #   138 LOC — emails_bp (/fretes/emails)
  ├── forms.py                      #   323 LOC — 13 FlaskForms
  ├── services/
  │   ├── lancamento_odoo_service.py             # 2.240 LOC — CORE: 16 etapas DFe → PO → Invoice
  │   ├── lancamento_despesa_odoo_service.py     # 1.505 LOC — CORE: idem para DespesaExtra (heranca)
  │   ├── relatorio_analise_fretes_service.py    # 1.711 LOC — Custo real por NF
  │   ├── analises_service.py                    #   859 LOC — Analytics SQL (UF, cidade, transp.)
  │   ├── cancelamento_cte_service.py            #   726 LOC — Cancela CTe (XML Outlook + manual)
  │   ├── despesa_cte_service.py                 #   611 LOC — Vincula CTe complementar → DespesaExtra
  │   └── documentacao_odoo/                     # 7 docs .md (historico de implementacao)
  ├── workers/
  │   └── lancamento_odoo_jobs.py   #   921 LOC — RQ jobs: lancar_frete/despesa/lote
  └── jobs/
      └── cte_cancelamento_outlook_job.py  # 559 LOC — Job Outlook → cancelamentos CTe
```

**Templates**: 43 em `app/templates/fretes/` (inclui subpastas `ctes/`, `frota/`).
**Sem JS/CSS dedicado** — usa Bootstrap + design tokens do layout base.
**Docs raiz**: `DOCUMENTACAO_PROCESSO_LANCAMENTO_FRETE.md`, `README_ANALISES.md`, `devolucao.md`.

---

## Blueprints

| Blueprint | Prefixo | Arquivo | Endpoints |
|-----------|---------|---------|-----------|
| `fretes_bp` | `/fretes` | `routes.py` | ~90 |
| `cte_bp` | `/fretes/ctes` | `cte_routes.py` | ~10 |
| `frota_bp` | `/fretes/frota` | `frota_routes.py` | ~8 |
| `emails_bp` | `/fretes/emails` | `email_routes.py` | ~5 |

Registrados em `app/__init__.py:882-885` (imports) + `:947` (register dos 4 blueprints) via lazy import dentro de `create_app()`.

---

## Regras Criticas

### R1: Anti-detach SQLAlchemy — extrair dados ANTES da Etapa 6
A Etapa 6 (`action_gerar_po_dfe`) demora 60-90s+ via fire-and-poll. SQLAlchemy expira a sessao → `Instance is not bound to a Session`.
**Padrao obrigatorio** (`lancamento_odoo_service.py:1101`, `lancamento_despesa_odoo_service.py:437`):
```python
# ANTES da Etapa 6 — extrair em variaveis locais
frete_fatura_id = frete.fatura_frete_id
frete_numero_fatura = frete.fatura_frete.numero_fatura if frete.fatura_frete else None
frete_cte_id_atual = frete.frete_cte_id
# ... Etapa 6 (60-90s+) ...
```

### R2: Etapa 16 — re-fetch com sessao nova
`db.session.remove()` ANTES de re-buscar `Frete` e `ConhecimentoTransporte` via `db.session.get()`. Nunca usar instancia capturada no inicio do metodo. — FONTE: `lancamento_odoo_service.py:2131`.

### R3: Etapa 8 DESABILITADA — nao reativar sem testes
`onchange_l10n_br_calcular_imposto` no PO zerava valores. Pulada permanentemente em `lancamento_odoo_service.py:1744-1748`. Numeracao das etapas mantem 8 para nao quebrar auditoria.

### R4: Etapas 12 e 14 sao OPCIONAIS — erros ignorados
`onchange_l10n_br_calcular_imposto` na Invoice falha em alguns DFes. Erros logados como warning, fluxo continua. Impostos podem precisar ajuste manual no Odoo.

### R5: CNPJ tomador → company mapeado
`CNPJ_PARA_COMPANY` em `lancamento_odoo_service.py`:
- `61724241000178` → company=1 (FB)
- `61724241000259` → company=3 (SC)
- `61724241000330` → company=4 (CD)
- `18467441000163` → company=5 (LF)
- **Padrao quando nao encontra**: company=4 (CD) com warning. **Pode causar lancamento na empresa errada** se CNPJ novo.

### R6: Tolerancia R$ 5,00 e bloqueio de fatura
Diferenca > R$ 5,00 entre `valor_considerado` ↔ `valor_pago` ou `valor_cotado` → `Frete.status = 'EM_TRATATIVA'`. Constante `FRETE_STATUS_BLOQUEANTES = ('EM_TRATATIVA', 'REJEITADO')` em `models.py:10` impede conferencia de fatura. Flag `considerar_diferenca` permite lancar conta corrente sem aprovacao.

### R7: Lock Redis de re-entrada no lancamento (anti duplo-clique)
Os jobs `lancar_frete_job` e `lancar_despesa_job` (`workers/lancamento_odoo_jobs.py`) adquirem um lock Redis (`SET nx ex=900`) por entidade ANTES de processar: chaves `lancamento_frete_lock:{frete_id}` e `lancamento_despesa_lock:{despesa_id}`. Helpers `_adquirir_lock_lancamento(tipo, id)` / `_liberar_lock_lancamento(tipo, id)` (liberado no `finally`), espelhando `recebimento_lf_jobs.py`.

**Motivo** (IMP-2026-06-08-001): a Etapa 6 (`action_gerar_po_dfe`) demora 60-90s+; sem lock, duplo-clique disparava duas execucoes paralelas do mesmo item que chamavam a Etapa 6 antes de qualquer uma criar o PO → **POs + invoices duplicados** (caso real CTe 135210: PO C2620079+C2620082, invoices COM2/2026/06/0090+0091). Se o lock ja esta retido, o job aborta com `error_type='LANCAMENTO_EM_ANDAMENTO'` e `skipped=True`.

**Fail-open**: se o Redis estiver indisponivel, `_adquirir_lock_lancamento` retorna True (nao bloqueia o lancamento). TTL 900s cobre o timeout do job (600s) + polling da Etapa 6; se o worker morrer, o lock expira sozinho. Camada complementar (nao substituida): `_verificar_lancamento_existente()` + estado do DFe no Odoo. Lote (`lancar_lote_job`) so enfileira jobs individuais — herda o lock de cada um, sem lock proprio.

### R8: Dois vinculos CTe ↔ Frete podem divergir
- `Frete.frete_cte_id` (FK direta para `ConhecimentoTransporte`)
- `ConhecimentoTransporte.frete_id` (FK reversa)

Sao campos diferentes, atualizados em momentos diferentes durante vinculacao manual. Ao consultar CTe atual de um frete: `frete.frete_cte_id` e fonte de verdade.

---

## Models

> Campos completos: `.claude/skills/consultando-sql/schemas/tables/{tabela}.json`

| Model | Tabela | Gotcha principal |
|-------|--------|------------------|
| `Frete` | `fretes` | `valor_cotado` x `valor_cte` x `valor_considerado` x `valor_pago` (4 valores). Status: PENDENTE, EM_TRATATIVA, APROVADO, REJEITADO, PAGO, CANCELADO, **LANCADO_ODOO**. Campos Odoo: `odoo_dfe_id`, `odoo_purchase_order_id`, `odoo_invoice_id` |
| `FaturaFrete` | `faturas_frete` | `status_conferencia` (PENDENTE/EM_CONFERENCIA/CONFERIDO). Conferencia bloqueada se algum frete em `FRETE_STATUS_BLOQUEANTES`. **`nova_fatura` bloqueia fatura repetida** (mesmo `numero_fatura` + `transportadora_id`) na aplicacao — SEM `UNIQUE` no banco (ha duplicatas historicas legitimas, ex. fechamentos de freteiro). Exclusao (`excluir_fatura`) ja bloqueia se ha frete com `numero_cte` (2026-06-24, IMP Talita) |
| `DespesaExtra` | `despesas_extras` | `transportadora_id` e **OVERRIDE**: NULL = usa `frete.transportadora`; preenchido = paga outra transportadora (ex: devolucao por terceiro). Property `transportadora_efetiva` resolve. `pode_lancar_odoo` exige `tipo_documento.upper()=='CTE'` + `despesa_cte_id` + `status='VINCULADO_CTE'` (3 condicoes) |
| `ConhecimentoTransporte` | `conhecimento_transporte` | `dfe_id`, `chave_acesso` UNIQUE. `tipo_cte`: '0'=Normal, '1'=Complementar, '2'=Anulacao, '3'=Substituto. `odoo_status_codigo`: **string** '01'-'07' (NAO int). '04'=PO valido para lancamento, '06'=Concluido aceito so em retomada. `tomador_e_empresa` = CNPJ comeca com `61724241` |
| `ContaCorrenteTransportadora` | `conta_corrente_transportadoras` | `tipo_movimentacao`: CREDITO/DEBITO/COMPENSACAO. Compensacao referencia frete original via `compensacao_frete_id` |
| `AprovacaoFrete` | `aprovacoes_frete` | Status: PENDENTE/APROVADO/REJEITADO. Criada quando `Frete.requer_aprovacao_por_valor()` retorna True |
| `LancamentoFreteOdooAuditoria` | `lancamento_frete_odoo_auditoria` | `etapa` (1-16), `status` (SUCESSO/ERRO/AVISO). FK para `frete_id` OU `despesa_extra_id` (mutuamente exclusivos) |
| `CtePendenciaCancelamento` | `cte_pendencia_cancelamento` | Status: CANCELADO_OK, PENDENTE_FATURA_CONFERIDA, ORPHAN, FRETE_CANCELADO_REVISAR, ERRO, CANCELAMENTO_ODOO_FALHOU |
| `FreteLancado` | `fretes_lancados` | **DEAD CODE** — model legado, lido apenas em rota `/antigo/<id>` (`routes.py:3421`). Nao remover sem migration |

**Constante global** (`models.py:10`): `FRETE_STATUS_BLOQUEANTES = ('EM_TRATATIVA', 'REJEITADO')` — fonte unica usada em routes.py para impedir conferencia de fatura.

---

## Origem do Frete — 2 caminhos

### Caminho 1: Automatico (a maior parte do volume)

`processar_lancamento_automatico_fretes(embarque_id, cnpj_cliente, usuario)` (`routes.py:4343`) e o **trigger central** — invocado por 4 modulos: `embarques`, `faturamento`, `odoo`, `portaria`.

**Gates obrigatorios** (em ordem):
1. `embarque.data_embarque` preenchido (portaria deu saida)
1.1. **ULTIMA saida (embarque bifurcado VM/TM)** — `verificar_requisitos` (REQUISITO 0.1) usa `app.utils.local_cd.cds_pendentes_de_saida(embarque)`: em embarque MISTO (itens ativos em >1 `local_cd`), o frete so dispara quando TODOS os CDs ja deram saida na portaria; a 1a saida carimba `data_embarque` mas NAO libera o frete (senao nasceria sem os itens do CD pendente). Embarque de 1 CD = sem restricao (comportamento legado; nao exige `ControlePortaria`). Espelhado em TODOS os 4 caminhos de disparo: CarVia (`CarviaFreteService._processar`), **Op. Assai** (`verificar_requisitos_op_assai`) e a **rota manual** (`processar_lancamento_frete` — ver Caminho 2). A mensagem de bloqueio vem da constante unica `MOTIVO_GATE_CD` (`"Aguardando saída dos CDs"`, topo de `routes.py`) usada pelos 2 gates Nacom/Op.Assai + o acoplamento da rota manual. Gate central em `verificar_requisitos` cobre os 5 call sites Nacom de `processar_lancamento_automatico_fretes`. Testes: `tests/fretes/test_frete_ultima_saida.py`, `tests/fretes/test_status_portaria_agregado.py`.
2. `validar_cnpj_embarque_faturamento(embarque_id)` retorna sucesso (TODAS as NFs validadas, sem `erro_validacao`)
3. `verificar_requisitos_para_lancamento_frete(embarque_id, cnpj)` — 5 requisitos: itens ativos, NFs faturadas, sem erros, transportadora definida, NFs do CNPJ existem
4. `Frete.query.filter_by(embarque_id, cnpj_cliente).first()` retorna None (idempotencia)

**Uma vez liberado**, `lancar_frete_automatico(embarque_id, cnpj, usuario)` (`routes.py:3714`) calcula `valor_cotado` baseado em **`tipo_carga`** do embarque:

| `tipo_carga` | Tabela usada | Calculo de `valor_cotado` |
|--------------|--------------|--------------------------|
| `DIRETA` | Tabela do **EMBARQUE** (`embarque.tabela_*`) | `valor_frete_total_embarque * (peso_cnpj / peso_total_embarque)` — proporcional ao peso |
| `FRACIONADA` | Tabela do **ITEM** (`embarque_item.tabela_*`) | `calcular_valor_frete_pela_tabela(tabela, peso_cnpj, valor_cnpj)` — direto por CNPJ |
| `FOB` (transportadora `'FOB - COLETA'`) | `TabelaFreteManager.preparar_cotacao_fob()` | `0.00` (frete fantasma) |

`calcular_valor_frete_pela_tabela()` (`app/utils/calculadora_frete.py`, alias deprecated) e o helper "single value" usado no fluxo automatico — retorna `valor_total_cotado` final (soma componentes + ICMS).

`TabelaFreteManager.atribuir_campos_objeto(novo_frete, tabela_dados)` copia os 30+ campos de tabela (valor_kg, percentual_valor, percentual_gris, percentual_adv, etc.) para o `Frete` — congela a tabela no momento do lancamento.

**Filtros importantes**:
- `_is_nacom_item(item)` — exclui itens CarVia (modulo isolado, dominio diferente)
- `EmbarqueItem.status == 'ativo'` — descarta itens cancelados

### Caminho 2: Manual

`criar_novo_frete_por_nf(numero_nf, fatura_frete_id)` (`routes.py:611`) — usuario cria manualmente quando o automatico falhou (gates nao atendidos) ou para freteiros (sem embarque normal). Mesma estrutura de campos. POST grava `Frete` + atribui campos da tabela. O POST `processar_lancamento_frete` exige `@require_financeiro()` e respeita o **gate de CD** (chama `verificar_requisitos_para_lancamento_frete`): em embarque MISTO com saida parcial, bloqueia (flash + redirect) sem criar o frete; nos demais motivos de falha, segue o fluxo manual normal (a tela existe justamente para esses casos).

### Caminho 3: Cancelamento

`cancelar_frete_por_embarque(embarque_id, cnpj_cliente, usuario)` (`routes.py:4104`) — invocado por `app/embarques/routes.py` quando embarque cancelado. Marca todos `Frete.status = 'CANCELADO'` (nao deleta). Idempotente (filtra `status != 'CANCELADO'`).

---

## Lancamento de Freteiros (fluxo paralelo)

`Transportadora.freteiro = True` (autonomo) tem fluxo **distinto** do transportador regular: nao emite CTe, fechamento via Excel + fatura agrupada, lancamento Odoo via NFS/RECIBO.

### Diferencas chave

| Aspecto | Transportadora regular | Freteiro |
|---------|------------------------|----------|
| Documento fiscal | CTe (`ConhecimentoTransporte`) | NFS ou RECIBO |
| Vinculo Frete↔documento | `frete_cte_id` → CTe | Sem CTe; fatura agrupa diretamente |
| Despesas extras | `tipo_documento='CTE'` + `despesa_cte_id` | `tipo_documento='NFS'` ou `'RECIBO'` |
| Lancamento Odoo (despesa) | `/despesas/<id>/lancar_odoo` (16 etapas via DFe) | `/despesas/<id>/lancar_nfs_recibo` (`routes.py:5934`) — fluxo simplificado, sem DFe |
| Fechamento | Fatura criada por upload PDF/integracao | UI dedicada `/lancamento_freteiros` (`routes.py:5069`) lista pendencias por freteiro — Nacom E CarVia |
| Geracao da fatura | Operador ou automatica (XML CTe) | `POST /emitir_fatura_freteiro/<transportadora_id>` (`routes.py:5286`) — agrupa fretes/despesas Nacom + fretes CarVia (`carvia_selecionados`) + **Custos de Entrega CarVia** (`carvia_custos_selecionados`, 2026-06-26 — xerox DespesaExtra; `emitir_fatura_freteiro_carvia(custos_entrega=...)` vincula o CE à FT e soma no `valor_total`) |
| Excel de fechamento | — | `GET /faturas/exportar-fechamento-freteiros` — **4 abas**: **Detalhamento** (Nacom + CarVia na MESMA aba, coluna `Operação`=NACOM/OP.ASSAÍ/CARVIA; fretes + DespesaExtra Nacom + `CarviaCustoEntrega` via `todos_custos_entrega()`) + **Resumo Nacom** + **Resumo Carvia** (dados bancarios) + **Inconsistencias** (2026-06-26). CarVia só entra sem filtro de origem; falha CarVia NÃO é mais silenciosa (flash + redirect). Restrito a admin/financeiro/logistica. **Validacao de integridade (2026-06-26)**: só entram nas abas Detalhamento/Resumo as faturas onde `Σ itens == valor_total_fatura` (round 2; Nacom = `valor_cte or valor_cotado`+despesas, CarVia = `valor_considerado or valor_cotado`+custos não-cancelados). As inconsistentes (órfã fantasma / soma divergente — `valor_total` NÃO recalcula ao desvincular frete) vão p/ a aba **Inconsistencias** — ocultas do fechamento, rastreáveis. Testes: `test_export_fechamento_freteiros_carvia.py`, `test_export_fechamento_integridade.py` |
| Filtro analises | `incluir_transportadora=True/False` | `incluir_freteiro=True/False` (default ambos True). Ver `analise_dinamica` |

### Pontos de atencao

- **Frete em si segue mesma estrutura**: `lancar_frete_automatico` cria `Frete` para freteiro IGUAL ao transportador regular (mesma logica DIRETA/FRACIONADA). A diferenca aparece apenas no documento fiscal (sem CTe → sem `frete_cte_id`) e no fechamento.
- **Despesa extra de freteiro**: preferir `tipo_documento='NFS'` (com NF de servico — Odoo vincula via `partner_id`+`numero_documento`) sobre `'RECIBO'` (sem NF — cria DFe sintetica). Ambos suportados.
- **Pagamento**: fatura de freteiro nao tem `numero_fatura` de transportadora — usa numero sequencial proprio gerado em `emitir_fatura_freteiro`.
- **CarVia unificado (2026-06-12, decisao Rafael — IMP-2026-06-10-005)**: a MESMA tela exibe e EMITE os fretes CarVia do freteiro (embarque compartilhado: carga Nacom + motos CarVia; o freteiro alega o frete TOTAL). Leitura/escrita CarVia via LAZY import de `app/carvia/services/financeiro/lancamento_freteiro_service.py` (`listar_fretes_carvia_pendentes_freteiro` + `emitir_fatura_freteiro_carvia`) — direcao fretes->carvia permitida (R1/R2 CarVia). Lado CarVia grava nas tabelas do modulo (CarviaFrete APROVADO/FATURADO + CarviaSubcontrato `Sub-###` + CarviaFaturaTransportadora CONFERIDA); pagamento CarVia segue conciliacao (R11) — emissao NAO marca FT paga. **Re-rateio conjunto**: embarque COM CarVia selecionado re-rateia o Valor Considerado proporcional ao `valor_cotado` de cada frete (Nacom+CarVia, "diferenca ambas pagam"); SEM CarVia mantém o rateio legado por peso. MESMA transacao (rollback conjunto). Selecao 100% CarVia nao cria FaturaFrete Nacom vazia. **BUG corrigido (2026-06-24)**: os checkboxes-mestre "selecionar tudo" de embarque e de transportadora (`lancamento_freteiros.html`) ignoravam `carvia_selecionados` — quem fechava o freteiro pelo mestre emitia SÓ Nacom (CarVia ficava pendente). Os 2 listeners passam a marcar tambem `carvia_selecionados`. **Totalizadores + rateio peso 0 (2026-06-24)**: (a) a linha "Total" do embarque e o "Resumo Geral" passam a somar Nacom+CarVia (antes SÓ Nacom; JS `atualizarTotalizadoresEmbarque`/`atualizarTotalGeral` + `data-peso`/`data-valor-nf` no checkbox CarVia; static Jinja do Resumo Geral soma `dados.total_carvia`); (b) `CarviaFreteService._calcular_custo_rateio` (custo CarVia) dava o frete do caminhão INTEIRO (`proporcao=1.0`) a frete DIRETA com `peso_grupo=0` (NF sem motos reconhecidas / cubado 0) — corrigido p/ `proporcao = (peso_grupo or 1)/peso_embarque` — peso 0 usa **fallback de 1 kg** (fatia mínima, decisão Rafael 2026-06-25), nem 0 nem o frete inteiro. Correção de dados já gravados: `scripts/carvia/corrigir_rateio_peso_zero.py` (rodar no Render). Testes: `tests/carvia/test_lancamento_freteiro_service.py`, `tests/carvia/test_calculo_custo_rateio_diretra.py`, `tests/fretes/test_export_fechamento_freteiros_carvia.py`.
- **Custos de Entrega CarVia no Lançamento + frete-preso (2026-06-26, decisao Rafael)**: (a) **Custos de Entrega CarVia** (`CarviaCustoEntrega`, xerox DespesaExtra) agora aparecem no Lançamento Freteiros (`listar_custos_entrega_carvia_pendentes_freteiro`: PENDENTE + sem fatura + transportadora efetiva freteiro + frete com embarque) e são emitidos junto (`carvia_custos_selecionados` → `emitir_fatura_freteiro_carvia(custos_entrega=...)` vincula à FT + soma `valor_total`). (b) **Causa-raiz "frete preso"** (embarque 6075): excluir/desanexar a FaturaTransportadora soltava SÓ a FK do `CarviaFrete`, deixando-o FATURADO + `valor_cte` preenchido → invisível ao Lançamento. `CarviaFreteService.reverter_frete_ao_desfazer_fatura` (espelho `cancelar_cte` Nacom: freteiro→PENDENTE limpa valor_cte; demais→CONFERIDO) é chamado em `admin_service.excluir_fatura_transportadora` (+ bloqueio CONFERIDA, paridade Nacom, fecha gap A-7) e `desanexar_subcontrato_fatura_transportadora`. Backfill: `scripts/carvia/corrigir_fretes_orfaos_faturado.py --embarque 6075`. Testes: `tests/carvia/test_reverter_frete_fatura.py`, `tests/fretes/test_lancamento_freteiros_custos_carvia.py`.

---

## CalculadoraFrete — visualizacao vs lancamento

`app/utils/calculadora_frete.py` expoe DOIS niveis de calculo:

| Funcao | Retorna | Onde e usada em fretes |
|--------|---------|------------------------|
| `calcular_valor_frete_pela_tabela(tabela, peso, valor)` | `float` (valor total) | `routes.py:55,3766,3790` — fluxo AUTOMATICO de lancamento |
| `CalculadoraFrete.calcular_frete_unificado(peso, valor_mercadoria, tabela_dados, transportadora_optante, transportadora_config, cidade, codigo_ibge)` | `dict` com `valor_bruto`, `valor_com_icms`, `valor_liquido`, `icms_aplicado`, `detalhes` (11 Decimals) | `routes.py:1281,1777` — `_calcular_componentes_analise()` para tela de visualizacao + analise dimensional |

**`detalhes` retornados** (`routes.py:1292-1356`): `peso_para_calculo`, `frete_base`, `gris`, `adv`, `rca`, `pedagio`, `valor_tas`, `valor_despacho`, `valor_cte`, `componentes_antes_minimo`, `componentes_apos_minimo`, `frete_liquido_antes_minimo`. Permite quebrar a cotacao em 11 componentes para conferencia humana (vs CTe real).

**JSON sanitization OBRIGATORIA** ao salvar `detalhes` em campo JSONB (Decimals do quantize): usar `app.utils.json_helpers.sanitize_for_json` (regra global em `.claude/references/REGRAS_DEV_LOCAL.md` secao JSON SANITIZATION). Bug historico em CotacaoV2Service motivou a regra.

`_calcular_componentes_analise()` e funcao **privada** (underscore) mas e importada em `app/carvia/routes/frete_routes.py` — risco de breaking change ao renomear/alterar assinatura. Documentado em "Funcoes Exportadas" abaixo.

---

## Fluxo Lancamento Odoo (16 etapas)

> **DETALHE COMPLETO** (cada etapa, IDs fixos, `CNPJ_PARA_COMPANY`, campos por modelo Odoo, problemas conhecidos): `app/fretes/services/documentacao_odoo/LANCAMENTO_ODOO.md` (SOT). Patterns P1-P7: `app/odoo/CLAUDE.md`.

Service: `lancamento_odoo_service.py` (`lancar_frete_odoo`). Pipeline DFe → PO → Invoice com checkpoint/retomada (`continuar_de_etapa`). Pontos que NAO se inferem do codigo:
- **Etapa 6 = FIRE-AND-POLL**: `action_gerar_po_dfe` dispara (~90s); em timeout/`cannot marshal None` → polla `DFe.purchase_id` cada 10s ate 600s (R1 anti-detach + R7 lock).
- **Etapa 8 PULADA** (R3) e **Etapas 12/14 OPCIONAIS** (R4) — numeracao mantida para nao quebrar a auditoria (`LancamentoFreteOdooAuditoria`).
- **Etapa 16**: `db.session.remove()` + re-fetch (R2) → `status='LANCADO_ODOO'` + IDs Odoo.
- **Rollback**: `_rollback_frete_odoo()` zera os IDs Odoo so se `etapas_concluidas < 16`.
- **Despesa**: `LancamentoDespesaOdooService` herda do service (override so de auditoria + verificacao de existencia).

---

## Workers RQ

Fila: `'odoo_lancamento'` (via `app/portal/workers:enqueue_job`).

| Job | Timeout | Funcao |
|-----|---------|--------|
| `lancar_frete_job(frete_id, cte_chave, usuario, ip)` | 600s | 1 frete: instancia `LancamentoOdooService` |
| `lancar_despesa_job(despesa_id, cte_chave, usuario, ip)` | 600s | 1 despesa: instancia `LancamentoDespesaOdooService` |
| `lancar_lote_job(fatura_id, usuario, ip)` | 1800s | Todos os fretes+despesas de uma fatura em serie. Progresso no Redis: `lote_progresso:{fatura_id}` (TTL 3600s) |

**Job standalone** (`jobs/cte_cancelamento_outlook_job.py`): processa emails Outlook com XMLs de cancelamento de CTe. Acionado pelo scheduler em `sincronizacao_incremental_definitiva.py` (step 18).

---

## Funcoes Exportadas (consumidores externos)

`routes.py` expoe funcoes consumidas por outros modulos. **Mudanca em qualquer uma quebra fluxo cross-modulo**:

| Funcao | Consumidores |
|--------|--------------|
| `processar_lancamento_automatico_fretes` | `embarques/routes.py`, `faturamento/routes.py`, `odoo/services/faturamento_service.py`, `portaria/routes.py` (4 callers) |
| `validar_cnpj_embarque_faturamento` | `embarques/routes.py`, `faturamento/routes.py` (top-level import) |
| `cancelar_frete_por_embarque` | `embarques/routes.py` |
| `lancar_frete_automatico`, `verificar_requisitos_para_lancamento_frete` | `cotacao/routes.py` |
| `_calcular_componentes_analise` (privada!) | `carvia/routes/frete_routes.py` — **risco de breaking change**, funcao com underscore foi importada por outro modulo |

---

## Interdependencias

| Importa de | O que | Pattern |
|-----------|-------|---------|
| `app.odoo.utils.connection` | `get_odoo_connection` | Lazy nos services Odoo |
| `app.odoo.services.cte_service` | `CteService` | Lazy em `cte_routes.py` |
| `app.embarques.models` | `Embarque, EmbarqueItem` | Top-level em `routes.py` |
| `app.faturamento.models` | `RelatorioFaturamentoImportado, FaturamentoProduto` | Top-level em `routes.py`, `relatorio_analise_fretes_service.py` |
| `app.transportadoras.models` | `Transportadora, GrupoTransportadora` | Top-level. Usa `expandir_filtro_fk`, `expandir_grupo_autocomplete` |
| `app.tabelas.models` | `TabelaFrete` | Top-level em `routes.py` |
| `app.vinculos.models` | `CidadeAtendida` | Top-level |
| `app.devolucao.models` | `NFDevolucao, NFDevolucaoNFReferenciada` | Em `relatorio_analise_fretes_service.py` |
| `app.custeio.models` | `CustoFrete` | Em `relatorio_analise_fretes_service.py` (custo orcado por UF/incoterm) |
| `app.utils.calculadora_frete` | `CalculadoraFrete` | Top-level — recalcula valores |
| `app.utils.tabela_frete_manager` | `TabelaFreteManager` | Top-level |
| `app.portal.workers` | `enqueue_job, get_redis_connection` | Workers RQ |

| Exporta para | O que |
|-------------|-------|
| `app/__init__.py` | 4 blueprints |
| `app/embarques/`, `app/faturamento/`, `app/odoo/`, `app/portaria/`, `app/cotacao/` | Funcoes de routes.py (ver tabela acima) |
| `app/bi/services.py`, `app/bi/services_helpers.py` | `Frete, DespesaExtra, ContaCorrenteTransportadora` |
| `app/devolucao/services/frete_placeholder_service.py` | `Frete, DespesaExtra` |
| `app/recebimento/services/validacao_ibscbs_service.py` | `ConhecimentoTransporte` |
| `app/scheduler/sincronizacao_incremental_definitiva.py` | `CteCancelamentoOutlookJob` |

---

## Gotchas

### G1: `buscar_ctes_relacionados` carrega TUDO
`Frete.buscar_ctes_relacionados()` (`models.py:232-258`) carrega TODOS os CTes ativos do banco e filtra em Python via set intersection de NFs. Pode ser lento com volume alto. Otimizar: pre-filtrar por transportadora + janela de data.

### G2: `l10n_br_data_entrada` SEMPRE atualizado (mesmo retomada)
Correcao 2026-04-20 (`lancamento_odoo_service.py:1275`): em retomada, atualiza data de entrada para refletir dia real do lancamento. Nao-bloqueante (DFe pode estar concluido/bloqueado no Odoo).

### G3: `FreteLancado` e dead code
Tabela `fretes_lancados` + rota `/antigo/<id>` (linha 3421 em routes.py). Nao usar em codigo novo. Nao remover sem migration de cleanup.

### G4: Rotas `*_antigo` nao removidas
`/lancar_antigo`, `/simulador_antigo` em `routes.py`. Mantidas por compatibilidade historica. Nao estender.

### G5: FrotaDespesa.odoo_vendor_bill_id reservado mas nunca preenchido
Comentario no codigo: "Fase 2: integracao Odoo - colunas reservadas". Modulo frota tem schema preparado para integracao Odoo mas nunca implementada.

### G6: Commits explicitos antes Etapa 12 e 14
`db.session.commit()` antes de chamar Odoo libera conexao PostgreSQL. Se commit falhar, lancamento continua (warning apenas).

### G7: 7 docs em `services/documentacao_odoo/`
Sinal de alta complexidade historica do fluxo. Quando depurar, comecar por `STATUS_IMPLEMENTACAO.md` e `IMPLEMENTACAO_FINAL_COMPLETA.md`.

---

## Permissao e Menu

**Decorator principal**: `@require_financeiro()` (em `app.utils.auth_decorators:68`) — bloqueia perfil `vendedor`. Aplicado na maioria das rotas de edicao/lancamento/financas.

**Restricoes adicionais**:
- `/faturas/exportar-fechamento-freteiros`: `@require_profiles('administrador', 'gerente_financeiro', 'financeiro', 'logistica')`

**Menu** (`app/templates/base.html:478-533`): secao "Fretes" condicionada a `current_user.tem_permissao('fretes')` OR `current_user.pode_acessar_financeiro()`. Items: Dashboard, Listar, Lancar CTe, Aprovacoes, Faturas, Analise, Pendencias Cancelamento CTe.

---

## Skills Relacionadas

| Skill / Subagente | Como interage |
|---|---|
| `controlador-custo-frete` (subagente) | Query SQL direta em `fretes`, `despesas_extras`, `conta_corrente_transportadoras`, `conhecimento_transporte` via `consultando-sql`. NAO importa codigo Python |
| `cotando-frete` (skill) | Script `consultando_frete_real.py` faz query SQL em `fretes`, `embarques`, `separacoes` (4 valores de frete). Sem import Python |
| `monitorando-entregas` (skill) | Query SQL em `fretes`, `embarques` para status pos-faturamento |
| `integracao-odoo` (skill) | **Documenta** o processo de 16 etapas. Dev guide para criar/modificar services de lancamento Odoo |
| `analista-performance-logistica` (subagente) | Referencia `FRETE_REAL_VS_TEORICO.md`, usa SQL nas tabelas |

---

## Referencias

> Este CLAUDE.md cobre estrutura, regras e gotchas. O detalhe profundo vive nos docs abaixo — preferir LER o doc a reconstruir do codigo.

### Docs internos do modulo

| Doc | Cobre |
|-----|-------|
| `app/fretes/services/documentacao_odoo/LANCAMENTO_ODOO.md` | **SOT** do lancamento Odoo: 16 etapas, IDs fixos, `CNPJ_PARA_COMPANY`, campos por modelo, problemas conhecidos |
| `app/fretes/DOCUMENTACAO_PROCESSO_LANCAMENTO_FRETE.md` | Visao sistemica do processo de frete (modelos, validacoes, fatura, CTe, fluxo de vida) |
| `app/fretes/README_ANALISES.md` | Sub-modulo de Analises (`analises_service`, API `/analises`, dimensoes transportadora/freteiro) |
| `app/fretes/services/documentacao_odoo/GUIA_VISUAL_INTERFACES_LANCAMENTO.md` | Wireframes das telas de lancamento (UI) |
| `app/fretes/services/documentacao_odoo/PROPOSTA_SUGESTAO_CTE.md` | Proposta (NAO implementada) de sugestao automatica de CTe |
| `app/fretes/devolucao.md` | Despesas extras de devolucao + `FretePlaceholderService` (frete fantasma pre-julho/2024) |

> Os demais `.md` de `documentacao_odoo/` (IMPLEMENTACAO_*, STATUS_*, RESUMO_*, `lancamento.md`, `DOCUMENTACAO_LANCAMENTO_FRETE_ODOO.md`) sao **stubs historicos** (14/11/2025) superados pelo SOT acima.

### Cross-modulo

| Preciso de... | Documento |
|---------------|-----------|
| Patterns Odoo P1-P7 / IDs por empresa / gotchas / modelos | `app/odoo/CLAUDE.md` + `.claude/references/odoo/{IDS_FIXOS,GOTCHAS,MODELOS_CAMPOS}.md` |
| Frete real vs teorico / margem / regras de negocio | `.claude/references/negocio/{FRETE_REAL_VS_TEORICO,MARGEM_CUSTEIO,REGRAS_NEGOCIO}.md` |
| Pagamento de fretes no Odoo / reconciliacao multi-company | `app/financeiro/CLAUDE.md` + `app/financeiro/{FLUXOS_RECONCILIACAO,GOTCHAS}.md` |
| Cadeia Pedido → Embarque → Frete → CTe → Pagamento | `.claude/references/modelos/CADEIA_PEDIDO_ENTREGA.md` |
| JSON sanitization / padroes de backend | `.claude/references/PADROES_BACKEND.md` + `.claude/references/REGRAS_DEV_LOCAL.md` |
| Campos das tabelas do modulo | `.claude/skills/consultando-sql/schemas/tables/{fretes,faturas_frete,despesas_extras,conhecimento_transporte}.json` |
