<!-- doc:meta
tipo: explanation
camada: L3
sot_de: Plano historico de otimizacao de performance do modulo comercial (indices, N+1, agregacao) e o que de fato foi implementado vs proposto
hub: docs/INDEX.md
superseded_by: —
atualizado: 2026-06-15
-->
# 🚀 PLANO DE OTIMIZAÇÃO DE PERFORMANCE - MÓDULO COMERCIAL

> **Papel:** explica o plano original de otimização de performance do módulo comercial e reconcilia cada solução proposta com o que realmente foi implementado no código.

## Contexto

Documento histórico (escrito em 21/01/2025) que mapeou gargalos de performance do módulo comercial e propôs 7 soluções. Esta versão foi reconciliada com o código atual: índices SQL, eliminação de N+1 e agregação foram aplicados de forma parcial/diferente do plano, enquanto cache Redis (Fase 2 item 4) e profiling (Fase 3) NÃO foram implementados. As notas de reconciliação estão marcadas em cada seção.

## Indice

- [Métricas atuais vs esperadas](#-métricas-atuais-vs-esperadas)
- [Solução 1: criar índices compostos](#-solução-1-criar-índices-compostos)
- [Solução 2: eliminar N+1 queries](#-solução-2-eliminar-n1-queries)
- [Solução 3: implementar cache Redis](#-solução-3-implementar-cache-redis)
- [Solução 4: queries agregadas otimizadas](#-solução-4-queries-agregadas-otimizadas)
- [Solução 5: paginação e lazy loading](#-solução-5-paginação-e-lazy-loading)
- [Solução 6: lazy loading de produtos](#-solução-6-lazy-loading-de-produtos)
- [Solução 7: monitoramento e métricas](#-solução-7-monitoramento-e-métricas)
- [Ordem de implementação](#-ordem-de-implementação)
- [Script de teste de performance](#-script-de-teste-de-performance)
- [Checklist de validação](#-checklist-de-validação)
- [Resultado esperado](#-resultado-esperado)
- [Avisos importantes](#-avisos-importantes)
- [Suporte](#-suporte)

**Data:** 21/01/2025
**Objetivo:** Reduzir tempo de carregamento em 90% e queries em 95%

## 📊 MÉTRICAS ATUAIS vs ESPERADAS

| Métrica | Atual | Meta | Redução |
|---------|-------|------|---------|
| Tempo Dashboard | 15-30s | 1-2s | 93% |
| Queries Dashboard | 500+ | 10-15 | 97% |
| Tempo Lista Clientes | 10-20s | 0.5-1s | 95% |
| Queries Lista | 300+ | 5-10 | 97% |
| Uso de Memória | 50-100MB | 10-20MB | 80% |
| Cache Hit Rate | 0% | 90% | - |

---

## 🔧 SOLUÇÃO 1: CRIAR ÍNDICES COMPOSTOS

> **Reconciliação (2026-06-15):** os índices realmente aplicados em produção diferem deste plano. Em particular, o índice `idx_carteira_cnpj_saldo` proposto abaixo foi posteriormente removido (ver `scripts/migrations/limpar_tabelas_deprecated_e_indices.sql`, `DROP INDEX IF EXISTS idx_carteira_cnpj_saldo`). Para o conjunto real de índices em vigor, consultar `scripts/sql/otimizacao_indices_comercial.sql`. O SQL abaixo é o proposto no plano original, mantido como referência histórica.

### 📝 Script SQL para Índices

```sql
-- ========================================
-- ÍNDICES CRÍTICOS PARA PERFORMANCE
-- Execute no banco de dados de produção
-- ========================================

-- 1. CarteiraPrincipal - Índices compostos para queries frequentes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_carteira_cnpj_saldo
ON carteira_principal(cnpj_cpf, qtd_saldo_produto_pedido)
WHERE qtd_saldo_produto_pedido > 0;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_carteira_equipe_vendedor
ON carteira_principal(equipe_vendas, vendedor)
WHERE equipe_vendas IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_carteira_vendedor_cnpj
ON carteira_principal(vendedor, cnpj_cpf)
WHERE vendedor IS NOT NULL;

-- 2. FaturamentoProduto - Índices para agregações
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_faturamento_equipe_vendedor
ON faturamento_produto(equipe_vendas, vendedor)
WHERE equipe_vendas IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_faturamento_cnpj_valor
ON faturamento_produto(cnpj_cliente, valor_produto_faturado);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_faturamento_nf_cnpj
ON faturamento_produto(numero_nf, cnpj_cliente);

-- 3. EntregaMonitorada - Índices para status
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_entrega_status_nf
ON entregas_monitoradas(status_finalizacao, numero_nf)
WHERE status_finalizacao != 'Entregue' OR status_finalizacao IS NULL;

-- 4. Separacao - Índices para sincronização
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_separacao_sync_lote
ON separacao(sincronizado_nf, separacao_lote_id)
WHERE sincronizado_nf = false;

-- Analisar tabelas após criação dos índices
ANALYZE carteira_principal;
ANALYZE faturamento_produto;
ANALYZE entregas_monitoradas;
ANALYZE separacao;
```

**⏱️ Impacto:** Redução de 70% no tempo de queries

---

## 🔧 SOLUÇÃO 2: ELIMINAR N+1 QUERIES

### 📝 Refatoração do Dashboard

**❌ CÓDIGO ATUAL (500+ queries):**
```python
# dashboard_diretoria() - PROBLEMA
for equipe in equipes:
    clientes_cnpj = ClienteService.obter_clientes_por_equipe(equipe)
    valor_total_equipe = 0
    for cnpj in clientes_cnpj:
        valor_cliente = ClienteService.calcular_valor_em_aberto(cnpj)
        valor_total_equipe += valor_cliente
```

**✅ CÓDIGO OTIMIZADO (1 query):**
```python
# dashboard_diretoria() - SOLUÇÃO
@comercial_bp.route('/dashboard')
@login_required
@comercial_required
def dashboard_diretoria():
    """Dashboard otimizado com query única"""

    # Query única agregada para todas as equipes
    query_dashboard = db.session.query(
        CarteiraPrincipal.equipe_vendas,
        func.count(distinct(CarteiraPrincipal.cnpj_cpf)).label('total_clientes'),
        func.sum(
            CarteiraPrincipal.qtd_saldo_produto_pedido *
            CarteiraPrincipal.preco_produto_pedido
        ).label('valor_em_aberto')
    ).filter(
        CarteiraPrincipal.equipe_vendas.isnot(None),
        CarteiraPrincipal.qtd_saldo_produto_pedido > 0
    ).group_by(
        CarteiraPrincipal.equipe_vendas
    )

    # Aplicar filtros de permissão se necessário
    if current_user.perfil == 'vendedor':
        permissoes = cache.get(f'permissoes_usuario_{current_user.id}')
        if not permissoes:
            permissoes = PermissaoService.obter_permissoes_usuario(current_user.id)
            cache.set(f'permissoes_usuario_{current_user.id}', permissoes, timeout=300)

        if permissoes['equipes']:
            query_dashboard = query_dashboard.filter(
                CarteiraPrincipal.equipe_vendas.in_(permissoes['equipes'])
            )

    equipes_data = []
    for row in query_dashboard.all():
        equipes_data.append({
            'nome': row.equipe_vendas,
            'total_clientes': row.total_clientes or 0,
            'valor_em_aberto': float(row.valor_em_aberto or 0)
        })

    return render_template('comercial/dashboard_diretoria.html', equipes=equipes_data)
```

---

## 🔧 SOLUÇÃO 3: IMPLEMENTAR CACHE REDIS

> **Reconciliação (2026-06-15):** esta solução (Fase 2, item 4) NÃO foi implementada. Não há `flask_caching` configurado no módulo `app/comercial/`. Em vez do cache Redis descrito abaixo, o `app/comercial/services/agregacao_service.py` usa um cache process-level interno apenas para o status das materialized views (ver o comentário `# Cache do status das materialized views (verificado 1x por processo)` no início do arquivo). O código abaixo é o desenho proposto, mantido como referência histórica.

### 📝 Configuração do Cache

```python
# app/comercial/cache_config.py
from flask_caching import Cache
from functools import wraps
import hashlib
import json

cache = Cache(config={
    'CACHE_TYPE': 'redis',
    'CACHE_REDIS_HOST': 'localhost',
    'CACHE_REDIS_PORT': 6379,
    'CACHE_REDIS_DB': 0,
    'CACHE_DEFAULT_TIMEOUT': 300  # 5 minutos
})

def cache_key_wrapper(prefix):
    """Decorator para criar cache keys inteligentes"""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            # Criar chave única baseada nos argumentos
            key_data = f"{prefix}:{str(args)}:{str(kwargs)}"
            cache_key = hashlib.md5(key_data.encode()).hexdigest()

            # Verificar cache
            cached = cache.get(cache_key)
            if cached is not None:
                return cached

            # Executar função e cachear resultado
            result = f(*args, **kwargs)
            cache.set(cache_key, result, timeout=300)
            return result
        return wrapped
    return decorator
```

### 📝 Aplicação do Cache nos Services

```python
# app/comercial/services/cliente_service.py
class ClienteService:

    @staticmethod
    @cache_key_wrapper('clientes_equipe')
    def obter_clientes_por_equipe(equipe_vendas: str) -> List[str]:
        """Versão cacheada - resultados por 5 minutos"""
        # ... código existente ...

    @staticmethod
    @cache_key_wrapper('valor_aberto')
    def calcular_valor_em_aberto_batch(cnpjs: List[str]) -> Dict[str, Decimal]:
        """
        Nova função para calcular valores em batch
        Evita N+1 queries
        """
        valores = {}

        # Uma query para todos os CNPJs
        saldos = db.session.query(
            CarteiraPrincipal.cnpj_cpf,
            func.sum(
                CarteiraPrincipal.qtd_saldo_produto_pedido *
                CarteiraPrincipal.preco_produto_pedido
            ).label('valor')
        ).filter(
            CarteiraPrincipal.cnpj_cpf.in_(cnpjs),
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        ).group_by(
            CarteiraPrincipal.cnpj_cpf
        ).all()

        for row in saldos:
            valores[row.cnpj_cpf] = Decimal(str(row.valor or 0))

        return valores
```

---

## 🔧 SOLUÇÃO 4: QUERIES AGREGADAS OTIMIZADAS

### 📝 Novo Service de Agregação

```python
# app/comercial/services/agregacao_service.py
from sqlalchemy import text
from app import db

class AgregacaoComercialService:
    """Service otimizado para agregações do módulo comercial"""

    @staticmethod
    @cache_key_wrapper('dashboard_completo')
    def obter_dashboard_completo():
        """
        Retorna todos os dados do dashboard em uma única query
        Usando CTE (Common Table Expression) para performance máxima
        """
        sql = text("""
            WITH dados_equipes AS (
                SELECT
                    equipe_vendas,
                    COUNT(DISTINCT cnpj_cpf) as total_clientes,
                    SUM(qtd_saldo_produto_pedido * preco_produto_pedido) as valor_carteira
                FROM carteira_principal
                WHERE equipe_vendas IS NOT NULL
                  AND qtd_saldo_produto_pedido > 0
                GROUP BY equipe_vendas
            ),
            dados_faturamento AS (
                SELECT
                    equipe_vendas,
                    COUNT(DISTINCT cnpj_cliente) as clientes_faturados,
                    SUM(valor_produto_faturado) as valor_faturado
                FROM faturamento_produto fp
                WHERE equipe_vendas IS NOT NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM entregas_monitoradas em
                      WHERE em.numero_nf = fp.numero_nf
                        AND em.status_finalizacao = 'Entregue'
                  )
                GROUP BY equipe_vendas
            )
            SELECT
                COALESCE(de.equipe_vendas, df.equipe_vendas) as equipe,
                COALESCE(de.total_clientes, 0) + COALESCE(df.clientes_faturados, 0) as total_clientes,
                COALESCE(de.valor_carteira, 0) + COALESCE(df.valor_faturado, 0) as valor_total
            FROM dados_equipes de
            FULL OUTER JOIN dados_faturamento df ON de.equipe_vendas = df.equipe_vendas
            ORDER BY equipe
        """)

        result = db.session.execute(sql)
        return [dict(row) for row in result]

    @staticmethod
    @cache_key_wrapper('vendedores_equipe_completo')
    def obter_vendedores_equipe_otimizado(equipe_nome: str):
        """
        Retorna dados de todos vendedores da equipe em uma query
        """
        sql = text("""
            WITH vendedores_dados AS (
                SELECT
                    vendedor,
                    COUNT(DISTINCT cnpj_cpf) as total_clientes,
                    SUM(qtd_saldo_produto_pedido * preco_produto_pedido) as valor_aberto
                FROM carteira_principal
                WHERE equipe_vendas = :equipe
                  AND vendedor IS NOT NULL
                  AND qtd_saldo_produto_pedido > 0
                GROUP BY vendedor
            )
            SELECT
                vendedor as nome,
                total_clientes,
                COALESCE(valor_aberto, 0) as valor_em_aberto
            FROM vendedores_dados
            ORDER BY vendedor
        """)

        result = db.session.execute(sql, {'equipe': equipe_nome})
        return [dict(row) for row in result]
```

---

## 🔧 SOLUÇÃO 5: PAGINAÇÃO E LAZY LOADING

### 📝 Implementar Paginação na Lista de Clientes

```python
# app/comercial/routes/diretoria.py
@comercial_bp.route('/clientes')
@login_required
@comercial_required
def lista_clientes():
    """Lista de clientes com paginação"""

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)  # 50 clientes por página
    filtro_posicao = request.args.get('posicao', 'em_aberto')

    # Query base otimizada
    query_base = db.session.query(
        CarteiraPrincipal.cnpj_cpf,
        CarteiraPrincipal.raz_social,
        CarteiraPrincipal.raz_social_red,
        CarteiraPrincipal.estado,
        CarteiraPrincipal.municipio,
        CarteiraPrincipal.vendedor,
        CarteiraPrincipal.equipe_vendas,
        func.sum(
            CarteiraPrincipal.qtd_saldo_produto_pedido *
            CarteiraPrincipal.preco_produto_pedido
        ).label('valor_em_aberto'),
        func.count(distinct(CarteiraPrincipal.num_pedido)).label('total_pedidos')
    ).filter(
        CarteiraPrincipal.qtd_saldo_produto_pedido > 0
    ).group_by(
        CarteiraPrincipal.cnpj_cpf,
        CarteiraPrincipal.raz_social,
        CarteiraPrincipal.raz_social_red,
        CarteiraPrincipal.estado,
        CarteiraPrincipal.municipio,
        CarteiraPrincipal.vendedor,
        CarteiraPrincipal.equipe_vendas
    )

    # Aplicar filtros de permissão
    if current_user.perfil == 'vendedor':
        query_base = PermissaoService.aplicar_filtro_permissoes(query_base)

    # Paginar
    clientes_paginados = query_base.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

    return render_template('comercial/lista_clientes.html',
                         clientes=clientes_paginados,
                         filtro_posicao=filtro_posicao)
```

### 📝 Template com Paginação

```html
<!-- templates/comercial/lista_clientes.html -->
<!-- Adicionar no final da tabela -->
<nav aria-label="Paginação">
    <ul class="pagination justify-content-center">
        {% if clientes.has_prev %}
            <li class="page-item">
                <a class="page-link" href="?page={{ clientes.prev_num }}">Anterior</a>
            </li>
        {% endif %}

        {% for page_num in clientes.iter_pages(left_edge=1, right_edge=1, left_current=1, right_current=2) %}
            {% if page_num %}
                <li class="page-item {% if page_num == clientes.page %}active{% endif %}">
                    <a class="page-link" href="?page={{ page_num }}">{{ page_num }}</a>
                </li>
            {% else %}
                <li class="page-item disabled"><span class="page-link">...</span></li>
            {% endif %}
        {% endfor %}

        {% if clientes.has_next %}
            <li class="page-item">
                <a class="page-link" href="?page={{ clientes.next_num }}">Próximo</a>
            </li>
        {% endif %}
    </ul>
</nav>

<!-- Informação de registros -->
<div class="text-center text-muted">
    Mostrando {{ clientes.per_page * (clientes.page - 1) + 1 }} -
    {{ min(clientes.per_page * clientes.page, clientes.total) }}
    de {{ clientes.total }} clientes
</div>
```

---

## 🔧 SOLUÇÃO 6: LAZY LOADING DE PRODUTOS

### 📝 Otimizar Carregamento de Produtos dos Documentos

```python
# app/comercial/services/produto_documento_service.py
class ProdutoDocumentoService:

    @staticmethod
    @cache_key_wrapper('produtos_documento')
    def obter_produtos_documento_otimizado(tipo: str, identificador: str):
        """Versão otimizada com cache e query única"""

        if tipo == 'nf':
            # Query única para todos os produtos da NF
            produtos = db.session.query(
                FaturamentoProduto.cod_produto,
                FaturamentoProduto.nome_produto,
                FaturamentoProduto.qtd_produto_faturado,
                FaturamentoProduto.preco_produto_faturado,
                FaturamentoProduto.valor_produto_faturado,
                FaturamentoProduto.peso_total
            ).filter(
                FaturamentoProduto.numero_nf == identificador
            ).all()

            return {
                'success': True,
                'produtos': [
                    {
                        'codigo': p.cod_produto,
                        'nome': p.nome_produto,
                        'quantidade': float(p.qtd_produto_faturado),
                        'preco': float(p.preco_produto_faturado),
                        'valor': float(p.valor_produto_faturado),
                        'peso': float(p.peso_total) if p.peso_total else None,
                        'pallet': None
                    } for p in produtos
                ]
            }

        # Similar para outros tipos...
```

---

## 🔧 SOLUÇÃO 7: MONITORAMENTO E MÉTRICAS

> **Reconciliação (2026-06-15):** esta solução (Fase 3) NÃO foi implementada. O arquivo `app/comercial/utils/performance.py` com o decorator `monitor_performance` não existe no repositório. O código abaixo é o desenho proposto, mantido como referência histórica.

### 📝 Adicionar Profiling de Performance

```python
# app/comercial/utils/performance.py
import time
from functools import wraps
import logging

logger = logging.getLogger('performance')

def monitor_performance(operation_name):
    """Decorator para monitorar performance de funções"""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            start_time = time.time()

            # Contar queries antes
            from app import db
            queries_before = len(db.session.query._legacy_facade)

            try:
                result = f(*args, **kwargs)

                # Calcular métricas
                execution_time = time.time() - start_time
                queries_count = len(db.session.query._legacy_facade) - queries_before

                # Log se demorar muito
                if execution_time > 1.0:  # Mais de 1 segundo
                    logger.warning(
                        f"SLOW: {operation_name} took {execution_time:.2f}s "
                        f"with {queries_count} queries"
                    )
                else:
                    logger.info(
                        f"OK: {operation_name} took {execution_time:.2f}s "
                        f"with {queries_count} queries"
                    )

                return result

            except Exception as e:
                logger.error(f"ERROR in {operation_name}: {str(e)}")
                raise

        return wrapped
    return decorator

# Aplicar nas rotas principais
@comercial_bp.route('/dashboard')
@login_required
@comercial_required
@monitor_performance('dashboard_diretoria')
def dashboard_diretoria():
    # ... código ...
```

---

## 📋 ORDEM DE IMPLEMENTAÇÃO

### Fase 1 - Imediato (1-2 dias)
1. ✅ Executar script de índices SQL — **nota (2026-06-15):** índices aplicados diferem do plano; ver `scripts/sql/otimizacao_indices_comercial.sql` para o conjunto real em vigor (`idx_carteira_cnpj_saldo` deste plano foi removido em `scripts/migrations/limpar_tabelas_deprecated_e_indices.sql`).
2. ✅ Implementar queries agregadas no dashboard
3. ✅ Eliminar loops N+1 nas rotas principais

**Ganho esperado: 70% de melhoria**

### Fase 2 - Curto Prazo (3-5 dias)
4. ❌ Configurar Redis e implementar cache — **NÃO realizado** (sem `flask_caching` no módulo; `agregacao_service.py` usa cache process-level interno de MV).
5. ⏳ Adicionar paginação na lista de clientes
6. ⏳ Otimizar ProdutoDocumentoService

**Ganho esperado: +20% de melhoria (total 90%)**

### Fase 3 - Médio Prazo (1 semana)
7. ❌ Implementar monitoring completo — **NÃO realizado** (`app/comercial/utils/performance.py` não existe).
8. ⏳ Criar testes de performance
9. ⏳ Otimizar templates e JavaScript

**Ganho esperado: +5% de melhoria (total 95%)**

---

## 🧪 SCRIPT DE TESTE DE PERFORMANCE

```python
# test_performance_comercial.py
import time
import statistics
from app import create_app
from flask import url_for

def test_dashboard_performance():
    """Testa performance do dashboard"""
    app = create_app()

    with app.test_client() as client:
        # Login
        client.post('/login', data={
            'email': 'admin@teste.com',
            'password': 'senha123'
        })

        # Testar dashboard 10 vezes
        tempos = []
        for i in range(10):
            start = time.time()
            response = client.get('/comercial/dashboard')
            tempo = time.time() - start
            tempos.append(tempo)
            print(f"Tentativa {i+1}: {tempo:.2f}s")

        print(f"\nTempo médio: {statistics.mean(tempos):.2f}s")
        print(f"Tempo máximo: {max(tempos):.2f}s")
        print(f"Tempo mínimo: {min(tempos):.2f}s")

        # Verificar se está dentro da meta
        assert statistics.mean(tempos) < 2.0, "Dashboard muito lento!"

if __name__ == '__main__':
    test_dashboard_performance()
```

---

## ✅ CHECKLIST DE VALIDAÇÃO

- [ ] Índices criados no banco de produção
- [ ] Dashboard carregando em menos de 2 segundos
- [ ] Lista de clientes paginada funcionando
- [ ] Cache Redis configurado e funcionando
- [ ] Logs de performance ativos
- [ ] Testes de performance passando
- [ ] Documentação atualizada

---

## 📊 RESULTADO ESPERADO

### Antes:
- **500+ queries** por página
- **15-30 segundos** de carregamento
- **50-100MB** de memória
- **Timeouts** em horários de pico

### Depois:
- **10-15 queries** por página
- **1-2 segundos** de carregamento
- **10-20MB** de memória
- **Resposta estável** mesmo em pico

### ROI:
- **95% menos queries** no banco
- **90% menos tempo** de espera
- **80% menos memória** utilizada
- **100% mais satisfação** do usuário

---

## 🚨 AVISOS IMPORTANTES

1. **Testar em homologação primeiro** antes de aplicar em produção
2. **Fazer backup do banco** antes de criar índices
3. **Monitorar performance** após cada mudança
4. **Implementar gradualmente** para identificar problemas
5. **Documentar mudanças** para a equipe

---

## 📞 SUPORTE

Em caso de dúvidas ou problemas durante a implementação:
1. Verificar logs de performance em `/var/log/comercial/`
2. Usar o script de teste para validar melhorias
3. Revisar queries lentas no PostgreSQL com `pg_stat_statements`
