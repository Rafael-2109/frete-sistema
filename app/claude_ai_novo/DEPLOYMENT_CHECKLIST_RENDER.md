# 📋 Checklist de Deploy do Claude AI Novo no Render

## ✅ Pré-Deploy

### 1. Configuração do Ambiente
- [ ] Configurar variável `ANTHROPIC_API_KEY` no Render
- [ ] Configurar variável `DATABASE_URL` (PostgreSQL)
- [ ] Configurar variável `USE_NEW_CLAUDE_SYSTEM=true`
- [ ] Configurar variável `FLASK_ENV=production`
- [ ] Configurar variável `PORT` (Render define automaticamente)
- [ ] Configurar `REDIS_URL` se usar cache Redis

### 2. Preparação do Código
- [ ] Executar script de correção de imports: `python app/claude_ai_novo/fix_all_imports.py`
- [ ] Verificar que todos os imports têm fallback
- [ ] Testar localmente com `USE_NEW_CLAUDE_SYSTEM=true`
- [ ] Confirmar que health checks estão funcionando

### 3. Dependências
- [ ] Adicionar `anthropic` ao requirements.txt
- [ ] Adicionar `psutil` para health checks
- [ ] Verificar versões das dependências
- [ ] Remover dependências desnecessárias

### 4. Banco de Dados
- [ ] Verificar que modelos SQLAlchemy estão corretos
- [ ] Testar conexão com PostgreSQL do Render
- [ ] Confirmar SSL está habilitado na conexão
- [ ] Executar migrações se necessário

## 🚀 Deploy

### 1. Configuração do Render
```yaml
# render.yaml
services:
  - type: web
    name: frete-sistema
    env: python
    buildCommand: "pip install -r requirements.txt"
    startCommand: "gunicorn app:app"
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.0
      - key: USE_NEW_CLAUDE_SYSTEM
        value: true
      - key: FLASK_ENV
        value: production
```

### 2. Health Checks no Render
- Path: `/api/claude-ai/health`
- Method: `GET`
- Expected Status: `200`
- Timeout: `30s`

### 3. Comandos de Build
```bash
# No build command do Render
pip install -r requirements.txt
python app/claude_ai_novo/fix_all_imports.py
```

## 📊 Pós-Deploy

### 1. Verificações Imediatas
- [ ] Acessar `/api/claude-ai/health` e verificar status
- [ ] Testar endpoint principal do Claude AI
- [ ] Verificar logs no Render Dashboard
- [ ] Confirmar conexão com banco de dados

### 2. Monitoramento
- [ ] Configurar alertas no Render
- [ ] Monitorar uso de memória e CPU
- [ ] Verificar latência das respostas
- [ ] Acompanhar logs de erro

### 3. Testes de Integração
- [ ] Testar consulta simples: "Quantas entregas hoje?"
- [ ] Testar consulta complexa com filtros
- [ ] Verificar geração de relatórios Excel
- [ ] Testar funcionalidades específicas do sistema

### 4. Rollback (se necessário)
- [ ] Desativar `USE_NEW_CLAUDE_SYSTEM`
- [ ] Reverter para commit anterior
- [ ] Analisar logs para identificar problema
- [ ] Corrigir e fazer novo deploy

## 🔧 Troubleshooting

### Problemas Comuns

1. **Import Errors**
   - Executar `fix_all_imports.py`
   - Verificar fallbacks nos imports

2. **Database Connection**
   - Verificar `DATABASE_URL`
   - Confirmar SSL habilitado
   - Testar com `psql $DATABASE_URL`

3. **Memory Issues**
   - Aumentar instância no Render
   - Otimizar cache
   - Reduzir workers do Gunicorn

4. **Claude API Errors**
   - Verificar `ANTHROPIC_API_KEY`
   - Confirmar limites de rate
   - Implementar retry logic

## 📝 Notas Importantes

1. **Segurança**
   - Nunca commitar API keys
   - Usar variáveis de ambiente
   - Habilitar HTTPS sempre

2. **Performance**
   - Cache Redis melhora resposta
   - Usar connection pooling
   - Otimizar queries SQL

3. **Logs**
   - Configurar log level apropriado
   - Usar structured logging
   - Monitorar erros críticos

## ✨ Comandos Úteis

```bash
# Verificar status local
curl http://localhost:5000/api/claude-ai/health

# Verificar status no Render
curl https://seu-app.onrender.com/api/claude-ai/health

# Logs em tempo real (Render CLI)
render logs --tail

# Executar comando no Render
render run python app/claude_ai_novo/test_sistema_simples.py
```

## 🎯 Critérios de Sucesso

- [ ] Health check retorna 200
- [ ] Sem erros nos logs
- [ ] Tempo de resposta < 3s
- [ ] Todas as funcionalidades testadas
- [ ] Sistema estável por 24h

---

**Última atualização:** 2025-01-26
**Versão:** 2.0.0