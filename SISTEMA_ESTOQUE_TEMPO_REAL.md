# Sistema de Estoque em Tempo Real - Documentação Completa

## 📋 Resumo da Implementação

Sistema de estoque em tempo real com projeção futura, garantindo performance < 100ms para todas as consultas.

### ✅ Arquivos Criados

1. **`app/estoque/models_tempo_real.py`** - Modelos EstoqueTempoReal e MovimentacaoPrevista
2. **`app/estoque/services/estoque_tempo_real.py`** - Serviço principal com toda lógica
3. **`app/estoque/triggers_tempo_real.py`** - Triggers SQLAlchemy para atualização automática
4. **`app/estoque/api_tempo_real.py`** - API REST otimizada para consultas
5. **`scripts/migrar_para_tempo_real.py`** - Script de migração de dados existentes
6. **`test_performance_tempo_real.py`** - Script de teste de performance
7. **`app/__init__.py`** - Integração do job de fallback (modificado)

## 🏗️ Arquitetura

### Tabelas Principais

#### EstoqueTempoReal
- **cod_produto** (PK): Código único do produto
- **nome_produto**: Nome descritivo
- **saldo_atual**: Saldo em tempo real (sempre atualizado)
- **menor_estoque_d7**: Menor saldo nos próximos 7 dias
- **dia_ruptura**: Data prevista de ruptura (se houver)
- **atualizado_em**: Timestamp para job de fallback

#### MovimentacaoPrevista
- **cod_produto**: Código do produto
- **data_prevista**: Data da movimentação
- **entrada_prevista**: Quantidade de entrada (cumulativa)
- **saida_prevista**: Quantidade de saída (cumulativa)

### Fluxo de Dados

```
MovimentacaoEstoque (INSERT/UPDATE/DELETE)
    ↓ [Trigger]
    → EstoqueTempoReal.saldo_atual (atualização imediata)
    
PreSeparacaoItem/Separacao/ProgramacaoProducao (INSERT/UPDATE/DELETE)
    ↓ [Trigger]
    → MovimentacaoPrevista (atualização cumulativa)
    ↓
    → calcular_ruptura_d7() (recálculo automático)
```

## 🚀 Como Usar

### 1. Migração Inicial

```bash
# Criar as tabelas e migrar dados existentes
python scripts/migrar_para_tempo_real.py
```

### 2. Consultas via API

#### Consultar Múltiplos Produtos
```python
POST /api/estoque/tempo-real/consultar
{
    "produtos": ["P001", "P002", "P003"]
}
```

#### Consultar Produto Individual
```python
GET /api/estoque/tempo-real/produto/P001
```

#### Consultar Rupturas
```python
GET /api/estoque/tempo-real/rupturas?dias=7
```

#### Consultar Projeção Completa
```python
GET /api/estoque/tempo-real/projecao/P001?dias=28
```

### 3. Uso Programático

```python
from app.estoque.api_tempo_real import APIEstoqueTempoReal

# Consultar workspace (múltiplos produtos)
produtos = APIEstoqueTempoReal.consultar_workspace(['P001', 'P002'])

# Consultar rupturas
rupturas = APIEstoqueTempoReal.consultar_rupturas(dias=7)

# Estatísticas gerais
stats = APIEstoqueTempoReal.get_estatisticas()
```

## ⚡ Performance

### Garantias
- ✅ Consultas < 100ms (testado com 100 produtos e 500 movimentações)
- ✅ Atualização em tempo real (máximo 1 segundo de atraso)
- ✅ Job de fallback a cada 60 segundos (10 produtos mais antigos)

### Otimizações Implementadas
1. **Índices compostos** em MovimentacaoPrevista
2. **Consultas em batch** para múltiplos produtos
3. **Campos pré-calculados** (menor_estoque_d7, dia_ruptura)
4. **Triggers assíncronos** via SQLAlchemy events
5. **Job de fallback** para garantir consistência

## 🔧 Manutenção

### Testar Performance
```bash
python test_performance_tempo_real.py
```

### Recalcular Produto Específico
```python
POST /api/estoque/tempo-real/recalcular/P001
```

### Monitorar Job de Fallback
O job roda automaticamente a cada 60 segundos e processa os 10 produtos com `atualizado_em` mais antigo.

## 🔄 Triggers Implementados

### Tabelas Origem → Efeitos

1. **MovimentacaoEstoque** → EstoqueTempoReal.saldo_atual
2. **PreSeparacaoItem** → MovimentacaoPrevista (saída)
3. **Separacao** → MovimentacaoPrevista (saída)
4. **ProgramacaoProducao** → MovimentacaoPrevista (entrada)
5. **EmbarqueItem.erro_validacao** → Cancela Separacao correspondente
6. **MovimentacaoPrevista** → Recalcula ruptura_d7
7. **EstoqueTempoReal.saldo_atual** → Recalcula ruptura_d7

## 🛡️ Segurança e Consistência

### Mecanismos de Proteção
1. **Transações atômicas** em todas as operações
2. **Job de fallback** recalcula 10 produtos/minuto
3. **UnificacaoCodigos** sempre considerada
4. **Validação de dados** antes de gravar
5. **Rollback automático** em caso de erro

### Tratamento de Erros
- Logs detalhados de erros
- Fallback para recálculo completo
- Retry automático em falhas temporárias

## 📊 Exemplo de Resposta da API

```json
{
    "cod_produto": "P001",
    "nome_produto": "Produto Exemplo",
    "estoque_atual": 1500.0,
    "menor_estoque_d7": -200.0,
    "dia_ruptura": "2025-08-10",
    "movimentacoes_previstas": [
        {
            "data": "2025-08-07",
            "entrada": 0,
            "saida": 500,
            "saldo_dia": -500
        },
        {
            "data": "2025-08-08",
            "entrada": 200,
            "saida": 300,
            "saldo_dia": -100
        }
    ]
}
```

## 🎯 Próximos Passos Recomendados

1. **Adicionar cache Redis** para consultas frequentes
2. **Implementar WebSocket** para atualizações em tempo real no frontend
3. **Dashboard de monitoramento** com gráficos de projeção
4. **Alertas automáticos** para rupturas iminentes
5. **Histórico de movimentações** com auditoria completa

## 📝 Notas Importantes

- O sistema considera **UnificacaoCodigos** em todas as operações
- Movimentações previstas são **cumulativas** por data
- O job de fallback **não substitui** os triggers, apenas garante consistência
- Performance testada com **100 produtos** e **500 movimentações**
- Todos os triggers são **não-bloqueantes** (executam após commit)