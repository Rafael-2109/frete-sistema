# 🔧 INTEGRAÇÃO DO SISTEMA DE WORKERS - INSTRUÇÕES

## 📋 ARQUIVOS CRIADOS

### 1. **Backend - API de Workers**
- **Arquivo**: `app/carteira/routes/ruptura_worker_api.py`
- **Função**: API que gerencia o processamento com workers
- **Endpoints**:
  - `/api/ruptura/worker/iniciar-processamento` - Envia pedidos para workers
  - `/api/ruptura/worker/buscar-resultados/<session_id>` - Busca resultados prontos
  - `/api/ruptura/worker/status/<session_id>` - Status do processamento
  - `/api/ruptura/worker/limpar-cache` - Limpa cache da sessão

### 2. **Worker**
- **Arquivo**: `app/portal/workers/ruptura_worker_novo.py`
- **Função**: Processa lotes de pedidos em background
- **Features**:
  - Processa em lotes de 20 pedidos
  - Salva resultados no Redis
  - Publica atualizações a cada 20 pedidos

### 3. **Frontend - Addon JavaScript**
- **Arquivo**: `app/static/carteira/js/ruptura-worker-addon.js`
- **Função**: Adiciona funcionalidade de workers SEM modificar sistema atual
- **Features**:
  - Detecta e integra com `ruptura-estoque.js` existente
  - Polling a cada 2 segundos
  - Fallback automático se workers falharem

## 🚀 COMO ATIVAR OS WORKERS

### OPÇÃO 1: Via Meta Tag (Recomendado)
Adicione no `agrupados_balanceado.html` dentro do `<head>`:

```html
<!-- Ativar processamento com workers -->
<meta name="ruptura-workers" content="true">
```

### OPÇÃO 2: Via JavaScript Global
Adicione no `agrupados_balanceado.html` antes de carregar os scripts:

```html
<script>
    window.RUPTURA_USE_WORKERS = true;
</script>
```

## 📝 MODIFICAÇÕES NECESSÁRIAS NO HTML

### Em `app/templates/carteira/agrupados_balanceado.html`:

**PASSO 1**: Adicionar o addon de workers (linha ~590, após outros scripts):

```html
<!-- Sistema de Ruptura Original (MANTER) -->
<script>
    {% include 'carteira/js/ruptura-estoque.js' %}
</script>

<!-- ADICIONAR: Addon de Workers (não modifica o sistema atual) -->
<script src="{{ url_for('static', filename='carteira/js/ruptura-worker-addon.js') }}"></script>

<!-- ADICIONAR: Ativar workers (opcional, para teste) -->
<script>
    // Descomente a linha abaixo para ativar workers
    // window.RUPTURA_USE_WORKERS = true;
</script>
```

## 🔌 MODIFICAÇÃO NO ARQUIVO PYTHON (APENAS 1 IMPORT)

### Em `app/carteira/routes/__init__.py`:

Adicione o import do novo módulo de workers:

```python
# Imports existentes
from .cotacao_api import *
from .separacao_api import *
from .ruptura_api import *  # <-- Manter este

# ADICIONAR esta linha:
from .ruptura_worker_api import *  # <-- Nova API de workers
```

## ⚙️ CONFIGURAÇÃO DOS WORKERS RQ

### 1. Criar arquivo `start_workers_ruptura.py`:

```python
#!/usr/bin/env python3
"""
Script para iniciar 2 workers de ruptura
"""
import os
import sys
from redis import Redis
from rq import Worker, Queue
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Conectar ao Redis
redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
redis_conn = Redis.from_url(redis_url)

# Criar filas
queue1 = Queue('ruptura_worker1', connection=redis_conn)
queue2 = Queue('ruptura_worker2', connection=redis_conn)

if __name__ == '__main__':
    import multiprocessing
    
    def start_worker(queue_name):
        """Inicia um worker para a fila especificada"""
        queue = Queue(queue_name, connection=redis_conn)
        worker = Worker([queue], connection=redis_conn)
        logger.info(f"🚀 Worker iniciado para fila: {queue_name}")
        worker.work()
    
    # Criar 2 processos para 2 workers
    p1 = multiprocessing.Process(target=start_worker, args=('ruptura_worker1',))
    p2 = multiprocessing.Process(target=start_worker, args=('ruptura_worker2',))
    
    # Iniciar workers
    p1.start()
    p2.start()
    
    logger.info("✅ 2 Workers de ruptura iniciados")
    
    # Aguardar
    try:
        p1.join()
        p2.join()
    except KeyboardInterrupt:
        logger.info("⏹️ Parando workers...")
        p1.terminate()
        p2.terminate()
```

### 2. Executar os workers:

```bash
python start_workers_ruptura.py
```

## 🧪 TESTE RÁPIDO

### 1. Teste Manual (SEM ativar globalmente):

No console do navegador, após a página carregar:

```javascript
// Forçar ativação dos workers para teste
window.RUPTURA_USE_WORKERS = true;
window.rupturaWorkerAddon = new RupturaWorkerAddon();
```

### 2. Verificar se está funcionando:

- Deve aparecer indicador "Workers Ativos (2)" no canto superior direito
- Botões devem mostrar "Enviando..." temporariamente
- Barra de progresso aparece no canto inferior direito
- Resultados atualizam a cada 2 segundos

## 🔄 COMO FUNCIONA

### Fluxo com Workers ATIVADO:

1. **Página carrega** → `ruptura-estoque.js` inicia normalmente
2. **Addon detecta** → `ruptura-worker-addon.js` verifica flag
3. **Se ativado** → Intercepta análise automática
4. **Envia para workers** → 2 workers processam em paralelo
5. **Polling** → Busca resultados a cada 2 segundos
6. **Atualiza DOM** → Botões mudam conforme resultados chegam
7. **Finaliza** → Remove progresso e limpa cache

### Fluxo com Workers DESATIVADO:

1. Sistema funciona **EXATAMENTE** como antes
2. Addon não interfere
3. Zero mudanças no comportamento

## ⚠️ IMPORTANTE

### O QUE NÃO MUDA:

- ✅ `ruptura_api.py` continua funcionando
- ✅ `ruptura-estoque.js` continua funcionando
- ✅ Clique manual nos botões funciona igual
- ✅ Modal de detalhes funciona igual
- ✅ Cache Redis de 15s no endpoint original

### O QUE MUDA (quando ativado):

- ⚡ Processamento em paralelo com 2 workers
- 📊 Barra de progresso visual
- 🔄 Atualização a cada 20 pedidos processados
- 🚀 Performance melhorada para muitos pedidos

## 🐛 TROUBLESHOOTING

### Workers não processam:
```bash
# Verificar se Redis está rodando
redis-cli ping

# Verificar filas
python -c "from redis import Redis; from rq import Queue; r = Redis(); q1 = Queue('ruptura_worker1', connection=r); print(f'Fila 1: {len(q1)} jobs'); q2 = Queue('ruptura_worker2', connection=r); print(f'Fila 2: {len(q2)} jobs')"
```

### Addon não ativa:
```javascript
// No console do navegador
console.log('Manager existe?', !!window.rupturaManager);
console.log('Addon existe?', !!window.rupturaWorkerAddon);
console.log('Workers ativos?', window.RUPTURA_USE_WORKERS);
```

### Limpar cache manualmente:
```bash
# Via Redis CLI
redis-cli
> KEYS ruptura:*
> DEL ruptura:session:*
```

## ✅ CHECKLIST DE IMPLEMENTAÇÃO

- [ ] Adicionar import em `app/carteira/routes/__init__.py`
- [ ] Adicionar script do addon em `agrupados_balanceado.html`
- [ ] Configurar flag de ativação (meta tag ou JS)
- [ ] Iniciar workers com `start_workers_ruptura.py`
- [ ] Testar com flag ativada
- [ ] Verificar indicador "Workers Ativos"
- [ ] Confirmar que sistema antigo continua funcionando

## 📊 MÉTRICAS DE SUCESSO

- Sistema antigo funciona 100% sem mudanças
- Workers processam quando ativados
- Atualização visual a cada 2 segundos
- Sem erros no console
- Fallback automático se workers falharem

## 🎉 RESULTADO ESPERADO

Com workers **DESATIVADOS**: Sistema funciona exatamente como antes
Com workers **ATIVADOS**: Processamento paralelo eficiente com feedback visual

**Risco**: ZERO - addon não modifica sistema existente, apenas adiciona funcionalidade opcional