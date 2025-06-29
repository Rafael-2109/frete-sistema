# 🚀 SPRINT 1: PERFORMANCE BOOST
**Objetivo**: Reduzir tempo de resposta em 50% | Duração: 2 semanas | Prioridade: ALTA

---

## 🎯 **OBJETIVOS ESPECÍFICOS**

### **Metas Quantitativas**
- ✅ Database Response Time: 95ms → <50ms (-47%)
- ✅ Page Load Time: 2.1s → <1s (-52%)
- ✅ Cache Hit Rate: 72% → >85% (+18%)
- ✅ Query Performance: Eliminar 80% das queries >500ms

### **Entregáveis**
1. **Performance Optimizer**: Sistema automatizado de otimização
2. **Cache Strategy**: Redis inteligente por contexto
3. **Query Optimization**: Índices e joinedload estratégicos
4. **Monitoring Dashboard**: APM básico implementado

---

## 📋 **BACKLOG DETALHADO**

### **🔧 TASK 1: Database Query Optimization (5 dias)**

#### **Subtask 1.1: Análise de Queries Lentas**
```python
# app/utils/query_analyzer.py
import time
import logging
from functools import wraps
from sqlalchemy import event
from sqlalchemy.engine import Engine

class QueryAnalyzer:
    def __init__(self):
        self.slow_queries = []
        self.query_stats = {}
    
    def track_query_performance(self):
        """Decorator para trackear performance de queries"""
        @event.listens_for(Engine, "before_cursor_execute")
        def receive_before_cursor_execute(conn, cursor, statement, 
                                        parameters, context, executemany):
            context._query_start_time = time.time()
        
        @event.listens_for(Engine, "after_cursor_execute")
        def receive_after_cursor_execute(conn, cursor, statement, 
                                       parameters, context, executemany):
            total = time.time() - context._query_start_time
            
            if total > 0.5:  # Queries > 500ms
                self.slow_queries.append({
                    'query': statement[:200] + '...',
                    'duration': total,
                    'timestamp': time.time()
                })
                logging.warning(f"SLOW QUERY ({total:.3f}s): {statement[:100]}")
    
    def get_performance_report(self):
        """Relatório de performance das queries"""
        return {
            'slow_queries_count': len(self.slow_queries),
            'slowest_query': max(self.slow_queries, key=lambda x: x['duration']) if self.slow_queries else None,
            'average_slow_time': sum(q['duration'] for q in self.slow_queries) / len(self.slow_queries) if self.slow_queries else 0
        }

# Implementação
query_analyzer = QueryAnalyzer()
query_analyzer.track_query_performance()
```

#### **Subtask 1.2: Índices Críticos**
```sql
-- indices_criticos.sql
-- Baseado nas queries mais lentas identificadas

-- 1. Monitoramento (exportação lenta: 2.3s)
CREATE INDEX CONCURRENTLY idx_entregas_data_embarque_vendedor 
ON entregas_monitoradas(data_embarque, vendedor) 
WHERE entregue = false;

CREATE INDEX CONCURRENTLY idx_entregas_cliente_periodo 
ON entregas_monitoradas(cliente, data_embarque) 
WHERE data_embarque >= CURRENT_DATE - INTERVAL '90 days';

-- 2. Dashboard embarques (890ms)
CREATE INDEX CONCURRENTLY idx_embarques_status_data 
ON embarques(status, data_embarque) 
WHERE status = 'ativo';

-- 3. Relatório faturamento (650ms)
CREATE INDEX CONCURRENTLY idx_faturamento_data_cliente 
ON relatorio_faturamento_importado(data_fatura, nome_cliente);

CREATE INDEX CONCURRENTLY idx_faturamento_valor_periodo 
ON relatorio_faturamento_importado(data_fatura, valor_total) 
WHERE data_fatura >= CURRENT_DATE - INTERVAL '30 days';

-- 4. Consulta fretes (520ms)
CREATE INDEX CONCURRENTLY idx_fretes_status_transportadora 
ON fretes(status, transportadora_id, criado_em);

-- 5. Status pedidos (380ms)
CREATE INDEX CONCURRENTLY idx_pedidos_status_expedicao 
ON pedidos(status, expedicao) 
WHERE expedicao >= CURRENT_DATE - INTERVAL '30 days';
```

#### **Subtask 1.3: Query Optimization com JoinedLoad**
```python
# app/utils/optimized_queries.py
from sqlalchemy.orm import joinedload, selectinload

class OptimizedQueries:
    """Queries otimizadas para evitar N+1 problems"""
    
    @staticmethod
    def get_entregas_with_relations(filters=None):
        """Carrega entregas com todos os relacionamentos de uma vez"""
        from app import db
        from app.monitoramento.models import EntregaMonitorada
        
        query = db.session.query(EntregaMonitorada).options(
            joinedload(EntregaMonitorada.agendamentos),
            joinedload(EntregaMonitorada.logs),
            joinedload(EntregaMonitorada.eventos),
            selectinload(EntregaMonitorada.custos_extras),  # 1:N relationship
            selectinload(EntregaMonitorada.comentarios)     # Dynamic relationship
        )
        
        if filters:
            if filters.get('vendedor'):
                query = query.filter(EntregaMonitorada.vendedor.ilike(f"%{filters['vendedor']}%"))
            if filters.get('data_inicio'):
                query = query.filter(EntregaMonitorada.data_embarque >= filters['data_inicio'])
        
        return query.order_by(EntregaMonitorada.data_embarque.desc())
    
    @staticmethod
    def get_embarques_with_items():
        """Embarques com itens carregados"""
        from app.embarques.models import Embarque
        
        return db.session.query(Embarque).options(
            selectinload(Embarque.itens),
            joinedload(Embarque.transportadora)
        ).filter(Embarque.status == 'ativo')
    
    @staticmethod
    def get_faturamento_with_stats(periodo_dias=30):
        """Faturamento com estatísticas pré-calculadas"""
        from datetime import datetime, timedelta
        from sqlalchemy import func
        
        data_limite = datetime.now() - timedelta(days=periodo_dias)
        
        return db.session.query(
            RelatorioFaturamentoImportado.nome_cliente,
            func.count(RelatorioFaturamentoImportado.id).label('total_nfs'),
            func.sum(RelatorioFaturamentoImportado.valor_total).label('valor_total'),
            func.avg(RelatorioFaturamentoImportado.valor_total).label('ticket_medio')
        ).filter(
            RelatorioFaturamentoImportado.data_fatura >= data_limite
        ).group_by(
            RelatorioFaturamentoImportado.nome_cliente
        ).order_by(
            func.sum(RelatorioFaturamentoImportado.valor_total).desc()
        )
```

### **💾 TASK 2: Redis Cache Strategy (3 dias)**

#### **Subtask 2.1: Cache Inteligente por Contexto**
```python
# app/utils/intelligent_cache.py
import json
import hashlib
from functools import wraps
from datetime import timedelta
from app.utils.redis_cache import cache_redis

class IntelligentCache:
    """Sistema de cache inteligente baseado em contexto"""
    
    CACHE_PATTERNS = {
        'faturamento': {'ttl': 3600, 'prefix': 'fat'},      # 1h
        'entregas': {'ttl': 1800, 'prefix': 'ent'},        # 30min
        'embarques': {'ttl': 900, 'prefix': 'emb'},        # 15min
        'dashboards': {'ttl': 300, 'prefix': 'dash'},      # 5min
        'claude_responses': {'ttl': 7200, 'prefix': 'claude'}, # 2h
        'user_context': {'ttl': 86400, 'prefix': 'user'}   # 24h
    }
    
    def __init__(self):
        self.hit_count = 0
        self.miss_count = 0
    
    def get_cache_key(self, context, params):
        """Gera chave de cache baseada no contexto e parâmetros"""
        pattern = self.CACHE_PATTERNS.get(context, {'prefix': 'generic'})
        
        # Criar hash dos parâmetros para key única
        param_hash = hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()[:8]
        
        return f"{pattern['prefix']}:{param_hash}"
    
    def cache_query_result(self, context='generic'):
        """Decorator para cachear resultados de queries"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Gerar chave baseada na função e parâmetros
                cache_key = self.get_cache_key(context, {
                    'func': func.__name__,
                    'args': str(args),
                    'kwargs': str(kwargs)
                })
                
                # Tentar buscar no cache
                cached_result = cache_redis.get(cache_key)
                if cached_result:
                    self.hit_count += 1
                    return json.loads(cached_result)
                
                # Se não encontrou, executar função
                result = func(*args, **kwargs)
                
                # Cachear resultado
                pattern = self.CACHE_PATTERNS.get(context, {'ttl': 1800})
                cache_redis.setex(
                    cache_key, 
                    pattern['ttl'], 
                    json.dumps(result, default=str)
                )
                
                self.miss_count += 1
                return result
            return wrapper
        return decorator
    
    def invalidate_context(self, context):
        """Invalida todo o cache de um contexto específico"""
        pattern = self.CACHE_PATTERNS.get(context, {'prefix': 'generic'})
        prefix = f"{pattern['prefix']}:*"
        
        keys = cache_redis.keys(prefix)
        if keys:
            cache_redis.delete(*keys)
    
    def get_cache_stats(self):
        """Estatísticas do cache"""
        total_requests = self.hit_count + self.miss_count
        hit_rate = (self.hit_count / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'hit_count': self.hit_count,
            'miss_count': self.miss_count,
            'hit_rate': round(hit_rate, 2),
            'total_requests': total_requests
        }

# Instância global
intelligent_cache = IntelligentCache()
```

#### **Subtask 2.2: Aplicação do Cache nas Funções Críticas**
```python
# app/claude_ai/claude_real_integration.py - PATCH
class ClaudeRealIntegration:
    
    @intelligent_cache.cache_query_result('faturamento')
    def _carregar_dados_faturamento(self, analise, filtros_usuario, data_limite):
        """VERSÃO CACHEABLE - Carrega dados de faturamento"""
        # Código existente da função...
        return dados_faturamento
    
    @intelligent_cache.cache_query_result('entregas')  
    def _carregar_entregas_banco(self, analise, filtros_usuario, data_limite):
        """VERSÃO CACHEABLE - Carrega entregas"""
        # Código existente da função...
        return dados_entregas
    
    @intelligent_cache.cache_query_result('embarques')
    def _carregar_dados_embarques(self, analise, filtros_usuario, data_limite):
        """VERSÃO CACHEABLE - Carrega embarques"""
        # Código existente da função...
        return dados_embarques

# app/monitoramento/routes.py - PATCH  
@monitoramento_bp.route('/exportar')
@intelligent_cache.cache_query_result('entregas')
def exportar_entregas():
    """VERSÃO CACHEABLE - Exportação otimizada"""
    # Usar OptimizedQueries.get_entregas_with_relations()
    # Código otimizado...
```

### **📊 TASK 3: Frontend Optimization (2 dias)**

#### **Subtask 3.1: Asset Optimization**
```python
# app/utils/asset_optimizer.py
import os
import gzip
import shutil
from flask import current_app

class AssetOptimizer:
    """Otimização de assets CSS/JS"""
    
    def __init__(self):
        self.static_dir = current_app.static_folder
    
    def minify_css(self):
        """Minificação básica de CSS"""
        css_files = [
            'app/static/css/custom.css',
            'app/static/style.css'
        ]
        
        minified_content = []
        for css_file in css_files:
            if os.path.exists(css_file):
                with open(css_file, 'r') as f:
                    content = f.read()
                    # Remover comentários e espaços
                    content = content.replace('\n', '').replace('  ', ' ')
                    minified_content.append(content)
        
        # Salvar versão minificada
        with open('app/static/css/app.min.css', 'w') as f:
            f.write(''.join(minified_content))
    
    def enable_gzip_compression(self):
        """Gzip compression para assets"""
        assets = [
            'app/static/css/app.min.css',
            'app/static/js/app.min.js'
        ]
        
        for asset in assets:
            if os.path.exists(asset):
                with open(asset, 'rb') as f_in:
                    with gzip.open(f"{asset}.gz", 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
```

#### **Subtask 3.2: Lazy Loading Implementation**
```javascript
// app/static/js/lazy-loading.js
class LazyLoader {
    constructor() {
        this.observer = null;
        this.init();
    }
    
    init() {
        // Intersection Observer para lazy loading
        this.observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    this.loadComponent(entry.target);
                    this.observer.unobserve(entry.target);
                }
            });
        });
        
        // Observar elementos com data-lazy
        document.querySelectorAll('[data-lazy]').forEach(el => {
            this.observer.observe(el);
        });
    }
    
    loadComponent(element) {
        const componentType = element.dataset.lazy;
        
        switch(componentType) {
            case 'chart':
                this.loadChart(element);
                break;
            case 'table':
                this.loadTable(element);
                break;
            case 'dashboard':
                this.loadDashboard(element);
                break;
        }
    }
    
    loadChart(element) {
        // Carregar Chart.js apenas quando necessário
        if (!window.Chart) {
            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/chart.js';
            script.onload = () => this.renderChart(element);
            document.head.appendChild(script);
        } else {
            this.renderChart(element);
        }
    }
    
    renderChart(element) {
        // Renderizar gráfico específico
        const chartType = element.dataset.chartType || 'line';
        const ctx = element.getContext('2d');
        
        // Implementação específica do gráfico
        new Chart(ctx, {
            type: chartType,
            data: JSON.parse(element.dataset.chartData),
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }
}

// Inicializar quando DOM estiver pronto
document.addEventListener('DOMContentLoaded', () => {
    new LazyLoader();
});
```

### **📈 TASK 4: Performance Monitoring (2 dias)**

#### **Subtask 4.1: APM Dashboard**
```python
# app/utils/performance_monitor.py
import time
import psutil
from datetime import datetime, timedelta
from app.utils.redis_cache import cache_redis

class PerformanceMonitor:
    """Monitor de performance da aplicação"""
    
    def __init__(self):
        self.metrics = {}
        self.alerts = []
    
    def track_request_performance(self):
        """Middleware para trackear performance de requests"""
        from flask import request, g
        
        def before_request():
            g.start_time = time.time()
        
        def after_request(response):
            total_time = time.time() - g.start_time
            
            # Salvar métrica
            self.record_metric('request_time', {
                'endpoint': request.endpoint,
                'method': request.method,
                'duration': total_time,
                'status_code': response.status_code,
                'timestamp': datetime.now()
            })
            
            # Alertar se muito lento
            if total_time > 3.0:
                self.add_alert(f"Slow request: {request.endpoint} took {total_time:.2f}s")
            
            return response
        
        return before_request, after_request
    
    def record_metric(self, metric_type, data):
        """Registra métrica no Redis"""
        key = f"metrics:{metric_type}:{datetime.now().strftime('%Y%m%d%H')}"
        cache_redis.lpush(key, str(data))
        cache_redis.expire(key, 86400)  # 24h
    
    def get_system_metrics(self):
        """Métricas do sistema"""
        return {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent,
            'timestamp': datetime.now()
        }
    
    def get_database_metrics(self):
        """Métricas do banco de dados"""
        from app import db
        
        # Pool info
        pool = db.engine.pool
        
        return {
            'pool_size': pool.size(),
            'checked_in': pool.checkedin(),
            'checked_out': pool.checkedout(),
            'overflow': pool.overflow(),
            'timestamp': datetime.now()
        }
    
    def generate_performance_report(self):
        """Relatório de performance das últimas 24h"""
        # Buscar métricas do Redis
        metrics_keys = cache_redis.keys("metrics:*")
        
        report = {
            'system': self.get_system_metrics(),
            'database': self.get_database_metrics(),
            'cache_stats': intelligent_cache.get_cache_stats(),
            'recent_alerts': self.alerts[-10:],  # Últimos 10 alertas
            'timestamp': datetime.now()
        }
        
        return report

# Instância global
performance_monitor = PerformanceMonitor()
```

#### **Subtask 4.2: Dashboard de Métricas**
```python
# app/utils/routes.py - Nova rota
@utils_bp.route('/performance-dashboard')
@login_required
@require_admin()
def performance_dashboard():
    """Dashboard de performance em tempo real"""
    
    report = performance_monitor.generate_performance_report()
    query_stats = query_analyzer.get_performance_report()
    
    return render_template('utils/performance_dashboard.html', 
                         report=report, 
                         query_stats=query_stats)
```

```html
<!-- app/templates/utils/performance_dashboard.html -->
<div class="container-fluid">
    <h2>🚀 Performance Dashboard</h2>
    
    <!-- System Metrics -->
    <div class="row mb-4">
        <div class="col-md-3">
            <div class="card">
                <div class="card-body text-center">
                    <h4 id="cpu-usage">{{ report.system.cpu_percent }}%</h4>
                    <p>CPU Usage</p>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card">
                <div class="card-body text-center">
                    <h4 id="memory-usage">{{ report.system.memory_percent }}%</h4>
                    <p>Memory Usage</p>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card">
                <div class="card-body text-center">
                    <h4 id="cache-hit-rate">{{ report.cache_stats.hit_rate }}%</h4>
                    <p>Cache Hit Rate</p>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card">
                <div class="card-body text-center">
                    <h4 id="db-connections">{{ report.database.checked_out }}/{{ report.database.pool_size }}</h4>
                    <p>DB Connections</p>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Query Performance -->
    <div class="row">
        <div class="col-12">
            <div class="card">
                <div class="card-header">
                    <h5>Query Performance</h5>
                </div>
                <div class="card-body">
                    <p><strong>Slow Queries:</strong> {{ query_stats.slow_queries_count }}</p>
                    {% if query_stats.slowest_query %}
                    <p><strong>Slowest:</strong> {{ query_stats.slowest_query.duration }}s</p>
                    <code>{{ query_stats.slowest_query.query }}</code>
                    {% endif %}
                </div>
            </div>
        </div>
    </div>
</div>

<script>
// Auto-refresh a cada 30 segundos
setInterval(() => {
    fetch('/utils/performance-dashboard')
        .then(response => response.text())
        .then(html => {
            // Atualizar apenas as métricas principais
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            
            document.getElementById('cpu-usage').textContent = 
                doc.getElementById('cpu-usage').textContent;
            document.getElementById('memory-usage').textContent = 
                doc.getElementById('memory-usage').textContent;
            document.getElementById('cache-hit-rate').textContent = 
                doc.getElementById('cache-hit-rate').textContent;
            document.getElementById('db-connections').textContent = 
                doc.getElementById('db-connections').textContent;
        });
}, 30000);
</script>
```

---

## 🧪 **PLANO DE TESTES**

### **Performance Tests**
```python
# tests/test_performance.py
import time
import pytest
from app import create_app, db

class TestPerformance:
    
    def test_database_response_time(self):
        """Testa se queries respondem em <50ms"""
        start = time.time()
        
        # Query crítica de teste
        result = db.session.execute("SELECT COUNT(*) FROM pedidos").scalar()
        
        duration = (time.time() - start) * 1000  # ms
        
        assert duration < 50, f"Query took {duration}ms, expected <50ms"
    
    def test_cache_hit_rate(self):
        """Testa se cache hit rate é >85%"""
        stats = intelligent_cache.get_cache_stats()
        
        assert stats['hit_rate'] > 85, f"Cache hit rate is {stats['hit_rate']}%, expected >85%"
    
    def test_page_load_time(self, client):
        """Testa se páginas carregam em <1s"""
        start = time.time()
        
        response = client.get('/monitoramento/listar')
        
        duration = time.time() - start
        
        assert response.status_code == 200
        assert duration < 1.0, f"Page loaded in {duration}s, expected <1s"
```

---

## 📅 **CRONOGRAMA DETALHADO**

### **Semana 1**
**Dia 1-2**: Task 1.1 + 1.2 (Análise queries + Índices)
**Dia 3-4**: Task 1.3 + 2.1 (JoinedLoad + Cache Strategy)
**Dia 5**: Task 3.1 (Asset Optimization)

### **Semana 2**
**Dia 1-2**: Task 2.2 (Aplicação do Cache)
**Dia 3-4**: Task 4.1 + 4.2 (Performance Monitoring)
**Dia 5**: Testes, validação e deploy

---

## ✅ **CRITÉRIOS DE ACEITAÇÃO**

1. **Database Response < 50ms** ✅
2. **Page Load < 1s** ✅
3. **Cache Hit Rate > 85%** ✅
4. **Zero queries > 1s** ✅
5. **Performance Dashboard funcional** ✅
6. **Todos os testes passando** ✅

---

## 🚀 **DEPLOYMENT STRATEGY**

### **Deployment Checklist**
- [ ] Aplicar índices em produção (CONCURRENTLY)
- [ ] Deploy código otimizado
- [ ] Verificar métricas pós-deploy
- [ ] Rollback plan preparado
- [ ] Monitoring ativo

### **Rollback Plan**
```bash
# Se algo der errado:
git revert <commit-hash>
git push origin main

# Remover índices se necessário:
DROP INDEX CONCURRENTLY idx_name;
```

---

**🎯 Sprint Goal**: Sistema 50% mais rápido e monitorado
**👥 Stakeholders**: Todos os usuários do sistema
**📊 Success Metrics**: Tempo resposta, satisfação usuário, throughput 

🚀 **PRÓXIMO SPRINT**

Após este sprint, partimos para o **Sprint 2: Claude AI Superintelligência** com as bases de performance sólidas implementadas.

**Meta**: Sistema 50% mais rápido = Usuários 100% mais satisfeitos 