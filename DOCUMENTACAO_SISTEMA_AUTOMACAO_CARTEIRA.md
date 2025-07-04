# 🤖 DOCUMENTAÇÃO COMPLETA - SISTEMA DE AUTOMAÇÃO DA CARTEIRA

## 📋 **VISÃO GERAL**

O Sistema de Automação da Carteira foi projetado para tornar a gestão de pedidos **"extremamente dinâmica, funcional e eficiente"** através de 4 motores integrados:

1. **🎯 Classification Engine** - Classificação automática por urgência e tipo de cliente
2. **📊 Stock Analyzer** - Análise preditiva de estoque D0-D28
3. **📅 Scheduling Optimizer** - Otimização de agendamentos e geração de protocolos
4. **🚛 Cargo Optimizer** - Formação inteligente de cargas e detecção de inconsistências

---

## 🎯 **1. CLASSIFICATION ENGINE**

### **Funcionalidade**
Classifica automaticamente pedidos por urgência, tipo de cliente e características especiais.

### **Parâmetros Configuráveis**

```python
config = {
    'dias_critico': 7,        # ≤7 dias = CRÍTICO
    'dias_atencao': 15,       # 8-15 dias = ATENÇÃO  
    'valor_alto': 50000.0,    # Pedidos de alto valor (R$)
    'qtd_alta': 1000.0        # Quantidades altas (unidades)
}
```

### **Clientes Estratégicos** ⚠️ **AJUSTAR CONFORME SEU NEGÓCIO**

```python
clientes_estrategicos = {
    '06.057.223/',  # Assai
    '75.315.333/',  # Atacadão  
    '45.543.915/',  # Carrefour
    '01.157.555/'   # Tenda
}
```

### **Critérios de Classificação**

#### **Por Urgência (baseado em `data_entrega_pedido`)**
- **CRÍTICO**: ≤ 7 dias (cor: VERMELHO)
- **ATENÇÃO**: 8-15 dias (cor: AMARELO)
- **NORMAL**: > 15 dias (cor: VERDE)
- **SEM_PRAZO**: Sem data definida (cor: CINZA)

#### **Por Tipo de Cliente (baseado em `cliente_nec_agendamento`)**
- **COM_AGENDAMENTO**: "Sim" → Pipeline AGENDAMENTO
- **SEM_AGENDAMENTO**: "Não" → Pipeline EXPEDIÇÃO_LIVRE
- **INDEFINIDO**: Null/vazio → Pipeline MANUAL

#### **Características Especiais Detectadas**
- **ALTO_VALOR**: Valor total ≥ R$ 50.000
- **ALTA_QUANTIDADE**: Quantidade ≥ 1.000 unidades
- **CLIENTE_ESTRATEGICO**: CNPJ na lista de estratégicos
- **PRODUTO_ESPECIAL**: Categoria contém "ESPECIAL"
- **COM_SEPARACAO**: Já tem `lote_separacao_id`
- **COM_PROTOCOLO**: Já tem `protocolo` definido

### **Cálculo de Prioridade Geral**

```python
# Score base por urgência
scores_urgencia = {
    'CRITICO': 100,
    'ATENCAO': 70, 
    'NORMAL': 50,
    'SEM_PRAZO': 30,
    'ERRO': 10
}

# Bonus por características
if 'CLIENTE_ESTRATEGICO': score += 20
if 'ALTO_VALOR': score += 15
if 'COM_SEPARACAO': score += 10
if 'COM_PROTOCOLO': score += 5

# Níveis finais
if score >= 90: 'MAXIMA'
elif score >= 70: 'ALTA'
elif score >= 50: 'MEDIA'
else: 'BAIXA'
```

### **Pipelines Recomendados**
- **URGENTE**: Urgência CRÍTICA ou Prioridade MÁXIMA
- **AGENDAMENTO**: Cliente necessita agendamento
- **EXPEDICAO_LIVRE**: Expedição sem agendamento

---

## 📊 **2. STOCK ANALYZER**

### **Funcionalidade**
Analisa disponibilidade usando campos `estoque_d0` até `estoque_d28` para programar expedições otimizadas.

### **Parâmetros Configuráveis**

```python
config = {
    'margem_seguranca': 0.1,     # 10% margem de segurança
    'dias_alerta_ruptura': 3,    # Alertar rupturas em D+3
    'estoque_minimo': 1.0,       # Estoque mínimo considerado
    'projecao_maxima': 28        # Máximo D+28
}
```

### **Análise de Disponibilidade**

#### **Verificação Hoje (D0)**
- **Disponível**: `estoque_d0 >= qtd_saldo_produto_pedido`
- **Com Margem**: `estoque_d0 >= qtd_necessaria * 1.1`
- **% Atendimento**: `(estoque_atual / qtd_necessaria) * 100`

#### **Projeção D0-D28**
- Analisa cada campo `estoque_d{dia}` (0 a 28)
- Calcula primeira data disponível
- Identifica `menor_estoque_produto_d7`
- Detecta reposição programada

### **Situações de Estoque**
- **DISPONIVEL_SEGURO**: Disponível hoje com margem
- **DISPONIVEL_LIMITADO**: Disponível hoje sem margem  
- **AGUARDA_REPOSICAO_CURTA**: Disponível em ≤ 7 dias
- **AGUARDA_REPOSICAO_LONGA**: Disponível em > 7 dias
- **RUPTURA_CRITICA**: Sem reposição em 28 dias

### **Ações Recomendadas**
- **SEPARAR_IMEDIATAMENTE**: Estoque seguro
- **SEPARAR_COM_PRIORIZACAO**: Estoque limitado
- **PROGRAMAR_EXPEDICAO**: Aguarda reposição curta
- **REAGENDAR_ENTREGA**: Aguarda reposição longa
- **STANDBY_COMERCIAL**: Ruptura crítica

### **Riscos Identificados**
- **RUPTURA_D{X}**: Ruptura em dia específico
- **ESTOQUE_BAIXO_7_DIAS**: Menor estoque < mínimo em 7 dias
- **SEM_REPOSICAO_PROGRAMADA**: Sem entrada D1-D28
- **PRODUTO_CRITICO**: Categoria crítica/especial

### **Campos Atualizados Automaticamente**
- `menor_estoque_produto_d7`: Menor estoque em 7 dias
- `saldo_estoque_pedido`: Estoque na data de expedição
- `expedicao`: Data sugerida de expedição

---

## 📅 **3. SCHEDULING OPTIMIZER**

### **Funcionalidade**
Gera protocolos automáticos e otimiza datas de agendamento considerando disponibilidade e prioridades.

### **Parâmetros Configuráveis**

```python
config = {
    'dias_antecedencia_min': 1,      # Mínimo 1 dia
    'dias_antecedencia_max': 7,      # Máximo 7 dias
    'max_entregas_por_dia': 50,      # Limite por dia
    'prefixo_protocolo': 'AGD',      # Prefixo protocolos
    'dias_uteis_apenas': True,       # Só dias úteis
    'horarios_preferenciais': [      # Horários
        '08:00-12:00',
        '13:00-17:00'
    ]
}
```

### **Configurações por Tipo de Cliente**

```python
config_clientes = {
    'estrategico': {
        'prioridade': 1,
        'antecedencia_max': 3,    # Até 3 dias
        'slot_reservado': True
    },
    'agendamento_obrigatorio': {
        'prioridade': 2, 
        'antecedencia_max': 7,
        'slot_reservado': False
    },
    'sem_agendamento': {
        'prioridade': 3,
        'antecedencia_max': 7,
        'slot_reservado': False
    }
}
```

### **Critérios de Necessidade de Agendamento**
1. Campo `cliente_nec_agendamento == 'Sim'`
2. Cliente estratégico (CNPJ na lista)
3. Pedido de alto valor

### **Otimização de Data**
- **Janela**: Entre `data_expedicao_sugerida` e `data_entrega_pedido`
- **Ajuste por urgência**: CRÍTICO ≤ 3 dias, ATENÇÃO ≤ 5 dias
- **Score da data**: Penaliza distância, prioriza mid-week

### **Geração de Protocolo**
- **Formato**: `{PREFIXO}{TIMESTAMP}{SUFIXO}`
- **Exemplo**: `AGD202501151030ABC`
- **Timestamp**: YYYYMMDDHHMMSS + 3 chars aleatórios

### **Conflitos Detectados**
- **AGENDAMENTO_ANTES_ESTOQUE**: Data antes da disponibilidade
- **ESTOQUE_RUPTURA_CRITICA**: Sem estoque
- **PRAZO_ENTREGA_VENCIDO**: Data pedido vencida

### **Campos Atualizados**
- `protocolo`: Protocolo gerado
- `agendamento`: Data otimizada
- `data_entrega_pedido`: Se não existir

---

## 🚛 **4. CARGO OPTIMIZER**

### **Funcionalidade**
Forma embarques otimizados considerando `lote_separacao_id`, cancelamentos, inconsistências e justificativas para cargas parciais.

### **Parâmetros Configuráveis**

```python
config = {
    'peso_maximo_padrao': 25000.0,      # 25 toneladas ⚠️ AJUSTAR
    'volume_maximo_padrao': 80.0,       # 80m³ ⚠️ AJUSTAR
    'ocupacao_minima': 0.70,            # 70% ocupação mínima
    'ocupacao_ideal': 0.85,             # 85% ocupação ideal
    'max_paradas_rota': 8,              # Máximo 8 paradas
    'tolerancia_peso': 0.05,            # 5% tolerância
    'priorizar_agendamentos': True      # Priorizar agendados
}
```

### **Tipos de Carga**

```python
tipos_carga = {
    'TOTAL': {
        'descricao': 'Carga completa do pedido',
        'ocupacao_minima': 0.70,
        'justificativa_desnecessaria': True
    },
    'PARCIAL': {
        'descricao': 'Carga parcial do pedido', 
        'ocupacao_minima': 0.60,
        'justificativa_obrigatoria': True
    },
    'FRACIONADA': {
        'descricao': 'Múltiplos embarques',
        'ocupacao_minima': 0.50,
        'justificativa_obrigatoria': True
    }
}
```

### **Motivos para Cargas Parciais** ⚠️ **REVISAR CONFORME NEGÓCIO**

```python
motivos_carga_parcial = {
    'ESTOQUE_INSUFICIENTE': 'Estoque insuficiente para pedido completo',
    'CAPACIDADE_VEICULO': 'Capacidade não comporta pedido completo',
    'RESTRICAO_AGENDAMENTO': 'Restrição de agendamento impede total',
    'SEPARACAO_INCOMPLETA': 'Separação não finalizada',
    'CANCELAMENTO_PARCIAL': 'Cancelamento de NFs do pedido',
    'INCONSISTENCIA_FATURAMENTO': 'Inconsistência detectada',
    'CLIENTE_SOLICITOU': 'Solicitação específica do cliente',
    'URGENCIA_ENTREGA': 'Urgência - embarque parcial necessário'
}
```

### **Critérios de Agrupamento**
1. **Data de expedição/agendamento**: Mesmo dia
2. **Região de destino**: Mesmo estado (`estado`)
3. **Prioridade**: Mesmo nível de urgência
4. **Agendamento**: Mesma necessidade
5. **Situação estoque**: Compatível

### **Regras de Compatibilidade**
- **Peso**: Total ≤ peso máximo configurado
- **Destino**: Mesmo estado
- **Data**: Diferença ≤ 1 dia
- **Estoque**: Não incluir rupturas críticas
- **Lote separação**: Mesmo `lote_separacao_id` ou sem conflito

### **Inconsistências Detectadas**
- **QUANTIDADE_ZERADA**: `qtd_produto_pedido ≤ 0`
- **PRECO_ZERADO**: `preco_produto_pedido ≤ 0`
- **CRITICO_SEM_DATA**: Crítico sem `data_entrega_pedido`
- **DATA_VENCIDA**: `data_entrega_pedido < hoje`
- **RUPTURA_CRITICA**: Estoque em ruptura crítica

---

## ⚙️ **CONFIGURAÇÕES CRÍTICAS PARA SEU NEGÓCIO**

### **1. Clientes Estratégicos** ⚠️ **URGENTE - AJUSTAR**

```python
# ALTERAR CONFORME SEUS CLIENTES PRINCIPAIS
clientes_estrategicos = {
    '06.057.223/',  # Substituir pelos CNPJs dos seus TOP clientes
    '75.315.333/',  # Exemplo: grandes redes, VIPs, etc.
    '45.543.915/',  
    '01.157.555/'
}
```

### **2. Capacidades de Veículos** ⚠️ **URGENTE - AJUSTAR**

```python
# ALTERAR CONFORME SUA FROTA
config = {
    'peso_maximo_padrao': 25000.0,      # Seu limite real em KG
    'volume_maximo_padrao': 80.0,       # Seu limite real em M³
    'ocupacao_minima': 0.70,            # % mínima para viabilidade
    'ocupacao_ideal': 0.85,             # % ideal para otimização
}
```

### **3. Prazos e Urgências** ⚠️ **REVISAR**

```python
# AJUSTAR CONFORME SUA OPERAÇÃO
config = {
    'dias_critico': 7,        # Quantos dias = CRÍTICO?
    'dias_atencao': 15,       # Quantos dias = ATENÇÃO?
    'valor_alto': 50000.0,    # Qual valor = ALTO?
    'qtd_alta': 1000.0        # Qual quantidade = ALTA?
}
```

### **4. Horários de Agendamento** ⚠️ **REVISAR**

```python
# AJUSTAR CONFORME SEU HORÁRIO DE FUNCIONAMENTO
'horarios_preferenciais': [
    '08:00-12:00',  # Manhã
    '13:00-17:00'   # Tarde
]
```

### **5. Prefixos e Códigos** ⚠️ **PERSONALIZAR**

```python
'prefixo_protocolo': 'AGD',  # Prefixo dos seus protocolos
'max_entregas_por_dia': 50,  # Sua capacidade diária
'dias_uteis_apenas': True,   # Trabalha fins de semana?
```

---

## 📊 **CAMPOS DO MODELO UTILIZADOS**

### **Campos Lidos pelo Sistema**
```python
# CHAVES PRIMÁRIAS
- num_pedido
- cod_produto

# CLASSIFICAÇÃO
- data_entrega_pedido        # Para urgência
- cliente_nec_agendamento    # Para tipo cliente
- cnpj_cpf                   # Para clientes estratégicos
- preco_produto_pedido       # Para valor alto
- qtd_produto_pedido         # Para quantidade alta
- categoria_produto          # Para produtos especiais

# ESTOQUE (29 campos)
- estoque_d0, estoque_d1, ..., estoque_d28
- qtd_saldo_produto_pedido   # Quantidade necessária

# DADOS OPERACIONAIS
- lote_separacao_id          # Vinculação separação
- protocolo                  # Protocolo existente
- agendamento               # Data agendamento
- expedicao                 # Data expedição
- peso                      # Para cálculo carga
- estado                    # Para agrupamento

# CLIENTE
- raz_social_red            # Nome cliente
- nome_produto              # Nome produto
- observ_ped_1              # Observações
```

### **Campos Atualizados pelo Sistema**
```python
# ESTOQUE ANALYZER
- menor_estoque_produto_d7   # Calculado automaticamente
- saldo_estoque_pedido       # Estoque na data expedição
- expedicao                  # Data sugerida expedição

# SCHEDULING OPTIMIZER  
- protocolo                  # Protocolo gerado
- agendamento               # Data otimizada
- data_entrega_pedido       # Se não existir
```

---

## 🔄 **FLUXO DE EXECUÇÃO**

### **1. Trigger: Importação da Carteira**
```python
# Na função importar_carteira()
if resultado['sucesso'] and resultado['total_processados'] > 0:
    resultado_automacao = _aplicar_automacao_carteira_completa(usuario)
```

### **2. Sequência de Processamento**
```python
# ETAPA 1: Classificação (3-5s para 1000 itens)
classification_engine = ClassificationEngine()
classificacoes = classification_engine.classificar_lote(itens_carteira)

# ETAPA 2: Análise Estoque (5-8s para 1000 itens)  
stock_analyzer = StockAnalyzer()
analises_estoque = stock_analyzer.analisar_lote_estoque(itens_carteira)

# ETAPA 3: Agendamentos (2-4s para 1000 itens)
scheduling_optimizer = SchedulingOptimizer()
agendamentos = scheduling_optimizer.otimizar_lote_agendamentos(...)

# ETAPA 4: Cargas (8-12s para 1000 itens)
cargo_optimizer = CargoOptimizer()
cargas = cargo_optimizer.otimizar_formacao_carga(...)
```

### **3. Resultado Final**
```python
# Resumo executivo exibido no flash
resumo = "150 itens: 12 críticos, 89 disponíveis hoje, 5 protocolos gerados, 8 cargas (82.5% ocupação)"
```

---

## 🎯 **PRÓXIMOS PASSOS PARA IMPLEMENTAÇÃO**

### **FASE 1: Configuração (1-2 dias)**
1. ⚠️ **URGENTE**: Ajustar lista de clientes estratégicos
2. ⚠️ **URGENTE**: Configurar capacidades reais dos veículos
3. ⚠️ **URGENTE**: Revisar prazos e valores de negócio
4. ⚠️ **URGENTE**: Validar horários de funcionamento

### **FASE 2: Testes (3-5 dias)**
1. Importar carteira pequena (50-100 itens)
2. Analisar resultados da automação
3. Ajustar parâmetros conforme necessário
4. Validar com equipe operacional

### **FASE 3: Ajustes Finos (5-7 dias)**
1. Calibrar algoritmos baseado nos testes
2. Adicionar regras específicas do negócio
3. Implementar exceções necessárias
4. Otimizar performance se necessário

### **FASE 4: Produção (1-2 dias)**
1. Ativar automação na importação
2. Treinar usuários nos novos recursos
3. Monitorar resultados primeiros dias
4. Documentar procedimentos operacionais

---

## 🚨 **ATENÇÃO: PARÂMETROS QUE PRECISAM REVISÃO URGENTE**

| Parâmetro | Valor Atual | ⚠️ Revisar |
|-----------|-------------|------------|
| `clientes_estrategicos` | CNPJs exemplo | **SIM - Usar seus clientes TOP** |
| `peso_maximo_padrao` | 25.000 kg | **SIM - Capacidade real da frota** |
| `volume_maximo_padrao` | 80 m³ | **SIM - Volume real dos veículos** |
| `dias_critico` | 7 dias | **TALVEZ - Seu prazo crítico** |
| `valor_alto` | R$ 50.000 | **TALVEZ - Seu ticket médio** |
| `horarios_preferenciais` | 8-12, 13-17 | **TALVEZ - Seu horário de entrega** |
| `max_entregas_por_dia` | 50 | **TALVEZ - Sua capacidade diária** |

---

## 📈 **BENEFÍCIOS ESPERADOS**

### **Operacionais**
- ⚡ **80%+ pedidos processados automaticamente**
- 🎯 **Priorização inteligente por criticidade**  
- 📅 **Agendamentos otimizados automaticamente**
- 🚛 **Cargas com 85%+ ocupação média**
- ⚠️ **Detecção automática de inconsistências**

### **Estratégicos**
- 📊 **Visibilidade completa do pipeline**
- 🔄 **Processo padronizado e escalável**
- 📈 **Métricas automáticas de performance**
- 🎛️ **Gestão por exceção (focar só nos problemas)**
- 💡 **Insights automáticos para tomada de decisão**

### **ROI Estimado**
- 💰 **60% redução tempo processamento carteira**
- 🚀 **40% melhoria ocupação de cargas**  
- ⚡ **85% redução erros de agendamento**
- 📊 **90% automação de tarefas repetitivas**

---

## 🛠️ **ARQUIVO DE CONFIGURAÇÃO SUGERIDO**

Recomendo criar um arquivo `config/automacao_carteira.py`:

```python
# config/automacao_carteira.py
AUTOMACAO_CONFIG = {
    # 🏢 CLIENTES ESTRATÉGICOS - AJUSTAR!
    'clientes_estrategicos': {
        'SEU_CLIENTE_1_CNPJ/',
        'SEU_CLIENTE_2_CNPJ/',
        'SEU_CLIENTE_3_CNPJ/',
    },
    
    # 🚛 CAPACIDADES - AJUSTAR!
    'capacidades': {
        'peso_maximo_padrao': 25000.0,  # KG
        'volume_maximo_padrao': 80.0,   # M³
        'ocupacao_minima': 0.70,
        'ocupacao_ideal': 0.85,
    },
    
    # ⏰ PRAZOS - REVISAR!
    'prazos': {
        'dias_critico': 7,
        'dias_atencao': 15,
        'valor_alto': 50000.0,
        'qtd_alta': 1000.0,
    },
    
    # 📅 AGENDAMENTOS - AJUSTAR!
    'agendamentos': {
        'horarios_preferenciais': ['08:00-12:00', '13:00-17:00'],
        'max_entregas_por_dia': 50,
        'prefixo_protocolo': 'AGD',
        'dias_uteis_apenas': True,
    }
}
```

---

**🎯 Este documento serve como base para configurar o sistema conforme suas necessidades específicas. Analise cada parâmetro e ajuste conforme a realidade do seu negócio!**
