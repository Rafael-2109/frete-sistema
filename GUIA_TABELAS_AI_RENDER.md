# 🚀 GUIA: APLICAR TABELAS DE APRENDIZADO NO RENDER

## 📋 RESUMO

Este guia explica como criar as tabelas de aprendizado vitalício do Claude AI no PostgreSQL do Render.

## 🎯 OPÇÕES DISPONÍVEIS

### OPÇÃO 1: Via Console do Render (Recomendado)

1. **Acesse o Console do Render**
   - Vá para: https://dashboard.render.com
   - Acesse seu serviço: `frete-sistema`
   - Clique em "Shell" no menu lateral

2. **Execute o Script**
   ```bash
   python aplicar_tabelas_ai_render.py
   ```

3. **Verifique o Resultado**
   - O script mostrará o progresso
   - Confirmará quais tabelas foram criadas
   - Inserirá grupos empresariais iniciais

### OPÇÃO 2: Via Deploy Automático

1. **Faça Commit dos Arquivos**
   ```bash
   git add aplicar_tabelas_ai_render.py
   git add app/claude_ai/knowledge_base.sql
   git add app/claude_ai/lifelong_learning.py
   git commit -m "feat: Adicionar sistema de aprendizado vitalício Claude AI"
   git push origin main
   ```

2. **Modifique o build.sh Temporariamente**
   Adicione no final do arquivo `build.sh`:
   ```bash
   # Aplicar tabelas de IA (remover após primeira execução)
   python aplicar_tabelas_ai_render.py || echo "Tabelas já existem"
   ```

3. **Faça Deploy**
   - O Render executará automaticamente
   - Após sucesso, remova a linha do build.sh

### OPÇÃO 3: Via SQL Direto (Avançado)

1. **Acesse o PostgreSQL do Render**
   - Use a connection string do Render
   - Conecte via pgAdmin ou psql

2. **Execute o SQL**
   - Use o conteúdo de `app/claude_ai/knowledge_base.sql`
   - Execute comando por comando

## 📊 TABELAS QUE SERÃO CRIADAS

1. **ai_knowledge_patterns** - Padrões de consulta aprendidos
2. **ai_semantic_mappings** - Mapeamento de termos do usuário
3. **ai_learning_history** - Histórico de aprendizado
4. **ai_grupos_empresariais** - Grupos empresariais detectados
5. **ai_business_contexts** - Contextos de negócio
6. **ai_response_templates** - Templates de resposta
7. **ai_learning_metrics** - Métricas de performance

## 🔧 CONFIGURAÇÃO PÓS-INSTALAÇÃO

### 1. Configure a ANTHROPIC_API_KEY

No Render Dashboard:
- Environment → Add Environment Variable
- Key: `ANTHROPIC_API_KEY`
- Value: `sua-chave-api-anthropic`

### 2. Verifique os Logs

```bash
# No console do Render
tail -f logs/app.log | grep "aprendizado"
```

### 3. Teste o Sistema

No chat do Claude AI, pergunte:
- "Quantas entregas do Assai?"
- "Mostre pedidos pendentes"
- "Fretes sem CTE"

## 🚨 TROUBLESHOOTING

### Erro: "permission denied"
- Certifique-se de estar usando o usuário correto
- O Render gerencia permissões automaticamente

### Erro: "already exists"
- Normal se as tabelas já foram criadas
- O script é idempotente (pode rodar várias vezes)

### Erro: "syntax error"
- Verifique se está no PostgreSQL (não SQLite)
- Use o script específico para PostgreSQL

## 📈 MONITORAMENTO

### Verificar Aprendizado
```sql
-- Total de padrões aprendidos
SELECT COUNT(*) FROM ai_knowledge_patterns;

-- Grupos empresariais
SELECT nome_grupo, tipo_negocio FROM ai_grupos_empresariais;

-- Últimas interações
SELECT created_at, consulta_original 
FROM ai_learning_history 
ORDER BY created_at DESC 
LIMIT 10;
```

### Dashboard de Métricas
```sql
-- Performance por tipo de consulta
SELECT 
    metrica_tipo,
    AVG(metrica_valor) as media,
    COUNT(*) as total
FROM ai_learning_metrics
GROUP BY metrica_tipo;
```

## ✅ CHECKLIST FINAL

- [ ] Script executado com sucesso
- [ ] 7 tabelas criadas
- [ ] Grupos empresariais inseridos
- [ ] ANTHROPIC_API_KEY configurada
- [ ] Sistema testado com consultas reais

## 🎉 PRONTO!

Após seguir este guia, o Claude AI terá:
- 🧠 Memória permanente
- 📈 Aprendizado contínuo
- 🎯 Detecção inteligente de grupos
- 💡 Melhoria automática com uso

---

**Dúvidas?** O sistema agora aprende sozinho! Quanto mais usar, melhor fica. 