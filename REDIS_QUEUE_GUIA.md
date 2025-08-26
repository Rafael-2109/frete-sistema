# 🚀 Guia do Sistema de Filas com Redis Queue

## 📋 Índice
1. [Introdução](#introdução)
2. [Instalação](#instalação)
3. [Configuração](#configuração)
4. [Como Usar](#como-usar)
5. [Monitoramento](#monitoramento)
6. [Troubleshooting](#troubleshooting)

---

## 🎯 Introdução

O sistema de filas com Redis Queue foi implementado para processar operações pesadas (como agendamentos no portal Atacadão) de forma **assíncrona**, evitando:
- ⏱️ Timeouts em requests HTTP
- 🔒 Bloqueio de workers do Flask
- 💥 Travamentos quando há CAPTCHAs ou delays
- 📉 Degradação de performance

### Arquitetura

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Browser    │────▶│  Flask App   │────▶│ Redis Queue  │
└──────────────┘     └──────────────┘     └──────────────┘
                             │                      │
                             ▼                      ▼
                      ┌──────────────┐     ┌──────────────┐
                      │   Database   │     │   Worker     │
                      └──────────────┘     └──────────────┘
                                                   │
                                                   ▼
                                            ┌──────────────┐
                                            │  Playwright  │
                                            │   (Portal)   │
                                            └──────────────┘
```

---

## 📦 Instalação

### 1. Instalar Redis (se ainda não tiver)

#### Ubuntu/Debian:
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

#### macOS:
```bash
brew install redis
brew services start redis
```

#### Windows (WSL):
```bash
# No WSL, seguir instruções do Ubuntu
```

### 2. Instalar dependências Python

```bash
pip install -r requirements.txt
```

As seguintes bibliotecas serão instaladas:
- `redis==5.0.8` - Cliente Redis para Python
- `rq==1.16.1` - Redis Queue
- `rq-dashboard==0.6.1` - Dashboard web para monitoramento (opcional)

### 3. Aplicar migração do banco de dados

```bash
# PostgreSQL
psql -d frete_sistema -f migrations/add_job_id_to_portal_integracoes.sql

# Ou via Flask-Migrate
flask db upgrade
```

---

## ⚙️ Configuração

### 1. Variáveis de Ambiente

Adicione ao seu `.env`:

```env
# Redis
REDIS_URL=redis://localhost:6379/0

# Worker Atacadão (credenciais do portal)
ATACADAO_USUARIO=seu_usuario
ATACADAO_SENHA=sua_senha
```

### 2. Configuração já adicionada em `config.py`:

```python
# Redis Queue Configuration
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
RQ_DEFAULT_TIMEOUT = '30m'  # 30 minutos para jobs longos
RQ_QUEUES = ['high', 'default', 'low', 'atacadao']
```

---

## 🎮 Como Usar

### 1. Iniciar o Worker

Em um terminal separado, execute:

```bash
# Worker único
python worker_atacadao.py

# Múltiplos workers (para processar em paralelo)
python worker_atacadao.py --workers 2

# Modo verbose (mais logs)
python worker_atacadao.py --verbose

# Verificar status das filas
python worker_atacadao.py --status
```

### 2. Usar a API Assíncrona

#### Endpoint Original (SÍNCRONO - EVITAR):
```javascript
// ❌ ANTIGO - Bloqueia o request
POST /portal/api/solicitar-agendamento
```

#### Novo Endpoint (ASSÍNCRONO - RECOMENDADO):
```javascript
// ✅ NOVO - Processa em background
POST /portal/api/solicitar-agendamento-async

// Request body:
{
  "lote_id": "SEP-2024-0001",
  "data_agendamento": "2024-08-27",
  "hora_agendamento": "14:00",
  "transportadora": "Agregado",
  "tipo_veiculo": "11"
}

// Response (202 Accepted):
{
  "success": true,
  "message": "Agendamento enfileirado para processamento",
  "integracao_id": 123,
  "job_id": "abc123def456",
  "status_url": "/portal/api/status-job/abc123def456"
}
```

### 3. Verificar Status do Job

```javascript
// Verificar status do processamento
GET /portal/api/status-job/{job_id}

// Response:
{
  "job_id": "abc123def456",
  "status": "finished",  // queued, started, finished, failed
  "criado_em": "2024-08-27T10:00:00",
  "iniciado_em": "2024-08-27T10:00:05",
  "finalizado_em": "2024-08-27T10:02:30",
  "resultado": {
    "success": true,
    "protocolo": "12345678",
    "message": "Agendamento criado com sucesso"
  },
  "integracao": {
    "id": 123,
    "status": "aguardando_confirmacao",
    "protocolo": "12345678"
  }
}
```

### 4. Reprocessar Integração com Erro

```javascript
// Reprocessar uma integração que falhou
POST /portal/api/reprocessar-integracao/{integracao_id}

// Response:
{
  "success": true,
  "message": "Integração enfileirada para reprocessamento",
  "job_id": "xyz789",
  "status_url": "/portal/api/status-job/xyz789"
}
```

---

## 📊 Monitoramento

### 1. Status das Filas via API

```javascript
GET /portal/api/status-filas

// Response:
{
  "success": true,
  "filas": {
    "atacadao": {
      "pendentes": 5,
      "em_execucao": 1,
      "concluidos": 42,
      "falhados": 2,
      "jobs": [...]
    }
  }
}
```

### 2. Dashboard Web (RQ-Dashboard)

Se instalado, acessar: http://localhost:9181

Para iniciar o dashboard:
```bash
rq-dashboard
```

### 3. Logs do Worker

O worker gera logs detalhados:

```
2024-08-27 10:00:00 - 🚀 WORKER ATACADÃO - INICIANDO
2024-08-27 10:00:00 - 📋 Filas monitoradas: ['atacadao', 'high', 'default']
2024-08-27 10:00:05 - 📦 Fila 'atacadao': 3 jobs pendentes
2024-08-27 10:00:10 - ✅ Job abc123 concluído com sucesso
```

### 4. Monitorar via Terminal

```bash
# Ver status das filas
python worker_atacadao.py --status

# Monitorar Redis diretamente
redis-cli ping
redis-cli llen rq:queue:atacadao
redis-cli monitor  # Ver comandos em tempo real
```

---

## 🔧 Troubleshooting

### Problema 1: Worker não conecta ao Redis

**Sintomas:**
```
Error: Redis connection refused
```

**Soluções:**
1. Verificar se Redis está rodando:
   ```bash
   redis-cli ping  # Deve retornar PONG
   ```
2. Verificar URL do Redis no `.env`
3. Verificar firewall/portas

### Problema 2: Jobs ficam pendentes eternamente

**Sintomas:**
- Jobs com status `queued` mas nunca processados

**Soluções:**
1. Verificar se worker está rodando
2. Verificar se worker está monitorando a fila correta:
   ```bash
   python worker_atacadao.py --queues atacadao,default
   ```

### Problema 3: Jobs falhando com "context was destroyed"

**Sintomas:**
```
Error: Execution context was destroyed
```

**Soluções:**
1. Aumentar timeout do Playwright no job
2. Verificar se sessão do portal está válida:
   ```bash
   python configurar_sessao_atacadao.py
   ```

### Problema 4: Memória alta no worker

**Sintomas:**
- Consumo de RAM crescente

**Soluções:**
1. Limitar workers paralelos
2. Adicionar job cleanup:
   ```python
   # No worker_atacadao.py
   job.cleanup(ttl=3600)  # Limpar após 1 hora
   ```

---

## 🚨 Comandos de Emergência

### Limpar todas as filas (CUIDADO!)
```python
from rq import Queue
from redis import Redis

redis_conn = Redis.from_url('redis://localhost:6379/0')
q = Queue('atacadao', connection=redis_conn)
q.empty()  # Remove todos os jobs pendentes
```

### Parar todos os workers
```bash
# Linux/macOS
pkill -f worker_atacadao

# Windows
taskkill /F /IM python.exe /T
```

### Reiniciar Redis
```bash
sudo systemctl restart redis-server
```

---

## 🔄 Migração dos Endpoints Existentes

Para migrar o código existente para usar o sistema assíncrono:

### Antes (Síncrono):
```python
# routes.py - ANTIGO
resultado = client.criar_agendamento(dados_enviados)
```

### Depois (Assíncrono):
```python
# routes_async.py - NOVO
from app.portal.workers import enqueue_job
from app.portal.workers.atacadao_jobs import processar_agendamento_atacadao

job = enqueue_job(
    processar_agendamento_atacadao,
    integracao.id,
    dados_agendamento,
    queue_name='atacadao',
    timeout='30m'
)
```

---

## 📈 Benefícios do Sistema

1. **Performance**: Requests retornam imediatamente (202 Accepted)
2. **Escalabilidade**: Adicione mais workers conforme necessário
3. **Resiliência**: Jobs falhos podem ser reprocessados
4. **Observabilidade**: Logs detalhados e métricas em tempo real
5. **Flexibilidade**: Diferentes filas com prioridades

---

## 🔗 Links Úteis

- [RQ Documentation](https://python-rq.org/)
- [Redis Documentation](https://redis.io/docs/)
- [Flask + RQ Integration](https://flask.palletsprojects.com/patterns/celery/)

---

## 📝 Notas Finais

- **Sempre** iniciar o worker antes de fazer agendamentos
- **Nunca** executar Playwright diretamente no request HTTP
- **Monitorar** regularmente as filas para evitar acúmulo
- **Configurar** alertas para jobs falhados em produção

Para suporte, verificar logs em:
- Worker: Terminal onde `worker_atacadao.py` está rodando
- Flask: Logs da aplicação
- Redis: `redis-cli monitor`
- Banco: Tabelas `portal_integracoes` e `portal_logs`

---

**Autor**: Sistema de Fretes  
**Data**: 27/08/2024  
**Versão**: 1.0