# 🚀 Melhorias em Requisições de Compras

**Data**: 05/11/2025
**Objetivo**: Melhorar vínculo Requisição-Pedido, exibir projeção de estoque e mostrar data de necessidade

---

## 📋 RESUMO DAS ALTERAÇÕES

### 1️⃣ **Correção do Campo `data_necessidade`**

#### ❌ Problema Identificado
- O campo `date_required` do Odoo era lido mas **NÃO era salvo**
- Apenas o `lead_time_requisicao` (calculado) era armazenado
- **3490 requisições** no banco com `data_necessidade = NULL`

#### ✅ Solução Implementada
**Arquivo**: [`app/odoo/services/requisicao_compras_service.py`](app/odoo/services/requisicao_compras_service.py)

```python
# ✅ Linhas 525-533: Extrair e salvar data_necessidade
data_necessidade = None
lead_time_requisicao = None
if linha_odoo.get('date_required'):
    data_necessidade = datetime.strptime(linha_odoo['date_required'], '%Y-%m-%d').date()

    if data_requisicao_solicitada:
        lead_time_requisicao = (data_necessidade - data_requisicao_solicitada).days

# Linha 547: Salvar no modelo
data_necessidade=data_necessidade,  # ✅ ADICIONADO
```

**Impacto**: Nas próximas sincronizações, todas as requisições terão `data_necessidade` preenchida.

---

### 2️⃣ **Serviço de Projeção de Estoque para Requisições**

#### ✅ Novo Método: `projetar_requisicao()`
**Arquivo**: [`app/manufatura/services/projecao_estoque_service.py`](app/manufatura/services/projecao_estoque_service.py:204)

**Funcionalidades**:
- Projeta estoque **-D7 a +D7** centrado na `data_necessidade`
- Calcula entradas (pedidos + requisições pendentes)
- Calcula saídas via **BOM recursiva** (suporta produtos intermediários)
- Busca **pedidos vinculados** via `RequisicaoCompraAlocacao`
- Lista **produtos programados que consomem o componente**
- Expande **hierarquia de intermediários** (ex: ACIDO → SALMOURA → AZEITONA)

**Retorno**:
```json
{
  "sucesso": true,
  "requisicao": { "num_requisicao", "cod_produto", "qtd_requisitada", ... },
  "estoque_atual": 1500.00,
  "data_centro": "2025-11-10",
  "projecao_diaria": [
    {
      "data": "2025-11-03",
      "estoque_inicial": 1500.00,
      "entradas": 500.00,
      "saidas": 200.00,
      "estoque_final": 1800.00
    },
    // ... -D7 a +D7
  ],
  "pedidos_vinculados": [
    {
      "num_pedido": "C2511667",
      "fornecedor": "VPS IMPORTAÇÃO",
      "qtd_alocada": 8820.00,
      "qtd_aberta": 0.00,
      "percentual_atendido": 100,
      "status": "purchase"
    }
  ],
  "produtos_consumidores": [
    {
      "cod_produto_programado": "10101005",
      "nome_produto_programado": "AZEITONA VERDE 180 G",
      "qtd_programada": 5000.00,
      "via_intermediario": "20103015",
      "nome_intermediario": "SALMOURA",
      "caminho_hierarquia": ["SALMOURA", "AZEITONA VERDE 180 G"],
      "qtd_consumo_previsto": 234.50
    }
  ]
}
```

---

### 3️⃣ **API de Projeção**

#### ✅ Nova Rota
**Arquivo**: [`app/manufatura/routes/requisicao_compras_routes.py`](app/manufatura/routes/requisicao_compras_routes.py:276)

**Endpoint**:
```
GET /manufatura/api/requisicoes-compras/<requisicao_id>/projecao
```

**Uso**: Chamada AJAX para carregar projeção na interface.

---

### 4️⃣ **Interface: Lista com Projeção Expansível**

#### ✅ Template Atualizado
**Arquivo**: [`app/templates/manufatura/requisicoes_compras/listar.html`](app/templates/manufatura/requisicoes_compras/listar.html)

**Mudanças**:
1. **Nova coluna**: `Data Necessidade` (linha 122)
2. **Botão de expansão** (linha 131-137)
3. **Linha expansível** com projeção (linha 190-210)

**Visual**:
```
┌──────────────────────────────────────────────────────────────────┐
│ [>] REQ/FB/06611 | COGUMELO | 10/30/2025 | 11/05/2025 | [Olho] │
├──────────────────────────────────────────────────────────────────┤
│ [v] Projeção Expandida:                                          │
│     ┌─────────────────────────────────────────────┐              │
│     │ Estoque: 1500 | Entradas: 500 | Saídas: 200│              │
│     ├─────────────────────────────────────────────┤              │
│     │ Data     | Est.Inic | Entradas | Saídas    │              │
│     │ 03/11/25 | 1500     | +500     | -200      │              │
│     │ 04/11/25 | 1800     | 0        | -100      │              │
│     │ [D-7 a D+7 da data_necessidade]            │              │
│     └─────────────────────────────────────────────┘              │
│                                                                  │
│     📦 Pedidos Vinculados:                                       │
│     C2511667 | VPS IMPORT | 8820 alocado | Status: purchase     │
│                                                                  │
│     🏭 Produtos Programados que Consomem:                        │
│     AZEITONA VERDE 180 G | 5000 programado | via SALMOURA       │
└──────────────────────────────────────────────────────────────────┘
```

---

### 5️⃣ **JavaScript Interativo**

#### ✅ Script Atualizado
**Arquivo**: [`app/static/manufatura/requisicoes_compras/js/requisicoes-compras.js`](app/static/manufatura/requisicoes_compras/js/requisicoes-compras.js)

**Funções Principais**:
- `inicializarProjecaoToggle()` (linha 62): Configura botões de expansão
- `carregarProjecao()` (linha 99): Carrega via AJAX
- `renderizarProjecao()` (linha 135): Renderiza cards e tabelas
- `renderizarPedidosVinculados()` (linha 226): Mostra pedidos vinculados
- `renderizarProdutosConsumidores()` (linha 278): Mostra produtos com intermediários expandidos

**Destaque - Hierarquia de Intermediários**:
```javascript
// Linha 314-316: Exibe caminho completo
${prod.caminho_hierarquia.join(' → ')}
// Ex: "ACIDO CITRICO → SALMOURA → AZEITONA VERDE 180 G"
```

---

## 🔗 VÍNCULO REQUISIÇÃO-PEDIDO

### ✅ Dados Disponíveis (Tabela `requisicao_compra_alocacao`)

**Relacionamento**: `N:N` entre Requisições e Pedidos

**Campos Úteis**:
- `requisicao_compra_id` → FK para `RequisicaoCompras`
- `pedido_compra_id` → FK para `PedidoCompras`
- `qtd_alocada`: Quantidade já atendida
- `qtd_aberta`: Saldo pendente
- `qtd_requisitada`: Quantidade original solicitada
- `purchase_state`: Status do pedido (purchase, done, cancel)

**Exemplo de Uso** (linha 247-263 do serviço):
```python
alocacoes = RequisicaoCompraAlocacao.query.filter_by(
    requisicao_compra_id=requisicao.id
).all()

for alocacao in alocacoes:
    if alocacao.pedido:
        pedidos_vinculados.append({
            'num_pedido': alocacao.pedido.num_pedido,
            'fornecedor': alocacao.pedido.raz_social,
            'qtd_alocada': float(alocacao.qtd_alocada),
            'percentual_atendido': alocacao.percentual_alocado(),
            'status': alocacao.purchase_state
        })
```

### 📊 Estatísticas Atuais do Banco
```sql
Total Alocações: 2997
Requisições com Alocação: 2954
Pedidos Vinculados: 131
Alocações com Pedido: 131
```

---

## 🎨 FEATURES VISUAIS

### Cards de Resumo
```html
┌────────────────┬────────────────┬────────────────┬────────────────┐
│ Estoque Atual  │ Total Entradas │ Total Saídas   │ Pedidos Vinc.  │
│ 1500.00        │ 500.00         │ 200.00         │ 2              │
└────────────────┴────────────────┴────────────────┴────────────────┘
```

### Tabela de Projeção
- **Destaque da Data Necessidade**: Linha em azul + badge "Data Necessidade"
- **Rupturas**: Linhas em vermelho quando estoque < 0
- **Movimentações**: Verde (+) para entradas, Vermelho (-) para saídas

### Pedidos Vinculados
- Badge verde para status "purchase"
- Percentual de atendimento
- Data de previsão de entrega

### Produtos Consumidores
- Badge "Intermediário" quando aplicável
- Caminho hierárquico expandido (ex: "SALMOURA → AZEITONA")
- Consumo previsto em destaque

---

## 🧪 TESTAR

### 1. **Sincronizar Requisições**
```
/manufatura/requisicoes-compras/sincronizar-manual
```
- Escolher período (ex: últimos 7 dias)
- Verificar se `data_necessidade` foi preenchida

### 2. **Visualizar Lista**
```
/manufatura/requisicoes-compras
```
- Verificar coluna "Data Necessidade"
- Clicar no botão `[>]` para expandir projeção

### 3. **Verificar Projeção**
- Deve carregar automaticamente via AJAX
- Exibir estoque atual, entradas, saídas
- Mostrar pedidos vinculados (se houver)
- Listar produtos programados que consomem

### 4. **Testar com Produto Intermediário**
- Escolher requisição de componente usado em SALMOURA, MOLHO, etc.
- Verificar se exibe caminho hierárquico completo

---

## 📝 PRÓXIMOS PASSOS (FUTURO)

### 🔜 Página de Detalhes
- Implementar aba "Projeção Completa" (60 dias)
- Gráfico visual de estoque projetado
- Timeline interativa

### 🔜 Filtros Avançados
- Filtrar por "Com Ruptura"
- Filtrar por "Data Necessidade Próxima"

### 🔜 Alertas
- Notificações de requisições com ruptura prevista
- Dashboard com métricas agregadas

---

## 🎯 BENEFÍCIOS

✅ **Visibilidade**: Data de necessidade sempre visível
✅ **Proatividade**: Projeção antecipa rupturas
✅ **Rastreabilidade**: Vínculo claro Requisição → Pedido
✅ **Transparência**: Hierarquia de BOM expandida
✅ **Performance**: Carregamento lazy via AJAX
✅ **UX**: Expansão/colapso sem reload da página

---

## 🔧 ARQUIVOS MODIFICADOS

1. [`app/odoo/services/requisicao_compras_service.py`](app/odoo/services/requisicao_compras_service.py)
2. [`app/manufatura/services/projecao_estoque_service.py`](app/manufatura/services/projecao_estoque_service.py)
3. [`app/manufatura/routes/requisicao_compras_routes.py`](app/manufatura/routes/requisicao_compras_routes.py)
4. [`app/templates/manufatura/requisicoes_compras/listar.html`](app/templates/manufatura/requisicoes_compras/listar.html)
5. [`app/static/manufatura/requisicoes_compras/js/requisicoes-compras.js`](app/static/manufatura/requisicoes_compras/js/requisicoes-compras.js)

---

**Documentação gerada automaticamente - Precision Mode ✅**
