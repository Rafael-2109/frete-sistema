# 🔍 DIAGNÓSTICO DO SCHEDULER DE SINCRONIZAÇÃO ODOO

**Data:** 12/11/2025
**Sistema:** Sistema de Fretes - Sincronização Incremental com Odoo

---

## 📋 SUMÁRIO EXECUTIVO

### ✅ CONFIGURAÇÃO IDENTIFICADA

O scheduler de atualização do Odoo está configurado para rodar **EM BACKGROUND** dentro do processo principal da aplicação, iniciado automaticamente pelo script de start do Render.

### 🎯 CARACTERÍSTICAS PRINCIPAIS

1. **Tipo de Scheduler:** APScheduler `BlockingScheduler`
2. **Localização:** `app/scheduler/sincronizacao_incremental_definitiva.py`
3. **Execução:** Background process iniciado no `start_render.sh`
4. **Frequência:** A cada 30 minutos (configurável via `SYNC_INTERVAL_MINUTES`)
5. **Log:** `logs/sincronizacao_incremental.log`

---

## 🔧 ARQUITETURA DO SCHEDULER

### 1. Script Principal
**Arquivo:** [app/scheduler/sincronizacao_incremental_definitiva.py](app/scheduler/sincronizacao_incremental_definitiva.py)

#### Características:
- ✅ Usa `BlockingScheduler` (roda em processo separado)
- ✅ Services instanciados FORA do contexto Flask (evita problemas SSL)
- ✅ Retry automático em caso de erros de conexão (MAX_RETRIES=3)
- ✅ Reconexão automática do banco entre sincronizações
- ✅ Suporte a configuração via variáveis de ambiente

#### Configurações:
```python
INTERVALO_MINUTOS = 30          # Executa a cada 30 minutos
JANELA_CARTEIRA = 40            # Busca carteira dos últimos 40 minutos
STATUS_FATURAMENTO = 5760       # Verifica status NFs últimas 96 horas (4 dias)
JANELA_REQUISICOES = 90         # Requisições de compra últimos 90 minutos
JANELA_PEDIDOS = 90             # Pedidos de compra últimos 90 minutos
JANELA_ALOCACOES = 90           # Alocações últimos 90 minutos
DIAS_ENTRADAS = 7               # Entradas de materiais últimos 7 dias
```

### 2. Inicialização no Render
**Arquivo:** [start_render.sh](start_render.sh) (linhas 100-128)

```bash
# 🔄 INICIAR SINCRONIZAÇÃO INCREMENTAL EM BACKGROUND
echo "Iniciando sincronização incremental em background..."
if [ -f "app/scheduler/sincronizacao_incremental_definitiva.py" ]; then
    mkdir -p logs

    python -m app.scheduler.sincronizacao_incremental_definitiva > logs/sincronizacao_incremental.log 2>&1 &
    SYNC_PID=$!

    sleep 3

    if kill -0 $SYNC_PID 2>/dev/null; then
        echo "✅ Sincronização incremental iniciada e confirmada (PID: $SYNC_PID)"
    else
        echo "❌ ERRO: Scheduler falhou ao iniciar!"
        tail -100 logs/sincronizacao_incremental.log
    fi
fi
```

### 3. Services Sincronizados

O scheduler sincroniza os seguintes módulos (em ordem):

1. **FaturamentoService** - NFs e status de faturamento
2. **CarteiraService** - Pedidos da carteira Odoo
3. **RequisicaoComprasService** - Requisições de compra
4. **PedidoComprasServiceOtimizado** - Pedidos de compra
5. **AlocacaoComprasServiceOtimizado** - Alocações de estoque
6. **EntradaMaterialService** - Entradas de materiais

---

## 🔍 COMO VERIFICAR SE ESTÁ RODANDO

### 1. Verificar Processo em Execução

```bash
# Localmente (WSL/Linux)
ps aux | grep sincronizacao_incremental_definitiva

# No Render (via logs ou shell)
ps aux | grep -E "python.*sincronizacao_incremental"
```

### 2. Verificar Log de Sincronização

```bash
# Ver últimas linhas do log
tail -f logs/sincronizacao_incremental.log

# Ver log completo
cat logs/sincronizacao_incremental.log
```

**O que procurar no log:**
```
============================================================
🔄 SINCRONIZAÇÃO DEFINITIVA - 2025-11-12 14:30:00
============================================================
⚙️ Configurações:
   - Intervalo: 30 minutos
   - Faturamento: status=5760min (96h)
   - Carteira: janela=40min
   - Requisições: janela=90min
   - Pedidos: janela=90min
   - Alocações: janela=90min
   - Entradas: dias=7
============================================================
💰 Sincronizando Faturamento (tentativa 1/3)...
   Status: 5760 minutos (26 horas)
✅ Faturamento sincronizado com sucesso!
   - Novos: 5
   - Atualizados: 12
📦 Sincronizando Carteira (tentativa 1/3)...
   Janela: 40 minutos
✅ Carteira sincronizada com sucesso!
   - Novos: 8
   - Atualizados: 15
```

### 3. Verificar PID no Startup

No log de startup do Render (ou logs/sincronizacao_incremental.log):
```
✅ Sincronização incremental iniciada e confirmada (PID: 12345)
    - Execução imediata para recuperar dados do deploy
    - Próximas execuções a cada 30 minutos
    - Logs em: logs/sincronizacao_incremental.log
```

### 4. Verificar Última Execução no Banco

```sql
-- Verificar última atualização de NFs vindas do Odoo
SELECT MAX(updated_at) as ultima_sync_nf
FROM faturamento_produtos
WHERE created_by = 'odoo_sync';

-- Verificar última atualização de pedidos da carteira
SELECT MAX(criado_em) as ultima_sync_carteira
FROM separacao
WHERE status != 'PREVISAO';
```

---

## ⚠️ PROBLEMAS COMUNS E DIAGNÓSTICO

### 1. Scheduler não inicia

**Sintomas:**
- Mensagem "❌ ERRO: Scheduler falhou ao iniciar!" no log
- PID não persiste após os 3 segundos de verificação

**Possíveis Causas:**
```bash
# Ver erro no log
tail -20 logs/sincronizacao_incremental.log

# Possíveis erros:
# - ImportError (falta alguma dependência)
# - ConnectionError (não consegue conectar ao Odoo/Banco)
# - ConfigurationError (variável de ambiente faltando)
```

**Solução:**
1. Verificar se todas as dependências estão instaladas
2. Verificar variáveis de ambiente necessárias:
   - `DATABASE_URL`
   - `ODOO_URL` (se necessário)
   - `ODOO_DB` (se necessário)
   - `ODOO_USERNAME` (se necessário)
   - `ODOO_PASSWORD` (se necessário)

### 2. Scheduler para após algum tempo

**Sintomas:**
- Inicia corretamente mas para de executar
- Log para de ser atualizado
- Processo não aparece mais no `ps`

**Possíveis Causas:**
- Erro fatal não tratado
- Timeout de conexão com Odoo
- Problema SSL/conexão persistente

**Diagnóstico:**
```bash
# Ver últimas linhas do log antes de parar
tail -50 logs/sincronizacao_incremental.log

# Procurar por:
# - "SSL"
# - "ConnectionError"
# - "Timeout"
# - "Exception"
```

**Solução:**
- O scheduler tem retry automático (3 tentativas)
- Verifica e reinicializa services entre tentativas
- Se continuar parando, aumentar `RETRY_DELAY` ou `MAX_RETRIES`

### 3. Sincronização lenta ou travando

**Sintomas:**
- Log mostra sincronização iniciada mas não completa
- Timeout em algum service específico

**Diagnóstico:**
```bash
# Ver em qual etapa está travado
tail -f logs/sincronizacao_incremental.log

# Verificar conexão com Odoo
curl -I https://odoo.nacomgoya.com.br/web/database/selector

# Verificar conexão com banco
psql $DATABASE_URL -c "SELECT 1;"
```

**Solução:**
- Ajustar janelas de sincronização (reduzir para trazer menos dados)
- Verificar performance do Odoo
- Verificar se não há deadlock no banco

---

## 🔧 CONFIGURAÇÃO VIA VARIÁVEIS DE AMBIENTE

Você pode ajustar o comportamento do scheduler via variáveis de ambiente no Render:

```bash
# Frequência de execução
SYNC_INTERVAL_MINUTES=30        # A cada 30 minutos (padrão)

# Janelas de sincronização
JANELA_CARTEIRA=40              # Carteira: últimos 40 minutos
STATUS_FATURAMENTO=5760         # Faturamento: últimas 96 horas
JANELA_REQUISICOES=90           # Requisições: últimos 90 minutos
JANELA_PEDIDOS=90               # Pedidos: últimos 90 minutos
JANELA_ALOCACOES=90             # Alocações: últimos 90 minutos
DIAS_ENTRADAS=7                 # Entradas: últimos 7 dias

# Retry e resiliência
MAX_RETRIES=3                   # Tentativas em caso de erro
RETRY_DELAY=5                   # Segundos entre tentativas
```

**Como adicionar no Render:**
1. Dashboard do Render → Seu serviço
2. Environment → Add Environment Variable
3. Adicionar a variável desejada
4. Redeploy do serviço

---

## 📊 MONITORAMENTO E MÉTRICAS

### 1. Verificar Taxa de Sucesso

```bash
# Contar sincronizações com sucesso vs erros
grep "✅.*sincronizado com sucesso" logs/sincronizacao_incremental.log | wc -l
grep "❌.*Erro" logs/sincronizacao_incremental.log | wc -l
```

### 2. Verificar Tempo de Execução

```bash
# Ver tempo médio de cada sincronização
grep "SINCRONIZAÇÃO DEFINITIVA" logs/sincronizacao_incremental.log
```

### 3. Verificar Dados Sincronizados

```sql
-- NFs sincronizadas nas últimas 24h
SELECT COUNT(*), DATE(updated_at) as dia
FROM faturamento_produtos
WHERE created_by = 'odoo_sync'
  AND updated_at > NOW() - INTERVAL '24 hours'
GROUP BY dia;

-- Pedidos da carteira sincronizados nas últimas 24h
SELECT COUNT(*), DATE(criado_em) as dia
FROM separacao
WHERE status != 'PREVISAO'
  AND criado_em > NOW() - INTERVAL '24 hours'
GROUP BY dia;
```

---

## 🚀 EXECUÇÃO MANUAL PARA TESTES

Se precisar executar manualmente (para testes ou debug):

```bash
# Executar diretamente (vai bloquear o terminal)
python -m app.scheduler.sincronizacao_incremental_definitiva

# Executar em background
python -m app.scheduler.sincronizacao_incremental_definitiva > logs/manual_sync.log 2>&1 &

# Monitorar log
tail -f logs/manual_sync.log
```

---

## ✅ CHECKLIST DE FUNCIONAMENTO CORRETO

- [ ] Processo aparece no `ps` com PID válido
- [ ] Log `logs/sincronizacao_incremental.log` existe e é atualizado
- [ ] Log mostra "✅ Sincronização incremental iniciada e confirmada"
- [ ] Log mostra execuções periódicas a cada 30 minutos
- [ ] Cada execução mostra sucesso para Faturamento e Carteira
- [ ] Dados estão sendo atualizados no banco (verificar `updated_at`)
- [ ] Não há erros SSL ou ConnectionError repetidos
- [ ] Tempo de execução é razoável (< 5 minutos por ciclo)

---

## 📝 CONCLUSÃO

O scheduler está configurado para rodar **automaticamente em background** durante o startup do serviço no Render. Ele:

1. ✅ Roda em processo separado (não bloqueia a aplicação)
2. ✅ Tem retry automático e reconexão
3. ✅ Logs detalhados para diagnóstico
4. ✅ Configurável via variáveis de ambiente
5. ✅ Sincroniza múltiplos módulos (Faturamento, Carteira, Compras, etc)

**Para verificar se está funcionando:**
- Verifique o log: `logs/sincronizacao_incremental.log`
- Verifique o processo: `ps aux | grep sincronizacao_incremental`
- Verifique os dados no banco: últimas atualizações em `faturamento_produtos` e `separacao`

**Se não estiver rodando:**
1. Verificar se o arquivo existe: `app/scheduler/sincronizacao_incremental_definitiva.py`
2. Verificar log de erro: `tail -50 logs/sincronizacao_incremental.log`
3. Verificar variáveis de ambiente necessárias
4. Tentar execução manual para ver erro completo

---

**Última atualização:** 12/11/2025
**Responsável:** Sistema de Fretes - Equipe de Integração Odoo



python -c "
from app import create_app
from app.odoo.services.carteira_service import CarteiraService
from app.utils.timezone import agora_utc
from datetime import timedelta

app = create_app()
with app.app_context():
    s = CarteiraService()
    r = s.obter_carteira_pendente(modo_incremental=True, minutos_janela=6360)
    print(f'Sucesso: {r.get(\"sucesso\")}')
    print(f'Registros: {len(r.get(\"dados\", []))}')
    print(f'Erro: {r.get(\"erro\", \"Nenhum\")}')
"