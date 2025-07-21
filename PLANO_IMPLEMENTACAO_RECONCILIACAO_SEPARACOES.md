# 🎯 **PLANO DE IMPLEMENTAÇÃO - RECONCILIAÇÃO DE SEPARAÇÕES**

## **🚨 PROBLEMA CRÍTICO IDENTIFICADO**

O sistema **NÃO implementa** o item **3-C** do `processo_atual.md`:

> **"Atualizar as Separações em caso de alteração no pedido decorrente da importação do Odoo"**

### **⚠️ SITUAÇÃO ATUAL:**
```python
# app/odoo/services/carteira_service.py - linha 830
db.session.query(CarteiraPrincipal).delete()  # 💥 DELETE ALL
# ... INSERT novos dados ...
# ❌ ZERO tratamento de Separações/PreSeparações existentes
```

---

## **📋 ANÁLISE DO PROCESSO REQUERIDO**

### **🔍 ITEM 3-C DETALHADO:**

```markdown
C- Atualizar as Separações em caso de alteração no pedido decorrente da importação do Odoo:

C.1 - Separação Total:
Caso haja alteração no pedido após a atualização, deverá ser atualizada a Separação

C.2 - Separação Parcial:
Deverá ter uma tela mostrando: 
- Separação Atual vs Saldo Pedido
- Alteração Separação (campos pré-preenchidos)
```

### **🎯 TIPOS DE SEPARAÇÃO:**

1. **📦 SEPARAÇÃO TOTAL:** Todo o saldo do pedido foi separado
2. **📦 SEPARAÇÃO PARCIAL:** Apenas parte do saldo foi separado

---

## **🔧 IMPLEMENTAÇÃO NECESSÁRIA**

### **FASE 1: SISTEMA DE DETECÇÃO (PRÉ-SINCRONIZAÇÃO)**

#### **1.1 - Backup de Separações Ativas**
```python
def backup_separacoes_ativas():
    """
    Criar backup de todas as Separações ativas antes da sincronização
    """
    separacoes_ativas = db.session.query(
        Separacao.separacao_lote_id,
        Separacao.num_pedido,
        Separacao.cod_produto,
        Separacao.qtd_saldo,
        Separacao.tipo_envio,
        # ... outros campos relevantes
    ).filter(
        Separacao.separacao_lote_id.isnot(None)
    ).all()
    
    return separacoes_ativas
```

#### **1.2 - Backup de PreSeparações Ativas**
```python
def backup_pre_separacoes_ativas():
    """
    Criar backup de todas as PreSeparacoes ativas
    """
    from app.carteira.models import PreSeparacaoItem
    
    pre_separacoes = PreSeparacaoItem.query.filter(
        PreSeparacaoItem.status.in_(['CRIADO', 'RECOMPOSTO'])
    ).all()
    
    return pre_separacoes
```

### **FASE 2: INTEGRAÇÃO COM SINCRONIZAÇÃO**

#### **2.1 - Modificar sincronizar_carteira_odoo()**
```python
def sincronizar_carteira_odoo(self, usar_filtro_pendente=True):
    """
    NOVA VERSÃO: Com sistema de reconciliação
    """
    try:
        # ✅ FASE 1: BACKUP PRÉ-SINCRONIZAÇÃO
        separacoes_backup = backup_separacoes_ativas()
        pre_separacoes_backup = backup_pre_separacoes_ativas()
        
        # ✅ FASE 2: SINCRONIZAÇÃO NORMAL (atual)
        # ... código atual de sincronização ...
        
        # ✅ FASE 3: RECONCILIAÇÃO PÓS-SINCRONIZAÇÃO
        resultados_reconciliacao = reconciliar_apos_sincronizacao(
            separacoes_backup, 
            pre_separacoes_backup
        )
        
        return {
            'sucesso': True,
            'reconciliacao': resultados_reconciliacao,
            # ... outros campos ...
        }
        
    except Exception as e:
        # Rollback completo em caso de erro
        pass
```

### **FASE 3: SISTEMA DE RECONCILIAÇÃO**

#### **3.1 - Reconciliação de PreSeparações**
```python
def reconciliar_pre_separacoes(pre_separacoes_backup):
    """
    Recompor PreSeparações após sincronização
    """
    from app.carteira.models import PreSeparacaoItem
    
    # ✅ USAR SISTEMA EXISTENTE (mas que nunca é chamado)
    resultado = PreSeparacaoItem.recompor_todas_pendentes(
        usuario='Sistema Odoo'
    )
    
    return resultado
```

#### **3.2 - Reconciliação de Separações**
```python
def reconciliar_separacoes(separacoes_backup):
    """
    Detectar e reconciliar Separações existentes
    """
    separacoes_problematicas = []
    separacoes_atualizadas = []
    
    for separacao_backup in separacoes_backup:
        # Buscar item atual na carteira
        item_carteira = CarteiraPrincipal.query.filter_by(
            num_pedido=separacao_backup.num_pedido,
            cod_produto=separacao_backup.cod_produto
        ).first()
        
        if not item_carteira:
            # Item foi cancelado no Odoo
            separacoes_problematicas.append({
                'tipo': 'ITEM_CANCELADO',
                'separacao': separacao_backup
            })
            continue
        
        # Comparar quantidades
        qtd_carteira_atual = item_carteira.qtd_saldo_produto_pedido
        qtd_separacao = separacao_backup.qtd_saldo
        
        if separacao_backup.tipo_envio == 'total':
            # SEPARAÇÃO TOTAL: Atualizar automaticamente
            if qtd_carteira_atual != qtd_separacao:
                atualizar_separacao_total(separacao_backup, item_carteira)
                separacoes_atualizadas.append(separacao_backup)
        else:
            # SEPARAÇÃO PARCIAL: Marcar para reconciliação manual
            if qtd_carteira_atual != (qtd_separacao + calcular_saldo_restante(separacao_backup)):
                separacoes_problematicas.append({
                    'tipo': 'PARCIAL_DIVERGENTE',
                    'separacao': separacao_backup,
                    'carteira_atual': item_carteira
                })
    
    return {
        'atualizadas': separacoes_atualizadas,
        'problematicas': separacoes_problematicas
    }
```

#### **3.3 - Atualização Automática (Separação Total)**
```python
def atualizar_separacao_total(separacao_backup, item_carteira):
    """
    Atualizar Separação Total automaticamente
    """
    # Buscar separação no banco
    separacao = Separacao.query.filter_by(
        separacao_lote_id=separacao_backup.separacao_lote_id
    ).first()
    
    if separacao:
        # Atualizar campos que podem ter mudado
        separacao.qtd_saldo = item_carteira.qtd_saldo_produto_pedido
        separacao.valor_saldo = (
            item_carteira.qtd_saldo_produto_pedido * 
            item_carteira.preco_produto_pedido
        )
        separacao.nome_produto = item_carteira.nome_produto
        # ... outros campos relevantes ...
        
        db.session.commit()
        
        logger.info(f"✅ Separação Total {separacao.separacao_lote_id} atualizada automaticamente")
```

### **FASE 4: TELA DE RECONCILIAÇÃO MANUAL**

#### **4.1 - Rota de Reconciliação**
```python
@carteira_bp.route('/reconciliar-separacoes')
@login_required
@require_admin()
def tela_reconciliacao():
    """
    Tela para reconciliar Separações Parciais divergentes
    """
    # Buscar separações marcadas como problemáticas
    separacoes_problematicas = get_separacoes_problematicas()
    
    return render_template(
        'carteira/reconciliar_separacoes.html',
        separacoes=separacoes_problematicas
    )
```

#### **4.2 - Template de Reconciliação**
```html
<!-- app/templates/carteira/reconciliar_separacoes.html -->
<div class="card">
    <div class="card-header">
        <h4>🔄 Reconciliação de Separações Divergentes</h4>
    </div>
    <div class="card-body">
        {% for separacao in separacoes %}
        <div class="row reconciliacao-item">
            <div class="col-md-4">
                <h6>📦 Separação Atual</h6>
                <ul>
                    <li>Lote: {{ separacao.separacao_lote_id }}</li>
                    <li>Qtd: {{ separacao.qtd_saldo }}</li>
                    <li>Valor: R$ {{ separacao.valor_saldo }}</li>
                </ul>
            </div>
            <div class="col-md-4">
                <h6>📋 Saldo Pedido (Odoo)</h6>
                <ul>
                    <li>Qtd Total: {{ separacao.carteira_atual.qtd_saldo_produto_pedido }}</li>
                    <li>Qtd Restante: {{ separacao.qtd_restante }}</li>
                    <li>Valor: R$ {{ separacao.carteira_atual.valor_total }}</li>
                </ul>
            </div>
            <div class="col-md-4">
                <h6>✏️ Alteração Separação</h6>
                <form method="POST" action="/carteira/reconciliar-item">
                    <input type="hidden" name="separacao_id" value="{{ separacao.id }}">
                    <div class="mb-2">
                        <label>Nova Quantidade:</label>
                        <input type="number" name="nova_qtd" 
                               value="{{ min(separacao.qtd_saldo, separacao.carteira_atual.qtd_saldo_produto_pedido) }}"
                               class="form-control" step="0.001">
                    </div>
                    <button type="submit" class="btn btn-primary btn-sm">💾 Aplicar</button>
                    <button type="button" class="btn btn-danger btn-sm" onclick="cancelarSeparacao({{ separacao.id }})">❌ Cancelar</button>
                </form>
            </div>
        </div>
        <hr>
        {% endfor %}
    </div>
</div>
```

### **FASE 5: VALIDAÇÃO PRÉ-SINCRONIZAÇÃO**

#### **5.1 - Alerta de Separações Ativas**
```python
def validar_antes_sincronizacao():
    """
    Validar se há separações ativas que serão afetadas
    """
    separacoes_ativas = Separacao.query.filter(
        Separacao.separacao_lote_id.isnot(None)
    ).count()
    
    pre_separacoes_ativas = PreSeparacaoItem.query.filter(
        PreSeparacaoItem.status.in_(['CRIADO', 'RECOMPOSTO'])
    ).count()
    
    if separacoes_ativas > 0 or pre_separacoes_ativas > 0:
        return {
            'tem_separacoes': True,
            'total_separacoes': separacoes_ativas,
            'total_pre_separacoes': pre_separacoes_ativas,
            'aviso': f"⚠️ Existem {separacoes_ativas} separações e {pre_separacoes_ativas} pré-separações ativas que serão reconciliadas"
        }
    
    return {'tem_separacoes': False}
```

#### **5.2 - Interface de Confirmação**
```html
<!-- Adicionar ao dashboard de sincronização -->
<div class="alert alert-warning" id="alert-separacoes" style="display: none;">
    <h6>⚠️ Separações Ativas Detectadas</h6>
    <p>Existem separações ativas que serão reconciliadas após a sincronização.</p>
    <div class="form-check">
        <input class="form-check-input" type="checkbox" id="confirmar_reconciliacao">
        <label class="form-check-label" for="confirmar_reconciliacao">
            Entendo que as separações serão automaticamente reconciliadas
        </label>
    </div>
</div>
```

---

## **🎯 CRONOGRAMA DE IMPLEMENTAÇÃO**

### **📅 SPRINT 1 (3 dias):**
- ✅ Implementar backup de separações ativas
- ✅ Implementar validação pré-sincronização
- ✅ Adicionar alertas na interface

### **📅 SPRINT 2 (5 dias):**
- ✅ Integrar sistema de reconciliação com sincronização
- ✅ Implementar reconciliação automática para Separação Total
- ✅ Implementar chamada de recompor_todas_pendentes()

### **📅 SPRINT 3 (4 dias):**
- ✅ Criar tela de reconciliação manual
- ✅ Implementar APIs para reconciliação de Separação Parcial
- ✅ Testes completos do sistema

---

## **📊 CRITÉRIOS DE SUCESSO**

### **✅ FUNCIONALIDADES OBRIGATÓRIAS:**

1. **🔄 Reconciliação Automática:**
   - PreSeparações recompostas automaticamente
   - Separações Totais atualizadas automaticamente

2. **🖥️ Reconciliação Manual:**
   - Tela de reconciliação para Separações Parciais
   - Interface intuitiva para ajustar quantidades

3. **⚠️ Validações:**
   - Alerta antes da sincronização sobre separações ativas
   - Opção de cancelar sincronização se necessário

4. **📊 Relatórios:**
   - Log detalhado de reconciliações realizadas
   - Estatísticas de separações afetadas

### **🎯 MÉTRICAS DE QUALIDADE:**

- ✅ 100% das PreSeparações preservadas
- ✅ 100% das Separações Totais atualizadas automaticamente  
- ✅ 0% de perda de dados operacionais
- ✅ Interface de reconciliação funcional para Separações Parciais

---

## **🚀 RESULTADO ESPERADO**

Após a implementação, a funcionalidade "Sincronizar Carteira Completa" irá:

1. **🔍 DETECTAR** automaticamente separações e pré-separações ativas
2. **⚠️ ALERTAR** o usuário sobre o impacto da sincronização  
3. **🔄 RECONCILIAR** automaticamente separações totais e pré-separações
4. **🖥️ APRESENTAR** tela de reconciliação para separações parciais divergentes
5. **📊 FORNECER** relatório completo das reconciliações realizadas

**✅ RESULTADO:** Sistema de sincronização seguro e confiável que preserva 100% dos dados operacionais conforme especificado no `processo_atual.md`. 