# ROADMAP TÉCNICO: SINCRONIZAÇÃO AVANÇADA ODOO-CARTEIRA

**Projeto:** Sistema de Fretes - Módulo Carteira  
**Data:** Janeiro 2025  
**Versão:** 1.0  

---

## 📋 VISÃO GERAL

### Problema
- Importações do Odoo podem alterar pedidos que já possuem separações/pré-separações
- Necessidade de sincronização inteligente que preserve trabalho realizado
- Controle de envios totais vs parciais
- Sistema de alertas para pedidos cotados alterados

### Solução
Sistema de sincronização hierárquica que aplica alterações seguindo ordem: Saldo → PreSeparação → Separações (da mais recente para mais antiga).

---

## 🗄️ ESTRUTURA DE DADOS

### Novos Campos

#### Tabela `separacao`
```sql
ALTER TABLE separacao ADD COLUMN tipo_envio VARCHAR(10) DEFAULT 'total';
-- Valores aceitos: 'total', 'parcial'
-- NOT NULL, com índice para performance
```

#### Tabela `pre_separacao_itens`
```sql
ALTER TABLE pre_separacao_itens ADD COLUMN tipo_envio VARCHAR(10) DEFAULT 'total';
-- Valores aceitos: 'total', 'parcial'
-- NOT NULL, herda para Separacao quando convertida
```

#### Tabela `pedido`
```sql
ALTER TABLE pedido ADD COLUMN alterado_pos_separacao BOOLEAN DEFAULT FALSE;
-- Indica se pedido foi alterado após ter separações
-- Usado para alertas visuais
```

#### Tabela `embarque`
```sql
ALTER TABLE embarque ADD COLUMN alterado_pos_separacao BOOLEAN DEFAULT FALSE;
-- Indica se embarque contém pedidos alterados
-- Usado para alertas visuais
```

#### Nova Tabela `log_sincronizacao_odoo`
```sql
CREATE TABLE log_sincronizacao_odoo (
    id SERIAL PRIMARY KEY,
    data_sincronizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    num_pedido VARCHAR(50) NOT NULL,
    cod_produto VARCHAR(50) NOT NULL,
    acao_realizada VARCHAR(200) NOT NULL,
    qtd_antes NUMERIC(15,3),
    qtd_depois NUMERIC(15,3),
    tipo_origem VARCHAR(20), -- 'saldo', 'pre_separacao', 'separacao'
    origem_id INTEGER, -- ID da PreSeparacao ou Separacao afetada
    usuario_id INTEGER REFERENCES usuario(id)
);

CREATE INDEX idx_log_sincronizacao_pedido ON log_sincronizacao_odoo(num_pedido);
CREATE INDEX idx_log_sincronizacao_data ON log_sincronizacao_odoo(data_sincronizacao);
```

---

## 🔧 IMPLEMENTAÇÃO TÉCNICA

### Classe Principal: SincronizadorOdooAvancado

**Localização:** `app/carteira/services/sincronizador_odoo.py`

```python
class SincronizadorOdooAvancado:
    def __init__(self):
        self.logs_sessao = []
        
    def processar_atualizacao_carteira(self):
        """
        Ponto de entrada principal após importação Odoo
        Retorna: dict com resumo das alterações
        """
        
    def analisar_impactos_pedido(self, num_pedido):
        """
        Compara quantidades antes/depois da importação
        Retorna: lista de produtos com diferenças
        """
        
    def aplicar_reducao_hierarquica(self, num_pedido, cod_produto, reducao):
        """
        Aplica redução seguindo hierarquia definida
        Retorna: dict com detalhes das alterações
        """
        
    def gerar_alertas_necessarios(self, pedidos_alterados):
        """
        Marca pedidos/embarques que precisam de alerta
        """
```

### Algoritmo de Redução Hierárquica

**Ordem de Redução:**
1. Saldo livre (carteira - separações - pré-separações)
2. PreSeparação (ID mais alto = mais recente)
3. Separações (ID mais alto = mais recente)

**Pseudocódigo:**
```
FUNÇÃO aplicar_reducao(num_pedido, cod_produto, reducao_total):
    
    // 1. Calcular saldo livre atual
    carteira_total = buscar_qtd_carteira(num_pedido, cod_produto)
    separacoes_total = somar_separacoes(num_pedido, cod_produto)
    pre_separacoes_total = somar_pre_separacoes(num_pedido, cod_produto)
    saldo_livre = carteira_total - separacoes_total - pre_separacoes_total
    
    // 2. Reduzir do saldo livre primeiro
    SE reducao_total > saldo_livre:
        reducao_total = reducao_total - saldo_livre
        registrar_log("Reduzido " + saldo_livre + " do saldo livre")
    SENÃO:
        registrar_log("Reduzido " + reducao_total + " do saldo livre")
        RETORNAR // Redução completa
    
    // 3. Reduzir de PreSeparações (mais recente primeiro)
    pre_separacoes = buscar_pre_separacoes_ordenadas_desc(num_pedido, cod_produto)
    PARA CADA pre_sep EM pre_separacoes:
        SE reducao_total <= 0: SAIR
        
        SE reducao_total >= pre_sep.qtd_selecionada:
            reducao_total = reducao_total - pre_sep.qtd_selecionada
            registrar_log("Removido PreSeparacao ID " + pre_sep.id)
            pre_sep.qtd_selecionada = 0
        SENÃO:
            pre_sep.qtd_selecionada = pre_sep.qtd_selecionada - reducao_total
            registrar_log("Reduzido " + reducao_total + " da PreSeparacao ID " + pre_sep.id)
            reducao_total = 0
    
    // 4. Reduzir de Separações (mais recente primeiro)
    separacoes = buscar_separacoes_ordenadas_desc(num_pedido, cod_produto)
    PARA CADA separacao EM separacoes:
        SE reducao_total <= 0: SAIR
        
        SE reducao_total >= separacao.qtd_saldo:
            reducao_total = reducao_total - separacao.qtd_saldo
            registrar_log("Removido Separacao ID " + separacao.id)
            separacao.qtd_saldo = 0
        SENÃO:
            separacao.qtd_saldo = separacao.qtd_saldo - reducao_total
            registrar_log("Reduzido " + reducao_total + " da Separacao ID " + separacao.id)
            reducao_total = 0
```

### Lógica de Alertas

**Critérios para Gerar Alerta:**
- Pedido possui separações OU pré-separações
- Status do pedido = "Cotado"
- Houve alteração na quantidade de pelo menos um produto

**Implementação:**
```python
def detectar_pedidos_para_alerta(self, pedidos_alterados):
    pedidos_alerta = []
    
    for num_pedido in pedidos_alterados:
        pedido = Pedido.query.filter_by(num_pedido=num_pedido).first()
        
        if not pedido:
            continue
            
        # Verificar se possui separações
        tem_separacoes = Separacao.query.filter_by(num_pedido=num_pedido).first() is not None
        
        # Verificar se possui pré-separações
        tem_pre_separacoes = PreSeparacaoItem.query.filter_by(num_pedido=num_pedido).first() is not None
        
        # Verificar se está cotado
        esta_cotado = pedido.status_calculado == 'Cotado'
        
        if (tem_separacoes or tem_pre_separacoes) and esta_cotado:
            pedido.alterado_pos_separacao = True
            pedidos_alerta.append(pedido)
            
            # Marcar embarques relacionados
            for embarque in pedido.embarques:
                embarque.alterado_pos_separacao = True
    
    return pedidos_alerta
```

---

## 🎨 INTERFACE DE USUÁRIO

### Adições nos Forms

#### Modal de Pré-Separação
```html
<!-- Adicionar campo tipo_envio -->
<div class="form-group">
    <label for="tipo_envio">Tipo de Envio:</label>
    <select name="tipo_envio" id="tipo_envio" class="form-control" required>
        <option value="total">Total - Enviar pedido completo</option>
        <option value="parcial">Parcial - Enviar parte do pedido</option>
    </select>
    <small class="form-text text-muted">
        <strong>Total:</strong> Pedido será enviado completo, sem divisões.<br>
        <strong>Parcial:</strong> Permite divisão do pedido em múltiplos embarques.
    </small>
</div>
```

### Alertas Visuais

#### Em `pedidos/lista_pedidos.html`
```html
{% if pedido.alterado_pos_separacao %}
<div class="alert alert-warning mb-2" id="alerta-{{pedido.id}}">
    <div class="d-flex justify-content-between align-items-center">
        <div>
            <i class="fas fa-exclamation-triangle"></i>
            <strong>PEDIDO ALTERADO:</strong> 
            Este pedido foi modificado no Odoo após ter separações/embarques criados.
            <br><small>Verifique se é necessária reimpressão dos documentos.</small>
        </div>
        <button type="button" class="btn btn-sm btn-outline-warning" 
                onclick="desativarAlerta({{pedido.id}})">
            <i class="fas fa-check"></i> Marcar como Visto
        </button>
    </div>
</div>
{% endif %}
```

#### Em `embarques/listar_embarques.html`
```html
{% if embarque.alterado_pos_separacao %}
<span class="badge badge-warning ml-1" title="Embarque contém pedidos alterados após separação">
    <i class="fas fa-edit"></i> Alterado
</span>
{% endif %}
```

### JavaScript para Alertas
```javascript
function desativarAlerta(pedidoId) {
    if (!confirm('Marcar este alerta como visto? Ele não aparecerá mais até uma nova alteração.')) {
        return;
    }
    
    fetch(`/carteira/desativar-alerta/${pedidoId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            document.getElementById(`alerta-${pedidoId}`).style.display = 'none';
            showNotification('Alerta marcado como visto', 'success');
        }
    })
    .catch(error => {
        showNotification('Erro ao desativar alerta', 'error');
    });
}
```

---

## 🔗 INTEGRAÇÃO COM IMPORTAÇÃO ODOO

### Ponto de Entrada
**Arquivo:** `app/carteira/routes.py`
**Rota:** `/carteira/importar`

**Modificação necessária:**
```python
@bp.route('/importar', methods=['POST'])
@login_required
def importar_carteira():
    # ... código existente de importação ...
    
    # NOVA SEÇÃO: Após importação bem-sucedida
    try:
        sincronizador = SincronizadorOdooAvancado()
        resultado_sync = sincronizador.processar_atualizacao_carteira()
        
        if resultado_sync['pedidos_alterados']:
            flash(f"⚠️ {len(resultado_sync['pedidos_alterados'])} pedidos foram alterados e requerem atenção", 'warning')
        
        if resultado_sync['reducoes_aplicadas']:
            flash(f"🔄 {resultado_sync['reducoes_aplicadas']} reduções aplicadas em separações/pré-separações", 'info')
            
    except Exception as e:
        logger.error(f"Erro na sincronização avançada: {str(e)}")
        flash("Importação realizada, mas houve problemas na sincronização automática", 'warning')
    
    # ... resto do código existente ...
```

### Rotas Adicionais Necessárias

```python
@bp.route('/desativar-alerta/<int:pedido_id>', methods=['POST'])
@login_required
def desativar_alerta(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    pedido.alterado_pos_separacao = False
    
    # Verificar se todos os pedidos do embarque não têm mais alertas
    for embarque in pedido.embarques:
        todos_sem_alerta = all(not p.alterado_pos_separacao for p in embarque.pedidos)
        if todos_sem_alerta:
            embarque.alterado_pos_separacao = False
    
    db.session.commit()
    return jsonify({'success': True})

@bp.route('/logs-sincronizacao')
@login_required
@require_admin
def logs_sincronizacao():
    logs = LogSincronizacaoOdoo.query.order_by(
        LogSincronizacaoOdoo.data_sincronizacao.desc()
    ).limit(100).all()
    
    return render_template('carteira/logs_sincronizacao.html', logs=logs)
```

---

## 🧪 CASOS DE TESTE

### Teste 1: Redução Simples
**Cenário:** Pedido com apenas saldo livre
- Pedido original: Produto A = 100 unidades
- Separações: 0
- Pré-separações: 0
- Atualização Odoo: Produto A = 80 unidades
- **Resultado esperado:** Saldo reduzido para 80, nenhum alerta

### Teste 2: Redução com Pré-Separação
**Cenário:** Redução afeta pré-separação
- Pedido original: Produto A = 100 unidades
- Pré-separação: 30 unidades
- Saldo livre: 70 unidades
- Atualização Odoo: Produto A = 90 unidades (redução de 10)
- **Resultado esperado:** Saldo livre = 60, pré-separação = 30

### Teste 3: Redução Complexa (Exemplo Crítico)
**Cenário:** Redução afeta múltiplas camadas
- Pedido original: Produto A = 100 unidades
- Separação 1: 30 unidades
- Separação 2: 40 unidades  
- Pré-separação: 20 unidades
- Saldo livre: 10 unidades
- Atualização Odoo: Produto A = 80 unidades (redução de 20)
- **Resultado esperado:** 
  - Saldo livre: 0
  - Pré-separação: 10 (reduzida de 20 para 10)
  - Separação 2: 40 (inalterada)
  - Separação 1: 30 (inalterada)

### Teste 4: Alerta para Pedido Cotado
**Cenário:** Pedido cotado alterado
- Pedido com status "Cotado"
- Possui separações
- Sofre alteração
- **Resultado esperado:** 
  - `alterado_pos_separacao = True`
  - Alerta visível na interface
  - Embarques relacionados marcados

### Teste 5: Múltiplos Produtos
**Cenário:** Pedido com vários produtos alterados
- Produto A: redução de 10 unidades
- Produto B: aumento de 5 unidades  
- Produto C: inalterado
- **Resultado esperado:** 
  - Apenas Produto A sofre redução hierárquica
  - Produto B: saldo livre aumenta
  - Logs detalhados de cada alteração

---

## 📅 CRONOGRAMA DETALHADO

### FASE 4.1: Estrutura Base (2 dias)
**Dia 1:**
- [ ] Criar migração para novos campos
- [ ] Atualizar models Python
- [ ] Criar tabela de logs
- [ ] Testes básicos de estrutura

**Dia 2:**
- [ ] Atualizar forms e templates básicos
- [ ] Validação de campos obrigatórios
- [ ] Testes de integridade de dados

### FASE 4.2: Motor de Sincronização (4 dias)
**Dia 1:**
- [ ] Classe `SincronizadorOdooAvancado` base
- [ ] Método `calcular_saldo_livre()`
- [ ] Método `analisar_impactos_pedido()`

**Dia 2:**
- [ ] Algoritmo de redução hierárquica
- [ ] Sistema de logs detalhado
- [ ] Testes unitários do algoritmo

**Dia 3:**
- [ ] Integração com importação existente
- [ ] Tratamento de erros e rollback
- [ ] Testes de performance

**Dia 4:**
- [ ] Refinamentos e otimizações
- [ ] Validação completa do fluxo
- [ ] Documentação de debugging

### FASE 4.3: Sistema de Alertas (2 dias)
**Dia 1:**
- [ ] Lógica de detecção de alertas
- [ ] Métodos de ativação/desativação
- [ ] Cascata para embarques

**Dia 2:**
- [ ] Interface visual completa
- [ ] JavaScript para interação
- [ ] Testes de usabilidade

### FASE 4.4: Interface de Controle (2 dias)
**Dia 1:**
- [ ] Modificação dos modals existentes
- [ ] Campo tipo_envio em todos os forms
- [ ] Validações frontend

**Dia 2:**
- [ ] Dashboard de logs de sincronização
- [ ] Ferramentas de administração
- [ ] Tela de relatórios

### FASE 4.5: Integração e Testes (1 dia)
**Dia 1:**
- [ ] Testes de integração completos
- [ ] Validação de todos os casos de teste
- [ ] Deploy e monitoramento

---

## ⚠️ RISCOS E LIMITAÇÕES

### Riscos Técnicos
1. **Performance:** Algoritmo pode ser lento com muitos produtos/separações
2. **Integridade:** Possibilidade de inconsistências em caso de erro
3. **Complexidade:** Lógica complexa = maior chance de bugs

### Limitações Conhecidas
1. **Não altera fretes:** Mudanças nos pedidos não impactam cálculos de frete
2. **Alertas manuais:** Requer ação humana para desativar alertas
3. **Ordem fixa:** Hierarquia de redução não é configurável

### Mitigações
1. **Performance:** Índices no banco + cache quando necessário
2. **Integridade:** Transações atomicas + logs detalhados
3. **Complexidade:** Testes extensivos + documentação clara

---

## 📊 MÉTRICAS DE SUCESSO

### Funcionais
- [ ] 100% dos casos de teste passando
- [ ] Redução hierárquica funciona corretamente
- [ ] Alertas aparecem/desaparecem adequadamente
- [ ] Logs capturam todas as alterações

### Performance
- [ ] Sincronização < 5 segundos para pedidos com <100 produtos
- [ ] Interface responde em < 2 segundos
- [ ] Sem impacto na importação normal

### Usabilidade
- [ ] Usuários conseguem entender alertas sem treinamento
- [ ] Processo de desativação de alerta é intuitivo
- [ ] Tipo de envio é selecionado corretamente 90%+ das vezes

---

## 🔧 CONFIGURAÇÕES TÉCNICAS

### Variáveis de Ambiente
```env
# Habilitar sincronização avançada (padrão: True)
CARTEIRA_SYNC_AVANCADA=True

# Timeout para operações de sincronização (segundos)
CARTEIRA_SYNC_TIMEOUT=30

# Máximo de logs por pedido (evitar spam)
CARTEIRA_MAX_LOGS_POR_PEDIDO=100
```

### Configurações de Log
```python
# Em config.py
CARTEIRA_LOG_LEVEL = 'INFO'  # DEBUG para desenvolvimento
CARTEIRA_LOG_FILE = 'logs/sincronizacao_odoo.log'
```

---

## 🏁 CONCLUSÃO

Este roadmap representa uma implementação técnica robusta para sincronização avançada entre Odoo e o sistema de carteira. A abordagem hierárquica garante que o trabalho já realizado seja preservado ao máximo, enquanto o sistema de alertas mantém os usuários informados sobre mudanças que requerem atenção.

**Estimativa total:** 11 dias de desenvolvimento
**Complexidade:** Alta  
**Impacto:** Crítico para operação com Odoo

**Aprovação necessária para prosseguir com implementação.** 