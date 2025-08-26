z# 🔧 GUIA DE INTEGRAÇÃO DOS BOTÕES ASSÍNCRONOS

## 📍 LOCALIZAÇÃO DOS BOTÕES ENCONTRADOS:

### 1. **listar_entregas.html** (linha 1710)
- Função: `agendarNoPortalAtacadao()`
- Endpoint atual: `/portal/api/solicitar-agendamento-nf`

### 2. **workspace-montagem.js** (linha 1478)
- Função: `agendarNoPortal()`
- Endpoint atual: `/portal/api/solicitar-agendamento`

---

## ✅ COMO INTEGRAR (SUPER SIMPLES!)

### **MÉTODO 1: Adicionar Script Global (RECOMENDADO)**

Adicione esta linha no arquivo `app/templates/base.html` antes do `</body>`:

```html
<!-- Sistema de Agendamento Assíncrono -->
<script src="{{ url_for('static', filename='js/portal-async-integration.js') }}"></script>
```

**OU** se não tiver base.html, adicione em cada template:

### **Em `app/templates/monitoramento/listar_entregas.html`:**

Adicione antes do `</body>`:
```html
<!-- Sistema de Agendamento Assíncrono com Redis Queue -->
<script src="{{ url_for('static', filename='js/portal-async-integration.js') }}"></script>
```

### **Em `app/templates/carteira/agrupados_balanceado.html`:**

Adicione após o script do workspace:
```html
<!-- Workspace original -->
<script src="{{ url_for('static', filename='carteira/js/workspace-montagem.js') }}"></script>

<!-- Sistema Assíncrono (substitui automaticamente as funções) -->
<script src="{{ url_for('static', filename='js/portal-async-integration.js') }}"></script>
```

---

## 🎯 O QUE ACONTECE AUTOMATICAMENTE:

O script `portal-async-integration.js` faz a **substituição automática**:

1. **Detecta** se as funções antigas existem
2. **Substitui** por versões assíncronas
3. **Mantém** a mesma interface (não quebra nada!)

```javascript
// ANTES (síncrono - trava navegador):
agendarNoPortalAtacadao(entregaId, numeroNf)
↓
// DEPOIS (assíncrono - processa em background):
agendarNoPortalAtacadaoAsync(entregaId, numeroNf)
```

---

## 🚀 TESTANDO A INTEGRAÇÃO:

### **1. No Console do Browser (F12):**

```javascript
// Deve aparecer:
// ✅ Sistema de Agendamento Assíncrono carregado
// 📦 Redis Queue habilitado para processamento em background
```

### **2. Verificar se funções foram substituídas:**

```javascript
console.log(typeof agendarNoPortalAtacadaoAsync)  // 'function'
console.log(typeof agendarNoPortalAsync)          // 'function'
```

### **3. Testar um agendamento:**

1. Clique em qualquer botão de "Agendar"
2. Deve aparecer loading com progresso
3. Não trava o navegador!
4. Mostra resultado com SweetAlert

---

## 🔥 ATIVAÇÃO RÁPIDA (COPIAR E COLAR):

### **Para listar_entregas.html:**

Encontre a linha (aproximadamente 2213):
```html
</script>
```

Adicione LOGO APÓS:
```html
<!-- Sistema Assíncrono Redis Queue -->
<script src="{{ url_for('static', filename='js/portal-async-integration.js') }}"></script>
```

### **Para agrupados_balanceado.html:**

Encontre onde carrega os scripts da carteira e adicione:
```html
<!-- Sistema Assíncrono Redis Queue -->
<script src="{{ url_for('static', filename='js/portal-async-integration.js') }}"></script>
```

---

## 📊 VERIFICAÇÃO DO SISTEMA:

### **Browser (Cliente):**
```javascript
// No console do browser:
window.verificarStatusFilas()  // Mostra status das filas
```

### **Servidor (Terminal):**
```bash
# Status das filas
python worker_atacadao.py --status

# Logs do worker
tail -f logs/worker_atacadao.log
```

---

## 🎨 VISUAL DO NOVO SISTEMA:

### **Loading com Progresso:**
```
┌─────────────────────────────────┐
│   🔄 Agendamento Assíncrono     │
│                                 │
│   Processando agendamento...    │
│   ████████████░░░░░░  75%      │
│                                 │
│  Sistema processando em         │
│  background...                  │
└─────────────────────────────────┘
```

### **Resultado com SweetAlert:**
```
┌─────────────────────────────────┐
│        ✅ Sucesso!              │
│                                 │
│  Agendamento criado com         │
│  sucesso!                       │
│                                 │
│  Protocolo: 12345678            │
│  Referência: NF-001             │
│                                 │
│  [Processado via Redis Queue]  │
│                                 │
│         [ OK ]                  │
└─────────────────────────────────┘
```

---

## 🚨 TROUBLESHOOTING:

### **Erro: "Função não definida"**
- Verificar se o script foi carregado
- Olhar console para erros 404

### **Erro: "CSRF token missing"**
- Adicionar no template:
```html
<meta name="csrf-token" content="{{ csrf_token() }}">
```

### **Loading infinito:**
- Verificar se worker está rodando: `ps aux | grep worker`
- Verificar Redis: `redis-cli ping`

---

## 📱 COMPATIBILIDADE:

✅ **Funciona com:**
- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Opera 76+

✅ **Bibliotecas detectadas automaticamente:**
- SweetAlert2 (se disponível)
- Bootstrap 5 (se disponível)
- jQuery (opcional)

---

## 🎯 RESUMO - O QUE VOCÊ PRECISA FAZER:

1. **Adicionar 1 linha** de script nos templates
2. **Iniciar o worker**: `python worker_atacadao.py`
3. **Pronto!** Os botões agora são assíncronos

**Tempo estimado:** 2 minutos ⏱️

---

## 📞 SUPORTE:

Se precisar de ajuda:
1. Verifique os logs: `logs/worker_atacadao.log`
2. Console do browser: F12 → Console
3. Status das filas: `/portal/api/status-filas`

---

**Criado em:** 27/08/2024  
**Sistema:** Fretes Assíncronos com Redis Queue