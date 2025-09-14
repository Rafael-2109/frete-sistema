# 🔄 FLUXO SENDAS: ATUAL vs IDEAL (ANÁLISE DETALHADA)

**Data:** 2025-01-13
**Versão:** 1.0
**Objetivo:** Documentar precisamente as diferenças entre o fluxo atual e o ideal

---

## 📊 RESUMO EXECUTIVO

O sistema tem **3 portas de entrada** que convergem para **1 processo comum** e divergem para **3 portas de saída**.
Atualmente há redundâncias, gambiarras e desperdício de processamento que podem ser eliminados.

---

## 🔴 FLUXO ATUAL (COM PROBLEMAS)

### 1️⃣ FLUXO 1: PROGRAMAÇÃO-LOTE

#### ENTRADA (Frontend)
```javascript
// app/static/js/programacao-lote.js linha 1341
endpoint = '/carteira/programacao-lote/api/processar-agendamento-sendas-async'

// Envia:
{
    portal: 'sendas',
    agendamentos: [
        {
            cnpj: '06057223000xxx',
            expedicao: '2025-01-12',
            agendamento: '2025-01-13'
        }
    ]
}
```

#### PROCESSAMENTO (Backend)
```python
# app/carteira/routes/programacao_em_lote/routes.py linha 1726-1729
lista_cnpjs_agendamento.append({
    'cnpj': cnpj,
    'data_agendamento': data_agendamento
})
# ❌ NÃO envia dados completos, apenas CNPJ e data
```

#### WORKER
```python
# app/portal/workers/sendas_jobs.py linha 100-102
arquivo_processado = preenchedor.preencher_multiplos_cnpjs(
    arquivo_origem=arquivo_baixado,
    lista_cnpjs_agendamento=lista_cnpjs_agendamento  # Apenas {cnpj, data}
)
```

#### BUSCA DE DADOS
```python
# app/portal/sendas/preencher_planilha.py
# ✅ Busca de 3 fontes (linhas 208-406):
# 1. CarteiraPrincipal (linha 212-287)
# 2. Separacao com sincronizado_nf=False (linha 292-352)
# 3. Separacao com sincronizado_nf=True e nf_cd=True (linha 356-406)
```

#### RETORNO
```python
# app/carteira/routes/programacao_em_lote/routes.py linha 1451-1520
# ✅ Cria Separacao com status='PREVISAO' e salva protocolo
```

---

### 2️⃣ FLUXO 2: CARTEIRA AGRUPADA

#### ENTRADA (Frontend)
```javascript
// app/templates/carteira/js/agendamento/sendas/portal-sendas.js linha 38-49
fetch('/portal/sendas/fila/adicionar', {
    body: JSON.stringify({
        tipo_origem: 'separacao',
        documento_origem: loteId,
        data_expedicao: dataExpedicao,  // Calcula D-1
        data_agendamento: dataAgendamento
    })
})
```

#### ADICIONAR NA FILA
```python
# app/portal/sendas/routes_fila.py linha 115-173
# ✅ Busca pedido_cliente com fallback Odoo (linha 128-135)
FilaAgendamentoSendas.adicionar(
    tipo_origem='separacao',
    documento_origem=documento_origem,
    cnpj=item.cnpj_cpf,
    num_pedido=item.num_pedido,
    cod_produto=item.cod_produto,
    quantidade=float(item.qtd_saldo),
    pedido_cliente=pedido_cliente  # ✅ TEM pedido_cliente!
)
```

#### PROCESSAR FILA (PROBLEMA!)
```javascript
// ❌ ERRO: portal-sendas.js linha 187 chama endpoint ERRADO!
const response = await fetch('/carteira/programacao-lote/api/processar-agendamento-sendas-async', {
    body: JSON.stringify({
        portal: 'sendas',
        cnpjs: cnpjsParaProcessar  // ❌ Mapeamento manual, perde dados da fila
    })
})
// DEVERIA chamar: '/portal/sendas/fila/processar'
```

#### WORKER
```python
# Mesmo worker, mas recebe formato errado por causa do endpoint incorreto
# ❌ Perde todos os dados ricos preparados na fila
```

#### BUSCA DE DADOS
```python
# preencher_planilha.py
# ❌ Re-busca tudo das 3 fontes, ignorando dados da fila
```

#### RETORNO
```python
# ❌ NÃO salva protocolo na Separacao
```

---

### 3️⃣ FLUXO 3: LISTAR ENTREGAS NF

#### ENTRADA (Frontend)
```javascript
// app/templates/monitoramento/listar_entregas.html linha 2666-2677
fetch('/portal/sendas/fila/adicionar', {
    body: JSON.stringify({
        tipo_origem: 'nf',
        documento_origem: numeroNf,
        data_expedicao: dataExpedicao,
        data_agendamento: dataAgendamento
    })
})
```

#### ADICIONAR NA FILA
```python
# app/portal/sendas/routes_fila.py linha 177-289
# Valida EntregaMonitorada (linha 179-187)
entrega = EntregaMonitorada.query.filter_by(numero_nf=documento_origem).first()

# Busca de FaturamentoProduto com fallback Odoo (linha 190-229)
# ✅ Prepara dados completos com pedido_cliente
```

#### PROCESSAR FILA
```javascript
// listar_entregas.html linha 2765
fetch('/portal/sendas/fila/processar', {
    method: 'POST'
})
// ✅ CORRETO: Chama endpoint certo
```

```python
# app/portal/sendas/routes_fila.py linha 462-469
job = enqueue_job(
    processar_agendamento_sendas,
    integracao.id,
    dados_para_processar,  # ✅ Envia dados COMPLETOS com itens
    usuario_nome,
    queue_name='sendas'
)
```

#### WORKER
```python
# ❌ PROBLEMA: Worker ignora estrutura rica
# Passa apenas {cnpj, data} para preencher_planilha
```

#### BUSCA DE DADOS
```python
# ❌ preencher_planilha re-busca tudo das 3 fontes
```

#### RETORNO
```python
# ❌ NÃO salva protocolo em EntregaMonitorada/AgendamentoEntrega
# DEVERIA:
AgendamentoEntrega(
    entrega_id=entrega.id,
    data_agendada=data_agendamento,
    forma_agendamento='Portal Sendas',
    protocolo_agendamento=protocolo,  # ← AQUI!
    status='confirmado'
)
```

---

## ✅ FLUXO IDEAL (PROPOSTO)

### 🎯 PRINCÍPIOS

1. **Estrutura de dados unificada** para todos os fluxos
2. **Sem re-busca** quando dados já estão preparados
3. **Protocolo salvo** no local correto para cada fluxo
4. **Endpoints corretos** sem gambiarras

### 📦 ESTRUTURA DE DADOS UNIFICADA

```python
# TODOS os fluxos devem preparar:
dados_agendamento = {
    'cnpj': str,
    'data_agendamento': date,
    'protocolo': str,  # AGEND_xxxx_YYYYMMDD
    'peso_total': float,
    'itens': [
        {
            'id': int,  # ID do registro original (para update do protocolo)
            'tipo_origem': str,  # 'carteira', 'separacao', 'nf'
            'num_pedido': str,
            'pedido_cliente': str,  # CRÍTICO para matching
            'cod_produto': str,
            'quantidade': float,
            'peso': float,
            'data_expedicao': date
        }
    ]
}
```

### 🔄 FLUXO 1 IDEAL: PROGRAMAÇÃO-LOTE

#### MUDANÇAS NECESSÁRIAS

```python
# app/carteira/routes/programacao_em_lote/routes.py

# ATUAL (linha 1726-1729):
lista_cnpjs_agendamento.append({
    'cnpj': cnpj,
    'data_agendamento': data_agendamento
})

# IDEAL:
# Buscar dados das 3 fontes AQUI e preparar estrutura completa
dados_completos = preparar_dados_programacao_lote(cnpj, data_agendamento)
lista_cnpjs_agendamento.append(dados_completos)
```

#### VANTAGEM
- Worker recebe dados prontos
- preencher_planilha não precisa buscar

---

### 🔄 FLUXO 2 IDEAL: CARTEIRA AGRUPADA

#### MUDANÇAS NECESSÁRIAS

```javascript
// app/templates/carteira/js/agendamento/sendas/portal-sendas.js linha 187

// ATUAL (ERRADO):
const response = await fetch('/carteira/programacao-lote/api/processar-agendamento-sendas-async', {
    body: JSON.stringify({
        portal: 'sendas',
        cnpjs: cnpjsParaProcessar  // Mapeamento manual
    })
})

// IDEAL:
const response = await fetch('/portal/sendas/fila/processar', {
    method: 'POST'
    // Sem body - processa fila acumulada
})
```

#### RETORNO IDEAL

```python
# Após sucesso do upload:
for item_id in processados:
    Separacao.query.filter_by(id=item_id).update({
        'protocolo': protocolo_gerado
    })
db.session.commit()
```

---

### 🔄 FLUXO 3 IDEAL: LISTAR ENTREGAS NF

#### JÁ ESTÁ QUASE CORRETO!

#### MUDANÇA NECESSÁRIA - RETORNO

```python
# Após sucesso do upload:

# 1. Criar AgendamentoEntrega
agendamento = AgendamentoEntrega(
    entrega_id=entrega.id,
    data_agendada=data_agendamento,
    forma_agendamento='Portal Sendas',
    protocolo_agendamento=protocolo,  # ← SALVAR PROTOCOLO!
    status='confirmado',
    autor='Sistema'
)
db.session.add(agendamento)

# 2. Atualizar EntregaMonitorada
entrega.data_agenda = data_agendamento
entrega.reagendar = False

db.session.commit()
```

---

## 📋 WORKER IDEAL

```python
# app/portal/workers/sendas_jobs.py

def processar_agendamento_sendas(integracao_id, lista_cnpjs_agendamento, usuario_nome=None):

    # DETECTAR formato dos dados
    if isinstance(lista_cnpjs_agendamento[0], dict) and 'itens' in lista_cnpjs_agendamento[0]:
        # ✅ Dados completos - passar direto
        dados_para_planilha = lista_cnpjs_agendamento
        usar_dados_fornecidos = True
    else:
        # ❌ Formato legado - manter compatibilidade
        dados_para_planilha = lista_cnpjs_agendamento
        usar_dados_fornecidos = False

    # Callback modificado
    def processar_planilha_callback(arquivo_baixado):
        arquivo_processado = preenchedor.preencher_multiplos_cnpjs(
            arquivo_origem=arquivo_baixado,
            lista_cnpjs_agendamento=dados_para_planilha,
            usar_dados_fornecidos=usar_dados_fornecidos  # ← NOVO PARÂMETRO
        )
        return arquivo_processado
```

---

## 📋 PREENCHER_PLANILHA IDEAL

```python
# app/portal/sendas/preencher_planilha.py

def preencher_multiplos_cnpjs(self, arquivo_origem, lista_cnpjs_agendamento,
                              arquivo_destino=None, usar_dados_fornecidos=False):

    if usar_dados_fornecidos and 'itens' in lista_cnpjs_agendamento[0]:
        # ✅ USAR dados fornecidos
        logger.info("✅ Usando dados PRÉ-PROCESSADOS")
        todos_dados = {}
        for grupo in lista_cnpjs_agendamento:
            cnpj = grupo['cnpj']
            todos_dados[cnpj] = {
                'cnpj': cnpj,
                'itens': grupo['itens'],
                'peso_total': grupo.get('peso_total', 0),
                'protocolo': grupo.get('protocolo')
            }
    else:
        # ❌ Buscar das 3 fontes (compatibilidade)
        logger.info("📋 Buscando dados das 3 fontes")
        todos_dados = self._buscar_todas_fontes(lista_cnpjs_agendamento)
```

---

## 📊 TABELA COMPARATIVA

| Aspecto | FLUXO ATUAL | FLUXO IDEAL |
|---------|------------|------------|
| **Estrutura de dados** | Inconsistente (simples vs completa) | Unificada para todos |
| **Busca pedido_cliente** | Re-busca sempre | Usa dados preparados |
| **Fluxo 2 endpoint** | ❌ Errado (programacao-lote) | ✅ Correto (fila/processar) |
| **Salvamento protocolo** | ❌ Só Fluxo 1 | ✅ Todos os fluxos |
| **Retorno Fluxo 3** | ❌ Não atualiza EntregaMonitorada | ✅ Cria AgendamentoEntrega |
| **Performance** | 3x busca no banco | 1x busca (quando necessário) |

---

## 🎯 BENEFÍCIOS DO FLUXO IDEAL

1. **Performance**: Elimina re-busca desnecessária
2. **Rastreabilidade**: Protocolo salvo em todos os fluxos
3. **Manutenibilidade**: Código limpo sem gambiarras
4. **Consistência**: Estrutura de dados unificada
5. **Correção**: Fluxo 3 atualiza tabelas corretas

---

## 📝 EVIDÊNCIAS DO CÓDIGO

### EVIDÊNCIA 1: Fluxo 2 chama endpoint errado
```javascript
// app/templates/carteira/js/agendamento/sendas/portal-sendas.js linha 187
const response = await fetch('/carteira/programacao-lote/api/processar-agendamento-sendas-async',
```

### EVIDÊNCIA 2: Worker ignora dados completos
```python
# app/portal/workers/sendas_jobs.py linha 100-102
# Passa lista_cnpjs_agendamento direto, sem verificar formato
arquivo_processado = preenchedor.preencher_multiplos_cnpjs(
    arquivo_origem=arquivo_baixado,
    lista_cnpjs_agendamento=lista_cnpjs_agendamento
)
```

### EVIDÊNCIA 3: preencher_planilha sempre busca
```python
# app/portal/sendas/preencher_planilha.py linha 208-406
# SEMPRE busca das 3 fontes, ignorando se recebeu dados
```

### EVIDÊNCIA 4: Protocolo não é salvo (Fluxos 2 e 3)
```python
# Nenhum código atualiza Separacao.protocolo ou AgendamentoEntrega.protocolo_agendamento
# após sucesso do upload
```

### EVIDÊNCIA 5: EntregaMonitorada tem campos para agendamento
```python
# app/monitoramento/models.py
# EntregaMonitorada linha 28:
data_agenda = db.Column(db.Date, nullable=True)

# AgendamentoEntrega linha 89:
protocolo_agendamento = db.Column(db.String(100))
```

---

## 🚀 IMPLEMENTAÇÃO RECOMENDADA

### PRIORIDADE 1: Corrigir Fluxo 2
- Mudar endpoint em `portal-sendas.js` linha 187
- Impacto: Alto (fluxo mais usado)
- Complexidade: Baixa (1 linha)

### PRIORIDADE 2: Worker detectar formato
- Adicionar detecção em `sendas_jobs.py`
- Impacto: Alto (habilita uso de dados preparados)
- Complexidade: Média

### PRIORIDADE 3: preencher_planilha usar dados fornecidos
- Adicionar condicional em `preencher_planilha.py`
- Impacto: Alto (elimina re-busca)
- Complexidade: Média

### PRIORIDADE 4: Salvar protocolo no retorno
- Adicionar update após sucesso
- Impacto: Médio (rastreabilidade)
- Complexidade: Baixa

---

## 📋 CONCLUSÃO

O sistema atual funciona mas com **desperdício significativo** de processamento e **falta de rastreabilidade**.
As mudanças propostas são **cirúrgicas** e **retrocompatíveis**, eliminando gambiarras e redundâncias.