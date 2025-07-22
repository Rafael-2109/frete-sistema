# 🧹 ANÁLISE DE LIMPEZA - CARTEIRA (listar_agrupados.html + routes.py)

**Data**: 22/07/2025  
**Objetivo**: Identificar funções não utilizadas, duplicadas e oportunidades de limpeza

---

## 📊 MAPEAMENTO COMPLETO

### 🔵 ROTAS UTILIZADAS NO TEMPLATE

| Rota | Tipo | Usado em | Linha |
|------|------|----------|-------|
| `/carteira/` | GET | Link botão | 19 |
| `/carteira/principal` | GET | Link botão | 22 |
| `/carteira/agrupados` | GET | Página atual | - |
| `/carteira/item/{num_pedido}/endereco` | GET | fetch() | 4344 |
| `/carteira/item/{item_id}/agendamento` | POST | fetch() | 2695 |
| `/carteira/api/pedido/{num}/itens` | GET | fetch() | 2546, 2668 |
| `/carteira/api/pedido/{num}/itens-editaveis` | GET | fetch() | 1105, 3876, 4023, 4407 |
| `/carteira/api/pedido/{num}/separacoes` | GET | fetch() | 1782, 3498, 5458 |
| `/carteira/api/pedido/{num}/estoque-d0-d7` | GET | fetch() | 2768, 3247 |
| `/carteira/api/pedido/{num}/estoque-projetado-28-dias` | GET | fetch() | 2335 |
| `/carteira/api/pedido/{num}/salvar-avaliacoes` | POST | fetch() | 3123 |
| `/carteira/api/pedido/{num}/criar-separacao` | POST | fetch() | 1521, 3973, 4813 |
| `/carteira/api/pedido/{num}/criar-pre-separacao` | POST | fetch() | 1644, 5001, 5647 |
| `/carteira/api/pedido/{num}/pre-separacoes-agrupadas` | GET | fetch() | 4024 |
| `/carteira/api/pedido/{num}/agendamento-existente` | GET | fetch() | 2547 |
| `/carteira/api/produto/{cod}/estoque-d0-d7` | GET | fetch() | 5274 |
| `/carteira/api/item/{id}/recalcular-estoques` | POST | fetch() | 1415, 4645 |
| `/carteira/api/item/{id}/salvar-alteracao` | POST | fetch() | 4855 |
| `/carteira/api/separacao/{id}/detalhes` | GET | fetch() | 3570, 3638 |
| `/carteira/api/separacao/{id}/editar` | POST | fetch() | 3715 |
| `/carteira/api/separacao/criar` | POST | fetch() | 5575 |
| `/carteira/api/pre-separacao/{id}/editar` | POST | fetch() | 5042, 5777 |
| `/carteira/api/pre-separacao/{id}/cancelar` | POST | fetch() | 1700, 5116 |
| `/carteira/api/pre-separacao/{id}/enviar-separacao` | POST | fetch() | 5160 |
| `/carteira/api/agrupamentos/enviar-separacao` | POST | fetch() | 4278 |
| `/carteira/api/export-excel/estoque-analise/{num}` | GET | fetch() | 2907 |
| `/carteira/api/export-excel/produto-detalhes/{cod}` | GET | fetch() | 2944 |
| `/carteira/api/export-excel/estoque-dados/{num}` | GET | fetch() | 3426 |

---

## 🔴 ROTAS NÃO UTILIZADAS NO TEMPLATE

| Rota | Tipo | Função | Motivo |
|------|------|---------|--------|
| `/carteira/item/<int:item_id>/endereco` | GET | `buscar_endereco_item()` | **DUPLICADA** - Usa versão com num_pedido |
| `/carteira/item/<int:item_id>/agendamento` | GET | `agendamento_item()` GET | Só POST é usado |
| `/carteira/api/item/<int:id>` | GET | `api_item_detalhes()` | **NÃO USADO** |
| `/carteira/api/pedido/{num}/estoque-d0-d7` | GET | `api_estoque_pedido_d0_d7()` | **DUPLICADA** com `api_estoque_d0_d7_pedido()` |
| `/carteira/api/item/{id}/dividir-linha` | POST | `api_dividir_linha_item()` | **NÃO USADO** - Divisão feita via pré-separação |

---

## 🟡 FUNÇÕES JAVASCRIPT NÃO IMPLEMENTADAS/QUEBRADAS

| Função | Status | Ação Recomendada |
|--------|--------|------------------|
| `criarNovaSeparacao()` | Existe mas não mapeada | Documentar ou remover |
| `salvarEdicaoPreSeparacao()` | Existe mas não mapeada | Documentar ou remover |
| `verDetalhesEstoque()` | Chamada no botão | Implementar ou remover botão |
| `/carteira/api/pre-separacao/{id}` GET | Usado em fetch() linha 5687 | **CRIAR ROTA** |

---

## 🔄 DUPLICAÇÕES IDENTIFICADAS

### 1. **Rotas de Endereço**
- `/carteira/item/<int:item_id>/endereco` - Por item_id
- `/carteira/item/<num_pedido>/endereco` - Por num_pedido  
**Ação**: Manter apenas por num_pedido

### 2. **Rotas de Estoque D0/D7**
- `api_estoque_d0_d7_pedido()` - linha 1203
- `api_estoque_pedido_d0_d7()` - linha 1456  
**Ação**: Remover `api_estoque_pedido_d0_d7()`

### 3. **Funções de Recálculo de Estoque (JS)**
- `recalcularEstoquesBaseadoD0Dropdown()`
- `recalcularEstoquesBaseadoD0()`  
**Ação**: Unificar usando service layer

---

## 🧹 PLANO DE LIMPEZA RECOMENDADO

### Fase 1 - Remover Rotas Não Utilizadas
```python
# REMOVER:
- @carteira_bp.route('/item/<int:item_id>/endereco')  # linha 347
- @carteira_bp.route('/api/item/<int:id>')             # linha 512
- @carteira_bp.route('/api/pedido/<num_pedido>/estoque-d0-d7')  # linha 1456 (segunda ocorrência)
- @carteira_bp.route('/api/item/<item_id>/dividir-linha')  # linha 3961
```

### Fase 2 - Criar Rotas Faltantes
```python
# CRIAR:
@carteira_bp.route('/api/pre-separacao/<int:pre_sep_id>')
@login_required
def api_pre_separacao_detalhes(pre_sep_id):
    """Obter detalhes de uma pré-separação"""
```

### Fase 3 - Implementar Funções JS Faltantes
```javascript
// IMPLEMENTAR ou REMOVER:
- verDetalhesEstoque()
- Documentar criarNovaSeparacao()
- Documentar salvarEdicaoPreSeparacao()
```

### Fase 4 - Unificar Duplicações
```javascript
// Usar CarteiraService para unificar:
- Funções de toggle
- Funções de recálculo
- Funções de carregamento
```

---

## 📈 MÉTRICAS DE LIMPEZA

- **Total de Rotas**: 31
- **Rotas Não Utilizadas**: 5 (16%)
- **Rotas Duplicadas**: 2 (6%)
- **Funções JS Quebradas**: 3
- **Potencial de Redução**: ~20% do código

---

## ⚠️ RISCOS

1. **Verificar dependências** antes de remover rotas
2. **Testar** após cada remoção
3. **Backup** do código atual
4. **Documentar** mudanças

---

## ✅ BENEFÍCIOS ESPERADOS

1. **Código mais limpo** e manutenível
2. **Menos confusão** sobre qual rota usar
3. **Performance** melhorada (menos código)
4. **Facilita** futuras implementações

---

**PRÓXIMO PASSO**: Aprovar plano e executar limpeza fase por fase.