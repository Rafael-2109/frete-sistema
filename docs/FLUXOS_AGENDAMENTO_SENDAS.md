# 📋 DOCUMENTAÇÃO TÉCNICA - FLUXOS DE AGENDAMENTO SENDAS

**Data:** 2025-01-13
**Versão:** 2.0 (REVISADA)
**Autor:** Sistema de Análise

---

## 📊 VISÃO GERAL

Sistema possui **3 fluxos distintos** para agendamento no portal Sendas:

1. **Programação-Lote**: Agendamento em massa (versões síncrona e assíncrona)
2. **Carteira Agrupada**: Agendamento individual via Separacao com fila
3. **Listar Entregas NF**: Agendamento individual via EntregaMonitorada com fila

**IMPORTANTE:** TODOS os fluxos convergem para o mesmo worker (`sendas_jobs.py`) que usa `consumir_agendas.py` e `preencher_planilha.py`

---

## 🔄 FLUXO 1: PROGRAMAÇÃO-LOTE (VERSÕES SÍNCRONA E ASSÍNCRONA)

### 📁 Arquivos Envolvidos

| Arquivo | Função | Linhas Relevantes |
|---------|--------|-------------------|
| `/app/carteira/routes/programacao_em_lote/routes.py` | Endpoints síncronos e assíncronos | 1267-1656 (sync), 1659-1821 (async) |
| `/app/portal/workers/sendas_jobs.py` | Worker processamento | 15-185 |
| `/app/portal/sendas/preencher_planilha.py` | Preenchimento planilha Excel | 144-890 |
| `/app/portal/sendas/consumir_agendas.py` | Navegação portal Sendas | - |

### 🔀 Fluxo de Dados

#### 1️⃣ **Frontend → Backend**
```javascript
// Frontend envia:
{
  portal: 'sendas',
  agendamentos: [
    {
      cnpj: '06057223000xxx',
      expedicao: '2025-01-12',    // Data fornecida, NÃO calculada
      agendamento: '2025-01-13'
    }
  ]
}
```

#### 2️⃣ **Endpoint Síncrono** (`/api/processar-agendamento-sendas`)
```python
# Linha 1267-1420: Processamento síncrono
# Validações:
- Verifica portal == 'sendas' (linha 1282)
- Filtra CNPJs com data_agendamento válida (linha 1302-1319)

# Prepara para preencher_planilha:
lista_cnpjs_agendamento = [
  {
    'cnpj': '06057223000xxx',
    'data_agendamento': date(2025, 1, 13)  # Convertido para date object
  }
]

# Busca dados da CarteiraPrincipal (linha 1445-1449):
pedidos_carteira = CarteiraPrincipal.query.filter_by(
    cnpj_cpf=cnpj,
    qtd_saldo_produto_pedido > 0
).all()

# Cria Separacao com dados (linha 1451-1520)
```

#### 3️⃣ **Endpoint Assíncrono** (`/api/processar-agendamento-sendas-async`)
```python
# Linha 1659-1821: Enfileira no Redis Queue
# Cria PortalIntegracao (linha 1752-1764):
integracao = PortalIntegracao(
    portal='sendas',
    lote_id=gerar_lote_id(),
    tipo_lote='agendamento_lote',
    status='aguardando',
    dados_enviados={
        'cnpjs': [{'cnpj': '...', 'data_agendamento': '2025-01-13'}],
        'total': len(cnpjs),
        'usuario': 'Sistema'
    }
)

# Enfileira job (linha 1770-1777):
job = enqueue_job(
    processar_sendas_job,
    integracao.id,
    lista_cnpjs_agendamento,  # APENAS {cnpj, data_agendamento}
    usuario_nome,
    queue_name='sendas',
    timeout='15m'
)
```

#### 4️⃣ **Worker** (`sendas_jobs.py`)
```python
# Linha 15: Assinatura da função
def processar_agendamento_sendas(
    integracao_id: int,
    lista_cnpjs_agendamento: list,  # [{cnpj, data_agendamento}, ...]
    usuario_nome: str = None
)

# Linha 100-102: Chama preencher_planilha
arquivo_processado = preenchedor.preencher_multiplos_cnpjs(
    arquivo_origem=arquivo_baixado,
    lista_cnpjs_agendamento=lista_cnpjs_agendamento
)
```

#### 5️⃣ **Preencher Planilha** (`preencher_planilha.py`)
```python
# Linha 190-410: Busca dados completos do banco
# Para cada CNPJ, busca em 3 fontes:

# 1. CarteiraPrincipal (linha 212-287):
query = CarteiraPrincipal.query.filter_by(cnpj_cpf=cnpj, ativo=True)
# Campos extraídos:
- num_pedido
- pedido_cliente         # CRÍTICO para matching
- cod_produto
- nome_produto
- qtd_saldo_produto_pedido
- preco_produto_pedido
- expedicao
- agendamento
- protocolo
- observ_ped_1

# 2. Separacao não sincronizada (linha 293-352):
query = Separacao.query.filter(
    cnpj_cpf=cnpj,
    sincronizado_nf=False
)
# Campos extraídos:
- num_pedido
- pedido_cliente        # Pode ser NULL
- cod_produto
- qtd_saldo
- peso
- pallet
- valor_saldo
- expedicao
- agendamento
- protocolo
- observ_ped_1

# 3. NFs no CD (linha 356-406):
query = Separacao.query.filter(
    cnpj_cpf=cnpj,
    sincronizado_nf=True,
    nf_cd=True
)
```

#### 6️⃣ **Preenchimento Excel** (linha 516-607)
```python
# Lê da planilha Sendas:
unidade_destino = ws.cell(row=row, column=4).value      # Col D
codigo_pedido_cliente = ws.cell(row=row, column=7).value # Col G - PEDIDO_CLIENTE
codigo_produto_sendas = ws.cell(row=row, column=8).value # Col H - Código Sendas
saldo_disponivel = ws.cell(row=row, column=15).value    # Col O

# Matching (linha 547-568):
if pedido_cliente == codigo_pedido_cliente and codigo_nosso == codigo_produto_sendas:
    # PREENCHE:
    ws.cell(row=row, column=1).value = demanda_id        # Col A - Demanda
    ws.cell(row=row, column=17).value = quantidade      # Col Q - Quantidade
    ws.cell(row=row, column=18).value = data_agendamento # Col R - Data
    ws.cell(row=row, column=21).value = 'Paletizada'    # Col U - Tipo carga
    ws.cell(row=row, column=22).value = tipo_caminhao   # Col V - Veículo
    ws.cell(row=row, column=24).value = observacao_unica # Col X - Protocolo
```

### ⚠️ Problemas Identificados
- ❌ Não calcula expedição = agendamento - 1 para SP automaticamente
- ❌ Worker recebe apenas {cnpj, data_agendamento} (não aproveita dados ricos)
- ✅ pedido_cliente é buscado em preencher_planilha (mas poderia usar dados prontos)

---

## 🔄 FLUXO 2: CARTEIRA AGRUPADA (COM FILA)

### 📁 Arquivos Envolvidos

| Arquivo | Função | Linhas Relevantes |
|---------|--------|-------------------|
| `/app/templates/carteira/js/agendamento/sendas/portal-sendas.js` | Frontend JS | 24-110 |
| `/app/portal/sendas/routes_fila.py` | Endpoints da fila | 80-531 |
| `/app/portal/models_fila_sendas.py` | Modelo FilaAgendamentoSendas | 9-192 |
| `/app/portal/workers/sendas_jobs.py` | Worker processamento | 15-185 |

### 🔀 Fluxo de Dados

#### 1️⃣ **Frontend → Backend** (`portal-sendas.js`)
```javascript
// Linha 38-49: Adicionar na fila
fetch('/portal/sendas/fila/adicionar', {
    method: 'POST',
    body: JSON.stringify({
        tipo_origem: 'separacao',
        documento_origem: loteId,  // separacao_lote_id
        data_expedicao: dataExpedicao,  // Calculado: agendamento - 1
        data_agendamento: dataAgendamento
    })
})
```

#### 2️⃣ **Adicionar na Fila** (`routes_fila.py`)
```python
# Linha 115-173: Tipo origem SEPARACAO
# Busca itens:
itens_sep = Separacao.query.filter_by(
    separacao_lote_id=documento_origem,
    sincronizado_nf=False
).all()

# Busca pedido_cliente COM FALLBACK (linha 128-135):
if primeiro_item.pedido_cliente:
    pedido_cliente = primeiro_item.pedido_cliente
elif primeiro_item.num_pedido:
    pedido_cliente = buscar_pedido_cliente_com_fallback(num_pedido)
    # Fallback para Odoo (linha 59-73)

# Adiciona na fila (linha 158-169):
FilaAgendamentoSendas.adicionar(
    tipo_origem='separacao',
    documento_origem=documento_origem,
    cnpj=item.cnpj_cpf,
    num_pedido=item.num_pedido,
    cod_produto=item.cod_produto,
    nome_produto=nome_produto,
    quantidade=float(item.qtd_saldo),
    data_expedicao=data_exp_final,  # Calculado para SP
    data_agendamento=data_agendamento,
    pedido_cliente=pedido_cliente  # JÁ COM ODOO FALLBACK!
)
```

#### 3️⃣ **Modelo FilaAgendamentoSendas** (`models_fila_sendas.py`)
```python
# Campos do modelo (linha 15-44):
tipo_origem = db.String(20)        # 'separacao' ou 'nf'
documento_origem = db.String(50)   # separacao_lote_id ou numero_nf
cnpj = db.String(20)
num_pedido = db.String(50)
pedido_cliente = db.String(100)    # ESSENCIAL para Sendas
cod_produto = db.String(50)
nome_produto = db.String(255)
quantidade = db.Numeric(15, 3)
data_expedicao = db.Date
data_agendamento = db.Date
protocolo = db.String(100)         # AGEND_{cnpj[-4:]}_{YYYYMMDD}
status = db.String(20)              # pendente, processado, erro
```

#### 4️⃣ **Processar Fila** (`routes_fila.py`)
```python
# Linha 336-430: Agrupa e processa fila
grupos = FilaAgendamentoSendas.obter_para_processar()

# Para cada grupo (linha 380-428):
for item in grupo['itens']:
    # Estrutura enviada (linha 407-418):
    itens_dict.append({
        'id': item.id,
        'num_pedido': item.num_pedido,
        'pedido_cliente': item.pedido_cliente,  # TEM O PEDIDO_CLIENTE!
        'cod_produto': item.cod_produto,
        'nome_produto': item.nome_produto,
        'quantidade': float(item.quantidade),
        'peso': peso_item,
        'data_expedicao': item.data_expedicao.isoformat(),
        'tipo_origem': item.tipo_origem,
        'documento_origem': item.documento_origem
    })

# Envia para worker (linha 465):
dados_para_processar = [
    {
        'cnpj': cnpj,
        'data_agendamento': data,
        'protocolo': protocolo,
        'peso_total': peso_grupo,
        'itens': itens_dict  # DADOS COMPLETOS!
    }
]
```

### ⚠️ Problemas Identificados
- ✅ Calcula expedição = agendamento - 1 para SP
- ✅ Busca pedido_cliente com fallback Odoo
- ✅ Envia dados completos para worker
- ❌ Worker recebe dados completos mas preencher_planilha ignora e re-busca tudo

---

## 🔄 FLUXO 3: LISTAR ENTREGAS NF (COM FILA)

### 📁 Arquivos Envolvidos

| Arquivo | Função | Linhas Relevantes |
|---------|--------|-------------------|
| `/app/templates/monitoramento/listar_entregas.html` | Frontend HTML/JS | 2623-2780 |
| `/app/portal/sendas/routes_fila.py` | Endpoints da fila | 177-289 |
| `/app/portal/models_fila_sendas.py` | Modelo FilaAgendamentoSendas | 9-192 |

### 🔀 Fluxo de Dados

#### 1️⃣ **Frontend → Backend** (`listar_entregas.html`)
```javascript
// Linha 2659-2677: Adicionar NF na fila
fetch('/portal/sendas/fila/adicionar', {
    method: 'POST',
    body: JSON.stringify({
        tipo_origem: 'nf',
        documento_origem: numeroNf,
        data_expedicao: dataExpedicao,  // Calculado: agendamento - 1
        data_agendamento: dataAgendamento
    })
})
```

#### 2️⃣ **Adicionar na Fila - Tipo NF** (`routes_fila.py`)
```python
# Linha 177-289: Tipo origem NF

# 1. Valida EntregaMonitorada (linha 179-187):
entrega = EntregaMonitorada.query.filter_by(
    numero_nf=documento_origem
).first()

# 2. FONTE PRIMÁRIA: FaturamentoProduto (linha 190-229):
produtos_faturados = FaturamentoProduto.query.filter_by(
    numero_nf=documento_origem
).all()

if produtos_faturados:
    # Busca pedido_cliente UMA VEZ (linha 195-202):
    num_pedido = produtos_faturados[0].origem  # Número do pedido
    pedido_cliente = buscar_pedido_cliente_com_fallback(num_pedido)

    # Para cada produto (linha 205-227):
    FilaAgendamentoSendas.adicionar(
        tipo_origem='nf',
        documento_origem=documento_origem,
        cnpj=produto.cnpj_cliente,
        num_pedido=produto.origem,
        cod_produto=produto.cod_produto,
        nome_produto=produto.nome_produto,
        quantidade=float(produto.qtd_produto_faturado),
        data_expedicao=data_exp_final,
        data_agendamento=data_agendamento,
        pedido_cliente=pedido_cliente
    )

# 3. FALLBACK: Separacao (linha 232-289):
else:
    itens_sep = Separacao.query.filter_by(
        numero_nf=documento_origem
    ).all()

    # Mesmo processo com pedido_cliente
```

### ⚠️ Problemas Identificados
- ✅ Usa FaturamentoProduto como fonte primária
- ✅ Fallback para Separacao se necessário
- ✅ Busca pedido_cliente com fallback Odoo
- ✅ Calcula expedição para SP
- ❌ Worker recebe dados completos mas preencher_planilha ignora e re-busca tudo

---

## 🔧 ESTRUTURAS DE DADOS COMPARTILHADAS

### 📦 PortalIntegracao
```python
portal = 'sendas'
lote_id = String(50)
tipo_lote = 'agendamento_lote' | 'agendamento_fila'
status = 'aguardando' | 'processando' | 'concluido' | 'erro'
job_id = String(36)  # UUID do Redis Queue
dados_enviados = JSONB  # Dados originais
resposta_portal = JSONB  # Resposta do portal
```

### 📦 FilaAgendamentoSendas (apenas Fluxos 2 e 3)
```python
# Método adicionar() retorna/atualiza:
- Se existe (mesmo documento + produto): atualiza quantidade e datas
- Se não existe: cria novo registro
- Gera protocolo: f"AGEND_{cnpj[-4:]}_{data_agendamento.strftime('%Y%m%d')}"
```

### 📦 Mapeamentos DE-PARA
```python
# FilialDeParaSendas:
cnpj_to_filial('06057223000xxx') → 'FILIAL_CODIGO'

# ProdutoDeParaSendas:
interno_to_sendas('COD_INTERNO') → 'COD_SENDAS'
```

---

## 🎯 CAMPOS CRÍTICOS PARA PREENCHIMENTO

### Excel Sendas - Colunas Preenchidas

| Coluna | Campo | Valor | Origem |
|--------|-------|-------|--------|
| A | Demanda | ID sequencial | Gerado |
| D | Unidade Destino | Nome filial | Lido da planilha |
| **G** | **Pedido Cliente** | **pedido_cliente** | **CRÍTICO - matching** |
| **H** | **Código Produto** | **Código Sendas** | **CRÍTICO - matching** |
| O | Saldo Disponível | Quantidade max | Lido da planilha |
| Q | Quantidade Entrega | min(nossa_qtd, saldo) | Calculado |
| R | Data Entrega | data_agendamento | Parâmetro |
| U | Tipo Carga | 'Paletizada' | Fixo |
| V | Tipo Veículo | Baseado no peso | Calculado |
| X | Observação | Protocolo único | AGEND_xxxx_YYYYMMDD |

---

## 🏗️ ARQUITETURA UNIFICADA - WORKER COMPARTILHADO

### 📊 Convergência dos Fluxos

```
FLUXO 1 SÍNCRONO:
└── consumir_agendas.py → preencher_planilha.py (DIRETO, sem worker)

FLUXO 1 ASSÍNCRONO:
└── Redis Queue → Worker → consumir_agendas.py → preencher_planilha.py

FLUXO 2 (Carteira):
└── FilaAgendamentoSendas → Redis Queue → Worker → consumir_agendas.py → preencher_planilha.py

FLUXO 3 (NF):
└── FilaAgendamentoSendas → Redis Queue → Worker → consumir_agendas.py → preencher_planilha.py
```

### 🔧 Worker Único (`sendas_jobs.py`)

**TODOS os fluxos assíncronos usam o mesmo worker:**
```python
def processar_agendamento_sendas(integracao_id, lista_cnpjs_agendamento, usuario_nome):
    # Linha 86-87: Importa SEMPRE ambos
    from app.portal.sendas.consumir_agendas import ConsumirAgendasSendas
    from app.portal.sendas.preencher_planilha import PreencherPlanilhaSendas

    # Linha 92-93: Cria instâncias
    consumidor = ConsumirAgendasSendas()
    preenchedor = PreencherPlanilhaSendas()

    # Linha 100: USA preencher_planilha
    arquivo_processado = preenchedor.preencher_multiplos_cnpjs(
        arquivo_origem=arquivo_baixado,
        lista_cnpjs_agendamento=lista_cnpjs_agendamento
    )

    # Linha 110: USA consumir_agendas
    resultado = consumidor.executar_fluxo_completo_sync(
        processar_planilha_callback=processar_planilha_callback
    )
```

## 🔴 PROBLEMAS CENTRAIS

1. **Worker ignora estrutura rica da fila**:
   - Fluxos 2/3 enviam `{cnpj, data, protocolo, itens:[pedido_cliente, cod_produto, ...]}`
   - Worker passa para preencher_planilha que espera apenas `{cnpj, data_agendamento}`

2. **Re-busca desnecessária**:
   - Fluxos 2/3 já têm pedido_cliente com fallback Odoo
   - preencher_planilha ignora e busca tudo novamente do banco

3. **Protocolo não é salvo**:
   - Após processamento, protocolo gerado não volta para Separacao/FaturamentoProduto

4. **Expedição não calculada uniformemente**:
   - Fluxo 1 não calcula D-1 para SP automaticamente

---

## ✅ CORREÇÕES NECESSÁRIAS

1. **Worker deve detectar formato**:
```python
if isinstance(lista_cnpjs_agendamento[0], dict) and 'itens' in lista_cnpjs_agendamento[0]:
    # Formato completo da fila
else:
    # Formato simples (compatibilidade)
```

2. **preencher_planilha deve aceitar dados completos**:
```python
if 'itens' in lista_cnpjs_agendamento[0]:
    # Usar dados fornecidos
else:
    # Buscar do banco (atual)
```

3. **Salvar protocolo após sucesso**:
```python
# Atualizar Separacao ou FaturamentoProduto
item.protocolo = observacao_unica
db.session.commit()
```

---

## 📝 RESUMO EXECUTIVO

### Descobertas Principais:

1. **TODOS os fluxos usam o mesmo worker** (`sendas_jobs.py`)
2. **TODOS os fluxos usam** `consumir_agendas.py` e `preencher_planilha.py`
3. **Diferença está na preparação dos dados**:
   - Fluxo 1: Envia apenas `{cnpj, data_agendamento}`
   - Fluxos 2/3: Preparam dados completos com `pedido_cliente` (Odoo fallback)

### Problema Central:
**Desperdício de processamento**: Fluxos 2/3 já buscam `pedido_cliente` do Odoo e preparam todos os dados, mas `preencher_planilha.py` ignora e busca tudo novamente do banco de dados.

### Solução Proposta:
Fazer `preencher_planilha.py` detectar e usar os dados já preparados quando disponíveis, mantendo compatibilidade com formato simples.