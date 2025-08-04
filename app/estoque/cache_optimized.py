"""
Sistema de Cache Otimizado para Estoque
========================================
Versão com alta performance que atualiza apenas o necessário
Com proteção contra operações concorrentes
"""

from app import db
from app.estoque.models_cache import SaldoEstoqueCache, ProjecaoEstoqueCache
from app.utils.timezone import agora_brasil
import logging
import threading
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Lock global por produto para evitar condições de corrida
_locks_por_produto = {}
_lock_geral = threading.Lock()

@contextmanager
def lock_produto(cod_produto):
    """
    Context manager para garantir acesso exclusivo ao cache de um produto
    Evita condições de corrida em operações concorrentes
    """
    global _locks_por_produto, _lock_geral
    
    # Obter ou criar lock para o produto
    with _lock_geral:
        if cod_produto not in _locks_por_produto:
            _locks_por_produto[cod_produto] = threading.Lock()
        lock = _locks_por_produto[cod_produto]
    
    # Tentar adquirir o lock com timeout
    acquired = lock.acquire(timeout=10)  # Timeout de 10 segundos
    if not acquired:
        logger.warning(f"⚠️ Timeout ao tentar lock para produto {cod_produto}")
        yield False
        return
    
    try:
        yield True
    finally:
        lock.release()
        
        # Limpar locks não utilizados (evitar vazamento de memória)
        with _lock_geral:
            if len(_locks_por_produto) > 1000:  # Limpar se tiver muitos locks
                _locks_por_produto.clear()

class CacheOptimizado:
    """
    Gerenciador otimizado de cache que minimiza operações desnecessárias
    """
    
    @staticmethod
    def atualizar_apenas_quantidades(cod_produto):
        """
        Atualiza APENAS as quantidades de carteira/separação sem recalcular saldo
        Muito mais rápido para mudanças em datas
        Com proteção contra concorrência
        """
        with lock_produto(cod_produto) as lock_acquired:
            if not lock_acquired:
                logger.error(f"Não foi possível obter lock para produto {cod_produto}")
                return False
        
        try:
            from app.carteira.models import CarteiraPrincipal, PreSeparacaoItem
            from app.separacao.models import Separacao
            from app.pedidos.models import Pedido
            from app.estoque.models import UnificacaoCodigos
            
            # Obter cache existente
            cache = SaldoEstoqueCache.query.filter_by(cod_produto=str(cod_produto)).first()
            if not cache:
                logger.warning(f"Cache não encontrado para produto {cod_produto}")
                return False
            
            # Obter códigos relacionados
            try:
                codigos_relacionados = UnificacaoCodigos.get_todos_codigos_relacionados(cod_produto)
            except Exception as e:
                logger.error(f"Erro ao obter códigos relacionados: {e}")
                codigos_relacionados = [str(cod_produto)]
            
            # OTIMIZAÇÃO: Usar COUNT em vez de trazer todos os registros
            qtd_carteira = 0
            for codigo in codigos_relacionados:
                # Usar SUM direto no banco - MUITO mais rápido
                resultado = db.session.query(
                    db.func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido)
                ).filter(
                    CarteiraPrincipal.cod_produto == str(codigo),
                    CarteiraPrincipal.separacao_lote_id.is_(None),
                    CarteiraPrincipal.ativo == True
                ).scalar()
                if resultado:
                    qtd_carteira += float(resultado)
            
            # Calcular qtd_pre_separacao com SUM
            qtd_pre_separacao = 0
            for codigo in codigos_relacionados:
                resultado = db.session.query(
                    db.func.sum(PreSeparacaoItem.qtd_selecionada_usuario)
                ).filter(
                    PreSeparacaoItem.cod_produto == str(codigo),
                    PreSeparacaoItem.status.in_(['CRIADO', 'RECOMPOSTO'])
                ).scalar()
                if resultado:
                    qtd_pre_separacao += float(resultado)
            
            # Calcular qtd_separacao com SUM
            qtd_separacao = 0
            for codigo in codigos_relacionados:
                resultado = db.session.query(
                    db.func.sum(Separacao.qtd_saldo)
                ).join(
                    Pedido, Separacao.separacao_lote_id == Pedido.separacao_lote_id
                ).filter(
                    Separacao.cod_produto == str(codigo),
                    Pedido.status.in_(['ABERTO', 'COTADO']),
                    Separacao.qtd_saldo > 0
                ).scalar()
                if resultado:
                    qtd_separacao += float(resultado)
            
            # Atualizar cache - SEM recalcular saldo
            cache.qtd_carteira = qtd_carteira
            cache.qtd_pre_separacao = qtd_pre_separacao
            cache.qtd_separacao = qtd_separacao
            cache.ultima_atualizacao_carteira = agora_brasil()
            
            db.session.commit()
            logger.debug(f"✅ Quantidades atualizadas para {cod_produto} (SEM recalcular saldo)")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao atualizar quantidades: {e}")
            db.session.rollback()
            return False
    
    @staticmethod
    def atualizar_projecao_otimizada(cod_produto, data_especifica=None):
        """
        Atualiza projeção de forma otimizada
        Se data_especifica for fornecida, atualiza apenas essa data
        """
        try:
            from datetime import timedelta
            from app.producao.models import ProgramacaoProducao
            from app.carteira.models import PreSeparacaoItem
            from app.separacao.models import Separacao
            from app.pedidos.models import Pedido
            
            cache = SaldoEstoqueCache.query.filter_by(cod_produto=str(cod_produto)).first()
            if not cache:
                return False
            
            data_hoje = agora_brasil().date()
            
            # Se data específica, atualizar apenas ela
            if data_especifica:
                dias_para_atualizar = [(data_especifica - data_hoje).days]
            else:
                # Atualizar apenas os próximos 7 dias (mais críticos)
                dias_para_atualizar = range(7)
            
            for dia in dias_para_atualizar:
                if dia < 0 or dia >= 29:
                    continue
                    
                data_calculo = data_hoje + timedelta(days=dia)
                
                # Usar queries otimizadas com SUM
                saida_dia = 0
                
                # Pré-separações - SUM direto
                resultado = db.session.query(
                    db.func.sum(PreSeparacaoItem.qtd_selecionada_usuario)
                ).filter(
                    PreSeparacaoItem.cod_produto == str(cod_produto),
                    PreSeparacaoItem.data_expedicao_editada == data_calculo,
                    PreSeparacaoItem.status.in_(['CRIADO', 'RECOMPOSTO'])
                ).scalar()
                if resultado:
                    saida_dia += float(resultado)
                
                # Separações - SUM direto
                resultado = db.session.query(
                    db.func.sum(Separacao.qtd_saldo)
                ).join(
                    Pedido, Separacao.separacao_lote_id == Pedido.separacao_lote_id
                ).filter(
                    Separacao.cod_produto == str(cod_produto),
                    Pedido.expedicao == data_calculo,
                    Pedido.status.in_(['ABERTO', 'COTADO'])
                ).scalar()
                if resultado:
                    saida_dia += float(resultado)
                
                # Produção - SUM direto
                producao_dia = 0
                resultado = db.session.query(
                    db.func.sum(ProgramacaoProducao.qtd_programada)
                ).filter(
                    ProgramacaoProducao.cod_produto == str(cod_produto),
                    ProgramacaoProducao.data_programacao == data_calculo
                ).scalar()
                if resultado:
                    producao_dia += float(resultado)
                
                # Atualizar ou criar projeção para este dia
                projecao = ProjecaoEstoqueCache.query.filter_by(
                    cod_produto=str(cod_produto),
                    data_projecao=data_calculo
                ).first()
                
                if dia == 0:
                    estoque_inicial = float(cache.saldo_atual)
                else:
                    # Buscar estoque final do dia anterior
                    proj_anterior = ProjecaoEstoqueCache.query.filter_by(
                        cod_produto=str(cod_produto),
                        dia_offset=dia-1
                    ).first()
                    if proj_anterior:
                        estoque_inicial = float(proj_anterior.estoque_final)
                    else:
                        estoque_inicial = float(cache.saldo_atual)
                
                estoque_final = estoque_inicial - saida_dia + producao_dia
                
                if projecao:
                    # Atualizar existente
                    projecao.estoque_inicial = estoque_inicial
                    projecao.saida_prevista = saida_dia
                    projecao.producao_programada = producao_dia
                    projecao.estoque_final = estoque_final
                else:
                    # Criar nova
                    projecao = ProjecaoEstoqueCache(
                        cod_produto=str(cod_produto),
                        data_projecao=data_calculo,
                        dia_offset=dia,
                        estoque_inicial=estoque_inicial,
                        saida_prevista=saida_dia,
                        producao_programada=producao_dia,
                        estoque_final=estoque_final
                    )
                    db.session.add(projecao)
            
            # Atualizar previsão de ruptura
            if not data_especifica:
                projecoes_7d = ProjecaoEstoqueCache.query.filter(
                    ProjecaoEstoqueCache.cod_produto == str(cod_produto),
                    ProjecaoEstoqueCache.dia_offset <= 7
                ).all()
                
                if projecoes_7d:
                    menor_estoque = min(float(p.estoque_final) for p in projecoes_7d)
                    cache.previsao_ruptura_7d = menor_estoque
                    cache.ultima_atualizacao_projecao = agora_brasil()
            
            db.session.commit()
            logger.debug(f"✅ Projeção otimizada atualizada para {cod_produto}")
            return True
            
        except Exception as e:
            logger.error(f"Erro na projeção otimizada: {e}")
            db.session.rollback()
            return False

# Função principal para usar no sistema
def atualizar_cache_inteligente(cod_produto, tipo_mudanca='generico', data_afetada=None):
    """
    Atualização inteligente que decide o que precisa ser recalculado
    
    Args:
        cod_produto: Código do produto
        tipo_mudanca: 'movimentacao', 'carteira', 'pre_separacao', 'separacao', 'data'
        data_afetada: Data específica que foi alterada (para otimizar projeção)
    """
    
    if tipo_mudanca == 'movimentacao':
        # Precisa recalcular saldo completo
        from app.estoque.cache_triggers_safe import atualizar_cache_manualmente
        return atualizar_cache_manualmente(cod_produto)
    
    elif tipo_mudanca in ['carteira', 'pre_separacao', 'separacao']:
        # Só atualizar quantidades (rápido)
        CacheOptimizado.atualizar_apenas_quantidades(cod_produto)
        
        # Se houver data específica, atualizar só ela
        if data_afetada:
            CacheOptimizado.atualizar_projecao_otimizada(cod_produto, data_afetada)
        else:
            # Atualizar projeção dos próximos 7 dias
            CacheOptimizado.atualizar_projecao_otimizada(cod_produto)
        
        return True
    
    elif tipo_mudanca == 'data' and data_afetada:
        # Mudança apenas de data - super otimizado
        CacheOptimizado.atualizar_apenas_quantidades(cod_produto)
        CacheOptimizado.atualizar_projecao_otimizada(cod_produto, data_afetada)
        return True
    
    else:
        # Fallback para atualização completa
        from app.estoque.cache_triggers_safe import atualizar_cache_manualmente
        return atualizar_cache_manualmente(cod_produto)