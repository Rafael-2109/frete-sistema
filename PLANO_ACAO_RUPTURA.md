# 📋 PLANO DE AÇÃO - IMPLEMENTAÇÃO DO SISTEMA DE RUPTURA COM WORKERS

## 🎯 OBJETIVO FINAL
Implementar sistema de ruptura com workers que processa em background e atualiza interface em tempo real, sem cache e sem recarregar página.

## ⚡ AÇÃO IMEDIATA RECOMENDADA

### 🔴 PROBLEMA URGENTE NO HTML
```html
<!-- agrupados_balanceado.html - LINHA 588 e 615 -->
<!-- ESTÁ CARREGANDO 2 SCRIPTS DIFERENTES + 1 DUPLICADO! -->
```

**CORREÇÃO IMEDIATA**: Remover as duplicações no HTML para evitar conflitos.

---

## 📅 CRONOGRAMA DE IMPLEMENTAÇÃO

### 🔧 FASE 1: LIMPEZA E PREPARAÇÃO (30 minutos)

#### 1.1 Backup dos Arquivos
```bash
# Criar backup
mkdir -p backup_ruptura_$(date +%Y%m%d)
cp app/static/carteira/js/ruptura-*.js backup_ruptura_$(date +%Y%m%d)/
cp app/templates/carteira/js/ruptura-*.js backup_ruptura_$(date +%Y%m%d)/
cp app/carteira/routes/ruptura_*.py backup_ruptura_$(date +%Y%m%d)/
```

#### 1.2 Remover Duplicações
- [ ] Deletar `/app/templates/carteira/js/ruptura-estoque.js` (duplicado)
- [ ] Remover linha 615-616 de `agrupados_balanceado.html`
- [ ] Comentar linha 588 temporariamente

#### 1.3 Decisão de Arquitetura
**Opção A**: SSE (Server-Sent Events) - Recomendado ✅
- Mais simples de implementar
- Suportado nativamente
- Ideal para comunicação unidirecional

**Opção B**: WebSockets
- Mais complexo
- Bidirecional (não necessário aqui)
- Requer mais configuração

---

### 🔨 FASE 2: IMPLEMENTAÇÃO BACKEND (2 horas)

#### 2.1 Criar API Unificada
**Arquivo**: `app/carteira/routes/ruptura_worker_api.py`

```python
# Estrutura principal
- /api/ruptura/processar-lote    # POST - Enfileira para workers
- /api/ruptura/stream/<session>  # GET - SSE stream
- /api/ruptura/status/<session>  # GET - Status do processamento
- /api/ruptura/analisar/<pedido> # GET - Análise individual (sem cache)
```

#### 2.2 Atualizar Worker
**Arquivo**: `app/portal/workers/ruptura_worker.py`

Principais mudanças:
- Publicar via Redis Pub/Sub
- Enviar a cada 20 pedidos
- Incluir progresso no payload

#### 2.3 Configurar Redis Pub/Sub
```python
# No worker
redis_conn.publish(f'ruptura:{session_id}', json.dumps(resultado))

# Na API
pubsub = redis_conn.pubsub()
pubsub.subscribe(f'ruptura:{session_id}')
```

---

### 💻 FASE 3: IMPLEMENTAÇÃO FRONTEND (2 horas)

#### 3.1 Criar Cliente JavaScript
**Arquivo**: `app/static/carteira/js/ruptura-worker-client.js`

Componentes principais:
```javascript
class RupturaWorkerClient {
    // 1. Identificar pedidos na tabela
    // 2. Adicionar botões únicos
    // 3. Enviar para processamento
    // 4. Abrir SSE stream
    // 5. Atualizar DOM conforme resultados chegam
}
```

#### 3.2 Implementar SSE
```javascript
const eventSource = new EventSource(`/api/ruptura/stream/${sessionId}`);
eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    this.atualizarInterface(data);
};
```

#### 3.3 Atualizar HTML
```html
<!-- agrupados_balanceado.html -->
<!-- Remover TODOS os scripts antigos -->
<!-- Adicionar apenas: -->
<script src="{{ url_for('static', filename='carteira/js/ruptura-worker-client.js') }}"></script>
```

---

### 🧪 FASE 4: TESTES E VALIDAÇÃO (1 hora)

#### 4.1 Testes Funcionais
- [ ] Carregar página com 100+ pedidos
- [ ] Verificar processamento em lotes
- [ ] Confirmar atualização a cada 20
- [ ] Testar clique manual no botão
- [ ] Validar dados sem cache

#### 4.2 Testes de Performance
- [ ] Medir tempo total de processamento
- [ ] Verificar uso de memória
- [ ] Confirmar 2 workers ativos
- [ ] Validar que não há polling

#### 4.3 Testes de UX
- [ ] Interface não trava
- [ ] Feedback visual adequado
- [ ] Botões respondem corretamente
- [ ] Modal de detalhes funciona

---

## 🚀 IMPLEMENTAÇÃO ALTERNATIVA RÁPIDA

Se preferir uma solução mais simples inicialmente:

### Opção Simplificada (2 horas total)

#### 1. Manter estrutura atual mas limpar
- Usar apenas `ruptura_api_async.py`
- Melhorar `ruptura-estoque-integrado.js`
- Remover arquivos duplicados

#### 2. Otimizar Polling
```javascript
// Em vez de polling a cada 2s para TODOS
// Fazer polling inteligente:
class PollingInteligente {
    constructor() {
        this.pendentes = new Set();
        this.intervalo = 2000;
        this.maxTentativas = 30;
    }
    
    async verificarPendentes() {
        if (this.pendentes.size === 0) return;
        
        const pedidos = Array.from(this.pendentes);
        const resultado = await this.buscarResultados(pedidos);
        
        // Remover processados da lista
        resultado.prontos.forEach(p => this.pendentes.delete(p));
        
        // Continuar só se houver pendentes
        if (this.pendentes.size > 0) {
            setTimeout(() => this.verificarPendentes(), this.intervalo);
        }
    }
}
```

#### 3. Cache Condicional
```python
# Em ruptura_api.py
@carteira_bp.route('/api/ruptura/analisar-pedido/<num_pedido>')
def analisar_ruptura_pedido(num_pedido):
    # Verificar parâmetro
    use_cache = request.args.get('cache', 'true') == 'true'
    
    if use_cache and REDIS_DISPONIVEL:
        # Verificar cache...
    
    # Sempre processar se cache=false
```

---

## 📊 COMPARAÇÃO DAS SOLUÇÕES

| Aspecto | Solução Completa (SSE) | Solução Simplificada |
|---------|------------------------|---------------------|
| **Tempo Implementação** | 5-6 horas | 2 horas |
| **Complexidade** | Média | Baixa |
| **Performance** | Excelente | Boa |
| **Manutenibilidade** | Excelente | Regular |
| **Escalabilidade** | Excelente | Limitada |
| **Experiência Usuário** | Ótima | Boa |

---

## ✅ CHECKLIST DE IMPLEMENTAÇÃO

### Preparação
- [ ] Backup realizado
- [ ] Ambiente de teste preparado
- [ ] Redis funcionando
- [ ] Workers configurados

### Implementação
- [ ] Backend API criada
- [ ] Worker atualizado
- [ ] Frontend novo criado
- [ ] HTML limpo e atualizado
- [ ] Arquivos antigos removidos

### Validação
- [ ] Sem erros no console
- [ ] Dados sempre atualizados
- [ ] 2 workers processando
- [ ] Interface responsiva
- [ ] Botões funcionais

### Deploy
- [ ] Testes em staging
- [ ] Monitoramento ativo
- [ ] Rollback preparado
- [ ] Documentação atualizada

---

## 🎯 RESULTADO ESPERADO

Após implementação:
1. **1 único arquivo JS** controlando ruptura
2. **2 workers** processando em paralelo
3. **Atualizações em tempo real** via SSE
4. **Zero cache** = dados sempre frescos
5. **Interface fluida** que não trava
6. **Código limpo** e manutenível

---

## 🆘 POSSÍVEIS PROBLEMAS E SOLUÇÕES

### Problema 1: SSE não funciona
**Solução**: Verificar configuração do Nginx/proxy para não bufferizar

### Problema 2: Workers não processam
**Solução**: Verificar filas RQ e conexão Redis

### Problema 3: Botões duplicados
**Solução**: Limpar DOM antes de adicionar novos

### Problema 4: Dados desatualizados
**Solução**: Garantir cache=false em todas chamadas

---

## 📝 NOTAS FINAIS

1. **Prioridade**: Resolver duplicação no HTML primeiro
2. **Teste incremental**: Implementar e testar por partes
3. **Monitoramento**: Logs detalhados durante implementação
4. **Rollback**: Manter backup para reverter se necessário

**Recomendação**: Começar com a limpeza e depois decidir entre solução completa ou simplificada baseado no tempo disponível.