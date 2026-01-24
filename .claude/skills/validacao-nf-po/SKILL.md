---
name: validacao-nf-po
description: |
  Executa e depura o processo de Validacao NF x PO (Fase 2 do Recebimento de Materiais).

  USAR QUANDO:
  - Depurar erro na validacao NF x PO: "erro ao validar DFE", "DFE nao encontrado"
  - Modificar logica de match: "alterar tolerancia", "mudar regra de preco"
  - Corrigir preview de POs candidatos: "modal nao abre", "erro no modal POs"
  - Entender fluxo de conversao De-Para: "como converte UM", "fator conversao"
  - Implementar nova regra de divergencia: "novo tipo de bloqueio"
  - Entender tabelas locais: "o que tem em MatchNfPoItem", "campos da validacao"

  NAO USAR QUANDO:
  - Rastrear documentos no Odoo -> usar rastreando-odoo
  - Descobrir campos de modelo Odoo desconhecido -> usar descobrindo-odoo-estrutura
  - Criar pagamentos ou reconciliar extratos -> usar executando-odoo-financeiro
  - Criar CTe ou despesas -> usar integracao-odoo
  - Depurar recebimento fisico (Fase 4) -> usar recebimento-fisico
  - Conciliar POs (split/consolidacao) -> usar conciliando-odoo-po
---

# Validacao NF x PO - Processo Completo

## Visao Geral

O processo de Validacao NF x PO compara itens de uma NF-e (DFE no Odoo) contra Pedidos de Compra (POs) do mesmo fornecedor, verificando preco, quantidade e data.

## Arquivo Principal

```
app/recebimento/services/validacao_nf_po_service.py
```

## Modelos/Tabelas Envolvidos

| Tabela Local | Modelo | Proposito |
|---|---|---|
| `validacao_nf_po_dfe` | ValidacaoNfPoDfe | Cabecalho da validacao (status, contadores) |
| `match_nf_po_item` | MatchNfPoItem | Resultado match item-a-item (NF vs PO) |
| `match_nf_po_alocacao` | MatchAlocacao | Alocacao split (1 item NF → N linhas PO) |
| `divergencia_nf_po` | DivergenciaNfPo | Divergencias para resolucao manual |
| `produto_fornecedor_depara` | ProdutoFornecedorDepara | Conversao codigo/UM fornecedor → interno |
| `pedido_compras` | PedidoCompras | POs locais (sincronizados do Odoo) |

| Modelo Odoo | Uso |
|---|---|
| `l10n_br_ciel_it_account.dfe` | NF-e eletronica (cabecalho) |
| `l10n_br_ciel_it_account.dfe.line` | Linhas/itens da NF-e |

## Fluxo Principal

```
┌─────────────────────────────────────────────────────────────┐
│                    validar_dfe(odoo_dfe_id)                  │
│                                                             │
│  1. Buscar DFE no Odoo (_buscar_dfe)                        │
│  2. Verificar se DFE ja tem PO vinculado                    │
│     └─ SIM → status='finalizado_odoo', retorna             │
│  3. Buscar linhas DFE no Odoo (_buscar_dfe_lines)           │
│  4. Converter itens com De-Para BATCH                       │
│     ├─ itens_convertidos (tem cod_produto_interno)          │
│     └─ itens_sem_depara (bloqueio imediato)                 │
│  5. Buscar POs LOCAL (_buscar_pos_fornecedor_local)         │
│  6. Para cada produto: match com split                      │
│     ├─ Filtrar POs por preco (0%) e data (±dias uteis)      │
│     ├─ Alocar qtd_nf nos POs (por data ASC)                │
│     └─ Registrar MatchNfPoItem + MatchAlocacao              │
│  7. Se 100% match → status='aprovado'                       │
│     Se <100% → status='bloqueado' + divergencias            │
└─────────────────────────────────────────────────────────────┘
```

## Constantes de Tolerancia

```python
TOLERANCIA_QTD_PERCENTUAL = Decimal('10.0')       # Qtd NF pode ser ate 10% MAIOR que PO
TOLERANCIA_PRECO_PERCENTUAL = Decimal('0.0')      # Preco deve ser EXATO (0% tolerancia)
TOLERANCIA_DATA_ANTECIPADO_DIAS = 5               # NF pode chegar 5 dias CORRIDOS ANTES
TOLERANCIA_DATA_ATRASADO_DIAS = 15                # NF pode chegar 15 dias CORRIDOS DEPOIS
```

## REGRA CRITICA: Preview vs Validacao

| Operacao | Fonte de Dados | Chama Odoo? |
|---|---|---|
| `validar_dfe()` | Odoo + Local | SIM (leitura DFE/linhas) |
| `buscar_preview_pos_candidatos()` | 100% LOCAL | **NUNCA** |

O **preview** (modal POs Candidatos) usa EXCLUSIVAMENTE dados locais:
- `ValidacaoNfPoDfe` para cabecalho
- `MatchNfPoItem` para itens (ja convertidos)
- `PedidoCompras` para POs candidatos

## Tipos de Divergencia

| Tipo | Causa | Resolucao |
|---|---|---|
| `sem_depara` | Codigo fornecedor sem cadastro | Criar De-Para |
| `sem_po` | Nenhum PO com saldo para o produto | Ajustar PO ou aprovar |
| `preco_diverge` | Preco NF != Preco PO (0% tolerancia) | Aprovar ou corrigir PO |
| `data_diverge` | Data NF fora da janela ±dias uteis | Aprovar |
| `qtd_diverge` | Qtd NF > saldo PO + 10% | Ajustar PO |
| `saldo_insuficiente` | Mesmo com split, saldo total < qtd NF | Criar PO complementar |

## Job de Validacao (Scheduler)

**Arquivo**: `app/recebimento/jobs/validacao_recebimento_job.py`
**Scheduler**: Cada 30 minutos (automatico)
**Execucao Manual**: Botao "Executar Validacao" na tela NF×PO (com modal De/Ate)

### Fluxo do Job (4 Etapas):

```
[1/4] Sync De-Para (Odoo -> Sistema)
      |-- Importa product.supplierinfo com product_code
      +-- Limite: 200 registros/execucao

[2/4] Sync POs Vinculados (SEM limite de data)
      |-- Busca TODAS as ValidacaoNfPoDfe sem PO (sem janela temporal)
      |-- Verifica 3 caminhos no Odoo:
      |   |-- Caminho 1: DFE.purchase_id
      |   |-- Caminho 2: DFE.purchase_fiscal_id
      |   +-- Caminho 3: PO.dfe_id -> DFE (inverso, BATCH)
      +-- Atualiza ValidacaoNfPoDfe com PO encontrado

[3/4] Buscar DFEs Pendentes (COM janela temporal)
      |-- Filtro Odoo: tipo=compra, status=04, write_date >= janela
      |-- Exclui: devolucoes, CTes, CNPJs do grupo (Nacom/Goya)
      |-- Limite: 100 DFEs por execucao
      +-- Filtra: ja processados em Fase 1 E Fase 2

[4/4] Processar DFEs (Fase 1 + Fase 2)
      |-- Fase 1: Validacao Fiscal (ValidacaoFiscalService)
      +-- Fase 2: Validacao NF x PO (ValidacaoNfPoService)
```

### Diferenca Critica entre Etapas 2 e 3:

| Aspecto | _sync_pos_vinculados | _buscar_dfes_pendentes |
|---------|---------------------|----------------------|
| Janela temporal | **NENHUMA** (todos) | `minutos_janela` (default 48h) |
| O que busca | ValidacaoNfPoDfe sem PO | DFEs no Odoo (compra, status=04) |
| Afetado pelo modal De/Ate | NAO | SIM |
| Proposito | Vincular POs que apareceram depois | Processar novos DFEs |

## Vinculacao DFE <-> PO (3 Caminhos)

**Arquivo**: `validacao_recebimento_job.py:206-345` (`_sync_pos_vinculados()`)

O Odoo possui 3 formas de vincular um DFE (NF-e) a um PO:

| # | Campo | Modelo | Direcao | Estatistica |
|---|-------|--------|---------|-------------|
| 1 | `purchase_id` | DFE -> PO | many2one direto | 14.6% (EXCEPCIONAL) |
| 2 | `purchase_fiscal_id` | DFE -> PO | many2one escrituracao | 75% dos status=06 |
| 3 | `PO.dfe_id` | PO -> DFE | many2one inverso | 85.4% dos status=04 (**PRINCIPAL**) |

### Prioridade de Consulta:

```python
# 2 queries no Odoo (batch):
# Query 1: search_read('l10n_br_ciel_it_account.dfe', [['id','in',dfe_ids]], ['purchase_id','purchase_fiscal_id'])
# Query 2: search_read('purchase.order', [['dfe_id','in',dfe_ids]], ['id','name','dfe_id'])

for validacao in validacoes_sem_po:
    # Caminho 1: DFE.purchase_id (14.6%)
    if dfe_data.get('purchase_id'):
        validacao.odoo_po_vinculado_id = purchase_id_data[0]

    # Caminho 2: DFE.purchase_fiscal_id (status=06)
    elif dfe_data.get('purchase_fiscal_id'):
        validacao.odoo_po_fiscal_id = purchase_fiscal_data[0]

    # Caminho 3: PO.dfe_id (85.4% dos status=04 - PRINCIPAL)
    elif pos_por_dfe.get(validacao.odoo_dfe_id):
        validacao.odoo_po_vinculado_id = po_inverso['id']
```

### Por que o Caminho 3 e o principal?

No workflow Odoo do recebimento de compras:
1. DFE chega (status=04 = "PO vinculado")
2. Operador vincula PO ao DFE — isso preenche `PO.dfe_id`, **NAO** `DFE.purchase_id`
3. `DFE.purchase_id` so e preenchido em casos excepcionais (importacao direta)
4. `DFE.purchase_fiscal_id` e preenchido na escrituracao (status=06)

**Resultado**: Para DFEs em status=04, o unico caminho confiavel e `PO.dfe_id` (85.4%).

## Status DFE no Odoo (l10n_br_status)

| Codigo | Nome | Significado | Relevancia para Validacao |
|--------|------|-------------|--------------------------|
| `01` | Rascunho | DFE recem-importado | Nao processar |
| `02` | Sincronizado | Sincronizado com SEFAZ | Nao processar |
| `03` | Ciencia | Ciencia da operacao confirmada | Nao processar |
| `04` | PO Vinculado | PO foi vinculado ao DFE | **ALVO DA VALIDACAO** |
| `05` | Rateio | Em processo de rateio | Nao processar |
| `06` | Concluido | Processo finalizado | Ja processado (purchase_fiscal_id preenchido) |
| `07` | Rejeitado | DFE rejeitado | Ignorar |

**Filtro do Job**: `['l10n_br_status', '=', '04']` — Apenas DFEs com PO vinculado.

## Execucao Manual (Modal De/Ate)

**Tela**: Validacoes NF x PO (`/api/recebimento/validacoes-nf-po`)
**Botao**: "Executar Validacao" (abre modal com selecao de periodo)
**Rota**: `POST /api/recebimento/executar-validacao`

### Modal:
- Campo "De" (date) — padrao: 7 dias atras
- Campo "Ate" (date) — padrao: hoje
- Periodo maximo: 90 dias
- Limite: 100 DFEs por execucao

### Logica de Conversao (rota, `validacao_nf_po_routes.py:1397`):
```python
# Converte datas absolutas para minutos_janela
dt_de = datetime.strptime(data_de, '%Y-%m-%d')
agora = datetime.utcnow()
minutos_janela = int((agora - dt_de).total_seconds() / 60)
# Usa minutos_janela no job (afeta APENAS etapa 3)
```

### O que o botao NAO afeta:
- `_sync_pos_vinculados()` (etapa 2) — sempre busca TODOS sem PO, sem janela
- `_sync_depara_odoo()` (etapa 1) — sempre importa De-Para

### O que o botao AFETA:
- `_buscar_dfes_pendentes()` (etapa 3) — usa minutos_janela para filtrar write_date

## Referencias

- [Fluxo Completo](references/fluxo-validacao-nf-po.md) - Etapas detalhadas com codigo
- [Erros Comuns](references/erros-comuns.md) - Armadilhas e solucoes

## Skills Relacionadas

- `rastreando-odoo` - Para CONSULTAR documentos (nao executar)
- `descobrindo-odoo-estrutura` - Para explorar campos Odoo desconhecidos
- `executando-odoo-financeiro` - Para operacoes financeiras (pagamentos, reconciliacao)
- `conciliando-odoo-po` - Para split/consolidacao de POs (Fase 3)
- `recebimento-fisico` - Para recebimento fisico (Fase 4)
