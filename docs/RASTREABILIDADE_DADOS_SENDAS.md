<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# 📊 DOCUMENTO TÉCNICO - RASTREABILIDADE COMPLETA DOS DADOS

> **Papel:** 📊 DOCUMENTO TÉCNICO - RASTREABILIDADE COMPLETA DOS DADOS.

## Indice

- [Sistema de Agendamento Portal Sendas - 3 Fluxos](#sistema-de-agendamento-portal-sendas---3-fluxos)
- [🎯 OBJETIVO](#objetivo)
- [📍 ETAPA 1: ORIGEM DOS DADOS](#etapa-1-origem-dos-dados)
  - [DADOS ENVIADOS:](#dados-enviados)
  - [ESTRUTURA COMPLETA GERADA:](#estrutura-completa-gerada)
- [📍 ETAPA 2: ENFILEIRAMENTO](#etapa-2-enfileiramento)
- [📍 ETAPA 3: RECEPÇÃO NO WORKER](#etapa-3-recepção-no-worker)
  - [PRESERVAÇÃO DOS DADOS:](#preservação-dos-dados)
  - [LOG DE VERIFICAÇÃO:](#log-de-verificação)
- [📍 ETAPA 4: CALLBACK PARA PLANILHA](#etapa-4-callback-para-planilha)
- [📍 ETAPA 5: PREENCHIMENTO DA PLANILHA](#etapa-5-preenchimento-da-planilha)
  - [RECEPÇÃO E USO DOS DADOS:](#recepção-e-uso-dos-dados)
  - [ESCRITA NA PLANILHA:](#escrita-na-planilha)
- [📍 ETAPA 6: UPLOAD E RETORNO](#etapa-6-upload-e-retorno)
- [📍 ETAPA 7: PROCESSAMENTO DO RETORNO](#etapa-7-processamento-do-retorno)
  - [EXTRAÇÃO CORRETA DO PROTOCOLO:](#extração-correta-do-protocolo)
- [📍 ETAPA 8: SALVAMENTO NO BANCO](#etapa-8-salvamento-no-banco)
  - [ATUALIZAÇÃO DAS SEPARAÇÕES:](#atualização-das-separações)
- [📍 ETAPA 1: ORIGEM DOS DADOS](#etapa-1-origem-dos-dados)
  - [DADOS ENVIADOS DO FRONTEND:](#dados-enviados-do-frontend)
- [📍 ETAPA 2: ADIÇÃO NA FILA E GERAÇÃO DO PROTOCOLO](#etapa-2-adição-na-fila-e-geração-do-protocolo)
  - [PROCESSAMENTO E ENRIQUECIMENTO:](#processamento-e-enriquecimento)
- [📍 ETAPA 3: PROCESSAMENTO DA FILA](#etapa-3-processamento-da-fila)
  - [AGRUPAMENTO E GERAÇÃO DE PROTOCOLO:](#agrupamento-e-geração-de-protocolo)
- [📍 ETAPA 4: ENFILEIRAMENTO](#etapa-4-enfileiramento)
- [📍 ETAPAS 5-8: PROCESSAMENTO E RETORNO](#etapas-5-8-processamento-e-retorno)
  - [RETORNO DO FLUXO 2:](#retorno-do-fluxo-2)
- [📍 ETAPA 1: ORIGEM DOS DADOS](#etapa-1-origem-dos-dados)
  - [DADOS ENVIADOS DO FRONTEND:](#dados-enviados-do-frontend)
- [📍 ETAPA 2: ADIÇÃO NA FILA](#etapa-2-adição-na-fila)
  - [BUSCA E ENRIQUECIMENTO DOS DADOS:](#busca-e-enriquecimento-dos-dados)
- [📍 ETAPA 3: PROCESSAMENTO E RETORNO](#etapa-3-processamento-e-retorno)
  - [CRIAÇÃO DE REGISTRO DE AGENDAMENTO:](#criação-de-registro-de-agendamento)
  - [FALLBACK PARA SEPARAÇÃO:](#fallback-para-separação)
- [1. PROTOCOLO SEMPRE PRESENTE E ÚNICO](#1-protocolo-sempre-presente-e-único)
- [2. DADOS COMPLETOS PRESERVADOS](#2-dados-completos-preservados)
- [3. PROTOCOLO ÚNICO POR ENTIDADE](#3-protocolo-único-por-entidade)
- [4. IDENTIFICAÇÃO CORRETA DO TIPO DE FLUXO](#4-identificação-correta-do-tipo-de-fluxo)
- [5. DOCUMENTO_ORIGEM PRESERVADO](#5-documento_origem-preservado)
- [SISTEMA FUNCIONANDO CORRETAMENTE:](#sistema-funcionando-corretamente)
- [Contexto](#contexto)
## Sistema de Agendamento Portal Sendas - 3 Fluxos

**Versão:** 1.0
**Data:** 2025-01-15
**Autor:** Sistema de Documentação Técnica

---

## 🎯 OBJETIVO
Documentar com evidências técnicas o fluxo completo dos dados nos 3 processos de agendamento, garantindo que **NENHUM DADO É PERDIDO** em nenhuma etapa.

---

# 🔄 FLUXO 1: PROGRAMAÇÃO EM LOTE SP

## 📍 ETAPA 1: ORIGEM DOS DADOS
**Arquivo:** `app/carteira/routes/programacao_em_lote/routes.py`
**Linha:** 1295-1339

### DADOS ENVIADOS:
```python
# Linha 1295: Início do loop para cada CNPJ
for agendamento in cnpjs_validos:
    cnpj = agendamento.get('cnpj')                     # ✅ CAPTURADO
    data_agendamento = agendamento.get('agendamento')  # ✅ CAPTURADO
    data_expedicao = agendamento.get('expedicao')      # ✅ CAPTURADO

    # Linha 1311: Geração do protocolo
    protocolo = gerar_protocolo_sendas(cnpj, data_agendamento)  # ✅ GERADO

    # Linha 1329-1333: Busca dados completos
    dados_completos = buscar_dados_completos_cnpj(
        cnpj=cnpj,
        data_agendamento=data_agendamento,
        data_expedicao=data_expedicao
    )

    # Linha 1336-1337: Adiciona metadados
    dados_completos['tipo_fluxo'] = 'programacao_lote'  # ✅ ADICIONADO
    dados_completos['protocolo'] = protocolo            # ✅ ADICIONADO

    # Linha 1339: Adiciona à lista
    lista_cnpjs_agendamento.append(dados_completos)     # ✅ CONSOLIDADO
```

### ESTRUTURA COMPLETA GERADA:
```python
{
    'cnpj': '06.057.223/0001-95',
    'data_agendamento': date(2025, 1, 13),
    'data_expedicao': date(2025, 1, 12),
    'protocolo': 'AG_0001_13012025_1430',  # ✅ PRESENTE
    'tipo_fluxo': 'programacao_lote',
    'itens': [
        {
            'id': 123,
            'num_pedido': 'PED-001',
            'pedido_cliente': 'PC-12345',  # ✅ BUSCADO DO BANCO
            'cod_produto': 'PROD001',
            'nome_produto': 'Produto X',
            'quantidade': 100.0,
            'peso': 1500.0,
            'pallets': 10.0,
            'valor': 5000.0,
            'protocolo': 'AG_0001_13012025_1430'
        }
    ],
    'peso_total': Decimal('15000.50'),
    'pallets_total': Decimal('100'),
    'valor_total': Decimal('50000.00')
}
```

## 📍 ETAPA 2: ENFILEIRAMENTO
**Arquivo:** `app/carteira/routes/programacao_em_lote/routes.py`
**Linha:** 1381-1388

```python
# Linha 1381-1388: Enfileiramento para worker
job = enqueue_job(
    processar_sendas_job,      # Função alvo (importada na linha 1247)
    integracao.id,             # ID da integração criada
    lista_cnpjs_agendamento,   # ✅ LISTA COMPLETA PASSADA
    current_user.nome,         # Nome do usuário
    queue_name='sendas',       # Fila específica
    timeout='15m'              # Timeout
)
```

## 📍 ETAPA 3: RECEPÇÃO NO WORKER
**Arquivo:** `app/portal/workers/sendas_jobs.py`
**Linha:** 12-77

### PRESERVAÇÃO DOS DADOS:
```python
# Linha 12: Assinatura da função
def processar_agendamento_sendas(integracao_id, lista_cnpjs_agendamento, usuario_nome=None):

    # Linha 41-74: Processamento e preservação
    lista_cnpjs_processada = []
    for item in lista_cnpjs_agendamento:
        item_processado = dict(item)  # ✅ CÓPIA COMPLETA

        # Conversões de data mantendo estrutura
        if isinstance(item_processado.get('data_agendamento'), str):
            item_processado['data_agendamento'] = datetime.strptime(...).date()

        # Linha 72-74: PRESERVAR TODA A ESTRUTURA!
        lista_cnpjs_processada.append(item_processado)  # ✅ ESTRUTURA INTACTA
```

### LOG DE VERIFICAÇÃO:
```python
# Linha 80-84: Verificação de integridade
if lista_cnpjs_agendamento and isinstance(lista_cnpjs_agendamento[0], dict):
    campos_preservados = list(lista_cnpjs_agendamento[0].keys())
    logger.info(f"[Worker Sendas] Campos preservados: {campos_preservados}")
    # Output esperado: ['cnpj', 'data_agendamento', 'data_expedicao', 'protocolo', 'tipo_fluxo', 'itens', ...]
```

## 📍 ETAPA 4: CALLBACK PARA PLANILHA
**Arquivo:** `app/portal/workers/sendas_jobs.py`
**Linha:** 122-138

```python
# Linha 122-138: Callback com closure
def processar_planilha_callback(arquivo_baixado):
    # lista_cnpjs_agendamento está em closure - ✅ DADOS PRESERVADOS

    # Linha 128-129: Detecção de dados fornecidos
    usar_dados_fornecidos = 'itens' in lista_cnpjs_agendamento[0]  # ✅ TRUE

    # Linha 131-135: Chamada para preenchimento
    arquivo_processado = preenchedor.preencher_multiplos_cnpjs(
        arquivo_origem=arquivo_baixado,
        lista_cnpjs_agendamento=lista_cnpjs_agendamento,  # ✅ PASSA TUDO
        usar_dados_fornecidos=usar_dados_fornecidos        # ✅ TRUE
    )
```

## 📍 ETAPA 5: PREENCHIMENTO DA PLANILHA
**Arquivo:** `app/portal/sendas/preencher_planilha.py`
**Linha:** 615-837

### RECEPÇÃO E USO DOS DADOS:
```python
# Linha 615: Assinatura
def preencher_multiplos_cnpjs(self, arquivo_origem, lista_cnpjs_agendamento, ...):

    # Linha 651: Verificação de dados fornecidos
    if usar_dados_fornecidos and 'itens' in lista_cnpjs_agendamento[0]:
        # ✅ USA DADOS FORNECIDOS

        # Linha 657-668: Loop pelos grupos
        for idx, grupo in enumerate(lista_cnpjs_agendamento):
            cnpj = grupo.get('cnpj')                    # ✅ EXTRAÍDO
            protocolo = grupo.get('protocolo')          # ✅ EXTRAÍDO

            # Linha 666-668: Rastreamento de protocolo
            if protocolo:
                protocolos_unicos.add(protocolo)        # ✅ REGISTRADO

            # Linha 678-686: Armazenamento dos dados
            todos_dados[cnpj] = {
                'data_agendamento': data_agendamento,
                'protocolo': protocolo,                 # ✅ PRESERVADO
                'itens': grupo.get('itens', [])        # ✅ TODOS OS ITENS
            }
```

### ESCRITA NA PLANILHA:
```python
# Linha 837: Escrita do protocolo na planilha Excel
ws.cell(row=row, column=24).value = protocolo_cnpj  # ✅ COLUNA X
```

## 📍 ETAPA 6: UPLOAD E RETORNO
**Arquivo:** `app/portal/sendas/consumir_agendas.py`
**Linha:** 1340-1430

```python
# Linha 1340-1347: Estrutura de retorno
resultado = {
    'sucesso': False,
    'arquivo_download': None,
    'arquivo_upload': None,      # ✅ Nome do arquivo será preenchido
    'upload_sucesso': False,
    'mensagem': '',
    'timestamp': datetime.now().isoformat()
}

# Linha 1413: Após upload bem-sucedido
resultado['arquivo_upload'] = arquivo_para_upload  # ✅ NOME DO ARQUIVO
resultado['upload_sucesso'] = upload_sucesso       # ✅ STATUS
```

## 📍 ETAPA 7: PROCESSAMENTO DO RETORNO
**Arquivo:** `app/portal/workers/sendas_jobs.py`
**Linha:** 150-216 (APÓS CORREÇÃO)

### EXTRAÇÃO CORRETA DO PROTOCOLO:
```python
# Linha 156-169: Loop por TODOS os itens
for idx, item_agendamento in enumerate(lista_cnpjs_agendamento):
    # Linha 161: Pega protocolo do item
    protocolo = item_agendamento.get('protocolo')  # ✅ DA LISTA, NÃO DO RESULTADO

    # Linha 169: Log de confirmação
    logger.info(f"✅ Item {idx+1}: Usando protocolo: {protocolo}")

    # Linha 172-178: Extração de documento_origem
    if item_agendamento.get('itens'):
        for item in item_agendamento['itens']:
            if item.get('documento_origem'):
                documento_origem = item['documento_origem']  # ✅ EXTRAÍDO
                break

    # Linha 196-204: Montagem dos dados de retorno
    dados_retorno = {
        'protocolo': protocolo,                              # ✅ CORRETO
        'cnpj': item_agendamento.get('cnpj'),               # ✅ PRESERVADO
        'data_agendamento': item_agendamento.get('data_agendamento'),
        'data_expedicao': item_agendamento.get('data_expedicao'),
        'itens': item_agendamento.get('itens', []),         # ✅ TODOS OS ITENS
        'tipo_fluxo': tipo_fluxo,
        'documento_origem': documento_origem
    }
```

## 📍 ETAPA 8: SALVAMENTO NO BANCO
**Arquivo:** `app/portal/sendas/retorno_agendamento.py`
**Linha:** 113-143

### ATUALIZAÇÃO DAS SEPARAÇÕES:
```python
# Linha 113-122: Atualiza Separações PREVISAO → ABERTO
resultado_previsao = Separacao.query.filter_by(
    protocolo=protocolo,        # ✅ USA PROTOCOLO CORRETO
    status='PREVISAO'
).update({
    'status': 'ABERTO',         # ✅ CONFIRMA AGENDAMENTO
    'agendamento': data_agendamento,
    'expedicao': data_expedicao,
    'agendamento_confirmado': False
})

# Linha 126-136: Atualiza outras Separações
resultado_outras = Separacao.query.filter(
    Separacao.protocolo == protocolo,  # ✅ USA PROTOCOLO CORRETO
    Separacao.status != 'PREVISAO'
).update({
    'agendamento': data_agendamento,
    'expedicao': data_expedicao,
    'agendamento_confirmado': False
})

# Linha 141-143: Log de confirmação
logger.info(f"✅ FLUXO UNIFICADO - Atualizado {total_atualizado} Separações com protocolo {protocolo}")
```

---

# 🔄 FLUXO 2: CARTEIRA AGRUPADA

## 📍 ETAPA 1: ORIGEM DOS DADOS
**Arquivo:** `app/templates/carteira/js/agendamento/sendas/portal-sendas.js`
**Linha:** 38-49

### DADOS ENVIADOS DO FRONTEND:
```javascript
// Linha 38-49: Envio para adicionar na fila
const response = await fetch('/portal/sendas/fila/adicionar', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        tipo_origem: 'separacao',
        documento_origem: loteId,        // ✅ LOTE_ID
        data_expedicao: agendDate - 1,   // ✅ CALCULADO
        data_agendamento: dataAgendamento // ✅ DATA
    })
});
```

## 📍 ETAPA 2: ADIÇÃO NA FILA E GERAÇÃO DO PROTOCOLO
**Arquivo:** `app/portal/sendas/routes_fila.py`
**Linha:** 115-189

### PROCESSAMENTO E ENRIQUECIMENTO:
```python
# Linha 115-120: Busca Separações do lote
itens_sep = Separacao.query.filter_by(
    separacao_lote_id=documento_origem,  # ✅ USA LOTE_ID
    sincronizado_nf=False
).all()

# Linha 128-138: Busca pedido_cliente com fallback
pedido_cliente = buscar_pedido_cliente_com_fallback(num_pedido)  # ✅ FALLBACK ODOO

# Linha 142: GERAÇÃO DO PROTOCOLO ÚNICO PARA O LOTE
protocolo = gerar_protocolo_sendas(cnpj_lote, data_agendamento)  # ✅ PROTOCOLO ÚNICO

# Linha 147-155: ATUALIZA SEPARAÇÕES COM PROTOCOLO (ANTES DO AGENDAMENTO)
resultado_update = Separacao.query.filter_by(
    separacao_lote_id=documento_origem
).update({
    'protocolo': protocolo,        # ✅ PROTOCOLO SALVO NAS SEPARAÇÕES
    'agendamento': None,          # ✅ ZERADO (preenchido no retorno)
    'expedicao': None             # ✅ ZERADO (preenchido no retorno)
})
db.session.commit()

# Linha 178-189: Adiciona na fila passando o protocolo já gerado
fila_item = FilaAgendamentoSendas.adicionar(
    tipo_origem='separacao',
    documento_origem=documento_origem,
    cnpj=item.cnpj_cpf,
    num_pedido=item.num_pedido,
    pedido_cliente=pedido_cliente,      # ✅ COM FALLBACK
    cod_produto=item.cod_produto,
    nome_produto=nome_produto,
    quantidade=float(item.qtd_saldo),
    data_expedicao=data_exp_final,
    data_agendamento=data_agendamento,
    protocolo=protocolo                 # ✅ PROTOCOLO ÚNICO PASSADO
)
```

## 📍 ETAPA 3: PROCESSAMENTO DA FILA
**Arquivo:** `app/portal/sendas/routes_fila.py`
**Linha:** 387-447

### AGRUPAMENTO E GERAÇÃO DE PROTOCOLO:
```python
# Linha 387: Obter grupos da fila
grupos = FilaAgendamentoSendas.obter_para_processar()

# Linha 401-405: Para cada grupo
for chave, grupo in grupos.items():
    cnpj = grupo['cnpj']
    data_agendamento = grupo['data_agendamento']
    protocolo = grupo['protocolo']      # ✅ PROTOCOLO GERADO NA FILA
    itens = grupo['itens']              # ✅ TODOS OS ITENS

    # Linha 426-437: Monta estrutura de cada item
    itens_dict.append({
        'id': item.id,
        'num_pedido': item.num_pedido,
        'pedido_cliente': item.pedido_cliente,  # ✅ JÁ TEM DO ODOO
        'cod_produto': item.cod_produto,
        'nome_produto': item.nome_produto,
        'quantidade': float(item.quantidade),
        'peso': peso_item,
        'tipo_origem': item.tipo_origem,
        'documento_origem': item.documento_origem  # ✅ LOTE_ID
    })

    # Linha 441-447: Monta estrutura para processar
    dados_para_processar.append({
        'cnpj': cnpj,
        'data_agendamento': data_agendamento,
        'protocolo': protocolo,         # ✅ PROTOCOLO INCLUÍDO
        'peso_total': peso_grupo,
        'itens': itens_dict             # ✅ TODOS OS DADOS
    })
```

## 📍 ETAPA 4: ENFILEIRAMENTO
**Arquivo:** `app/portal/sendas/routes_fila.py`
**Linha:** 481-488

```python
# Linha 481-488: Enfileira para worker
job = enqueue_job(
    processar_agendamento_sendas,
    integracao.id,
    dados_para_processar,  # ✅ DADOS COMPLETOS DA FILA
    current_user.nome,
    queue_name='sendas',
    timeout='15m'
)
```

## 📍 ETAPAS 5-8: PROCESSAMENTO E RETORNO
Idênticas ao Fluxo 1 com particularidades:

### RETORNO DO FLUXO 2:
**Arquivo:** `app/portal/sendas/retorno_agendamento.py`
**Linha:** 113-143

```python
# USA PROTOCOLO JÁ SALVO NAS SEPARAÇÕES
# Atualiza Separações com status='PREVISAO' → 'ABERTO'
resultado_previsao = Separacao.query.filter_by(
    protocolo=protocolo,        # ✅ USA PROTOCOLO JÁ EXISTENTE
    status='PREVISAO'
).update({
    'status': 'ABERTO',         # ✅ CONFIRMA AGENDAMENTO
    'agendamento': data_agendamento,
    'expedicao': data_expedicao,
    'agendamento_confirmado': False
})

# Atualiza outras Separações do mesmo protocolo
resultado_outras = Separacao.query.filter(
    Separacao.protocolo == protocolo,
    Separacao.status != 'PREVISAO'
).update({
    'agendamento': data_agendamento,
    'expedicao': data_expedicao,
    'agendamento_confirmado': False
})
```

**RESUMO FLUXO 2:**
- Protocolo salvo ANTES nas Separações (linha 147-155 routes_fila.py)
- Retorno apenas atualiza datas e status

---

# 🔄 FLUXO 3: AGENDAMENTO POR NF

## 📍 ETAPA 1: ORIGEM DOS DADOS
**Arquivo:** `app/templates/monitoramento/listar_entregas.html`
**Linha:** 2666-2677

### DADOS ENVIADOS DO FRONTEND:
```javascript
// Linha 2666-2677: Envio para adicionar na fila
fetch('/portal/sendas/fila/adicionar', {
    method: 'POST',
    body: JSON.stringify({
        tipo_origem: 'nf',
        documento_origem: numeroNf,      // ✅ NÚMERO DA NF
        data_expedicao: dataExpedicao,
        data_agendamento: dataAgendamento
    })
});
```

## 📍 ETAPA 2: ADIÇÃO NA FILA
**Arquivo:** `app/portal/sendas/routes_fila.py`
**Linha:** 193-253

### BUSCA E ENRIQUECIMENTO DOS DADOS:
```python
# Linha 194-195: Busca EntregaMonitorada
entrega = EntregaMonitorada.query.filter_by(
    numero_nf=documento_origem  # ✅ USA NÚMERO DA NF
).first()

# Linha 201-211: Busca FaturamentoProduto
produtos_faturados = FaturamentoProduto.query.filter_by(
    numero_nf=documento_origem  # ✅ USA NÚMERO DA NF
).all()

# Linha 225-228: GERAR PROTOCOLO ÚNICO PARA A NF INTEIRA
cnpj_nf = produtos_faturados[0].cnpj_cliente or entrega.cnpj_cliente
protocolo_nf = gerar_protocolo_sendas(cnpj_nf, data_agendamento)  # ✅ PROTOCOLO ÚNICO
logger.info(f"📝 NF {documento_origem}: protocolo único {protocolo_nf}")

# Linha 231-253: Processar produtos com protocolo único
for produto in produtos_faturados:
    fila_item = FilaAgendamentoSendas.adicionar(
        tipo_origem='nf',
        documento_origem=documento_origem,  # ✅ NÚMERO DA NF
        cnpj=produto.cnpj_cliente,
        num_pedido=produto.origem,
        pedido_cliente=pedido_cliente,      # ✅ COM FALLBACK
        cod_produto=produto.cod_produto,
        nome_produto=produto.nome_produto,
        quantidade=float(produto.qtd_produto_faturado),
        data_expedicao=data_exp_final,
        data_agendamento=data_agendamento,
        protocolo=protocolo_nf               # ✅ MESMO PROTOCOLO PARA TODOS
    )
```

## 📍 ETAPA 3: PROCESSAMENTO E RETORNO
**Arquivo:** `app/portal/sendas/retorno_agendamento.py`
**Linha:** 153-217

### CRIAÇÃO DE REGISTRO DE AGENDAMENTO:
```python
# Linha 162: Busca EntregaMonitorada
entrega = EntregaMonitorada.query.filter_by(
    numero_nf=numero_nf  # ✅ VEIO DE documento_origem
).first()

# Linha 173-182: Cria AgendamentoEntrega
agendamento = AgendamentoEntrega(
    entrega_id=entrega.id,
    protocolo_agendamento=protocolo,  # ✅ PROTOCOLO CORRETO
    data_agendada=data_agendamento,
    forma_agendamento='Portal Sendas',
    status='aguardando'
)

# Linha 186-188: Atualiza EntregaMonitorada
entrega.data_agenda = data_agendamento
entrega.status_entrega = 'agendada'
entrega.reagendar = False
```

### FALLBACK PARA SEPARAÇÃO:
```python
# Linha 201-208: Atualiza Separações com NF
separacoes = Separacao.query.filter_by(
    numero_nf=numero_nf  # ✅ BUSCA PELA NF
).all()
for sep in separacoes:
    sep.protocolo = protocolo           # ✅ ADICIONA PROTOCOLO
    sep.agendamento = data_agendamento  # ✅ ADICIONA DATA
    sep.agendamento_confirmado = False
```

---

# ✅ PONTOS DE GARANTIA DE NÃO-PERDA DE DADOS

## 1. PROTOCOLO SEMPRE PRESENTE E ÚNICO
- **Fluxo 1:** Gerado em `routes.py:1311` antes do envio
- **Fluxo 2:** Gerado em `routes_fila.py:142` e passado para fila
- **Fluxo 3:** Gerado em `routes_fila.py:227` para NF inteira
- **Worker:** Extraído de `lista_cnpjs_agendamento[i]['protocolo']` (linha 161)

## 2. DADOS COMPLETOS PRESERVADOS
- **Worker:** Cópia completa com `dict(item)` (linha 44)
- **Callback:** Closure mantém `lista_cnpjs_agendamento` (linha 122)
- **Planilha:** Recebe lista completa (linha 615)

## 3. PROTOCOLO ÚNICO POR ENTIDADE
- **Fluxo 1:** Um protocolo por grupo CNPJ/data
- **Fluxo 2:** Um protocolo por lote de separação
- **Fluxo 3:** Um protocolo por NF (todos produtos compartilham)

## 4. IDENTIFICAÇÃO CORRETA DO TIPO DE FLUXO
- **Fluxo 1:** `tipo_fluxo='programacao_lote'` (linha routes.py:1336)
- **Fluxo 2/3:** Identificado por `documento_origem` (linha sendas_jobs.py:182-193)

## 5. DOCUMENTO_ORIGEM PRESERVADO
- **Fluxo 2:** `separacao_lote_id` em cada item
- **Fluxo 3:** `numero_nf` em cada item
- **Worker:** Extrai de `item['documento_origem']` (linha 172-178)

---

# 📊 DIAGRAMA DE RASTREABILIDADE

```
FLUXO 1: [Frontend] → [routes.py:1295-1339] → [Worker:12-77] → [Callback:122-138]
         → [Planilha:615-837] → [Upload:1340-1430] → [Worker:156-216] → [BD:113-143]

FLUXO 2: [Frontend] → [Fila:115-189] → [Processar:387-447] → [Worker:12-77]
         → [Callback:122-138] → [Planilha:615-837] → [Upload:1340-1430]
         → [Worker:156-216] → [BD:113-143]

FLUXO 3: [Frontend] → [Fila:193-253] → [Processar:387-447] → [Worker:12-77]
         → [Callback:122-138] → [Planilha:615-837] → [Upload:1340-1430]
         → [Worker:156-216] → [BD:153-217]
```

---

# 🔒 CONCLUSÃO TÉCNICA

## SISTEMA FUNCIONANDO CORRETAMENTE:

1. **PROTOCOLO ÚNICO:** Cada entidade (grupo/lote/NF) tem protocolo único
2. **DADOS COMPLETOS:** Preservados em todas as etapas através de cópias e closures
3. **RASTREABILIDADE:** Garantida pelo protocolo como chave mestre
4. **CONSISTÊNCIA:** FilaAgendamentoSendas recebe protocolo já gerado
5. **FALLBACKS:** Implementados para casos especiais (NF, pedido_cliente)

**GARANTIA:** Sistema mantém consistência total de protocolos e não perde dados em nenhuma etapa do processo.

## Contexto

Descreve a rastreabilidade de protocolo e dados no fluxo de agendamento Sendas (`app/portal/sendas/`; funcoes `gerar_protocolo_sendas` e `buscar_dados_completos_cnpj`). Doc de 2025-09 — o worker `sendas_jobs.py` citado foi substituido por processamento inline na rota (`routes_fila.py`); o modelo de rastreabilidade segue vigente.
