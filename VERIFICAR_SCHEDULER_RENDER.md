# 🔍 COMO VERIFICAR SE O SCHEDULER ESTÁ RODANDO NO RENDER

## 📊 RESUMO DO PROBLEMA

O scheduler **FUNCIONA LOCALMENTE** mas **NÃO ESTÁ RODANDO NO RENDER**.

### ✅ Confirmado Localmente:
- Conecta no Odoo com sucesso (UID: 42)
- Executa sincronização sem erros
- APScheduler está instalado e funcional

### ❌ Problema no Render:
- Processo do scheduler não está ativo
- Logs não estão sendo gerados

---

## 🚀 COMO VERIFICAR NO RENDER

### 1️⃣ **Via Shell do Render (MAIS COMPLETO)**

No dashboard do Render, acesse o Shell do seu serviço:

```bash
# Verificar se o processo está rodando
ps aux | grep sincronizacao

# Verificar logs
cat logs/sincronizacao_incremental.log | tail -50

# Executar script de diagnóstico
python testar_scheduler.py

# Tentar executar manualmente
python -m app.scheduler.sincronizacao_incremental_simples
```

### 2️⃣ **Via Logs do Render**

No dashboard do Render, vá em "Logs" e procure por:

```
🎯 INICIANDO SCHEDULER DE SINCRONIZAÇÃO INCREMENTAL
✅ Sincronização incremental iniciada (PID:
```

Se NÃO encontrar essas mensagens, o scheduler não iniciou.

### 3️⃣ **Via Endpoint de Diagnóstico (CRIAR)**

Adicione temporariamente ao seu `app/__init__.py`:

```python
@app.route('/scheduler-status')
def scheduler_status():
    import subprocess
    import json

    # Verificar processo
    result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
    scheduler_running = 'sincronizacao_incremental' in result.stdout

    # Verificar log
    import os
    log_exists = os.path.exists('logs/sincronizacao_incremental.log')
    log_size = 0
    if log_exists:
        log_size = os.path.getsize('logs/sincronizacao_incremental.log')

    return json.dumps({
        'scheduler_running': scheduler_running,
        'log_exists': log_exists,
        'log_size': log_size,
        'odoo_url_set': bool(os.environ.get('ODOO_URL'))
    })
```

Depois acesse: `https://seu-app.onrender.com/scheduler-status`

---

## 🔧 POSSÍVEIS CAUSAS E SOLUÇÕES

### Causa 1: **Erro no start_render.sh**
O scheduler é iniciado na linha 106 do `start_render.sh`:
```bash
python app/scheduler/sincronizacao_incremental_simples.py > logs/sincronizacao_incremental.log 2>&1 &
```

**PROBLEMA IDENTIFICADO**: O script usa caminho relativo `app/scheduler/...`

**SOLUÇÃO**: Modificar para usar módulo Python:
```bash
python -m app.scheduler.sincronizacao_incremental_simples > logs/sincronizacao_incremental.log 2>&1 &
```

### Causa 2: **Diretório logs não existe**
O script tenta criar logs em `logs/sincronizacao_incremental.log`

**SOLUÇÃO**: Linha 104 já cria o diretório (`mkdir -p logs`), mas verificar se funcionou.

### Causa 3: **Processo morre logo após iniciar**
Pode estar crashando sem gerar logs visíveis.

**SOLUÇÃO**: Capturar PID e verificar se ainda existe:
```bash
python -m app.scheduler.sincronizacao_incremental_simples > logs/sincronizacao_incremental.log 2>&1 &
SYNC_PID=$!
sleep 5
if kill -0 $SYNC_PID 2>/dev/null; then
    echo "✅ Scheduler ainda rodando após 5 segundos"
else
    echo "❌ Scheduler morreu! Verificar logs"
    tail -50 logs/sincronizacao_incremental.log
fi
```

---

## 🛠️ CORREÇÃO RECOMENDADA

Modifique o arquivo `start_render.sh` linha 106:

**DE:**
```bash
python app/scheduler/sincronizacao_incremental_simples.py > logs/sincronizacao_incremental.log 2>&1 &
```

**PARA:**
```bash
# Usar módulo Python para garantir imports corretos
python -m app.scheduler.sincronizacao_incremental_simples > logs/sincronizacao_incremental.log 2>&1 &
SYNC_PID=$!

# Verificar se ainda está rodando após 5 segundos
sleep 5
if kill -0 $SYNC_PID 2>/dev/null; then
    echo " ✅ Scheduler confirmado rodando (PID: $SYNC_PID)"
else
    echo " ❌ ERRO: Scheduler morreu! Últimas linhas do log:"
    tail -20 logs/sincronizacao_incremental.log
    echo " ⚠️ Continuando sem scheduler..."
fi
```

---

## 📝 COMANDO PARA TESTE RÁPIDO NO RENDER

Execute isto no Shell do Render:

```bash
# Teste completo em uma linha
python testar_scheduler.py && echo "---" && ps aux | grep sync && echo "---" && python -m app.scheduler.sincronizacao_incremental_simples 2>&1 | head -50
```

---

## ⚠️ IMPORTANTE

Se o scheduler não funcionar no Render, você pode:

1. **Solução temporária**: Criar endpoint HTTP que executa sincronização e chamar via cron externo
2. **Solução alternativa**: Usar Render Cron Jobs (recurso pago)
3. **Solução manual**: Executar sincronização via Shell periodicamente

---

## 🔍 CHECKLIST DE VERIFICAÇÃO

- [ ] Variáveis ODOO_* estão configuradas no Render
- [ ] APScheduler==3.11.0 está no requirements.txt
- [ ] Diretório logs existe e tem permissão de escrita
- [ ] start_render.sh usa `python -m` em vez de caminho direto
- [ ] Processo do scheduler sobrevive após 5 segundos
- [ ] Logs mostram "INICIANDO SCHEDULER"
- [ ] Conexão com Odoo funciona do Render

Se todos os itens acima estiverem OK, o scheduler deve funcionar!