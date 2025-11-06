# 🔧 Circuit Breaker para Odoo

## 📋 **O QUE É?**

O Circuit Breaker é um padrão de proteção que **evita que o sistema trave completamente** quando o Odoo está offline ou lento.

**Problema que resolve:**
- Antes: Odoo offline → Sistema trava por 90 segundos tentando conectar
- Depois: Odoo offline → Sistema falha em 8 segundos e continua funcionando

---

## 🎯 **CONFIGURAÇÃO ULTRA CONSERVADORA**

Para **evitar falsos positivos**, a configuração é muito cautelosa:

| Parâmetro | Valor | Explicação |
|-----------|-------|------------|
| **Falhas para abrir** | 5 consecutivas | Precisa falhar 5 vezes (não 3) |
| **Timeout por chamada** | 8 segundos | Timeout generoso (não 5s) |
| **Intervalo de teste** | 30 segundos | Tenta novamente a cada 30s |
| **Sucessos para fechar** | 1 | Basta 1 sucesso para voltar ao normal |
| **Auto-reset** | 120 segundos | Reseta contadores após 2min sem erros |

**Total para abrir:** 5 × 8s = **40 segundos** de tentativas antes de bloquear

---

## 🔄 **ESTADOS DO CIRCUIT BREAKER**

### 🟢 **CLOSED (Fechado - Normal)**
- ✅ Sistema funcionando normalmente
- ✅ Todas as chamadas ao Odoo passam
- ✅ Monitora falhas consecutivas
- ⚠️ Se atingir 5 falhas consecutivas → vai para OPEN

### 🔴 **OPEN (Aberto - Bloqueado)**
- ❌ Odoo considerado offline
- ❌ Chamadas retornam erro IMEDIATAMENTE (não espera 8s)
- ⏱️ Aguarda 30 segundos
- 🔄 Após 30s → vai para HALF_OPEN

### 🟡 **HALF_OPEN (Meio Aberto - Teste)**
- 🧪 Permite 1 chamada de teste
- ✅ Se sucesso → volta para CLOSED imediatamente
- ❌ Se falha → volta para OPEN por mais 30s

---

## 🚨 **CENÁRIOS DE USO**

### **Cenário 1: Odoo caiu (erro 502)**

```
13:50:00 - Tentativa 1: Timeout após 8s - Falha 1/5
13:50:08 - Tentativa 2: Timeout após 8s - Falha 2/5
13:50:16 - Tentativa 3: Timeout após 8s - Falha 3/5
13:50:24 - Tentativa 4: Timeout após 8s - Falha 4/5
13:50:32 - Tentativa 5: Timeout após 8s - Falha 5/5
13:50:40 - Circuit ABRIU! 🔴

Das 13:50:40 até 13:51:10 (30s):
- Qualquer chamada ao Odoo retorna erro INSTANTÂNEO
- Sistema continua funcionando (só funcionalidades Odoo falham)
- Logs mostram: "⚠️ Circuit Breaker ABERTO: Odoo indisponível"

13:51:10 - Teste automático (1 chamada)
          - Se Odoo voltou: Circuit fecha 🟢
          - Se ainda offline: Espera mais 30s
```

**Resultado:** Sistema **não trava**, usuários continuam trabalhando.

---

### **Cenário 2: Rede instável (falso positivo potencial)**

```
13:50:00 - Falha temporária de rede - Falha 1/5
13:50:08 - Falha temporária de rede - Falha 2/5
13:50:16 - SUCESSO! (rede voltou) - Contador RESETA para 0/5

Circuit NÃO abre porque teve sucesso antes de atingir 5 falhas
```

**Proteção contra falso positivo:** Precisa de **5 falhas CONSECUTIVAS**.

---

### **Cenário 3: Erro 500 do Odoo (não crítico)**

```
13:50:00 - Erro 500 (erro interno Odoo)
          - Circuit ignora (não é timeout ou conexão recusada)
          - Contador NÃO aumenta

Circuit só conta erros GRAVES:
- Timeout
- Connection refused
- Connection reset
```

**Proteção contra falso positivo:** Só conta erros de conectividade.

---

## 📊 **MONITORAMENTO**

### **Dashboard Visual**

Acesse: `https://sistema-fretes.onrender.com/admin/circuit-breaker/dashboard`

**Permissão:** Apenas administradores

**O que mostra:**
- 🟢🔴🟡 Estado atual do circuit
- 📊 Total de chamadas, sucessos e falhas
- ⏱️ Tempo até próxima tentativa (se aberto)
- 📈 Vezes que o circuit abriu (histórico)
- ⚙️ Configuração atual

**Auto-refresh:** A cada 5 segundos

---

### **API de Status**

```bash
# Ver status
GET /admin/circuit-breaker/status

# Resposta:
{
  "success": true,
  "circuit_breaker": {
    "state": "CLOSED",
    "is_healthy": true,
    "failure_count": 0,
    "failure_threshold": 5,
    "total_calls": 1523,
    "total_successes": 1520,
    "total_failures": 3,
    "times_opened": 0,
    "time_until_retry": null
  }
}
```

---

### **Reset Manual**

```bash
# Resetar circuit (forçar novas tentativas)
POST /admin/circuit-breaker/reset

# Resposta:
{
  "success": true,
  "message": "Circuit Breaker resetado com sucesso"
}
```

**Quando usar:**
- ✅ Você sabe que Odoo voltou
- ✅ Circuit está travado por engano
- ✅ Após manutenção programada do Odoo

**⚠️ CUIDADO:** Resetar o circuit força novas tentativas de conexão. Não abuse!

---

## 🔍 **LOGS DETALHADOS**

O Circuit Breaker gera logs **muito verbosos** para debugging:

```python
# Estado CLOSED (normal)
⚠️ Circuit CLOSED: Falha 1/5 (erro: TimeoutError)
⚠️ Circuit CLOSED: Falha 2/5 (erro: TimeoutError)
🔄 Circuit CLOSED: Resetando contador de falhas (2 → 0) após sucesso

# Estado OPEN (bloqueado)
🔴 Circuit ABERTO! Odoo considerado offline. Próxima tentativa em 30s. (Total de aberturas: 1)

# Estado HALF_OPEN (testando)
🟡 Circuit HALF_OPEN (testando). Permitindo 1 tentativa para verificar se Odoo voltou...
✅ Circuit HALF_OPEN: Sucesso 1/1

# Fechando circuit
🟢 Circuit FECHADO! Odoo voltou ao normal. Estatísticas: 1520 sucessos, 5 falhas, 1 aberturas

# Auto-reset
🔄 Auto-reset: 120s sem erros. Resetando contador (2 → 0)
```

---

## 💡 **FUNCIONALIDADES QUE USAM ODOO**

Funcionalidades **afetadas** quando Circuit está OPEN:

### ❌ **NÃO FUNCIONAM (dependem de Odoo em tempo real):**
- Busca de `pedido_cliente` (PO do cliente)
- Sincronização de novos pedidos
- Importação de clientes
- Importação de produtos

### ✅ **CONTINUAM FUNCIONANDO (dados locais):**
- Monitoramento de NFs
- Carteira de Pedidos (já sincronizados)
- Embarques
- Cotações
- Separações
- Faturamento
- Rastreamento GPS

---

## 🧪 **TESTANDO O CIRCUIT BREAKER**

### **Teste 1: Simular Odoo offline**

1. Pare o Odoo (se tiver acesso)
2. Tente usar uma funcionalidade que depende do Odoo
3. Observe os logs:
   ```
   ⚠️ Circuit CLOSED: Falha 1/5
   ⚠️ Circuit CLOSED: Falha 2/5
   ⚠️ Circuit CLOSED: Falha 3/5
   ⚠️ Circuit CLOSED: Falha 4/5
   ⚠️ Circuit CLOSED: Falha 5/5
   🔴 Circuit ABERTO! Odoo considerado offline.
   ```

4. Tente novamente após 10s → Erro instantâneo (não espera 8s)
5. Aguarde 30s → Circuit tenta automaticamente
6. Ligue o Odoo novamente
7. Aguarde próximo teste → Circuit fecha automaticamente

---

### **Teste 2: Monitorar Dashboard**

1. Acesse: `/admin/circuit-breaker/dashboard`
2. Force algumas falhas (pare o Odoo temporariamente)
3. Observe o dashboard mudar de estado em tempo real
4. Veja as estatísticas acumulando

---

## ⚙️ **ARQUIVOS MODIFICADOS**

### **Novos arquivos:**
- `app/odoo/utils/circuit_breaker.py` - Implementação do Circuit Breaker
- `app/odoo/routes_circuit_breaker.py` - Rotas de monitoramento
- `CIRCUIT_BREAKER_ODOO.md` - Esta documentação

### **Arquivos modificados:**
- `app/odoo/utils/connection.py` - Integração com Circuit Breaker
- `app/__init__.py` - Registro do blueprint

---

## 🔧 **CONFIGURAÇÃO AVANÇADA**

Se precisar ajustar os parâmetros do Circuit Breaker:

```python
# Em app/odoo/utils/circuit_breaker.py, linha ~285

_odoo_circuit_breaker = OdooCircuitBreaker(
    failure_threshold=5,      # Falhas consecutivas para abrir
    timeout_duration=30,      # Segundos até tentar novamente
    success_threshold=1,      # Sucessos para fechar
    timeout_per_call=8,       # Timeout por chamada
    auto_reset_after=120      # Reset após X segundos sem erros
)
```

**⚠️ IMPORTANTE:** Não altere sem necessidade! A configuração atual é **ultra conservadora** para evitar falsos positivos.

---

## 📈 **MÉTRICAS E ESTATÍSTICAS**

O Circuit Breaker rastreia:

- ✅ Total de chamadas ao Odoo
- ✅ Total de sucessos
- ✅ Total de falhas
- ✅ Vezes que o circuit abriu
- ✅ Último horário de falha
- ✅ Último horário de sucesso
- ✅ Tempo desde última falha
- ✅ Tempo até próximo teste

---

## ❓ **FAQ**

### **1. O Circuit Breaker vai causar mais falhas?**
**Não!** Ele só **detecta** falhas que já estavam acontecendo. A diferença é que agora o sistema **não trava** esperando o Odoo responder.

### **2. E se o Odoo voltar mas o Circuit estiver aberto?**
O circuit **testa automaticamente** a cada 30s. Quando o Odoo voltar, na próxima tentativa de teste o circuit fecha automaticamente.

### **3. Posso desabilitar o Circuit Breaker?**
Não recomendado! Mas se realmente precisar, pode aumentar `failure_threshold` para 999 (nunca abrirá).

### **4. O Circuit Breaker afeta performance?**
**Melhora a performance!** Quando Odoo está offline, falha em 8s em vez de 90s.

### **5. Como sei se o Circuit Breaker está funcionando?**
Veja os logs:
```bash
grep "Circuit" logs/app.log
```

Ou acesse o dashboard: `/admin/circuit-breaker/dashboard`

---

## 🎯 **RESUMO**

✅ **O QUE FOI IMPLEMENTADO:**
- Circuit Breaker conservador (5 falhas, 8s timeout)
- Dashboard de monitoramento visual
- API de status e reset manual
- Logs detalhados
- Auto-recuperação quando Odoo volta

✅ **BENEFÍCIOS:**
- Sistema não trava mais quando Odoo cai
- Falhas rápidas (8s em vez de 90s)
- Detecção automática de recuperação
- Proteção contra falsos positivos

✅ **PRÓXIMOS PASSOS:**
1. Monitorar dashboard após deploy
2. Ajustar timeouts se necessário (improvável)
3. Observar quantas vezes circuit abre (idealmente 0)

---

**Data de implementação:** 2025-11-05
**Autor:** Sistema de Fretes
**Versão:** 1.0.0
