# 📚 Documentação Completa - Sistema Claude AI

## 🎯 Visão Geral

O Sistema Claude AI é uma integração avançada do Claude 4 Sonnet da Anthropic no sistema de fretes, oferecendo capacidades de processamento de linguagem natural, análise de dados e acesso inteligente a arquivos.

## 🏗️ Arquitetura do Sistema

### Componentes Principais

1. **ClaudeRealIntegration** (`claude_real_integration.py`)
   - Motor principal de integração com Claude 4 Sonnet
   - Gerencia contexto, comandos e respostas
   - Integra todos os subsistemas

2. **NLPEnhancedAnalyzer** (`nlp_enhanced_analyzer.py`)
   - Análise avançada de linguagem natural
   - Detecção de intenções e entidades
   - Suporte para SpaCy, NLTK e FuzzyWuzzy

3. **ClaudeProjectScanner** (`claude_project_scanner.py`)
   - Descoberta dinâmica de código e estrutura
   - Leitura segura de arquivos
   - Busca inteligente em código-fonte

4. **MultiAgentSystem** (`multi_agent_system.py`)
   - Sistema multi-agente para tarefas complexas
   - Agentes especializados por domínio
   - Coordenação entre agentes

## 🚀 Funcionalidades

### 1. **Processamento de Consultas**
- Análise de linguagem natural
- Detecção de intenções múltiplas
- Contexto conversacional

### 2. **Acesso a Arquivos**
```python
# Comandos disponíveis:
"listar arquivos em app/utils"
"verificar app/carteira/routes.py"
"buscar função processar_pedido"
"mostrar estrutura do projeto"
```

### 3. **Análise de Dados**
- Consultas sobre entregas, pedidos, fretes
- Geração de relatórios
- Estatísticas em tempo real

### 4. **Comandos de Desenvolvimento**
- Detecção automática de solicitações técnicas
- Acesso seguro ao código-fonte
- Sugestões de implementação

## ⚙️ Configuração

### Variáveis de Ambiente
```bash
# Produção (Render)
ANTHROPIC_API_KEY=sk-ant-api03-...

# Desenvolvimento (opcional)
export ANTHROPIC_API_KEY=sua_chave_aqui
```

### Modelo Configurado
- **Modelo**: Claude 4 Sonnet
- **ID**: `claude-sonnet-4-20250514`
- **Lançamento**: 14 de maio de 2025
- **Context Window**: 200K tokens

## 🔧 Uso

### Via Interface Web
1. Acesse `/claude-ai/chat`
2. Digite sua pergunta
3. Claude responderá com contexto completo

### Via API
```python
from app.claude_ai.claude_real_integration import ClaudeRealIntegration

claude = ClaudeRealIntegration()
resposta = await claude.processar_consulta_real(
    consulta="Quantas entregas temos pendentes?",
    user_context={"vendedor_codigo": "V123"}
)
```

## 🛠️ Manutenção

### Testes
```bash
# Teste completo do sistema
python test_claude_ai_completo.py

# Teste específico
python -c "from app.claude_ai.claude_real_integration import ClaudeRealIntegration; print('✅ OK')"
```

### Logs
- `logs/claude_ai.log` - Log principal
- `logs/multi_agent.log` - Sistema multi-agente
- `logs/mcp_v4_errors.log` - Erros do MCP

## 🔒 Segurança

1. **Acesso a Arquivos**
   - Apenas leitura, sem escrita
   - Restrito ao diretório do projeto
   - Extensões seguras (.py, .html, .js, .css)

2. **Validação de Entrada**
   - Sanitização de consultas
   - Prevenção de prompt injection
   - Rate limiting

3. **Contexto de Usuário**
   - Vendedores veem apenas seus dados
   - Admin tem acesso completo
   - Logs de auditoria

## 📊 Performance

- **Tempo de Resposta**: ~1-3s (modo normal)
- **Context Window**: 200K tokens
- **Cache**: Redis (produção) / Memória (dev)
- **Taxa de Sucesso**: 100% nos testes

## 🐛 Troubleshooting

### Erro: "ANTHROPIC_API_KEY não configurada"
**Solução**: Configure a variável de ambiente ou use em produção onde já está configurada.

### Erro: "Redis não disponível"
**Solução**: Normal em desenvolvimento. Em produção, Redis está configurado.

### Erro: "Resposta não disponível"
**Solução**: Verifique logs para detalhes. Geralmente é timeout ou erro de API.

## 🔄 Atualizações Recentes

1. **Claude 4 Sonnet** (Maio 2025)
   - Modelo mais recente da Anthropic
   - Melhor performance em coding
   - Extended thinking capabilities

2. **Melhorias no Sistema**
   - Resolvido imports circulares
   - NLP corrigido
   - System prompt simplificado
   - Detecção de intenções aprimorada
   - Project scanner integrado

## 📈 Roadmap

- [ ] Implementar cache mais eficiente
- [ ] Adicionar mais comandos de arquivo
- [ ] Melhorar detecção de contexto
- [ ] Integrar com mais módulos do sistema
- [ ] Adicionar suporte para geração de código

## 🤝 Contribuindo

1. Teste suas alterações com `test_claude_ai_completo.py`
2. Mantenha o system prompt simples
3. Documente novos comandos
4. Preserve a segurança de acesso a arquivos

## 📞 Suporte

- **Logs**: Verifique `logs/` para debug
- **Testes**: Execute o script de teste completo
- **Documentação**: Este arquivo e comentários no código

---

*Última atualização: Julho 2025*
*Sistema usando Claude 4 Sonnet - Versão mais recente disponível* 