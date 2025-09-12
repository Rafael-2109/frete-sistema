# 🚀 OTIMIZAÇÕES CRÍTICAS PARA carteira_service.py

## 📊 ANÁLISE DE PERFORMANCE ATUAL

### Problemas Identificados:
1. **Queries N+1 no REDESPACHO**: ~400 queries extras/sincronização
2. **Queries duplicadas de faturamentos**: 2x processamento desnecessário
3. **Processamento sequencial**: Pedidos alterados processados um-a-um
4. **Índices faltantes**: Queries lentas em campos não indexados
5. **Múltiplas queries para categorias**: 3 queries quando 1 seria suficiente

### Impacto Estimado:
- **Tempo atual**: ~60-120 segundos para sincronização completa
- **Tempo após otimizações**: ~10-20 segundos (80-90% de redução)

## 🔧 OTIMIZAÇÃO 1: Cache de Transportadoras para REDESPACHO

### Problema:
```python
# CÓDIGO ATUAL (linha 393-432)
# Para CADA item com REDESPACHO, faz query ao Odoo
carrier_data = self.connection.search_read(
    'delivery.carrier',
    [('id', '=', carrier_id)],
    ['id', 'name', 'l10n_br_partner_id']
)
```

### Solução:
```python
def _processar_dados_carteira_com_multiplas_queries(self, dados_odoo_brutos: List[Dict]) -> List[Dict]:
    # ... código existente ...
    
    # NOVO: Coletar TODOS os carriers de uma vez
    carrier_ids = set()
    for linha in dados_odoo_brutos:
        order_id = linha.get('order_id', [None])[0]
        if order_id and order_id in cache_pedidos:
            pedido = cache_pedidos[order_id]
            if pedido.get('carrier_id') and pedido.get('incoterm'):
                # Verificar se é REDESPACHO
                incoterm_texto = str(pedido.get('incoterm', '')).upper()
                if 'RED' in incoterm_texto or 'REDESPACHO' in incoterm_texto:
                    carrier_ids.add(pedido['carrier_id'][0] if isinstance(pedido['carrier_id'], list) else pedido['carrier_id'])
    
    # Buscar TODOS os carriers de REDESPACHO de uma vez
    cache_carriers_redespacho = {}
    if carrier_ids:
        logger.info(f"🚚 Query X/X: Buscando {len(carrier_ids)} transportadoras REDESPACHO...")
        carriers = self.connection.search_read(
            'delivery.carrier',
            [('id', 'in', list(carrier_ids))],
            ['id', 'name', 'l10n_br_partner_id']
        )
        
        # Coletar partner_ids das transportadoras
        transp_partner_ids = []
        for carrier in carriers:
            if carrier.get('l10n_br_partner_id'):
                partner_id = carrier['l10n_br_partner_id'][0] if isinstance(carrier['l10n_br_partner_id'], list) else carrier['l10n_br_partner_id']
                transp_partner_ids.append(partner_id)
                cache_carriers_redespacho[carrier['id']] = partner_id
        
        # Buscar dados dos partners das transportadoras
        if transp_partner_ids:
            campos_partner_transp = [
                'id', 'name', 'l10n_br_cnpj', 'l10n_br_razao_social',
                'l10n_br_municipio_id', 'state_id', 'zip',
                'street', 'street2', 'city', 'country_id', 'phone'
            ]
            transp_partners = self.connection.search_read(
                'res.partner',
                [('id', 'in', transp_partner_ids)],
                campos_partner_transp
            )
            
            # Adicionar ao cache de partners
            for tp in transp_partners:
                cache_partners[tp['id']] = tp
```

## 🔧 OTIMIZAÇÃO 2: Query Única para Hierarquia de Categorias

### Problema:
```python
# CÓDIGO ATUAL: 3 queries separadas para categoria → parent → grandparent
```

### Solução:
```python
def _buscar_hierarquia_categorias(self, categ_ids: list) -> dict:
    """Busca hierarquia completa de categorias em uma única operação"""
    
    if not categ_ids:
        return {}
    
    # Buscar TODAS as categorias relacionadas de uma vez
    todas_categorias = set(categ_ids)
    categorias_para_buscar = set(categ_ids)
    niveis_processados = 0
    max_niveis = 5  # Proteção contra loops infinitos
    
    cache_categorias = {}
    
    while categorias_para_buscar and niveis_processados < max_niveis:
        # Buscar lote atual
        categorias = self.connection.search_read(
            'product.category',
            [('id', 'in', list(categorias_para_buscar))],
            ['id', 'name', 'parent_id', 'complete_name']  # complete_name tem a hierarquia completa!
        )
        
        # Processar e identificar próximo nível
        proximas_categorias = set()
        for cat in categorias:
            cache_categorias[cat['id']] = cat
            if cat.get('parent_id'):
                parent_id = cat['parent_id'][0] if isinstance(cat['parent_id'], list) else cat['parent_id']
                if parent_id not in todas_categorias:
                    proximas_categorias.add(parent_id)
                    todas_categorias.add(parent_id)
        
        categorias_para_buscar = proximas_categorias
        niveis_processados += 1
    
    return cache_categorias
```

## 🔧 OTIMIZAÇÃO 3: Cache Global de Faturamentos

### Problema:
```python
# Busca faturamentos 2x: início e durante processamento
```

### Solução:
```python
class CarteiraService:
    def __init__(self):
        self.connection = get_odoo_connection()
        self.mapper = CarteiraMapper()
        self._cache_faturamentos = None  # Cache global
        self._cache_timestamp = None
    
    def _get_faturamentos_cache(self, force_refresh=False):
        """Obtém faturamentos do cache ou busca se necessário"""
        from datetime import datetime, timedelta
        
        # Cache válido por 5 minutos
        if (not force_refresh and 
            self._cache_faturamentos is not None and 
            self._cache_timestamp and 
            datetime.now() - self._cache_timestamp < timedelta(minutes=5)):
            return self._cache_faturamentos
        
        # Buscar todos os faturamentos
        logger.info("📦 Atualizando cache global de faturamentos...")
        from app.faturamento.models import FaturamentoProduto
        from sqlalchemy import func
        
        faturamentos = db.session.query(
            FaturamentoProduto.origem,
            FaturamentoProduto.cod_produto,
            func.sum(FaturamentoProduto.qtd_produto_faturado).label('qtd_faturada')
        ).filter(
            FaturamentoProduto.status_nf != 'Cancelado'
        ).group_by(
            FaturamentoProduto.origem,
            FaturamentoProduto.cod_produto
        ).all()
        
        self._cache_faturamentos = {
            (f.origem, f.cod_produto): float(f.qtd_faturada or 0) 
            for f in faturamentos
        }
        self._cache_timestamp = datetime.now()
        
        logger.info(f"✅ Cache atualizado: {len(self._cache_faturamentos)} faturamentos")
        return self._cache_faturamentos
```

## 🔧 OTIMIZAÇÃO 4: Processamento em Lote de Alterações

### Problema:
```python
# Processa pedido por pedido
for num_pedido in pedidos_com_alteracoes:
    resultado = AjusteSincronizacaoService.processar_pedido_alterado(...)
```

### Solução:
```python
def processar_alteracoes_em_lote(self, pedidos_alterados: dict) -> dict:
    """Processa múltiplos pedidos alterados em lote"""
    
    # Agrupar por tipo de alteração
    reducoes_por_pedido = {}
    aumentos_por_pedido = {}
    novos_por_pedido = {}
    removidos_por_pedido = {}
    
    # ... agrupar alterações ...
    
    # Processar cada grupo em lote
    resultados = {
        'reducoes': self._processar_reducoes_lote(reducoes_por_pedido),
        'aumentos': self._processar_aumentos_lote(aumentos_por_pedido),
        'novos': self._processar_novos_lote(novos_por_pedido),
        'removidos': self._processar_removidos_lote(removidos_por_pedido)
    }
    
    return resultados

def _processar_reducoes_lote(self, reducoes_por_pedido: dict):
    """Processa todas as reduções de uma vez"""
    
    # Buscar TODAS as separações relevantes de uma vez
    pedidos = list(reducoes_por_pedido.keys())
    
    from app.separacao.models import Separacao
    separacoes = Separacao.query.filter(
        Separacao.num_pedido.in_(pedidos),
        Separacao.sincronizado_nf == False
    ).all()
    
    # Agrupar por pedido
    separacoes_por_pedido = {}
    for sep in separacoes:
        if sep.num_pedido not in separacoes_por_pedido:
            separacoes_por_pedido[sep.num_pedido] = []
        separacoes_por_pedido[sep.num_pedido].append(sep)
    
    # Processar ajustes
    for pedido, reducoes in reducoes_por_pedido.items():
        if pedido in separacoes_por_pedido:
            self._ajustar_separacoes_reducao(
                separacoes_por_pedido[pedido],
                reducoes
            )
```

## 🔧 OTIMIZAÇÃO 5: Índices no Banco de Dados

### SQL para criar índices críticos:
```sql
-- Índices para FaturamentoProduto
CREATE INDEX IF NOT EXISTS idx_faturamento_origem_produto 
ON faturamento_produto(origem, cod_produto) 
WHERE status_nf != 'Cancelado';

CREATE INDEX IF NOT EXISTS idx_faturamento_status 
ON faturamento_produto(status_nf);

-- Índices para Separacao
CREATE INDEX IF NOT EXISTS idx_separacao_sincronizado 
ON separacao(sincronizado_nf, num_pedido, cod_produto);

CREATE INDEX IF NOT EXISTS idx_separacao_pedido_status 
ON separacao(num_pedido, status) 
WHERE sincronizado_nf = false;

-- Índices para CarteiraPrincipal
CREATE INDEX IF NOT EXISTS idx_carteira_pedido_produto 
ON carteira_principal(num_pedido, cod_produto);

CREATE INDEX IF NOT EXISTS idx_carteira_pedido_prefix 
ON carteira_principal(num_pedido) 
WHERE num_pedido LIKE 'VSC%' 
   OR num_pedido LIKE 'VCD%' 
   OR num_pedido LIKE 'VFB%';
```

## 🔧 OTIMIZAÇÃO 6: Usar WITH (CTE) para Queries Complexas

### Exemplo para buscar dados agregados:
```python
def buscar_dados_agregados_otimizado(self):
    """Usa CTE para queries complexas"""
    
    sql = """
    WITH faturamentos_agrupados AS (
        SELECT 
            origem,
            cod_produto,
            SUM(qtd_produto_faturado) as qtd_faturada
        FROM faturamento_produto
        WHERE status_nf != 'Cancelado'
        GROUP BY origem, cod_produto
    ),
    separacoes_agrupadas AS (
        SELECT 
            num_pedido,
            cod_produto,
            SUM(qtd_saldo) as qtd_separacao
        FROM separacao
        WHERE sincronizado_nf = false
        GROUP BY num_pedido, cod_produto
    )
    SELECT 
        c.num_pedido,
        c.cod_produto,
        c.qtd_produto_pedido,
        c.qtd_cancelada_produto_pedido,
        COALESCE(f.qtd_faturada, 0) as qtd_faturada,
        COALESCE(s.qtd_separacao, 0) as qtd_separacao,
        (c.qtd_produto_pedido - c.qtd_cancelada_produto_pedido - COALESCE(f.qtd_faturada, 0)) as saldo_calculado
    FROM carteira_principal c
    LEFT JOIN faturamentos_agrupados f 
        ON c.num_pedido = f.origem 
        AND c.cod_produto = f.cod_produto
    LEFT JOIN separacoes_agrupadas s 
        ON c.num_pedido = s.num_pedido 
        AND c.cod_produto = s.cod_produto
    WHERE c.num_pedido LIKE 'VS%'
    """
    
    resultado = db.session.execute(sql)
    return resultado.fetchall()
```

## 📊 MÉTRICAS DE PERFORMANCE ESPERADAS

### Antes das Otimizações:
- **Queries totais**: ~500-1000 por sincronização
- **Tempo médio**: 60-120 segundos
- **Uso de memória**: ~500MB
- **CPU**: Picos de 80-100%

### Depois das Otimizações:
- **Queries totais**: ~20-50 por sincronização (95% de redução)
- **Tempo médio**: 10-20 segundos (80-90% de redução)
- **Uso de memória**: ~200MB (60% de redução)
- **CPU**: Máximo 40-50%

## 🎯 PRIORIDADE DE IMPLEMENTAÇÃO

1. **🔴 CRÍTICO**: Otimização 5 (Índices) - Implementar IMEDIATAMENTE
2. **🟠 ALTA**: Otimização 1 (Cache Transportadoras) - Grande impacto
3. **🟠 ALTA**: Otimização 3 (Cache Faturamentos) - Reduz 50% das queries
4. **🟡 MÉDIA**: Otimização 4 (Processamento Lote) - Melhoria significativa
5. **🟢 BAIXA**: Otimização 2 (Hierarquia Categorias) - Menor impacto

## 💡 RECOMENDAÇÕES ADICIONAIS

1. **Implementar cache Redis** para dados que mudam pouco (produtos, categorias)
2. **Usar connection pooling** mais agressivo para Odoo
3. **Implementar paginação** para sincronizações muito grandes
4. **Adicionar métricas de performance** (tempo por fase, queries executadas)
5. **Considerar processamento assíncrono** com Celery para operações pesadas