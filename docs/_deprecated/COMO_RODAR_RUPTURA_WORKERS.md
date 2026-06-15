# 🚀 COMO RODAR O SISTEMA DE WORKERS DE RUPTURA

## 📋 PRÉ-REQUISITOS

### 1. Redis (OBRIGATÓRIO)
O sistema de workers usa Redis para fila de jobs e cache.

#### Opção A: Instalar Redis Local (Ubuntu/WSL)
```bash
# Instalar Redis
sudo apt update
sudo apt install redis-server

# Verificar se está rodando
redis-cli ping
# Deve retornar: PONG
```

#### Opção B: Usar Docker
```bash
# Rodar Redis via Docker
docker run -d -p 6379:6379 --name redis-local redis

# Verificar conexão
docker exec -it redis-local redis-cli ping
```

#### Opção C: Redis no Windows
```bash
# Via WSL2 (recomendado)
wsl --install  # Se não tiver WSL
# Depois seguir Opção A dentro do WSL

# Ou baixar Redis para Windows:
# https://github.com/microsoftarchive/redis/releases
```

### 2. Dependências Python
```bash
# Instalar RQ (Redis Queue)
pip install rq redis

# Verificar instalação
python -c "import rq; print(f'RQ versão: {rq.__version__}')"
```

## 🔧 CONFIGURAÇÃO

### 1. Variável de Ambiente (Opcional)
```bash
# Se Redis não estiver em localhost:6379
export REDIS_URL="redis://localhost:6379/0"

# Para Redis com senha:
export REDIS_URL="redis://:senha@localhost:6379/0"
```

### 2. Verificar Conexão Redis
```bash
# Testar conexão
python -c "
from redis import Redis
r = Redis.from_url('redis://localhost:6379/0')
print('Redis conectado:', r.ping())
"
```

## 🏃 EXECUTAR O SISTEMA

### PASSO 1: Iniciar os Workers
```bash
# Na raiz do projeto
python start_ruptura_workers.py
```

Você verá:
```
========================================================
🔧 SISTEMA DE WORKERS DE RUPTURA
========================================================
✅ Redis conectado: redis://localhost:6379/0
🚀 Iniciando 2 workers de ruptura...
✅ Workers iniciados com sucesso!
   Pressione Ctrl+C para parar
------------------------------------------------------------
```

### PASSO 2: Ativar no Frontend

#### Método 1: Ativação Temporária (Para Teste)
1. Abra a página da carteira agrupada
2. Abra o Console do navegador (F12)
3. Execute:
```javascript
// Ativar workers temporariamente
window.RUPTURA_USE_WORKERS = true;
window.rupturaWorkerAddon = new RupturaWorkerAddon();
console.log('✅ Workers ativados para esta sessão');
```

#### Método 2: Ativação Permanente
Edite `app/templates/carteira/agrupados_balanceado.html`:

```html
<!-- Adicionar dentro do <head> -->
<meta name="ruptura-workers" content="true">

<!-- OU adicionar antes dos scripts -->
<script>
    window.RUPTURA_USE_WORKERS = true;
</script>
```

### PASSO 3: Verificar Funcionamento

#### No Terminal (Workers):
- Você verá logs conforme jobs são processados:
```
🚀 Worker ruptura-worker-1 iniciado para fila: ruptura_worker1
🚀 Worker ruptura-worker-2 iniciado para fila: ruptura_worker2
   Aguardando jobs...
[INFO] Processando lote com 50 pedidos...
[INFO] Processados 20/50 pedidos
[INFO] Processados 40/50 pedidos
[INFO] Lote completo: 50 pedidos processados
```

#### No Navegador:
- Indicador "Workers Ativos (2)" no canto superior direito
- Barra de progresso no canto inferior direito
- Botões atualizando a cada 2 segundos
- Mensagem "Enviando..." temporária ao clicar

## 🧪 TESTE RÁPIDO

### 1. Verificar Workers Rodando
```bash
# Ver filas e jobs
python -c "
from redis import Redis
from rq import Queue

r = Redis.from_url('redis://localhost:6379/0')
q1 = Queue('ruptura_worker1', connection=r)
q2 = Queue('ruptura_worker2', connection=r)

print(f'Worker 1: {len(q1)} jobs na fila')
print(f'Worker 2: {len(q2)} jobs na fila')
print(f'Jobs processando: {q1.started_job_registry.count + q2.started_job_registry.count}')
"
```

### 2. Monitorar em Tempo Real
```bash
# Instalar RQ Dashboard (opcional)
pip install rq-dashboard

# Rodar dashboard
rq-dashboard

# Acessar: http://localhost:9181
```

### 3. Limpar Cache/Filas (Se Necessário)
```bash
# Limpar todas as filas
python -c "
from redis import Redis
from rq import Queue

r = Redis.from_url('redis://localhost:6379/0')
Queue('ruptura_worker1', connection=r).empty()
Queue('ruptura_worker2', connection=r).empty()
print('Filas limpas')
"

# Limpar cache de sessões
redis-cli
> KEYS ruptura:*
> DEL ruptura:session:*
> exit
```

## 🐛 TROUBLESHOOTING

### Problema: "Redis connection refused"
```bash
# Verificar se Redis está rodando
sudo systemctl status redis-server

# Iniciar Redis
sudo systemctl start redis-server

# Ou via Docker
docker start redis-local
```

### Problema: Workers não processam
```bash
# Verificar logs dos workers
# Os workers devem mostrar "Aguardando jobs..."

# Verificar se as filas existem
redis-cli
> KEYS rq:queue:*
> LLEN rq:queue:ruptura_worker1
> LLEN rq:queue:ruptura_worker2
```

### Problema: Frontend não ativa workers
```javascript
// No console do navegador
console.log('Manager existe?', !!window.rupturaManager);
console.log('Addon existe?', !!window.rupturaWorkerAddon);
console.log('Workers ativados?', window.RUPTURA_USE_WORKERS);
console.log('Indicador visível?', document.querySelector('.ruptura-worker-indicator'));
```

### Problema: Botões não atualizam
```javascript
// Verificar polling
console.log('Polling ativo?', window.rupturaWorkerAddon?.pollingInterval);

// Verificar sessão
console.log('Session ID:', window.rupturaWorkerAddon?.sessionId);

// Forçar busca manual
if (window.rupturaWorkerAddon) {
    window.rupturaWorkerAddon.buscarResultados();
}
```

## 📊 PERFORMANCE ESPERADA

### Com Workers DESATIVADOS:
- 100 pedidos: ~30-60 segundos (sequencial)
- Travamento da página durante processamento
- Timeout possível em lotes grandes

### Com Workers ATIVADOS:
- 100 pedidos: ~15-30 segundos (2 workers paralelos)
- Página responsiva durante processamento
- Atualização visual a cada 2 segundos
- Sem risco de timeout

### Métricas de Sucesso:
✅ Workers processando em paralelo
✅ Indicador "Workers Ativos (2)" visível
✅ Barra de progresso funcionando
✅ Botões atualizando incrementalmente
✅ Zero erros no console
✅ Sistema antigo continua funcionando se desativado

## 🔄 FLUXO COMPLETO

1. **Página Carrega** → Sistema normal inicia
2. **Addon Detecta Flag** → Se `RUPTURA_USE_WORKERS=true`
3. **Intercepta Análise** → Envia para workers em vez de API direta
4. **Workers Processam** → 2 workers em paralelo, lotes de 20
5. **Frontend Polling** → Busca resultados a cada 2 segundos
6. **Atualiza DOM** → Botões mudam conforme resultados chegam
7. **Finaliza** → Remove progresso, limpa cache

## 💡 DICAS

### Para Desenvolvimento:
```bash
# Rodar workers com mais logs
python start_ruptura_workers.py 2>&1 | tee workers.log

# Monitorar Redis
redis-cli monitor

# Ver memória Redis
redis-cli info memory
```

### Para Produção:
```bash
# Usar supervisor ou systemd
# Exemplo supervisor config:
[program:ruptura_worker1]
command=python -c "from redis import Redis; from rq import Worker, Queue; Worker([Queue('ruptura_worker1', connection=Redis.from_url('redis://localhost:6379/0'))]).work()"
autostart=true
autorestart=true

[program:ruptura_worker2]
command=python -c "from redis import Redis; from rq import Worker, Queue; Worker([Queue('ruptura_worker2', connection=Redis.from_url('redis://localhost:6379/0'))]).work()"
autostart=true
autorestart=true
```

## ✅ CHECKLIST RÁPIDO

- [ ] Redis instalado e rodando (`redis-cli ping`)
- [ ] RQ instalado (`pip install rq`)
- [ ] Workers iniciados (`python start_ruptura_workers.py`)
- [ ] Frontend com addon carregado (verificar no HTML)
- [ ] Flag ativada (`window.RUPTURA_USE_WORKERS = true`)
- [ ] Indicador "Workers Ativos" aparecendo
- [ ] Botões processando com workers

## 🎉 SUCESSO!

Se tudo estiver funcionando:
1. Os workers estarão processando em paralelo
2. A interface mostrará progresso em tempo real
3. Performance será ~2x mais rápida
4. Sistema antigo continua funcionando se desativar a flag

**Importante**: Este é um sistema ADDON - não modifica o sistema existente, apenas adiciona funcionalidade opcional!


// Ativar workers para esta sessão
window.RUPTURA_USE_WORKERS = true;
window.rupturaWorkerAddon = new RupturaWorkerAddon();
console.log('✅ Workers ativados para esta sessão');