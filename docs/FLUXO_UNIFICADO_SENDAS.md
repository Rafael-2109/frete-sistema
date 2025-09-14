# 🎯 FLUXO UNIFICADO DE AGENDAMENTO SENDAS

**Data:** 2025-01-13
**Versão:** 1.0
**Objetivo:** Documentar o fluxo REAL unificado, eliminando gambiarras

---

## 📊 VISÃO CONCEITUAL

```
ENTRADA (3 origens) → AFUNILAMENTO → PROCESSAMENTO ÚNICO → EXPANSÃO → RETORNO (3 destinos)
```

---

## 1️⃣ FASE DE ENTRADA (DIVERGENTE)

### FLUXO 1: Programação-Lote
```
Origem: Interface de programação em lote - app/templates/carteira/programacao_em_lote.html
Seleção: Múltiplos CNPJs (com UF=SP)
Fontes de dados (3 camadas):
  1. CarteiraPrincipal (ativo=True)
  2. Separacao (sincronizado_nf=True, nf_cd=True - NFs voltaram ao CD)
Acumulação:
Sendas - NÃO (já é lote)
Atacadão - NÃO (Agendamento realizado unitario)
```

### FLUXO 2: Carteira Agrupada
```
Origem: Interface carteira agrupada app/templates/carteira/agrupados_balanceado.html
Seleção: Um separacao_lote_id
Fonte de dados: Separacao (sincronizado_nf=False)
Acumulação: 
Sendas - SIM (FilaAgendamentoSendas)
Atacadão - NÃO (Agendamento realizado unitario)
```

### FLUXO 3: Listar Entregas
```
Origem: Interface monitoramento app/templates/monitoramento/listar_entregas.html
Seleção: Uma numero_nf
Fonte de dados: FaturamentoProduto → Separacao
Acumulação: 
Sendas - SIM (FilaAgendamentoSendas)
Atacadão - NÃO (Agendamento realizado unitario)

```

---

## 2️⃣ PREPARAÇÃO DE DADOS (PADRONIZAÇÃO)

### 📦 ESTRUTURA DE DADOS UNIFICADA

**Independente da origem, TODOS devem preparar:**

```python
dados_agendamento = {
    'cnpj': str,              # Para mapear filial Sendas
    'data_agendamento': date, # Data do agendamento
    'protocolo': str,         # AGEND_xxxx_YYYYMMDD
    'itens': [
        {
            'num_pedido': str,
            'pedido_cliente': str,    # CRÍTICO! Para matching na planilha
            'cod_produto': str,       # Código interno
            'quantidade': float,
            'peso': float,            # Para tipo_caminhao
            'data_expedicao': date    # D-1 para SP
        }
    ]
}
```

### REGRAS DE PREPARAÇÃO:

1. **pedido_cliente:**
   - Fluxo 1: Buscar de CarteiraPrincipal + Separacao (3 fontes)
   - Fluxo 2/3: Buscar de Separacao/FaturamentoProduto com fallback Odoo

2. **data_expedicao para SP:**
   - Se UF='SP' e não informada: calcular D-1 útil do agendamento

3. **protocolo:**
   - Formato: `AGEND_{cnpj[-4:]}_{data_agendamento.strftime('%Y%m%d')}`

---

## 3️⃣ PONTO DE AFUNILAMENTO

### 🎯 WORKER ÚNICO: `processar_agendamento_sendas`

**Recebe estrutura unificada e:**

1. **Detecta formato dos dados:**
```python
if 'itens' in lista_cnpjs_agendamento[0]:
    # Dados completos - usar direto
    usar_dados_fornecidos = True
else:
    # Formato legado - buscar do banco
    usar_dados_fornecidos = False
```

2. **Chama módulos padrão:**
   - `consumir_agendas.py`: Navega no portal Sendas
   - `preencher_planilha.py`: Preenche Excel

---

## 4️⃣ PROCESSAMENTO COMUM

### NAVEGAÇÃO NO PORTAL (`consumir_agendas.py`)
1. Login no portal Sendas
2. Download da planilha em branco
3. Callback para preenchimento
4. Upload da planilha preenchida

### PREENCHIMENTO DA PLANILHA (`preencher_planilha.py`)

**MATCHING (linha ~564):**
```python
# Busca na planilha Excel:
pedido_cliente_excel = ws.cell(row=row, column=7).value  # Coluna G
codigo_produto_sendas = ws.cell(row=row, column=8).value # Coluna H

# Compara com nossos dados:
if pedido_cliente == pedido_cliente_excel and
   codigo_nosso == DE_PARA[codigo_produto_sendas]:
    # MATCH! Preenche linha
```

**PREENCHIMENTO:**
- Coluna A: Demanda ID
- Coluna Q: Quantidade
- Coluna R: Data agendamento
- Coluna U: 'Paletizada'
- Coluna V: Tipo caminhão (baseado no peso)
- Coluna X: Protocolo único

---

## 5️⃣ PONTO DE EXPANSÃO (RETORNO)

### 📤 SALVAMENTO DO PROTOCOLO

**Por tipo de origem:**

```python
# FLUXO 1: Atualizar Separacao criada
if tipo_origem == 'programacao_lote':
    Separacao.query.filter_by(
        separacao_lote_id=lote_id,
        status='PREVISAO'
    ).update({'protocolo': protocolo})

# FLUXO 2: Atualizar Separacao existente
elif tipo_origem == 'separacao':
    Separacao.query.filter_by(
        separacao_lote_id=documento_origem
    ).update({'protocolo': protocolo})

# FLUXO 3: Atualizar por NF
elif tipo_origem == 'nf':
    # Tentar FaturamentoProduto primeiro
    FaturamentoProduto.query.filter_by(
        numero_nf=documento_origem
    ).update({'observacoes': protocolo})

    # Ou Separacao se existir
    Separacao.query.filter_by(
        numero_nf=documento_origem
    ).update({'protocolo': protocolo})
```

---

## 6️⃣ PROBLEMAS ATUAIS

### 🔴 PRINCIPAIS ISSUES:

1. **Fluxo 2 chama endpoint errado:**
   - Atual: `/carteira/programacao-lote/api/processar-agendamento-sendas-async`
   - Correto: `/portal/sendas/fila/processar`

2. **Worker ignora dados ricos:**
   - Recebe estrutura completa mas passa formato simples para preencher_planilha

3. **Protocolo não é salvo no retorno:**
   - Nenhum fluxo está atualizando o protocolo após sucesso

4. **Re-busca desnecessária:**
   - preencher_planilha busca tudo do banco mesmo recebendo dados

---

## 7️⃣ FLUXO IDEAL PROPOSTO

### ARQUITETURA LIMPA:

```
                    ┌─────────────────┐
                    │ ENTRADA (3 tipos)│
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ PREPARAÇÃO      │
                    │ (Estrutura única)│
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ FILA OPCIONAL   │
                    │ (Acumulação)    │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ WORKER ÚNICO    │
                    │ (Processamento) │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ PORTAL SENDAS   │
                    │ (Upload Excel)  │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ RETORNO         │
                    │ (Salva protocolo)│
                    └─────────────────┘
```

### ENDPOINTS CORRETOS:

1. **Programação-Lote:**
   - Endpoint próprio: `/carteira/programacao-lote/api/processar-agendamento-sendas-async`
   - Envia direto para worker

2. **Carteira/NF com Fila:**
   - Adicionar: `/portal/sendas/fila/adicionar`
   - Processar: `/portal/sendas/fila/processar`
   - Envia dados acumulados para worker

### VANTAGENS:

1. **Elimina duplicação:** Um único formato de dados
2. **Aproveita preparação:** Não re-busca o que já tem
3. **Rastreabilidade:** Protocolo salvo em todos os fluxos
4. **Manutenibilidade:** Código limpo sem gambiarras

---

## 8️⃣ OBSERVAÇÕES IMPORTANTES

### 📊 Sobre as 3 Fontes de Dados (Fluxo 1)

O `preencher_planilha.py` sempre busca nas 3 fontes para garantir cobertura completa:

1. **CarteiraPrincipal**: Pedidos em aberto (saldo)
2. **Separacao não faturada**: Itens já separados aguardando NF
3. **NFs no CD**: Notas que retornaram ao centro de distribuição

Isso garante que TODOS os itens disponíveis para agendamento sejam considerados, independente do status no fluxo logístico.

---

## 9️⃣ IMPLEMENTAÇÃO NECESSÁRIA

### PASSO 1: Corrigir Fluxo 2
```javascript
// portal-sendas.js linha 187
// Mudar para: '/portal/sendas/fila/processar'
```

### PASSO 2: Worker detectar formato
```python
# sendas_jobs.py
if isinstance(lista_cnpjs_agendamento[0], dict) and 'itens' in lista_cnpjs_agendamento[0]:
    # Passar dados completos para preencher_planilha
```

### PASSO 3: preencher_planilha usar dados fornecidos
```python
# preencher_planilha.py
if 'itens' in lista_cnpjs_agendamento[0]:
    # Usar dados fornecidos, não buscar do banco
```

### PASSO 4: Salvar protocolo no retorno
```python
# Após sucesso do upload, atualizar registros com protocolo
```

---

## 📝 CONCLUSÃO

O sistema tem **UM processo de agendamento** com:
- **3 portas de entrada** (origens diferentes)
- **1 processamento comum** (worker + portal)
- **3 portas de saída** (retorno aos originadores)

A complexidade atual vem de gambiarras de compatibilidade que podem ser eliminadas com uma estrutura de dados unificada.