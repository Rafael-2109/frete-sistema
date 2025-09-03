# 🚀 Plano de Refatoração do Sistema de Estoque

## 📋 Resumo Executivo

**Objetivo**: Simplificar o cálculo de estoque eliminando tabelas intermediárias e triggers, substituindo por queries diretas otimizadas com índices adequados.

**Princípio**: "Dados em tempo real calculados sob demanda, não armazenados"

## 🔴 Estrutura Atual (PROBLEMA)

### Tabelas e Classes Envolvidas
1. **EstoqueTempoReal** - Tabela cache de saldo atual
2. **MovimentacaoPrevista** - Tabela cache de entradas/saídas futuras  
3. **SaldoEstoque** - Classe complexa de cálculo
4. **Triggers SQL** - 11 triggers diferentes atualizando as tabelas cache
5. **RecalculoMovimentacaoPrevista** - Classe de recálculo

### Fluxo Atual Complexo
```
MovimentacaoEstoque → Trigger → EstoqueTempoReal
Separacao → Trigger → MovimentacaoPrevista → RecalculoMovimentacaoPrevista
ProgramacaoProducao → Trigger → MovimentacaoPrevista
PreSeparacaoItem → Trigger → MovimentacaoPrevista
```

### Problemas Identificados
- **Sincronização**: Tabelas cache podem ficar dessincronizadas
- **Triggers Falhos**: "Session is already flushing" errors frequentes
- **Complexidade**: 500+ linhas de código de triggers
- **Performance**: Múltiplas escritas para cada operação
- **Manutenção**: Difícil debugar e corrigir problemas

## ✅ Nova Estrutura Proposta (SOLUÇÃO)

### Princípios
1. **Zero Cache**: Eliminar EstoqueTempoReal e MovimentacaoPrevista
2. **Queries Diretas**: Calcular tudo sob demanda
3. **Índices Otimizados**: Garantir performance < 100ms
4. **Código Simples**: Uma única classe de serviço

### Tabelas Fonte (já existentes)
```sql
-- 1. ESTOQUE ATUAL
MovimentacaoEstoque:
  - cod_produto (INDEX)
  - qtd_movimentacao 
  - status_nf != 'CANCELADO'
  - ativo = true

-- 2. SAÍDAS PREVISTAS  
Separacao:
  - cod_produto (INDEX)
  - qtd_saldo
  - expedicao (INDEX)
  - sincronizado_nf = false (INDEX)

-- 3. ENTRADAS PREVISTAS
ProgramacaoProducao:
  - cod_produto (INDEX)
  - qtd_programada
  - data_programacao (INDEX)
```

### Nova Classe de Serviço
```python
class ServicoEstoqueSimples:
    """
    Serviço único para todos os cálculos de estoque
    Sem triggers, sem cache, apenas queries otimizadas
    """
    
    @staticmethod
    def calcular_estoque_atual(cod_produto):
        """Query direta em MovimentacaoEstoque"""
        
    @staticmethod
    def calcular_saidas_previstas(cod_produto, data_inicio, data_fim):
        """Query direta em Separacao"""
        
    @staticmethod
    def calcular_entradas_previstas(cod_produto, data_inicio, data_fim):
        """Query direta em ProgramacaoProducao"""
        
    @staticmethod
    def calcular_projecao(cod_produto, dias=28):
        """Combina as 3 queries acima"""
```

## 📊 Índices Necessários

### MovimentacaoEstoque
```sql
-- Índice composto para estoque atual
CREATE INDEX idx_mov_estoque_produto_ativo_status 
ON movimentacao_estoque(cod_produto, ativo, status_nf)
WHERE ativo = true AND status_nf != 'CANCELADO';
```

### Separacao
```sql
-- Índice composto para saídas previstas
CREATE INDEX idx_separacao_produto_expedicao_sync 
ON separacao(cod_produto, expedicao, sincronizado_nf)
WHERE sincronizado_nf = false;

-- Índice de cobertura para evitar table lookup
CREATE INDEX idx_separacao_cobertura 
ON separacao(cod_produto, expedicao, qtd_saldo)
WHERE sincronizado_nf = false;
```

### ProgramacaoProducao
```sql
-- Índice composto para entradas previstas
CREATE INDEX idx_programacao_produto_data 
ON programacao_producao(cod_produto, data_programacao);

-- Índice de cobertura
CREATE INDEX idx_programacao_cobertura
ON programacao_producao(cod_produto, data_programacao, qtd_programada);
```

## 🔧 Implementação

### Fase 1: Criar Nova Estrutura (Sem Quebrar Existente)
1. Criar `ServicoEstoqueSimples` com métodos novos
2. Criar índices otimizados
3. Testar performance das queries

### Fase 2: Migração Gradual
1. Modificar APIs para usar nova estrutura com fallback
2. Atualizar workspace para usar novo serviço
3. Atualizar modais e outras interfaces

### Fase 3: Limpeza
1. Desativar triggers gradualmente
2. Remover tabelas EstoqueTempoReal e MovimentacaoPrevista
3. Remover código legado

## 📈 Queries Otimizadas

### 1. Estoque Atual (< 10ms)
```sql
SELECT 
    SUM(CASE 
        WHEN tipo_movimentacao = 'ENTRADA' THEN qtd_movimentacao
        ELSE -qtd_movimentacao 
    END) as estoque_atual
FROM movimentacao_estoque
WHERE cod_produto = :produto
  AND ativo = true
  AND (status_nf != 'CANCELADO' OR status_nf IS NULL);
```

### 2. Saídas Previstas por Dia (< 20ms)
```sql
SELECT 
    expedicao as data,
    SUM(qtd_saldo) as saida_prevista
FROM separacao
WHERE cod_produto = :produto
  AND sincronizado_nf = false
  AND expedicao BETWEEN :data_inicio AND :data_fim
GROUP BY expedicao
ORDER BY expedicao;
```

### 3. Entradas Previstas por Dia (< 20ms)
```sql
SELECT 
    data_programacao as data,
    SUM(qtd_programada) as entrada_prevista
FROM programacao_producao
WHERE cod_produto = :produto
  AND data_programacao BETWEEN :data_inicio AND :data_fim
GROUP BY data_programacao
ORDER BY data_programacao;
```

### 4. Projeção Completa (< 50ms total)
```python
def calcular_projecao(cod_produto, dias=28):
    # 1. Estoque atual (1 query)
    estoque_atual = calcular_estoque_atual(cod_produto)
    
    # 2. Movimentações futuras (2 queries paralelas)
    saidas = calcular_saidas_previstas(cod_produto, hoje, hoje + dias)
    entradas = calcular_entradas_previstas(cod_produto, hoje, hoje + dias)
    
    # 3. Montar projeção dia a dia (em memória, sem query)
    projecao = []
    saldo = estoque_atual
    
    for dia in range(dias + 1):
        data = hoje + timedelta(days=dia)
        entrada_dia = entradas.get(data, 0)
        saida_dia = saidas.get(data, 0)
        
        saldo = saldo + entrada_dia - saida_dia
        
        projecao.append({
            'dia': dia,
            'data': data,
            'entrada': entrada_dia,
            'saida': saida_dia,
            'saldo': saldo
        })
    
    return projecao
```

## 🎯 APIs Refatoradas

### /api/estoque/produto/<cod_produto>
```python
@bp.route('/api/estoque/produto/<cod_produto>')
def get_estoque_produto(cod_produto):
    """API simples e rápida"""
    return jsonify({
        'estoque_atual': ServicoEstoqueSimples.calcular_estoque_atual(cod_produto),
        'projecao': ServicoEstoqueSimples.calcular_projecao(cod_produto, dias=7)
    })
```

### /api/workspace/<num_pedido>/estoque
```python
@bp.route('/api/workspace/<num_pedido>/estoque')
def get_workspace_estoque(num_pedido):
    """Batch otimizado para múltiplos produtos"""
    produtos = get_produtos_pedido(num_pedido)
    
    # Paralelizar cálculos
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            produto.cod_produto: executor.submit(
                ServicoEstoqueSimples.calcular_projecao, 
                produto.cod_produto
            )
            for produto in produtos
        }
        
    resultados = {
        cod: future.result() 
        for cod, future in futures.items()
    }
    
    return jsonify(resultados)
```

## 📊 Métricas de Sucesso

### Performance
- ✅ Consulta única produto: < 50ms (atual: 100-200ms)
- ✅ Workspace 10 produtos: < 200ms (atual: 500-1000ms)  
- ✅ Dashboard ruptura: < 100ms (atual: 300-500ms)

### Confiabilidade
- ✅ Zero erros de sincronização
- ✅ Sem "Session flushing" errors
- ✅ Dados sempre em tempo real

### Manutenibilidade
- ✅ -70% linhas de código
- ✅ -100% triggers SQL
- ✅ 1 única classe de serviço

## 🔄 Plano de Rollback

### Fase 1 (Sem Risco)
- Nova estrutura coexiste com antiga
- Rollback: simplesmente não usar nova estrutura

### Fase 2 (Baixo Risco)
- Feature flags para cada endpoint
- Rollback: desativar feature flag

### Fase 3 (Médio Risco)
- Backup completo antes de remover tabelas
- Rollback: restaurar backup e reativar triggers

## 📅 Cronograma

### Semana 1
- [ ] Criar ServicoEstoqueSimples
- [ ] Implementar métodos de cálculo
- [ ] Criar índices no banco

### Semana 2
- [ ] Refatorar APIs com feature flags
- [ ] Testes de performance
- [ ] Ajustes de índices

### Semana 3
- [ ] Migrar workspace
- [ ] Migrar modais
- [ ] Validação em produção

### Semana 4
- [ ] Desativar triggers
- [ ] Remover código legado
- [ ] Documentação final

## 🚦 Próximos Passos

1. **Aprovar plano** com a equipe
2. **Criar branch** `refactor/estoque-queries-diretas`
3. **Implementar** ServicoEstoqueSimples
4. **Testar** performance em desenvolvimento
5. **Deploy** gradual com feature flags

## 📝 Notas Importantes

- **Unificação de Códigos**: Manter suporte via `UnificacaoCodigos.get_todos_codigos_relacionados()`
- **Cache Redis**: Considerar para o futuro se necessário (após otimização)
- **Monitoring**: Adicionar métricas de performance em cada endpoint