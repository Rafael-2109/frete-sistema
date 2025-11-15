# 🔍 Guia Completo: Buscar Logs de Webhooks TagPlus

## 🎯 Objetivo
Facilitar a busca e análise de logs de webhooks do TagPlus no Render.

---

## ⚡ OPÇÃO 1: Render CLI (Mais Rápida)

### Instalação
```bash
# Instalar Render CLI
npm install -g @render-devs/cli

# Autenticar
render auth
```

### Comandos Prontos

#### Buscar webhooks recebidos hoje
```bash
render logs frete-sistema --tail 5000 | grep "🔔 WEBHOOK RECEBIDO"
```

#### Buscar webhooks de NFe
```bash
render logs frete-sistema --tail 5000 | grep "📦 WEBHOOK NFE"
```

#### Buscar webhooks rejeitados (erros de segurança)
```bash
render logs frete-sistema --tail 5000 | grep "🚫 WEBHOOK REJEITADO"
```

#### Buscar webhooks validados
```bash
render logs frete-sistema --tail 5000 | grep "✅ WEBHOOK VALIDADO"
```

#### Buscar webhooks das últimas 24h e salvar em arquivo
```bash
render logs frete-sistema --since 24h > logs_$(date +%Y%m%d).log
grep -E "WEBHOOK|🔔|📦|✅|🚫" logs_$(date +%Y%m%d).log
```

#### Buscar NFe específica
```bash
render logs frete-sistema --tail 5000 | grep -i "NFe.*12345"
```

#### Buscar payload completo recebido
```bash
render logs frete-sistema --tail 1000 | grep "Payload completo"
```

#### Buscar erros no processamento
```bash
render logs frete-sistema --tail 5000 | grep "Erro no webhook"
```

#### Buscar NFes processadas com sucesso
```bash
render logs frete-sistema --tail 5000 | grep "NF.*processada via webhook"
```

---

## 🐍 OPÇÃO 2: Script Python Customizado

### Configuração Inicial

1. **Obter credenciais do Render:**
   - API Key: Render Dashboard → Account Settings → API Keys
   - Service ID: URL do serviço (formato: `srv-xxxxx`)

2. **Configurar variáveis de ambiente:**

```bash
# Linux/Mac
export RENDER_API_KEY="rnd_xxxxxxxxxxxxxxxx"
export RENDER_SERVICE_ID="srv-xxxxxxxxxxxxxxxx"

# Ou adicionar ao ~/.bashrc ou ~/.zshrc
echo 'export RENDER_API_KEY="rnd_xxx"' >> ~/.bashrc
echo 'export RENDER_SERVICE_ID="srv_xxx"' >> ~/.bashrc
source ~/.bashrc
```

3. **Instalar dependências:**
```bash
pip install requests
```

### Uso do Script

#### Buscar webhooks das últimas 24h
```bash
python scripts/buscar_logs_webhooks.py --horas 24
```

#### Buscar apenas webhooks de NFe
```bash
python scripts/buscar_logs_webhooks.py --tipo nfe --horas 48
```

#### Buscar apenas webhooks rejeitados
```bash
python scripts/buscar_logs_webhooks.py --rejeitados
```

#### Buscar logs de uma NFe específica
```bash
python scripts/buscar_logs_webhooks.py --nfe 12345
```

#### Exibir log completo (verbose)
```bash
python scripts/buscar_logs_webhooks.py --verbose
```

#### Gerar estatísticas
```bash
python scripts/buscar_logs_webhooks.py --stats
```

#### Exportar para JSON
```bash
python scripts/buscar_logs_webhooks.py --exportar logs_webhooks.json
```

#### Combinar opções
```bash
python scripts/buscar_logs_webhooks.py --tipo nfe --horas 72 --stats --exportar nfes_72h.json
```

---

## 📊 Exemplos de Análise

### Investigar webhooks rejeitados
```bash
# Via CLI
render logs frete-sistema --since 24h | grep "WEBHOOK REJEITADO" -A 5

# Via script
python scripts/buscar_logs_webhooks.py --rejeitados --verbose
```

### Rastrear processamento de uma NFe
```bash
# Buscar todos os eventos da NFe 12345
python scripts/buscar_logs_webhooks.py --nfe 12345

# Resultado esperado:
# - Webhook recebido
# - Validação
# - Busca na API TagPlus
# - Processamento dos itens
# - Sincronização com carteira
```

### Monitorar webhooks em tempo real
```bash
# Monitorar continuamente
render logs frete-sistema --tail | grep --line-buffered "WEBHOOK"
```

### Análise de volume
```bash
# Contar webhooks por hora nas últimas 24h
render logs frete-sistema --since 24h | grep "WEBHOOK RECEBIDO" | cut -d' ' -f2 | cut -d':' -f1 | sort | uniq -c
```

---

## 🔍 Padrões de Busca Úteis

### Emojis usados no código
- `🔔` - Webhook recebido
- `📦` - Dados do webhook (NFe ou Cliente)
- `✅` - Webhook validado com sucesso
- `🚫` - Webhook rejeitado
- `🔐` - Validação de segurança
- `🔍` - Payload/Debug
- `❌` - Erro
- `⚠️` - Warning

### Buscar por padrão
```bash
# Todos os eventos de segurança
render logs frete-sistema --tail 5000 | grep -E "🔐|🔒|🚫"

# Todos os erros e warnings
render logs frete-sistema --tail 5000 | grep -E "❌|⚠️|ERROR"

# Fluxo completo de um webhook
render logs frete-sistema --tail 5000 | grep -E "WEBHOOK.*nfe.*12345" -A 10
```

---

## 🛠️ Troubleshooting

### Webhook não aparece nos logs
1. Verificar se o webhook foi enviado (checar TagPlus)
2. Verificar URL do webhook está correta
3. Verificar se aplicação está rodando

### Webhook rejeitado
```bash
# Buscar motivo
render logs frete-sistema --tail 5000 | grep "REJEITADO" -B 2 -A 2
```

Causas comuns:
- X-Hub-Secret incorreto
- X-TagPlus-Signature inválida
- Payload malformado

### NFe não processada
```bash
# Rastrear fluxo completo
python scripts/buscar_logs_webhooks.py --nfe <numero> --verbose
```

Verificar:
1. Webhook foi recebido?
2. Validação passou?
3. API TagPlus retornou dados?
4. Houve erro no processamento?

---

## 📈 Monitoramento Contínuo

### Script de alerta (opcional)
Criar um cron job para verificar webhooks rejeitados:

```bash
#!/bin/bash
# /home/user/monitor_webhooks.sh

REJEITADOS=$(render logs frete-sistema --since 1h | grep -c "WEBHOOK REJEITADO")

if [ "$REJEITADOS" -gt 0 ]; then
    echo "⚠️ $REJEITADOS webhooks rejeitados na última hora!"
    # Enviar alerta (email, Slack, etc)
fi
```

```bash
# Adicionar ao crontab (executar a cada hora)
crontab -e
0 * * * * /home/user/monitor_webhooks.sh
```

---

## 🎓 Dicas Avançadas

### Buscar tempo de processamento
```bash
# Extrair timestamps de início e fim
render logs frete-sistema --tail 5000 | grep -E "WEBHOOK RECEBIDO|processada via webhook" | grep "nfe.*12345"
```

### Analisar payloads
```bash
# Extrair payloads completos para análise
render logs frete-sistema --tail 5000 | grep "Payload completo" | sed 's/.*Payload completo recebido: //' > payloads.json
```

### Comparar estruturas
```bash
# Salvar múltiplos payloads e comparar
python scripts/buscar_logs_webhooks.py --tipo nfe --horas 168 --exportar nfes_semana.json
```

---

## 🆘 Precisa de Ajuda?

### Render CLI não funciona
```bash
# Verificar instalação
render --version

# Re-autenticar
render logout
render auth
```

### Script Python não funciona
```bash
# Verificar variáveis
echo $RENDER_API_KEY
echo $RENDER_SERVICE_ID

# Testar manualmente
curl -H "Authorization: Bearer $RENDER_API_KEY" \
     https://api.render.com/v1/services/$RENDER_SERVICE_ID/logs
```

---

## 📚 Recursos Adicionais

- **Render CLI Docs**: https://render.com/docs/cli
- **Render API Docs**: https://api-docs.render.com/reference/get-logs
- **Código dos Webhooks**: `app/integracoes/tagplus/webhook_routes.py`
- **Documentação TagPlus**: `app/integracoes/tagplus/DOCUMENTACAO_API_TAGPLUS.md`
