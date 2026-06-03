<!-- doc:meta
tipo: reference
camada: L2
sot_de: —
hub: docs/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# 📋 ESPECIFICAÇÃO TÉCNICA - SISTEMA UNIFICADO AGENDAMENTO SENDAS

> **Papel:** 📋 ESPECIFICAÇÃO TÉCNICA - SISTEMA UNIFICADO AGENDAMENTO SENDAS.

## Indice

- [🎯 ARQUITETURA](#arquitetura)
  - [Nomenclatura:](#nomenclatura)
- [🔍 ETAPA 0: IDENTIFICAÇÃO DO PORTAL](#etapa-0-identificação-do-portal)
  - [Arquivo Principal: `app/portal/utils/grupo_empresarial.py`](#arquivo-principal-appportalutilsgrupo_empresarialpy)
  - [JavaScript: `app/templates/carteira/js/agendamento/destinacao-portais.js:36`](#javascript-apptemplatescarteirajsagendamentodestinacao-portaisjs36)
  - [Endpoints Identificação:](#endpoints-identificação)
- [📦 ESTRUTURA DE DADOS UNIFICADA](#estrutura-de-dados-unificada)
- [🔄 FLUXO 1: AGENDAMENTO POR LOTE SP](#fluxo-1-agendamento-por-lote-sp)
  - [ENTRADA](#entrada)
  - [DADOS ENVIADOS](#dados-enviados)
  - [PROCESSAMENTO](#processamento)
  - [BUSCA DE DADOS (3 FONTES)](#busca-de-dados-3-fontes)
  - [RETORNO](#retorno)
- [🔄 FLUXO 2: AGENDAMENTO PELA CARTEIRA](#fluxo-2-agendamento-pela-carteira)
  - [ENTRADA](#entrada)
  - [DADOS ENVIADOS](#dados-enviados)
  - [ADICIONAR NA FILA](#adicionar-na-fila)
  - [PROCESSAMENTO FILA](#processamento-fila)
  - [RETORNO](#retorno)
- [🔄 FLUXO 3: AGENDAMENTO POR NF](#fluxo-3-agendamento-por-nf)
  - [ENTRADA](#entrada)
  - [DADOS ENVIADOS](#dados-enviados)
  - [ADICIONAR NA FILA](#adicionar-na-fila)
  - [PROCESSAMENTO](#processamento)
  - [RETORNO](#retorno)
- [🔧 WORKER UNIFICADO](#worker-unificado)
  - [Arquivo: `app/portal/workers/sendas_jobs.py`](#arquivo-appportalworkerssendas_jobspy)
- [📋 PREENCHIMENTO PLANILHA EXCEL](#preenchimento-planilha-excel)
  - [Arquivo: `app/portal/sendas/preencher_planilha.py`](#arquivo-appportalsendaspreencher_planilhapy)
  - [MATCHING (linha 547-568)](#matching-linha-547-568)
  - [COLUNAS](#colunas)
  - [MODIFICAÇÃO NECESSÁRIA](#modificação-necessária)
- [🗄️ MODELOS](#modelos)
  - [FilaAgendamentoSendas](#filaagendamentosendas)
  - [PortalIntegracao](#portalintegracao)
- [🚨 CORREÇÕES NECESSÁRIAS](#correções-necessárias)
  - [1. ENDPOINT ERRADO](#1-endpoint-errado)
  - [2. WORKER DESTRUINDO DADOS](#2-worker-destruindo-dados)
  - [3. PREENCHER_PLANILHA](#3-preencher_planilha)
  - [4. PROTOCOLO NÃO SALVO](#4-protocolo-não-salvo)
- [📊 REGRAS DE NEGÓCIO](#regras-de-negócio)
  - [Data Expedição SP](#data-expedição-sp)
  - [Protocolo](#protocolo)
  - [Fallback pedido_cliente](#fallback-pedido_cliente)
- [⚡ DIFERENÇAS PORTAIS](#diferenças-portais)
  - [SENDAS](#sendas)
  - [ATACADÃO](#atacadão)

**Versão:** 4.0 DEFINITIVA
**Data:** 2025-01-14

---

## 🎯 ARQUITETURA

```
[IDENTIFICAÇÃO PORTAL] → ENTRADA (3 origens) → AFUNILAMENTO → PROCESSAMENTO → EXPANSÃO → RETORNO (3 destinos)
```

### Nomenclatura:
- **FLUXO 1**: Agendamento por Lote SP
- **FLUXO 2**: Agendamento pela Carteira
- **FLUXO 3**: Agendamento por NF

---

## 🔍 ETAPA 0: IDENTIFICAÇÃO DO PORTAL

### Arquivo Principal: `app/portal/utils/grupo_empresarial.py`

```python
GRUPOS_EMPRESARIAIS = {
    'atacadao': {
        'portal': 'atacadao',
        'prefixos': ['93209765', '75315333', '00063960']
    },
    'assai': {
        'portal': 'sendas',
        'prefixos': ['06057223']
    }
}

GrupoEmpresarial.identificar_grupo(cnpj) → 'assai'|'atacadao'|None
GrupoEmpresarial.identificar_portal(cnpj) → 'sendas'|'atacadao'|None
```

### JavaScript: `app/templates/carteira/js/agendamento/destinacao-portais.js:36`
```javascript
// LIMITAÇÃO: Só funciona com lote_id (Fluxo 2)
async identificarPortal(loteId) {
    fetch('/portal/utils/api/identificar-portal-por-lote')
    // Backend busca CNPJ do lote → chama identificar_grupo
}
```

### Endpoints Identificação:
- `/portal/utils/api/identificar-portal-por-lote` (usa lote_id)
- `/portal/utils/api/identificar-portal-por-cnpj` (direto)

---

## 📦 ESTRUTURA DE DADOS UNIFICADA

```python
{
    'cnpj': str,                    # 14 dígitos
    'data_agendamento': date,       # YYYY-MM-DD
    'data_expedicao': date,         # D-1 útil para SP
    'protocolo': str,               # AGEND_{cnpj[-4:]}_{YYYYMMDD}
    'peso_total': float,            # kg
    'tipo_origem': str,             # 'lote_sp'|'carteira'|'nf'
    'documento_origem': str,        # separacao_lote_id|numero_nf
    'itens': [{
        'id': int,
        'num_pedido': str,
        'pedido_cliente': str,      # CRÍTICO para matching
        'cod_produto': str,
        'nome_produto': str,
        'quantidade': float,
        'peso': float,
        'data_expedicao': date,
        'tipo_origem': str,
        'documento_origem': str
    }]
}
```

---

## 🔄 FLUXO 1: AGENDAMENTO POR LOTE SP

### ENTRADA
| Campo | Arquivo | Linha |
|-------|---------|-------|
| Interface | `app/templates/carteira/programacao_em_lote.html` | - |
| Botão | `id="btnProcessarLote"` | 84 |
| Endpoint | `/carteira/programacao-lote/api/processar-agendamento-sendas-async` | 1244 |
| Handler | `app/carteira/routes/programacao_em_lote/routes.py` | 1246 |

### DADOS ENVIADOS
```javascript
// app/static/js/programacao-lote.js:1341
{
    portal: 'sendas',
    agendamentos: [{
        cnpj: '06057223000xxx',
        expedicao: '2025-01-12',
        agendamento: '2025-01-13'
    }]
}
```

### PROCESSAMENTO
```python
# routes.py:1300-1309
lista_cnpjs_agendamento = [{
    'cnpj': cnpj,
    'data_agendamento': datetime.strptime(data_agendamento, '%Y-%m-%d').date()
}]

# NÃO USA FILA - Direto para worker
# routes.py:1770-1777
job = enqueue_job(processar_agendamento_sendas, ...)
```

### BUSCA DE DADOS (3 FONTES)
```python
# preencher_planilha.py:212-406
# 1. CarteiraPrincipal (linha 212-287)
CarteiraPrincipal.query.filter_by(cnpj_cpf=cnpj, ativo=True)

# 2. Separacao não faturada (linha 293-352)
Separacao.query.filter(cnpj_cpf=cnpj, sincronizado_nf=False)

# 3. NF no CD (linha 356-406)
Separacao.query.filter(cnpj_cpf=cnpj, sincronizado_nf=True, nf_cd=True)
```

### RETORNO
```python
# routes.py:1451-1520
Separacao(
    separacao_lote_id=lote_id,
    status='PREVISAO',
    protocolo=protocolo  # Salvando aqui
)
```

---

## 🔄 FLUXO 2: AGENDAMENTO PELA CARTEIRA

### ENTRADA
| Campo | Arquivo | Linha |
|-------|---------|-------|
| Interface | `app/templates/carteira/agrupados_balanceado.html` | - |
| Botão | `carteiraAgrupada.agendarNoPortal` | 57 |
| JavaScript | `app/templates/carteira/js/agendamento/sendas/portal-sendas.js` | 24 |
| Endpoint ADD | `/portal/sendas/fila/adicionar` | 38 |

### DADOS ENVIADOS
```javascript
// portal-sendas.js:38-49
{
    tipo_origem: 'separacao',
    documento_origem: loteId,
    data_expedicao: agendDate - 1,  // Calculado
    data_agendamento: dataAgendamento
}
```

### ADICIONAR NA FILA
```python
# routes_fila.py:115-173
itens_sep = Separacao.query.filter_by(
    separacao_lote_id=documento_origem,
    sincronizado_nf=False
).all()

# Busca pedido_cliente com fallback (linha 128-135)
pedido_cliente = buscar_pedido_cliente_com_fallback(num_pedido)
# → Separacao.pedido_cliente ou buscar_pedido_cliente_odoo()

FilaAgendamentoSendas.adicionar(
    tipo_origem='separacao',
    documento_origem=documento_origem,
    cnpj=item.cnpj_cpf,
    pedido_cliente=pedido_cliente  # COM FALLBACK
)
```

### PROCESSAMENTO FILA
```javascript
// ❌ ERRO portal-sendas.js:187
fetch('/carteira/programacao-lote/api/processar-agendamento-sendas-async')
// ✅ CORRETO
fetch('/portal/sendas/fila/processar')
```

```python
# routes_fila.py:422-428
dados_para_processar = [{
    'cnpj': cnpj,
    'data_agendamento': data,
    'protocolo': protocolo,
    'peso_total': peso_grupo,
    'itens': [{
        'id': item.id,
        'pedido_cliente': item.pedido_cliente,  # JÁ TEM!
        'cod_produto': item.cod_produto,
        'quantidade': float(item.quantidade)
    }]
}]
```

### RETORNO
```python
# FALTA IMPLEMENTAR
Separacao.query.filter_by(
    separacao_lote_id=documento_origem
).update({'protocolo': protocolo})
```

---

## 🔄 FLUXO 3: AGENDAMENTO POR NF

### ENTRADA
| Campo | Arquivo | Linha |
|-------|---------|-------|
| Interface | `app/templates/monitoramento/listar_entregas.html` | 2623 |
| Modal | `modalAgendamentoPortal` | 42 |
| Endpoint ADD | `/portal/sendas/fila/adicionar` | 2666 |

### DADOS ENVIADOS
```javascript
// listar_entregas.html:2666-2677
{
    tipo_origem: 'nf',
    documento_origem: numeroNf,
    data_expedicao: dataExpedicao,
    data_agendamento: dataAgendamento
}
```

### ADICIONAR NA FILA
```python
# routes_fila.py:177-289
# 1. Valida EntregaMonitorada (linha 179-187)
entrega = EntregaMonitorada.query.filter_by(numero_nf=documento_origem).first()

# 2. FaturamentoProduto (linha 190-229)
produtos_faturados = FaturamentoProduto.query.filter_by(numero_nf=documento_origem).all()
pedido_cliente = buscar_pedido_cliente_com_fallback(produtos_faturados[0].origem)

# 3. Fallback Separacao (linha 232-289)
if not produtos_faturados:
    itens_sep = Separacao.query.filter_by(numero_nf=documento_origem).all()
```

### PROCESSAMENTO
```javascript
// listar_entregas.html:2765
fetch('/portal/sendas/fila/processar')  // ✅ CORRETO
```

### RETORNO
```python
# FALTA IMPLEMENTAR
AgendamentoEntrega(
    entrega_id=entrega.id,
    protocolo_agendamento=protocolo,
    data_agendada=data_agendamento,
    forma_agendamento='Portal Sendas'
)
EntregaMonitorada.data_agenda = data_agendamento
```

---

## 🔧 WORKER UNIFICADO

### Arquivo: `app/portal/workers/sendas_jobs.py`

```python
def processar_agendamento_sendas(integracao_id, lista_cnpjs_agendamento, usuario_nome):
    # ❌ PROBLEMA linhas 52-58: Destrói dados
    lista_cnpjs_processada = []
    for item in lista_cnpjs_agendamento:
        lista_cnpjs_processada.append({
            'cnpj': cnpj,
            'data_agendamento': data_agendamento
        })  # PERDE 'itens'!

    # ✅ CORREÇÃO NECESSÁRIA
    if 'itens' in lista_cnpjs_agendamento[0]:
        usar_dados_fornecidos = True  # NÃO MODIFICAR

    # linha 100-109
    arquivo_processado = preenchedor.preencher_multiplos_cnpjs(
        arquivo_origem=arquivo_baixado,
        lista_cnpjs_agendamento=lista_cnpjs_agendamento,
        usar_dados_fornecidos=usar_dados_fornecidos  # ADICIONAR
    )
```

---

## 📋 PREENCHIMENTO PLANILHA EXCEL

### Arquivo: `app/portal/sendas/preencher_planilha.py`

### MATCHING (linha 547-568)
```python
# Excel
pedido_cliente_excel = ws.cell(row=row, column=7).value   # Col G
codigo_produto_sendas = ws.cell(row=row, column=8).value  # Col H

# Match
if pedido_cliente == pedido_cliente_excel and
   codigo_interno == DE_PARA[codigo_produto_sendas]:
    # PREENCHER
```

### COLUNAS
| Col | Campo | Valor |
|-----|-------|-------|
| A | Demanda ID | Sequencial |
| G | Pedido Cliente | pedido_cliente |
| H | Código Produto | Código Sendas |
| Q | Quantidade | min(qtd, saldo) |
| R | Data Agendamento | data_agendamento |
| U | Tipo Carga | 'Paletizada' |
| V | Tipo Veículo | tipo_caminhao(peso) |
| X | Protocolo | AGEND_xxxx_YYYYMMDD |

### MODIFICAÇÃO NECESSÁRIA
```python
def preencher_multiplos_cnpjs(self, arquivo_origem, lista_cnpjs_agendamento,
                              usar_dados_fornecidos=False):
    if usar_dados_fornecidos and 'itens' in lista_cnpjs_agendamento[0]:
        # USAR dados fornecidos
        todos_dados = self._converter_dados_fornecidos(lista_cnpjs_agendamento)
    else:
        # Buscar das 3 fontes (atual)
        todos_dados = self._buscar_todas_fontes(lista_cnpjs_agendamento)
```

---

## 🗄️ MODELOS

### FilaAgendamentoSendas
```python
tipo_origem = String(20)        # 'separacao'|'nf'
documento_origem = String(50)   # lote_id|numero_nf
cnpj = String(20)
num_pedido = String(50)
pedido_cliente = String(100)    # COM FALLBACK ODOO
cod_produto = String(50)
quantidade = Numeric(15,3)
data_expedicao = Date
data_agendamento = Date
protocolo = String(100)         # AGEND_{cnpj[-4:]}_{YYYYMMDD}
status = String(20)             # 'pendente'|'processado'|'erro'
```

### PortalIntegracao
```python
portal = 'sendas'
lote_id = String(50)
tipo_lote = 'agendamento_lote'|'agendamento_fila'
status = 'aguardando'|'processando'|'concluido'|'erro'
job_id = String(36)
dados_enviados = JSONB
resposta_portal = JSONB
```

---

## 🚨 CORREÇÕES NECESSÁRIAS

### 1. ENDPOINT ERRADO
| Arquivo | Linha | Atual | Correto |
|---------|-------|-------|---------|
| `portal-sendas.js` | 187 | `/carteira/programacao-lote/api/processar-agendamento-sendas-async` | `/portal/sendas/fila/processar` |

### 2. WORKER DESTRUINDO DADOS
| Arquivo | Linhas | Problema | Solução |
|---------|--------|----------|---------|
| `sendas_jobs.py` | 52-58 | Sobrescreve com `{cnpj, data}` | Preservar quando tem 'itens' |

### 3. PREENCHER_PLANILHA
| Arquivo | Problema | Solução |
|---------|----------|---------|
| `preencher_planilha.py` | Sempre busca do banco | Adicionar `usar_dados_fornecidos` |

### 4. PROTOCOLO NÃO SALVO
| Fluxo | Destino | Implementar |
|-------|---------|-------------|
| 2 | `Separacao.protocolo` | UPDATE após sucesso |
| 3 | `AgendamentoEntrega.protocolo_agendamento` | INSERT após sucesso |

---

## 📊 REGRAS DE NEGÓCIO

### Data Expedição SP
```python
if uf == 'SP' and not data_expedicao:
    data_exp = data_agendamento - timedelta(days=1)
    if data_exp.weekday() == 6: data_exp -= timedelta(days=2)  # Dom→Sex
    if data_exp.weekday() == 5: data_exp -= timedelta(days=1)  # Sab→Sex
```

### Protocolo
```python
f"AGEND_{cnpj[-4:]}_{data_agendamento.strftime('%Y%m%d')}"
```

### Fallback pedido_cliente
```python
# routes_fila.py:43-77
def buscar_pedido_cliente_com_fallback(num_pedido):
    # 1. Separacao.pedido_cliente
    # 2. buscar_pedido_cliente_odoo()
    # 3. Atualizar Separacao para cache
```

---

## ⚡ DIFERENÇAS PORTAIS

### SENDAS
- Planilha Excel do portal
- Agrupa múltiplos pedidos
- Fluxo 1: Direto worker
- Fluxo 2/3: FilaAgendamentoSendas (20min)

### ATACADÃO
- Agendamento unitário
- Sempre enfileira
- Transportadora fixa na rota
