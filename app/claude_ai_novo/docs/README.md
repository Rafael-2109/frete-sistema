# 🤖 Claude AI - Módulo Reestruturado

## 📁 Estrutura Organizada

Este módulo foi completamente reestruturado para máxima modularidade e manutenibilidade.

### 🧠 Core (Núcleo)
- `claude_client.py` - Cliente único para Claude 4 Sonnet
- `query_processor.py` - Processador principal de consultas
- `response_formatter.py` - Formatação padronizada de respostas

### 🤖 Intelligence (Inteligência)
- `context_manager.py` - Contexto conversacional real
- `learning_system.py` - Aprendizado vitalício funcional
- `feedback_handler.py` - Human-in-the-loop efetivo

### 🔍 Analyzers (Análise)
- `query_analyzer.py` - Análise inteligente de consultas
- `intent_detector.py` - Detecção precisa de intenções
- `data_analyzer.py` - Análise específica de dados de frete

## 🚀 Como Usar

```python
from app.claude_ai_novo import ClaudeAI

# Inicializar
claude_ai = ClaudeAI(api_key="sua_api_key")

# Processar consulta
response = claude_ai.process_query(
    "Quantas entregas em atraso?",
    {"user_id": 123}
)

# Registrar feedback
claude_ai.record_feedback(
    query="...",
    response="...", 
    feedback={"type": "positive", "text": "Ótima resposta!"}
)
```

## 🔧 Vantagens da Nova Estrutura

- ✅ **Modular**: Cada componente tem responsabilidade específica
- ✅ **Testável**: Fácil criar testes unitários
- ✅ **Manutenível**: Localização rápida de funcionalidades
- ✅ **Escalável**: Suporta crescimento futuro
- ✅ **Performante**: Otimizado e eficiente
