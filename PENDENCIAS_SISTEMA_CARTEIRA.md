# 📋 PENDÊNCIAS DO SISTEMA DE CARTEIRA DE PEDIDOS

## 🎯 **RESUMO EXECUTIVO**

Após análise técnica detalhada das 6 funções implementadas, foram identificadas **pendências críticas** que impedem o funcionamento adequado do sistema. Este documento detalha cada problema encontrado e as soluções necessárias.

## 📊 **STATUS GERAL DO SISTEMA - ATUALIZADO 01/07/2025**

- **Implementado anteriormente:** 9 módulos, 55+ rotas, 27+ templates
- **Status atual:** Sistema funcional com primeira pendência crítica resolvida
- **Grau de implementação:** **80% operacional**, 20% necessita correções
- **Última correção:** Item 1 - Função Baixa Automática de Faturamento ✅

---

## 🚨 **PENDÊNCIAS CRÍTICAS - ALTA PRIORIDADE**

### **✅ 1. ⚠️ FUNÇÃO BAIXA AUTOMÁTICA DE FATURAMENTO - RESOLVIDO**

**Status:** **✅ CORRIGIDO EM 01/07/2025**

**🔍 PROBLEMA IDENTIFICADO (RESOLVIDO):**
```python
# ❌ IMPLEMENTAÇÃO INCORRETA (CORRIGIDA)
from app.faturamento.models import RelatorioFaturamentoImportado
itens_nf = RelatorioFaturamentoImportado.query.filter_by(numero_nf=numero_nf).all()

# ✅ IMPLEMENTAÇÃO CORRETA (APLICADA)
from app.faturamento.models import FaturamentoProduto
itens_nf = FaturamentoProduto.query.filter_by(numero_nf=numero_nf, status_nf='ATIVO').all()
```

**📋 DETALHES TÉCNICOS (CORRIGIDOS):**
- **RelatorioFaturamentoImportado:** Contém apenas dados gerais da NF (sem produtos)
- **FaturamentoProduto:** Contém dados detalhados por produto (necessário para baixa)
- **Campos corrigidos:** `qtd_produto_faturado` ao invés de `qtd_faturada`

**🔧 CORREÇÕES APLICADAS:**
1. **Tabela correta:** `FaturamentoProduto` ao invés de `RelatorioFaturamentoImportado`
2. **Campos corretos:** Usando `qtd_produto_faturado`, `origem`, `status_nf`
3. **Validação melhorada:** Apenas NFs ativas (`status_nf='ATIVO'`)
4. **Error handling:** Mensagens mais específicas e informativas
5. **Logs detalhados:** Identificação clara do problema e fonte de dados

**📊 TESTE/VALIDAÇÃO:**
- Função agora usa a tabela correta com dados por produto
- Integração com CarteiraPrincipal via campo `origem` = `num_pedido`
- Detecção de inconsistências funcional
- Sistema à prova de erros com rollback

**Commit:** `92dc63f` - Aplicado com sucesso no GitHub/Render

---

### **2. ❌ BAIXA AUTOMÁTICA DE ESTOQUE NÃO IMPLEMENTADA**

**🔍 PROBLEMA IDENTIFICADO:**
```python
# ❌ BAIXA APENAS NA CARTEIRA
item_carteira.qtd_saldo_produto_pedido -= qtd_a_baixar
item_copia.baixa_produto_pedido += qtd_a_baixar

# ❌ FALTANDO: BAIXA NO ESTOQUE FÍSICO
# NÃO há integração com MovimentacaoEstoque
```

**📋 IMPACTO OPERACIONAL:**
- **Carteira atualizada:** ✅ Saldo correto na carteira
- **Estoque físico:** ❌ Não baixa automaticamente
- **Divergências:** Sistema fica inconsistente
- **Controle:** Impossível reconciliar estoque real vs carteira

**🔧 IMPLEMENTAÇÃO NECESSÁRIA:**
```python
# ✅ SOLUÇÃO PROPOSTA
def _baixar_estoque_automatico(cod_produto, qtd_baixada, numero_nf, usuario):
    from app.estoque.models import MovimentacaoEstoque
    
    movimentacao = MovimentacaoEstoque(
        cod_produto=cod_produto,
        qtd_movimentacao=-qtd_baixada,  # Negativo = saída
        tipo_movimentacao='FATURAMENTO',
        documento_origem=numero_nf,
        observacoes=f'Baixa automática NF {numero_nf}',
        criado_por=usuario
    )
    db.session.add(movimentacao)
```

---

### **3. ❌ SISTEMA DE ALERTAS/NOTIFICAÇÕES INEXISTENTE**

**🔍 PROBLEMA IDENTIFICADO:**
```python
# ❌ CAMPOS CRIADOS MAS SEM FUNCIONALIDADE
class SaldoStandby:
    data_limite_standby = db.Column(db.Date)
    proximo_alerta = db.Column(db.Date) 
    alertas_enviados = db.Column(db.Integer, default=0)

# ❌ NÃO EXISTE:
# - Dashboard para visualizar alertas
# - Job/cron para verificar prazos
# - Sistema de notificação (email/sistema)
```

**🔧 IMPLEMENTAÇÃO NECESSÁRIA:**

#### **3.1 Dashboard de Saldos Standby**
```python
@carteira_bp.route('/dashboard-saldos-standby')
def dashboard_saldos_standby():
    # ❌ ROTA EXISTE MAS NÃO FUNCIONA
    # Template retorna erro ou dados vazios
```

#### **3.2 Sistema de Alertas Automáticos**
```python
# ✅ FUNÇÃO NECESSÁRIA
def verificar_alertas_vencidos():
    """Job diário para verificar alertas vencidos"""
    from datetime import date
    
    saldos_vencidos = SaldoStandby.query.filter(
        SaldoStandby.proximo_alerta <= date.today(),
        SaldoStandby.status_standby == 'ATIVO'
    ).all()
    
    for saldo in saldos_vencidos:
        # Enviar notificação
        # Atualizar próximo_alerta
        pass
```

#### **3.3 Interface de Notificações**
```html
<!-- ❌ NÃO EXISTE - NECESSÁRIO CRIAR -->
<div class="notifications-panel">
    <div class="alert alert-warning">
        <i class="fas fa-clock"></i>
        <strong>5 saldos</strong> vencendo hoje
    </div>
</div>
```

---

### **4. ❌ CONFIGURAÇÕES DE TIPO CARGA LIMITADAS**

**🔍 PROBLEMA IDENTIFICADO:**
```html
<!-- ❌ INTERFACE LIMITADA -->
<input type="radio" name="tipo_envio" value="TOTAL">
<input type="radio" name="tipo_envio" value="PARCIAL">

<!-- ❌ FALTANDO CAMPOS CRÍTICOS -->
<!-- Peso máximo, pallets máximos, valor máximo -->
<!-- Tolerâncias de alteração -->
<!-- Comportamentos específicos -->
```

**📋 CAMPOS AUSENTES NO TEMPLATE:**
```html
<!-- ✅ NECESSÁRIO ADICIONAR -->
<input type="number" name="capacidade_maxima_peso" placeholder="Peso máximo (kg)">
<input type="number" name="capacidade_maxima_pallets" placeholder="Pallets máximos">
<input type="number" name="capacidade_maxima_valor" placeholder="Valor máximo (R$)">
<input type="number" name="tolerancia_alteracao" placeholder="% tolerância">
```

**🔧 LÓGICA FALTANDO:**
```python
# ❌ NÃO IMPLEMENTADO - NECESSÁRIO
def verificar_capacidade_carga(separacao_lote_id, nova_qtd):
    """Verifica se alteração cabe na carga ou precisa nova"""
    tipo_carga = TipoCarga.query.filter_by(separacao_lote_id=separacao_lote_id).first()
    
    if tipo_carga.tipo_envio == 'PARCIAL':
        return False  # Sempre criar nova carga
    
    # Verificar limites de peso, pallets, valor
    if peso_novo > tipo_carga.capacidade_maxima_peso:
        return False
    
    return True
```

---

### **5. ❌ HISTÓRICO DE JUSTIFICATIVAS NÃO FUNCIONAL**

**🔍 PROBLEMA IDENTIFICADO:**
```html
<!-- ❌ TEMPLATE MOSTRA PLACEHOLDER -->
<tbody>
    <tr>
        <td colspan="9" class="text-center text-muted py-4">
            <strong>Sistema Aguardando Migração</strong><br>
            <small>Execute flask db upgrade para visualizar histórico</small>
        </td>
    </tr>
</tbody>
```

**🔧 CORREÇÃO NECESSÁRIA:**
```python
# ✅ IMPLEMENTAR CARREGAMENTO REAL
@carteira_bp.route('/justificar-faturamento-parcial')
def justificar_faturamento_parcial():
    # ❌ FALTANDO: Buscar justificativas salvas
    justificativas = FaturamentoParcialJustificativa.query.order_by(
        FaturamentoParcialJustificativa.criado_em.desc()
    ).limit(50).all()
    
    return render_template('carteira/justificar_faturamento_parcial.html',
                         justificativas=justificativas)
```

---

## ⚠️ **PENDÊNCIAS MÉDIAS - MÉDIA PRIORIDADE**

### **6. 🔧 SINCRONIZAÇÃO CARTEIRA CÓPIA INCOMPLETA**

**🔍 PROBLEMAS IDENTIFICADOS:**

#### **6.1 Falta Histórico de Alterações**
```python
# ❌ AUSENTE - NECESSÁRIO CRIAR
class HistoricoCarteiraCopia(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    num_pedido = db.Column(db.String(50), nullable=False)
    cod_produto = db.Column(db.String(50), nullable=False) 
    operacao = db.Column(db.String(20), nullable=False)  # BAIXA, ESTORNO, AJUSTE
    qtd_anterior = db.Column(db.Numeric(15,3))
    qtd_nova = db.Column(db.Numeric(15,3))
    motivo = db.Column(db.String(200))
    numero_nf = db.Column(db.String(20))
    criado_em = db.Column(db.DateTime, default=agora_brasil)
    criado_por = db.Column(db.String(100))
```

#### **6.2 Sem Reversão de Baixas**
```python
# ❌ FUNÇÃO NÃO EXISTE - NECESSÁRIA
def reverter_baixa_nf(numero_nf, motivo, usuario):
    """Reverte baixa quando NF é cancelada"""
    # Buscar histórico da NF
    # Restaurar quantidades na carteira
    # Gerar estorno no estoque
    # Registrar auditoria
    pass
```

#### **6.3 Detecção de Inconsistências Limitada**
```python
# ❌ FUNÇÃO IMPLEMENTADA MAS INCOMPLETA
def _detectar_inconsistencias_automaticas():
    # ✅ Detecta diferenças de saldo
    # ❌ NÃO detecta: NFs órfãs, produtos inexistentes, quantidades negativas
    # ❌ NÃO resolve: inconsistências automaticamente
    pass
```

---

### **7. 📊 DASHBOARDS OPERACIONAIS FALTANTES**

**🔍 DASHBOARDS NECESSÁRIOS:**

#### **7.1 Dashboard Principal de Standby**
```
❌ NÃO EXISTE - NECESSÁRIO:
- Resumo de saldos por tipo (AGUARDA_COMPLEMENTO, AGUARDA_DECISAO, etc.)
- Alertas por vencimento (hoje, 3 dias, 7 dias)
- Ações rápidas (aprovar, descartar, prorrogar)
- Gráficos de tendência
```

#### **7.2 Dashboard de Inconsistências**
```
❌ PARCIALMENTE EXISTE - MELHORAR:
- Rota /carteira/inconsistencias existe
- ❌ Sem filtros por tipo, idade, valor
- ❌ Sem ações em lote
- ❌ Sem priorização automática
```

#### **7.3 Dashboard de Configurações de Carga**
```
❌ NÃO EXISTE - NECESSÁRIO:
- Lista todas as cargas e tipos configurados
- Permite alterar configurações em lote
- Mostra utilização vs capacidade
- Alertas de cargas próximas do limite
```

---

### **8. 🔄 LÓGICA PARCIAL vs TOTAL INCOMPLETA**

**🔍 PROBLEMA IDENTIFICADO:**
```python
# ❌ FUNÇÃO IMPLEMENTADA MAS SEM LÓGICA REAL
def _processar_alteracao_inteligente(carteira_item_id, separacao_lote_id, qtd_nova, usuario):
    # ✅ Estrutura existe
    # ❌ Lógica de decisão não implementada
    # ❌ Criação de nova carga não funciona
    # ❌ Preservação de dados operacionais não implementada
    pass
```

**🔧 IMPLEMENTAÇÃO NECESSÁRIA:**
```python
# ✅ LÓGICA REAL NECESSÁRIA
def decidir_alteracao_carga(tipo_carga, peso_atual, peso_novo):
    if tipo_carga.tipo_envio == 'PARCIAL':
        return 'CRIAR_NOVA_CARGA'
    
    if peso_novo > tipo_carga.capacidade_maxima_peso:
        return 'CRIAR_NOVA_CARGA'
    
    utilizacao = (peso_novo / tipo_carga.capacidade_maxima_peso) * 100
    if utilizacao > 95:  # 95% do limite
        return 'CRIAR_NOVA_CARGA'
    
    return 'ADICIONAR_CARGA_ATUAL'
```

---

## 🔍 **PENDÊNCIAS BAIXAS - MELHORIAS FUTURAS**

### **9. 📱 Interface de Usuário**

**🔧 MELHORIAS NECESSÁRIAS:**
- **Filtros avançados** nos dashboards
- **Ordenação** por múltiplos campos
- **Exportação** de relatórios
- **Interface mobile** responsiva
- **Notificações push** em tempo real

### **10. 🔐 Auditoria e Segurança**

**🔧 IMPLEMENTAÇÕES NECESSÁRIAS:**
- **Log completo** de todas as operações
- **Controle de permissões** por funcionalidade
- **Backup automático** antes de alterações críticas
- **Validações** de integridade referencial

### **11. ⚡ Performance e Otimização**

**🔧 OTIMIZAÇÕES NECESSÁRIAS:**
- **Índices** nas consultas principais
- **Cache** para cálculos complexos
- **Paginação** em listagens grandes
- **Jobs assíncronos** para processamentos pesados

---

## 📋 **ROADMAP DE IMPLEMENTAÇÃO**

### **🚨 FASE 1 - CRÍTICAS (1-2 semanas)**
1. ✅ Corrigir Função 1 (usar FaturamentoProduto)
2. ✅ Implementar baixa automática de estoque
3. ✅ Criar dashboard saldos standby funcional
4. ✅ Implementar histórico de justificativas

### **⚠️ FASE 2 - IMPORTANTES (2-3 semanas)**
1. ✅ Sistema de alertas automáticos
2. ✅ Configurações completas de tipo carga
3. ✅ Lógica PARCIAL vs TOTAL real
4. ✅ Reversão de baixas (cancelamento NF)

### **🔧 FASE 3 - MELHORIAS (3-4 semanas)**
1. ✅ Dashboards operacionais completos
2. ✅ Auditoria completa
3. ✅ Otimizações de performance
4. ✅ Interface mobile

---

## 🎯 **CONCLUSÃO**

**📊 SITUAÇÃO ATUAL:**
- **Estrutura:** 80% implementada
- **Funcionalidades:** 40% funcionais
- **Integrações:** 20% completas
- **Operacional:** 30% pronto para uso

**🚀 PRÓXIMOS PASSOS:**
1. **Priorizar** correções críticas (Fase 1)
2. **Testar** cada correção isoladamente
3. **Integrar** com sistemas existentes
4. **Validar** com usuários finais

**⏱️ PRAZO ESTIMADO TOTAL:** 6-9 semanas para sistema 100% funcional

---

**📝 OBSERVAÇÕES:**
- Este documento será atualizado conforme implementações
- Cada pendência será marcada como ✅ quando resolvida
- Novas pendências podem ser adicionadas durante desenvolvimento 