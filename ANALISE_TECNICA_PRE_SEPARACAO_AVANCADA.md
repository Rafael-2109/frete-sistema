# 🔬 **ANÁLISE TÉCNICA: PRÉ-SEPARAÇÃO AVANÇADA COMO RASCUNHO DE SEPARAÇÃO**

> **Data:** 21/07/2025  
> **Versão:** 1.1 - REVISADA  
> **Escopo:** Análise completa dos gaps técnicos para implementação do sistema de pré-separação como provisão de estoque futuro

---

## 🎯 **RESUMO EXECUTIVO**

### **PROCESSO SOLICITADO (REVISADO):**
Transformar `PreSeparacaoItem` em um sistema de "rascunho" operacional que:
- Funciona como provisão de expedição futura (não definitiva)
- É considerado no cálculo de estoques futuros Just-in-Time
- Interface ágil via dropdown com divisão automática de linhas
- Constraint única por combinação: **Data Expedição + Agendamento + Protocolo**
- Sistema de alertas (não bloqueio) para separações com status "Cotado"

### **🔄 CORREÇÕES E REGRAS DE NEGÓCIO:**
- **CarteiraPrincipal SEM campo expedição** - Campo expedição só existe após pré-separação
- **Cálculo de estoque APENAS** PreSeparacao + Separacao (sem CarteiraPrincipal)
- **Data expedição OBRIGATÓRIA** em pré-separação (resolve problema constraint NULL)
- **Sistema de ALERTAS** para separações cotadas (não bloqueio)
- **REGRA CRÍTICA:** Lógica de consumo/aumento em atualizações Odoo definida

---

## 📊 **ANÁLISE DE GAPS TÉCNICOS CRÍTICOS**

### **✅ GAP 1: CONSTRAINT ÚNICA SIMPLIFICADA**

**SITUAÇÃO ATUAL:**
```python
# app/carteira/models.py - PreSeparacaoItem
# Constraint única REMOVIDA para permitir múltiplas pré-separações
# Permite: múltiplas pré-separações do mesmo produto sem restrição
```

**NOVA NECESSIDADE (SIMPLIFICADA):**
```python
# CONSTRAINT ÚNICA NECESSÁRIA:
# (num_pedido + cod_produto + data_expedicao + agendamento + protocolo)
# ✅ data_expedicao OBRIGATÓRIA (resolve problema NULL)
```

**PROBLEMA TÉCNICO RESOLVIDO:**
- ✅ **Data expedição obrigatória** elimina problema de NULL na constraint
- ⚠️ Campos `data_agendamento_editada`, `protocolo_editado` ainda podem ser NULL
- Precisa estratégia apenas para 2 campos (não 3)

**SOLUÇÃO SIMPLIFICADA:**
```sql
-- Constraint única MAIS SIMPLES - só 2 campos com COALESCE
ALTER TABLE pre_separacao_item 
ADD CONSTRAINT uq_pre_separacao_contexto UNIQUE (
    num_pedido, 
    cod_produto, 
    data_expedicao_editada,  -- ✅ OBRIGATÓRIO (sem COALESCE)
    COALESCE(data_agendamento_editada, '1900-01-01'::date),
    COALESCE(protocolo_editado, 'SEM_PROTOCOLO')
);

-- E modificar campo para NOT NULL
ALTER TABLE pre_separacao_item 
ALTER COLUMN data_expedicao_editada SET NOT NULL;
```

---

### **✅ GAP 2: INTEGRAÇÃO SIMPLIFICADA COM CÁLCULO DE ESTOQUE**

**SITUAÇÃO ATUAL:**
```python
# app/estoque/models.py - SaldoEstoque._calcular_saidas_completas()
# Considera apenas:
# 1. Separações efetivadas (status != 'Cancelado')  
# 2. Carteira não separada (com campo expedição)
# ❌ NÃO considera PreSeparacaoItem
```

**SITUAÇÃO NOVA (SIMPLIFICADA):**
- ✅ **CarteiraPrincipal SEM campo expedição** - não entra no cálculo
- ✅ **Apenas 2 fontes**: PreSeparacao + Separacao
- ✅ **Lógica mais simples** e performática

**INTEGRAÇÃO NECESSÁRIA (SIMPLIFICADA):**
```python
# NOVO: Cálculo APENAS com PreSeparacao + Separacao
def _calcular_saidas_completas_simplificado(self, produto, data_expedicao):
    total_saida = 0
    
    # 1. Separações efetivadas (mantido)
    separacoes = Separacao.query.filter(
        Separacao.cod_produto == produto,
        Separacao.expedicao == data_expedicao,
        Separacao.ativo == True,
        Separacao.status.in_(['ABERTO', 'COTADO'])
    ).all()
    total_saida += sum(s.qtd_saldo for s in separacoes)
    
    # 2. ✅ NOVO: Pré-separações ativas (obrigatoriamente com data)
    pre_separacoes = PreSeparacaoItem.query.filter(
        PreSeparacaoItem.cod_produto == produto,
        PreSeparacaoItem.data_expedicao_editada == data_expedicao,
        PreSeparacaoItem.status.in_(['CRIADO', 'RECOMPOSTO'])
    ).all()
    total_saida += sum(p.qtd_selecionada_usuario for p in pre_separacoes)
    
    # ❌ REMOVIDO: CarteiraPrincipal (sem expedição não participa)
    
    return total_saida
```

**VANTAGENS DA SIMPLIFICAÇÃO:**
- ✅ **Performance melhor** (2 queries vs 3)
- ✅ **Lógica mais clara** (só itens com data expedição)
- ✅ **Sem ambiguidade** sobre fonte dos dados

---

### **🔄 GAP 3: INTERFACE DINÂMICA JÁ EXISTE MAS PRECISA CORREÇÃO**

**SITUAÇÃO ATUAL:**
```html
<!-- app/templates/carteira/listar_agrupados.html -->
<!-- ✅ Interface dinâmica JÁ IMPLEMENTADA -->
<!-- ⚠️ Funcionamento INCORRETO - precisa revisão -->
```

**IDENTIFICAÇÃO DO PROBLEMA:**
- ✅ **Sistema já existe** na interface atual  
- ❌ **Funcionamento incorreto** precisa ser revisado
- 🔄 **Refatoração necessária** ao invés de desenvolvimento do zero

**ANÁLISE DO CÓDIGO EXISTENTE NECESSÁRIA:**
```javascript
// REVISAR: Sistema existente em listar_agrupados.html
// Localizar funções de divisão automática
// Identificar bugs no comportamento atual
// Corrigir lógica de merge/divisão de linhas

// FUNÇÕES A REVISAR:
// - criarPreSeparacao()
// - editarPreSeparacao() 
// - divisaoAutomaticaLinhas()
// - consolidacaoLinhas()
```

**TRABALHO NECESSÁRIO (REDUZIDO):**
- 🔍 **Análise do código existente** para identificar bugs
- 🔧 **Correção da lógica** ao invés de reescrita completa  
- ✅ **Testes do comportamento** correto
- 🎯 **Otimização da performance** se necessário

**VANTAGEM:**
- ⏰ **Tempo reduzido** significativamente
- 🛠️ **Base sólida** já implementada
- 🎯 **Foco em correção** ao invés de desenvolvimento

---

### **✅ GAP 4: SISTEMA DE ALERTAS PARA SEPARAÇÕES "COTADO"**

**SITUAÇÃO ATUAL:**
```python
# Sincronização Odoo substitui CarteiraPrincipal completamente
# Sem distinção de proteção por status de separação
```

**RISCO CRÍTICO:**
- Separação "Cotado" = **já pode estar impressa**
- Alteração pelo Odoo pode **quebrar processo físico**
- ✅ **Sistema de ALERTAS** (não bloqueio) necessário

**SISTEMA DE ALERTAS PROPOSTO:**
```python
# SISTEMA DE ALERTAS (SEM BLOQUEIO)
class AlertaSeparacaoCotada:
    
    @staticmethod  
    def verificar_separacoes_cotadas_antes_sincronizacao():
        """Gera alertas sobre separações cotadas antes da sincronização"""
        separacoes_cotadas = db.session.query(Separacao).filter(
            Separacao.status == 'COTADO',
            Separacao.ativo == True
        ).all()
        
        if separacoes_cotadas:
            return {
                'alertas': True,
                'nivel': 'ATENCAO',
                'quantidade': len(separacoes_cotadas),
                'separacoes_afetadas': [s.separacao_lote_id for s in separacoes_cotadas],
                'mensagem': f'⚠️ {len(separacoes_cotadas)} separações COTADAS podem ser afetadas',
                'recomendacao': 'Confirme se estas separações já foram processadas fisicamente'
            }
        
        return {'alertas': False}
    
    @staticmethod
    def detectar_alteracoes_separacao_cotada_pos_sincronizacao(alteracoes_detectadas):
        """Detecta alterações que afetaram separações cotadas APÓS sincronização"""
        alertas = []
        
        for alteracao in alteracoes_detectadas:
            # Buscar se pedido tem separação cotada
            separacao_cotada = Separacao.query.filter(
                Separacao.num_pedido == alteracao['num_pedido'],
                Separacao.status == 'COTADO',
                Separacao.ativo == True
            ).first()
            
            if separacao_cotada:
                alertas.append({
                    'nivel': 'CRITICO',
                    'tipo': 'SEPARACAO_COTADA_ALTERADA', 
                    'separacao_lote_id': separacao_cotada.separacao_lote_id,
                    'pedido': alteracao['num_pedido'],
                    'produto': alteracao['cod_produto'],
                    'alteracao': alteracao['tipo_alteracao'],
                    'mensagem': f'🚨 URGENTE: Separação COTADA {separacao_cotada.separacao_lote_id} foi afetada por alteração no Odoo',
                    'acao_requerida': 'Verificar impacto no processo físico imediatamente'
                })
        
        return alertas
    
    @staticmethod
    def exibir_alertas_interface(alertas):
        """Exibe alertas na interface para o usuário"""
        # Implementar sistema de notificações visuais
        # Modal de aviso, barras de alerta, etc.
        pass
```

**VANTAGENS DO SISTEMA DE ALERTAS:**
- ✅ **Não bloqueia** operações críticas
- ✅ **Informa riscos** ao usuário  
- ✅ **Permite decisão** consciente
- ✅ **Rastreável** para auditoria

---

### **🚨 GAP 5: LÓGICA DE ATUALIZAÇÕES PÓS-SINCRONIZAÇÃO ODOO**

**SITUAÇÃO ATUAL:**
```python
# Sincronização Odoo substitui CarteiraPrincipal completamente
# Sem lógica específica para preservar/atualizar pré-separações/separações
# Sistema de recomposição básico sem considerar tipos de envio
```

**REGRAS DE NEGÓCIO DEFINIDAS:**

#### **📉 REDUÇÃO DE QUANTIDADE (Ordem de Consumo):**
```python
# HIERARQUIA DE CONSUMO EM CASO DE REDUÇÃO:
# 1º SALDO (CarteiraPrincipal sem pré-separação)
# 2º PRÉ-SEPARAÇÃO (status: CRIADO, RECOMPOSTO) 
# 3º SEPARAÇÃO ABERTO (status: ABERTO)
# 4º SEPARAÇÃO COTADO (status: COTADO) - ÚLTIMO RECURSO

def aplicar_reducao_quantidade(num_pedido, cod_produto, qtd_reduzida):
    """Aplica redução respeitando hierarquia de impacto"""
    
    # 1º Consumir do saldo livre primeiro
    saldo_livre = CarteiraPrincipal.query.filter(
        CarteiraPrincipal.num_pedido == num_pedido,
        CarteiraPrincipal.cod_produto == cod_produto,
        CarteiraPrincipal.separacao_lote_id.is_(None)
    ).first()
    
    if saldo_livre and saldo_livre.qtd_saldo_produto_pedido >= qtd_reduzida:
        saldo_livre.qtd_saldo_produto_pedido -= qtd_reduzida
        return {'consumido_de': 'SALDO_LIVRE', 'restante': 0}
    
    # 2º Consumir de pré-separações
    qtd_restante = qtd_reduzida - (saldo_livre.qtd_saldo_produto_pedido if saldo_livre else 0)
    pre_separacoes = PreSeparacaoItem.query.filter(
        PreSeparacaoItem.num_pedido == num_pedido,
        PreSeparacaoItem.cod_produto == cod_produto,
        PreSeparacaoItem.status.in_(['CRIADO', 'RECOMPOSTO'])
    ).order_by(PreSeparacaoItem.data_criacao.desc()).all()
    
    for pre_sep in pre_separacoes:
        if qtd_restante <= 0:
            break
        
        if pre_sep.qtd_selecionada_usuario >= qtd_restante:
            pre_sep.qtd_selecionada_usuario -= qtd_restante
            qtd_restante = 0
        else:
            qtd_restante -= pre_sep.qtd_selecionada_usuario
            pre_sep.qtd_selecionada_usuario = 0
            # Marcar para exclusão se zerou
    
    # 3º Consumir de separações ABERTO
    if qtd_restante > 0:
        separacoes_aberto = Separacao.query.filter(
            Separacao.num_pedido == num_pedido,
            Separacao.cod_produto == cod_produto,
            Separacao.status == 'ABERTO'
        ).all()
        
        # Aplicar redução...
    
    # 4º ÚLTIMO RECURSO: Separações COTADO (gerar alerta crítico)
    if qtd_restante > 0:
        separacoes_cotado = Separacao.query.filter(
            Separacao.num_pedido == num_pedido,
            Separacao.cod_produto == cod_produto,
            Separacao.status == 'COTADO'
        ).all()
        
        # GERAR ALERTA CRÍTICO
        AlertaSeparacaoCotada.gerar_alerta_reducao_forcada(
            pedido=num_pedido,
            produto=cod_produto,
            quantidade=qtd_restante,
            separacoes_afetadas=separacoes_cotado
        )
```

#### **📈 AUMENTO DE QUANTIDADE (Lógica do tipo_envio):**
```python
def aplicar_aumento_quantidade(num_pedido, cod_produto, qtd_aumentada):
    """Aplica aumento respeitando lógica de tipo_envio corrigida"""
    
    # 1º Detectar tipo atual do pedido
    tipo_envio_atual = detectar_tipo_envio_automatico(num_pedido)
    
    if tipo_envio_atual == 'total':
        # PEDIDO TOTAL: Existe 1 única pré-separação OU 1 única separação
        # Identificar e atualizar o registro único
        
        pre_sep_unica = PreSeparacaoItem.query.filter(
            PreSeparacaoItem.num_pedido == num_pedido,
            PreSeparacaoItem.cod_produto == cod_produto,
            PreSeparacaoItem.status.in_(['CRIADO', 'RECOMPOSTO'])
        ).first()
        
        if pre_sep_unica:
            # ATUALIZAR pré-separação única (TOTAL)
            pre_sep_unica.qtd_selecionada_usuario += qtd_aumentada
            pre_sep_unica.tipo_envio = 'total'  # Manter como total
            return {
                'acao': 'ATUALIZACAO_PRE_SEPARACAO_TOTAL',
                'pre_separacao_id': pre_sep_unica.id,
                'nova_qtd': pre_sep_unica.qtd_selecionada_usuario
            }
        
        separacao_unica = Separacao.query.filter(
            Separacao.num_pedido == num_pedido,
            Separacao.cod_produto == cod_produto,
            Separacao.ativo == True
        ).first()
        
        if separacao_unica:
            # ATUALIZAR separação única (TOTAL)
            separacao_unica.qtd_saldo += qtd_aumentada
            separacao_unica.tipo_envio = 'total'  # Manter como total
            return {
                'acao': 'ATUALIZACAO_SEPARACAO_TOTAL',
                'separacao_lote_id': separacao_unica.separacao_lote_id,
                'nova_qtd': separacao_unica.qtd_saldo
            }
    
    elif tipo_envio_atual == 'parcial':
        # PEDIDO PARCIAL: Múltiplas pré-separações/separações
        # NÃO atualizar registros existentes - criar saldo livre
        return {
            'acao': 'SALDO_LIVRE_CRIADO',
            'qtd_disponivel': qtd_aumentada,
            'motivo': 'Pedido com envio PARCIAL - nova quantidade fica disponível'
        }
    
    else:
        # SEM pré-separações/separações - criar saldo livre
        return {
            'acao': 'SALDO_LIVRE_CRIADO',
            'qtd_disponivel': qtd_aumentada,
            'motivo': 'Pedido sem programação - quantidade fica disponível'
        }

def detectar_tipo_envio_automatico(num_pedido):
    """Detecta automaticamente se envio é total ou parcial"""
    
    # Verificar pré-separações do pedido
    pre_separacoes = PreSeparacaoItem.query.filter(
        PreSeparacaoItem.num_pedido == num_pedido,
        PreSeparacaoItem.status.in_(['CRIADO', 'RECOMPOSTO'])
    ).all()
    
    # Verificar separações do pedido
    separacoes = Separacao.query.filter(
        Separacao.num_pedido == num_pedido,
        Separacao.ativo == True
    ).all()
    
    total_pre_separacoes = len(pre_separacoes)
    total_separacoes = len(separacoes)
    
    # REGRA CORRETA:
    # TOTAL = 1 única pré-separação OU 1 única separação
    # PARCIAL = múltiplas pré-separações/separações (indicando que foi dividido)
    
    if (total_pre_separacoes == 1 and total_separacoes == 0) or \
       (total_pre_separacoes == 0 and total_separacoes == 1):
        return 'total'
    elif (total_pre_separacoes > 1) or (total_separacoes > 1) or \
         (total_pre_separacoes >= 1 and total_separacoes >= 1):
        return 'parcial'
    else:
        # Sem pré-separações nem separações
        return None
```

**VANTAGENS DA LÓGICA CORRIGIDA:**
- ✅ **Protege separações cotadas** (último recurso)
- ✅ **Detecção precisa de tipo_envio** baseada na QUANTIDADE de registros
- ✅ **Lógica clara:** 1 registro = TOTAL, múltiplos = PARCIAL
- ✅ **Direcionamento exato** de onde adicionar aumentos
- ✅ **Hierarquia clara** de impacto na redução

**CENÁRIOS DE TIPO_ENVIO:**
```python
# TOTAL (1 único registro):
# - 1 pré-separação + 0 separações → TOTAL
# - 0 pré-separações + 1 separação → TOTAL

# PARCIAL (múltiplos registros = foi dividido):  
# - 2+ pré-separações → PARCIAL
# - 2+ separações → PARCIAL
# - 1+ pré-separação + 1+ separação → PARCIAL (teve divisão)
```

---

### **🔴 GAP 6: SISTEMA DE RECOMPOSIÇÃO INCOMPATÍVEL**

**SITUAÇÃO ATUAL:**
```python
# Sistema atual de recomposição após Odoo
# Baseado em hash MD5 sem considerar constraint única nova
def recompor_na_carteira(self, carteira_item, usuario):
    # Aplica divisão SEM verificar constraint única
    # Pode criar duplicatas na nova constraint
```

**PROBLEMA:**
- Nova constraint única **pode quebrar** recomposição
- Múltiplas pré-separações podem ter **mesma combinação**
- Sistema precisa **consolidar** antes de recompor

**ADAPTAÇÃO NECESSÁRIA:**
```python
def recompor_com_constraint_unica(self, carteira_item, usuario):
    """Recomposição adaptada para nova constraint única"""
    
    # 1. Verificar se já existe pré-separação com mesma combinação
    combinacao_existente = PreSeparacaoItem.query.filter(
        PreSeparacaoItem.num_pedido == self.num_pedido,
        PreSeparacaoItem.cod_produto == self.cod_produto,
        func.coalesce(PreSeparacaoItem.data_expedicao_editada, date(1900,1,1)) == 
        func.coalesce(self.data_expedicao_editada, date(1900,1,1)),
        func.coalesce(PreSeparacaoItem.data_agendamento_editada, date(1900,1,1)) == 
        func.coalesce(self.data_agendamento_editada, date(1900,1,1)),
        func.coalesce(PreSeparacaoItem.protocolo_editado, 'SEM_PROTOCOLO') == 
        func.coalesce(self.protocolo_editado, 'SEM_PROTOCOLO'),
        PreSeparacaoItem.id != self.id
    ).first()
    
    if combinacao_existente:
        # 2. Consolidar quantidades
        combinacao_existente.qtd_selecionada_usuario += self.qtd_selecionada_usuario
        # 3. Remover duplicata
        db.session.delete(self)
    else:
        # 4. Recompor normalmente
        self.aplicar_divisao_na_carteira(carteira_item)
    
    self.marcar_como_recomposto(usuario)
```

---

### **🔴 GAP 6: PERFORMANCE DE CONSULTAS COMPLEXAS**

**SITUAÇÃO ATUAL:**
```sql
-- Consultas simples baseadas em chaves primárias
-- Sem otimização para constraint composta
```

**NOVA COMPLEXIDADE:**
- Consultas por **constraint composta** com COALESCE
- JOIN com **múltiplas tabelas** (CarteiraPrincipal + Separacao + PreSeparacaoItem)
- Cálculo de **estoque em tempo real** com 3 fontes de dados

**ÍNDICES NECESSÁRIOS:**
```sql
-- Índice para constraint única composta
CREATE INDEX idx_pre_sep_constraint_composta ON pre_separacao_item (
    num_pedido, 
    cod_produto, 
    COALESCE(data_expedicao_editada, '1900-01-01'::date),
    COALESCE(data_agendamento_editada, '1900-01-01'::date),
    COALESCE(protocolo_editado, 'SEM_PROTOCOLO')
);

-- Índice para cálculo de estoque por data
CREATE INDEX idx_pre_sep_data_expedicao ON pre_separacao_item (
    cod_produto, 
    data_expedicao_editada, 
    status
) WHERE status IN ('CRIADO', 'RECOMPOSTO');

-- Índice para consultas de dashboard
CREATE INDEX idx_pre_sep_dashboard ON pre_separacao_item (
    num_pedido,
    status,
    data_criacao DESC
);
```

---

## ⚠️ **RISCOS E CENÁRIOS CRÍTICOS**

### **RISCO 1: DEADLOCK NA SINCRONIZAÇÃO**
**Cenário:** Usuário editando pré-separação WHILE sincronização Odoo executando
**Impacto:** Transação travada, dados inconsistentes
**Mitigação:** Lock exclusivo durante sincronização

### **RISCO 2: SEPARAÇÃO COTADA ALTERADA**
**Cenário:** Odoo altera pedido que já tem separação impressa e em processo
**Impacto:** Processo físico quebrado, retrabalho
**Mitigação:** Bloqueio preventivo na sincronização

### **RISCO 3: CONSTRAINT VIOLATION EM PRODUÇÃO**
**Cenário:** Dados existentes violam nova constraint única
**Impacto:** Sistema inoperante após deploy
**Mitigação:** Migration cuidadosa com limpeza prévia

### **RISCO 4: PERFORMANCE DEGRADADA**
**Cenário:** Consultas complexas sem índices adequados
**Impacto:** Dashboard lento, timeout em consultas
**Mitigação:** Índices específicos + cache Redis

---

## 🛠️ **PLANO DE IMPLEMENTAÇÃO REVISADO E OTIMIZADO**

### **FASE 1: PREPARAÇÃO DA BASE DE DADOS (SIMPLIFICADA)**
1. **Análise de pré-separações** existentes sem data_expedição  
2. **Definição de data padrão** ou limpeza de registros inválidos
3. **Modificação do campo** data_expedicao_editada para NOT NULL
4. **Criação da constraint única** otimizada (2 campos com COALESCE)
5. **Criação dos índices** de performance

### **FASE 2: ADAPTAÇÃO DO BACKEND (OTIMIZADA)**  
1. **Modificação do modelo** PreSeparacaoItem (campo obrigatório)
2. **Integração SIMPLES** com cálculo de estoque (apenas 2 fontes)
3. **Implementação da lógica** de redução/aumento pós-Odoo
4. **Sistema de alertas** (não bloqueio) para separações cotadas
5. **Detecção automática** de tipo_envio total/parcial

### **FASE 3: CORREÇÃO DO FRONTEND (REDUZIDA)**
1. **Análise do código existente** em listar_agrupados.html
2. **Correção das funções** de divisão automática existentes
3. **Ajuste das validações** para nova constraint única
4. **Sistema de alertas** visuais básico

### **FASE 4: SEGURANÇA E MONITORAMENTO (SIMPLIFICADA)**
1. **Sistema de alertas** (sem bloqueio) durante sincronização
2. **Logs de operações** críticas
3. **Validação pós-sincronização** para separações cotadas
4. **Dashboard de alertas** simples

### **FASE 5: TESTES E VALIDAÇÃO (FOCADA)**
1. **Testes da constraint única** com cenários reais
2. **Validação da divisão automática** corrigida
3. **Teste do cálculo de estoque** simplificado
4. **Simulação da lógica redução/aumento** pós-Odoo
5. **Testes de tipo_envio automático** (total/parcial)
6. **Simulação de alertas** para separações cotadas

**ESTIMATIVA AJUSTADA COM NOVA LÓGICA:** 
- ✅ **50% menos complexidade** (interface já existe)
- ✅ **30% menos backend** (cálculo simplificado)
- ✅ **Sem sistema de bloqueio** (apenas alertas)
- ➕ **Lógica redução/aumento** (complexidade média)
- **ESTIMATIVA FINAL:** 2,5 semanas desenvolvimento + 4 dias testes

---

## 📋 **ALTERAÇÕES NECESSÁRIAS NO CÓDIGO**

### **MODELOS (models.py)**
```python
class PreSeparacaoItem(db.Model):
    # ✅ NOVA CONSTRAINT ÚNICA COMPOSTA
    __table_args__ = (
        db.Index('idx_pre_sep_constraint_composta', 
                'num_pedido', 'cod_produto',
                func.coalesce('data_expedicao_editada', '1900-01-01'),
                func.coalesce('data_agendamento_editada', '1900-01-01'),  
                func.coalesce('protocolo_editado', 'SEM_PROTOCOLO'),
                unique=True),
    )
    
    # ✅ NOVOS MÉTODOS DE NEGÓCIO
    @classmethod
    def criar_ou_atualizar_por_contexto(cls, carteira_item, dados_editaveis, usuario):
        """Cria ou atualiza pré-separação respeitando constraint única"""
        
    def consolidar_com_existente(self, pre_separacao_existente):
        """Consolida duas pré-separações com mesmo contexto"""
```

### **ESTOQUE (estoque/models.py)**
```python
def _calcular_saidas_completas_com_pre_separacao(self, produto, data_expedicao):
    """Inclui pré-separações no cálculo de saídas futuras"""
    # Implementação completa necessária
```

### **FRONTEND (listar_agrupados.html)**
```javascript
class GerenciadorPreSeparacaoAvancada {
    // Sistema completo de divisão dinâmica
    // Validação de constraint única
    // Sincronização com backend
}
```

### **SINCRONIZAÇÃO (odoo/services/carteira_service.py)**
```python
def sincronizar_com_protecao_separacao_cotada(self):
    """Sincronização com proteção especial"""
    # Verificações pré-sincronização
    # Sistema de alertas e bloqueios
```

---

## 🎯 **CONCLUSÃO E RECOMENDAÇÕES (REVISADAS)**

### **VIABILIDADE TÉCNICA:** ✅ **POSSÍVEL E SIMPLIFICADA**

### **PRINCIPAIS VANTAGENS IDENTIFICADAS:**
1. ✅ **Constraint única simplificada** (data expedição obrigatória resolve NULLs)
2. ✅ **Integração dupla** (apenas PreSeparacao + Separacao) - mais simples
3. ✅ **Interface já implementada** - precisa apenas correção
4. ✅ **Sistema de alertas** mais simples que bloqueio

### **PRINCIPAIS DESAFIOS (REDUZIDOS):**
1. **Constraint única composta** com apenas 2 campos nullable (resolvível)
2. **Correção da interface** existente (não desenvolvimento do zero)
3. **Sistema de alertas** visuais básico
4. **Integração com estoque** simplificada

### **RECOMENDAÇÕES CRÍTICAS (ATUALIZADAS):**
1. **Implementar em fases** para reduzir riscos
2. **Analisar código existente** da interface antes de alterar
3. **Backup completo** antes das alterações de schema
4. **Foco em correção** ao invés de reescrita completa

### **TEMPO ESTIMADO FINAL:** 
- **Desenvolvimento:** 2,5 semanas (inclui lógica redução/aumento)
- **Testes:** 4 dias (cenários de sincronização Odoo)
- **TOTAL:** ~3 semanas

### **RISCO GERAL:** 🟢 **MÉDIO-BAIXO** (simplificação significativa, base já existe)

### **FATORES DE REDUÇÃO DE RISCO:**
- ✅ Interface já implementada
- ✅ Cálculo de estoque simplificado  
- ✅ Sistema de alertas ao invés de bloqueio
- ✅ Campo expedição obrigatório resolve constraint

---

*📅 Documento gerado em: 21/07/2025*  
*🔍 Análise baseada na arquitetura atual do sistema*  
*⚡ Foco em implementação segura e performática*