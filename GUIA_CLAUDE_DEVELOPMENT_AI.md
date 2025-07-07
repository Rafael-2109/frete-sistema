# 🧠 Guia de Uso - Claude Development AI

## Capacidades Implementadas

### 🔍 Análise de Projeto
- **Comando:** "analisar projeto"
- **API:** `/claude-ai/dev-ai/analyze-project`
- **Funcionalidade:** Escaneia todo o projeto e gera relatório detalhado

### 📄 Análise de Arquivo
- **Comando:** "analisar arquivo app/models.py"
- **API:** `/claude-ai/dev-ai/analyze-file-v2`
- **Funcionalidade:** Analisa arquivo específico com métricas

### 🚀 Geração de Módulo
- **Comando:** "criar módulo vendas"
- **API:** `/claude-ai/dev-ai/generate-module-v2`
- **Funcionalidade:** Gera módulo Flask completo

### ✏️ Modificação de Arquivo
- **Comando:** "adicionar campo ao modelo"
- **API:** `/claude-ai/dev-ai/modify-file-v2`
- **Funcionalidade:** Modifica arquivos existentes

### 🔧 Detecção de Problemas
- **Comando:** "detectar problemas"
- **API:** `/claude-ai/dev-ai/detect-and-fix`
- **Funcionalidade:** Detecta e corrige problemas automaticamente

### 📚 Geração de Documentação
- **Comando:** "gerar documentação"
- **API:** `/claude-ai/dev-ai/generate-documentation`
- **Funcionalidade:** Gera documentação automática

### 📋 Listar Capacidades
- **Comando:** "capacidades" ou "o que você pode fazer"
- **API:** `/claude-ai/dev-ai/capabilities-v2`
- **Funcionalidade:** Lista todas as capacidades disponíveis

## Como Usar

### 1. No Chat do Claude AI
Digite consultas como:
- "Analisar o projeto completo"
- "Criar módulo de vendas com campos nome, email, telefone"
- "Detectar problemas de segurança"
- "Gerar documentação do projeto"

### 2. Via API REST
```javascript
// Análise de projeto
fetch('/claude-ai/dev-ai/analyze-project')

// Geração de módulo
fetch('/claude-ai/dev-ai/generate-module-v2', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        module_name: 'vendas',
        description: 'Módulo de vendas'
    })
})
```

### 3. Integração Automática
O Claude AI detecta automaticamente consultas sobre desenvolvimento e usa as ferramentas apropriadas.

## Arquivos Principais

- `claude_development_ai.py` - Sistema central
- `claude_project_scanner.py` - Escaneamento de projeto
- `claude_code_generator.py` - Geração de código
- `routes.py` - APIs REST

## Comandos de Teste

Execute o script de teste:
```bash
python test_claude_identity.py
```

## Solução de Problemas

1. **Erro de import:** Verifique se todos os arquivos estão presentes
2. **Erro de rota:** Verifique se não há duplicatas nas rotas
3. **Erro de permissão:** Certifique-se de ter permissões de escrita

## Próximos Passos

1. Teste as funcionalidades básicas
2. Customize conforme suas necessidades
3. Adicione novas capacidades conforme necessário
