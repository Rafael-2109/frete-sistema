# 📋 ESTRUTURA DE WORKERS - EXPLICAÇÃO COMPLETA

## 🎯 RESUMO RÁPIDO
- **DESENVOLVIMENTO**: usa `start_workers.py`
- **PRODUÇÃO (Render)**: usa `worker_atacadao.py`
- **SCHEDULER SENDAS**: precisa ser adicionado em AMBOS

## 📂 ARQUIVOS DE WORKERS

### 1. `start_workers.py` (DESENVOLVIMENTO)
- **Uso**: Desenvolvimento local
- **Comando**: `python start_workers.py`
- **Filas**: default, high, low, atacadao, sendas
- **Workers**: 3 processos paralelos
- **✅ JÁ TEM SCHEDULER SENDAS INTEGRADO**

### 2. `worker_atacadao.py` (PRODUÇÃO)
- **Uso**: Produção no Render
- **Comando**: `python worker_atacadao.py --workers 2`
- **Filas**: atacadao, sendas, high, default
- **Workers**: 2 processos paralelos
- **❌ AINDA NÃO TEM SCHEDULER SENDAS**

### 3. `start_worker_render.sh`
- **Uso**: Script de inicialização no Render
- **Executa**: `worker_atacadao.py`
- **Função**: Verifica Redis, DB, instala Playwright

## 🔄 FLUXO DE EXECUÇÃO

### DESENVOLVIMENTO LOCAL:
```
Terminal → python start_workers.py
         ↓
    Inicia 3 workers RQ
         +
    Inicia thread scheduler Sendas
```

### PRODUÇÃO (RENDER):
```
Render → start_worker_render.sh
       ↓
  Verificações de saúde
       ↓
  worker_atacadao.py
       ↓
  2 workers RQ (SEM scheduler ainda)
```

## ⚠️ PROBLEMA ATUAL
O scheduler Sendas está APENAS no `start_workers.py` (desenvolvimento).
Em PRODUÇÃO, o `worker_atacadao.py` NÃO tem o scheduler ainda.

## ✅ SOLUÇÃO SEGURA

### OPÇÃO 1: Adicionar scheduler no worker_atacadao.py (RECOMENDADO)
Adicionar a mesma lógica de thread do scheduler que está em `start_workers.py` no `worker_atacadao.py`.

**Vantagens:**
- Não quebra nada existente
- Mantém separação dev/prod
- Fácil de testar antes do deploy

### OPÇÃO 2: Criar job recorrente no próprio Render
Usar o Render Cron Jobs para executar o scheduler.

**Vantagens:**
- Totalmente separado dos workers
- Mais controle e visibilidade

**Desvantagens:**
- Custo adicional ($7/mês)

### OPÇÃO 3: Unificar workers (ARRISCADO)
Usar `start_workers.py` tanto em dev quanto prod.

**Vantagens:**
- Código único

**Desvantagens:**
- Pode quebrar produção
- Perde otimizações específicas do worker_atacadao.py

## 🎯 RECOMENDAÇÃO

**USE A OPÇÃO 1**: Adicionar o scheduler no `worker_atacadao.py`

É a mais segura porque:
1. Não altera o fluxo existente
2. Mantém compatibilidade
3. Fácil de reverter se houver problemas
4. Já testado em `start_workers.py`

## 📝 PRÓXIMOS PASSOS

1. Adicionar função `run_sendas_scheduler()` no `worker_atacadao.py`
2. Integrar thread do scheduler no início do worker
3. Testar localmente com `python worker_atacadao.py`
4. Deploy para produção
5. Monitorar logs no Render

## 🔍 COMANDOS ÚTEIS

### Ver workers rodando localmente:
```bash
ps aux | grep -E "(worker|rq)" | grep -v grep
```

### Testar worker_atacadao localmente:
```bash
python worker_atacadao.py --workers 1 --verbose
```

### Ver logs no Render:
```bash
# No dashboard do Render → Worker → Logs
```

### Verificar fila Sendas:
```python
from app import create_app
from app.portal.models_fila_sendas import FilaAgendamentoSendas

app = create_app()
with app.app_context():
    pendentes = FilaAgendamentoSendas.contar_pendentes()
    print(f"Itens pendentes: {pendentes}")
```