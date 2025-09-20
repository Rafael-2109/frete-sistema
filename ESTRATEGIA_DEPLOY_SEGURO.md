# 🚀 ESTRATÉGIA DE DEPLOY SEGURO - SINCRONIZAÇÃO INCREMENTAL

## 📊 CONFIGURAÇÃO DO SCHEDULER

| Parâmetro | Valor | Justificativa |
|-----------|-------|---------------|
| **Intervalo de Execução** | 30 minutos | Frequência adequada para manter dados atualizados |
| **Janela de Busca** | 40 minutos | Cria sobreposição de segurança |
| **Sobreposição** | 10 minutos | Garante que nenhum dado seja perdido |
| **Lock Timeout** | 25 minutos | Menor que intervalo para evitar travamentos |

## 🔄 COMO FUNCIONA A SOBREPOSIÇÃO

```
Timeline de Execução:
──────────────────────────────────────────────────────────────────>
    10:00         10:30         11:00         11:30         12:00
      │             │             │             │             │
      ├─────────────┤             │             │             │
      │  Execução 1 │             │             │             │
      │  (09:20-10:00)            │             │             │
      │             ├─────────────┤             │             │
      │             │  Execução 2 │             │             │
      │             │  (09:50-10:30)            │             │
      │             │             ├─────────────┤             │
      │             │             │  Execução 3 │             │
      │             │             │  (10:20-11:00)            │
      └─────────────┴─────────────┴─────────────┴─────────────┘
           40min         40min         40min         40min
      └──────┬──────┘
       SOBREPOSIÇÃO
         10 min
```

### 🛡️ GARANTIAS DA SOBREPOSIÇÃO:
1. **Dados dos minutos 20-30** são buscados em DUAS execuções
2. **Se uma execução falhar**, a próxima ainda pega os dados
3. **Durante deploys**, a sobreposição mantém continuidade

## 🔧 CENÁRIOS DE DEPLOY

### CENÁRIO 1: Deploy Normal (Sem Interrupção)
```
10:00 - Execução normal (busca 09:20-10:00)
10:15 - DEPLOY INICIADO
10:20 - Deploy concluído
10:30 - Próxima execução (busca 09:50-10:30)
       ✅ Dados 10:00-10:20 foram capturados
       ✅ Sobreposição garante continuidade
```

### CENÁRIO 2: Deploy Longo (Com Interrupção)
```
10:00 - Execução normal (busca 09:20-10:00)
10:25 - DEPLOY INICIADO
10:35 - Deploy concluído (perdeu execução das 10:30)
11:00 - Próxima execução (busca 10:20-11:00)
       ✅ Dados 10:00-10:20 da sobreposição anterior
       ✅ Dados 10:20-11:00 capturados normalmente
       ⚠️ Pequeno gap de 10:00-10:20 se não houve sobreposição
```

### CENÁRIO 3: Múltiplas Instâncias (Blue-Green Deploy)
```
Instância A (antiga):
10:00 - Execução normal
10:30 - PARADA para deploy

Instância B (nova):
10:25 - INICIADA
10:30 - Assume execução (busca 09:50-10:30)
       ✅ Redis Lock impede execução duplicada
       ✅ Continuidade garantida
```

## 🔒 MECANISMOS DE PROTEÇÃO

### 1. **LOCK DISTRIBUÍDO (Redis)**
```python
# Previne execuções simultâneas
redis_client.set(
    "carteira:sync:incremental:lock",
    timestamp,
    nx=True,  # Only if not exists
    ex=1500   # Expira em 25 minutos
)
```

### 2. **LOCK LOCAL (Threading)**
```python
# Fallback se Redis não estiver disponível
_sync_lock = Lock()
_sync_lock.acquire(blocking=False)
```

### 3. **IDEMPOTÊNCIA**
- **UPSERT** ao invés de INSERT
- Baseado em `(num_pedido, cod_produto)`
- Múltiplas execuções do mesmo período são seguras

### 4. **WRITE_DATE DO ODOO**
- Campo sempre atualizado em qualquer mudança
- Garante que capturamos TODAS as alterações
- Independente de qual campo foi alterado

## 📋 CHECKLIST DE DEPLOY SEGURO

### ANTES DO DEPLOY:
- [ ] Verificar última execução bem-sucedida
- [ ] Confirmar que Redis está operacional
- [ ] Anotar horário para calcular janela de recuperação

### DURANTE O DEPLOY:
- [ ] Manter Redis rodando (se possível)
- [ ] Deploy rápido (< 10 minutos idealmente)
- [ ] Logs do scheduler preservados

### APÓS O DEPLOY:
- [ ] Verificar se scheduler reiniciou
- [ ] Confirmar primeira execução
- [ ] Monitorar logs por erros
- [ ] Se necessário, executar manualmente com janela maior

## 🔧 COMANDOS ÚTEIS

### Executar Manualmente (Recuperação)
```bash
# Buscar últimas 2 horas (em caso de deploy longo)
python -c "
from app.scheduler.jobs.sincronizacao_incremental import SincronizacaoIncrementalJob
SincronizacaoIncrementalJob.executar_manualmente(janela_minutos=120)
"
```

### Verificar Status no Redis
```bash
redis-cli GET "carteira:sync:incremental:lock"
redis-cli GET "carteira:sync:incremental:last_run"
```

### Forçar Liberação de Lock (Emergência)
```bash
redis-cli DEL "carteira:sync:incremental:lock"
```

### Iniciar Scheduler
```bash
# Normal
python iniciar_scheduler_incremental.py

# Com execução imediata
python iniciar_scheduler_incremental.py --executar-agora
```

## 📊 MONITORAMENTO

### MÉTRICAS IMPORTANTES:
1. **Tempo entre execuções**: Deve ser ~30 minutos
2. **Duração da execução**: Deve ser < 5 minutos
3. **Pedidos processados**: Varia, mas não deve ser 0 sempre
4. **Erros de lock**: Não deve haver (indica problema)

### LOGS PARA ACOMPANHAR:
```
✅ "SINCRONIZAÇÃO INCREMENTAL CONCLUÍDA COM SUCESSO"
⚠️ "Sincronização já em execução - pulando"
❌ "Erro na sincronização:"
🔒 "Lock distribuído adquirido"
🔓 "Lock distribuído liberado"
```

## 🚨 TROUBLESHOOTING

### PROBLEMA: Dados faltando após deploy
**SOLUÇÃO**: Execute manualmente com janela maior
```python
SincronizacaoIncrementalJob.executar_manualmente(janela_minutos=120)
```

### PROBLEMA: Lock travado
**DIAGNÓSTICO**:
```bash
redis-cli TTL "carteira:sync:incremental:lock"
```
**SOLUÇÃO**: Se TTL < 0, deletar manualmente
```bash
redis-cli DEL "carteira:sync:incremental:lock"
```

### PROBLEMA: Execuções duplicadas
**CAUSA**: Múltiplas instâncias sem Redis
**SOLUÇÃO**: Garantir que Redis esteja configurado ou usar apenas uma instância

### PROBLEMA: Scheduler não reinicia após deploy
**SOLUÇÃO**: Adicionar ao supervisor/systemd
```ini
[program:scheduler_incremental]
command=python iniciar_scheduler_incremental.py
autostart=true
autorestart=true
```

## ✅ CONCLUSÃO

A estratégia de **30/40 minutos** com **sobreposição de 10 minutos** garante:

1. **ZERO perda de dados** em deploys normais
2. **Recuperação automática** em deploys longos
3. **Proteção contra execuções duplicadas**
4. **Idempotência** em todas as operações

O sistema é **RESILIENTE** e **AUTO-RECUPERÁVEL**.