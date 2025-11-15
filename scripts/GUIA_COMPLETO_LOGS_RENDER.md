# 🔍 Guia Completo: Buscar Logs no Render

Você tem **3 opções oficiais** do Render para acessar logs:

1. **SSH** - Acesso direto ao container
2. **Log Streams** - Stream contínuo para serviços externos
3. **MCP Server** - Usar IA para consultar logs

---

## 🔐 OPÇÃO 1: SSH (Recomendado para Debug)

### Pré-requisitos
- ✅ Plano PRO (você já tem)
- ✅ SSH key configurada

### 1.1 Gerar SSH Key (se não tiver)

```bash
# Gerar chave SSH
ssh-keygen -t ed25519 -C "rafael@nacomgoya.com.br"

# Exibir chave pública
cat ~/.ssh/id_ed25519.pub
```

### 1.2 Adicionar no Render

1. Render Dashboard → Account Settings
2. "SSH Public Keys"
3. "+ Add SSH Public Key"
4. Colar o conteúdo de `~/.ssh/id_ed25519.pub`

### 1.3 Conectar via SSH

```bash
# Via Render CLI (mais fácil)
render ssh sistema-fretes

# Ou direto via SSH
ssh srv-d13m38vfte5s738t6p60@ssh.oregon.render.com
```

### 1.4 Buscar Logs Dentro do Container

Uma vez conectado via SSH:

```bash
# Ver logs da aplicação (se estiver usando arquivo)
tail -f /var/log/app.log

# Ou se logs vão para stdout/stderr
journalctl -u render-service -f

# Buscar webhooks
journalctl -u render-service | grep "WEBHOOK"

# Filtrar por tempo
journalctl -u render-service --since "1 hour ago" | grep "WEBHOOK"
```

**Limitações do SSH:**
- ⚠️ Apenas logs do container atual (não histórico completo)
- ⚠️ Sessão termina quando desconectar
- ✅ Útil para debug em tempo real

---

## 📡 OPÇÃO 2: Log Streams (Recomendado para Produção)

### O que é?
Stream contínuo de logs para serviços externos como **Datadog**, **Better Stack**, **Papertrail**.

### 2.1 Configurar Better Stack (Gratuito até 1GB/mês)

#### Passo 1: Criar conta no Better Stack
1. Acesse https://betterstack.com/logtail
2. Criar conta gratuita
3. Criar "Source" para Render
4. Copiar o endpoint (formato: `logs.betterstack.com:6514`)

#### Passo 2: Configurar no Render
1. Render Dashboard → Integrations → Observability
2. "Add Log Stream Destination"
3. Colar endpoint do Better Stack
4. Salvar

#### Passo 3: Buscar Logs no Better Stack
- Interface web com busca avançada
- Query language poderosa
- Dashboards e alertas
- API própria para consultas

**Exemplo de busca no Better Stack:**
```
# Via interface web
message:"WEBHOOK RECEBIDO"

# Via API
curl -X POST https://logtail.betterstack.com/api/v1/tail \
  -H "Authorization: Bearer <token>" \
  -d '{"query": "WEBHOOK RECEBIDO"}'
```

### 2.2 Alternativas ao Better Stack

#### Papertrail (Simples)
- Endpoint: `logs.papertrailapp.com:PORT`
- Gratuito até 50MB/mês
- Interface web simples

#### Datadog (Profissional)
- Mais completo
- APM + Logs + Métricas
- Trial 14 dias

---

## 🤖 OPÇÃO 3: MCP Server do Render

### O que é?
O Render tem um **MCP Server** que permite usar IA (Claude, Cursor) para consultar logs usando linguagem natural.

### 3.1 Configurar MCP

Adicionar ao `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "render": {
      "command": "npx",
      "args": ["-y", "@render-oss/mcp-server-render"],
      "env": {
        "RENDER_API_KEY": "rnd_IJGa5I7NlOsktvEwmIil1xljd3Xx",
        "RENDER_WORKSPACE": "tea-d01amimuk2gs73dhlup0"
      }
    }
  }
}
```

### 3.2 Usar via Claude Code

Uma vez configurado, você pode perguntar:

- "Show me webhook logs from the last 24 hours"
- "Find all rejected webhooks in sistema-fretes"
- "Search for NFe 12345 in logs"

---

## 🎯 COMPARAÇÃO DAS OPÇÕES

| Método | Quando Usar | Prós | Contras |
|--------|-------------|------|---------|
| **SSH** | Debug em tempo real | Acesso direto, rápido | Sem histórico, sessão temporária |
| **Log Streams** | Produção, análise | Histórico completo, busca avançada | Requer serviço externo |
| **MCP** | Consultas pontuais | Linguagem natural, integrado | Depende de configuração MCP |

---

## 🚀 RECOMENDAÇÃO PARA VOCÊ

### Setup Completo (Melhor dos 3 mundos)

1. **SSH** - Para debug urgente
2. **Better Stack** - Para histórico e análise
3. **MCP** - Para consultas rápidas via IA

### Passo a Passo

#### 1. Configurar SSH (5 minutos)
```bash
# Gerar key
ssh-keygen -t ed25519 -C "rafael@nacomgoya.com.br"

# Copiar chave pública
cat ~/.ssh/id_ed25519.pub

# Adicionar no Render Dashboard → SSH Public Keys

# Testar
render ssh sistema-fretes
```

#### 2. Configurar Better Stack (10 minutos)
1. Criar conta: https://betterstack.com/logtail
2. Criar source "Render Logs"
3. Copiar endpoint
4. Render → Integrations → Add Log Stream
5. Aguardar alguns minutos para logs aparecerem

#### 3. Configurar MCP (5 minutos)
```bash
# Instalar MCP Render
npm install -g @render-oss/mcp-server-render

# Configurar no Claude Code
# (adicionar JSON acima ao config)
```

---

## 📋 SCRIPTS PRÁTICOS

### Script 1: Buscar Webhooks via SSH
```bash
#!/bin/bash
# scripts/ssh_buscar_webhooks.sh

echo "🔍 Conectando via SSH..."
ssh srv-d13m38vfte5s738t6p60@ssh.oregon.render.com << 'ENDSSH'
  echo "📦 Buscando webhooks..."
  journalctl -u render-service --since "1 hour ago" | grep "WEBHOOK"
ENDSSH
```

### Script 2: Configurar Better Stack
Vou criar um script para facilitar:

```bash
#!/bin/bash
# scripts/configurar_betterstack.sh

echo "📡 Configurando Better Stack Log Stream"
echo ""
echo "1. Acesse: https://betterstack.com/logtail"
echo "2. Crie uma conta (gratuita)"
echo "3. Clique em 'Create Source' → 'Syslog'"
echo "4. Copie o endpoint (formato: logs.betterstack.com:XXXX)"
echo ""
read -p "Cole o endpoint aqui: " ENDPOINT

echo ""
echo "5. Agora configure no Render:"
echo "   - Dashboard → Integrations → Observability"
echo "   - Add Log Stream Destination"
echo "   - Cole: $ENDPOINT"
echo ""
echo "✅ Aguarde 5 minutos para logs começarem a aparecer"
```

---

## 🔍 CASOS DE USO PRÁTICOS

### Buscar webhook rejeitado (SSH)
```bash
render ssh sistema-fretes
# Dentro do SSH:
journalctl --since "1 hour ago" | grep "WEBHOOK REJEITADO"
```

### Rastrear NFe específica (Better Stack)
Interface web → Query:
```
message:"NFe.*12345"
```

### Consulta via MCP
No Claude Code:
```
"Show me all webhook errors from sistema-fretes in the last 24 hours"
```

---

## 📚 Documentação Oficial

- **SSH**: https://render.com/docs/ssh-keys
- **Log Streams**: https://render.com/docs/log-streams
- **MCP Server**: https://render.com/docs/mcp-server
- **API**: https://api-docs.render.com/reference/list-logs

---

## ⚡ Quick Start (30 segundos)

Quer testar agora? Execute:

```bash
# 1. Conectar via SSH
render ssh sistema-fretes

# 2. Ver logs em tempo real
journalctl -u render-service -f | grep WEBHOOK
```

**Quer que eu crie os scripts completos para SSH e Better Stack?**
