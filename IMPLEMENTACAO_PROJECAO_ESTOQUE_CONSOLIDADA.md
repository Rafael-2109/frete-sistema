# Implementação: Projeção de Estoque Consolidada
================================================================================

**Data**: 2025-11-03
**Objetivo**: Criar tela de projeção com layout tabular (linhas=produtos, colunas=datas+dados)

---

## 📋 RESUMO

Nova tela de projeção de estoque com estrutura similar à necessidade de produção:
- **Linhas**: Produtos (componentes comprados)
- **Colunas Fixas**: Estoque, Consumo Carteira, Saldo, Qtd Requisições, Qtd Pedidos
- **Colunas Dinâmicas**: Timeline D0-D60 com projeção diária

---

## ✅ IMPLEMENTAÇÕES REALIZADAS

### 1. **Backend - Serviço de Projeção**

**Arquivo**: `app/manufatura/services/projecao_estoque_service.py`

#### Novo Método: `projetar_componentes_consolidado()`
```python
def projetar_componentes_consolidado(self) -> Dict[str, Any]:
    """
    Projeta componentes com dados consolidados para tabela

    Retorna:
    - Colunas fixas calculadas
    - Timeline D0-D60 (array de 61 posições)
    """
```

#### Métodos Auxiliares Criados:

**`_calcular_consumo_carteira(cod_produto)`**
- Calcula consumo necessário para atender CarteiraPrincipal
- Lógica: (Saldo Carteira PA - Estoque PA) × BOM
- Considera produtos intermediários

**`_calcular_qtd_requisicoes(cod_produto)`**
- Soma requisições ativas (não rejeitadas)
- Filtro: `status_requisicao != 'rejected'`

**`_calcular_qtd_pedidos(cod_produto)`**
- Soma pedidos ativos (não cancelados)
- Filtro: `status_odoo != 'cancel'`

**`_gerar_timeline_60_dias()`**
- Gera array de 61 posições (D0 a D60)
- Retorna apenas estoque final de cada dia

---

### 2. **Backend - API Endpoint**

**Arquivo**: `app/manufatura/routes/projecao_estoque_routes.py`

**Novo Endpoint**: `GET /manufatura/projecao-estoque/api/projetar-consolidado`

**Resposta**:
```json
{
  "sucesso": true,
  "data_calculo": "2025-11-03",
  "total_componentes": 150,
  "componentes": [
    {
      "cod_produto": "102030601",
      "nome_produto": "AZEITONA VERDE RECHEADA",
      "estoque_atual": 0.00,
      "consumo_carteira": 2500.00,
      "saldo_carteira": -2500.00,
      "qtd_requisicoes": 0.00,
      "qtd_pedidos": 0.00,
      "timeline": [0.00, -2519.10, -5038.20, ...]  // 61 posições
    }
  ]
}
```

---

### 3. **Frontend - Template HTML**

**Arquivo**: `app/templates/manufatura/projecao_estoque/consolidado.html`

**Estrutura**:
- Cabeçalho com filtros e botão calcular
- Customizador de colunas (checkboxes)
- Controle de tamanho de fonte (XS/S/M/L)
- Tabela com scroll horizontal/vertical
- Colunas fixas (sticky) para código e produto

**Colunas Implementadas**:
1. Código (sticky)
2. Nome Produto (sticky)
3. Estoque Atual
4. Consumo para Carteira
5. Saldo para Carteira
6. Qtd em Requisições
7. Qtd em Pedidos
8. D0 a D60 (61 colunas dinâmicas)

---

### 4. **Frontend - CSS**

**Arquivo**: `app/static/manufatura/projecao_estoque/css/projecao-consolidado.css`

**Recursos**:
- Tabela responsiva com scroll
- Colunas fixas (sticky positioning)
- 4 tamanhos de fonte (very-small, small, medium, large)
- Cores para valores (positivo=verde, negativo=vermelho, zero=cinza)
- Estilização do customizador de colunas
- Loading overlay

**Classes Principais**:
```css
.sticky-col-codigo         /* Coluna código fixa */
.sticky-col-produto        /* Coluna produto fixa */
.col-estoque, .col-consumo /* Colunas de dados */
.col-projecao              /* Colunas D0-D60 */
.valor-positivo            /* Verde para valores > 0 */
.valor-negativo            /* Vermelho para valores < 0 */
```

---

### 5. **Frontend - JavaScript**

**Arquivo**: `app/static/manufatura/projecao_estoque/js/projecao-consolidado.js`

**Funções Principais**:

**`gerarHeadersProjecao()`**
- Gera headers D0-D60 dinamicamente
- Formato: "Dia<br>Semana"

**`calcular()`**
- Chama API `/api/projetar-consolidado`
- Renderiza tabela com dados

**`renderizarTabela(componentes)`**
- Renderiza linhas com produtos
- Aplica cores conforme valores
- Adiciona colunas timeline

**`filtrarTabela()`**
- Filtra por código ou nome do produto

**`toggleColunas()`**
- Mostra/oculta colunas selecionadas

**`mudarTamanhoFonte(tamanho)`**
- Altera classe do body para ajustar fonte

---

## 🔧 CORREÇÕES APLICADAS

### Bug de Timezone (Corrigido)
**Problema**: Datas apareciam 1 dia antes
**Causa**: `new Date('2025-11-05')` interpretava como UTC 00:00, que ao converter para GMT-3 virava 04/11
**Solução**: `new Date('2025-11-05T12:00:00')` força meio-dia

**Arquivos Corrigidos**:
- `app/templates/manufatura/projecao_estoque/index.html` (linhas 100, 150)

---

## 📊 ESTRUTURA DA TABELA FINAL

```
┌──────────┬─────────────────┬─────────┬──────────┬────────┬──────┬──────┬────┬────┬─────┐
│ Código   │ Nome Produto    │ Estoque │ Consumo  │ Saldo  │ Qtd  │ Qtd  │ D0 │ D1 │ ... │
│          │                 │ Atual   │ Carteira │ Cart.  │ Req. │ Ped. │    │    │     │
├──────────┼─────────────────┼─────────┼──────────┼────────┼──────┼──────┼────┼────┼─────┤
│ 102030601│ AZEITONA VERDE  │ 0       │ 2500     │ -2500  │ 0    │ 0    │ 0  │-25 │ ... │
│ 301000001│ EMBALAGEM VIDRO │ 1500    │ 800      │ 700    │ 500  │ 300  │700 │650 │ ... │
└──────────┴─────────────────┴─────────┴──────────┴────────┴──────┴──────┴────┴────┴─────┘
```

---

## 🚀 COMO USAR

### 1. **Acessar a Tela**
```
http://localhost:5000/manufatura/projecao-estoque/
```

### 2. **Calcular Projeção**
- Clique no botão **"Calcular"**
- Aguarde processamento (pode demorar para muitos produtos)

### 3. **Customizar Visualização**
- Use checkboxes para mostrar/ocultar colunas
- Ajuste tamanho da fonte (XS/S/M/L)
- Filtre por código ou nome do produto

### 4. **Interpretar Resultados**
- **Verde**: Valor positivo (estoque disponível)
- **Vermelho**: Valor negativo (ruptura)
- **Cinza**: Valor zero

---

## 📁 ARQUIVOS CRIADOS/MODIFICADOS

### Criados:
1. `app/templates/manufatura/projecao_estoque/consolidado.html`
2. `app/static/manufatura/projecao_estoque/css/projecao-consolidado.css`
3. `app/static/manufatura/projecao_estoque/js/projecao-consolidado.js`
4. `scripts/adicionar_status_odoo_pedidos.py`
5. `scripts/adicionar_status_odoo_pedidos.sql`

### Modificados:
1. `app/manufatura/services/projecao_estoque_service.py` (+115 linhas)
2. `app/manufatura/routes/projecao_estoque_routes.py` (+24 linhas)
3. `app/manufatura/models.py` (campo `status_odoo` em PedidoCompras)
4. `app/odoo/services/pedido_compras_service.py` (detecção cancelamento/exclusão)
5. `app/odoo/services/requisicao_compras_service.py` (detecção cancelamento/exclusão)
6. `app/odoo/services/alocacao_compras_service.py` (detecção cancelamento/exclusão)
7. `app/templates/manufatura/projecao_estoque/index.html` (correção timezone)

---

## ⚙️ CONFIGURAÇÕES

### Produtos Considerados
Apenas produtos com:
- `produto_comprado = True`
- `ativo = True`

### Filtros Aplicados
- **Requisições**: Exclui `status_requisicao = 'rejected'`
- **Pedidos**: Exclui `status_odoo = 'cancel'`
- **Projeção**: Considera até 60 dias no futuro

---

## 🔄 FLUXO DE CÁLCULO

### Consumo para Carteira:
```
1. Para cada componente:
   ├─ Buscar quais PAs (produtos acabados) o consomem
   ├─ Para cada PA:
   │  ├─ Saldo Carteira = SUM(CarteiraPrincipal.qtd_saldo_produto_pedido)
   │  ├─ Estoque PA = Estoque atual do PA
   │  ├─ Necessidade = Saldo Carteira - Estoque PA
   │  └─ Se Necessidade > 0:
   │     └─ Consumo += Necessidade × BOM.qtd_utilizada
   └─ Retornar Consumo Total
```

### Timeline D0-D60:
```
Estoque[D0] = Estoque Atual
Para cada dia D1 a D60:
   Entradas = Pedidos Compra + Requisições
   Saídas = Consumo por Programação Produção (BOM)
   Estoque[Di] = Estoque[Di-1] + Entradas - Saídas
```

---

## 🎯 MELHORIAS FUTURAS (Opcional)

1. **Performance**: Cache de cálculos pesados
2. **Export**: Exportar para Excel
3. **Alertas**: Notificações de rupturas críticas
4. **Gráficos**: Visualização gráfica da projeção
5. **Filtros Avançados**: Por tipo de matéria-prima, categoria, etc.

---

**FIM DO DOCUMENTO**
