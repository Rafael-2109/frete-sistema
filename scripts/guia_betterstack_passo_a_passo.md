# 📊 Guia Passo a Passo: Better Stack + Render

## ✅ CHECKLIST DE CONFIGURAÇÃO

- [ ] **PASSO 1:** Criar conta Better Stack
- [ ] **PASSO 2:** Criar Source para Render
- [ ] **PASSO 3:** Copiar endpoint syslog
- [ ] **PASSO 4:** Configurar Log Stream no Render
- [ ] **PASSO 5:** Aguardar 5 minutos
- [ ] **PASSO 6:** Validar que logs estão chegando
- [ ] **PASSO 7:** Fazer primeira busca de webhooks

---

## 🎯 PASSO 1: Criar Conta Better Stack

### Acessar:
👉 https://betterstack.com/logtail

### Ações:
1. Clique em **"Start Free Trial"** ou **"Sign Up"**
2. Email: `rafael@nacomgoya.com.br`
3. Senha: (escolha uma senha forte)
4. Confirmar email (checar caixa de entrada)

### ✅ Verificar:
- Você está logado no Better Stack
- Dashboard inicial apareceu

---

## 📡 PASSO 2: Criar Source para Render

### No Dashboard Better Stack:

1. **Clique em:** "Sources" (menu lateral esquerdo)

2. **Clique em:** "+ Connect source" (botão azul)

3. **Escolha:** "Syslog" (é o formato que o Render usa)

4. **Preencha:**
   - **Name:** `Render - Sistema Fretes`
   - **Platform:** `Render`

5. **Clique em:** "Create source"

### ✅ Verificar:
- Source foi criado
- Você vê uma tela com detalhes de conexão

---

## 🔗 PASSO 3: Copiar Endpoint

### Na tela de detalhes do Source:

Você verá algo assim:
```
Host: in.logs.betterstack.com
Port: 6514
```

### ⚠️ IMPORTANTE: Copie no formato COMPLETO:
```
in.logs.betterstack.com:6514
```

**Formato correto:** `HOST:PORT` (sem espaços, com os dois pontos)

### ✅ Verificar:
- Você copiou o endpoint completo (host + : + port)
- Exemplo: `in.logs.betterstack.com:6514`

**📋 Cole aqui para eu validar:**
```
Endpoint copiado: ___________________________
```

---

## 🚀 PASSO 4: Configurar Log Stream no Render

### Acessar Render Dashboard:
👉 https://dashboard.render.com

### Ações:

1. **Clique em:** "Account Settings" (canto superior direito, ícone de engrenagem)

2. **No menu lateral esquerdo, clique em:** "Integrations"

3. **Procure seção:** "Observability"

4. **Clique em:** "Add Log Stream Destination" ou "+ Add Destination"

5. **Preencha:**
   - **Destination:** Cole o endpoint que você copiou
     ```
     in.logs.betterstack.com:6514
     ```

   - **Token (opcional):** Deixe em branco (não precisa)

6. **Clique em:** "Save" ou "Add Destination"

### ✅ Verificar:
- Destino aparece na lista de log streams
- Status: "Active" ou "Configured"

---

## ⏳ PASSO 5: Aguardar Sincronização

### O que acontece agora:
1. Render começa a enviar logs para Better Stack
2. **Isso leva ~5 minutos** para começar

### Enquanto espera:
☕ Pode tomar um café!

### Timeline:
```
⏰ 0min  - Configuração salva
⏰ 1min  - Render estabelece conexão
⏰ 3min  - Primeiros logs começam a fluir
⏰ 5min  - Logs aparecem no Better Stack
```

---

## ✅ PASSO 6: Validar Logs

### Após 5 minutos:

1. **Volte ao Better Stack Dashboard**
   👉 https://betterstack.com

2. **Clique em:** "Live tail" ou "Logs" (menu lateral)

3. **Você deve ver logs aparecendo em tempo real!**

### ✅ O que você deve ver:
- Linhas de log do seu app Flask
- Timestamps recentes
- Mensagens variadas (INFO, WARNING, etc)

### ❌ Se não vir nada:
- Aguarde mais 2-3 minutos
- Verifique se endpoint está correto no Render
- Me avise se precisar de ajuda!

---

## 🔍 PASSO 7: Primeira Busca de Webhooks

### Agora vem a parte legal! 🎉

1. **No Better Stack, vá em:** "Search" ou "Logs"

2. **No campo de busca, digite:**
   ```
   WEBHOOK
   ```

3. **Pressione Enter**

### ✅ Você deve ver:
- Todos os logs que contêm "WEBHOOK"
- Incluindo:
  - 🔔 WEBHOOK RECEBIDO
  - 📦 WEBHOOK NFE
  - ✅ WEBHOOK VALIDADO
  - 🚫 WEBHOOK REJEITADO (se houver)

### 🎓 Buscas avançadas:

**Apenas webhooks rejeitados:**
```
WEBHOOK REJEITADO
```

**Webhooks de NFe:**
```
WEBHOOK NFE
```

**Webhooks das últimas 24h com "erro":**
```
WEBHOOK AND erro
```

**NFe específica:**
```
NFe 12345
```

---

## 🎯 QUERIES PRONTAS PARA COPIAR

Salve essas queries para usar depois:

### 1️⃣ Todos os webhooks recebidos hoje
```
WEBHOOK RECEBIDO
```

### 2️⃣ Webhooks rejeitados (problemas de segurança)
```
WEBHOOK REJEITADO
```

### 3️⃣ Webhooks de NFe processados com sucesso
```
processada via webhook
```

### 4️⃣ Erros no processamento
```
Erro no webhook
```

### 5️⃣ Buscar NFe específica (troque 12345 pelo número)
```
NFe 12345
```

### 6️⃣ Payload completo recebido
```
Payload completo recebido
```

### 7️⃣ Validações de segurança
```
WEBHOOK VALIDADO OR WEBHOOK REJEITADO
```

---

## 📊 RECURSOS AVANÇADOS

### Criar Dashboard

1. Better Stack → "Dashboards"
2. "Create Dashboard"
3. Adicionar widgets:
   - **Count:** Quantos webhooks/hora
   - **Timeline:** Linha do tempo de eventos
   - **Top values:** IPs mais frequentes

### Configurar Alertas

1. Better Stack → "Alerts"
2. "Create Alert"
3. Condição: `WEBHOOK REJEITADO`
4. Ação: Enviar email ou Slack
5. Salvar

**Exemplo:** Receber email se > 5 webhooks rejeitados em 1 hora

---

## 🆘 TROUBLESHOOTING

### Logs não aparecem após 10 minutos

**Verificar:**
1. Render Dashboard → Integrations → Log stream está "Active"?
2. Endpoint está correto? Formato: `host:port`
3. Aplicação está rodando?

**Testar:**
```bash
# Forçar log no Render
render logs sistema-fretes --tail 1

# Ver se app está ativo
render services list
```

### Logs aparecem mas não consigo buscar

**Dica:** Better Stack indexa logs após alguns segundos
- Aguarde 30s depois que log aparece
- Depois busque normalmente

### Busca não retorna resultados

**Verificar:**
1. Query está correta? (case-sensitive!)
2. Filtro de data está muito restrito?
3. Logs realmente existem? (checar no Live Tail)

---

## 🎉 PRÓXIMOS PASSOS

### Agora que está funcionando:

1. **Explorar interface:**
   - Live Tail (tempo real)
   - Search (buscar histórico)
   - Dashboards (visualizações)
   - Alerts (notificações)

2. **Criar suas queries favoritas:**
   - Salvar buscas frequentes
   - Criar shortcuts

3. **Configurar alertas:**
   - Webhook rejeitado
   - Erro crítico
   - Volume anormal

---

## 📚 DOCUMENTAÇÃO

- Better Stack Docs: https://betterstack.com/docs/logs
- Query Language: https://betterstack.com/docs/logs/query-language
- Render Log Streams: https://render.com/docs/log-streams

---

## ✅ CHECKLIST FINAL

Antes de considerar configurado, verifique:

- [x] Conta Better Stack criada
- [x] Source configurado
- [x] Endpoint copiado
- [x] Log Stream configurado no Render
- [x] Logs aparecem no Better Stack
- [x] Consegui buscar "WEBHOOK" com sucesso
- [x] Entendi como usar queries
- [ ] (Opcional) Criei dashboard
- [ ] (Opcional) Configurei alerta

---

## 🎓 DICAS PRO

### 1. Salvar queries frequentes
Better Stack permite criar "Saved Searches" para queries que você usa sempre.

### 2. Usar operadores lógicos
```
WEBHOOK AND (REJEITADO OR erro)
WEBHOOK NFE NOT teste
```

### 3. Filtrar por timestamp
Use a interface de calendário para selecionar período exato.

### 4. Exportar logs
Você pode exportar resultados em CSV/JSON para análise offline.

### 5. API do Better Stack
Você pode consultar logs programaticamente via API deles:
```bash
curl -X POST https://logtail.betterstack.com/api/v1/tail \
  -H "Authorization: Bearer SEU_TOKEN" \
  -d '{"query": "WEBHOOK REJEITADO"}'
```

---

**🎉 Parabéns! Você agora tem um sistema profissional de logs!**
