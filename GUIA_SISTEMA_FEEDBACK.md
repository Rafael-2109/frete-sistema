# 🎯 GUIA DO SISTEMA DE FEEDBACK AVANÇADO

## ✅ CORREÇÃO APLICADA

### **PROBLEMA IDENTIFICADO:**
- Sistema estava recebendo tipo `'error'` mas o enum `FeedbackType` não possuía esse valor
- Erro: `'error' is not a valid FeedbackType`

### **SOLUÇÃO IMPLEMENTADA:**

1. **Mapeamento de Tipos** (`routes.py`):
```python
feedback_type_mapping = {
    'general': 'improvement',
    'error': 'bug_report',     # Mapeamento corrigido
    'excellent': 'positive',
    'good': 'positive',
    'improvement': 'improvement',
    'correction': 'correction',
    'negative': 'negative',
    'bug': 'bug_report',
    'bug_report': 'bug_report',
    'positive': 'positive'
}
```

2. **Template Atualizado** (`advanced_feedback.html`):
```html
<!-- ANTES -->
<button data-type="error">Erro</button>

<!-- DEPOIS -->
<button data-type="bug_report">Bug/Erro</button>
```

## 📊 TIPOS DE FEEDBACK VÁLIDOS

### **Enum FeedbackType:**
1. **`positive`** - Feedback positivo (⭐⭐⭐⭐⭐)
2. **`negative`** - Feedback negativo (⭐)
3. **`correction`** - Correção necessária (⭐⭐)
4. **`improvement`** - Sugestão de melhoria (⭐⭐⭐)
5. **`bug_report`** - Reporte de bug/erro (⭐)

### **Mapeamento de Avaliação:**
```sql
CASE 
    WHEN feedback_type = 'positive' THEN 5
    WHEN feedback_type = 'improvement' THEN 3
    WHEN feedback_type = 'correction' THEN 2
    WHEN feedback_type = 'negative' THEN 1
    WHEN feedback_type = 'bug_report' THEN 1
    ELSE 3
END
```

## 🚀 COMO USAR O SISTEMA

### **1. Interface de Feedback (`/claude-ai/advanced-feedback`)**
- Avaliação por estrelas (1-5)
- Seleção do tipo de feedback
- Comentário detalhado
- Categorias específicas (para improvement/bug_report)
- Sugestões de melhoria

### **2. API de Feedback (`/api/advanced-feedback`)**
```javascript
POST /claude-ai/api/advanced-feedback
{
    "session_id": "feedback_1750890306908",
    "query": "consulta original",
    "response": "resposta da IA",
    "rating": 4,
    "type": "improvement",  // Usar valores válidos!
    "feedback": "Texto do feedback",
    "improvement_suggestions": "Sugestões"
}
```

### **3. Dashboard Analytics (`/claude-ai/advanced-dashboard`)**
- Visualização de feedbacks por tipo
- Métricas de satisfação
- Análise temporal
- Padrões de aprendizado

## 🔍 MONITORAMENTO

### **Logs Importantes:**
```python
logger.info(f"📝 FEEDBACK AVANÇADO registrado: {session_id} -> {feedback_type}")
logger.info(f"💡 Feedback capturado: {feedback_id} - {feedback_type}")
```

### **Verificação no Banco:**
```sql
-- Verificar feedbacks recentes
SELECT feedback_type, COUNT(*) 
FROM ai_feedback_history 
WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY feedback_type;

-- Verificar tipos inválidos (não deve retornar nada)
SELECT * FROM ai_feedback_history 
WHERE feedback_type NOT IN ('positive','negative','correction','improvement','bug_report');
```

## 💡 FLUXO DO FEEDBACK

1. **Usuário** → Seleciona tipo no frontend
2. **Frontend** → Envia tipo (pode ser 'error', 'excellent', etc)
3. **Backend** → Mapeia para enum válido
4. **Sistema** → Armazena com tipo correto
5. **Analytics** → Calcula métricas corretamente

## 🛠️ TROUBLESHOOTING

### **Se ainda aparecer erro de FeedbackType:**
1. Verificar se o mapeamento está funcionando
2. Checar logs para ver qual tipo está sendo recebido
3. Garantir que o template está atualizado
4. Limpar cache do navegador

### **Comandos Úteis:**
```bash
# Verificar tipos no banco
python -c "
from app import db
from sqlalchemy import text
result = db.session.execute(text('SELECT DISTINCT feedback_type FROM ai_feedback_history'))
print([r[0] for r in result])
"

# Corrigir tipos antigos (se necessário)
python -c "
from app import db
from sqlalchemy import text
db.session.execute(text(\"UPDATE ai_feedback_history SET feedback_type='bug_report' WHERE feedback_type='error'\"))
db.session.commit()
"
```

## ✨ RESULTADO ESPERADO

Agora o sistema deve:
- ✅ Aceitar todos os tipos de feedback sem erro
- ✅ Mapear corretamente tipos do frontend
- ✅ Calcular métricas de satisfação
- ✅ Mostrar analytics corretas
- ✅ Aplicar aprendizado contínuo

---
*Sistema de Feedback Avançado v2.0 - Com Human-in-the-Loop Learning* 