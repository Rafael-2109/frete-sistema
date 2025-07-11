# 📋 REGRAS DE ARQUITETURA - CLAUDE AI NOVO

**Versão**: 1.0  
**Data**: 2025-01-07  
**Objetivo**: Manter consistência arquitetural por responsabilidade única  

---

## 🎯 PRINCÍPIOS FUNDAMENTAIS

### **1. RESPONSABILIDADE ÚNICA (PRINCIPAL)**
- **Critério ÚNICO**: Organização por **RESPONSABILIDADE** (o que FAZ)
- **NÃO por domínio**: Evitar pastas como `data/`, `semantic/`, `intelligence/`
- **Verbos definem pastas**: `analyzers/`, `processors/`, `mappers/`, etc.

### **2. HIERARQUIA DE DECISÃO**
1. 🥇 **RESPONSABILIDADE** - O que o arquivo FAZ (critério principal)
2. 🥈 **COMPLEXIDADE** - Manager vs Worker vs Utility  
3. 🥉 **DOMÍNIO** - Apenas para especialização dentro da responsabilidade

---

## 📁 ESTRUTURA DE PASTAS OBRIGATÓRIA

### **Pastas por Responsabilidade:**
```
claude_ai_novo/
├── analyzers/          # ANALISAR (dados, consultas, intenções)
├── processors/         # PROCESSAR (dados, contexto, respostas)
├── mappers/           # MAPEAR (conceitos, campos, relacionamentos)
├── loaders/           # CARREGAR (dados, contexto, configurações)
├── validators/        # VALIDAR (dados, estruturas, regras)
├── enrichers/         # ENRIQUECER (dados, contexto, informações)
├── learners/          # APRENDER (padrões, comportamentos)
├── memorizers/        # MEMORIZAR (contexto, conhecimento)
├── conversers/        # GERENCIAR (conversas, diálogos)
├── orchestrators/     # ORQUESTRAR (processos complexos)
├── coordinators/      # COORDENAR (componentes, agentes)
├── providers/         # PROVER (dados, serviços)
├── integration/       # INTEGRAR (APIs, sistemas externos)
├── scanning/          # ESCANEAR (código, estruturas, metadados)
├── commands/          # EXECUTAR (comandos, ações)
├── tools/             # FERRAMENTAR (utilitários específicos)
├── suggestions/       # SUGERIR (recomendações)
├── utils/             # AUXILIAR (infraestrutura, helpers)
├── config/            # CONFIGURAR (parâmetros, settings)
├── security/          # PROTEGER (autenticação, validação)
├── tests/             # TESTAR (validação, testes unitários)
└── knowledge/         # BASE DE CONHECIMENTO (exceção por domínio)
```

### **❌ PASTAS PROIBIDAS (por domínio):**
- `data/` - Use `loaders/`, `providers/`, `mappers/`
- `semantic/` - Use responsabilidade específica
- `intelligence/` - Use `learners/`, `orchestrators/`
- `multi_agent/` - Use `coordinators/`, `orchestrators/`

---

## 📄 PADRÕES DE ARQUIVOS

### **1. NOMENCLATURA**
```python
# ✅ CORRETO - Responsabilidade clara
pedidos_analyzer.py      # Analisa pedidos
context_processor.py     # Processa contexto
semantic_mapper.py       # Mapeia semântica
data_validator.py        # Valida dados

# ❌ INCORRETO - Domínio primeiro
pedidos_data.py          # Ambíguo
semantic_system.py       # Muito genérico
intelligence_core.py     # Domínio primeiro
```

### **2. ESTRUTURA INTERNA**
```python
"""
Arquivo: analyzers/pedidos_analyzer.py
Responsabilidade: ANALISAR consultas relacionadas a pedidos
Autor: [Nome]
Data: [Data]
"""

# 1. IMPORTS PADRÃO
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# 2. IMPORTS LOCAIS (por responsabilidade)
from utils.base_classes import BaseAnalyzer
from mappers.pedidos_mapper import PedidosMapper
from validators.data_validator import DataValidator

# 3. CONFIGURAÇÃO LOGGING
logger = logging.getLogger(__name__)

# 4. CLASSES/FUNÇÕES
class PedidosAnalyzer(BaseAnalyzer):
    """Analisa consultas relacionadas a pedidos."""
    
    def __init__(self):
        super().__init__()
        self.mapper = PedidosMapper()
        self.validator = DataValidator()
    
    def analyze(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analisa consulta de pedidos."""
        logger.info(f"Analisando consulta de pedidos: {query[:50]}...")
        
        try:
            # Lógica de análise
            result = self._perform_analysis(query, context)
            logger.info("Análise de pedidos concluída com sucesso")
            return result
            
        except Exception as e:
            logger.error(f"Erro na análise de pedidos: {str(e)}")
            raise
```

### **3. MANAGERS OBRIGATÓRIOS**
- **Cada pasta DEVE ter um manager**
- **Manager coordena componentes da responsabilidade**
- **Não apenas delega - tem lógica inteligente**

```python
# analyzers/analyzer_manager.py
class AnalyzerManager:
    """Coordena diferentes tipos de análise."""
    
    def analyze_query(self, query: str, context: Optional[Dict[str, Any]] = None):
        # LÓGICA REAL DE COORDENAÇÃO:
        # 1. Detecta tipo de consulta
        # 2. Escolhe analyzer apropriado
        # 3. Aplica análises sequenciais se necessário
        # 4. Consolida resultados
```

---

## 🔗 PADRÕES DE IMPORTS

### **1. ORDEM OBRIGATÓRIA**
```python
# 1. Python padrão
import logging
import os
from typing import Dict, List, Optional, Any

# 2. Bibliotecas externas
import pandas as pd
import numpy as np
from flask import Flask

# 3. Imports locais por RESPONSABILIDADE (não por domínio)
from utils.base_classes import BaseProcessor
from analyzers.intention_analyzer import IntentionAnalyzer
from mappers.semantic_mapper import SemanticMapper
from validators.data_validator import DataValidator

# 4. NUNCA imports relativos complexos
# ❌ from ..semantic.mappers import PedidosMapper
# ✅ from mappers.pedidos_mapper import PedidosMapper
```

### **2. IMPORTS CIRCULARES - PREVENÇÃO**
```python
# ✅ CORRETO - Dependency Injection
class AnalyzerManager:
    def __init__(self, intention_analyzer: Optional[IntentionAnalyzer] = None):
        self.intention_analyzer = intention_analyzer or IntentionAnalyzer()

# ❌ INCORRETO - Import circular
from analyzers.analyzer_manager import AnalyzerManager  # NO TOPO
```

---

## 📝 PADRÕES DE LOGGING

### **1. CONFIGURAÇÃO OBRIGATÓRIA**
```python
import logging

# Em CADA arquivo
logger = logging.getLogger(__name__)

# Níveis por tipo de operação:
logger.debug("Detalhes técnicos")       # Desenvolvimento
logger.info("Operação normal")          # Fluxo principal  
logger.warning("Situação anômala")      # Atenção
logger.error("Erro recuperável")        # Problemas
logger.critical("Erro fatal")           # Sistema parado
```

### **2. MENSAGENS PADRONIZADAS**
```python
# ✅ PADRÃO OBRIGATÓRIO
logger.info(f"Iniciando análise de {tipo_consulta}: {query[:50]}...")
logger.info(f"Análise concluída - resultado: {len(result)} itens")
logger.error(f"Erro em {self.__class__.__name__}: {str(e)}")

# ❌ INCORRETO
logger.info("fazendo algo")              # Muito vago
logger.error(str(e))                     # Sem contexto
```

---

## 🔧 PADRÕES DE CONFIGURAÇÃO

### **1. ARQUIVO __init__.py OBRIGATÓRIO**
```python
# Em CADA pasta - exemplo: analyzers/__init__.py
"""
Módulo de análise - Responsabilidade: ANALISAR
Contém todos os componentes para análise de dados e consultas.
"""

from .analyzer_manager import AnalyzerManager
from .intention_analyzer import IntentionAnalyzer
from .query_analyzer import QueryAnalyzer

# Função de conveniência OBRIGATÓRIA
def get_analyzer_manager() -> AnalyzerManager:
    """Retorna instância configurada do AnalyzerManager."""
    return AnalyzerManager()

# Export explícito
__all__ = [
    'AnalyzerManager',
    'IntentionAnalyzer', 
    'QueryAnalyzer',
    'get_analyzer_manager'
]
```

### **2. CONFIGURAÇÃO DE MÓDULO**
```python
# config/module_config.py - Centraliza configurações
ANALYZER_CONFIG = {
    'timeout': 30,
    'max_retries': 3,
    'debug_mode': False
}

PROCESSOR_CONFIG = {
    'batch_size': 100,
    'parallel_processing': True
}
```

---

## ✅ VALIDAÇÕES OBRIGATÓRIAS

### **1. ANTES DE CRIAR ARQUIVO**
```bash
# VERIFICAR:
1. Qual responsabilidade principal? (verbo)
2. Pasta correta existe?
3. Não há conflito com domínio?
4. Manager da pasta existe?
5. __init__.py atualizado?
```

### **2. ANTES DE IMPORTS**
```bash
# VERIFICAR:
1. Import por responsabilidade, não domínio?
2. Ordem correta (padrão, externo, local)?
3. Não cria import circular?
4. Manager usado para coordenação?
```

### **3. ANTES DE COMMIT**
```bash
# VERIFICAR:
1. Logs padronizados?
2. Documentação atualizada?
3. Testes não quebrados?
4. __init__.py exports atualizados?
5. Configurações centralizadas?
```

---

## 🚨 REGRAS DE MIGRAÇÃO

### **1. MOVIMENTAÇÃO DE ARQUIVOS**
```bash
# ORDEM OBRIGATÓRIA:
1. Mover arquivo físico
2. Atualizar imports em arquivos dependentes  
3. Atualizar __init__.py origem e destino
4. Testar imports não quebraram
5. Verificar managers funcionam
6. Atualizar documentação
```

### **2. QUEBRA DE IMPORTS - SOLUÇÃO**
```python
# TEMPORÁRIO - Para compatibilidade durante migração
# utils/legacy_imports.py
from analyzers.semantic_diagnostics import SemanticDiagnostics
# Permite import antigo funcionar temporariamente
```

---

## 📊 MÉTRICAS DE QUALIDADE

### **1. INDICADORES OBRIGATÓRIOS**
- **Responsabilidade única**: 100% arquivos na pasta correta
- **Imports circulares**: 0 ocorrências
- **Managers funcionais**: 100% coordenam (não apenas delegam)  
- **Logs padronizados**: 100% arquivos com logger configurado
- **Documentação**: 100% arquivos com docstring responsabilidade

### **2. FERRAMENTAS DE VALIDAÇÃO**
```python
# scripts/validar_arquitetura.py - Executar sempre
def validar_estrutura():
    """Valida se arquitetura segue regras."""
    verificar_pastas_proibidas()
    verificar_imports_circulares() 
    verificar_managers_existem()
    verificar_logs_padronizados()
    verificar_documentacao_completa()
```

---

## 🎯 RESUMO EXECUTIVO

### **SEMPRE PERGUNTAR:**
1. **Qual a responsabilidade PRINCIPAL?** (verbo)
2. **Está na pasta da responsabilidade?**
3. **Manager coordena inteligentemente?**
4. **Imports seguem padrão responsabilidade?**
5. **Logs estão padronizados?**

### **NUNCA ACEITAR:**
- ❌ Pastas por domínio (`data/`, `semantic/`)
- ❌ Imports circulares
- ❌ Managers que só delegam
- ❌ Logs sem padrão
- ❌ Arquivos sem responsabilidade clara

### **SEMPRE APLICAR:**
- ✅ Princípio responsabilidade única
- ✅ Managers com lógica inteligente
- ✅ Imports por responsabilidade
- ✅ Logs estruturados
- ✅ Documentação clara

---

**🔒 REGRA DE OURO**: Quando em dúvida, **responsabilidade (verbo)** sempre vence **domínio (substantivo)**. 