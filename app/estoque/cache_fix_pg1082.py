"""
Solução definitiva para erro PG 1082 no cache de estoque
Implementa fallback robusto para ambientes de produção
"""
from app import db
from app.estoque.models_cache import SaldoEstoqueCache, ProjecaoEstoqueCache
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

def obter_projecao_cache_segura(cod_produto):
    """
    Obtém projeção do cache com tratamento robusto para erro PG 1082
    Usa múltiplas estratégias de fallback
    """
    try:
        # ESTRATÉGIA 1: Query com TO_CHAR (mais segura)
        logger.debug(f"Tentando obter projeção para {cod_produto} com TO_CHAR")
        
        query = text("""
            SELECT 
                cod_produto,
                TO_CHAR(data_projecao, 'YYYY-MM-DD') as data_str,
                dia_offset,
                COALESCE(estoque_inicial, 0) as estoque_inicial,
                COALESCE(saida_prevista, 0) as saida_prevista,
                COALESCE(producao_programada, 0) as producao_programada,
                COALESCE(estoque_final, 0) as estoque_final
            FROM projecao_estoque_cache
            WHERE cod_produto = :cod
            ORDER BY dia_offset
        """)
        
        result = db.session.execute(query, {'cod': str(cod_produto)})
        projecoes = result.fetchall()
        
        logger.debug(f"✅ Query TO_CHAR bem sucedida: {len(projecoes)} registros")
        return projecoes
        
    except Exception as e:
        if "1082" in str(e):
            logger.warning(f"Erro PG 1082 detectado, tentando fallback: {e}")
            
            # ESTRATÉGIA 2: Query sem campo DATE
            try:
                query = text("""
                    SELECT 
                        cod_produto,
                        dia_offset,
                        COALESCE(estoque_inicial, 0) as estoque_inicial,
                        COALESCE(saida_prevista, 0) as saida_prevista,
                        COALESCE(producao_programada, 0) as producao_programada,
                        COALESCE(estoque_final, 0) as estoque_final
                    FROM projecao_estoque_cache
                    WHERE cod_produto = :cod
                    ORDER BY dia_offset
                """)
                
                result = db.session.execute(query, {'cod': str(cod_produto)})
                projecoes_sem_data = result.fetchall()
                
                # Adicionar data calculada baseada no offset
                from datetime import datetime, timedelta
                hoje = datetime.now().date()
                
                projecoes = []
                for row in projecoes_sem_data:
                    data_calc = hoje + timedelta(days=row[1])
                    # Criar tupla compatível com formato esperado
                    projecoes.append((
                        row[0],  # cod_produto
                        data_calc.strftime('%Y-%m-%d'),  # data_str
                        row[1],  # dia_offset
                        row[2],  # estoque_inicial
                        row[3],  # saida_prevista
                        row[4],  # producao_programada
                        row[5]   # estoque_final
                    ))
                
                logger.info(f"✅ Fallback sem DATE bem sucedido: {len(projecoes)} registros")
                return projecoes
                
            except Exception as e2:
                logger.error(f"❌ Fallback também falhou: {e2}")
                return []
        else:
            logger.error(f"❌ Erro não relacionado a PG 1082: {e}")
            return []

def obter_cache_seguro(cod_produto):
    """
    Obtém dados completos do cache com tratamento robusto
    """
    try:
        # Buscar cache principal
        cache = SaldoEstoqueCache.query.filter_by(cod_produto=str(cod_produto)).first()
        
        if not cache:
            logger.debug(f"Cache não encontrado para {cod_produto}")
            return None
            
        # Buscar projeções com método seguro
        projecoes = obter_projecao_cache_segura(cod_produto)
        
        # Formatar projeções
        projecao_formatada = []
        for proj in projecoes:
            try:
                cod, data_str, dia_offset, est_ini, saida, prod, est_fim = proj
                
                # Formatar data
                data_formatada = ''
                if data_str:
                    try:
                        from datetime import datetime
                        data_temp = datetime.strptime(data_str, '%Y-%m-%d')
                        data_formatada = data_temp.strftime('%d/%m')
                    except:
                        data_formatada = data_str[:5] if len(data_str) > 5 else data_str
                
                projecao_formatada.append({
                    'dia': dia_offset,
                    'data': data_str,
                    'data_formatada': data_formatada,
                    'estoque_inicial': float(est_ini),
                    'saida_prevista': float(saida),
                    'producao_programada': float(prod),
                    'estoque_final': float(est_fim)
                })
            except Exception as e:
                logger.debug(f"Erro ao formatar projeção: {e}")
                continue
        
        # Retornar dados completos
        return {
            'cod_produto': cache.cod_produto,
            'nome_produto': cache.nome_produto,
            'estoque_inicial': float(cache.saldo_atual or 0),
            'qtd_carteira': float(cache.qtd_carteira or 0),
            'qtd_pre_separacao': float(cache.qtd_pre_separacao or 0),
            'qtd_separacao': float(cache.qtd_separacao or 0),
            'previsao_ruptura': float(cache.previsao_ruptura_7d or 0),
            'status_ruptura': cache.status_ruptura or 'OK',
            'projecao_29_dias': projecao_formatada
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter cache seguro: {e}")
        return None