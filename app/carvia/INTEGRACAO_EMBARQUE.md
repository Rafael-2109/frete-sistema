# CarVia — Integracao com Embarques

**Documento mestre** para a integracao CarVia x lista_pedidos x Embarque x Impressao.
**Ultima atualizacao**: 21/03/2026
**Plano tecnico**: `~/.claude/plans/encapsulated-kindling-hopper.md`
**Fluxograma**: `app/carvia/fluxograma_refatoracao.md`
**Requisitos originais**: `app/carvia/refatoracao.md`

---

## Indice

1. [Visao Geral do Processo](#1-visao-geral)
2. [Decisoes de Design](#2-decisoes)
3. [Conceito: Item Provisorio com Saldo Parcial](#3-provisorio)
4. [Arquivos Modificados — Detalhes](#4-arquivos)
5. [Regras de Identificacao](#5-identificacao)
6. [Fluxo E2E Detalhado](#6-fluxo)
7. [Progresso de Implementacao](#7-progresso)
8. [Perguntas Respondidas pelo Usuario](#8-perguntas)

---

## 1. Visao Geral

### O problema

CarVia cotacoes aparecem em `lista_pedidos.html` (via VIEW UNION) mas NAO conseguem
entrar no sistema de embarques. Motivo: o fluxo existente espera dados de `Separacao`,
que nao existem para itens CarVia.

### A solucao

Item **provisorio** no embarque. A cotacao CarVia entra como placeholder que e
gradualmente substituido por pedidos/NFs reais conforme chegam.

```
Cotacao APROVADA → lista_pedidos → Embarque (provisorio)
  → Jessica cria pedidos → Jessica anexa NFs
  → Provisorio substituido por itens reais
  → Embarque completo → Portaria → CarviaFreteService (orquestrador)
```

### Regra de ouro — Tabelas

```
TABELA CARVIA (preco VENDA ao cliente)     TABELA NACOM (preco CUSTO transporte)
CarViaTabelaService.cotar_carvia()         CotacaoService.cotar_subcontrato()
  → CarviaCotacao.valor_final_aprovado       → CarviaSubcontrato.valor_cotado
  → CarviaFaturaCliente (A RECEBER)          → CarviaFaturaTransportadora (A PAGAR)
```

O frete cotado pela Elaine (automatico ou manual) = **CUSTO** (tabela Nacom).
A transportadora selecionada = transportadora **subcontratada**.

---

## 2. Decisoes de Design

### Respondidas pelo usuario (21/03/2026)

| # | Decisao | Resposta |
|---|---------|----------|
| D1 | Caminho de integracao | A — unificado na lista_pedidos |
| D2 | Elaine roteiriza com... | So a cotacao (sem itens detalhados) |
| D3 | Separacao motos quando? | DEPOIS do embarque ser criado |
| D4 | Rota/sub_rota para CarVia | CALCULADOS via `cadastro_rota`/`cadastro_sub_rota` (UF+cidade destino) |
| D5 | Identificacao CarVia | Pelo prefixo `separacao_lote_id` (CARVIA- ou CARVIA-PED-) |
| D6 | Saldo parcial | Cotacao substituida GRADUALMENTE (pedidos/NFs chegam em momentos diferentes) |
| D7 | Layout embarque | Itens CarVia em secao separada abaixo dos Nacom |
| D8 | Embarque mix | Pode ter Nacom + CarVia ou so CarVia |
| D9 | Cotacao frete = custo | Tanto automatica quanto manual geram CarviaSubcontrato |
| D10 | Transportadora selecionada | = subcontratada (custo) |
| D11 | Dados custo DIRETA | Gravados no **Embarque** (nivel container) |
| D12 | Dados custo FRACIONADA | Gravados no **EmbarqueItem** (nivel item) |
| D13 | Portaria com provisorios | ALERTA (nao bloqueia) |
| D14 | Cotacao cancelada | Remove provisorio do embarque |
| D15 | 1 cotacao pode gerar | Pedidos SP + RJ simultaneamente |

### Decisoes tecnicas

| # | Decisao | Motivo |
|---|---------|--------|
| T1 | NAO sobrescrever rota com 'CARVIA' | Elaine usa rota para roteirizar por regiao |
| T2 | Deteccao por prefixo (nao rota) | `Pedido.eh_carvia` = `separacao_lote_id.startswith('CARVIA-')` |
| T3 | Cotacao Nacom so se ha itens Nacom | Se so CarVia → `Embarque.cotacao_id = NULL` |
| T4 | `Separacao.atualizar_cotacao()` skip CARVIA- | CarVia nao tem registros em Separacao |
| T5 | EmbarqueItem.provisorio BOOLEAN | Flag simples para distinguir placeholder de real |
| T6 | EmbarqueItem.carvia_cotacao_id | Rastreabilidade: qual cotacao originou o provisorio |

---

## 3. Conceito: Item Provisorio com Saldo Parcial

### Ciclo de vida

```
ESTADO 1 — Cotacao sem pedidos:
  lista_pedidos: [CARVIA-42 (cotacao inteira)]
  embarque:      [EmbarqueItem provisorio, peso=500kg, valor=R$5000]

ESTADO 2 — Cotacao com 1 pedido (sem NF):
  lista_pedidos: [CARVIA-42 (saldo)] + [CARVIA-PED-7 (pedido SP)]
  embarque:      [EmbarqueItem provisorio] (inalterado, aguardando NF)

ESTADO 3 — Pedido SP com NF, pedido RJ sem NF:
  lista_pedidos: [CARVIA-42 (saldo)] + [CARVIA-PED-7] + [CARVIA-PED-8]
  embarque:      [EmbarqueItem provisorio (saldo)] + [EmbarqueItem real (PED-7 c/ NF)]

ESTADO 4 — Todos pedidos com NF (cotacao 100% resolvida):
  lista_pedidos: [CARVIA-PED-7] + [CARVIA-PED-8] (cotacao desapareceu)
  embarque:      [EmbarqueItem real (PED-7)] + [EmbarqueItem real (PED-8)]
                 Provisorio REMOVIDO → Embarque COMPLETO
```

### Regra de desaparecimento da cotacao na VIEW

A cotacao (Parte 2A da VIEW) desaparece quando:
- TEM pelo menos 1 pedido nao-cancelado
- E TODOS pedidos nao-cancelados tem TODOS itens com `numero_nf` preenchido

Enquanto houver ao menos 1 pedido com item sem NF → cotacao permanece como saldo.

---

## 4. Arquivos Modificados — Detalhes

### P1.1 — EmbarqueItem model

**Arquivo**: `app/embarques/models.py`
**Mudanca**: 2 campos adicionados

```python
provisorio = db.Column(db.Boolean, nullable=False, default=False, server_default='false')
carvia_cotacao_id = db.Column(db.Integer, nullable=True, index=True)
```

**Migration**: `scripts/migrations/adicionar_provisorio_embarque_item.py` + `.sql`
- 2 indices parciais: `WHERE provisorio = TRUE` e `WHERE carvia_cotacao_id IS NOT NULL`

### P1.2 — VIEW pedidos (3 partes)

**Arquivo**: `scripts/migrations/alterar_view_pedidos_union_carvia.sql` (v4)

| Parte | Fonte | separacao_lote_id | rota/sub_rota |
|-------|-------|-------------------|---------------|
| 1 | `separacao` (Nacom) | LOTE-* | Da tabela separacao |
| 2A | `carvia_cotacoes` (saldo) | CARVIA-{id} | Via JOIN `cadastro_rota`/`cadastro_sub_rota` |
| 2B | `carvia_pedidos` (individual) | CARVIA-PED-{id} | Via JOIN `cadastro_rota`/`cadastro_sub_rota` |

**JOINs de rota** (partes 2A e 2B):
```sql
LEFT JOIN cadastro_rota cr ON cr.cod_uf = dest.fisico_uf AND cr.ativa = TRUE
LEFT JOIN cadastro_sub_rota csr ON csr.cod_uf = dest.fisico_uf
    AND UPPER(dest.fisico_cidade) LIKE '%' || UPPER(csr.nome_cidade) || '%'
    AND csr.ativa = TRUE
```

### P1.3 — Pedido model + template

**Arquivo**: `app/pedidos/models.py`
- `eh_carvia` (property): detecta por prefixo `CARVIA-`
- `status_calculado`: branch CarVia antes do branch Nacom

**Arquivo**: `app/templates/pedidos/lista_pedidos.html`
- Checkbox aceita status 'CARVIA'
- Badge discreto "CarVia" + tipo (Cotacao/Pedido)
- Coluna rota: mostra rota calculada (sem hardcode 'CARVIA')

### P2.1 — Rotas de criacao de embarque

**Arquivo**: `app/pedidos/routes.py` (processar_cotacao_manual, L1692-1865)

Mudancas:
1. Separacao `pedidos_nacom` / `pedidos_carvia` por prefixo
2. Cotacao Nacom criada SOMENTE se ha itens Nacom (`cotacao = None` se so CarVia)
3. CotacaoItem criado apenas para Nacom
4. EmbarqueItem: branch Nacom (fluxo existente) vs CarVia (provisorio=True)
5. `Embarque.cotacao_id = cotacao.id if cotacao else None`
6. `Separacao.atualizar_cotacao()` skip CARVIA-*

**Arquivo**: `app/cotacao/routes.py` (fechar_frete, L1006-1628)

Mudancas:
1. Loop `Separacao.atualizar_cotacao` (L1450): skip `CARVIA-*`
2. Loop EmbarqueItem (L1518): branch `eh_carvia` com provisorio
3. Loop sync pos-commit (L1578): skip `CARVIA-*` (2 instancias: criacao + alteracao)

**Ponto de atencao**: `fechar_frete` tem 2 paths (criacao L1432+ e alteracao L1288+).
A alteracao NAO foi modificada para CarVia — sera tratada em fase futura se necessario.

### P2.2 — EmbarqueCarViaService

**Arquivo**: `app/carvia/services/embarque_carvia_service.py` (NOVO)

| Metodo | Funcao | Chamado por |
|--------|--------|-------------|
| `expandir_provisorio(cotacao_id, pedido_id, nf)` | Cria EmbarqueItem real + verifica se remove provisorio | `pedido_routes.api_anexar_nf_pedido` |
| `verificar_embarque_completo(embarque_id)` | Retorna {completo, provisorios, total} | Templates de alerta |
| `obter_embarques_com_provisorios()` | Lista embarques com provisorios pendentes | Dashboard alertas |
| `remover_provisorio_cotacao(cotacao_id)` | Remove provisorio + reais quando cotacao cancelada | `CotacaoV2Service.cancelar()` |

**Logica de expansao**:
1. Busca EmbarqueItem provisorio pela `carvia_cotacao_id`
2. Verifica dedup (ja existe item real para esse pedido?)
3. Cria EmbarqueItem real com `provisorio=False`, `nota_fiscal=NF`
4. Copia dados de tabela do provisorio (FRACIONADA) se existirem
5. `_cotacao_totalmente_resolvida()` → se TODOS pedidos tem NF → remove provisorio
6. `_recalcular_totais()` → atualiza peso/valor/pallet do Embarque

### P5.1 — Endpoint anexar NF

**Arquivo**: `app/carvia/routes/pedido_routes.py`
**Rota**: `PUT /carvia/api/pedidos-carvia/<id>/nf`
**Body**: `{ "numero_nf": "123456" }`

Fluxo:
1. Preenche `CarviaPedidoItem.numero_nf` em todos itens do pedido
2. Atualiza `CarviaPedido.status` → FATURADO (se era PENDENTE/SEPARADO)
3. Chama `EmbarqueCarViaService.expandir_provisorio()` (nao-bloqueante)
4. Retorna JSON com resultado da expansao

### P5.3 — Cancelamento limpa embarque

**Arquivo**: `app/carvia/services/cotacao_v2_service.py` (metodo `cancelar`)

Adicionado:
- Chama `EmbarqueCarViaService.remover_provisorio_cotacao(cotacao_id)` antes de cancelar
- Remove provisorio + itens reais ja expandidos
- Recalcula totais do embarque
- Nao-bloqueante (try/except)

---

## 5. Regras de Identificacao

| Prefixo separacao_lote_id | Tipo | Origem | Provisorio? |
|---------------------------|------|--------|-------------|
| `LOTE-*` | Nacom | CarteiraPrincipal → Separacao | Nao |
| `CARVIA-{id}` | CarVia cotacao | CarViaCotacao APROVADA | Sim |
| `CARVIA-PED-{id}` | CarVia pedido | CarViaPedido | Sim (ate ter NF) |

**Deteccao no codigo**:
- Python: `Pedido.eh_carvia` ou `lote_id.startswith('CARVIA-')`
- SQL: `separacao_lote_id LIKE 'CARVIA-%'`
- Template: `{% if p.eh_carvia %}`

**Extracao de IDs**:
- `CARVIA-42` → `carvia_cotacao_id = 42`
- `CARVIA-PED-7` → busca `CarviaPedido(id=7).cotacao_id`

---

## 6. Fluxo E2E Detalhado

```
[1] Jessica cria CarViaCotacao (COT-042)
    → CotacaoV2Service.criar_cotacao()
    → CotacaoV2Service.calcular_preco() (tabela CarVia = VENDA)
    → CotacaoV2Service.registrar_aprovacao_cliente() → status=APROVADO

[2] VIEW pedidos exibe COT-042 em lista_pedidos
    → separacao_lote_id = 'CARVIA-42'
    → rota/sub_rota calculados via cadastro_rota (UF destino)
    → status_calculado = 'CARVIA'

[3] Elaine seleciona [LOTE-001, CARVIA-42] e clica Cotar Frete
    → fechar_frete() ou processar_cotacao_manual()
    → LOTE-001: Cotacao Nacom + EmbarqueItem normal
    → CARVIA-42: EmbarqueItem(provisorio=True, carvia_cotacao_id=42)
    → Embarque criado com 2 itens

[4] Jessica cria CarviaPedido(s) SP e RJ
    → api_criar_pedido() → PED-CV-007 (SP) + PED-CV-008 (RJ)
    → VIEW: CARVIA-42 (saldo) + CARVIA-PED-7 + CARVIA-PED-8

[5] Jessica anexa NF ao pedido SP
    → PUT /carvia/api/pedidos-carvia/7/nf
    → EmbarqueItem real criado para PED-CV-007
    → Provisorio permanece (RJ pendente)

[6] Jessica anexa NF ao pedido RJ
    → PUT /carvia/api/pedidos-carvia/8/nf
    → EmbarqueItem real criado para PED-CV-008
    → Provisorio REMOVIDO (cotacao 100% resolvida)
    → Embarque COMPLETO

[7] Portaria: registrar saida
    → Se provisorios: ALERTA (nao bloqueia)
    → CarviaFreteService.lancar_frete_carvia() (orquestrador unico)
    → CarviaOperacao + CarviaSubcontrato + CarviaFrete criados atomicamente

[8] Conferencia + Faturamento + Conciliacao
    → ConferenciaService (tabela Nacom)
    → CarviaFaturaCliente (venda) + CarviaFaturaTransportadora (custo)
    → Conciliacao extrato → quitacao automatica
```

---

## 7. Progresso de Implementacao

| Fase | Descricao | Status | Data |
|------|-----------|--------|------|
| P1.1 | EmbarqueItem: campos provisorio + carvia_cotacao_id | FEITO | 21/03 |
| P1.2 | VIEW pedidos: 3 partes + rota/sub_rota via JOIN | FEITO | 21/03 |
| P1.3 | Pedido.eh_carvia + status_calculado + template | FEITO | 21/03 |
| P2.1 | processar_cotacao_manual + fechar_frete: provisorio | FEITO | 21/03 |
| P2.2 | EmbarqueCarViaService (expandir, verificar, remover) | FEITO | 21/03 |
| P2.3 | Triggers de expansao (criar pedido, anexar NF) | FEITO (via P5.1) | 21/03 |
| P2.4a | Frete CarVia: model CarviaFrete + migration + FKs | FEITO | 21/03 |
| P2.4b | Frete CarVia: CarviaFreteService + 2 gatilhos (portaria + NF) | FEITO | 21/03 |
| G2 | fechar_frete path alteracao: skip CARVIA-* | FEITO | 21/03 |
| G3 | fechar_frete_grupo + incluir_em_embarque: skip CARVIA-* | FEITO | 21/03 |
| G4 | imprimir_completo: paginas CarVia + watermark PROVISORIO | FEITO | 21/03 |
| G5 | UI Jessica: botao Anexar NF + feedback visual + atalho cotacao | FEITO | 21/03 |
| G7 | Flag impresso com auditoria (Embarque.impresso_em/por/alterado) | FEITO | 21/03 |
| P3.1 | Tela embarque: alerta + badge provisorio na tabela | FEITO | 21/03 |
| P3.2 | Impressao embarque: secao Nacom + secao CarVia separadas | FEITO | 21/03 |
| P3.3 | Portaria: alerta provisorios na saida (nao bloqueia) | FEITO | 21/03 |
| P4.1+2 | Template impressao separacao CarVia (provisorio + pedido unificado) | FEITO | 21/03 |
| P4.3 | Rota impressao + funcao _imprimir_separacao_carvia() | FEITO | 21/03 |
| P5.1 | Endpoint anexar NF + trigger expansao | FEITO | 21/03 |
| P5.2 | Hook ao criar pedido (VIEW dinamica, nao precisa hook) | N/A | — |
| P5.3 | Cancelamento cotacao (limpar embarque) | FEITO | 21/03 |

### Sessoes anteriores (ja concluidas)

| Item | Descricao | Status |
|------|-----------|--------|
| BUG-1 | SubcontratoAutoService: cadeia CarviaOperacao→Sub | FEITO |
| BUG-2 | categoria_moto_id=0 → validacao NOT NULL | FEITO |
| BUG-3 | Conciliacao quita titulo (5 tipos + reversao) | FEITO |
| BUG-4 | Tabelas corretas: VENDA=CarVia, CUSTO=Nacom | FEITO |
| BUG-5 | Quick nav labels: Comercial + Rotas | FEITO |

---

## 8. Gaps Pendentes — Analise Detalhada

### P2.4 — Frete CarVia (CORE — maior item pendente)

**O que e**: Um registro de "Frete" no modulo CarVia que funciona como o Frete Nacom
(`app/fretes/models.py`) mas com 2 lados (CUSTO + VENDA) e agregacao por CNPJ emitente+destino.

**Referencia Nacom**: `Frete` (tabela `fretes`) — 1 frete = 1 CNPJ + 1 Embarque, com N NFs.
- FK: embarque_id, transportadora_id
- FK opcional: fatura_frete_id (fatura), frete_cte_id (CTe)
- 4 valores: cotado, cte, considerado, pago
- Relationship: despesas_extras (1:N cascade)
- Criado por: `lancar_frete_automatico()` em `app/fretes/routes.py:3342`

**Mapeamento Nacom → CarVia**:

| Conceito | Nacom | CarVia CUSTO | CarVia VENDA |
|----------|-------|-------------|-------------|
| Frete | `Frete` | Mesmo registro | Mesmo registro |
| CTe | `ConhecimentoTransporte` | `CarviaSubcontrato` | `CarviaOperacao` |
| Fatura | `FaturaFrete` | `CarviaFaturaTransportadora` | `CarviaFaturaCliente` |
| Despesa | `DespesaExtra` | `CarviaCustoEntrega` | `CarviaCteComplementar` |

**Diferencas da Nacom**:
1. **Agregacao CNPJ**: Nacom agrupa por cnpj_cliente (destinatario). CarVia agrupa por
   CNPJ emitente + CNPJ destino (pois NFs sao de terceiros, nao emitidas pela Nacom).
   Essa agregacao tambem afeta a cotacao (momento do calculo do frete).
2. **6 entidades vinculadas**: Alem do trio CUSTO (Sub + FatTransp + CustoEntrega),
   tambem vincula o trio VENDA (Operacao + FatCliente + CteComp).
3. **Gatilho condicional**: Se embarque completo (todas NFs) + portaria deu saida → gera frete.
   Se portaria ja saiu mas falta NF → gatilho e a propria NF ao ser anexada.

**Decisao**: Tabela nova `carvia_fretes` (R1 — modulo isolado, sem Odoo).

### Design do Model CarviaFrete

```python
class CarviaFrete(db.Model):
    """Frete CarVia — 1 frete = 1 grupo CNPJ (emitente+destino) + 1 Embarque.

    Equivalente ao Frete Nacom mas com 2 lados:
    - CUSTO: CarviaSubcontrato + CarviaFaturaTransportadora + CarviaCustoEntrega
    - VENDA: CarviaOperacao + CarviaFaturaCliente + CarviaCteComplementar

    Sem integracao Odoo. Sem aprovacao multi-nivel.
    """
    __tablename__ = 'carvia_fretes'

    id = db.Column(db.Integer, primary_key=True)

    # --- Chaves ---
    embarque_id = db.Column(db.Integer, db.ForeignKey('embarques.id'), nullable=False, index=True)
    transportadora_id = db.Column(db.Integer, db.ForeignKey('transportadoras.id'), nullable=False)

    # --- Agregacao por CNPJ (emitente + destino) ---
    # Diferente da Nacom que agrupa so por cnpj_cliente (destino)
    cnpj_emitente = db.Column(db.String(20), nullable=False, index=True)
    nome_emitente = db.Column(db.String(255))
    cnpj_destino = db.Column(db.String(20), nullable=False, index=True)
    nome_destino = db.Column(db.String(255))

    # --- Rota ---
    uf_destino = db.Column(db.String(2), nullable=False)
    cidade_destino = db.Column(db.String(100), nullable=False)
    tipo_carga = db.Column(db.String(20), nullable=False)  # DIRETA | FRACIONADA

    # --- Totais das NFs deste grupo ---
    peso_total = db.Column(db.Float, nullable=False, default=0)
    valor_total_nfs = db.Column(db.Float, nullable=False, default=0)
    quantidade_nfs = db.Column(db.Integer, nullable=False, default=0)
    numeros_nfs = db.Column(db.Text)  # CSV com numeros das NFs

    # --- Snapshot tabela frete (custo) ---
    tabela_nome_tabela = db.Column(db.String(100))
    tabela_valor_kg = db.Column(db.Float)
    tabela_percentual_valor = db.Column(db.Float)
    tabela_frete_minimo_valor = db.Column(db.Float)
    tabela_frete_minimo_peso = db.Column(db.Float)
    tabela_icms = db.Column(db.Float)
    tabela_percentual_gris = db.Column(db.Float)
    tabela_pedagio_por_100kg = db.Column(db.Float)
    tabela_valor_tas = db.Column(db.Float)
    tabela_percentual_adv = db.Column(db.Float)
    tabela_percentual_rca = db.Column(db.Float)
    tabela_valor_despacho = db.Column(db.Float)
    tabela_valor_cte = db.Column(db.Float)
    tabela_icms_incluso = db.Column(db.Boolean, default=False)
    tabela_icms_destino = db.Column(db.Float)
    tabela_gris_minimo = db.Column(db.Float, default=0)
    tabela_adv_minimo = db.Column(db.Float, default=0)
    tabela_icms_proprio = db.Column(db.Float)

    # --- 4 tipos de valor (CUSTO = subcontrato) ---
    valor_cotado = db.Column(db.Float, nullable=False, default=0)  # Calculado pela tabela Nacom
    valor_cte = db.Column(db.Float)       # Valor real cobrado no CTe subcontrato
    valor_considerado = db.Column(db.Float)  # Valor validado internamente
    valor_pago = db.Column(db.Float)      # Valor efetivamente pago

    # --- Valor VENDA (tabela CarVia) ---
    valor_venda = db.Column(db.Float)     # Preco de venda (tabela CarVia)
    margem = db.Column(db.Float)          # venda - custo (calculado)

    # --- Vinculacao CUSTO ---
    subcontrato_id = db.Column(db.Integer, db.ForeignKey('carvia_subcontratos.id'), nullable=True, index=True)
    fatura_transportadora_id = db.Column(db.Integer, db.ForeignKey('carvia_faturas_transportadora.id'), nullable=True)

    # --- Vinculacao VENDA ---
    operacao_id = db.Column(db.Integer, db.ForeignKey('carvia_operacoes.id'), nullable=True, index=True)
    fatura_cliente_id = db.Column(db.Integer, db.ForeignKey('carvia_faturas_cliente.id'), nullable=True)

    # --- Status ---
    # PENDENTE → CONFERIDO → FATURADO
    # (sem LANCADO_ODOO — CarVia nao integra Odoo)
    status = db.Column(db.String(20), default='PENDENTE', index=True)

    # --- Auditoria ---
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=False)
    observacoes = db.Column(db.Text)

    # --- Relationships ---
    embarque = db.relationship('Embarque')
    transportadora = db.relationship('Transportadora')
    subcontrato = db.relationship('CarviaSubcontrato')
    operacao = db.relationship('CarviaOperacao')
    fatura_transportadora = db.relationship('CarviaFaturaTransportadora')
    fatura_cliente = db.relationship('CarviaFaturaCliente')
    custos_entrega = db.relationship('CarviaCustoEntrega')  # via FK em CustoEntrega? TBD
    ctes_complementares = db.relationship('CarviaCteComplementar')  # via FK? TBD
```

### Agregacao: CNPJ emitente + destino

**Nacom**: 1 Frete = 1 `cnpj_cliente` (destino) por embarque.
Todas as NFs do mesmo CNPJ destino no embarque → 1 frete.

**CarVia**: 1 Frete = 1 par (`cnpj_emitente`, `cnpj_destino`) por embarque.
NFs com mesmo par emitente+destino → 1 frete.
Motivo: NFs CarVia sao de terceiros (emitentes diferentes), nao da Nacom.

**Impacto na cotacao**: A agregacao para calculo do frete tambem agrupa por emitente+destino
(nao so por destino como na Nacom).

### Gatilho de criacao

```
CONDICAO 1: Embarque completo + portaria deu saida
  → Todas NFs preenchidas em EmbarqueItem
  → Portaria registrou saida
  → GERA frete CarVia automaticamente

CONDICAO 2: Portaria ja saiu mas NF chega depois
  → NF anexada via PUT /carvia/api/pedidos-carvia/<id>/nf
  → Verifica se portaria ja saiu para este embarque
  → Se sim → GERA frete para o grupo desta NF

Logica: CarviaFreteService.lancar_frete_carvia() (orquestrador unico, 22/03/2026)
  1. Buscar EmbarqueItems CarVia ativos com NF preenchida
  2. Agrupar por (cnpj_emitente, cnpj_destino)
  3. Para cada grupo: criar CarviaOperacao + CarviaSubcontrato + CarviaFrete atomicamente
  4. Todos FKs populados na criacao (operacao_id, subcontrato_id)
  5. Se frete ja existe (NF tardia): ATUALIZAR totais + junctions + valores
```

### Ordem de vinculacao — VENDA vs CUSTO (logica de negocio)

**VENDA (CarVia → cliente): CTe ANTES de Fatura**
```
CarviaOperacao (CTe CarVia) → criado ao gerar frete
  → vinculado ao CarviaFrete.operacao_id
  → CarviaFaturaCliente criada DEPOIS, agrupando CTes
  → vinculada ao CarviaFrete.fatura_cliente_id posteriormente
```
**Motivo**: Todo servico prestado DEVE ser cobrado. O CTe e o registro do servico,
a fatura e a cobranca. Primeiro garante que o CTe existe, depois cobra.

**CUSTO (Transportadora → CarVia): Fatura ANTES de CTe**
```
CarviaFaturaTransportadora → recebida da transportadora (importacao PDF)
  → vinculada ao CarviaFrete.fatura_transportadora_id
  → CarviaSubcontrato (CTe) vinculado DEPOIS, dentro da fatura
  → conferencia valida cada CTe da fatura
```
**Motivo**: Transportadoras cancelam CTes sem avisar. Os CTes validos sao os que
estao sendo cobrados na fatura. Inicia pelo documento de cobranca, depois confere.

**Consequencia para o CarviaFrete**:
- `operacao_id`: preenchido na CRIACAO do frete (auto-gerado)
- `fatura_cliente_id`: preenchido DEPOIS (quando fatura e criada manualmente)
- `fatura_transportadora_id`: preenchido DEPOIS (quando fatura e importada)
- `subcontrato_id`: preenchido DEPOIS (quando CTe e vinculado a fatura)

### Relacionamento com CustoEntrega e CteComplementar

FK inversa (padrao Nacom): `CarviaCustoEntrega.frete_id` e `CarviaCteComplementar.frete_id`.
Migration adicionou campos nas tabelas existentes.

**Escopo estimado**: Model + Migration + Service + Gatilhos — ~2-3 dias

### G2 — fechar_frete path alteracao

O path de ALTERACAO de embarque existente (`app/cotacao/routes.py:1288-1430`) nao tem
tratamento de itens CARVIA-*. Se Elaine alterar cotacao de embarque com provisorios:
- Itens Nacom: atualizados normalmente
- Itens CarVia: podem ser sobrescritos ou perdidos

**Fix**: Mesmo padrao de P2.1 — skip CARVIA-* nos loops de alteracao.

### G3 — fechar_frete_grupo

Rota `fechar_frete_grupo` (`app/cotacao/routes.py:1630+`) fecha frete por grupo (N embarques).
Precisa do mesmo skip CARVIA-* que `fechar_frete`.

### G4 — imprimir_completo com provisorio

Template `imprimir_completo.html` itera `separacoes_data` para cada item do embarque.
Para CARVIA-*, nao ha `separacoes_data` (nao existe Separacao). Precisa:
1. Detectar itens CARVIA-* e buscar dados de CarViaCotacao/CarviaPedido
2. Se provisorio: imprimir com marca d'agua/flag "PROVISORIO"
3. Se pedido com NF: imprimir normalmente (template CarVia)

### G5 — UI Jessica (cotacao → pedidos → NF)

Telas existentes:
- `/carvia/cotacoes` — lista/criar/detalhe (JA EXISTE)
- `/carvia/pedidos-carvia` — lista/detalhe (JA EXISTE)
- Endpoint `PUT /carvia/api/pedidos-carvia/<id>/nf` (JA EXISTE)

O que FALTA:
- Botao "Incluir Pedido" na tela de detalhe da cotacao
- Botao "Anexar NF" na tela de detalhe do pedido
- Botao "Anexar NF" na tela de detalhe da cotacao (atalho direto)
- Feedback visual: quais pedidos tem NF, quais faltam

### G7 — Flag impresso com auditoria

Conceito: quando embarque e impresso, marcar flag. Quando EmbarqueItem e alterado
(ex: provisorio substituido por real), flag indica "impresso ANTES da alteracao" — pendente
de reimprimir. Garante que o embarque fisico impresso corresponda ao estado atual do sistema.

Campos necessarios (EmbarqueItem ou Embarque):
- `impresso_em`, `impresso_por`
- `alterado_apos_impressao` (bool, setado quando item e modificado apos impressao)

---

## 9. Perguntas Respondidas pelo Usuario

| # | Pergunta | Resposta | Impacto |
|---|----------|----------|---------|
| Q1 | "Fora da tabela" e o que? | Preco < tabela - desconto. Admin usa Nacom como referencia | Fluxo pricing |
| Q2A | Elaine roteiriza com itens? | So cotacao (sem detalhes) | Dados do provisorio |
| Q2B | Separacao antes/depois embarque? | Depois | Item provisorio necessario |
| Q2C | Como garantir que CarVia saia? | Sistema de alertas (#1-#5 do usuario) | Fases P3-P4 |
| Q2D | Embarque mix ou isolado? | Ambos | Tratamento cotacao_id NULL |
| Q3A | Quem preenche numero_nf? | Jessica ao anexar NF | Endpoint P5.1 |
| Q3B | Faturamento motos: mesmo sistema? | NFs CarVia (externas) | Clarificado |
| Q4A | Portaria bloqueia provisorios? | Alerta (nao bloqueia) | P3.3 |
| Q4B | Cotacao aprovada sem pedido? | Cancelar ou admin remove | P5.3 |
| Q4C | 1 cotacao → SP + RJ? | Sim, simultaneo | VIEW Parte 2B |
| Q5 | Rota/sub_rota para CarVia? | Calculados via cadastro_rota (UF+cidade) | VIEW v4 |
| Q6 | Dados custo DIRETA? | No Embarque (container) | P2.4 |
| Q7 | Dados custo FRACIONADA? | No EmbarqueItem (item) | P2.4 |
| Q8 | Cotacao automatica aplica CarVia? | Sim, gera CarviaSubcontrato | fechar_frete |
| Q9 | Saldo parcial? | Cotacao→Pedidos/NF/Saldo (gradual) | VIEW + EmbarqueItem |
| Q10 | FOB aplica CarVia? | NAO — FOB nao se aplica a CarVia | G1 eliminado |
| Q11 | fechar_frete alteracao + grupo? | Necessarios — precisam suporte CarVia | G2 + G3 |
| Q12 | imprimir_completo provisorio? | Flag/marca d'agua, removido quando pedido/NF substitui cotacao | G4 |
| Q13 | Flag impresso? | Necessario para separacoes E embarque. Alteracao invalida flag. | G7 |
| Q14 | UI Jessica (fluxo)? | Cotacao → acha → inclui pedidos ou NF. Se pedido, depois NF. | G5 |
| Q15 | Frete CarVia gatilho? | Portaria (se completo) OU NF (se portaria ja saiu) | P2.4 |
| Q16 | Agregacao CNPJ frete CarVia? | Emitente + Destino da NF (nao so cliente como Nacom) | P2.4 |
| Q17 | Entidades vinculadas ao frete? | 6: Sub+FatTransp+CustoEntrega + Oper+FatCliente+CteComp | P2.4 |
| Q18 | Frete CarVia tabela nova ou reuso? | Tabela nova isolada (R1 — modulo isolado) | P2.4 |
| Q19 | Frete CarVia passa pelo Odoo? | NAO — sem integracao Odoo | P2.4 |
| Q20 | FOB se aplica a CarVia? | NAO | G1 eliminado |
| Q21 | CarviaSubcontrato gerado como? | MANUALMENTE via fatura (fatura primeiro, CTe depois). Transportadoras cancelam CTe sem avisar. | P2.4b |
| Q22 | CarviaOperacao gerado como? | AUTO no frete. CTe primeiro, fatura depois. Garante que todo servico seja cobrado. | P2.4b |
| Q23 | Ordem vinculacao VENDA? | CTe CarVia (auto) → Fatura Cliente (manual posterior) | P2.4b |
| Q24 | Ordem vinculacao CUSTO? | Fatura Transp (importada) → CTe Subcontrato (conferencia posterior) | P2.4b |
